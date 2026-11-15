import gc
import json
import math
import re
import sqlite3
import sys
import threading
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
from scipy import sparse

try:
    import ijson  # type: ignore
except ImportError:
    ijson = None

try:
    import orjson  # type: ignore
except ImportError:
    orjson = None


CACHE_SCHEMA_VERSION = 3

ALL_CONDITIONS_CATEGORY = "All Conditions"

PRIORITY_CATEGORIES = (
    "Geology & Mineralogy",
    "Terrain & Topography",
    "Thermal & Extremes",
    "Water & Ice",
    "Atmospheric/Dust (MARS)",
    "Subsurface/Caves (MARS)",
    "Landing/Mobility",
)

CATEGORY_ALIASES = {
    "": ALL_CONDITIONS_CATEGORY,
    "none": ALL_CONDITIONS_CATEGORY,
    "no category": ALL_CONDITIONS_CATEGORY,
    "no_category": ALL_CONDITIONS_CATEGORY,
    "all": ALL_CONDITIONS_CATEGORY,
    "all conditions": ALL_CONDITIONS_CATEGORY,
    "all_conditions": ALL_CONDITIONS_CATEGORY,
    "balanced": ALL_CONDITIONS_CATEGORY,
    "any": ALL_CONDITIONS_CATEGORY,
    "geology & mineralogy": "Geology & Mineralogy",
    "geology": "Geology & Mineralogy",
    "terrain & topography": "Terrain & Topography",
    "terrain": "Terrain & Topography",
    "thermal & extremes": "Thermal & Extremes",
    "thermal": "Thermal & Extremes",
    "water & ice": "Water & Ice",
    "water": "Water & Ice",
    "atmospheric/dust (mars)": "Atmospheric/Dust (MARS)",
    "atmospheric/dust": "Atmospheric/Dust (MARS)",
    "atmosphere": "Atmospheric/Dust (MARS)",
    "subsurface/caves (mars)": "Subsurface/Caves (MARS)",
    "subsurface/caves": "Subsurface/Caves (MARS)",
    "caves": "Subsurface/Caves (MARS)",
    "landing/mobility": "Landing/Mobility",
    "landing": "Landing/Mobility",
    "mobility": "Landing/Mobility",
}

MARS_ONLY_CATEGORIES = frozenset({
    "Atmospheric/Dust (MARS)",
    "Subsurface/Caves (MARS)",
})

FEATURE_GROUPS: Dict[str, Tuple[int, ...]] = {
    "Terrain & Topography": (0, 1, 2, 3, 4, 5, 6),
    "Thermal & Extremes": (7, 8, 9, 10, 11),
    "Geology & Mineralogy": (12, 13, 14, 15, 16, 17, 18),
    "Water & Ice": (19, 20, 21),
    "Atmospheric/Dust (MARS)": (22, 23),
    "Subsurface/Caves (MARS)": (24, 25),
    "Landing/Mobility": (26, 27, 28),
}

QUANTILE_ALIGN_COLS = (0, 1, 2, 3, 4, 7, 8, 9, 11, 18, 20, 21, 22, 23, 24, 25, 26, 28)
BOUNDED_COLS = (5, 6, 10, 12, 13, 14, 15, 16, 17, 19, 27)
N_FEATURES = 29

GLIM_MAP: Dict[str, Tuple[float, float, float, float, float, float]] = {
    "vb": (1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    "vi": (0.6, 0.4, 0.0, 0.0, 0.0, 0.0),
    "va": (0.2, 0.8, 0.0, 0.0, 0.0, 0.0),
    "py": (0.6, 0.2, 0.2, 0.0, 0.0, 0.0),
    "pb": (0.8, 0.2, 0.0, 0.0, 0.0, 0.0),
    "pi": (0.3, 0.7, 0.0, 0.0, 0.0, 0.0),
    "pa": (0.0, 1.0, 0.0, 0.0, 0.0, 0.0),
    "mt": (0.2, 0.8, 0.0, 0.0, 0.0, 0.0),
    "ss": (0.0, 0.0, 1.0, 0.0, 0.0, 0.0),
    "sm": (0.0, 0.0, 0.7, 0.0, 0.3, 0.0),
    "su": (0.0, 0.0, 0.2, 1.0, 0.0, 0.0),
    "sc": (0.0, 0.0, 0.2, 0.0, 1.0, 0.0),
    "ev": (0.0, 0.0, 0.0, 0.0, 1.0, 0.0),
    "ig": (0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
}

TEXT_LITH_PATTERNS: Tuple[Tuple[re.Pattern, np.ndarray], ...] = (
    (
        re.compile(r"\b(basalt|mare|maria|lava|volcan|shield|caldera|mafic|tharsis|olympus|flood|pyroclast|scoria)\b"),
        np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0), dtype=np.float64),
    ),
    (
        re.compile(r"\b(terra|highland|anorthosit|granit|pluton|felsic|craton|metamorphic|gneiss|schist|crystalline|noachian)\b"),
        np.array((0.0, 1.0, 0.0, 0.0, 0.0, 0.0), dtype=np.float64),
    ),
    (
        re.compile(r"\b(sediment|fluvial|alluvial|lacustrine|delta|basin|sandstone|shale|mudstone|outwash|channel|valley|crater floor)\b"),
        np.array((0.0, 0.0, 1.0, 0.0, 0.0, 0.0), dtype=np.float64),
    ),
    (
        re.compile(r"\b(eolian|aeolian|dune|sand|dust|regolith|loess|unconsolidated|mantle|ejecta|plain)\b"),
        np.array((0.0, 0.0, 0.1, 1.0, 0.0, 0.0), dtype=np.float64),
    ),
    (
        re.compile(r"\b(evaporit|sulfate|chloride|carbonate|limestone|karst|clay|phyllosilicate|smectite|alteration|saline|playa)\b"),
        np.array((0.0, 0.0, 0.1, 0.0, 1.0, 0.0), dtype=np.float64),
    ),
    (
        re.compile(r"\b(polar|ice|glaci|cap|layered deposit|frost|permafrost)\b"),
        np.array((0.0, 0.0, 0.0, 0.0, 0.0, 1.0), dtype=np.float64),
    ),
)


