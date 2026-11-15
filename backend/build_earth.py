"""
build_earth.py  --  builds output/earth_025deg_lookup.json

A 0.25-degree Earth lookup (720 x 1440 cells) in the same schema as
mars_1deg_lookup.json / moon_1deg_lookup.json, so one matcher can compare them.
Only "barren-like" land cells are kept (deserts, polar, alpine, ice, Antarctica),
so the matcher never proposes rainforest or farmland.

Inputs (all inside raw_data/earth/):
  ETOPO_2022_v1_60s_N90W180_surface.tif     elevation (1 arc-minute)
  worldclim_bio/wc2.1_5m_bio_{1,2,5,6,10,12}.tif   climate (5 arc-minute)
  glim/glim_wgs84_0point5deg.txt.asc + glim/Classnames.txt   lithology (0.5 deg)
  OPTIONAL: EarthEnv consensus land cover class_10 / class_11 / class_12 .tif
            (snow/ice, barren, open water). If absent, a climate rule is used.

Key format: "{lat_q}_{lon_q}" where lat_q = floor(lat_center*4) and
lon_q = floor(lon_center*4)  (quarter-degree indices; south-west corner = q/4).
Example: the cell centred at 89.875N, -179.875E has key "359_-720".

Notes / caveats (also worth putting in the app):
  * WorldClim temperatures are AIR temperatures from monthly averages, not
    extreme surface temperatures like the Mars/Moon fields.
  * WorldClim does not cover Antarctica, so Antarctic cells have terrain and
    lithology but null climate fields.
  * Slope is computed from the 1.85 km ETOPO grid. Compare it with Mars/Moon
    slopes computed at a similar pixel size.
  * GLiM is 0.5 deg, so each GLiM value is copied into 4 cells of 0.25 deg.

Run from the back-end folder:   python build_earth.py
"""
from __future__ import annotations

import json
import math
import re
import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from rasterio.windows import Window

# ----------------------------------------------------------------------------
# Settings you can tweak
# ----------------------------------------------------------------------------
RAW = Path("raw_data/earth")
OUT = Path("output")
OUT.mkdir(exist_ok=True)

CELL = 0.25                                   # degrees
N_ROWS, N_COLS = int(180 / CELL), int(360 / CELL)   # 720 x 1440
R_EARTH = 6_371_008.8                         # metres (NOT the Mars radius)
BAND_CELL_ROWS = 60                           # cell rows processed at a time (memory)

# "Barren-like" rule used when EarthEnv land cover is NOT available:
ARID_PRECIP_MM = 250.0        # annual precipitation below this = arid
POLAR_WARMEST_QTR_C = 10.0    # warmest-quarter mean temp below this = polar / alpine

# Rule used when EarthEnv land cover IS available:
LC_BARREN_PLUS_ICE_MIN_PCT = 50.0
LC_WATER_MAX_PCT = 25.0


