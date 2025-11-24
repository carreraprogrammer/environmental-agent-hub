#!/usr/bin/env bash
# validation-edv59.sh - Validación completa del ticket EDV-59
# FastAPI Endpoint POST /classify

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fix: Unset problematic CORS_ORIGINS variable that causes Pydantic parsing errors
unset CORS_ORIGINS 2>/dev/null || true

# Resolve project root (environmental-agent-hub/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/venv/bin/python"
PYTEST="$PROJECT_ROOT/venv/bin/pytest"

PASS=0
FAIL=0
WARN=0

section() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

check() {
  local description="$1"
  local command="$2"

  echo -e "\n${BLUE}Checking:${NC} $description"
  if eval "$command" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASS++))
    return 0
  else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAIL++))
    return 1
  fi
}

warn() {
  local description="$1"
  echo -e "${YELLOW}⚠️  WARN${NC} $description"
  ((WARN++))
}

echo "======================================================="
echo " EDV-59 VALIDATION - FastAPI Endpoint POST /classify"
echo "======================================================="
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Python: $PYTHON"
echo "Pytest: $PYTEST"
echo ""

#
# 0. Environment / prerequisites
#
section "0️⃣  ENVIRONMENT & PRE-REQUISITES"

check "Running inside environmental-agent-hub" "[ -f app/main.py ]"
check "Virtualenv Python exists" "test -x \"$PYTHON\""
check "Pytest exists" "test -x \"$PYTEST\""

#
# 1. Endpoint POST /classify
#
section "1️⃣  ENDPOINT POST /classify"

check "classify.py exists" "test -f app/api/endpoints/classify.py"
check "classify.py importable" "$PYTHON -c 'from app.api.endpoints.classify import router'"
check "Route is /api/v1/classify" "grep -q 'prefix=\"/api/v1\"' app/api/endpoints/classify.py"
check "Response model is ClassifyResponse" "grep -q 'response_model=ClassifyResponse' app/api/endpoints/classify.py"
check "Router included in main.py" "grep -q 'from app.api.endpoints.classify import router' app/main.py"

#
# 2. Detección de Formato (multipart vs JSON)
#
section "2️⃣  DETECCIÓN DE FORMATO"

check "Detects multipart/form-data format" "grep -q 'multipart/form-data' app/api/endpoints/classify.py"
check "Detects JSON format" "grep -q 'application/json' app/api/endpoints/classify.py"
check "Returns 400 if neither format" "grep -q 'INVALID_INPUT' app/api/endpoints/classify.py"
check "Logs input_format" "grep -q 'input_format' app/api/endpoints/classify.py"

#
# 3. Procesamiento Multipart (PREFERIDO)
#
section "3️⃣  PROCESAMIENTO MULTIPART (PREFERIDO)"

check "Reads image with await image.read()" "grep -q 'await.*\\.read()' app/api/endpoints/classify.py"
check "Builds ClassifyRequestForm" "grep -q 'ClassifyRequestForm' app/api/endpoints/classify.py"
check "Supports scan_id from form" "grep -q 'scan_id' app/api/endpoints/classify.py"
check "Supports station_id from form" "grep -q 'station_id' app/api/endpoints/classify.py"
check "Supports tenant_id from form" "grep -q 'tenant_id' app/api/endpoints/classify.py"
check "Supports trace_id from form (optional)" "grep -q 'trace_id' app/api/endpoints/classify.py"

#
# 4. Procesamiento JSON (LEGACY)
#
section "4️⃣  PROCESAMIENTO JSON (LEGACY)"

check "ClassifyRequest schema exists" "test -f app/schemas/requests.py"
check "ClassifyRequest importable" "$PYTHON -c 'from app.schemas.requests import ClassifyRequest'"
check "Validates image_url present" "grep -q 'image_url' app/schemas/requests.py"
check "JSON backward compatible" "grep -q 'ClassifyRequest' app/api/endpoints/classify.py"

#
# 5. Ejecución Pipeline
#
section "5️⃣  EJECUCIÓN PIPELINE"

check "Pipeline dependency injection" "grep -q 'Depends(get_pipeline)' app/api/endpoints/classify.py"
check "Calls pipeline.process()" "grep -q 'pipeline.process' app/api/endpoints/classify.py"
check "Measures latency" "grep -q 'elapsed_ms' app/api/endpoints/classify.py"
check "Includes trace_id in logs" "grep -q 'trace_id' app/api/endpoints/classify.py"

