#!/bin/bash
#
# EDV-61 Validation Script
# Error Handling Robusto + Circuit Breaker + Retry (V4.2)
#
# Este script valida automáticamente todos los criterios de aceptación del ticket EDV-61
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          EDV-61 - VALIDATION SCRIPT                            ║${NC}"
echo -e "${BLUE}║   Error Handling Robusto + Circuit Breaker + Retry (V4.2)     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print test result
print_result() {
    local test_name=$1
    local status=$2
    local message=$3

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC} - $test_name"
        [ -n "$message" ] && echo -e "   ${message}"
        ((PASSED++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ FAIL${NC} - $test_name"
        [ -n "$message" ] && echo -e "   ${message}"
        ((FAILED++))
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  WARN${NC} - $test_name"
        [ -n "$message" ] && echo -e "   ${message}"
        ((WARNINGS++))
    fi
}

# Function to check file exists
check_file() {
    local file=$1
    local description=$2

    if [ -f "$file" ]; then
        print_result "$description" "PASS" "Archivo encontrado: $file"
        return 0
    else
        print_result "$description" "FAIL" "Archivo no encontrado: $file"
        return 1
    fi
}

# Function to check pattern in file
check_pattern() {
    local file=$1
    local pattern=$2
    local description=$3

    if grep -q "$pattern" "$file" 2>/dev/null; then
        print_result "$description" "PASS"
        return 0
    else
        print_result "$description" "FAIL" "Patrón '$pattern' no encontrado en $file"
        return 1
    fi
}

echo -e "${BLUE}[CA-1] Verificando Excepciones Custom...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_file "app/core/exceptions.py" "CA-1.1: Archivo exceptions.py existe"
check_pattern "app/core/exceptions.py" "class AgentHubException" "CA-1.2: Clase base AgentHubException"
check_pattern "app/core/exceptions.py" "def to_dict" "CA-1.3: Método to_dict()"
check_pattern "app/core/exceptions.py" "class ValidationError" "CA-1.4: ValidationError definido"
check_pattern "app/core/exceptions.py" "class ClassificationError" "CA-1.5: ClassificationError definido"
check_pattern "app/core/exceptions.py" "class AgentTimeoutError" "CA-1.6: AgentTimeoutError definido"
check_pattern "app/core/exceptions.py" "class ExternalAPIError" "CA-1.7: ExternalAPIError definido"
check_pattern "app/core/exceptions.py" "class BackendIntegrationError" "CA-1.8: BackendIntegrationError definido"
check_pattern "app/core/exceptions.py" "class CircuitBreakerOpenError" "CA-1.9: CircuitBreakerOpenError definido"

echo ""
echo -e "${BLUE}[CA-2] Verificando Circuit Breaker...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_file "app/core/circuit_breaker.py" "CA-2.1: Archivo circuit_breaker.py existe"
check_pattern "app/core/circuit_breaker.py" "class CircuitState" "CA-2.2: Estados definidos"
check_pattern "app/core/circuit_breaker.py" "CLOSED.*OPEN.*HALF_OPEN" "CA-2.3: Estados CLOSED, OPEN, HALF_OPEN"
check_pattern "app/core/circuit_breaker.py" "def call" "CA-2.4: Decorator call() implementado"
check_pattern "app/core/circuit_breaker.py" "_on_success" "CA-2.5: Método _on_success()"
check_pattern "app/core/circuit_breaker.py" "_on_failure" "CA-2.6: Método _on_failure()"
check_pattern "app/orchestrator/pipeline.py" "CircuitBreaker.*openai-api" "CA-2.7: Circuit breaker para OpenAI"
check_pattern "app/orchestrator/pipeline.py" "CircuitBreaker.*google-api" "CA-2.8: Circuit breaker para Google"

echo ""
echo -e "${BLUE}[CA-3] Verificando Retry Logic...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_file "app/utils/retry.py" "CA-3.1: Archivo retry.py existe"
check_pattern "app/utils/retry.py" "async def retry_with_backoff" "CA-3.2: Función retry_with_backoff()"
check_pattern "app/utils/retry.py" "exponential_base" "CA-3.3: Exponential backoff implementado"
check_pattern "app/utils/retry.py" "jitter" "CA-3.4: Jitter configurable"
check_pattern "app/utils/retry.py" "def with_retry" "CA-3.5: Decorator with_retry()"
check_pattern "app/utils/retry.py" "retryable_exceptions" "CA-3.6: Excepciones retryables configurables"

echo ""
echo -e "${BLUE}[CA-4] Verificando Pipeline Error Handling...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_pattern "app/orchestrator/pipeline.py" "except ValidationError" "CA-4.1: Handler para ValidationError"
check_pattern "app/orchestrator/pipeline.py" "except AgentTimeoutError" "CA-4.2: Handler para AgentTimeoutError"
check_pattern "app/orchestrator/pipeline.py" "except CircuitBreakerOpenError" "CA-4.3: Handler para CircuitBreakerOpenError"
check_pattern "app/orchestrator/pipeline.py" "except ClassificationError" "CA-4.4: Handler para ClassificationError"
check_pattern "app/orchestrator/pipeline.py" "except Exception" "CA-4.5: Handler genérico para Exception"
check_pattern "app/orchestrator/pipeline.py" "finally:" "CA-4.6: Bloque finally presente"

echo ""
echo -e "${BLUE}[CA-5] Verificando Logging Estructurado...${NC}"
echo "─────────────────────────────────────────────────────────────"

TRACE_ID_COUNT=$(grep -r "trace_id" app/orchestrator/pipeline.py app/api/endpoints/classify.py | wc -l)
if [ "$TRACE_ID_COUNT" -gt 50 ]; then
    print_result "CA-5.1: trace_id en logs" "PASS" "Encontradas $TRACE_ID_COUNT menciones"
else
    print_result "CA-5.1: trace_id en logs" "WARN" "Solo $TRACE_ID_COUNT menciones (esperado >50)"
fi

check_pattern "app/orchestrator/pipeline.py" "logger.info" "CA-5.2: Logging info utilizado"
check_pattern "app/orchestrator/pipeline.py" "logger.warning" "CA-5.3: Logging warning utilizado"
check_pattern "app/orchestrator/pipeline.py" "logger.error" "CA-5.4: Logging error utilizado"

echo ""
echo -e "${BLUE}[CA-6] Verificando Finally Ejecuta Métricas...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_pattern "app/orchestrator/pipeline.py" "finally:" "CA-6.1: Bloque finally presente"
check_pattern "app/orchestrator/pipeline.py" "record_pipeline_execution" "CA-6.2: record_pipeline_execution() llamado"

# Verificar que finally está después de los except
if grep -A 20 "except Exception" app/orchestrator/pipeline.py | grep -q "finally:"; then
    print_result "CA-6.3: Finally después de todos los except" "PASS"
else
    print_result "CA-6.3: Finally después de todos los except" "FAIL"
fi

echo ""
echo -e "${BLUE}[CA-7] Verificando FastAPI Error Mapping...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_pattern "app/api/endpoints/classify.py" "except ValidationError.*400" "CA-7.1: ValidationError → HTTP 400"
check_pattern "app/api/endpoints/classify.py" "except CircuitBreakerOpenError.*503" "CA-7.2: CircuitBreakerOpenError → HTTP 503"
check_pattern "app/api/endpoints/classify.py" "except AgentTimeoutError.*504" "CA-7.3: AgentTimeoutError → HTTP 504"
check_pattern "app/api/endpoints/classify.py" "except ClassificationError.*500" "CA-7.4: ClassificationError → HTTP 500"
check_pattern "app/api/endpoints/classify.py" "except Exception.*500" "CA-7.5: Exception → HTTP 500"

echo ""
echo -e "${BLUE}[CA-8] Verificando Request Data Safe...${NC}"
echo "─────────────────────────────────────────────────────────────"

SAFE_PATTERN_COUNT=$(grep -c "request_trace_id.*in locals()" app/api/endpoints/classify.py || echo "0")
if [ "$SAFE_PATTERN_COUNT" -ge 5 ]; then
    print_result "CA-8.1: Pattern 'in locals()' utilizado" "PASS" "Encontrado $SAFE_PATTERN_COUNT veces"
else
    print_result "CA-8.1: Pattern 'in locals()' utilizado" "WARN" "Solo $SAFE_PATTERN_COUNT veces (esperado ≥5)"
fi

echo ""
echo -e "${BLUE}[CA-9] Verificando Backend NO Aborta...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_pattern "app/core/exceptions.py" "BackendIntegrationError.*LOW" "CA-9.1: BackendIntegrationError severity=LOW"
check_pattern "app/orchestrator/pipeline.py" "logger.warning.*backend_integration_failed" "CA-9.2: Backend failure logueado como warning"
check_pattern "app/orchestrator/pipeline.py" "return None.*backend" "CA-9.3: Backend failure retorna None (no raise)"

echo ""
echo -e "${BLUE}[CA-10] Verificando Partial Success...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_pattern "app/api/endpoints/classify.py" "fast_path_failed_fallback" "CA-10.1: Fast path fallback implementado"
check_pattern "app/orchestrator/pipeline.py" "asyncio.create_task" "CA-10.2: Tasks en background (no blocking)"

echo ""
echo -e "${BLUE}[CA-11] Verificando Métricas Prometheus...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_file "app/core/metrics.py" "CA-11.1: Archivo metrics.py existe"
check_pattern "app/core/metrics.py" "from prometheus_client import" "CA-11.2: prometheus_client importado"
check_pattern "app/core/metrics.py" "Counter" "CA-11.3: Counters definidos"
check_pattern "app/core/metrics.py" "Histogram" "CA-11.4: Histograms definidos"
check_pattern "app/core/metrics.py" "Gauge" "CA-11.5: Gauges definidos"
check_pattern "app/core/metrics.py" "class MetricsCollector" "CA-11.6: MetricsCollector implementado"

# Verificar si /metrics está expuesto
if grep -q "/metrics" app/main.py 2>/dev/null; then
    print_result "CA-11.7: Endpoint /metrics expuesto" "PASS"
else
    print_result "CA-11.7: Endpoint /metrics expuesto" "WARN" "Métricas definidas pero endpoint no expuesto"
fi

echo ""
echo -e "${BLUE}[CA-12] Verificando Coverage...${NC}"
echo "─────────────────────────────────────────────────────────────"

# Ejecutar pytest con coverage si está disponible
if command -v pytest &> /dev/null; then
    echo "Ejecutando tests con coverage..."
    COVERAGE_OUTPUT=$(PYTHONPATH=. venv/bin/pytest --cov=app --cov-report=term-missing --cov-report=json tests/ -q 2>&1 || true)

    # Extraer coverage total del output
    COVERAGE_PERCENT=$(echo "$COVERAGE_OUTPUT" | grep "^TOTAL" | awk '{print $NF}' | sed 's/%//' || echo "0")

    if [ -z "$COVERAGE_PERCENT" ] || [ "$COVERAGE_PERCENT" = "0" ]; then
        print_result "CA-12.1: Coverage total" "WARN" "No se pudo determinar coverage"
    elif [ "$(echo "$COVERAGE_PERCENT >= 85" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
        print_result "CA-12.1: Coverage total ≥85%" "PASS" "Coverage: ${COVERAGE_PERCENT}%"
    else
        print_result "CA-12.1: Coverage total ≥85%" "FAIL" "Coverage: ${COVERAGE_PERCENT}% (objetivo: ≥85%)"
    fi
else
    print_result "CA-12.1: Coverage total" "WARN" "pytest no disponible - saltando verificación"
fi

echo ""
echo -e "${BLUE}[CA-13] Verificando Responses Seguros...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_pattern "app/api/endpoints/classify.py" 'details.*{}.*Do NOT expose' "CA-13.1: Exception genérica no expone detalles internos"
check_pattern "app/core/exceptions.py" "def to_dict" "CA-13.2: to_dict() controla campos expuestos"

# Verificar que no hay stacktrace en responses
if grep -q "traceback\|exc_info.*True" app/api/endpoints/classify.py; then
    print_result "CA-13.3: Sin stacktrace en responses" "FAIL" "Posible exposición de stacktrace"
else
    print_result "CA-13.3: Sin stacktrace en responses" "PASS"
fi

echo ""
echo -e "${BLUE}[CA-14] Verificando Documentación...${NC}"
echo "─────────────────────────────────────────────────────────────"

check_file "README.md" "CA-14.1: README.md existe"

# Verificar docstrings en módulos principales
MODULES=("app/core/exceptions.py" "app/core/circuit_breaker.py" "app/utils/retry.py" "app/core/metrics.py")
DOCSTRING_COUNT=0
for module in "${MODULES[@]}"; do
    if grep -q '"""' "$module" 2>/dev/null; then
        ((DOCSTRING_COUNT++))
    fi
done

if [ "$DOCSTRING_COUNT" -eq "${#MODULES[@]}" ]; then
    print_result "CA-14.2: Docstrings en módulos principales" "PASS" "Todos los módulos tienen docstrings"
else
    print_result "CA-14.2: Docstrings en módulos principales" "WARN" "Solo $DOCSTRING_COUNT/${#MODULES[@]} módulos"
fi

# Verificar ERROR_HANDLING.md
if [ -f "docs/ERROR_HANDLING.md" ]; then
    print_result "CA-14.3: ERROR_HANDLING.md existe" "PASS"
else
    print_result "CA-14.3: ERROR_HANDLING.md existe" "FAIL" "Archivo docs/ERROR_HANDLING.md no encontrado"
fi

# Verificar diagramas
if ls docs/*.png docs/*.svg docs/*.mmd &> /dev/null; then
    print_result "CA-14.4: Diagramas presentes" "PASS"
else
    print_result "CA-14.4: Diagramas presentes" "WARN" "No se encontraron diagramas en docs/"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    RESUMEN DE VALIDACIÓN                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}✅ PASSED:${NC}   $PASSED"
echo -e "  ${YELLOW}⚠️  WARNINGS:${NC} $WARNINGS"
echo -e "  ${RED}❌ FAILED:${NC}   $FAILED"
echo ""

TOTAL=$((PASSED + WARNINGS + FAILED))
SCORE=$((PASSED * 100 / TOTAL))

if [ "$SCORE" -ge 85 ]; then
    echo -e "  ${GREEN}Puntuación: ${SCORE}% - EXCELENTE ✨${NC}"
    exit 0
elif [ "$SCORE" -ge 70 ]; then
    echo -e "  ${YELLOW}Puntuación: ${SCORE}% - BUENO (con observaciones) ⚠️${NC}"
    exit 0
else
    echo -e "  ${RED}Puntuación: ${SCORE}% - NECESITA MEJORAS ❌${NC}"
    exit 1
fi
