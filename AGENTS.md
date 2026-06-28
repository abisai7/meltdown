# AGENTS.md

## Project

Meltdown — document-to-Markdown converter. Single-service deployment: FastAPI backend serves a React (Vite) frontend as static files.

## Commands

### Local development

**Backend** (port 8000):
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

**Frontend** (port 5173, proxies `/api` → localhost:8000):
```bash
cd frontend && npm install && npm run dev
```

### Docker build

```bash
docker build -t meltdown .
docker run -p 8000:8000 meltdown
```

### No test suite or linter configured

There are no test files, pytest config, or lint/typecheck scripts. Do not attempt to run tests.

## Architecture

- `backend/main.py` — single-file FastAPI app. Serves the `/api/convert` endpoint and mounts the React build at `/`.
- `frontend/` — React 19 + Vite. Single-component app (`App.jsx`). No router.
- `Dockerfile` — 3-stage build: (1) Node builds React, (2) Python installs pip deps into a venv, (3) Alpine runtime image copies venv + built frontend.
- `railway.toml` — Railway uses the Dockerfile directly.

## Gotchas

- **VITE_API_KEY must be a Docker ARG.** The frontend reads `import.meta.env.VITE_API_KEY` at build time. The Dockerfile declares `ARG VITE_API_KEY=` in the `frontend-build` stage. If this ARG is missing, the frontend sends an empty key and backend auth fails silently. After changing this env var on Railway, trigger a **rebuild** (not just redeploy).
- **`requirements.txt` is not the source of truth for Docker installs.** The Dockerfile's `pip install` line in Stage 2 lists packages directly. If you add a dependency to `requirements.txt`, also add it to the Dockerfile, or it won't be in the container.
- **Alpine, not Debian.** System packages use Alpine names: `libmagic` (not `libmagic1`), `file-dev` (not `libmagic-dev`). No `tesseract-ocr-eng` package — English data is bundled with `tesseract-ocr`.
- **Static mount must be last.** `app.mount("/", ...)` in `main.py` is a catch-all. Any routes added after it will be unreachable.
- **Temp files.** Conversion writes to a temp file and deletes it in a `finally` block. Do not remove the cleanup.
- **Textarea controlled/uncontrolled.** The editor textarea uses `ref` + `defaultValue` (uncontrolled) with `onInput` to update state. Do not switch to `value` + `onChange` — it causes cursor-jump bugs.

## Environment Variables

All optional, safe defaults for local dev. See `.env.example`.

| Variable | Stage | Notes |
|---|---|---|
| `ALLOWED_ORIGINS` | runtime | Comma-separated, default `*` |
| `API_KEY` | runtime | Backend auth, skipped if unset |
| `VITE_API_KEY` | **build** | Must match `API_KEY`, needs Docker ARG |
| `RATE_LIMIT` | runtime | Default `10/minute` |
| `CONVERSION_TIMEOUT` | runtime | Default `30` seconds |
| `MAX_CONCURRENT` | runtime | Default `5` |
