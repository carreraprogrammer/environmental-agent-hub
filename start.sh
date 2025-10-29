#!/bin/bash
# =============================================================================
# Railway Startup Script
# =============================================================================

# Set default port if not provided by Railway
PORT=${PORT:-8000}

echo "Starting application on port $PORT"
echo "Environment PORT variable: $PORT"

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info