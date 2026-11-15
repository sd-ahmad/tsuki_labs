import React from 'react';
import { ArrowRight } from 'lucide-react';

export default function StartButton({ text = 'Start Mission', onClick }) {
  return (
    <button
      onClick={onClick}
      className="group flex items-center gap-3 px-8 py-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 active:scale-95 text-slate-950 font-bold text-lg shadow-lg shadow-cyan-500/25 transition-all duration-200 cursor-pointer"
    >
      <span>{text}</span>
      <ArrowRight className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-1" />
    </button>
  );
}