#!/bin/bash
# scripts/validate_edv45.sh

set -e  # Exit on error

echo "========================================="
echo "  VALIDACIÓN COMPLETA EDV-45"
echo "========================================="

# Check structure
echo "✓ Verificando estructura..."
test -f app/main.py || (echo "❌ Falta app/main.py" && exit 1)
test -f docker/Dockerfile || (echo "❌ Falta docker/Dockerfile" && exit 1)

# Check dependencies
echo "✓ Verificando dependencias..."
pip install -q -r requirements.txt

# Check syntax
echo "✓ Verificando sintaxis..."
python -m py_compile app/main.py

# Run linters
echo "✓ Ejecutando linters..."
black --check app/ tests/ || (echo "❌ Black falló" && exit 1)
isort --check-only app/ tests/ || (echo "❌ isort falló" && exit 1)

# Run tests
echo "✓ Ejecutando tests..."
pytest tests/unit/test_health.py -v || (echo "❌ Tests fallaron" && exit 1)

# Build Docker
echo "✓ Construyendo Docker..."
docker build -f docker/Dockerfile -t agent-hub:test . || (echo "❌ Docker build falló" && exit 1)

echo ""
echo "========================================="
echo "  ✅ VALIDACIÓN COMPLETA EXITOSA"
echo "========================================="
echo ""
echo "El ticket EDV-45 está LISTO para DONE ✅"
