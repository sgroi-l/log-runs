# Best Efforts Design

## Overview

Add Strava best efforts data to the dashboard. Best efforts are Strava-computed splits for standard distances (400m, 1k, 1 mile, 5k, etc.) recorded from the first occurrence of each distance within a run — not the fastest split. They are returned by the Strava API on every activity detail fetch and are not currently stored.

The feature has two surfaces:
1. **Cross-activity** — a PR board and trend chart replacing the pace-over-time chart in Overview
2. **Per-activity** — a Best Efforts table in ActivityDetail, alongside existing Laps and Segments sections

## Data Model

New table `best_efforts`:

| column | type | notes |
|---|---|---|
| `id` | BigInteger PK | Strava's effort ID |
| `activity_id` | BigInteger FK → activities | |
| `athlete_id` | BigInteger FK → athletes | for filtering without join |
| `name` | String(50) | "400m", "1k", "1 mile", "5k", etc. |
| `distance` | Float | metres |
| `elapsed_time` | Integer | seconds |
| `moving_time` | Integer | seconds |
| `start_date` | DateTime | from the effort payload |
| `pr_rank` | Integer nullable | 1 = current PR for this distance |

Schema is created automatically on startup via `Base.metadata.create_all()` — no migration needed.

## Sync

`_upsert_activity` in `routers/sync.py` gets a new loop after the laps loop, iterating over `detail.get("best_efforts", [])` and upserting `BestEffort` rows. Same upsert pattern as laps and segment efforts: `db.get(BestEffort, effort_id)` then assign fields. Sync is already idempotent so re-syncing is safe.

The Strava call in `strava.py` already passes `include_all_efforts=True`, so no change needed there.

## API Endpoints

All new endpoints added to `routers/activities.py`.

### `GET /activities/{athlete_id}/best-efforts/prs`

Returns the best (lowest elapsed_time) effort per distance name, along with total effort count for percentile display.

```json
[
  {
    "name": "400m",
    "distance_m": 400,
    "elapsed_time": 78,
    "pace_min_per_km": 3.25,
    "activity_id": 123,
    "date": "2024-03-01",
    "total_efforts": 47
  }
]
```

Ordered by `distance` ascending so distances appear in natural order.

### `GET /activities/{athlete_id}/best-efforts/history?name=<name>`

All efforts for a given distance name, ordered by date. Used for the trend chart. `name` is a query parameter (not a path segment) because Strava distance names include slashes, e.g. "1/2 mile".

```json
[
  {
    "date": "2024-01-01",
    "elapsed_time": 225,
    "pace_min_per_km": 3.75,
    "activity_id": 99,
    "pr_rank": 2
  }
]
```

The `name` value matches the Strava-supplied name string exactly (e.g. `"1k"`, `"1/2 mile"`, `"1 mile"`).

### Extended: `GET /activities/{athlete_id}/{activity_id}`

Two additions to the existing response:

1. `best_efforts` array — each row includes `name`, `distance_m`, `elapsed_time`, `moving_time`, `pace_min_per_km`, `pr_rank`, `total_efforts` (count of all efforts by this athlete for that distance name)
2. Each entry in `segment_efforts` gains a `total_efforts` field (count of all efforts by this athlete on that segment)

## PR Rank Display

A shared frontend helper function `formatPrRank(prRank, totalEfforts)`:

- `prRank === 1` → 🥇
- `prRank === 2` → 🥈
- `prRank === 3` → 🥉
- `prRank >= 4` → `"top X%"` where `X = Math.round(prRank / totalEfforts * 100)`
- `prRank === null` → `"–"`

Used in:
- Best Efforts table in ActivityDetail
- Segments table in ActivityDetail (replaces current raw `#N` display)
- PR board in Overview

## Frontend

### Overview page

The pace-over-time chart is removed. A new "Best Efforts" section is added, visible only when `sportType === "Run"`. Layout: two columns.

**Left — PR board table**

Columns: Distance | Time | Pace | PR

Rows ordered by distance ascending (400m → marathon). Clicking a row selects that distance in the trend chart.

**Right — trend chart**

Recharts `LineChart` showing `elapsed_time` (Y axis, formatted as `mm:ss`) vs date (X axis). Distance selector pills above the chart, same pill-button style as existing sport type and bucket filters. Defaults to the first distance with data.

Data fetched on mount via `getBestEffortPRs` (for the board) and lazily per distance via `getBestEffortHistory` when a distance is selected.

### ActivityDetail component

New "Best Efforts" section below the Laps section, above Segments. Only rendered if `detail.best_efforts?.length > 0`.

Table columns: Distance | Time | Pace | PR

PR column uses `formatPrRank(effort.pr_rank, effort.total_efforts)`.

Segments table PR column updated to use the same `formatPrRank` helper (currently shows raw `#N`).

### API client (`api/client.js`)

Two new methods:
- `getBestEffortPRs(athleteId)` → `GET /activities/{athleteId}/best-efforts/prs`
- `getBestEffortHistory(athleteId, name)` → `GET /activities/{athleteId}/best-efforts/history?name=<name>`

## Styling

Follows existing dark-mode conventions: CSS variables (`--border`, `--accent`, `--muted`, `--bg`), inline styles, same table and pill-button patterns as existing components. No new CSS classes needed.
