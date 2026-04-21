import React, { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { api } from "../api/client";
import { format, parseISO } from "date-fns";

function formatTime(secs) {
  if (!secs) return "-";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}:${String(s).padStart(2, "0")}` : `0:${String(s).padStart(2, "0")}`;
}

const AXIS_TICK = { fill: "#888", fontSize: 11 };
const GRID_STROKE = "#2a2a2a";

export default function SegmentsPage({ athleteId }) {
  const [segments, setSegments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.segments(athleteId).then(setSegments);
  }, [athleteId]);

  const handleSelect = async (seg) => {
    setSelected(seg);
    const h = await api.segmentHistory(athleteId, seg.segment_id);
    setHistory(h);
  };

  const prTime = history.length ? Math.min(...history.map((h) => h.elapsed_time).filter(Boolean)) : null;

  return (
    <div style={{ display: "flex", gap: 24 }}>
      <div style={{ width: 320, flexShrink: 0 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>
          Segments <span style={{ color: "var(--muted)", fontSize: 14 }}>({segments.length})</span>
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {segments.map((seg) => (
            <button
              key={seg.segment_id}
              onClick={() => handleSelect(seg)}
              style={{
                background: selected?.segment_id === seg.segment_id ? "var(--accent-dim)" : "var(--surface)",
                border: `1px solid ${selected?.segment_id === seg.segment_id ? "var(--accent)" : "var(--border)"}`,
                borderRadius: "var(--radius)",
                padding: "10px 14px",
                textAlign: "left",
                color: "var(--text)",
                cursor: "pointer",
              }}
            >
              <div style={{ fontWeight: 500, marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{seg.name}</div>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>
                {seg.distance_m ? `${(seg.distance_m / 1000).toFixed(2)} km` : "-"}
                {seg.average_grade ? ` · ${seg.average_grade.toFixed(1)}% grade` : ""}
                {" · "}<span style={{ color: "var(--accent)" }}>{seg.effort_count}×</span>
              </div>
            </button>
          ))}
          {segments.length === 0 && (
            <div style={{ color: "var(--muted)", padding: "16px 0" }}>No segment data yet.</div>
          )}
        </div>
      </div>

      <div style={{ flex: 1 }}>
        {selected ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <h3 style={{ fontSize: 18, fontWeight: 700 }}>{selected.name}</h3>
              <p style={{ color: "var(--muted)", fontSize: 13 }}>
                {selected.distance_m ? `${(selected.distance_m / 1000).toFixed(2)} km` : ""}
                {selected.average_grade ? ` · ${selected.average_grade.toFixed(1)}% avg grade` : ""}
              </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              <div className="card">
                <div className="stat-value">{formatTime(prTime)}</div>
                <div className="stat-label">PR</div>
              </div>
              <div className="card">
                <div className="stat-value">{selected.effort_count}</div>
                <div className="stat-label">Efforts</div>
              </div>
              <div className="card">
                <div className="stat-value">{formatTime(history.length ? Math.round(history.reduce((s, h) => s + (h.elapsed_time || 0), 0) / history.length) : null)}</div>
                <div className="stat-label">Avg Time</div>
              </div>
            </div>

            {history.length > 1 && (
              <div className="card">
                <h4 style={{ marginBottom: 16, fontWeight: 600 }}>Time History</h4>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={history}>
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(d) => format(parseISO(d), "MMM yy")}
                      tick={AXIS_TICK}
                      minTickGap={40}
                    />
                    <YAxis
                      reversed
                      tickFormatter={formatTime}
                      tick={AXIS_TICK}
                      width={55}
                    />
                    {prTime && (
                      <ReferenceLine y={prTime} stroke="var(--accent)" strokeDasharray="4 4" label={{ value: "PR", fill: "var(--accent)", fontSize: 11 }} />
                    )}
                    <Tooltip
                      contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)" }}
                      labelFormatter={(d) => format(parseISO(d), "d MMM yyyy")}
                      formatter={(v) => [formatTime(v), "Time"]}
                    />
                    <Line type="monotone" dataKey="elapsed_time" stroke="var(--accent)" dot={false} strokeWidth={2} activeDot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Date", "Time", "HR", "PR Rank"].map((h) => (
                      <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...history].reverse().map((e, i) => (
                    <tr key={i} style={{ borderBottom: i < history.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding: "10px 14px", color: "var(--muted)" }}>{e.date ? format(parseISO(e.date), "d MMM yyyy") : "-"}</td>
                      <td style={{ padding: "10px 14px", fontVariantNumeric: "tabular-nums" }}>
                        {formatTime(e.elapsed_time)}
                        {e.elapsed_time === prTime && <span className="badge" style={{ marginLeft: 8 }}>PR</span>}
                      </td>
                      <td style={{ padding: "10px 14px" }}>{e.average_heartrate ? `${Math.round(e.average_heartrate)} bpm` : "-"}</td>
                      <td style={{ padding: "10px 14px" }}>{e.pr_rank ? `#${e.pr_rank}` : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--muted)" }}>
            Select a segment to see its history.
          </div>
        )}
      </div>
    </div>
  );
}
