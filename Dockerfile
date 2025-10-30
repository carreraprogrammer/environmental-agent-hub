# =============================================================================
# Agent Hub - Railway Optimized Dockerfile
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies - minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy requirements first for better caching
COPY requirements-prod.txt .

# Install Python dependencies - production only
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY app/ ./app/
COPY config/ ./config/
COPY start.sh ./start.sh

# Make script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Start command
CMD ["./start.sh"]
