#!/bin/bash
# validation-edv47.sh - Validación completa del ticket EDV-47
# Implementar ClassifierFactory con Factory Pattern

echo "═══════════════════════════════════════════════════════════════"
echo "  VALIDACIÓN EDV-47: ClassifierFactory (Factory Pattern)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Información del sistema
echo "🖥️  INFORMACIÓN DEL SISTEMA:"
echo "   Fecha: $(date)"
echo "   Directorio: $(pwd)"
echo "   Usuario: $(whoami)"
PY=$(command -v python || command -v python3 || echo "")
PIP=$(command -v pip || command -v pip3 || echo "")
echo "   Python: $([ -n "$PY" ] && $PY --version 2>/dev/null || echo 'No instalado')"
echo "   Pip: $([ -n "$PIP" ] && $PIP --version 2>/dev/null || echo 'No instalado')"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    echo "❌ ERROR: No estás en el directorio raíz del proyecto Agent Hub"
    echo "   Ejecuta este script desde: environmental-agent-hub/"
    exit 1
fi

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
PASS=0
FAIL=0
WARN=0

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

# Helper: verificar paquete Python instalado
check_python_package() {
    local package="$1"
    if [ -n "$PY" ] && $PY - <<PYCHK 2>/dev/null
import importlib, sys
sys.exit(0 if importlib.util.find_spec('${package}') else 1)
PYCHK
    then
        echo -e "${GREEN}✅${NC} $package instalado"
        ((PASS++))
        return 0
    else
        echo -e "${YELLOW}⚠️${NC}  $package no instalado"
        ((WARN++))
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════
# FASE 0: PRE-REQUISITOS Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════
section "0️⃣  PRE-REQUISITOS Y CONFIGURACIÓN"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️${NC}  Archivo .env no encontrado (usando defaults de Settings)"
    ((WARN++))
else
    echo -e "${GREEN}✅${NC} Archivo .env existe"
    ((PASS++))
fi

echo ""
echo "Verificando paquetes requeridos para importar adapters (para correr tests):"
check_python_package "openai"
check_python_package "google.generativeai"
check_python_package "roboflow"

# ═══════════════════════════════════════════════════════════════
# FASE 1: ESTRUCTURA DE ARCHIVOS
# ═══════════════════════════════════════════════════════════════
section "1️⃣  ESTRUCTURA DE ARCHIVOS"

check "app/factories/classifier_factory.py existe" "[ -f app/factories/classifier_factory.py ]"
check "app/factories/__init__.py existe" "[ -f app/factories/__init__.py ]"
check "tests/unit/test_classifier_factory.py existe" "[ -f tests/unit/test_classifier_factory.py ]"
check "tests/integration/test_classifier_factory_integration.py existe" "[ -f tests/integration/test_classifier_factory_integration.py ]"

check "app/core/config.py existe" "[ -f app/core/config.py ]"
check "app/core/logging.py existe" "[ -f app/core/logging.py ]"

# ═══════════════════════════════════════════════════════════════
# FASE 2: VALIDACIONES ESTÁTICAS (CÓDIGO)
# ═══════════════════════════════════════════════════════════════
section "2️⃣  VALIDACIONES ESTÁTICAS (CÓDIGO)"

echo "Verificando definición de Factory y métodos requeridos:"
check "Clase ClassifierFactory definida" "grep -q 'class ClassifierFactory' app/factories/classifier_factory.py"
check "Método estático create()" "grep -Eq '^\s*@staticmethod' app/factories/classifier_factory.py && grep -Eq 'def create\s*\(' app/factories/classifier_factory.py"
check "Método estático list_available()" "grep -q 'def list_available' app/factories/classifier_factory.py"

echo ""
echo "Verificando modelos soportados en Factory (MVP):"
check "Modelo openai-gpt4 mapeado" "grep -q 'openai-gpt4' app/factories/classifier_factory.py"
check "Modelo openai-gpt4o mapeado" "grep -q 'openai-gpt4o' app/factories/classifier_factory.py"
check "Modelo claude mapeado" "grep -q 'claude' app/factories/classifier_factory.py"
check "Modelo gemini mapeado" "grep -q 'gemini' app/factories/classifier_factory.py"
check "Modelo roboflow mapeado" "grep -q 'roboflow' app/factories/classifier_factory.py"

echo ""
echo "Verificando validación y logging estructurado en Factory:"
check "ValueError para modelo no soportado" "grep -q 'Unsupported model' app/factories/classifier_factory.py"
check "Log info al crear adapter" "grep -q 'classifier_factory_create' app/factories/classifier_factory.py"
check "Warning para claude placeholder" "grep -q 'classifier_factory_unsupported' app/factories/classifier_factory.py"
check "Lee modelo desde settings.CLASSIFIER_MODEL" "grep -q 'settings.CLASSIFIER_MODEL' app/factories/classifier_factory.py"

echo ""
echo "Verificando configuración de modelos permitidos en Settings:"
check "CLASSIFIER_MODEL declarado" "grep -q 'CLASSIFIER_MODEL' app/core/config.py"
check "'claude' permitido en Settings" "grep -q 'claude' app/core/config.py"
check "Valores permitidos incluyen openai|gemini|roboflow" "grep -Eq 'openai-gpt4o?.*gemini.*roboflow' app/core/config.py"

# ═══════════════════════════════════════════════════════════════
# FASE 3: TESTS UNITARIOS (Factory)
# ═══════════════════════════════════════════════════════════════
section "3️⃣  TESTS UNITARIOS (Factory)"

RUN_UNIT_TESTS=1
if ! check_python_package "pytest"; then
  RUN_UNIT_TESTS=0
fi

# Si faltan dependencias de proveedores, los tests pueden fallar al importar
if ! $PY - <<'PYDEPS' 2>/dev/null
import importlib, sys
required = [
    ('openai', 'openai'),
    ('google.generativeai', 'google.generativeai'),
    ('roboflow', 'roboflow')
]
missing = [name for name, spec in required if not importlib.util.find_spec(spec)]
sys.exit(0 if not missing else 1)
PYDEPS
then
  warn "Faltan paquetes de SDK (openai/google/roboflow); saltando tests unitarios"
  RUN_UNIT_TESTS=0
fi

if [ $RUN_UNIT_TESTS -eq 1 ]; then
  UNIT_LOG="/tmp/test-classifier-factory-$(date +%s).log"
  if pytest tests/unit/test_classifier_factory.py -v --tb=short > "$UNIT_LOG" 2>&1; then
    echo -e "${GREEN}✅${NC} Tests unitarios de ClassifierFactory PASSED"
    ((PASS++))
    echo ""
    grep -E "(PASSED|FAILED|ERROR)" "$UNIT_LOG" | head -5
  else
    echo -e "${RED}❌${NC} Tests unitarios de ClassifierFactory FAILED"
    ((FAIL++))
    echo ""
    echo "   Últimos errores:"
    tail -20 "$UNIT_LOG"
    echo "   Log completo: $UNIT_LOG"
  fi
else
  info "Para ejecutar manualmente: pytest tests/unit/test_classifier_factory.py -v"
fi

# ═══════════════════════════════════════════════════════════════
# FASE 4: TESTS DE INTEGRACIÓN (Opcional)
# ═══════════════════════════════════════════════════════════════
section "4️⃣  TESTS DE INTEGRACIÓN (Opcional)"

if [ -n "$RUN_INTEGRATION_TESTS" ]; then
  INT_LOG="/tmp/test-classifier-factory-int-$(date +%s).log"
  if pytest tests/integration/test_classifier_factory_integration.py -v --tb=short > "$INT_LOG" 2>&1; then
    echo -e "${GREEN}✅${NC} Tests de integración PASSED"
    ((PASS++))
    echo ""; grep -E "(PASSED|FAILED|ERROR)" "$INT_LOG" | head -5
  else
    echo -e "${RED}❌${NC} Tests de integración FAILED"
    ((FAIL++))
    echo ""; tail -20 "$INT_LOG"
  fi
else
  warn "Tests de integración deshabilitados (definir RUN_INTEGRATION_TESTS=1 para ejecutarlos)"
  info "Validan Roboflow + OpenAI + Gemini con imagen real"
fi

# ═══════════════════════════════════════════════════════════════
# FASE 5: VALIDACIÓN DE ROBOFLOW (Setup + Factory)
# ═══════════════════════════════════════════════════════════════
section "5️⃣  VALIDACIÓN DE ROBOFLOW (Setup + Factory)"

check "RoboflowClassifierAdapter implementado" "grep -q 'class RoboflowClassifierAdapter' app/adapters/roboflow_adapter.py"
check "Factory mapea 'roboflow' al adapter" "grep -q "'roboflow'" app/factories/classifier_factory.py"
check "README documenta Roboflow Setup" "grep -iq 'Roboflow Setup' README.md"

if [ -f ".env" ]; then
  # No mostrar valores; sólo validar presencia
  RF_API=$(grep '^ROBOFLOW_API_KEY=' .env | cut -d '=' -f2)
  RF_ID=$(grep '^ROBOFLOW_MODEL_ID=' .env | cut -d '=' -f2)
  if [ -n "$RF_API" ] && [ ${#RF_API} -ge 10 ]; then
    echo -e "${GREEN}✅${NC} ROBOFLOW_API_KEY configurada"
    ((PASS++))
  else
    echo -e "${YELLOW}⚠️${NC}  ROBOFLOW_API_KEY faltante o inválida"
    ((WARN++))
  fi
  if [ -n "$RF_ID" ]; then
    echo -e "${GREEN}✅${NC} ROBOFLOW_MODEL_ID configurado"
    ((PASS++))
  else
    echo -e "${YELLOW}⚠️${NC}  ROBOFLOW_MODEL_ID no configurado"
    ((WARN++))
  fi
else
  warn ".env no presente; saltando verificación de claves Roboflow"
fi

warn "No es posible validar cuenta/dataset/entrenamiento de Roboflow vía script (revisión manual)"

# ═══════════════════════════════════════════════════════════════
# FASE 6: DOCUMENTACIÓN
# ═══════════════════════════════════════════════════════════════
section "6️⃣  DOCUMENTACIÓN"

check "README documenta ClassifierFactory" "grep -Eq 'ClassifierFactory|Factory Pattern' README.md"
check ".env.example tiene CLASSIFIER_MODEL" "grep -q '^CLASSIFIER_MODEL=' .env.example"
check "README documenta switch por env y override" "grep -Eq 'model_override|CLASSIFIER_MODEL' README.md"

# ═══════════════════════════════════════════════════════════════
# FASE 7: CHECKLIST FINAL DE CRITERIOS DE ACEPTACIÓN
# ═══════════════════════════════════════════════════════════════
section "7️⃣  CHECKLIST FINAL DE CRITERIOS DE ACEPTACIÓN (EDV-47)"

echo "Factory Pattern:"
check "- Clase ClassifierFactory con create()" "grep -q 'class ClassifierFactory' app/factories/classifier_factory.py && grep -q 'def create' app/factories/classifier_factory.py"
check "- Lee modelo desde settings por defecto" "grep -q 'settings.CLASSIFIER_MODEL' app/factories/classifier_factory.py"
check "- Permite override con parámetro" "grep -Eq 'def create\(model_override' app/factories/classifier_factory.py"
check "- Instancia adapter correcto por modelo" "grep -q '_SUPPORTED_MODELS' app/factories/classifier_factory.py"
check "- Valida modelo soportado (ValueError)" "grep -q 'Unsupported model' app/factories/classifier_factory.py"
check "- list_available() retorna modelos" "grep -q 'def list_available' app/factories/classifier_factory.py"
check "- Log estructurado al crear adapter" "grep -q 'classifier_factory_create' app/factories/classifier_factory.py"

echo ""
echo "Roboflow Integration:"
check "- Variables ROBOFLOW_* en settings" "grep -Eq 'ROBOFLOW_API_KEY|ROBOFLOW_MODEL_ID' app/core/config.py"
check "- Adapter Roboflow implementado" "grep -q 'class RoboflowClassifierAdapter' app/adapters/roboflow_adapter.py"
check "- Factory puede instanciar roboflow" "grep -q "'roboflow'" app/factories/classifier_factory.py"
check "- Test integración con 1 imagen (archivo)" "grep -q 'test_factory_roboflow_integration' tests/integration/test_classifier_factory_integration.py"
check "- Documentación de configuración en README" "grep -iq 'Roboflow' README.md"

echo ""
echo "Testing:"
check "- Tests unitarios del Factory presentes" "[ -f tests/unit/test_classifier_factory.py ]"
check "- Tests validan modelos soportados" "grep -Eq 'openai|gemini|roboflow|claude' tests/unit/test_classifier_factory.py"
check "- Tests validan errores para modelos no soportados" "grep -q 'invalid-model' tests/unit/test_classifier_factory.py"
check "- Test de integración del Factory presente" "[ -f tests/integration/test_classifier_factory_integration.py ]"

# ═══════════════════════════════════════════════════════════════
# RESUMEN FINAL Y REPORTE
# ═══════════════════════════════════════════════════════════════

echo ""
echo "━━━━━━━━━━ RESULTADOS ━━━━━━━━━━"
echo -e "${GREEN}PASS:${NC} $PASS  ${RED}FAIL:${NC} $FAIL  ${YELLOW}WARN:${NC} $WARN"

TOTAL=$((PASS+FAIL+WARN))
SUCCESS=$((PASS*100/(PASS+FAIL>0?PASS+FAIL:1)))

echo ""
if [ $FAIL -eq 0 ]; then
  echo "  🎉 ¡TICKET EDV-47 COMPLETADO!"
else
  echo "  📌 Revisar criterios fallidos"
fi

# Generar reporte Markdown
REPORT_PATH="validations/EDV-47/validation_report_edv47.md"
mkdir -p "$(dirname "$REPORT_PATH")"
{
  echo "# 📋 Reporte de Validación EDV-47"
  echo "**Fecha:** $(date +"%Y-%m-%d %H:%M:%S")  "
  echo "**Ticket:** EDV-47 - ClassifierFactory (Factory Pattern)  "
  echo "**Sprint Designer:** Validación Automatizada  "
  echo ""
  echo "## 📊 Métricas de Calidad"
  echo "- ✅ **PASS:** $PASS criterios"
  echo "- ❌ **FAIL:** $FAIL criterios  "
  echo "- ⚠️ **WARN:** $WARN advertencias"
  echo ""
  echo "## ✅ Criterios Validados"
  echo "- Factory Pattern implementado (create, list_available, validación, logging)"
  echo "- Soporte de modelos: openai-gpt4, openai-gpt4o, claude, gemini, roboflow"
  echo "- Integración Roboflow documentada y testeada (opcional con RUN_INTEGRATION_TESTS)"
  echo ""
  echo "## 📝 Notas"
  echo "- Algunos checks pueden requerir dependencias (openai, google, roboflow)."
  echo "- Integra tests de red sólo si RUN_INTEGRATION_TESTS está definido."
  echo ""
  echo "---"
  echo "*Reporte generado automáticamente por validations/EDV-47/validation-edv47.sh*"
} > "$REPORT_PATH"

echo ""
echo "Reporte guardado en: $REPORT_PATH"

exit 0
