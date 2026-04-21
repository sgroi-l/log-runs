import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import RouteMap from "./RouteMap";
import { format, parseISO } from "date-fns";

function formatPace(minPerKm) {
  if (!minPerKm) return "–";
  const m = Math.floor(minPerKm);
  const s = Math.round((minPerKm - m) * 60);
  return `${m}:${String(s).padStart(2, "0")} /km`;
}

function formatTime(secs) {
  if (!secs) return "–";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}:${String(s).padStart(2, "0")}` : `0:${String(s).padStart(2, "0")}`;
}

export default function ActivityDetail({ athleteId, activityId, onClose }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getActivity(athleteId, activityId).then(setDetail).finally(() => setLoading(false));
  }, [athleteId, activityId]);

  return (
    <div style={{ background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 20, display: "flex", flexDirection: "column", gap: 20 }}>
      {loading && <div style={{ color: "var(--muted)" }}>Loading…</div>}

      {detail && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h3 style={{ fontWeight: 700, fontSize: 16 }}>{detail.name}</h3>
              <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 2 }}>
                {detail.start_date ? format(parseISO(detail.start_date), "EEEE d MMMM yyyy") : ""}
                {detail.description && ` · ${detail.description}`}
              </p>
            </div>
            <button className="btn-ghost" onClick={onClose} style={{ padding: "4px 10px", fontSize: 13 }}>✕</button>
          </div>

          <RouteMap
            polyline={detail.map_polyline || detail.map_summary_polyline}
            segments={detail.segment_efforts}
            height="300px"
          />

          {detail.laps && detail.laps.length > 1 && (
            <div>
              <h4 style={{ fontWeight: 600, marginBottom: 10 }}>Laps</h4>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["Lap", "Distance", "Time", "Pace", "HR", "Elev"].map((h) => (
                        <th key={h} style={{ padding: "6px 10px", textAlign: "left", color: "var(--muted)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {detail.laps.map((lap, i) => (
                      <tr key={i} style={{ borderBottom: i < detail.laps.length - 1 ? "1px solid var(--border)" : "none" }}>
                        <td style={{ padding: "6px 10px", color: "var(--muted)" }}>{lap.lap_index ?? i + 1}</td>
                        <td style={{ padding: "6px 10px" }}>{lap.distance_km ? `${lap.distance_km} km` : "–"}</td>
                        <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{formatTime(lap.moving_time)}</td>
                        <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{formatPace(lap.pace_min_per_km)}</td>
                        <td style={{ padding: "6px 10px" }}>{lap.average_heartrate ? `${Math.round(lap.average_heartrate)}` : "–"}</td>
                        <td style={{ padding: "6px 10px" }}>{lap.total_elevation_gain ? `${Math.round(lap.total_elevation_gain)}m` : "–"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {detail.segment_efforts && detail.segment_efforts.length > 0 && (
            <div>
              <h4 style={{ fontWeight: 600, marginBottom: 10 }}>Segments</h4>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["Segment", "Time", "HR", "Rank"].map((h) => (
                        <th key={h} style={{ padding: "6px 10px", textAlign: "left", color: "var(--muted)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {detail.segment_efforts.map((e, i) => (
                      <tr key={i} style={{ borderBottom: i < detail.segment_efforts.length - 1 ? "1px solid var(--border)" : "none" }}>
                        <td style={{ padding: "6px 10px", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {e.pr_rank === 1 && <span style={{ marginRight: 6, fontSize: 12 }}>🥇</span>}
                          {e.name}
                        </td>
                        <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{formatTime(e.elapsed_time)}</td>
                        <td style={{ padding: "6px 10px" }}>{e.average_heartrate ? `${Math.round(e.average_heartrate)}` : "–"}</td>
                        <td style={{ padding: "6px 10px", color: e.pr_rank === 1 ? "#facc15" : "var(--text)" }}>
                          {e.pr_rank ? `#${e.pr_rank}` : "–"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
