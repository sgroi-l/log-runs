# Best Efforts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store Strava best efforts (400m, 1k, 1 mile, 5k, etc.) from the sync and surface them as a PR board + trend chart in Overview, and a table in each activity's detail view.

**Architecture:** New `BestEffort` DB model populated during sync (data already returned by Strava API). Three new backend endpoints serve the frontend. Overview replaces the pace-over-time chart with a two-column best efforts section. ActivityDetail gains a Best Efforts table and an updated PR rank display in the Segments table.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), React/Recharts (frontend). No automated tests — verify backend via Swagger UI at `/docs`, frontend via browser.

---

### Notes for implementer

- No migrations: schema is created from models on startup via `Base.metadata.create_all()`. After adding the model, restart the backend and the table is created.
- The `include_all_efforts=True` param is already passed in `strava.py:104` — no change there.
- All new backend routes must be declared **before** `GET /{athlete_id}/{activity_id}` in `activities.py` (FastAPI matches in declaration order).
- This project has no test suite. Each task ends with manual verification steps instead of `pytest`.

---

### Task 1: BestEffort data model

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add BestEffort model and Activity relationship**

In `backend/app/models.py`, add the `BestEffort` class at the end of the file (before nothing — just append), and add the `best_efforts` relationship to `Activity`:

```python
# In the Activity class, after the `laps` relationship (line 58):
best_efforts: Mapped[list["BestEffort"]] = relationship(back_populates="activity")
```

```python
# New class at the end of the file:
class BestEffort(Base):
    __tablename__ = "best_efforts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("activities.id"))
    athlete_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("athletes.id"))
    name: Mapped[str | None] = mapped_column(String(50))
    distance: Mapped[float | None] = mapped_column(Float)       # metres
    elapsed_time: Mapped[int | None] = mapped_column(Integer)   # seconds
    moving_time: Mapped[int | None] = mapped_column(Integer)    # seconds
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    pr_rank: Mapped[int | None] = mapped_column(Integer)

    activity: Mapped["Activity"] = relationship(back_populates="best_efforts")
```

- [ ] **Step 2: Restart the backend and verify the table is created**

```bash
# From the repo root (assumes docker compose is running with the db):
docker compose restart backend
# OR if running locally:
# Kill and restart uvicorn
```

Then visit `http://localhost:8000/docs` — no startup errors means the table was created. You can also confirm via psql:
```bash
docker compose exec db psql -U logruns logruns -c "\dt best_efforts"
```
Expected: table `best_efforts` listed.

- [ ] **Step 3: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add BestEffort model"
```

---

### Task 2: Store best efforts during sync

**Files:**
- Modify: `backend/app/routers/sync.py`

- [ ] **Step 1: Import BestEffort**

In `backend/app/routers/sync.py`, update the models import on line 8:

```python
from app.models import Activity, Athlete, BestEffort, Lap, Segment, SegmentEffort, SyncLog
```

- [ ] **Step 2: Add upsert loop in `_upsert_activity`**

After the laps loop (after line 110), add:

```python
    # Best efforts
    for be_data in detail.get("best_efforts", []):
        be = db.get(BestEffort, be_data["id"])
        if be is None:
            be = BestEffort(id=be_data["id"])
            db.add(be)
        be.activity_id = activity_id
        be.athlete_id = athlete_id
        be.name = be_data.get("name")
        be.distance = be_data.get("distance")
        be.elapsed_time = be_data.get("elapsed_time")
        be.moving_time = be_data.get("moving_time")
        be.start_date = datetime.fromisoformat(be_data["start_date"].replace("Z", "+00:00")) if be_data.get("start_date") else None
        be.pr_rank = be_data.get("pr_rank")
```

- [ ] **Step 3: Verify via a sync**

Trigger a sync via `POST /sync/{athlete_id}` in Swagger UI (or use the Sync button in the app). Wait for it to complete, then check:

```bash
docker compose exec db psql -U logruns logruns -c "SELECT name, elapsed_time, pr_rank FROM best_efforts LIMIT 10;"
```

Expected: rows with names like "400m", "1k", "1 mile", "5k".

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/sync.py
git commit -m "feat: store best efforts during sync"
```

---

### Task 3: Backend API — best-efforts endpoints

**Files:**
- Modify: `backend/app/routers/activities.py`

