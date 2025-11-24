# Agent Hub - AI Orchestrator V4

Waste classification system with interchangeable AI models (GPT-4, Claude, Gemini) optimized for edge + backend hybrid architecture.

> **Latest:** V4.0.0 introduces 70% faster classification, 65% cheaper costs, and unified MaterialClassifier. See [CHANGELOG.md](CHANGELOG.md) for details.

## 🎯 Features

- **Complete AI Pipeline**: 10-agent orchestration (PreValidator, Classifier, SubtypeDetector, VolumeEstimator, WasteTypeMapper, FeedbackCoach, etc.)
- **Interchangeable Models**: Switch between GPT-4o, Gemini 2.0 Flash, Roboflow Custom without code changes
- **Bytes Processing**: 60% faster latency using image bytes vs URLs (async S3 upload in background)
- **Physical Estimation**: Volume and weight estimation for environmental impact calculations
- **Backend Integration**: Full data sync with Rails API (waste_type_code, volume, weight, characteristics)
- **DDD Architecture**: Clean, maintainable, extensible codebase
- **Fast**: <3s p95 latency end-to-end (complete pipeline with 10 agents)
- **Cost-Effective**: Optimized for <$0.025 per scan
- **Observable**: Structured JSON logging with trace_id and per-agent metrics
- **Production-Ready**: Docker + Railway deployment

## 🏗️ Stack

- **Runtime**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **AI Providers**: OpenAI, Google Gemini, Roboflow
- **Deployment**: Docker + Railway
- **Logging**: structlog (JSON)

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- Railway CLI (for deployment)
- OpenAI API Key (required)
- Roboflow API Key (optional)

## 🚀 Quick Start

### Local Development (Python)

```bash
# 1. Clone repository
git clone <repository-url>
cd agent-hub

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run server
uvicorn app.main:app --reload

# 6. Open browser
# http://localhost:8000/docs
```

### Local Development (Docker) **⭐ Recommended**

Docker simplifies the workflow to just 3 essential commands (vs 10+ commands with venv):

```bash
# 1. Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# 2. Start services (with hot-reload)
docker compose -f docker/docker-compose.yml up -d

# 3. View logs
docker compose -f docker/docker-compose.yml logs -f

# 4. Open browser
# http://localhost:8000/docs

# Stop services
docker compose -f docker/docker-compose.yml down
```

**Features:**
- ✅ Hot-reload enabled (code changes apply automatically)
- ✅ Volume mounts for `app/` and `config/` directories
- ✅ Health checks configured
- ✅ No need to manage Python virtual environments

## 🧪 Testing

### With Docker (Recommended)

```bash
# Run all tests inside container
docker compose -f docker/docker-compose.yml exec agent-hub pytest tests/ -v

# Run specific test file
docker compose -f docker/docker-compose.yml exec agent-hub pytest tests/unit/test_health.py -v

# Run with coverage
docker compose -f docker/docker-compose.yml exec agent-hub pytest --cov=app --cov-report=html
```

### With Python (Alternative)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_health.py

# Run with verbose output
pytest -v
```

## 🎨 Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint
pylint app/

# Type check
mypy app/
```

## 🚂 Deploy to Railway

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Link project
railway link

# 4. Set environment variables in Railway dashboard
# OPENAI_API_KEY
# CLASSIFIER_MODEL
# ... (see .env.example)

# 5. Deploy
railway up

