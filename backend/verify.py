import json
import math
from pathlib import Path
import numpy as np


def find_output_dir() -> Path:
    for p in [Path("output"), Path("back-end/output")]:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find 'output/' directory.")


def check_grid_and_schema(name: str, data: dict, is_mars: bool):
    assert len(data) == 64800, f"{name}: Expected 64800 blocks, got {len(data)}"

    # Verify every expected lat/lon key exists & coordinates match
    for lat_idx in range(-90, 90):
        for lon_idx in range(-180, 180):
            k = f"{lat_idx}_{lon_idx}"
            assert k in data, f"{name}: Missing key {k}"
            b = data[k]
            assert b["lat_center"] == lat_idx + 0.5, f"{name}: Bad lat_center at {k}"
            assert b["lon_center"] == lon_idx + 0.5, f"{name}: Bad lon_center at {k}"

            t = b["terrain"]
            if t["elev_mean_m"] is not None:
                assert t["elev_min_m"] <= t["elev_mean_m"] <= t["elev_max_m"], f"{name}: Elev order bad at {k}"
                assert abs((t["elev_max_m"] - t["elev_min_m"]) - t["relief_m"]) <= 0.25, f"{name}: Relief bad at {k}"
            if t["slope_mean_deg"] is not None:
                assert t["slope_mean_deg"] >= 0 and t["slope_p95_deg"] >= 0, f"{name}: Negative slope at {k}"

            th = b["thermal"]
            td, tn = th["temp_day_max_k"], th["temp_night_min_k"]
            if td is not None and tn is not None:
                assert td >= tn, f"{name}: Tmax < Tmin at {k}"
                assert abs((td - tn) - th["diurnal_swing_k"]) <= 0.25, f"{name}: Swing bad at {k}"

            mob = b["landing_mobility"]["mobility_rating_0_100"]
            if mob is not None:
                assert 0.0 <= mob <= 100.0, f"{name}: Mobility out of range at {k}"

            # Ensure zero NaNs/Infs leaked into JSON
            for sec, val in b.items():
                if isinstance(val, dict):
                    for fk, fv in val.items():
                        if isinstance(fv, float):
                            assert math.isfinite(fv), f"{name}: Non-finite {sec}.{fk} at {k}"

    if is_mars:
        assert sum(1 for v in data.values() if v["terrain"]["elev_mean_m"] is not None) == 64800, "Mars MOLA incomplete"
        assert sum(1 for v in data.values() if v["geology"]["unit_code"] is not None) == 64800, "Mars geology incomplete"
        assert sum(1 for v in data.values() if v["thermal"]["thermal_inertia_tiu"] is not None) == 64800, "Mars TI incomplete"
        assert sum(1 for v in data.values() if v["atmosphere_dust"]["dust_cover_index"] is not None) == 64800, "Mars DCI incomplete"
        assert sum(1 for v in data.values() if v["subsurface_caves"]["nearest_cave_km"] is not None) == 64800, "Mars caves incomplete"
        assert sum(1 for v in data.values() if v["water_ice"]["swim_ice_consistency"] is not None) == 43200, "Mars SWIM count != 43200"
        for elem in ["fe_wt_pct", "si_wt_pct", "k_wt_pct", "th_ppm"]:
            cnt = sum(1 for v in data.values() if v["geology"][elem] is not None)
            assert cnt >= 35000, f"Mars GRS {elem} too low ({cnt})"
        assert sum(1 for v in data.values() if v["water_ice"]["weh_wt_pct"] is not None) >= 35000, "Mars GRS WEH too low"
    else:
        assert sum(1 for v in data.values() if v["terrain"]["elev_mean_m"] is not None) == 64800, "Moon LOLA incomplete"
        assert sum(1 for v in data.values() if v["geology"]["unit_code"] is not None) == 64800, "Moon geology incomplete"
        assert sum(1 for v in data.values() if v["geology"]["unit_name"] is not None) == 64800, "Moon unit_name incomplete"
        assert sum(1 for v in data.values() if v["geology"]["unit_age"] is not None) == 64800, "Moon unit_age incomplete"
        assert sum(1 for v in data.values() if v["thermal"]["temp_day_max_k"] is not None) == 64800, "Moon Diviner Tmax incomplete"
        assert sum(1 for v in data.values() if v["thermal"]["temp_night_min_k"] is not None) == 64800, "Moon Diviner Tmin incomplete"
        assert sum(1 for v in data.values() if v["thermal"]["rock_abundance_frac"] is not None) == 43200, "Moon Rock Abund != 43200"
        for elem in ["feo_wt_pct", "tio2_wt_pct", "th_ppm", "k_wt_pct"]:
            cnt = sum(1 for v in data.values() if v["geology"][elem] is not None)
            assert cnt >= 60000, f"Moon LPGRS {elem} too low ({cnt})"

    print(f"[PASS] {name}: Grid, schema, finite values, and coverage assertions passed!")