- [ ] **Step 1: Import BestEffort**

Update the models import at the top of `backend/app/routers/activities.py`:

```python
from app.models import Activity, BestEffort, Lap, Segment, SegmentEffort
```

- [ ] **Step 2: Add the PRs endpoint**

Insert this route **before** the existing `GET /{athlete_id}/{activity_id}` route (currently at line 150). Add after the `segment_history` endpoint:

```python
@router.get("/{athlete_id}/best-efforts/prs")
def best_effort_prs(athlete_id: int, db: Session = Depends(get_db)):
    """Best (lowest elapsed_time) effort per distance name, with total effort count."""
    efforts = (
        db.query(BestEffort)
        .filter(BestEffort.athlete_id == athlete_id)
        .order_by(BestEffort.distance, BestEffort.elapsed_time)
        .all()
    )
    groups: dict[str, list] = {}
    for e in efforts:
        if e.name:
            groups.setdefault(e.name, []).append(e)

    result = []
    for name, group in sorted(groups.items(), key=lambda x: x[1][0].distance or 0):
        best = group[0]  # lowest elapsed_time first due to ORDER BY
        result.append({
            "name": best.name,
            "distance_m": best.distance,
            "elapsed_time": best.elapsed_time,
            "pace_min_per_km": round((best.elapsed_time / 60) / (best.distance / 1000), 2) if best.distance and best.elapsed_time else None,
            "activity_id": best.activity_id,
            "date": best.start_date.isoformat() if best.start_date else None,
            "pr_rank": best.pr_rank,
            "total_efforts": len(group),
        })
    return result
```

- [ ] **Step 3: Add the history endpoint**

Immediately after the PRs endpoint:

```python
@router.get("/{athlete_id}/best-efforts/history")
def best_effort_history(
    athlete_id: int,
    name: str = Query(...),
    db: Session = Depends(get_db),
):
    """All efforts for a given distance name over time."""
    efforts = (
        db.query(BestEffort)
        .filter(BestEffort.athlete_id == athlete_id, BestEffort.name == name)
        .order_by(BestEffort.start_date)
        .all()
    )
    return [
        {
            "date": e.start_date.isoformat() if e.start_date else None,
            "elapsed_time": e.elapsed_time,
            "pace_min_per_km": round((e.elapsed_time / 60) / (e.distance / 1000), 2) if e.distance and e.elapsed_time else None,
            "activity_id": e.activity_id,
            "pr_rank": e.pr_rank,
        }
        for e in efforts
    ]
```

- [ ] **Step 4: Verify both endpoints in Swagger UI**

Visit `http://localhost:8000/docs`:
- `GET /activities/{athlete_id}/best-efforts/prs` — should return an array ordered by distance
- `GET /activities/{athlete_id}/best-efforts/history?name=1k` — should return efforts over time

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/activities.py
git commit -m "feat: add best-efforts/prs and best-efforts/history endpoints"
```

---

### Task 4: Extend activity detail with best_efforts and segment total_efforts

**Files:**
- Modify: `backend/app/routers/activities.py`

- [ ] **Step 1: Eager-load best_efforts in get_activity**

In the `get_activity` function, update the `.options(...)` call to also joinedload best_efforts:

```python
    activity = (
        db.query(Activity)
        .options(
            joinedload(Activity.laps),
            joinedload(Activity.segment_efforts).joinedload(SegmentEffort.segment),
            joinedload(Activity.best_efforts),
        )
        .filter(Activity.id == activity_id, Activity.athlete_id == athlete_id)
        .first()
    )
```

- [ ] **Step 2: Add count lookups and extend the response**

After `base["description"] = activity.description` and before the `base["laps"] = [...]` block, add:

```python
    # Count best efforts per distance name for this athlete (for percentile display)
    be_counts = dict(
        db.query(BestEffort.name, func.count(BestEffort.id))
        .filter(BestEffort.athlete_id == athlete_id)
        .group_by(BestEffort.name)
        .all()
    )
    # Count segment efforts per segment for this athlete (for percentile display)
    seg_counts = dict(
        db.query(SegmentEffort.segment_id, func.count(SegmentEffort.id))
        .filter(SegmentEffort.athlete_id == athlete_id)
        .group_by(SegmentEffort.segment_id)
        .all()
    )
