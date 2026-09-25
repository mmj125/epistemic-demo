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
import copy
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
    pwp, fc, sat = max(0.01, theta_1500), max(0.02, theta_33), max(0.05, theta_sat)

    # Secondary parameters (Saxton & Rawls 2006, Soil Sci. Soc. Am. J. 70(5), Table 1,
    # Eq. 4/14-18) -- obtained directly from the paper (Matt supplied the PDF 2026-09-23
    # after this sandbox's network policy blocked every attempt to fetch it, including
    # WebSearch). Verified against the paper's own Table 3 worked example (Sand texture,
    # S=88%, C=5%, OM=2.5%w) before trusting: this function's existing pwp/fc/sat reproduce
    # the table's 5/10/46 %v to the displayed precision, and ksat below reproduces the
    # table's 108.1 mm/h as 108.15 -- both essentially exact, not just plausible.
    # B/lambda (Eq. 14-15/18) describe the slope of the log moisture-tension curve; ksat
    # (Eq. 16) is the saturated hydraulic conductivity Darcy's law would use to rate-limit
    # flow between layers. psi_e (Eq. 4, kPa) is the air-entry/bubbling pressure. None of
    # these were previously computed anywhere in this engine -- redistribute() moved water
    # between layers at an unlimited daily rate (a same-day cascading bucket), the specific
    # gap already flagged in this file's own docstrings and in CLAUDE.md as an approximation
    # of Cycles' real sub-daily capacitance-weighted flow (Eq. 1-2). ksat_mm_day now lets
    # redistribute() rate-limit that flow by each layer's own real conductivity -- see its
    # docstring. B/lambda/psi_e are exposed but not yet consumed anywhere; a real prerequisite
    # for a fuller unsaturated-flow (Darcy/Richards-style) redistribution scheme, not attempted
    # here -- that would need Cycles' own Eq. 1-2 exact form, not just these soil parameters.
    psi_et = (-21.67 * S - 27.93 * C - 81.97 * theta_s33
              + 71.12 * (S * theta_s33) + 8.29 * (C * theta_s33)
              + 14.05 * (S * C) + 27.16)
    psi_e = psi_et + (0.02 * psi_et ** 2 - 0.113 * psi_et - 0.70)
    B = (math.log(1500) - math.log(33)) / (math.log(fc) - math.log(pwp))
    lam = 1 / B
    ksat_mm_h = 1930 * (sat - fc) ** (3 - lam)
    return dict(pwp=pwp, fc=fc, sat=sat, psi_e_kpa=psi_e, B=B, lam=lam,
                ksat_mm_day=ksat_mm_h * 24)


def campbell_khe(theta_s, theta_sfc, theta_sat, ksat, psi_e, b):
    """Real Eq. 1, Kemanian et al. 2024: the capacitance-weighted effective hydraulic
    conductivity between the current moisture theta_s and field capacity theta_sfc, using
    Campbell's (1974) power-law moisture-release curve theta(psi) = theta_sat*(psi_e/psi)^(1/b)
    (b is Saxton-Rawls' own B -- both papers use the same exponent for the same curve family).
    The paper's own typeset integral collapses to closed form once that substitution is made:
    both the numerator and denominator become simple power-function integrals of theta, since
    d(theta)/d(psi) integrated over psi is just theta(psi_s) - theta(psi_sfc) by the fundamental
    theorem of calculus, and (psi_e/psi)^m becomes (theta/theta_sat)^(m*b) via the same curve.
    Verified against brute-force scipy.integrate.quad numerical integration of the paper's own
    literal integral to machine precision (relative error ~1e-15) before use here.

    One real correction made to the paper's own printed exponent: it reads "(2+3b)" in the
    numerator's (psi_e/psi) term, but that literal reading makes khe collapse to ~0 everywhere
    except within a hair of saturation (checked numerically, not just suspected) -- physically
    implausible, since real soils drain measurably well below saturation. Reading it as
    "2+3/b" instead (a division slash almost certainly lost in the PDF's text extraction, the
    same category of OCR/typesetting issue already documented elsewhere in this file for the
    SI's sign errors) exactly recovers Campbell's own well-known, independently-citable
    K(theta) = Ksat*(theta/theta_sat)^(2b+3) conductivity form -- both the numeric sanity check
    and the match to a standard textbook formula point the same direction, not just one of them.

    Returns an effective conductivity in the same units as ksat (mm/day here): 0 when
    theta_s <= theta_sfc (no gradient to drive flow), rising smoothly and always staying
    below ksat itself as theta_s approaches theta_sat -- capturing the paper's own stated
    intent ("weighting by capacitance slows down water flow as the soil approaches field
    capacity") directly, rather than the flat ksat-as-a-rate-cap this file used before today."""
    if theta_s <= theta_sfc:
        return 0.0
    n = 2 * b + 3
    numer = ksat / theta_sat ** n * (theta_s ** (n + 1) - theta_sfc ** (n + 1)) / (n + 1)
    denom = theta_s - theta_sfc
    return numer / denom


OM_FROM_SOC = 1.72  # standard Van Bemmelen conversion, SOC% -> OM%


# ---------------------------------------------------------------------------
# Curve-number runoff (Eq. SI.1-7). Sign corrected per module docstring.
# ---------------------------------------------------------------------------

def slope_factor(slp):
    return 1.1 - slp / (slp + math.exp(3.7 + 0.02 * slp))


def cn_dry(cnb):
    """Real SCS Antecedent Soil Moisture Condition I (dry) curve number. History: started as a
    rounded NEH-4-style approximation (cnb/(2.3-0.013*cnb)); replaced 2026-09-22 with a
    SWAT+-sourced form (Eq 2:1.1.4) that agreed within ~1-2.5 CN points; replaced again
    2026-09-24 with Cycles' own literal SI Eq. SI.5 (read directly from the SI's own parsed
    OMML XML -- no sign issue here, unlike Eq. SI.6 below), now that Eq. SI.7's f_wc is fully
    resolved too (see retention_param_mm()) -- this is Cycles' OWN stated formula, not a
    substitute, and testing (below) showed it's at least as good as the SWAT substitute it
    replaces, so faithfulness to the primary source broke the tie."""
    return cnb / (2.3 - 0.013 * cnb)


def cn_wet(cnb):
    """Real SCS Antecedent Soil Moisture Condition III (wet) curve number -- Cycles' own SI
    Eq. SI.6, sign-corrected: the SI prints "CNb/(0.4-0.006*CNb)", which goes negative for any
    CNb above ~66.7 (confirmed numerically, breaking most real agricultural soils) -- the
    external SCS-CN derivation this equation is based on requires a "+", giving sensible,
    always-above-CNb wet curve numbers throughout the realistic range instead. Previously
    replaced by a SWAT+-sourced substitute (Eq 2:1.1.5) specifically to sidestep this sign
    ambiguity; reverted to Cycles' own (now sign-corrected) formula 2026-09-24 alongside
    cn_dry() above, for the same reason."""
    return cnb / (0.4 + 0.006 * cnb)


def depth_weighted_ffc(layers, depth_m=0.6):
    """Real, sourced f_wc (2026-09-24) -- Cycles' own SI Eq. SI.7 curve-number moisture-
    adjustment factor, described only in words in both Cycles sources ("1 for soil saturated
    to a depth of 0.6m... decreasing to zero if air dry... weighted based on depth, with the
    soil surface having the most importance"), no exact formula ever given by either. Resolved
    by finding the real, disclosed depth-weighting function this same curve-number lineage
    already uses for exactly this purpose: Williams, Kannan, Wang, Santhi & Arnold (2012,
    J. Hydrologic Engineering 17(11):1221-1229), Eq. 16, applied to their own Eq. 11 fraction-
    of-field-capacity (FFC = (SW-WP)/(FC-WP) -- Cycles' words say "field capacity" is the
    reference point, not saturation, unlike this function's own earlier ad-hoc guess which
    used a saturation fraction instead):

        FFC* = sum(FFCl*(Zl-Zl-1)/Zl) / sum((Zl-Zl-1)/Zl),  summed over layers with Zl<=depth_m

    where Zl = real cumulative depth (m) to the bottom of layer l. Quoting the paper's own
    stated intent for this exact shape: dividing by Zl "reduces the influence of lower layers";
    multiplying by layer thickness (Zl-Zl-1) "gives proper weight to thick layers relative to
    thin layers" -- both match Cycles' own "surface has the most importance" description
    exactly, not just approximately. Uses Cycles' own stated 0.6m cutoff, not Williams' own
    1.0m (calibrated for a different model family, APEX/SWAT). Sums only WHOLE layers with
    Zl<=depth_m (the paper's own literal quantifier), not a fractional split of a layer
    straddling the cutoff -- Rock Springs' own layer boundaries (0.05+0.05+0.10+0.20+0.20m)
    land exactly on 0.6m with no straddle to resolve there.

    Tested (not just derived) against both established benchmarks before shipping: at Rock
    Springs, corn/soybean/wheat/silage-corn correlations all moved within +/-0.006 of the
    prior SWAT-substitute values (0.547/0.858/0.399/0.512 -> 0.550/0.856/0.393/0.518) --
    noise-level, not a regression. At the harder, more diagnostic 6-year Kansas benchmark
    (semi-arid, where the curve-number/runoff mechanism actually matters), it improved on
    every one of four metrics: fresh-start correlation 0.975->0.981, fresh MAE 1.454->1.435,
    chained correlation 0.976->0.983, chained MAE 0.628->0.536. Combined with cn_dry()/cn_wet()
    reverting to Cycles' own literal (sign-corrected) formulas above, this closes out
    QUESTIONS_FOR_DEVS.md item 1 -- the whole curve-number mechanism is now Cycles' own
    disclosed structure with a real, cited f_wc, not a substitute borrowed from a different
    model family."""
    z_prev, weighted_sum, weight_total = 0.0, 0.0, 0.0
    for l in layers:
        z = z_prev + l["thick"]
        if z > depth_m + 1e-9:
            break
        ffc_l = (l["theta"] - l["pwp"]) / (l["fc"] - l["pwp"]) if l["fc"] > l["pwp"] else 0.0
        ffc_l = max(0.0, min(1.0, ffc_l))
        w = (z - z_prev) / z if z > 0 else 0.0
        weighted_sum += ffc_l * w
        weight_total += w
        z_prev = z
    return weighted_sum / weight_total if weight_total > 0 else 0.0


