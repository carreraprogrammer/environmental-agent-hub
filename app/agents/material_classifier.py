"""
MaterialClassifier Agent V4 - Unified material classification.

This agent merges the functionality of three V3 agents into one:
- Classifier: Material base type (PLASTIC, PAPER, GLASS, etc.)
- SubtypeDetector: Specific subtype (PET, HDPE, recycling codes, etc.)
- VolumeEstimator: Volume estimation with OCR label reading

Performs complete classification in ONE LLM call with per-field confidences
to support partial success scenarios.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.adapters.base import ClassifierAdapter
from app.core.logging import logger
from app.schemas.classification import (
    ConditionField,
    Material,
    MaterialClassificationResult,
    MaterialField,
    PhysicalCondition,
    Recyclability,
    RecyclabilityField,
    SubtypeField,
    VolumeField,
    VolumeSource,
)


class MaterialClassifier:
    """
    MaterialClassifier Agent V4 - Unified classification in one LLM call.

    Classifies:
    - Material base type (PLASTIC, PAPER, GLASS, METAL, ORGANIC, CARDBOARD, TETRAPAK)
    - Subtype (PET, HDPE, recycling code, paper type, etc.)
    - Physical condition (CLEAN, CONTAMINATED, DAMAGED, etc.)
    - Volume (in liters, from label OCR or estimation)
    - Recyclability (RECYCLABLE, NON_RECYCLABLE, etc.)

    Each field returns its own confidence score for partial success support.

    Cost: ~$0.010 per request (GPT-4 Vision)
    Latency: <1500ms p95

    Example:
        >>> classifier = MaterialClassifier(adapter)
        >>> result = await classifier.classify(image_bytes, "trace-123")
        >>> print(f"Material: {result.material.material_type}")
        >>> print(f"Confidence: {result.material.confidence}")
    """

    # Confidence thresholds for partial success
    MIN_MATERIAL_CONFIDENCE = 0.7  # Material must be high confidence
    MIN_SUBTYPE_CONFIDENCE = 0.6  # Subtype can be lower
    MIN_VOLUME_CONFIDENCE = 0.5  # Volume can be even lower

    def __init__(self, adapter: ClassifierAdapter):
        """
        Initialize MaterialClassifier with a vision model adapter.

        Args:
            adapter: Vision model adapter (OpenAI, Anthropic, or Google)
        """
        self.adapter = adapter

        logger.info(
            "material_classifier_initialized",
            adapter=type(adapter).__name__,
            model_name=adapter.model_name,
        )

    async def classify(
        self, image_data: bytes, trace_id: str
    ) -> MaterialClassificationResult:
        """
        Perform complete material classification in one LLM call.

        Args:
            image_data: Image bytes (JPEG, PNG, WEBP)
            trace_id: Request trace ID for logging

        Returns:
            MaterialClassificationResult with per-field confidences

        Raises:
            ValueError: If classification fails or material confidence too low
        """
        logger.info(
            "material_classifier_started",
            trace_id=trace_id,
            agent="MaterialClassifier",
            adapter=type(self.adapter).__name__,
        )

        start_time = datetime.now()

        # Call adapter with unified classification prompt
        result_dict = await self.adapter.classify_material(
            image_data=image_data,
            trace_id=trace_id,
        )

        # Parse response into MaterialClassificationResult
        classification_result = self._parse_result(result_dict, trace_id)

        # Calculate latency
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Log structured classification data
        logger.info(
            "material_classifier_complete",
            trace_id=trace_id,
            agent="MaterialClassifier",
            material=classification_result.material.material_type.value,
            material_confidence=classification_result.material.confidence,
            subtype=classification_result.subtype.value,
            subtype_confidence=classification_result.subtype.confidence,
            volume_liters=classification_result.volume.liters,
            volume_confidence=classification_result.volume.confidence,
            condition=classification_result.condition.value.value,
            recyclability=classification_result.recyclability.value.value,
            partial_success=classification_result.partial_success,
            latency_ms=round(latency_ms, 2),
            cost_usd=classification_result.cost,
            model_used=classification_result.model_used,
        )

        return classification_result

    def _parse_result(
        self, result_dict: dict[str, Any], trace_id: str
    ) -> MaterialClassificationResult:
        """
        Parse adapter response into MaterialClassificationResult.

        Handles partial responses and validates confidence thresholds.

        Args:
            result_dict: Response dict from adapter
            trace_id: Request trace ID

        Returns:
            MaterialClassificationResult

        Raises:
            ValueError: If material confidence is too low
        """
        # Extract material field
        material_data = result_dict.get("material", {})
        material_type_str = material_data.get("type", "OTHER")
        material_confidence = float(material_data.get("confidence", 0.0))

        try:
            material_type = Material(material_type_str.upper())
        except ValueError:
            logger.warning(
                "material_classifier_invalid_material",
                trace_id=trace_id,
                material_value=material_type_str,
            )
            material_type = Material.OTHER
            material_confidence = 0.5

        # Validate material confidence
        if material_confidence < self.MIN_MATERIAL_CONFIDENCE:
            raise ValueError(
                f"Material confidence too low: {material_confidence} < {self.MIN_MATERIAL_CONFIDENCE}"
            )

        material_field = MaterialField(
            material_type=material_type,
            confidence=material_confidence,
        )

        # Extract subtype field (can be partial success)
        subtype_data = result_dict.get("subtype", {})
        subtype_value = subtype_data.get("value")
        subtype_code = subtype_data.get("recycling_code")
        subtype_confidence = float(subtype_data.get("confidence", 0.0))

        # Partial success: set subtype to None if confidence too low
        if subtype_confidence < self.MIN_SUBTYPE_CONFIDENCE:
            logger.info(
                "material_classifier_low_subtype_confidence",
                trace_id=trace_id,
                subtype_confidence=subtype_confidence,
                threshold=self.MIN_SUBTYPE_CONFIDENCE,
            )
            subtype_value = None
            subtype_code = None

        subtype_field = SubtypeField(
            value=subtype_value,
            recycling_code=subtype_code,
            confidence=subtype_confidence,
        )

        # Extract condition field
        condition_data = result_dict.get("condition", {})
        condition_str = condition_data.get("value", "CLEAN")
        condition_confidence = float(condition_data.get("confidence", 0.7))

        try:
            condition_value = PhysicalCondition(condition_str.upper())
        except ValueError:
            logger.warning(
                "material_classifier_invalid_condition",
                trace_id=trace_id,
                condition_value=condition_str,
            )
            condition_value = PhysicalCondition.CLEAN
            condition_confidence = 0.5

        condition_field = ConditionField(
            value=condition_value,
            confidence=condition_confidence,
        )

        # Extract volume field (can be partial success)
        volume_data = result_dict.get("volume", {})
        volume_liters = volume_data.get("liters")
        volume_source_str = volume_data.get("source", "ESTIMATED")
        volume_confidence = float(volume_data.get("confidence", 0.0))

        try:
            volume_source = VolumeSource(volume_source_str.upper())
        except ValueError:
            volume_source = VolumeSource.ESTIMATED

        # Partial success: set volume to None if confidence too low
        if volume_confidence < self.MIN_VOLUME_CONFIDENCE:
            logger.info(
                "material_classifier_low_volume_confidence",
                trace_id=trace_id,
                volume_confidence=volume_confidence,
                threshold=self.MIN_VOLUME_CONFIDENCE,
            )
            volume_liters = None

        volume_field = VolumeField(
            liters=volume_liters,
            source=volume_source,
            confidence=volume_confidence,
        )

        # Extract recyclability field
        recyclability_data = result_dict.get("recyclability", {})
        recyclability_str = recyclability_data.get("value", "RECYCLABLE")
        recyclability_confidence = float(recyclability_data.get("confidence", 0.7))

        try:
            recyclability_value = Recyclability(recyclability_str.upper())
        except ValueError:
            logger.warning(
                "material_classifier_invalid_recyclability",
                trace_id=trace_id,
                recyclability_value=recyclability_str,
            )
            recyclability_value = Recyclability.RECYCLABLE
            recyclability_confidence = 0.5

        recyclability_field = RecyclabilityField(
            value=recyclability_value,
            confidence=recyclability_confidence,
        )

        # Extract metadata
        reasoning = result_dict.get("reasoning", "")
        cost = float(result_dict.get("cost", 0.010))
        model_used = result_dict.get("model_used", "unknown")
        model_provider = result_dict.get("model_provider", "unknown")

        # Determine if this is partial success
        partial_success = (
            subtype_confidence < self.MIN_SUBTYPE_CONFIDENCE
            or volume_confidence < self.MIN_VOLUME_CONFIDENCE
        )

        return MaterialClassificationResult(
            material=material_field,
            subtype=subtype_field,
            condition=condition_field,
            volume=volume_field,
            recyclability=recyclability_field,
            reasoning=reasoning,
            timestamp=datetime.now(),
            cost=cost,
            model_used=model_used,
            model_provider=model_provider,
            partial_success=partial_success,
            metadata=result_dict.get("metadata", {}),
        )


def build_classification_prompt() -> str:
    """
    Build the unified classification prompt for MaterialClassifier.

    This prompt instructs the vision model to perform complete classification
    with per-field confidence scores.

    Returns:
        Prompt string for the vision model
    """
    return """Analiza esta imagen de residuo y realiza una clasificación COMPLETA en español.

