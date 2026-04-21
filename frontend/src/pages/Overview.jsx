import React, { useEffect, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { api } from "../api/client";
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

export default function Overview({ athleteId }) {
  const [sportType, setSportType] = useState("Run");
  const [paceData, setPaceData] = useState([]);
  const [weeklyData, setWeeklyData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.paceOverTime(athleteId, sportType),
      api.weeklyVolume(athleteId, sportType),
    ]).then(([pace, weekly]) => {
      setPaceData(pace);
      setWeeklyData(weekly);
    }).finally(() => setLoading(false));
  }, [athleteId, sportType]);

  const avgPace = paceData.length
    ? paceData.reduce((s, d) => s + (d.pace_min_per_km || 0), 0) / paceData.length
    : null;

  const totalKm = weeklyData.reduce((s, w) => s + (w.distance_km || 0), 0);
  const totalRuns = weeklyData.reduce((s, w) => s + (w.count || 0), 0);

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

      {!loading && paceData.length === 0 && (
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: 48 }}>
          No {sportType} data yet. Hit <strong>Sync Now</strong> to pull your activities.
        </div>
      )}

      {paceData.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: 16, fontWeight: 600 }}>Pace Over Time</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={paceData} style={CHART_STYLE}>
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
                tickFormatter={formatPace}
                tick={AXIS_TICK}
                width={70}
              />
              {avgPace && (
                <ReferenceLine y={avgPace} stroke="var(--accent)" strokeDasharray="4 4" label={{ value: "avg", fill: "var(--accent)", fontSize: 11 }} />
              )}
              <Tooltip
                contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)" }}
                labelFormatter={(d) => format(parseISO(d), "d MMM yyyy")}
                formatter={(v, name) => [formatPace(v), "Pace"]}
              />
              <Line
                type="monotone"
                dataKey="pace_min_per_km"
                stroke="var(--accent)"
                dot={false}
                strokeWidth={2}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
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
