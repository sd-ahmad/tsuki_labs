// src/components/selection/SelectionHeader.jsx

export default function SelectionHeader() {
  return (
    <header className="w-full px-8 py-7 flex items-center justify-between sticky top-0 z-50 relative overflow-hidden bg-gradient-to-b from-black/80 via-black/40 to-transparent">
      {/* Left Title Content */}
      <div className="flex items-center font-mono relative z-10">
        <span className="text-sm font-bold tracking-widest uppercase text-zinc-200 drop-shadow-md">
          NASA Space Apps 2026 // Project Kagami
        </span>
      </div>

      {/* Navigation Breadcrumb (Highlighting Selection) */}
      <div className="relative z-10 flex items-center gap-2 font-mono text-sm text-zinc-400">
        <a href="/" className="hover:text-zinc-200 transition-colors">Home</a>
        <span>/</span>
        <span className="text-zinc-100 font-bold underline underline-offset-4">Selection</span>
      </div>
    </header>
  );
}