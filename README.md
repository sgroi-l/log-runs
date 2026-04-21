# Log Runs

A self-hosted Strava dashboard. Pull all your activity data, own it locally, and see the charts and maps that Strava gates behind their paywall.

---

## Table of contents

- [Stack](#stack)
- [Features](#features)
- [Architecture](#architecture)
- [Setup](#setup)
- [API reference](#api-reference)
- [Strava API notes](#strava-api-notes)
- [Development](#development)
- [TODO](#todo)

---

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.12) |
| ORM | SQLAlchemy 2 |
| Database | PostgreSQL 16 |
| Frontend | React 18 + Vite |
| Charts | Recharts |
| Maps | Leaflet + react-leaflet |
| Deployment | Docker Compose |

---

## Features

### Authentication
- **Strava OAuth2** — one-click "Connect with Strava" flow. Tokens are stored per athlete and automatically refreshed before they expire. Multiple athletes can connect to the same instance (each sees only their own data).

### Sync
- **Manual resync** — a "Sync Now" button in the header kicks off a background sync. A live counter shows how many activities have been processed so far.
- **Full history on first sync** — paginates through all of your Strava activities and fetches the detail record for each one. This includes segment efforts, laps, heart rate, power, cadence, and the full-resolution route polyline.
- **Upsert semantics** — re-running sync is safe. Existing records are updated in place, new activities are inserted. No duplicates.
- **Rate limit aware** — a 0.5 s delay between detail fetches keeps the request rate well below Strava's free tier limit of 100 requests per 15 minutes.

### Overview page
- **Stat cards** — total activities, total distance, average pace, average weekly km.
- **Pace over time** — line chart of pace (min/km) for every activity, with a dashed average reference line. Y-axis is inverted so improving pace goes up.
- **Weekly distance** — bar chart of total km per week.
- **Sport type filter** — switch between Run, Ride, Swim, Walk, Hike to see the same charts for any activity type.

### Activities page
- **Paginated table** — 50 activities per page, filterable by sport type. Columns: date, name, type, distance, moving time, pace, avg heart rate, elevation gain.
- **Expandable rows** — click any row to expand an inline detail panel showing:
  - **Route map** — the full-resolution GPS route drawn on an OpenStreetMap base layer. Start point marked. Segment start points overlaid as coloured dots (yellow = PR, blue = normal effort).
  - **Lap splits** — table of every lap with distance, time, pace, heart rate, and elevation.
  - **Segment efforts** — every named segment on the activity with elapsed time, heart rate, and PR rank. Gold medal shown for PRs.

### Segments page
- **Segment list** — all segments you have ever ridden or run, sorted by number of efforts. Shows distance, average grade, and effort count.
- **Segment detail** — click a segment to see:
  - PR, average time, and total effort count stat cards.
  - **Time history chart** — line chart of elapsed time on each effort over time, with a dashed PR reference line. Y-axis inverted so improving times go up.
  - **Effort history table** — every effort with date, time, heart rate, and PR rank.

---

## Architecture

```
┌─────────────────────────────────────┐
│            Docker Compose           │
│                                     │
│  ┌──────────┐    ┌───────────────┐  │
│  │ frontend │    │    backend    │  │
│  │  :80     │───▶│    :8000      │  │
│  │  nginx   │    │   FastAPI     │  │
│  └──────────┘    └───────┬───────┘  │
│                          │          │
│                  ┌───────▼───────┐  │
│                  │   PostgreSQL  │  │
│                  │     :5432     │  │
│                  └───────────────┘  │
└─────────────────────────────────────┘
```

Nginx serves the built React app and proxies `/api/*` requests to the FastAPI backend. In local development, Vite's dev server handles the proxy instead.

### Database schema

| Table | Key columns |
|---|---|
| `athletes` | Strava athlete ID, OAuth tokens, profile |
| `activities` | All fields from the Strava detailed activity endpoint: distance, moving time, speed, HR, power, cadence, suffer score, full-resolution polyline, summary polyline, start coordinates |
| `segments` | Segment metadata: distance, grade, city, start/end coordinates |
| `segment_efforts` | Each time you hit a segment, linked to both activity and segment. Includes elapsed time, HR, power, PR rank, KOM rank |
| `laps` | Lap splits per activity: distance, time, speed, HR, power, cadence, elevation |
| `sync_logs` | Audit log of every sync run: start time, finish time, activities synced, status, error message |

---

## Setup

### 1. Create a Strava API app

1. Go to [https://www.strava.com/settings/api](https://www.strava.com/settings/api)
2. Create an app — name and description can be anything
3. Set **Authorization Callback Domain** to your server's domain (use `localhost` for local dev)
4. Note your **Client ID** and **Client Secret**

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
POSTGRES_PASSWORD=a-strong-password
SECRET_KEY=a-long-random-string          # used for future session signing
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
FRONTEND_URL=http://localhost             # change to your domain when deployed
```

### 3. Start

```bash
docker compose up --build
```

- Dashboard: [http://localhost](http://localhost)
- API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Connect and sync

1. Open [http://localhost](http://localhost)
2. Click **Connect with Strava** and authorise the app
3. Click **Sync Now** — the first sync fetches everything (allow 5–15 minutes depending on activity count)
4. After any new activity, click **Sync Now** again to pull it in

### Deploying to a server

The stack is a standard Docker Compose app. Any VPS (DigitalOcean, Hetzner, Fly.io, Render, etc.) with Docker installed works. Steps:

1. Copy the repo and your `.env` to the server
2. Set `FRONTEND_URL` to your public domain (e.g. `https://runs.example.com`)
3. Update the **Authorization Callback Domain** in your Strava app settings to match
4. Run `docker compose up -d --build`
5. Put a reverse proxy (Caddy or nginx) in front for HTTPS

---

## API reference

All endpoints are prefixed with `/api/` when accessed through the frontend proxy.

### Auth

| Method | Path | Description |
|---|---|---|
| `GET` | `/auth/login` | Redirect to Strava OAuth |
| `GET` | `/auth/callback?code=…` | OAuth callback, stores tokens, redirects to frontend |
| `GET` | `/auth/athlete/{id}` | Fetch basic athlete profile |

### Sync

| Method | Path | Description |
|---|---|---|
| `POST` | `/sync/{athlete_id}` | Start a background sync (returns immediately) |
| `GET` | `/sync/{athlete_id}/status` | Poll sync progress |

### Activities

| Method | Path | Description |
|---|---|---|
| `GET` | `/activities/{athlete_id}` | Paginated activity list. Query params: `sport_type`, `limit` (max 500), `offset` |
| `GET` | `/activities/{athlete_id}/{activity_id}` | Full activity detail with laps, segment efforts, and map polylines |
| `GET` | `/activities/{athlete_id}/pace-over-time` | Date + pace for every activity of a given `sport_type` |
| `GET` | `/activities/{athlete_id}/weekly-volume` | Weekly distance totals grouped by ISO week |
| `GET` | `/activities/{athlete_id}/segments` | All segments with PR time and effort count |
| `GET` | `/activities/{athlete_id}/segments/{segment_id}/history` | All efforts on one segment over time |

---

## Strava API notes

**Free tier limits:** 100 requests per 15 minutes, 1 000 requests per day.

| Scenario | Requests used |
|---|---|
| Initial sync (100 activities) | ~102 (1 list page + 100 details + token refresh if needed) |
| Initial sync (500 activities) | ~510 |
| Single new activity resync | 6–8 (list page + 1 detail + token refresh) |

The 0.5 s inter-request delay means 500 activities take ~4 minutes and use roughly half the daily allowance. If you have more than ~950 activities, the initial sync will hit the daily limit and resume on the next calendar day.

**Scopes requested:** `read` (basic profile) and `activity:read_all` (private activities included).

---

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
# requires a running Postgres — simplest is to start just the db with Docker:
docker compose up db -d
DATABASE_URL=postgresql://logruns:yourpassword@localhost:5432/logruns \
STRAVA_CLIENT_ID=xxx STRAVA_CLIENT_SECRET=xxx SECRET_KEY=xxx \
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # proxies /api to http://localhost:8000 by default
```

To point the dev proxy at a different backend:

```bash
VITE_API_URL=http://my-server:8000 npm run dev
```

---

## TODO

### High priority

- [ ] **Delta sync** — track the timestamp of the most recent activity and use Strava's `after` query parameter to only fetch new activities, instead of re-fetching everything on every sync
- [ ] **Webhook integration** — register a Strava webhook so new activities are synced automatically without clicking "Sync Now"
- [ ] **Segment polylines** — fetch full segment route geometry from `GET /segments/{id}` during sync and render segments as highlighted overlays on the route map (currently only start/end points are stored)
- [ ] **Gear tracking** — store and display shoe/bike gear data per activity; show mileage per gear item so you know when to replace shoes or service a bike

### Charts and analysis

- [ ] **Fitness/fatigue (CTL/ATL)** — calculate chronic training load and acute training load from suffer score or HR-based TSS, plot the classic form curve
- [ ] **Heart rate zones** — pie/bar chart of time in each HR zone per activity and over rolling periods
- [ ] **Best efforts** — best times at standard distances (1 km, 5 km, 10 km, half marathon, marathon) over time, plotted as a progression curve
- [ ] **Elevation profile** — draw the elevation gain/loss curve for a selected activity beneath the route map
- [ ] **Heatmap** — overlay all routes on a single map to visualise where you run/ride most
- [ ] **Power analysis** (for cyclists with a power meter) — normalised power, intensity factor, TSS, power curve, W/kg over time
- [ ] **Cadence trends** — cadence over time per sport type
- [ ] **Year-in-review** — annual summary page with total distance, elevation, time, and longest streak

### Maps

- [ ] **Segment polylines** — as above, render the full segment line on the map, not just a dot
- [ ] **Heatmap layer** — toggle a layer on the overview map that shows all routes as a density heatmap
- [ ] **Route comparison** — side-by-side map of two activities on the same course
- [ ] **Map clustering** — when zoomed out, cluster start-point markers to avoid clutter

### UX / quality of life

- [ ] **Dark/light mode toggle** — currently dark-only
- [ ] **Activity search** — full-text search on activity name and description
- [ ] **Date range filter** — filter all views to a custom date range or preset (this month, this year, last 90 days)
- [ ] **CSV / GPX export** — export filtered activity list or a single activity's route to a file
- [ ] **Personal records table** — a dedicated PRs page listing your all-time bests per distance
- [ ] **Notifications** — in-app toast when sync completes or fails

### Infrastructure

- [ ] **Alembic migrations** — currently the schema is created with `create_all` on startup; add Alembic so schema changes can be applied without dropping and recreating the database
- [ ] **Healthcheck endpoint** — extend `/health` to verify database connectivity
- [ ] **Auth hardening** — the athlete ID is currently stored in `localStorage` with no server-side session; add signed JWT cookies or a session table
- [ ] **Rate limit backoff** — detect Strava's 429 responses during sync and pause/resume automatically rather than failing
- [ ] **Sync progress via WebSocket** — push real-time sync progress to the frontend instead of polling every 2 seconds
