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
    INITIAL_MOISTURE_FRACTION, CO2_PPM_BY_YEAR, CO2_REF_PPM,
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
        layers.append(dict(thick=L["thick"], fc=hyd["fc"], pwp=hyd["pwp"], sat=hyd["sat"],
                            theta=hyd["pwp"] + INITIAL_MOISTURE_FRACTION * (hyd["fc"] - hyd["pwp"]),
                            ksat_mm_day=hyd["ksat_mm_day"], psi_e_kpa=hyd["psi_e_kpa"], B=hyd["B"]))
    return layers


SOYBEAN = dict(tt_maturity=2250, flowering_tt=1250, base_t=5, opt_t=28, max_t=43,
               rue=1.3, wue=4.5, hi_x=0.4, hi_o=0.15, hi_slope=1.0, fsti=0.45, fstf=0.95,
               kc=1.0, eix=1.0, tr_min_t=3.0, tr_threshold_t=15.0, lat_deg=LAT,
               make_layers=make_layers, calibration_factor=1.4678,  # unchanged by the real
               # CO2-WUE-scaling mechanism added 2026-10-01 (wue_co2_scale, see
               # simulate_season()'s own docstring) -- model mean moved by <0.001 Mg/ha, a real
               # but negligible effect here (correlation 0.9545->0.9471, within noise), unlike
               # corn/wheat's substantial gains from the same mechanism. Re-derived 2026-10-01
               # (same day) for the
               # real cold-kill mechanism (threshold_temp_cold_damage below) -- previous value
               # 1.4297, re-derived 2026-09-30 for the
               # real f_G harvest-index fix (Kemanian et al. 2007) -- see
               # cycles_engine_validate.py's own HI-computation docstring. Previous value 1.1894,
               # itself re-derived 2026-09-24 for the
               # real-data TTF50_SHOOT_PARTITION refit (0.5 -> 0.32) + the same-day emergence-gate
               # fix + the cold-temperature radiation-growth reduction + the NET_GROWTH_FRACTION
               # post-limitation growth-conversion fix + the curve-number/f_wc swap (real Eq
               # SI.5-SI.7, see retention_param_mm()) -- see cycles_engine_validate.py, and re-
               # derived again 2026-09-25 for the hydraulic-conductance water-stress mechanism
               # (campbell_water_uptake()) -- correlation moved 0.856 -> 0.802 from that switch
               # alone, see QUESTIONS_FOR_DEVS.md/CLAUDE.md for the full account
               n_max_conc=0.07, n_dilution_slope=0.4, legume=True,  # real GenericCrops.crop values;
               # soybean fixes its own N (LEGUME=1) so the nitrogen knob correctly has no effect on it
               depletion_fraction=0.50,  # real FAO-56 Table 22 value for soybeans -- same as this
               # engine's own prior default, so this crop's numbers are unaffected by adding it
               tr_max_mm_day=8,  # real GenericCrops.crop TRANSPIRATION_MAX (SoybeanMG.5)
               root_max_m=1.5,  # real GenericCrops.crop MAXIMUM_ROOTING_DEPTH (SoybeanMG.5)
               tt_emergence=70,  # real GenericCrops.crop THERMAL_TIME_TO_EMERGENCE (SoybeanMG.5)
               lwp_stress_onset=-1100, lwp_wilting_point=-1800,  # real GenericCrops.crop
               # LWP_STRESS_ONSET/LWP_WILTING_POINT (SoybeanMG.5, J/kg), added 2026-09-25 for
               # campbell_water_uptake() -- see CORN's own comment in run_validation.py. Water
               # stress still applies to soybean (only NITROGEN stress is exempted, via the
               # legume flag) -- this crop selects the new mechanism same as any other.
               threshold_temp_cold_damage=2)  # real GenericCrops.crop THRESHOLD_TEMPERATURE_FOR_
               # COLD_DAMAGE (SoybeanMG.5), added 2026-10-01 for the real cold-kill mechanism --
               # see cycles_engine_validate.py's own comment at the kill check. Correlation moved
               # 0.871 -> 0.950, the second-largest jump this mechanism produced (after corn's
               # own 0.505 -> 0.691) -- re-derived calibration_factor below for the real mean shift.

