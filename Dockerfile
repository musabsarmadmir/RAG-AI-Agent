# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for healthcheck
RUN apt-get update -y && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app /app/app
COPY rag-data /app/rag-data

# Default envs (override in Azure)
ENV CORS_ORIGINS="*"

EXPOSE 8000

# Healthcheck on /health
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD curl -f http://localhost:8000/health || exit 1

# Run the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
