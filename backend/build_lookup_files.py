from __future__ import annotations
from rasterio.windows import Window

import json
import math
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from scipy.spatial import cKDTree

RAW = Path("raw_data")
OUT = Path("output")
OUT.mkdir(exist_ok=True)


def r_round(val, n: int = 2):
    """Safely rounds floats and converts NaN/Inf to None (valid JSON null)."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, n)


def clean_str(val):
    """Converts NaN/missing text fields to None (valid JSON null)."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def find_first_existing(base_dir: Path, candidates: list[str]) -> Path | None:
    """Returns the first file path from candidates that exists inside base_dir."""
    for rel in candidates:
        p = base_dir / rel
        if p.exists():
            return p
    return None


def read_global_raster(path: Path) -> np.ndarray:
    """Reads .lbl/.img, .xml/.img, .tif, or .vicar into North->South, -180..+180 float64 array."""
    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float64)
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
        scale = src.scales[0] if src.scales else 1.0
        offset = src.offsets[0] if src.offsets else 0.0
        arr = arr * scale + offset
        if not src.transform.is_identity and src.transform.e > 0:
            arr = np.flipud(arr)
        lon_0 = src.crs.to_dict().get("lon_0", 0.0) if src.crs else 0.0
        if abs(lon_0 - 180.0) < 1.0 or (src.crs and not src.crs.is_projected and src.bounds.left >= -1.0):
            arr = np.roll(arr, arr.shape[1] // 2, axis=1)
    return arr


def bin_to_1deg(arr: np.ndarray, stat: str = "mean") -> np.ndarray:
    """Aggregates a global cylindrical array into a (180, 360) 1-degree grid."""
    if arr is None:
        return np.full((180, 360), np.nan)
    rows, cols = arr.shape
    ky, kx = max(1, rows // 180), max(1, cols // 360)
    blocks = (
        arr[: 180 * ky, : 360 * kx]
        .reshape(180, ky, 360, kx)
        .transpose(0, 2, 1, 3)
        .reshape(180, 360, ky * kx)
    )
    with np.errstate(all="ignore"):
        if stat == "min":
            return np.nanmin(blocks, axis=2)
        if stat == "max":
            return np.nanmax(blocks, axis=2)
        if stat == "std":
            return np.nanstd(blocks, axis=2)
        if stat == "p95":
            return np.nanpercentile(blocks, 95, axis=2)
        return np.nanmean(blocks, axis=2)


def calc_spherical_slope(dem: np.ndarray, radius_m: float) -> np.ndarray:
    """Computes local slope (degrees) accounting for cos(lat) meridian convergence."""
    rows, cols = dem.shape
    dy = (math.pi * radius_m) / (180.0 * (rows / 180.0))
    cos_lat = np.clip(np.cos(np.radians(np.linspace(89.5, -89.5, rows))), 0.01, 1.0)[:, None]
    dx = ((math.pi * radius_m) / (180.0 * (cols / 360.0))) * cos_lat
    dz_dy, dz_dx = np.gradient(dem)
    return np.degrees(np.arctan(np.sqrt((dz_dx / dx) ** 2 + (dz_dy / dy) ** 2)))


def ingest_raster_1deg(path: Path, stat: str = "mean") -> np.ndarray:
    if not path.exists():
        print(f"  [!] Optional raster missing (filling null): {path.name}")
        return np.full((180, 360), np.nan)
    print(f"  [+] Loaded raster: {path.name}")
    return bin_to_1deg(read_global_raster(path), stat)


def ingest_swim_1deg(path: Path) -> np.ndarray:
    """Loads SWIM mid-latitude GeoTIFF (60°S-60°N) into a full (180, 360) 1-degree grid."""
    out = np.full((180, 360), np.nan)
    if not path.exists():
        print(f"  [!] Optional raster missing (filling null): {path.name}")
        return out

    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float64)
        if src.nodata is not None:
            arr[np.isclose(arr, src.nodata, atol=0.1)] = np.nan
        arr[arr < -2.0] = np.nan  # Valid SWIM Ci range is [-1.0, +1.0]

        m_per_deg = (math.pi * 3_396_190.0) / 180.0
        top_lat = round(src.bounds.top / m_per_deg)
        bot_lat = round(src.bounds.bottom / m_per_deg)
        n_lat = int(top_lat - bot_lat)

        rows, cols = arr.shape
        ky, kx = max(1, rows // n_lat), max(1, cols // 360)
        blocks = (
            arr[: n_lat * ky, : 360 * kx]
            .reshape(n_lat, ky, 360, kx)
            .transpose(0, 2, 1, 3)
            .reshape(n_lat, 360, ky * kx)
        )
        with np.errstate(all="ignore"):
            sub = np.nanmean(blocks, axis=2)

        r_start = 90 - int(top_lat)
        out[r_start : r_start + n_lat, :] = sub

    print(f"  [+] Loaded SWIM raster: {path.name} ({bot_lat}° to {top_lat}°)")
    return out


def ingest_diviner_xyz_1deg(path: Path, stat: str = "max") -> np.ndarray:
    """Aggregates 0.5° Diviner global .xyz (lon, lat, Tbol_K) onto a (180, 360) 1-degree grid."""
    out = np.full((180, 360), np.nan)
    if not path.exists():
        print(f"  [!] Optional Diviner XYZ missing (filling null): {path.name}")
        return out

    df = pd.read_csv(path, sep=r"\s+", header=None, names=["lon", "lat", "val"])
    lons = ((pd.to_numeric(df["lon"], errors="coerce").values + 180.0) % 360.0) - 180.0
    lats = pd.to_numeric(df["lat"], errors="coerce").values
    vals = pd.to_numeric(df["val"], errors="coerce").values

    valid = ~(np.isnan(lons) | np.isnan(lats) | np.isnan(vals)) & (vals > 0.0) & (vals < 1000.0)
    r_idx = np.clip(89 - np.floor(lats[valid]).astype(int), 0, 179)
    c_idx = np.clip(np.floor(lons[valid]).astype(int) + 180, 0, 359)

    agg = pd.DataFrame({"r": r_idx, "c": c_idx, "v": vals[valid]}).groupby(["r", "c"])["v"].agg(stat)
    out[agg.index.get_level_values(0), agg.index.get_level_values(1)] = agg.values

    print(f"  [+] Loaded Diviner XYZ: {path.name} ({int(np.sum(valid))} pts, stat={stat})")
    return out


def ingest_moon_rock_1deg(path: Path | None) -> np.ndarray:
    """Loads Diviner Rock Abundance GDR_L3 (-60° to +60°) into a full (180, 360) 1-degree grid."""
    out = np.full((180, 360), np.nan)
    if path is None or not path.exists():
        print("  [!] Optional Moon rock abundance missing (filling null).")
        return out

    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float64)
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
        scale = src.scales[0] if src.scales else 1.0
        offset = src.offsets[0] if src.offsets else 0.0
        arr = arr * scale + offset
        arr[arr < 0.0] = np.nan

        if not src.transform.is_identity and src.transform.e > 0:
            arr = np.flipud(arr)

        lon_0 = src.crs.to_dict().get("lon_0", 0.0) if src.crs else 0.0
        if abs(lon_0 - 180.0) < 1.0:
            arr = np.roll(arr, arr.shape[1] // 2, axis=1)

        m_per_deg = (math.pi * 1_737_400.0) / 180.0
        top_lat = round(src.bounds.top / m_per_deg)
        bot_lat = round(src.bounds.bottom / m_per_deg)
        n_lat = int(top_lat - bot_lat)

        rows, cols = arr.shape
        ky, kx = max(1, rows // n_lat), max(1, cols // 360)
        blocks = (
            arr[: n_lat * ky, : 360 * kx]
            .reshape(n_lat, ky, 360, kx)
            .transpose(0, 2, 1, 3)
            .reshape(n_lat, 360, ky * kx)
        )
        with np.errstate(all="ignore"):
            sub = np.nanmean(blocks, axis=2)

        r_start = 90 - int(top_lat)
        out[r_start : r_start + n_lat, :] = sub

    print(f"  [+] Loaded Moon rock abundance: {path.name} ({bot_lat}° to {top_lat}°)")
    return out


def ingest_table_1deg(
    path: Path,
    lat_col=0,
    lon_col=1,
    val_col=2,
    sep=r"\s+",
    has_header: bool = False,
    missing_val: float = 9999.999,
) -> np.ndarray:
    """Maps a GRS .tab/.csv point table onto a (180, 360) 1-degree grid, masking missing values."""
    if not path.exists():
        print(f"  [!] Optional table missing (filling null): {path.name}")
        return np.full((180, 360), np.nan)

    df = pd.read_csv(path, sep=sep, comment="#", header=0 if has_header else None)
    lats = pd.to_numeric(df[lat_col], errors="coerce").values
    lons = ((pd.to_numeric(df[lon_col], errors="coerce").values + 180.0) % 360.0) - 180.0
    vals = pd.to_numeric(df[val_col], errors="coerce").values

    valid = ~(np.isnan(lats) | np.isnan(lons) | np.isnan(vals) | np.isclose(vals, missing_val, atol=0.01))
    if not np.any(valid):
        print(f"  [!] No valid values in table: {path.name}")
        return np.full((180, 360), np.nan)

    def to_xyz(la, lo):
        la, lo = np.radians(la), np.radians(lo)
        return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])

    valid_vals = vals[valid]
    tree = cKDTree(to_xyz(lats[valid], lons[valid]))

    glat = np.repeat(np.arange(89.5, -90.0, -1.0), 360)
    glon = np.tile(np.arange(-179.5, 180.0, 1.0), 180)
    _, idx = tree.query(to_xyz(glat, glon), distance_upper_bound=0.068)  # ~3.9 deg max radius

    out = np.full(180 * 360, np.nan)
    ok = idx < len(valid_vals)
    out[ok] = valid_vals[idx[ok]]
    print(f"  [+] Loaded table: {path.name}")
    return out.reshape(180, 360)


def ingest_lpgrs_1deg(tab_path: Path):
    """Loads Lunar Prospector equal-area 5-deg .tab using its .xml column definitions."""
    empty = {k: np.full((180, 360), np.nan) for k in ["fe", "ti", "th", "k"]}
    if not tab_path.exists():
        print(f"  [!] Optional LPGRS table missing (filling null): {tab_path.name}")
        return empty

    xml_path = tab_path.with_suffix(".xml")
    if not xml_path.exists():
        try:
            urllib.request.urlretrieve(
                "https://pds-geosciences.wustl.edu/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/lpgrs_high1_elem_abundance_5deg.xml",
                xml_path,
            )
        except Exception as e:
            print(f"  [!] Missing {xml_path.name} ({e}); skipping LPGRS.")
            return empty

    root = ET.parse(xml_path).getroot()
    col_names = [
        next((c.text.strip() for c in el if c.tag.endswith("name") and c.text), None)
        for el in root.iter()
        if el.tag.endswith(("Field_Character", "Field_Delimited"))
    ]

    df = pd.read_csv(tab_path, sep=r"\s+", header=None)
    if len(col_names) != df.shape[1]:
        print(f"  [!] LPGRS XML column count ({len(col_names)}) != table ({df.shape[1]}); skipping.")
        return empty
    df.columns = col_names

    grids = {k: np.full((180, 360), np.nan) for k in ["fe", "ti", "th", "k"]}
    glat = np.arange(89.5, -90.0, -1.0)[:, None]
    glon = np.arange(-179.5, 180.0, 1.0)[None, :]

    for _, row in df.iterrows():
        la0, la1 = float(row["Southernmost_Latitude"]), float(row["Northernmost_Latitude"])
        lo0, lo1 = float(row["Westernmost_Longitude"]), float(row["Easternmost_Longitude"])
        mask = (glat >= la0) & (glat < la1) & (glon >= lo0) & (glon < lo1)

        grids["fe"][mask] = float(row["W_FeO"]) * 100.0   # FeO wt%
        grids["ti"][mask] = float(row["TiO2"]) * 100.0    # TiO2 wt%
        grids["th"][mask] = float(row["W_Th"])            # Th ppm
        grids["k"][mask]  = float(row["W_K"]) / 10000.0   # K wt%

    print(f"  [+] Loaded LPGRS table: {tab_path.name} (W_FeO, TiO2, W_Th, W_K)")
    return grids


def ingest_geology_1deg(shp_path: Path | None, unit_col: str = "Unit", desc_col: str = None):
    """Samples polygon geologic map at all 64,800 1° block centers (handles projected & degree CRSs)."""
    unit_grid = np.full((180, 360), None, dtype=object)
    desc_grid = np.full((180, 360), None, dtype=object)
    if shp_path is None or not shp_path.exists():
        print("  [!] Optional geology shapefile missing (filling null).")
        return unit_grid, desc_grid

    gdf = gpd.read_file(shp_path)
    print(f"  [+] Loaded geology: {shp_path.name} (CRS: {gdf.crs.name if gdf.crs else 'None'})")

    glat = np.repeat(np.arange(89.5, -90.0, -1.0), 360)
    glon = np.tile(np.arange(-179.5, 180.0, 1.0), 180)
    if gdf.crs is not None and not gdf.crs.is_projected and gdf.total_bounds[2] > 185:
        glon = glon % 360.0

    base_crs = gdf.crs.geodetic_crs if (gdf.crs and gdf.crs.is_projected) else gdf.crs
    pts = gpd.GeoDataFrame(
        {"r": np.repeat(np.arange(180), 360), "c": np.tile(np.arange(360), 180)},
        geometry=gpd.points_from_xy(glon, glat),
        crs=base_crs,
    )
    if gdf.crs and gdf.crs.is_projected:
        pts = pts.to_crs(gdf.crs)

    cols = [unit_col, "geometry"] + ([desc_col] if desc_col else [])
    joined = gpd.sjoin(pts, gdf[cols], how="left", predicate="within").drop_duplicates(["r", "c"])

    unit_grid[joined["r"].values, joined["c"].values] = joined[unit_col].values
    if desc_col:
        desc_grid[joined["r"].values, joined["c"].values] = joined[desc_col].values
    return unit_grid, desc_grid


def ingest_moon_geology_raster(moon_dir: Path):
    """Finds dominant lunar geologic unit (mode DN) per 1° block from the 64 ppd USGS GeoTIFF."""
    unit_grid = np.full((180, 360), None, dtype=object)
    name_grid = np.full((180, 360), None, dtype=object)
    age_grid  = np.full((180, 360), None, dtype=object)

    tif_matches = list(moon_dir.rglob("Unified_Geologic_Map_of_the_Moon_64ppd.tif"))
    csv_matches = list(moon_dir.rglob("Dn_GeologicUnit_RGBcolor.csv"))
    if not tif_matches or not csv_matches:
        print("  [!] Optional Moon geology GeoTIFF/CSV missing (filling null).")
        return unit_grid, name_grid, age_grid

    tif_path, csv_path = tif_matches[0], csv_matches[0]
    df = pd.read_csv(csv_path)
    dn_map = {
        int(row["DN"]): (row["Unit"], row["Unit_Name"], row["Unit_Age"])
        for _, row in df.iterrows()
    }

    with rasterio.open(tif_path) as src:
        rows, cols = src.height, src.width
        ky, kx = rows // 180, cols // 360  # 64 x 64 pixels per 1-degree block
        bottom_up = src.transform.e > 0
        for r in range(180):
            strip = src.read(1, window=Window(0, r * ky, cols, ky))
            if bottom_up:
                strip = np.flipud(strip)
            for c in range(360):
                block = strip[:, c * kx : (c + 1) * kx]
                pos = block[block > 0]
                if pos.size > 0:
                    dom_dn = int(np.bincount(pos.astype(np.int32)).argmax())
                    if dom_dn in dn_map:
                        unit_grid[r, c], name_grid[r, c], age_grid[r, c] = dn_map[dom_dn]

    if bottom_up:
        unit_grid = np.flipud(unit_grid)
        name_grid = np.flipud(name_grid)
        age_grid  = np.flipud(age_grid)

    print(f"  [+] Loaded Moon geology raster: {tif_path.name} ({len(dn_map)} units)")
    return unit_grid, name_grid, age_grid


def ingest_caves_1deg(csv_path: Path, radius_m: float = 3_396_190.0):
    """Counts cave candidates per 1° block and computes great-circle distance (km) to nearest cave."""
    counts = np.zeros((180, 360), dtype=int)
    nearest_km = np.full((180, 360), np.nan)
    if not csv_path.exists():
        print(f"  [!] Optional cave catalog missing (filling null): {csv_path.name}")
        return counts, nearest_km

    df = pd.read_csv(csv_path)

    # Fix rotated USGS MGC3 header where Label/Lon/Lat are shifted across the first 3 columns
    if (
        "longitude:string" in df.columns
        and "latitude:string" in df.columns
        and "Label:string" in df.columns
        and pd.to_numeric(df["longitude:string"], errors="coerce").isna().all()
    ):
        lon_c, lat_c = "latitude:string", "Label:string"
    else:
        lat_c = next((col for col in ["lat", "Latitude", "LAT", "Y", "latitude:string"] if col in df.columns), None)
        lon_c = next((col for col in ["lon", "Longitude", "LON", "X", "longitude:string"] if col in df.columns), None)

    if lat_c is None or lon_c is None:
        print(f"  [!] Could not find lat/lon columns in {csv_path.name}: {df.columns.tolist()}")
        return counts, nearest_km

    lats = pd.to_numeric(df[lat_c], errors="coerce").values
    lons = ((pd.to_numeric(df[lon_c], errors="coerce").values + 180.0) % 360.0) - 180.0
    valid = ~(np.isnan(lats) | np.isnan(lons))
    lats, lons = lats[valid], lons[valid]

    for la, lo in zip(lats, lons):
        counts[int(np.clip(89 - math.floor(la), 0, 179)), int(np.clip(math.floor(lo) + 180, 0, 359))] += 1

    def to_xyz(la, lo):
        la, lo = np.radians(la), np.radians(lo)
        return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])

    tree = cKDTree(to_xyz(lats, lons))
    glat = np.repeat(np.arange(89.5, -90.0, -1.0), 360)
    glon = np.tile(np.arange(-179.5, 180.0, 1.0), 180)
    d, _ = tree.query(to_xyz(glat, glon))
    nearest_km = (2.0 * np.arcsin(np.clip(d / 2.0, 0.0, 1.0)) * radius_m / 1000.0).reshape(180, 360)
    print(f"  [+] Loaded caves: {csv_path.name} ({len(lats)} candidates)")
    return counts, nearest_km


