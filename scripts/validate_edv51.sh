#!/usr/bin/env bash
# validate_edv51.sh - Wrapper para ejecutar la validación EDV-51

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [ ! -x "validations/EDV-51/validation-edv51.sh" ]; then
  echo "❌ validations/EDV-51/validation-edv51.sh no existe o no es ejecutable"
  exit 1
fi

exec validations/EDV-51/validation-edv51.sh

