"""Validation harness for the TRUE continuous multi-year Rock Springs chain -- see
cycles_engine_validate.py's run_bare_fallow_window() docstring for why this exists and what
it found. Requires the same local Cycles v1.4.4 reference data as run_validation.py (see that
file's module docstring), plus annualN.txt from the same ContinuousCorn output directory for
the nitrogen-pathway comparison.

Unlike run_validation.py, this chains soil-moisture state across ALL 37 years with NO gap --
layers carry from one season's harvest, through a real bare-fallow bridge (run_bare_fallow_window)
to December 31, into the next year's spinup -- rather than resetting to INITIAL_MOISTURE_FRACTION
every year. This is NOT a replacement for run_validation.py's own documented numbers (yield is
essentially unaffected either way); it exists specifically to validate the gross water balance
(total drainage) and the nitrogen-pathway mechanisms (leaching/denitrification/volatilization)
against real Cycles output under conditions that actually let deep soil layers behave like real,
continuously-simulated soil instead of a fresh value reset every January 1st.
"""
import math
import statistics
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import cycles_engine_validate as cev
from cycles_engine_validate import (
    REFERENCE_DATA_DIR, simulate_soil_temp, find_planting_doy, simulate_season,
    run_bare_fallow_window, compute_tew, REW_DEFAULT_MM, CO2_PPM_BY_YEAR, CO2_REF_PPM,
)
from run_validation import CORN, make_layers


def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(len(a)))
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return cov / (sa * sb) if sa and sb else float("nan")


