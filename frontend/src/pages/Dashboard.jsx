import React, { useCallback, useEffect, useState } from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import { api } from "../api/client";
import Overview from "./Overview";
import ActivitiesList from "./ActivitiesList";
import SegmentsPage from "./SegmentsPage";
import SyncButton from "../components/SyncButton";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/activities", label: "Activities" },
  { to: "/segments", label: "Segments" },
];

export default function Dashboard({ athleteId, onLogout }) {
  const [athlete, setAthlete] = useState(null);

  useEffect(() => {
    api.getAthlete(athleteId).then(setAthlete).catch(console.error);
  }, [athleteId]);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 16px" }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 0", borderBottom: "1px solid var(--border)", marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <span style={{ fontWeight: 800, fontSize: 18 }}>Log Runs</span>
          <nav style={{ display: "flex", gap: 4 }}>
            {NAV.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                style={({ isActive }) => ({
                  padding: "6px 12px",
                  borderRadius: "var(--radius)",
                  color: isActive ? "var(--accent)" : "var(--muted)",
                  fontWeight: isActive ? 600 : 400,
                  background: isActive ? "var(--accent-dim)" : "transparent",
                })}
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {athlete && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {athlete.profile_medium && (
                <img src={athlete.profile_medium} alt="" style={{ width: 28, height: 28, borderRadius: "50%" }} />
              )}
              <span style={{ color: "var(--muted)" }}>{athlete.firstname} {athlete.lastname}</span>
            </div>
          )}
          <SyncButton athleteId={athleteId} />
          <button className="btn-ghost" onClick={onLogout} style={{ padding: "6px 12px" }}>Log out</button>
        </div>
      </header>

      <Routes>
        <Route path="/" element={<Overview athleteId={athleteId} />} />
        <Route path="/activities" element={<ActivitiesList athleteId={athleteId} />} />
        <Route path="/segments" element={<SegmentsPage athleteId={athleteId} />} />
      </Routes>
    </div>
  );
}
