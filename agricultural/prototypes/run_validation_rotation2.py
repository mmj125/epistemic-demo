"""
Validation harness for the CornSilageSoyWheat rotation (soybean, winter
wheat, silage corn). See cycles_engine_validate.py's module docstring and
QUESTIONS_FOR_DEVS.md for what's disclosed vs. approximated vs. still
genuinely unresolved. Requires the same local Cycles v1.4.4 reference data
as run_validation.py (see that file / REFERENCE_DATA_DIR).
"""
import math
import statistics
import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from cycles_engine_validate import (
    REFERENCE_DATA_DIR, saxton_rawls, OM_FROM_SOC, simulate_season, CORN_CANOPY_SHAPE,
)

LAT = 40.6875

SOIL_LAYERS_RAW = [
    dict(thick=0.05, clay=21, sand=15, soc=1.74), dict(thick=0.05, clay=21, sand=15, soc=1.74),
    dict(thick=0.10, clay=21, sand=15, soc=1.74), dict(thick=0.20, clay=37, sand=17, soc=0.27),
    dict(thick=0.20, clay=37, sand=17, soc=0.27), dict(thick=0.20, clay=55, sand=4, soc=0.17),
    dict(thick=0.20, clay=55, sand=4, soc=0.17), dict(thick=0.20, clay=55, sand=4, soc=0.17),
    dict(thick=0.20, clay=55, sand=4, soc=0.17),
]


def make_layers():
    layers = []
    for L in SOIL_LAYERS_RAW:
        hyd = saxton_rawls(L["sand"], L["clay"], L["soc"] * OM_FROM_SOC)
        layers.append(dict(thick=L["thick"], fc=hyd["fc"], pwp=hyd["pwp"], sat=hyd["sat"], theta=hyd["fc"]))
    return layers


SOYBEAN = dict(tt_maturity=2250, flowering_tt=1250, base_t=5, opt_t=28, max_t=43,
               rue=1.3, wue=4.5, hi_x=0.4, hi_o=0.15, hi_slope=1.0, fsti=0.45, fstf=0.95,
               kc=1.0, eix=1.0, tr_min_t=3.0, tr_threshold_t=15.0, lat_deg=LAT,
               make_layers=make_layers, calibration_factor=1.116)

WHEAT = dict(tt_maturity=1800, flowering_tt=1250, base_t=0, opt_t=20, max_t=35,
             rue=1.6, wue=6.0, hi_x=0.52, hi_o=0.2, hi_slope=1.0, fsti=0.45, fstf=0.95,
             kc=1.0, eix=1.0, tr_min_t=0.0, tr_threshold_t=12.0, lat_deg=LAT,
             make_layers=make_layers, calibration_factor=0.716,
             canopy_shape=(5, -14, -15, 16))  # refit from real data -- see QUESTIONS_FOR_DEVS.md item 5;
                                               # fixes level bias, does NOT fix wheat's weak correlation

CORN_SILAGE = dict(tt_maturity=1800, flowering_tt=1000, base_t=6, opt_t=28, max_t=46,
                    rue=2.2, wue=8.7, hi_x=0.8, hi_o=0.15, hi_slope=1.0, fsti=0.45, fstf=0.95,
                    kc=1.1, eix=1.0, tr_min_t=3.0, tr_threshold_t=15.0, lat_deg=LAT,
                    make_layers=make_layers, forage_fraction=0.95, calibration_factor=0.806,
                    canopy_shape=CORN_CANOPY_SHAPE)  # real fix (thermal time, canopy shape, harvest
                    # date, forage ratio all individually verified accurate) does NOT move correlation
                    # (0.503 -> 0.501) -- see QUESTIONS_FOR_DEVS.md, this is a distinct, still-open item


def load_weather():
    weather_by_yd, weather_flat = {}, []
    with open(os.path.join(REFERENCE_DATA_DIR, "input/RockSprings.weather")) as f:
        for line in f.readlines()[5:]:
            p = line.split()
            if len(p) < 9:
                continue
            y, doy = int(p[0]), int(p[1])
            row = dict(doy=doy, pp=float(p[2]), tx=float(p[3]), tn=float(p[4]),
                       solar=float(p[5]), rhx=float(p[6]), rhn=float(p[7]), wind=float(p[8]))
            weather_by_yd[(y, doy)] = row
            weather_flat.append((y, doy, row))
    return weather_by_yd, weather_flat


def real_harvest(rotation, crop_name):
    path = os.path.join(REFERENCE_DATA_DIR, f"output/{rotation}/harvest.txt")
    out = {}
    with open(path) as f:
        for line in f.readlines()[2:]:
            parts = line.split("\t")
            if len(parts) < 8 or parts[1].strip() != crop_name:
                continue
            harvest_year = int(parts[0][:4])
            plant_date = parts[2].strip()
            py, pm, pd = int(plant_date[:4]), int(plant_date[5:7]), int(plant_date[8:10])
            plant_doy = datetime.date(py, pm, pd).timetuple().tm_yday
            out[harvest_year] = dict(plant_year=py, plant_doy=plant_doy, grain=float(parts[5]), forage=float(parts[6]))
    return out


def validate(rotation, crop_name, crop_params, label, metric="grain", harvest_ttf=1.0):
    _, weather_flat = load_weather()
    flat_index = {(y, d): i for i, (y, d, r) in enumerate(weather_flat)}
    real = real_harvest(rotation, crop_name)
    if not real:
        print(f"\n=== {label}: no reference data found under {REFERENCE_DATA_DIR} ===")
        return

    my_yield = {}
    for hyear, info in real.items():
        start = flat_index.get((info["plant_year"], info["plant_doy"]))
        if start is None:
            continue
        rows = [r for (_, _, r) in weather_flat[start:start + 400]]
        result = simulate_season(rows, crop_params, harvest_ttf=harvest_ttf)
        my_yield[hyear] = result[metric]

    years = sorted(my_yield)
    rv = [real[y][metric] for y in years]
    mv = [my_yield[y] for y in years]
    mr, mm = statistics.mean(rv), statistics.mean(mv)
    cov = sum((rv[i] - mr) * (mv[i] - mm) for i in range(len(rv)))
    sr = math.sqrt(sum((x - mr) ** 2 for x in rv))
    sm = math.sqrt(sum((x - mm) ** 2 for x in mv))
    corr = cov / (sr * sm) if sr and sm else float("nan")
    mae = statistics.mean(abs(rv[i] - mv[i]) for i in range(len(years)))
    print(f"\n=== {label} ({len(years)} harvests) ===")
    print(f"Real mean: {mr:.2f} Mg/ha, model mean: {mm:.2f} Mg/ha")
    print(f"Mean absolute error: {mae:.2f} Mg/ha, correlation: {corr:.3f}")


if __name__ == "__main__":
    validate("CornSilageSoyWheat", "SoybeanMG.5", SOYBEAN, "Soybean")
    validate("CornSilageSoyWheat", "WinterWheat", WHEAT, "Winter Wheat")
    validate("CornSilageSoyWheat", "CornSilageRM.90", CORN_SILAGE, "Silage Corn", metric="forage", harvest_ttf=0.85)