def check_mars_landmarks(mars: dict):
    # Olympus Mons summit (18.65N, -133.8E)
    oly = mars["18_-134"]
    assert oly["terrain"]["elev_mean_m"] > 15000, f"Olympus Mons elev wrong: {oly['terrain']['elev_mean_m']}"
    assert oly["atmosphere_dust"]["surface_pressure_mbar"] < 2.0
    assert oly["landing_mobility"]["edl_elev_feasible"] is False

    # Hellas Planitia floor (-42.4S, 70.5E)
    hel = mars["-43_70"]
    assert hel["terrain"]["elev_mean_m"] < -5000, f"Hellas elev wrong: {hel['terrain']['elev_mean_m']}"

    # Jezero Crater (18.38N, 77.58E)
    jez = mars["18_77"]
    assert jez["terrain"]["elev_mean_m"] < -1500 and jez["landing_mobility"]["edl_elev_feasible"] is True
    assert jez["thermal"]["thermal_inertia_tiu"] > 200

    # Arabia Terra vs Southern Highlands (proves DCI is NOT flipped upside down)
    arabia_dci = mars["20_30"]["atmosphere_dust"]["dust_cover_index"]
    south_dci = mars["-21_30"]["atmosphere_dust"]["dust_cover_index"]
    syrtis_dci = mars["10_68"]["atmosphere_dust"]["dust_cover_index"]
    assert arabia_dci < 0.945 and south_dci > 0.960 and syrtis_dci > 0.960, (
        f"DCI orientation wrong! Arabia={arabia_dci}, South={south_dci}, Syrtis={syrtis_dci}"
    )

    # Arcadia Planitia buried ice (46.7N, -172E)
    arc = mars["46_-172"]
    assert arc["water_ice"]["swim_ice_consistency"] > 0.30, f"Arcadia SWIM wrong: {arc['water_ice']}"

    # Arsia Mons cave zone (-9S, -121E)
    ars = mars["-9_-121"]
    assert ars["subsurface_caves"]["nearest_cave_km"] < 120.0, f"Arsia cave dist wrong: {ars['subsurface_caves']}"

    # South Pole (-85S, 0E)
    sp = mars["-85_0"]
    assert sp["water_ice"]["polar_ice_flag"] is True and sp["water_ice"]["swim_ice_consistency"] is None

    print("[PASS] MARS: All landmark orientation & physical calibration checks passed!")


def check_moon_landmarks(moon: dict):
    # Apollo 11 (0.674N, 23.473E)
    a11 = moon["0_23"]
    assert a11["geology"]["unit_code"] == "Im2", f"Apollo 11 unit wrong: {a11['geology']}"
    assert a11["geology"]["feo_wt_pct"] > 10.0 and a11["geology"]["tio2_wt_pct"] > 3.0
    assert a11["terrain"]["elev_mean_m"] < -1000
    assert a11["thermal"]["temp_day_max_k"] > 380 and a11["thermal"]["temp_night_min_k"] < 105
    assert a11["thermal"]["rock_abundance_frac"] < 0.015
    assert a11["landing_mobility"]["earth_los_visible"] is True

    # Tycho Crater (-43.31S, -11.36W) - proves Rock Abund 180° roll & thermal retention
    tycho = moon["-44_-12"]
    assert tycho["geology"]["unit_code"] == "Cc", f"Tycho unit wrong: {tycho['geology']}"
    assert tycho["geology"]["feo_wt_pct"] < 6.0
    assert tycho["thermal"]["rock_abundance_frac"] > 0.04, f"Tycho rock abund too low: {tycho['thermal']}"
    assert tycho["thermal"]["rock_abundance_frac"] > a11["thermal"]["rock_abundance_frac"] * 5
    assert tycho["thermal"]["temp_night_min_k"] > a11["thermal"]["temp_night_min_k"]

    # Aristarchus Plateau KREEP hotspot (23.73N, -47.49W) - proves LPGRS alignment
    ari = moon["23_-48"]
    assert ari["geology"]["th_ppm"] > 5.0, f"Aristarchus Th too low: {ari['geology']}"

    # Tsiolkovskiy Crater Far Side (-20.4S, 129.1E)
    tsi = moon["-21_129"]
    assert tsi["landing_mobility"]["earth_los_visible"] is False

    # Shackleton / South Pole (-89.5S, 0E)
    sp = moon["-90_0"]
    assert sp["water_ice"]["polar_psr_zone"] is True
    assert sp["thermal"]["temp_night_min_k"] < 60.0
    assert sp["thermal"]["rock_abundance_frac"] is None

    print("[PASS] MOON: All landmark orientation & physical calibration checks passed!")