```

- [ ] **Step 3: Add best_efforts to the response**

After the `base["laps"] = [...]` block, add:

```python
    base["best_efforts"] = [
        {
            "name": be.name,
            "distance_m": be.distance,
            "elapsed_time": be.elapsed_time,
            "moving_time": be.moving_time,
            "pace_min_per_km": round((be.elapsed_time / 60) / (be.distance / 1000), 2) if be.distance and be.elapsed_time else None,
            "pr_rank": be.pr_rank,
            "total_efforts": be_counts.get(be.name, 0),
        }
        for be in sorted(activity.best_efforts, key=lambda b: b.distance or 0)
    ]
```

- [ ] **Step 4: Add total_efforts to each segment effort**

Update `base["segment_efforts"] = [...]` to include `total_efforts` on each row. Replace the existing block with:

```python
    base["segment_efforts"] = [
        {
            "segment_id": e.segment_id,
            "name": e.name,
            "elapsed_time": e.elapsed_time,
            "distance_m": e.distance,
            "average_heartrate": e.average_heartrate,
            "pr_rank": e.pr_rank,
            "kom_rank": e.kom_rank,
            "total_efforts": seg_counts.get(e.segment_id, 0),
            "segment_start_latlng": (
                [e.segment.start_latlng_lat, e.segment.start_latlng_lng]
                if e.segment and e.segment.start_latlng_lat is not None else None
            ),
            "segment_end_latlng": (
                [e.segment.end_latlng_lat, e.segment.end_latlng_lng]
                if e.segment and e.segment.end_latlng_lat is not None else None
            ),
        }
        for e in sorted(activity.segment_efforts, key=lambda e: e.start_date or activity.start_date)
    ]
```

- [ ] **Step 5: Verify in Swagger UI**

Hit `GET /activities/{athlete_id}/{activity_id}` in Swagger. The response should include:
- `"best_efforts": [{"name": "400m", "elapsed_time": ..., "total_efforts": ..., ...}, ...]`
- Each entry in `"segment_efforts"` should have `"total_efforts": <number>`

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/activities.py
git commit -m "feat: add best_efforts and segment total_efforts to activity detail"
```

---

### Task 5: Frontend utils and API client

**Files:**
- Create: `frontend/src/utils.js`
- Modify: `frontend/src/api/client.js`

- [ ] **Step 1: Create shared utils**

Create `frontend/src/utils.js`:

```javascript
export function formatPrRank(prRank, totalEfforts) {
  if (prRank === 1) return "🥇";
  if (prRank === 2) return "🥈";
  if (prRank === 3) return "🥉";
  if (prRank >= 4 && totalEfforts) return `top ${Math.round((prRank / totalEfforts) * 100)}%`;
  return "–";
}

export function formatElapsedTime(secs) {
  if (!secs) return "–";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
```

- [ ] **Step 2: Add API client methods**

In `frontend/src/api/client.js`, add two methods to the `api` object after the existing `getActivity` entry:

```javascript
  getBestEffortPRs: (athleteId) =>
    request(`/activities/${athleteId}/best-efforts/prs`),
  getBestEffortHistory: (athleteId, name) =>
    request(`/activities/${athleteId}/best-efforts/history?name=${encodeURIComponent(name)}`),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils.js frontend/src/api/client.js
git commit -m "feat: add formatPrRank/formatElapsedTime utils and best-efforts API client methods"
```

---

### Task 6: ActivityDetail — Best Efforts table and updated Segments PR column

**Files:**
- Modify: `frontend/src/components/ActivityDetail.jsx`

- [ ] **Step 1: Import formatPrRank**

At the top of `frontend/src/components/ActivityDetail.jsx`, add the import after the existing imports:

```javascript
import { formatPrRank } from "../utils";
```

- [ ] **Step 2: Add Best Efforts table**

After the closing `</div>` of the Laps section (after line 79), and before the Segments section (line 81), insert:

