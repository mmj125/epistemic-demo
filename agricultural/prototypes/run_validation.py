"""
Validation harness for rhizo_engine.py. Requires a local copy of
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
from rhizo_engine import (
    REFERENCE_DATA_DIR, saxton_rawls, OM_FROM_SOC, simulate_soil_temp,
    find_planting_doy, simulate_season, CORN_CANOPY_SHAPE, INITIAL_MOISTURE_FRACTION,
    CO2_PPM_BY_YEAR, CO2_REF_PPM,
)

CORN = dict(
    n_crit_lemaire=(3.4, 0.37), n_demand_scale=1.0, n_stress_n0=0.2, n_uptake_gj=True, weps_k=0.01, wue_co2_exp=0.45, rue_co2_exp=0.0, residue_grain_n=0.70,   # Lemaire et al. 2008 critical curve and linear NNI growth response (class B), 2026-10-26
    senes_delay=0.12, senes_k=1.0,   # 2026-10-26 senescence law fitted to Mead LAI (class O, plan 2026-10-26)
    # 2026-10-17 corn N model built only from measured Cycles pieces (ENGINE_REBUILD_PLAN.md, uptake-limit entry): root retention from the exact 5/3 root input, marginal N concentration 0.75 of the
    # engine's critical-curve slope (x0.88 of the old scale), Cycles' aboveground N stress law (REFIT_PLAN row 14b), uptake about 3% of the mineral pool per day.
    root_retained_frac=0.6, n_demand_ref=True, n_stress_ag_basis=True, n_uptake_rate=0.03,
    c1_water=True,  # 2026-10-15 c1 water-regime package (REFIT_PLAN rows 39-41)
    tt_maturity=1800, flowering_tt=1000, base_t=6, opt_t=28, max_t=46,
    rue=2.2, wue=8.7, hi_x=0.8, hi_o=0.15, hi_slope=1.3077, fsti=0.45, fstf=0.95,
    calibration_factor=1.0,  # row 54: no calibration at the base. 0.8924 (row 50 re-centering, was 1.026) was a Rock Springs artifact that the regional grain factor then undid at other sites (mean g 1.12); that factor is now carried inside regional_params.G_REBASE so tile-site predictions are unchanged
    #  # 2026-10-13 re-centered after the measured harvest-index law (hi_x 0.760, hi_o 0.151, slope 1.479, fitted on 518 Cycles corn seasons, rms 0.0034); was 1.0916 with the old 0.8/0.15/1.0
    #  # 2026-10-08 multi-site recalibration: rue x1.06 (2.2 -> 2.332) with this factor x1.05 (1.0944 -> 1.1491), fitted on the 16-site N=150/N=400 table against native Cycles on identical inputs (N150 grain MAE 1.34 -> 1.10, N400 1.46 -> 1.06). The Rock Springs sample mean (10.56) is no longer matched exactly; the multi-site table is the headline. Previously 1.0944, re-derived 2026-10-01 for the real CO2-WUE-scaling mechanism
    # (wue_co2_scale, see simulate_season()'s own docstring) -- correlation moved 0.691->0.777
    # from that mechanism alone; previous value 1.1076, re-derived the same day for the real
    # cold-kill mechanism (see threshold_temp_cold_damage below) -- itself replacing 1.0977,
    # re-derived 2026-09-30 for the
    # CORN_CANOPY_SHAPE late-senescence refit (see that constant's own comment in
    # rhizo_engine.py), itself re-derived the same day for the real f_G harvest-index fix
    # (Kemanian et al. 2007) -- see rhizo_engine.py's own HI-computation docstring.
    # Previous value 0.8490, residual after the AG-biomass fix + corn-specific canopy refit +
    # the 2026-09-23 TTF50_SHOOT_PARTITION refit + the emergence-gate fix + the cold-temperature
    # radiation-growth reduction + the NET_GROWTH_FRACTION post-limitation growth-conversion fix +
    # the 2026-09-24 curve-number/f_wc swap (real Eq SI.5-SI.7, see retention_param_mm()) + the
    # 2026-09-25 hydraulic-conductance water-stress mechanism (campbell_water_uptake(), replacing
    # root_zone_availability()/water_stress_response() as the primary path -- see lwp_stress_onset/
    # lwp_wilting_point below); re-derived to keep the mean yield matching real output exactly,
    # same as every prior update. Correlation moved 0.550 -> 0.527 from the water-mechanism switch
    # alone (this recalibration only fixes the mean, doesn't touch correlation, as always) -- see
    # MECHANISM_LOG.md and CLAUDE.md for the full before/after account across all four crops
    # plus the Kansas benchmark, and why this was kept despite the Rock Springs correlation cost.
    canopy_shape=CORN_CANOPY_SHAPE,
    canopy_shape_faithful=(6.04, -20.51, -14.95, 14.57), eix_faithful=0.951, ngf_faithful=1.0,  # 2026-10-18 measured on Cycles' unstressed corn days (14 sites, rms 0.0022); see AUDIT_PAPER_SI_2026-10-18.md and CANOPY_FAITHFUL
    kc=1.1, eix=1.0, tr_min_t=3.0, tr_threshold_t=15.0, lat_deg=40.6875,
    n_max_conc=0.055, n_dilution_slope=0.4, legume=False,  # real GenericCrops.crop values, corn is not a legume
    n_min_conc=0.002,  # real GenericCrops.crop N_MIN_CONCENTRATION_STRAW (0.2%), added 2026-09-25
    # for the day-by-day concentration-tracked N-stress mechanism -- see simulate_season()'s
    # own comment above canopy_n_kg_ha in rhizo_engine.py. Never triggers on this
    # crop's own default (n_rate_kg_ha=None) validation path.
    depletion_fraction=0.55,  # real FAO-56 Table 22 value for maize, field (grain)
    tr_max_mm_day=10,  # real GenericCrops.crop TRANSPIRATION_MAX (CornRM.90); never triggers at
    # Rock Springs (TRp maxes out ~7.4mm/day across the full record) but real and disclosed
    root_max_m=2.0,  # real GenericCrops.crop MAXIMUM_ROOTING_DEPTH (CornRM.90); previously every
    # crop shared a hardcoded 1.4m default regardless of species -- a real, ignored difference
    tt_emergence=65,  # real GenericCrops.crop THERMAL_TIME_TO_EMERGENCE (CornRM.90); real Cycles'
    # own daily output shows exactly zero biomass in a PRE_EMERGENCE stage before this point, not
    # a smoothly-ramping small value -- a genuine, if tiny, discrepancy this now closes
    lwp_stress_onset=-1100, lwp_wilting_point=-2000,  # real GenericCrops.crop LWP_STRESS_ONSET/
    # LWP_WILTING_POINT (CornRM.90, J/kg), added 2026-09-25 for the real hydraulic-conductance-
    # based transpiration/water-stress mechanism (campbell_water_uptake(), see
    # rhizo_engine.py) -- presence of both fields (plus the already-real
    # tr_max_mm_day above) is what selects that mechanism over the older, superseded
    # depletion_fraction/root_zone_availability fallback for this crop.
    threshold_temp_cold_damage=3,  # real GenericCrops.crop THRESHOLD_TEMPERATURE_FOR_COLD_DAMAGE
    # (CornRM.90), added 2026-10-01 for the real cold-kill mechanism -- see
    # rhizo_engine.py's own comment at the kill check for the full account.
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
        layers.append(dict(thick=L["thick"], fc=hyd["fc"], pwp=hyd["pwp"], sat=hyd["sat"],
                            theta=hyd["pwp"] + INITIAL_MOISTURE_FRACTION * (hyd["fc"] - hyd["pwp"]),
                            ksat_mm_day=hyd["ksat_mm_day"], psi_e_kpa=hyd["psi_e_kpa"], B=hyd["B"]))
    return layers


CORN["make_layers"] = make_layers


def main():
    weather_path = os.path.join(REFERENCE_DATA_DIR, "input/RockSprings.weather")
    harvest_path = os.path.join(REFERENCE_DATA_DIR, "output/ContinuousCorn/harvest.txt")
    if not os.path.exists(weather_path) or not os.path.exists(harvest_path):
        print(f"Reference data not found under {REFERENCE_DATA_DIR}.")
        print("Download Cycles v1.4.4 and run the ContinuousCorn sample first -- see")
        print("rhizo_engine.py's module docstring for exact steps.")
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
        # Real antecedent soil moisture instead of an arbitrary field-capacity reset -- the
        # same calendar year's own Jan-1-through-day-before-planting weather (already loaded,
        # no new data needed), run as bare fallow. See simulate_season()'s spinup_rows
        # docstring / CLAUDE.md 2026-09-22 for why this replaced always starting full.
        spinup_rows = [daily[year][d] for d in range(1, plant_doy) if d in daily[year]]
        # Real rising atmospheric CO2's effect on water-use efficiency (wue_co2_scale -- see
        # simulate_season()'s own docstring) -- added 2026-10-01 after finding corn's own
        # 37-year real-minus-model residual correlates 0.73 with calendar year, a real
        # secular bias this mechanism substantially (not fully) corrects.
        wue_co2_scale = CO2_PPM_BY_YEAR.get(year, CO2_REF_PPM) / CO2_REF_PPM
        result = simulate_season(rows, CORN, spinup_rows=spinup_rows, wue_co2_scale=wue_co2_scale)
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
