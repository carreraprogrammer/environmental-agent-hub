# Agent Hub – Architecture Specification V4.0 (Hybrid Edge + Backend)

## ⚠️ CONTEXTO - Tesis Ingeniería Ambiental

**Este documento especifica la arquitectura técnica del Agent Hub Python V4.**

**Propósito Principal (Tesis):**
Sistema de recolección de **datos ambientales** para investigación en gestión de residuos universitarios. La arquitectura V4 introduce edge computing para mejorar UX y reducir costos, manteniendo precisión en clasificación.

**Objetivos Ambientales:**
1. Recolectar datos: tipo, volumen, peso, ubicación, fecha de residuos
2. Educación: retroalimentación inmediata a usuarios
3. Análisis: datos estructurados para toma de decisiones ambientales
4. Impacto: cuantificar CO₂ evitado, recursos ahorrados

**Stack acordado:**
- Runtime: Python 3.11+
- Framework: FastAPI 0.104+
- Orquestación: Custom Pipeline (secuencial asíncrono)
- LLM: OpenAI GPT-4 Vision, Anthropic Claude Sonnet 4.5, Google Gemini 1.5 Pro
- Object Detection: Roboflow (edge + backend)
- Deploy: Railway/Render (Docker)
- Storage: S3 (upload asíncrono en background)

**Principios arquitectónicos V4:**
- ✅ Hybrid Architecture (Edge + Backend)
- ✅ Unified Classification (fusión de 3 agentes → 1)
- ✅ Per-Field Confidences (granular accuracy tracking)
- ✅ Partial Success Support (robustez ante incertidumbre)
- ✅ Defense in Depth (validación multi-capa)
- ✅ Cost Optimization (68% reducción vs V3)
- ✅ Latency Optimization (70% mejora vs V3)
- ✅ Adapter Pattern (modelos intercambiables)
- ✅ Stateless agents
- ✅ Structured logging (observabilidad)

---

## 1) Mejoras V3 → V4

### 1.1 Comparación Arquitectónica

**V3 Architecture (Backend-Only):**
```
Cliente → Backend Pipeline (10 agentes):
  1. Router
  2. PreValidator (GPT-4o-mini anti-troll) ← $0.010/request, 500ms
  3. Classifier (material base)
  4. SubtypeDetector (subtipo específico)
  5. VolumeEstimator (volumen + OCR)
  6. Mapper (color NTC 2184)
  7. WasteTypeMapper (waste_type_id)
  8. FeedbackCoach (mensaje educativo)
  9. Assembler (JSON final)
  10. BackendIntegration (Rails API)

Costo total: $0.031/request
Latencia: 3-5 segundos
Agentes: 10
```

**V4 Architecture (Hybrid Edge + Backend):**
```
Cliente (Edge):
  - Roboflow Object Detection (local) ← Implementación futura (EDV-XX)
  - Auto-captura + crop
  - UX inmediata (feedback visual)

Backend Pipeline (5-6 agentes):
  1. Router
  2. PreValidator (Roboflow API + validaciones técnicas) ← $0.001, <500ms
  3. MaterialClassifier (fusión de 3 agentes) ← $0.010, <1.5s
  4. WasteTypeMapper ← Pendiente
  5. Mapper ← Pendiente
  6. Assembler ← Pendiente

Costo total: $0.011/request (68% reducción)
Latencia: 0.8-1.2 segundos (70% mejora)
Agentes: 5-6
```

### 1.2 Decisiones Arquitectónicas Clave

#### 1.2.1 Edge Computing (Cliente)
**Decisión:** Mover object detection a cliente (Roboflow local)
**Rationale:**
- Reducción de latencia: 0ms para detección inicial
- UX mejorada: feedback visual inmediato
- Ahorro de costos: detección local gratuita
- Offline capability: funciona sin conectividad (cache)

**Implementación futura:** Ticket EDV-XX

#### 1.2.2 PreValidator Optimizado
**Decisión:** Cambiar de GPT-4o-mini a Roboflow Object Detection API
**Rationale:**
- **Costo:** GPT-4o-mini ($0.010) → Roboflow ($0.001) = 90% ahorro
- **Latencia:** 500ms → <200ms = 60% mejora
- **Precisión:** Similar para detección binaria (waste vs no-waste)
- **Especialización:** Roboflow entrenado específicamente en waste detection

