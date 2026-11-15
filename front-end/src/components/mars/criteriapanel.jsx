// src/components/mars/CriteriaPanel.jsx

import { useState } from "react";

const PRIORITIES = [
  { id: "geology", label: "Geology & Mineralogy" },
  { id: "terrain", label: "Terrain & Topography" },
  { id: "thermal", label: "Thermal & Extremes" },
  { id: "water", label: "Water Ice & Volatiles" },
  { id: "atmosphere", label: "Atmospheric Pressure & Winds" },
  { id: "radiation", label: "Radiation & Solar Flux" },
  { id: "mobility", label: "Landing & Rover Mobility" },
  { id: "overall", label: "Best Overall" },
];

export default function CriteriaPanel({ selectedCoords = null, onSelectPriority = () => {} }) {
  const [selectedPriority, setSelectedPriority] = useState(null);

  const handlePriorityClick = (id) => {
    setSelectedPriority(id);
    onSelectPriority(id);
  };

  return (
    <div className="flex flex-col justify-between items-center h-full w-full rounded-2xl border-2 border-amber-900/40 bg-[#161210] p-7 shadow-2xl text-amber-100 text-center relative overflow-hidden">
      {/* Subtle Fiery Ambient Glows */}
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-orange-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-amber-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="w-full flex flex-col items-center pt-1 pb-2 relative z-10">
        <h2 className="text-4xl font-black tracking-wider text-amber-100 font-mono uppercase drop-shadow">
          Priority
        </h2>
        <p className="mt-1.5 text-sm text-amber-300/70 font-medium tracking-wide">
          Select a priority and click a point on the map
        </p>
      </div>

      {/* 8 Priority Buttons */}
      <div className="flex flex-col justify-center items-center gap-2 w-full my-3 relative z-10">
        {PRIORITIES.map((item) => {
          const isSelected = selectedPriority === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handlePriorityClick(item.id)}
              className={`w-full rounded-xl px-4 py-2.5 text-sm font-bold tracking-wide transition-all duration-300 ease-out border-2 flex items-center justify-center text-center font-mono cursor-pointer hover:scale-[1.02] ${
                isSelected
                  ? "bg-gradient-to-r from-amber-200 via-amber-300 to-orange-300 border-amber-100 text-zinc-950 shadow-lg shadow-amber-500/20 scale-[1.02]"
                  : "bg-[#1f1815] border-amber-900/40 text-amber-200/80 hover:bg-amber-500/10 hover:border-amber-600/50 hover:text-white"
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </div>

      {/* Clicked Target Coordinates HUD */}
      <div className="w-full pb-1 relative z-10">
        <div className="w-full rounded-2xl bg-[#1b1412] border-2 border-amber-900/50 px-5 py-3.5 font-mono shadow-inner flex flex-col items-center justify-center gap-1.5">
          <span className="text-[11px] uppercase tracking-widest text-amber-400/80 font-semibold">
            Selected Target Coordinates
          </span>
          <div className="flex items-center justify-center gap-4 text-sm font-bold whitespace-nowrap">
            <span className="text-amber-100">
              Lat: {selectedCoords ? selectedCoords.lat : "---"}
            </span>
            <span className="text-amber-900">|</span>
            <span className="text-orange-200">
              Long: {selectedCoords ? selectedCoords.lon : "---"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}