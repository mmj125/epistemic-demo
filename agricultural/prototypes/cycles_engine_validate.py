"""
Agricultural unit -- from-scratch agroecosystem engine (water balance,
canopy growth, yield), independently implemented from published sources,
NOT derived from or containing any of the real Cycles model's source code
or binary (see CLAUDE.md, "Agricultural unit" section, for the full
licensing story on why that distinction matters for this project).

Sources used:
  - Kemanian et al. 2024, "The Cycles Agroecosystem Model: Fundamentals,
    Testing, and Applications," Computers and Electronics in Agriculture
    227, 109510 -- main governing equations (numbered Eq. 1-7 in-line
    below), all public, peer-reviewed.
  - The paper's Supplemental Information document (equations labeled
    Eq. SI.1-15 below) -- curve-number runoff, biomass partitioning,
    harvest index. Two of its typeset equations (Eq. SI.1's runoff
    denominator, Eq. SI.6's CN_wet) have what looks like a systematic
    sign error against the well-established external methods they cite
    (USDA-SCS 1972; Williams et al. 2012) -- implemented here with the
    mathematically-correct sign, flagged at each spot.
  - Saxton, K.E., Rawls, W.J., 2006, "Soil water characteristic estimates
    by texture and organic matter for hydrologic solutions," SSSAJ 70(5)
    -- standard public pedotransfer function, cited by the Cycles papers
    but not itself part of Cycles.
  - Real per-crop parameters (radiation/transpiration use efficiency,
    phenology thresholds, harvest index bounds, temperature-transpiration
    thresholds) come from the actual GenericCrops.crop file bundled with
    the free public Cycles v1.4.4 binary release -- these are input data
    the software reads at runtime, not compiled source, and are the real
    numbers, not literature approximations.

Validated against real Cycles v1.4.4 binary output (Rock Springs, PA,
continuous corn, 1980-2016, the exact sample scenario bundled with the
release) -- NOT reproduced here; see "How to reproduce validation" below.

Status as of this validation pass:
  - Reference evapotranspiration (ETo, FAO-56 Penman-Monteith): matches
    real Cycles' own "REFERENCE ET" output to within 0.008 mm/day mean
    absolute error across the full 37-year, 13,515-day record. Essentially
    exact -- this is a standard external public formula, not a Cycles
    invention, so an exact match is expected of a correct implementation.
  - Curve-number runoff: right order of magnitude, not yet a clean match.
    The model's own moisture-adjustment factor (fwc) is described only in
    words in the supplement ("1 for soil saturated to 0.6m depth,
    decreasing to zero if air-dry, depth-weighted toward the surface"),
    not given as an exact formula -- this file's implementation is a
    defensible interpretation of that description, not a verified exact
    match.
  - Soil moisture: real signal, correlates with real layer-1 output but
    was biased dry until canopy cover was coupled in (bare soil evaporates
    too aggressively without a crop shading it for ~4 months of the year).
  - Crop growth and yield: strong year-to-year correlation with real
    output (0.74-0.80) once actual root-zone soil-moisture stress was
    coupled into transpiration (real crops can't transpire at potential
    demand when the soil is actually dry -- the first version of this
    model had no such limit and would have taught students the wrong
    lesson about what drives a bad year, exactly the failure mode a crude
    first attempt at this hit before the real equations were sourced).
    Absolute yield level still ran ~20-25% high after that fix, and after
    testing four candidate causes (canopy cover shape: not the cause;
    nitrogen stress: real Cycles shows none in this well-fertilized
    scenario, so not applicable; CO2 scaling of radiation-use-efficiency:
    undisclosed in either source AND implausible to be large for a C4
    crop like corn; cold-temperature transpiration stress: real mechanism,
    correctly implemented, negligible effect at this site) none of them
    closed the remaining gap. Rather than keep guessing, a disclosed
    calibration factor is applied instead -- see "calibration_factor" below.
    IMPORTANT: validating soybean and wheat afterward turned up a real bug
    contributing to that gap, not just an unidentified mechanism -- harvest
    index was being applied to *total* biomass, but real Cycles' own
    HARVEST_INDEX column is defined against *aboveground* biomass only
    (verified: 11.61 / (26.17 - 3.48 root) = 0.5117, matching the real
    reported value exactly; 11.61 / 26.17 does not). Fixed by adding real
    shoot/root partitioning (Eq. SI.8-11) before applying HI. Calibration
    factors below are the *residual* needed after that fix, and are
    crop-specific, not a universal constant -- soybean's residual runs the
    opposite direction from corn's (under, not over), confirming this
    isn't one missing mechanism that scales uniformly across crops.

crop["calibration_factor"] is an empirical correction, not physics --
computed per crop by fitting this model's mean yield to real Cycles' mean
yield for a validated scenario. It does not change
year-to-year correlation (multiplying every value by a constant preserves
ranking), only the absolute scale. Treat it as covering whatever specific
mechanism this validation pass didn't identify, not as license to trust
the model's absolute numbers for a different crop, soil, or location
without re-checking against real output there too.

How to reproduce validation: this file does not bundle Cycles' own sample
weather/soil/crop/operation files or any of its generated output --
deliberately, pending resolution of whether republishing Cycles' output
data requires the same permission as the model itself (see CLAUDE.md).
Download Cycles v1.4.4 from the official GitHub release
(https://github.com/PSUmodeling/Cycles/releases) to get RockSprings.weather,
GenericHagerstown.soil, GenericCrops.crop, and ContinuousCorn.operation/.ctrl,
run the real binary once to get real output to compare against, and point
REFERENCE_DATA_DIR below at that directory.
"""
import math

REFERENCE_DATA_DIR = "/tmp/cycles-run"  # set to a local Cycles v1.4.4 sample directory to reproduce validation

# Calibration factors live per-crop, in each crop's own dict (see module docstring).


# ---------------------------------------------------------------------------
# Reference evapotranspiration -- FAO-56 Penman-Monteith (Allen et al. 1998).
# Standard external public method, not a Cycles invention. Validated to
# 0.008 mm/day mean absolute error against real Cycles output.
# ---------------------------------------------------------------------------

def eto_fao56(doy, tmax, tmin, rs, rhmax, rhmin, wind_z, lat_deg, alt_m=0.0, wind_height_m=10.0):
    tmean = (tmax + tmin) / 2
    delta = 4098 * (0.6108 * math.exp(17.27 * tmean / (tmean + 237.3))) / (tmean + 237.3) ** 2
    P = 101.3 * ((293 - 0.0065 * alt_m) / 293) ** 5.26
    gamma = 0.000665 * P

    def e0(t):
        return 0.6108 * math.exp(17.27 * t / (t + 237.3))
    es = (e0(tmax) + e0(tmin)) / 2
    ea = (e0(tmin) * rhmax / 100 + e0(tmax) * rhmin / 100) / 2

    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * doy)
    decl = 0.409 * math.sin(2 * math.pi / 365 * doy - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(decl))))
    Gsc = 0.0820
    Ra = (24 * 60 / math.pi) * Gsc * dr * (
        ws * math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.sin(ws)
    )
    Rso = (0.75 + 2e-5 * alt_m) * Ra
    Rns = (1 - 0.23) * rs
    sigma = 4.903e-9
    tmax_k, tmin_k = tmax + 273.16, tmin + 273.16
    rs_rso = min(1.0, rs / Rso) if Rso > 0 else 0
    Rnl = sigma * ((tmax_k ** 4 + tmin_k ** 4) / 2) * (0.34 - 0.14 * math.sqrt(max(0, ea))) * (1.35 * rs_rso - 0.35)
    Rn = Rns - Rnl
    u2 = wind_z * 4.87 / math.log(67.8 * wind_height_m - 5.42)
    num = 0.408 * delta * Rn + gamma * (900 / (tmean + 273)) * u2 * (es - ea)
    den = delta + gamma * (1 + 0.34 * u2)
    return num / den


