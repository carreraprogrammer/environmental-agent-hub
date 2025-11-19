#!/usr/bin/env bash
# validation-edv55.sh - Validación completa del ticket EDV-55
# WasteTypeMapper Agent - Hybrid catalog (Backend + local fallback)

set -euo pipefail

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
echo " EDV-55 VALIDATION - WasteTypeMapper Agent"
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
# 1. Estructura WasteTypeMapper + catálogo local
#
section "1️⃣  WASTETYPEMAPPER STRUCTURE & LOCAL CATALOG"

check "WasteTypeMapper agent file exists" "test -f app/agents/waste_type_mapper.py"
check "WasteTypeMapper importable" "$PYTHON -c 'from app.agents.waste_type_mapper import WasteTypeMapper; print(WasteTypeMapper)'"

check "Backend waste types YAML exists" "test -f config/backend_waste_types.yaml"
check "YAML has at least 12 waste_types" "$PYTHON - << 'EOF'
import yaml
from pathlib import Path

path = Path('config/backend_waste_types.yaml')
data = yaml.safe_load(path.read_text(encoding='utf-8'))
assert isinstance(data, dict)
wt = data.get('waste_types') or []
assert isinstance(wt, list)
assert len(wt) >= 12
EOF"

check "YAML entries have code and category" "$PYTHON - << 'EOF'
import yaml
from pathlib import Path

data = yaml.safe_load(Path('config/backend_waste_types.yaml').read_text(encoding='utf-8'))
for wt in data.get('waste_types', []):
    assert 'code' in wt
    assert 'category' in wt
EOF"

check "Hardcoded catalog has required 12 codes" "$PYTHON - << 'EOF'
from app.agents.waste_type_mapper import WasteTypeMapper

mapper = WasteTypeMapper()
catalog = mapper._get_hardcoded_catalog()
codes = {wt['code'] for wt in catalog}
required = {
    'PET_BOTTLE_500ML',
    'PET_BOTTLE_1500ML',
    'HDPE_BOTTLE',
    'PLASTIC_OTHER',
    'ALUMINUM_CAN',
    'STEEL_CAN',
    'GLASS_BOTTLE_CLEAR',
    'GLASS_BOTTLE_COLORED',
    'PAPER_WHITE_A4',
    'CARDBOARD_BOX',
    'NEWSPAPER',
    'FOOD_WASTE',
}
assert required.issubset(codes)
EOF"

#
# 2. Sincronización con Backend (initialize + refresh)
#
section "2️⃣  BACKEND SYNC (INITIALIZE & REFRESH)"

check "BackendClient.get_waste_types_catalog exists" "$PYTHON - << 'EOF'
from inspect import iscoroutinefunction
from app.services.backend_client import BackendClient

client = BackendClient()
assert hasattr(client, 'get_waste_types_catalog')
assert iscoroutinefunction(client.get_waste_types_catalog)
EOF"

check "BackendClient uses /environmental/waste-types endpoint" "grep -q '/environmental/waste-types' app/services/backend_client.py"

check "WasteTypeMapper.initialize() syncs backend catalog (unit tests)" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestInitialization'"

check "WasteTypeMapper.refresh_if_needed() behaves correctly (unit tests)" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestRefresh'"

#
# 3. Integración en vivo con Backend (opcional)
#
section "3️⃣  BACKEND LIVE INTEGRATION (OPTIONAL)"

if [ "${RUN_BACKEND_INTEGRATION:-}" = "1" ]; then
  check "Live Backend: WasteTypeMapper can sync real catalog" "$PYTHON - << 'EOF'
import asyncio
from app.agents.waste_type_mapper import WasteTypeMapper

async def main() -> None:
    mapper = WasteTypeMapper()
    await mapper.initialize('edv55-backend-live')
    catalog = mapper.backend_catalog
    assert catalog is not None, 'backend_catalog is None; ensure Backend is running and BACKEND_API_URL is correct'
    assert isinstance(catalog, list) and len(catalog) > 0, 'backend_catalog must be a non-empty list'
    for wt in catalog[:3]:
        assert 'code' in wt and 'category' in wt

