FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    APP_ENV=production FRONTEND_DIST=/app/frontend/dist \
    PORT=8000 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
WORKDIR /app
COPY requirements-backend.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements-backend.txt \
    && useradd --create-home --uid 10001 sauda
COPY backend/ ./backend/
COPY ml/ ./ml/
COPY models/ ./models/
COPY --from=frontend /build/frontend/dist ./frontend/dist/
COPY deploy/start.py ./deploy/start.py
USER sauda
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/v1/health/live', timeout=4)"
CMD ["python", "deploy/start.py"]