# 6. Check deployment
railway logs
```

## 📚 Documentation

- **API Docs**: `/docs` (Swagger UI)
- **ReDoc**: `/redoc` (Alternative docs)
- **Health Check**: `/health`
- **Project Spec V3**: `agents-specs/V3/project-spec-agents.v3.md`
- **Architecture Spec V2**: `agents-specs/V2/architecture-spec-agents.v2.md`

## 🏛️ Architecture

### V4 Architecture (Hybrid Edge + Backend) 🆕

**Major improvements in V4:**
- **70% faster:** 3-5s → 0.8-1.2s latency
- **65% cheaper:** $0.031 → $0.011 per request
- **Unified classification:** 3 agents merged into MaterialClassifier
- **Per-field confidences:** Granular accuracy tracking
- **Claude Sonnet 4.5:** Full Anthropic support

#### Core Pipeline V4 (5-6 Agents)

1. **Router** → Request validation
2. **PreValidator V4** → Two-layer validation
   - Layer 1: Technical (format, size, dimensions)
   - Layer 2: Roboflow Object Detection API ($0.001 vs $0.010 GPT-4o-mini)
3. **MaterialClassifier V4** → **UNIFIED** classification in ONE LLM call
   - Material base (PLASTIC, PAPER, GLASS, METAL, etc.)
   - Subtype (PET, HDPE, recycling codes)
   - Physical condition (CLEAN, CONTAMINATED, DAMAGED)
   - Volume estimation (OCR + estimation, in liters)
   - Recyclability assessment
   - **Per-field confidence scores** for partial success support
4. **WasteTypeMapper** → Material+volume → waste_type_code *(pending)*
5. **Mapper** → Material → Color NTC 2184 *(pending)*
6. **Assembler** → Response construction *(pending)*

#### Adapter Support V4

- **OpenAI GPT-4 Vision** (gpt-4o, gpt-4-turbo): ✅ Full support
- **Anthropic Claude** (claude-sonnet-4-5, claude-3-5-sonnet-20241022): ✅ Full support 🆕
- **Google Gemini** (gemini-1.5-pro-vision): ✅ Full support
- **Roboflow** (object detection): ✅ PreValidator only

#### Key V4 Features

**Unified Classification Schema:**
```python
@dataclass
class MaterialClassificationResult:
    material: MaterialField(type, confidence)
    subtype: SubtypeField(value, recycling_code, confidence)
    condition: ConditionField(value, confidence)
    volume: VolumeField(liters, source, confidence)
    recyclability: RecyclabilityField(value, confidence)
    reasoning: str  # Model's explanation
    partial_success: bool  # True if some fields have low confidence
```

**Partial Success Logic:**
```python
if material.confidence < 0.7:
    raise ValueError("Material confidence too low")

if subtype.confidence < 0.6:
    subtype = None  # Continue with generic material

if volume.confidence < 0.5:
    volume = None  # Continue without volume
```

**Documentation:**
- [Architecture Spec V4](agents-specs/V4/architecture-spec-agents_v4.md) - Complete V4 architecture
- [Migration Guide V3→V4](docs/MIGRATION_V3_TO_V4.md) - How to migrate from V3
- [CHANGELOG](CHANGELOG.md) - V4.0.0 release notes

---

### 🎯 Multi-Model Consensus Classification (V4.1) 🆕

**Ensemble learning for improved accuracy in uncertain cases**

**Problem:** 30% of classifications show confidence <0.70, indicating model uncertainty in:
- Transparent objects (glass vs plastic)
- Oxidized materials (metal vs reject)
- Partially visible objects
- Poor lighting conditions

**Solution:** Multi-model consensus system that uses 3 models (primary, secondary, tiebreaker) to achieve consensus.

#### How It Works

```
Input Image
    ↓
Primary Model (GPT-4o)
    ↓
Confidence ≥ 0.70?
    ├─→ YES (70%) → [Fast Path] → Return immediately
    └─→ NO (30%) → [Trigger Consensus]
          ↓
    Secondary Model (Gemini)
          ↓
    Both Agree?
        ├─→ YES → Agreement Boost (+10% bonus)
        └─→ NO → Confidence-Based or Tie-Breaker
```

#### Consensus Strategies

1. **Agreement Boost** (20% of consensus cases)
   - Both models agree on material type
   - Weighted average: `(primary * 0.6) + (secondary * 0.4) + 0.10`
   - Example: PLASTIC (0.65) + PLASTIC (0.68) → **0.762** ✅

2. **Confidence-Based** (8% of consensus cases)
   - Models disagree, but one has >0.15 higher confidence
   - Winner gets selected with 10% penalty
   - Example: PLASTIC (0.65) vs METAL (0.45) → **PLASTIC (0.585)** ✅

3. **Tie-Breaker Vote** (2% of consensus cases)
   - Marginal difference (<0.15), 3rd model decides
   - Majority vote (2 of 3 wins)
   - Example: PLASTIC (0.60) + METAL (0.58) + PLASTIC (0.62) → **PLASTIC (0.517)** ✅

4. **Conservative Fallback** (0.5% of consensus cases)
   - All 3 models disagree → Return **OTHER** with confidence 0.50

#### Performance Metrics

| Metric | Single Model (v4.0) | Consensus (v4.1) | Improvement |
|--------|---------------------|------------------|-------------|
| **Accuracy** | 85% | 89% | **+4pp** ✅ |
| **Cost** | $0.010/scan | $0.0103/scan | +3% |
| **Latency P95** | 800ms | 1200ms | +50% |
| **Fast Path** | N/A | 70% | Optimized ✅ |

#### Configuration

**Enable consensus mode:**
```bash
# .env configuration
CLASSIFIER_MODEL=consensus                    # Enable consensus
UNCERTAINTY_THRESHOLD=0.70                    # Trigger threshold (default)
CONSENSUS_PRIMARY_MODEL=openai-gpt4o          # Primary model
CONSENSUS_SECONDARY_MODEL=gemini              # Secondary model
CONSENSUS_TIEBREAKER_MODEL=roboflow           # Tiebreaker model
```

**models.yaml configuration:**
```yaml
consensus:
  enabled: true
  uncertainty_threshold: 0.70
  primary:
    model: openai-gpt4o
    weight: 0.6
  secondary:
    model: gemini
    weight: 0.4
  tiebreaker:
    model: roboflow
  strategies:
    agreement_boost:
      confidence_bonus: 0.10
    confidence_based:
      confidence_diff_threshold: 0.15
      penalty_factor: 0.90
    tie_breaker:
      penalty_factor: 0.85
