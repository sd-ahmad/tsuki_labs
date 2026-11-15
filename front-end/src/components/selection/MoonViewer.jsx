import React, { useEffect, useRef } from 'react';
import { createRotatingPlanet } from './createRotatingPlanet';

export default function MoonViewer({ modelUrl = '/models/moon_small.glb', onClick }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const planetInstance = createRotatingPlanet(container, modelUrl, {
      speed: 0.003,
      tilt: 0.2,
      onClick: onClick, // Passes the click handler down
    });

    return () => {
      planetInstance.dispose();
    };
  }, [modelUrl, onClick]);

  return (
    <div 
      ref={containerRef} 
      className="w-full h-full min-h-[400px] flex items-center justify-center cursor-pointer"
    />
  );
}