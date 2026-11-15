// src/components/earth/AnalyticsCharts.jsx
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

export default function AnalyticsCharts({ chartsData }) {
  const radarRef = useRef(null);
  const thermalRef = useRef(null);
  const terrainRef = useRef(null);

  const radarInstance = useRef(null);
  const thermalInstance = useRef(null);
  const terrainInstance = useRef(null);

  const colors = ["#34d399", "#38bdf8", "#a78bfa"];

  useEffect(() => {
    if (!chartsData) return;

    // 1. Radar Chart
    if (radarInstance.current) radarInstance.current.destroy();
    if (radarRef.current) {
      radarInstance.current = new Chart(radarRef.current, {
        type: "radar",
        data: {
          labels: chartsData.category_radar.map((x) => x.category),
          datasets: [1, 2, 3].map((r, i) => ({
            label: `Match #${r}`,
            data: chartsData.category_radar.map((x) => x[`candidate_${r}`]),
            borderColor: colors[i],
            backgroundColor: colors[i] + "28",
          })),
        },
        options: {
          maintainAspectRatio: false,
          scales: {
            r: {
              min: 0,
              max: 100,
              ticks: { backdropColor: "transparent", color: "#94a3b8" },
              grid: { color: "#1e3a32" },
              pointLabels: { color: "#cbd5e1", font: { size: 10 } },
            },
          },
          plugins: { legend: { labels: { color: "#e6edf7" } } },
        },
      });
    }

    // 2. Thermal Chart
    if (thermalInstance.current) thermalInstance.current.destroy();
    if (thermalRef.current) {
      thermalInstance.current = new Chart(thermalRef.current, {
        type: "bar",
        data: {
          labels: chartsData.thermal_envelope.map((x) => x.location),
          datasets: [
            { label: "Night Min (°C)", data: chartsData.thermal_envelope.map((x) => x.temp_night_min_c), backgroundColor: "#38bdf8" },
            { label: "Day Max (°C)", data: chartsData.thermal_envelope.map((x) => x.temp_day_max_c), backgroundColor: "#f97316" },
            { label: "Swing (°C)", data: chartsData.thermal_envelope.map((x) => x.diurnal_swing_c), backgroundColor: "#facc15" },
          ],
        },
        options: {
          maintainAspectRatio: false,
          scales: {
            x: { ticks: { color: "#94a3b8" } },
            y: { ticks: { color: "#94a3b8" }, grid: { color: "#1e3a32" } },
          },
          plugins: { legend: { labels: { color: "#e6edf7" } } },
        },
      });
    }

    // 3. Terrain Chart
    if (terrainInstance.current) terrainInstance.current.destroy();
    if (terrainRef.current) {
      terrainInstance.current = new Chart(terrainRef.current, {
        type: "bar",
        data: {
          labels: chartsData.terrain_profile.map((x) => x.location),
          datasets: [
            { label: "Mean Slope (°)", data: chartsData.terrain_profile.map((x) => x.slope_mean_deg), backgroundColor: "#34d399" },
            { label: "P95 Slope (°)", data: chartsData.terrain_profile.map((x) => x.slope_p95_deg), backgroundColor: "#a78bfa" },
          ],
        },
        options: {
          maintainAspectRatio: false,
          scales: {
            x: { ticks: { color: "#94a3b8" } },
            y: { ticks: { color: "#94a3b8" }, grid: { color: "#1e3a32" } },
          },
          plugins: { legend: { labels: { color: "#e6edf7" } } },
        },
      });
    }
  }, [chartsData]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full font-mono">
      <div className="rounded-2xl border-2 border-emerald-900/60 bg-[#121317] p-5 shadow-xl flex flex-col justify-between">
        <h3 className="text-sm font-bold text-emerald-50 mb-2">Category Similarity (%)</h3>
        <div className="relative w-full h-64">
          <canvas ref={radarRef} />
        </div>
      </div>

      <div className="rounded-2xl border-2 border-emerald-900/60 bg-[#121317] p-5 shadow-xl flex flex-col justify-between">
        <h3 className="text-sm font-bold text-emerald-50 mb-2">Thermal Envelope (°C)</h3>
        <div className="relative w-full h-64">
          <canvas ref={thermalRef} />
        </div>
      </div>

      <div className="rounded-2xl border-2 border-emerald-900/60 bg-[#121317] p-5 shadow-xl flex flex-col justify-between">
        <h3 className="text-sm font-bold text-emerald-50 mb-2">Terrain Slope Profile (°)</h3>
        <div className="relative w-full h-64">
          <canvas ref={terrainRef} />
        </div>
      </div>
    </div>
  );
}