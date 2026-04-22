import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";

export default function App() {
  const [athleteId, setAthleteId] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("athlete_id");
    if (id) {
      localStorage.setItem("athlete_id", id);
      return id;
    }
    return localStorage.getItem("athlete_id");
  });

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("athlete_id")) {
      window.history.replaceState({}, "", "/");
    }
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={athleteId ? <Dashboard athleteId={athleteId} onLogout={() => { localStorage.removeItem("athlete_id"); setAthleteId(null); }} /> : <Navigate to="/login" replace />}
      />
    </Routes>
  );
}
