"""Adapter implementation for OpenAI vision models."""

from __future__ import annotations

import asyncio
import base64
from typing import Final

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.adapters.base import ClassifierAdapter
from app.core.config import settings
from app.core.logging import logger
from app.schemas.domain import ClassificationResult, WasteMaterial

_ALLOWED_MODELS: Final[set[str]] = {"gpt-4-vision-preview", "gpt-4o"}


class OpenAIClassifierAdapter(ClassifierAdapter):
    """Adapter for OpenAI GPT-4 Vision family."""

    def __init__(self, model: str | None = None) -> None:
        self.model = (model or settings.OPENAI_MODEL).strip()
        if self.model not in _ALLOWED_MODELS:
            raise ValueError("OpenAI model must be one of 'gpt-4-vision-preview' or 'gpt-4o'")

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def classify(
        self, image: bytes | str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        bound_logger = logger.bind(trace_id=trace_id, adapter="openai")
        prompt = self._prepare_prompt()
        attempt_error: Exception | None = None

        # Convert bytes to base64 data URL if needed
        image_url = self._prepare_image(image)

        for attempt in range(settings.OPENAI_MAX_RETRIES):
            try:
                bound_logger.info(
                    "openai_request",
                    attempt=attempt + 1,
                    image_type="bytes" if isinstance(image, bytes) else "url",
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

    def _prepare_image(self, image: bytes | str) -> str:
        """
        Convert image to format expected by OpenAI API.

        Args:
            image: Raw image bytes or URL string

        Returns:
            URL string (either original or base64 data URL)
        """
        if isinstance(image, bytes):
            # Convert to base64 data URL
            base64_image = base64.b64encode(image).decode("utf-8")
            return f"data:image/jpeg;base64,{base64_image}"
        return image  # Already a URL

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
        }
        return pricing.get(self.model, 0.010)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"OpenAIClassifierAdapter(model='{self.model}')"