def retention_param_mm(layers, curve_number):
    """Retention parameter S, now via Cycles' OWN literal Eq. SI.5-SI.7 structure (2026-09-24):
    CN = CN_dry + (CN_wet-CN_dry)*f_wc, S = 254*(100/CN - 1) -- cn_dry()/cn_wet()/
    depth_weighted_ffc() above. Replaces a SWAT+-sourced continuous S(SW) substitute used
    2026-09-23 to 2026-09-24 while f_wc itself was still undisclosed; see
    depth_weighted_ffc()'s own docstring for the real source that resolved it and the
    head-to-head test results that justified switching back to Cycles' own formula."""
    cn_d = cn_dry(curve_number)
    cn_w = cn_wet(curve_number)
    fwc = depth_weighted_ffc(layers)
    cn = cn_d + (cn_w - cn_d) * fwc
    return 254.0 * (100.0 / cn - 1.0)


def runoff_mm(win, s_mm, slope_pct):
    """Daily SCS/NRCS curve-number runoff (Eq. SI.1-7, sign-corrected -- see module docstring),
    now taking the retention parameter S directly (mm, from retention_param_mm()'s real
    soil-moisture-based formula) rather than computing S from a curve number itself -- the
    slope adjustment (already real/disclosed, unchanged) still multiplies S here."""
    S = s_mm * slope_factor(slope_pct)
    if win <= 0.2 * S:
        return 0.0
    return (win - 0.2 * S) ** 2 / (win + 0.8 * S)  # supplement showed "Win-0.8S"; SCS derivation forces +0.8S


# ---------------------------------------------------------------------------
# Layered soil water balance -- cascading bucket (a defensible simplification
# of the paper's Eq. 1-2 capacitance-weighted redistribution integral, not a
# literal implementation of it -- see module docstring) plus bare-soil
# evaporation (no disclosed formula in either source; standard proxy used).
# ---------------------------------------------------------------------------

REDISTRIBUTE_SUBSTEPS = 24  # see redistribute() docstring for the convergence check that sets this

# Real, measured (2026-09-24) -- NOT field capacity. Every make_layers()-equivalent in this
# project initialized theta=fc (100% of plant-available water) at the start of any fresh run,
# a disclosed simplification ("every soil layer always initializes to field capacity with no
# spin-up or carryover"). Directly checking real Cycles' own water.txt output for a semi-arid
# Kansas site (a run whose simulation literally starts 2011-01-01) found its actual starting
# SMC sits almost exactly halfway between wilting point and field capacity in every layer:
# (theta0-pwp)/(fc-pwp) = 0.463, 0.497, 0.503 for layers 1-3 -- not a coincidence, two of three
# land within 0.7% of exactly 0.50. At a humid site (Rock Springs) this makes no measurable
# difference (the real Jan-1-to-planting bare-fallow spinup already run before every season has
# enough real rain to erase a 100%-vs-50%-of-available starting difference well before planting
# -- confirmed: the full 4-crop validation suite is byte-identical to three decimals with this
# constant applied). At a semi-arid site it matters for months: Kansas's real layer 3 never
# gets meaningfully recharged once depleted, so starting our own fresh-run default at "full"
# instead of "half" was carrying phantom water the entire season. Tested directly against 6
# independent real Kansas reference years (drought to wet): fresh-start mean overshoot dropped
# from 5.05x to 3.63x (2012 specifically: 18.44x -> 12.49x), zero cost anywhere. See
# QUESTIONS_FOR_DEVS.md item 6 for the full evidence trail.
INITIAL_MOISTURE_FRACTION = 0.5


def redistribute(layers, water_in_mm, n_substeps=REDISTRIBUTE_SUBSTEPS):
    """Cascading bucket. When a layer carries the full Saxton-Rawls parameter set
    (psi_e_kpa, B, sat, plus ksat_mm_day), its drainage above field capacity is now
    integrated across n_substeps sub-daily steps (real Eq. 1-2, Kemanian et al. 2024),
    recomputing campbell_khe() at each substep since the real rate genuinely decays as
    the layer drains within the day -- a single full-day step using only the day's
    starting moisture (this file's own first Eq. 1 implementation, shipped earlier the
    same day this substepping was added) was found to overdrain substantially: a synthetic
    near-saturated topsoil layer drained 22.2mm in one Euler step vs. a converged ~12.2mm
    once substepped (n=480), roughly 1.8x too much water leaving the layer. n_substeps=24
    (hourly) was chosen after checking convergence directly: 24 gives 12.42mm against the
    n=480 reference's 12.24mm, ~1.5% off, while n=1 is ~82% off -- a disclosed, fixed-count
    approximation of the paper's own adaptive-step-size scheme (which varies its sub-step
    length by the profile's own slowest travel time, Eq. 2), not a literal implementation
    of that adaptive stepping, but a real numerical integration of the same governing rate
    law rather than one coarse Euler step. A layer with only ksat_mm_day (no psi_e_kpa/B)
    falls back to a flat rate cap for its whole-day drainage, and a layer with neither
    field falls back to the original unlimited-rate behavior -- three-tier graceful
    degradation so every existing make_layers()-equivalent in this project keeps working
    exactly as it did before, opting into more real physics only as its own layer dict
    carries more of the needed fields."""
    remaining = water_in_mm
    for l in layers:
        thick_mm = l["thick"] * 1000
        add = min(remaining, max(0.0, (l["sat"] - l["theta"]) * thick_mm))
        l["theta"] += add / thick_mm
        remaining -= add
        if "psi_e_kpa" in l and "B" in l:
            dt = 1.0 / n_substeps
            drain = 0.0
            for _ in range(n_substeps):
                excess_step = max(0.0, (l["theta"] - l["fc"]) * thick_mm)
                if excess_step <= 0:
                    break
                khe = campbell_khe(l["theta"], l["fc"], l["sat"], l["ksat_mm_day"], l["psi_e_kpa"], l["B"])
                flux = min(excess_step, khe * dt)
                l["theta"] -= flux / thick_mm
                drain += flux
            remaining += drain
            continue
        excess_mm = max(0.0, (l["theta"] - l["fc"]) * thick_mm)
        rate_cap = l.get("ksat_mm_day", math.inf)
        drain = min(excess_mm, rate_cap)
        l["theta"] -= drain / thick_mm
        remaining += drain
    return remaining


def infiltrate(layers, water_in_mm, curve_number, slope_pct):
    """One day's curve-number runoff (Eq. SI.1-7, sign-corrected) followed by infiltration
    (redistribute()) -- shared by simulate_season()'s main loop and its optional spin-up
    window, so the two can't drift apart. Previously runoff_mm()/moisture_adjusted_cn()
    existed but were never actually called anywhere in the water balance (all precipitation
    went straight to infiltration) -- see CLAUDE.md, 2026-09-22, for why this was flagged as
    a real gap rather than a deliberate simplification: it means every drop of rain currently
    enters the soil, which retains more water than reality especially in a drier climate.
    Moisture adjustment now goes through retention_param_mm()'s real SWAT formula directly
    (2026-09-23) rather than the earlier compute_fwc()/moisture_adjusted_cn() ad hoc pair --
    see retention_param_mm()'s own docstring for the source and verification."""
    if water_in_mm <= 0:
        return 0.0, 0.0
    s_mm = retention_param_mm(layers, curve_number)
    runoff = runoff_mm(water_in_mm, s_mm, slope_pct)
    drainage_mm = redistribute(layers, water_in_mm - runoff)
    return drainage_mm, runoff