```

#### API Response with Consensus Metadata

```json
{
  "material": "PLASTIC",
  "confidence": 0.762,
  "waste_type_code": "PLW001",
  "color": "WHITE",
  "message": "¡Excelente! El plástico va en el contenedor BLANCO.",
  "meta": {
    "consensus_strategy": "agreement_boost",
    "consensus_triggered": true,
    "models_consulted": 2,
    "primary_confidence": 0.65,
    "secondary_confidence": 0.68,
    "primary_model": "gpt-4o",
    "secondary_model": "gemini-2.5-flash"
  }
}
```

#### Testing & Validation

**Run unit tests:**
```bash
pytest tests/unit/test_consensus_classifier.py -v
# 8 tests, >85% coverage ✅
```

**Run validation script:**
```bash
python scripts/validate_consensus.py --cases 20 --verbose
# Compares single-model vs consensus accuracy
```

#### Documentation

- [Consensus Architecture Deep-Dive](docs/CONSENSUS_ARCHITECTURE.md) - Technical details
- [Architecture Spec V4](docs/architecture-spec-agents.v4.md) - System architecture
- [Project Spec V4](docs/project-spec-agents.v4.md) - Requirements & acceptance criteria

#### Trade-offs

**Pros:**
- ✅ +4pp accuracy improvement (85% → 89%)
- ✅ Minimal cost increase (+3%)
- ✅ Fast path optimization (70% no extra cost)
- ✅ Backward compatible

**Cons:**
- ⚠️ +50% latency in consensus path (still <2s target)
- ⚠️ More complex monitoring needed
- ⚠️ 3 API keys required (OpenAI, Google, Roboflow)

**Recommendation:** Enable consensus for production deployments where accuracy is critical. Keep single-model for development/testing.

---

### V3 Architecture (Legacy - Deprecated)

#### Complete AI Pipeline (10 Agents)
1. **Router** → Request validation
2. **PreValidator** → Anti-troll detection (GPT-4o-mini)
3. **Classifier** → Material classification (GPT-4o/Gemini/Roboflow)
4. **SubtypeDetector** → Specific characteristics (PET, aluminum, size, color)
5. **VolumeEstimator** → Volume and weight estimation (lookup table)
6. **Mapper** → Material → Color (NTC 2184)
7. **WasteTypeMapper** → Characteristics → Backend waste_type_code
8. **FeedbackCoach** → Educational message generation (GPT-3.5-turbo)
9. **Assembler** → Response construction
10. **BackendIntegration** → Data sync with Rails API

### Project Structure
```
agent-hub/
├── app/
│   ├── api/          # FastAPI endpoints
│   ├── core/         # Configuration & logging
│   ├── agents/       # 10 domain agents (complete pipeline)
│   ├── adapters/     # Model adapters (bytes | str support)
│   ├── factories/    # Object creation (Factory Pattern)
│   ├── orchestrator/ # Pipeline coordination
│   ├── schemas/      # Pydantic models
│   ├── services/     # External services (S3, Backend client)
│   └── utils/        # Shared utilities
├── config/           # YAML configurations
├── tests/            # Unit & integration tests
└── docker/           # Docker configuration
```

## 🔧 Configuration

### Model Configuration

Configure provider credentials and model selection in `.env`:

```bash
# Active classifier model
# Options: openai-gpt4, openai-gpt4o, claude, gemini, roboflow
CLASSIFIER_MODEL=openai-gpt4o

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Google Gemini
GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-2.5-flash

# Anthropic (placeholder - not fully implemented)
ANTHROPIC_API_KEY=...

