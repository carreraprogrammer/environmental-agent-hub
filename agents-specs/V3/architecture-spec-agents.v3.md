# Agent Hub – Architecture Specification V3.0 (Technical Design)

## ⚠️ CONTEXTO - Tesis Ingeniería Ambiental

**Este documento especifica la arquitectura técnica del Agent Hub Python.**

**Propósito Principal (Tesis):**
Sistema de recolección de **datos ambientales** para investigación en gestión de residuos universitarios. La arquitectura técnica es un **medio**, no el fin - herramienta para lograr objetivos ambientales.

**Objetivos Ambientales:**
1. Recolectar datos: tipo, volumen, peso, ubicación, fecha de residuos
2. Educación: retroalimentación inmediata a usuarios
3. Análisis: datos estructurados para toma de decisiones ambientales
4. Impacto: cuantificar CO₂ evitado, recursos ahorrados

**Stack acordado:**
- Runtime: Python 3.11+
- Framework: FastAPI 0.104+
- Orquestación: Custom Pipeline (secuencial síncrono)
- LLM: OpenAI API, Google API, Roboflow API (experimentación técnica)
- Deploy: Railway/Render (Docker)
- Storage: S3 (upload asíncrono en background)

**Principios arquitectónicos (soporte técnico):**
- ✅ SOLID principles
- ✅ Adapter Pattern para modelos intercambiables (experimentación)
- ✅ Dependency Injection
- ✅ Stateless agents
- ✅ Fail-fast validation (calidad de datos ambientales)
- ✅ Logs estructurados JSON (trazabilidad de datos)
- ✅ Bytes-first processing (performance)
- ✅ Pipeline expandido (10 agentes especializados)

---

## 1) Stack Tecnológico

### 1.1 Core

```yaml
Lenguaje: Python 3.11+
Framework API: FastAPI 0.104+
ASGI Server: Uvicorn
HTTP Client: httpx (async)
Validación: Pydantic V2
Config: python-dotenv + PyYAML
Image Processing: Pillow>=10.0.0
```

### 1.2 Integraciones LLM

```yaml
OpenAI: openai>=1.0.0
Google: google-generativeai>=0.3.0
Roboflow: roboflow>=1.1.0    # ✅ YA IMPLEMENTADO
```

### 1.3 Storage & Utils

```yaml
AWS S3: boto3>=1.28.0
Logging: structlog
Image Processing: Pillow
Base64 Utils: base64 (built-in)
Testing: pytest + pytest-asyncio
```

### 1.4 Deployment

```yaml
Containerization: Docker
Orchestration: docker-compose (local)
Cloud: Railway / Render
CI/CD: GitHub Actions
```

---

## 2) Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT HUB (FastAPI)                              │
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
│  │              Pipeline Orchestrator (10 Agentes)                  │    │
│  │  - Coordina secuencia expandida de agentes                       │    │
│  │  - Maneja errores y timeouts por agente                          │    │
│  │  - Propaga trace_id                                               │    │
│  │  - Optimizado para <2s latencia                                  │    │
│  └─────────────────────────┬─────────────────────────────────────────┘    │
│                             │                                               │
│  ┌─────────────────────────▼─────────────────────────────────────────┐    │
│  │                  Agents Layer (Expandido)                         │    │
│  │                                                                   │    │
│  │  [1. Router] → Valida schema + procesa input                     │    │
│  │      ↓                                                            │    │
│  │  [2. PreValidator] → Detecta residuo (anti-troll)                │    │
│  │      ↓                                                            │    │
│  │  [3. Classifier] ← Factory → Adapter (intercambiable)            │    │
│  │      ↓                                                            │    │
│  │  [4. SubtypeDetector] → Identifica subtipo específico            │    │
│  │      ↓                                                            │    │
│  │  [5. VolumeEstimator] → Estima volumen y peso                    │    │
│  │      ↓                                                            │    │
│  │  [6. Mapper] → Material → Color (NTC 2184)                       │    │
│  │      ↓                                                            │    │
│  │  [7. WasteTypeMapper] → Material+volumen → waste_type_code       │    │
│  │      ↓                                                            │    │
│  │  [8. FeedbackCoach] → Mensaje educativo enriquecido              │    │
│  │      ↓                                                            │    │
│  │  [9. Assembler] → Construye response completo                    │    │
│  │      ↓                                                            │    │
│  │  [10. BackendIntegration] → Envía datos a Rails API              │    │
│  │                                                                   │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │            Adapters (Intercambiables - ACTUALIZADOS)             │    │
│  │                                                                   │    │
│  │  ┌─────────────────────────────────────────────────────────────┐ │    │
│  │  │            ClassifierAdapter (ABC)                         │ │    │
│  │  │  - classify(image: bytes | str) -> ClassificationResult   │ │    │
│  │  │  - model_name (property)                                   │ │    │
│  │  │  - cost_per_request (property)                             │ │    │
│  │  │  - supports_bytes: bool (property)                        │ │    │
│  │  └───────────────────┬───────────────────────────────────────┘ │    │
│  │                      │                                         │    │
│  │  ┌─────────────────┬─┴──────────────┬──────────────────────┐ │    │
│  │  │                 │                │                      │ │    │
│  │  ▼                 ▼                ▼                      ▼ │    │
│  │  OpenAI           Google          Roboflow             Future │    │
│  │  Adapter          Adapter         Adapter             Adapters│    │
│  │  (GPT-4o)         (Gemini 2.0)    (✅ IMPLEMENTADO)          │    │
│  │  ✅ Bytes         ✅ Bytes        ✅ Bytes                   │    │
│  │  ✅ URL           ✅ URL          ✅ URL                     │    │
│  │                                                               │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      Services Layer                               │ │
│  │  - S3Service (upload asíncrono en background)                    │ │
│  │  - BackendClient (llamar Rails API con datos completos)          │ │
│  │  - MetricsCollector (telemetría expandida)                       │ │
│  │  - ImageProcessor (bytes ↔ PIL ↔ base64)                         │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3) Estructura de Carpetas (DDD Expandido)

```
agent-hub/
├── app/
│   ├── __init__.py
│   │
│   ├── main.py                    # FastAPI app + startup
│   │
│   ├── api/                       # API Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py        # DI containers
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── classify.py        # POST /classify (multipart + JSON)
│   │       ├── health.py          # GET /health
│   │       └── models.py          # GET /models
│   │
│   ├── core/                      # Core config & utils
│   │   ├── __init__.py
│   │   ├── config.py              # Settings (Pydantic BaseSettings)
│   │   ├── logging.py             # Structured logging setup
│   │   └── exceptions.py          # Custom exceptions
│   │
│   ├── agents/                    # Domain agents (10 agentes)
│   │   ├── __init__.py
│   │   ├── router.py              # 1. Valida request schema + input
│   │   ├── pre_validator.py       # 2. Detecta residuo (GPT-4o-mini)
│   │   ├── classifier.py          # 3. Clasifica con modelo activo
│   │   ├── subtype_detector.py    # 4. NUEVO: Detecta subtipo específico
│   │   ├── volume_estimator.py    # 5. NUEVO: Estima volumen y peso
│   │   ├── mapper.py              # 6. Material → Color (NTC 2184)
│   │   ├── waste_type_mapper.py   # 7. NUEVO: Material+vol → waste_type_code
│   │   ├── feedback_coach.py      # 8. Genera mensaje educativo
│   │   ├── assembler.py           # 9. Construye response final
│   │   └── backend_integration.py # 10. NUEVO: Envía a Rails API
│   │
│   ├── adapters/                  # Adapter Pattern (ACTUALIZADOS)
│   │   ├── __init__.py
│   │   ├── base.py                # ClassifierAdapter (ABC) + bytes support
│   │   ├── openai_adapter.py      # GPT-4o (bytes + URL)
│   │   ├── google_adapter.py      # Gemini 2.0 Flash (bytes + URL)
│   │   ├── roboflow_adapter.py    # ✅ YA IMPLEMENTADO (bytes + URL)
│   │   └── anthropic_adapter.py   # REMOVIDO (no está en MVP)
│   │
│   ├── factories/                 # Factory Pattern
│   │   ├── __init__.py
│   │   └── classifier_factory.py  # Crea adapters según config
│   │
│   ├── orchestrator/              # Pipeline coordinator
│   │   ├── __init__.py
│   │   ├── pipeline.py            # Orquestador principal (10 agentes)
│   │   └── pipeline_config.py     # Config de flujo
│   │
│   ├── schemas/                   # Pydantic models (ACTUALIZADOS)
│   │   ├── __init__.py
│   │   ├── requests.py            # ClassifyRequest (multipart + JSON)
│   │   ├── responses.py           # ClassifyResponse (+ volumen, subtipo)
│   │   └── domain.py              # ClassificationResult, WasteMaterial, SubTypes
│   │
│   ├── services/                  # External services (EXPANDIDOS)
│   │   ├── __init__.py
│   │   ├── s3_service.py          # Upload async + download
│   │   ├── backend_client.py      # HTTP client a Rails API (datos completos)
│   │   ├── metrics_collector.py   # Telemetría expandida
│   │   └── image_processor.py     # NUEVO: bytes ↔ PIL ↔ base64
│   │
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── tracing.py             # trace_id propagation
│       ├── retry.py               # Exponential backoff
│       └── cache.py               # In-memory idempotency cache
│
├── config/                        # Configuration files (ACTUALIZADOS)
│   ├── models.yaml                # Model configurations (+ Roboflow)
│   ├── subtype_mappings.yaml      # NUEVO: Material → Subtipos
│   ├── volume_estimates.yaml      # NUEVO: Subtipo → Volumen/Peso
│   └── prompts.yaml               # Prompt templates (expandidos)
│
├── scripts/                       # Analysis & experimentation (ACTUALIZADOS)
│   ├── run_experiment.py          # Run model comparison (+ subtipos)
│   ├── analyze_models.py          # Generate comparison tables
│   ├── export_metrics.py          # Export logs to CSV
│   ├── validate_volume_estimates.py # NUEVO: Validar precisión estimaciones
│   └── ground_truth_validator.py  # Validate against ground truth
│
├── tests/                         # Testing (EXPANDIDOS)
│   ├── unit/                      # Unit tests (10 agentes + adapters)
│   ├── integration/               # Integration tests (pipeline completo)
│   ├── fixtures/                  # Test data & mocks (+ imágenes subtipo)
│   └── performance/               # NUEVO: Performance tests (<2s)
│
├── docker/
│   ├── Dockerfile                 # Production image
│   └── docker-compose.yml         # Local development
│
├── .env.example                   # Environment variables template
├── pyproject.toml                 # Dependencies (Poetry)
├── requirements.txt               # Alternative (pip)
└── README.md                      # Setup & usage instructions
```

