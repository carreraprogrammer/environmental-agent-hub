# Agent Hub – Architecture Specification V4.0 (Hybrid Edge + Backend)

## 🔄 ACTUALIZACIONES IMPORTANTES

### v4.2 - Fast Path + Consensus Architecture (Dic 2025)

**Fast Path Architecture implementada:**
- ✅ **FastClassifier (Roboflow)** - Clasificación ultra-rápida <1s
- ✅ **ValidationPipeline** - Gemini valida en background sin bloquear respuesta
- ✅ **ENABLE_FAST_PATH=true** - Feature flag activo en producción
- ✅ **ConsensusClassificationAgent** - Ensemble multi-modelo cuando Fast Path no aplica

**Resultados de validación (scripts/validate_fast_vs_full_pipeline.py):**
| Métrica | Resultado |
|---------|-----------|
| Agreement Rate | 33.3% (2/6) |
| PLASTIC Accuracy | 100% (2/2) |
| NO_WASTE Accuracy | 0% (0/4) |
| Roboflow Avg Confidence | 0.865 |
| Gemini Avg Confidence | 0.983 |

**Resultados de benchmark (scripts/benchmark_fast_path.py):**
| Entorno | Latencia Cold | Latencia Warmed | Target |
|---------|--------------|-----------------|--------|
| Local | N/A | 570ms | ✅ <1s |
| Docker | 2936ms | 1801ms | ⚠️ ~2x target |

**Archivos implementados:**
- `app/agents/fast_classifier.py` - FastClassifier con Roboflow
- `app/orchestrator/fast_pipeline.py` - ValidationPipeline background
- `app/agents/consensus_classifier.py` - Ensemble multi-modelo
- `scripts/benchmark_fast_path.py` - Benchmark de performance
- `scripts/validate_fast_vs_full_pipeline.py` - Validación Roboflow vs Gemini

### v4.1 - PreValidator movido a cliente (Nov 2025 - EDV-58)

**PreValidator eliminado del backend:**
- ✅ **Validación movida a client-side** - backend recibe solo imágenes válidas
- ✅ **5 processing agents + 1 Assembler** (era 7) - simplificación significativa
- ✅ **$0.010/request** (era $0.011) - 9% más barato
- ✅ **~1000ms latency** (era ~1200ms) - 17% más rápido
- ✅ **Serverless-ready** - sin cold start de Roboflow (era 37s)

**Razón de eliminación:**
- Solo ahorraba $9/mes con <1% troll rate
- Agregaba 200ms latency
- Creaba false negatives
- Industria estándar: validación client-side (OpenAI, Anthropic, Google)

Ver: `/validations/EDV-58/PREVALIDATOR_ANALYSIS.md`

---

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

**V4.1 Architecture (Client-Side Validation):**
```
Cliente:
  - Validación de imagen (formato, tamaño)
  - Roboflow Object Detection (opcional, futuro)
  - Auto-captura + crop
  - UX inmediata (feedback visual)

Backend Pipeline (6 agentes):
  1. Router
  2. MaterialClassifier (clasificación unificada) ← $0.010, <1000ms
  3. VolumeEstimator
  4. Mapper
  5. WasteTypeMapper
  6. FeedbackCoach
  7. Assembler (empaqueta response, no en agents_executed)

Costo total: $0.010/request (68% reducción vs V3, 9% vs V4.0)
Latencia: ~1000ms (70% mejora vs V3, 17% vs V4.0)
Agentes backend: 6 (5 processing + 1 assembler)
```

**V4.2 Architecture (Fast Path + Consensus):**
```
┌─────────────────────────────────────────────────────────────┐
│                    FAST PATH FLOW                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Request → FastClassifier (Roboflow) → Response <1s         │
│                    ↓                                         │
│            Background Async:                                 │
│            ValidationPipeline (Gemini) → Sync to Backend     │
│                                                              │
│  Latency: 570ms (local), 1.8s (Docker)                      │
│  Target: <1s first response                                  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                   CONSENSUS FLOW (fallback)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Request → ConsensusClassificationAgent                      │
│                ↓                                             │
│         ┌─────────────────┐                                  │
│         │  GPT-4o (primary)                                  │
│         │  confidence ≥0.70 → fast path                     │
│         │  confidence <0.70 → consult Gemini                │
│         └─────────────────┘                                  │
│                ↓                                             │
│         ┌─────────────────┐                                  │
│         │  Gemini (secondary)                                │
│         │  agrees → boost confidence                        │
│         │  disagrees → Roboflow tiebreaker                  │
│         └─────────────────┘                                  │
│                                                              │
│  Latency: 1.5-3s                                            │
│  Target: High accuracy when Fast Path uncertain              │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Modos de deployment:
| Variable               | Modo Fast | Modo Consensus | Modo Híbrido |
|------------------------|-----------|----------------|--------------|
| ENABLE_FAST_PATH       | true      | false          | true         |
| Fast Path Threshold    | 0.70      | N/A            | 0.70         |
| Background Validation  | Gemini    | N/A            | Gemini       |
| Fallback               | Consensus | Consensus      | Consensus    |

Feature flags:
- ENABLE_FAST_PATH=true → Fast Path activo
- FAST_PATH_CONFIDENCE_THRESHOLD=0.70 → Umbral mínimo
- CLASSIFIER_MODEL=gemini → Modelo para validation pipeline
```

