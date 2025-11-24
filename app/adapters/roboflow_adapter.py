"""Adapter implementation for Roboflow waste classifiers."""

from __future__ import annotations

import asyncio

from inference_sdk import InferenceHTTPClient

from app.adapters.base import ClassifierAdapter
from app.core.config import settings
from app.core.logging import logger
from app.schemas.domain import ClassificationResult, WasteMaterial


class RoboflowClassifierAdapter(ClassifierAdapter):
    """Adapter for specialized Roboflow waste classification models."""

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or settings.ROBOFLOW_MODEL_ID
        try:
            workspace, project, version = self.model_id.split("/")
        except ValueError as exc:
            raise ValueError(
                "Roboflow model_id must follow 'workspace/project/version' format"
            ) from exc

        # InferenceHTTPClient expects project/version (without workspace)
        self.inference_model_id = f"{project}/{version}"

        # Use serverless inference client for hosted classification models
        self.client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=settings.ROBOFLOW_API_KEY,
        )

        logger.info(
            "roboflow_adapter_initialized",
            model_id=self.model_id,
            api_url="https://serverless.roboflow.com",
            workspace=workspace,
            project=project,
            version=version,
        )

    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict:
        """Roboflow doesn't support full classify_material yet, use basic classify."""
        # For now, return minimal classification
        result = await self.classify_bytes(image_data, trace_id=trace_id)
        return {
            "material": {"material_type": result.material, "confidence": result.confidence},
            "subtype": {"value": None, "confidence": 0.0},
            "condition": {"value": "UNKNOWN", "confidence": 0.0},
            "volume": {"liters": 0.0, "confidence": 0.0},
            "recyclability": {"recyclable": True, "confidence": 0.8},
        }

    async def classify_bytes(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> ClassificationResult:
        """Fast classification from image bytes."""
        bound_logger = logger.bind(trace_id=trace_id, adapter="roboflow")
        bound_logger.info("roboflow_fast_classification", model_id=self.model_id)

        import tempfile
        import os

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(image_data)
                tmp_path = tmp.name

            try:
                prediction = await asyncio.to_thread(
                    self.client.infer,
                    tmp_path,
                    model_id=self.inference_model_id,
                )
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            bound_logger.error("roboflow_fast_classification_failed", error=str(e))
            raise

        predictions = self._extract_predictions(prediction)
        if not predictions:
            bound_logger.warning("roboflow_no_predictions")
            return ClassificationResult(
                material=WasteMaterial.OTHER,
                confidence=0.0,
                model_used=self.model_name,
                model_provider=self.model_provider,
                raw_response="No predictions",
            )

        best_prediction = self._select_top_prediction(predictions)
        class_name, confidence, confidence_source = self._extract_class_and_confidence(
            best_prediction
        )

        material = self._map_roboflow_class(class_name)

        bound_logger.info(
            "roboflow_fast_classification_success",
            material=material.value,
            confidence=confidence,
            latency_estimate="400-800ms",
            confidence_source=confidence_source,
            raw_prediction=str(best_prediction),
        )

        return ClassificationResult(
            material=material,
            confidence=confidence,
            model_used=self.model_name,
            model_provider=self.model_provider,
            raw_response=class_name,
        )

    async def classify(
        self, image_url: str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        bound_logger = logger.bind(trace_id=trace_id, adapter="roboflow")
        bound_logger.info("roboflow_request", image_url=image_url, model_id=self.model_id)

        try:
            prediction = await asyncio.to_thread(
                self.client.infer,
                image_url,
                model_id=self.inference_model_id,
            )
        except Exception as e:
            # If hosted fails, log the error
            bound_logger.error("roboflow_prediction_failed", error=str(e))
            raise

        predictions = self._extract_predictions(prediction)
        if not predictions:
            bound_logger.warning("roboflow_no_predictions")
            return ClassificationResult(
                material=WasteMaterial.OTHER,
                confidence=0.0,
                model_used=self.model_name,
                model_provider=self.model_provider,
                raw_response="No predictions",
            )

        best_prediction = self._select_top_prediction(predictions)
        class_name, confidence, confidence_source = self._extract_class_and_confidence(
            best_prediction
        )

        material = self._map_roboflow_class(class_name)

        bound_logger.info(
            "roboflow_classification_success",
            material=material.value,
            confidence=confidence,
            confidence_source=confidence_source,
            raw_prediction=str(best_prediction),
        )

        return ClassificationResult(
            material=material,
            confidence=confidence,
            model_used=self.model_name,
            model_provider=self.model_provider,
            raw_response=class_name,
        )

    def _map_roboflow_class(self, class_name: str) -> WasteMaterial:
        normalized = class_name.lower()
        direct_map = {
            "plastic": WasteMaterial.PLASTIC,
            "paper": WasteMaterial.PAPER,
            "glass": WasteMaterial.GLASS,
            "metal": WasteMaterial.METAL,
            "organic": WasteMaterial.ORGANIC,
            "cardboard": WasteMaterial.PAPER,
        }

        if normalized in direct_map:
            return direct_map[normalized]

        # Heuristics for common label variants
        if "plastic" in normalized or "pet" in normalized:
            return WasteMaterial.PLASTIC
        if "bottle" in normalized:
            return WasteMaterial.PLASTIC
        if "bag" in normalized:
            return WasteMaterial.PLASTIC
        if "plastico" in normalized:
            return WasteMaterial.PLASTIC
        if "paper" in normalized or "cardboard" in normalized:
            return WasteMaterial.PAPER
        if "carton" in normalized:
            return WasteMaterial.PAPER
        if "papel" in normalized:
            return WasteMaterial.PAPER
        if "glass" in normalized:
            return WasteMaterial.GLASS
        if "vidrio" in normalized:
            return WasteMaterial.GLASS
        if "metal" in normalized or "aluminum" in normalized:
            return WasteMaterial.METAL
        if "can" in normalized or "lata" in normalized:
            return WasteMaterial.METAL
        if "organic" in normalized or "food" in normalized:
            return WasteMaterial.ORGANIC
        if "organico" in normalized or "comida" in normalized:
            return WasteMaterial.ORGANIC
        if "biodegradable" in normalized:
            return WasteMaterial.ORGANIC
        return WasteMaterial.OTHER

    def _extract_predictions(self, prediction: object) -> list:
        """
        Normalize predictions container from Roboflow response.

        Roboflow SDK may return an object with `.predictions`, or a dict,
        or require calling `.json()`. We try them in order.
        """
        preds = getattr(prediction, "predictions", None)
        if preds:
            return preds

        # Dict-style response
        try:
            preds = prediction["predictions"]  # type: ignore[index]
            if preds:
                return preds
        except Exception:
            pass

        # JSON payload from SDK
        try:
            payload = prediction.json()  # type: ignore[call-arg]
            if payload and payload.get("predictions"):
                return payload["predictions"]
        except Exception:
            pass

        return []

    def _extract_class_and_confidence(self, top_prediction: object) -> tuple[str, float, str]:
        """
        Extract class name and confidence from a prediction entry.

        Supports Roboflow classification models (keys: top/class) and detection
        models (class_name). If confidence is missing, default to 1.0 so the
        fast path can return immediately.
        """
        class_name = getattr(top_prediction, "class_name", None)
        confidence_attr = getattr(top_prediction, "confidence", None)

        if class_name is None:
            try:
                class_name = top_prediction.get("class")  # type: ignore[call-arg]
            except Exception:
                class_name = None

        # Roboflow classification models often use "top" for the winning class
        if class_name is None:
            try:
                class_name = top_prediction.get("top")  # type: ignore[call-arg]
            except Exception:
                class_name = None

        if class_name is None:
            try:
                class_name = top_prediction.get("class_name")  # type: ignore[call-arg]
            except Exception:
                class_name = None

        if class_name is None:
            class_name = ""

        confidence = None
        if confidence_attr is not None:
            confidence = float(confidence_attr)
        else:
            try:
                confidence_val = top_prediction.get("confidence")  # type: ignore[call-arg]
                if confidence_val is not None:
                    confidence = float(confidence_val)
            except Exception:
                confidence = None

        # Fallback: some Roboflow classes expose .json() returning a dict
        if class_name in ("", None) or confidence is None:
            try:
                payload = top_prediction.json()  # type: ignore[call-arg]
                if not class_name:
                    class_name = (
                        payload.get("class")
                        or payload.get("top")
                        or payload.get("class_name")
                        or class_name
                    )
                if confidence is None:
                    payload_conf = payload.get("confidence")
                    if payload_conf is not None:
                        confidence = float(payload_conf)
            except Exception:
                pass

        if confidence is None:
            confidence = 1.0
            confidence_source = "default_1.0"
        else:
            confidence_source = "roboflow"

        return class_name, confidence, confidence_source

    def _select_top_prediction(self, predictions: list) -> object:
        """
        Pick the prediction with the highest confidence (default 1.0 if missing).
        """

        def _conf(pred: object) -> float:
            try:
                val = getattr(pred, "confidence", None)
                if val is None:
                    val = pred.get("confidence")  # type: ignore[call-arg]
                if val is None and hasattr(pred, "json"):
                    payload = pred.json()  # type: ignore[call-arg]
                    val = payload.get("confidence")
                return float(val) if val is not None else 1.0
            except Exception:
                return 1.0

        return max(predictions, key=_conf)

    @property
    def model_name(self) -> str:
        return f"roboflow/{self.inference_model_id}"

    @property
    def model_provider(self) -> str:
        return "roboflow"

    @property
    def cost_per_request(self) -> float:
        return 0.001

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"RoboflowClassifierAdapter(model_id='{self.model_id}')"
