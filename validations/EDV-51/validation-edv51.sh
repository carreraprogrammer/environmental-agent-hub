#!/usr/bin/env bash
# validation-edv51.sh - Validación completa del ticket EDV-51
# Core Classification Pipeline V4 + Architecture Spec Update

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
echo " EDV-51 VALIDATION - Core Classification Pipeline V4"
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
# 1. PreValidator V4 (Roboflow anti-troll)
#
section "1️⃣  PREVALIDATOR V4 - ROBOFLOW ANTI-TROLL"

check "PreValidator file exists" "test -f app/agents/pre_validator.py"
check "PreValidator importable" "$PYTHON -c 'from app.agents.pre_validator import PreValidator'"

# 1.1 Roboflow integration
check "PreValidator mentions Roboflow" "grep -qi 'roboflow' app/agents/pre_validator.py"
check "Roboflow waste detection tests" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'TestRoboflowWasteDetection'"

# 1.2 Roboflow config (thresholds & model)
check "Roboflow configuration tests" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'TestRoboflowConfig'"

# 1.3 Two-layer validation behaviour
check "Two-layer validation tests" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'TestTwoLayerValidation'"
check "Rejects no waste" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'test_rejects_no_waste_when_no_detections'"
check "Accepts waste" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'test_accepts_waste_when_detections_present'"

# 1.4 ValidationResult V4 schema
check "ValidationResult schema updated (V4)" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'TestValidationResultSchema'"

# 1.5 Fallback behaviour on Roboflow errors
check "Roboflow timeout fallback" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'test_roboflow_timeout_fallback'"
check "Roboflow error fallback" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'test_roboflow_error_fallback'"

# 1.6 Latency (p95 < 500ms)
check "PreValidator latency performance" "$PYTEST -q tests/performance/test_prevalidator_latency.py"

# 1.7 Metadata logging
check "Roboflow metadata logging" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py -k 'TestRoboflowMetadataLogging'"

# 1.8 Anti-troll behaviour with real images
check "PreValidator anti-troll integration" "$PYTEST -q tests/integration/test_prevalidator_antitroll.py"

#
# 2. MaterialClassifier unified agent
#
section "2️⃣  MATERIALCLASSIFIER - UNIFIED CLASSIFIER"

# 2.1 File renaming
check "material_classifier.py exists" "test -f app/agents/material_classifier.py"
check "Legacy classifier.py removed" "test ! -f app/agents/classifier.py"

# 2.2 Complete classification in one call
check "MaterialClassifier complete classification" "$PYTEST -q tests/unit/test_material_classifier.py::test_complete_classification"

# 2.3 Confidences per field
check "MaterialClassifier confidence per field" "$PYTEST -q tests/unit/test_material_classifier.py::test_confidence_per_field"

# 2.4 Partial success behaviour
check "Partial success - low volume confidence" "$PYTEST -q tests/unit/test_material_classifier.py::test_confidence_per_field"
check "Reject low material confidence" "$PYTEST -q tests/unit/test_material_classifier.py::test_reject_low_material_confidence"

# 2.5 Prompt structure
check "Prompt structure for unified classifier" "$PYTEST -q tests/unit/test_material_classifier.py::test_prompt_structure"

# 2.6 Multi-adapter integration (OpenAI, Anthropic, Gemini)
if [ -n "${RUN_INTEGRATION_TESTS:-}" ]; then
  check "MaterialClassifier OpenAI integration" "RUN_INTEGRATION_TESTS=1 $PYTEST -q tests/integration/test_material_classifier_openai.py"
  check "MaterialClassifier Anthropic integration" "RUN_INTEGRATION_TESTS=1 $PYTEST -q tests/integration/test_material_classifier_anthropic.py"
  check "MaterialClassifier Gemini integration" "RUN_INTEGRATION_TESTS=1 $PYTEST -q tests/integration/test_material_classifier_gemini.py"
else
  warn "MaterialClassifier integration tests skipped (set RUN_INTEGRATION_TESTS=1 and API keys to enable)"
fi