**Implementación:** Two-layer validation
1. **Layer 1:** Technical validations (formato, tamaño, dimensiones)
2. **Layer 2:** Roboflow Object Detection (waste presence)

#### 1.2.3 MaterialClassifier Unificado
**Decisión:** Fusionar Classifier + SubtypeDetector + VolumeEstimator → MaterialClassifier
**Rationale:**
- **Latencia:** 3 llamadas LLM → 1 llamada = 66% reducción
- **Contexto compartido:** Modelo ve imagen UNA vez, infiere todo junto
- **Consistencia:** Decisiones coherentes (ej: si detecta PET → sabe volumen típico)
- **Costos:** 3× $0.010 → 1× $0.010 = 66% ahorro

**Trade-off aceptado:**
- Pérdida de granularidad en logs (antes: 3 agentes, ahora: 1)
- Mitigación: Per-field confidences permiten análisis granular

#### 1.2.4 Per-Field Confidences
**Decisión:** Cada campo retorna su propio confidence score
**Rationale:**
- **Partial Success:** Sistema puede continuar si volume confidence es bajo
- **Análisis Granular:** Permite identificar qué campos son más difíciles de predecir
- **Debugging:** Facilita identificar problemas de clasificación
- **Métricas:** Permite tracking de accuracy por campo

**Ejemplo:**
```json
{
  "material": {"type": "PLASTIC", "confidence": 0.95},
  "subtype": {"value": "PET", "confidence": 0.90},
  "volume": {"liters": null, "confidence": 0.40}  ← Partial success
}
```

#### 1.2.5 Defense in Depth
**Decisión:** Dos capas de validación (cliente + backend)
**Rationale:**
- **Capa 1 (Cliente):** Roboflow local → UX inmediata + offline
- **Capa 2 (Backend):** Roboflow API → Seguridad anti-troll

**Costo:** $0.001 adicional aceptable para seguridad

---

