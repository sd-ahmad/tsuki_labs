// src/components/earth/EarthMap.jsx
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export default function EarthMap({ candidates, onSelectCandidate }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerLayerRef = useRef(null);

  useEffect(() => {
    if (!mapInstanceRef.current) {
      const map = L.map(mapRef.current).setView([20, 0], 2);
      L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        { attribution: "Esri World Imagery" }
      ).addTo(map);

      markerLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;
    }
  }, []);

  useEffect(() => {
    const map = mapInstanceRef.current;
    const markerLayer = markerLayerRef.current;
    if (!map || !markerLayer) return;

    markerLayer.clearLayers();
    const bounds = [];
    const colors = ["#34d399", "#38bdf8", "#a78bfa"];

    candidates.forEach((c, i) => {
      const lat = c.earth_latitude;
      const lon = c.earth_longitude;
      bounds.push([lat, lon]);

      const marker = L.circleMarker([lat, lon], {
        radius: 9,
        color: "#fff",
        weight: 2,
        fillColor: colors[i],
        fillOpacity: 0.9,
      }).bindPopup(
        `<b>#${c.rank} ${c.location_name}</b> (${c.similarity_pct}%)<br>Lat: ${lat.toFixed(3)}, Lon: ${lon.toFixed(3)}`
      );

      marker.on("click", () => {
        if (onSelectCandidate) onSelectCandidate(c);
      });

      marker.addTo(markerLayer);
    });

    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 5 });
    }
  }, [candidates, onSelectCandidate]);

  return (
    <div className="w-full h-full min-h-[420px] rounded-2xl border-2 border-emerald-900/60 bg-[#121317] overflow-hidden relative shadow-2xl flex flex-col font-mono">
      <div className="absolute top-4 left-4 z-[400] bg-black/80 backdrop-blur-md px-4 py-2 rounded-xl border border-emerald-800/70 text-xs text-emerald-50 shadow-lg flex items-center gap-3">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
        <span className="font-bold tracking-wider uppercase">Top 3 Earth Analog Locations</span>
      </div>
      <div ref={mapRef} className="w-full flex-1 z-10 min-h-[380px]" />
    </div>
  );
}