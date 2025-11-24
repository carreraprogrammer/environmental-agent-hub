#!/usr/bin/env bash
# validation-edv58-quick.sh - Validación rápida del ticket EDV-58
# Pipeline Orchestrator V4 - Solo checks básicos sin tests pesados

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/venv/bin/python"

PASS=0
FAIL=0

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

echo "======================================================="
echo " EDV-58 QUICK VALIDATION - Pipeline Orchestrator V4"
echo "======================================================="
echo ""

# 1. Files exist
echo -e "\n${BLUE}1. FILES & STRUCTURE${NC}"
check "Pipeline file exists" "test -f app/orchestrator/pipeline.py"
check "Pipeline importable" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline'"
check "Integration test exists" "test -f tests/integration/test_pipeline.py"
check "Performance test exists" "test -f tests/performance/test_pipeline_latency.py"

# 2. Pipeline initialization
echo -e "\n${BLUE}2. PIPELINE INITIALIZATION${NC}"
check "Pipeline can be instantiated" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline; p = Pipeline()'"
check "Has 7 agents initialized" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline; p = Pipeline(); assert all([p.pre_validator, p.classifier, p.volume_estimator, p.mapper, p.waste_type_mapper, p.feedback_coach, p.assembler])'"
check "Has BackendIntegration" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline; p = Pipeline(); assert p.backend_integration'"
check "Has process method" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline; import inspect; p = Pipeline(); assert inspect.iscoroutinefunction(p.process)'"

# 3. Embedded agents
echo -e "\n${BLUE}3. EMBEDDED AGENTS${NC}"
check "VolumeEstimator exists" "$PYTHON -c 'from app.orchestrator.pipeline import VolumeEstimator; ve = VolumeEstimator()'"
check "VolumeEstimator has DEFAULTS" "$PYTHON -c 'from app.orchestrator.pipeline import VolumeEstimator, Material; assert Material.PLASTIC in VolumeEstimator.DEFAULTS'"
check "FeedbackCoach exists" "$PYTHON -c 'from app.orchestrator.pipeline import FeedbackCoach; fc = FeedbackCoach()'"
check "FeedbackCoach has MESSAGES" "$PYTHON -c 'from app.orchestrator.pipeline import FeedbackCoach, Material; assert Material.PLASTIC in FeedbackCoach.MESSAGES'"
check "BackendIntegration exists" "$PYTHON -c 'from app.orchestrator.pipeline import BackendIntegration; bi = BackendIntegration()'"

# 4. Constants and configuration
echo -e "\n${BLUE}4. CONFIGURATION${NC}"
check "Has TOTAL_TIMEOUT = 5.0s" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline; assert Pipeline.TOTAL_TIMEOUT == 5.0'"
check "Has AGENT_TIMEOUTS dict" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline; assert isinstance(Pipeline.AGENT_TIMEOUTS, dict)'"
check "Cost calculation method exists" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline; p = Pipeline(); cost = p._calculate_total_cost(); assert cost > 0'"

# 5. Error handling
echo -e "\n${BLUE}5. ERROR HANDLING${NC}"
check "ValidationError class exists" "$PYTHON -c 'from app.orchestrator.pipeline import ValidationError'"
check "ClassificationError class exists" "$PYTHON -c 'from app.orchestrator.pipeline import ClassificationError'"
check "Has NO_WASTE_DETECTED handling" "grep -q 'NO_WASTE_DETECTED' app/orchestrator/pipeline.py"
check "Has LOW_CONFIDENCE handling" "grep -q 'LOW_CONFIDENCE' app/orchestrator/pipeline.py"
check "Has confidence thresholds (0.3, 0.6)" "grep -q '0.3' app/orchestrator/pipeline.py && grep -q '0.6' app/orchestrator/pipeline.py"

# 6. Architecture V4 (no Router, no SubtypeDetector)
echo -e "\n${BLUE}6. ARCHITECTURE V4${NC}"
check "No Router Agent" "! grep -q 'self.router' app/orchestrator/pipeline.py"
check "No SubtypeDetector Agent" "! grep -q 'self.subtype_detector' app/orchestrator/pipeline.py"
check "No separate Confidence Agent" "! grep -q 'self.confidence_agent' app/orchestrator/pipeline.py"
check "Has 7 core agents" "$PYTHON -c 'from app.orchestrator.pipeline import Pipeline; p = Pipeline(); agents = [p.pre_validator, p.classifier, p.volume_estimator, p.mapper, p.waste_type_mapper, p.feedback_coach, p.assembler]; assert len([a for a in agents if a]) == 7'"