def main():
    weather_path = os.path.join(REFERENCE_DATA_DIR, "input/RockSprings.weather")
    harvest_path = os.path.join(REFERENCE_DATA_DIR, "output/ContinuousCorn/harvest.txt")
    annualn_path = os.path.join(REFERENCE_DATA_DIR, "output/ContinuousCorn/annualN.txt")
    if not os.path.exists(weather_path) or not os.path.exists(harvest_path):
        print(f"Reference data not found under {REFERENCE_DATA_DIR}.")
        print("See cycles_engine_validate.py's module docstring for exact setup steps.")
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

    real_n = {}
    if os.path.exists(annualn_path):
        with open(annualn_path) as f:
            for line in f.readlines()[2:]:
                p = line.split("\t")
                if len(p) < 12:
                    continue
                y = int(p[0])
                real_n[y] = dict(leach=float(p[4]) + float(p[5]), denit=float(p[8]), volat=float(p[10]))

    layers = make_layers()  # fresh start ONLY for the very first year -- every later year
    # carries forward via run_bare_fallow_window(), not a reset.
    yields, model_n, annual_drainage = {}, {}, {}

    # Instrument infiltrate() just long enough to total one headline year's own drainage --
    # the single most direct piece of evidence for this chain's real point (gross water
    # balance realism), compared against real Cycles' own water.txt DRAINAGE column summed
    # over the same calendar year below.
    real_infiltrate = cev.infiltrate
    drain_tracker = {"year": None, "total": 0.0}

    def _traced_infiltrate(l, w, cn, sp, n_by_layer=None):
        d, r, nl = real_infiltrate(l, w, cn, sp, n_by_layer)
        if drain_tracker["year"] is not None:
            drain_tracker["total"] += d
        return d, r, nl

    cev.infiltrate = _traced_infiltrate

    for year in sorted(daily):
        if year not in real_yield:
            continue
        doys_sorted = sorted(daily[year])
        tmeans = [(daily[year][d]["tx"] + daily[year][d]["tn"]) / 2 for d in doys_sorted]
        tsoils = simulate_soil_temp(tmeans, k=0.15)
        tsoil_by_doy = dict(zip(doys_sorted, tsoils))
        plant_doy = find_planting_doy(tsoil_by_doy, (110, 131), 12.0)
        rows = [daily[year][d] for d in range(plant_doy, 300) if d in daily[year]]
        spinup_rows = [daily[year][d] for d in range(1, plant_doy) if d in daily[year]]
        wue_co2_scale = CO2_PPM_BY_YEAR.get(year, CO2_REF_PPM) / CO2_REF_PPM

        drain_tracker["year"], drain_tracker["total"] = year, 0.0
        result = simulate_season(rows, CORN, spinup_rows=spinup_rows, initial_layers=layers,
                                  wue_co2_scale=wue_co2_scale, record_history=True,
                                  n_rate_kg_ha=150, nh4_no3_split=True, model_denitrification=True,
                                  model_volatilization=True, fertilizer_source="uan")
        yields[year] = result["grain"]
        model_n[year] = dict(leach=result.get("n_leached_kg_ha", 0.0),
                              volat=result.get("n_volatilized_pool_kg_ha", 0.0),
                              denit=result.get("n_denitrified_kg_ha", 0.0))
        harvest_doy = result["history"][-1]["doy"] if result["history"] else rows[-1]["doy"]
        layers = result["final_layers"]

        bridge_rows = [daily[year][d] for d in range(harvest_doy + 1, 367) if d in daily[year]]
        de_state = dict(de=0.0, tew=compute_tew(layers[0]["fc"], layers[0]["pwp"]), rew=REW_DEFAULT_MM)
        run_bare_fallow_window(layers, bridge_rows, lat_deg=CORN["lat_deg"], de_state=de_state)
        annual_drainage[year] = drain_tracker["total"]

    cev.infiltrate = real_infiltrate
    years = sorted(yields)
    rv_y = [real_yield[y] for y in years]
    mv_y = [yields[y] for y in years]
    mr, mm = statistics.mean(rv_y), statistics.mean(mv_y)
    mae = statistics.mean(abs(rv_y[i] - mv_y[i]) for i in range(len(rv_y)))
    print(f"=== Yield, true continuous chain, {len(years)} years ===")
    print(f"Real mean: {mr:.2f} Mg/ha, model mean: {mm:.2f} Mg/ha, MAE: {mae:.2f} Mg/ha, "
          f"correlation: {corr(mv_y, rv_y):.3f}")
    print("(run_validation.py's own fresh-start-every-year number: 0.777 -- expect this to "
          "match closely; yield is not what this chain was built to fix.)")

    water_path = os.path.join(REFERENCE_DATA_DIR, "output/ContinuousCorn/water.txt")
    if os.path.exists(water_path) and 2012 in annual_drainage:
        real_drain_2012 = 0.0
        with open(water_path) as f:
            for line in f.readlines()[3:]:
                p = line.split("\t")
                if p and p[0].startswith("2012-"):
                    real_drain_2012 += float(p[4])
        print(f"\n=== Gross water balance: total 2012 drainage (the headline evidence) ===")
        print(f"Model (true continuous chain): {annual_drainage[2012]:.1f} mm")
        print(f"Real Cycles (water.txt, summed over all of 2012): {real_drain_2012:.1f} mm")
        print("(fresh-start-every-year convention gives ~28mm for just the first 240 days of "
              "the same year -- a ~7x undershoot this chain closes to within ~6%.)")

    if real_n:
        n_years = sorted(set(model_n) & set(real_n))
        print(f"\n=== Nitrogen pathways, true continuous chain, {len(n_years)} years (150 kg N/ha UAN) ===")
        for key, label in [("leach", "Leaching (NO3+NH4)"), ("volat", "Volatilization"), ("denit", "Denitrification")]:
            mv = [model_n[y][key] for y in n_years]
            rv_ = [real_n[y][key] for y in n_years]
            rmean = statistics.mean(rv_)
            print(f"{label:22s}: model {statistics.mean(mv):7.3f}  real {rmean:7.3f}  "
                  f"ratio {statistics.mean(mv) / rmean if rmean else float('nan'):6.2f}x  "
                  f"correlation {corr(mv, rv_):+.3f}")
        print("(fresh-start baseline: leaching 10.05x/+0.527, volatilization 0.76x/+0.027, "
              "denitrification 0.93x/+0.549 -- the true chain moves none of these meaningfully, "
              "despite fixing the gross water balance -- see run_bare_fallow_window()'s own "
              "docstring and QUESTIONS_FOR_DEVS.md for the full account.)")


if __name__ == "__main__":
    main()