asyncio.run(main())
EOF"
else
  warn "Backend live integration skipped (set RUN_BACKEND_INTEGRATION=1 and run Rails on BACKEND_API_URL to enable)"
fi

#
# 4. Lógica principal de mapping por material
#
section "4️⃣  MATERIAL MAPPING LOGIC"

check "Unit tests for plastic mapping" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestMappingPlastic'"
check "Unit tests for metal mapping" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestMappingMetal'"
check "Unit tests for glass mapping" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestMappingGlass'"
check "Unit tests for paper mapping" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestMappingPaper'"
check "Unit tests for organic/other mapping" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestMappingOrganic or TestMappingOther'"

check "Interactive mapping examples (PLASTIC, METAL, GLASS)" "$PYTHON - << 'EOF'
from app.agents.waste_type_mapper import WasteTypeMapper
from app.schemas.classification import Material

mapper = WasteTypeMapper()

code = mapper.map_to_waste_type_code(
    Material.PLASTIC,
    {'material_specific': 'PET'},
    520.0,
    'validation-edv55',
)
assert code == 'PET_BOTTLE_500ML'

code = mapper.map_to_waste_type_code(
    Material.METAL,
    {'material_specific': 'aluminum'},
    355.0,
    'validation-edv55',
)
assert code == 'ALUMINUM_CAN'

code = mapper.map_to_waste_type_code(
    Material.GLASS,
    {'color': 'clear'},
    330.0,
    'validation-edv55',
)
assert code == 'GLASS_BOTTLE_CLEAR'
EOF"

#
# 5. Fallbacks, helpers y garantías
#
section "5️⃣  FALLBACKS, HELPERS & GUARANTEES"

check "Helper methods behave correctly (get_active_catalog/get_valid_codes)" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestHelpers'"
check "Fallback behavior covered by unit tests" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestFallbacks'"
check "Edge cases covered (never None/empty)" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestEdgeCases'"

check "get_valid_codes() returns required codes" "$PYTHON - << 'EOF'
from app.agents.waste_type_mapper import WasteTypeMapper

mapper = WasteTypeMapper()
codes = mapper.get_valid_codes()
required = ['PET_BOTTLE_500ML', 'ALUMINUM_CAN', 'GLASS_BOTTLE_CLEAR']
for code in required:
    assert code in codes
EOF"

#
# 6. Logging estructurado
#
section "6️⃣  STRUCTURED LOGGING"

check "WasteTypeMapper uses structured logger" "grep -q 'from app.core.logging import logger' app/agents/waste_type_mapper.py"
check "Logging events covered by unit tests" "$PYTEST -q tests/unit/agents/test_waste_type_mapper.py -k 'TestLogging'"

#
# 7. Test suite completa + coverage
#
section "7️⃣  UNIT TESTS & COVERAGE"

check "WasteTypeMapper unit test file exists" "test -f tests/unit/agents/test_waste_type_mapper.py"
check "Run full WasteTypeMapper unit test suite" "$PYTEST tests/unit/agents/test_waste_type_mapper.py -q"

check "Coverage report for WasteTypeMapper (target ≥85%)" "$PYTEST tests/unit/agents/test_waste_type_mapper.py --cov=app.agents.waste_type_mapper --cov-report=term-missing"

#
# 8. Calidad de código (pylint, mypy, isort)
#
section "8️⃣  CODE QUALITY (PYLINT, MYPY, ISORT)"

check "Pylint score (target ≥8.5)" "$PYTHON -m pylint app/agents/waste_type_mapper.py"
check "Mypy type checking without errors" "$PYTHON -m mypy app/agents/waste_type_mapper.py"
check "Isort import ordering correct" "$PYTHON -m isort --check-only app/agents/waste_type_mapper.py"

#
# 9. Resumen
#
section "9️⃣  SUMMARY"

echo -e "${GREEN}PASS: $PASS${NC}"
echo -e "${RED}FAIL: $FAIL${NC}"
echo -e "${YELLOW}WARN: $WARN${NC}"

if [ "$FAIL" -eq 0 ]; then
  echo -e "\n${GREEN}✅ EDV-55 READY FOR CLOSURE${NC}"
else
  echo -e "\n${RED}❌ EDV-55 HAS FAILING CHECKS${NC}"
  exit 1
fi

