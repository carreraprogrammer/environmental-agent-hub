#!/bin/bash

# EDV-50 SMOKE - PreValidator Agent

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Paths (alineado con otros scripts de validations)
cd /Users/danielcarrera/Desktop/CDD/environmental-agent-hub
PYTHON=/Users/danielcarrera/Desktop/CDD/environmental-agent-hub/venv/bin/python

echo -e "${BLUE}EDV-50 SMOKE - PreValidator${NC}"

echo -e "\n${BLUE}1) Imports básicos${NC}"
$PYTHON - << 'PY'
from app.agents.pre_validator import PreValidator
from app.schemas.validation import ValidationResult
print('✅ Imports OK: PreValidator, ValidationResult')
PY

echo -e "\n${BLUE}2) Smoke offline (sin red, mock API)${NC}"
$PYTHON - << 'PY'
import asyncio
from app.agents.pre_validator import PreValidator
from app.schemas.validation import ValidationResult

async def main():
    v = PreValidator()
    async def fake_call(*args, **kwargs):
        return ValidationResult(has_waste=True, confidence=0.9, reason='Smoke mock ok')
    # inyectamos mock evitando llamada real
    setattr(v, '_call_gpt4o_mini', fake_call)
    res = await v.validate(b'fake', 'smoke-offline')
    print(f"Has waste: {res.has_waste}; Conf: {res.confidence}; Reason: {res.reason}")

asyncio.run(main())
PY

echo -e "\n${BLUE}3) Smoke online (opcional)${NC}"
IMG_PATH="${1:-}"
if [ -n "$IMG_PATH" ] && [ -f "$IMG_PATH" ]; then
  echo -e "Usando imagen: $IMG_PATH"
else
  echo -e "${YELLOW}Sin imagen proporcionada. Para ejecutar online: smoke-edv50.sh /ruta/a/imagen.jpg${NC}"
  echo -e "${YELLOW}Saltando prueba online.${NC}"
  exit 0
fi

if [ -z "${OPENAI_API_KEY:-}" ] || [ "$OPENAI_API_KEY" = "changeme-openai" ]; then
  echo -e "${YELLOW}OPENAI_API_KEY no definido o placeholder. Usar .env o export OPENAI_API_KEY=...${NC}"
  echo -e "${YELLOW}Saltando prueba online.${NC}"
  exit 0
fi

echo -e "${BLUE}Ejecutando llamada real (timeout relajado a 3s solo para smoke)${NC}"
$PYTHON - << PY
import asyncio
from app.agents.pre_validator import PreValidator

async def main():
    v = PreValidator()
    v.timeout = 3.0  # relajamos para smoke interactivo
    with open("$IMG_PATH", "rb") as f:
        data = f.read()
    try:
        res = await v.validate(data, 'smoke-online')
        print(f"✅ Online OK | has_waste={res.has_waste} conf={res.confidence:.2f} reason={res.reason}")
    except Exception as e:
        print(f"⚠️ Online falló: {e}")

asyncio.run(main())
PY

echo -e "\n${GREEN}SMOKE DONE${NC}"

