// src/components/mars/MarsMap.jsx

import { useRef, useState, useEffect } from "react";
import marsMapImage from "../../assets/marsmap.jpg";

export default function MarsMap({ onSelectCoords = () => {} }) {
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [cursorCoords, setCursorCoords] = useState(null);
  const [isHovered, setIsHovered] = useState(false);

  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const dragging = useRef(false);
  const hasDragged = useRef(false);
  const lastPosition = useRef({ x: 0, y: 0 });

  const MIN_ZOOM = 1;
  const MAX_ZOOM = 8;
  const VIEWBOX_WIDTH = 8192;
  const VIEWBOX_HEIGHT = 4096;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheelGlobal = (e) => {
      if (isHovered) {
        e.preventDefault();
      }
    };

    container.addEventListener("wheel", handleWheelGlobal, { passive: false });
    return () => {
      container.removeEventListener("wheel", handleWheelGlobal);
    };
  }, [isHovered]);

  const clampOffset = (x, y, currentZoom) => {
    const maxPanX = 0;
    const minPanX = VIEWBOX_WIDTH - VIEWBOX_WIDTH * currentZoom;
    const maxPanY = 0;
    const minPanY = VIEWBOX_HEIGHT - VIEWBOX_HEIGHT * currentZoom;

    return {
      x: Math.min(maxPanX, Math.max(minPanX, x)),
      y: Math.min(maxPanY, Math.max(minPanY, y)),
    };
  };

  const calculateCoords = (e) => {
    if (!svgRef.current) return null;
    const rect = svgRef.current.getBoundingClientRect();

    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;

    const svgX = (clientX / rect.width) * VIEWBOX_WIDTH;
    const svgY = (clientY / rect.height) * VIEWBOX_HEIGHT;

    const mapX = (svgX - offset.x) / zoom;
    const mapY = (svgY - offset.y) / zoom;

    if (mapX >= 0 && mapX <= VIEWBOX_WIDTH && mapY >= 0 && mapY <= VIEWBOX_HEIGHT) {
      let rawLon = (mapX / VIEWBOX_WIDTH) * 360 - 180;
      let rawLat = 90 - (mapY / VIEWBOX_HEIGHT) * 180;

      rawLat = Math.max(-90, Math.min(90, rawLat));
      rawLon = Math.max(-180, Math.min(180, rawLon));

      const formattedLat = `${rawLat >= 0 ? `+${rawLat.toFixed(2)}` : rawLat.toFixed(2)}°`;
      const formattedLon = `${rawLon >= 0 ? `+${rawLon.toFixed(2)}` : rawLon.toFixed(2)}°`;

      return { lat: formattedLat, lon: formattedLon };
    }
    return null;
  };

  const handleWheel = (e) => {
    e.preventDefault();
    if (!svgRef.current) return;

    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * VIEWBOX_WIDTH;
    const mouseY = ((e.clientY - rect.top) / rect.height) * VIEWBOX_HEIGHT;

    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const nextZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom * zoomFactor));

    if (nextZoom === zoom) return;

    const scaleRatio = nextZoom / zoom;
    const nextX = mouseX - (mouseX - offset.x) * scaleRatio;
    const nextY = mouseY - (mouseY - offset.y) * scaleRatio;

    setZoom(nextZoom);
    setOffset(clampOffset(nextX, nextY, nextZoom));
  };

  const handlePointerDown = (e) => {
    dragging.current = true;
    hasDragged.current = false;
    lastPosition.current = { x: e.clientX, y: e.clientY };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e) => {
    const coords = calculateCoords(e);
    setCursorCoords(coords);

    if (!dragging.current || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();

    const dxScreen = e.clientX - lastPosition.current.x;
    const dyScreen = e.clientY - lastPosition.current.y;

    if (Math.abs(dxScreen) > 3 || Math.abs(dyScreen) > 3) {
      hasDragged.current = true;
    }

    const dxSvg = (dxScreen / rect.width) * VIEWBOX_WIDTH;
    const dySvg = (dyScreen / rect.height) * VIEWBOX_HEIGHT;

    setOffset((prev) => clampOffset(prev.x + dxSvg, prev.y + dySvg, zoom));
    lastPosition.current = { x: e.clientX, y: e.clientY };
  };

  const handlePointerUp = (e) => {
    if (!hasDragged.current) {
      const clickedCoords = calculateCoords(e);
      if (clickedCoords) {
        onSelectCoords(clickedCoords);
      }
    }
    dragging.current = false;
  };

  const handlePointerLeave = () => {
    dragging.current = false;
    setCursorCoords(null);
    setIsHovered(false);
  };

  return (
    <div 
      ref={containerRef} 
      className="flex flex-col gap-4 w-full"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div 
        className={`w-full aspect-[2/1] rounded-2xl overflow-hidden border-2 border-amber-900/40 shadow-2xl bg-black relative select-none transition-transform duration-500 ease-out ${
          isHovered ? "scale-[1.015] shadow-orange-600/20 border-orange-500" : "scale-100"
        }`}
      >
        <svg
          ref={svgRef}
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
          className="w-full h-full block cursor-crosshair touch-none active:cursor-grabbing object-cover"
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerLeave}
          onPointerCancel={handlePointerUp}
        >
          <g transform={`translate(${offset.x} ${offset.y}) scale(${zoom})`}>
            <image
              href={marsMapImage}
              x="0"
              y="0"
              width={VIEWBOX_WIDTH}
              height={VIEWBOX_HEIGHT}
              preserveAspectRatio="none"
            />
          </g>
        </svg>
      </div>

      <div className="w-full flex justify-center">
        <div className="flex items-center gap-5 rounded-2xl bg-[#161210] border border-amber-900/40 px-8 py-3.5 font-mono text-base text-amber-100 shadow-xl whitespace-nowrap">
          <span className="text-amber-200 font-semibold">
            Latitude: {cursorCoords ? cursorCoords.lat : "---"}
          </span>
          <span className="text-amber-900 text-lg">|</span>
          <span className="text-orange-200 font-semibold">
            Longitude: {cursorCoords ? cursorCoords.lon : "---"}
          </span>
        </div>
      </div>
    </div>
  );
}