---

## 4) Componentes Detallados

### 4.1 API Layer ACTUALIZADA

#### 4.1.1 FastAPI Application

**File:** `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.endpoints import classify, health, models

# Setup logging
setup_logging()

# Create app
app = FastAPI(
    title="Agent Hub API",
    version="3.0.0",
    description="Waste classification orchestrator with 10 specialized agents"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(classify.router, prefix="/api/v1", tags=["classification"])
app.include_router(health.router, tags=["health"])
app.include_router(models.router, prefix="/api/v1", tags=["models"])

@app.on_event("startup")
async def startup_event():
    """Log active model on startup"""
    from app.factories.classifier_factory import ClassifierFactory
    from app.core.logging import logger
    
    classifier = ClassifierFactory.create()
    logger.info(
        "agent_hub_started",
        active_model=classifier.model_name,
        cost_per_request=classifier.cost_per_request,
        supports_bytes=classifier.supports_bytes,
        pipeline_agents=10
    )
```

#### 4.1.2 Classify Endpoint ACTUALIZADO

**File:** `app/api/endpoints/classify.py`

```python
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from fastapi.responses import JSONResponse
from app.schemas.requests import ClassifyRequest, ClassifyRequestForm
from app.schemas.responses import ClassifyResponse, ErrorResponse
from app.orchestrator.pipeline import Pipeline
from app.core.logging import logger
from app.services.image_processor import ImageProcessor
import time

router = APIRouter()

async def get_pipeline() -> Pipeline:
    """Dependency injection for Pipeline"""
    return Pipeline()

@router.post("/classify", response_model=ClassifyResponse)
async def classify_waste(
    # Opción A: multipart/form-data (PREFERIDA - bytes processing)
    image: UploadFile = File(None),
    scan_id: str = Form(None),
    station_id: str = Form(None),
    tenant_id: str = Form(None),
    trace_id: str = Form(None),
    idempotency_key: str = Form(None),
    
    # Opción B: JSON (LEGACY - URL processing)
    request: ClassifyRequest = None,
    
    pipeline: Pipeline = Depends(get_pipeline)
):
    """
    Classify waste from image using active model.
    
    Supports two input formats:
    1. multipart/form-data with image bytes (PREFERRED - 60% faster)
    2. JSON with image_url (LEGACY - backward compatible)
    
    Process:
    1. Detect input format
    2. Process image (bytes vs URL)
    3. Run 10-agent pipeline
    4. Return enhanced response
    """
    start_time = time.time()
    
    try:
        # Detect input format
        if image and scan_id:
            # Opción A: multipart/form-data (PREFERIDA)
            image_bytes = await image.read()
            request_data = ClassifyRequestForm(
                scan_id=scan_id,
                station_id=station_id,
                image_bytes=image_bytes,
                tenant_id=tenant_id,
                trace_id=trace_id,
                idempotency_key=idempotency_key
            )
            input_format = "bytes"
            logger.info(
                "classify_request_received",
                trace_id=str(request_data.trace_id),
                input_format="bytes",
                image_size_kb=len(image_bytes) // 1024
            )
        elif request:
            # Opción B: JSON (LEGACY)
            request_data = request
            input_format = "url"
            logger.info(
                "classify_request_received",
                trace_id=str(request.trace_id),
                input_format="url",
                image_url=request.image_url
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail="Provide either multipart form data or JSON request"
            )
        
        # Execute 10-agent pipeline
        result = await pipeline.process(request_data)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "classify_request_completed",
            trace_id=str(request_data.trace_id),
            material=result.material,
            subtype=result.subtype,
            volume_ml=result.volume_ml,
            confidence=result.confidence,
            model_used=result.meta.model_used,
            input_format=input_format,
            latency_ms=elapsed_ms,
            agents_executed=len(result.meta.agents_executed)
        )
        
        # Add input metadata to response
        result.meta.input_format = input_format
        if input_format == "bytes":
            result.meta.s3_upload_status = "pending"  # Upload en background
        
        return result
        
    except ValidationError as e:
        logger.warning(
            "classify_request_rejected",
            trace_id=str(request_data.trace_id if 'request_data' in locals() else 'unknown'),
            reason=e.error_code,
            latency_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=400, detail=e.to_dict())
        
    except TimeoutError as e:
        logger.error(
            "classify_request_timeout",
            trace_id=str(request_data.trace_id if 'request_data' in locals() else 'unknown'),
            latency_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=504, detail="Classification timeout")
        
    except Exception as e:
        logger.exception(
            "classify_request_failed",
            trace_id=str(request_data.trace_id if 'request_data' in locals() else 'unknown'),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

### 4.2 Adapters Layer ACTUALIZADOS

#### 4.2.1 Base Adapter ACTUALIZADO

**File:** `app/adapters/base.py`

```python
from abc import ABC, abstractmethod
from app.schemas.domain import ClassificationResult
from typing import Union

class ClassifierAdapter(ABC):
    """
    Abstract base class for all classification models.
    
    V3.0 Updates:
    - Support for bytes AND URL input
    - Performance metadata
    - Enhanced error handling
    """
    
    @abstractmethod
    async def classify(self, image: Union[bytes, str]) -> ClassificationResult:
        """
        Classify waste from image bytes or URL.
        
        Args:
            image: Image as bytes (preferred) or URL string (legacy)
            
        Returns:
            ClassificationResult with material, confidence, metadata
            
        Raises:
            ClassificationError: If classification fails
            TimeoutError: If request exceeds timeout
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Full model identifier.
        
        Format: "provider/model-name"
        Example: "openai/gpt-4o"
        """
        pass
    
    @property
    @abstractmethod
    def model_provider(self) -> str:
        """
        Provider name.
        
        Example: "openai", "google", "roboflow"
        """
        pass
    
    @property
    @abstractmethod
    def cost_per_request(self) -> float:
        """
        Cost in USD per classification request.
        """
        pass
    
    @property
    @abstractmethod
    def supports_bytes(self) -> bool:
        """
        Whether adapter supports direct bytes processing.
        
        Returns:
            True: Can process image bytes directly (faster)
            False: Requires URL (legacy)
        """
        pass
    
    def get_latency_estimate(self, input_format: str) -> int:
        """
        Estimate latency based on input format.
        
        Args:
            input_format: "bytes" or "url"
            
        Returns:
            Estimated latency in milliseconds
        """
        base_latency = self._get_base_latency()
        if input_format == "url" and self.supports_bytes:
            return int(base_latency * 1.5)  # 50% penalty for URL processing
        return base_latency
    
    @abstractmethod
    def _get_base_latency(self) -> int:
        """Base latency for bytes processing"""
        pass
```

#### 4.2.2 OpenAI Adapter ACTUALIZADO

**File:** `app/adapters/openai_adapter.py`

```python
from openai import AsyncOpenAI
from app.adapters.base import ClassifierAdapter
from app.schemas.domain import ClassificationResult, WasteMaterial
from app.core.config import settings
from app.core.logging import logger
from app.services.image_processor import ImageProcessor
import asyncio
from typing import Union

class OpenAIClassifierAdapter(ClassifierAdapter):
    """
    OpenAI GPT-4o adapter with bytes support.
    
    V3.0 Features:
    - Native bytes processing (60% faster)
    - URL fallback for backward compatibility
    - Enhanced error handling
    """
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.image_processor = ImageProcessor()
        self._cost_map = {
            "gpt-4o": 0.005,
            "gpt-4-vision-preview": 0.010
        }
    
    async def classify(self, image: Union[bytes, str]) -> ClassificationResult:
        """Classify using OpenAI Vision API with bytes or URL"""
        
        prompt = await self._prepare_prompt()
        
        try:
            # Prepare image content based on input type
            if isinstance(image, bytes):
                # Opción A: Bytes processing (PREFERIDA)
                base64_image = self.image_processor.bytes_to_base64(image)
                image_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
                processing_method = "bytes"
            else:
                # Opción B: URL processing (LEGACY)
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": image}
                }
                processing_method = "url"
            
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                image_content
                            ]
                        }
                    ],
                    max_tokens=100,
                    temperature=0.0  # Deterministic
                ),
                timeout=10.0
            )
            
            # Parse response
            content = response.choices[0].message.content.strip().upper()
            material = self._parse_material(content)
            confidence = self._estimate_confidence(content)
            
            return ClassificationResult(
                material=material,
                confidence=confidence,
                model_used=self.model_name,
                model_provider=self.model_provider,
                raw_response=content,
                processing_method=processing_method
            )
            
        except asyncio.TimeoutError:
            logger.error("openai_timeout", model=self.model)
            raise TimeoutError(f"OpenAI {self.model} request timeout")
        
        except Exception as e:
            logger.exception("openai_error", model=self.model, error=str(e))
            raise ClassificationError(f"OpenAI classification failed: {str(e)}")
    
    async def _prepare_prompt(self) -> str:
        """Generate classification prompt"""
        return """
Clasifica el residuo en esta imagen en EXACTAMENTE una de estas categorías:

- PLASTIC: Botellas plásticas, envases, bolsas
- PAPER: Papel, cartón, periódicos
- GLASS: Botellas de vidrio, frascos
- METAL: Latas de aluminio o acero
- ORGANIC: Restos de comida, material vegetal
- OTHER: Si no encaja claramente en las anteriores

Responde SOLO con el nombre de la categoría en MAYÚSCULAS.
Si tienes dudas, usa OTHER.
"""
    
    def _parse_material(self, content: str) -> WasteMaterial:
        """Parse OpenAI response to WasteMaterial enum"""
        content = content.strip().upper()
        
        # Direct match
        try:
            return WasteMaterial(content)
        except ValueError:
            pass
        
        # Fuzzy match
        if "PLASTIC" in content:
            return WasteMaterial.PLASTIC
        elif "PAPER" in content:
            return WasteMaterial.PAPER
        elif "GLASS" in content:
            return WasteMaterial.GLASS
        elif "METAL" in content:
            return WasteMaterial.METAL
        elif "ORGANIC" in content:
            return WasteMaterial.ORGANIC
        else:
            return WasteMaterial.OTHER
    
    def _estimate_confidence(self, content: str) -> float:
        """Estimate confidence heuristically"""
        content = content.strip().upper()
        
        # Single word response = high confidence
        if len(content.split()) == 1:
            return 0.90
        
        # Response with explanations = lower confidence
        return 0.75
    
    @property
    def model_name(self) -> str:
        return f"openai/{self.model}"
    
    @property
    def model_provider(self) -> str:
        return "openai"
    
    @property
    def cost_per_request(self) -> float:
        return self._cost_map.get(self.model, 0.005)
    
    @property
    def supports_bytes(self) -> bool:
        return True  # OpenAI supports base64
    
    def _get_base_latency(self) -> int:
        return 600  # 600ms for bytes processing