def build_mars():
    print("\n=== Building Mars 1° Lookup ===")
    d = RAW / "mars"
    R = 3_396_190.0

    mola_file = find_first_existing(d, ["megt90n000eb.lbl", "megt90n000eb.xml", "megt90n000cb.lbl", "megt90n000cb.xml"])
    if mola_file is None:
        print("  [X] Mars MOLA DEM not found in raw_data/mars/. Skipping Mars.")
        return

    print(f"  [+] Loaded Mars DEM: {mola_file.name}")
    dem = read_global_raster(mola_file)
    slope = calc_spherical_slope(dem, R)

    el_mean, el_min, el_max = bin_to_1deg(dem, "mean"), bin_to_1deg(dem, "min"), bin_to_1deg(dem, "max")
    rough = bin_to_1deg(dem, "std")
    sl_mean, sl_p95 = bin_to_1deg(slope, "mean"), bin_to_1deg(slope, "p95")

    mars_geo_shp = find_first_existing(
        d,
        [
            "SIM3292_Global_Geology.shp",
            "SIM3292_MarsGlobalGeologicGIS_20M/SIM3292_Shapefiles/SIM3292_Global_Geology.shp",
        ],
    )
    geo_unit, geo_desc = ingest_geology_1deg(mars_geo_shp, unit_col="Unit", desc_col="UnitDesc")
    fe  = ingest_table_1deg(d / "fe_sr_5x5.tab")
    si  = ingest_table_1deg(d / "si_sr_5x5.tab")
    k   = ingest_table_1deg(d / "k_sr_5x5.tab")
    th  = ingest_table_1deg(d / "th_sr_5x5.tab")
    weh = ingest_table_1deg(d / "h2o_sr_5x5.tab")

    ti = ingest_raster_1deg(d / "global_ti_day_2007.lbl", "mean")
    dci = ingest_raster_1deg(d / "dci_lo_ice_dust_16ppd_shifted.vicar", "mean")
    swim = ingest_swim_1deg(d / "swim_ice_consistency.tif")
    cave_cnt, cave_km = ingest_caves_1deg(d / "mgc3_caves.csv", R)

    lookup = {}
    for r in range(180):
        lat_idx = 89 - r
        lat_c = lat_idx + 0.5
        for c in range(360):
            lon_idx = c - 180
            el = float(el_mean[r, c])
            sl95 = float(sl_p95[r, c])
            ti_v = float(ti[r, c])
            dci_v = float(dci[r, c])

            p_mbar = 6.10 * math.exp(-el / 11100.0) if not math.isnan(el) else np.nan

            lat_factor = math.cos(math.radians(lat_c))
            t_max = 185.0 + 100.0 * lat_factor
            swing = 135.0 - min(ti_v, 600.0) * 0.12 if not math.isnan(ti_v) else 95.0
            t_min = max(130.0, t_max - swing)

            if math.isnan(el) or math.isnan(sl95):
                mob = np.nan
            else:
                mob = 100.0 - min(sl95, 15.0) * 4.0 - max(0.0, (el + 2000.0) / 150.0)
                if not math.isnan(dci_v) and dci_v < 0.94:
                    mob -= (0.94 - dci_v) * 300.0
                mob = max(0.0, min(100.0, mob))

            lookup[f"{lat_idx}_{lon_idx}"] = {
                "lat_center": lat_c,
                "lon_center": lon_idx + 0.5,
                "geology": {
                    "unit_code": clean_str(geo_unit[r, c]),
                    "unit_desc": clean_str(geo_desc[r, c]),
                    "fe_wt_pct": r_round(fe[r, c]),
                    "si_wt_pct": r_round(si[r, c]),
                    "k_wt_pct": r_round(k[r, c], 3),
                    "th_ppm": r_round(th[r, c]),
                },
                "terrain": {
                    "elev_mean_m": r_round(el, 1),
                    "elev_min_m": r_round(el_min[r, c], 1),
                    "elev_max_m": r_round(el_max[r, c], 1),
                    "relief_m": r_round(el_max[r, c] - el_min[r, c], 1),
                    "slope_mean_deg": r_round(sl_mean[r, c]),
                    "slope_p95_deg": r_round(sl95),
                    "roughness_std_m": r_round(rough[r, c], 1),
                },
                "thermal": {
                    "thermal_inertia_tiu": r_round(ti_v, 1),
                    "temp_day_max_k": r_round(t_max, 1),
                    "temp_night_min_k": r_round(t_min, 1),
                    "diurnal_swing_k": r_round(t_max - t_min, 1),
                },
                "water_ice": {
                    "weh_wt_pct": r_round(weh[r, c]),
                    "swim_ice_consistency": r_round(swim[r, c], 3),
                    "polar_ice_flag": abs(lat_c) >= 75.0,
                },
                "atmosphere_dust": {
                    "surface_pressure_mbar": r_round(p_mbar),
                    "dust_cover_index": r_round(dci_v, 3),
                },
                "subsurface_caves": {
                    "cave_count": int(cave_cnt[r, c]),
                    "nearest_cave_km": r_round(cave_km[r, c], 1),
                },
                "landing_mobility": {
                    "edl_elev_feasible": None if math.isnan(el) else bool(el < -1000.0),
                    "hazard_slope_p95_deg": r_round(sl95),
                    "bearing_strength_tiu": r_round(ti_v, 1),
                    "mobility_rating_0_100": r_round(mob, 1),
                },
            }

    out_path = OUT / "mars_1deg_lookup.json"
    with open(out_path, "w") as f:
        json.dump(lookup, f, separators=(",", ":"), allow_nan=False)
    print(f"Saved {out_path} ({len(lookup)} blocks)")


