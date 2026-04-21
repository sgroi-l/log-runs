import React from "react";

export default function Login() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", flexDirection: "column", gap: 24 }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ fontSize: 32, fontWeight: 800, marginBottom: 8 }}>Log Runs</h1>
        <p style={{ color: "var(--muted)" }}>Your Strava data, your dashboard.</p>
      </div>
      <a href="/api/auth/login">
        <button className="btn-primary" style={{ fontSize: 16, padding: "12px 28px" }}>
          Connect with Strava
        </button>
      </a>
    </div>
  );
}
