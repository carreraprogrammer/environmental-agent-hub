# Agent Hub - AI Orchestrator

Waste classification system with interchangeable AI models (GPT-4, Claude, Gemini).

## 🎯 Features

- **Interchangeable Models**: Switch between GPT-4, Claude, Gemini without code changes
- **DDD Architecture**: Clean, maintainable, extensible codebase
- **Fast**: <2s p95 latency end-to-end
- **Cost-Effective**: Optimized for <$0.015 per classification
- **Observable**: Structured JSON logging with trace_id
- **Production-Ready**: Docker + Railway deployment

## 🏗️ Stack

- **Runtime**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **AI Providers**: OpenAI, Anthropic, Google
- **Deployment**: Docker + Railway
- **Logging**: structlog (JSON)

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- Railway CLI (for deployment)
- OpenAI API Key (required)
- Anthropic API Key (optional)

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
- **Project Spec**: `docs/project-spec-agents.v2.1.md`
- **Architecture Spec**: `docs/architecture-spec-agents.v2.md`

## 🏛️ Architecture

```
agent-hub/
├── app/
│   ├── api/          # FastAPI endpoints
│   ├── core/         # Configuration & logging
│   ├── agents/       # Domain agents
│   ├── adapters/     # Model adapters (Adapter Pattern)
│   ├── factories/    # Object creation (Factory Pattern)
│   ├── orchestrator/ # Pipeline coordination
│   ├── schemas/      # Pydantic models
│   ├── services/     # External services
│   └── utils/        # Shared utilities
├── config/           # YAML configurations
├── tests/            # Unit & integration tests
└── docker/           # Docker configuration
```

## 🔧 Configuration

### Switch Classification Model

Edit `.env`:
```bash
# Options: openai-gpt4, openai-gpt4o, claude, gemini
CLASSIFIER_MODEL=openai-gpt4o
```

No code changes required!

### Adjust Logging

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json # json or text
```

## 📊 Performance Targets

- **Latency**: p95 < 2000ms
- **Cost**: < $0.015 per classification
- **Availability**: 99.9%
- **Success Rate**: > 95%

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
