#!/usr/bin/env bash
# validation-edv64.sh - Validación completa del ticket EDV-64
# ConsensusClassificationAgent (Multi-Model Ensemble) + Integración en Pipeline

set -euo pipefail

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Evitar issues de Pydantic con CORS_ORIGINS heredado
unset CORS_ORIGINS 2>/dev/null || true

# Resolver root del proyecto (environmental-agent-hub/)
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
echo " EDV-64 VALIDATION - Multi-Model Consensus Agent"
echo "======================================================="
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Python: $PYTHON"
echo "Pytest: $PYTEST"
echo ""

#
# 0. Entorno / prerequisitos
#
section "0️⃣  ENVIRONMENT & PRE-REQUISITES"

check "Running inside environmental-agent-hub" "[ -f app/main.py ]"
check "Virtualenv Python exists" "test -x \"$PYTHON\""
check "Pytest exists" "test -x \"$PYTEST\""

#
# 1. ConsensusClassificationAgent (núcleo)
#
section "1️⃣  CONSENSUS AGENT CORE"

check "consensus_classifier.py existe" "test -f app/agents/consensus_classifier.py"
check "ConsensusClassificationAgent importable" "$PYTHON - <<'EOF'
from app.agents.consensus_classifier import ConsensusClassificationAgent
print(ConsensusClassificationAgent)
EOF"
check "Estrategias definidas (agreement/confidence/tie-breaker)" "grep -q 'consensus_strategy' app/agents/consensus_classifier.py"

#
# 2. Integración en Pipeline
#
section "2️⃣  PIPELINE INTEGRATION"

check "Pipeline referencia ConsensusClassificationAgent" "grep -q 'ConsensusClassificationAgent' app/orchestrator/pipeline.py"
# Pipeline consensus activation test (via pytest)
echo -e "\n${BLUE}Checking:${NC} Pipeline activa consensus cuando CLASSIFIER_MODEL=consensus"
if CLASSIFIER_MODEL=consensus $PYTEST tests/integration/test_consensus_scenarios.py::test_pipeline_consensus_mode_fast_path -q > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAIL++))
fi
# Summary
#
section "✅  RESUMEN EDV-64"

echo -e "${GREEN}PASS:${NC} $PASS"
echo -e "${RED}FAIL:${NC} $FAIL"
echo -e "${YELLOW}WARN:${NC} $WARN"

if [ "$FAIL" -eq 0 ]; then
  echo -e "\n${GREEN}🎉 EDV-64 COMPLETADO: Todos los checks pasan.${NC}"
  exit 0
else
  echo -e "\n${RED}❌ EDV-64 INCOMPLETO: Revisa los checks fallidos.${NC}"
  exit 1
fi
