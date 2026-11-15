// src/components/mars/marsheader.jsx
import marsBanner from "../../assets/marsmap.jpg";

export default function MarsHeader() {
  return (
    <header className="w-full px-8 py-7 flex items-center justify-between sticky top-0 z-50 relative overflow-hidden bg-black font-mono">
      {/* Mars Background Banner Image */}
      <img
        src={marsBanner}
        alt="Mars Horizon"
        className="absolute inset-0 w-full h-full object-cover object-center opacity-45 pointer-events-none z-0"
      />
      
      {/* Dark Gradient Overlay & Bottom Fade */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/85 via-black/40 to-black/85 pointer-events-none z-0" />
      <div className="absolute inset-x-0 bottom-0 h-6 bg-gradient-to-t from-black to-transparent pointer-events-none z-0" />

      {/* Left Title Content */}
      <div className="flex items-center relative z-10">
        <span className="text-sm font-bold tracking-widest uppercase text-amber-100 drop-shadow-md">
          NASA Space Apps 2026 // Project Kagami
        </span>
      </div>

      {/* Navigation Breadcrumb */}
      <div className="relative z-10 flex items-center gap-2 text-sm text-zinc-400">
        <a href="/" className="hover:text-zinc-200 transition-colors">Home</a>
        <span>/</span>
        <a href="/selection" className="hover:text-zinc-200 transition-colors">Selection</a>
        <span>/</span>
        <span className="text-orange-400 font-bold underline underline-offset-4">Mars</span>
      </div>
    </header>
  );
}