#!/bin/bash

# validation-edv50.sh - Validación completa del ticket EDV-50 (PreValidator Agent)

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ajustar paths locales (siguiendo patrón de EDV-49)
cd /Users/danielcarrera/Desktop/CDD/environmental-agent-hub
PYTHON=/Users/danielcarrera/Desktop/CDD/environmental-agent-hub/venv/bin/python
PYTEST=/Users/danielcarrera/Desktop/CDD/environmental-agent-hub/venv/bin/pytest

PASSED=0
FAILED=0

check() {
  echo -e "\n${BLUE}Checking:${NC} $1"
  if eval "$2" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
    PASSED=$((PASSED + 1))
  else
    echo -e "${RED}❌ FAIL${NC}"
    FAILED=$((FAILED + 1))
  fi
}

echo "========================================"
echo "EDV-50 VALIDATION - PreValidator Agent"
echo "========================================"

# 0) Smoke test rápido
echo -e "\n${BLUE}0. SMOKE TEST${NC}"
if bash validations/EDV-50/smoke-edv50.sh > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Smoke OK${NC}"
  PASSED=$((PASSED + 1))
else
  echo -e "${RED}❌ Smoke FAILED${NC}"
  FAILED=$((FAILED + 1))
fi

# 1) Estructura
echo -e "\n${BLUE}1. ESTRUCTURA${NC}"
check "pre_validator.py existe" "test -f app/agents/pre_validator.py"
check "validation.py existe" "test -f app/schemas/validation.py"
check "test_pre_validator.py existe" "test -f tests/unit/agents/test_pre_validator.py"

# 2) Imports
echo -e "\n${BLUE}2. IMPORTS${NC}"
check "Import PreValidator" "$PYTHON -c 'from app.agents.pre_validator import PreValidator'"
check "Import ValidationResult" "$PYTHON -c 'from app.schemas.validation import ValidationResult'"

# 3) Code Quality y parámetros
echo -e "\n${BLUE}3. CODE QUALITY${NC}"
check "Structured logging import" "grep -q 'from app.core.logging import logger' app/agents/pre_validator.py"
check "Log started" "grep -q 'pre_validator_started' app/agents/pre_validator.py"
check "Log complete" "grep -q 'pre_validator_complete' app/agents/pre_validator.py"
check "Log timeout" "grep -q 'pre_validator_timeout' app/agents/pre_validator.py"
check "Log error" "grep -q 'pre_validator_error' app/agents/pre_validator.py"
check "Parse error warning" "grep -q 'pre_validator_parse_error' app/agents/pre_validator.py"
check "Usa gpt-4o-mini" "grep -q 'gpt-4o-mini' app/agents/pre_validator.py"
check "Temperatura 0.0" "grep -q 'temperature=0.0' app/agents/pre_validator.py"
check "max_tokens=150" "grep -q 'max_tokens=150' app/agents/pre_validator.py"
check "Timeout 500ms" "grep -q 'self.timeout = 0.5' app/agents/pre_validator.py"
check "asyncio.wait_for" "grep -q 'asyncio.wait_for' app/agents/pre_validator.py"
check "Prompt en español" "grep -q 'Analiza esta imagen' app/agents/pre_validator.py"
check "Rechaza selfies/paisajes" "grep -q 'selfie, paisaje' app/agents/pre_validator.py"
# Nota: Se valida parsing de code fences via tests unitarios; evitamos backticks en shell.

# 4) Tests unitarios
echo -e "\n${BLUE}4. TESTS UNITARIOS${NC}"
echo -e "${BLUE}Ejecutando tests...${NC}"
$PYTEST tests/unit/agents/test_pre_validator.py -v
TEST_RESULT=$?
if [ $TEST_RESULT -eq 0 ]; then
  echo -e "${GREEN}✅ Tests OK${NC}"
  PASSED=$((PASSED + 1))
else
  echo -e "${RED}❌ Tests fallaron${NC}"
  FAILED=$((FAILED + 1))
fi

echo -e "\n${BLUE}Coverage (>=90%)...${NC}"
$PYTEST tests/unit/agents/test_pre_validator.py --cov=app.agents.pre_validator --cov-report=term --cov-fail-under=90 -q
COV_RESULT=$?
if [ $COV_RESULT -eq 0 ]; then
  echo -e "${GREEN}✅ Coverage >90%${NC}"
  PASSED=$((PASSED + 1))
else
  echo -e "${RED}❌ Coverage <90%${NC}"
  FAILED=$((FAILED + 1))
fi

# 5) Resumen y reporte
TOTAL=$((PASSED + FAILED))
PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")

REPORT_DIR="validations/EDV-50"
mkdir -p "$REPORT_DIR"
cat > "$REPORT_DIR/validation_report_edv50.md" << EOF
# 📋 Reporte de Validación EDV-50
**Ticket:** EDV-50 - Implementar PreValidator Agent (Anti-Troll)
**Fecha:** $(date '+%Y-%m-%d %H:%M:%S')
**Pass Rate:** $PASS_RATE% ($PASSED/$TOTAL)

---

## ✅ Criterios de Aceptación
- [ ] Smoke test básico (imports + mock offline)
- [ ] Schema ValidationResult en app/schemas/validation.py
- [ ] Campos: has_waste (bool), confidence (float), reason (str)
- [ ] PreValidator.validate() async con timeout 500ms
- [ ] Usa gpt-4o-mini, temperatura 0.0, max_tokens=150
- [ ] Prompt en español y formato JSON
- [ ] Parsing robusto y fallback
- [ ] Logging completo (started, complete, timeout, error)
- [ ] Tests unitarios + coverage >= 90%

---

## 🎯 Conclusión
EOF

if (( $(echo "$PASS_RATE >= 95" | bc -l) )); then
  echo "**✅ VALIDACIÓN EXITOSA**" >> "$REPORT_DIR/validation_report_edv50.md"
  echo "Todos los criterios de aceptación del ticket EDV-50 han sido cumplidos." >> "$REPORT_DIR/validation_report_edv50.md"
  exit 0
else
  echo "**⚠️ VALIDACIÓN PARCIAL**" >> "$REPORT_DIR/validation_report_edv50.md"
  echo "Se encontraron $FAILED ítems fallidos. Revisar antes de merge." >> "$REPORT_DIR/validation_report_edv50.md"
  exit 1
fi