WHEAT = dict(tt_maturity=1800, flowering_tt=1250, base_t=0, opt_t=20, max_t=35,
             rue=1.6, wue=6.0, hi_x=0.52, hi_o=0.2, hi_slope=1.0, fsti=0.45, fstf=0.95,
             kc=1.0, eix=1.0, tr_min_t=0.0, tr_threshold_t=12.0, lat_deg=LAT,
             hi_use_thermal_time_fraction=True,  # real exemption, 2026-09-30 -- see
             # cycles_engine_validate.py's own HI-computation docstring: the real f_G
             # (Kemanian et al. 2007) regressed wheat's correlation (0.337->0.163) even
             # though it helped corn/soybean, plausibly tied to wheat's own already-
             # documented winter-dormancy anomaly.
             make_layers=make_layers, calibration_factor=0.7502,  # re-derived 2026-10-01 for the
             # real CO2-WUE-scaling mechanism (wue_co2_scale, see simulate_season()'s own
             # docstring) -- a real, substantial win for wheat specifically (correlation
             # 0.337->0.444, the second-largest single-mechanism gain this crop has gotten,
             # after the day-by-day nitrogen rebuild); previous value 0.7528. CORRECTED
             # 2026-09-29 (see top of
             # file's own note below this one) -- was 0.7506 as of 2026-09-28.
             #
             # 2026-09-29: a real, previously-undiscovered bug was found and fixed in
             # cycles_engine_validate.py's rothc_temp_factor() usage, via a new pattern-assertion
             # test suite (pattern_assertions.py) built to check DIRECTION of classroom-relevant
             # claims rather than point accuracy -- it found corn showing ZERO nitrogen response
             # at every multi-site test location, traced to rothc_temp_factor()'s raw output being
             # multiplied straight into BACKGROUND_N_KG_HA_DAY as if it were a bounded 0-1 "how
             # warm was today" dimmer. It isn't: real RothC's own curve crosses 1.0 around 9.5C and
             # keeps climbing (2.82 at 20C, 4.79 at 30C), so any real growing season was getting
             # background nitrogen credited at roughly 3x the rate BACKGROUND_N_KG_HA_DAY was
             # actually calibrated for. Fixed by normalizing against the empirical mean of that
             # same raw weather factor across every real growing day in the full validated 37-year
             # Rock Springs record (2.025, see ROTHC_WEATHER_FACTOR_NORM's own docstring in
             # cycles_engine_validate.py for the full derivation) -- this makes a typical Rock
             # Springs growing day read ~1.0 again, matching the original design intent, while
             # keeping all the real day-to-day/year-to-year variability the raw RothC shape
             # provides. Confirmed by direct A/B toggle of the new normalization constant that
             # soybean and silage corn's own default validation (neither activates nitrogen
             # tracking) are BYTE-IDENTICAL before and after this fix -- only wheat, the one crop
             # whose default validation tracks real nitrogen, moved: correlation 0.285 -> 0.341,
             # mean recalibrated here (0.7506 -> 0.7528) to match the real 3.9205414444444444
             # Mg/ha mean exactly. A real, separate, pre-existing problem was also found while
             # doing this A/B check and is NOT fixed here, out of scope for this fix: silage
             # corn's own correlation is currently 0.182 (real mean 13.22 vs. model 14.81 Mg/ha),
             # present identically whether today's fix is on or off, so it predates this session's
             # work and needs its own separate diagnosis pass.
             #
             # Wheat is still deliberately exempted from the hydraulic-conductance mechanism
             # (campbell_water_uptake(), see CORN's own comment in run_validation.py), by simply not
             # giving it lwp_stress_onset/lwp_wilting_point -- the engine's own graceful fallback (see
             # simulate_season()'s crop_ct precompute) routes wheat through the older
             # root_zone_availability()/water_stress_response()/extract_transpiration() trio instead.
             # That part of the reasoning still holds: the Campbell mechanism was verified working
             # CORRECTLY for wheat (water_stress reads exactly 1.0 every day, all 9 years -- wheat's
             # real root profile genuinely never gets that dry at Rock Springs), and wheat's real
             # dominant driver is nitrogen (-0.894 vs 0.359 correlation against real Cycles' own
             # stress columns), not water.
             #
             # The "0.523" figure this comment previously claimed for that state was never actually
             # reproducible: a real git-bisect against a freshly re-obtained Cycles v1.4.4 reference
             # (2026-09-28, this exact commit's own real Cycles run, not an assumption) showed every
             # commit since the day-by-day nitrogen rebuild -- including the exact commit the "0.523"
             # figure was supposedly measured at -- gives 0.411 against this real data, not 0.523.
             # The reference data and the crop dict both check out (real mean matches to 2 decimals,
             # soil/weather files are byte-identical to what's hardcoded here), so this was either a
             # stale/incorrect historical measurement or came from a container whose own reference
             # setup differed in some way that can no longer be reconstructed. Rather than chase a
             # number that may never have been real, this was reported and set aside (see CLAUDE.md,
             # "not the exception... nail down corn" -- wheat is explicitly the exception here).
             #
             # While nailing down CORN's own real N-tracking path (its own DEFAULT validation never
             # tracks nitrogen, so this was purely a correctness check on an optional path), a real,
             # separate, and much more consequential bug was found and fixed in simulate_season()'s
             # shared day-by-day nitrogen mechanism itself: it passed biomass*10 into
             # n_critical_pct()/n_marginal_demand_pct() (both of which want plain Mg/ha, per their
             # own docstrings) and then applied the Mg-to-kg/pct conversion factor of 10 a SECOND time
             # in demand_today_kg_ha, inflating daily nitrogen demand roughly an order of magnitude.
             # Caught via the standard "does a very-high N rate converge to the no-tracking baseline"
             # sanity check, which corn's optional N path failed outright (capped at the same yield
             # and uptake whether given 150 or 2000 kg N/ha) -- see cycles_engine_validate.py's own
             # comment at the fix site for the full account. Wheat's validation wires nitrogen in by
             # default (below), so it was running this exact buggy math the whole time too. Fixing it
             # moves wheat's own number again, in a DIFFERENT direction than the historical "0.523"
             # claim: real mean 4.33 (old, buggy, still stale) -> uncalibrated 6.74 (fixed math, wheat
             # is now correctly LESS nitrogen-stressed than the buggy version made it look) ->
             # recalibrated here to match the real 3.9205414444444444 Mg/ha mean exactly (1.2895 *
             # 3.9205414444444444 / 6.735047429878611). Correlation with this real bug fixed and the
             # mean corrected: 0.285 -- worse than the unreproducible 0.523, and also worse than the
             # 0.411 this exact crop dict gave under the OLD buggy math, confirming the demand-scaling
             # bug was not itself the reason wheat's number wouldn't reproduce. Wheat's real accuracy
             # question remains open and is explicitly NOT being chased further right now (the "rule"
             # being nailed down this session is corn, not wheat) -- this calibration_factor exists so
             # wheat's own mean stays honestly matched to real output under the corrected, no-longer-
             # buggy shared engine, not as a claim that 0.285 is wheat's final answer.
             #
             # calibration_factor before the LWP switch (1.2895) was re-derived 2026-09-25 (a second
             # time the same day) after replacing the season-total quadratic-plateau N-stress
             # mechanism with a real, day-by-day concentration-tracked one (see simulate_season()'s
             # own comment above canopy_n_kg_ha in cycles_engine_validate.py) -- correlation moved
             # 0.473 -> (claimed 0.523, per the correction above, not reproducible) from this fix
             # alone, recalibrated at the time to keep the mean matching the real 4.328790555555556
             # Mg/ha in wheat's own real fertilization event (see n_applications=[(75, 90)] on the
             # validate() call below) -- before this, wheat's validation ran with NO nitrogen
             # tracking at all despite a real, disclosed 90 kg N/ha UAN application sitting in
             # CornSilageSoyWheat.operation (YEAR 3, DOY 75, the spring topdress after fall
             # planting) that had simply never been plugged into the validation harness. Tested
             # against the fully-current engine (post f_wc/RothC/TTf50/radiation-temp fixes):
             # correlation 0.393 -> 0.473, the single largest jump wheat has seen from any fix
             # this project has tried, achieved with zero new formula guessing. A real previous-
             # crop N credit (60 kg/ha, disclosed for maize-following-soybean, SI Sec. IX -- an
             # assumption to extend it to wheat-following-soybean, not itself disclosed for wheat)
             # was tested too and rejected: 90kg+credit gives a better absolute mean untouched
             # (3.75 vs 4.33 Mg/ha) but a WORSE correlation (0.431) than 90kg alone -- and
             # calibration_factor already exists specifically to correct absolute-level bias
             # without touching correlation, so there's no real reason to lean on the shakier,
             # cross-crop-assumption credit when the fully-disclosed 90kg-alone number scores
             # higher once recalibrated. This calibration_factor (0.8288 * 4.328790555555556 /
             # 2.9712609741581075) brings the recalibrated mean back to the real 4.329 Mg/ha
             # exactly (MAE 0.496, essentially the same level accuracy as the old no-N baseline's
             # 0.48) while keeping the new 0.473 correlation untouched, per this project's own
             # standing discipline that calibration_factor rescaling never changes correlation.
             # Everything from the prior calibration history below is unaffected and still real:
             # the TTF50_SHOOT_PARTITION refit (0.223 -> 0.276), the same-day emergence-gate fix,
             # the cold-temperature radiation-growth reduction (transpiration_temp_factor also
             # applied to GR, 0.276 -> 0.397), the NET_GROWTH_FRACTION post-limitation growth-
             # conversion fix, wheat's own rad_temp_floor/rad_temp_plateau_t refit (0.397 -> 0.399),
             # and the curve-number/f_wc swap (0.399 -> 0.393, the baseline this fix started from)
             # -- see the comments above thermal_time_increment() and radiation_temp_factor() in
             # cycles_engine_validate.py
             depletion_fraction=0.55,  # real FAO-56 Table 22 (winter/spring wheat)
             canopy_shape=(5, -14, -15, 16),  # refit from real data -- see QUESTIONS_FOR_DEVS.md item 5;
                                               # fixes level bias, does NOT fix wheat's weak correlation
             rad_temp_floor=0.257, rad_temp_plateau_t=15.55,  # wheat-specific radiation-temperature
             # response (2026-09-23), separate from tr_min_t/tr_threshold_t used for transpiration --
             # fit directly from real Cycles output (see radiation_temp_factor()'s own docstring in
             # cycles_engine_validate.py); wheat's own fall-to-spring season never reaches truly warm,
             # unambiguously-radiation-limited conditions, so reusing the transpiration threshold
             # (12 degC) undershot real growth at every temperature this crop actually experiences
             tr_max_mm_day=8,  # real GenericCrops.crop TRANSPIRATION_MAX (WinterWheat)
             root_max_m=2.0,  # real GenericCrops.crop MAXIMUM_ROOTING_DEPTH (WinterWheat)
             tt_emergence=100,  # real GenericCrops.crop THERMAL_TIME_TO_EMERGENCE (WinterWheat)
             n_max_conc=0.07, n_dilution_slope=0.45,  # real GenericCrops.crop values (WinterWheat) --
             # added 2026-09-24, a real data-completeness gap: unlike CORN/SOYBEAN, WHEAT never had
             # these two fields set, so it silently fell back to whatever crop["n_max_conc"] happened
             # to be if nitrogen tracking were ever activated for it -- currently a KeyError risk, not
             # a wrong-number risk, since nothing in this project calls simulate_season() for wheat
             # with n_rate_kg_ha/n_applications/n_credit_kg_ha/manure_n_kg_ha set (verified: zero
             # effect on validation, confirming this is a pure completeness fix, not a behavior change)
             n_min_conc=0.002,  # real GenericCrops.crop N_MIN_CONCENTRATION_STRAW (0.2%), added
             # 2026-09-25 for the day-by-day concentration-tracked N-stress mechanism -- see
             # simulate_season()'s own comment above canopy_n_kg_ha in cycles_engine_validate.py.
             # Deliberately NO lwp_stress_onset/lwp_wilting_point here -- see calibration_factor's
             # own comment above for why wheat specifically is exempted from campbell_water_uptake().
             threshold_temp_cold_damage=-10)  # real GenericCrops.crop THRESHOLD_TEMPERATURE_FOR_
             # COLD_DAMAGE (WinterWheat) -- confirmed, not assumed, a real null result: tested
             # directly 2026-10-01 alongside the same mechanism's real wins for corn/soybean,
             # correlation unchanged to three decimals. Real and expected: winter wheat flowers
             # in spring, well after the coldest part of winter, and -10C is rarely if ever
             # reached that late at this site -- added for completeness/documentation, not
             # because it does anything here.

