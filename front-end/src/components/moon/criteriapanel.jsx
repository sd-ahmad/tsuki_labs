// src/components/moon/CriteriaPanel.jsx

import { useState } from "react";

const PRIORITIES = [
  { id: "geology", label: "Geology & Mineralogy" },
  { id: "terrain", label: "Terrain & Topography" },
  { id: "thermal", label: "Thermal & Extremes" },
  { id: "water", label: "Water & Ice" },
  { id: "mobility", label: "Landing & Mobility" },
  { id: "overall", label: "Best Overall" },
];

export default function CriteriaPanel({ selectedCoords = null, onSelectPriority = () => {} }) {
  const [selectedPriority, setSelectedPriority] = useState(null);

  const handlePriorityClick = (id) => {
    setSelectedPriority(id);
    onSelectPriority(id);
  };

  return (
    <div className="flex flex-col justify-between items-center h-full w-full rounded-2xl border-2 border-zinc-700/80 bg-[#121317] p-8 shadow-2xl text-zinc-200 text-center relative overflow-hidden">
      {/* Ambient Glow */}
      <div className="absolute -top-24 -right-24 w-56 h-56 bg-zinc-400/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="w-full flex flex-col items-center relative z-10">
        <h2 className="text-4xl font-black tracking-wider text-white font-mono uppercase">
          Priority
        </h2>
        <p className="mt-2 text-sm text-zinc-400 font-medium tracking-wide">
          Select a priority and click a point on the map
        </p>
      </div>

      {/* Priority Buttons */}
      <div className="flex flex-col justify-center items-center gap-3 w-full my-4 relative z-10">
        {PRIORITIES.map((item) => {
          const isSelected = selectedPriority === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handlePriorityClick(item.id)}
              className={`w-full rounded-xl px-4 py-3.5 text-sm font-bold tracking-wide transition-all duration-300 ease-out border-2 flex items-center justify-center text-center font-mono cursor-pointer hover:scale-[1.02] ${
                isSelected
                  ? "bg-gradient-to-r from-zinc-200 to-zinc-400 border-white text-zinc-950 shadow-lg shadow-zinc-300/20 scale-[1.02]"
                  : "bg-[#1b1c22] border-zinc-800 text-zinc-300 hover:bg-zinc-200/15 hover:border-zinc-300 hover:text-white"
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </div>

      {/* Clicked Target Coordinates HUD */}
      <div className="w-full relative z-10">
        <div className="w-full rounded-2xl bg-[#18191f] border-2 border-zinc-700/90 px-5 py-3.5 font-mono shadow-inner flex flex-col items-center justify-center gap-1.5">
          <span className="text-[11px] uppercase tracking-widest text-zinc-400 font-semibold">
            Selected Target Coordinates
          </span>
          <div className="flex items-center justify-center gap-4 text-sm font-bold whitespace-nowrap">
            <span className="text-white">
              Lat: {selectedCoords ? selectedCoords.lat : "---"}
            </span>
            <span className="text-zinc-600">|</span>
            <span className="text-zinc-300">
              Long: {selectedCoords ? selectedCoords.lon : "---"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}