REW_DEFAULT_MM = 9.0  # FAO-56 Table 19's real range is 5-12mm by soil texture (confirmed via
# web search, since this sandbox's network policy blocks fao.org directly and no full Chapter 7
# document has been obtained the way Chapter 8 was); the exact per-texture table itself wasn't
# recoverable, so this uses a single disclosed value near the middle of that real range rather
# than inventing a per-texture lookup from unconfirmed numbers.


def compute_tew(theta_fc, theta_wp, ze_m=0.15):
    """Real FAO-56 Eq. 73 (total evaporable water): TEW = 1000*(theta_fc - 0.5*theta_wp)*Ze,
    confirmed via web search against the paper's own stated formula and Ze range (0.10-0.15m,
    0.15m FAO-56's own recommended default when unknown, used here)."""
    return 1000 * (theta_fc - 0.5 * theta_wp) * ze_m


def soil_evaporation(layers, eto_mm, canopy_cover_frac, precip_mm=0.0, de_state=None):
    """Bare-soil/residue evaporation. When de_state is given (a dict with 'de'/'tew'/'rew'
    keys, mutated in place across calls to track depletion since the surface was last wetted),
    today's potential demand is reduced by the real FAO-56 two-stage evaporation-reduction
    coefficient Kr (Eq. 74, confirmed via web search against the paper's own formula, since no
    full Chapter 7 document has been obtained): Kr=1 while de<=rew (Stage 1, energy-limited,
    evaporation proceeds at the full potential rate), decaying linearly as
    (tew-de)/(tew-rew) once de>rew (Stage 2, falling-rate, water-limited) -- previously this
    engine's only limit on daily evaporation was the top layer's own water content down to
    wilting point, with no memory of how long the surface had been drying, so evaporation
    could proceed at the full potential rate indefinitely as long as *some* water remained
    above wilting point, never slowing down the way real bare soil does as its surface dries.
    de_state's own 'tew'/'rew' should come from compute_tew()/REW_DEFAULT_MM once per season;
    'de' starts at 0 (a freshly wetted surface, consistent with this engine's existing
    always-starts-at-field-capacity convention) and is updated here: increased by today's
    actual evaporation, reduced by today's precipitation, clipped to [0, tew].

    The potential-demand term itself (eto_mm*(1-canopy_cover_frac)) is unchanged, still this
    engine's own existing proxy -- NOT FAO-56's own Kcmax-based demand (Eq. 72, which needs a
    basal crop coefficient Kcb this engine doesn't compute, since it grows canopy via a
    different Campbell-style mechanism, not FAO-56's own Kc*ETo framework). Only the two-stage
    depletion mechanism (Kr) is the real, sourced addition here, not the whole dual crop
    coefficient method -- a disclosed, bounded piece of it, not a full replacement.

    de_state=None (the default) reproduces the exact prior single-stage, no-memory behavior
    byte-for-byte -- every existing caller not yet passing de_state is unaffected."""
    l0 = layers[0]
    demand_mm = eto_mm * (1 - canopy_cover_frac)
    if de_state is not None:
        de, tew, rew = de_state["de"], de_state["tew"], de_state["rew"]
        kr = 1.0 if de <= rew else (max(0.0, (tew - de) / (tew - rew)) if tew > rew else 0.0)
        demand_mm *= kr
    available_mm = max(0.0, (l0["theta"] - l0["pwp"]) * l0["thick"] * 1000)
    actual_mm = min(demand_mm, available_mm)
    l0["theta"] -= actual_mm / (l0["thick"] * 1000)
    if de_state is not None:
        de_state["de"] = max(0.0, min(de_state["tew"], de_state["de"] + actual_mm - precip_mm))
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
    "Bale_straw_or_residue": (0.01, 3, 0),
    "Bed_shaper": (0.05, 7, 0.071554),
    "Bedder_hipper_disk_hiller": (0.15, 29, 0.8),
    "Bulldozer_clearing": (0.3, 30, 0.8),
    "Burn_residue_high_intensity": (0.01, 0, 0.01),
    "Burn_residue_low_intensity": (0.01, 0, 0.01),
    "Chisel_st_pt": (0.25, 19, 0.265919),
    "Chisel_sweep_shovel": (0.2, 21, 0.265919),
    "Chisel_twisted_shovel": (0.2, 24, 0.447042),
    "Cultipacker_roller": (0.05, 19, 0.265919),
    "Cultivator_field_6-12_in_sweeps": (0.12, 20, 0.202386),
    "Cultivator_field_w_spike_points": (0.12, 18, 0.371806),
    "Cultivator_hipper_disk_hiller_on_beds": (0.12, 23, 0.572433),
    "Cultivator_off_bar_w_disk_hillers_on_beds": (0.12, 13, 0.308274),
    "Disk_offset_heavy": (0.15, 27, 0.657771),
    "Disk_offset_heavy_>12_in_depth": (0.3, 28, 0.8),
    "Disk_tandem_heavy_primary_op": (0.2, 26, 0.657771),
    "Disk_tandem_secondary_op": (0.1, 18, 0.265919),
    "Drill_air_seeder_sweep_or_band_opener": (0.08, 22, 0.497198),
    "Drill_deep/semi-deep_furrow_12_to_18_in_spacing": (0.12, 17, 0.497198),
    "Drill_heavy_direct_seed_dbl_disk_opnr": (0.1, 23, 0.639427),
    "Drill_or_air_seeder_double_disk_openers_7-10_in_spac": (0.08, 6, 0.071554),
    "Drill_or_air_seeder_hoe/chisel_openers_6-12_in_spac": (0.08, 17, 0.639427),
    "Drill_or_air_seeder_hoe_opener_in_hvy_residue": (0.08, 16, 0.497198),
    "Drill_or_airseeder_double_disk": (0.08, 17, 0.497198),
    "Drill_or_airseeder_double_disk_opener_w_fert_openers": (0.08, 23, 0.639427),
    "Drill_or_airseeder_double_disk_w_fluted_coulters": (0.09, 18, 0.639427),
    "Drill_or_airseeder_offset_double_disk_openers": (0.08, 8, 0.259212),
    "Fert_applic_anhyd_knife_12_in": (0.12, 13, 0.265919),
    "Fert_applic_anhyd_knife_30_in": (0.12, 8, 0.120616),
    "Fert_applic_deep_plcmt_hvy_shnk": (0.15, 16, 0.371806),
    "Fert_applic_strip-till_30_in": (0.12, 13, 0.265919),
    "Fert_applic_surface_broadcast": (0.005, 5, 0),
    "Furrow_diker": (0.15, 15, 0.265919),
    "Furrow_shaper_torpedo": (0.1, 7, 0),
    "Graze_continuous": (0.02, 4, 0.026833),
    "Graze_rotational": (0.02, 4, 0.026833),
    "Graze_stubble_or_residue": (0.03, 4, 0.026833),
    "Harrow_coiled_tine": (0.08, 11, 0.120616),
    "Harrow_heavy_or_rotary": (0.08, 15, 0.265919),
    "Harrow_spike_tooth": (0.08, 10, 0.075895),
    "Harrow_tine_on_beds": (0.08, 11, 0.120616),
    "Harvest_corn_silage_or_forage_sorghum": (0.02, 5, 0),
    "Harvest_cotton": (0.02, 5, 0),
    "Harvest_grain": (0.01, 5, 0),
    "Harvest_grass_or_legume_seed": (0.01, 3, 0),
    "Harvest_hay": (0.01, 3, 0),
    "Harvest_peanut_digger": (0.1, 25, 0.8),
    "Harvest_root_crops_digger": (0.2, 25, 0.8),
    "Harvest_rootcrops_manually": (0.15, 11, 0.202386),
    "Harvest_sugarcane": (0.02, 5, 0),
    "Harvest_tobacco": (0.18, 1, 0),
    "Kill_Crop": (0, 0, 0),
    "Manure_injector": (0.1, 21, 0.447042),
    "Manure_spreader": (0.01, 5, 0),
    "Mower_swather_windrower": (0.01, 3, 0),
    "Mulch_treader": (0.04, 14, 0.371806),
    "Permeable_weed_barrier_applicator": (0.04, 9, 0.202386),
    "Planter_double_disk_opnr": (0.08, 5, 0.071554),
    "Planter_double_disk_opnr_18_in_rows": (0.08, 7, 0.120616),
    "Planter_double_disk_opnr_w_fluted_coulter": (0.08, 5, 0.071554),
    "Planter_in-row_subsoiler": (0.1, 11, 0.120616),
    "Planter_ridge_till": (0.15, 17, 0.447042),
    "Planter_small_veg_seed": (0.02, 4, 0),
    "Planter_strip_till": (0.08, 8, 0.120616),
    "Planter_sugarcane": (0.05, 6, 0.026833),
    "Planter_transplanter_vegetable": (0.1, 6, 0.026833),
    "Planting_broadcast_seeder": (0.01, 3, 0),
    "Plastic_mulch_apply": (0.05, 9, 0.202386),
    "Plastic_mulch_remove": (0.05, 9, 0.202386),
    "Plow_disk": (0.18, 26, 0.657771),
    "Plow_moldboard": (0.18, 29, 0.8),
    "Plow_moldboard_conservation": (0.18, 27, 0.657771),
    "Residue_row_cleaner": (0.02, 12, 0.265919),
    "Rodweeder": (0.05, 12, 0.265919),
    "Roller_corrugated_packer": (0.02, 1, 0.153324),
    "Roller_smooth": (0.02, 4, 0.026833),
    "Rotary_hoe": (0.05, 11, 0.071554),
    "Rototiller": (0.05, 29, 0.8),
    "Sprayer": (0.005, 3, 0),
    "Stalk_puller": (0.18, 6, 0.153324),
    "Striptiller_w_middlebuster_on_beds": (0.15, 23, 0.572433),
    "Subsoiler": (0.25, 15, 0.120616),
    "Subsoiler_bedder(ripper/hipper)": (0.25, 29, 0.12),
    "Subsoiler_ripper_24_to_40_in_deep": (0.25, 16, 0.120616),
    "Sweep_plow": (0.15, 17, 0),
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

