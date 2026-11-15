// src/components/moon/Buttons.jsx

export default function Buttons({ onBack = () => {}, onForward = () => {} }) {
  return (
    <div className="grid grid-cols-2 gap-4 w-full max-w-lg mx-auto">
      <button
        onClick={onBack}
        className="w-full rounded-xl px-4 py-3 text-sm font-bold tracking-wide transition-all duration-300 ease-out border-2 border-zinc-700/80 bg-[#1b1c22] text-zinc-300 hover:bg-zinc-200/15 hover:border-zinc-300 hover:text-white hover:scale-[1.02] flex items-center justify-center font-mono cursor-pointer shadow-lg"
      >
        ← Selection
      </button>
      <button
        onClick={onForward}
        className="w-full rounded-xl px-4 py-3 text-sm font-bold tracking-wide transition-all duration-300 ease-out border-2 border-white bg-gradient-to-r from-zinc-200 to-zinc-400 text-zinc-950 hover:from-white hover:to-zinc-300 hover:scale-[1.02] flex items-center justify-center font-mono cursor-pointer shadow-lg shadow-zinc-300/20"
      >
        View Earth Locations →
      </button>
    </div>
  );
}