# ---------------------------------------------------------------------------
# Saxton-Rawls (2006) pedotransfer -- field capacity / wilting point /
# saturation from soil texture. Standard public method.
# ---------------------------------------------------------------------------

def saxton_rawls(sand_pct, clay_pct, om_pct):
    S, C, OM = sand_pct / 100, clay_pct / 100, om_pct
    theta_1500t = (-0.024 * S + 0.487 * C + 0.006 * OM
                   + 0.005 * (S * OM) - 0.013 * (C * OM) + 0.068 * (S * C) + 0.031)
    theta_1500 = theta_1500t + (0.14 * theta_1500t - 0.02)
    theta_33t = (-0.251 * S + 0.195 * C + 0.011 * OM
                 + 0.006 * (S * OM) - 0.027 * (C * OM) + 0.452 * (S * C) + 0.299)
    theta_33 = theta_33t + (1.283 * theta_33t ** 2 - 0.374 * theta_33t - 0.015)
    theta_s33t = (0.278 * S + 0.034 * C + 0.022 * OM
                  - 0.018 * (S * OM) - 0.027 * (C * OM) - 0.584 * (S * C) + 0.078)
    theta_s33 = theta_s33t + (0.636 * theta_s33t - 0.107)
    theta_sat = theta_33 + theta_s33 - 0.097 * S + 0.043
    return dict(pwp=max(0.01, theta_1500), fc=max(0.02, theta_33), sat=max(0.05, theta_sat))


OM_FROM_SOC = 1.72  # standard Van Bemmelen conversion, SOC% -> OM%


# ---------------------------------------------------------------------------
# Curve-number runoff (Eq. SI.1-7). Sign corrected per module docstring.
# ---------------------------------------------------------------------------

def slope_factor(slp):
    return 1.1 - slp / (slp + math.exp(3.7 + 0.02 * slp))


def cn_dry(cnb):
    """Real SCS Antecedent Soil Moisture Condition I (dry) curve number, Matt-provided
    directly from SWAT+ documentation (Eq 2:1.1.4) 2026-09-22, replacing this file's earlier
    rounded NEH-4-style approximation (cnb/(2.3-0.013*cnb)) -- both are legitimate standard
    forms for the same conversion and agree within ~1-2.5 CN points across a realistic 50-95
    CN2 range (checked numerically before swapping), so this is a real refinement to the exact,
    citable formula, not a correction of something wrong."""
    return cnb - (20 * (100 - cnb)) / ((100 - cnb) + math.exp(2.533 - 0.0636 * (100 - cnb)))


def cn_wet(cnb):
    """Real SCS Antecedent Soil Moisture Condition III (wet) curve number, same source and
    swap as cn_dry() above (SWAT+ Eq 2:1.1.5). Previously: cnb/(0.4+0.0058*cnb), with a
    comment noting the SI itself showed the sign wrong ("0.4 - 0.006xCNb") -- this SWAT+ form
    sidesteps that ambiguity entirely since it's a different, independently-sourced equation
    family, not a reading of Cycles' own (still possibly miskeyed) SI text."""
    return cnb * math.exp(0.00673 * (100 - cnb))


def moisture_adjusted_cn(cnb, fwc, slope_pct):
    cnd, cnw = cn_dry(cnb), cn_wet(cnb)
    return cnd + (cnw - cnd) * fwc


def compute_fwc(layers, depth_m=0.6):
    """The curve-number moisture-adjustment factor moisture_adjusted_cn() needs, computed
    from actual soil state -- described only in words in the SI ("1 for soil saturated to
    0.6m depth, decreasing to zero if air-dry, depth-weighted toward the surface"), no exact
    formula given (QUESTIONS_FOR_DEVS.md item 1). This is a defensible reading of that
    description, not a verified match: for each layer within the top 0.6m, a 0-1 saturation
    fraction (theta-pwp)/(sat-pwp), weighted by that layer's remaining distance to 0.6m (so
    a shallower layer's moisture counts more -- "depth-weighted toward the surface") and by
    how much of the 0.6m window the layer actually occupies."""
    depth, weighted_sum, weight_total = 0.0, 0.0, 0.0
    for l in layers:
        if depth >= depth_m:
            break
        d = min(l["thick"], depth_m - depth)
        sat_frac = (l["theta"] - l["pwp"]) / (l["sat"] - l["pwp"]) if l["sat"] > l["pwp"] else 0.0
        sat_frac = max(0.0, min(1.0, sat_frac))
        weight = (depth_m - depth) * d  # more weight on shallower, and on thicker-within-window, layers
        weighted_sum += sat_frac * weight
        weight_total += weight
        depth += l["thick"]
    return weighted_sum / weight_total if weight_total > 0 else 0.0


def runoff_mm(win, cn, slope_pct):
    S = 254 * slope_factor(slope_pct) * (100 / cn - 1)
    if win <= 0.2 * S:
        return 0.0
    return (win - 0.2 * S) ** 2 / (win + 0.8 * S)  # supplement showed "Win-0.8S"; SCS derivation forces +0.8S


# ---------------------------------------------------------------------------
# Layered soil water balance -- cascading bucket (a defensible simplification
# of the paper's Eq. 1-2 capacitance-weighted redistribution integral, not a
# literal implementation of it -- see module docstring) plus bare-soil
# evaporation (no disclosed formula in either source; standard proxy used).
# ---------------------------------------------------------------------------

def redistribute(layers, water_in_mm):
    remaining = water_in_mm
    for l in layers:
        cap_mm = max(0.0, (l["fc"] - l["theta"]) * l["thick"] * 1000)
        add = min(remaining, cap_mm + max(0.0, (l["sat"] - l["fc"]) * l["thick"] * 1000))
        l["theta"] += add / (l["thick"] * 1000)
        remaining -= add
        excess_mm = max(0.0, (l["theta"] - l["fc"]) * l["thick"] * 1000)
        l["theta"] -= excess_mm / (l["thick"] * 1000)
        remaining += excess_mm
    return remaining


def infiltrate(layers, water_in_mm, curve_number, slope_pct):
    """One day's curve-number runoff (Eq. SI.1-7, sign-corrected) followed by infiltration
    (redistribute()) -- shared by simulate_season()'s main loop and its optional spin-up
    window, so the two can't drift apart. Previously runoff_mm()/moisture_adjusted_cn()
    existed but were never actually called anywhere in the water balance (all precipitation
    went straight to infiltration) -- see CLAUDE.md, 2026-09-22, for why this was flagged as
    a real gap rather than a deliberate simplification: it means every drop of rain currently
    enters the soil, which retains more water than reality especially in a drier climate."""
    if water_in_mm <= 0:
        return 0.0, 0.0
    fwc = compute_fwc(layers)
    cn = moisture_adjusted_cn(curve_number, fwc, slope_pct)
    runoff = runoff_mm(water_in_mm, cn, slope_pct)
    drainage_mm = redistribute(layers, water_in_mm - runoff)
    return drainage_mm, runoff


