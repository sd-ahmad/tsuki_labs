// src/pages/Moon.jsx

import { useState } from "react";
import MoonMap from "../components/moon/MoonMap";
import CriteriaPanel from "../components/moon/criteriapanel";
import Buttons from "../components/moon/buttons";
import Header from "../components/moon/moonheader";
import { runAnalogAnalysis } from "../api/analogApi";

const STATIC_STARS = [
  { top: "5%", left: "4%", size: "w-1 h-1", opacity: "opacity-70", delay: "0s" },
  { top: "9%", left: "14%", size: "w-0.5 h-0.5", opacity: "opacity-50", delay: "1.2s" },
  { top: "12%", left: "25%", size: "w-1.5 h-1.5", opacity: "opacity-40", delay: "0.5s" },
  { top: "15%", left: "38%", size: "w-0.5 h-0.5", opacity: "opacity-60", delay: "2.1s" },
  { top: "8%", left: "52%", size: "w-1 h-1", opacity: "opacity-50", delay: "1.7s" },
  { top: "22%", left: "65%", size: "w-1 h-1", opacity: "opacity-65", delay: "0.8s" },
  { top: "25%", left: "78%", size: "w-1 h-1", opacity: "opacity-55", delay: "2.4s" },
  { top: "19%", left: "89%", size: "w-0.5 h-0.5", opacity: "opacity-40", delay: "1.1s" },
  { top: "28%", left: "96%", size: "w-1.5 h-1.5", opacity: "opacity-35", delay: "2.9s" },
  { top: "24%", left: "8%", size: "w-1 h-1", opacity: "opacity-60", delay: "0.3s" },
  { top: "35%", left: "18%", size: "w-0.5 h-0.5", opacity: "opacity-50", delay: "1.9s" },
  { top: "38%", left: "31%", size: "w-1 h-1", opacity: "opacity-70", delay: "1.4s" },
  { top: "33%", left: "45%", size: "w-1 h-1", opacity: "opacity-45", delay: "2.6s" },
  { top: "42%", left: "59%", size: "w-1.5 h-1.5", opacity: "opacity-40", delay: "0.7s" },
  { top: "37%", left: "72%", size: "w-0.5 h-0.5", opacity: "opacity-65", delay: "1.5s" },
  { top: "45%", left: "85%", size: "w-1 h-1", opacity: "opacity-55", delay: "2.2s" },
  { top: "49%", left: "95%", size: "w-0.5 h-0.5", opacity: "opacity-60", delay: "3.1s" },
  { top: "44%", left: "3%", size: "w-1 h-1", opacity: "opacity-50", delay: "0.9s" },
  { top: "52%", left: "16%", size: "w-1 h-1", opacity: "opacity-75", delay: "0.4s" },
  { top: "58%", left: "29%", size: "w-0.5 h-0.5", opacity: "opacity-50", delay: "1.8s" },
  { top: "62%", left: "42%", size: "w-1 h-1", opacity: "opacity-60", delay: "2.5s" },
  { top: "56%", left: "55%", size: "w-1.5 h-1.5", opacity: "opacity-40", delay: "1.3s" },
  { top: "65%", left: "68%", size: "w-0.5 h-0.5", opacity: "opacity-70", delay: "0.6s" },
  { top: "60%", left: "81%", size: "w-1 h-1", opacity: "opacity-45", delay: "2.0s" },
  { top: "72%", left: "92%", size: "w-1 h-1", opacity: "opacity-65", delay: "1.0s" },
  { top: "75%", left: "6%", size: "w-0.5 h-0.5", opacity: "opacity-50", delay: "2.7s" },
  { top: "69%", left: "20%", size: "w-1 h-1", opacity: "opacity-60", delay: "0.2s" },
  { top: "78%", left: "35%", size: "w-1.5 h-1.5", opacity: "opacity-35", delay: "1.6s" },
  { top: "71%", left: "49%", size: "w-0.5 h-0.5", opacity: "opacity-55", delay: "2.3s" },
  { top: "85%", left: "62%", size: "w-1 h-1", opacity: "opacity-70", delay: "0.9s" },
  { top: "82%", left: "75%", size: "w-0.5 h-0.5", opacity: "opacity-60", delay: "1.7s" },
  { top: "88%", left: "88%", size: "w-1 h-1", opacity: "opacity-50", delay: "2.8s" },
  { top: "84%", left: "98%", size: "w-1 h-1", opacity: "opacity-65", delay: "0.5s" },
  { top: "94%", left: "11%", size: "w-1.5 h-1.5", opacity: "opacity-40", delay: "1.2s" },
  { top: "91%", left: "26%", size: "w-0.5 h-0.5", opacity: "opacity-55", delay: "2.1s" },
  { top: "96%", left: "53%", size: "w-1 h-1", opacity: "opacity-70", delay: "0.4s" },
  { top: "93%", left: "67%", size: "w-1 h-1", opacity: "opacity-45", delay: "1.8s" },
  { top: "97%", left: "84%", size: "w-0.5 h-0.5", opacity: "opacity-60", delay: "2.6s" }
];

