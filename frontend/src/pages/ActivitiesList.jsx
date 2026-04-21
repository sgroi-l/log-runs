import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { format, parseISO } from "date-fns";

function formatPace(minPerKm) {
  if (!minPerKm) return "-";
  const mins = Math.floor(minPerKm);
  const secs = Math.round((minPerKm - mins) * 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function formatDuration(secs) {
  if (!secs) return "-";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

const PAGE_SIZE = 50;

export default function ActivitiesList({ athleteId }) {
  const [data, setData] = useState(null);
  const [offset, setOffset] = useState(0);
  const [sportType, setSportType] = useState("");

  useEffect(() => {
    setOffset(0);
  }, [sportType]);

  useEffect(() => {
    const params = { limit: PAGE_SIZE, offset };
    if (sportType) params.sport_type = sportType;
    api.listActivities(athleteId, params).then(setData);
  }, [athleteId, offset, sportType]);

  if (!data) return <div style={{ color: "var(--muted)" }}>Loading…</div>;

  const totalPages = Math.ceil(data.total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>Activities <span style={{ color: "var(--muted)", fontSize: 14 }}>({data.total})</span></h2>
        <select
          value={sportType}
          onChange={(e) => setSportType(e.target.value)}
          style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: "var(--radius)", padding: "6px 12px", fontSize: 13 }}
        >
          <option value="">All types</option>
          {["Run", "Ride", "Swim", "Walk", "Hike"].map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {["Date", "Name", "Type", "Distance", "Time", "Pace", "HR", "Elev"].map((h) => (
                <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.items.map((a, i) => (
              <tr key={a.id} style={{ borderBottom: i < data.items.length - 1 ? "1px solid var(--border)" : "none" }}>
                <td style={{ padding: "10px 14px", color: "var(--muted)", whiteSpace: "nowrap" }}>
                  {a.start_date ? format(parseISO(a.start_date), "d MMM yy") : "-"}
                </td>
                <td style={{ padding: "10px 14px", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {a.name || "-"}
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <span className="badge">{a.sport_type || "-"}</span>
                </td>
                <td style={{ padding: "10px 14px" }}>{a.distance_km ? `${a.distance_km} km` : "-"}</td>
                <td style={{ padding: "10px 14px" }}>{formatDuration(a.moving_time)}</td>
                <td style={{ padding: "10px 14px" }}>{formatPace(a.pace_min_per_km)}</td>
                <td style={{ padding: "10px 14px" }}>{a.average_heartrate ? `${Math.round(a.average_heartrate)} bpm` : "-"}</td>
                <td style={{ padding: "10px 14px" }}>{a.total_elevation_gain ? `${Math.round(a.total_elevation_gain)}m` : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn-ghost" onClick={() => setOffset(o => o - PAGE_SIZE)} disabled={offset === 0} style={{ padding: "6px 12px" }}>← Prev</button>
          <span style={{ color: "var(--muted)", fontSize: 13 }}>{currentPage} / {totalPages}</span>
          <button className="btn-ghost" onClick={() => setOffset(o => o + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= data.total} style={{ padding: "6px 12px" }}>Next →</button>
        </div>
      )}
    </div>
  );
}