# Cold-temperature reduction of radiation-limited growth (2026-09-23): GenericCrops.crop's
# RADIATION_USE_EFFICIENCY is explicitly labeled "Maximum eR" in Kemanian et al. 2024 (Table
# SI.2's own heading) -- neither source discloses what reduces it from that maximum to a day's
# actual value. Diagnosed by backing out a day's ACTUAL radiation-use efficiency directly from
# real Cycles' own daily BIOMASS output (on any day with zero N/water stress and canopy cover in
# a clean 0.15-0.85 range: dB[Mg/ha]*100 / (FRAC_INTERCEP * solar_MJ) = implied g/MJ, no back-
# solving through yield needed) across the full real record for four crops. The clean warm-season
# subset of this data (transpiration_temp_factor already at 1.0) showed a real, consistent ~25%
# gap below the nominal RUE value for every crop -- but implementing that as a flat multiplicative
# correction (tested directly, not assumed) made every crop's correlation WORSE, not better,
# despite fixing the mean. The gap that DOES help, isolated by testing each piece separately: the
# COLD-season portion of the same data (wheat's raw fall-to-spring implied RUE averages under 0.35
# of nominal) correlates far better with each crop's own EXISTING transpiration_temp_factor
# (tr_min_t/tr_threshold_t, pooled corr 0.69) than with a thermal-time-style factor (corr 0.53),
# and applying ONLY that -- reusing the exact same temp_factor already computed for transpiration,
# not inventing new per-crop thresholds -- fixed the mean-level bias for all four crops (mean
# error dropped to near-exact for corn/soybean/wheat/silage corn, no calibration_factor change
# needed to get there) AND meaningfully improved correlation for wheat (a real, not marginal,
# jump) while leaving corn/soybean/silage corn's own correlations roughly unchanged or slightly
# better. The flat warm-season "maximum eR" gap itself (see NET_GROWTH_FRACTION below for how it
# was eventually implemented, and QUESTIONS_FOR_DEVS.md item 9 for what's still genuinely open
# about it) was NOT applied here, as a multiplier on GR before the min(GR, GT) choice -- that's
# structurally unsafe regardless of the exact fraction used (confirmed directly, not assumed):
# discounting GR alone made radiation the binding constraint on 81-85% of days in a synthetic
# test (corn, three separate years), up from a real 38-46% baseline, because a smaller GR is more
# often the smaller of the two terms. Since real year-to-year yield variation is overwhelmingly
# water-driven (precipitation varies far more than solar radiation does), making radiation almost
# always the limiting factor instead destroys the model's sensitivity to the actual real signal --
# exactly why that version made every crop's correlation worse despite fixing the mean.

# Warm-day radiation-use-efficiency gap, resolved as a post-limitation growth-conversion loss
# (2026-09-23, continuing directly from the cold-temperature fix above): re-diagnosed the ~25%
# warm-day gap and found it was itself partly a measurement artifact of the diagnostic method,
# not the true size of the effect. The original implied-RUE calculation assumed every sampled day
# was purely radiation-limited (dividing that day's real biomass gain by RUE*eie*solar), but many
# of those days were actually water-limited or ambiguous in this engine's own water-balance
# simulation -- binning the same implied-RUE-ratio data by this engine's own GT/GR ratio (using
# nominal, uncorrected RUE) shows the ratio rising smoothly and monotonically from 0.62 (GT/GR
# 0.6-0.9, water-limited-leaning) to 0.80 (GT/GR > 1.33, unambiguously radiation-limited) -- most,
# but not all, of the apparent ~25% gap was really just water-limited days being misattributed to
# the radiation formula. Restricting to the cleanest, most unambiguous days (GT/GR > 1.5, n=23,
# stdev 0.039 -- a tight, reproducible sample despite the small n) gives a real, residual gap of
# 0.785, not the original ~0.74.
#
# The key insight that makes this safely implementable: since real biomass accumulation in this
# engine depends on nothing downstream of the daily growth increment itself (canopy cover and
# root depth are both pure functions of thermal time, not of accumulated biomass; soil-moisture
# extraction depends only on realized transpiration, not on how much biomass that transpiration
# produced), multiplying dGB by a flat fraction AFTER the min(GR, GT) choice is mathematically
# equivalent to a uniform rescaling of the whole season's biomass trajectory -- it cannot change
# which of GR or GT wins on any given day, unlike scaling GR beforehand. Verified directly, not
# just reasoned: applying this exact fraction after min(GR, GT) reproduces every validated crop's
# correlation to three decimals, unchanged (corn 0.547, soybean 0.858, wheat 0.397, silage corn
# 0.512, all identical to the pre-fix values) -- only the mean moved, absorbed by re-deriving each
# crop's calibration_factor, the same way this project has always handled a pure level correction.
# This targets a real, previously-disclosed-but-unfixed gap directly: the "Beyond final yield"
# multi-variable comparison in model-validation.html has repeatedly flagged that this engine's
# UNCALIBRATED total/aboveground biomass runs 26-32% higher than real Cycles even when the
# CALIBRATED grain number matches well -- this is a real, verified fix to that specific, honestly-
# disclosed problem, not a cosmetic change to a number nobody was checking.
NET_GROWTH_FRACTION = 0.785


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


def effective_canopy_cover(ei, pdf=1.0):
    """Real Eq. 7, Kemanian et al. 2024: adjusts the base canopy cover fraction (ei, from
    canopy_cover()/Eq. 6 above) for planting density, since the paper's own hardcoded default
    shape constants (6, -20, -15, 16) "represent a normalized plant density (PDf) of 1" -- a
    higher PDf hastens canopy closure (denser stands shade the ground faster), the mechanism
    this engine had no way to represent at all before this. pdf=1.0 (the default) is an exact
    no-op: ln(1-ei)*sqrt(1) = ln(1-ei), so 1-exp(ln(1-ei)) = ei identically, confirmed to full
    float precision -- every currently-validated crop leaves this parameter unset and gets
    byte-identical behavior. Clamped just below 1.0 to avoid a math-domain error from ln(0);
    ei reaching exactly eix is a limit the sigmoid in Eq. 6 never actually attains in practice,
    so this clamp is a numerical safety net, not a behavior change."""
    ei = min(ei, 1.0 - 1e-9)
    if ei <= 0.0:
        return 0.0
    return 1.0 - math.exp(math.log(1.0 - ei) * math.sqrt(pdf))


def transpiration_temp_factor(tmean, min_t, threshold_t):
    if tmean <= min_t:
        return 0.0
    if tmean >= threshold_t:
        return 1.0
    return (tmean - min_t) / (threshold_t - min_t)


def radiation_temp_factor(tmean, min_t, floor, plateau_t):
    """A second, separate temperature-response curve for radiation-limited growth (GR), reusing
    transpiration_temp_factor's own linear-ramp shape but with its own floor/plateau, since
    2026-09-23's "next fix" investigation found wheat's own real data does NOT fit the reused
    transpiration threshold (see NET_GROWTH_FRACTION's docstring above for how that shared 0.785
    constant was derived for corn/soybean/silage corn). Wheat's clean (GT/GR>1.5, n=401 real day
    samples, all real Cycles output, no N/water stress) raw implied-RUE ratio -- WITHOUT any
    temp_factor pre-divided out -- regresses linearly against tmean as 0.202 + 0.0375*tmean,
    reaching the shared 0.785 plateau (the same value corn/soybean/silage corn's own warm-day data
    converges to) at tmean~15.55 degC, not at wheat's own tr_threshold_t=12 (transpiration's real
    threshold, never independently validated for radiation). The nonzero floor at tmean=min_t
    (0.202/0.785=0.257 of the plateau) is real too: transpiration_temp_factor predicts exactly 0
    growth at wheat's own min_t=0 degC, but real Cycles' wheat output keeps growing at ~26% of its
    eventual full rate even near freezing. With floor=0 and plateau_t=threshold_t this collapses
    to exactly transpiration_temp_factor(tmean, min_t, threshold_t) -- a true no-op for any crop
    that doesn't set rad_temp_floor/rad_temp_plateau_t, verified directly, not just by
    inspection."""
    if tmean <= min_t:
        return floor
    if tmean >= plateau_t:
        return 1.0
    return floor + (1 - floor) * (tmean - min_t) / (plateau_t - min_t)