```jsx
          {detail.best_efforts && detail.best_efforts.length > 0 && (
            <div>
              <h4 style={{ fontWeight: 600, marginBottom: 10 }}>Best Efforts</h4>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["Distance", "Time", "Pace", "PR"].map((h) => (
                        <th key={h} style={{ padding: "6px 10px", textAlign: "left", color: "var(--muted)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {detail.best_efforts.map((be, i) => (
                      <tr key={i} style={{ borderBottom: i < detail.best_efforts.length - 1 ? "1px solid var(--border)" : "none" }}>
                        <td style={{ padding: "6px 10px", fontWeight: 600 }}>{be.name}</td>
                        <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{formatTime(be.elapsed_time)}</td>
                        <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{be.pace_min_per_km ? `${Math.floor(be.pace_min_per_km)}:${String(Math.round((be.pace_min_per_km % 1) * 60)).padStart(2, "0")} /km` : "–"}</td>
                        <td style={{ padding: "6px 10px" }}>{formatPrRank(be.pr_rank, be.total_efforts)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
```

- [ ] **Step 3: Update Segments PR column**

Replace the PR cell in the Segments table (lines 96-104). Change:

```jsx
                        <td style={{ padding: "6px 10px", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {e.pr_rank === 1 && <span style={{ marginRight: 6, fontSize: 12 }}>🥇</span>}
                          {e.name}
                        </td>
                        <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{formatTime(e.elapsed_time)}</td>
                        <td style={{ padding: "6px 10px" }}>{e.average_heartrate ? `${Math.round(e.average_heartrate)}` : "–"}</td>
                        <td style={{ padding: "6px 10px", color: e.pr_rank === 1 ? "#facc15" : "var(--text)" }}>
                          {e.pr_rank ? `#${e.pr_rank}` : "–"}
                        </td>