### 1.2 Decisiones Arquitectónicas Clave

#### 1.2.1 Fast Path Architecture (V4.2 - Dic 2025)
**Decisión:** Roboflow responde inmediatamente, Gemini valida en background
**Rationale:**
- **UX Priority:** Usuario recibe respuesta en <1s
- **Accuracy garantizada:** Gemini valida y corrige en background
- **Best of both:** Speed de Roboflow + accuracy de LLM

**Implementación:**
```python
# app/agents/fast_classifier.py
class FastClassifier:
    async def classify_fast(image_data, trace_id) -> FastClassificationResult:
        # Roboflow classification <1s
        # Returns: material, confidence, color, message, should_validate

# app/orchestrator/fast_pipeline.py  
class ValidationPipeline:
    async def validate_and_sync(request, fast_result, trace_id):
        # Background: Gemini validation
        # Sync to backend if mismatch detected
```

**Resultados actuales:**
- Latencia: 570ms (local), 1.8s (Docker)
- Agreement rate: 33.3% (Roboflow vs Gemini)
- PLASTIC accuracy: 100%
- NO_WASTE accuracy: 0% (requiere reentrenamiento Roboflow)

**Trade-offs aceptados:**
- 33.3% agreement inicial (modelo Roboflow requiere más entrenamiento)
- Latencia Docker ~2x vs local (network overhead)

#### 1.2.2 Consensus Architecture (V4.2)
**Decisión:** Ensemble multi-modelo para alta confianza
**Rationale:**
- **Uncertainty handling:** Cuando GPT-4o no está seguro, consultar Gemini
- **Tiebreaker:** Roboflow resuelve desacuerdos entre LLMs
- **Confidence boost:** Acuerdo entre modelos aumenta confianza final

**Estrategias implementadas:**
1. **Agreement Boost:** Modelos coinciden → confidence +0.10
2. **Confidence-Based:** Mayor confidence gana
3. **Tie-Breaker:** Roboflow decide empates
4. **Conservative Fallback:** Ante duda, Material más conservador

#### 1.2.3 Edge Computing (Cliente)
**Decisión:** Mover object detection a cliente (Roboflow local)
**Rationale:**
- Reducción de latencia: 0ms para detección inicial
- UX mejorada: feedback visual inmediato
- Ahorro de costos: detección local gratuita
- Offline capability: funciona sin conectividad (cache)

**Implementación futura:** Ticket EDV-XX

#### 1.2.4 PreValidator Eliminado (V4.1 - EDV-58)
**Decisión:** Eliminar PreValidator del backend, validación client-side
**Rationale:**
- **ROI negativo:** Solo ahorra $9/mes con <1% troll rate (necesita >0.75% para justificar)
- **Latencia:** Elimina 200ms de overhead
- **False negatives:** PreValidator podía rechazar imágenes válidas
- **Industria:** OpenAI, Anthropic, Google no usan PreValidator separado
- **Serverless:** Roboflow tiene 37s cold start (inviable para serverless)
- **Simplificación:** 7 agentes → 6 agentes

**Alternativa implementada:** Validación client-side
- Formato/tamaño verificado antes de enviar
- UX inmediata (no espera respuesta backend)
- Zero backend cost

**Implementación:** Two-layer validation
1. **Layer 1:** Technical validations (formato, tamaño, dimensiones)
2. **Layer 2:** Roboflow Object Detection (waste presence)

#### 1.2.5 MaterialClassifier Unificado
**Decisión:** Fusionar Classifier + SubtypeDetector + VolumeEstimator → MaterialClassifier
**Rationale:**
- **Latencia:** 3 llamadas LLM → 1 llamada = 66% reducción
- **Contexto compartido:** Modelo ve imagen UNA vez, infiere todo junto
- **Consistencia:** Decisiones coherentes (ej: si detecta PET → sabe volumen típico)
- **Costos:** 3× $0.010 → 1× $0.010 = 66% ahorro

**Trade-off aceptado:**
- Pérdida de granularidad en logs (antes: 3 agentes, ahora: 1)
- Mitigación: Per-field confidences permiten análisis granular

#### 1.2.6 Per-Field Confidences
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
