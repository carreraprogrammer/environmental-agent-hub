"""Adapter implementation for Roboflow waste classifiers."""

from __future__ import annotations

import asyncio

from roboflow import Roboflow

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

        client = Roboflow(api_key=settings.ROBOFLOW_API_KEY)
        project_ref = client.workspace(workspace).project(project)
        self.model = project_ref.version(version).model

        logger.info("roboflow_adapter_initialized", model_id=self.model_id)

    async def classify(
        self, image_url: str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        bound_logger = logger.bind(trace_id=trace_id, adapter="roboflow")
        bound_logger.info("roboflow_request", image_url=image_url, model_id=self.model_id)

        # Roboflow needs the actual URL string - it handles the download internally
        # But we need to check if it's a valid URL that Roboflow can access
        try:
            prediction = await asyncio.to_thread(
                self.model.predict,
                image_url,
                hosted=True,  # Indicates it's a hosted URL
            )
        except Exception as e:
            # If hosted fails, log the error
            bound_logger.error("roboflow_prediction_failed", error=str(e))
            raise

        predictions = getattr(prediction, "predictions", None) or []
        if not predictions:
            bound_logger.warning("roboflow_no_predictions")
            return ClassificationResult(
                material=WasteMaterial.OTHER,
                confidence=0.0,
                model_used=self.model_name,
                model_provider=self.model_provider,
                raw_response="No predictions",
            )

        top_prediction = predictions[0]
        class_name = getattr(top_prediction, "class_name", "")
        confidence = float(getattr(top_prediction, "confidence", 0.0))

        material = self._map_roboflow_class(class_name)

        bound_logger.info(
            "roboflow_classification_success",
            material=material.value,
            confidence=confidence,
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
        }

        if normalized in direct_map:
            return direct_map[normalized]

        if "plastic" in normalized or "pet" in normalized:
            return WasteMaterial.PLASTIC
        if "paper" in normalized or "cardboard" in normalized:
            return WasteMaterial.PAPER
        if "glass" in normalized:
            return WasteMaterial.GLASS
        if "metal" in normalized or "aluminum" in normalized:
            return WasteMaterial.METAL
        if "organic" in normalized or "food" in normalized:
            return WasteMaterial.ORGANIC
        return WasteMaterial.OTHER

    @property
    def model_name(self) -> str:
        return f"roboflow/{self.model_id}"

    @property
    def model_provider(self) -> str:
        return "roboflow"

    @property
    def cost_per_request(self) -> float:
        return 0.001

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"RoboflowClassifierAdapter(model_id='{self.model_id}')"
