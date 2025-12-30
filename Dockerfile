# Multi-stage Dockerfile for RAG AI Agent

# 1) Builder image (installs dependencies)
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for building wheels (faiss, sentence-transformers, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir uvicorn[standard]

# 2) Runtime image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user
RUN useradd -m appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ app/
COPY scripts/ scripts/
COPY rag-data/ rag-data/
COPY docs/ docs/
COPY requirements.txt ./

# Ensure rag-data exists and is writable
RUN mkdir -p rag-data/providers \
    && chown -R appuser:appuser /app

USER appuser

# Expose FastAPI default port
EXPOSE 8000

# Default environment placeholders (override in docker-compose or kubernetes)
ENV API_KEY=dev-key-123 \
    CORS_ORIGINS="*" \
    FIRESTORE_ENABLED=0

# Note: for Firestore in Docker you must mount the service account JSON and set
# GOOGLE_APPLICATION_CREDENTIALS to its path via environment variables.

# Run the API with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
