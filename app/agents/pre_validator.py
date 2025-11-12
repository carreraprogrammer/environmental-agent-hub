"""
PreValidator Agent - Anti-Troll waste detection.

Responsibilities:
- Binary detection: does image contain waste? (YES/NO)
- Reject trolls, selfies, landscapes, inappropriate content
- Fast and cheap: GPT-4o-mini (~$0.0002/request)
- Aggressive timeout: 500ms max latency

This agent protects the pipeline from abuse and reduces costs by filtering
out non-waste images before expensive classification.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging import logger
from app.schemas.validation import ValidationResult

if TYPE_CHECKING:
    import openai


class PreValidator:
    """
    PreValidator Agent - Detects if image contains waste (anti-troll).

    Uses GPT-4o-mini for fast and cheap binary classification.
    Cost: ~$0.0002 per request
    Timeout: 500ms

    Example:
        >>> validator = PreValidator()
        >>> result = await validator.validate(image_bytes, "trace-123")
        >>> if result.has_waste:
        ...     print(f"Waste detected: {result.reason}")
        ... else:
        ...     print(f"No waste: {result.reason}")
    """

    def __init__(self, timeout: float = 0.5):
        """
        Initialize PreValidator with OpenAI client.

        Args:
            timeout: Timeout in seconds for validation (default: 0.5s = 500ms)
        """
        # Lazy import to avoid loading OpenAI unless needed
        import openai

        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"
        self.timeout = timeout

    async def validate(self, image_data: bytes, trace_id: str) -> ValidationResult:
        """
        Validate if image contains waste.

        Args:
            image_data: Image bytes (JPEG, PNG, etc.)
            trace_id: Request trace ID for logging

        Returns:
            ValidationResult with has_waste, confidence, reason

        Raises:
            TimeoutError: If validation takes >500ms
            ValueError: If API fails or image is invalid

        Example:
            >>> validator = PreValidator()
            >>> with open("bottle.jpg", "rb") as f:
            ...     image_bytes = f.read()
            >>> result = await validator.validate(image_bytes, "trace-123")
            >>> print(f"Has waste: {result.has_waste}")
            Has waste: True
        """
        logger.info(
            "pre_validator_started",
            trace_id=trace_id,
            agent="PreValidator",
            model=self.model,
            timeout_ms=self.timeout * 1000,
        )

        try:
            # Timeout wrapper
            result = await asyncio.wait_for(
                self._call_gpt4o_mini(image_data, trace_id), timeout=self.timeout
            )

            logger.info(
                "pre_validator_complete",
                trace_id=trace_id,
                agent="PreValidator",
                has_waste=result.has_waste,
                confidence=result.confidence,
                reason=result.reason[:100],  # Truncate for logging
            )

            return result

        except asyncio.TimeoutError:
            logger.error(
                "pre_validator_timeout",
                trace_id=trace_id,
                agent="PreValidator",
                timeout_ms=self.timeout * 1000,
            )
            raise TimeoutError(
                f"PreValidator timeout after {self.timeout}s (500ms limit exceeded)"
            )

        except Exception as e:
            logger.error(
                "pre_validator_error",
                trace_id=trace_id,
                agent="PreValidator",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ValueError(f"PreValidator failed: {str(e)}")

    async def _call_gpt4o_mini(
        self, image_data: bytes, trace_id: str
    ) -> ValidationResult:
        """
        Call GPT-4o-mini API for waste detection.

        Args:
            image_data: Image bytes
            trace_id: Request trace ID for logging

        Returns:
            ValidationResult with parsed response

        Raises:
            Exception: If API call fails
        """
        # Encode image to base64
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        # Prompt engineering: Spanish, structured JSON, clear criteria
        prompt = """Analiza esta imagen y determina si contiene algún tipo de RESIDUO o BASURA.

Residuos incluyen: botellas, latas, papel, cartón, envases, empaques, desechos orgánicos,
envolturas, contenedores, bolsas, plásticos, vidrio, metal, etc.

Responde ÚNICAMENTE en formato JSON:
{
  "has_waste": true o false,
  "confidence": 0.0 a 1.0,
  "reason": "Descripción breve en español de qué ves"
}

IMPORTANTE:
- Si ves residuos → has_waste: true
- Si es selfie, paisaje, animal, persona, objeto NO residuo → has_waste: false
- Si la imagen es borrosa o no se distingue → has_waste: false, confidence bajo
- Si no estás seguro → has_waste: false, confidence bajo

Ejemplos:
- Botella de plástico en el suelo → has_waste: true, confidence: 0.95
- Selfie de una persona → has_waste: false, confidence: 0.99
- Paisaje de montaña → has_waste: false, confidence: 0.95
- Imagen borrosa → has_waste: false, confidence: 0.3"""

        try:
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
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=150,  # Sufficient for short JSON response
                temperature=0.0,  # Deterministic output
            )

            # Extract response content
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from GPT-4o-mini")

            # Parse JSON response
            return self._parse_response(content, trace_id)

        except Exception as e:
            logger.error(
                "pre_validator_api_error",
                trace_id=trace_id,
                agent="PreValidator",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _parse_response(self, content: str, trace_id: str) -> ValidationResult:
        """
        Parse GPT-4o-mini response into ValidationResult.

        Args:
            content: Raw response content (may contain markdown)
            trace_id: Request trace ID for logging

        Returns:
            ValidationResult with parsed data

        Note:
            Handles markdown code blocks (```json) and falls back to
            safe defaults if parsing fails.
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
            if "has_waste" not in result_dict:
                raise ValueError("Missing 'has_waste' field in response")
            if "confidence" not in result_dict:
                raise ValueError("Missing 'confidence' field in response")
            if "reason" not in result_dict:
                raise ValueError("Missing 'reason' field in response")

            return ValidationResult(
                has_waste=bool(result_dict["has_waste"]),
                confidence=float(result_dict["confidence"]),
                reason=str(result_dict["reason"]),
            )

        except Exception as e:
            logger.warning(
                "pre_validator_parse_error",
                trace_id=trace_id,
                agent="PreValidator",
                raw_response=content[:200],  # Truncate for logging
                error=str(e),
            )

            # Fallback: assume it's waste for safety (better false positive than false negative)
            # This prevents blocking legitimate waste images due to parsing errors
            return ValidationResult(
                has_waste=True,
                confidence=0.5,
                reason="Error parsing response, assuming waste for safety",
            )

    async def close(self):
        """Close OpenAI client and cleanup resources."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Legacy function for backward compatibility
def validate_payload(payload: dict[str, object]) -> bool:
    """
    Placeholder validation logic for incoming payloads.

    DEPRECATED: Use PreValidator class instead.

    Args:
        payload: Request payload data

    Returns:
        bool: True if payload passes placeholder validation
    """
    return bool(payload)