def soil_evaporation(layers, eto_mm, canopy_cover_frac):
    l0 = layers[0]
    demand_mm = eto_mm * (1 - canopy_cover_frac)
    available_mm = max(0.0, (l0["theta"] - l0["pwp"]) * l0["thick"] * 1000)
    actual_mm = min(demand_mm, available_mm)
    l0["theta"] -= actual_mm / (l0["thick"] * 1000)
    return actual_mm


def water_stress_response(avail_frac, depletion_fraction=0.5):
    """Maps root-zone available-water fraction (0=at wilting point, 1=at field capacity) to
    a 0-1 multiplier on potential transpiration (1=no stress). This IS the real, standard
    FAO-56 water-stress coefficient Ks (Allen et al. 1998, Ch. 8, Eq. 84), not an invented
    shape -- confirmed 2026-09-22 by extracting the real chapter text (Matt-provided, this
    sandbox's network egress blocks fao.org directly) and checking the exact formula against
    the source's own worked numeric example (Example 37): Ks=(TAW-Dr)/(TAW-RAW), which in
    this engine's own avail_frac/depletion_fraction terms reduces exactly to
    avail_frac/(1-depletion_fraction), clipped to [0,1] -- reproduced the source's own 0.97
    and 0.62 at the example's Day 3 and Day 10 to the given precision, not just a plausible
    match. depletion_fraction (FAO-56's "p", real Table 22 values, not a literature guess):
    Maize/wheat 0.55, soybean 0.50 -- the crop dict's own depletion_fraction field, defaulting
    to 0.50 (FAO-56's own "commonly used for many crops" value) when a crop doesn't set one.

    A DIFFERENT alternative was tried and reverted earlier the same day (2026-09-22, see
    CLAUDE.md for the full account) -- worth recording why it's not this: paired real Cycles'
    own daily WATER STRESS output against its own daily soil moisture across the full 37-year
    Rock Springs record and fit a power-law shape, stress=(avail_frac/0.45)^0.51 --
    essentially sqrt(avail_frac/0.45). Plugged in, correlation got WORSE for every crop.
    Notice the threshold that fit found, 0.45, exactly equals 1-0.55 -- the real FAO-56
    threshold for corn/wheat found independently just now. The earlier attempt had the right
    THRESHOLD and the wrong SHAPE (a concave power curve where the real, standard relationship
    is plain linear) -- it was found by grid-searching threshold and power together, and a
    worse-fitting linear+0.45 combination lost to a better-fitting sqrt+0.45 one in that search,
    even though linear+0.45 is the physically correct answer. This version tests that specific,
    corrected hypothesis instead: keep the linear shape, use the real per-crop threshold."""
    threshold = 1.0 - depletion_fraction
    if threshold <= 0:
        return 1.0
    return max(0.0, min(1.0, avail_frac / threshold))


def root_zone_availability(layers, root_depth_m):
    depth, avail, capacity = 0.0, 0.0, 0.0
    for l in layers:
        if depth >= root_depth_m:
            break
        d = min(l["thick"], root_depth_m - depth)
        avail += max(0.0, l["theta"] - l["pwp"]) * d * 1000
        capacity += (l["fc"] - l["pwp"]) * d * 1000
        depth += l["thick"]
    return avail / capacity if capacity > 0 else 1.0


def extract_transpiration(layers, root_depth_m, tr_mm):
    remaining, depth = tr_mm, 0.0
    for l in layers:
        if depth >= root_depth_m or remaining <= 0:
            break
        d = min(l["thick"], root_depth_m - depth)
        avail_mm = max(0.0, l["theta"] - l["pwp"]) * d * 1000
        take = min(remaining, avail_mm)
        l["theta"] -= take / (l["thick"] * 1000)
        remaining -= take
        depth += l["thick"]
    return tr_mm - remaining


# Real per-implement tillage data, parsed directly from /tmp/cycles-run/input/till.txt
# (Matt's own local Cycles v1.4.4 sample files, not committed to this repo, same category
# as RockSprings.weather) -- (depth_m, mixing_efficiency) for all 86 real named implements
# Cycles ships. mixing_efficiency is the real, disclosed "implement-specific coefficient"
# Kemanian et al. 2024 Sec. 2.6 references only in words -- these are the actual numbers.
TILLAGE_IMPLEMENTS = {
    "Bale_straw_or_residue": (0.01, 0.0),
    "Bed_shaper": (0.05, 0.071554),
    "Bedder_hipper_disk_hiller": (0.15, 0.8),
    "Bulldozer_clearing": (0.3, 0.8),
    "Burn_residue_high_intensity": (0.01, 0.01),
    "Burn_residue_low_intensity": (0.01, 0.01),
    "Chisel_st_pt": (0.25, 0.265919),
    "Chisel_sweep_shovel": (0.2, 0.265919),
    "Chisel_twisted_shovel": (0.2, 0.447042),
    "Cultipacker_roller": (0.05, 0.265919),
    "Cultivator_field_6-12_in_sweeps": (0.12, 0.202386),
    "Cultivator_field_w_spike_points": (0.12, 0.371806),
    "Cultivator_hipper_disk_hiller_on_beds": (0.12, 0.572433),
    "Cultivator_off_bar_w_disk_hillers_on_beds": (0.12, 0.308274),
    "Disk_offset_heavy": (0.15, 0.657771),
    "Disk_offset_heavy_>12_in_depth": (0.3, 0.8),
    "Disk_tandem_heavy_primary_op": (0.2, 0.657771),
    "Disk_tandem_secondary_op": (0.1, 0.265919),
    "Drill_air_seeder_sweep_or_band_opener": (0.08, 0.497198),
    "Drill_deep/semi-deep_furrow_12_to_18_in_spacing": (0.12, 0.497198),
    "Drill_heavy_direct_seed_dbl_disk_opnr": (0.1, 0.639427),
    "Drill_or_air_seeder_double_disk_openers_7-10_in_spac": (0.08, 0.071554),
    "Drill_or_air_seeder_hoe/chisel_openers_6-12_in_spac": (0.08, 0.639427),
    "Drill_or_air_seeder_hoe_opener_in_hvy_residue": (0.08, 0.497198),
    "Drill_or_airseeder_double_disk": (0.08, 0.497198),
    "Drill_or_airseeder_double_disk_opener_w_fert_openers": (0.08, 0.639427),
    "Drill_or_airseeder_double_disk_w_fluted_coulters": (0.09, 0.639427),
    "Drill_or_airseeder_offset_double_disk_openers": (0.08, 0.259212),
    "Fert_applic_anhyd_knife_12_in": (0.12, 0.265919),
    "Fert_applic_anhyd_knife_30_in": (0.12, 0.120616),
    "Fert_applic_deep_plcmt_hvy_shnk": (0.15, 0.371806),
    "Fert_applic_strip-till_30_in": (0.12, 0.265919),
    "Fert_applic_surface_broadcast": (0.005, 0.0),
    "Furrow_diker": (0.15, 0.265919),
    "Furrow_shaper_torpedo": (0.1, 0.0),
    "Graze_continuous": (0.02, 0.026833),
    "Graze_rotational": (0.02, 0.026833),
    "Graze_stubble_or_residue": (0.03, 0.026833),
    "Harrow_coiled_tine": (0.08, 0.120616),
    "Harrow_heavy_or_rotary": (0.08, 0.265919),
    "Harrow_spike_tooth": (0.08, 0.075895),
    "Harrow_tine_on_beds": (0.08, 0.120616),
    "Harvest_corn_silage_or_forage_sorghum": (0.02, 0.0),
    "Harvest_cotton": (0.02, 0.0),
    "Harvest_grain": (0.01, 0.0),
    "Harvest_grass_or_legume_seed": (0.01, 0.0),
    "Harvest_hay": (0.01, 0.0),
    "Harvest_peanut_digger": (0.1, 0.8),
    "Harvest_root_crops_digger": (0.2, 0.8),
    "Harvest_rootcrops_manually": (0.15, 0.202386),
    "Harvest_sugarcane": (0.02, 0.0),
    "Harvest_tobacco": (0.18, 0.0),
    "Kill_Crop": (0.0, 0.0),
    "Manure_injector": (0.1, 0.447042),
    "Manure_spreader": (0.01, 0.0),
    "Mower_swather_windrower": (0.01, 0.0),
    "Mulch_treader": (0.04, 0.371806),
    "Permeable_weed_barrier_applicator": (0.04, 0.202386),
    "Planter_double_disk_opnr": (0.08, 0.071554),
    "Planter_double_disk_opnr_18_in_rows": (0.08, 0.120616),
    "Planter_double_disk_opnr_w_fluted_coulter": (0.08, 0.071554),
    "Planter_in-row_subsoiler": (0.1, 0.120616),
    "Planter_ridge_till": (0.15, 0.447042),
    "Planter_small_veg_seed": (0.02, 0.0),
    "Planter_strip_till": (0.08, 0.120616),
    "Planter_sugarcane": (0.05, 0.026833),
    "Planter_transplanter_vegetable": (0.1, 0.026833),
    "Planting_broadcast_seeder": (0.01, 0.0),
    "Plastic_mulch_apply": (0.05, 0.202386),
    "Plastic_mulch_remove": (0.05, 0.202386),
    "Plow_disk": (0.18, 0.657771),
    "Plow_moldboard": (0.18, 0.8),
    "Plow_moldboard_conservation": (0.18, 0.657771),
    "Residue_row_cleaner": (0.02, 0.265919),
    "Rodweeder": (0.05, 0.265919),
    "Roller_corrugated_packer": (0.02, 0.153324),
    "Roller_smooth": (0.02, 0.026833),
    "Rotary_hoe": (0.05, 0.071554),
    "Rototiller": (0.05, 0.8),
    "Sprayer": (0.005, 0.0),
    "Stalk_puller": (0.18, 0.153324),
    "Striptiller_w_middlebuster_on_beds": (0.15, 0.572433),
    "Subsoiler": (0.25, 0.120616),
    "Subsoiler_bedder(ripper/hipper)": (0.25, 0.12),
    "Subsoiler_ripper_24_to_40_in_deep": (0.25, 0.120616),
    "Sweep_plow": (0.15, 0.0),
}