def _f(val: Any) -> float:
    if val is None:
        return math.nan
    try:
        v = float(val)
        return v if math.isfinite(v) else math.nan
    except (TypeError, ValueError):
        return math.nan


def _b(val: Any) -> float:
    if val is None:
        return math.nan
    return 1.0 if val else 0.0


def _norm_lon(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


def _latlon_to_xyz_single(lat_deg: float, lon_deg: float) -> np.ndarray:
    lat_r = math.radians(lat_deg)
    lon_r = math.radians(lon_deg)
    c = math.cos(lat_r)
    return np.array([c * math.cos(lon_r), c * math.sin(lon_r), math.sin(lat_r)], dtype=np.float32)


def _latlon_to_xyz(lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    lat_r = np.radians(lat_deg)
    lon_r = np.radians(lon_deg)
    c = np.cos(lat_r)
    return np.column_stack([c * np.cos(lon_r), c * np.sin(lon_r), np.sin(lat_r)]).astype(np.float32)


def _dump_json_bytes(obj: Dict[str, Any]) -> bytes:
    if orjson is not None:
        return orjson.dumps(obj)
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def _load_json_bytes(raw: bytes) -> Dict[str, Any]:
    if orjson is not None:
        return orjson.loads(raw)
    return json.loads(raw.decode("utf-8"))


def _iter_json_kv(path: Path) -> Iterable[Tuple[str, Dict[str, Any]]]:
    if ijson is not None:
        with open(path, "rb") as f:
            yield from ijson.kvitems(f, "")
        return

    if orjson is not None:
        with open(path, "rb") as f:
            data = orjson.loads(f.read())
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    for k, v in data.items():
        yield k, v
    del data
    gc.collect()


def _is_earth_land_or_ice(cell: Dict[str, Any]) -> bool:
    geo = cell.get("geology") or {}
    ter = cell.get("terrain") or {}
    wat = cell.get("water_ice") or {}

    lith = geo.get("lith_class")
    elev_max = _f(ter.get("elev_max_m"))
    polar_flag = bool(wat.get("polar_ice_flag"))
    glim_ice = bool(wat.get("glim_ice_class"))
    barren = _f(wat.get("barren_pct"))
    snow = _f(wat.get("snow_ice_pct"))

    if lith == "wb" and not (polar_flag or glim_ice or (not math.isnan(snow) and snow > 20.0)):
        return False
    if (
        (math.isnan(elev_max) or elev_max <= 0.0)
        and lith in (None, "wb", "nd")
        and not polar_flag
        and not glim_ice
        and math.isnan(barren)
        and math.isnan(snow)
    ):
        return False
    return True


def _extract_geology_vector(cell: Dict[str, Any], body: str) -> Tuple[np.ndarray, float, str]:
    geo = cell.get("geology") or {}
    wat = cell.get("water_ice") or {}
    vec = np.zeros(6, dtype=np.float64)
    has_signal = False

    if body == "earth":
        lith = (geo.get("lith_class") or "").strip().lower()
        desc = " ".join(p for p in (geo.get("unit_desc"), geo.get("unit_code"), lith) if p)
        if lith in GLIM_MAP:
            vec += GLIM_MAP[lith]
            has_signal = True
        if wat.get("glim_ice_class") or wat.get("polar_ice_flag"):
            vec[5] = max(vec[5], 0.9)
            has_signal = True

        k_th_proxy = math.nan
        if lith in ("pa", "va", "pi"):
            k_th_proxy = 0.85
        elif lith in ("mt", "ss", "sm", "vi"):
            k_th_proxy = 0.55
        elif lith in ("su", "sc", "ev"):
            k_th_proxy = 0.35
        elif lith in ("vb", "pb", "py"):
            k_th_proxy = 0.15
        elif lith == "ig":
            k_th_proxy = 0.05

    elif body == "mars":
        desc = " ".join(p for p in (geo.get("unit_desc"), geo.get("unit_code")) if p)
        fe = _f(geo.get("fe_wt_pct"))
        si = _f(geo.get("si_wt_pct"))
        k = _f(geo.get("k_wt_pct"))
        th = _f(geo.get("th_ppm"))

        if not math.isnan(fe):
            has_signal = True
            if fe >= 14.5:
                vec[0] += min(1.0, max(0.0, (fe - 13.0) / 6.0))
            else:
                vec[1] += min(0.7, max(0.0, (15.0 - fe) / 6.0))
        if not math.isnan(si):
            has_signal = True
            if si >= 21.5:
                vec[1] += min(0.8, max(0.0, (si - 21.0) / 4.0))
            else:
                vec[0] += min(0.8, max(0.0, (21.5 - si) / 4.0))
        if wat.get("polar_ice_flag"):
            vec[5] = max(vec[5], 1.0)
            has_signal = True

        k_th_proxy = math.nan
        if not math.isnan(k) or not math.isnan(th):
            parts = []
            if not math.isnan(k):
                parts.append(min(1.5, max(0.0, k / 0.6)))
            if not math.isnan(th):
                parts.append(min(1.5, max(0.0, th / 6.0)))
            k_th_proxy = sum(parts) / len(parts)

    else:
        desc = " ".join(p for p in (geo.get("unit_name"), geo.get("unit_age"), geo.get("unit_code")) if p)
        feo = _f(geo.get("feo_wt_pct"))
        tio2 = _f(geo.get("tio2_wt_pct"))
        k = _f(geo.get("k_wt_pct"))
        th = _f(geo.get("th_ppm"))

        if not math.isnan(feo):
            has_signal = True
            vec[0] += min(1.2, max(0.0, (feo - 8.0) / 10.0))
            vec[1] += min(1.0, max(0.0, (10.0 - feo) / 6.0))
        if not math.isnan(tio2):
            has_signal = True
            vec[0] += min(0.8, max(0.0, tio2 / 5.0))
        if wat.get("polar_psr_zone"):
            vec[5] = max(vec[5], 0.5)

        k_th_proxy = math.nan
        if not math.isnan(k) or not math.isnan(th):
            parts = []
            if not math.isnan(k):
                parts.append(min(1.5, max(0.0, k / 0.4)))
            if not math.isnan(th):
                parts.append(min(1.5, max(0.0, th / 8.0)))
            k_th_proxy = sum(parts) / len(parts)

    desc_low = desc.lower()
    if desc_low:
        for pat, pvec in TEXT_LITH_PATTERNS:
            if pat.search(desc_low):
                vec += pvec * 0.8
                has_signal = True

    if not has_signal or vec.sum() <= 0.0:
        return np.full(6, np.nan, dtype=np.float64), k_th_proxy, desc

    vec /= max(float(vec.max()), 1e-6)
    return vec, k_th_proxy, desc


def _extract_raw_row(cell: Dict[str, Any], body: str) -> Tuple[np.ndarray, str]:
    row = np.full(N_FEATURES, np.nan, dtype=np.float64)

    ter = cell.get("terrain") or {}
    thm = cell.get("thermal") or {}
    wat = cell.get("water_ice") or {}
    atm = cell.get("atmosphere_dust") or {}
    cav = cell.get("subsurface_caves") or {}
    mob = cell.get("landing_mobility") or {}

    elev_mean = _f(ter.get("elev_mean_m"))
    elev_min = _f(ter.get("elev_min_m"))
    relief = _f(ter.get("relief_m"))
    slope_mean = _f(ter.get("slope_mean_deg"))
    slope_p95 = _f(ter.get("slope_p95_deg"))
    rough = _f(ter.get("roughness_std_m"))

    if not math.isnan(relief):
        row[0] = math.log1p(max(0.0, relief))
    if not math.isnan(slope_mean):
        l_sm = math.log1p(max(0.0, slope_mean))
        row[1] = l_sm
        row[6] = min(1.0, max(0.0, l_sm / 3.5))
    if not math.isnan(slope_p95):
        row[2] = math.log1p(max(0.0, slope_p95))
    if not math.isnan(rough):
        row[3] = math.log1p(max(0.0, rough))
    row[4] = elev_mean
    if not math.isnan(elev_mean) and not math.isnan(elev_min) and not math.isnan(relief) and relief > 1.0:
        row[5] = min(1.0, max(0.0, (elev_mean - elev_min) / relief))

    row[7] = _f(thm.get("temp_day_max_k"))
    row[8] = _f(thm.get("temp_night_min_k"))
    swing = _f(thm.get("diurnal_swing_k"))
    row[9] = swing
    if not math.isnan(swing):
        row[10] = min(1.0, max(0.0, math.log1p(max(0.0, swing)) / 5.0))

    geo_vec, k_th_proxy, geo_text = _extract_geology_vector(cell, body)
    row[12:18] = geo_vec
    row[18] = k_th_proxy

    if body == "mars":
        row[11] = _f(thm.get("thermal_inertia_tiu"))
    elif body == "moon":
        row[11] = _f(thm.get("rock_abundance_frac"))
    else:
        barren = _f(wat.get("barren_pct"))
        g0 = 0.0 if math.isnan(geo_vec[0]) else geo_vec[0]
        g1 = 0.0 if math.isnan(geo_vec[1]) else geo_vec[1]
        g3 = 0.0 if math.isnan(geo_vec[3]) else geo_vec[3]
        bedrock = max(0.0, g0, g1) - 0.5 * g3
        r_comp = 0.0 if math.isnan(rough) else min(1.0, math.log1p(max(0.0, rough)) / 7.0)
        b_comp = 0.3 if math.isnan(barren) else barren / 100.0
        row[11] = 0.4 * b_comp + 0.35 * r_comp + 0.25 * min(1.0, max(0.0, bedrock))

    if body == "mars":
        p_ice = _b(wat.get("polar_ice_flag"))
        row[19] = p_ice
        weh = _f(wat.get("weh_wt_pct"))
        swim = _f(wat.get("swim_ice_consistency"))
        vals = [v for v in (weh, math.nan if math.isnan(swim) else swim * 10.0) if not math.isnan(v)]
        if vals:
            m_val = sum(vals) / len(vals)
            row[20] = m_val
            row[21] = 0.0 if p_ice == 1.0 else -m_val
        elif p_ice == 1.0:
            row[20] = 50.0
            row[21] = -50.0
        else:
            row[21] = 1.0

    elif body == "moon":
        psr = _b(wat.get("polar_psr_zone"))
        row[19] = psr
        row[20] = 1.0 if psr == 1.0 else 0.0
        row[21] = 0.0 if psr == 1.0 else 1.0

    else:
        p_ice = _b(wat.get("polar_ice_flag"))
        g_ice = _b(wat.get("glim_ice_class"))
        snow = _f(wat.get("snow_ice_pct"))
        barren = _f(wat.get("barren_pct"))
        precip = _f(wat.get("annual_precip_mm"))
        tmean = _f(thm.get("mean_annual_temp_k"))

        ice_frac = 0.0
        if p_ice == 1.0 or g_ice == 1.0:
            ice_frac = 1.0
        elif not math.isnan(snow):
            ice_frac = min(1.0, max(0.0, snow / 100.0))
        row[19] = ice_frac

        cold_bonus = 0.0 if math.isnan(tmean) else min(1.0, max(0.0, (275.0 - tmean) / 30.0))
        row[20] = 0.65 * ice_frac + 0.35 * cold_bonus

        p_arid = 0.5 if math.isnan(precip) else (1.0 - min(1.0, math.log1p(max(0.0, precip)) / 8.0))
        b_arid = 0.5 if math.isnan(barren) else min(1.0, max(0.0, barren / 100.0))
        row[21] = (0.6 * p_arid + 0.4 * b_arid) * (1.0 - 0.8 * ice_frac)

    if body == "mars":
        row[22] = _f(atm.get("surface_pressure_mbar"))
        row[23] = _f(atm.get("dust_cover_index"))
    elif body == "earth":
        if not math.isnan(elev_mean):
            row[22] = -elev_mean
        barren = _f(wat.get("barren_pct"))
        precip = _f(wat.get("annual_precip_mm"))
        snow = _f(wat.get("snow_ice_pct"))
        b_val = 0.3 if math.isnan(barren) else barren / 100.0
        p_dry = 0.5 if math.isnan(precip) else (1.0 - min(1.0, math.log1p(max(0.0, precip)) / 8.0))
        s_val = 0.0 if math.isnan(snow) else snow / 100.0
        unconsol = 0.0 if math.isnan(geo_vec[3]) else geo_vec[3]
        row[23] = (0.45 * b_val + 0.35 * p_dry + 0.20 * unconsol) * (1.0 - 0.85 * s_val)

    if body == "mars":
        c_cnt = _f(cav.get("cave_count"))
        c_km = _f(cav.get("nearest_cave_km"))
        if not math.isnan(c_cnt) or not math.isnan(c_km):
            cnt_term = 0.0 if math.isnan(c_cnt) else math.log1p(max(0.0, c_cnt))
            dist_term = 0.0 if math.isnan(c_km) else math.exp(-max(0.0, c_km) / 250.0)
            cave_score = 0.55 * cnt_term + 0.45 * dist_term
            row[24] = cave_score
            mafic = 0.5 if math.isnan(geo_vec[0]) else geo_vec[0]
            row[25] = cave_score * (0.3 + 0.7 * mafic)
    elif body == "earth":
        mafic = 0.0 if math.isnan(geo_vec[0]) else geo_vec[0]
        karst = 0.0 if math.isnan(geo_vec[4]) else geo_vec[4]
        rel_n = 0.0 if math.isnan(row[0]) else min(1.0, max(0.0, row[0] / 8.0))
        arid_n = 0.5 if math.isnan(row[21]) else min(1.0, max(0.0, row[21]))
        row[24] = (0.65 * mafic + 0.35 * karst) * (0.35 + 0.45 * rel_n + 0.20 * arid_n)
        row[25] = mafic * rel_n

    if body in ("mars", "moon"):
        haz = _f(mob.get("hazard_slope_p95_deg"))
        if not math.isnan(haz):
            row[26] = math.log1p(max(0.0, haz))
        m_rat = _f(mob.get("mobility_rating_0_100"))
        if not math.isnan(m_rat):
            row[27] = min(1.0, max(0.0, m_rat / 100.0))

        if body == "mars":
            edl = _b(mob.get("edl_elev_feasible"))
            tiu = _f(mob.get("bearing_strength_tiu"))
            if not math.isnan(edl) or not math.isnan(tiu):
                edl_v = 0.5 if math.isnan(edl) else edl
                tiu_v = 0.5 if math.isnan(tiu) else min(1.0, max(0.0, tiu / 400.0))
                row[28] = 0.5 * edl_v + 0.5 * tiu_v
        else:
            los = _b(mob.get("earth_los_visible"))
            rock = _f(mob.get("rock_abundance_frac"))
            if not math.isnan(los) or not math.isnan(rock):
                los_v = 0.5 if math.isnan(los) else los
                rock_v = 0.5 if math.isnan(rock) else (1.0 - min(1.0, max(0.0, rock)))
                row[28] = 0.4 * los_v + 0.6 * rock_v
    else:
        if not math.isnan(slope_p95):
            row[26] = math.log1p(max(0.0, slope_p95))
            s_pen = min(1.0, slope_p95 / 30.0)
            r_pen = 0.3 if math.isnan(rough) else min(1.0, rough / 350.0)
            snow = _f(wat.get("snow_ice_pct"))
            snow_pen = 0.0 if math.isnan(snow) else 0.25 * (snow / 100.0)
            row[27] = min(1.0, max(0.0, 1.0 - (0.55 * s_pen + 0.30 * r_pen + snow_pen)))
        if not math.isnan(elev_mean):
            elev_ok = min(1.0, max(0.0, 1.0 - max(0.0, elev_mean) / 5000.0))
            inertia = 0.5 if math.isnan(row[11]) else min(1.0, max(0.0, row[11]))
            row[28] = 0.5 * elev_ok + 0.5 * inertia

    return row, geo_text


def _align_features(X: np.ndarray) -> np.ndarray:
    from sklearn.preprocessing import QuantileTransformer

    X_out = np.full_like(X, np.nan, dtype=np.float32)
    n_q = min(1000, max(10, X.shape[0]))

    for col in QUANTILE_ALIGN_COLS:
        vals = X[:, col]
        valid = ~np.isnan(vals)
        if valid.sum() < 20 or np.nanstd(vals) < 1e-9:
            if valid.sum() > 0:
                X_out[valid, col] = 0.0
            continue
        qt = QuantileTransformer(n_quantiles=n_q, output_distribution="normal", random_state=42)
        transformed = qt.fit_transform(vals[valid].reshape(-1, 1)).ravel()
        X_out[valid, col] = np.clip(transformed, -3.5, 3.5).astype(np.float32)

    for col in BOUNDED_COLS:
        vals = X[:, col]
        valid = ~np.isnan(vals)
        X_out[valid, col] = ((vals[valid] - 0.5) * 3.0).astype(np.float32)

    return X_out


def build_cache(
    earth_json_path: Union[str, Path] = "earth_0.25deg_lookup.json",
    mars_json_path: Union[str, Path] = "mars_1deg_lookup.json",
    moon_json_path: Union[str, Path] = "moon_1deg_lookup.json",
    cache_dir: Union[str, Path] = "analog_cache",
) -> Path:
    from sklearn.feature_extraction.text import TfidfVectorizer

    paths = {
        "earth": Path(earth_json_path),
        "mars": Path(mars_json_path),
        "moon": Path(moon_json_path),
    }
    for body, p in paths.items():
        if not p.exists():
            raise FileNotFoundError(f"Missing lookup JSON for {body}: {p}")

    out_dir = Path(cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pack raw cell JSONs into compressed SQLite for O(1), near-zero-RAM runtime lookup
    db_tmp = out_dir / "lookup.db.tmp"
    db_final = out_dir / "lookup.db"
    if db_tmp.exists():
        db_tmp.unlink()

    db_conn = sqlite3.connect(str(db_tmp))
    db_conn.execute("PRAGMA journal_mode=OFF")
    db_conn.execute("PRAGMA synchronous=OFF")
    db_conn.execute(
        "CREATE TABLE cells ("
        "body TEXT NOT NULL, "
        "cell_key TEXT NOT NULL, "
        "data BLOB NOT NULL, "
        "PRIMARY KEY (body, cell_key)"
        ")"
    )

    texts_by_body: Dict[str, List[str]] = {}
    corpus: List[str] = []

    try:
        for body in ("mars", "moon", "earth"):
            coords_list: List[Tuple[float, float]] = []
            feat_rows: List[np.ndarray] = []
            texts: List[str] = []
            keys_list: List[str] = []
            db_batch: List[Tuple[str, str, bytes]] = []
            grid_map = np.full((180, 360), -1, dtype=np.int32) if body in ("mars", "moon") else None

            for k, cell in _iter_json_kv(paths[body]):
                if body == "earth" and not _is_earth_land_or_ice(cell):
                    continue
                lat = _f(cell.get("lat_center"))
                lon = _f(cell.get("lon_center"))
                if math.isnan(lat) or math.isnan(lon):
                    continue

                idx = len(coords_list)
                row, gtext = _extract_raw_row(cell, body)
                coords_list.append((lon, lat))
                feat_rows.append(row)
                texts.append(gtext)
                keys_list.append(k)

                db_batch.append((body, k, zlib.compress(_dump_json_bytes(cell), level=6)))
                if len(db_batch) >= 10000:
                    db_conn.executemany("INSERT OR REPLACE INTO cells VALUES (?, ?, ?)", db_batch)
                    db_conn.commit()
                    db_batch.clear()

                if grid_map is not None:
                    try:
                        lat_i_s, lon_i_s = k.split("_", 1)
                        lat_i, lon_i = int(lat_i_s), int(lon_i_s)
                        if -90 <= lat_i < 90 and -180 <= lon_i < 180:
                            grid_map[lat_i + 90, lon_i + 180] = idx
                    except ValueError:
                        pass

            if db_batch:
                db_conn.executemany("INSERT OR REPLACE INTO cells VALUES (?, ?, ?)", db_batch)
                db_conn.commit()
                db_batch.clear()

            coords = np.asarray(coords_list, dtype=np.float32)
            X_raw = np.asarray(feat_rows, dtype=np.float64)
            del coords_list, feat_rows
            gc.collect()

            X_aligned = _align_features(X_raw)
            del X_raw
            gc.collect()

            np.save(out_dir / f"{body}_coords.npy", coords)
            np.save(out_dir / f"{body}_keys.npy", np.asarray([s.encode("utf-8")[:16] for s in keys_list], dtype="S16"))
            np.save(out_dir / f"{body}_texts.npy", np.asarray([t.encode("utf-8")[:160] for t in texts], dtype="S160"))

            if body == "earth":
                V_T = (~np.isnan(X_aligned)).astype(np.float32).T.copy()
                X0_T = np.nan_to_num(X_aligned, nan=0.0).astype(np.float32).T.copy()
                X0_sq_T = (X0_T ** 2).copy()
                np.save(out_dir / "earth_V_T.npy", V_T)
                np.save(out_dir / "earth_X0_T.npy", X0_T)
                np.save(out_dir / "earth_X0_sq_T.npy", X0_sq_T)
                del V_T, X0_T, X0_sq_T
            else:
                np.save(out_dir / f"{body}_features.npy", X_aligned)
                np.save(out_dir / f"{body}_grid_map.npy", grid_map)
                np.save(out_dir / f"{body}_xyz.npy", _latlon_to_xyz(coords[:, 1], coords[:, 0]))

            texts_by_body[body] = texts
            corpus.extend(t for t in texts if t.strip())
            del X_aligned, coords, keys_list
            gc.collect()
    finally:
        db_conn.close()

    db_tmp.replace(db_final)

    has_tfidf = False
    if corpus:
        tfidf = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_features=4096,
            stop_words="english",
            sublinear_tf=True,
            dtype=np.float32,
        )
        tfidf.fit(corpus)
        del corpus
        gc.collect()

        earth_mat = tfidf.transform(texts_by_body["earth"]).tocsc()
        mars_mat = tfidf.transform(texts_by_body["mars"]).tocsr()
        moon_mat = tfidf.transform(texts_by_body["moon"]).tocsr()

        sparse.save_npz(out_dir / "earth_tfidf_csc.npz", earth_mat)
        sparse.save_npz(out_dir / "mars_tfidf_csr.npz", mars_mat)
        sparse.save_npz(out_dir / "moon_tfidf_csr.npz", moon_mat)
        has_tfidf = True

    meta = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "has_tfidf": has_tfidf,
        "sources": {
            b: {"size": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns}
            for b, p in paths.items()
        },
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out_dir


class PlanetaryAnalogMatcher:
    def __init__(
        self,
        earth_json_path: Union[str, Path] = "earth_0.25deg_lookup.json",
        mars_json_path: Union[str, Path] = "mars_1deg_lookup.json",
        moon_json_path: Union[str, Path] = "moon_1deg_lookup.json",
        cache_dir: Union[str, Path] = "analog_cache",
        auto_build_cache: bool = True,
        lru_cache_size: int = 8192,
    ):
        self.cache_dir = Path(cache_dir)
        sources = {
            "earth": Path(earth_json_path),
            "mars": Path(mars_json_path),
            "moon": Path(moon_json_path),
        }

        if not self._is_cache_valid(sources):
            if not auto_build_cache:
                raise RuntimeError(
                    f"Binary cache missing or stale at '{self.cache_dir}'. "
                    "Run `python analog_matcher.py build` first."
                )
            build_cache(earth_json_path, mars_json_path, moon_json_path, self.cache_dir)

        meta = json.loads((self.cache_dir / "meta.json").read_text(encoding="utf-8"))
        self.has_tfidf = bool(meta.get("has_tfidf", False))
        self._db_path = (self.cache_dir / "lookup.db").resolve()
        self._db_local = threading.local()

        self.earth_coords = np.load(self.cache_dir / "earth_coords.npy", mmap_mode="r")
        self.earth_keys = np.load(self.cache_dir / "earth_keys.npy", mmap_mode="r")
        self.earth_texts = np.load(self.cache_dir / "earth_texts.npy", mmap_mode="r")
        self.earth_V_T = np.load(self.cache_dir / "earth_V_T.npy", mmap_mode="r")
        self.earth_X0_T = np.load(self.cache_dir / "earth_X0_T.npy", mmap_mode="r")
        self.earth_X0_sq_T = np.load(self.cache_dir / "earth_X0_sq_T.npy", mmap_mode="r")

        self.body_coords: Dict[str, np.ndarray] = {}
        self.body_keys: Dict[str, np.ndarray] = {}
        self.body_feats: Dict[str, np.ndarray] = {}
        self.body_grid_map: Dict[str, np.ndarray] = {}
        self.body_xyz: Dict[str, np.ndarray] = {}
        for body in ("mars", "moon"):
            self.body_coords[body] = np.load(self.cache_dir / f"{body}_coords.npy", mmap_mode="r")
            self.body_keys[body] = np.load(self.cache_dir / f"{body}_keys.npy", mmap_mode="r")
            self.body_feats[body] = np.load(self.cache_dir / f"{body}_features.npy", mmap_mode="r")
            self.body_grid_map[body] = np.load(self.cache_dir / f"{body}_grid_map.npy", mmap_mode="r")
            self.body_xyz[body] = np.load(self.cache_dir / f"{body}_xyz.npy", mmap_mode="r")

        self.earth_tfidf_csc = None
        self.body_tfidf_csr: Dict[str, Any] = {}
        if self.has_tfidf:
            self.earth_tfidf_csc = sparse.load_npz(self.cache_dir / "earth_tfidf_csc.npz")
            self.body_tfidf_csr["mars"] = sparse.load_npz(self.cache_dir / "mars_tfidf_csr.npz")
            self.body_tfidf_csr["moon"] = sparse.load_npz(self.cache_dir / "moon_tfidf_csr.npz")

        self._weight_vectors: Dict[str, np.ndarray] = {
            cat: self._build_weight_vector(cat)
            for cat in (*PRIORITY_CATEGORIES, ALL_CONDITIONS_CATEGORY)
        }

        self._cached_query = lru_cache(maxsize=lru_cache_size)(self._query_by_src_idx)

    def _is_cache_valid(self, sources: Dict[str, Path]) -> bool:
        meta_path = self.cache_dir / "meta.json"
        db_path = self.cache_dir / "lookup.db"
        if not meta_path.exists() or not db_path.exists():
            return False
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        if meta.get("schema_version") != CACHE_SCHEMA_VERSION:
            return False

        recorded = meta.get("sources", {})
        for body, p in sources.items():
            if not p.exists():
                continue
            st = p.stat()
            rec = recorded.get(body)
            if not rec or rec.get("size") != st.st_size or rec.get("mtime_ns") != st.st_mtime_ns:
                return False
        return True

    def get_cell_data(self, body: str, cell_key: str) -> Optional[Dict[str, Any]]:
        """Thread-safe O(1) fetch of the raw JSON object for any Earth/Mars/Moon cell."""
        if not self._db_path.exists():
            return None
        conn = getattr(self._db_local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(f"{self._db_path.as_uri()}?mode=ro", uri=True, check_same_thread=False)
            self._db_local.conn = conn
        row = conn.execute(
            "SELECT data FROM cells WHERE body = ? AND cell_key = ?",
            (body, cell_key),
        ).fetchone()
        if row is None:
            return None
        return _load_json_bytes(zlib.decompress(row[0]))

    @staticmethod
    def _build_weight_vector(priority_cat: str, priority_weight: float = 0.78) -> np.ndarray:
        w = np.zeros(N_FEATURES, dtype=np.float32)

        if priority_cat == ALL_CONDITIONS_CATEGORY:
            per_cat_w = 1.0 / len(FEATURE_GROUPS)
            for cols in FEATURE_GROUPS.values():
                per_col = per_cat_w / len(cols)
                for c in cols:
                    w[c] = per_col
            return w

        baseline = {
            "Terrain & Topography": 0.08,
            "Thermal & Extremes": 0.07,
            "Geology & Mineralogy": 0.04,
            "Water & Ice": 0.06,
        }
        for cat, cols in FEATURE_GROUPS.items():
            cat_w = priority_weight if cat == priority_cat else baseline.get(cat, 0.0)
            if cat_w > 0.0:
                per_col = cat_w / len(cols)
                for c in cols:
                    w[c] = per_col
        return w

    @staticmethod
    def _normalize_category(priority_category: Optional[str], body: str) -> str:
        if priority_category is None:
            return ALL_CONDITIONS_CATEGORY
        canonical = CATEGORY_ALIASES.get(priority_category.strip().lower())
        if canonical is None:
            raise ValueError(
                f"Unknown priority_category '{priority_category}'. "
                f"Expected None / 'All Conditions' or one of: {PRIORITY_CATEGORIES}"
            )
        if body == "moon" and canonical in MARS_ONLY_CATEGORIES:
            raise ValueError(
                f"Priority category '{canonical}' is Mars-only and not available for Moon."
            )
        return canonical

    def _lookup_source_idx(self, lon: float, lat: float, body: str) -> int:
        lon_n = _norm_lon(float(lon))
        lat_c = max(-90.0, min(90.0, float(lat)))

        lat_idx = max(-90, min(89, math.floor(lat_c)))
        lon_idx = max(-180, min(179, math.floor(lon_n)))
        idx = int(self.body_grid_map[body][lat_idx + 90, lon_idx + 180])
        if idx >= 0:
            return idx

        q_xyz = _latlon_to_xyz_single(lat_c, lon_n)
        return int(np.argmax(self.body_xyz[body] @ q_xyz))

    def _query_by_src_idx(
        self,
        body: str,
        src_idx: int,
        canon_cat: str,
        top_k: int,
        return_details: bool,
    ) -> Union[Tuple[float, float], Tuple[Dict[str, Any], ...]]:
        q = self.body_feats[body][src_idx]
        w = self._weight_vectors[canon_cat]

        active = np.flatnonzero((~np.isnan(q)) & (w > 0.0))
        if active.size == 0:
            raise ValueError("Selected planetary cell has no valid features for matching.")

        w_act = w[active]
        q_act = q[active]

        V_act = self.earth_V_T[active]
        B = np.vstack((w_act, w_act * (q_act * q_act)))
        denom_t1 = B @ V_act
        denom = denom_t1[0]

        mse = (-2.0 * w_act * q_act) @ self.earth_X0_T[active]
        mse += denom_t1[1]
        mse += w_act @ self.earth_X0_sq_T[active]

        np.maximum(mse, 0.0, out=mse)
        denom_safe = np.maximum(denom, 1e-6)
        mse /= denom_safe

        if canon_cat == ALL_CONDITIONS_CATEGORY:
            total_wq = float(w_act.sum())
            if total_wq > 0.0:
                overall_cov = denom / total_wq
                mse += np.where(overall_cov < 0.50, 5.0 * (1.0 - overall_cov), 0.35 * (1.0 - overall_cov))
        else:
            prio_cols = FEATURE_GROUPS[canon_cat]
            p_mask = np.isin(active, prio_cols)
            if p_mask.any():
                p_cols = active[p_mask]
                p_w = w_act[p_mask]
                p_max = float(p_w.sum())
                if p_max > 0.0:
                    prio_cov = (p_w @ self.earth_V_T[p_cols]) / p_max
                    mse += np.where(prio_cov < 0.35, 5.0 * (1.0 - prio_cov), 0.35 * (1.0 - prio_cov))

        if self.has_tfidf and canon_cat in ("Geology & Mineralogy", ALL_CONDITIONS_CATEGORY):
            q_tfidf = self.body_tfidf_csr[body][src_idx]
            if q_tfidf.nnz > 0:
                text_sim = np.asarray(
                    self.earth_tfidf_csc[:, q_tfidf.indices].dot(q_tfidf.data)
                ).ravel()
                boost = 0.35 if canon_cat == "Geology & Mineralogy" else 0.08
                mse -= boost * text_sim

        if top_k == 1 and not return_details:
            best_idx = int(np.argmin(mse))
            lon, lat = self.earth_coords[best_idx]
            return float(lon), float(lat)

        k = min(max(1, top_k), mse.shape[0])
        best_indices = np.argpartition(mse, k - 1)[:k]
        best_indices = best_indices[np.argsort(mse[best_indices])]

        if not return_details:
            lon, lat = self.earth_coords[best_indices[0]]
            return float(lon), float(lat)

        q_key = self.body_keys[body][src_idx].decode("utf-8", errors="ignore")
        q_lon, q_lat = self.body_coords[body][src_idx]
        results = []
        for idx in best_indices:
            e_lon, e_lat = self.earth_coords[idx]
            dist_val = float(mse[idx])
            results.append(
                {
                    "earth_longitude": float(e_lon),
                    "earth_latitude": float(e_lat),
                    "earth_key": self.earth_keys[idx].decode("utf-8", errors="ignore"),
                    "distance": dist_val,
                    "similarity_0_1": float(math.exp(-max(0.0, dist_val))),
                    "earth_geology_desc": self.earth_texts[idx].decode("utf-8", errors="ignore"),
                    "query_key": q_key,
                    "query_coord": (float(q_lon), float(q_lat)),
                    "priority_category": canon_cat,
                }
            )
        return tuple(results)

    def find_analogs(
        self,
        longitude_inp: float,
        latitude_inp: float,
        astronomical_body: str,
        priority_category: Optional[str] = None,
        top_k: int = 1,
        return_details: bool = False,
    ) -> Union[Tuple[float, float], List[Dict[str, Any]]]:
        body = astronomical_body.strip().lower()
        if body not in ("mars", "moon"):
            raise ValueError("astronomical_body must be 'moon' or 'mars'.")

        canon_cat = self._normalize_category(priority_category, body)
        src_idx = self._lookup_source_idx(longitude_inp, latitude_inp, body)
        res = self._cached_query(body, src_idx, canon_cat, int(top_k), bool(return_details))
        return list(res) if return_details else res


_MATCHER_LOCK = threading.Lock()
_DEFAULT_MATCHER: Optional[PlanetaryAnalogMatcher] = None


def init_matcher(
    earth_json_path: Union[str, Path] = "earth_0.25deg_lookup.json",
    mars_json_path: Union[str, Path] = "mars_1deg_lookup.json",
    moon_json_path: Union[str, Path] = "moon_1deg_lookup.json",
    cache_dir: Union[str, Path] = "analog_cache",
    auto_build_cache: bool = True,
) -> PlanetaryAnalogMatcher:
    global _DEFAULT_MATCHER
    with _MATCHER_LOCK:
        if _DEFAULT_MATCHER is None:
            _DEFAULT_MATCHER = PlanetaryAnalogMatcher(
                earth_json_path=earth_json_path,
                mars_json_path=mars_json_path,
                moon_json_path=moon_json_path,
                cache_dir=cache_dir,
                auto_build_cache=auto_build_cache,
            )
        return _DEFAULT_MATCHER


def find_analogs(
    longitude_inp: float,
    latitude_inp: float,
    astronomical_body: str,
    priority_category: Optional[str] = None,
    **kwargs,
) -> Union[Tuple[float, float], List[Dict[str, Any]]]:
    matcher = _DEFAULT_MATCHER or init_matcher()
    return matcher.find_analogs(
        longitude_inp=longitude_inp,
        latitude_inp=latitude_inp,
        astronomical_body=astronomical_body,
        priority_category=priority_category,
        **kwargs,
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        out = build_cache()
        print(f"Cache successfully built at: {out.resolve()}")