# 2.7 Adapters parsing new schema
check "Adapter unit tests for MaterialClassificationResult" "$PYTEST -q tests/unit/test_openai_adapter.py tests/unit/test_anthropic_adapter.py -k 'parse_material_classification'"

# 2.8 Latency (p95 < 1500ms)
check "MaterialClassifier latency performance" "$PYTEST -q tests/performance/test_material_classifier_latency.py"

# 2.9 Structured logging
check "MaterialClassifier structured logging" "$PYTEST -q tests/unit/test_material_classifier.py::test_structured_logging"

#
# 3. Architecture Specs V4 & docs
#
section "3️⃣  ARCHITECTURE SPECS V4 & DOCS"

check "Architecture spec V4 created" "test -f agents-specs/V4/architecture-spec-agents_v4.md"
check "Project spec V4 created" "test -f agents-specs/V4/project-spec-agents_v4.md"
check "Migration guide V3 → V4 created" "test -f docs/MIGRATION_V3_TO_V4.md"

check "MaterialClassifier documented in architecture spec" "grep -q 'MaterialClassifier' agents-specs/V4/architecture-spec-agents_v4.md"
check "Edge computing explained in architecture spec" "grep -q 'Edge Computing' agents-specs/V4/architecture-spec-agents_v4.md"
check "Partial success documented in project spec" "grep -q 'partial success' agents-specs/V4/project-spec-agents_v4.md"

check "Spec documents PreValidator → MaterialClassifier contract" "grep -q 'PreValidator → MaterialClassifier' agents-specs/V4/architecture-spec-agents_v4.md"
check "Spec documents MaterialClassifier → WasteTypeMapper contract" "grep -q 'MaterialClassifier → WasteTypeMapper' agents-specs/V4/architecture-spec-agents_v4.md"

check "Spec documents material_classifier_latency_ms metric" "grep -q 'material_classifier_latency_ms' agents-specs/V4/architecture-spec-agents_v4.md"
check "Spec documents material_classifier_partial_success_rate metric" "grep -q 'material_classifier_partial_success_rate' agents-specs/V4/architecture-spec-agents_v4.md"

#
# 4. Test suites & coverage
#
section "4️⃣  TEST SUITES & COVERAGE"

check "PreValidator V4 unit tests" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py"
check "MaterialClassifier unit tests" "$PYTEST -q tests/unit/test_material_classifier.py"
check "Classification pipeline V4 integration tests" "$PYTEST -q tests/integration/test_classification_pipeline_v4.py"
check "Performance tests (PreValidator, MaterialClassifier)" "$PYTEST -q tests/performance/test_prevalidator_latency.py tests/performance/test_material_classifier_latency.py"
check "All agent tests pass" "$PYTEST -q tests/unit/agents/test_pre_validator_v4.py tests/unit/test_material_classifier.py tests/integration/test_classification_pipeline_v4.py"

#
# 5. Documentation & changelog
#
section "5️⃣  DOCUMENTATION & CHANGELOG"

check "README mentions V4 Architecture" "grep -q 'V4 Architecture' README.md"
check "README links architecture-spec-agents_v4.md" "grep -q 'architecture-spec-agents_v4.md' README.md"
check "Migration guide referenced in README" "grep -q 'MIGRATION_V3_TO_V4.md' README.md"

check "CHANGELOG contains 4.0.0 entry" "grep -q '\\[4.0.0\\]' CHANGELOG.md"
check "CHANGELOG mentions MaterialClassifier" "grep -q 'MaterialClassifier' CHANGELOG.md"

#
# Summary
#
section "✅  RESUMEN EDV-51"

echo -e "${GREEN}PASS:${NC} $PASS"
echo -e "${RED}FAIL:${NC} $FAIL"
echo -e "${YELLOW}WARN:${NC} $WARN"

if [ "$FAIL" -eq 0 ]; then
  echo -e "\n${GREEN}🎉 EDV-51 COMPLETADO: Todos los criterios de aceptación pasan.${NC}"
  exit 0
else
  echo -e "\n${RED}❌ EDV-51 INCOMPLETO: Revisa los checks fallidos arriba.${NC}"
  exit 1
fi
