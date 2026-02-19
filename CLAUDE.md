# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Flask server (port 5001)
python server.py

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_auth.py -v

# Run a single test
pytest tests/test_auth.py::test_register_success -v
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Development server (port 5173, proxies /api to port 5001)
npm run dev

# Production build (output: frontend/dist/)
npm run build

# Preview production build
npm run preview
```

## Architecture

This is a full-stack Google Maps business scraper with a Python/Flask backend and a React/Vite frontend.

### Backend (`server.py`, `app.py`, `busca.py`)

**Two-stage processing pipeline:**

1. **Stage 1 — Google Maps scraping** (`app.py`): Selenium headless Chrome driver scrolls a Google Maps search feed, extracting business name, address, website URL, and GPS coordinates (lat/lng parsed from URL params).

2. **Stage 2 — Contact extraction** (`busca.py`): For each scraped URL, fetches the website and uses regex + BeautifulSoup to extract emails, phone numbers, and social media links (Facebook, Instagram, Twitter/X, LinkedIn, YouTube, TikTok).

**API layer** (`server.py`):
- Jobs run on background threads; progress is communicated via a `Queue` and streamed to the client using Server-Sent Events (SSE) at `GET /api/progress/<job_id>`.
- Authentication is JWT-based. User records are stored in `users.json` (hashed passwords via Werkzeug).
- Environment variable `JWT_SECRET` is used for token signing (falls back to a default in dev).

**Key endpoints:**
- `POST /api/register` / `POST /api/login` — Auth
- `POST /api/search` — Start a scraping job (returns `job_id`)
- `GET /api/progress/<job_id>` — SSE stream for real-time progress
- `GET /api/download/<job_id>` — Download result CSV

### Frontend (`frontend/src/`)

- `App.jsx` — Manages auth state, SSE connection (`EventSource`), two-stage progress bars, and the download button.
- `AuthForm.jsx` — Login/register with real-time password strength validation (5 rules checked client-side).
- Vite proxy forwards `/api` requests to `http://localhost:5001` in dev mode.

### Data flow

```
User submits search form
  → POST /api/search (returns job_id)
  → App opens EventSource /api/progress/<job_id>
  → Background thread: Selenium scrapes Maps → emits stage1 progress events
  → Background thread: busca.py fetches websites → emits stage2 progress events
  → SSE stream closes → download button appears
  → GET /api/download/<job_id> → CSV file
```

### Output files

Scraped results are written to `TEMP/` as CSV files keyed by `job_id`.
