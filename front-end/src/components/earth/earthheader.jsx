// src/components/earth/earthheader.jsx
import earthBanner from "../../assets/earthmap1.jpg";

export default function Header() {
  return (
    <header className="w-full px-8 py-7 flex items-center justify-between sticky top-0 z-50 relative overflow-hidden bg-black font-mono">
      {/* Earth Background Banner Image (8192x849 optimized with object-cover) */}
      <img
        src={earthBanner}
        alt="Earth Horizon"
        className="absolute inset-0 w-full h-full object-cover object-center opacity-45 pointer-events-none z-0"
      />
      
      {/* Dark Gradient Overlay for Text Readability & Bottom Fade */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/85 via-black/40 to-black/85 pointer-events-none z-0" />
      <div className="absolute inset-x-0 bottom-0 h-6 bg-gradient-to-t from-black to-transparent pointer-events-none z-0" />

      {/* Left Title Content */}
      <div className="flex items-center relative z-10">
        <span className="text-sm font-bold tracking-widest uppercase text-emerald-50 drop-shadow-md">
          NASA Space Apps 2026 // Project Kagami
        </span>
      </div>

      {/* Navigation Breadcrumb */}
      <div className="relative z-10 flex items-center gap-2 text-sm text-emerald-200/70">
        <a href="/" className="hover:text-emerald-200 transition-colors">Home</a>
        <span>/</span>
        <a href="/selection" className="hover:text-emerald-200 transition-colors">Selection</a>
        <span>/</span>
        <span className="text-emerald-400 font-bold underline underline-offset-4">Earth</span>
      </div>
    </header>
  );
}