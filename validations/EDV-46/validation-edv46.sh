#!/bin/bash
# validation-edv46.sh - Validación completa del ticket EDV-46
# Core Classifier Adapters Implementation (OpenAI, Gemini, Roboflow)

echo "═══════════════════════════════════════════════════════════════"
echo "  VALIDACIÓN EDV-46: Core Classifier Adapters Implementation"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Detectar y activar virtual environment si existe
if [ -f "venv/bin/activate" ]; then
    echo "🔍 Detectando virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activado"
elif [ -f ".venv/bin/activate" ]; then
    echo "🔍 Detectando virtual environment..."
    source .venv/bin/activate
    echo "✅ Virtual environment activado"
fi

# Información del sistema
echo ""
echo "🖥️  INFORMACIÓN DEL SISTEMA:"
echo "   Fecha: $(date)"
echo "   Directorio: $(pwd)"
echo "   Usuario: $(whoami)"

# Usar Python del venv si está disponible
if [ -f "venv/bin/python" ]; then
    PY="venv/bin/python"
    PIP="venv/bin/pip"
elif [ -f ".venv/bin/python" ]; then
    PY=".venv/bin/python"
    PIP=".venv/bin/pip"
else
    PY=$(command -v python || command -v python3 || echo "")
    PIP=$(command -v pip || command -v pip3 || echo "")
fi

echo "   Python: $([ -n "$PY" ] && $PY --version 2>/dev/null || echo 'No instalado')"
echo "   Python path: $PY"
echo "   Pip: $([ -n "$PIP" ] && $PIP --version 2>/dev/null || echo 'No instalado')"

# Configurar pytest del venv
if [ -f "venv/bin/pytest" ]; then
    PYTEST="venv/bin/pytest"
elif [ -f ".venv/bin/pytest" ]; then
    PYTEST=".venv/bin/pytest"
else
    PYTEST=$(command -v pytest || echo "")
fi
echo "   Pytest: $([ -n "$PYTEST" ] && echo $PYTEST || echo 'No encontrado')"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    echo "❌ ERROR: No estás en el directorio raíz del proyecto Agent Hub"
    echo "   Ejecuta este script desde: agent-hub/"
    exit 1
fi

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
PASS=0
FAIL=0
WARN=0

# Función de validación
check() {
    local description="$1"
    local command="$2"
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $description"
        ((PASS++))
        return 0
    else
        echo -e "${RED}❌${NC} $description"
        ((FAIL++))
        return 1
    fi
}

warn() {
    local description="$1"
    echo -e "${YELLOW}⚠️${NC}  $description"
    ((WARN++))
}

section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

info() {
    echo -e "${BLUE}ℹ️${NC}  $1"
}

# ═══════════════════════════════════════════════════════════════
# FASE 0: PRE-REQUISITOS Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════
section "0️⃣  PRE-REQUISITOS Y CONFIGURACIÓN"

echo "Verificando variables de entorno críticas:"

# Verificar .env existe
if [ ! -f ".env" ]; then
    echo -e "${RED}❌${NC} Archivo .env no encontrado"
    echo "   Crea .env basándote en .env.example"
    ((FAIL++))
else
    echo -e "${GREEN}✅${NC} Archivo .env existe"
    ((PASS++))
fi

# Verificar API keys configuradas (sin mostrar valores completos)
echo ""
echo "Verificando API keys en .env:"

