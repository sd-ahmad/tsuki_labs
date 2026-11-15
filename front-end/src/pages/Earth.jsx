// src/pages/Earth.jsx
import { useState, useEffect } from "react";
import Header from "../components/earth/earthheader";
import EarthControls from "../components/earth/EarthControls";
import EarthMap from "../components/earth/earthmap";
import AnalogsPanel from "../components/earth/AnalogsPanel";
import AnalyticsCharts from "../components/earth/analyticscharts";
import ComparisonTable from "../components/earth/comparisontable";

const STATIC_STARS = [
  { top: "12%", left: "25%", size: "w-1.5 h-1.5", opacity: "opacity-40", delay: "0.5s" },
  { top: "22%", left: "65%", size: "w-1 h-1", opacity: "opacity-65", delay: "0.8s" },
  { top: "35%", left: "18%", size: "w-0.5 h-0.5", opacity: "opacity-50", delay: "1.9s" },
  { top: "45%", left: "85%", size: "w-1 h-1", opacity: "opacity-55", delay: "2.2s" },
  { top: "58%", left: "29%", size: "w-0.5 h-0.5", opacity: "opacity-50", delay: "1.8s" },
  { top: "71%", left: "49%", size: "w-0.5 h-0.5", opacity: "opacity-55", delay: "2.3s" }
];

const FALLING_STARS = [
  { left: "10%", height: "h-[110px]", duration: "12s", delay: "0s" },
  { left: "45%", height: "h-[120px]", duration: "10s", delay: "3s" },
  { left: "80%", height: "h-[115px]", duration: "14s", delay: "1.5s" }
];

const API_BASE = "https://tsuki-labs.onrender.com";

