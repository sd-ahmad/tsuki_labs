// src/pages/HomePage.jsx
import React from 'react';
import SpaceWallpaperInteractive from '../components/selection/SpaceWallpaperInteractive';
import { ArrowRight } from 'lucide-react';

export default function HomePage() {
  const handleExplore = () => {
    window.location.href = '/selection'; 
  };

  return (
    <div className="relative min-h-screen w-full text-zinc-100 flex flex-col justify-between overflow-hidden font-mono selection:bg-zinc-700 selection:text-white">
      
      {/* Live Interactive Space Wallpaper Background */}
      <SpaceWallpaperInteractive />
      <div className="absolute inset-0 bg-black/50 pointer-events-none z-0"></div>

      {/* Header & Navigation Bar */}
      <header className="relative z-10 w-full flex items-center justify-between px-8 py-7 bg-transparent">
        <span className="text-sm font-bold tracking-widest uppercase text-zinc-300">
          NASA SPACE APPS 2026 // PROJECT KAGAMI
        </span>
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <span className="text-zinc-200 font-bold underline underline-offset-4">Home</span>
          <span>/</span>
          <a href="/selection" className="hover:text-zinc-200 transition-colors">Selection</a>
        </div>
      </header>

      {/* Main Centralized Hero Content */}
      <main className="relative z-10 max-w-4xl mx-auto w-full flex flex-col items-center text-center justify-center my-auto px-6 gap-5 pt-2 pb-12">
        
        {/* Title */}
        <h1 className="text-7xl sm:text-9xl font-serif font-extrabold tracking-tight text-white drop-shadow-2xl">
          Project かがみ
        </h1>

        {/* Slogan & Team Name moved into the middle space between title and card */}
        <div className="flex flex-col items-center gap-1 my-1">
          <p className="text-xl sm:text-2xl tracking-[0.25em] uppercase text-zinc-200 font-semibold italic">
            "Mirroring Environments"
          </p>
          <p className="text-base sm:text-lg text-white font-bold tracking-widest uppercase">
            By: Tsuki Labs
          </p>
        </div>

        {/* Objective & Summary Card */}
        <div className="w-full max-w-3xl bg-[#121317]/90 border border-zinc-700/80 rounded-2xl p-8 backdrop-blur-md shadow-2xl flex flex-col gap-4 text-center mt-2">
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-wide">
            Identify Earth Locations That Analog Permanent Moon Base Locations and Mars
          </h2>
          <p className="text-sm sm:text-base text-zinc-300/90 leading-relaxed font-light">
            Selecting future landing sites depends on topography, geology, and environment. Using open Earth, Moon, and Mars data from NASA and other agencies, we identify and characterize new terrestrial analogs—from deserts and volcanic terrains to caves—sharing conditions with the lunar and Martian surface.
          </p>
        </div>

        {/* Interactive, Non-Vibrant Start Button */}
        <div className="mt-2">
          <button 
            onClick={handleExplore}
            className="group relative inline-flex items-center gap-3 px-9 py-4 rounded-xl bg-[#171c26] border border-zinc-700 text-zinc-200 hover:text-white hover:bg-[#202838] hover:border-zinc-500 transition-all duration-300 cursor-pointer text-base shadow-xl font-bold overflow-hidden"
          >
            <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></span>
            <span className="relative z-10">Start</span>
            <ArrowRight className="w-5 h-5 relative z-10 transition-transform duration-300 group-hover:translate-x-1.5" />
          </button>
        </div>

      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full py-4 text-center text-xs text-zinc-600">
        {/* Blank spacer */}
      </footer>
    </div>
  );
}