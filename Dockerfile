# =============================================================================
# Agent Hub - Railway Optimized Dockerfile
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with better error handling
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and startup script
COPY app/ ./app/
COPY config/ ./config/
COPY start.sh ./start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Make startup script executable and create non-root user for security
RUN chmod +x start.sh && \
    useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Start command using startup script
CMD ["./start.sh"]