# Roboflow (workspace/project/version)
ROBOFLOW_API_KEY=...
ROBOFLOW_MODEL_ID=environmental-assitant-agents/waste-classifier-louut-b9sot/1
ROBOFLOW_CONFIDENCE_THRESHOLD=0.4
```

### Switch Classification Model

The Factory Pattern enables switching between models **without code changes**. Simply edit `.env`:

```bash
# Options: openai-gpt4, openai-gpt4o, claude, gemini, roboflow
CLASSIFIER_MODEL=openai-gpt4o
```

Or programmatically override in code:

```python
from app.factories.classifier_factory import ClassifierFactory

# Use default from settings
adapter = ClassifierFactory.create()

# Override for specific request
adapter = ClassifierFactory.create(model_override="roboflow")

# List all available models
models = ClassifierFactory.list_available()
# ['openai-gpt4', 'openai-gpt4o', 'claude', 'gemini', 'roboflow']
```

### Roboflow Setup & Configuration

**Model already trained and deployed**: `environmental-assitant-agents/waste-classifier-louut-b9sot/1`

#### Using the Public Model

1. Get API Key from [Roboflow Account](https://app.roboflow.com)
2. Configure `.env`:
   ```bash
   ROBOFLOW_API_KEY=your_api_key_here
   ROBOFLOW_MODEL_ID=environmental-assitant-agents/waste-classifier-louut-b9sot/1
   CLASSIFIER_MODEL=roboflow
   ```

#### Creating a Custom Model

1. **Create Account**: Sign up at [Roboflow](https://roboflow.com)

2. **Create Project**:
   - Navigate to "Create Project"
   - Select "Object Detection" or "Classification"
   - Name: `waste-classifier`

3. **Upload Dataset**:
   - Upload waste images (recommended: 100+ images per class)
   - Classes: plastic, paper, glass, metal, organic, other
   - Annotate images (bounding boxes or labels)

4. **Train Model**:
   - Generate dataset version
   - Click "Train" → Select plan (Free or Paid)
   - Wait 5-15 minutes for training

5. **Deploy & Configure**:
   - Copy Model ID from deployment page (format: `workspace/project/version`)
   - Update `.env`:
     ```bash
     ROBOFLOW_MODEL_ID=your-workspace/waste-classifier/1
     ```

6. **Test Integration**:
   ```bash
   # Run integration tests
   RUN_INTEGRATION_TESTS=1 pytest tests/integration/test_classifier_factory_integration.py::test_factory_roboflow_integration -v
   ```

#### Roboflow Adapter Features

- **Free Tier**: 1,000 API calls/month
- **Cost**: ~$0.001 per classification (10x cheaper than GPT-4)
- **Speed**: ~500ms average (faster than LLMs)
- **Accuracy**: Depends on training data (typically 70-90% for waste)
- **Use Case**: Production deployments requiring cost optimization

### Logging Configuration

Agent Hub uses **structured logging with structlog** for production observability and debugging.

#### Basic Configuration

Configure logging via environment variables in `.env`:

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json # json (production) or text (development)
```

#### Log Formats

**Production (JSON)**:
```bash
LOG_FORMAT=json
```
- Structured JSON output for log aggregation systems
- Parseable by CloudWatch, Datadog, Elasticsearch, etc.
- Example output:
  ```json
  {
    "timestamp": "2025-11-07T10:30:15.234Z",
    "level": "info",
    "event": "classification_complete",
    "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "agent": "Classifier",
    "action": "classify_material",
    "material": "PLASTIC",
    "confidence": 0.89,
    "model_used": "openai/gpt-4-vision-preview",
    "latency_ms": 1200,
    "cost_usd": 0.010
  }
  ```

**Development (Text)**:
```bash
LOG_FORMAT=text
```
- Human-readable console output with colors
- Better for local debugging
- Example output:
  ```
  2025-11-07 10:30:15 [info     ] classification_complete agent=Classifier material=PLASTIC confidence=0.89
  ```

#### Standard Log Fields

**Mandatory fields** (present in all logs):
- `timestamp`: ISO 8601 format (e.g., `2025-11-07T10:30:15.234Z`)
- `level`: Log level (`debug`, `info`, `warning`, `error`, `critical`)
- `event`: Event description (e.g., `pipeline_step`, `classification_complete`)

