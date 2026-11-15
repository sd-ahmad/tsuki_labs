// src/components/earth/AnalogsPanel.jsx
export default function AnalogsPanel({ sourceLabel, priorityCategory, candidates, onSelectCard }) {
  const displayMode = !priorityCategory || priorityCategory === "All Conditions" || priorityCategory === "Best Overall"
    ? "Best Overall"
    : priorityCategory;

  return (
    <div className="flex flex-col h-full w-full rounded-2xl border-2 border-emerald-900/60 bg-[#121317] p-6 shadow-2xl text-emerald-50 font-mono relative overflow-hidden">
      <div className="flex items-center justify-between gap-3 pb-4 border-b border-emerald-900/40 mb-4">
        <span className="text-sm font-bold text-white truncate">
          {sourceLabel || "Candidate Summary"}
        </span>
        <span className="text-xs px-3 py-1 rounded-full bg-[#0c1714] text-emerald-400 border border-emerald-800/70 shrink-0 whitespace-nowrap">
          Mode: {displayMode}
        </span>
      </div>

      <div className="flex flex-col gap-3.5 flex-1 justify-between">
        {candidates.map((c, i) => (
          <div
            key={i}
            onClick={() => onSelectCard && onSelectCard(c)}
            className="bg-[#0c1714] border border-emerald-900/50 hover:border-emerald-400 rounded-xl p-4 transition-all cursor-pointer flex flex-col justify-center gap-2 shadow-md group"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="text-sm font-extrabold text-white group-hover:text-emerald-400 transition-colors leading-snug">
                #{c.rank} {c.location_name}
              </span>
              <span className="text-xs px-3 py-1 rounded-full font-bold border bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shrink-0 whitespace-nowrap">
                {c.similarity_pct}% match
              </span>
            </div>
            <div className="text-xs text-emerald-200/70">
              Lat: {c.earth_latitude.toFixed(3)}, Lon: {c.earth_longitude.toFixed(3)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}