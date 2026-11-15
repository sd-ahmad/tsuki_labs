// src/api/analogApi.js

const API_BASE = "https://tsuki-labs.onrender.com";

const PRIORITY_MAP = {
  all: null,
  none: null,
  no_category: null,
  all_conditions: null,
  "all conditions": null,
  "no category": null,
  best_overall: null,
  "best overall": null,
  overall: null,

  geology: "Geology & Mineralogy",
  geology_mineralogy: "Geology & Mineralogy",
  "geology & mineralogy": "Geology & Mineralogy",

  terrain: "Terrain & Topography",
  terrain_topography: "Terrain & Topography",
  "terrain & topography": "Terrain & Topography",

  thermal: "Thermal & Extremes",
  thermal_extremes: "Thermal & Extremes",
  "thermal & extremes": "Thermal & Extremes",

  // Closest thermal/solar insolation proxy available on both Mars & Moon
  radiation: "Thermal & Extremes",
  radiation_solar_flux: "Thermal & Extremes",
  "radiation & solar flux": "Thermal & Extremes",
  solar: "Thermal & Extremes",

  water: "Water & Ice",
  water_ice: "Water & Ice",
  "water & ice": "Water & Ice",
  water_ice_volatiles: "Water & Ice",
  "water ice & volatiles": "Water & Ice",
  volatiles: "Water & Ice",

  atmosphere: "Atmospheric/Dust (MARS)",
  atmospheric_dust: "Atmospheric/Dust (MARS)",
  atmospheric_pressure_winds: "Atmospheric/Dust (MARS)",
  "atmospheric pressure & winds": "Atmospheric/Dust (MARS)",
  pressure: "Atmospheric/Dust (MARS)",
  dust: "Atmospheric/Dust (MARS)",

  caves: "Subsurface/Caves (MARS)",
  subsurface_caves: "Subsurface/Caves (MARS)",

  landing: "Landing/Mobility",
  mobility: "Landing/Mobility",
  landing_mobility: "Landing/Mobility",
  landing_rover_mobility: "Landing/Mobility",
  "landing & rover mobility": "Landing/Mobility",
  rover: "Landing/Mobility",
};

function parseCoordNum(val) {
  if (typeof val === "number") return val;
  if (typeof val === "string") return Number(val.replace(/[°\s]/g, ""));
  return NaN;
}

function normalizeCoords(coords) {
  console.log("Selected coords from map:", coords);
  if (!coords) throw new Error("No coordinates selected.");

  if (Array.isArray(coords)) {
    const latitude = parseCoordNum(coords[0]);
    const longitude = parseCoordNum(coords[1]);
    if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
      return { longitude, latitude };
    }
  }

  const rawLon = coords.longitude ?? coords.lon ?? coords.lng ?? coords.long ?? coords.x;
  const rawLat = coords.latitude ?? coords.lat ?? coords.y;

  const longitude = parseCoordNum(rawLon);
  const latitude = parseCoordNum(rawLat);

  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) {
    throw new Error(`Invalid coordinate object from map: ${JSON.stringify(coords)}`);
  }
  return { longitude, latitude };
}

function normalizePriority(priority) {
  if (!priority) return null;
  const raw =
    typeof priority === "object"
      ? priority.id ?? priority.value ?? priority.name ?? priority.label
      : priority;
  if (!raw) return null;
  const key = String(raw).trim().toLowerCase().replace(/-/g, "_");
  if (key in PRIORITY_MAP) return PRIORITY_MAP[key];
  return String(raw).trim();
}

export async function runAnalogAnalysis({ body, coords, priority, topK = 3 }) {
  const { longitude, latitude } = normalizeCoords(coords);
  const priority_category = normalizePriority(priority);

  const res = await fetch(`${API_BASE}/api/find-analogs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      longitude,
      latitude,
      astronomical_body: body,
      priority_category,
      top_k: topK,
    }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Backend error (${res.status})`);
  }

  sessionStorage.setItem("analogResult", JSON.stringify(data));
  sessionStorage.setItem("lastBody", body);
  return data;
}