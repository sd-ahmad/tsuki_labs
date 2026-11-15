// src/components/global/Navibar.jsx

export default function Navibar() {
  return (
    <nav className="flex items-center gap-6 font-mono text-sm text-zinc-400">
      <a href="/" className="hover:text-zinc-200 transition-colors">
        Home
      </a>
      <span className="text-zinc-600">/</span>
      <a href="/selection" className="hover:text-zinc-200 transition-colors">
        Selection
      </a>
      <span className="text-zinc-600">/</span>
      <a href="/moon" className="text-zinc-200 font-bold border-b border-zinc-200 pb-0.5">
        Moon
      </a>
    </nav>
  );
}