CORN_SILAGE = dict(tt_maturity=1800, flowering_tt=1000, base_t=6, opt_t=28, max_t=46,
                    rue=2.2, wue=8.7, hi_x=0.8, hi_o=0.15, hi_slope=1.0, fsti=0.45, fstf=0.95,
                    kc=1.1, eix=1.0, tr_min_t=3.0, tr_threshold_t=15.0, lat_deg=LAT,
                    make_layers=make_layers, forage_fraction=0.95, calibration_factor=0.7925,  # re-
                    # derived 2026-10-01 for the real CO2-WUE-scaling mechanism (wue_co2_scale,
                    # see simulate_season()'s own docstring) -- a real cost here (correlation
                    # 0.2035->0.1170), kept anyway since the mechanism is physically general
                    # (not selectively applied only where it helps) and this crop is already far
                    # below the classroom-workable bar either way; previous value 0.7911,
                    # re-derived
                    # 2026-09-30 again for the CORN_CANOPY_SHAPE late-senescence refit (this crop
                    # uses CORN_CANOPY_SHAPE too, see below -- was 0.8431), and before that:
                    # 2026-09-24 for the real-data TTF50_SHOOT_PARTITION refit + the same-day
                    # emergence-gate fix + the cold-temperature radiation-growth reduction + the
                    # NET_GROWTH_FRACTION post-limitation growth-conversion fix + the curve-number/
                    # f_wc swap (real Eq SI.5-SI.7, see retention_param_mm()) -- see
                    # cycles_engine_validate.py, and again 2026-09-25 for the hydraulic-conductance
                    # water-stress mechanism (campbell_water_uptake()) -- correlation essentially
                    # unchanged from that switch (0.518 -> 0.516)
                    depletion_fraction=0.55,  # real FAO-56 Table 22 value, same crop biology as grain corn
                    canopy_shape=CORN_CANOPY_SHAPE,  # real fix (thermal time, canopy shape, harvest
                    # date, forage ratio all individually verified accurate) does NOT move correlation
                    # (0.503 -> 0.501) -- see QUESTIONS_FOR_DEVS.md, this is a distinct, still-open item
                    tr_max_mm_day=10,  # real GenericCrops.crop TRANSPIRATION_MAX (CornSilageRM.90)
                    root_max_m=1.55,  # real GenericCrops.crop MAXIMUM_ROOTING_DEPTH (CornSilageRM.90)
                    # -- notably shallower than grain corn's 2.0m, a real distinguishing trait
                    tt_emergence=65,  # real GenericCrops.crop THERMAL_TIME_TO_EMERGENCE (CornSilageRM.90)
                    n_max_conc=0.055, n_dilution_slope=0.4, legume=False,  # real GenericCrops.crop
                    # values for CornRM.90 -- CORN_SILAGE shares every other growth parameter
                    # (rue/wue/hi_x/tt_maturity/base_t/opt_t/max_t, all identical to CORN's own
                    # values above) with grain corn, since it's the same crop harvested earlier,
                    # so it's the same real crop-file entry for these fields too. Added 2026-09-25
                    # during a broad audit for exactly this class of gap (found for WHEAT on
                    # 2026-09-24, missed here at the time): without these two fields,
                    # n_marginal_demand_pct()/n_critical_pct() would raise a bare KeyError the
                    # moment nitrogen tracking was ever activated for this crop. Currently a
                    # completeness fix, not a behavior change -- nothing in this project calls
                    # simulate_season() for CORN_SILAGE with n_rate_kg_ha/n_applications/
                    # n_credit_kg_ha/manure_n_kg_ha set (confirmed: this crop isn't even in
                    # model-validation.html's own CROPS registry, so it isn't reachable from that
                    # page's "Full simulation controls" panel either) -- but the same KeyError
                    # trap wheat had before 2026-09-24 doesn't need to exist here waiting for
                    # whoever wires nitrogen into this crop next.
                    n_min_conc=0.002,  # real GenericCrops.crop N_MIN_CONCENTRATION_STRAW (0.2%),
                    # added 2026-09-25 for the day-by-day concentration-tracked N-stress mechanism
                    # -- see simulate_season()'s own comment above canopy_n_kg_ha in
                    # cycles_engine_validate.py. Same not-currently-reachable status as above.
                    lwp_stress_onset=-1100, lwp_wilting_point=-2000,  # real GenericCrops.crop
                    # LWP_STRESS_ONSET/LWP_WILTING_POINT (CornSilageRM.90, J/kg, identical to
                    # grain corn's own CornRM.90 values), added 2026-09-25 for
                    # campbell_water_uptake() -- see CORN's own comment in run_validation.py.
                    threshold_temp_cold_damage=3)  # real GenericCrops.crop THRESHOLD_TEMPERATURE_
                    # FOR_COLD_DAMAGE (CornSilageRM.90, identical to grain corn) -- confirmed, not
                    # assumed, a real null result: tested directly 2026-10-01 alongside the same
                    # mechanism's real wins for corn/soybean, correlation unchanged to three
                    # decimals. Real and expected: this crop is harvested at harvest_ttf=0.85
                    # (mid-growth, well before grain corn's own full-maturity harvest window),
                    # so it's cut and gone before the late-season cold-kill window this mechanism
                    # targets would ever become relevant.


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


