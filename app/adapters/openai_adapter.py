"""Adapter implementation for OpenAI vision models."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, Final

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.adapters.base import ClassifierAdapter
from app.agents.material_classifier import build_classification_prompt
from app.core.config import settings
from app.core.logging import logger
from app.schemas.domain import ClassificationResult, WasteMaterial

_ALLOWED_MODELS: Final[set[str]] = {"gpt-4-vision-preview", "gpt-4o", "gpt-4-turbo"}


class OpenAIClassifierAdapter(ClassifierAdapter):
    """Adapter for OpenAI GPT-4 Vision family."""

    def __init__(self, model: str | None = None) -> None:
        self.model = (model or settings.OPENAI_MODEL).strip()
        if self.model not in _ALLOWED_MODELS:
            raise ValueError("OpenAI model must be one of 'gpt-4-vision-preview' or 'gpt-4o'")

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def classify(
        self, image_url: str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        bound_logger = logger.bind(trace_id=trace_id, adapter="openai")
        prompt = self._prepare_prompt()
        attempt_error: Exception | None = None

        for attempt in range(settings.OPENAI_MAX_RETRIES):
            try:
                bound_logger.info(
                    "openai_request",
                    attempt=attempt + 1,
                    image_url=image_url,
                    model=self.model,
                )
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": image_url},
                                    },
                                ],
                            }
                        ],
                        max_tokens=100,
                        temperature=0.0,
                    ),
                    timeout=settings.OPENAI_TIMEOUT,
                )
                content = response.choices[0].message.content or ""
                break
            except (RateLimitError, APITimeoutError) as exc:
                attempt_error = exc
                if attempt < settings.OPENAI_MAX_RETRIES - 1:
                    sleep_seconds = 2**attempt
                    bound_logger.warning(
                        "openai_retry_backoff",
                        attempt=attempt + 1,
                        wait_seconds=sleep_seconds,
                    )
                    await asyncio.sleep(sleep_seconds)
                    continue
                raise
            except asyncio.TimeoutError as exc:  # pragma: no cover - wait_for raises
                attempt_error = exc
                bound_logger.error("openai_timeout", timeout=settings.OPENAI_TIMEOUT)
                raise TimeoutError("OpenAI classification timed out") from exc
            except APIError as exc:
                attempt_error = exc
                bound_logger.error("openai_api_error", error=str(exc))
                raise
        else:  # pragma: no cover - loop else for completeness
            raise TimeoutError("OpenAI classification failed") from attempt_error

        content = content.strip().upper()
        material = self._parse_material(content)
        confidence = self._estimate_confidence(content)

        bound_logger.info(
            "openai_classification_success",
            material=material.value,
            confidence=confidence,
        )

        return ClassificationResult(
            material=material,
            confidence=confidence,
            model_used=self.model_name,
            model_provider=self.model_provider,
            raw_response=content,
        )

    def _prepare_prompt(self) -> str:
        return (
            "\n"
            "Clasifica el residuo en esta imagen en EXACTAMENTE una de estas categorías:\n\n"
            "- PLASTIC: Botellas plásticas, envases PET, bolsas, empaques\n"
            "- PAPER: Papel, cartón, periódicos, cajas\n"
            "- GLASS: Botellas de vidrio, frascos, cristal\n"
            "- METAL: Latas de aluminio o acero, envases metálicos\n"
            "- ORGANIC: Restos de comida, material vegetal, biodegradables\n"
            "- OTHER: Si no encaja claramente en las anteriores\n\n"
            "INSTRUCCIONES CRÍTICAS:\n"
            "1. Responde SOLO con el nombre de la categoría en MAYÚSCULAS\n"
            "2. NO agregues explicaciones adicionales\n"
            "3. Si tienes dudas, usa OTHER\n"
            "4. Si ves múltiples objetos, clasifica el más prominente\n\n"
            "Respuesta:"
        )

    def _parse_material(self, content: str) -> WasteMaterial:
        cleaned = content.strip().upper()
        try:
            return WasteMaterial(cleaned)
        except ValueError:
            pass

        if "PLASTIC" in cleaned or "PLÁSTICO" in cleaned:
            return WasteMaterial.PLASTIC
        if "PAPER" in cleaned or "PAPEL" in cleaned or "CARTÓN" in cleaned:
            return WasteMaterial.PAPER
        if "GLASS" in cleaned or "VIDRIO" in cleaned:
            return WasteMaterial.GLASS
        if "METAL" in cleaned:
            return WasteMaterial.METAL
        if "ORGANIC" in cleaned or "ORGÁNICO" in cleaned:
            return WasteMaterial.ORGANIC
        return WasteMaterial.OTHER

    def _estimate_confidence(self, content: str) -> float:
        words = [word for word in content.strip().split() if word]
        return 0.85 if len(words) == 1 else 0.70

    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict[str, Any]:
        """
        Perform unified material classification with GPT-4 Vision (V4).

        Args:
            image_data: Image bytes
            trace_id: Request trace ID

        Returns:
            Dict with complete classification and per-field confidences
        """
        bound_logger = logger.bind(trace_id=trace_id, adapter="openai")
        prompt = build_classification_prompt()
        attempt_error: Exception | None = None

        # Encode image to base64
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        for attempt in range(settings.OPENAI_MAX_RETRIES):
            try:
                bound_logger.info(
                    "openai_material_classification_request",
                    attempt=attempt + 1,
                    model=self.model,
                )
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_base64}"
                                        },
                                    },
                                ],
                            }
                        ],
                        max_tokens=1000,  # More tokens for detailed classification
                        temperature=0.0,  # Deterministic
                    ),
                    timeout=settings.OPENAI_TIMEOUT,
                )
                content = response.choices[0].message.content or ""
                break
            except (RateLimitError, APITimeoutError) as exc:
                attempt_error = exc
                if attempt < settings.OPENAI_MAX_RETRIES - 1:
                    sleep_seconds = 2**attempt
                    bound_logger.warning(
                        "openai_retry_backoff",
                        attempt=attempt + 1,
                        wait_seconds=sleep_seconds,
                    )
                    await asyncio.sleep(sleep_seconds)
                    continue
                raise
            except asyncio.TimeoutError as exc:
                attempt_error = exc
                bound_logger.error("openai_timeout", timeout=settings.OPENAI_TIMEOUT)
                raise TimeoutError("OpenAI material classification timed out") from exc
            except APIError as exc:
                attempt_error = exc
                bound_logger.error("openai_api_error", error=str(exc))
                raise
        else:  # pragma: no cover
            raise TimeoutError("OpenAI material classification failed") from attempt_error

        # Parse JSON response
        result_dict = self._parse_material_classification(content, trace_id)

        # Add metadata
        result_dict["model_used"] = self.model_name
        result_dict["model_provider"] = self.model_provider
        result_dict["cost"] = self.cost_per_request

        bound_logger.info(
            "openai_material_classification_success",
            material=result_dict.get("material", {}).get("type"),
            subtype=result_dict.get("subtype", {}).get("value"),
        )

        return result_dict

    def _parse_material_classification(
        self, content: str, trace_id: str | None
    ) -> dict[str, Any]:
        """
        Parse GPT-4 Vision response into classification dict.

        Args:
            content: Raw response content (may contain markdown)
            trace_id: Request trace ID

        Returns:
            Dict with classification fields

        Note:
            Handles markdown code blocks and validates JSON schema.
        """
        try:
            # Strip markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON
            result_dict = json.loads(content)

            # Validate required fields
            if "material" not in result_dict:
                raise ValueError("Missing 'material' field in response")
            if "type" not in result_dict["material"]:
                raise ValueError("Missing 'material.type' field in response")
            if "confidence" not in result_dict["material"]:
                raise ValueError("Missing 'material.confidence' field in response")

            return result_dict

        except Exception as e:
            logger.warning(
                "openai_material_parse_error",
                trace_id=trace_id,
                raw_response=content[:200],
                error=str(e),
            )

            # Fallback: return minimal valid structure
            return {
                "material": {"type": "OTHER", "confidence": 0.5},
                "subtype": {"value": None, "recycling_code": None, "confidence": 0.0},
                "condition": {"value": "CLEAN", "confidence": 0.5},
                "volume": {"liters": None, "source": "ESTIMATED", "confidence": 0.0},
                "recyclability": {"value": "RECYCLABLE", "confidence": 0.5},
                "reasoning": f"Error parsing response: {str(e)}",
            }

    @property
    def model_name(self) -> str:
        return f"openai/{self.model}"

    @property
    def model_provider(self) -> str:
        return "openai"

    @property
    def cost_per_request(self) -> float:
        pricing: dict[str, float] = {
            "gpt-4-vision-preview": 0.010,
            "gpt-4o": 0.005,
            "gpt-4-turbo": 0.010,
        }
        return pricing.get(self.model, 0.010)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"OpenAIClassifierAdapter(model='{self.model}')"