def print_ml_audit(name: str, data: dict, is_mars: bool):
    print(f"\n{'=' * 95}")
    print(f"FEATURE SUMMARY & ML READINESS: {name}")
    print(f"{'=' * 95}")
    cols = {}
    for b in data.values():
        for sec, val in b.items():
            if sec in ("lat_center", "lon_center") or val is None:
                continue
            if isinstance(val, dict):
                for k, v in val.items():
                    cols.setdefault(f"{sec}.{k}", []).append(v)

    print(f"{'Feature':<38} {'Nulls':>7} {'Null%':>6} {'Zeros':>7} {'Min':>9} {'Median':>9} {'P95':>9} {'Max':>9}")
    print("-" * 95)
    for col, vals in cols.items():
        nulls = sum(1 for v in vals if v is None)
        non_null = [v for v in vals if v is not None]
        if non_null and isinstance(non_null[0], bool):
            print(f"{col:<38} {nulls:>7} {100*nulls/64800:>5.1f}%   [bool: True={sum(non_null)}, False={len(non_null)-sum(non_null)}]")
        elif non_null and isinstance(non_null[0], str):
            print(f"{col:<38} {nulls:>7} {100*nulls/64800:>5.1f}%   [str: {len(set(non_null))} unique]")
        else:
            arr = np.array(non_null, dtype=np.float64)
            print(
                f"{col:<38} {nulls:>7} {100*nulls/64800:>5.1f}% {int(np.sum(arr == 0)):>7} "
                f"{arr.min():>9.2f} {np.percentile(arr, 50):>9.2f} {np.percentile(arr, 95):>9.2f} {arr.max():>9.2f}"
            )

    if is_mars:
        ti_zero = sum(1 for b in data.values() if b["thermal"]["thermal_inertia_tiu"] == 0)
        dci_floor = sum(1 for b in data.values() if b["atmosphere_dust"]["dust_cover_index"] == 0.85)
        tmin_floor = sum(1 for b in data.values() if b["thermal"]["temp_night_min_k"] == 130.0)
        print(f"\n[ML Notes - Mars] TI==0 sentinels: {ti_zero} | DCI==0.85 ice clamps: {dci_floor} | Tmin==130.0 clamps: {tmin_floor}")
    else:
        rk = [b["thermal"]["rock_abundance_frac"] for b in data.values() if b["thermal"]["rock_abundance_frac"] is not None]
        print(f"\n[ML Notes - Moon] Rock abundance > 1.0: {sum(1 for x in rk if x > 1.0)} | == 0.0: {sum(1 for x in rk if x == 0.0)}")


def main():
    out = find_output_dir()
    print(f"Verifying files in: {out.resolve()}\n")

    mars = json.load(open(out / "mars_1deg_lookup.json"))
    check_grid_and_schema("MARS", mars, is_mars=True)
    check_mars_landmarks(mars)
    print_ml_audit("MARS", mars, is_mars=True)

    print()
    moon = json.load(open(out / "moon_1deg_lookup.json"))
    check_grid_and_schema("MOON", moon, is_mars=False)
    check_moon_landmarks(moon)
    print_ml_audit("MOON", moon, is_mars=False)

    print("\nALL CHECKS PASSED — BOTH LOOKUP FILES ARE 100% VERIFIED!")


if __name__ == "__main__":
    main()