# === Stage 1: Build frontend ===
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# === Stage 2: Python backend + frontend dist ===
FROM python:3.11-slim
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Backend code (preserve directory structure for relative paths)
COPY backend/ /app/backend/

# Frontend build output
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
RUN test -f /app/frontend/dist/index.html || (echo "ERROR: frontend/dist/index.html missing — Vite build failed" && exit 1)

# Uploads directory
RUN mkdir -p /app/backend/uploads/results \
             /app/backend/uploads/calibration/predictions

EXPOSE 5001

CMD gunicorn \
    --chdir /app/backend \
    --bind "0.0.0.0:${PORT:-5001}" \
    --workers 2 \
    --threads 4 \
    --timeout 300 \
    --access-logfile - \
    "app:create_app()"
