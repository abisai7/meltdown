# ── Stage 1: Build React frontend ──────────────────────────────
FROM node:24-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python deps ────────────────────────────────────────
FROM python:3.12-slim AS python-build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# Install markitdown WITHOUT heavy optional extras
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    markitdown \
    && pip uninstall -y \
    pydub \
    SpeechRecognition \
    requests 2>/dev/null || true

# ── Stage 3: Final runtime image ───────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# OPTION A — minimal (DOCX, PPTX, XLSX, HTML, TXT only): ~750 MB
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libmagic1 \
#     && rm -rf /var/lib/apt/lists/*

# OPTION B — with PDF support: ~780 MB
# RUN apt-get update && apt-get install -y --no-install-recommends \
#    libmagic1 \
#    poppler-utils \
#    && rm -rf /var/lib/apt/lists/*

# OPTION C — with PDF + OCR on images: ~840 MB
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# (skip ffmpeg entirely unless you specifically need audio transcription)

COPY --from=python-build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser backend/ ./backend/
COPY --from=frontend-build --chown=appuser /app/frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]