# Philippines Real-Time Earthquake Monitoring System

This monorepo contains the backend and frontend for a real-time earthquake monitoring system focused on the Philippines.

## Stack

- Backend: FastAPI, Python 3.11, Celery, Redis, PostgreSQL/TimescaleDB
- Frontend: Next.js 16, TypeScript, Tailwind CSS, shadcn/ui-compatible styling
- Realtime: Socket.IO
- Map and charts: Mapbox GL JS, Recharts, D3.js
- Deployment targets: Fly.io backend, Vercel frontend

## Project Structure

```text
backend/
  app/
    main.py
    config.py
    database.py
    redis_client.py
    models/
    schemas/
    routers/
    services/
    workers/
  celery_app.py
  requirements.txt
  Dockerfile
  fly.toml
frontend/
  src/
    app/
    components/
    hooks/
    lib/
    types/
  package.json
  next.config.mjs
  tailwind.config.ts
```

## Local Setup

### Backend

```powershell
cd C:\xampp\htdocs\earthquake_sys\eq-monitor\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The backend will run at `http://localhost:8000`.

### Frontend

```powershell
cd C:\xampp\htdocs\earthquake_sys\eq-monitor\frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

The frontend will run at `http://localhost:3000`.

## Required Services

- PostgreSQL 15 with TimescaleDB extension
- Redis-compatible service
- Mapbox token for the map UI
- Optional alert credentials for Firebase, Telegram, Semaphore, and Resend

Semaphore SMS is planned as a direct REST integration through `httpx`; the package name `semaphore-py` from the source prompt is not currently available on PyPI.

## Phase Status

Phase 1 scaffolds the repository and configuration only. Database models, ingestion, API behavior, realtime events, alerts, production deployment, and hardening are implemented in later phases.
