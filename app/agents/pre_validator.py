from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import openai

from app.core.config import settings
from app.core.logging import logger
from app.schemas.validation import ValidationResult


class PreValidator:
    """
    PreValidator Agent - Detects if image contains waste (anti-troll).

    Uses GPT-4o-mini for fast and cheap binary classification.
    Cost: ~$0.0002 per request
    Timeout: 500ms
    """

    def __init__(self) -> None:
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"
        self.timeout = 0.5  # 500ms

    async def validate(self, image_data: bytes, trace_id: str) -> ValidationResult:
        """
        Validate if image contains waste.

        Args:
            image_data: Image bytes
            trace_id: Request trace ID

        Returns:
            ValidationResult with has_waste, confidence, reason

        Raises:
            TimeoutError: If validation takes >500ms
            ValueError: If API fails
        """
        logger.info(
            "pre_validator_started",
            trace_id=trace_id,
            agent="PreValidator",
            model=self.model,
        )

        try:
            result = await asyncio.wait_for(
                self._call_gpt4o_mini(image_data, trace_id),
                timeout=self.timeout,
            )

            logger.info(
                "pre_validator_complete",
                trace_id=trace_id,
                has_waste=result.has_waste,
                confidence=result.confidence,
            )

            return result

        except asyncio.TimeoutError:
            logger.error(
                "pre_validator_timeout",
                trace_id=trace_id,
                timeout_ms=self.timeout * 1000,
            )
            raise TimeoutError(f"PreValidator timeout after {self.timeout}s")

        except Exception as e:  # noqa: BLE001 - bubble as ValueError per spec
            logger.error(
                "pre_validator_error",
                trace_id=trace_id,
                error=str(e),
            )
            raise ValueError(f"PreValidator failed: {str(e)}")

    async def _call_gpt4o_mini(self, image_data: bytes, trace_id: str) -> ValidationResult:
        """Call GPT-4o-mini API for waste detection"""

        image_base64 = base64.b64encode(image_data).decode("utf-8")

        prompt = (
            """Analiza esta imagen y determina si contiene algún tipo de RESIDUO o BASURA.

Residuos incluyen: botellas, latas, papel, cartón, envases, empaques, desechos orgánicos, 
envolturas, contenedores, bolsas, etc.

Responde ÚNICAMENTE en formato JSON:
{
  "has_waste": true o false,
  "confidence": 0.0 a 1.0,
  "reason": "Descripción breve en español de qué ves"
}

IMPORTANTE:
- Si ves residuos → has_waste: true
- Si es selfie, paisaje, animal, persona, objeto NO residuo → has_waste: false
- Si la imagen es borrosa o no se distingue → has_waste: false, confidence bajo"""
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=150,
            temperature=0.0,  # Deterministic
        )

        content: str = response.choices[0].message.content  # type: ignore[assignment]

        try:
            # Extract JSON if wrapped in code fences
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result_dict: dict[str, Any] = json.loads(content)

            return ValidationResult(
                has_waste=bool(result_dict["has_waste"]),
                confidence=float(result_dict["confidence"]),
                reason=str(result_dict["reason"]),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "pre_validator_parse_error",
                trace_id=trace_id,
                raw_response=content,
                error=str(e),
            )
            # Fallback: assume it's waste if parsing fails
            return ValidationResult(
                has_waste=True,
                confidence=0.5,
                reason="Error parsing response, assuming waste for safety",
            )


# Backwards-compat placeholder used by legacy pipeline placeholder
def validate_payload(payload: dict[str, object]) -> bool:  # pragma: no cover - legacy compat
    """Simple payload validation used by the old placeholder pipeline."""
    return bool(payload)
