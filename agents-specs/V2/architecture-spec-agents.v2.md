# Agent Hub – Architecture Specification V2 (Technical Design)

## ⚠️ CONTEXTO

**Este documento especifica la arquitectura técnica del Agent Hub Python.**

**Stack acordado:**
- Runtime: Python 3.11+
- Framework: FastAPI 0.104+
- Orquestación: Custom Pipeline (secuencial síncrono)
- LLM: OpenAI API, Anthropic API, Google API
- Deploy: Railway/Render (Docker)
- Storage: S3 (lectura imágenes)

**Principios arquitectónicos:**
- ✅ SOLID principles
- ✅ Adapter Pattern para modelos intercambiables
- ✅ Factory Pattern para instanciar clasificadores
- ✅ Dependency Injection
- ✅ Stateless agents
- ✅ Fail-fast validation
- ✅ Logs estructurados JSON

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
```

### 1.2 Integraciones LLM

```yaml
OpenAI: openai>=1.0.0
Anthropic: anthropic>=0.7.0
Google: google-generativeai>=0.3.0
Roboflow: roboflow>=1.1.0 (futuro)
```

### 1.3 Storage & Utils

```yaml
AWS S3: boto3>=1.28.0
Logging: structlog
Monitoring: prometheus-client (opcional)
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
┌─────────────────────────────────────────────────────┐
│              AGENT HUB (FastAPI)                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────────────────────────────────────┐    │
│  │         API Layer (FastAPI)               │    │
│  │  - POST /classify                         │    │
│  │  - GET /health                            │    │
│  │  - GET /models (list available)           │    │
│  └──────────────┬────────────────────────────┘    │
│                 │                                   │
│  ┌──────────────▼────────────────────────────┐    │
│  │      Pipeline Orchestrator                │    │
│  │  - Coordina secuencia de agentes          │    │
│  │  - Maneja errores y timeouts              │    │
│  │  - Propaga trace_id                       │    │
│  └──────────────┬────────────────────────────┘    │
│                 │                                   │
│  ┌──────────────▼────────────────────────────┐    │
│  │           Agents Layer                    │    │
│  │                                           │    │
│  │  [Router] → Valida schema                │    │
│  │      ↓                                    │    │
│  │  [PreValidator] → Detecta residuo        │    │
│  │      ↓                                    │    │
│  │  [Classifier] ← Factory → Adapter        │    │
│  │      ↓                                    │    │
│  │  [Mapper] → Material → Color             │    │
│  │      ↓                                    │    │
│  │  [FeedbackCoach] → Mensaje educativo     │    │
│  │      ↓                                    │    │
│  │  [Assembler] → Construye response        │    │
│  │                                           │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  ┌───────────────────────────────────────────┐    │
│  │        Adapters (Intercambiables)         │    │
│  │                                           │    │
│  │  ┌─────────────────────────────────┐    │    │
│  │  │  ClassifierAdapter (ABC)        │    │    │
│  │  │  - classify(image_url)          │    │    │
│  │  │  - model_name (property)        │    │    │
│  │  │  - cost_per_request (property)  │    │    │
│  │  └─────────────┬───────────────────┘    │    │
│  │                │                          │    │
│  │  ┌─────────────┼───────────────────┐    │    │
│  │  │             │                   │    │    │
│  │  ▼             ▼                   ▼    │    │
│  │  OpenAI    Anthropic           Google   │    │
│  │  Adapter     Adapter            Adapter │    │
│  │                                           │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  ┌───────────────────────────────────────────┐    │
│  │          Services Layer                   │    │
│  │  - S3Service (descargar imágenes)         │    │
│  │  - BackendClient (llamar Rails API)       │    │
│  │  - MetricsCollector (telemetría)          │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 3) Estructura de Carpetas (DDD Ligero)

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
│   │       ├── classify.py        # POST /classify
│   │       ├── health.py          # GET /health
│   │       └── models.py          # GET /models
│   │
│   ├── core/                      # Core config & utils
│   │   ├── __init__.py
│   │   ├── config.py              # Settings (Pydantic BaseSettings)
│   │   ├── logging.py             # Structured logging setup
│   │   └── exceptions.py          # Custom exceptions
│   │
│   ├── agents/                    # Domain agents (Single Responsibility)
│   │   ├── __init__.py
│   │   ├── router.py              # Valida request schema
│   │   ├── pre_validator.py       # Detecta residuo (GPT-4o-mini)
│   │   ├── classifier.py          # Clasifica con modelo activo
│   │   ├── mapper.py              # Material → Color (NTC 2184)
│   │   ├── feedback_coach.py      # Genera mensaje educativo
│   │   └── assembler.py           # Construye response final
│   │
│   ├── adapters/                  # Adapter Pattern (Open/Closed)
│   │   ├── __init__.py
│   │   ├── base.py                # ClassifierAdapter (ABC)
│   │   ├── openai_adapter.py      # GPT-4 Vision, GPT-4o
│   │   ├── anthropic_adapter.py   # Claude 3.5 Sonnet
│   │   ├── google_adapter.py      # Gemini Pro Vision (futuro)
│   │   └── roboflow_adapter.py    # Custom model (futuro)
│   │
│   ├── factories/                 # Factory Pattern
│   │   ├── __init__.py
│   │   └── classifier_factory.py  # Crea adapters según config
│   │
│   ├── orchestrator/              # Pipeline coordinator
│   │   ├── __init__.py
│   │   ├── pipeline.py            # Orquestador principal
│   │   └── pipeline_config.py     # Config de flujo
│   │
│   ├── schemas/                   # Pydantic models (Contracts)
│   │   ├── __init__.py
│   │   ├── requests.py            # ClassifyRequest
│   │   ├── responses.py           # ClassifyResponse, ErrorResponse
│   │   └── domain.py              # ClassificationResult, WasteMaterial (enums)
│   │
│   ├── services/                  # External services
│   │   ├── __init__.py
│   │   ├── s3_service.py          # Download images from S3
│   │   ├── backend_client.py      # HTTP client to Rails API
│   │   └── metrics_collector.py   # Collect telemetry
│   │
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── tracing.py             # trace_id propagation
│       ├── retry.py               # Exponential backoff
│       └── cache.py               # In-memory idempotency cache
│
├── config/                        # Configuration files
│   ├── models.yaml                # Model configurations
│   └── prompts.yaml               # Prompt templates
│
├── scripts/                       # Analysis & experimentation
│   ├── run_experiment.py          # Run model comparison
│   ├── analyze_models.py          # Generate comparison tables
│   ├── export_metrics.py          # Export logs to CSV
│   └── ground_truth_validator.py  # Validate against ground truth
│
├── tests/                         # Testing
│   ├── unit/                      # Unit tests (agents, adapters)
│   ├── integration/               # Integration tests (pipeline)
│   └── fixtures/                  # Test data & mocks
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