**Contextual fields** (agent-specific):
- `trace_id`: UUID for request correlation across pipeline
- `agent`: Agent name (`PreValidator`, `Classifier`, etc.)
- `action`: Specific action (`validate_image`, `classify_material`)
- `latency_ms`: Execution time in milliseconds
- `cost_usd`: Operation cost (for LLM calls)
- `model_used`: Active model (e.g., `openai/gpt-4o`)
- `confidence`: Classification confidence score (0.0-1.0)
- `material`: Classified material type
- `error_code`: Error code for failures

#### Usage in Code

**Basic logging**:
```python
from app.core.logging import logger

logger.info("event_name", trace_id="abc-123", agent="Classifier")
logger.error("validation_failed", error_code="NO_WASTE_DETECTED")
```

**Context binding** (recommended for agents):
```python
from app.core.logging import logger

# Create agent-specific logger with persistent context
agent_logger = logger.bind(agent="PreValidator", trace_id="abc-123")

# All subsequent logs include agent and trace_id
agent_logger.info("validation_started")
agent_logger.info("image_received", size_kb=450)
agent_logger.info("validation_complete", has_waste=True)
```

**Logging with exceptions**:
```python
try:
    result = classify_image(image)
except Exception as e:
    logger.error("classification_failed", error=str(e), exc_info=True)
```

#### Log Levels

- `DEBUG`: Detailed diagnostic information (development only)
  ```python
  logger.debug("processing_step", step=1, data=image_data)
  ```

- `INFO`: General informational messages (default for production)
  ```python
  logger.info("classification_complete", material="PLASTIC")
  ```

- `WARNING`: Warning messages for unexpected but handled situations
  ```python
  logger.warning("low_confidence", confidence=0.45, threshold=0.7)
  ```

- `ERROR`: Error messages for failures
  ```python
  logger.error("api_call_failed", provider="openai", status_code=500)
  ```

- `CRITICAL`: Critical failures requiring immediate attention
  ```python
  logger.critical("database_connection_lost", retry_count=3)
  ```

#### Viewing Logs

**Local development**:
```bash
# Start with DEBUG level and text format
LOG_LEVEL=DEBUG LOG_FORMAT=text uvicorn app.main:app --reload
```

**Production (Railway)**:
```bash
# View live logs
railway logs

# Follow logs in real-time
railway logs --follow

# Filter by level
railway logs | grep "error"
```

**Docker**:
```bash
# View logs
docker-compose -f docker/docker-compose.yml logs

# Follow logs
docker-compose -f docker/docker-compose.yml logs -f

# Filter by service
docker-compose -f docker/docker-compose.yml logs agent-hub
```

#### Trace ID Correlation

Every request through the pipeline gets a unique `trace_id` that propagates through all agents:

1. Request arrives → Generate `trace_id`
2. PreValidator → Logs with `trace_id`
3. Classifier → Logs with same `trace_id`
4. All subsequent agents → Use same `trace_id`

This enables **end-to-end request tracing** in production:

```bash
# Find all logs for a specific request
railway logs | grep "trace_id=a1b2c3d4-e5f6-7890"

# Or with JSON logs:
railway logs | jq 'select(.trace_id == "a1b2c3d4-e5f6-7890")'
```

#### Testing Logging

```bash
# Run logging tests
pytest tests/unit/test_logging.py -v

# Test JSON format output
pytest tests/unit/test_logging.py::TestJSONOutput -v

# Test trace_id propagation
pytest tests/unit/test_logging.py::TestTraceIdPropagation -v
```

## 📊 Performance Targets

- **Latency**: p95 < 3000ms (complete pipeline with 10 agents)
  - With bytes processing: ~2.4s (60% faster than URLs)
  - Breakdown: PreValidator (450ms) + Classifier (600ms) + SubtypeDetector (700ms) + VolumeEstimator (50ms) + Others (600ms)
- **Cost**: < $0.025 per scan (MVP with lookup table for volume estimation)
  - PreValidator: $0.0002 | Classifier: $0.0050 | SubtypeDetector: $0.0050 | FeedbackCoach: $0.0020
- **Availability**: 99.9%
- **Success Rate**: > 95%
- **Subtype Accuracy**: > 75%
- **Volume Estimation Precision**: ±25%

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/amazing-feature`
2. Commit changes: `git commit -m 'Add amazing feature'`
3. Push to branch: `git push origin feature/amazing-feature`
4. Open Pull Request

## 📝 License

MIT License - See LICENSE file for details

## 👤 Author

Daniel Carrera - [carreraprogrammer@gmail.com](mailto:carreraprogrammer@gmail.com)

## 🆘 Support

- Issues: GitHub Issues
- Email: carreraprogrammer@gmail.com
