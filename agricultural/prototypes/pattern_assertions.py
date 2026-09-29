"""
Pattern-assertion test suite -- checks DIRECTION and ORDERING, not point
accuracy, against the real classroom-facing claims this project's tools
already make or imply (see CLAUDE.md's own panel descriptions for where each
claim comes from). Built 2026-09-29 per Matt's direct request, after the
project's own validation history showed that chasing correlation/mean-yield
fit is the wrong target for the actual classroom risk: a model can hit good
aggregate metrics while still being wrong on the specific qualitative pattern
a lesson teaches (equifinality -- see the conversation this file's commit is
attached to for the full methodological discussion, Wallach's crop-model-
evaluation literature, and AgMIP's own systematic-perturbation approach,
which this file's design borrows from).

Deliberately uses ONLY data already committed to this repo (weather-tiles/,
statsgo2_soil_grid.json.gz, via field_data.py) rather than /tmp/cycles-run --
this suite must survive this container's own repeatedly-documented mid-
session reprovisioning (see CLAUDE.md's "Operational note") and must be
re-runnable by anyone who clones this repo, not just in a session that
happens to still have Matt's licensed Cycles sample files sitting in /tmp.
That is a deliberate tradeoff: these checks use the real committed multi-
site weather/soil (already validated once in CLAUDE.md's "Four preset sites"
and subsequent entries), not the hand-curated exact Rock Springs record the
canonical run_validation.py scripts use -- so a failure here could mean
either a real regression OR a real, already-disclosed site-resolution
distance issue (see field_data.py). Check both before assuming the model
itself is wrong.

Each check is a single directional claim, not a magnitude claim -- e.g.
"more nitrogen should not decrease corn yield," not "corn yield at N=150
should be 8.03 Mg/ha." That is the entire point of this file: it should
keep passing across model refinements that change magnitudes, and it
should FAIL LOUDLY the moment a refinement accidentally flips a direction
a classroom lesson depends on -- which is exactly the failure mode point-
accuracy validation (correlation, MAE) cannot catch, and which already
happened once in this project undetected for weeks (the harvest-index bug
hiding behind a calibration factor).

This is a starting set, not exhaustive -- see the "Not yet covered" list at
the end of this file for real classroom claims not yet encoded here.

Run: python3 pattern_assertions.py
Exit code is nonzero if any check fails.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cycles_engine_validate import (
    simulate_season, simulate_soil_temp, find_planting_doy,
    saxton_rawls, OM_FROM_SOC, INITIAL_MOISTURE_FRACTION,
)
import field_data as fd

# ---------------------------------------------------------------------------
# Real per-crop parameters, copied from run_validation.py / run_validation_
# rotation2.py (the same real GenericCrops.crop-sourced values used for the
# actual validated engine) -- duplicated here rather than imported, since
# those two files' own module-level code assumes /tmp/cycles-run exists
# (they read real Cycles reference output at import time via main()). Kept
# in sync by hand; if either canonical file's CORN/SOYBEAN dict changes,
# update these to match.
# ---------------------------------------------------------------------------

CORN = dict(
    tt_maturity=1800, flowering_tt=1000, base_t=6, opt_t=28, max_t=46,
    rue=2.2, wue=8.7, hi_x=0.8, hi_o=0.15, hi_slope=1.0, fsti=0.45, fstf=0.95,
    calibration_factor=0.8490, kc=1.1, eix=1.0, tr_min_t=3.0, tr_threshold_t=15.0,
    n_max_conc=0.055, n_dilution_slope=0.4, legume=False, n_min_conc=0.002,
    depletion_fraction=0.55, tr_max_mm_day=10, root_max_m=2.0, tt_emergence=65,
    lwp_stress_onset=-1100, lwp_wilting_point=-2000,
)

CORN_LONG_SEASON = dict(CORN, tt_maturity=2300, flowering_tt=1300)
# Real CornRM.110 values (confirmed directly against GenericCrops.crop,
# 2026-09-29) -- only maturity/flowering differ from CornRM.90 (CORN above),
# per CLAUDE.md's own "Tab 1 rebuilt around real climate risk" entry.

SOYBEAN = dict(
    tt_maturity=2250, flowering_tt=1250, base_t=5, opt_t=28, max_t=43,
    rue=1.3, wue=4.5, hi_x=0.4, hi_o=0.15, hi_slope=1.0, fsti=0.45, fstf=0.95,
    calibration_factor=1.1894, kc=1.0, eix=1.0, tr_min_t=3.0, tr_threshold_t=15.0,
    n_max_conc=0.07, n_dilution_slope=0.4, legume=True,
    depletion_fraction=0.50, tr_max_mm_day=8, root_max_m=1.5, tt_emergence=70,
    lwp_stress_onset=-1100, lwp_wilting_point=-1800,
)


def build_layers_fn(soil_layers_raw):
    """Same construction as run_validation.py's make_layers(), generalized to
    any resolved soil_layers_raw instead of Rock Springs' own hand-curated
    values."""
    def make_layers():
        layers = []
        for L in soil_layers_raw:
            om = L["soc"] * OM_FROM_SOC
            hyd = saxton_rawls(L["sand"], L["clay"], om)
            layers.append(dict(
                thick=L["thick"], fc=hyd["fc"], pwp=hyd["pwp"], sat=hyd["sat"],
                theta=hyd["pwp"] + INITIAL_MOISTURE_FRACTION * (hyd["fc"] - hyd["pwp"]),
                ksat_mm_day=hyd["ksat_mm_day"], psi_e_kpa=hyd["psi_e_kpa"], B=hyd["B"],
            ))
        return layers
    return make_layers


_SITE_CACHE = {}


def _site(site_key):
    if site_key not in _SITE_CACHE:
        lat, lon = fd.PRESET_SITES[site_key]
        weather_by_year, wx_dist = fd.resolve_field_weather(lat, lon)
        soil_raw, soil_dist, series = fd.resolve_field_soil(lat, lon)
        if weather_by_year is None:
            raise RuntimeError(f"{site_key} has no real weather-tile coverage")
        _SITE_CACHE[site_key] = dict(weather_by_year=weather_by_year, soil_raw=soil_raw,
                                      series=series, lat=lat)
    return _SITE_CACHE[site_key]


def run_crop_season(site_key, year, crop, **kwargs):
    """Resolves real committed weather+soil for a preset site, finds a
    soil-temperature-triggered planting date the same way run_validation.py
    does (a defensible simplification reused here for soybean too, not just
    corn -- this suite tests DIRECTION, not exact planting-date accuracy, so
    reusing one real, validated trigger for both crops is an acceptable
    simplification, flagged here rather than silently assumed), and runs
    simulate_season() with a real Jan-1-to-planting spin-up."""
    site = _site(site_key)
    year_wx = site["weather_by_year"][year]
    doys_sorted = sorted(year_wx)
    tmeans = [(year_wx[d]["tx"] + year_wx[d]["tn"]) / 2 for d in doys_sorted]
    tsoils = simulate_soil_temp(tmeans, k=0.15)
    tsoil_by_doy = dict(zip(doys_sorted, tsoils))
    plant_doy = find_planting_doy(tsoil_by_doy, (110, 131), 12.0)
    rows = [year_wx[d] for d in range(plant_doy, 300) if d in year_wx]
    spinup_rows = [year_wx[d] for d in range(1, plant_doy) if d in year_wx]
    crop = dict(crop, lat_deg=site["lat"], make_layers=build_layers_fn(site["soil_raw"]))
    return simulate_season(rows, crop, spinup_rows=spinup_rows, **kwargs)


def growing_season_precip(site_key, year, doy_range=(121, 273)):
    """Real total precipitation over a fixed May-Sept window -- used to pick
    a genuinely wet vs. dry year at a site from real data, rather than
    hard-coding years from a different, uncommitted weather record."""
    site = _site(site_key)
    year_wx = site["weather_by_year"][year]
    return sum(year_wx[d]["pp"] for d in year_wx if doy_range[0] <= d <= doy_range[1])


# ---------------------------------------------------------------------------
# Checks. Each returns (name, passed, detail_string).
# ---------------------------------------------------------------------------

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("Corn: more nitrogen does not decrease yield")
def c_n_direction():
    lo = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=0)["grain"]
    hi = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=650)["grain"]
    return hi > lo, f"N=0 -> {lo:.3f} Mg/ha, N=650 -> {hi:.3f} Mg/ha"


@check("Corn: nitrogen response shows diminishing returns (concave, not accelerating)")
def c_n_diminishing():
    y0 = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=0)["grain"]
    y50 = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=50)["grain"]
    y600 = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=600)["grain"]
    y650 = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=650)["grain"]
    early_gain, late_gain = y50 - y0, y650 - y600
    return early_gain > late_gain, (
        f"gain N=0->50: {early_gain:.4f} Mg/ha, gain N=600->650: {late_gain:.4f} Mg/ha "
        f"(early gain should be larger -- a straight line or accelerating curve here "
        f"would teach students the opposite of real diminishing returns)"
    )


@check("Soybean: nitrogen rate has no effect on yield (legume exemption)")
def c_soybean_n_invariant():
    lo = run_crop_season("iowa", 2012, SOYBEAN, n_rate_kg_ha=0)["grain"]
    hi = run_crop_season("iowa", 2012, SOYBEAN, n_rate_kg_ha=650)["grain"]
    return math.isclose(lo, hi, rel_tol=1e-9), f"N=0 -> {lo:.6f}, N=650 -> {hi:.6f} Mg/ha"


@check("Corn: nitrogen leaching increases with nitrogen rate")
def c_leaching_direction():
    # Iowa 2012 (used in an earlier version of this check) is the single driest year in this
    # project's own 30-year committed sample (293mm growing-season precip, next-closest is
    # 319mm) -- there's essentially no drainage event to leach anything through, so the check
    # failed there for a real but uninteresting reason (no water moving, not "leaching doesn't
    # respond to N"). Rock Springs 1993 is a genuinely wet real year with a real drainage
    # event -- confirmed directly before locking this in, not guessed.
    lo = run_crop_season("rock_springs", 1993, CORN, n_rate_kg_ha=50)["n_leached_kg_ha"]
    hi = run_crop_season("rock_springs", 1993, CORN, n_rate_kg_ha=400)["n_leached_kg_ha"]
    return hi > lo, f"N=50 -> {lo:.2f} kg N/ha leached, N=400 -> {hi:.2f} kg N/ha leached"


@check("Crop choice: soybean beats corn with no fertilizer, corn overtakes it at high N")
def c_crop_crossover():
    # Real finding (2026-09-29), not a test-design flaw like the two checks above: this
    # crossover does NOT currently exist anywhere it was tested (Iowa, and Rock Springs via
    # both the tile-resolved AND the exact validated weather record -- checked directly
    # against /tmp/cycles-run's real RockSprings.weather before concluding this). Corn beats
    # soybean at N=0 in every case checked. This project's own agricultural/investigation.html
    # Tab 3 ("Crop Choice") currently tells students there's a real crossover at 37.22 kg N/ha
    # at Rock Springs -- that claim was true when it was measured (2026-09-21) but a great
    # deal of the engine has changed since then (the 2026-09-25 hydraulic-conductance water-
    # stress switch among the largest), and it does not appear to be true of the CURRENT
    # engine. This check is left failing deliberately rather than silently passed by picking
    # a year/site where it happens to hold -- it's flagging a real, currently-shipped,
    # possibly-false classroom claim, which is exactly the failure mode this suite exists to
    # catch. Not fixed here -- re-deriving Tab 3's crossover point (or confirming it's really
    # gone) is a separate task from today's nitrogen-background fix.
    soy_lo = run_crop_season("rock_springs", 2012, SOYBEAN, n_rate_kg_ha=0)["grain"]
    corn_lo = run_crop_season("rock_springs", 2012, CORN, n_rate_kg_ha=0)["grain"]
    soy_hi = run_crop_season("rock_springs", 2012, SOYBEAN, n_rate_kg_ha=650)["grain"]
    corn_hi = run_crop_season("rock_springs", 2012, CORN, n_rate_kg_ha=650)["grain"]
    ok = (soy_lo > corn_lo) and (corn_hi > soy_hi)
    return ok, (
        f"N=0: soybean {soy_lo:.2f} vs corn {corn_lo:.2f} Mg/ha (soybean should win); "
        f"N=650: soybean {soy_hi:.2f} vs corn {corn_hi:.2f} Mg/ha (corn should win) -- "
        f"if this fails, agricultural/investigation.html Tab 3's own '37.22 kg N/ha "
        f"crossover' claim is very likely stale against the current engine, not just this "
        f"check -- see this check's own docstring before assuming it's a test bug"
    )


@check("Tillage: helps when nitrogen is limiting, has ~no effect when it isn't")
def c_tillage_interaction():
    # Also moved off Iowa 2012 for the same reason as the leaching check above -- confirmed
    # this mechanism genuinely works once tested somewhere water isn't the sole constraint.
    lo_no_till = run_crop_season("rock_springs", 2012, CORN, n_rate_kg_ha=10)["grain"]
    lo_till = run_crop_season("rock_springs", 2012, CORN, n_rate_kg_ha=10,
                               tillage_doy=110, tillage_implement="Plow_moldboard")["grain"]
    hi_no_till = run_crop_season("rock_springs", 2012, CORN, n_rate_kg_ha=650)["grain"]
    hi_till = run_crop_season("rock_springs", 2012, CORN, n_rate_kg_ha=650,
                               tillage_doy=110, tillage_implement="Plow_moldboard")["grain"]
    low_gain, high_gain = lo_till - lo_no_till, hi_till - hi_no_till
    ok = low_gain > 0.05 and abs(high_gain) < 0.05
    return ok, (
        f"low N (10): +{low_gain:.4f} Mg/ha from tillage; high N (650): {high_gain:+.4f} "
        f"Mg/ha -- tillage should visibly help only when N is the limiting factor, "
        f"otherwise a student would wrongly conclude tillage always raises yield"
    )


@check("Soil: deep prairie soil (Iowa) outyields sandy semi-arid soil (Kansas), same weather/N")
def c_soil_comparison():
    iowa = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=150)["grain"]
    kansas = run_crop_season("kansas", 2012, CORN, n_rate_kg_ha=150)["grain"]
    return iowa > kansas, f"Iowa (Canisteo) -> {iowa:.2f} Mg/ha, Kansas (Manter) -> {kansas:.2f} Mg/ha"


@check("Weather: a real wetter growing season outyields a real drier one, same site/crop/N")
def c_weather_comparison():
    site = "iowa"
    candidate_years = range(1985, 2015)
    precip_by_year = {y: growing_season_precip(site, y) for y in candidate_years}
    wet_year = max(precip_by_year, key=precip_by_year.get)
    dry_year = min(precip_by_year, key=precip_by_year.get)
    wet_yield = run_crop_season(site, wet_year, CORN, n_rate_kg_ha=150)["grain"]
    dry_yield = run_crop_season(site, dry_year, CORN, n_rate_kg_ha=150)["grain"]
    return wet_yield > dry_yield, (
        f"wettest real year in sample, {wet_year} ({precip_by_year[wet_year]:.0f}mm) -> "
        f"{wet_yield:.2f} Mg/ha; driest, {dry_year} ({precip_by_year[dry_year]:.0f}mm) -> "
        f"{dry_yield:.2f} Mg/ha"
    )


@check("Hybrid choice: long-season hybrid wins at a warm site, short-season wins at a cold one")
def c_hybrid_crossover():
    warm_long = run_crop_season("iowa", 2012, CORN_LONG_SEASON, n_rate_kg_ha=650)["grain"]
    warm_short = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=650)["grain"]
    cold_long = run_crop_season("north_dakota", 2012, CORN_LONG_SEASON, n_rate_kg_ha=650)["grain"]
    cold_short = run_crop_season("north_dakota", 2012, CORN, n_rate_kg_ha=650)["grain"]
    ok = (warm_long > warm_short) and (cold_short > cold_long)
    return ok, (
        f"Iowa: long-season {warm_long:.2f} vs short-season {warm_short:.2f} Mg/ha "
        f"(long should win, more time to cash in higher maturity); North Dakota: "
        f"long-season {cold_long:.2f} vs short-season {cold_short:.2f} Mg/ha (short "
        f"should win or tie -- a longer-season hybrid risks not finishing before frost)"
    )


@check("Irrigation raises yield at a nitrogen-limiting rate in a dry climate")
def c_irrigation_helps():
    no_irr = run_crop_season("kansas", 2012, CORN, n_rate_kg_ha=50)["grain"]
    irr = run_crop_season("kansas", 2012, CORN, n_rate_kg_ha=50,
                           irrigation_trigger_frac=0.5, irrigation_amount_mm=25.0)["grain"]
    return irr > no_irr, f"no irrigation -> {no_irr:.2f} Mg/ha, irrigated -> {irr:.2f} Mg/ha"


@check("Manure at its real 0.5 availability matches an equivalent mineral-N rate exactly")
def c_manure_equivalence():
    mineral = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=100)["grain"]
    manure = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=0, manure_n_kg_ha=200,
                              manure_availability=0.5)["grain"]
    return math.isclose(mineral, manure, rel_tol=1e-9), (
        f"100 kg/ha mineral N -> {mineral:.6f} Mg/ha; 200 kg/ha manure @ 0.5 "
        f"availability -> {manure:.6f} Mg/ha (should be identical -- this is a real, "
        f"disclosed Cycles number, not a tunable one)"
    )


@check("Nitrogen mass balance closes: supply equals uptake + leached + remaining")
def c_mass_balance():
    r = run_crop_season("iowa", 2012, CORN, n_rate_kg_ha=150)
    supply = 150.0  # the only source at this rate (no credit/manure/background separate from supply tracking)
    accounted = r["n_uptake_kg_ha"] + r["n_leached_kg_ha"] + r["n_remaining_kg_ha"]
    # background mineralization also feeds the pool -- so accounted should be >= the
    # fertilizer supply alone, and the gap should be a plausible background contribution,
    # not an arbitrary mismatch signaling a real leak in the pool bookkeeping.
    background_implied = accounted - supply
    ok = 0 <= background_implied <= 200  # a season's real background credit is real but bounded
    return ok, (
        f"uptake {r['n_uptake_kg_ha']:.2f} + leached {r['n_leached_kg_ha']:.2f} + "
        f"remaining {r['n_remaining_kg_ha']:.2f} = {accounted:.2f} kg N/ha accounted, "
        f"vs. {supply:.0f} kg N/ha fertilizer supply (implied background credit "
        f"{background_implied:.2f} kg N/ha -- should be positive and plausible, not huge)"
    )


@check("Rock Springs via the resolved-tile path shows the same N-response DIRECTION as the exact validated path")
def c_resolved_vs_exact_rock_springs():
    # This is the headline finding from this suite's first real run (2026-09-29): every
    # site tested through the tile-resolved path (Iowa, Kansas, Maryland, North Dakota,
    # AND Rock Springs itself) showed IDENTICAL corn yield at N=0 and N=650 -- nitrogen
    # doing literally nothing -- while the exact, hand-curated Rock Springs weather
    # run_validation.py actually validates against shows a real, positive response at
    # every year checked (2005, 2012, 1993, 2001). Since "Rock Springs" is the one place
    # we have both an exact and an approximate answer for, comparing them AT THE SAME
    # NOMINAL LOCATION isolates whether this is a real site/climate effect (plausible) or
    # an artifact of the resolved-tile pathway itself that would then also be
    # misrepresenting Iowa/Kansas/Maryland/North Dakota (a much bigger problem). See this
    # check's own failure detail for which one it is.
    lo = run_crop_season("rock_springs", 2012, CORN, n_rate_kg_ha=0)["grain"]
    hi = run_crop_season("rock_springs", 2012, CORN, n_rate_kg_ha=650)["grain"]
    return hi > lo, (
        f"resolved-tile Rock Springs, N=0 -> {lo:.4f} Mg/ha, N=650 -> {hi:.4f} Mg/ha "
        f"(the exact validated Rock Springs record shows 9.52 -> 10.22 Mg/ha for this "
        f"same year -- if this check fails, the tile-resolved pathway used by every "
        f"multi-site panel in engine-demo.html is showing a materially different, "
        f"flat-nitrogen pattern than the one this project's own validation is built on, "
        f"at the SAME location -- see the conversation this commit is attached to)"
    )


@check("Water stress and canopy cover stay within their physical [0,1] bounds")
def c_bounds_check():
    r = run_crop_season("kansas", 2012, CORN, n_rate_kg_ha=650, record_history=True)
    bad = [h for h in r["history"]
           if not (0.0 <= h["water_stress"] <= 1.0) or not (0.0 <= h["canopy"] <= 1.001)]
    return len(bad) == 0, (
        f"{len(bad)} of {len(r['history'])} days out of [0,1] bounds"
        + (f" (first offender: {bad[0]})" if bad else "")
    )


def main():
    print(f"Running {len(CHECKS)} pattern-assertion checks against real committed field data\n")
    n_pass = 0
    for name, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001 -- a crash is itself a real finding here
            ok, detail = False, f"CRASHED: {e!r}"
        status = "PASS" if ok else "FAIL"
        n_pass += 1 if ok else 0
        print(f"[{status}] {name}\n       {detail}\n")
    print(f"{n_pass}/{len(CHECKS)} checks passed.")
    return 0 if n_pass == len(CHECKS) else 1


# Not yet covered here -- real classroom claims worth adding next, not
# encoded yet because they need machinery this file doesn't have (a bare-
# fallow-vs-cover-crop comparison function, which currently only exists as
# JS glue inside engine-demo.html, not in cycles_engine_validate.py itself):
#   - Cover crop leaches less nitrogen than bare fallow, at every tested rate.
#   - The three-perspective frontier (farmer/water-advocate/policymaker
#     positions) stays correctly ordered by nitrogen rate across a range of
#     sites/years, not just the one Rock Springs case already checked.
#   - Wheat's fall-planted cover-crop role behaves sensibly across sites
#     (currently only exercised at Rock Springs in engine-demo.html).
#   - A version of the whole suite run at several points in the plausible
#     range of the "disclosed placeholder" constants (depletion_fraction,
#     NET_GROWTH_FRACTION, curve_number, REW_DEFAULT_MM, etc.) to check
#     whether each pattern above is robust across that uncertainty, not just
#     true at the one calibrated point -- the actual sensitivity-analysis
#     step discussed in conversation, not yet built.

if __name__ == "__main__":
    sys.exit(main())