```

To:

```jsx
                        <td style={{ padding: "6px 10px", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.name}</td>
                        <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{formatTime(e.elapsed_time)}</td>
                        <td style={{ padding: "6px 10px" }}>{e.average_heartrate ? `${Math.round(e.average_heartrate)}` : "–"}</td>
                        <td style={{ padding: "6px 10px" }}>{formatPrRank(e.pr_rank, e.total_efforts)}</td>
```

- [ ] **Step 4: Verify in browser**

Open an activity detail (expand any row in Activities list). Check:
- A "Best Efforts" section appears above Segments showing distance / time / pace / PR
- The Segments table Rank column shows 🥇/🥈/🥉 for top 3 and "top X%" for the rest

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ActivityDetail.jsx
git commit -m "feat: add Best Efforts table and update Segments PR rank display in ActivityDetail"
```

---

### Task 7: Overview — replace pace chart with Best Efforts section

**Files:**
- Modify: `frontend/src/pages/Overview.jsx`

- [ ] **Step 1: Update imports**

Replace the existing import block at the top of `frontend/src/pages/Overview.jsx` with:

```javascript
import { useEffect, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { api } from "../api/client";
import { formatPrRank, formatElapsedTime } from "../utils";
import { format, parseISO } from "date-fns";
```

(Removes `ReferenceLine` since the average pace reference line is going away.)

- [ ] **Step 2: Remove DISTANCE_BUCKETS constant**

Delete lines 11-20 (the `DISTANCE_BUCKETS` array).

- [ ] **Step 3: Replace state, data fetching, and derived values**

Replace everything from `const [sportType, setSportType]` through `const avgPace = ...` (i.e. all state declarations, useEffect calls, and the derived-values block) with:

```javascript
  const [sportType, setSportType] = useState("Run");
  const [weeklyData, setWeeklyData] = useState([]);
  const [bestEffortPRs, setBestEffortPRs] = useState([]);
  const [selectedDistance, setSelectedDistance] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const promises = [api.weeklyVolume(athleteId, sportType)];
    if (sportType === "Run") promises.push(api.getBestEffortPRs(athleteId));
    Promise.all(promises).then((results) => {
      setWeeklyData(results[0]);
      if (sportType === "Run" && results[1]) {
        const prs = results[1];
        setBestEffortPRs(prs);
        setSelectedDistance(prs.length > 0 ? prs[0].name : null);
      } else {
        setBestEffortPRs([]);
        setSelectedDistance(null);
      }
    }).finally(() => setLoading(false));
  }, [athleteId, sportType]);

  useEffect(() => {
    if (!selectedDistance) return;
    setHistoryLoading(true);
    api.getBestEffortHistory(athleteId, selectedDistance)
      .then(setHistoryData)
      .finally(() => setHistoryLoading(false));
  }, [athleteId, selectedDistance]);

  const totalKm = weeklyData.reduce((s, w) => s + (w.distance_km || 0), 0);
  const totalTime = weeklyData.reduce((s, w) => s + (w.total_time_seconds || 0), 0);
  const totalRuns = weeklyData.reduce((s, w) => s + (w.count || 0), 0);
  const avgPace = totalKm > 0 ? (totalTime / 60) / totalKm : null;
```

The old code being replaced spans from `const [sportType, setSportType] = useState("Run");` through `const avgPace = filteredPaceData.length ? ... : null;` — delete all of it and substitute the block above.

- [ ] **Step 4: Replace the pace chart card with Best Efforts section**

Remove the entire pace chart card block — find `{paceData.length > 0 && (` and delete everything through its closing `)}` (the whole card div). Replace with:

```jsx
      {sportType === "Run" && bestEffortPRs.length > 0 && (
        <div className="card">
          <h3 style={{ fontWeight: 600, marginBottom: 16 }}>Best Efforts</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            {/* PR board */}
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Distance", "Time", "Pace", "PR"].map((h) => (
                      <th key={h} style={{ padding: "6px 10px", textAlign: "left", color: "var(--muted)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {bestEffortPRs.map((pr, i) => (
                    <tr
                      key={pr.name}
                      onClick={() => setSelectedDistance(pr.name)}
                      style={{
                        borderBottom: i < bestEffortPRs.length - 1 ? "1px solid var(--border)" : "none",
                        cursor: "pointer",
                        background: selectedDistance === pr.name ? "var(--surface)" : "transparent",
                      }}
                    >
                      <td style={{ padding: "6px 10px", fontWeight: 600 }}>{pr.name}</td>
                      <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{formatElapsedTime(pr.elapsed_time)}</td>
                      <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{formatPace(pr.pace_min_per_km)}</td>
                      <td style={{ padding: "6px 10px" }}>{formatPrRank(pr.pr_rank, pr.total_efforts)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Trend chart */}
            <div>
              <div style={{ display: "flex", gap: 2, flexWrap: "wrap", marginBottom: 12 }}>
                {bestEffortPRs.map((pr) => (
                  <button
                    key={pr.name}
                    onClick={() => setSelectedDistance(pr.name)}
                    style={{
                      padding: "4px 10px",
                      fontSize: 12,
                      background: selectedDistance === pr.name ? "var(--accent)" : "var(--bg)",
                      color: selectedDistance === pr.name ? "#fff" : "var(--muted)",
                      border: "1px solid var(--border)",
                      cursor: "pointer",
                    }}
                  >
                    {pr.name}
                  </button>
                ))}
              </div>
              {historyLoading ? (
                <div style={{ color: "var(--muted)", padding: 24, textAlign: "center" }}>Loading…</div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={historyData} style={CHART_STYLE}>
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(d) => format(parseISO(d), "MMM yy")}
                      tick={AXIS_TICK}
                      minTickGap={40}
                    />
                    <YAxis
                      reversed
                      domain={["auto", "auto"]}
                      tickFormatter={formatElapsedTime}
                      tick={AXIS_TICK}
                      width={50}
                    />
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      labelFormatter={(d) => format(parseISO(d), "d MMM yyyy")}
                      formatter={(v) => [formatElapsedTime(v), selectedDistance]}
                    />
                    <Line
                      type="monotone"
                      dataKey="elapsed_time"
                      stroke="var(--accent)"
                      dot={false}
                      strokeWidth={2}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      )}
```

- [ ] **Step 5: Update the no-data guard**

The existing no-data message (lines 84-88) references `paceData.length`. Replace it:

```jsx
      {!loading && weeklyData.length === 0 && (
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: 48 }}>
          No {sportType} data yet. Hit <strong>Sync Now</strong> to pull your activities.
        </div>
      )}
```

- [ ] **Step 6: Verify in browser**

- Switch to "Run" sport type on Overview — should see Best Efforts section with PR board on left and trend chart on right
- Click a distance in the PR board or pill buttons — chart updates to show that distance's history
- Switch to "Ride" — Best Efforts section should not appear
- Avg Pace stat card should still show a value (now computed from weekly volume data)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Overview.jsx
git commit -m "feat: replace pace chart with Best Efforts PR board and trend chart in Overview"
```
