#!/bin/bash
# =============================================================================
# Railway Startup Script
# =============================================================================

# Set default port if not provided by Railway
export PORT=${PORT:-8000}

# Set minimal environment for startup
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Debug info
echo "Starting application on port $PORT"
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

# Start the application with verbose output
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info