### 4.1 API Layer

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
    version="2.0.0",
    description="Waste classification orchestrator with interchangeable models"
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
        cost_per_request=classifier.cost_per_request
    )
```

#### 4.1.2 Classify Endpoint

**File:** `app/api/endpoints/classify.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.requests import ClassifyRequest
from app.schemas.responses import ClassifyResponse, ErrorResponse
from app.orchestrator.pipeline import Pipeline
from app.core.logging import logger
import time

router = APIRouter()

async def get_pipeline() -> Pipeline:
    """Dependency injection for Pipeline"""
    return Pipeline()

@router.post("/classify", response_model=ClassifyResponse)
async def classify_waste(
    request: ClassifyRequest,
    pipeline: Pipeline = Depends(get_pipeline)
):
    """
    Classify waste from image using active model.
    
    Process:
    1. Validate request
    2. Check idempotency
    3. Run pipeline
    4. Return response
    """
    start_time = time.time()
    
    try:
        logger.info(
            "classify_request_received",
            trace_id=str(request.trace_id),
            scan_id=str(request.scan_id)
        )
        
        # Execute pipeline
        result = await pipeline.process(request)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "classify_request_completed",
            trace_id=str(request.trace_id),
            material=result.material,
            confidence=result.confidence,
            model_used=result.meta.model_used,
            latency_ms=elapsed_ms
        )
        
        return result
        
    except ValidationError as e:
        logger.warning(
            "classify_request_rejected",
            trace_id=str(request.trace_id),
            reason=e.error_code,
            latency_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=400, detail=e.to_dict())
        
    except TimeoutError as e:
        logger.error(
            "classify_request_timeout",
            trace_id=str(request.trace_id),
            latency_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=504, detail="Classification timeout")
        
    except Exception as e:
        logger.exception(
            "classify_request_failed",
            trace_id=str(request.trace_id),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

### 4.2 Adapters Layer (Intercambiable)

#### 4.2.1 Base Adapter (Interface)

**File:** `app/adapters/base.py`

```python
from abc import ABC, abstractmethod
from app.schemas.domain import ClassificationResult

class ClassifierAdapter(ABC):
    """
    Abstract base class for all classification models.
    
    Implements Adapter Pattern to allow interchangeable models
    without changing business logic.
    
    All adapters MUST implement:
    - classify(image_url: str) -> ClassificationResult
    - model_name property
    - cost_per_request property
    """
    
    @abstractmethod
    async def classify(self, image_url: str) -> ClassificationResult:
        """
        Classify waste from image URL.
        
        Args:
            image_url: S3 presigned URL or public URL
            
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
        Example: "openai/gpt-4-vision-preview"
        """
        pass
    
    @property
    @abstractmethod
    def model_provider(self) -> str:
        """
        Provider name.
        
        Example: "openai", "anthropic", "google"
        """
        pass
    
    @property
    @abstractmethod
    def cost_per_request(self) -> float:
        """
        Cost in USD per classification request.
        
        Used for telemetry and cost analysis.
        """
        pass
    
    @abstractmethod
    async def _prepare_prompt(self) -> str:
        """
        Generate classification prompt.
        
        Can be customized per model while keeping interface consistent.
        """
        pass
```

#### 4.2.2 OpenAI Adapter

**File:** `app/adapters/openai_adapter.py`

```python
from openai import AsyncOpenAI
from app.adapters.base import ClassifierAdapter
from app.schemas.domain import ClassificationResult, WasteMaterial
from app.core.config import settings
from app.core.logging import logger
import asyncio

class OpenAIClassifierAdapter(ClassifierAdapter):
    """
    OpenAI GPT-4 Vision / GPT-4o adapter.
    
    Supports:
    - gpt-4-vision-preview ($0.010/image)
    - gpt-4o ($0.005/image)
    """
    
    def __init__(self, model: str = "gpt-4-vision-preview"):
        self.model = model
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._cost_map = {
            "gpt-4-vision-preview": 0.010,
            "gpt-4o": 0.005
        }
    
    async def classify(self, image_url: str) -> ClassificationResult:
        """Classify using OpenAI Vision API"""
        
        prompt = await self._prepare_prompt()
        
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": image_url}}
                            ]
                        }
                    ],
                    max_tokens=100,
                    temperature=0.0  # Deterministic
                ),
                timeout=10.0  # 10 second timeout
            )
            
            # Parse response
            content = response.choices[0].message.content.strip().upper()
            material = self._parse_material(content)
            
            # OpenAI doesn't provide confidence, use heuristic
            confidence = self._estimate_confidence(content)
            
            return ClassificationResult(
                material=material,
                confidence=confidence,
                model_used=self.model_name,
                model_provider=self.model_provider,
                raw_response=content
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
        if "PLASTIC" in content or "PLÁSTICO" in content:
            return WasteMaterial.PLASTIC
        elif "PAPER" in content or "PAPEL" in content:
            return WasteMaterial.PAPER
        elif "GLASS" in content or "VIDRIO" in content:
            return WasteMaterial.GLASS
        elif "METAL" in content:
            return WasteMaterial.METAL
        elif "ORGANIC" in content or "ORGÁNICO" in content:
            return WasteMaterial.ORGANIC
        else:
            return WasteMaterial.OTHER
    
    def _estimate_confidence(self, content: str) -> float:
        """
        Estimate confidence heuristically.
        
        OpenAI doesn't provide logprobs in Vision API,
        so we use simple heuristics.
        """
        content = content.strip().upper()
        
        # If response is single word (clean), high confidence
        if len(content.split()) == 1:
            return 0.85
        
        # If response has explanations, lower confidence
        return 0.70
    
    @property
    def model_name(self) -> str:
        return f"openai/{self.model}"
    
    @property
    def model_provider(self) -> str:
        return "openai"
    
    @property
    def cost_per_request(self) -> float:
        return self._cost_map.get(self.model, 0.010)
```

#### 4.2.3 Anthropic Adapter

**File:** `app/adapters/anthropic_adapter.py`

```python
from anthropic import AsyncAnthropic
from app.adapters.base import ClassifierAdapter
from app.schemas.domain import ClassificationResult, WasteMaterial
from app.core.config import settings
from app.services.s3_service import S3Service
import asyncio
import base64

class AnthropicClassifierAdapter(ClassifierAdapter):
    """
    Anthropic Claude 3.5 Sonnet adapter.
    
    Cost: $0.008/image (input: $3/MTok, output: $15/MTok)
    Note: Claude requires base64-encoded images, not URLs.
    """
    
    def __init__(self):
        self.model = "claude-3-5-sonnet-20241022"
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.s3_service = S3Service()
    
    async def classify(self, image_url: str) -> ClassificationResult:
        """Classify using Claude Vision"""
        
        # Download image and encode to base64
        image_data = await self.s3_service.download_and_encode(image_url)
        
        prompt = await self._prepare_prompt()
        
        try:
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model=self.model,
                    max_tokens=100,
                    temperature=0.0,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                ),
                timeout=10.0
            )
            
            # Parse response
            content = response.content[0].text.strip().upper()
            material = self._parse_material(content)
            confidence = 0.90  # Claude typically high confidence
            
            return ClassificationResult(
                material=material,
                confidence=confidence,
                model_used=self.model_name,
                model_provider=self.model_provider,
                raw_response=content
            )
            
        except asyncio.TimeoutError:
            raise TimeoutError("Claude request timeout")
        except Exception as e:
            raise ClassificationError(f"Claude classification failed: {str(e)}")
    
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
            # Fuzzy matching...
            if "PLASTIC" in content:
                return WasteMaterial.PLASTIC
            # ... (same as OpenAI)
            return WasteMaterial.OTHER
    
    @property
    def model_name(self) -> str:
        return f"anthropic/{self.model}"
    
    @property
    def model_provider(self) -> str:
        return "anthropic"
    
    @property
    def cost_per_request(self) -> float:
        return 0.008  # Approximate
```

---

### 4.3 Factory Pattern

**File:** `app/factories/classifier_factory.py`

```python
from app.adapters.base import ClassifierAdapter
from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.adapters.anthropic_adapter import AnthropicClassifierAdapter
from app.core.config import settings
from app.core.logging import logger

class ClassifierFactory:
    """
    Factory for creating classifier adapters.
    
    Reads active model from settings and instantiates
    appropriate adapter.
    
    Usage:
        classifier = ClassifierFactory.create()
        result = await classifier.classify(image_url)
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
            case "openai-gpt4":
                logger.info("classifier_created", model="openai/gpt-4-vision-preview")
                return OpenAIClassifierAdapter("gpt-4-vision-preview")
            
            case "openai-gpt4o":
                logger.info("classifier_created", model="openai/gpt-4o")
                return OpenAIClassifierAdapter("gpt-4o")
            
            case "claude":
                logger.info("classifier_created", model="anthropic/claude-3.5-sonnet")
                return AnthropicClassifierAdapter()
            
            case "gemini":
                # TODO: Implement GeminiAdapter
                raise NotImplementedError("Gemini adapter not yet implemented")
            
            case "roboflow":
                # TODO: Implement RoboflowAdapter
                raise NotImplementedError("Roboflow adapter not yet implemented")
            
            case _:
                raise ValueError(
                    f"Unknown classifier model: {model}. "
                    f"Supported: openai-gpt4, openai-gpt4o, claude, gemini, roboflow"
                )
    
    @staticmethod
    def list_available() -> list[str]:
        """List all available models"""
        return ["openai-gpt4", "openai-gpt4o", "claude", "gemini", "roboflow"]
```

---

### 4.4 Pipeline Orchestrator

**File:** `app/orchestrator/pipeline.py`

```python
from app.schemas.requests import ClassifyRequest
from app.schemas.responses import ClassifyResponse
from app.agents import (
    router, pre_validator, classifier, 
    mapper, feedback_coach, assembler
)
from app.factories.classifier_factory import ClassifierFactory
from app.services.metrics_collector import MetricsCollector
from app.core.logging import logger
import time

class Pipeline:
    """
    Orchestrates sequential execution of agents.
    
    Flow:
    1. Router → Validate request
    2. PreValidator → Detect waste
    3. Classifier → Classify material
    4. Mapper → Material → Color
    5. FeedbackCoach → Generate message
    6. Assembler → Build response
    
    Handles:
    - Error propagation
    - Timeout management
    - Telemetry collection
    - trace_id propagation
    """
    
    def __init__(self):
        self.classifier_adapter = ClassifierFactory.create()
        self.metrics = MetricsCollector()
    
    async def process(self, request: ClassifyRequest) -> ClassifyResponse:
        """Execute full pipeline"""
        
        start_time = time.time()
        trace_id = str(request.trace_id)
        
        try:
            # Step 1: Router (validate)
            logger.info("pipeline_step", step="router", trace_id=trace_id)
            router.validate(request)
            
            # Step 2: PreValidator (detect waste)
            logger.info("pipeline_step", step="pre_validator", trace_id=trace_id)
            validation_result = await pre_validator.validate(request.image_url)
            
            if not validation_result.has_waste:
                raise ValidationError(
                    error_code="NO_WASTE_DETECTED",
                    message=validation_result.reason,
                    suggestion="Acerca un residuo a la cámara"
                )
            
            # Step 3: Classifier (classify material)
            logger.info("pipeline_step", step="classifier", trace_id=trace_id)
            classification = await classifier.classify(
                image_url=request.image_url,
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
            
            # Step 4: Mapper (material → color)
            logger.info("pipeline_step", step="mapper", trace_id=trace_id)
            color = mapper.map_to_color(classification.material)
            
            # Step 5: FeedbackCoach (generate message)
            logger.info("pipeline_step", step="feedback_coach", trace_id=trace_id)
            message = await feedback_coach.generate_message(
                material=classification.material,
                confidence=classification.confidence
            )
            
            # Step 6: Assembler (build response)
            logger.info("pipeline_step", step="assembler", trace_id=trace_id)
            response = assembler.build_response(
                material=classification.material,
                confidence=classification.confidence,
                color=color,
                message=message,
                model_used=classification.model_used,
                model_provider=classification.model_provider,
                latency_ms=int((time.time() - start_time) * 1000),
                cost_usd=self.classifier_adapter.cost_per_request + 0.0022  # +validator+coach
            )
            
            # Collect metrics
            await self.metrics.record_classification(
                trace_id=trace_id,
                model=classification.model_used,
                material=classification.material,
                confidence=classification.confidence,
                latency_ms=response.meta.latency_ms,
                cost_usd=response.meta.cost_usd
            )
            
            return response
            
        except ValidationError:
            raise
        except TimeoutError:
            raise
        except Exception as e:
            logger.exception("pipeline_error", trace_id=trace_id, error=str(e))
            raise
```

---

### 4.5 Configuration

**File:** `app/core/config.py`

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Priority:
    1. Environment variables
    2. .env file
    3. Default values
    """
    
    # API Settings
    API_TITLE: str = "Agent Hub"
    API_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Active Model (CRITICAL - cambiar sin redeploy)
    CLASSIFIER_MODEL: str = "openai-gpt4"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_TIMEOUT: int = 10
    
    # Anthropic
    ANTHROPIC_API_KEY: str | None = None
    
    # Google
    GOOGLE_API_KEY: str | None = None
    
    # Roboflow
    ROBOFLOW_API_KEY: str | None = None
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "agent-hub-images"
    
    # Backend Rails API
    BACKEND_API_URL: str = "http://localhost:3000/api/v1"
    BACKEND_TIMEOUT: int = 3
    
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
# Model configurations
# Active model is determined by CLASSIFIER_MODEL env var

models:
  openai-gpt4:
    provider: "openai"
    model_name: "gpt-4-vision-preview"
    cost_per_image: 0.010
    max_tokens: 100
    temperature: 0.0
    timeout: 10
    enabled: true
    description: "GPT-4 Vision (baseline, alta accuracy)"
    
  openai-gpt4o:
    provider: "openai"
    model_name: "gpt-4o"
    cost_per_image: 0.005
    max_tokens: 100
    temperature: 0.0
    timeout: 10
    enabled: true
    description: "GPT-4o (económico, rápido)"
    
  claude:
    provider: "anthropic"
    model_name: "claude-3-5-sonnet-20241022"
    cost_per_image: 0.008
    max_tokens: 100
    temperature: 0.0
    timeout: 10
    enabled: true
    description: "Claude 3.5 Sonnet (mejor razonamiento contextual)"
    
  gemini:
    provider: "google"
    model_name: "gemini-pro-vision"
    cost_per_image: 0.002
    max_tokens: 100
    temperature: 0.0
    timeout: 10
    enabled: false
    description: "Gemini Pro (muy económico) - Fase 2"
    
  roboflow:
    provider: "roboflow"
    model_id: "waste-classifier-v1"
    cost_per_image: 0.001
    timeout: 5
    enabled: false
    description: "Roboflow Custom (especializado) - Fase 2"

# Common classification prompt
classification_prompt: |
  Clasifica el residuo en esta imagen en EXACTAMENTE una de estas categorías:
  
  - PLASTIC: Botellas plásticas, envases, bolsas
  - PAPER: Papel, cartón, periódicos
  - GLASS: Botellas de vidrio, frascos
  - METAL: Latas de aluminio o acero
  - ORGANIC: Restos de comida, material vegetal
  - OTHER: Si no encaja claramente en las anteriores
  
  Responde SOLO con el nombre de la categoría en MAYÚSCULAS.
  Si tienes dudas, usa OTHER.

# Validation thresholds
thresholds:
  confidence_min: 0.3   # Reject below this
  confidence_low: 0.6   # Map to OTHER below this
  confidence_high: 0.85  # High confidence
```

---

## 5) Schemas & Contracts

**File:** `app/schemas/domain.py`

```python
from enum import Enum
from pydantic import BaseModel

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
    raw_response: str | None = None
```

**File:** `app/schemas/responses.py`

```python
from pydantic import BaseModel
from app.schemas.domain import WasteMaterial, BinColor

class ResponseMeta(BaseModel):
    """Metadata about classification"""
    model_used: str
    model_provider: str
    latency_ms: int
    cost_usd: float
    validator_passed: bool

class ClassifyResponse(BaseModel):
    """Successful classification response"""
    material: WasteMaterial
    confidence: float
    color: BinColor
    message: str
    meta: ResponseMeta

class ErrorResponse(BaseModel):
    """Error response"""
    error_code: str
    message: str
    suggestion: str
    meta: dict | None = None
```

---

## 6) Scripts de Análisis

**File:** `scripts/run_experiment.py`

```python
"""
Run model comparison experiment.

Usage:
    python scripts/run_experiment.py --ground-truth data/ground_truth.csv --model openai-gpt4
    python scripts/run_experiment.py --ground-truth data/ground_truth.csv --model claude
"""

import asyncio
import csv
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.factories.classifier_factory import ClassifierFactory
from app.core.logging import setup_logging, logger
import time

async def main(ground_truth_file: str, model: str):
    """Run experiment with specified model"""
    
    setup_logging()
    logger.info("experiment_started", model=model)
    
    # Load ground truth
    with open(ground_truth_file) as f:
        ground_truth = list(csv.DictReader(f))
    
    # Create classifier
    classifier = ClassifierFactory.create(model_override=model)
    
    results = []
    
    for idx, row in enumerate(ground_truth):
        image_url = row['image_url']
        true_label = row['true_label']
        
        logger.info("classifying", idx=idx+1, total=len(ground_truth))
        
        start = time.time()
        try:
            result = await classifier.classify(image_url)
            latency_ms = int((time.time() - start) * 1000)
            
            correct = (result.material == true_label)
            
            results.append({
                'image_id': row['image_id'],
                'true_label': true_label,
                'predicted_label': result.material,
                'confidence': result.confidence,
                'correct': correct,
                'latency_ms': latency_ms,
                'model': classifier.model_name,
                'cost_usd': classifier.cost_per_request
            })
            
            logger.info(
                "classification_result",
                correct=correct,
                predicted=result.material,
                confidence=result.confidence
            )
            
        except Exception as e:
            logger.exception("classification_failed", error=str(e))
            results.append({
                'image_id': row['image_id'],
                'true_label': true_label,
                'predicted_label': 'ERROR',
                'confidence': 0.0,
                'correct': False,
                'latency_ms': 0,
                'model': classifier.model_name,
                'cost_usd': 0.0,
                'error': str(e)
            })
    
    # Save results
    output_file = f"results_{model}_{int(time.time())}.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    logger.info("experiment_completed", output=output_file)
    
    # Print summary
    accuracy = sum(r['correct'] for r in results) / len(results)
    avg_latency = sum(r['latency_ms'] for r in results) / len(results)
    total_cost = sum(r['cost_usd'] for r in results)
    
    print(f"\nResults for {classifier.model_name}:")
    print(f"  Accuracy: {accuracy:.2%}")
    print(f"  Avg Latency: {avg_latency:.0f}ms")
    print(f"  Total Cost: ${total_cost:.4f}")
    print(f"  Results saved to: {output_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    
    asyncio.run(main(args.ground_truth, args.model))
```

---

## 7) Deployment

**File:** `docker/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File:** `.env.example`

```bash
# API Settings
DEBUG=false
CORS_ORIGINS=["http://localhost:3000"]

# CRITICAL: Active model (change to switch)
CLASSIFIER_MODEL=openai-gpt4  # Options: openai-gpt4, openai-gpt4o, claude, gemini, roboflow

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
ROBOFLOW_API_KEY=...

# AWS S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=agent-hub-images

# Backend Rails
BACKEND_API_URL=https://api.example.com/api/v1

# Logging
LOG_LEVEL=INFO
```

---

## 8) Testing Strategy

### 8.1 Unit Tests

**File:** `tests/unit/test_adapters.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.adapters.openai_adapter import OpenAIClassifierAdapter

@pytest.mark.asyncio
async def test_openai_adapter_classify():
    """Test OpenAI adapter classification"""
    
    adapter = OpenAIClassifierAdapter("gpt-4-vision-preview")
    
    # Mock OpenAI client
    adapter.client.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[Mock(message=Mock(content="PLASTIC"))]
        )
    )
    
    result = await adapter.classify("https://example.com/image.jpg")
    
    assert result.material == "PLASTIC"
    assert result.model_used == "openai/gpt-4-vision-preview"
    assert result.confidence > 0.0

@pytest.mark.asyncio
async def test_classifier_factory():
    """Test factory creates correct adapter"""
    from app.factories.classifier_factory import ClassifierFactory
    
    adapter = ClassifierFactory.create("openai-gpt4")
    assert adapter.model_provider == "openai"
    
    adapter = ClassifierFactory.create("claude")
    assert adapter.model_provider == "anthropic"
```

### 8.2 Integration Tests

**File:** `tests/integration/test_pipeline.py`

```python
@pytest.mark.asyncio
async def test_full_pipeline():
    """Test complete pipeline with mocked LLM"""
    
    pipeline = Pipeline()
    
    request = ClassifyRequest(
        scan_id=uuid4(),
        station_id="TEST-01",
        image_url="https://test.com/plastic_bottle.jpg",
        tenant_id="test",
        trace_id=uuid4(),
        idempotency_key=uuid4()
    )
    
    # Mock classifier
    pipeline.classifier_adapter.classify = AsyncMock(
        return_value=ClassificationResult(
            material="PLASTIC",
            confidence=0.89,
            model_used="mock/test",
            model_provider="mock"
        )
    )
    
    response = await pipeline.process(request)
    
    assert response.material == "PLASTIC"
    assert response.color == "WHITE"
    assert response.confidence == 0.89
```

---

## 9) Antipatrones a Evitar

❌ **Hardcodear modelo en código de negocio**
```python
# MAL
classifier = OpenAIClassifierAdapter()  # Hardcoded
```

✅ **Usar Factory con configuración**
```python
# BIEN
classifier = ClassifierFactory.create()  # Reads from settings
```

---

❌ **Lógica de negocio en adapter**
```python
# MAL
class OpenAIAdapter:
    def classify(self, image_url):
        result = self.call_api(image_url)
        # ❌ Business logic in adapter
        if result.material == "PLASTIC":
            color = "WHITE"
```

✅ **Separar responsabilidades**
```python
# BIEN
class Mapper:  # Dedicated agent for business logic
    def map_to_color(self, material):
        return COLOR_MAP[material]
```

---

❌ **Ignorar trace_id**
```python
# MAL
logger.info("classification_done")  # No trace_id
```

✅ **Propagar trace_id**
```python
# BIEN
logger.info("classification_done", trace_id=trace_id)
```

---

## 10) Métricas de Éxito Técnico

- ✅ **Adapter Pattern**: Switching de modelos sin cambiar código
- ✅ **SOLID**: Single Responsibility en cada agente
- ✅ **Testabilidad**: >70% coverage, mocks claros
- ✅ **Performance**: p95 latency <2s
- ✅ **Observabilidad**: Logs estructurados con trace_id
- ✅ **Deployment**: Docker funcional en Railway/Render

---

**Versión:** 2.0  
**Fecha:** 2025-10-24  
**Próximo paso:** Crear tickets de desarrollo en Jira (Sprint 3)