## 2) Arquitectura de Alto Nivel V4

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENTE (Edge Computing)                          │
│                         [Implementación Futura EDV-XX]                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │        Roboflow Object Detection (Local - TensorFlow.js)         │    │
│  │  - Modelo: waste-hsysm (6 clases)                                │    │
│  │  - Latencia: <100ms                                               │    │
│  │  - Costo: $0 (gratis)                                             │    │
│  │  - Output: Bounding boxes + clases detectadas                    │    │
│  └─────────────────────────┬─────────────────────────────────────────┘    │
│                             │                                               │
│  ┌─────────────────────────▼─────────────────────────────────────────┐    │
│  │                  UX Layer (Immediate Feedback)                    │    │
│  │  - Highlight bounding boxes en pantalla                           │    │
│  │  - Auto-captura cuando detecta waste                              │    │
│  │  - Auto-crop a waste object                                       │    │
│  │  - Loading states durante backend processing                     │    │
│  └─────────────────────────┬─────────────────────────────────────────┘    │
│                             │                                               │
│                             │ POST /classify (image bytes + metadata)      │
│                             ▼                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (Agent Hub V4 - FastAPI)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │                    API Layer (FastAPI)                           │    │
│  │  - POST /classify (multipart/form-data + JSON)                   │    │
│  │  - GET /health                                                    │    │
│  │  - GET /models (list available)                                   │    │
│  │  - Bytes processing (preferido) + URL fallback                   │    │
│  └─────────────────────────┬─────────────────────────────────────────┘    │
│                             │                                               │
│  ┌─────────────────────────▼─────────────────────────────────────────┐    │
│  │              Pipeline Orchestrator (5-6 Agentes)                  │    │
│  │  - Coordina secuencia de agentes                                 │    │
│  │  - Maneja errores y timeouts por agente                          │    │
│  │  - Propaga trace_id                                               │    │
│  │  - Optimizado para <1.2s latencia                                │    │
│  └─────────────────────────┬─────────────────────────────────────────┘    │
│                             │                                               │
│  ┌─────────────────────────▼─────────────────────────────────────────┐    │
│  │                  Agents Layer V4 (Simplified)                     │    │
│  │                                                                   │    │
│  │  [1. Router] → Valida schema + procesa input                     │    │
│  │      ↓                                                            │    │
│  │  [2. PreValidator] → Two-layer validation                        │    │
│  │      - Layer 1: Technical (formato, tamaño, dimensiones)         │    │
│  │      - Layer 2: Roboflow Object Detection API                    │    │
│  │      - Cost: $0.001, Latency: <500ms                             │    │
│  │      ↓                                                            │    │
│  │  [3. MaterialClassifier] ← Factory → Adapter                     │    │
│  │      - Unified classification (material + subtype + volume)      │    │
│  │      - Per-field confidences                                     │    │
│  │      - Partial success support                                   │    │
│  │      - Cost: $0.010, Latency: <1500ms                            │    │
│  │      ↓                                                            │    │
│  │  [4. WasteTypeMapper] → Material+volumen → waste_type_code       │    │
│  │      [PENDIENTE - Ticket subsecuente]                            │    │
│  │      ↓                                                            │    │
│  │  [5. Mapper] → Material → Color (NTC 2184)                       │    │
│  │      [PENDIENTE - Ticket subsecuente]                            │    │
│  │      ↓                                                            │    │
│  │  [6. Assembler] → Construye response completo                    │    │
│  │      [PENDIENTE - Ticket subsecuente]                            │    │
│  │                                                                   │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │            Adapters V4 (Intercambiables + classify_material)     │    │
│  │                                                                   │    │
│  │  ┌─────────────────────────────────────────────────────────────┐ │    │
│  │  │            ClassifierAdapter (ABC)                         │ │    │
│  │  │  - classify(image_url) → ClassificationResult [V3 compat]│ │    │
│  │  │  - classify_material(image_bytes) → Dict [V4 unified]    │ │    │
│  │  │  - model_name, cost_per_request (properties)             │ │    │
│  │  └───────────────────┬───────────────────────────────────────┘ │    │
│  │                      │                                         │    │
│  │  ┌─────────────────┬─┴──────────────┬──────────────────────┐ │    │
│  │  │                 │                │                      │ │    │
│  │  ▼                 ▼                ▼                      ▼ │    │
│  │  OpenAI           Anthropic        Google             Roboflow│    │
│  │  Adapter          Adapter         Adapter             Adapter │    │
│  │  (GPT-4o)         (Claude 4.5)    (Gemini 1.5 Pro)   (Object │    │
│  │  ✅ V4            ✅ V4           ✅ V4              Detection)│    │
│  │  $0.005-0.010     $0.003          $0.000             $0.001   │    │
│  │                                                               │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3) Agentes Detallados V4

### 3.1 PreValidator (Two-Layer Validation)

**Responsabilidad:** Filtrar imágenes no válidas antes de clasificación costosa

**Layer 1: Technical Validations**
```python
- Image not empty (len > 0)
- Format valid (JPEG, PNG, WEBP)
- Size < 10MB
- Dimensions >= 224x224px
```

**Layer 2: Roboflow Object Detection**
```python
- Model: waste-hsysm (6 clases: plastic, paper, cardboard, metal, glass, biodegradable)
- Confidence threshold: 0.4 (permissive)
- Overlap threshold: 0.5
- Timeout: 3s con fallback

if len(detections) == 0:
    return REJECT "NO_WASTE_DETECTED"
else:
    return ACCEPT "WASTE_DETECTED" + metadata
```

**Output Schema:**
```python
@dataclass
class ValidationResult:
    is_valid: bool
    reason: ValidationReason  # WASTE_DETECTED, NO_WASTE_DETECTED, etc.
    metadata: dict  # {detections: [...], classes: [...], confidences: [...]}
    cost: float = 0.001  # Roboflow API cost
    fallback_used: bool = False  # Si Roboflow falló
```

**Fallback Strategy:**
```python
try:
    roboflow_result = await roboflow_api(image, timeout=3s)
except (Timeout, APIError):
    # Permitir continuar a MaterialClassifier
    return ValidationResult(
        is_valid=True,
        reason=WASTE_DETECTED,
        fallback_used=True,
        cost=0.0
    )
```