def validate(rotation, crop_name, crop_params, label, metric="grain", harvest_ttf=1.0, n_applications=None):
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
        # Real antecedent soil moisture -- that same plant_year's own Jan-1-through-day-
        # before-planting weather, already in weather_flat, as bare fallow (see
        # run_validation.py's identical treatment / simulate_season()'s spinup_rows
        # docstring / CLAUDE.md 2026-09-22).
        jan1_idx = flat_index.get((info["plant_year"], 1))
        spinup_rows = [r for (_, _, r) in weather_flat[jan1_idx:start]] if jan1_idx is not None else None
        # Real rising atmospheric CO2's effect on water-use efficiency -- see
        # run_validation.py's identical comment / simulate_season()'s own docstring. Applied
        # uniformly to all three crops in this rotation (the mechanism is general to C3 and C4
        # alike, per Bassiouni & Vico's own theory), not selectively kept only where it helps --
        # it's a real win for wheat, negligible for soybean, and a real (disclosed) cost for
        # silage corn, already far below the classroom-workable bar either way.
        wue_co2_scale = CO2_PPM_BY_YEAR.get(info["plant_year"], CO2_REF_PPM) / CO2_REF_PPM
        result = simulate_season(rows, crop_params, harvest_ttf=harvest_ttf, spinup_rows=spinup_rows,
                                  n_applications=n_applications, wue_co2_scale=wue_co2_scale)
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
    validate("CornSilageSoyWheat", "WinterWheat", WHEAT, "Winter Wheat",
              n_applications=[(75, 90)])  # real UAN topdress, CornSilageSoyWheat.operation
              # YEAR 3 DOY 75 -- see WHEAT's calibration_factor comment above for why this
              # is now wired in as the default rather than validating with no N tracking
    validate("CornSilageSoyWheat", "CornSilageRM.90", CORN_SILAGE, "Silage Corn", metric="forage", harvest_ttf=0.85)
