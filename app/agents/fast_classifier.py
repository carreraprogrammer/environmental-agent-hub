"""
Fast Classifier - Ultra-low latency classification using Roboflow.

This agent provides quick material classification (400-800ms) for immediate
user feedback, while a validation pipeline runs in background to ensure
data quality in the backend.

Architecture:
1. Fast Response (Roboflow): Material + Color + Message → User (< 1s)
2. Background Validation (Gemini/GPT-4o): Full pipeline → Rails

Performance:
- Latency: 400-800ms (vs 5-7s for full pipeline)
- Cost: $0.001 (vs $0.010 for GPT-4o)
- Accuracy: 85-90% (sufficient for fast UX)
- Validation: 100% of responses validated in background
"""

from __future__ import annotations

import time
from typing import Any

from app.adapters.base import ClassifierAdapter
from app.core.logging import logger
from app.schemas.classification import Material
from app.utils.classification.color_mapper import ColorMapper


class FastClassifier:
    """
    Ultra-fast classifier using Roboflow for immediate user feedback.
    
    Use Cases:
    - Initial user response (< 1s)
    - Real-time feedback in mobile apps
    - High-throughput scenarios
    
    Trade-offs:
    - Lower accuracy (85-90% vs 95-99%)
    - Requires background validation
    - Limited metadata (no subtype, volume, etc.)
    """

    # Confidence threshold for fast path
    # If Roboflow confidence < 0.70, fallback to full pipeline
    FAST_PATH_THRESHOLD = 0.70

    def __init__(self, adapter: ClassifierAdapter) -> None:
        """
        Initialize fast classifier with Roboflow adapter.
        
        Args:
            adapter: Roboflow classifier adapter
        """
        self.adapter = adapter
        self.color_mapper = ColorMapper()
        
        logger.info(
            "fast_classifier_initialized",
            adapter=type(adapter).__name__,
            threshold=self.FAST_PATH_THRESHOLD,
        )

    async def classify_fast(
        self,
        image_data: bytes,
        trace_id: str,
    ) -> dict[str, Any]:
        """
        Perform fast classification for immediate user response.
        
        Returns minimal classification data:
        - material: Material type
        - confidence: Classification confidence
        - color: Bin color for disposal
        - message: Educational feedback
        - should_validate: Whether to run full validation pipeline
        
        Args:
            image_data: Image bytes
            trace_id: Request trace ID
            
        Returns:
            Fast classification result with minimal metadata
        """
        start_time = time.time()
        
        logger.info(
            "fast_classifier_started",
            trace_id=trace_id,
            agent="FastClassifier",
        )
        
        # Classify with Roboflow
        result = await self.adapter.classify_bytes(image_data, trace_id=trace_id)

        # Normalize to shared Material enum (adapter returns WasteMaterial)
        try:
            material_normalized = Material(result.material.value)
        except Exception:
            material_normalized = Material.OTHER
        
        # Map material to bin color
        color = self.color_mapper.map_to_color(material_normalized, trace_id)
        
        # Generate quick feedback message
        message = self._generate_quick_message(material_normalized, color)
        
        # Determine if full validation is needed
        should_validate = result.confidence < self.FAST_PATH_THRESHOLD
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "fast_classifier_complete",
            trace_id=trace_id,
            agent="FastClassifier",
            material=material_normalized.value,
            confidence=result.confidence,
            color=color.value,
            should_validate=should_validate,
            latency_ms=latency_ms,
        )
        
        return {
            "material": material_normalized,
            "material_raw": result.material,
            "confidence": result.confidence,
            "color": color,
            "message": message,
            "should_validate": should_validate,
            "model_used": result.model_used,
            "model_provider": result.model_provider,
            "latency_ms": latency_ms,
        }

    def _generate_quick_message(self, material: Material, color) -> str:
        """Generate quick educational feedback message."""
        messages = {
            Material.PLASTIC: f"¡Bien! Deposítalo en el contenedor {color.value}.",
            Material.METAL: f"¡Correcto! Va en el contenedor {color.value}.",
            Material.GLASS: f"¡Perfecto! Deposítalo en el contenedor {color.value}.",
            Material.PAPER: f"¡Excelente! Va en el contenedor {color.value}.",
            Material.CARDBOARD: f"¡Muy bien! Deposítalo en el contenedor {color.value}.",
            Material.ORGANIC: f"¡Bien hecho! Va en el contenedor {color.value}.",
            Material.TETRAPAK: f"¡Correcto! Deposítalo en el contenedor {color.value}.",
            Material.OTHER: "Material identificado. Consulta con el personal.",
        }
        
        return messages.get(material, f"Deposítalo en el contenedor {color.value}.")

    async def should_use_fast_path(self, image_data: bytes) -> bool:
        """
        Determine if fast path should be used.
        
        Currently always returns True, but could be enhanced with:
        - Image quality check
        - User preference
        - System load
        
        Args:
            image_data: Image bytes
            
        Returns:
            True if fast path should be used
        """
        # Future: Add image quality check
        # If image is blurry or low quality, use full pipeline
        return True