def mix_tilled_layers(layers, depth_m, mixing_efficiency):
    """Homogenizes soil moisture within the tilled depth, weighted by the real implement's
    mixing_efficiency (from TILLAGE_IMPLEMENTS above). Real Cycles applies this exact
    coefficient to mixing organic carbon/nitrogen pools in its six-pool soil system
    (Sec. 2.6) -- this engine has no per-layer C/N pools (nitrogen here is one whole-profile
    pool, not per layer, see simulate_season's docstring), so there is nothing of that kind
    to mix. Applying the real coefficient to soil moisture instead is a disclosed
    reinterpretation of a real number for a different, but also real, physical effect of the
    same tillage pass (a tillage pass does homogenize moisture in the disturbed zone) -- not
    a reproduction of Cycles' own documented use of this coefficient. Soil hydraulic
    properties (fc/pwp/sat) are left untouched; blending those too would be a further,
    undisclosed extrapolation beyond what's defensible here.

    Uses the same fractional-layer-overlap handling as root_zone_availability/
    extract_transpiration above (a tillage depth ending partway through a layer only mixes
    that fraction of it), not a whole-layer simplification.
    """
    if mixing_efficiency <= 0 or depth_m <= 0:
        return
    depth, water_mm, zone_mm = 0.0, 0.0, 0.0
    affected = []  # (layer, fraction of this layer's thickness inside the tilled depth)
    for l in layers:
        if depth >= depth_m:
            break
        d = min(l["thick"], depth_m - depth)
        affected.append((l, d / l["thick"]))
        water_mm += l["theta"] * d * 1000
        zone_mm += d * 1000
        depth += l["thick"]
    if not affected or zone_mm <= 0:
        return
    mean_theta = water_mm / zone_mm
    for l, frac in affected:
        blend = frac * mixing_efficiency
        l["theta"] = l["theta"] * (1 - blend) + mean_theta * blend


# ---------------------------------------------------------------------------
# Soil-temperature-triggered planting. No disclosed formula in either
# source for soil temperature itself (same category of gap as soil
# evaporation) -- standard lag-filter proxy of air temperature used
# instead, validated against real per-year planting dates (2.65 days mean
# absolute error across the 37-year record).
# ---------------------------------------------------------------------------

def simulate_soil_temp(daily_tmean, k=0.15, t0=None):
    tsoil = t0 if t0 is not None else daily_tmean[0]
    out = []
    for t in daily_tmean:
        tsoil = tsoil + k * (t - tsoil)
        out.append(tsoil)
    return out


def find_planting_doy(tsoil_by_doy, window, min_soil_temp):
    for doy in range(window[0], window[1] + 1):
        if doy in tsoil_by_doy and tsoil_by_doy[doy] > min_soil_temp:
            return doy
    return window[1]


# ---------------------------------------------------------------------------
# Canopy cover (Eq. 6) and radiation/water-limited growth (Eq. 3-5) with
# real soil moisture coupled into actual (not just potential) transpiration
# -- the single biggest fix in this validation pass, see module docstring.
#
# The paper's default shape constants (6, -20, -15, 16) are stated to
# "represent a normalized plant density (PDf) of 1" for the corn case it
# demonstrates -- they do NOT transfer to other crops unchanged. Verified
# directly for winter wheat: at the point real Cycles shows 0.746 canopy
# cover, the corn defaults predict 0.886, a real, checked gap (thermal-time
# accumulation was ruled out first as the cause -- ours matched real Cycles
# to within 2.5%). A wheat-specific refit (5, -14, -15, 16), fit against 13
# real FRAC INTERCEP data points across one real season, improves the level
# bias (yield ratio 1.51 -> 1.40) but does NOT fix wheat's weak year-to-year
# correlation (0.362 -> 0.253, actually worse) -- the real driver of that is
# still unidentified. On the dev-questions list, not something to keep
# guessing at blindly (see QUESTIONS_FOR_DEVS.md).
# ---------------------------------------------------------------------------

DEFAULT_CANOPY_SHAPE = (6, -20, -15, 16)   # the paper's stated defaults
CORN_CANOPY_SHAPE = (6, -20, -12, 12)      # refit from real corn FRAC INTERCEP data --
                                            # the paper's own defaults run ~5% high at peak
                                            # for corn itself, negligible for grain corn
                                            # (harvest happens well into senescence, growth
                                            # has already stopped) but compounds into a real,
                                            # growing error for silage corn (harvested at 85%
                                            # of maturity, mid-peak-growth) -- see module
                                            # docstring and QUESTIONS_FOR_DEVS.md.


