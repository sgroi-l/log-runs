import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import ActivityDetail from "../components/ActivityDetail";
import { format, parseISO } from "date-fns";

function formatPace(minPerKm) {
  if (!minPerKm) return "–";
  const m = Math.floor(minPerKm);
  const s = Math.round((minPerKm - m) * 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatDuration(secs) {
  if (!secs) return "–";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

const PAGE_SIZE = 50;

export default function ActivitiesList({ athleteId }) {
  const [data, setData] = useState(null);
  const [offset, setOffset] = useState(0);
  const [sportType, setSportType] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    setOffset(0);
    setExpandedId(null);
  }, [sportType]);

  useEffect(() => {
    const params = { limit: PAGE_SIZE, offset };
    if (sportType) params.sport_type = sportType;
    api.listActivities(athleteId, params).then(setData);
  }, [athleteId, offset, sportType]);

  if (!data) return <div style={{ color: "var(--muted)" }}>Loading…</div>;

  const totalPages = Math.ceil(data.total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const handleRowClick = (id) => setExpandedId((prev) => (prev === id ? null : id));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>
          Activities <span style={{ color: "var(--muted)", fontSize: 14 }}>({data.total})</span>
        </h2>
        <select
          value={sportType}
          onChange={(e) => setSportType(e.target.value)}
          style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: "var(--radius)", padding: "6px 12px", fontSize: 13 }}
        >
          <option value="">All types</option>
          {["Run", "Ride", "Swim", "Walk", "Hike"].map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {data.items.map((a) => (
          <React.Fragment key={a.id}>
            <div
              onClick={() => handleRowClick(a.id)}
              style={{
                display: "grid",
                gridTemplateColumns: "90px 1fr 80px 80px 70px 70px 60px 50px",
                alignItems: "center",
                gap: 8,
                padding: "10px 14px",
                background: expandedId === a.id ? "var(--accent-dim)" : "var(--surface)",
                border: `1px solid ${expandedId === a.id ? "var(--accent)" : "var(--border)"}`,
                borderRadius: "var(--radius)",
                cursor: "pointer",
                transition: "background 0.1s",
              }}
            >
              <span style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap" }}>
                {a.start_date ? format(parseISO(a.start_date), "d MMM yy") : "–"}
              </span>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 500 }}>
                {a.name || "–"}
              </span>
              <span><span className="badge">{a.sport_type || "–"}</span></span>
              <span style={{ fontSize: 13 }}>{a.distance_km ? `${a.distance_km} km` : "–"}</span>
              <span style={{ fontSize: 13, fontVariantNumeric: "tabular-nums" }}>{formatDuration(a.moving_time)}</span>
              <span style={{ fontSize: 13, fontVariantNumeric: "tabular-nums" }}>{formatPace(a.pace_min_per_km)}</span>
              <span style={{ fontSize: 13 }}>{a.average_heartrate ? `${Math.round(a.average_heartrate)}` : "–"}</span>
              <span style={{ fontSize: 13 }}>{a.total_elevation_gain ? `${Math.round(a.total_elevation_gain)}m` : "–"}</span>
            </div>

            {expandedId === a.id && (
              <ActivityDetail
                athleteId={athleteId}
                activityId={a.id}
                onClose={() => setExpandedId(null)}
              />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Column headers — shown as a legend above the list */}
      <div style={{ display: "grid", gridTemplateColumns: "90px 1fr 80px 80px 70px 70px 60px 50px", gap: 8, padding: "0 14px", order: -1 }}>
        {["Date", "Name", "Type", "Distance", "Time", "Pace", "HR", "Elev"].map((h) => (
          <span key={h} style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>{h}</span>
        ))}
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn-ghost" onClick={() => setOffset((o) => o - PAGE_SIZE)} disabled={offset === 0} style={{ padding: "6px 12px" }}>← Prev</button>
          <span style={{ color: "var(--muted)", fontSize: 13 }}>{currentPage} / {totalPages}</span>
          <button className="btn-ghost" onClick={() => setOffset((o) => o + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= data.total} style={{ padding: "6px 12px" }}>Next →</button>
        </div>
      )}
    </div>
  );
}
