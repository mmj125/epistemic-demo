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
    return cnb / (2.3 - 0.013 * cnb)


def cn_wet(cnb):
    return cnb / (0.4 + 0.0058 * cnb)  # supplement showed "0.4 - 0.006xCNb"; standard AMC-III form uses +


def moisture_adjusted_cn(cnb, fwc, slope_pct):
    cnd, cnw = cn_dry(cnb), cn_wet(cnb)
    return cnd + (cnw - cnd) * fwc


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


def soil_evaporation(layers, eto_mm, canopy_cover_frac):
    l0 = layers[0]
    demand_mm = eto_mm * (1 - canopy_cover_frac)
    available_mm = max(0.0, (l0["theta"] - l0["pwp"]) * l0["thick"] * 1000)
    actual_mm = min(demand_mm, available_mm)
    l0["theta"] -= actual_mm / (l0["thick"] * 1000)
    return actual_mm


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


def _reference_n_demand(weather_rows, crop, root_max_m, harvest_ttf):
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
    the same day by construction, since thermal time never depends on nitrogen)."""
    layers = crop["make_layers"]()
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

        redistribute(layers, w["pp"])
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
        water_stress = max(0.0, min(1.0, avail_frac / 0.5))
        TR_actual = TRp * water_stress
        extract_transpiration(layers, root_depth, TR_actual)

        GT = crop["wue"] / math.sqrt(Da) * TR_actual
        dGB_water_limited = max(0.0, min(GR, GT)) / 1000

        demand.append(dGB_water_limited * 10 * n_marginal_demand_pct(ref_biomass * 10, crop) * 10)
        ref_biomass += dGB_water_limited
    return demand


def simulate_season(weather_rows, crop, root_max_m=1.4, harvest_ttf=1.0, n_rate_kg_ha=None, record_history=False):
    """weather_rows: dicts with doy, tx, tn, solar, rhx, rhn, wind, pp, in planting-day order.
    harvest_ttf: fraction of thermal time to maturity that triggers harvest -- 1.0 for grain
    crops (HARVEST_TIMING=-999 in the real crop file), lower for forage/silage crops harvested
    before full maturity (e.g. 0.85 for CornSilageRM.90's real HARVEST_TIMING=85).
    n_rate_kg_ha: total fertilizer N applied at planting (kg N/ha), the student-facing nitrogen
    knob -- see the mineral-N-balance section above. None (default) skips N tracking entirely.
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
    purely additive, no effect on any of the other returned values or existing callers."""
    layers = crop["make_layers"]()
    tt_cum, biomass, ag_biomass = 0.0, 0.0, 0.0
    n_pool = n_rate_kg_ha if (n_rate_kg_ha is not None and not crop.get("legume", False)) else None
    n_leached_total = 0.0 if n_pool is not None else None
    history = [] if record_history else None

    n_stress_fraction, daily_demand, day_i = 1.0, None, 0
    if n_pool is not None:
        daily_demand = _reference_n_demand(weather_rows, crop, root_max_m, harvest_ttf)
        total_demand_kg_ha = sum(daily_demand)
        # Background credit only counts on days the reference trajectory actually grows
        # (daily_demand[i] > 0 exactly when that day's dGB_water_limited > 0, i.e. the
        # crop is biologically active, not frozen/dormant) -- a flat per-calendar-day
        # rate calibrated against a corn/soybean summer growing season (see
        # BACKGROUND_N_KG_HA_DAY's comment) silently swamped a winter cover crop's much
        # smaller total demand when applied across its many dormant days too (caught by
        # testing the corn/cover-crop/soybean rotation demo: background alone nearly
        # matched the cover crop's whole-season N need before this gate was added).
        active_days = sum(1 for d in daily_demand if d > 0)
        total_supply_kg_ha = n_pool + BACKGROUND_N_KG_HA_DAY * active_days
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

        drainage_mm = redistribute(layers, w["pp"])
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
        water_stress = max(0.0, min(1.0, avail_frac / 0.5))
        TR_actual = TRp * water_stress
        extract_transpiration(layers, root_depth, TR_actual)

        GT = crop["wue"] / math.sqrt(Da) * TR_actual
        dGB_water_limited = max(0.0, min(GR, GT)) / 1000

        n_stress = 1.0
        if n_pool is not None:
            if dGB_water_limited > 0:
                n_pool += BACKGROUND_N_KG_HA_DAY
            n_stress = n_stress_fraction
            target_uptake_kg_ha = n_stress_fraction * daily_demand[day_i]
            n_uptake_kg_ha = min(n_pool, target_uptake_kg_ha)
            n_pool -= n_uptake_kg_ha
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
    result = dict(total=biomass_mg_ha, ag=ag_biomass_mg_ha, grain=grain_mg_ha, forage=forage_mg_ha)
    if n_leached_total is not None:
        result["n_leached_kg_ha"] = n_leached_total
    if record_history:
        result["history"] = history
    return result
