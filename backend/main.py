import os
import tempfile
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from markitdown import MarkItDown

app = FastAPI(title="Meltdown")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

md = MarkItDown()

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".html", ".htm", ".txt", ".csv",
    ".jpg", ".jpeg", ".png", ".mp3", ".wav",
    ".zip", ".epub"
}

MAX_FILE_SIZE_MB = 20


@app.post("/api/convert", response_class=PlainTextResponse)
async def convert(file: UploadFile):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB."
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = md.convert(tmp_path)
        return result.text_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    finally:
        os.unlink(tmp_path)


# Serve React build — must be last
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
