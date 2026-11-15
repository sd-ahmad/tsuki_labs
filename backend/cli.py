import argparse
import math
import time
from typing import List, Optional, Tuple

from analog_matcher import (
    ALL_CONDITIONS_CATEGORY,
    MARS_ONLY_CATEGORIES,
    PRIORITY_CATEGORIES,
    find_analogs,
    init_matcher,
)


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def maps_url(lon: float, lat: float) -> str:
    return f"https://www.google.com/maps?q={lat:.4f},{lon:.4f}&t=k"


# (name, body, lon, lat, category_or_None, expected_earth_region, ref_lon, ref_lat)
KNOWN_TEST_PAIRS: List[Tuple[str, str, float, float, Optional[str], str, float, float]] = [
    (
        "Jezero Crater - ALL CONDITIONS",
        "mars",
        77.58,
        18.38,
        None,
        "Hyper-arid desert / playa / plateau (Atacama / Qaidam / Sahara)",
        -70.01,
        -24.10,
    ),
    (
        "Gale Crater - ALL CONDITIONS",
        "mars",
        137.8,
        -5.4,
        None,
        "Arid sedimentary basin (Qaidam Basin / Atacama / Colorado Plateau)",
        94.45,
        37.27,
    ),
    (
        "Mare Tranquillitatis - ALL CONDITIONS",
        "moon",
        23.47,
        0.67,
        None,
        "Flat barren basaltic or desert plain (Iceland / Hawaii / Sahara)",
        -155.29,
        19.42,
    ),
    (
        "Mars North Polar Cap",
        "mars",
        -179.5,
        89.5,
        "Water & Ice",
        "East Antarctic / Greenland Ice Sheet",
        77.0,
        -78.0,
    ),
    (
        "Olympus Mons (Shield Volcano)",
        "mars",
        -133.8,
        18.65,
        "Atmospheric/Dust (MARS)",
        "High-altitude arid plateau / volcano (Tibetan Plateau / Andean Puna)",
        -68.54,
        -27.11,
    ),
    (
        "Valles Marineris (Deep Canyon)",
        "mars",
        -59.2,
        -13.9,
        "Terrain & Topography",
        "Steep arid canyon / high-relief gorge (Andes / Grand Canyon / Tibet)",
        -112.11,
        36.10,
    ),
    (
        "Arsia Mons Flank (Lava Caves)",
        "mars",
        -120.1,
        -8.3,
        "Subsurface/Caves (MARS)",
        "Volcanic basalt cave terrain (Lava Beds CA / Harrat / Canary Islands)",
        -121.52,
        41.76,
    ),
    (
        "Shackleton Crater (Lunar South Pole)",
        "moon",
        0.0,
        -89.5,
        "Thermal & Extremes",
        "McMurdo Dry Valleys / Antarctic Plateau",
        162.0,
        -77.5,
    ),
    (
        "Descartes Highlands (Apollo 16)",
        "moon",
        15.50,
        -8.97,
        "Terrain & Topography",
        "Barren rugged highlands (Andes / Transantarctic / Tibet)",
        -68.0,
        -22.0,
    ),
]


