import React, { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export default function SyncButton({ athleteId }) {
  const [status, setStatus] = useState(null);
  const pollRef = useRef(null);

  const fetchStatus = async () => {
    const s = await api.syncStatus(athleteId);
    setStatus(s);
    return s;
  };

  useEffect(() => {
    fetchStatus();
  }, [athleteId]);

  const startPolling = () => {
    pollRef.current = setInterval(async () => {
      const s = await fetchStatus();
      if (s.status !== "running") clearInterval(pollRef.current);
    }, 2000);
  };

  const handleSync = async () => {
    await api.triggerSync(athleteId);
    setStatus({ status: "running", activities_synced: 0 });
    startPolling();
  };

  useEffect(() => () => clearInterval(pollRef.current), []);

  const isRunning = status?.status === "running";
  const label = isRunning
    ? `Syncing… (${status.activities_synced ?? 0})`
    : "Sync Now";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {status?.status === "done" && (
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          Last: {status.activities_synced} activities
        </span>
      )}
      {status?.status === "error" && (
        <span style={{ fontSize: 12, color: "#f87171" }}>Sync failed</span>
      )}
      <button className="btn-primary" onClick={handleSync} disabled={isRunning}>
        {label}
      </button>
    </div>
  );
}