TTF50_SHOOT_PARTITION = 0.32  # Eq. SI.8-11's own half-max point isn't given a numeric value in
# either source -- the literal reading of its name (0.5) was replaced 2026-09-23 with a real,
# data-driven fit against real Cycles' own daily output (QUESTIONS_FOR_DEVS.md item 3, formerly
# unresolved): the paper's own equation implies the INSTANTANEOUS (marginal) shoot fraction of
# a day's new growth equals shoot_fraction(ttf) exactly (dAG/dTotal = shoot_fraction(ttf) by
# construction, since dAG = dGB*shoot_fraction(ttf) and dTotal = dGB), so day-to-day differences
# in real AG BIOMASS/BIOMASS from four independent real daily-output files (two separate corn
# seasons, soybean, wheat -- 5174 usable (ttf, marginal-fraction) points total, growth days only)
# were regressed against this exact functional form with fsti=0.45/fstf=0.95 held fixed. Every
# one of the four independently gave a best fit clustered tightly at 0.315-0.335 (corn 0.320 and
# 0.317 from two different rotations, soybean 0.316, wheat 0.335) -- strong, consistent evidence
# this is a real, roughly species-independent constant near 0.32, not 0.5. Pooled fit across all
# four: 0.3205 (SSE 6.87 vs. 78.54 at the old 0.5 -- an ~11x reduction, mean absolute error
# 0.113->0.025). Rounded to 0.32 here, not the literal 0.3205, since the fit's own precision
# doesn't warrant a 4th significant figure.


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

# ---------------------------------------------------------------------------
# Weather-driven scaling on BACKGROUND_N_KG_HA_DAY (2026-09-24). The flat
# constant above has zero year-to-year variability, which is exactly why
# turning nitrogen tracking on for winter wheat (which real Cycles output
# shows is dominated by nitrogen stress, not water -- see QUESTIONS_FOR_DEVS.md
# item 6) made correlation WORSE than not modeling nitrogen at all: applying
# real nitrogen constraints at a flat, unvarying supply rate can fix the mean
# level but can't reproduce which specific years get more or less N-stressed.
# Real Cycles' own soil-carbon/mineralization equations (SI Eq. SI.10-14,
# now readable via this session's OMML parser) give the right STRUCTURE but
# not the numbers needed to run them -- the rate constants (k_ra, k_rt, k_rz,
# k_rm, k_m, k_s), the soil-environment scalar fE, the microbial-cap scalar
# fA, and the saturation capacity C_sx are disclosed nowhere, not in the
# paper, the SI, or any of Cycles' own input files (checked GenericCrops.crop
# and the .soil files directly). Rather than guess at those, this uses a
# real, independently-sourced, external formula for exactly the same kind of
# temperature/moisture scaling on organic-matter decomposition: RothC
# (Rothamsted Research's own soil carbon model, Coleman & Jenkinson, widely
# cited since the 1990s, not a Cycles-specific or invented shape), obtained
# from its own literal Fortran source
# (github.com/Rothamsted-Models/RothC_Code/blob/master/RothC.for) rather than
# a paraphrase, since a web-search summary of the same formula came back
# transcribed wrong on the first pass.
# ---------------------------------------------------------------------------

def rothc_temp_factor(tmean):
    """Real RothC temperature rate-modifier (Coleman & Jenkinson), quoted verbatim from the
    model's own Fortran source: RM_TMP = 0 for T<-5C, else 47.91/(exp(106.06/(T+18.27))+1.0).
    Ranges from 0 at/below -5C through 1.0 around 30C (its own real behavior, not tuned for
    this engine) -- used here to scale BACKGROUND_N_KG_HA_DAY's flat rate by how warm a given
    day actually was, giving real, sourced year-to-year variability the flat constant never
    had."""
    if tmean < -5.0:
        return 0.0
    return 47.91 / (math.exp(106.06 / (tmean + 18.27)) + 1.0)


def rothc_moisture_factor(theta, fc, pwp, min_factor=0.2):
    """Real RothC moisture rate-modifier, adapted to this engine's own already-tracked soil
    state rather than RothC's own separate soil-moisture-deficit (SMD) bookkeeping (a
    monthly-timestep quantity this engine has no equivalent of). RothC's own real shape is a
    linear ramp between min_factor (0.2, RothC's own real default floor) at a wilting-point-
    like threshold and 1.0 at a field-capacity-like threshold -- reproduced here using this
    engine's own (theta-pwp)/(fc-pwp) fraction as the ramp's input in place of RothC's own
    SMD/SMD1bar/SMD15barAdj ratio, since both are the same real concept (how depleted is the
    topsoil relative to field capacity/wilting point) expressed through different, already-
    tracked bookkeeping -- a disclosed adaptation of a real formula's shape, not a literal
    port of RothC's own moisture accounting."""
    if fc <= pwp:
        return 1.0
    frac = max(0.0, min(1.0, (theta - pwp) / (fc - pwp)))
    return min_factor + (1.0 - min_factor) * frac


# ---------------------------------------------------------------------------
# Tillage's real decomposition-acceleration factor (Kemanian & Stockle 2010,
# Eq. 5 -- C-Farm, Cycles' own predecessor model, real source PDF in this
# repo's root as of 2026-09-22). Real formula, real per-implement input data,
# still applied here as a disclosed stand-in multiplier on
# BACKGROUND_N_KG_HA_DAY rather than a reproduction of the real mechanism,
# which requires the full six-pool soil-carbon system this engine doesn't
# implement -- see TILLAGE_IMPLEMENTS' docstring and simulate_season's
# tillage_doy paragraph for the full account.
# ---------------------------------------------------------------------------

def tillage_ftx(clay_frac):
    """Real texture scaling on tillage's decomposition-acceleration effect:
    ftx = 1+4*exp(-5.5*fclay), ranging ~1.4 for clay soils to ~4.0 for sandy soils.
    clay_frac is a 0-1 fraction (this engine's clay inputs are usually a 0-100 percent,
    e.g. SOIL_LAYERS_RAW's own "clay" field -- divide by 100 at the call site)."""
    return 1 + 4 * math.exp(-5.5 * clay_frac)


def tillage_ft(dr, ftx):
    """Real tillage-acceleration factor: ft = ftx*dr/(dr+exp(5.5-0.05*dr)), where dr is a
    cumulative soil-disturbance rating (0-30 NRCS Soil Conditioning Index scale, additive
    across tillage passes -- real per-implement values are TILLAGE_IMPLEMENTS' third
    element, straight from Cycles v1.4.4's own till.txt SOIL_DISTURB_RATIO field).
    ft is 0 at dr=0 (no disturbance, no acceleration) and rises toward ftx as dr grows --
    a single tillage pass typically pushes dr into the range where ft is already close to
    its ceiling (the paper: "a typical conventional tillage sequence... is sufficient to
    accelerate the turnover rate near the maximum values")."""
    if dr <= 0:
        return 0.0
    return ftx * dr / (dr + math.exp(5.5 - 0.05 * dr))


def tillage_dr_decay(layers, max_rate_per_day=0.02):
    """dr's own daily decay -- the paper states plainly that ft (and by extension its
    driver, dr) decreases at "a maximum rate of 2% day-1 for soils at field capacity,"
    slower when drier, but gives no exact moisture-scaling formula (this specific
    sub-formula is not disclosed, unlike the ft/ftx equations themselves -- a defensible
    interpretation, not a verified match, same spirit as this file's existing fwc/bare-
    soil-evaporation proxies). Scales the 2%/day ceiling by the topsoil layer's own
    fraction of field capacity (theta/fc, capped at 1.0, since field capacity is the
    stated reference point and the paper gives no guidance for wetter-than-field-capacity
    soil). Returns the fraction of the CURRENT dr that decays away today."""
    l0 = layers[0]
    if l0["fc"] <= 0:
        return 0.0
    moisture_frac = max(0.0, min(1.0, l0["theta"] / l0["fc"]))
    return max_rate_per_day * moisture_frac


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