**Métricas:**
- `prevalidator_layer1_rejects`: Counter (formato, tamaño, dimensiones)
- `prevalidator_layer2_rejects`: Counter (no waste detected)
- `prevalidator_fallback_activations`: Counter (Roboflow errors)
- `prevalidator_latency_ms`: Histogram

---

### 3.2 MaterialClassifier (Unified Classification)

**Responsabilidad:** Clasificación completa en UNA llamada LLM

**Input:** Image bytes (JPEG, PNG, WEBP)

**Output Fields (con confidences):**
1. **Material Base:**
   - PLASTIC, PAPER, CARDBOARD, GLASS, METAL, ORGANIC, TETRAPAK, OTHER
   - Confidence: 0.0-1.0
   - Threshold mínimo: 0.7 (rechaza si < 0.7)

2. **Subtype:**
   - Plastic: PET (#1), HDPE (#2), PVC (#3), LDPE (#4), PP (#5), PS (#6), OTHER (#7)
   - Paper: Newspaper, Magazine, Office Paper, Cardboard Box
   - Metal: Aluminum Can, Steel Can
   - Glass: Clear Glass, Green Glass, Brown Glass
   - Confidence: 0.0-1.0
   - Threshold mínimo: 0.6 (null si < 0.6)

3. **Physical Condition:**
   - CLEAN, CONTAMINATED, PARTIALLY_FULL, DAMAGED, CRUSHED
   - Confidence: 0.0-1.0

4. **Volume:**
   - Liters: float (from OCR label read or estimation)
   - Source: LABEL_READ | ESTIMATED
   - Confidence: 0.0-1.0
   - Threshold mínimo: 0.5 (null si < 0.5)

5. **Recyclability:**
   - RECYCLABLE, RECYCLABLE_AFTER_CLEANING, NON_RECYCLABLE, COMPOSTABLE, REQUIRES_SPECIAL_PROCESSING
   - Confidence: 0.0-1.0

**Output Schema:**
```python
@dataclass
class MaterialClassificationResult:
    material: MaterialField(type: Material, confidence: float)
    subtype: SubtypeField(value: str | None, recycling_code: str | None, confidence: float)
    condition: ConditionField(value: PhysicalCondition, confidence: float)
    volume: VolumeField(liters: float | None, source: VolumeSource, confidence: float)
    recyclability: RecyclabilityField(value: Recyclability, confidence: float)
    reasoning: str  # Explicación del modelo
    timestamp: datetime
    cost: float  # Costo de la llamada LLM
    model_used: str  # "openai/gpt-4o", "anthropic/claude-sonnet-4-5"
    model_provider: str  # "openai", "anthropic", "google"
    partial_success: bool  # True si algún campo tiene baja confidence
    metadata: dict  # Additional data
```

**Partial Success Logic:**
```python
if material.confidence < 0.7:
    raise ValueError("Material confidence too low")

if subtype.confidence < 0.6:
    subtype.value = None  # Continue con material genérico

if volume.confidence < 0.5:
    volume.liters = None  # Continue sin volumen

partial_success = (subtype is None) or (volume is None)
```

**Prompt Engineering:**
```python
def build_classification_prompt() -> str:
    """
    Prompt optimizado para clasificación unificada.

    Features:
    - Instrucciones claras para cada campo
    - Ejemplos few-shot (PET bottle, aluminum can, imagen borrosa)
    - JSON schema explícito
    - OCR instructions para volume reading
    - Recycling codes (#1-7)
    - Confidence scoring guidance
    """
    return """
    Analiza esta imagen de residuo y realiza una clasificación COMPLETA...
    [Ver app/agents/material_classifier.py para prompt completo]
    """
```

**Adapter Support:**
- OpenAI GPT-4 Vision (gpt-4o, gpt-4-turbo): ✅ Implementado
- Anthropic Claude Sonnet 4.5 (claude-3-5-sonnet-20241022): ✅ Implementado
- Google Gemini 1.5 Pro (gemini-1.5-pro-vision): ✅ Implementado

**Métricas:**
- `material_classifier_latency_ms`: Histogram
- `material_classifier_cost_usd`: Counter
- `material_classifier_partial_success_rate`: Gauge
- `material_confidence_distribution`: Histogram (por material)
- `subtype_confidence_distribution`: Histogram (por subtype)
- `volume_confidence_distribution`: Histogram
- `model_used`: Label (openai, anthropic, google)

---

### 3.3 WasteTypeMapper (Pendiente - Ticket subsecuente)

**Responsabilidad:** Mapear (material + volume) → waste_type_id del backend

**Implementación futura:** EDV-54

---

### 3.4 Mapper (Pendiente - Ticket subsecuente)

**Responsabilidad:** Mapear material → color NTC 2184 + mensaje UI

**Implementación futura:** EDV-55

---

### 3.5 Assembler (Pendiente - Ticket subsecuente)

**Responsabilidad:** Construir JSON final para respuesta

**Implementación futura:** EDV-57

---

## 4) Contratos JSON entre Agentes

### 4.1 PreValidator → MaterialClassifier

**Input to MaterialClassifier:**
```json
{
  "image_data": "<bytes>",
  "trace_id": "req-abc123",
  "validation_metadata": {
    "roboflow_classes": ["plastic", "paper"],
    "roboflow_confidences": [0.85, 0.72],
    "num_detections": 2
  }
}
```

**MaterialClassifier ignora validation_metadata** (solo informativo en logs)

### 4.2 MaterialClassifier → WasteTypeMapper (Futuro)

**Output from MaterialClassifier:**
```json
{
  "material": {
    "material_type": "PLASTIC",
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
    "source": "LABEL_READ",
    "confidence": 0.90
  },
  "recyclability": {
    "value": "RECYCLABLE",
    "confidence": 0.95
  },
  "reasoning": "Botella PET de 500ml, limpia, código #1 visible",
  "timestamp": "2025-11-14T10:30:00Z",
  "cost": 0.010,
  "model_used": "openai/gpt-4o",
  "model_provider": "openai",
  "partial_success": false
}
```

**Input to WasteTypeMapper:**
```json
{
  "material": "PLASTIC",
  "subtype": "PET",
  "volume_liters": 0.5
}
```

**Output from WasteTypeMapper:**
```json
{
  "waste_type_id": "plastic_pet_bottle_small",  // Backend ID
  "waste_type_name": "Botella PET pequeña (< 1L)",
  "category": "Envases plásticos"
}
```

---

## 5) Métricas de Observabilidad

### 5.1 Métricas por Agente

**PreValidator:**
```python
prevalidator_layer1_rejects_total{reason="invalid_format"} Counter
prevalidator_layer1_rejects_total{reason="invalid_size"} Counter
prevalidator_layer1_rejects_total{reason="invalid_dimensions"} Counter
prevalidator_layer1_rejects_total{reason="empty_image"} Counter
prevalidator_layer2_rejects_total{reason="no_waste_detected"} Counter
prevalidator_fallback_activations_total{reason="timeout"} Counter
prevalidator_fallback_activations_total{reason="api_error"} Counter
prevalidator_latency_ms Histogram
```

**MaterialClassifier:**
```python
material_classifier_latency_ms Histogram
material_classifier_cost_usd Counter
material_classifier_partial_success_rate Gauge
material_confidence{material="PLASTIC"} Histogram
material_confidence{material="PAPER"} Histogram
subtype_confidence{subtype="PET"} Histogram
volume_confidence{source="LABEL_READ"} Histogram
volume_confidence{source="ESTIMATED"} Histogram
model_used{provider="openai",model="gpt-4o"} Counter
model_used{provider="anthropic",model="claude-sonnet-4-5"} Counter
```

### 5.2 Dashboards Clave

**Performance Dashboard:**
- p50, p95, p99 latency por agente
- Total pipeline latency
- Throughput (requests/second)

**Cost Dashboard:**
- Cost per request (PreValidator: $0.001, MaterialClassifier: $0.010)
- Daily cost projection
- Cost by model provider

**Accuracy Dashboard:**
- Material confidence distribution
- Subtype confidence distribution
- Volume confidence distribution
- Partial success rate

---

## 6) Performance Targets V4

| Métrica | V3 Target | V4 Target | Mejora |
|---------|-----------|-----------|--------|
| **Total Latency (p95)** | 5000ms | 1500ms | 70% ↓ |
| **PreValidator Latency** | 500ms | 300ms | 40% ↓ |
| **MaterialClassifier Latency** | N/A (3 agentes) | 1200ms | N/A |
| **Total Cost** | $0.031 | $0.011 | 65% ↓ |
| **PreValidator Cost** | $0.010 | $0.001 | 90% ↓ |
| **Classification Cost** | $0.030 | $0.010 | 67% ↓ |
| **Agentes Backend** | 10 | 5-6 | 40-50% ↓ |
| **Accuracy (Material)** | 85% | 85% | = |
| **Accuracy (Subtype)** | N/A | 80% | New |
| **Accuracy (Volume)** | N/A | 70% | New |

---

## 7) Testing Strategy V4

### 7.1 Unit Tests

**PreValidator:**
- ✅ Layer 1 validations (formato, tamaño, dimensiones)
- ✅ Layer 2 Roboflow integration (mock responses)
- ✅ Fallback logic (timeout, API errors)
- ✅ Schema validation

**MaterialClassifier:**
- ✅ Unified classification (todos los campos)
- ✅ Per-field confidence parsing
- ✅ Partial success scenarios
- ✅ Low confidence rejection (material < 0.7)
- ✅ Prompt structure validation

**Adapters:**
- ✅ OpenAI adapter (classify_material)
- ✅ Anthropic adapter (classify_material)
- ✅ Google adapter (classify_material)
- ✅ JSON parsing robustness
- ✅ Error handling (API errors, timeouts)

### 7.2 Integration Tests

**Pipeline E2E:**
- ✅ PreValidator → MaterialClassifier (happy path)
- ✅ PreValidator rejection handling
- ✅ MaterialClassifier partial success
- ✅ Real API calls (con test API keys)

### 7.3 Performance Tests

**Latency:**
- ✅ PreValidator < 500ms (p95)
- ✅ MaterialClassifier < 1500ms (p95)
- ✅ Total pipeline < 2000ms (p95)

**Load Testing:**
- ✅ 10 requests/second sustained
- ✅ 50 requests/second burst

---

## 8) Migration Path V3 → V4

Ver `/docs/MIGRATION_V3_TO_V4.md` para guía detallada.

**Breaking Changes:**
1. PreValidator: Schema cambió (ValidationResult V4 vs V3)
2. Classifier → MaterialClassifier: API completamente nueva
3. Adapters: Nuevo método `classify_material(image_bytes)` requerido

**Backward Compatibility:**
- ✅ V3 `classify(image_url)` method preserved en adapters
- ✅ V3 endpoints siguen funcionando (deprecated)

**Recommended Migration:**
1. Implementar MaterialClassifier primero
2. Migrar PreValidator segundo
3. Actualizar downstream agents (WasteTypeMapper, Mapper, Assembler)
4. Deprecar V3 endpoints después de 30 días

---

## 9) Deployment V4

**Railway/Render Config:**
```yaml
services:
  agent-hub-v4:
    build:
      context: .
      dockerfile: Dockerfile
    env:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - ROBOFLOW_API_KEY=${ROBOFLOW_API_KEY}
      - ROBOFLOW_MODEL_ID=workspace/waste-hsysm/6
    resources:
      cpu: 1
      memory: 512MB
    healthcheck:
      path: /health
      interval: 30s
```

---

## 10) Future Work

**Edge Computing (EDV-XX):**
- Implementar Roboflow local en cliente (TensorFlow.js)
- Auto-captura + crop
- Offline mode

**Downstream Agents:**
- WasteTypeMapper (EDV-54)
- Mapper (EDV-55)
- Assembler (EDV-57)

**Optimizations:**
- Cache de clasificaciones idénticas
- Batch processing para múltiples imágenes
- Model fine-tuning con datos reales

---

## APÉNDICE A: Decisiones de Diseño Detalladas

Ver `/DECISIONES_ARQUITECTURA_V4.md` en outputs/ para análisis completo.

---

**Versión:** 4.0
**Fecha:** 2025-11-14
**Autor:** Agent Hub Team
**Status:** IMPLEMENTED (Core pipeline), PENDING (Downstream agents)
