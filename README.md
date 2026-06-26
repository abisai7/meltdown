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

## License

MIT