Debes identificar:

1. **Material Base** (OBLIGATORIO):
   - PLASTIC: Botellas plásticas, envases, bolsas, empaques
   - PAPER: Papel, periódicos, revistas
   - CARDBOARD: Cartón, cajas
   - GLASS: Botellas de vidrio, frascos
   - METAL: Latas de aluminio, acero, envases metálicos
   - ORGANIC: Restos de comida, material vegetal
   - TETRAPAK: Envases Tetra Pak (cartón + plástico + aluminio)
   - OTHER: Si no encaja en las anteriores

2. **Subtipo Específico** (OPCIONAL):
   Si es plástico:
   - PET (#1): Botellas de agua, refrescos
   - HDPE (#2): Botellas de leche, detergentes
   - PVC (#3): Tuberías, empaques
   - LDPE (#4): Bolsas plásticas, film
   - PP (#5): Tapas, contenedores
   - PS (#6): Poliestireno, vasos desechables
   - OTHER (#7): Otros plásticos

   Si es papel/cartón:
   - Newspaper, Magazine, Office Paper, Cardboard Box, etc.

   Si es metal:
   - Aluminum Can, Steel Can, etc.

   Si es vidrio:
   - Clear Glass, Green Glass, Brown Glass

3. **Condición Física** (OBLIGATORIO):
   - CLEAN: Limpio, vacío, sin residuos
   - CONTAMINATED: Con residuos de comida, líquidos
   - PARTIALLY_FULL: Parcialmente lleno
   - DAMAGED: Roto, aplastado
   - CRUSHED: Compactado

4. **Volumen** (OPCIONAL):
   - Intenta LEER la etiqueta (OCR) para obtener el volumen exacto
   - Si no hay etiqueta visible, ESTIMA el volumen en litros
   - Ejemplos: Botella PET típica = 0.5-2.0 L, Lata = 0.33-0.5 L

5. **Reciclabilidad** (OBLIGATORIO):
   - RECYCLABLE: Se puede reciclar directamente
   - RECYCLABLE_AFTER_CLEANING: Requiere limpieza primero
   - NON_RECYCLABLE: No reciclable
   - COMPOSTABLE: Compostable (orgánicos)
   - REQUIRES_SPECIAL_PROCESSING: Requiere proceso especial (ej: Tetrapak)

INSTRUCCIONES CRÍTICAS:
- Responde ÚNICAMENTE en formato JSON
- Incluye un campo "confidence" (0.0-1.0) para CADA clasificación
- Si no estás seguro de un campo, usa confidence bajo y valor null
- Incluye "reasoning" explicando tu clasificación

FORMATO DE RESPUESTA:
```json
{
  "material": {
    "type": "PLASTIC",
    "confidence": 0.95
  },
  "subtype": {
    "value": "PET",
    "recycling_code": "#1",
    "confidence": 0.90
  },
  "condition": {
    "value": "CLEAN",
    "confidence": 0.85
  },
  "volume": {
    "liters": 0.5,
    "source": "LABEL_READ",  // o "ESTIMATED"
    "confidence": 0.80
  },
  "recyclability": {
    "value": "RECYCLABLE",
    "confidence": 0.90
  },
  "reasoning": "Es una botella PET de 500ml, limpia, con código #1 visible en la base. Volumen leído de la etiqueta frontal."
}
```

EJEMPLOS:

**Ejemplo 1: Botella PET clara**
```json
{
  "material": {"type": "PLASTIC", "confidence": 0.95},
  "subtype": {"value": "PET", "recycling_code": "#1", "confidence": 0.90},
  "condition": {"value": "CLEAN", "confidence": 0.85},
  "volume": {"liters": 0.5, "source": "LABEL_READ", "confidence": 0.90},
  "recyclability": {"value": "RECYCLABLE", "confidence": 0.95},
  "reasoning": "Botella PET transparente de 500ml, vacía y limpia, código #1 visible."
}
```

**Ejemplo 2: Lata de aluminio contaminada**
```json
{
  "material": {"type": "METAL", "confidence": 0.90},
  "subtype": {"value": "Aluminum Can", "recycling_code": null, "confidence": 0.85},
  "condition": {"value": "CONTAMINATED", "confidence": 0.80},
  "volume": {"liters": 0.355, "source": "ESTIMATED", "confidence": 0.75},
  "recyclability": {"value": "RECYCLABLE_AFTER_CLEANING", "confidence": 0.85},
  "reasoning": "Lata de aluminio de ~355ml con residuos líquidos. Requiere enjuague antes de reciclar."
}
```

**Ejemplo 3: Imagen borrosa (partial success)**
```json
{
  "material": {"type": "PLASTIC", "confidence": 0.70},
  "subtype": {"value": null, "recycling_code": null, "confidence": 0.30},
  "condition": {"value": "CLEAN", "confidence": 0.50},
  "volume": {"liters": null, "source": "ESTIMATED", "confidence": 0.40},
  "recyclability": {"value": "RECYCLABLE", "confidence": 0.60},
  "reasoning": "Imagen borrosa, parece plástico pero no puedo determinar subtipo ni volumen con certeza."
}
```

IMPORTANTE:
- Sé conservador con los confidence scores
- Si no puedes leer una etiqueta, usa source: "ESTIMATED" y baja el confidence
- Si ves múltiples objetos, clasifica el más prominente
- Siempre incluye "reasoning" con tu justificación

Responde SOLO con el JSON, sin markdown, sin explicaciones adicionales.
"""