#
# 6. Background Task S3 Upload
#
section "6️⃣  BACKGROUND TASK S3 UPLOAD"

check "BackgroundTasks parameter present" "grep -q 'BackgroundTasks' app/api/endpoints/classify.py"
check "Schedules S3 upload for bytes format" "grep -q 'background_tasks.add_task' app/api/endpoints/classify.py"
check "S3Service dependency injection exists" "grep -q 'get_s3_service' app/api/dependencies.py"
check "Sets s3_upload_status = pending" "grep -q 's3_upload_status.*pending' app/api/endpoints/classify.py"

#
# 7. Error Handling
#
section "7️⃣  ERROR HANDLING"

check "ValidationError → 400 Bad Request" "grep -q 'ValidationError' app/api/endpoints/classify.py"
check "TimeoutError → 504 Gateway Timeout" "grep -q 'TimeoutError' app/api/endpoints/classify.py"
check "Exception → 500 Internal Server Error" "grep -q '500' app/api/endpoints/classify.py"
check "Error responses include suggestion" "grep -q 'suggestion' app/api/endpoints/classify.py"

#
# 8. Response Headers
#
section "8️⃣  RESPONSE HEADERS"

check "Sets X-Trace-Id header" "grep -q 'X-Trace-Id' app/api/endpoints/classify.py"
check "Sets X-Request-Duration header" "grep -q 'X-Request-Duration' app/api/endpoints/classify.py"
check "Content-Type is application/json" "grep -q 'response_model' app/api/endpoints/classify.py"

#
# 9. Logging
#
section "9️⃣  LOGGING"

check "Logs classify_request_received" "grep -q 'classify_request_received' app/api/endpoints/classify.py"
check "Logs classify_request_completed" "grep -q 'classify_request_completed' app/api/endpoints/classify.py"
check "Logs classify_request_rejected on ValidationError" "grep -q 'classify_request_rejected' app/api/endpoints/classify.py"
check "Logs classify_request_timeout on TimeoutError" "grep -q 'classify_request_timeout' app/api/endpoints/classify.py"
check "Logs classify_request_failed on Exception" "grep -q 'classify_request_failed' app/api/endpoints/classify.py"
check "All logs include trace_id" "grep -c 'trace_id' app/api/endpoints/classify.py | grep -q '[5-9]\\|[1-9][0-9]'"

#
# 10. Dependency Injection
#
section "🔟  DEPENDENCY INJECTION"

check "dependencies.py exists" "test -f app/api/dependencies.py"
check "get_pipeline function exists" "grep -q 'def get_pipeline' app/api/dependencies.py"
check "get_pipeline returns Pipeline" "grep -q 'Pipeline()' app/api/dependencies.py"
check "get_s3_service function exists" "grep -q 'def get_s3_service' app/api/dependencies.py"
check "get_s3_service returns S3Service" "grep -q 'S3Service()' app/api/dependencies.py"

#
# 11. Testing - Integration Tests E2E
#
section "1️⃣1️⃣  INTEGRATION TESTS E2E"

check "test_classify_endpoint.py exists" "test -f tests/integration/test_classify_endpoint.py"

# Test multipart format
check "Test multipart request success" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointMultipart::test_classify_multipart_success"
check "Test multipart with auto-generated IDs" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointMultipart::test_classify_multipart_with_auto_generated_ids"

# Test JSON format
check "Test JSON request success" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointJSON::test_classify_json_success"

# Test validation errors
check "Test 400 when no input provided" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointValidationErrors::test_classify_no_input_provided"
check "Test ValidationError (NO_WASTE)" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointValidationErrors::test_classify_no_waste_detected"
check "Test ValidationError (LOW_CONFIDENCE)" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointValidationErrors::test_classify_low_confidence"

# Test timeout
check "Test TimeoutError (504)" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointTimeouts::test_classify_timeout_error"

# Test server errors
check "Test ClassificationError (500)" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointServerErrors::test_classify_classification_error"
check "Test unexpected error (500)" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointServerErrors::test_classify_unexpected_error"

# Test headers
check "Test response headers present" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointHeaders::test_classify_response_headers_present"

