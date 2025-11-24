#!/usr/bin/env bash
# test_backend_integration.sh - Test integration with Rails backend

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/venv/bin/python"
PYTEST="$PROJECT_ROOT/venv/bin/pytest"

echo "==========================================================="
echo " BACKEND INTEGRATION TESTS - Rails + Python Hub"
echo "==========================================================="
echo ""

# Check if BACKEND_API_URL is set
if [ -z "${BACKEND_API_URL:-}" ]; then
    echo -e "${YELLOW}⚠️  BACKEND_API_URL not set. Using default: http://localhost:3000/api/v1${NC}"
    export BACKEND_API_URL="http://localhost:3000/api/v1"
fi

echo -e "${BLUE}Configuration:${NC}"
echo "  Backend URL: $BACKEND_API_URL"
echo "  Backend Token: ${BACKEND_SERVICE_TOKEN:-<not set>}"
echo "  Organization ID: ${BACKEND_ORGANIZATION_ID:-<not set>}"
echo ""

# Check if Rails backend is running
echo -e "${BLUE}Checking Rails backend...${NC}"
BACKEND_BASE_URL="${BACKEND_API_URL%/api/v1}"

if curl -s -f "$BACKEND_BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Rails backend is running at $BACKEND_BASE_URL${NC}"
else
    echo -e "${RED}❌ Rails backend is NOT running at $BACKEND_BASE_URL${NC}"
    echo ""
    echo "To start Rails backend:"
    echo "  cd /path/to/rails/backend"
    echo "  rails s  # Starts on port 3000"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo ""
echo -e "${BLUE}Running backend integration tests...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run tests with --backend flag
$PYTEST tests/integration/test_backend_integration.py -v --backend --tb=short

echo ""
echo -e "${GREEN}✅ Backend integration tests completed!${NC}"