def thermal_time_increment(tx, tn, base_t, opt_t, max_t):
    tmean = (tx + tn) / 2
    if tmean <= base_t or tmean >= max_t:
        return 0.0
    if tmean <= opt_t:
        return tmean - base_t
    return (opt_t - base_t) * (max_t - tmean) / (max_t - opt_t)


def canopy_cover(ttf_norm, eix=1.0, shape=DEFAULT_CANOPY_SHAPE):
    a, b, c, d = shape
    ttf_norm = max(0.0, ttf_norm)
    return eix / (1 + math.exp(a + b * ttf_norm) + math.exp(c + d * ttf_norm))


def transpiration_temp_factor(tmean, min_t, threshold_t):
    if tmean <= min_t:
        return 0.0
    if tmean >= threshold_t:
        return 1.0
    return (tmean - min_t) / (threshold_t - min_t)


TTF50_SHOOT_PARTITION = 0.5  # Eq. SI.8-11's own half-max point isn't given a numeric value anywhere
                             # in either source -- using the literal reading of its name ("TTf50")


def shoot_fraction(ttf, fsti, fstf, ttf50=TTF50_SHOOT_PARTITION):
    """Eq. SI.8-11: modified Michaelis-Menten allocation of new growth to shoot vs. root."""
    ttf = max(1e-6, ttf)
    return fsti + (fstf - fsti) / (1 + (ttf50 / ttf) ** 4)


# ---------------------------------------------------------------------------
# Simplified mineral-N balance -- a student-facing knob (fertilizer rate),
# NOT an attempt at Cycles' own six-pool soil carbon/nitrogen system (that
# full model is explicitly out of scope for v1, see CLAUDE.md). This is a
# standard "critical N dilution curve" (crop N demand falls as biomass
# accumulates -- Justes et al. 1994 / Lemaire's dilution theory, a widely
# used simplification, not a Cycles invention) driven by each crop's real
# N_MAX_CONCENTRATION and N_DILUTION_SLOPE from GenericCrops.crop (corn:
# 0.055 g/g, 0.4; soybean: 0.07 g/g, 0.4), plus a simple "well-mixed
# reservoir" leaching model that reuses the water balance's own daily
# drainage output (redistribute()'s return value, previously discarded) --
# leaching loss = drainage_mm * (N remaining / current profile water, mm),
# i.e. nitrate washes out in proportion to how much water leaves the profile
# and how concentrated the remaining N pool is. Neither piece is a verified
# Cycles formula; both are disclosed, defensible standard proxies, same
# spirit as this file's existing soil-evaporation and fwc approximations.
#
# Legume crops (soybean: LEGUME=1 in the real crop file) are deliberately
# exempt -- real soybeans fix atmospheric N via rhizobia symbiosis and are
# not normally nitrogen-fertilized, so a fertilizer-rate knob correctly
# has little/no effect on them. This isn't a modeled fixation submodel
# (that level of detail isn't disclosed or needed for a v1 knob); it's a
# direct, correct consequence of the same LEGUME flag already read from
# the crop file elsewhere in this codebase.
#
# When n_rate_kg_ha is left as None (the default), none of this runs and
# behavior is byte-identical to before this feature existed -- verified by
# re-running run_validation.py / run_validation_rotation2.py unchanged.
NCRIT_FLOOR_MGHA = 1.0  # dilution curve is flat (at N_MAX_CONCENTRATION) below this biomass; standard convention

# Background soil-supplied nitrogen from organic matter mineralization -- a real,
# disclosed proxy for the gap already flagged above ("no background soil-supplied
# nitrogen... the full six-pool system would include"), not a Cycles-verified rate.
# Real unfertilized ("check plot") corn commonly draws on the order of 60-120 kg
# N/ha of soil-supplied nitrogen over a season in temperate agricultural soils
# (a standard range cited by land-grant nitrogen-rate guidance); spread over this
# site's roughly 150-day growing season, 0.5 kg N/ha/day lands in the middle of
# that range. Without this, a fixed fertilizer pool that runs out mid-season drops
# n_stress to a hard, permanent 0 for every remaining day (no partial recovery,
# since nothing ever refills the pool) -- producing an unrealistic "grows fine
# then dies outright" response instead of a crop that's stressed during peak
# demand and recovers, which in turn made the nitrogen-rate slider's marginal
# grain response *increase* with more N over most of its range before hitting a
# hard ceiling, the opposite of the diminishing returns a real N-response curve
# shows. This constant is what fixes that; not itself Cycles- or site-verified.
BACKGROUND_N_KG_HA_DAY = 0.5


def n_critical_pct(biomass_mgha, crop):
    """Whole-plant average/critical N concentration (%) at the given total biomass --
    the standard dilution-curve quantity, %Nc(W) = a*W^-b. Not what a day-by-day
    uptake calculation should use directly (see n_marginal_demand_pct below)."""
    biomass_mgha = max(biomass_mgha, 0.01)
    if biomass_mgha < NCRIT_FLOOR_MGHA:
        return crop["n_max_conc"] * 100
    return crop["n_max_conc"] * 100 * biomass_mgha ** (-crop["n_dilution_slope"])


def n_marginal_demand_pct(biomass_mgha, crop):
    """N (%) required per unit of NEW biomass added -- d(total plant N)/d(biomass), not
    the whole-plant average concentration n_critical_pct returns. Total plant N content
    at biomass W is a/100*W^(1-b) (the integral of the dilution curve), so its derivative
    carries a (1-dilution_slope) factor; using n_critical_pct directly here would double-
    count already-accumulated tissue's N on every day's new growth and roughly triple
    total seasonal demand (caught by checking: an unconstrained run integrated to 668 kg
    N/ha for a ~30 Mg/ha corn crop, well above real total-uptake figures for that yield
    level; this closed-form marginal rate integrates to the correct ~a/100*W_final^(1-b)
    total)."""
    biomass_mgha = max(biomass_mgha, 0.01)
    if biomass_mgha < NCRIT_FLOOR_MGHA:
        return crop["n_max_conc"] * 100  # below the floor the curve is flat, so marginal = average
    return crop["n_max_conc"] * 100 * (1 - crop["n_dilution_slope"]) * biomass_mgha ** (-crop["n_dilution_slope"])


