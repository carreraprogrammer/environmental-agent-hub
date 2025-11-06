"""Adapter implementation for Google Gemini models."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import ClassVar, Deque

import google.generativeai as genai
import httpx

from app.adapters.base import ClassifierAdapter
from app.core.config import settings
from app.core.logging import logger
from app.schemas.domain import ClassificationResult, WasteMaterial

_MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class GoogleClassifierAdapter(ClassifierAdapter):
    """Adapter for Google Gemini Pro Vision with rate limiting."""

    _request_timestamps: ClassVar[Deque[datetime]] = deque(maxlen=60)
    _daily_requests: ClassVar[int] = 0
    _daily_reset: ClassVar[datetime] = datetime.now()

    def __init__(self, model: str | None = None) -> None:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model_name_internal = (model or settings.GOOGLE_MODEL).strip()
        self.model = genai.GenerativeModel(self.model_name_internal)

    async def classify(
        self, image_url: str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        bound_logger = logger.bind(trace_id=trace_id, adapter="google")
        await self._wait_for_rate_limit(bound_logger)

        image_part = await self._download_image(image_url, bound_logger)
        prompt = self._prepare_prompt()

        bound_logger.info("google_request", image_url=image_url, model=self.model_name_internal)
        try:
            response = await self.model.generate_content_async([prompt, image_part])
        except Exception as exc:  # pragma: no cover - SDK specific errors
            bound_logger.error("google_api_error", error=str(exc))
            raise

        content = (response.text or "").strip().upper()
        material = self._parse_material(content)
        confidence = 0.80

        self._register_request()
        bound_logger.info(
            "google_classification_success",
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

    async def _wait_for_rate_limit(self, bound_logger) -> None:
        now = datetime.now()
        cutoff = now - timedelta(seconds=60)

        while self._request_timestamps and self._request_timestamps[0] < cutoff:
            self._request_timestamps.popleft()

        if len(self._request_timestamps) >= settings.GOOGLE_RATE_LIMIT_PER_MIN:
            wait_time = max(
                1,
                60 - int((now - self._request_timestamps[0]).total_seconds()),
            )
            bound_logger.warning("google_rate_limit_wait", wait_seconds=wait_time)
            await asyncio.sleep(wait_time)

        if now.date() != self._daily_reset.date():
            self._daily_requests = 0
            self._daily_reset = now

        if self._daily_requests >= settings.GOOGLE_DAILY_LIMIT:
            raise RuntimeError("Google API daily limit exceeded")

    def _register_request(self) -> None:
        self._request_timestamps.append(datetime.now())
        self._daily_requests += 1

    async def _download_image(self, url: str, bound_logger) -> dict[str, bytes | str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > _MAX_IMAGE_SIZE_BYTES:
                raise ValueError("Image exceeds 10MB limit for Gemini")
            content_type = response.headers.get("content-type", "image/jpeg")
            data = response.content
            if len(data) > _MAX_IMAGE_SIZE_BYTES:
                raise ValueError("Image exceeds 10MB limit for Gemini")

        bound_logger.info("google_image_downloaded", content_type=content_type)
        return {"mime_type": content_type, "data": data}

    def _prepare_prompt(self) -> str:
        return (
            "\n"
            "Clasifica el residuo en esta imagen en EXACTAMENTE una de estas categorías:\n\n"
            "- PLASTIC: Botellas plásticas, envases, bolsas\n"
            "- PAPER: Papel, cartón, periódicos\n"
            "- GLASS: Botellas de vidrio, frascos\n"
            "- METAL: Latas de aluminio o acero\n"
            "- ORGANIC: Restos de comida, material vegetal\n"
            "- OTHER: Si no encaja claramente en las anteriores\n\n"
            "Responde SOLO con el nombre de la categoría en MAYÚSCULAS.\n"
            "Si tienes dudas, usa OTHER."
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

    @property
    def model_name(self) -> str:
        return f"google/{self.model_name_internal}"

    @property
    def model_provider(self) -> str:
        return "google"

    @property
    def cost_per_request(self) -> float:
        return 0.0

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"GoogleClassifierAdapter(model='{self.model_name_internal}')"
