export function formatPrRank(prRank, totalEfforts) {
  if (prRank === 1) return "🥇";
  if (prRank === 2) return "🥈";
  if (prRank === 3) return "🥉";
  if (prRank >= 4 && totalEfforts) return `top ${Math.round((prRank / totalEfforts) * 100)}%`;
  return "–";
}

export function formatElapsedTime(secs) {
  if (!secs) return "–";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
