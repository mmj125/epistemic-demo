"""
Validation harness for cycles_engine_validate.py. Requires a local copy of
Cycles v1.4.4's sample files plus a real run's output (see that file's
module docstring for exactly what's needed and why they aren't bundled
in this repo). Not itself needed to use the engine -- this just reproduces
the validation numbers documented there.
"""
import math
import statistics
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from cycles_engine_validate import (
    REFERENCE_DATA_DIR, saxton_rawls, OM_FROM_SOC, simulate_soil_temp,
    find_planting_doy, simulate_season, CORN_CANOPY_SHAPE,
)

CORN = dict(
    tt_maturity=1800, flowering_tt=1000, base_t=6, opt_t=28, max_t=46,
    rue=2.2, wue=8.7, hi_x=0.8, hi_o=0.15, hi_slope=1.0, fsti=0.45, fstf=0.95,
    calibration_factor=0.841,  # residual after the AG-biomass fix + corn-specific canopy refit
    canopy_shape=CORN_CANOPY_SHAPE,
    kc=1.1, eix=1.0, tr_min_t=3.0, tr_threshold_t=15.0, lat_deg=40.6875,
)

SOIL_LAYERS_RAW = [
    dict(thick=0.05, clay=21, sand=15, soc=1.74),
    dict(thick=0.05, clay=21, sand=15, soc=1.74),
    dict(thick=0.10, clay=21, sand=15, soc=1.74),
    dict(thick=0.20, clay=37, sand=17, soc=0.27),
    dict(thick=0.20, clay=37, sand=17, soc=0.27),
    dict(thick=0.20, clay=55, sand=4, soc=0.17),
    dict(thick=0.20, clay=55, sand=4, soc=0.17),
    dict(thick=0.20, clay=55, sand=4, soc=0.17),
    dict(thick=0.20, clay=55, sand=4, soc=0.17),
]


def make_layers():
    layers = []
    for L in SOIL_LAYERS_RAW:
        om = L["soc"] * OM_FROM_SOC
        hyd = saxton_rawls(L["sand"], L["clay"], om)
        layers.append(dict(thick=L["thick"], fc=hyd["fc"], pwp=hyd["pwp"], sat=hyd["sat"], theta=hyd["fc"]))
    return layers


CORN["make_layers"] = make_layers


def main():
    weather_path = os.path.join(REFERENCE_DATA_DIR, "input/RockSprings.weather")
    harvest_path = os.path.join(REFERENCE_DATA_DIR, "output/ContinuousCorn/harvest.txt")
    if not os.path.exists(weather_path) or not os.path.exists(harvest_path):
        print(f"Reference data not found under {REFERENCE_DATA_DIR}.")
        print("Download Cycles v1.4.4 and run the ContinuousCorn sample first -- see")
        print("cycles_engine_validate.py's module docstring for exact steps.")
        return

    daily = {}
    with open(weather_path) as f:
        for line in f.readlines()[5:]:
            p = line.split()
            if len(p) < 9:
                continue
            y, doy = int(p[0]), int(p[1])
            daily.setdefault(y, {})[doy] = dict(doy=doy, pp=float(p[2]), tx=float(p[3]), tn=float(p[4]),
                                                 solar=float(p[5]), rhx=float(p[6]), rhn=float(p[7]), wind=float(p[8]))

    real_yield = {}
    with open(harvest_path) as f:
        for line in f.readlines()[2:]:
            parts = line.split("\t")
            if len(parts) < 6:
                continue
            real_yield[int(parts[0][:4])] = float(parts[5])

    results = {}
    for year in sorted(daily):
        if year not in real_yield:
            continue
        doys_sorted = sorted(daily[year])
        tmeans = [(daily[year][d]["tx"] + daily[year][d]["tn"]) / 2 for d in doys_sorted]
        tsoils = simulate_soil_temp(tmeans, k=0.15)
        tsoil_by_doy = dict(zip(doys_sorted, tsoils))
        plant_doy = find_planting_doy(tsoil_by_doy, (110, 131), 12.0)
        rows = [daily[year][d] for d in range(plant_doy, 300) if d in daily[year]]
        result = simulate_season(rows, CORN)
        results[year] = result["grain"]

    years = sorted(results)
    rv = [real_yield[y] for y in years]
    mv = [results[y] for y in years]
    mr, mm = statistics.mean(rv), statistics.mean(mv)
    cov = sum((rv[i] - mr) * (mv[i] - mm) for i in range(len(rv)))
    sr = math.sqrt(sum((x - mr) ** 2 for x in rv))
    sm = math.sqrt(sum((x - mm) ** 2 for x in mv))
    corr = cov / (sr * sm) if sr and sm else float("nan")
    mae = statistics.mean(abs(rv[i] - mv[i]) for i in range(len(rv)))

    print(f"Years validated: {len(years)}")
    print(f"Real mean yield: {mr:.2f} Mg/ha, model mean: {mm:.2f} Mg/ha")
    print(f"Mean absolute error: {mae:.2f} Mg/ha")
    print(f"Year-to-year correlation: {corr:.3f}")


if __name__ == "__main__":
    main()
