// src/components/earth/EarthControls.jsx
export default function EarthControls({
  body, setBody,
  lat, setLat,
  lon, setLon,
  categories, category, setCategory,
  onRunQuery, loading, error
}) {
  return (
    <div className="w-full rounded-2xl border-2 border-zinc-700/80 bg-[#121317] p-6 shadow-2xl font-mono text-zinc-200">
      <h1 className="text-lg font-bold text-white mb-5 text-center tracking-wide">
        Backend Analog Matcher Control Panel
      </h1>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
        <div>
          <label className="block text-xs text-zinc-400 mb-1.5 text-center">Body</label>
          <select
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-zinc-700 bg-[#0e1422] text-white text-sm text-center focus:outline-none focus:border-zinc-500 cursor-pointer"
          >
            <option value="mars">Mars</option>
            <option value="moon">Moon</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1.5 text-center">Latitude (°)</label>
          <input
            type="number"
            step="0.01"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-zinc-700 bg-[#0e1422] text-white text-sm text-center focus:outline-none focus:border-zinc-500"
          />
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1.5 text-center">Longitude (°)</label>
          <input
            type="number"
            step="0.01"
            value={lon}
            onChange={(e) => setLon(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-zinc-700 bg-[#0e1422] text-white text-sm text-center focus:outline-none focus:border-zinc-500"
          />
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1.5 text-center">Priority Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-zinc-700 bg-[#0e1422] text-white text-sm text-center focus:outline-none focus:border-zinc-500 cursor-pointer"
          >
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <button
            onClick={onRunQuery}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl font-bold bg-[#1b3b2b] border border-emerald-700/70 text-emerald-100 hover:bg-[#234d37] hover:border-emerald-600 transition-all cursor-pointer text-sm shadow-md disabled:opacity-50 text-center"
          >
            {loading ? "Analyzing..." : "Find Earth Analogs"}
          </button>
        </div>
      </div>

      {error && <div className="text-rose-400 text-xs mt-3 text-center">{error}</div>}
    </div>
  );
}