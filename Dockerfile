# ── Stage 1: Build React frontend ──────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python deps (Alpine) ─────────────────────────────
FROM python:3.12-alpine AS python-build

RUN apk add --no-cache \
    build-base \
    file-dev

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    python-magic \
    slowapi \
    markitdown \
    && pip uninstall -y \
    pydub \
    SpeechRecognition 2>/dev/null || true

# ── Stage 3: Final runtime image (Alpine) ─────────────────────
FROM python:3.12-alpine

WORKDIR /app

# Runtime deps — Alpine package names
RUN apk add --no-cache \
    libmagic \
    file \
    poppler-utils \
    tesseract-ocr

COPY --from=python-build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Non-root user for security
RUN adduser -D -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser backend/ ./backend/
COPY --from=frontend-build --chown=appuser /app/frontend/dist ./frontend/dist

EXPOSE 8000

ENV PORT=8000
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
