#!/bin/bash
# =============================================================================
# Railway Startup Script
# =============================================================================

# Set default port if not provided by Railway
export PORT=${PORT:-8000}

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1