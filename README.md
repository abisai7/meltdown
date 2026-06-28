# Meltdown

A full-stack web app that converts documents to Markdown using Microsoft's [markitdown](https://github.com/microsoft/markitdown) library. No files are persisted — everything is processed in memory and immediately discarded.

## Stack

- **Backend:** Python + FastAPI + markitdown
- **Frontend:** React 19 + Vite
- **Deployment:** Railway via Dockerfile

## Supported Formats

| Format | Extensions |
|---|---|
| PDF | `.pdf` |
| Word | `.docx` |
| PowerPoint | `.pptx` |
| Excel | `.xlsx` |
| HTML | `.html`, `.htm` |
| Plain text / CSV | `.txt`, `.csv` |
| Images (OCR) | `.jpg`, `.jpeg`, `.png` |
| Audio (transcription) | `.mp3`, `.wav` |
| Archives | `.zip` |
| eBooks | `.epub` |

## Local Development

### Backend

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. The Vite dev server proxies `/api` to FastAPI on port 8000.

## Docker

```bash
docker build -t meltdown .
docker run -p 8000:8000 meltdown
```

## Deploy to Railway

1. Push to a Git repository
2. Connect the repo to Railway
3. Railway detects the `Dockerfile` and deploys automatically

The `railway.toml` configures the build and start command.

## Security

All security features are env-var driven with safe defaults (open access for local dev).

| Variable | Default | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins (backend) |
| `API_KEY` | *(none)* | Require `X-API-Key` header — skipped if unset (backend) |
| `VITE_API_KEY` | *(none)* | Must match `API_KEY` — bundled into frontend at build time |
| `RATE_LIMIT` | `10/minute` | Requests per IP |
| `CONVERSION_TIMEOUT` | `30` | Max seconds per conversion |
| `MAX_CONCURRENT` | `5` | Max simultaneous conversions |

### Generating an API Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set it in Railway (Variables tab) or in a local `.env` file — **both vars must match**:

```
API_KEY=your-generated-key
VITE_API_KEY=your-generated-key
```

The frontend reads `VITE_API_KEY` and sends it as the `X-API-Key` header.

> **Note:** `VITE_API_KEY` must be available at Docker build time (Vite embeds it into the JS bundle). Railway passes environment variables to the Docker build automatically. If the frontend still sends an empty key, trigger a **rebuild** (not just a redeploy) so the Dockerfile picks up the new variable.

## License

MIT