def build_moon():
    print("\n=== Building Moon 1° Lookup ===")
    d = RAW / "moon"
    R = 1_737_400.0

    lola_file = find_first_existing(d, ["ldem_16.lbl", "ldem_16.xml", "ldem_4.lbl", "ldem_4.xml"])
    if lola_file is None:
        print("  [X] Moon LOLA DEM not found in raw_data/moon/. Skipping Moon.")
        return

    print(f"  [+] Loaded Moon DEM: {lola_file.name}")
    dem = read_global_raster(lola_file)
    if np.nanmean(dem) > 100_000.0:
        dem -= R  # Convert LOLA radius from Moon center -> elevation relative to 1,737,400 m
    slope = calc_spherical_slope(dem, R)

    el_mean, el_min, el_max = bin_to_1deg(dem, "mean"), bin_to_1deg(dem, "min"), bin_to_1deg(dem, "max")
    rough = bin_to_1deg(dem, "std")
    sl_mean, sl_p95 = bin_to_1deg(slope, "mean"), bin_to_1deg(slope, "p95")

    geo_unit, geo_name, geo_age = ingest_moon_geology_raster(d)
    lp = ingest_lpgrs_1deg(d / "lpgrs_high1_elem_abundance_5deg.tab")
    fe, ti, th, k = lp["fe"], lp["ti"], lp["th"], lp["k"]

    t_day = ingest_diviner_xyz_1deg(d / "diviner_tbol_max.xyz", "max")
    t_night = ingest_diviner_xyz_1deg(d / "diviner_tbol_min.xyz", "min")
    rock_file = find_first_existing(d, ["dgdr_ra_avg_cyl_032_img.lbl", "dgdr_ra_avg_cyl_032_img.xml", "diviner_rock_abundance.lbl"])
    rock = ingest_moon_rock_1deg(rock_file)

    lookup = {}
    for r in range(180):
        lat_idx = 89 - r
        lat_c = lat_idx + 0.5
        for c in range(360):
            lon_idx = c - 180
            lon_c = lon_idx + 0.5
            sl95 = float(sl_p95[r, c])
            rk = float(rock[r, c])
            td, tn = float(t_day[r, c]), float(t_night[r, c])

            if math.isnan(sl95):
                mob = np.nan
            else:
                mob = max(0.0, min(100.0, 100.0 - min(sl95, 15.0) * 4.5 - (0.0 if math.isnan(rk) else rk * 120.0)))

            lookup[f"{lat_idx}_{lon_idx}"] = {
                "lat_center": lat_c,
                "lon_center": lon_c,
                "geology": {
                    "unit_code": clean_str(geo_unit[r, c]),
                    "unit_name": clean_str(geo_name[r, c]),
                    "unit_age": clean_str(geo_age[r, c]),
                    "feo_wt_pct": r_round(fe[r, c]),
                    "tio2_wt_pct": r_round(ti[r, c]),
                    "th_ppm": r_round(th[r, c]),
                    "k_wt_pct": r_round(k[r, c], 3),
                },
                "terrain": {
                    "elev_mean_m": r_round(el_mean[r, c], 1),
                    "elev_min_m": r_round(el_min[r, c], 1),
                    "elev_max_m": r_round(el_max[r, c], 1),
                    "relief_m": r_round(el_max[r, c] - el_min[r, c], 1),
                    "slope_mean_deg": r_round(sl_mean[r, c]),
                    "slope_p95_deg": r_round(sl95),
                    "roughness_std_m": r_round(rough[r, c], 1),
                },
                "thermal": {
                    "temp_day_max_k": r_round(td, 1),
                    "temp_night_min_k": r_round(tn, 1),
                    "diurnal_swing_k": None if (math.isnan(td) or math.isnan(tn)) else r_round(td - tn, 1),
                    "rock_abundance_frac": r_round(rk, 3),
                },
                "water_ice": {
                    "polar_psr_zone": abs(lat_c) >= 80.0,
                },
                "atmosphere_dust": None,
                "subsurface_caves": None,
                "landing_mobility": {
                    "earth_los_visible": abs(lon_c) < 85.0,
                    "hazard_slope_p95_deg": r_round(sl95),
                    "rock_abundance_frac": r_round(rk, 3),
                    "mobility_rating_0_100": r_round(mob, 1),
                },
            }

    out_path = OUT / "moon_1deg_lookup.json"
    with open(out_path, "w") as f:
        json.dump(lookup, f, separators=(",", ":"), allow_nan=False)
    print(f"Saved {out_path} ({len(lookup)} blocks)")


if __name__ == "__main__":
    build_mars()
    build_moon()