const FALLING_STARS = [
  { left: "5%", height: "h-[110px]", duration: "11s", delay: "0s" },
  { left: "22%", height: "h-[100px]", duration: "13s", delay: "2.5s" },
  { left: "40%", height: "h-[120px]", duration: "10s", delay: "5s" },
  { left: "58%", height: "h-[105px]", duration: "15s", delay: "1s" },
  { left: "75%", height: "h-[115px]", duration: "12s", delay: "3.5s" },
  { left: "90%", height: "h-[110px]", duration: "14s", delay: "6s" },
  { left: "105%", height: "h-[105px]", duration: "11s", delay: "4s" }
];

export default function Moon() {
  const [selectedCoords, setSelectedCoords] = useState(null);
  const [selectedPriority, setSelectedPriority] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleBack = () => {
    window.location.href = "/selection";
  };

  const handleForward = async () => {
    if (loading) return;
    if (!selectedCoords) {
      alert("Please click a point on the map to select target coordinates.");
      return;
    }

    setLoading(true);
    try {
      await runAnalogAnalysis({
        body: "moon",
        coords: selectedCoords,
        priority: selectedPriority,
        topK: 3,
      });
      window.location.href = "/earth";
    } catch (err) {
      alert(`Error finding Earth analogs: ${err.message}`);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-black text-zinc-100 flex flex-col justify-between selection:bg-zinc-700 selection:text-white relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        {STATIC_STARS.map((star, idx) => (
          <div
            key={`star-${idx}`}
            className={`absolute bg-white rounded-full animate-pulse ${star.size} ${star.opacity}`}
            style={{ top: star.top, left: star.left, animationDelay: star.delay }}
          />
        ))}
        {FALLING_STARS.map((meteor, idx) => (
          <div
            key={`meteor-${idx}`}
            className={`absolute -top-16 w-[1.5px] bg-gradient-to-b from-transparent via-zinc-200 to-transparent opacity-0 rotate-[35deg] ${meteor.height}`}
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

      {loading && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center">
          <div className="border border-zinc-600 bg-zinc-950 px-8 py-6 rounded-2xl text-center font-mono">
            <p className="text-zinc-100 text-lg font-bold">Analyzing Lunar Terrain & Matching Earth Analogs...</p>
            <p className="text-zinc-400 text-xs mt-2">First request may take ~30s while the backend wakes up.</p>
          </div>
        </div>
      )}

      <main className="flex-1 w-full max-w-[1700px] mx-auto p-8 flex flex-col justify-center relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start w-full">
          <div className="lg:col-span-8 flex flex-col gap-4">
            <MoonMap onSelectCoords={(coords) => setSelectedCoords(coords)} />
            <Buttons onBack={handleBack} onForward={handleForward} loading={loading} />
          </div>

          <div className="lg:col-span-4 w-full h-full">
            <CriteriaPanel
              selectedCoords={selectedCoords}
              onSelectPriority={(priorityId) => setSelectedPriority(priorityId)}
            />
          </div>
        </div>
      </main>
    </div>
  );
}