```

#### 4.2.3 Roboflow Adapter IMPLEMENTADO

**File:** `app/adapters/roboflow_adapter.py`

```python
from roboflow import Roboflow
from app.adapters.base import ClassifierAdapter
from app.schemas.domain import ClassificationResult, WasteMaterial
from app.core.config import settings
from app.core.logging import logger
from app.services.image_processor import ImageProcessor
import asyncio
from typing import Union
import tempfile
import os

class RoboflowClassifierAdapter(ClassifierAdapter):
    """
    Roboflow Custom Model adapter.
    
    Model: environmental-assitant-agents/waste-classifier-louut-b9sot/1
    Status: ✅ YA IMPLEMENTADO
    """
    
    def __init__(self):
        self.rf = Roboflow(api_key=settings.ROBOFLOW_API_KEY)
        self.project = self.rf.workspace("environmental-assitant-agents").project("waste-classifier-louut-b9sot")
        self.model = self.project.version(1).model
        self.image_processor = ImageProcessor()
    
    async def classify(self, image: Union[bytes, str]) -> ClassificationResult:
        """Classify using Roboflow specialized model"""
        
        try:
            if isinstance(image, bytes):
                # Opción A: Bytes processing
                # Roboflow requiere archivo temporal
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp.write(image)
                    tmp_path = tmp.name
                
                prediction = await asyncio.to_thread(
                    self.model.predict, tmp_path
                )
                
                # Cleanup
                os.unlink(tmp_path)
                processing_method = "bytes"
                
            else:
                # Opción B: URL processing
                prediction = await asyncio.to_thread(
                    self.model.predict, image
                )
                processing_method = "url"
            
            # Parse Roboflow response
            material, confidence = self._parse_roboflow_response(prediction)
            
            return ClassificationResult(
                material=material,
                confidence=confidence,
                model_used=self.model_name,
                model_provider=self.model_provider,
                raw_response=str(prediction.json()),
                processing_method=processing_method
            )
            
        except Exception as e:
            logger.exception("roboflow_error", error=str(e))
            raise ClassificationError(f"Roboflow classification failed: {str(e)}")
    
    def _parse_roboflow_response(self, prediction) -> tuple[WasteMaterial, float]:
        """Parse Roboflow prediction to WasteMaterial"""
        
        # Roboflow devuelve class, pero puede no enviar confidence; usar 1.0 por defecto
        if not prediction.predictions:
            return WasteMaterial.OTHER, 0.3
        
        best_prediction = max(
            prediction.predictions,
            key=lambda p: getattr(p, "confidence", 1.0),
        )
        
        # Mapear clase de Roboflow a WasteMaterial
        class_mapping = {
            "plastic": WasteMaterial.PLASTIC,
            "paper": WasteMaterial.PAPER,
            "glass": WasteMaterial.GLASS,
            "metal": WasteMaterial.METAL,
            "organic": WasteMaterial.ORGANIC,
            "cardboard": WasteMaterial.PAPER,
            "bottle": WasteMaterial.PLASTIC,  # Asumir plástico por defecto
            "can": WasteMaterial.METAL,
        }
        
        detected_class = best_prediction.class_name.lower()
        material = class_mapping.get(detected_class, WasteMaterial.OTHER)
        confidence = float(best_prediction.confidence)
        
        return material, confidence
    
    @property
    def model_name(self) -> str:
        return "roboflow/waste-classifier-louut-b9sot-v1"
    
    @property
    def model_provider(self) -> str:
        return "roboflow"
    
    @property
    def cost_per_request(self) -> float:
        return 0.001  # Muy económico
    
    @property
    def supports_bytes(self) -> bool:
        return True  # Soporta archivos
    
    def _get_base_latency(self) -> int:
        return 300  # 300ms - muy rápido
```

#### 4.2.4 Google Adapter ACTUALIZADO

**File:** `app/adapters/google_adapter.py`

```python
import google.generativeai as genai
from app.adapters.base import ClassifierAdapter
from app.schemas.domain import ClassificationResult, WasteMaterial
from app.core.config import settings
from app.core.logging import logger
from app.services.image_processor import ImageProcessor
import asyncio
from typing import Union
from PIL import Image
import io

class GoogleClassifierAdapter(ClassifierAdapter):
    """
    Google Gemini 2.0 Flash adapter with bytes support.
    
    V3.0 Features:
    - Native PIL Image processing
    - URL and bytes support
    - Cost: $0.00 (gratis)
    """
    
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.image_processor = ImageProcessor()
    
    async def classify(self, image: Union[bytes, str]) -> ClassificationResult:
        """Classify using Gemini Vision API"""
        
        prompt = await self._prepare_prompt()
        
        try:
            if isinstance(image, bytes):
                # Opción A: Bytes processing (PREFERIDA)
                pil_image = Image.open(io.BytesIO(image))
                processing_method = "bytes"
            else:
                # Opción B: URL processing (LEGACY)
                # Descargar imagen y convertir a PIL
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(image)
                    pil_image = Image.open(io.BytesIO(response.content))
                processing_method = "url"
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, pil_image]
            )
            
            # Parse response
            content = response.text.strip().upper()
            material = self._parse_material(content)
            confidence = 0.85  # Gemini generalmente alta confianza
            
            return ClassificationResult(
                material=material,
                confidence=confidence,
                model_used=self.model_name,
                model_provider=self.model_provider,
                raw_response=content,
                processing_method=processing_method
            )
            
        except Exception as e:
            logger.exception("google_error", error=str(e))
            raise ClassificationError(f"Google Gemini classification failed: {str(e)}")
    
    async def _prepare_prompt(self) -> str:
        """Same prompt as OpenAI for consistency"""
        return """
Clasifica el residuo en esta imagen en EXACTAMENTE una de estas categorías:

- PLASTIC: Botellas plásticas, envases, bolsas
- PAPER: Papel, cartón, periódicos
- GLASS: Botellas de vidrio, frascos
- METAL: Latas de aluminio o acero
- ORGANIC: Restos de comida, material vegetal
- OTHER: Si no encaja claramente en las anteriores

Responde SOLO con el nombre de la categoría en MAYÚSCULAS.
Si tienes dudas, usa OTHER.
"""
    
    def _parse_material(self, content: str) -> WasteMaterial:
        """Same parsing logic as OpenAI"""
        content = content.strip().upper()
        try:
            return WasteMaterial(content)
        except ValueError:
            # Fuzzy matching
            if "PLASTIC" in content:
                return WasteMaterial.PLASTIC
            elif "PAPER" in content:
                return WasteMaterial.PAPER
            elif "GLASS" in content:
                return WasteMaterial.GLASS
            elif "METAL" in content:
                return WasteMaterial.METAL
            elif "ORGANIC" in content:
                return WasteMaterial.ORGANIC
            else:
                return WasteMaterial.OTHER
    
    @property
    def model_name(self) -> str:
        return "google/gemini-2.0-flash-exp"
    
    @property
    def model_provider(self) -> str:
        return "google"
    
    @property
    def cost_per_request(self) -> float:
        return 0.000  # Gratis en preview
    
    @property
    def supports_bytes(self) -> bool:
        return True  # Gemini soporta PIL Images
    
    def _get_base_latency(self) -> int:
        return 700  # 700ms for bytes processing
```

---

### 4.3 Factory Pattern ACTUALIZADO

**File:** `app/factories/classifier_factory.py`

```python
from app.adapters.base import ClassifierAdapter
from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.adapters.google_adapter import GoogleClassifierAdapter
from app.adapters.roboflow_adapter import RoboflowClassifierAdapter
from app.core.config import settings
from app.core.logging import logger