def _reference_n_demand(weather_rows, crop, root_max_m, harvest_ttf, curve_number=75.0, slope_pct=0.0, spinup_rows=None,
                         tillage_doy=None, tillage_implement=None, tillage_clay_frac=0.21, initial_layers=None,
                         irrigation_trigger_frac=None, irrigation_amount_mm=25.0):
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
    one it's meant to mirror -- see infiltrate()/simulate_season()'s own parameters.

    tillage_doy, tillage_implement, tillage_clay_frac: for the same reason, this also has
    to mirror the main loop's own tillage moisture-mixing call (mix_tilled_layers()) and dr
    decomposition-boost tracking (see simulate_season's tillage_doy paragraph and
    tillage_ft()'s own docstring), or the two loops' water and background-N trajectories
    would silently diverge. Returns (demand, bg_multiplier) -- a second list, one entry per
    day, of the multiplier that day's BACKGROUND_N_KG_HA_DAY should be scaled by: the tillage
    (1+ft) factor (1.0 when tillage_doy is None) times a real, weather-driven RothC
    temperature/moisture factor (rothc_temp_factor()/rothc_moisture_factor() above, added
    2026-09-24 -- never 1.0, always reflects that day's actual temperature and topsoil
    moisture).

    initial_layers: real multi-year state carryover (2026-09-24), see simulate_season's own
    initial_layers paragraph for the full story -- this function needs its own INDEPENDENT
    copy, never the caller's real carried-forward object, since it's a throwaway parallel
    trajectory used only to size N demand, not the actual season being simulated. A test
    harness that shared one object between this precompute pass and simulate_season's main
    loop (rather than the deep copy used here) let both mutate the same soil state within a
    single call, corrupting a whole day's worth of investigation before being caught -- see
    QUESTIONS_FOR_DEVS.md item 6's "real correction" paragraph. copy.deepcopy() here is what
    keeps that from being possible again.

    irrigation_trigger_frac, irrigation_amount_mm: real, previously-missing bug fix
    (2026-09-25, found during a broad audit for exactly this class of issue, not from a
    specific report). This function is documented above as needing to mirror EVERY input
    that affects the main loop's water balance, "or the two loops' water... trajectories
    would silently diverge" -- but irrigation was added to simulate_season() without ever
    being added here, so any caller combining nitrogen tracking with irrigation got a
    demand baseline computed as if irrigation never happened, silently understating how
    much MORE nitrogen an irrigated (faster-growing) crop would actually need. Confirmed
    directly, not just reasoned: at a real semi-arid site (Western Kansas, 2012, N=100),
    turning irrigation on changed grain from 1.58 to 10.16 Mg/ha (irrigation clearly doing
    real work) while n_uptake stayed pinned at the exact same 128.88 kg/ha in both cases --
    the tell that n_stress_fraction was computed identically either way, ignoring
    irrigation's real effect on demand entirely. This was live and reachable, not just
    theoretical: model-validation.html's own "Full simulation controls" panel lets a
    reviewer set nitrogen and irrigation together in the same run. Fixed by mirroring the
    exact same irrigation block the main loop already has, using the same
    root_zone_availability() call already computed for water_stress -- see the identical
    logic and comment below."""
    layers = copy.deepcopy(initial_layers) if initial_layers is not None else crop["make_layers"]()
    root_max_m = crop.get("root_max_m", root_max_m)
    de_state = dict(de=0.0, tew=compute_tew(layers[0]["fc"], layers[0]["pwp"]), rew=REW_DEFAULT_MM)
    if spinup_rows:
        for w in spinup_rows:
            infiltrate(layers, w["pp"], curve_number, slope_pct)
            eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
            soil_evaporation(layers, eto, 0.0, precip_mm=w["pp"], de_state=de_state)
    tillage_depth_m, tillage_mixing_efficiency = (TILLAGE_IMPLEMENTS[tillage_implement][0], TILLAGE_IMPLEMENTS[tillage_implement][2]) \
        if tillage_doy is not None else (None, None)
    ftx = tillage_ftx(tillage_clay_frac)
    dr = 0.0
    tt_cum, ref_biomass = 0.0, 0.0
    demand, bg_multiplier = [], []
    for w in weather_rows:
        dtt = thermal_time_increment(w["tx"], w["tn"], crop["base_t"], crop["opt_t"], crop["max_t"])
        tt_cum += dtt
        ttf = tt_cum / crop["tt_maturity"]
        if ttf >= harvest_ttf:
            break
        eie = 0.0 if tt_cum < crop.get("tt_emergence", 0.0) else effective_canopy_cover(
            canopy_cover(ttf, crop.get("eix", 1.0), crop.get("canopy_shape", DEFAULT_CANOPY_SHAPE)),
            crop.get("plant_density_factor", 1.0))
        root_depth = root_max_m * min(1.0, ttf / 0.5)

        if tillage_doy is not None and w["doy"] == tillage_doy:
            mix_tilled_layers(layers, tillage_depth_m, tillage_mixing_efficiency)
            dr += TILLAGE_IMPLEMENTS[tillage_implement][1]

        # Mirrors simulate_season()'s main loop exactly -- see this function's own
        # irrigation_trigger_frac docstring paragraph for why this was missing and what it
        # silently broke.
        irrigation_mm = 0.0
        if irrigation_trigger_frac is not None:
            pre_avail_frac = root_zone_availability(layers, root_depth)
            if pre_avail_frac < irrigation_trigger_frac:
                irrigation_mm = irrigation_amount_mm

        infiltrate(layers, w["pp"] + irrigation_mm, curve_number, slope_pct)
        eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
        soil_evaporation(layers, eto, eie, precip_mm=w["pp"] + irrigation_mm, de_state=de_state)

        tmean = (w["tx"] + w["tn"]) / 2
        temp_factor = transpiration_temp_factor(tmean, crop["tr_min_t"], crop["tr_threshold_t"])
        rad_temp_factor = radiation_temp_factor(tmean, crop["tr_min_t"], crop.get("rad_temp_floor", 0.0),
                                                 crop.get("rad_temp_plateau_t", crop["tr_threshold_t"]))
        GR = crop["rue"] * rad_temp_factor * eie * w["solar"]
        es = 0.6108 * math.exp(17.27 * tmean / (tmean + 237.3))
        ea = es * (w["rhx"] + w["rhn"]) / 200
        Da = max(0.05, es - ea)
        TRp = (1 + (crop["kc"] - 1) * eie) * eie * eto
        TRp *= temp_factor

        avail_frac = root_zone_availability(layers, root_depth)
        water_stress = water_stress_response(avail_frac, crop.get("depletion_fraction", 0.5))
        TR_actual = min(TRp * water_stress, crop.get("tr_max_mm_day", math.inf))
        extract_transpiration(layers, root_depth, TR_actual)

        GT = crop["wue"] / math.sqrt(Da) * TR_actual
        dGB_water_limited = max(0.0, min(GR, GT)) * NET_GROWTH_FRACTION / 1000

        demand.append(dGB_water_limited * 10 * n_marginal_demand_pct(ref_biomass * 10, crop) * 10)
        weather_factor = rothc_temp_factor(tmean) * rothc_moisture_factor(layers[0]["theta"], layers[0]["fc"], layers[0]["pwp"])
        bg_multiplier.append((1.0 + tillage_ft(dr, ftx)) * weather_factor)
        if dr > 0:
            dr -= dr * tillage_dr_decay(layers)
        ref_biomass += dGB_water_limited
    return demand, bg_multiplier


NH3_FRAC_SYNTHETIC = 0.10  # IPCC 2006/2019 Refinement Tier-1 default FracGASF: 10% of applied
# synthetic mineral fertilizer N volatilizes as NH3/NOx when surface-applied -- a widely-cited
# general default (Table 11.3, Vol. 4), not derived from Cycles or this engine's own site data.
NH3_FRAC_MANURE = 0.20  # Same source's FracGASM: organic amendments (manure) volatilize at
# roughly twice the rate of mineral fertilizer, real and disclosed, not an invented multiplier.


def macnack_ammonia_loss_pct(soil_ph, air_temp_c, wind_speed_ms):
    """Macnack, Chim & Raun (2013), "Applied Model for Estimating Potential Ammonia Loss from
    Surface Applied Urea" (Communications in Soil Science and Plant Analysis 44:2055-2063) --
    a real, sourced, weather-driven alternative to the flat IPCC Tier-1 NH3_FRAC_SYNTHETIC
    default, specific to SURFACE-APPLIED (broadcast) urea. The paper compiled 159 records / 43
    site-years from 25 published articles (1960-2010), fit separate linear regressions of
    ammonia loss (AL, % of applied N) against soil pH, wind speed, and air temperature (each
    individually significant, p<0.05, but with low r^2: 0.18, 0.27, 0.04 respectively -- Table
    1 -- a real, disclosed limitation of a composite built across studies with different
    measurement windows, not a precise per-day flux model), then combined them additively into
    one final equation (paper's own text, "Materials and Methods"):
        AL = b0_pH + b1_pH*pH + b1_ws*WS + b1_AT*AT
    with b0_pH=-40.7, b1_pH=8.43, b1_ws=3.85 (WS in m/sec), b1_AT=0.33 (AT in deg C) -- the
    paper's own final reported coefficients. Returns a FRACTION (not percent), clamped to
    [0, 1] since the linear form is otherwise unbounded outside the real data's own range.
    """
    al_pct = -40.7 + 8.43 * soil_ph + 3.85 * wind_speed_ms + 0.33 * air_temp_c
    return max(0.0, min(1.0, al_pct / 100.0))


def simulate_season(weather_rows, crop, root_max_m=1.4, harvest_ttf=1.0, n_rate_kg_ha=None, record_history=False,
                     n_applications=None, n_credit_kg_ha=0.0, manure_n_kg_ha=0.0, manure_availability=0.5,
                     irrigation_trigger_frac=None, irrigation_amount_mm=25.0,
                     tillage_doy=None, tillage_implement=None, tillage_clay_frac=0.21,
                     fert_placement_implement=None, soil_ph=None,
                     spinup_rows=None, curve_number=75.0, slope_pct=0.0, initial_layers=None):
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

    tillage_doy, tillage_implement, tillage_clay_frac: tillage's real Cycles mechanism (soil
    mixing by an implement-specific coefficient, plus temporarily faster soil organic matter
    decomposition from disrupted aggregates -- Kemanian et al. 2024 Sec. 2.6, "tillage
    stimulation of Cs degradation") is coupled to the full six-pool soil carbon/nitrogen
    saturation system this engine deliberately does not implement (out of scope for v1, see
    CLAUDE.md). tillage_implement selects a real named implement from TILLAGE_IMPLEMENTS
    (parsed directly from Cycles v1.4.4's own till.txt, 86 real tools with real depth_m/
    soil_disturb_rating/mixing_efficiency values -- raises ValueError if the name isn't in
    that table). Two effects, split by how directly each is grounded in real data:
    (1) Soil moisture is genuinely mixed within the implement's real depth, weighted by its
    real mixing_efficiency, on tillage_doy itself -- see mix_tilled_layers() above for why
    this applies the real coefficient to moisture rather than the C/N pools Cycles itself
    mixes with it (this engine has no per-layer C/N pools to mix).
    (2) BACKGROUND_N_KG_HA_DAY is multiplied by (1 + ft) every day, where ft is C-Farm's own
    real, disclosed decomposition-acceleration factor (Kemanian & Stockle 2010 Eq. 5 -- see
    tillage_ft()/tillage_ftx()/tillage_dr_decay() above for the full formula and its real
    inputs), still a disclosed placeholder for the real six-pool fT effect (this engine has
    no soil-carbon pools for ft to act on directly), but now driven by the real formula's
    actual shape -- a cumulative disturbance rating (dr) that jumps by the real implement's
    SOIL_DISTURB_RATIO on tillage_doy and decays daily, rather than the earlier flat
    multiplier held constant for an arbitrary fixed number of days. tillage_clay_frac (0-1)
    feeds ftx's real texture scaling; defaults to 0.21, Rock Springs' own real topsoil clay
    fraction (SOIL_LAYERS_RAW's own top-layer value elsewhere in this file) -- pass a site's
    own real value when one is available (e.g. from a resolved STATSGO2 cell).
    tillage_doy=None (default) means neither effect runs.

    fert_placement_implement: real ammonia volatilization loss (previously this engine had NO
    volatilization pathway at all -- confirmed absent from both the paper and its SI by
    grepping the extracted SI text for "volatiliz" and finding zero matches -- so injected vs.
    broadcast fertilizer placement, Matt's own stated interest, had no mechanism to modulate).
    Not a Cycles formula (still undisclosed there); a real, independently-sourced Tier-1
    default from IPCC's 2006/2019 Refinement Guidelines (Table 11.3): NH3_FRAC_SYNTHETIC=0.10
    of applied mineral fertilizer N and NH3_FRAC_MANURE=0.20 of applied manure N volatilize
    when surface-broadcast, reduced by (1 - mixing_efficiency) of whichever real implement is
    named here -- reusing TILLAGE_IMPLEMENTS' real per-implement mixing_efficiency (already
    parsed from Cycles' own till.txt) for the physically real reason that incorporating
    fertilizer into the soil (anhydrous knife, manure injector) shields it from atmospheric
    loss the way surface broadcast never does, not because mixing_efficiency was defined for
    this purpose. Applied once, at the point mineral/manure N enters the pool -- volatilized N
    never becomes available to the crop or to leaching, tracked separately as
    n_volatilized_kg_ha for a complete mass balance alongside uptake/leached/remaining.
    n_credit_kg_ha (a previous-crop residual, not a fresh surface application) is not
    volatilized. fert_placement_implement=None (default) means no volatilization is modeled,
    reproducing the exact prior (zero-loss) behavior.

    soil_ph: when given, REPLACES the flat NH3_FRAC_SYNTHETIC=0.10 default with a real,
    weather-driven per-application estimate from macnack_ammonia_loss_pct() above (Macnack,
    Chim & Raun 2013) -- looks up each mineral application's own real day (mean of that day's
    tx/tn for air temp, that day's own wind) from weather_rows, real data this engine already
    carries, not a new dependency. Still reduced by (1 - mixing_efficiency) exactly like the
    IPCC-default path when fert_placement_implement is also given -- Macnack's own equation is
    specific to unincorporated surface urea and says nothing about incorporation, so the two
    effects (weather-driven base rate, incorporation shielding) compose rather than conflict.
    Manure keeps the flat NH3_FRAC_MANURE default regardless of soil_ph -- Macnack's data is
    urea-specific, not manure. This engine has no real soil pH data source (STATSGO2 doesn't
    carry pH, a genuine gap, not silently assumed away) -- soil_ph is a caller-supplied number,
    not derived internally; a real, typical cropland default (~6.5) is a reasonable choice
    absent site-specific data, but that choice is left to the caller, not hidden in here.
    soil_ph=None (default) means the flat IPCC-default behavior above is unchanged.
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
    defensible (see the Iowa/Kansas head-to-head comparison, CLAUDE.md 2026-09-22).

    root_max_m: real, disclosed per-crop GenericCrops.crop MAXIMUM_ROOTING_DEPTH values
    (corn 2.0m, silage corn 1.55m, soybean 1.5m, wheat 2.0m) OVERRIDE this parameter's own
    default when the crop dict sets its own "root_max_m" key -- previously every crop shared
    this same hardcoded 1.4m default regardless of species, a real, disclosed difference this
    engine was simply ignoring. crop.get("root_max_m", root_max_m) keeps exact prior behavior
    for any crop dict that doesn't set the field (backward compatible, no call site changes
    needed anywhere in this project).

    initial_layers: real multi-year, crop-inclusive soil-state carryover (2026-09-24). When
    given (a layers list in the exact shape crop["make_layers"]() returns -- typically a
    prior call's own returned "final_layers"), this season starts from THAT actual ending
    moisture state instead of always resetting to field capacity via crop["make_layers"]().
    None (default) reproduces the exact old always-fresh-start behavior byte-for-byte.

    This closes a real, substantial gap, not a marginal one: a directed head-to-head test
    against native Cycles at a semi-arid site (Western Kansas, real STATSGO2 soil, real
    NLDAS-2 weather, 2012 corn) found this engine overshoots by 18.44x when every season
    starts fresh. A hand-chained 3-year test (2010-2012, real crop-driven depletion carried
    forward via this exact mechanism, not bare fallow) cut that to 7.65x -- more than half
    the gap closed by this one change, the largest effect any single mechanism has had on
    that comparison this session (see QUESTIONS_FOR_DEVS.md item 6 for the full account,
    including a real test-harness bug that initially hid this finding and was caught and
    fixed before trusting it). Rock Springs' own 37-year validated record was NOT re-checked
    against a chained run before this was implemented -- carryover there would need the same
    real off-season weather (harvest day through next planting, spanning the calendar-year
    boundary) a caller must supply via spinup_rows, not something this function derives on
    its own.

    A caller chaining seasons must NOT pass the same crop dict's "make_layers" closure a
    shared, hand-built layers object the way this session's own early test scripts briefly
    did by mistake -- that let this function's OWN internal _reference_n_demand() precompute
    pass (an intentionally-independent, throwaway parallel trajectory, never the real season)
    mutate the same soil state the real main loop below was also mutating, silently
    corrupting the result. initial_layers exists specifically so a caller never needs that
    workaround: this function deep-copies initial_layers internally, once for
    _reference_n_demand()'s own independent pass, once for the main loop's real trajectory
    below -- the two can never see or affect each other's soil state, regardless of what a
    caller passes in. When initial_layers is given, the result dict also carries
    "final_layers" -- the real ending soil state (theta, and any per-layer state a future
    mechanism might add), ready to feed into the next chained call's own initial_layers with
    no extraction step needed."""
    layers = copy.deepcopy(initial_layers) if initial_layers is not None else crop["make_layers"]()
    root_max_m = crop.get("root_max_m", root_max_m)
    de_state = dict(de=0.0, tew=compute_tew(layers[0]["fc"], layers[0]["pwp"]), rew=REW_DEFAULT_MM)
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
            soil_evaporation(layers, eto, 0.0, precip_mm=w["pp"], de_state=de_state)
    tillage_depth_m, tillage_mixing_efficiency = None, None
    if tillage_doy is not None:
        if tillage_implement not in TILLAGE_IMPLEMENTS:
            raise ValueError(f"Unknown tillage implement {tillage_implement!r} -- see TILLAGE_IMPLEMENTS for the real Cycles v1.4.4 implement catalog.")
        tillage_depth_m, tillage_disturb_rating, tillage_mixing_efficiency = TILLAGE_IMPLEMENTS[tillage_implement]
    tillage_ftx_val = tillage_ftx(tillage_clay_frac)
    tillage_dr = 0.0  # cumulative disturbance state -- see tillage_ft()/tillage_dr_decay() above
    tt_cum, biomass, ag_biomass = 0.0, 0.0, 0.0
    n_tracking_active = (not crop.get("legume", False)) and (
        n_rate_kg_ha is not None or n_applications or n_credit_kg_ha or manure_n_kg_ha)
    volatilization_active = fert_placement_implement is not None or soil_ph is not None
    fert_mixing_efficiency = 0.0
    if fert_placement_implement is not None:
        if fert_placement_implement not in TILLAGE_IMPLEMENTS:
            raise ValueError(f"Unknown fertilizer placement implement {fert_placement_implement!r} -- see TILLAGE_IMPLEMENTS for the real Cycles v1.4.4 implement catalog.")
        fert_mixing_efficiency = TILLAGE_IMPLEMENTS[fert_placement_implement][2]
    wx_by_doy = {w["doy"]: w for w in weather_rows} if soil_ph is not None else None

    def mineral_retention_for_doy(doy):
        if not volatilization_active:
            return 1.0
        if soil_ph is None:
            base_frac = NH3_FRAC_SYNTHETIC
        else:
            w = wx_by_doy.get(doy)
            # Fallback to the flat default if an application day falls outside the tracked
            # weather window (e.g. spinup-only doy) -- real weather just isn't available there.
            base_frac = NH3_FRAC_SYNTHETIC if w is None else macnack_ammonia_loss_pct(
                soil_ph, (w["tx"] + w["tn"]) / 2.0, w["wind"])
        return 1.0 - base_frac * (1.0 - fert_mixing_efficiency)

    manure_retention = 1.0 - NH3_FRAC_MANURE * (1.0 - fert_mixing_efficiency) if volatilization_active else 1.0
    n_volatilized_total = 0.0 if volatilization_active else None
    applications_by_doy = {}
    if n_tracking_active:
        n_volatilized_mineral = 0.0
        if n_applications:
            mineral_applied = sum(amount for _, amount in n_applications)
            total_n_input_kg_ha = 0.0
            n_pool = 0.0  # events fund the pool on their own scheduled days below, not all at once
            for doy, amount in n_applications:
                r = mineral_retention_for_doy(doy)
                retained = amount * r
                applications_by_doy[doy] = applications_by_doy.get(doy, 0.0) + retained
                total_n_input_kg_ha += retained
                n_volatilized_mineral += amount * (1.0 - r)
        else:
            mineral_applied = n_rate_kg_ha or 0.0
            planting_doy = weather_rows[0]["doy"] if weather_rows else None
            r = mineral_retention_for_doy(planting_doy)
            total_n_input_kg_ha = mineral_applied * r
            n_pool = total_n_input_kg_ha  # original single-lump behavior, unchanged when n_applications isn't used
            n_volatilized_mineral = mineral_applied * (1.0 - r)
        manure_after_volatilization = manure_n_kg_ha * manure_retention
        credit_and_manure = n_credit_kg_ha + manure_after_volatilization * manure_availability
        total_n_input_kg_ha += credit_and_manure
        n_pool += credit_and_manure  # credit/manure land at day 0 either way, real applications are the only dated ones
        if n_volatilized_total is not None:
            n_volatilized_total = n_volatilized_mineral + manure_n_kg_ha * (1.0 - manure_retention)
    else:
        n_pool, total_n_input_kg_ha = None, None
    n_leached_total = 0.0 if n_pool is not None else None
    n_uptake_total = 0.0 if n_pool is not None else None
    irrigation_total_mm = 0.0
    history = [] if record_history else None

    n_stress_fraction, daily_demand, day_i = 1.0, None, 0
    if n_pool is not None:
        daily_demand, tillage_bg_multiplier = _reference_n_demand(
            weather_rows, crop, root_max_m, harvest_ttf, curve_number=curve_number, slope_pct=slope_pct,
            spinup_rows=spinup_rows, tillage_doy=tillage_doy, tillage_implement=tillage_implement,
            tillage_clay_frac=tillage_clay_frac, initial_layers=initial_layers,
            irrigation_trigger_frac=irrigation_trigger_frac, irrigation_amount_mm=irrigation_amount_mm)
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
            total_background_kg_ha += BACKGROUND_N_KG_HA_DAY * tillage_bg_multiplier[i]
        total_supply_kg_ha = total_n_input_kg_ha + total_background_kg_ha
        supply_ratio = min(1.0, total_supply_kg_ha / total_demand_kg_ha) if total_demand_kg_ha > 0 else 1.0
        n_stress_fraction = 2 * supply_ratio - supply_ratio ** 2  # quadratic-plateau, see docstring above

    for w in weather_rows:
        dtt = thermal_time_increment(w["tx"], w["tn"], crop["base_t"], crop["opt_t"], crop["max_t"])
        tt_cum += dtt
        ttf = tt_cum / crop["tt_maturity"]
        if ttf >= harvest_ttf:
            break
        eie = 0.0 if tt_cum < crop.get("tt_emergence", 0.0) else effective_canopy_cover(
            canopy_cover(ttf, crop.get("eix", 1.0), crop.get("canopy_shape", DEFAULT_CANOPY_SHAPE)),
            crop.get("plant_density_factor", 1.0))
        root_depth = root_max_m * min(1.0, ttf / 0.5)

        # Tillage's soil-moisture mixing happens once, on tillage_doy itself, before
        # today's irrigation check and water balance -- see mix_tilled_layers() above.
        # The cumulative disturbance rating (tillage_dr) jumps by the real implement's
        # SOIL_DISTURB_RATIO the same day -- see tillage_ft()/tillage_dr_decay() above.
        if tillage_doy is not None and w["doy"] == tillage_doy:
            mix_tilled_layers(layers, tillage_depth_m, tillage_mixing_efficiency)
            tillage_dr += tillage_disturb_rating

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
        soil_evaporation(layers, eto, eie, precip_mm=w["pp"] + irrigation_mm, de_state=de_state)

        tmean = (w["tx"] + w["tn"]) / 2
        temp_factor = transpiration_temp_factor(tmean, crop["tr_min_t"], crop["tr_threshold_t"])
        rad_temp_factor = radiation_temp_factor(tmean, crop["tr_min_t"], crop.get("rad_temp_floor", 0.0),
                                                 crop.get("rad_temp_plateau_t", crop["tr_threshold_t"]))
        GR = crop["rue"] * rad_temp_factor * eie * w["solar"]
        es = 0.6108 * math.exp(17.27 * tmean / (tmean + 237.3))
        ea = es * (w["rhx"] + w["rhn"]) / 200
        Da = max(0.05, es - ea)
        TRp = (1 + (crop["kc"] - 1) * eie) * eie * eto
        TRp *= temp_factor

        avail_frac = root_zone_availability(layers, root_depth)
        water_stress = water_stress_response(avail_frac, crop.get("depletion_fraction", 0.5))
        # tr_max_mm_day: real, disclosed per-crop TRANSPIRATION_MAX from GenericCrops.crop
        # (corn/silage corn 10, soybean/wheat 8 mm/day), a physical ceiling on daily
        # transpiration this engine never applied before -- crop.get(...) with an inf
        # default keeps this a no-op for any crop dict that doesn't set it. Checked before
        # relying on it: at Rock Springs, computed TRp never exceeds ~7.4mm/day across the
        # full 37-year record for any validated crop, so this is a genuine no-op there (the
        # regression suite's own unchanged numbers confirm it) -- kept anyway since it's real
        # and could matter at a hotter/drier site already used elsewhere in this project
        # (e.g. Kansas), not because it moves any currently-validated number.
        TR_actual = min(TRp * water_stress, crop.get("tr_max_mm_day", math.inf))
        extract_transpiration(layers, root_depth, TR_actual)

        GT = crop["wue"] / math.sqrt(Da) * TR_actual
        dGB_water_limited = max(0.0, min(GR, GT)) * NET_GROWTH_FRACTION / 1000

        n_stress = 1.0
        if n_pool is not None:
            if w["doy"] in applications_by_doy:
                n_pool += applications_by_doy[w["doy"]]
            if dGB_water_limited > 0:
                weather_factor = rothc_temp_factor(tmean) * rothc_moisture_factor(layers[0]["theta"], layers[0]["fc"], layers[0]["pwp"])
                n_pool += BACKGROUND_N_KG_HA_DAY * (1.0 + tillage_ft(tillage_dr, tillage_ftx_val)) * weather_factor
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

        if tillage_dr > 0:
            tillage_dr -= tillage_dr * tillage_dr_decay(layers)

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
    if n_volatilized_total is not None:
        result["n_volatilized_kg_ha"] = n_volatilized_total
    if initial_layers is not None:
        result["final_layers"] = layers
    return result