def run_benchmark_suite() -> None:
    print("\n=== Running Known Planetary-to-Earth Analog Test Suite ===\n")
    for name, body, lon, lat, cat, ref_region, ref_lon, ref_lat in KNOWN_TEST_PAIRS:
        t0 = time.perf_counter()
        matches = find_analogs(
            longitude_inp=lon,
            latitude_inp=lat,
            astronomical_body=body,
            priority_category=cat,
            top_k=3,
            return_details=True,
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        best = matches[0]
        b_lon, b_lat = best["earth_longitude"], best["earth_latitude"]
        q_lon, q_lat = best["query_coord"]
        dist_km = haversine_km(b_lon, b_lat, ref_lon, ref_lat)

        print(f"[{name}] ({body.upper()} lon={lon}, lat={lat} | {best['priority_category']})")
        print(f"  Snapped cell    : {best['query_key']} (lon={q_lon:.2f}, lat={q_lat:.2f})")
        print(f"  Expected region : {ref_region} (ref ~ {ref_lon:.2f}, {ref_lat:.2f})")
        print(
            f"  Best match      : lon={b_lon:.3f}, lat={b_lat:.3f} "
            f"| sim={best['similarity_0_1']:.3f} | {dt_ms:.2f} ms"
        )
        print(f"  Dist to ref pt  : {dist_km:,.0f} km | Map: {maps_url(b_lon, b_lat)}")
        if best["earth_geology_desc"]:
            print(f"  Earth geology   : {best['earth_geology_desc']}")
        print()


def interactive_loop() -> None:
    print("\n=== Interactive Planetary Analog Tester ===")
    print("Type 'q' at any prompt to quit.\n")

    while True:
        body = input("Astronomical body (mars / moon): ").strip().lower()
        if body in ("q", "quit", "exit"):
            break
        if body not in ("mars", "moon"):
            print("Invalid body. Enter 'mars' or 'moon'.\n")
            continue

        try:
            lon_s = input("Longitude (deg, e.g. -133.8 or 77.58): ").strip()
            if lon_s.lower() in ("q", "quit", "exit"):
                break
            lat_s = input("Latitude  (deg, e.g. 18.65 or -89.5): ").strip()
            if lat_s.lower() in ("q", "quit", "exit"):
                break
            lon, lat = float(lon_s), float(lat_s)
        except ValueError:
            print("Invalid coordinates. Please enter numeric values.\n")
            continue

        available = [
            c for c in PRIORITY_CATEGORIES
            if not (body == "moon" and c in MARS_ONLY_CATEGORIES)
        ]
        print("\nSelect preferred condition:")
        print(f"  0. No Priority Category ({ALL_CONDITIONS_CATEGORY}) [press Enter]")
        for i, c in enumerate(available, 1):
            print(f"  {i}. {c}")

        choice = input(f"Choice (0-{len(available)}, name, or Enter for All Conditions): ").strip()
        if choice.lower() in ("q", "quit", "exit"):
            break
        if choice == "" or choice == "0":
            cat: Optional[str] = None
        elif choice.isdigit() and 1 <= int(choice) <= len(available):
            cat = available[int(choice) - 1]
        else:
            cat = choice

        try:
            t0 = time.perf_counter()
            best_lon, best_lat = find_analogs(lon, lat, body, cat)
            top3 = find_analogs(lon, lat, body, cat, top_k=3, return_details=True)
            dt_ms = (time.perf_counter() - t0) * 1000.0
        except ValueError as e:
            print(f"Error: {e}\n")
            continue

        q_lon, q_lat = top3[0]["query_coord"]
        print(
            f"\nSnapped {body.upper()} cell: {top3[0]['query_key']} "
            f"(lon={q_lon:.2f}, lat={q_lat:.2f}) | Mode: {top3[0]['priority_category']}"
        )
        print(f"Optimal Earth Coordinates: lon={best_lon:.4f}, lat={best_lat:.4f} ({dt_ms:.2f} ms)")
        print(f"Satellite View: {maps_url(best_lon, best_lat)}")
        print("\nTop 3 Analog Candidates:")
        for rank, m in enumerate(top3, 1):
            print(
                f"  #{rank}: lon={m['earth_longitude']:.4f}, lat={m['earth_latitude']:.4f} "
                f"| sim={m['similarity_0_1']:.3f} | geo='{m['earth_geology_desc']}'"
            )
        print("-" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test PlanetaryAnalogMatcher interactively or via suite.")
    parser.add_argument("--suite", action="store_true", help="Run known Mars/Moon test pairs.")
    parser.add_argument("--earth", default="earth_0.25deg_lookup.json")
    parser.add_argument("--mars", default="mars_1deg_lookup.json")
    parser.add_argument("--moon", default="moon_1deg_lookup.json")
    args = parser.parse_args()

    t_init = time.perf_counter()
    init_matcher(
        earth_json_path=args.earth,
        mars_json_path=args.mars,
        moon_json_path=args.moon,
    )
    print(f"Matcher ready in {(time.perf_counter() - t_init):.2f}s")

    if args.suite:
        run_benchmark_suite()
    else:
        interactive_loop()