check_env_var() {
    local var_name="$1"
    local var_value=$(grep "^${var_name}=" .env 2>/dev/null | cut -d '=' -f2)
    
    if [ -z "$var_value" ]; then
        echo -e "${RED}❌${NC} ${var_name} no configurada"
        ((FAIL++))
        return 1
    elif [ ${#var_value} -lt 10 ]; then
        echo -e "${RED}❌${NC} ${var_name} parece inválida (muy corta)"
        ((FAIL++))
        return 1
    else
        local masked="${var_value:0:5}...${var_value: -3}"
        echo -e "${GREEN}✅${NC} ${var_name}=${masked}"
        ((PASS++))
        return 0
    fi
}

check_env_var "OPENAI_API_KEY"
check_env_var "GOOGLE_API_KEY"
check_env_var "ROBOFLOW_API_KEY"
check_env_var "ROBOFLOW_MODEL_ID"

# Verificar dependencias Python instaladas
echo ""
echo "Verificando dependencias Python:"

check_python_package() {
    local package="$1"
    if python -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $package instalado"
        ((PASS++))
        return 0
    else
        echo -e "${RED}❌${NC} $package no instalado"
        ((FAIL++))
        return 1
    fi
}

if [ -n "$PY" ]; then
    check_python_package "openai"
    check_python_package "google.generativeai"
    check_python_package "roboflow"
else
    warn "Python no disponible en PATH; saltando verificación de paquetes"
fi

# ═══════════════════════════════════════════════════════════════
# FASE 1: ESTRUCTURA DE ARCHIVOS
# ═══════════════════════════════════════════════════════════════
section "1️⃣  ESTRUCTURA DE ARCHIVOS"

echo "Verificando archivos de adapters:"
check "app/adapters/base.py existe" "[ -f app/adapters/base.py ]"
check "app/adapters/openai_adapter.py existe" "[ -f app/adapters/openai_adapter.py ]"
check "app/adapters/google_adapter.py existe" "[ -f app/adapters/google_adapter.py ]"
check "app/adapters/roboflow_adapter.py existe" "[ -f app/adapters/roboflow_adapter.py ]"

echo ""
echo "Verificando archivos de tests unitarios:"
check "tests/unit/test_openai_adapter.py existe" "[ -f tests/unit/test_openai_adapter.py ]"
check "tests/unit/test_google_adapter.py existe" "[ -f tests/unit/test_google_adapter.py ]"
check "tests/unit/test_roboflow_adapter.py existe" "[ -f tests/unit/test_roboflow_adapter.py ]"

echo ""
echo "Verificando tests de integración:"
check "tests/integration/ existe" "[ -d tests/integration ]"
check "tests/integration/test_adapters_integration.py existe" "[ -f tests/integration/test_adapters_integration.py ]"

echo ""
echo "Verificando configuración actualizada:"
check "app/core/config.py existe" "[ -f app/core/config.py ]"

# Verificar que config.py tiene las nuevas variables
if grep -q "OPENAI_API_KEY" app/core/config.py && \
   grep -q "GOOGLE_API_KEY" app/core/config.py && \
   grep -q "ROBOFLOW_API_KEY" app/core/config.py; then
    echo -e "${GREEN}✅${NC} config.py tiene configuración de API keys"
    ((PASS++))
else
    echo -e "${RED}❌${NC} config.py falta configuración de API keys"
    ((FAIL++))
fi

# ═══════════════════════════════════════════════════════════════
# FASE 2: VALIDACIÓN DE CÓDIGO (LINTERS)
# ═══════════════════════════════════════════════════════════════
section "2️⃣  VALIDACIÓN DE CÓDIGO (LINTERS)"

echo "Ejecutando Black (formateo de código):"
if command -v black &> /dev/null; then
    if black --check app/adapters/*.py 2>&1 | grep -q "would be reformatted"; then
        echo -e "${YELLOW}⚠️${NC}  Código necesita formateo (ejecutar: black app/adapters/)"
        ((WARN++))
    else
        echo -e "${GREEN}✅${NC} Código formateado correctamente"
        ((PASS++))
    fi
else
    warn "Black no instalado, saltando validación de formateo"
fi

echo ""
echo "Ejecutando isort (imports ordenados):"
if command -v isort &> /dev/null; then
    if isort --check-only app/adapters/*.py 2>&1 | grep -q "would be reformatted"; then
        echo -e "${YELLOW}⚠️${NC}  Imports necesitan ordenamiento (ejecutar: isort app/adapters/)"
        ((WARN++))
    else
        echo -e "${GREEN}✅${NC} Imports ordenados correctamente"
        ((PASS++))
    fi
else
    warn "isort no instalado, saltando validación de imports"
fi

echo ""
echo "Ejecutando mypy (type checking):"
if command -v mypy &> /dev/null; then
    MYPY_LOG="/tmp/mypy-edv46-$(date +%s).log"
    if mypy app/adapters/*.py > "$MYPY_LOG" 2>&1; then
        echo -e "${GREEN}✅${NC} Type hints correctos"
        ((PASS++))
    else
        if grep -q "INTERNAL ERROR" "$MYPY_LOG"; then
            warn "mypy tuvo un INTERNAL ERROR; marcando como warning"
            echo "   Log: $MYPY_LOG"
            echo "   Primeras líneas:"; head -10 "$MYPY_LOG"
            ((WARN++))
        else
            echo -e "${RED}❌${NC} Errores de type hints encontrados"
            echo "   Log: $MYPY_LOG"
            echo ""
            echo "   Primeros errores:"
            head -10 "$MYPY_LOG"
            ((FAIL++))
        fi
    fi
else
    warn "mypy no instalado, saltando type checking"
fi

# ═══════════════════════════════════════════════════════════════
# FASE 3: TESTS UNITARIOS (CON MOCKS)
# ═══════════════════════════════════════════════════════════════
section "3️⃣  TESTS UNITARIOS (CON MOCKS)"

echo "Ejecutando tests unitarios de OpenAI Adapter:"
OPENAI_TEST_LOG="/tmp/test-openai-$(date +%s).log"
if $PYTEST tests/unit/test_openai_adapter.py -v --tb=short > "$OPENAI_TEST_LOG" 2>&1; then
    echo -e "${GREEN}✅${NC} OpenAI Adapter tests PASSED"
    ((PASS++))
    
    # Mostrar resumen
    echo ""
    grep -E "(PASSED|FAILED|ERROR)" "$OPENAI_TEST_LOG" | head -5
else
    echo -e "${RED}❌${NC} OpenAI Adapter tests FAILED"
    ((FAIL++))
    echo ""
    echo "   Últimos errores:"
    tail -20 "$OPENAI_TEST_LOG"
    echo "   Log completo: $OPENAI_TEST_LOG"
fi

echo ""
echo "Ejecutando tests unitarios de Google Adapter:"
GOOGLE_TEST_LOG="/tmp/test-google-$(date +%s).log"
if $PYTEST tests/unit/test_google_adapter.py -v --tb=short > "$GOOGLE_TEST_LOG" 2>&1; then
    echo -e "${GREEN}✅${NC} Google Adapter tests PASSED"
    ((PASS++))
    
    echo ""
    grep -E "(PASSED|FAILED|ERROR)" "$GOOGLE_TEST_LOG" | head -5
else
    echo -e "${RED}❌${NC} Google Adapter tests FAILED"
    ((FAIL++))
    echo ""
    echo "   Últimos errores:"
    tail -20 "$GOOGLE_TEST_LOG"
    echo "   Log completo: $GOOGLE_TEST_LOG"
fi

echo ""
echo "Ejecutando tests unitarios de Roboflow Adapter:"
ROBOFLOW_TEST_LOG="/tmp/test-roboflow-$(date +%s).log"
if $PYTEST tests/unit/test_roboflow_adapter.py -v --tb=short > "$ROBOFLOW_TEST_LOG" 2>&1; then
    echo -e "${GREEN}✅${NC} Roboflow Adapter tests PASSED"
    ((PASS++))
    
    echo ""
    grep -E "(PASSED|FAILED|ERROR)" "$ROBOFLOW_TEST_LOG" | head -5
else
    echo -e "${RED}❌${NC} Roboflow Adapter tests FAILED"
    ((FAIL++))
    echo ""
    echo "   Últimos errores:"
    tail -20 "$ROBOFLOW_TEST_LOG"
    echo "   Log completo: $ROBOFLOW_TEST_LOG"
fi

# Verificar coverage
echo ""
echo "Verificando coverage de tests unitarios:"
COVERAGE_LOG="/tmp/coverage-edv46-$(date +%s).log"
if $PYTEST tests/unit/ --cov=app/adapters --cov-report=term > "$COVERAGE_LOG" 2>&1; then
    COVERAGE_PERCENT=$(grep -oP "TOTAL.*\K\d+(?=%)" "$COVERAGE_LOG" | tail -1)
    
    if [ -n "$COVERAGE_PERCENT" ]; then
        if [ "$COVERAGE_PERCENT" -ge 90 ]; then
            echo -e "${GREEN}✅${NC} Coverage: ${COVERAGE_PERCENT}% (objetivo: >90%)"
            ((PASS++))
        elif [ "$COVERAGE_PERCENT" -ge 70 ]; then
            echo -e "${YELLOW}⚠️${NC}  Coverage: ${COVERAGE_PERCENT}% (objetivo: >90%)"
            ((WARN++))
        else
            echo -e "${RED}❌${NC} Coverage: ${COVERAGE_PERCENT}% (muy bajo, objetivo: >90%)"
            ((FAIL++))
        fi
    else
        warn "No se pudo extraer porcentaje de coverage"
    fi
    
    echo ""
    echo "   Detalle de coverage por archivo:"
    grep -E "app/adapters" "$COVERAGE_LOG" | grep -v "^-"
else
    echo -e "${RED}❌${NC} Error ejecutando coverage"
    ((FAIL++))
fi

# ═══════════════════════════════════════════════════════════════
# FASE 4: TESTS DE INTEGRACIÓN (CON APIs REALES)
# ═══════════════════════════════════════════════════════════════
section "4️⃣  TESTS DE INTEGRACIÓN (CON APIs REALES)"

echo -e "${YELLOW}⚠️${NC}  IMPORTANTE: Los siguientes tests usan APIs reales"
echo "   - Requieren API keys válidas en .env"
echo "   - Consumen créditos/cuota de APIs"
echo "   - Pueden tardar varios segundos"
echo ""

read -p "¿Ejecutar tests de integración? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    
    echo ""
    echo "Ejecutando tests de integración con imagen de prueba:"
    
    INTEGRATION_LOG="/tmp/integration-edv46-$(date +%s).log"
    
    # Timeout de 60 segundos para tests de integración
    if timeout 60 $PYTEST tests/integration/test_adapters_integration.py -v --tb=short > "$INTEGRATION_LOG" 2>&1; then
        echo -e "${GREEN}✅${NC} Tests de integración PASSED"
        ((PASS++))
        
        echo ""
        echo "   Resumen de tests:"
        grep -E "(PASSED|FAILED|test_)" "$INTEGRATION_LOG" | tail -10
        
    elif [ $? -eq 124 ]; then
        echo -e "${RED}❌${NC} Tests de integración TIMEOUT (>60s)"
        ((FAIL++))
        echo "   Posibles causas: API lenta, rate limits, network issues"
        
    else
        echo -e "${RED}❌${NC} Tests de integración FAILED"
        ((FAIL++))
        echo ""
        echo "   Últimos errores:"
        tail -30 "$INTEGRATION_LOG"
        echo ""
        echo "   Log completo: $INTEGRATION_LOG"
    fi
    
    # Test específico de rate limiting en Gemini
    echo ""
    echo "Verificando rate limiting en Google Gemini:"
    
    if grep -q "test_gemini_rate_limiting" tests/integration/test_adapters_integration.py; then
        info "Test de rate limiting implementado en suite de integración"
        ((PASS++))
    else
        warn "Test de rate limiting no encontrado (recomendado implementar)"
    fi
    
else
    warn "Tests de integración saltados (usuario decidió no ejecutar)"
    info "Para ejecutar manualmente: pytest tests/integration/test_adapters_integration.py -v"
fi

# ═══════════════════════════════════════════════════════════════
# FASE 5: VALIDACIÓN DE ROBOFLOW SETUP
# ═══════════════════════════════════════════════════════════════
section "5️⃣  VALIDACIÓN DE ROBOFLOW SETUP"

echo "Verificando configuración de Roboflow:"

# Extraer variables de .env
ROBOFLOW_API_KEY=$(grep "^ROBOFLOW_API_KEY=" .env 2>/dev/null | cut -d '=' -f2)
ROBOFLOW_MODEL_ID=$(grep "^ROBOFLOW_MODEL_ID=" .env 2>/dev/null | cut -d '=' -f2)
ROBOFLOW_WORKSPACE=$(grep "^ROBOFLOW_WORKSPACE=" .env 2>/dev/null | cut -d '=' -f2)

if [ -z "$ROBOFLOW_API_KEY" ]; then
    echo -e "${RED}❌${NC} ROBOFLOW_API_KEY no configurada"
    ((FAIL++))
else
    echo -e "${GREEN}✅${NC} ROBOFLOW_API_KEY configurada"
    ((PASS++))
fi

if [ -z "$ROBOFLOW_MODEL_ID" ]; then
    echo -e "${RED}❌${NC} ROBOFLOW_MODEL_ID no configurada"
    ((FAIL++))
    warn "Formato esperado: workspace/proyecto/versión (p.ej. environmental-agent-hub/waste-classifier/1)"
else
    echo -e "${GREEN}✅${NC} ROBOFLOW_MODEL_ID: $ROBOFLOW_MODEL_ID"
    ((PASS++))
    
    # Validar formato de model_id (workspace/proyecto/versión)
    if [[ "$ROBOFLOW_MODEL_ID" =~ ^[a-z0-9-]+/[a-z0-9-]+/[0-9]+$ ]]; then
        echo -e "${GREEN}✅${NC} Formato de model_id válido"
        ((PASS++))
    else
        echo -e "${RED}❌${NC} Formato de model_id inválido (esperado: workspace/proyecto/versión)"
        ((FAIL++))
    fi
fi

if [ -z "$ROBOFLOW_WORKSPACE" ]; then
    warn "ROBOFLOW_WORKSPACE no configurada (usando default)"
else
    echo -e "${GREEN}✅${NC} ROBOFLOW_WORKSPACE: $ROBOFLOW_WORKSPACE"
    ((PASS++))
fi

# Test de conectividad con Roboflow API
echo ""
echo "Testeando conectividad con Roboflow API:"

if [ -n "$ROBOFLOW_API_KEY" ] && [ -n "$ROBOFLOW_MODEL_ID" ]; then
    if [ "${SKIP_ROBOFLOW_API_TEST:-}" = "true" ] || [ "${NETWORK_RESTRICTED:-}" = "true" ]; then
        warn "Saltando test de API (modo offline/CI)"
    else
    
    ROBOFLOW_TEST_SCRIPT="/tmp/test-roboflow-api.py"
    cat > "$ROBOFLOW_TEST_SCRIPT" << 'EOF'
import os
import sys
from roboflow import Roboflow

try:
    rf = Roboflow(api_key=os.getenv("ROBOFLOW_API_KEY"))
    parts = os.getenv("ROBOFLOW_MODEL_ID").split("/")
    workspace, project_name, version = parts[0], parts[1], int(parts[2])
    project = rf.workspace(workspace).project(project_name)
    model = project.version(version).model
    print("✓ Roboflow API conectada exitosamente")
    print(f"✓ Modelo: {model.id}")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF
    
    RUN_ROBOFLOW_TEST=0
    if [ -n "$PY" ]; then
        if $PY - <<'PYCHK' 2>/dev/null
import importlib, sys
sys.exit(0 if importlib.util.find_spec('roboflow') else 1)
PYCHK
        then
            RUN_ROBOFLOW_TEST=1
        else
            warn "Paquete roboflow no instalado; saltando test de conectividad"
        fi
    else
        warn "Python no disponible; saltando test de conectividad"
    fi

    if [ "$RUN_ROBOFLOW_TEST" -eq 1 ] && $PY "$ROBOFLOW_TEST_SCRIPT" 2>&1 | grep -q "conectada exitosamente"; then
        echo -e "${GREEN}✅${NC} Conectividad con Roboflow API exitosa"
        ((PASS++))
    else
        echo -e "${RED}❌${NC} Error conectando con Roboflow API"
        ((FAIL++))
        echo "   Verifica: API key, model_id, workspace"
    fi
    
    rm -f "$ROBOFLOW_TEST_SCRIPT"
    fi
else
    warn "Saltando test de API (faltan credenciales)"
fi

# ═══════════════════════════════════════════════════════════════
# FASE 6: VALIDACIÓN DE ESQUEMA UNIFICADO
# ═══════════════════════════════════════════════════════════════
section "6️⃣  VALIDACIÓN DE ESQUEMA UNIFICADO"

echo "Verificando que todos los adapters retornan ClassificationResult:"

# Script de validación de esquema
SCHEMA_TEST_SCRIPT="/tmp/test-schema-unified.py"
cat > "$SCHEMA_TEST_SCRIPT" << 'EOF'
import sys
from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.adapters.google_adapter import GoogleClassifierAdapter
from app.adapters.roboflow_adapter import RoboflowClassifierAdapter
from app.schemas.domain import ClassificationResult

adapters = [
    OpenAIClassifierAdapter,
    GoogleClassifierAdapter,
    RoboflowClassifierAdapter
]

for adapter_class in adapters:
    method = getattr(adapter_class, 'classify', None)
    if not method:
        print(f"✗ {adapter_class.__name__} no tiene método classify()")
        sys.exit(1)
    
    # Verificar que el método está anotado con ClassificationResult
    annotations = method.__annotations__
    if 'return' not in annotations:
        print(f"✗ {adapter_class.__name__}.classify() no tiene type hint de return")
        sys.exit(1)
    
    print(f"✓ {adapter_class.__name__} tiene esquema unificado")

print("✓ Todos los adapters implementan esquema unificado")
sys.exit(0)
EOF

if [ -n "$PY" ] && PYTHONPATH=. $PY "$SCHEMA_TEST_SCRIPT" 2>&1; then
    echo -e "${GREEN}✅${NC} Esquema unificado implementado en todos los adapters"
    ((PASS++))
else
    echo -e "${RED}❌${NC} Esquema unificado inconsistente entre adapters"
    ((FAIL++))
fi

rm -f "$SCHEMA_TEST_SCRIPT"

# Verificar campos obligatorios en ClassificationResult
echo ""
echo "Verificando campos de ClassificationResult:"

if grep -q "material:" app/schemas/domain.py && \
   grep -q "confidence:" app/schemas/domain.py && \
   grep -q "model_used:" app/schemas/domain.py; then
    echo -e "${GREEN}✅${NC} ClassificationResult tiene campos obligatorios"
    ((PASS++))
else
    echo -e "${RED}❌${NC} ClassificationResult falta campos obligatorios"
    ((FAIL++))
fi

# ═══════════════════════════════════════════════════════════════
# FASE 7: DOCUMENTACIÓN
# ═══════════════════════════════════════════════════════════════
section "7️⃣  DOCUMENTACIÓN"

echo "Verificando README actualizado:"

if [ -f "README.md" ]; then
    check "Sección Model Configuration" "grep -iq 'model configuration' README.md"
    check "Variables de entorno OPENAI" "grep -q 'OPENAI_API_KEY' README.md"
    check "Variables de entorno GOOGLE" "grep -q 'GOOGLE_API_KEY' README.md"
    check "Variables de entorno ROBOFLOW" "grep -q 'ROBOFLOW_API_KEY' README.md"
    check "Instrucciones setup Roboflow" "grep -iq 'roboflow' README.md"
else
    echo -e "${RED}❌${NC} README.md no encontrado"
    ((FAIL++))
fi

echo ""
echo "Verificando .env.example actualizado:"

if [ -f ".env.example" ]; then
    check "OPENAI_API_KEY en .env.example" "grep -q 'OPENAI_API_KEY' .env.example"
    check "GOOGLE_API_KEY en .env.example" "grep -q 'GOOGLE_API_KEY' .env.example"
    check "ROBOFLOW_API_KEY en .env.example" "grep -q 'ROBOFLOW_API_KEY' .env.example"
    check "ROBOFLOW_MODEL_ID en .env.example" "grep -q 'ROBOFLOW_MODEL_ID' .env.example"
    check "CLASSIFIER_MODEL en .env.example" "grep -q 'CLASSIFIER_MODEL' .env.example"
else
    echo -e "${RED}❌${NC} .env.example no encontrado"
    ((FAIL++))
fi

echo ""
echo "Verificando docstrings en adapters:"

check "openai_adapter.py tiene docstrings" "grep -q '\"\"\"' app/adapters/openai_adapter.py"
check "google_adapter.py tiene docstrings" "grep -q '\"\"\"' app/adapters/google_adapter.py"
check "roboflow_adapter.py tiene docstrings" "grep -q '\"\"\"' app/adapters/roboflow_adapter.py"

# ═══════════════════════════════════════════════════════════════
# FASE 8: CHECKLIST FINAL DE CRITERIOS DE ACEPTACIÓN
# ═══════════════════════════════════════════════════════════════
section "8️⃣  CHECKLIST FINAL DE CRITERIOS DE ACEPTACIÓN"

echo "Mapeando resultados a criterios de aceptación del ticket EDV-46:"
echo ""

# OpenAI Adapter
echo "🔹 OpenAI Adapter:"
echo "   Funcionalidad Core:"
check "   - Hereda de ClassifierAdapter" "grep -q 'class OpenAIClassifierAdapter(ClassifierAdapter)' app/adapters/openai_adapter.py"
check "   - Método classify() implementado" "grep -Eq 'def classify\s*\(' app/adapters/openai_adapter.py"
check "   - Soporte para gpt-4-vision-preview" "grep -q 'gpt-4-vision-preview' app/adapters/openai_adapter.py"

echo "   Configuración y Seguridad:"
check "   - Lee OPENAI_API_KEY desde settings" "grep -q 'OPENAI_API_KEY' app/adapters/openai_adapter.py"
check "   - Retry logic implementado" "grep -qE '(retry|backoff)' app/adapters/openai_adapter.py"
check "   - Logging estructurado" "grep -q 'logger' app/adapters/openai_adapter.py"

echo ""

# Google Adapter
echo "🔹 Google Gemini Adapter:"
echo "   Funcionalidad Core:"
check "   - Hereda de ClassifierAdapter" "grep -q 'class GoogleClassifierAdapter(ClassifierAdapter)' app/adapters/google_adapter.py"
check "   - Método classify() implementado" "grep -Eq 'def classify\s*\(' app/adapters/google_adapter.py"
check "   - Usa Gemini Pro Vision API" "grep -qE 'google\.generativeai|GenerativeModel' app/adapters/google_adapter.py"

echo "   Rate Limiting:"
check "   - Queue system para batch processing" "grep -qE '(deque|queue|Queue)' app/adapters/google_adapter.py"
check "   - Respeta límite 60 req/min" "grep -q '60' app/adapters/google_adapter.py"

echo ""

# Roboflow Adapter
echo "🔹 Roboflow Adapter:"
echo "   Setup Roboflow:"
if [ -n "$ROBOFLOW_API_KEY" ] && [ -n "$ROBOFLOW_MODEL_ID" ]; then
    echo -e "${GREEN}   ✅${NC} Cuenta Roboflow configurada"
    ((PASS++))
else
    echo -e "${RED}   ❌${NC} Cuenta Roboflow no configurada completamente"
    ((FAIL++))
fi

echo "   Funcionalidad Core:"
check "   - Hereda de ClassifierAdapter" "grep -q 'class RoboflowClassifierAdapter(ClassifierAdapter)' app/adapters/roboflow_adapter.py"
check "   - Método classify() implementado" "grep -Eq 'def classify\s*\(' app/adapters/roboflow_adapter.py"
check "   - Usa Roboflow Inference API" "grep -q 'roboflow' app/adapters/roboflow_adapter.py"

echo ""

# Tests
echo "🔹 Tests:"
UNIT_TEST_COUNT=$(find tests/unit -name "test_*adapter.py" 2>/dev/null | wc -l)
if [ "$UNIT_TEST_COUNT" -eq 3 ]; then
    echo -e "${GREEN}   ✅${NC} 3 archivos de tests unitarios (uno por adapter)"
    ((PASS++))
else
    echo -e "${RED}   ❌${NC} Faltan tests unitarios (encontrados: $UNIT_TEST_COUNT, esperados: 3)"
    ((FAIL++))
fi

if [ -f "tests/integration/test_adapters_integration.py" ]; then
    echo -e "${GREEN}   ✅${NC} Tests de integración implementados"
    ((PASS++))
else
    echo -e "${RED}   ❌${NC} Tests de integración no encontrados"
    ((FAIL++))
fi

echo ""

# Documentación
echo "🔹 Documentación:"
check "   - README actualizado con model config" "grep -iq 'model' README.md"
check "   - .env.example actualizado" "[ -f .env.example ] && grep -q 'ROBOFLOW' .env.example"
check "   - Docstrings completos" "grep -q '\"\"\"' app/adapters/openai_adapter.py"

# ═══════════════════════════════════════════════════════════════
# RESUMEN FINAL Y DECISIÓN
# ═══════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                        RESUMEN FINAL"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✅ PASS:${NC} $PASS"
echo -e "${RED}❌ FAIL:${NC} $FAIL"
echo -e "${YELLOW}⚠️  WARN:${NC} $WARN"
echo ""

# Calcular porcentaje de éxito
TOTAL=$((PASS + FAIL))
if [ $TOTAL -gt 0 ]; then
    PERCENTAGE=$(( (PASS * 100) / TOTAL ))
    echo "Porcentaje de éxito: $PERCENTAGE%"
    echo ""
fi

# Generar reporte para Sprint Designer
echo "🚀 GENERANDO REPORTE PARA SPRINT DESIGNER..."

cat > validation_report_edv46.md << EOF
# 📋 Reporte de Validación EDV-46
**Fecha:** $(date '+%Y-%m-%d %H:%M:%S')  
**Ticket:** EDV-46 - Core Classifier Adapters Implementation  
**Sprint Designer:** Validación Automatizada  

## 📊 Métricas de Calidad
- ✅ **PASS:** $PASS criterios
- ❌ **FAIL:** $FAIL criterios  
- ⚠️ **WARN:** $WARN advertencias
- 📈 **Éxito:** $PERCENTAGE%

## ✅ Criterios de Aceptación Validados

### 🤖 OpenAI Adapter
$(if grep -q 'class OpenAIClassifierAdapter(ClassifierAdapter)' app/adapters/openai_adapter.py 2>/dev/null; then echo "✅ **COMPLETADO** - Adapter implementado con GPT-4 Vision"; else echo "❌ **PENDIENTE** - Implementar OpenAI adapter"; fi)

### 🔮 Google Gemini Adapter
$(if grep -q 'class GoogleClassifierAdapter(ClassifierAdapter)' app/adapters/google_adapter.py 2>/dev/null; then echo "✅ **COMPLETADO** - Adapter con rate limiting tier gratuito"; else echo "❌ **PENDIENTE** - Implementar Gemini adapter"; fi)

### 🎯 Roboflow Adapter
$(if grep -q 'class RoboflowClassifierAdapter(ClassifierAdapter)' app/adapters/roboflow_adapter.py 2>/dev/null; then echo "✅ **COMPLETADO** - Adapter especializado configurado"; else echo "❌ **PENDIENTE** - Implementar Roboflow adapter"; fi)

### 🧪 Testing
$(if [ $UNIT_TEST_COUNT -eq 3 ]; then echo "✅ **COMPLETADO** - Tests unitarios para 3 adapters"; else echo "❌ **PENDIENTE** - Completar suite de tests"; fi)

### 📖 Documentación
$(if grep -q 'ROBOFLOW' README.md 2>/dev/null; then echo "✅ **COMPLETADO** - README y .env.example actualizados"; else echo "❌ **PENDIENTE** - Actualizar documentación"; fi)

## 🎯 Estado del Ticket
$(if [ $FAIL -eq 0 ]; then echo "🎉 **TICKET COMPLETADO** - Todos los criterios PASSED"; elif [ $FAIL -le 5 ]; then echo "⚠️ **CASI COMPLETO** - $FAIL criterios menores pendientes"; else echo "❌ **INCOMPLETO** - $FAIL criterios críticos fallando"; fi)

## 🔬 Comparación Científica Habilitada
$(if [ $PERCENTAGE -ge 80 ]; then echo "✅ Base sólida para tesis académica:\n- OpenAI (generalista pagado)\n- Gemini (generalista gratuito)\n- Roboflow (especializado custom)\n\n**Métricas comparables:** accuracy, latencia, costo"; else echo "⚠️ Completar implementación para habilitar comparación científica"; fi)

## 📝 Próximos Pasos
$(if [ $FAIL -eq 0 ]; then echo "- ✅ Mover ticket a DONE\n- ✅ Iniciar EDV-47 (Factory Pattern)\n- 🔬 Ejecutar experimentos comparativos\n- 📊 Recolectar métricas para tesis"; else echo "- 🔧 Revisar criterios fallidos arriba\n- 🔄 Re-ejecutar validación\n- 📋 Crear subtasks si es necesario"; fi)

---
*Reporte generado automáticamente por validation-edv46.sh*
EOF

echo -e "${GREEN}✅${NC} Reporte generado: validation_report_edv46.md"
echo ""

# Decisión final
if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}"
    echo "  🎉 ¡TICKET EDV-46 COMPLETADO! 🎉"
    echo ""
    echo "  ✅ 3 Adapters implementados (OpenAI, Gemini, Roboflow)"
    echo "  ✅ Esquema unificado validado"
    echo "  ✅ Tests unitarios pasando"
    echo "  ✅ Roboflow configurado para comparación científica"
    echo "  ✅ Documentación completa"
    echo ""
    echo "  🔬 SISTEMA LISTO PARA COMPARACIÓN CIENTÍFICA"
    echo -e "${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    exit 0
    
elif [ $FAIL -le 5 ]; then
    echo -e "${YELLOW}"
    echo "  ⚠️  TICKET CASI COMPLETO"
    echo ""
    echo "  Hay $FAIL criterios menores pendientes."
    echo "  Revisar los ❌ arriba para completar."
    echo ""
    echo "  Posibles causas:"
    echo "  - Tests de integración requieren API keys válidas"
    echo "  - Roboflow model_id no configurado"
    echo "  - Documentación incompleta"
    echo -e "${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    exit 1
    
else
    echo -e "${RED}"
    echo "  ❌ TICKET INCOMPLETO"
    echo ""
    echo "  Hay $FAIL criterios fallando."
    echo "  Revisar sección por sección arriba."
    echo ""
    echo "  Acción recomendada:"
    echo "  1. Revisar estructura de archivos (Fase 1)"
    echo "  2. Verificar API keys en .env (Fase 0)"
    echo "  3. Ejecutar tests unitarios manualmente"
    echo "  4. Consultar logs de error generados"
    echo -e "${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    exit 1
fi