def _reference_n_demand(weather_rows, crop, root_max_m, harvest_ttf, curve_number=75.0, slope_pct=0.0, spinup_rows=None):
    """Runs the same water/canopy physics as simulate_season's main loop below, but with
    no nitrogen feedback at all, to precompute the day-by-day nitrogen DEMAND of the fully
    unconstrained growth trajectory. This is a deliberate, verified duplication (not a
    call to simulate_season itself) so this function's physics can be read and checked
    directly against the main loop rather than trusted to a cleverer, harder-to-audit
    reuse. It's safe to duplicate because dGB_water_limited never depends on biomass or
    nitrogen status: canopy cover is a function of thermal-time fraction alone, and
    transpiration-limited growth depends only on soil moisture, never on how much biomass
    or N the crop has already accumulated -- so the unconstrained trajectory is identical
    regardless of N rate and can be computed once, independent of the actual (possibly
    N-limited) pass.

    Why this exists: the previous approach computed demand from the plant's ACTUAL
    (possibly already-stunted) biomass and paid it out of a single fertilizer pool on a
    first-come-first-served basis -- once the pool hit exactly zero, n_stress locked at a
    permanent 0 for every remaining day (nothing ever refills it), giving a "grows fine,
    then dies outright" response. Because delaying that collapse into a period of higher
    unconstrained growth is worth progressively more per added kg of N (right up until the
    collapse is avoided entirely), the resulting yield-vs-N-rate curve had ACCELERATING
    marginal returns followed by a hard cliff -- the opposite of the diminishing returns a
    real nitrogen response curve shows, and not a curve a real economic optimum could be
    built on. Returns a list of daily N demand (kg N/ha), one per day the main loop below
    will actually iterate (same weather, crop, and harvest_ttf, so the two loops break at
    the same day by construction, since thermal time never depends on nitrogen).

    curve_number, slope_pct, spinup_rows: must match whatever simulate_season's main loop
    is called with, or this duplicated water balance would silently diverge from the real
    one it's meant to mirror -- see infiltrate()/simulate_season()'s own parameters."""
    layers = crop["make_layers"]()
    if spinup_rows:
        for w in spinup_rows:
            infiltrate(layers, w["pp"], curve_number, slope_pct)
            eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
            soil_evaporation(layers, eto, 0.0)
    tt_cum, ref_biomass = 0.0, 0.0
    demand = []
    for w in weather_rows:
        dtt = thermal_time_increment(w["tx"], w["tn"], crop["base_t"], crop["opt_t"], crop["max_t"])
        tt_cum += dtt
        ttf = tt_cum / crop["tt_maturity"]
        if ttf >= harvest_ttf:
            break
        eie = canopy_cover(ttf, crop.get("eix", 1.0), crop.get("canopy_shape", DEFAULT_CANOPY_SHAPE))
        root_depth = root_max_m * min(1.0, ttf / 0.5)

        infiltrate(layers, w["pp"], curve_number, slope_pct)
        eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
        soil_evaporation(layers, eto, eie)

        GR = crop["rue"] * eie * w["solar"]
        tmean = (w["tx"] + w["tn"]) / 2
        es = 0.6108 * math.exp(17.27 * tmean / (tmean + 237.3))
        ea = es * (w["rhx"] + w["rhn"]) / 200
        Da = max(0.05, es - ea)
        TRp = (1 + (crop["kc"] - 1) * eie) * eie * eto
        TRp *= transpiration_temp_factor(tmean, crop["tr_min_t"], crop["tr_threshold_t"])

        avail_frac = root_zone_availability(layers, root_depth)
        water_stress = water_stress_response(avail_frac, crop.get("depletion_fraction", 0.5))
        TR_actual = TRp * water_stress
        extract_transpiration(layers, root_depth, TR_actual)

        GT = crop["wue"] / math.sqrt(Da) * TR_actual
        dGB_water_limited = max(0.0, min(GR, GT)) / 1000

        demand.append(dGB_water_limited * 10 * n_marginal_demand_pct(ref_biomass * 10, crop) * 10)
        ref_biomass += dGB_water_limited
    return demand