function readSavedAnalog() {
  try {
    const raw = sessionStorage.getItem("analogResult");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function Earth() {
  const [initialSaved] = useState(() => readSavedAnalog());

  const [body, setBody] = useState(() => initialSaved?.source?.body || sessionStorage.getItem("lastBody") || "mars");
  const [lat, setLat] = useState(() =>
    initialSaved?.source?.latitude != null ? String(initialSaved.source.latitude) : "18.38"
  );
  const [lon, setLon] = useState(() =>
    initialSaved?.source?.longitude != null ? String(initialSaved.source.longitude) : "77.58"
  );
  const [categories, setCategories] = useState(["Best Overall"]);
  const [category, setCategory] = useState(() => {
    const cat = initialSaved?.priority_category;
    if (!cat || cat === "All Conditions" || cat === "Best Overall") return "Best Overall";
    return cat;
  });

  const [queryData, setQueryData] = useState(() =>
    initialSaved || {
      source: { label: "Target Site" },
      priority_category: "Best Overall",
      candidates: [],
      charts: null,
      comparison_table: [],
    }
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load categories when body changes, ensuring "Best Overall" sits at the bottom
  useEffect(() => {
    let active = true;
    async function loadCategories() {
      try {
        const res = await fetch(`${API_BASE}/api/categories?body=${encodeURIComponent(body)}`);
        const data = await res.json();
        if (!active) return;
        const filtered = (data.categories || []).filter(
          (c) => c !== "All Conditions" && c !== "Best Overall"
        );
        const list = [...Array.from(new Set(filtered)), "Best Overall"];
        setCategories(list);
        if (!list.includes(category)) {
          setCategory("Best Overall");
        }
      } catch (err) {
        console.error("Failed to load categories", err);
      }
    }
    loadCategories();
    return () => {
      active = false;
    };
  }, [body]);

  // Run Query to API
  const runQuery = async () => {
    setError("");
    setLoading(true);
    const priority_category =
      !category || category === "Best Overall" || category === "All Conditions"
        ? null
        : category;

    try {
      const res = await fetch(`${API_BASE}/api/find-analogs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          longitude: Number(lon),
          latitude: Number(lat),
          astronomical_body: body,
          priority_category,
          top_k: 3,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "API error");
      setQueryData(data);
      sessionStorage.setItem("analogResult", JSON.stringify(data));
      sessionStorage.setItem("lastBody", body);
    } catch (err) {
      setError("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Only auto-fetch default preset if user did not come from Mars/Moon selection
  useEffect(() => {
    if (!initialSaved) {
      runQuery();
    }
  }, []);

  return (
    <div className="min-h-screen w-full bg-black text-emerald-50 flex flex-col justify-between selection:bg-emerald-600 selection:text-white relative overflow-hidden">
      {/* Subtle Emerald / Ocean-Forest Ambient Background Glows */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[400px] bg-gradient-to-b from-emerald-600/10 via-teal-600/5 to-transparent rounded-full blur-[120px] pointer-events-none z-0" />
      <div className="absolute bottom-10 right-10 w-[500px] h-[400px] bg-gradient-to-t from-blue-600/10 via-emerald-600/5 to-transparent rounded-full blur-[140px] pointer-events-none z-0" />

      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        {STATIC_STARS.map((star, idx) => (
          <div
            key={`star-${idx}`}
            className={`absolute bg-emerald-100 rounded-full animate-pulse ${star.size} ${star.opacity}`}
            style={{ top: star.top, left: star.left, animationDelay: star.delay }}
          />
        ))}

        {FALLING_STARS.map((meteor, idx) => (
          <div
            key={`meteor-${idx}`}
            className={`absolute -top-16 w-[1.5px] bg-gradient-to-b from-transparent via-emerald-300 to-transparent opacity-0 rotate-[35deg] ${meteor.height}`}
            style={{
              left: meteor.left,
              animation: `shootingStar ${meteor.duration} ease-in-out infinite ${meteor.delay}`,
            }}
          />
        ))}
      </div>

      <style>{`
        @keyframes shootingStar {
          0% { transform: translateY(0) translateX(0) rotate(35deg); opacity: 0; }
          10% { opacity: 0.85; }
          85% { opacity: 0.85; }
          98% { transform: translateY(1200px) translateX(-700px) rotate(35deg); opacity: 0; }
          100% { transform: translateY(1200px) translateX(-700px) rotate(35deg); opacity: 0; }
        }
      `}</style>

      <div className="relative z-10">
        <Header />
      </div>

      <main className="flex-1 w-full max-w-[1700px] mx-auto p-8 flex flex-col gap-6 justify-center relative z-10">
        {/* Controls Card */}
        <EarthControls
          body={body} setBody={setBody}
          lat={lat} setLat={setLat}
          lon={lon} setLon={setLon}
          categories={categories} category={category} setCategory={setCategory}
          onRunQuery={runQuery} loading={loading} error={error}
        />

        {/* Top Grid: Interactive Map + Analogs Ranking Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch w-full">
          <div className="lg:col-span-8 h-full">
            <EarthMap candidates={queryData.candidates} />
          </div>
          <div className="lg:col-span-4 h-full">
            <AnalogsPanel
              sourceLabel={queryData.source?.label}
              priorityCategory={queryData.priority_category}
              candidates={queryData.candidates}
            />
          </div>
        </div>

        {/* Analytics Graphs Grid */}
        {queryData.charts && (
          <div className="w-full">
            <AnalyticsCharts chartsData={queryData.charts} />
          </div>
        )}

        {/* Comparison Table */}
        {queryData.comparison_table?.length > 0 && (
          <div className="w-full">
            <ComparisonTable
              comparisonRows={queryData.comparison_table}
              sourceLabel={queryData.source?.label}
            />
          </div>
        )}

        {/* Centered Navigation Button */}
        <div className="flex justify-center items-center w-full pt-4">
          <button
            onClick={() => (window.location.href = "/selection")}
            className="w-full max-w-xs rounded-xl px-6 py-3 text-sm font-bold tracking-wide transition-all duration-300 ease-out border-2 border-emerald-700/70 bg-[#1b3b2b] text-emerald-100 hover:bg-[#234d37] hover:border-emerald-600 hover:scale-[1.02] flex items-center justify-center font-mono cursor-pointer shadow-lg"
          >
            Return to Selection →
          </button>
        </div>
      </main>
    </div>
  );
}