class ClassifierFactory:
    """
    Factory for creating classifier adapters.
    
    V3.0 Updates:
    - Roboflow support (YA IMPLEMENTADO)
    - Removed Anthropic (not in MVP)
    - Enhanced model validation
    """
    
    @staticmethod
    def create(model_override: str = None) -> ClassifierAdapter:
        """
        Create classifier adapter based on config.
        
        Args:
            model_override: Optional override for testing
            
        Returns:
            Initialized ClassifierAdapter
            
        Raises:
            ValueError: If model not supported
        """
        model = model_override or settings.CLASSIFIER_MODEL
        
        match model:
            case "openai-gpt4o":
                logger.info("classifier_created", model="openai/gpt-4o")
                return OpenAIClassifierAdapter("gpt-4o")
            
            case "openai-gpt4-vision":
                logger.info("classifier_created", model="openai/gpt-4-vision-preview")
                return OpenAIClassifierAdapter("gpt-4-vision-preview")
            
            case "gemini-flash":
                logger.info("classifier_created", model="google/gemini-2.0-flash-exp")
                return GoogleClassifierAdapter()
            
            case "roboflow":
                logger.info("classifier_created", model="roboflow/waste-classifier-v1")
                return RoboflowClassifierAdapter()
            
            case _:
                raise ValueError(
                    f"Unknown classifier model: {model}. "
                    f"Supported: openai-gpt4o, gemini-flash, roboflow"
                )
    
    @staticmethod
    def list_available() -> list[str]:
        """List all available models with status"""
        return [
            "openai-gpt4o",      # ✅ IMPLEMENTADO
            "gemini-flash",      # ✅ IMPLEMENTADO  
            "roboflow"           # ✅ IMPLEMENTADO
        ]
    
    @staticmethod
    def get_model_info(model: str) -> dict:
        """Get detailed model information"""
        model_info = {
            "openai-gpt4o": {
                "provider": "openai",
                "cost_per_request": 0.005,
                "latency_bytes": 600,
                "latency_url": 900,
                "supports_bytes": True,
                "status": "✅ IMPLEMENTADO"
            },
            "gemini-flash": {
                "provider": "google",
                "cost_per_request": 0.000,
                "latency_bytes": 700,
                "latency_url": 1100,
                "supports_bytes": True,
                "status": "✅ IMPLEMENTADO"
            },
            "roboflow": {
                "provider": "roboflow",
                "cost_per_request": 0.001,
                "latency_bytes": 300,
                "latency_url": 400,
                "supports_bytes": True,
                "status": "✅ IMPLEMENTADO"
            }
        }
        
        return model_info.get(model, {"status": "❌ NO IMPLEMENTADO"})
```

---

### 4.4 NUEVOS AGENTES (4-7)

#### 4.4.1 SubtypeDetector Agent

**File:** `app/agents/subtype_detector.py`

```python
from app.adapters.base import ClassifierAdapter
from app.schemas.domain import WasteMaterial
from app.core.logging import logger
from typing import Union, Dict
import asyncio

class SubtypeDetector:
    """
    Agent 4: Detecta características específicas de residuos.
    
    Purpose: Identificar atributos para mapeo preciso a waste_type_code
    Input: image + material clasificado
    Output: características detectadas (NO códigos directos del Backend)
    
    IMPORTANTE: Este agente detecta CARACTERÍSTICAS (tamaño, material específico, color),
    NO códigos de waste_type. El mapeo a códigos del Backend lo hace WasteTypeMapper.
    """
    
    def __init__(self, classifier_adapter: ClassifierAdapter):
        self.classifier_adapter = classifier_adapter
        self.detection_method = "lookup"  # "lookup" | "llm"
    
    async def detect_characteristics(
        self, 
        image: Union[bytes, str], 
        material: WasteMaterial,
        volume_ml: float = None
    ) -> Dict:
        """
        Detect specific characteristics based on material.
        
        Args:
            image: Image bytes or URL
            material: Already classified material
            volume_ml: Optional volume hint from estimator
            
        Returns:
            {
                "material_specific": str,  # Ej: "aluminum" vs "steel"
                "container_type": str,     # Ej: "bottle", "can", "box"
                "size": str,               # Ej: "small", "medium", "large"
                "color": str,              # Ej: "clear", "colored"
                "confidence": float
            }
        """
        
        try:
            if self.detection_method == "lookup":
                characteristics = self._detect_characteristics_heuristic(
                    material, 
                    volume_ml
                )
            else:
                # Futuro: LLM-based detection
                characteristics = await self._detect_characteristics_llm(
                    image, 
                    material
                )
            
            logger.info(
                "characteristics_detected",
                material=material.value,
                characteristics=characteristics,
                method=self.detection_method
            )
            
            return characteristics
            
        except Exception as e:
            logger.exception("characteristic_detection_failed", error=str(e))
            # Fallback to minimal characteristics
            return {
                "material_specific": None,
                "container_type": "unknown",
                "size": "medium",
                "color": None,
                "confidence": 0.3
            }
    
    def _detect_characteristics_heuristic(
        self, 
        material: WasteMaterial,
        volume_ml: float = None
    ) -> Dict:
        """
        Heuristic characteristic detection for MVP.
        Based on material and optional volume hint.
        """
        
        characteristics = {"confidence": 0.7}
        
        if material == WasteMaterial.PLASTIC:
            characteristics.update({
                "container_type": "bottle",
                "material_specific": "PET",
                "size": self._determine_size(volume_ml, [500, 1500]) if volume_ml else "medium"
            })
        
        elif material == WasteMaterial.METAL:
            characteristics.update({
                "container_type": "can",
                "material_specific": "aluminum",  # Default más común
                "size": self._determine_size(volume_ml, [355, 500]) if volume_ml else "standard"
            })
        
        elif material == WasteMaterial.GLASS:
            characteristics.update({
                "container_type": "bottle",
                "color": "clear",  # Default más común
                "size": self._determine_size(volume_ml, [330, 750]) if volume_ml else "medium"
            })
        
        elif material == WasteMaterial.PAPER:
            characteristics.update({
                "container_type": "box" if volume_ml and volume_ml > 100 else "sheet",
                "material_specific": "cardboard" if volume_ml and volume_ml > 50 else "paper",
                "size": "medium"
            })
        
        else:  # OTHER, ORGANIC
            characteristics.update({
                "container_type": "unknown",
                "material_specific": None,
                "size": "medium"
            })
        
        return characteristics
    
    def _determine_size(self, volume_ml: float, breakpoints: list) -> str:
        """Determine size category based on volume"""
        if not volume_ml or not breakpoints:
            return "medium"
        
        if volume_ml < breakpoints[0] * 0.8:
            return "small"
        elif volume_ml > breakpoints[-1] * 1.2:
            return "large"
        else:
            return "medium"
    
    async def _detect_characteristics_llm(
        self,
        image: Union[bytes, str],
        material: WasteMaterial
    ) -> Dict:
        """LLM-based detection (Futuro V3.2)"""
        raise NotImplementedError("LLM detection not yet implemented")
```

#### 4.4.2 VolumeEstimator Agent

**File:** `app/agents/volume_estimator.py`

```python
from app.schemas.domain import WasteMaterial
from app.core.config import settings
from app.core.logging import logger
import yaml
from pathlib import Path

