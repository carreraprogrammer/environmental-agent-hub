"""Adapter implementation for Anthropic Claude vision models."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, Final

from anthropic import Anthropic, AsyncAnthropic, APIError, APITimeoutError, RateLimitError

from app.adapters.base import ClassifierAdapter
from app.agent.material_classifier import build_classification_prompt
from app.core.config import settings
from app.core.logging import logger
from app.schemas.domain import ClassificationResult, WasteMaterial

_ALLOWED_MODELS: Final[set[str]] = {
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-5-sonnet-20241022",  # Claude Sonnet 4.5
    "claude-sonnet-4-5",
}


class AnthropicAdapter(ClassifierAdapter):
    """Adapter for Anthropic Claude Vision family."""

    def __init__(self, model: str | None = None) -> None:
        """
        Initialize Anthropic adapter.

        Args:
            model: Claude model name (default: claude-3-5-sonnet-20241022)
        """
        self.model = (model or settings.ANTHROPIC_MODEL or "claude-3-5-sonnet-20241022").strip()
        if self.model not in _ALLOWED_MODELS:
            raise ValueError(
                f"Anthropic model must be one of {_ALLOWED_MODELS}, got: {self.model}"
            )

        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.max_retries = getattr(settings, "ANTHROPIC_MAX_RETRIES", 3)
        self.timeout = getattr(settings, "ANTHROPIC_TIMEOUT", 30.0)

        logger.info(
            "anthropic_adapter_initialized",
            model=self.model,
            max_retries=self.max_retries,
        )

    async def classify(
        self, image_url: str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        """
        Classify waste material from image URL (V3 compatibility).

        DEPRECATED: Use classify_material() for V4 unified classification.
        """
        bound_logger = logger.bind(trace_id=trace_id, adapter="anthropic")
        prompt = self._prepare_simple_prompt()

        # For URL-based classification, we'd need to download the image
        # For now, return a placeholder since V3 compatibility isn't critical
        bound_logger.warning(
            "anthropic_classify_deprecated",
            message="Use classify_material() with image bytes instead",
        )

        return ClassificationResult(
            material=WasteMaterial.OTHER,
            confidence=0.0,
            model_used=self.model_name,
            model_provider=self.model_provider,
            raw_response="V3 classify() is deprecated, use classify_material()",
        )

    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict[str, Any]:
        """
        Perform unified material classification with Claude Vision (V4).

        Args:
            image_data: Image bytes
            trace_id: Request trace ID

        Returns:
            Dict with complete classification and per-field confidences
        """
        bound_logger = logger.bind(trace_id=trace_id, adapter="anthropic")
        prompt = build_classification_prompt()
        attempt_error: Exception | None = None

        # Encode image to base64
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        # Detect media type (assume JPEG for simplicity, could be enhanced)
        media_type = "image/jpeg"
        if image_data.startswith(b"\x89PNG"):
            media_type = "image/png"
        elif image_data.startswith(b"RIFF") and b"WEBP" in image_data[:20]:
            media_type = "image/webp"

        for attempt in range(self.max_retries):
            try:
                bound_logger.info(
                    "anthropic_material_classification_request",
                    attempt=attempt + 1,
                    model=self.model,
                )

                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self.model,
                        max_tokens=2000,  # More tokens for detailed classification
                        temperature=0.0,  # Deterministic
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": media_type,
                                            "data": image_base64,
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": prompt,
                                    },
                                ],
                            }
                        ],
                    ),
                    timeout=self.timeout,
                )

                # Extract content
                if response.content and len(response.content) > 0:
                    content = response.content[0].text
                else:
                    raise ValueError("Empty response from Claude")

                break

            except (RateLimitError, APITimeoutError) as exc:
                attempt_error = exc
                if attempt < self.max_retries - 1:
                    sleep_seconds = 2**attempt
                    bound_logger.warning(
                        "anthropic_retry_backoff",
                        attempt=attempt + 1,
                        wait_seconds=sleep_seconds,
                    )
                    await asyncio.sleep(sleep_seconds)
                    continue
                raise

            except asyncio.TimeoutError as exc:
                attempt_error = exc
                bound_logger.error("anthropic_timeout", timeout=self.timeout)
                raise TimeoutError("Anthropic material classification timed out") from exc

            except APIError as exc:
                attempt_error = exc
                bound_logger.error("anthropic_api_error", error=str(exc))
                raise

        else:  # pragma: no cover
            raise TimeoutError("Anthropic material classification failed") from attempt_error

        # Parse JSON response
        result_dict = self._parse_material_classification(content, trace_id)

        # Add metadata
        result_dict["model_used"] = self.model_name
        result_dict["model_provider"] = self.model_provider
        result_dict["cost"] = self.cost_per_request

        bound_logger.info(
            "anthropic_material_classification_success",
            material=result_dict.get("material", {}).get("type"),
            subtype=result_dict.get("subtype", {}).get("value"),
        )

        return result_dict

    def _parse_material_classification(
        self, content: str, trace_id: str | None
    ) -> dict[str, Any]:
        """
        Parse Claude response into classification dict.

        Args:
            content: Raw response content (may contain markdown)
            trace_id: Request trace ID

        Returns:
            Dict with classification fields
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
                "anthropic_material_parse_error",
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

    def _prepare_simple_prompt(self) -> str:
        """Simple prompt for V3 compatibility."""
        return (
            "Clasifica el residuo en esta imagen en EXACTAMENTE una de estas categorías:\n\n"
            "- PLASTIC: Botellas plásticas, envases PET, bolsas, empaques\n"
            "- PAPER: Papel, cartón, periódicos, cajas\n"
            "- GLASS: Botellas de vidrio, frascos, cristal\n"
            "- METAL: Latas de aluminio o acero, envases metálicos\n"
            "- ORGANIC: Restos de comida, material vegetal, biodegradables\n"
            "- OTHER: Si no encaja claramente en las anteriores\n\n"
            "Responde SOLO con el nombre de la categoría en MAYÚSCULAS"
        )

    @property
    def model_name(self) -> str:
        return f"anthropic/{self.model}"

    @property
    def model_provider(self) -> str:
        return "anthropic"

    @property
    def cost_per_request(self) -> float:
        pricing: dict[str, float] = {
            "claude-3-opus-20240229": 0.015,
            "claude-3-sonnet-20240229": 0.003,
            "claude-3-5-sonnet-20241022": 0.003,  # Claude Sonnet 4.5
            "claude-sonnet-4-5": 0.003,
        }
        return pricing.get(self.model, 0.003)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AnthropicAdapter(model='{self.model}')"
