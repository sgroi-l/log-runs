import React, { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import polylineCodec from "@mapbox/polyline";

// Fix Leaflet's broken default icon paths when bundled with Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function FitBounds({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 1) {
      map.fitBounds(positions, { padding: [16, 16] });
    } else if (positions.length === 1) {
      map.setView(positions[0], 14);
    }
  }, [positions]);
  return null;
}

/**
 * Renders a decoded Strava polyline on an OpenStreetMap base layer.
 *
 * Props:
 *   polyline        – encoded polyline string (full or summary)
 *   segments        – optional array of { segment_start_latlng, segment_end_latlng, name, pr_rank }
 *   height          – CSS height string, default "320px"
 *   accentColor     – route colour, default Strava orange
 */
export default function RouteMap({
  polyline,
  segments = [],
  height = "320px",
  accentColor = "#fc4c02",
}) {
  if (!polyline) {
    return (
      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", background: "var(--surface)", borderRadius: "var(--radius)", color: "var(--muted)", fontSize: 13 }}>
        No route data
      </div>
    );
  }

  // @mapbox/polyline decodes to [[lat, lng], ...]
  const positions = polylineCodec.decode(polyline);

  if (positions.length === 0) return null;

  const center = positions[Math.floor(positions.length / 2)];

  return (
    <MapContainer
      center={center}
      zoom={13}
      style={{ height, borderRadius: "var(--radius)", zIndex: 0 }}
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds positions={positions} />

      {/* Main route */}
      <Polyline positions={positions} color={accentColor} weight={3} opacity={0.9} />

      {/* Start marker */}
      <Marker position={positions[0]} />

      {/* Segment start/end markers */}
      {segments.map((seg, i) => {
        if (!seg.segment_start_latlng) return null;
        const isPR = seg.pr_rank === 1;
        const icon = L.divIcon({
          className: "",
          html: `<div style="width:10px;height:10px;border-radius:50%;background:${isPR ? "#facc15" : "#60a5fa"};border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.5)"></div>`,
          iconSize: [10, 10],
          iconAnchor: [5, 5],
        });
        return (
          <Marker key={i} position={seg.segment_start_latlng} icon={icon} title={seg.name} />
        );
      })}
    </MapContainer>
  );
}