class VolumeEstimator:
    """
    Agent 5: Estima volumen y peso de residuos.
    
    Purpose: Generar datos precisos para cálculos ambientales
    Input: material + subtipo
    Output: {volume_ml, weight_g, estimation_method}
    """
    
    def __init__(self):
        self.estimation_method = settings.VOLUME_ESTIMATION_METHOD  # "lookup" | "ai"
        self.volume_mappings = self._load_volume_mappings()
    
    def _load_volume_mappings(self) -> dict:
        """Load volume/weight mappings from config"""
        config_path = Path("config/volume_estimates.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Default mappings if config file doesn't exist
            return {
                "PET_BOTTLE_250ML": {"volume_ml": 250, "weight_g": 12},
                "PET_BOTTLE_500ML": {"volume_ml": 500, "weight_g": 15},
                "PET_BOTTLE_1L": {"volume_ml": 1000, "weight_g": 28},
                "PET_BOTTLE_2L": {"volume_ml": 2000, "weight_g": 45},
                "ALUMINUM_CAN_355ML": {"volume_ml": 355, "weight_g": 15},
                "ALUMINUM_CAN_500ML": {"volume_ml": 500, "weight_g": 18},
                "GLASS_BOTTLE_330ML": {"volume_ml": 330, "weight_g": 180},
                "GLASS_BOTTLE_750ML": {"volume_ml": 750, "weight_g": 400},
                "GLASS_JAR_200ML": {"volume_ml": 200, "weight_g": 150},
                "CARDBOARD_BOX_SMALL": {"volume_ml": 1000, "weight_g": 50},
                "CARDBOARD_BOX_LARGE": {"volume_ml": 5000, "weight_g": 200},
                # Fallbacks genéricos
                "PLASTIC_GENERIC": {"volume_ml": 500, "weight_g": 15},
                "METAL_GENERIC": {"volume_ml": 355, "weight_g": 15},
                "GLASS_GENERIC": {"volume_ml": 330, "weight_g": 180},
                "PAPER_GENERIC": {"volume_ml": 1000, "weight_g": 50},
                "ORGANIC_GENERIC": {"volume_ml": 0, "weight_g": 100},
                "OTHER_GENERIC": {"volume_ml": 0, "weight_g": 50}
            }
    
    async def estimate_volume(
        self, 
        material: WasteMaterial, 
        subtype: str
    ) -> dict:
        """
        Estimate volume and weight.
        
        Args:
            material: Classified material
            subtype: Detected subtype
            
        Returns:
            {volume_ml: float, weight_g: float, estimation_method: str}
        """
        
        try:
            if self.estimation_method == "lookup":
                return await self._estimate_by_lookup(material, subtype)
            elif self.estimation_method == "ai":
                return await self._estimate_by_ai(material, subtype)
            else:
                raise ValueError(f"Unknown estimation method: {self.estimation_method}")
                
        except Exception as e:
            logger.exception("volume_estimation_failed", error=str(e))
            # Fallback to generic estimates
            return self._get_fallback_estimate(material)
    
    async def _estimate_by_lookup(self, material: WasteMaterial, subtype: str) -> dict:
        """
        Estimate using lookup table (FAST, MVP approach).
        """
        
        # Try specific subtype first
        if subtype in self.volume_mappings:
            estimate = self.volume_mappings[subtype]
            logger.info(
                "volume_estimated",
                method="lookup",
                subtype=subtype,
                volume_ml=estimate["volume_ml"],
                weight_g=estimate["weight_g"]
            )
            return {
                "volume_ml": estimate["volume_ml"],
                "weight_g": estimate["weight_g"],
                "estimation_method": "lookup"
            }
        
        # Fallback to generic material estimate
        generic_key = f"{material.value}_GENERIC"
        if generic_key in self.volume_mappings:
            estimate = self.volume_mappings[generic_key]
            logger.info(
                "volume_estimated",
                method="lookup_fallback",
                material=material.value,
                volume_ml=estimate["volume_ml"],
                weight_g=estimate["weight_g"]
            )
            return {
                "volume_ml": estimate["volume_ml"],
                "weight_g": estimate["weight_g"],
                "estimation_method": "lookup_fallback"
            }
        
        # Ultimate fallback
        return self._get_fallback_estimate(material)
    
    async def _estimate_by_ai(self, material: WasteMaterial, subtype: str) -> dict:
        """
        Estimate using AI model (PRECISE, more expensive).
        
        TODO: Implement in V3.1 with specialized prompt
        """
        
        # For now, fallback to lookup
        logger.warning("ai_estimation_not_implemented", falling_back_to="lookup")
        return await self._estimate_by_lookup(material, subtype)
    
    def _get_fallback_estimate(self, material: WasteMaterial) -> dict:
        """Ultimate fallback estimates"""
        
        fallbacks = {
            WasteMaterial.PLASTIC: {"volume_ml": 500, "weight_g": 15},
            WasteMaterial.METAL: {"volume_ml": 355, "weight_g": 15},
            WasteMaterial.GLASS: {"volume_ml": 330, "weight_g": 180},
            WasteMaterial.PAPER: {"volume_ml": 1000, "weight_g": 50},
            WasteMaterial.ORGANIC: {"volume_ml": 0, "weight_g": 100},
            WasteMaterial.OTHER: {"volume_ml": 0, "weight_g": 50}
        }
        
        estimate = fallbacks[material]
        
        logger.warning(
            "volume_estimation_fallback",
            material=material.value,
            volume_ml=estimate["volume_ml"],
            weight_g=estimate["weight_g"]
        )
        
        return {
            "volume_ml": estimate["volume_ml"],
            "weight_g": estimate["weight_g"],
            "estimation_method": "fallback"
        }
```

#### 4.4.3 WasteTypeMapper Agent

**File:** `app/agents/waste_type_mapper.py`

```python
from app.schemas.domain import WasteMaterial
from app.core.config import settings
from app.core.logging import logger
from app.services.backend_client import BackendClient
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class WasteTypeMapper:
    """
    Agent 7: Mapea características → waste_type_code del Backend Rails.
    
    Purpose: Generar código compatible con catálogo REAL del Backend
    Input: material, características (de SubtypeDetector), volumen
    Output: waste_type_code válido en Backend (Ej: "ALUMINUM_CAN", "PET_BOTTLE_500ML")
    
    PATRÓN HÍBRIDO:
    - Intenta sincronizar catálogo desde Backend en startup
    - Fallback a catálogo local si Backend no disponible
    - Refresh periódico del catálogo
    - Validación de códigos antes de enviar al Backend
    """
    
    def __init__(self):
        self.local_catalog = self._load_local_catalog()
        self.backend_catalog: Optional[List[Dict]] = None
        self.last_sync: Optional[datetime] = None
        self.sync_interval = timedelta(hours=24)
    
    def _load_local_catalog(self) -> List[Dict]:
        """Load local catalog as fallback"""
        catalog_path = Path("config/backend_waste_types.yaml")
        
        if catalog_path.exists():
            with open(catalog_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('waste_types', [])
        else:
            logger.warning("local_catalog_not_found", using="hardcoded_fallback")
            return self._get_hardcoded_catalog()
    
    def _get_hardcoded_catalog(self) -> List[Dict]:
        """
        Hardcoded fallback catalog sincronizado con Backend Rails.
        Códigos REALES de db/seeds/waste_types.rb
        """
        return [
            # Plásticos - Específicos por volumen
            {"code": "PET_BOTTLE_500ML", "category": "PLASTIC", "volume_range": [400, 600]},
            {"code": "PET_BOTTLE_1500ML", "category": "PLASTIC", "volume_range": [1300, 1700]},
            {"code": "HDPE_BOTTLE", "category": "PLASTIC"},
            {"code": "PLASTIC_OTHER", "category": "PLASTIC"},
            
            # Metales - Genéricos, distinguir por material
            {"code": "ALUMINUM_CAN", "category": "METAL", "material_type": "aluminum"},
            {"code": "STEEL_CAN", "category": "METAL", "material_type": "steel"},
            
            # Vidrio - Por color, no volumen
            {"code": "GLASS_BOTTLE_CLEAR", "category": "GLASS", "color": "clear"},
            {"code": "GLASS_BOTTLE_COLORED", "category": "GLASS", "color": "colored"},
            
            # Papel
            {"code": "PAPER_WHITE_A4", "category": "PAPER"},
            {"code": "CARDBOARD_BOX", "category": "PAPER"},
            {"code": "NEWSPAPER", "category": "PAPER"},
            
            # Orgánico
            {"code": "FOOD_WASTE", "category": "ORGANIC"},
        ]
    
    async def initialize(self):
        """
        Initialize catalog from Backend (llamar en startup).
        Patrón Híbrido: intenta Backend, fallback a local.
        """
        try:
            self.backend_catalog = await BackendClient.get_waste_types_catalog()
            self.last_sync = datetime.now()
            logger.info(
                "waste_type_catalog_synced",
                source="backend",
                count=len(self.backend_catalog),
                codes_sample=[wt['code'] for wt in self.backend_catalog[:5]]
            )
        except Exception as e:
            logger.warning(
                "backend_catalog_sync_failed",
                using="local_fallback",
                error=str(e)
            )
            self.backend_catalog = None
    
    async def refresh_if_needed(self):
        """Refresh catalog if stale"""
        if not self.last_sync or datetime.now() - self.last_sync > self.sync_interval:
            await self.initialize()
    
    def get_active_catalog(self) -> List[Dict]:
        """Get active catalog (backend if available, else local)"""
        return self.backend_catalog or self.local_catalog
    
    def get_valid_codes(self) -> List[str]:
        """Get list of valid waste_type_codes"""
        catalog = self.get_active_catalog()
        return [wt['code'] for wt in catalog]
    
    def map_to_waste_type_code(
        self,
        material: WasteMaterial,
        characteristics: Dict,
        volume_ml: float
    ) -> str:
        """
        Map material + characteristics + volume to Backend waste_type_code.
        
        Args:
            material: Classified material (PLASTIC, METAL, etc.)
            characteristics: Dict from SubtypeDetector with:
                - material_specific: "aluminum", "steel", "PET", etc.
                - container_type: "bottle", "can", "box"
                - color: "clear", "colored"
            volume_ml: Estimated volume
            
        Returns:
            waste_type_code: VALID code from Backend catalog
        """
        
        try:
            catalog = self.get_active_catalog()
            
            # Find best matching code
            candidate_code = self._find_best_match(
                material,
                characteristics,
                volume_ml,
                catalog
            )
            
            # Validate exists in catalog
            valid_codes = self.get_valid_codes()
            
            if candidate_code in valid_codes:
                logger.info(
                    "waste_type_mapped",
                    strategy="direct_match",
                    material=material.value,
                    code=candidate_code,
                    characteristics=characteristics
                )
                return candidate_code
            else:
                logger.warning(
                    "invalid_candidate_code",
                    candidate=candidate_code,
                    falling_back=True
                )
                return self._get_fallback_code(material, catalog)
            
        except Exception as e:
            logger.exception("waste_type_mapping_failed", error=str(e))
            return self._get_fallback_code(material, catalog)
    
    def _find_best_match(
        self,
        material: WasteMaterial,
        characteristics: Dict,
        volume_ml: float,
        catalog: List[Dict]
    ) -> str:
        """Find best matching waste_type_code from catalog"""
        
        if material == WasteMaterial.PLASTIC:
            return self._match_plastic(volume_ml, catalog)
        
        elif material == WasteMaterial.METAL:
            return self._match_metal(characteristics, catalog)
        
        elif material == WasteMaterial.GLASS:
            return self._match_glass(characteristics, catalog)
        
        elif material == WasteMaterial.PAPER:
            return self._match_paper(characteristics, catalog)
        
        elif material == WasteMaterial.ORGANIC:
            return "FOOD_WASTE"
        
        else:
            return "PLASTIC_OTHER"
    
    def _match_plastic(self, volume_ml: float, catalog: List[Dict]) -> str:
        """Match plastic by volume ranges"""
        for wt in catalog:
            if wt['category'] != 'PLASTIC':
                continue
            
            volume_range = wt.get('volume_range')
            if volume_range and volume_range[0] <= volume_ml <= volume_range[1]:
                return wt['code']
        
        return "HDPE_BOTTLE"  # Genérico
    
    def _match_metal(self, characteristics: Dict, catalog: List[Dict]) -> str:
        """Match metal by material type (aluminum vs steel)"""
        material_type = characteristics.get('material_specific', '').lower()
        
        for wt in catalog:
            if wt['category'] != 'METAL':
                continue
            
            if wt.get('material_type') == material_type:
                return wt['code']
        
        return "ALUMINUM_CAN"  # Default más común
    
    def _match_glass(self, characteristics: Dict, catalog: List[Dict]) -> str:
        """Match glass by color"""
        color = characteristics.get('color', '').lower()
        
        for wt in catalog:
            if wt['category'] != 'GLASS':
                continue
            
            if wt.get('color') == color:
                return wt['code']
        
        return "GLASS_BOTTLE_CLEAR"  # Default
    
    def _match_paper(self, characteristics: Dict, catalog: List[Dict]) -> str:
        """Match paper by container type"""
        container_type = characteristics.get('container_type', '').lower()
        
        if 'box' in container_type:
            return "CARDBOARD_BOX"
        else:
            return "PAPER_WHITE_A4"
    
    def _get_fallback_code(self, material: WasteMaterial, catalog: List[Dict]) -> str:
        """Get fallback code for material"""
        for wt in catalog:
            if wt['category'] == material.value:
                return wt['code']
        
        fallback_map = {
            WasteMaterial.PLASTIC: "PLASTIC_OTHER",
            WasteMaterial.METAL: "ALUMINUM_CAN",
            WasteMaterial.GLASS: "GLASS_BOTTLE_CLEAR",
            WasteMaterial.PAPER: "PAPER_WHITE_A4",
            WasteMaterial.ORGANIC: "FOOD_WASTE",
            WasteMaterial.OTHER: "PLASTIC_OTHER"
        }
        
        return fallback_map.get(material, "PLASTIC_OTHER")
```

---

#### 4.4.4 BackendIntegration Agent

**File:** `app/agents/backend_integration.py`

```python
from app.core.config import settings
from app.core.logging import logger
from app.services.backend_client import BackendClient
from app.schemas.domain import WasteMaterial
from typing import Dict, Optional
import httpx

class BackendIntegration:
    """
    Agent 10: Envía scan al Backend Rails.
    
    Purpose: Registrar scan en Backend y recibir impacto ambiental
    Input: Todos los datos del scan (waste_type_code, volume, weight, etc.)
    Output: BackendResult con impacto ambiental o error
    
    AUTENTICACIÓN (MVP):
    - Backend Rails actualmente NO requiere autenticación para scans (skip_before_action)
    - Solo requiere idempotency_key para prevenir duplicados
    - FUTURO: Service-to-Service con X-Service-Key (post-MVP)
    
    RETRY STRATEGY:
    - 3 intentos con backoff exponencial
    - Idempotency: X-Idempotency-Key header previene duplicados
    """
    
    def __init__(self):
        self.backend_client = BackendClient()
        self.max_retries = 3
    
    async def send_to_backend(
        self,
        scan_id: str,
        station_id: str,
        waste_type_code: str,
        confidence: float,
        estimated_volume_ml: float,
        estimated_weight_g: float,
        estimation_method: str,
        material: str,
        characteristics: Dict,
        tenant_id: Optional[str],
        trace_id: str,
        idempotency_key: Optional[str]
    ) -> "BackendResult":
        """
        Send scan to Backend Rails API.
        
        Endpoint: POST /api/v1/scans
        Authentication: None (MVP) - Backend usa skip_before_action :authenticate_user!
        Idempotency: X-Idempotency-Key header (REQUERIDO)
        
        NOTA: Backend Rails actualmente NO requiere X-Service-Key.
        Implementación futura post-MVP para ambiente productivo.
        """
        
        payload = {
            "scan": {
                "scan_id": scan_id,
                "station_id": station_id,
                "waste_type_code": waste_type_code,
                "confidence_score": confidence,
                "estimated_volume_ml": estimated_volume_ml,
                "estimated_weight_g": estimated_weight_g,
                "estimation_method": estimation_method,
                "agent_metadata": {
                    "material": material,
                    "characteristics": characteristics,
                    "trace_id": trace_id
                },
                "tenant_id": tenant_id
            }
        }
        
        headers = {
            "X-Trace-Id": trace_id,
            "Content-Type": "application/json"
        }
        
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        
        # NOTA: X-Service-Key comentado - Backend no lo requiere en MVP
        # Descomentar cuando Backend implemente autenticación de servicios:
        # headers["X-Service-Key"] = settings.BACKEND_SERVICE_KEY
        
        # Retry strategy
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "backend_request_attempt",
                    attempt=attempt,
                    trace_id=trace_id,
                    waste_type_code=waste_type_code
                )
                
                response = await self.backend_client.post(
                    "/api/v1/scans",
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 201:
                    data = response.json()
                    logger.info(
                        "backend_request_success",
                        trace_id=trace_id,
                        scan_id=data.get("scan_id"),
                        co2_saved_kg=data.get("environmental_impact", {}).get("co2_saved_kg")
                    )
                    
                    return BackendResult(
                        success=True,
                        environmental_impact=data.get("environmental_impact"),
                        scan_id=data.get("scan_id")
                    )
                
                elif response.status_code == 422:
                    # Validation error - NO reintentar
                    error_data = response.json()
                    logger.error(
                        "backend_validation_error",
                        trace_id=trace_id,
                        status_code=422,
                        errors=error_data.get("errors"),
                        waste_type_code=waste_type_code
                    )
                    
                    return BackendResult(
                        success=False,
                        error_code="VALIDATION_ERROR",
                        error_message=str(error_data.get("errors"))
                    )
                
                elif response.status_code == 401:
                    # Authentication error - NO reintentar
                    # NOTA: Backend actualmente NO retorna 401 para scans (no auth requerido)
                    # Este caso es para compatibilidad futura
                    logger.error(
                        "backend_authentication_error",
                        trace_id=trace_id,
                        status_code=401
                    )
                    
                    return BackendResult(
                        success=False,
                        error_code="AUTHENTICATION_ERROR",
                        error_message="Backend requires authentication (future feature)"
                    )
                
                else:
                    # Server error - Reintentar
                    logger.warning(
                        "backend_request_failed",
                        trace_id=trace_id,
                        status_code=response.status_code,
                        attempt=attempt,
                        will_retry=attempt < self.max_retries
                    )
                    
                    if attempt >= self.max_retries:
                        return BackendResult(
                            success=False,
                            error_code="BACKEND_ERROR",
                            error_message=f"Backend returned {response.status_code}"
                        )
                
            except httpx.TimeoutException as e:
                logger.warning(
                    "backend_request_timeout",
                    trace_id=trace_id,
                    attempt=attempt,
                    will_retry=attempt < self.max_retries
                )
                
                if attempt >= self.max_retries:
                    return BackendResult(
                        success=False,
                        error_code="TIMEOUT_ERROR",
                        error_message="Backend request timed out"
                    )
            
            except Exception as e:
                logger.exception(
                    "backend_request_exception",
                    trace_id=trace_id,
                    attempt=attempt,
                    error=str(e)
                )
                
                if attempt >= self.max_retries:
                    return BackendResult(
                        success=False,
                        error_code="UNKNOWN_ERROR",
                        error_message=str(e)
                    )
            
            # Exponential backoff antes de retry
            if attempt < self.max_retries:
                import asyncio
                await asyncio.sleep(2 ** attempt)
        
        # Should never reach here
        return BackendResult(
            success=False,
            error_code="MAX_RETRIES_EXCEEDED",
            error_message="Failed after all retry attempts"
        )


class BackendResult:
    """Result from Backend API call"""
    
    def __init__(
        self,
        success: bool,
        environmental_impact: Optional[Dict] = None,
        scan_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        self.success = success
        self.environmental_impact = environmental_impact
        self.scan_id = scan_id
        self.error_code = error_code
        self.error_message = error_message
```

---

### 4.5 Pipeline Orchestrator ACTUALIZADO

**File:** `app/orchestrator/pipeline.py`

```python
from app.schemas.requests import ClassifyRequest, ClassifyRequestForm
from app.schemas.responses import ClassifyResponse
from app.agents import (
    router, pre_validator, classifier, subtype_detector,
    volume_estimator, mapper, waste_type_mapper,
    feedback_coach, assembler, backend_integration
)
from app.factories.classifier_factory import ClassifierFactory
from app.services.metrics_collector import MetricsCollector
from app.core.logging import logger
import time
from typing import Union

class Pipeline:
    """
    Orchestrates sequential execution of 10 agents.
    
    V3.0 Flow:
    1. Router → Validate request + process input
    2. PreValidator → Detect waste (anti-troll)
    3. Classifier → Classify material 
    4. SubtypeDetector → Identify specific subtype
    5. VolumeEstimator → Calculate volume and weight
    6. Mapper → Material → Color
    7. WasteTypeMapper → Material+volume → waste_type_code
    8. FeedbackCoach → Generate enhanced message
    9. Assembler → Build complete response
    10. BackendIntegration → Send to Rails API
    """
    
    def __init__(self):
        self.classifier_adapter = ClassifierFactory.create()
        self.metrics = MetricsCollector()
        
        # Initialize all agents
        self.router = router.Router()
        self.pre_validator = pre_validator.PreValidator()
        self.classifier = classifier.Classifier()
        self.subtype_detector = subtype_detector.SubtypeDetector(self.classifier_adapter)
        self.volume_estimator = volume_estimator.VolumeEstimator()
        self.mapper = mapper.Mapper()
        self.waste_type_mapper = waste_type_mapper.WasteTypeMapper()
        self.feedback_coach = feedback_coach.FeedbackCoach()
        self.assembler = assembler.Assembler()
        self.backend_integration = backend_integration.BackendIntegration()
    
    async def process(self, request: Union[ClassifyRequest, ClassifyRequestForm]) -> ClassifyResponse:
        """Execute full 10-agent pipeline"""
        
        start_time = time.time()
        trace_id = str(request.trace_id)
        agents_executed = []
        
        try:
            # Step 1: Router (validate + process input)
            logger.info("pipeline_step", step="router", trace_id=trace_id)
            agents_executed.append("router")
            
            validated_request, image_data = await self.router.validate_and_process(request)
            
            # Step 2: PreValidator (detect waste)
            logger.info("pipeline_step", step="pre_validator", trace_id=trace_id)
            agents_executed.append("pre_validator")
            
            validation_result = await self.pre_validator.validate(image_data)
            
            if not validation_result.has_waste:
                raise ValidationError(
                    error_code="NO_WASTE_DETECTED",
                    message=validation_result.reason,
                    suggestion="Acerca un residuo a la cámara"
                )
            
            # Step 3: Classifier (classify material)
            logger.info("pipeline_step", step="classifier", trace_id=trace_id)
            agents_executed.append("classifier")
            
            classification = await self.classifier.classify(
                image=image_data,
                adapter=self.classifier_adapter
            )
            
            # Check confidence threshold
            if classification.confidence < 0.6:
                classification.material = WasteMaterial.OTHER
            
            if classification.confidence < 0.3:
                raise ValidationError(
                    error_code="LOW_CONFIDENCE",
                    message="Clasificación con baja confianza",
                    suggestion="Mejora iluminación o acerca más el objeto"
                )
            
            # Step 4: SubtypeDetector (detect characteristics, not codes)
            logger.info("pipeline_step", step="subtype_detector", trace_id=trace_id)
            agents_executed.append("subtype_detector")
            
            characteristics = await self.subtype_detector.detect_characteristics(
                image=image_data,
                material=classification.material
            )
            
            # Step 5: VolumeEstimator (calculate volume and weight)
            logger.info("pipeline_step", step="volume_estimator", trace_id=trace_id)
            agents_executed.append("volume_estimator")
            
            volume_result = await self.volume_estimator.estimate_volume(
                material=classification.material,
                characteristics=characteristics
            )
            
            # Step 6: Mapper (material → color)
            logger.info("pipeline_step", step="mapper", trace_id=trace_id)
            agents_executed.append("mapper")
            
            color = self.mapper.map_to_color(classification.material)
            
            # Step 7: WasteTypeMapper (características → waste_type_code del Backend)
            logger.info("pipeline_step", step="waste_type_mapper", trace_id=trace_id)
            agents_executed.append("waste_type_mapper")
            
            # Sincronizar catálogo del backend si necesario
            await self.waste_type_mapper.refresh_if_needed()
            
            waste_type_code = self.waste_type_mapper.map_to_waste_type_code(
                material=classification.material,
                characteristics=characteristics,
                volume_ml=volume_result["volume_ml"]
            )
            
            # Step 8: FeedbackCoach (generate enhanced message)
            logger.info("pipeline_step", step="feedback_coach", trace_id=trace_id)
            agents_executed.append("feedback_coach")
            
            message = await self.feedback_coach.generate_message(
                material=classification.material,
                characteristics=characteristics,
                volume_ml=volume_result["volume_ml"],
                confidence=classification.confidence
            )
            
            # Step 9: Assembler (build complete response)
            logger.info("pipeline_step", step="assembler", trace_id=trace_id)
            agents_executed.append("assembler")
            
            response = self.assembler.build_response(
                material=classification.material,
                characteristics=characteristics,  # NO subtype inventado
                confidence=classification.confidence,
                color=color,
                volume_ml=volume_result["volume_ml"],
                weight_g=volume_result["weight_g"],
                waste_type_code=waste_type_code,
                message=message,
                model_used=classification.model_used,
                model_provider=classification.model_provider,
                latency_ms=int((time.time() - start_time) * 1000),
                cost_usd=self._calculate_total_cost(),
                agents_executed=agents_executed,
                estimation_method=volume_result["estimation_method"]
            )
            
            # Step 10: BackendIntegration (send to Rails API con autenticación)
            logger.info("pipeline_step", step="backend_integration", trace_id=trace_id)
            agents_executed.append("backend_integration")
            
            backend_result = await self.backend_integration.send_to_backend(
                scan_id=validated_request.scan_id,
                station_id=validated_request.station_id,
                waste_type_code=waste_type_code,  # CÓDIGO REAL del Backend
                confidence=classification.confidence,
                estimated_volume_ml=volume_result["volume_ml"],
                estimated_weight_g=volume_result["weight_g"],
                estimation_method=volume_result["estimation_method"],
                material=classification.material.value,
                characteristics=characteristics,  # Para metadata
                tenant_id=validated_request.tenant_id,
                trace_id=trace_id,
                idempotency_key=validated_request.idempotency_key
            )
            
            # Enrich response with backend data
            if backend_result.success:
                response.environmental_impact = backend_result.environmental_impact
                response.meta.backend_integration = True
            else:
                response.meta.backend_integration = False
                logger.warning("backend_integration_failed", trace_id=trace_id)
            
            # Collect metrics
            await self.metrics.record_classification(
                trace_id=trace_id,
                model=classification.model_used,
                material=classification.material,
                characteristics=characteristics,  # NO subtype
                confidence=classification.confidence,
                volume_ml=volume_result["volume_ml"],
                latency_ms=response.meta.latency_ms,
                cost_usd=response.meta.cost_usd,
                agents_executed=agents_executed
            )
            
            return response
            
        except ValidationError:
            raise
        except TimeoutError:
            raise
        except Exception as e:
            logger.exception("pipeline_error", trace_id=trace_id, error=str(e))
            raise
    
    def _calculate_total_cost(self) -> float:
        """Calculate total cost for all agents"""
        base_cost = self.classifier_adapter.cost_per_request  # Classifier
        base_cost += 0.0002  # PreValidator (GPT-4o-mini)
        base_cost += 0.0020  # FeedbackCoach (GPT-3.5-turbo)
        # SubtypeDetector, VolumeEstimator, others are free (heuristic/lookup)
        
        return base_cost
```

---

### 4.6 Configuration ACTUALIZADA

**File:** `app/core/config.py`

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    V3.0 Updates:
    - Added volume estimation settings
    - Updated model preferences
    - Enhanced performance settings
    """
    
    # API Settings
    API_TITLE: str = "Agent Hub"
    API_VERSION: str = "3.0.0"
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Active Model (PREFERENCIA ACTUALIZADA)
    CLASSIFIER_MODEL: str = "openai-gpt4o"  # Preferido por balance costo/performance
    
    # Volume Estimation
    VOLUME_ESTIMATION_METHOD: str = "lookup"  # "lookup" | "ai"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_TIMEOUT: int = 10
    
    # Google (Gemini)
    GOOGLE_API_KEY: str | None = None
    
    # Roboflow (YA IMPLEMENTADO)
    ROBOFLOW_API_KEY: str | None = None
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "agent-hub-images"
    
    # Backend Rails API (ACTUALIZADO - Autenticación no requerida en MVP)
    BACKEND_API_URL: str = "http://localhost:3000/api/v1"
    BACKEND_TIMEOUT: int = 10
    
    # FUTURO: Descomentar cuando Backend implemente autenticación de servicios
    # BACKEND_SERVICE_KEY: str = ""  # X-Service-Key para autenticación service-to-service
    
    # Performance Settings
    MAX_IMAGE_SIZE_MB: int = 5
    PIPELINE_TIMEOUT: int = 8  # 8 seconds total
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Singleton instance
settings = Settings()
```

**File:** `config/models.yaml`

```yaml
# Model configurations V3.0
# Active model is determined by CLASSIFIER_MODEL env var

models:
  openai-gpt4o:
    provider: "openai"
    model_name: "gpt-4o"
    cost_per_image: 0.005
    latency_bytes: 600      # ms with bytes processing
    latency_url: 900        # ms with URL processing  
    max_tokens: 100
    temperature: 0.0
    timeout: 10
    enabled: true
    supports_bytes: true
    status: "✅ IMPLEMENTADO"
    description: "GPT-4o (preferido: balance costo/performance)"
    
  openai-gpt4-vision:
    provider: "openai"
    model_name: "gpt-4-vision-preview"
    cost_per_image: 0.010
    latency_bytes: 800
    latency_url: 1200
    max_tokens: 100
    temperature: 0.0
    timeout: 10
    enabled: true
    supports_bytes: true
    status: "✅ IMPLEMENTADO"
    description: "GPT-4 Vision (baseline, más costoso)"
    
  gemini-flash:
    provider: "google"
    model_name: "gemini-2.0-flash-exp"
    cost_per_image: 0.000    # Gratis en preview
    latency_bytes: 700
    latency_url: 1100
    max_tokens: 100
    temperature: 0.0
    timeout: 10
    enabled: true
    supports_bytes: true
    status: "✅ IMPLEMENTADO"
    description: "Gemini 2.0 Flash (gratis, experimental)"
    
  roboflow:
    provider: "roboflow"
    model_id: "environmental-assitant-agents/waste-classifier-louut-b9sot/1"
    cost_per_image: 0.001
    latency_bytes: 300
    latency_url: 400
    timeout: 5
    enabled: true
    supports_bytes: true
    status: "✅ IMPLEMENTADO"
    description: "Roboflow Custom (especializado, muy rápido)"

# Volume estimation settings
volume_estimation:
  default_method: "lookup"  # "lookup" | "ai"
  ai_model: "openai-gpt4o"  # For V3.1
  confidence_threshold: 0.7

# Pipeline performance targets
performance:
  target_latency_ms: 2000   # <2s with bytes processing
  max_latency_ms: 3000      # Abort after 3s
  target_cost_per_scan: 0.015
```

**File:** `config/backend_waste_types.yaml`

```yaml
# Catálogo de waste_types del Backend Rails (FALLBACK)
# Este archivo se usa cuando el Backend no está disponible
# Sincronizar con db/seeds/waste_types.rb del Backend

waste_types:
  # Plásticos - Específicos por volumen
  - code: "PET_BOTTLE_500ML"
    category: "PLASTIC"
    material_type: "PET"
    volume_range: [400, 600]
    description: "Botella PET 500ml"
    
  - code: "PET_BOTTLE_1500ML"
    category: "PLASTIC"
    material_type: "PET"
    volume_range: [1300, 1700]
    description: "Botella PET 1.5L"
    
  - code: "HDPE_BOTTLE"
    category: "PLASTIC"
    material_type: "HDPE"
    description: "Botella HDPE genérica"
    
  - code: "PLASTIC_OTHER"
    category: "PLASTIC"
    description: "Plástico genérico"
  
  # Metales - Distinguir por material
  - code: "ALUMINUM_CAN"
    category: "METAL"
    material_type: "aluminum"
    description: "Lata de aluminio"
    
  - code: "STEEL_CAN"
    category: "METAL"
    material_type: "steel"
    description: "Lata de acero"
  
  # Vidrio - Por color
  - code: "GLASS_BOTTLE_CLEAR"
    category: "GLASS"
    color: "clear"
    description: "Botella vidrio transparente"
    
  - code: "GLASS_BOTTLE_COLORED"
    category: "GLASS"
    color: "colored"
    description: "Botella vidrio de color"
  
  # Papel
  - code: "PAPER_WHITE_A4"
    category: "PAPER"
    description: "Papel blanco A4"
    
  - code: "CARDBOARD_BOX"
    category: "PAPER"
    container_type: "box"
    description: "Caja de cartón"
    
  - code: "NEWSPAPER"
    category: "PAPER"
    description: "Periódico"
  
  # Orgánico
  - code: "FOOD_WASTE"
    category: "ORGANIC"
    description: "Residuo orgánico alimentario"

# Metadata de sincronización
sync_metadata:
  last_updated: "2025-11-07"
  backend_version: "1.0"
  notes: "Sincronizado con Backend Rails db/seeds/waste_types.rb"
```

---

### 4.7 Schemas ACTUALIZADOS

**File:** `app/schemas/domain.py`

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional

class WasteMaterial(str, Enum):
    """Waste material categories"""
    PLASTIC = "PLASTIC"
    PAPER = "PAPER"
    GLASS = "GLASS"
    METAL = "METAL"
    ORGANIC = "ORGANIC"
    OTHER = "OTHER"

class BinColor(str, Enum):
    """Bin colors according to NTC 2184"""
    WHITE = "WHITE"    # Recyclables
    GREEN = "GREEN"    # Organics
    BLACK = "BLACK"    # Rejects

class ClassificationResult(BaseModel):
    """Result from classifier adapter"""
    material: WasteMaterial
    confidence: float
    model_used: str
    model_provider: str
    raw_response: Optional[str] = None
    processing_method: Optional[str] = None  # "bytes" | "url"

# ACTUALIZADO: Characteristics (NO subtypes inventados)
class WasteCharacteristics(BaseModel):
    """
    Características detectadas del residuo.
    SubtypeDetector detecta ESTAS características, NO códigos.
    """
    material_specific: Optional[str] = None  # "aluminum", "steel", "PET", "HDPE"
    container_type: Optional[str] = None     # "bottle", "can", "box", "jar"
    size: Optional[str] = None               # "small", "standard", "large"
    color: Optional[str] = None              # "clear", "colored", "white"
    
    class Config:
        json_schema_extra = {
            "example": {
                "material_specific": "aluminum",
                "container_type": "can",
                "size": "standard",
                "color": None
            }
        }

# Environmental impact from Backend
class EnvironmentalImpact(BaseModel):
    """Environmental impact data from Backend Rails"""
    recyclable: bool
    co2_saved_kg: float  # CORREGIDO: Backend usa co2_saved_kg, no carbon_footprint_avoided_kg
    recycling_efficiency: float
    environmental_score: float
    water_saved_liters: Optional[float] = None
    energy_saved_kwh: Optional[float] = None
```

**File:** `app/schemas/responses.py`

```python
from pydantic import BaseModel
from app.schemas.domain import WasteMaterial, BinColor, EnvironmentalImpact
from typing import Optional, List

class ResponseMeta(BaseModel):
    """Metadata about classification (EXPANDIDO)"""
    model_used: str
    model_provider: str
    latency_ms: int
    cost_usd: float
    validator_passed: bool
    estimation_method: str                    # NUEVO: "lookup" | "ai"
    input_format: Optional[str] = None        # NUEVO: "bytes" | "url"
    s3_upload_status: Optional[str] = None    # NUEVO: "pending" | "completed"
    agents_executed: List[str] = []           # NUEVO: Lista de agentes ejecutados
    backend_integration: Optional[bool] = None # NUEVO: ¿Backend respondió?

class ClassifyResponse(BaseModel):
    """Successful classification response (ACTUALIZADO sin subtypes inventados)"""
    material: WasteMaterial
    confidence: float
    color: BinColor
    volume_ml: float                          # NUEVO: Volumen estimado
    weight_g: float                           # NUEVO: Peso estimado
    waste_type_code: str                      # NUEVO: Código REAL del Backend Rails
    message: str
    meta: ResponseMeta
    environmental_impact: Optional[EnvironmentalImpact] = None  # NUEVO: Del Backend
    
    # Características opcionales (para debugging/metadata)
    characteristics: Optional[dict] = None    # {"material_specific": "aluminum", "container_type": "can"}

class ErrorResponse(BaseModel):
    """Error response (UNCHANGED)"""
    error_code: str
    message: str
    suggestion: str
    meta: dict | None = None
```

---

## 5) Deployment & Performance

### 5.1 Performance Targets V3.0

```yaml
Latency Targets (con bytes processing):
  p50: <1.8s
  p95: <2.0s  
  p99: <2.5s
  timeout: 3.0s

Latency por Agente:
  Router:           ~10ms
  PreValidator:     ~450ms  (GPT-4o-mini)
  Classifier:       ~600ms  (GPT-4o con bytes)
  SubtypeDetector:  ~50ms   (heuristic)
  VolumeEstimator:  ~5ms    (lookup)
  Mapper:           ~2ms    (deterministic)
  WasteTypeMapper:  ~5ms    (deterministic)
  FeedbackCoach:    ~400ms  (GPT-3.5-turbo)
  Assembler:        ~10ms   (deterministic)
  BackendIntegration: ~200ms (HTTP call)
  ══════════════════════════════════════
  TOTAL ESTIMADO:   ~1.7s  (dentro del target)

Cost Targets:
  Total per scan: <$0.015
  Breakdown:
    - PreValidator: $0.0002
    - Classifier: $0.005 (GPT-4o)
    - FeedbackCoach: $0.002
    - Others: $0.000 (heuristics)
    - Total: ~$0.007 (muy por debajo del límite)
```

### 5.2 Docker Configuration

**File:** `docker/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Environment
ENV PYTHONPATH=/app
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

---

## 6) Testing Strategy V3.0

### 6.1 Performance Tests

**File:** `tests/performance/test_pipeline_latency.py`

```python
import pytest
import asyncio
import time
from app.orchestrator.pipeline import Pipeline
from app.schemas.requests import ClassifyRequestForm

@pytest.mark.asyncio
async def test_pipeline_latency_bytes():
    """Test pipeline latency with bytes processing"""
    
    pipeline = Pipeline()
    
    # Simulate image bytes
    test_image = b"fake_image_bytes_for_testing"
    
    request = ClassifyRequestForm(
        scan_id="test-123",
        station_id="TEST-01",
        image_bytes=test_image,
        tenant_id="test",
        trace_id="test-trace",
        idempotency_key="test-key"
    )
    
    start_time = time.time()
    
    response = await pipeline.process(request)
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    # Assertions
    assert elapsed_ms < 2000  # <2s target
    assert response.meta.latency_ms < 2000
    assert len(response.meta.agents_executed) == 10
    assert response.meta.input_format == "bytes"

@pytest.mark.asyncio 
async def test_pipeline_cost():
    """Test pipeline cost is within budget"""
    
    pipeline = Pipeline()
    
    # Test with minimal request
    test_image = b"fake_image_bytes"
    request = ClassifyRequestForm(...)
    
    response = await pipeline.process(request)
    
    # Cost assertion
    assert response.meta.cost_usd < 0.015  # Budget limit
```

---

## 7) Antipatrones a Evitar V3.0

❌ **Procesar URLs cuando tienes bytes**
```python
# MAL
if isinstance(image, bytes):
    image_url = upload_to_s3(image)  # Pérdida de performance
    result = adapter.classify(image_url)
```

✅ **Usar bytes directamente**
```python
# BIEN  
if isinstance(image, bytes):
    result = adapter.classify(image)  # 60% más rápido
```

---

❌ **Ignorar fallos de agentes individuales**
```python
# MAL
volume = estimator.estimate()  # Sin manejo de errores
```

✅ **Fallback graceful por agente**
```python
# BIEN
try:
    volume = estimator.estimate()
except Exception:
    volume = get_fallback_estimate()  # Continuidad del pipeline
```

---

## 8) Métricas de Éxito Técnico V3.0

- ✅ **Pipeline de 10 agentes**: Secuencia completa funcional
- ✅ **Latencia <2s**: Con bytes processing optimizado  
- ✅ **Costo <$0.015**: Dentro del presupuesto establecido
- ✅ **3 modelos implementados**: OpenAI, Google, Roboflow
- ✅ **Datos completos a Backend**: Volumen, peso, subtipo
- ✅ **Testabilidad**: >80% coverage, mocks claros
- ✅ **Observabilidad**: Logs por agente con trace_id
- ✅ **Deploy**: Docker funcional en Railway/Render

---

**Versión:** 3.0  
**Fecha:** 2025-11-07  
**Changelog v3.0:**
- ✅ Expandido de 7 a 10 agentes especializados
- ✅ Agregado soporte bytes processing (60% mejora performance)
- ✅ Implementado Roboflow adapter (especializado)
- ✅ Agregados agentes: SubtypeDetector, VolumeEstimator, WasteTypeMapper
- ✅ Actualizada integración Backend Rails con datos completos
- ✅ Optimizada latencia objetivo de 3s a 2s
- ✅ Removido Anthropic adapter (no en MVP)
- ✅ Actualizada estructura de carpetas y schemas
- ✅ Agregado soporte multipart/form-data + JSON legacy

**Próximo paso:** Actualizar tickets de Sprint 3 en Jira con nuevos agentes
