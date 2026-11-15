// src/pages/SelectionPage.jsx

import React from 'react';
import SpaceWallpaperInteractive from '../components/selection/SpaceWallpaperInteractive';
import MoonViewer from '../components/selection/MoonViewer';
import SelectionHeader from '../components/selection/selectionheader';

export default function SelectionPage() {
  const handleMoonClick = () => {
    window.location.href = '/moon'; 
  };

  const handleMarsClick = () => {
    window.location.href = '/mars'; 
  };

  return (
    <div className="relative min-h-screen w-full text-white flex flex-col justify-between overflow-hidden">
      
      {/* Background & Tint */}
      <SpaceWallpaperInteractive />
      <div className="absolute inset-0 bg-slate-950/40 pointer-events-none z-0"></div>

      {/* Selection Header */}
      <div className="relative z-10">
        <SelectionHeader />
      </div>

      {/* Unified Centered Content Wrapper */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-start pt-6 pb-12 px-6 gap-10 max-w-7xl mx-auto w-full">
        
        {/* Central Title Header (Pushed slightly lower) */}
        <div className="text-center pt-6">
          <h1 className="text-3xl md:text-4xl lg:text-5xl font-extrabold tracking-[0.15em] md:tracking-[0.25em] text-gray-100 font-mono drop-shadow-md">
            SELECT DESTINATION
          </h1>
          <p className="mt-3 text-sm md:text-base text-gray-400 tracking-[0.15em] md:tracking-[0.2em] uppercase font-mono">
            Choose your planetary path
          </p>
        </div>

        {/* Planets Side-by-Side Container */}
        <div className="flex flex-col md:flex-row items-center justify-center gap-16 w-full">
          
          {/* Left Side: Moon */}
          <div 
            onClick={handleMoonClick}
            className="group flex flex-col items-center cursor-pointer"
          >
            <div className="w-[520px] h-[520px] flex items-center justify-center relative">
              <div className="absolute inset-0 bg-blue-500/5 rounded-full blur-3xl pointer-events-none"></div>
              <div className="w-full h-full transition-transform duration-500 ease-out group-hover:scale-110 drop-shadow-[0_20px_30px_rgba(0,0,0,0.9)]">
                <MoonViewer modelUrl="/models/moon_small.glb" />
              </div>
            </div>
            
            <h2 className="mt-4 text-2xl font-bold tracking-[0.35em] text-gray-300 font-mono transition-all duration-300 group-hover:text-white group-hover:tracking-[0.45em]">
              MOON
            </h2>
            <p className="mt-1 text-xs uppercase tracking-widest text-gray-500 font-mono opacity-0 transition-opacity duration-300 group-hover:opacity-100">
              Launch Mission →
            </p>
          </div>

          {/* Right Side: Mars */}
          <div 
            onClick={handleMarsClick}
            className="group flex flex-col items-center cursor-pointer"
          >
            <div className="w-[520px] h-[520px] flex items-center justify-center relative">
              <div className="absolute inset-0 bg-red-500/5 rounded-full blur-3xl pointer-events-none"></div>
              <div className="w-full h-full transition-transform duration-500 ease-out group-hover:scale-110 drop-shadow-[0_20px_30px_rgba(0,0,0,0.9)]">
                <MoonViewer modelUrl="/models/mars.glb" />
              </div>
            </div>
            
            <h2 className="mt-4 text-2xl font-bold tracking-[0.35em] text-gray-300 font-mono transition-all duration-300 group-hover:text-amber-400 group-hover:tracking-[0.45em]">
              MARS
            </h2>
            <p className="mt-1 text-xs uppercase tracking-widest text-gray-500 font-mono opacity-0 transition-opacity duration-300 group-hover:opacity-100">
              Launch Mission →
            </p>
          </div>

        </div>

      </div>

    </div>
  );
}