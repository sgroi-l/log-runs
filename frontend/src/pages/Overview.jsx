import React, { useEffect, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { api } from "../api/client";
import { formatPrRank, formatElapsedTime } from "../utils";
import { format, parseISO } from "date-fns";

const SPORT_TYPES = ["Run", "Ride", "Swim", "Walk", "Hike"];

function formatPace(minPerKm) {
  if (!minPerKm) return "-";
  const mins = Math.floor(minPerKm);
  const secs = Math.round((minPerKm - mins) * 60);
  return `${mins}:${String(secs).padStart(2, "0")} /km`;
}

function formatDuration(secs) {
  if (!secs) return "-";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

const CHART_STYLE = { fontSize: 12 };
const GRID_STROKE = "#2a2a2a";
const AXIS_TICK = { fill: "#888", fontSize: 11 };
const TOOLTIP_STYLE = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)" };

export default function Overview({ athleteId }) {
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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>Overview</h2>
        <select
          value={sportType}
          onChange={(e) => setSportType(e.target.value)}
          style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: "var(--radius)", padding: "6px 12px", fontSize: 13 }}
        >
          {SPORT_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <StatCard value={totalRuns} label="Total Activities" />
        <StatCard value={`${totalKm.toFixed(0)} km`} label="Total Distance" />
        <StatCard value={formatPace(avgPace)} label="Avg Pace" />
        <StatCard value={weeklyData.length > 0 ? `${(totalKm / weeklyData.length).toFixed(1)} km` : "-"} label="Avg Weekly km" />
      </div>

      {!loading && weeklyData.length === 0 && (
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: 48 }}>
          No {sportType} data yet. Hit <strong>Sync Now</strong> to pull your activities.
        </div>
      )}

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

      {weeklyData.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: 16, fontWeight: 600 }}>Weekly Distance (km)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={weeklyData} style={CHART_STYLE}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
              <XAxis
                dataKey="week"
                tickFormatter={(d) => format(parseISO(d), "d MMM")}
                tick={AXIS_TICK}
                minTickGap={40}
              />
              <YAxis tick={AXIS_TICK} tickFormatter={(v) => `${v}km`} />
              <Tooltip
                contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)" }}
                labelFormatter={(d) => `Week of ${format(parseISO(d), "d MMM yyyy")}`}
                formatter={(v) => [`${v} km`, "Distance"]}
              />
              <Bar dataKey="distance_km" fill="var(--accent)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function StatCard({ value, label }) {
  return (
    <div className="card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
