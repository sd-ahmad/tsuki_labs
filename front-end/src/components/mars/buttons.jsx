// src/components/mars/Buttons.jsx

export default function Buttons({ onBack = () => {}, onForward = () => {} }) {
  return (
    <div className="grid grid-cols-2 gap-4 w-full max-w-lg mx-auto">
      <button
        onClick={onBack}
        className="w-full rounded-xl px-4 py-3 text-sm font-bold tracking-wide transition-all duration-300 ease-out border-2 border-amber-900/60 bg-[#1f1815] text-amber-200/80 hover:bg-amber-500/15 hover:border-amber-600 hover:text-white hover:scale-[1.02] flex items-center justify-center font-mono cursor-pointer shadow-lg"
      >
        ← Selection
      </button>
      <button
        onClick={onForward}
        className="w-full rounded-xl px-4 py-3 text-sm font-bold tracking-wide transition-all duration-300 ease-out border-2 border-amber-300 bg-gradient-to-r from-amber-200 via-amber-300 to-orange-300 text-zinc-950 hover:from-amber-100 hover:to-amber-200 hover:scale-[1.02] flex items-center justify-center font-mono cursor-pointer shadow-lg shadow-amber-500/20"
      >
        View Earth Locations →
      </button>
    </div>
  );
}