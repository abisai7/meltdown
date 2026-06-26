import os
import re
import time
import json
import asyncio
import logging
import tempfile
from datetime import datetime, timezone

import magic
from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from markitdown import MarkItDown

# ── Config ────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
API_KEY = os.getenv("API_KEY")
CONVERSION_TIMEOUT = int(os.getenv("CONVERSION_TIMEOUT", "30"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "5"))
MAX_FILE_SIZE_MB = 20
RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".html", ".htm", ".txt", ".csv",
    ".jpg", ".jpeg", ".png",
    ".zip", ".epub",
}

EXTENSION_TO_MIME = {
    ".pdf":  {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".html": {"text/html"},
    ".htm":  {"text/html"},
    ".txt":  {"text/plain"},
    ".csv":  {"text/csv", "text/plain"},
    ".jpg":  {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png":  {"image/png"},
    ".zip":  {"application/zip", "application/x-zip-compressed"},
    ".epub": {"application/epub+zip", "application/zip"},
}

# ── Structured logging ────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "data"):
            log["data"] = record.data
        return json.dumps(log)

logger = logging.getLogger("meltdown")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ── App setup ─────────────────────────────────────────────────
app = FastAPI(title="Meltdown")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["POST"],
    allow_headers=["*"],
)

md = MarkItDown()
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# ── Security headers middleware ───────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
    )
    return response

# ── Rate limit error handler ──────────────────────────────────
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )

# ── Helpers ───────────────────────────────────────────────────
def sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^\w.\-]", "_", name)
    return name.strip("_.") or "upload"

def log_event(message: str, level: str = "info", **data):
    record = logging.LogRecord(
        name="meltdown", level=getattr(logging, level.upper()),
        pathname="", lineno=0, msg=message, args=(), exc_info=None,
    )
    record.data = data
    logger.handle(record)

# ── Convert endpoint ──────────────────────────────────────────
@app.post("/api/convert", response_class=PlainTextResponse)
@limiter.limit(RATE_LIMIT)
async def convert(request: Request, file: UploadFile):
    client_ip = get_remote_address(request)
    start = time.monotonic()

    # 1. API key check
    if API_KEY:
        provided = request.headers.get("x-api-key")
        if provided != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    # 2. Filename sanitization
    filename = sanitize_filename(file.filename or "")
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 3. Read contents
    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.",
        )

    # 4. MIME type validation
    detected_mime = magic.from_buffer(contents, mime=True)
    expected_mimes = EXTENSION_TO_MIME.get(ext, set())
    if expected_mimes and detected_mime not in expected_mimes:
        log_event(
            "MIME mismatch",
            level="warning",
            ip=client_ip, file=filename, ext=ext, detected=detected_mime,
        )
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match extension '{ext}'. Detected type: {detected_mime}",
        )

    # 5. Concurrency limit
    if semaphore.locked():
        log_event("Concurrency limit hit", level="warning", ip=client_ip, file=filename)
        raise HTTPException(status_code=503, detail="Server busy. Try again shortly.")

    # 6. Conversion with timeout
    async with semaphore:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(md.convert, tmp_path),
                timeout=CONVERSION_TIMEOUT,
            )
            duration = round(time.monotonic() - start, 3)
            log_event(
                "Conversion OK",
                ip=client_ip, file=filename, size=len(contents),
                mime=detected_mime, duration=duration,
            )
            return result.text_content

        except asyncio.TimeoutError:
            log_event(
                "Conversion timeout",
                level="warning",
                ip=client_ip, file=filename, timeout=CONVERSION_TIMEOUT,
            )
            raise HTTPException(
                status_code=504,
                detail=f"Conversion timed out after {CONVERSION_TIMEOUT}s.",
            )
        except Exception as e:
            log_event(
                "Conversion error",
                level="error",
                ip=client_ip, file=filename, error=str(e),
            )
            raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
        finally:
            os.unlink(tmp_path)


# Serve React build — must be last
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