def simulate_season(weather_rows, crop, root_max_m=1.4, harvest_ttf=1.0, n_rate_kg_ha=None, record_history=False,
                     n_applications=None, n_credit_kg_ha=0.0, manure_n_kg_ha=0.0, manure_availability=0.5,
                     irrigation_trigger_frac=None, irrigation_amount_mm=25.0,
                     tillage_doy=None, tillage_implement=None, tillage_boost_days=30,
                     spinup_rows=None, curve_number=75.0, slope_pct=0.0):
    """weather_rows: dicts with doy, tx, tn, solar, rhx, rhn, wind, pp, in planting-day order.
    harvest_ttf: fraction of thermal time to maturity that triggers harvest -- 1.0 for grain
    crops (HARVEST_TIMING=-999 in the real crop file), lower for forage/silage crops harvested
    before full maturity (e.g. 0.85 for CornSilageRM.90's real HARVEST_TIMING=85).
    n_rate_kg_ha: total fertilizer N applied at planting (kg N/ha), the student-facing nitrogen
    knob -- see the mineral-N-balance section above. None (default) skips N tracking entirely,
    UNLESS n_applications, n_credit_kg_ha, or manure_n_kg_ha supply nitrogen some other way.

    n_applications: optional list of (doy, amount_kg_ha) tuples -- real, disclosed Cycles usage
    (Kemanian et al. 2024, Fig. 6: winter wheat fertilized 80/60 kg N/ha split fall-at-planting/
    spring; SI Section IX: Iowa maize fertilized in one spring application, or 50/50 fall/spring
    when manured). When given, REPLACES the single day-0 lump n_rate_kg_ha would otherwise add --
    the pool starts at 0 and each listed amount is added to it on its scheduled day instead of
    all at once. n_rate_kg_ha is still honored if n_applications is None (backward compatible,
    single up-front lump, the original behavior).

    n_credit_kg_ha: a previous-crop nitrogen credit added to the pool at day 0 -- real and
    disclosed (SI Section IX: "a 60 kg/ha of N credit if maize followed soy").

    manure_n_kg_ha, manure_availability: an organic nitrogen amendment, added to the pool at
    day 0 as manure_n_kg_ha * manure_availability. The 0.5 default is a real, disclosed number
    (SI Section IX: manure N "adjusted upward to account for 0.5 availability compared with
    mineral N"), not an invented discount.

    irrigation_trigger_frac, irrigation_amount_mm: irrigation is real and disclosed in Cycles
    (operations "can be... conditional to soil temperature, soil moisture, and crop phenology
    thresholds," Kemanian et al. 2024 Sec. 2.8) but no exact trigger threshold or application
    depth is disclosed in the paper or its SI -- both are scenario-specific configuration in
    real Cycles, not a formula to discover. irrigation_trigger_frac=None (default) means no
    irrigation. When set, irrigation of irrigation_amount_mm is added to that day's water input
    whenever root-zone available water (avail_frac, the same quantity water_stress is already
    computed from) drops below the trigger -- the default trigger, if a caller chooses to use
    one, is left to the caller to set explicitly rather than guessed at here.

    tillage_doy, tillage_implement, tillage_boost_days: tillage's real Cycles mechanism (soil
    mixing by an implement-specific coefficient, plus temporarily faster soil organic matter
    decomposition from disrupted aggregates -- Kemanian et al. 2024 Sec. 2.6, "tillage
    stimulation of Cs degradation") is coupled to the full six-pool soil carbon/nitrogen
    saturation system this engine deliberately does not implement (out of scope for v1, see
    CLAUDE.md). tillage_implement selects a real named implement from TILLAGE_IMPLEMENTS
    (parsed directly from Cycles v1.4.4's own till.txt, 86 real tools with real depth_m/
    mixing_efficiency values -- raises ValueError if the name isn't in that table). Two
    effects, split by how directly each is grounded in real data:
    (1) Soil moisture is genuinely mixed within the implement's real depth, weighted by its
    real mixing_efficiency, on tillage_doy itself -- see mix_tilled_layers() above for why
    this applies the real coefficient to moisture rather than the C/N pools Cycles itself
    mixes with it (this engine has no per-layer C/N pools to mix).
    (2) BACKGROUND_N_KG_HA_DAY is multiplied by (1 + mixing_efficiency) for tillage_boost_days
    days starting at tillage_doy, representing "tillage briefly releases previously-protected
    soil organic nitrogen" -- still a disclosed placeholder for the real fT decomposition-
    boost factor (undisclosed formula, same six-pool-system gap as above), just now SIZED by
    a real per-implement number instead of an arbitrary caller-supplied multiplier.
    tillage_doy=None (default) means neither effect runs.
    Nitrogen adequacy is applied as a single WHOLE-SEASON fraction of the unconstrained
    trajectory's total N demand (computed via _reference_n_demand above), not a day-by-day
    pool that can hit a hard, uncorrectable zero mid-season -- see that function's docstring
    for why the day-by-day version produced an unrealistic accelerating-then-cliff yield
    response instead of genuine diminishing returns. The fraction uses a QUADRATIC-PLATEAU
    shape (f(x) = 2x - x^2 for x = supply/demand capped at 1, so f(0)=0, f(1)=1, and the two
    pieces meet with zero slope at the join) rather than a plain linear-plateau (f(x) = x):
    both are real, standard functional forms from the actual agronomic N-response literature
    (e.g. Cerrato & Blackmer 1990, which compares exactly these model families for corn),
    but a straight linear-plateau has CONSTANT marginal yield per added kg of N right up to
    a sharp corner -- which would make a later economic-optimum calculation degenerate into
    a step function (all-or-nothing at that corner) instead of a genuine interior maximum.
    The quadratic-plateau gives real, smoothly diminishing marginal returns throughout the
    rising portion, which is what makes a profit-maximizing nitrogen rate below the yield-
    maximizing rate an actual computed result rather than an artifact of the curve's shape.
    The day-by-day fertilizer pool is still tracked, but only to give leaching a real
    trajectory (surplus N left in the pool after the season's rationed uptake washes out
    with drainage as before); it no longer drives growth stress directly.
    record_history: when True, also returns a day-by-day "history" list (doy, canopy cover,
    water stress, cumulative aboveground biomass) for charting a season's progression --
    purely additive, no effect on any of the other returned values or existing callers.

    When nitrogen tracking is active, the result also carries n_uptake_kg_ha (cumulative N
    actually drawn into the crop over the season) and n_remaining_kg_ha (whatever is left in
    the mineral-N pool at season end -- not yet taken up, not yet leached). Together with
    n_leached_kg_ha these three account for the full nitrogen mass balance: total supply
    (n_rate_kg_ha/n_applications + n_credit_kg_ha + manure contribution + background
    mineralization) equals uptake + leached + remaining, to floating-point precision.

    curve_number, slope_pct: real curve-number runoff (Eq. SI.1-7) is now wired into the water
    balance via infiltrate() (previously implemented but never called -- see CLAUDE.md,
    2026-09-22). curve_number=75.0 is a flat default carried over from Cycles' own bundled
    Rock Springs sample soil file, NOT a real per-site value -- this project's STATSGO2 data
    has no curve-number field to draw from, so every site currently gets the same one, a real,
    disclosed simplification. slope_pct=0.0 for the same reason this project has always used
    flat terrain: no real slope data exists in any dataset here. Result now always carries
    runoff_mm (cumulative, mm) alongside the existing water-balance outputs.

    spinup_rows: optional list of real weather rows (same shape as weather_rows) simulated as
    bare, uncropped soil (canopy_cover=0, no transpiration, no N) immediately before the main
    loop starts, instead of every run beginning at field capacity regardless of season. Real
    Cycles carries continuous soil state across years; this engine previously had zero
    carryover of any kind. None (default) reproduces the exact old field-capacity-start
    behavior. Callers typically pass that season's own Jan-1-through-day-before-planting
    weather (already loaded, no new data needed) as a defensible antecedent-moisture proxy --
    not a true multi-year equilibrium spin-up, but a real, non-arbitrary improvement over
    always starting full, especially in drier climates where that assumption is least
    defensible (see the Iowa/Kansas head-to-head comparison, CLAUDE.md 2026-09-22)."""
    layers = crop["make_layers"]()
    runoff_total = 0.0
    if spinup_rows:
        # A bare-soil (no canopy, no transpiration) water balance over real weather from
        # before the tracked season starts, replacing an always-reset-to-field-capacity
        # start -- see CLAUDE.md, 2026-09-22: a real Cycles vs. this-engine head-to-head at
        # a semi-arid site (western Kansas) showed an ~18x yield gap traced directly to this
        # assumption having no basis in a dry climate. Uses the SAME infiltrate() (now
        # runoff-aware) and soil_evaporation() the main loop uses, just with canopy_cover=0.
        for w in spinup_rows:
            _, spin_runoff = infiltrate(layers, w["pp"], curve_number, slope_pct)
            runoff_total += spin_runoff
            eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
            soil_evaporation(layers, eto, 0.0)
    tillage_depth_m, tillage_mixing_efficiency = None, None
    if tillage_doy is not None:
        if tillage_implement not in TILLAGE_IMPLEMENTS:
            raise ValueError(f"Unknown tillage implement {tillage_implement!r} -- see TILLAGE_IMPLEMENTS for the real Cycles v1.4.4 implement catalog.")
        tillage_depth_m, tillage_mixing_efficiency = TILLAGE_IMPLEMENTS[tillage_implement]
    # Disclosed placeholder for the real fT decomposition-boost factor (undisclosed formula --
    # see tillage_doy's docstring); sized by the real implement's mixing_efficiency instead of
    # an arbitrary caller-supplied multiplier. 1.0 (no boost) when tillage isn't used.
    tillage_n_boost_factor = 1.0 + (tillage_mixing_efficiency or 0.0)
    tt_cum, biomass, ag_biomass = 0.0, 0.0, 0.0
    n_tracking_active = (not crop.get("legume", False)) and (
        n_rate_kg_ha is not None or n_applications or n_credit_kg_ha or manure_n_kg_ha)
    applications_by_doy = {}
    if n_tracking_active:
        if n_applications:
            total_n_input_kg_ha = sum(amount for _, amount in n_applications)
            n_pool = 0.0  # events fund the pool on their own scheduled days below, not all at once
            for doy, amount in n_applications:
                applications_by_doy[doy] = applications_by_doy.get(doy, 0.0) + amount
        else:
            total_n_input_kg_ha = n_rate_kg_ha or 0.0
            n_pool = total_n_input_kg_ha  # original single-lump behavior, unchanged when n_applications isn't used
        credit_and_manure = n_credit_kg_ha + manure_n_kg_ha * manure_availability
        total_n_input_kg_ha += credit_and_manure
        n_pool += credit_and_manure  # credit/manure land at day 0 either way, real applications are the only dated ones
    else:
        n_pool, total_n_input_kg_ha = None, None
    n_leached_total = 0.0 if n_pool is not None else None
    n_uptake_total = 0.0 if n_pool is not None else None
    irrigation_total_mm = 0.0
    history = [] if record_history else None

    n_stress_fraction, daily_demand, day_i = 1.0, None, 0
    if n_pool is not None:
        daily_demand = _reference_n_demand(weather_rows, crop, root_max_m, harvest_ttf,
                                            curve_number=curve_number, slope_pct=slope_pct, spinup_rows=spinup_rows)
        total_demand_kg_ha = sum(daily_demand)
        # Background credit only counts on days the reference trajectory actually grows
        # (daily_demand[i] > 0 exactly when that day's dGB_water_limited > 0, i.e. the
        # crop is biologically active, not frozen/dormant) -- a flat per-calendar-day
        # rate calibrated against a corn/soybean summer growing season (see
        # BACKGROUND_N_KG_HA_DAY's comment) silently swamped a winter cover crop's much
        # smaller total demand when applied across its many dormant days too (caught by
        # testing the corn/cover-crop/soybean rotation demo: background alone nearly
        # matched the cover crop's whole-season N need before this gate was added).
        # Total background contribution over the season, accounting for the tillage boost
        # window if one applies -- this has to match the actual boosted rate exactly, not a
        # flat estimate, because n_stress_fraction (and therefore yield) is fixed from this
        # season-total BEFORE the day loop runs; a tillage boost only added to the day-by-day
        # pool below would still leach out as unused surplus without ever affecting yield,
        # since day-by-day uptake is already capped by n_stress_fraction, not by whether the
        # pool physically has money on a given day (caught by testing: a first version boosted
        # only the day-loop pool and yield came out completely unchanged from an unboosted run,
        # a real bug, not a rounding artifact).
        total_background_kg_ha = 0.0
        for i, d in enumerate(daily_demand):
            if d <= 0:
                continue
            rate = BACKGROUND_N_KG_HA_DAY
            doy = weather_rows[i]["doy"]
            if tillage_doy is not None and tillage_doy <= doy < tillage_doy + tillage_boost_days:
                rate *= tillage_n_boost_factor
            total_background_kg_ha += rate
        total_supply_kg_ha = total_n_input_kg_ha + total_background_kg_ha
        supply_ratio = min(1.0, total_supply_kg_ha / total_demand_kg_ha) if total_demand_kg_ha > 0 else 1.0
        n_stress_fraction = 2 * supply_ratio - supply_ratio ** 2  # quadratic-plateau, see docstring above

    for w in weather_rows:
        dtt = thermal_time_increment(w["tx"], w["tn"], crop["base_t"], crop["opt_t"], crop["max_t"])
        tt_cum += dtt
        ttf = tt_cum / crop["tt_maturity"]
        if ttf >= harvest_ttf:
            break
        eie = canopy_cover(ttf, crop.get("eix", 1.0), crop.get("canopy_shape", DEFAULT_CANOPY_SHAPE))
        root_depth = root_max_m * min(1.0, ttf / 0.5)

        # Tillage's soil-moisture mixing happens once, on tillage_doy itself, before
        # today's irrigation check and water balance -- see mix_tilled_layers() above.
        if tillage_doy is not None and w["doy"] == tillage_doy:
            mix_tilled_layers(layers, tillage_depth_m, tillage_mixing_efficiency)

        # Irrigation (if requested) triggers off YESTERDAY's ending soil moisture, same
        # quantity water_stress is computed from below, and is added to today's water input
        # before infiltration/redistribution -- so irrigated water shows up in today's
        # available water exactly like an equivalent rain event would.
        irrigation_mm = 0.0
        if irrigation_trigger_frac is not None:
            pre_avail_frac = root_zone_availability(layers, root_depth)
            if pre_avail_frac < irrigation_trigger_frac:
                irrigation_mm = irrigation_amount_mm
                irrigation_total_mm += irrigation_mm

        drainage_mm, runoff = infiltrate(layers, w["pp"] + irrigation_mm, curve_number, slope_pct)
        runoff_total += runoff
        eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
        soil_evaporation(layers, eto, eie)

        GR = crop["rue"] * eie * w["solar"]
        tmean = (w["tx"] + w["tn"]) / 2
        es = 0.6108 * math.exp(17.27 * tmean / (tmean + 237.3))
        ea = es * (w["rhx"] + w["rhn"]) / 200
        Da = max(0.05, es - ea)
        TRp = (1 + (crop["kc"] - 1) * eie) * eie * eto
        TRp *= transpiration_temp_factor(tmean, crop["tr_min_t"], crop["tr_threshold_t"])

        avail_frac = root_zone_availability(layers, root_depth)
        water_stress = water_stress_response(avail_frac, crop.get("depletion_fraction", 0.5))
        TR_actual = TRp * water_stress
        extract_transpiration(layers, root_depth, TR_actual)

        GT = crop["wue"] / math.sqrt(Da) * TR_actual
        dGB_water_limited = max(0.0, min(GR, GT)) / 1000

        n_stress = 1.0
        if n_pool is not None:
            if w["doy"] in applications_by_doy:
                n_pool += applications_by_doy[w["doy"]]
            if dGB_water_limited > 0:
                background_rate = BACKGROUND_N_KG_HA_DAY
                if tillage_doy is not None and tillage_doy <= w["doy"] < tillage_doy + tillage_boost_days:
                    background_rate *= tillage_n_boost_factor
                n_pool += background_rate
            n_stress = n_stress_fraction
            target_uptake_kg_ha = n_stress_fraction * daily_demand[day_i]
            n_uptake_kg_ha = min(n_pool, target_uptake_kg_ha)
            n_pool -= n_uptake_kg_ha
            n_uptake_total += n_uptake_kg_ha
            profile_water_mm = sum(l["theta"] * l["thick"] * 1000 for l in layers)
            if profile_water_mm > 0 and n_pool > 0 and drainage_mm > 0:
                leached_kg_ha = drainage_mm * (n_pool / profile_water_mm)
                n_pool = max(0.0, n_pool - leached_kg_ha)
                n_leached_total += leached_kg_ha
            day_i += 1

        dGB = dGB_water_limited * n_stress
        biomass += dGB
        ag_biomass += dGB * shoot_fraction(ttf, crop["fsti"], crop["fstf"])

        if record_history:
            history.append(dict(doy=w["doy"], ttf=round(ttf, 4), canopy=round(eie, 4),
                                 water_stress=round(water_stress, 4), ag_mg_ha=round(ag_biomass * 10, 4)))

    flowering_frac = crop["flowering_tt"] / crop["tt_maturity"]
    fpf = max(0.0, min(1.0, (tt_cum - crop["tt_maturity"] * flowering_frac) / (crop["tt_maturity"] * (1 - flowering_frac))))
    HI = crop["hi_x"] - (crop["hi_x"] - crop["hi_o"]) * math.exp(-crop["hi_slope"] * fpf)
    biomass_mg_ha = biomass * 10
    ag_biomass_mg_ha = ag_biomass * 10
    grain_mg_ha = ag_biomass * HI * 10 * crop.get("calibration_factor", 1.0)
    forage_mg_ha = ag_biomass_mg_ha * crop.get("forage_fraction", 0.95) * crop.get("calibration_factor", 1.0)
    result = dict(total=biomass_mg_ha, ag=ag_biomass_mg_ha, grain=grain_mg_ha, forage=forage_mg_ha,
                  runoff_mm=runoff_total)
    if n_leached_total is not None:
        result["n_leached_kg_ha"] = n_leached_total
    if irrigation_trigger_frac is not None:
        result["irrigation_mm"] = irrigation_total_mm
    if record_history:
        result["history"] = history
    if n_uptake_total is not None:
        result["n_uptake_kg_ha"] = n_uptake_total
        result["n_remaining_kg_ha"] = n_pool
    return result