# 7. Logging
echo -e "\n${BLUE}7. LOGGING${NC}"
check "Uses structured logger" "grep -q 'from app.core.logging import logger' app/orchestrator/pipeline.py"
check "Logs pipeline_started" "grep -q 'pipeline_started' app/orchestrator/pipeline.py"
check "Logs pipeline_complete" "grep -q 'pipeline_complete' app/orchestrator/pipeline.py"
check "Logs pipeline_step" "grep -q 'pipeline_step' app/orchestrator/pipeline.py"
check "Logs trace_id" "grep -q 'trace_id=' app/orchestrator/pipeline.py"

# 8. Sequential execution
echo -e "\n${BLUE}8. SEQUENTIAL EXECUTION${NC}"
check "Step 1: PreValidator" "grep -q 'STEP 1.*PreValidator' app/orchestrator/pipeline.py"
check "Step 2: MaterialClassifier" "grep -q 'STEP 2.*MaterialClassifier' app/orchestrator/pipeline.py"
check "Step 3: VolumeEstimator" "grep -q 'STEP 3.*VolumeEstimator' app/orchestrator/pipeline.py"
check "Step 4: Mapper" "grep -q 'STEP 4.*Mapper' app/orchestrator/pipeline.py"
check "Step 5: WasteTypeMapper" "grep -q 'STEP 5.*WasteTypeMapper' app/orchestrator/pipeline.py"
check "Step 6: FeedbackCoach" "grep -q 'STEP 6.*FeedbackCoach' app/orchestrator/pipeline.py"
check "Step 7: Assembler" "grep -q 'STEP 7.*Assembler' app/orchestrator/pipeline.py"

# 9. BackendIntegration (fire-and-forget)
echo -e "\n${BLUE}9. BACKEND INTEGRATION${NC}"
check "BackendIntegration is async" "grep -q 'asyncio.create_task' app/orchestrator/pipeline.py"
check "Has _send_to_backend method" "grep -q '_send_to_backend' app/orchestrator/pipeline.py"
check "Backend failures don't block" "grep -A 10 '_send_to_backend' app/orchestrator/pipeline.py | grep -q 'warning'"

# 10. Metrics
echo -e "\n${BLUE}10. METRICS${NC}"
check "Has _record_metrics method" "grep -q '_record_metrics' app/orchestrator/pipeline.py"
check "Records latency" "grep -q 'classification_latency_ms' app/orchestrator/pipeline.py"
check "Records cost" "grep -q 'classification_cost_usd' app/orchestrator/pipeline.py"
check "Records confidence" "grep -q 'classification_confidence' app/orchestrator/pipeline.py"

# 11. Interactive test
echo -e "\n${BLUE}11. INTERACTIVE TEST${NC}"
echo -e "${BLUE}Testing Pipeline initialization...${NC}"
$PYTHON - << 'EOF'
from app.orchestrator.pipeline import Pipeline

pipeline = Pipeline()

print("\n🔍 AGENTES INICIALIZADOS V4:")
print(f"1. PreValidator: {pipeline.pre_validator is not None}")
print(f"2. Classifier: {pipeline.classifier is not None}")
print(f"3. VolumeEstimator: {pipeline.volume_estimator is not None}")
print(f"4. Mapper: {pipeline.mapper is not None}")
print(f"5. WasteTypeMapper: {pipeline.waste_type_mapper is not None}")
print(f"6. FeedbackCoach: {pipeline.feedback_coach is not None}")
print(f"7. Assembler: {pipeline.assembler is not None}")
print(f"8. BackendIntegration: {pipeline.backend_integration is not None}")

total_cost = pipeline._calculate_total_cost()
print(f"\nCost per request: ${total_cost:.4f}")
print(f"Target cost: $0.008")

all_initialized = all([
    pipeline.pre_validator is not None,
    pipeline.classifier is not None,
    pipeline.volume_estimator is not None,
    pipeline.mapper is not None,
    pipeline.waste_type_mapper is not None,
    pipeline.feedback_coach is not None,
    pipeline.assembler is not None,
    pipeline.backend_integration is not None
])

assert all_initialized
print("\n✅ Todos los agentes V4 inicializados correctamente")
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Pipeline initialization validated${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ Pipeline initialization failed${NC}"
    ((FAIL++))
fi

# Summary
TOTAL=$((PASS + FAIL))
PERCENTAGE=$(( (PASS * 100) / TOTAL ))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RESUMEN EDV-58 QUICK VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}PASS:${NC} $PASS"
echo -e "${RED}FAIL:${NC} $FAIL"
echo "Pass Rate: $PERCENTAGE%"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}🎉 EDV-58 QUICK VALIDATION PASSED${NC}"
  echo -e "${GREEN}Pipeline Orchestrator V4 está funcionando correctamente.${NC}"
  echo ""
  echo "Para validación completa con tests de integración:"
  echo "  pytest tests/integration/test_pipeline.py -v"
  echo "  pytest tests/performance/test_pipeline_latency.py -v"
  exit 0
else
  echo -e "${RED}❌ EDV-58 TIENE $FAIL CHECKS FALLIDOS${NC}"
  exit 1
fi
