const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const api = {
  getAthlete: (id) => request(`/auth/athlete/${id}`),
  triggerSync: (id) => request(`/sync/${id}`, { method: "POST" }),
  syncStatus: (id) => request(`/sync/${id}/status`),
  listActivities: (id, params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/activities/${id}${qs ? "?" + qs : ""}`);
  },
  paceOverTime: (id, sportType = "Run") =>
    request(`/activities/${id}/pace-over-time?sport_type=${sportType}`),
  weeklyVolume: (id, sportType = "Run") =>
    request(`/activities/${id}/weekly-volume?sport_type=${sportType}`),
  segments: (id) => request(`/activities/${id}/segments`),
  segmentHistory: (id, segmentId) =>
    request(`/activities/${id}/segments/${segmentId}/history`),
  getActivity: (athleteId, activityId) =>
    request(`/activities/${athleteId}/${activityId}`),
};