# ----------------------------------------------------------------------------
# Small helpers (same behaviour as in your Mars/Moon script)
# ----------------------------------------------------------------------------
def r_round(val, n: int = 2):
    """Round floats and turn NaN/Inf/None into None (valid JSON null)."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, n)


def find_one(patterns: list[str]) -> Path | None:
    """First file under RAW matching any of the glob patterns."""
    for pat in patterns:
        hits = sorted(RAW.rglob(pat))
        if hits:
            return hits[0]
    return None


# ----------------------------------------------------------------------------
# Terrain from ETOPO (chunked, so it fits in normal laptop memory)
# ----------------------------------------------------------------------------
def terrain_stats(path: Path) -> dict[str, np.ndarray]:
    """Elevation and slope statistics per 0.25-degree cell, from a global DEM."""
    names = ["mean", "min", "max", "std", "slope_mean", "slope_p95"]
    out = {k: np.full((N_ROWS, N_COLS), np.nan, dtype=np.float32) for k in names}

    with rasterio.open(path) as src:
        height, width = src.height, src.width
        ppd_y, ppd_x = height / 180.0, width / 360.0
        ky, kx = int(round(ppd_y * CELL)), int(round(ppd_x * CELL))   # pixels per cell
        if ky * N_ROWS != height or kx * N_COLS != width:
            raise SystemExit(
                f"[X] DEM shape {height}x{width} does not divide into {CELL} deg cells "
                f"({ky}x{kx} px per cell)."
            )
        dy = R_EARTH * math.pi / 180.0 / ppd_y            # metres per pixel, north-south
        dx0 = R_EARTH * math.pi / 180.0 / ppd_x           # metres per pixel at the equator

        for cr0 in range(0, N_ROWS, BAND_CELL_ROWS):
            cr1 = min(cr0 + BAND_CELL_ROWS, N_ROWS)
            r0, r1 = cr0 * ky, cr1 * ky
            a, b = max(r0 - 1, 0), min(r1 + 1, height)    # 1-pixel halo for the gradient

            arr = src.read(1, window=Window(0, a, width, b - a)).astype(np.float32)
            if src.nodata is not None:
                arr[arr == src.nodata] = np.nan

            lat = 90.0 - (np.arange(a, b) + 0.5) / ppd_y   # true latitude of every pixel row
            cos_lat = np.clip(np.cos(np.radians(lat)), 0.01, 1.0)[:, None]
            dx = dx0 * cos_lat

            dz_dy, dz_dx = np.gradient(arr)
            slope = np.degrees(np.arctan(np.hypot(dz_dx / dx, dz_dy / dy)))

            inner = slice(r0 - a, r0 - a + (r1 - r0))
            nr = cr1 - cr0
            def blocks(x):
                return (
                    x[inner]
                    .reshape(nr, ky, N_COLS, kx)
                    .transpose(0, 2, 1, 3)
                    .reshape(nr, N_COLS, ky * kx)
                )
            eb, sb = blocks(arr), blocks(slope)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out["mean"][cr0:cr1] = np.nanmean(eb, axis=2)
                out["min"][cr0:cr1] = np.nanmin(eb, axis=2)
                out["max"][cr0:cr1] = np.nanmax(eb, axis=2)
                out["std"][cr0:cr1] = np.nanstd(eb, axis=2)
                out["slope_mean"][cr0:cr1] = np.nanmean(sb, axis=2)
                out["slope_p95"][cr0:cr1] = np.nanpercentile(sb, 95, axis=2)
            print(f"    terrain: cell rows {cr0}-{cr1} of {N_ROWS}")
    return out


# ----------------------------------------------------------------------------
# Any global lat/lon raster -> 0.25-degree grid by averaging valid pixels
# ----------------------------------------------------------------------------
def average_to_grid(path: Path) -> np.ndarray:
    dst = np.full((N_ROWS, N_COLS), np.nan, dtype=np.float32)
    with rasterio.open(path) as src:
        if src.crs is not None:
            source, extra = rasterio.band(src, 1), {}
        else:  # no CRS in the file: assume plain lat/lon
            source = src.read(1)
            extra = {"src_transform": src.transform, "src_crs": "EPSG:4326"}
        if src.nodata is not None:
            extra["src_nodata"] = src.nodata
        reproject(
            source=source,
            destination=dst,
            dst_transform=from_origin(-180.0, 90.0, CELL, CELL),
            dst_crs="EPSG:4326",
            dst_nodata=np.nan,
            init_dest_nodata=True,
            resampling=Resampling.average,
            **extra,
        )
    dst[~np.isfinite(dst)] = np.nan
    return dst


# ----------------------------------------------------------------------------
# GLiM lithology
# ----------------------------------------------------------------------------
def coarse_lith(name: str | None) -> str | None:
    """Map a GLiM class name to a coarse category that Mars/Moon units can also be mapped to."""
    if not name:
        return None
    n = name.lower()
    if "no data" in n or "nodata" in n:
        return None
    if "ice" in n or "glacier" in n:
        return "ice"
    if "water" in n:
        return "water"
    if "pyroclast" in n:
        return "pyroclastic"
    if "volcan" in n:
        return "volcanic_basic" if "basic" in n else "volcanic_other"
    if "evaporite" in n:
        return "evaporite"
    if "plutonic" in n:
        return "plutonic"
    if "metamorph" in n:
        return "metamorphic"
    if "unconsolidated" in n:
        return "unconsolidated_sediment"
    if "sediment" in n or "carbonate" in n or "siliciclastic" in n:
        return "sedimentary"
    return "other"


def load_glim_classes(path: Path) -> dict[int, tuple[str | None, str, str | None]]:
    """Parse Classnames.txt -> {code: (short_code, name, coarse_class)}. Tolerant of formats."""
    classes: dict[int, tuple[str | None, str, str | None]] = {}
    for line in path.read_text(errors="ignore").splitlines():
        tokens = [t for t in re.split(r"[\s,;=:|\t]+", line.strip()) if t]
        ints = [i for i, t in enumerate(tokens) if re.fullmatch(r"\d+", t)]
        if not ints:
            continue
        i = ints[0]
        code = int(tokens[i])
        rest = [t for j, t in enumerate(tokens) if j != i]
        short = rest[0] if rest and re.fullmatch(r"[a-z]{2}", rest[0]) else None
        name_tokens = rest[1:] if short else rest
        name = " ".join(name_tokens) if name_tokens else (short or str(code))
        classes[code] = (short, name, coarse_lith(name))
    if not classes:
        print(f"  [!] Could not parse {path.name}. Its contents:\n{path.read_text(errors='ignore')}")
    else:
        print("  GLiM classes found:")
        for code, (short, name, coarse) in sorted(classes.items()):
            print(f"    {code:>3}  {short or '--':<3} {name}  ->  {coarse}")
    return classes


def read_glim_grid(path: Path) -> np.ndarray:
    """Read the ESRI ASCII grid into a (720, 1440) float array of class codes (NaN = none)."""
    header: dict[str, float] = {}
    rows = []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            key = parts[0].lower()
            if key in ("ncols", "nrows", "xllcorner", "yllcorner", "xllcenter",
                       "yllcenter", "cellsize", "nodata_value"):
                header[key] = float(parts[1])
            else:
                rows.append(np.array(parts, dtype=np.float64))
    arr = np.vstack(rows)
    if arr.shape != (360, 720):
        raise SystemExit(f"[X] Expected a 360x720 GLiM grid, got {arr.shape}.")
    nod = header.get("nodata_value")
    if nod is not None:
        arr[arr == nod] = np.nan
    x0 = header.get("xllcorner", header.get("xllcenter"))
    if x0 is not None and x0 > -90.0:          # grid runs 0..360 instead of -180..180
        arr = np.roll(arr, arr.shape[1] // 2, axis=1)
    return np.repeat(np.repeat(arr, 2, axis=0), 2, axis=1)    # 0.5 deg -> 0.25 deg


# ----------------------------------------------------------------------------
# Main build
# ----------------------------------------------------------------------------
def build_earth():
    print("\n=== Building Earth 0.25 deg lookup ===")

    etopo = find_one(["ETOPO_2022*surface*.tif", "ETOPO*.tif"])
    if etopo is None:
        raise SystemExit("[X] ETOPO DEM not found under raw_data/earth/")
    print(f"  [+] DEM: {etopo.name}")

    bio = {}
    for n in (1, 2, 5, 6, 10, 12):
        p = find_one([f"wc2.1_*_bio_{n}.tif"])
        if p is None:
            raise SystemExit(f"[X] WorldClim bio_{n} not found under raw_data/earth/")
        bio[n] = p
    print(f"  [+] WorldClim bio layers: {bio[1].name} ...")

    glim_asc = find_one(["glim*.asc"])
    glim_names = find_one(["Classnames.txt", "classnames.txt"])
    if glim_asc is None or glim_names is None:
        raise SystemExit("[X] GLiM .asc / Classnames.txt not found under raw_data/earth/")
    print(f"  [+] GLiM: {glim_asc.name}")

    lc_paths = {}
    for cls in (10, 11, 12):
        p = find_one([f"*class_{cls}.tif"])
        if p is not None:
            lc_paths[cls] = p
    use_landcover = len(lc_paths) == 3
    print("  [+] EarthEnv land cover found: using barren/ice/water rule" if use_landcover
          else "  [i] No EarthEnv land cover: using climate rule (arid OR polar/alpine)")

    # --- rasters on the 0.25 deg grid ---------------------------------------
    print("  Terrain (slow part, about 1-3 minutes)...")
    terr = terrain_stats(etopo)

    print("  Climate...")
    b1, b2, b5, b6, b10, b12 = (average_to_grid(bio[n]) for n in (1, 2, 5, 6, 10, 12))
    if np.nanmax(b1) > 100:        # old WorldClim style: degrees C x 10
        print("  [i] Temperatures look like degC x 10; dividing by 10.")
        b1, b2, b5, b6, b10 = (x / 10.0 for x in (b1, b2, b5, b6, b10))

    print("  Lithology...")
    glim_codes = read_glim_grid(glim_asc)
    classes = load_glim_classes(glim_names)

    def class_mask(label: str) -> np.ndarray:
        codes = [c for c, (_, _, coarse) in classes.items() if coarse == label]
        return np.isin(glim_codes, codes) if codes else np.zeros(glim_codes.shape, bool)

    glim_ice, glim_water = class_mask("ice"), class_mask("water")

    barren_pct = snow_pct = water_pct = None
    if use_landcover:
        print("  Land cover...")
        barren_pct = average_to_grid(lc_paths[11])
        snow_pct = average_to_grid(lc_paths[10])
        water_pct = average_to_grid(lc_paths[12])

    # --- which cells to keep -------------------------------------------------
    rows = np.arange(N_ROWS)[:, None]
    lat_c = 90.0 - (rows + 0.5) * CELL                      # (720, 1)
    lat_c_full = np.repeat(lat_c, N_COLS, axis=1)

    with np.errstate(all="ignore"):
        has_clim = np.isfinite(b1)
        has_terrain = np.isfinite(terr["mean"])
        if use_landcover:
            barren_like = (np.nan_to_num(barren_pct) + np.nan_to_num(snow_pct)
                           >= LC_BARREN_PLUS_ICE_MIN_PCT) & (np.nan_to_num(water_pct) < LC_WATER_MAX_PCT)
        else:
            barren_like = (b12 < ARID_PRECIP_MM) | (b10 < POLAR_WARMEST_QTR_C)
        antarctic = (lat_c_full < -60.0) & ~has_clim & (terr["mean"] > 0)   # WorldClim has no Antarctica

        keep = has_terrain & ~glim_water & (
            (has_clim & (barren_like | glim_ice)) | antarctic
        )
    print(f"  Cells kept: {int(keep.sum()):,} of {N_ROWS * N_COLS:,} "
          f"(Antarctic cells with no climate data: {int((keep & antarctic).sum()):,})")

    # --- assemble JSON -------------------------------------------------------
    def k(arr, r, c):          # Celsius -> Kelvin, keeping NaN
        v = arr[r, c]
        return None if not np.isfinite(v) else float(v) + 273.15

    lookup: dict[str, dict] = {}
    for r, c in np.argwhere(keep):
        lat_center = float(lat_c[r, 0])
        lon_center = -180.0 + (c + 0.5) * CELL

        code = glim_codes[r, c]
        short = name = coarse = None
        if np.isfinite(code) and int(code) in classes:
            short, name, coarse = classes[int(code)]

        lookup[f"{359 - r}_{c - 720}"] = {
            "lat_center": lat_center,
            "lon_center": lon_center,
            "geology": {
                "unit_code": short or (None if not np.isfinite(code) else str(int(code))),
                "unit_desc": name,
                "lith_class": coarse,
            },
            "terrain": {
                "elev_mean_m": r_round(terr["mean"][r, c], 1),
                "elev_min_m": r_round(terr["min"][r, c], 1),
                "elev_max_m": r_round(terr["max"][r, c], 1),
                "relief_m": r_round(terr["max"][r, c] - terr["min"][r, c], 1),
                "slope_mean_deg": r_round(terr["slope_mean"][r, c]),
                "slope_p95_deg": r_round(terr["slope_p95"][r, c]),
                "roughness_std_m": r_round(terr["std"][r, c], 1),
            },
            "thermal": {
                "temp_day_max_k": r_round(k(b5, r, c), 1),       # warmest-month mean daily max (air)
                "temp_night_min_k": r_round(k(b6, r, c), 1),     # coldest-month mean daily min (air)
                "diurnal_swing_k": r_round(b2[r, c], 1),         # mean diurnal range
                "mean_annual_temp_k": r_round(k(b1, r, c), 1),
                "warmest_quarter_temp_k": r_round(k(b10, r, c), 1),
            },
            "water_ice": {
                "annual_precip_mm": r_round(b12[r, c], 0),
                "glim_ice_class": bool(glim_ice[r, c]),
                "polar_ice_flag": abs(lat_center) >= 75.0,
                "barren_pct": r_round(barren_pct[r, c], 0) if use_landcover else None,
                "snow_ice_pct": r_round(snow_pct[r, c], 0) if use_landcover else None,
            },
            "atmosphere_dust": None,
            "subsurface_caves": None,
            "landing_mobility": None,
        }

    out_path = OUT / "earth_025deg_lookup.json"
    with open(out_path, "w") as f:
        json.dump(lookup, f, separators=(",", ":"), allow_nan=False)
    size_mb = out_path.stat().st_size / 1e6
    print(f"Saved {out_path} ({len(lookup):,} cells, {size_mb:.1f} MB)")

    sanity_report(lookup)


def sanity_report(lookup: dict) -> None:
    """Prints a few known places so you can eyeball whether the grid is sensible."""
    print("\n--- Sanity checks ---")
    places = {
        "Atacama (-24.5, -69.5)": (-24.5, -69.5),
        "McMurdo Dry Valleys (-77.5, 162.5)": (-77.5, 162.5),
        "Iceland highlands (64.8, -18.5)": (64.8, -18.5),
        "Devon Island / Haughton (75.4, -89.5)": (75.4, -89.5),
        "Amazon (-3.0, -60.0) should be absent": (-3.0, -60.0),
    }
    for label, (lat, lon) in places.items():
        key = f"{math.floor(lat * 4)}_{math.floor(lon * 4)}"
        cell = lookup.get(key)
        if cell is None:
            print(f"  {label}: not in file")
            continue
        t, th = cell["terrain"], cell["thermal"]
        print(f"  {label}: key {key}, elev {t['elev_mean_m']} m, slope p95 {t['slope_p95_deg']} deg, "
              f"Tmax {th['temp_day_max_k']} K, Tmin {th['temp_night_min_k']} K, "
              f"precip {cell['water_ice']['annual_precip_mm']} mm, lith {cell['geology']['lith_class']}")

    print("\n  Non-null counts per field:")
    total = len(lookup)
    for group in ("geology", "terrain", "thermal", "water_ice"):
        for field in next(iter(lookup.values()))[group]:
            n = sum(1 for v in lookup.values() if v[group].get(field) is not None)
            print(f"    {group}.{field}: {n:,} / {total:,}")


if __name__ == "__main__":
    build_earth()