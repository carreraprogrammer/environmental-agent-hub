# Agent Hub - AI Orchestrator

Waste classification system with interchangeable AI models (GPT-4, Gemini, Roboflow).

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

### Local Development (Docker)

```bash
# 1. Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# 2. Start services
docker-compose -f docker/docker-compose.yml up

# 3. Open browser
# http://localhost:8000/docs
```

## 🧪 Testing

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

### Complete AI Pipeline (10 Agents)
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

### Adjust Logging

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json # json or text
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