# Test background tasks
check "Test background S3 upload scheduled" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointBackgroundTasks::test_classify_multipart_schedules_s3_upload"

# Test trace_id propagation
check "Test trace_id propagation multipart" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointTraceIdPropagation::test_trace_id_propagated_multipart"
check "Test trace_id propagation JSON" "$PYTEST -q tests/integration/test_classify_endpoint.py::TestClassifyEndpointTraceIdPropagation::test_trace_id_propagated_json"

#
# 12. Test Coverage
#
section "1️⃣2️⃣  TEST COVERAGE"

# Run all tests for classify endpoint
check "All classify endpoint tests pass" "$PYTEST -q tests/integration/test_classify_endpoint.py"

# Check coverage (≥80%)
if [ -n "${CHECK_COVERAGE:-}" ]; then
  echo -e "\n${BLUE}Checking:${NC} Test coverage ≥80%"
  COVERAGE=$($PYTEST tests/integration/test_classify_endpoint.py --cov=app.api.endpoints.classify --cov-report=term-missing | grep "^app/api/endpoints/classify.py" | awk '{print $4}' | sed 's/%//')

  if [ -n "$COVERAGE" ] && [ "$COVERAGE" -ge 80 ]; then
    echo -e "${GREEN}✅ PASS${NC} (Coverage: ${COVERAGE}%)"
    ((PASS++))
  else
    echo -e "${RED}❌ FAIL${NC} (Coverage: ${COVERAGE}%)"
    ((FAIL++))
  fi
else
  warn "Coverage check skipped (set CHECK_COVERAGE=1 to enable)"
fi

#
# 13. Code Quality
#
section "1️⃣3️⃣  CODE QUALITY"

# Pylint
if command -v pylint &> /dev/null; then
  echo -e "\n${BLUE}Checking:${NC} Pylint score ≥8.5"
  PYLINT_SCORE=$(pylint app/api/endpoints/classify.py 2>/dev/null | grep "Your code has been rated at" | awk '{print $7}' | cut -d'/' -f1 || echo "0")

  # Convert to integer comparison (multiply by 10)
  SCORE_INT=$(echo "$PYLINT_SCORE * 10" | bc 2>/dev/null | cut -d'.' -f1 || echo "0")

  if [ "$SCORE_INT" -ge 85 ]; then
    echo -e "${GREEN}✅ PASS${NC} (Score: ${PYLINT_SCORE}/10)"
    ((PASS++))
  else
    echo -e "${RED}❌ FAIL${NC} (Score: ${PYLINT_SCORE}/10)"
    ((FAIL++))
  fi
else
  warn "Pylint not installed, skipping"
fi

# Mypy
if command -v mypy &> /dev/null; then
  check "Mypy type checking passes" "mypy app/api/endpoints/classify.py --ignore-missing-imports"
else
  warn "Mypy not installed, skipping"
fi

# Type hints
check "Type hints present in classify.py" "grep -q '-> ClassifyResponse' app/api/endpoints/classify.py"
check "Docstring present in endpoint" "grep -q '\"\"\"' app/api/endpoints/classify.py"

#
# 14. Schemas Validation
#
section "1️⃣4️⃣  SCHEMAS VALIDATION"

check "ClassifyRequest schema exists" "test -f app/schemas/requests.py"
check "ClassifyRequestForm schema exists" "$PYTHON -c 'from app.schemas.requests import ClassifyRequestForm'"
check "ClassifyResponse schema exists" "$PYTHON -c 'from app.schemas.responses import ClassifyResponse'"
check "ResponseMeta schema exists" "$PYTHON -c 'from app.schemas.responses import ResponseMeta'"

#
# Summary
#
section "✅  RESUMEN EDV-59"

echo -e "${GREEN}PASS:${NC} $PASS"
echo -e "${RED}FAIL:${NC} $FAIL"
echo -e "${YELLOW}WARN:${NC} $WARN"

if [ "$FAIL" -eq 0 ]; then
  echo -e "\n${GREEN}🎉 EDV-59 COMPLETADO: Todos los criterios de aceptación pasan.${NC}"
  exit 0
else
  echo -e "\n${RED}❌ EDV-59 INCOMPLETO: Revisa los checks fallidos arriba.${NC}"
  exit 1
fi
