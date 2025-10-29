# =============================================================================
# Agent Hub - Railway Optimized Dockerfile
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code and startup script
COPY app/ ./app/
COPY config/ ./config/
COPY start.sh ./start.sh

# Make startup script executable
RUN chmod +x start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port (Railway will set $PORT)
EXPOSE 8000

# Use startup script
CMD ["./start.sh"]