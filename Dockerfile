# Multi-stage Dockerfile for Job Radar

# Stage 1: Build React Frontend UI
FROM node:20-alpine AS frontend-builder
WORKDIR /app/ui

COPY ui/package*.json ./
RUN npm ci

COPY ui/ ./
RUN npm run build

# Stage 2: Production Python Backend
FROM python:3.11-slim AS runner
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy project files needed for setuptools installation
COPY pyproject.toml README.md* ./
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Install Python package and Playwright library
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy built frontend static bundle from Stage 1 into FastAPI static directory
COPY --from=frontend-builder /app/src/job_radar/static/ ./src/job_radar/static/

ENV PYTHONPATH=/app/src
ENV PORT=18080

EXPOSE 18080

CMD ["uvicorn", "job_radar.main:app", "--host", "0.0.0.0", "--port", "18080"]
