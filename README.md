# Log Runs

A self-hosted Strava dashboard. Pull all your data, own it, and see the charts Strava hides behind their paywall.

## Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: React + Vite + Recharts
- **Infra**: Docker Compose

## Setup

### 1. Create a Strava API app

Go to https://www.strava.com/settings/api and create an app.

Set the **Authorization Callback Domain** to your server's domain (or `localhost` for local dev).

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Strava credentials and a secret key
```

### 3. Run

```bash
docker compose up --build
```

The dashboard will be at http://localhost.

The API docs are at http://localhost:8000/docs.

### 4. Connect and sync

1. Open http://localhost
2. Click **Connect with Strava** — you'll be redirected back after auth
3. Hit **Sync Now** — this pulls all your activities (runs the first time, only new ones on subsequent syncs if you implement delta sync later)

## Strava API rate limits

Free tier: **100 requests / 15 min**, **1000 requests / day**.

The sync adds a 0.5s delay between activity detail fetches. A first-time sync of 500 activities takes ~5 minutes and uses ~500 of your daily 1000 requests. Incremental resyncs after new activities cost 2 requests per activity.

## Development

```bash
# Backend (with hot reload)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (with hot reload)
cd frontend
npm install
npm run dev
```
