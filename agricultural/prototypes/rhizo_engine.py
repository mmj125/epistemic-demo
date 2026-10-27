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
import os
import math

REFERENCE_DATA_DIR = os.environ.get("REF_DIR", "/tmp/cycles-run")  # set to a local Cycles v1.4.4 sample directory to reproduce validation

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

PSI_E_FROM_ANCHOR = True    # default since 2026-10-08 (16-site N150 grain MAE 1.37 -> 1.11, corr 0.77 -> 0.82); see saxton_rawls()


def saxton_rawls(sand_pct, clay_pct, om_pct, fc_measured=None, pwp_measured=None, bd_measured=None):
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
    if fc_measured is not None and pwp_measured is not None:   # measured water retention (volumetric, 33 and 1500 kPa) replaces the texture estimate; B, psi_e and ksat follow from it below
        fc, pwp = fc_measured, pwp_measured
        sat = max(1.0 - bd_measured / 2.65 if bd_measured else sat, fc + 0.02)

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
    if PSI_E_FROM_ANCHOR:
        # Self-consistent Campbell curve: psi(fc) = -33 kPa exactly (B above is already fitted through the
        # 33 and 1500 kPa points). Eq. 4 is a regression (SE ~2.9 kPa) whose small values, amplified by
        # (theta/sat)^-B, gave +550 kPa at field capacity for sands (Carolina) and flipped sign between layers.
        psi_e = 33.0 * (fc / sat) ** B
    ksat_mm_h = 1930 * (sat - fc) ** (3 - lam)
    return dict(pwp=pwp, fc=fc, sat=sat, psi_e_kpa=psi_e, B=B, lam=lam,
                ksat_mm_day=ksat_mm_h * 24)


KHE_SCALE = 1.0  # (the N-loss refit's 0.279 cost yield, row 46)  # multiplier on the capacitance-weighted conductivity in redistribute() (1.0 = validated default); under test 2026-10-06


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


FWC_NO_UPPER_CLIP = True  # step 2: let a layer above field capacity count above 1 (Cycles does); only the total is capped at 1


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
    MECHANISM_LOG.md item 1 -- the whole curve-number mechanism is now Cycles' own
    disclosed structure with a real, cited f_wc, not a substitute borrowed from a different
    model family."""
    z_prev, weighted_sum, weight_total = 0.0, 0.0, 0.0
    for l in layers:
        z = z_prev + l["thick"]
        if z > depth_m + 1e-9:
            break
        ffc_l = (l["theta"] - l["pwp"]) / (l["fc"] - l["pwp"]) if l["fc"] > l["pwp"] else 0.0
        ffc_l = max(0.0, ffc_l if FWC_NO_UPPER_CLIP else min(1.0, ffc_l))
        w = (z - z_prev) / z if z > 0 else 0.0
        weighted_sum += ffc_l * w
        weight_total += w
        z_prev = z
    r = weighted_sum / weight_total if weight_total > 0 else 0.0
    return min(1.0, r) if FWC_NO_UPPER_CLIP else r


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
# MECHANISM_LOG.md item 6 for the full evidence trail.
INITIAL_MOISTURE_FRACTION = 0.5


REDISTRIBUTE_MAX_STEPS = 200  # safety cap against a floating-point edge case ever
# preventing time_left from reaching exactly zero -- real profiles converge in a
# handful of steps (rarely more than the layer count), this is headroom, not a target.


SOLUTE_GJ_EQ1 = True   # 2026-10-27 step 9: nitrate leaching as in CERES (Godwin and Jones 1991 Eq. 1), instead of drainage over the saturated water volume
SOLUTE_VOL_SAT = True   # 2026-10-18 measured on Cycles' own daily output (6 sites, 37 years, N=150, leach_transport_2026_10_18.py): nitrate leached out of the profile = drainage x previous-day bottom-layer nitrate / the layer's SATURATED water volume (ratio to Cycles 0.96 to 1.03, daily corr 0.99 to 1.00), not / its current water content; applied to the gravity-drainage stage of every layer. False restores division by current water.
def redistribute(layers, water_in_mm, n_substeps=REDISTRIBUTE_SUBSTEPS, n_by_layer=None):
    """First, infiltration fills each layer to saturation, cascading any overflow to the
    next layer down -- unconditional, not governed by Eq. 1-2 (this matches the paper's own
    stated first step: "infiltration is allocated to the first soil layer, up to
    saturation"). Second, when every layer carries the full Saxton-Rawls parameter set
    (psi_e_kpa, B, sat, plus ksat_mm_day), gravity drainage of any layer above field
    capacity now runs as the paper's OWN real Eq. 1-2 adaptive, PROFILE-WIDE stepping
    scheme (2026-09-30, replacing the earlier fixed-24-substep-per-layer approximation
    below): at the start of each step, every active (theta>fc) layer's own travel time
    t=(theta-fc)*thick/khe is computed (Eq. 2, algebraically simplified -- see below), the
    single largest one across the WHOLE profile sets this step's shared dt (the paper's own
    words: "the time step is... set as that of the layer with the slowest travel time in
    the soil profile at the beginning of the time step"), every active layer drains
    flux=min(excess, khe*dt) using THAT SAME dt (so the slowest layer reaches exactly its
    own field capacity while faster layers are naturally capped at their own excess, having
    already been resolved within this dt), and only THEN does the total outflow cascade
    downward through the profile (each layer's own drainage plus whatever overflowed from
    shallower layers into it, filling to saturation, further overflow continuing deeper) --
    repeating until no layer has excess left or the cumulative dt reaches one full day.
    Third, matching the paper's own stated fallback ("if the water allocated to daily
    infiltration has not been redistributed after 24h, the soil layers are saturated from
    top to bottom and excess water... drained as percolation"): any water still unresolved
    when the daily budget runs out simply exits the profile as return value (deep
    percolation / leaching source), exactly as it always has in this function.

    Eq. 2 as printed (Kemanian et al. 2024) is t=(theta-thetafc)*dz*rho_w/(khe*g), with
    khe stated in the paper's own native mass-based units (kg s m^-3) -- NOT the same units
    this file's campbell_khe() deliberately outputs (mm/day, matching ksat, chosen when
    Eq. 1 was first implemented). Converting the paper's mass-based khe_paper to this
    engine's length-based K_length via K_length=khe_paper*g/rho_w (the standard head-vs-
    energy-per-mass potential relationship) and substituting into Eq. 2 makes rho_w and g
    cancel completely: t=(theta-thetafc)*dz/K_length -- the plain, physically obvious
    "excess depth divided by flow rate," directly usable with the already-verified
    campbell_khe() and requiring no new unit-conversion code. Confirmed dimensionally
    self-consistent both ways (SI base units give seconds, as the paper states; this
    engine's own mm/day-and-days convention gives days) before trusting it.

    Verified against the fixed-substep version this replaces (2026-09-30): the standing
    tillage/manure/mass-balance sanity checks and the full 4-crop Rock Springs validation
    suite were re-run after this change -- see the calling code's own commit message and
    MECHANISM_LOG.md for the actual before/after numbers, not reproduced here since
    this docstring predates any specific run's results.

    A layer with only ksat_mm_day (no psi_e_kpa/B) falls back to a flat rate cap for its
    whole-day drainage, and a layer with neither field falls back to the original
    unlimited-rate behavior -- unchanged from before, and still keyed on ALL layers sharing
    the same tier (every make_layers()-equivalent in this project builds a uniform profile,
    so a genuinely mixed-tier profile within one call has never actually occurred).

    n_by_layer, when given (a list of kg N/ha, one per layer, mutated in place, built
    2026-09-30 for the real CropSyst-style min(demand, potential_uptake) mechanism -- see
    MECHANISM_LOG.md), is transported downward in lockstep with the SAME gravity-
    drainage fluxes computed above (stage two), at each layer's own current concentration
    (kg N per mm of that layer's own water) -- solute never modeled separately from the
    water that carries it. A disclosed simplification: stage ONE (the saturation-fill/
    cascade at the top of this function, driven by incoming rainfall/irrigation) does NOT
    move n_by_layer at all, on the assumption that incoming water itself carries no
    dissolved N -- real rain is close to N-free, and any N sitting in a layer that stage
    one pushes to or past saturation still gets picked up by stage two's own drainage
    check on the SAME call (theta>fc includes theta=sat), just possibly capped by that
    layer's own travel time rather than moving instantly; a layer would only need more
    than one day to fully clear under an unusually large single-day storm, a small, named
    approximation rather than an unmodeled gap. Returns (remaining, n_leached) always --
    n_leached is exactly 0.0 when n_by_layer is None, so a caller passing water-only
    arguments is completely unaffected by this parameter's existence."""
    remaining = water_in_mm
    n_leached = 0.0
    thicks_mm = [l["thick"] * 1000 for l in layers]
    for i, l in enumerate(layers):
        incoming_before = remaining
        water_before_mm = l["theta"] * thicks_mm[i]
        add = min(remaining, max(0.0, (l["sat"] - l["theta"]) * thicks_mm[i]))
        l["theta"] += add / thicks_mm[i]
        overflow = incoming_before - add
        if n_by_layer is not None and overflow > 1e-9:
            # Well-mixed-reservoir assumption (the same one this project's own original,
            # whole-profile leaching formula already used) applied per layer: incoming
            # water is N-free, mixes instantly with the layer's resident N, and whatever
            # overflows onward carries a share of that mix proportional to how much of
            # the total (resident + incoming) water it represents. Needed because a thin,
            # fast-saturating surface layer (where fertilizer actually lands) moves most
            # of its water through THIS stage, not stage two's slower gravity drainage --
            # confirmed directly: without this, N applied at the surface never leaves the
            # top layer at all (0.0 leaching in every tested year), an early real bug this
            # docstring note exists to keep from recurring.
            mixed_water = water_before_mm + incoming_before
            if mixed_water > 1e-9:
                n_out_overflow = n_by_layer[i] * (overflow / mixed_water)
                n_by_layer[i] -= n_out_overflow
                if i + 1 < len(layers):
                    n_by_layer[i + 1] += n_out_overflow
                else:
                    n_leached += n_out_overflow
        remaining -= add

    if layers and all("psi_e_kpa" in l and "B" in l for l in layers):
        time_left = 1.0
        _sub = [] if DIAG_SUBDAY is not None else None
        _p = DENITRIF_RESP_REL_POW
        _prev = max(layers[0]["theta"] / layers[0]["sat"], 0.0)
        _acc = 0.0
        for _ in range(REDISTRIBUTE_MAX_STEPS):
            excesses = [max(0.0, (l["theta"] - l["fc"]) * thicks_mm[i]) for i, l in enumerate(layers)]
            khes = [KHE_SCALE * campbell_khe(l["theta"], l["fc"], l["sat"], l["ksat_mm_day"], l["psi_e_kpa"], l["B"])
                    if excesses[i] > 1e-9 else 0.0 for i, l in enumerate(layers)]
            travel_times = [e / k for e, k in zip(excesses, khes) if k > 0]
            if not travel_times:
                break
            dt = min(max(travel_times), time_left)
            if dt <= 1e-9:
                break
            if _sub is not None:
                _sub.append((dt, [l["theta"] / l["sat"] for l in layers[:3]]))
            fluxes = [min(excesses[i], khes[i] * dt) if khes[i] > 0 else 0.0 for i in range(len(layers))]
            water_before_mm = [l["theta"] * thicks_mm[i] for i, l in enumerate(layers)]
            n_out = [0.0] * len(layers)
            for i, l in enumerate(layers):
                l["theta"] -= fluxes[i] / thicks_mm[i]
                if n_by_layer is not None and water_before_mm[i] > 1e-9:
                    if SOLUTE_GJ_EQ1:
                        n_out[i] = n_by_layer[i] * fluxes[i] / (water_before_mm[i] + fluxes[i])   # Godwin and Jones 1991 Eq. 1: the fraction of the layer's nitrate that moves is drainage over retained water plus drainage
                    else:
                        n_out[i] = fluxes[i] * (n_by_layer[i] / (l["sat"] * thicks_mm[i] if SOLUTE_VOL_SAT else water_before_mm[i]))
                    n_by_layer[i] -= n_out[i]
            carry = 0.0
            n_carry = 0.0
            for i, l in enumerate(layers):
                carry += fluxes[i]
                if n_by_layer is not None:
                    n_carry += n_out[i]
                if carry <= 0:
                    continue
                if i + 1 < len(layers):
                    nxt = layers[i + 1]
                    add2 = min(carry, max(0.0, (nxt["sat"] - nxt["theta"]) * thicks_mm[i + 1]))
                    nxt["theta"] += add2 / thicks_mm[i + 1]
                    if n_by_layer is not None and carry > 1e-9:
                        n_added = n_carry * (add2 / carry)
                        n_by_layer[i + 1] += n_added
                        n_carry -= n_added
                    carry -= add2
                else:
                    remaining += carry
                    if n_by_layer is not None:
                        n_leached += n_carry
                        n_carry = 0.0
                    carry = 0.0
            _new = max(layers[0]["theta"] / layers[0]["sat"], 0.0)
            _acc += dt * 0.5 * (_prev ** _p + _new ** _p)
            _prev = _new
            time_left -= dt
            if time_left <= 1e-9:
                break
        _acc += max(time_left, 0.0) * _prev ** _p
        global _SUBDAY_REL1_EFF
        _SUBDAY_REL1_EFF = _acc ** (1.0 / _p)   # time-weighted layer-1 saturation over the day's redistribution steps
        if _sub is not None:
            DIAG_SUBDAY.append((_sub, time_left, [l["theta"] / l["sat"] for l in layers[:3]]))
        return remaining, n_leached

    for i, l in enumerate(layers):
        excess_mm = max(0.0, (l["theta"] - l["fc"]) * thicks_mm[i])
        rate_cap = l.get("ksat_mm_day", math.inf)
        drain = min(excess_mm, rate_cap)
        water_before_mm = l["theta"] * thicks_mm[i]
        l["theta"] -= drain / thicks_mm[i]
        remaining += drain
        if n_by_layer is not None and water_before_mm > 1e-9:
            n_out_i = drain * (n_by_layer[i] / (l["sat"] * thicks_mm[i] if SOLUTE_VOL_SAT else water_before_mm))
            n_by_layer[i] -= n_out_i
            if i + 1 < len(layers):
                n_by_layer[i + 1] += n_out_i
            else:
                n_leached += n_out_i
    return remaining, n_leached


def infiltrate(layers, water_in_mm, curve_number, slope_pct, n_by_layer=None):
    """One day's curve-number runoff (Eq. SI.1-7, sign-corrected) followed by infiltration
    (redistribute()) -- shared by simulate_season()'s main loop and its optional spin-up
    window, so the two can't drift apart. Previously runoff_mm()/moisture_adjusted_cn()
    existed but were never actually called anywhere in the water balance (all precipitation
    went straight to infiltration) -- see CLAUDE.md, 2026-09-22, for why this was flagged as
    a real gap rather than a deliberate simplification: it means every drop of rain currently
    enters the soil, which retains more water than reality especially in a drier climate.
    Moisture adjustment now goes through retention_param_mm()'s real SWAT formula directly
    (2026-09-23) rather than the earlier compute_fwc()/moisture_adjusted_cn() ad hoc pair --
    see retention_param_mm()'s own docstring for the source and verification.

    n_by_layer, when given, is passed straight through to redistribute() for the real
    per-layer nitrogen transport it implements -- see that function's own docstring.
    Always returns a 3-tuple now (drainage_mm, runoff, n_leached); n_leached is 0.0
    whenever n_by_layer isn't given, so every pre-existing call site just needs to
    unpack one extra value, not change behavior."""
    if water_in_mm <= 0:
        return 0.0, 0.0, 0.0
    s_mm = retention_param_mm(layers, curve_number)
    runoff = runoff_mm(water_in_mm, s_mm, slope_pct)
    drainage_mm, n_leached = redistribute(layers, water_in_mm - runoff, n_by_layer=n_by_layer)
    if DIAG_DRAIN is not None: DIAG_DRAIN.append((_DIAG_YEAR, drainage_mm, n_leached))
    return drainage_mm, runoff, n_leached


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


# Air-dry floor of the CropSyst surface-evaporation formula as a fraction of wilting point (CropSyst's own 1/3; Cycles' layer 1 reaches 0.62-0.94).
CROPSYST_AIRDRY_FRAC = 1.0 / 3.0


EVAP_LAW_PARAMS = (0.25, 0.85, 3.5)   # air-dry as a fraction of wilting point, critical water content as a fraction of field capacity, exponent; measured on Cycles designed experiments (class D), adopted 2026-10-26 after the water budget and county-yield tests (plan 2026-10-26); was (0.5, 0.7, 2.0)
SOIL_EVAP_SCALE = 1.0  # multiplier on the potential soil-evaporation demand (tested 2026-10-13)


SNOW_MODEL = True   # 2026-10-13: snowpack measured from designed experiments on Cycles v1.5.20 (see snow_adjust); off by default
SNOW_RAIN_TEMP_C = 1.0    # precipitation is rain at a daily mean temperature >= this, snow below it
SNOW_MELT_BASE_C = -1.0   # melt base temperature
SNOW_MELT_DDF = 2.5       # mm per degree C


def snow_adjust(layers, w, lat_deg):
    """Cycles' snowpack, reproduced from designed experiments (bare field, constant atmosphere, 40-150 mm packs; every
    number below matched Cycles to 0.1 mm over 100+ cases): precipitation falls as snow when the daily mean temperature
    is below 1 C and as rain otherwise; the pack loses water by sublimation equal to the reference evapotranspiration
    each day it is present (ratio exactly 1.00 in every case), then by melt that does not depend on pack size:
    tmax <= -1 C: none; tmin > -1 C: 2.5 * (tmean + 1); otherwise 2.5 * (tmax + 1)^2 / (tmax - tmin). Water reaching the
    soil is rain plus melt, and soil evaporation is zero on days with snow. Returns the weather row with pp replaced by
    that water input and snow_day set. The pack (swe_mm) is stored on layers[0] so it persists across windows."""
    l0 = layers[0]
    swe = l0.get("swe_mm", 0.0)
    tx, tn, pp = w["tx"], w["tn"], w["pp"]
    tmean = (tx + tn) / 2.0
    snowfall = pp if tmean < SNOW_RAIN_TEMP_C else 0.0
    rain = pp - snowfall
    swe += snowfall
    if swe <= 0.0:
        return w
    eto = eto_fao56(w["doy"], tx, tn, w["solar"], w["rhx"], w["rhn"], w["wind"], lat_deg)
    t0 = SNOW_MELT_BASE_C
    if tx <= t0:
        m = 0.0
    elif tn > t0:
        m = SNOW_MELT_DDF * (tmean - t0)
    else:
        m = SNOW_MELT_DDF * (tx - t0) ** 2 / (tx - tn)
    melt = min(swe, m)
    swe -= melt
    sub = min(swe, eto)
    swe -= sub
    l0["swe_mm"] = swe
    w2 = dict(w)
    w2["pp"] = rain + melt
    w2["snow_day"] = True
    return w2


EVAP_ZONE_DEPTH_M = 0.2   # step 4: when set, the Cycles law acts on the thickness-weighted state of the top EVAP_ZONE_DEPTH_M of the profile


def soil_evaporation_zone(layers, pot_evap_mm, zone_start):
    """Step 4: Cycles evaporates from the top ~0.2 m of the profile, not from layer 1 as such (with layer 1 of 0.15 m or
    thicker it is mostly layer 1; with thin layers it spans several). The same law as soil_evaporation_cycles acts on the
    zone's thickness-weighted water content, fc and wilting point; the water comes out of every zone layer in equal
    volumetric steps (shares of loss by layer matched the 13 test sites to 0.04 on average at 0.2 m).
    zone_start is the zone's mean water content at the start of the day."""
    a, b, n = EVAP_LAW_PARAMS
    zlayers, tot = [], 0.0
    for l in layers:
        t = min(l["thick"], max(0.0, EVAP_ZONE_DEPTH_M - tot))
        if t <= 0:
            break
        zlayers.append((l, t)); tot += t
    zfc = sum(l["fc"] * t for l, t in zlayers) / tot
    zpwp = sum(l["pwp"] * t for l, t in zlayers) / tot
    tc, ta = b * zfc, a * zpwp
    ratio = 1.0 if zone_start >= tc else max(0.0, (zone_start - ta) / (tc - ta)) ** n
    zth = sum(l["theta"] * t for l, t in zlayers) / tot
    avail = max(0.0, (zth - ta) * tot * 1000)
    evap = min(ratio * pot_evap_mm, avail)
    dtheta = evap / (tot * 1000)
    # 2026-10-15: no zone layer may be drawn below its own air-dry water content. With thin top layers the zone's mean can stay high
    # (a rain-fed layer 1) while layers 2-3 are drained every day by the equal-volumetric-step rule until negative (found in the
    # designed fallow experiment, REFIT_PLAN row 42). The cap is inactive whenever the zone is uniformly wet, so normal runs are unchanged.
    taken = 0.0
    for l, t in zlayers:
        take = min(dtheta, max(0.0, l["theta"] - a * l["pwp"]))
        l["theta"] -= take * t / l["thick"]   # the zone takes only its part of a thicker layer
        taken += take * t * 1000
    return taken


SOIL_EVAP_DOC = None   # None: the fitted Cycles law on the top EVAP_ZONE_DEPTH_M (default); "fao56": FAO-56 two-stage Kr with REW and TEW (Allen et al. 1998, Eqs 73 to 77); "cropsyst": the CropSyst Evaporator form


def soil_evaporation_fao56(layers, pot_evap_mm, precip_mm, de_state, snow_day=False):
    """FAO-56 two-stage bare-soil evaporation (Allen et al. 1998, ch. 7 and 8). De is the cumulative depth evaporated since the surface layer was last at
    field capacity: rain reduces it (Eq. 77 with no runoff, irrigation or transpiration term for the evaporation layer), evaporation raises it. Stage 1 (De <= REW)
    evaporates at the full demand; stage 2 scales it by Kr = (TEW - De)/(TEW - REW) (Eq. 74). TEW = 1000 (theta_fc - 0.5 theta_pwp) Ze (Eq. 73, `compute_tew`),
    REW from `REW_DEFAULT_MM`. The water leaves the top EVAP_ZONE_DEPTH_M in equal volumetric steps, never below half the wilting point."""
    if snow_day:
        return 0.0
    tew, rew = de_state["tew"], de_state["rew"]
    de = max(0.0, de_state["de"] - max(precip_mm, 0.0))
    kr = 1.0 if de <= rew else max(0.0, (tew - de) / max(1e-9, tew - rew))
    zl, tot = [], 0.0
    for l in layers:
        t = min(l["thick"], max(0.0, EVAP_ZONE_DEPTH_M - tot))
        if t <= 0:
            break
        zl.append((l, t)); tot += t
    avail = sum(max(0.0, l["theta"] - 0.5 * l["pwp"]) * t for l, t in zl) * 1000.0
    evap = min(kr * pot_evap_mm, avail)
    dtheta = evap / (tot * 1000.0)
    taken = 0.0
    for l, t in zl:
        take = min(dtheta, max(0.0, l["theta"] - 0.5 * l["pwp"]))
        l["theta"] -= take * t / l["thick"]
        taken += take * t * 1000.0
    de_state["de"] = min(tew, de + taken)
    return taken


def zone_mean_theta(layers):
    tot, w = 0.0, 0.0
    for l in layers:
        t = min(l["thick"], max(0.0, EVAP_ZONE_DEPTH_M - tot))
        if t <= 0:
            break
        w += l["theta"] * t; tot += t
    return w / tot


def soil_evaporation(layers, eto_mm, canopy_cover_frac, precip_mm=0.0, de_state=None,
                      use_cropsyst_formula=False, fallow=False, summer_time=False, theta_start=None, snow_day=False):
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
    byte-for-byte -- every existing caller not yet passing de_state is unaffected.

    use_cropsyst_formula=True (default False, so every existing validated number is
    byte-identical) switches to a real, alternate, fully-disclosed formula for this same
    physical process instead of the FAO-56 Kr mechanism above -- see
    soil_evaporation_cropsyst()'s own docstring for the source and shape, and its own
    "NOT YET VALIDATED" note before relying on it for anything real."""
    if snow_day:
        return 0.0
    demand_mm = eto_mm * (1 - canopy_cover_frac) * SOIL_EVAP_SCALE
    if SOIL_EVAP_DOC == "fao56" and de_state is not None:
        return soil_evaporation_fao56(layers, demand_mm, precip_mm, de_state, snow_day)
    if SOIL_EVAP_DOC == "cropsyst":
        return soil_evaporation_cropsyst(layers, demand_mm, fallow=fallow, summer_time=summer_time)
    if theta_start is not None:
        return soil_evaporation_zone(layers, demand_mm, theta_start)
    return soil_evaporation_cropsyst(layers, demand_mm, fallow=fallow, summer_time=summer_time)


# Residue cover and residue evaporation (2026-10-02), back-calculated from Cycles' own output at 16 sites:
# water.txt SOIL EVAP / ETo on wet, canopy-free, rain-free days equals (1 - residue cover) almost exactly
# (cover from residue.txt FRAC INTERCEP, 35,017 days, every 0.1 cover bin within 0.01), and residue cover
# follows 1 - exp(-0.27 * residue biomass (AG + BG, Mg/ha)) (bins 0.2-0.5 -> 0.09 ... 8-15 -> 0.90). A separate
# RES EVAP term takes about min(0.55 * rain, 1.0) mm on rain days at cover 0.77 (scaled here by cover/0.77).
# Together they explain why Cycles' soil evaporation is 0.14-0.9 of ETo by site (residue decays fast at warm
# sites) where this engine evaporated ~1.0 x ETo all off-season and ended 90-140 mm/yr too dry. Only active
# when the per-layer six-pool state (which tracks the surface residue pool cra) is in use.
RESIDUE_COVER_K = 0.27
RESIDUE_RAIN_EVAP_FRAC = 0.55
RESIDUE_RAIN_EVAP_CAP_MM = 1.0
RESIDUE_COVER_REF = 0.77
RESIDUE_COVER_BIOMASS_FRAC = 1.0  # 2026-10-18 was 0.7: that factor corrected a pool mass mismatch of 2026-10-02 (engine surface residue about 1.4x Cycles'), but after the residue refits the pool is within about 6% of Cycles' above-ground residue biomass, so 0.7 left cover 21 to 30% too low, soil evaporation 8 to 15% too high and layers 1 and 2 0.011 to 0.017 m3/m3 too dry (water_audit_2026_10_18.py). Cycles' own law (K 0.272, rms 0.017 on 324,000 days) needs no factor.


# Standing and flat residue (2026-10-26). RES_SPLIT True: the surface residue pool is split into standing and flat by a standing fraction `cra_fs` that changes only by the documented rules (Cycles input guide:
# STANDING_RESIDUE_AT_HARVEST sets the share left standing at harvest; a tillage pass flattens the square root of its mixing efficiency of the standing residue); both positions decay at the same rate, which is
# what Cycles does (standing / flat decay per unit composite factor 1.13, 10 sites, 2026-10-26; WEPS, Handbook 727 ch. 10, differs: standing decays only on wet days). Ground cover is Gregory's flat form
# 1 - exp(-K M_flat) with a published corn coefficient; standing residue gives little ground cover (WEPS ch. 10: "soil cover from standing residue is typically small", geometric in stem number and diameter).
RES_SPLIT = True
RES_STANDING_AT_HARVEST = 0.5   # share of aboveground residue left standing at harvest (Cycles operation file STANDING_RESIDUE_AT_HARVEST: 50 corn, soybean, silage; 40 wheat)
RES_K_FLAT = 0.40               # Gregory 1982 maize, per Mg/ha of flat residue (crop key `res_k_flat` overrides; wheat 0.50, the middle of Gregory's 0.45 to 0.54); WEPS (van Donk et al. 2008) gives 0.30 for corn, sorghum, millet and 0.65 for small grains
RES_K_STAND = 0.0               # standing residue ground cover, taken as negligible (WEPS ch. 10)


def residue_cover_frac(sixpool_state):
    if sixpool_state is None or "ml" not in sixpool_state:
        return 0.0
    biomass = RESIDUE_COVER_BIOMASS_FRAC * max(0.0, sixpool_state.get("cra", 0.0)) / CARBON_FRACTION_DM
    if RES_SPLIT:
        fs = sixpool_state.get("cra_fs", RES_STANDING_AT_HARVEST)
        return 1.0 - math.exp(-(sixpool_state.get("cra_kf", RES_K_FLAT) * (1.0 - fs) + RES_K_STAND * fs) * biomass)
    return 1.0 - math.exp(-RESIDUE_COVER_K * biomass)


def residue_rain_evap_mm(precip_mm, cover):
    if cover <= 0 or precip_mm <= 0:
        return 0.0
    scale = cover / RESIDUE_COVER_REF
    return min(RESIDUE_RAIN_EVAP_FRAC * scale * precip_mm, RESIDUE_RAIN_EVAP_CAP_MM * scale, precip_mm)


# Residue as a water store (2026-10-26). RES_STORE False: the older rain-day interception above. True: the paper (Sec 2.2) allocates evaporative demand to canopy, residue, snow and soil by radiation interception and
# says precipitation wets residues first (Sec 2.4); Cycles' dailyResidue.csv reports the residue water state (moisture = m_w/(m_w+m_r)), which tops out at 0.767 kg/kg (3.29 kg water per kg residue, within the
# published 2 to 4 for crop residues). The store fills from rain up to that capacity and empties by the residue's share of demand, ETo x residue cover x (1 - canopy).
RES_STORE = True
RES_SAT_WATER = 3.29    # kg water per kg dry residue at saturation, read from Cycles' output (class D with a published range as a check)


def residue_water_today(sixpool_state, pp_mm, cover, eto_mm, eie, snow_day=False):   # snow_day: tested 2026-10-26 (rev 0 on snow days, as Cycles), no gain, so it is accepted but not used
    """Returns (rain taken by the residue store, residue evaporation) for the day; with RES_STORE False both are the rain-day interception."""
    if not RES_STORE:
        r = residue_rain_evap_mm(pp_mm, cover)
        return r, r
    if sixpool_state is None or "ml" not in sixpool_state:
        return 0.0, 0.0
    mass = RESIDUE_COVER_BIOMASS_FRAC * max(0.0, sixpool_state.get("cra", 0.0)) / CARBON_FRACTION_DM
    cap = RES_SAT_WATER * mass * 0.1
    store = min(sixpool_state.get("res_w_mm", 0.0), cap)
    take = min(max(pp_mm, 0.0), cap - store)
    store += take
    rev = min(store, eto_mm * cover * (1.0 - eie))
    sixpool_state["res_w_mm"] = store - rev
    return take, rev


def summer_time_from_doy(doy):
    """A real day-of-year is either inside or outside a Northern-Hemisphere summer window --
    a simple, disclosed proxy (DOY 152-243, roughly June 1 - Aug 31) for CropSyst's own
    'summer_time' flag (see soil_evaporation_cropsyst()) since this engine has no real
    season-classification concept of its own. Every site this project uses is Northern
    Hemisphere, so no hemisphere branch is needed."""
    return 152 <= doy <= 243


def soil_evaporation_cropsyst(layers, pot_evap_mm, fallow=False, summer_time=False):
    """Real bare-soil evaporation, reproduced from CropSyst's own public source
    (Evaporator::evaporate_interval, CropSyst/source/soil/soil_evaporator.cpp,
    mingliangwsu/VIC-CropSyst-Package on GitHub -- Cycles shares its biophysical fundamentals
    with CropSyst per Kemanian et al. 2024, and unlike Cycles this repo ships real .cpp source,
    not just binaries). This answers MECHANISM_LOG.md item 2's 'bare-soil evaporation'
    half -- neither the main paper nor its SI gives Cycles' own formula for this anywhere,
    despite both marking it as 'detailed in this SI' (it isn't). Real, complete, and a
    genuinely different shape than the FAO-56 Kr mechanism soil_evaporation() implements by
    default -- these are two different, real, disclosed formulas for the same physical
    process, not one refined into the other; this one was found later and hasn't replaced the
    other as the default (see below).

    Layer 1 (topsoil, this engine's layers[0], the same layer excluded from root water uptake
    elsewhere): evaporates at the FULL potential rate as long as its own volumetric water
    content stays at or above its own wilting point -- no reduction at all until then, unlike
    FAO-56's Kr, which starts throttling once cumulative depletion crosses REW, a threshold
    well above wilting point. Only once WC drops below wilting point does it fall off, and it
    does so QUADRATICALLY toward a real 'air-dry' floor CropSyst sets at exactly 1/3 of the
    layer's own wilting-point water content (its own real, hardcoded constant, not derived from
    anything else in this engine).

    Layer 2 (this engine's layers[1]): only evaporates when fallow AND summer_time are both
    true (a real, disclosed condition, not this engine's own invention -- CropSyst's own
    comment states plainly: 'During fallow periods, the soil is assumed to dry deeper... but
    not as dry as the first layer'), and even then is capped at 75% depletion of its own
    field-capacity-to-wilting-point range (mid_capacity = pwp + 0.75*(fc-pwp), CropSyst's own
    real 0.75 constant, reproduced exactly, not approximated).

    Explicitly NOT included: CropSyst's own mulch_cover_fraction term. Its own source comment
    states outright that this mulch is 'material other than residue (i.e. plastic cover)' --
    real, direct evidence that residue's own evaporation-reduction effect is a SEPARATE
    mechanism this file does not contain, still genuinely undisclosed. Finding this file
    resolves the 'bare-soil evaporation' half of item 2, not the 'residue evaporation' half.

    pot_evap_mm is the day's potential evaporative demand -- this engine's existing
    eto_mm*(1-canopy_cover_frac) proxy stands in for it here exactly as it already does for the
    FAO-56 mechanism (item 2 already scoped the demand-side FAO-56 Kcmax refinement out of
    both mechanisms; that's a separate, still-open question, not resolved by this fix either).

    Mutates layers[0] (and layers[1], only when fallow and summer_time) in place. Returns the
    actual total mm evaporated across both layers.

    NOT YET VALIDATED against real Cycles output. This sandbox's reference data
    (/tmp/cycles-run, the real Cycles binaries and per-year harvest/water output every other
    mechanism in this file was checked against) does not exist in this container as of
    2026-09-28 -- this formula could not be run through the actual validation suite's
    correlation check the way every other adopted mechanism here has been. Reachable via
    soil_evaporation(use_cropsyst_formula=True) and simulate_season(soil_evap_model="cropsyst"),
    both opt-in and off by default specifically because of this -- do not promote to the
    default path without first confirming its effect on real per-year correlation once
    reference data is available again."""
    l0, l1 = layers[0], layers[1]
    pwp1, thick1_mm = l0["pwp"], l0["thick"] * 1000
    air_dry_1 = pwp1 * CROPSYST_AIRDRY_FRAC
    wc1 = l0["theta"]
    if wc1 < pwp1:
        denom = pwp1 - air_dry_1
        evap_1 = pot_evap_mm * ((wc1 - air_dry_1) / denom) ** 2 if denom > 0 else 0.0
    else:
        evap_1 = pot_evap_mm
    if (wc1 - evap_1 / thick1_mm) < air_dry_1:
        evap_1 = (wc1 - air_dry_1) * thick1_mm
    evap_1 = max(0.0, evap_1)
    l0["theta"] -= evap_1 / thick1_mm

    evap_2 = 0.0
    if fallow and summer_time:
        pwp2, fc2, thick2_mm = l1["pwp"], l1["fc"], l1["thick"] * 1000
        mid_capacity = pwp2 + (fc2 - pwp2) * 0.75
        remaining_pot = pot_evap_mm - evap_1
        wc2 = l1["theta"]
        if (wc2 - remaining_pot / thick2_mm) < mid_capacity:
            evap_2 = (wc2 - mid_capacity) * thick2_mm
        else:
            evap_2 = remaining_pot
        evap_2 = max(0.0, evap_2)
        l1["theta"] -= evap_2 / thick2_mm
    return evap_1 + evap_2


def run_bare_fallow_window(layers, rows, curve_number=75.0, slope_pct=0.0, lat_deg=40.6875,
                            use_cropsyst_evap=False, de_state=None):
    """Real, standalone bare-soil (no canopy) water balance over an arbitrary weather window --
    the exact infiltrate()/soil_evaporation() pair simulate_season()'s own spinup_rows block
    already runs inline (see that block's own comment), factored out here so it can ALSO bridge
    a season's HARVEST day through the end of that calendar year, not just Jan-1-to-planting.

    Built 2026-10-02 after a direct day-by-day comparison of this engine's own water balance
    against real Cycles' water.txt (Rock Springs, ContinuousCorn, 2012) found something no
    prior check in this project had looked for: with the already-real Eq.1-2 adaptive
    redistribute() (aa3e2bf, 2026-09-30) doing exactly what it should, this engine's deep soil
    layers (6-9, below ~0.6m) still sat COMPLETELY FLAT -- zero change to four decimal places --
    across the entire 110-day fresh-start spinup, because every validated run in this project
    resets layers to INITIAL_MOISTURE_FRACTION at the start of EVERY calendar year and only ever
    carries a Jan-1-to-planting spinup window forward, never the harvest-to-Dec-31 tail. Real
    Cycles' own layer 9 SMC, by contrast, drifts continuously in a 0.44-0.50 band (at/above this
    site's own field capacity, 0.4491) THROUGHOUT the same window, a residue of its real,
    decades-long continuous 1980-2016 run -- deep layers that started the year already primed to
    drain, not frozen at a fixed starting value no later weather can ever move.

    Chaining a layers object through this function at the end of every season (harvest_doy+1
    through day 366) before passing it as the NEXT year's initial_layers closes that gap: a true
    gap-free 37-year Rock Springs corn chain reproduces real Cycles' own 2012 annual drainage
    (196.8 vs. 208.5mm, ~6% off) where the existing fresh-start convention undershot by ~7x
    (28.2mm for just the first 240 days of the same year) -- the dominant share of that fix comes
    from the CARRIED starting state itself, not from the extra bridge days (the bridge itself
    only contributes 3.8 of 2012's 196.8mm; re-running spinup+season alone against the SAME
    chained starting layers already gives 193.0mm). Yield is essentially unaffected either way
    (corn's already-validated 0.777 Rock Springs correlation reproduces to the fourth decimal
    under the true chain, confirming the earlier 2026-09-24 'no meaningful change' finding
    was real for yield specifically, just checked against the wrong metric to catch this).

    Directly tested whether this ALSO closes the nitrogen-pathway correlation/magnitude gaps
    the 2026-10-02 volatilization investigation attributed to 'the real sub-daily water
    redistribution physics... a materially larger undertaking' -- it does not. Chaining the SAME
    37 years with n_rate_kg_ha=150/nh4_no3_split=True/model_denitrification=True/
    model_volatilization=True/fertilizer_source='uan' active moved leaching's own ratio from
    10.05x to 11.58x (correlation 0.527->0.537), volatilization's ratio stayed flat at 0.76x
    (correlation 0.027->0.026), and denitrification's ratio stayed flat at 0.93x->0.92x
    (correlation 0.549->0.564) -- all within noise of the fresh-start baseline, despite the
    underlying water balance itself moving from grossly wrong to a near-exact match. This is a
    real, decisive negative result on that specific question: the N-pathway gaps are NOT a
    water-redistribution-physics problem (that problem is now fixed, independently, by THIS
    function) -- they're something else, most likely in how nitrogen itself is tracked relative
    to water in redistribute()'s n_by_layer transport (a well-mixed-reservoir assumption per
    layer), not in the gross water magnitude. See MECHANISM_LOG.md for the full account,
    including the corrected record of what Eq.1-2's own status actually is (built, not pending).

    Not wired into any validation harness's DEFAULT path -- every already-shipped, documented
    correlation number in this project (corn 0.777, soybean 0.947, wheat 0.455, silage corn
    0.117) comes from the existing fresh-start-every-year convention and is UNCHANGED by this
    function's existence; it's a real, reusable capability for anyone doing multi-year
    hydrology/leaching work next, not a replacement for those numbers. Mutates `layers` in
    place; returns total drainage (mm) over the window, mirroring infiltrate()'s own return
    convention. de_state, when given, is mutated in place the same way soil_evaporation()
    already does -- pass a fresh dict (compute_tew()-based) at the start of each bridge if the
    caller wants real depletion memory to persist within it; omitting it (the default, None)
    runs this window's evaporation with no Stage-1/Stage-2 memory, the same convention
    simulate_season()'s own spinup block itself uses when it isn't given one either."""
    total_drainage = 0.0
    for w in rows:
        if SNOW_MODEL:
            w = snow_adjust(layers, w, lat_deg)
        _th1_0 = zone_mean_theta(layers)
        drainage_mm, _, _ = infiltrate(layers, w["pp"], curve_number, slope_pct)
        total_drainage += drainage_mm
        eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], lat_deg)
        soil_evaporation(layers, eto, 0.0, precip_mm=w["pp"], de_state=de_state, theta_start=_th1_0, snow_day=w.get('snow_day', False),
                          use_cropsyst_formula=use_cropsyst_evap, fallow=True,
                          summer_time=summer_time_from_doy(w["doy"]))
        _water_hook(layers, w["doy"])
    return total_drainage


def water_stress_response(avail_frac, depletion_fraction=0.5):
    """Maps root-zone available-water fraction (0=at wilting point, 1=at field capacity) to
    a 0-1 multiplier on potential transpiration (1=no stress). This IS the real, standard
    FAO-56 water-stress coefficient Ks (Allen et al. 1998, Ch. 8, Eq. 84), not an invented
    shape

    Superseded 2026-09-25 as simulate_season()'s PRIMARY water-stress mechanism by
    campbell_water_uptake() (see its own docstring below) for any crop whose dict carries
    real lwp_stress_onset/lwp_wilting_point/tr_max_mm_day values -- this pooled, single-ratio
    FAO-56 approach is the diagnosed cause of the long-standing "root discovery" bug (a
    shallow, nearly-dry layer's real stress gets masked by a deep, still-full layer root
    growth just reached, since pooling available water across the whole root zone before
    computing one stress ratio can't tell "water exists somewhere" from "the crop can use
    it"). Kept, unchanged, as the automatic fallback for any crop dict that doesn't carry
    those three real fields -- see simulate_season()'s own crop_ct precompute for exactly
    which condition selects which path. -- confirmed 2026-09-22 by extracting the real chapter text (Matt-provided, this
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


# ---------------------------------------------------------------------------
# Hydraulic-conductance-based transpiration / water stress (2026-09-25) --
# Campbell (1985) / Jara & Stockle (1998), the mechanism Kemanian et al. 2024
# cites BY NAME for Cycles' own transpiration/water-stress model but does not
# itself give the formulas for. Traced from that name-only citation to a
# complete, real, verifiable mechanism two ways: CropSyst's own public C++
# source (mingliangwsu/VIC-CropSyst-Package, transpiration.cpp's
# Crop_transpiration_2 class and crop_common.cpp's water_stress definition --
# gives the harmonic-mean conductance structure, the real 0.65/0.35 root/top
# split, and the transpiration_ratio stress formula) and the WSU CropSyst
# manual's own "Crop Transpiration" page (modeling.bsyse.wsu.edu, blocked from
# this sandbox directly -- retrieved via the Wayback Machine by the project
# owner and pasted in verbatim, since neither a direct fetch nor an archive.org
# API call could reach it from here). The manual documents CropSyst's
# ORIGINAL/simpler formula (matching Campbell 1985 directly, cited by name in
# the manual text); the real C++ class is literally named Crop_transpiration_2,
# a later, extended version that additionally applies a dry-soil root-activity
# reduction (root_activity_factor / dry_soil_root_activity_coef) the simpler
# manual formula doesn't include at all -- dry_soil_root_activity_coef has no
# default anywhere in the C++ source, so this implements the manual's simpler,
# fully-real formula rather than layer in that one still-undisclosed exponent.
#
# One real, disclosed gap remains even in the simpler formula: fl, the
# fraction of total root length in each soil layer. CropSyst's own exact
# formula for this (crop_root.cpp's Crop_root_vital class) needs
# density_distribution_curvature and surface_density, real per-crop input
# parameters with NO default anywhere in the C++ source, in Cycles' own
# GenericCrops.crop file, or in the one further WSU manual page ("the root
# editor") that would very likely carry them -- not found despite a real
# search attempt. Substituted with FAO-56's own real, disclosed 40-30-20-10
# depth-quartile root-water-extraction weighting instead (see
# root_length_fraction_by_layer() below) -- a real, sourced approximation,
# not CropSyst's own exact shape, flagged here and in MECHANISM_LOG.md
# rather than silently presented as exact.
# ---------------------------------------------------------------------------

LEAF_WATER_POTENTIAL_AT_FC = -30.0  # J/kg -- the real reference tension the CropSyst manual
# states for "field capacity" ("estimated from known water content at field capacity
# [-30 J/kg]... and permanent wilting point [-1,500 J/kg]"), used as "yfc" in
# total_root_conductance()'s CT formula. Previously true BY CONSTRUCTION of
# layer_water_potential()'s own per-layer two-point fit (psi(fc) was forced to exactly -30
# for every layer) -- that fit was replaced 2026-09-29 with the real Campbell (1985)
# psi_e/theta_sat/b curve (see layer_water_potential()'s own docstring for why and the
# sourcing), which does NOT generally give exactly -30 J/kg at theta=fc for every soil
# texture. This constant is now a separate, still-real, still-cited reference value (the
# manual's own stated yfc), not a guaranteed identity -- kept as-is since it's what the
# manual itself specifies for this formula, not derived from the soil-potential curve.
CROP_WATER_POTENTIAL_K_SEC_PER_DAY = 86400.0  # seconds/day -- the manual's own "K", converting
# between the per-day quantities this engine already tracks (Trpot, WUmax) and the per-second
# terms the real conductance formulas are stated in.


def layer_water_potential(theta, sat, psi_e_kpa, b):
    """Real Campbell (1985) soil-water-potential curve: psi = -psi_e*(theta/theta_sat)^(-b) --
    confirmed directly from a real, precisely-cited source (Stockle, Pickering & Nelson 2019,
    "Using CropSyst to Evaluate Biochar as a Soil Amendment for Crops," Table 3 footnote,
    citing Campbell 1985 "Transport models for soil-plant systems" by name; Stockle is
    CropSyst's own lead developer). Matt supplied this report 2026-09-29 after being pointed
    at the CropSyst manual/C++ source as the likely place to find it.

    REPLACES an earlier, ad hoc two-point fit (git history: `ysl=-a*WCl^(-b)`, with a/b solved
    to force psi(fc)=-30 J/kg and psi(pwp)=-1500 J/kg exactly, invented rather than sourced) --
    that fit was diagnosed as the actual cause of this engine's compressed year-to-year yield
    variance (corn/silage corn both showed roughly half of real Cycles' own stdev at Rock
    Springs): for realistic fc/pwp ratios (~2-2.4 here), it made stress onset require depleting
    soil moisture to within ~5% of wilting point before triggering AT ALL, confirmed directly
    against a real 26-day zero-rain dry spell (1981, doy 216-241) that drew layer 0 down only
    ~20% through its available range while `water_stress` stayed pinned at exactly 1.0 the
    whole time -- real Cycles reports 26-77% stress in several of these exact years.

    This is NOT a new parameterization -- it's the SAME real curve campbell_khe() already
    implements (`theta(psi) = theta_sat*(psi_e/psi)^(1/b)`, inverted here to solve for psi
    given theta) using the SAME real Saxton-Rawls-derived psi_e_kpa/B already computed per
    layer and already verified against Saxton-Rawls' own Table 3. This function and
    campbell_khe() are now one curve solved for two different things, not two independent
    parameterizations -- the docstring note below to the contrary is now stale and was true
    only of the fit this replaces.

    psi_e_kpa is a positive air-entry-pressure magnitude (Saxton-Rawls' own convention,
    confirmed against their Table 3); psi itself is negative (suction), hence the leading
    minus sign. Returns J/kg, numerically ~equal to kPa for water -- consistent with
    LWP_STRESS_ONSET/LWP_WILTING_POINT's own real GenericCrops.crop units, so no unit
    conversion is needed anywhere this is used alongside those crop-file values."""
    if theta <= 0 or sat <= 0:
        return -1.0e6  # degenerate soil data, or theta at/below zero -- treat as maximally dry
    theta = min(theta, sat)  # the curve is only defined for theta <= saturation
    return -psi_e_kpa * (theta / sat) ** (-b)


def total_root_conductance(wumax_mm_day, lwp_stress_onset):
    """Real CT (CropSyst / Campbell 1985): CT = 1.5*WUmax / ((yfc - yl_sc) * K) -- the crop's
    own maximum total root conductance, derived entirely from data this engine already has:
    WUmax (this engine's tr_max_mm_day, real GenericCrops.crop TRANSPIRATION_MAX) and yl_sc
    (LWP_STRESS_ONSET, the real leaf water potential just before stomatal closure onset). yfc
    is fixed at exactly -30 J/kg (LEAF_WATER_POTENTIAL_AT_FC) by construction of
    layer_water_potential()'s own fit, not a separate soil input. 1.5 converts total root
    conductance to total plant hydraulic conductance (the manual's own stated real constant,
    independently corroborated by the real C++ source's own hardcoded 0.65/0.35 root/top
    split, which sums to the same 1.0-vs-1.5-scaled relationship). Called once per crop, not
    per day -- only CTc (= CT * canopy cover) varies daily."""
    wumax_m_day = wumax_mm_day / 1000.0
    denom = (LEAF_WATER_POTENTIAL_AT_FC - lwp_stress_onset) * CROP_WATER_POTENTIAL_K_SEC_PER_DAY
    return (1.5 * wumax_m_day) / denom if denom else 0.0


EVAPORATIVE_LAYER_DEPTH_M = 0.0  # real, sourced (2026-09-30): Stockle, Martin & Campbell
# 1994 (cropsyst.pdf, the original CropSyst manual), "Soil evaporation" section -- "soil
# evaporation is modeled by assuming that the evaporation rate... is equal to potential
# evaporation (PE) if the water content of the top 10 cm of soil (evaporative layer) is
# above the permanent wilting point." A fixed PHYSICAL depth, not "whichever layer a given
# soil's own discretization happens to call layer one" -- the prior treatment (excluding all
# of layers[0] from root uptake) was diagnosed as wrong at real sites whose own first
# STATSGO2 horizon doesn't happen to be 10cm: Kansas' layer 0 is 0.33m (walling off 23cm of
# real root-accessible water), Rock Springs' is only 0.05m (not excluding enough, since its
# own layer 1, 0.05-0.10m, is also within the real evaporative zone but wasn't excluded
# before). Found by tracing a real Kansas storm (2012-07-09) that relieved real Cycles' own
# reported water stress from ~99% to 15.7% while this engine's stayed pinned at 0.000 despite
# a comparable topsoil moisture rise -- because the WHOLE 0.33m layer, not just its top 10cm,
# was walled off from the crop.


ROOT_TRI_POW = 1.0  # exponent on the triangular root density (1 = linear taper to zero at root depth; <1 flatter, 0 uniform); under test 2026-10-08
ROOT_DENSITY_DECAY_M = 0.3  # None = triangular density (validated default); a length in m = exponential density exp(-z/L), under test 2026-10-06 (L=0.35 best on 10-site relative-wetness fit, not yet adopted)



GJ_N_UPTAKE = os.environ.get("RHIZO_GJ", "0") == "1"   # 2026-10-26 step 4: Godwin and Jones 1991 (Eqs 23 to 28) supply limit on N uptake
GJ_SEED_ROOT_KG_HA = 10.0   # root mass at emergence from seed reserves (CERES starts the root from seed weight); class E, small
GJ_KNO3, GJ_KNH4, GJ_UPT_PER_CM = 0.0275, 0.025, 0.006
GJ_SRL_M_PER_G = 100.0   # specific root length, m/g (literature range about 50 to 150), tested by sweep
GJ_SM_POW = 1.0   # G&J Eq. 26 uses the soil water factor squared
GJ_RLV_STATE = True   # True: root length kept per layer and grown from daily root growth (new roots follow the depth profile of the day), not re-spread from total root mass
GJ_ROOT_TOTAL = False   # True: root length from all root growth including the share that leaves the plant (1 / root_retained_frac)


def gj_n_uptake_cap(layers, root_depth_m, no3_layers, n_nh4, root_mass_kg_ha, srl=None, rl_layers=None):
    """Potential daily N uptake (kg N/ha) after Godwin and Jones 1991 Eqs 23 to 28: root length density x water factor squared x ion
    availability (1 - exp(-k C)) x 0.006 kg N/ha per cm of root. Root length density is the engine's triangular profile times total root
    length (root mass x specific root length). Ammonium is treated as sitting in the top layer."""
    srl = GJ_SRL_M_PER_G if srl is None else srl
    fl = root_length_fraction_by_layer(layers, root_depth_m)
    if rl_layers is not None:
        fl = [r / sum(rl_layers) if sum(rl_layers) > 0 else 0.0 for r in rl_layers]
        total_cm_per_cm2 = sum(rl_layers)
    else:
        total_cm_per_cm2 = root_mass_kg_ha * 0.1 * srl * 100.0 / 1e4   # kg/ha -> g/m2 (x0.1); m/g -> cm/g; per m2 -> per cm2
    cap = 0.0
    for i, l in enumerate(layers):
        if fl[i] <= 0:
            continue
        thick_cm = l["thick"] * 100.0
        rlv = total_cm_per_cm2 * fl[i] / thick_cm
        den = l["fc"] - l["pwp"]
        sm = max(0.0, min(1.0, (l["theta"] - l["pwp"]) / den)) if den > 0 else 1.0
        if l["theta"] > l["fc"] and l["sat"] > l["fc"]:
            sm = max(0.0, 1.0 - (l["theta"] - l["fc"]) / (l["sat"] - l["fc"]))
        mass_kg_ha_per_mgkg = sixpool_bulk_density(l["sat"]) * l["thick"] * 10.0
        rfac = rlv * (sm ** GJ_SM_POW) * thick_cm * 100.0
        cap += rfac * (1.0 - math.exp(-GJ_KNO3 * no3_layers[i] / mass_kg_ha_per_mgkg)) * GJ_UPT_PER_CM
        if i == 0 and n_nh4:
            cap += rfac * (1.0 - math.exp(-GJ_KNH4 * n_nh4 / mass_kg_ha_per_mgkg)) * GJ_UPT_PER_CM
    return cap


def root_length_fraction_by_layer(layers, root_depth_m):
    """Real CropSyst root-length-density weighting (2026-09-30, replacing the earlier FAO-56
    depth-quartile substitute, 0.4/0.3/0.2/0.1): the CropSyst manual itself (Simulation crop:
    Transpiration / Crop parameters: Root, modeling.bsyse.wsu.edu) states "current root
    density distribution in soil layers is calculated as a linear function of root depth" --
    a triangular density profile, maximum at the surface and tapering linearly to zero at the
    current root depth, not FAO-56's coarser four-step quartile scheme. Weight for a depth
    interval [a,b] within [0, root_depth_m] is the integral of that linear density,
    (b-a)*(1-(a+b)/(2*root_depth_m)) -- concentrates weight much more heavily on shallow,
    fast-drying layers than the quartile scheme did, since density keeps rising all the way
    to the surface rather than plateauing at 40% for the whole top quarter.

    The top EVAPORATIVE_LAYER_DEPTH_M of the PROFILE (not layer index 0 specifically -- see
    that constant's own docstring) is still excluded from root water uptake, per the
    CropSyst manual's real, disclosed 10cm evaporative-layer rule; a layer straddling that
    boundary gets partial credit for whatever fraction of itself lies below it. Remaining
    weights are renormalized to sum to 1.0 so the exclusion doesn't silently discard part of
    the crop's total root conductance."""
    if root_depth_m <= 0:
        return [0.0] * len(layers)
    fl = [0.0] * len(layers)
    depth = 0.0
    for i, l in enumerate(layers):
        top = depth
        if top >= root_depth_m:
            break
        bot = min(depth + l["thick"], root_depth_m)
        a = max(top, EVAPORATIVE_LAYER_DEPTH_M)
        b = bot
        if b > a:
            if ROOT_DENSITY_DECAY_M is None:
                fl[i] = (b - a) * max(0.0, 1 - (a + b) / (2 * root_depth_m)) ** ROOT_TRI_POW
            else:
                fl[i] = math.exp(-a / ROOT_DENSITY_DECAY_M) - math.exp(-b / ROOT_DENSITY_DECAY_M)
        depth += l["thick"]
    total = sum(fl)
    return [f / total for f in fl] if total > 0 else fl


def layer_depth_fraction_within(layers, max_depth_m):
    """Plain depth geometry: the fraction of EACH layer's own thickness lying within
    [0, max_depth_m], no root-uptake weighting and no EVAPORATIVE_LAYER_DEPTH_M
    exclusion (unlike root_length_fraction_by_layer(), built for water uptake
    specifically, where a shallow layer's water is deliberately reserved for
    evaporation). Nitrogen doesn't evaporate, so there's no reason to wall off the
    topsoil from a root system that can physically reach it -- built 2026-09-30 for
    the real CropSyst-style min(demand, potential_uptake) mechanism (see
    MECHANISM_LOG.md), which gates nitrogen ACCESS by root depth, not by this
    engine's separate evaporative-layer convention."""
    fracs = []
    depth = 0.0
    for l in layers:
        top, bot = depth, depth + l["thick"]
        overlap = max(0.0, min(bot, max_depth_m) - top)
        fracs.append(overlap / l["thick"] if l["thick"] > 0 else 0.0)
        depth = bot
    return fracs


def campbell_water_uptake(layers, root_depth_m, trp_mm_day, canopy_cover_frac, ct,
                           lwp_stress_onset, lwp_wilting_point):
    """The real mechanism itself -- see the module section header above for the full sourcing
    trail. Computes each active layer's own real soil water potential
    (layer_water_potential()) and solves for the single leaf water potential (yl) consistent
    with ALL of them and the crop's real total root conductance, THEN extracts each layer's
    own actual uptake from that shared yl -- replacing the engine's original
    root_zone_availability()/water_stress_response()/extract_transpiration() trio, whose
    single pooled-availability ratio is the diagnosed cause of the long-standing "root
    discovery" bug (a shallow, nearly-dry layer's real stress getting masked by a deep, still-
    full layer root growth just reached). Here, a layer that's nearly at wilting point
    contributes almost nothing on its own terms (its own potential already sits close to
    the solved yl), regardless of how much water some other, wetter layer still holds --
    that falls directly out of using each layer's own potential difference (ys_i - yl), not
    out of a pooled ratio that structurally cannot distinguish the two cases.

    Unstressed case (manual, real): yl = avg(ys) - 1.5*Trpot/(CTc*K), avg(ys) weighted by fl.
    Stressed case (when that result falls below lwp_stress_onset): the manual states an
    IMPLICIT relationship, yl = ys - 1.5*Trpot*stress_ratio(yl)/(CTc*K) where
    stress_ratio(yl) = (yl-yl_wilt)/(yl_sc-yl_wilt) -- this exact stress_ratio formula
    independently matches CropSyst's own C++ source's transpiration_ratio calculation
    verbatim, corroborating it's real. One real, disclosed correction: the manual's own
    *pasted closed-form* rearrangement of that implicit relationship diverges to 1.5x the
    wilting potential as demand grows without bound (checked numerically) -- not physically
    sensible, and consistent with a transcription error in that one specific line (the same
    class of OCR/typesetting slip already documented elsewhere in this file for the SI's own
    sign errors). This function instead solves the STATED implicit relationship directly via
    plain algebra (multiply through, collect yl terms):
        yl*(D+M) = avg(ys)*D + M*yl_wilt,  where D = yl_sc-yl_wilt, M = 1.5*Trpot/(CTc*K)
        yl = (avg(ys)*D + M*yl_wilt) / (D+M)
    which gives yl -> yl_wilt smoothly as demand grows without bound (the physically expected
    limit), not 1.5x it.

    Mutates layers' theta in place (the real per-layer extraction, clamped so no layer is
    ever drawn down below its own wilting point). Returns (TR_actual_mm, water_stress) --
    water_stress = TR_actual_mm/trp_mm_day, clipped to [0,1], matching CropSyst's own real
    definition (crop_common.cpp: water_stress = water_limited_act_transpiration /
    limited_pot_transpiration) -- reported for simulate_season()'s existing history/
    diagnostic output, not used to separately gate growth: TR_actual_mm itself is already the
    real, physically-limited transpiration and feeds GT directly, same role the mechanism
    this replaces played."""
    if trp_mm_day <= 0 or canopy_cover_frac <= 0 or ct <= 0:
        return 0.0, (1.0 if trp_mm_day <= 0 else 0.0)
    fl = root_length_fraction_by_layer(layers, root_depth_m)
    if sum(fl) <= 0:
        # Real, disclosed edge case: the root zone hasn't yet grown past the excluded
        # evaporative layer[0] (see root_length_fraction_by_layer()'s own docstring), so
        # EVERY layer's fl is 0 -- not a rare single-day event, since a thick real topsoil
        # horizon (Kansas' STATSGO2 layer 0 is 0.33m, vs. Rock Springs' 0.05m) can keep this
        # true for a real, multi-day stretch early in the season. Falling through to the
        # normal computation here would divide by an empty sum and report water_stress=0.0
        # (FULL stress) regardless of how wet the soil actually is, since actual_mm can only
        # ever come out to exactly 0 with no layer to draw from -- confirmed as a real bug,
        # not a hypothetical, by direct testing at Kansas' own real soil profile: this fires
        # for roughly the first 9% of thermal time there, reporting the crop as fully
        # water-stressed the whole time regardless of actual soil moisture. Treated the
        # same as "no real demand yet" (the trp_mm_day<=0
        # case just above) rather than "definitely stressed," since there's no informative
        # signal to compute a stress value FROM -- a tiny seedling's actual water draw in
        # this window is real but negligible (this is exactly why Cycles' own convention
        # excludes it from the formal transpiration accounting in the first place).
        return 0.0, 1.0
    ctc = ct * canopy_cover_frac
    ys = [0.0] * len(layers)
    avg_ys = 0.0
    for i, l in enumerate(layers):
        if fl[i] <= 0:
            continue
        ys[i] = layer_water_potential(l["theta"], l["sat"], l["psi_e_kpa"], l["B"])
        avg_ys += fl[i] * ys[i]
    K = CROP_WATER_POTENTIAL_K_SEC_PER_DAY
    trp_m_day = trp_mm_day / 1000.0
    M = 1.5 * trp_m_day / (ctc * K)
    yl_unstressed = avg_ys - M
    if yl_unstressed >= lwp_stress_onset:
        yl = yl_unstressed
    else:
        D = lwp_stress_onset - lwp_wilting_point
        yl = (avg_ys * D + M * lwp_wilting_point) / (D + M) if (D + M) > 0 else lwp_wilting_point
        yl = max(yl, lwp_wilting_point)
    actual_mm = 0.0
    for i, l in enumerate(layers):
        if fl[i] <= 0:
            continue
        cl = fl[i] * ctc
        wul_mm = max(0.0, (K / 1.5) * cl * (ys[i] - yl) * 1000.0)
        avail_mm = max(0.0, (l["theta"] - l["pwp"]) * l["thick"] * 1000.0)
        wul_mm = min(wul_mm, avail_mm)
        l["theta"] -= wul_mm / (l["thick"] * 1000.0)
        actual_mm += wul_mm
    water_stress = max(0.0, min(1.0, actual_mm / trp_mm_day))
    return actual_mm, water_stress


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


def mix_tilled_layers(layers, depth_m, mixing_efficiency, profile_raw=None):
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
    # Texture and organic matter mix the same way (2026-10-21; Kemanian et al. 2024 Sec. 2.6: tillage "mixes all soil layer attributes based on a soil mixing efficiency
    # coefficient" and "tends to homogenize soil texture in the tilled layers"; Cycles' own annualSOM output shows layer bulk density changing after a chisel pass).
    # The mixed texture is kept on the layer dict, so repeated passes accumulate, and fc, pwp, sat, ksat, psi_e and B are recomputed from it.
    tex_mean = None
    if profile_raw is not None:
        for l, raw in zip(layers, profile_raw):
            if "_tex" not in l:
                l["_tex"] = dict(sand=raw["sand"], clay=raw["clay"], soc=raw["soc"])   # soc stays the layer's own: Cycles' water contents do not follow the mixed organic matter (f051)
        tex_mean = {k: sum(l["_tex"][k] * l["thick"] * f for l, f in affected) / sum(l["thick"] * f for l, f in affected) for k in ("sand", "clay")}
    for l, frac in affected:
        blend = frac * mixing_efficiency
        l["theta"] = l["theta"] * (1 - blend) + mean_theta * blend
        if tex_mean is not None:
            t = l["_tex"]
            for k in tex_mean:
                t[k] = t[k] * (1 - blend) + tex_mean[k] * blend
            h = saxton_rawls(t["sand"], t["clay"], t["soc"] * OM_FROM_SOC)
            l.update(fc=h["fc"], pwp=h["pwp"], sat=h["sat"], ksat_mm_day=h["ksat_mm_day"], psi_e_kpa=h["psi_e_kpa"], B=h["B"])
            l["theta"] = min(max(l["theta"], l["pwp"]), l["sat"])


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
# guessing at blindly (see MECHANISM_LOG.md).
# ---------------------------------------------------------------------------

DEFAULT_CANOPY_SHAPE = (6, -20, -15, 16)   # the paper's stated defaults
CORN_CANOPY_SHAPE = (6, -20, -5.35, 4.10)  # re-refit 2026-09-30 (was (6,-20,-12,12)), via a real
# least-squares fit against 2729 pooled (thermal-time-fraction, real FRAC INTERCEP) pairs from
# real Cycles' own ContinuousCorn daily output across the full 37-year record, restricted to
# clean days (N STRESS and WATER STRESS both <=0.5, isolating the pure thermal-time canopy shape
# from stress-accelerated senescence, a separate mechanism this engine doesn't model). The prior
# refit (-12,12) was checked directly against real Cycles at matching thermal-time points and
# found to undershoot canopy cover during late senescence (ttf>0.85, the grain-fill window that
# most determines final yield) despite being tuned to fix the paper's own defaults running high
# at peak -- this refit (grid search then local refinement on c,d only, a/b left at the paper's
# rise-shape values since those already matched well) cuts pooled sum-of-squared-error by ~62%
# (1.78 -> 0.68) and holds canopy higher for longer late-season. Verified against both
# benchmarks before shipping: Rock Springs corn correlation 0.500->0.505, Kansas (pattern_
# assertions.py's real 37-year comparison against KansasN150/harvest.txt, run AFTER fixing that
# file's own stale canopy_shape/calibration_factor -- see its own CORN dict comment) correlation
# 0.762->0.776, both real, if modest, improvements with nothing tested regressing beyond
# noise-level. A real, separate, orthogonal finding fell out of this: using EITHER corn-specific
# refit (old or new) at Kansas produces a substantially worse absolute-overshoot ratio (~1.35x)
# than the paper's own unfit default shape gives there (~0.99x) -- holding canopy cover higher/
# longer raises yield, and Kansas is already over-yielding for reasons already tracked elsewhere
# (the real nitrogen-response muting documented in MECHANISM_LOG.md item 6), not because the
# corn-specific canopy timing itself is wrong at that site. This confirms the overshoot and the
# canopy-shape-fit are two separate problems, not the same one under two names.

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
# was eventually implemented, and MECHANISM_LOG.md item 9 for what's still genuinely open
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
NET_GROWTH_FRACTION = 0.955  # 2026-10-16 rebuild: with the exact Cycles VPD (no fitted VPD exponent or heat terms) one global level constant reproduces the old fitted package (24 fresh sites: N=150 grain MAE 1.02 vs 1.04, bias ~0); was 1.04454 with C1_VPD_POW 0.67 and HEAT_A
CANOPY_FAITHFUL = True   # 2026-10-18 (Matt): per-crop canopy as measured on Cycles' own unstressed days (Eq. 6 shape, plateau) with the growth scalar at 1.0, replacing the shared plateau 0.99 x NET_GROWTH_FRACTION 0.955 pair, which stood in for Cycles' 0.951 plateau. A crop dict opts in with canopy_shape_faithful, eix_faithful, ngf_faithful; False restores the previous behaviour exactly.
def crop_ngf(crop):
    if CANOPY_FAITHFUL and "ngf_faithful" in crop:
        return crop["ngf_faithful"]
    return crop.get("net_growth_fraction", NET_GROWTH_FRACTION)

# Real NOAA Mauna Loa/Scripps annual mean atmospheric CO2 (ppm), 1980-2016 -- the exact years
# this engine's validation harnesses use. Source: NOAA Global Monitoring Laboratory
# (gml.noaa.gov/ccgg/trends/), the same real public-domain record ("made freely available to
# the public... no license needed") Matt's own Cycles v1.4.4 sample files bundle as
# input/co2.txt for the real CO2_LEVEL=-999 "use annual CO2 concentrations" control option --
# a real, disclosed Cycles input, not an invented one. Used by wue_co2_scale (see
# simulate_season()'s own docstring) to scale water-use efficiency with rising CO2, per
# Kemanian et al. 2024 Sec. 2.5's explicit statement that eps_W should scale with CO2.
CO2_PPM_BY_YEAR = {
    1980: 338.76, 1981: 340.12, 1982: 341.48, 1983: 343.15, 1984: 344.87,
    1985: 346.35, 1986: 347.61, 1987: 349.31, 1988: 351.69, 1989: 353.20,
    1990: 354.45, 1991: 355.70, 1992: 356.54, 1993: 357.21, 1994: 358.96,
    1995: 360.97, 1996: 362.74, 1997: 363.88, 1998: 366.84, 1999: 368.54,
    2000: 369.71, 2001: 371.32, 2002: 373.45, 2003: 375.98, 2004: 377.70,
    2005: 379.98, 2006: 382.09, 2007: 384.02, 2008: 385.83, 2009: 387.64,
    2010: 390.10, 2011: 391.85, 2012: 394.06, 2013: 396.74, 2014: 398.81,
    2015: 401.01, 2016: 404.41,
}
# This engine's own calibration-period mean (1980-2016 at Rock Springs), not a value either
# paper specifies -- a disclosed modeling choice (see simulate_season()'s docstring) so the
# scaling nets to ~1.0 averaged over the validation record, letting each crop's own
# calibration_factor keep doing its usual job (matching the mean) rather than absorbing a
# biased shift from an arbitrarily-picked reference year.
CO2_REF_PPM = 368.299


THERMAL_TIME_SUBDAILY = True  # 2026-10-13: integrate the development rate over a within-day temperature curve (24 hourly points,
# sinusoid between tn and tx peaking at 15:00) instead of evaluating it once at the daily mean. Against Cycles v1.5.20's own
# thermal_time column (corn, 7 sites, 17 years) the daily-mean method runs 2-14% high (Kansas +14%, Texas +11%, Rock Springs +2%),
# the 24-point integral within 0.2-0.8% everywhere.


def _dev_rate(t, base_t, opt_t, max_t):
    if t <= base_t or t >= max_t:
        return 0.0
    if t <= opt_t:
        return t - base_t
    return (opt_t - base_t) * (max_t - t) / (max_t - opt_t)


WINTER_PHENOLOGY = dict(   # rebuild phase 6 (2026-10-16). Disclosed in GenericCrops.crop: req 230, photoperiod 8-18 h, flowering at Pmax 340, grain filling 500, post-flowering 7/20/35 C.
    req=230.0, pmin=8.0, pmax=18.0, tt_flower_pmax=340.0, gf_tt=500.0, post=(7.0, 20.0, 35.0), base_t=2.0,
    # NOT disclosed, fitted to Cycles' own daily vernalization column (3 sites, 8,000 accumulating days, corr 0.99, rmse 0.42): increment = K x tent(daily mean T; L, O, U).
    # The fitted peak (7.8 C) differs from the file's VERNALIZATION_TEMPERATURE_THRESHOLD_OPTIMAL (1.5 C); L and U agree with the file (-4, 15) to within 1 C.
    vern_k=10.0, vern_l=-4.53, vern_o=7.78, vern_u=15.88,
    # NOT disclosed: the twilight allowance in the photoperiod (0 deg gives 279, 6 deg gives 359 against the disclosed 340 at a Texas site)
    twilight_deg=4.6)


def photoperiod_hours(doy, lat_deg, twilight_deg=0.0):
    dec = 0.409 * math.sin(2 * math.pi * doy / 365.0 - 1.39)
    x = (-math.tan(math.radians(lat_deg)) * math.tan(dec) - math.sin(math.radians(twilight_deg)) / (math.cos(math.radians(lat_deg)) * math.cos(dec)))
    return 24.0 / math.pi * math.acos(max(-1.0, min(1.0, x)))


def vernalization_increment(tavg, V):
    if tavg <= V["vern_l"] or tavg >= V["vern_u"]:
        return 0.0
    f = (tavg - V["vern_l"]) / (V["vern_o"] - V["vern_l"]) if tavg <= V["vern_o"] else (V["vern_u"] - tavg) / (V["vern_u"] - V["vern_o"])
    return V["vern_k"] * f


def thermal_time_increment(tx, tn, base_t, opt_t, max_t):
    if THERMAL_TIME_SUBDAILY:
        mean, amp = (tx + tn) / 2, (tx - tn) / 2
        return sum(_dev_rate(mean + amp * math.cos(2 * math.pi * (h + 0.5 - 15) / 24), base_t, opt_t, max_t)
                   for h in range(24)) / 24
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


ROOT_TTF_FULL = 0.5   # thermal-time fraction at which roots reach maximum depth (engine assumption; Cycles has a ROOT_PROGRESSION nudge parameter)
# Senescence timing (2026-10-26, under test against Mead LAI): the senescence clock of the two-clock canopy runs at dtt (1 + CANOPY_SENES_STRESS_K (1 - water factor x N factor)), so a stressed canopy senesces earlier
# (N deficiency accelerates leaf senescence, Sinclair and de Wit 1975; Cycles' wheat output shows it), and the whole senescence term is moved later by CANOPY_SENES_DELAY in thermal-time fraction. Both 0 = the documented shape.
CANOPY_SENES_STRESS_K = 0.0
# Late-season growth efficiency (2026-10-26, under test against Mead biomass): growth after thermal-time fraction LATE_RUE_X0 is scaled down linearly to LATE_RUE_F at maturity (radiation use efficiency falls during grain filling as leaf N is
# remobilized to the grain, Sinclair and Horie 1989). F = 1 is no effect.
LATE_RUE_X0 = 0.7
LATE_RUE_F = 1.0
CANOPY_SENES_DELAY = 0.0
CANOPY_TWO_CLOCK = True   # 2026-10-14: expansion term on the stress-slowed canopy clock, senescence term on real thermal time (Cycles' unstressed corn matches eix 0.95 and the paper's decline -16 + 16x on thermal-time fraction)
CANOPY_SHAPE_FORCE = (6, -20, -16, 16)   # default since 2026-10-14 (simultaneous calibration): the paper's own senescence constants, applied to all crops
CANOPY_EIX_FORCE = 0.99


def canopy_cover_two(x_clock, x_thermal, eix=1.0, shape=DEFAULT_CANOPY_SHAPE):
    a, b, c, d = shape
    return eix / (1 + math.exp(a + b * max(0.0, x_clock)) + math.exp(c + d * max(0.0, x_thermal)))


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


TTF50_SHOOT_PARTITION = 0.42   # 2026-10-18: 0.42 (was 0.32). Fitted on Cycles' realised shoot share of net growth with the SI form (exponent 4), crop-file fsti/fstf and root retention 0.6: corn 0.422, silage 0.422, sorghum 0.419 (rms 0.0007 to 0.005), identical across site halves and N rates; with it and a growth scalar of 1.0, Cycles' states forced, above-ground biomass matches at N>=150 (corn 1.002, silage 1.007, sorghum 1.002, soybean 1.016). The old 0.32 was a compensating refit; wheat keeps it via crop key ttf50 until checked.
# Previous note: Eq. SI.8-11's own half-max point isn't given a numeric value in
# either source -- the literal reading of its name (0.5) was replaced 2026-09-23 with a real,
# data-driven fit against real Cycles' own daily output (MECHANISM_LOG.md item 3, formerly
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


def shoot_fraction(ttf, fsti, fstf, ttf50=None):
    """Eq. SI.8-11: modified Michaelis-Menten allocation of new growth to shoot vs. root."""
    if ttf50 is None:
        ttf50 = TTF50_SHOOT_PARTITION   # read at call time (a default argument would freeze the value at import and make overrides no-ops)
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
PLANT_DAY_TT = os.environ.get("PLANT_DAY_TT", "1") == "1"   # True = the engine counts the planting day's thermal time (until 2026-10-23); False = Cycles' convention, accumulation starts the day after planting
N_SOLVE_DEBUG = None
DIAG_DENIT = None   # appends (year, doy, layer-1 relative saturation used, profile nitrate, respired C, denitrification) per day; None = off
N_UNMET = None   # diagnostic: appends (year, doy, kg N/ha) of net immobilization the mineral pool could not supply
N_SIMULTANEOUS = True   # ADOPTED 2026-10-19 (corn 94 sites vs the same code without it: grain MAE gain +0.039 [+0.028,+0.051] / +0.012 [+0.006,+0.017] / 0.000 at N=0/150/400); simultaneous solve of uptake, growth and N factor within the day (see simulate_season)
N_UPTAKE_RATE_PER_DAY = None  # None = uptake limited only by demand (validated default); else also capped at this fraction/day of the reachable mineral N pool (nitrate_per_layer path)
DIAG_LOSTC = None
ROOT_C_AT_HARVEST = os.environ.get("ROOT_AT_HARVEST", "0") == "1"   # 2026-10-21: retained root carbon enters the residue pool at the end of the crop, not daily
NH4_UPTAKE_W = float(os.environ.get("NH4_UPTAKE_W", "1.0"))   # weight of the ammonium pool in the pool the crop draws from (1 = pro rata with nitrate, as before; 0 = nitrate only)
IMMOB_SPLIT = os.environ.get("IMMOB_SPLIT", "nh4first")   # nh4first (net form, as before) or prorata
RHIZO_N_UPTAKE = os.environ.get("RHIZO_N", "1") == "1"   # 2026-10-21: the N for the share of root growth that leaves the plant (1 - root_retained_frac) is also taken from the mineral pool
N_DEMAND_SCALE = 0.70   # 2026-10-17 measured: Cycles unstressed marginal total-N concentration of new growth is 0.68 (corn, silage corn) to 0.75 (winter wheat) of the crop-file dilution curve marginal a(1-b)W^-b, growth-weighted over 16 sites x 3 N rates (n_demand_ratio_2026_10_17.py). Was 0.874562 (a leaching fit).
GROWTH_CANOPY_LAG = 1.0   # days between the reported canopy and the canopy that drives radiation-limited growth (1 = previous day; 1.5 = mean of the previous two days); per-crop key growth_canopy_lag overrides
GROWTH_PREV_CANOPY = True   # step 6: radiation-limited growth uses the canopy at the start of the day (previous day's)
CANOPY_WATER_POW = 0.0   # step 6 (replaces the W0 line): canopy clock rate = water_stress_mult ** POW (Cycles: 0.9 at 2.5% stress, 0.6 at 27%, 0.37 at 60%, 0.06 at 90%)
VPD_FLOOR_KPA = 0.2
WUE_CO2_EXP = 0.197   # 2026-10-18: measured on Cycles' own response to fixed CO2 of 300/400/500 ppm (co2_response_2026_10_18.py, 12 sites, corn N=400: biomass exponent 0.12 to 0.25, mean 0.18, rising with water stress); the engine's response with this exponent matches (RMS 0.023 across sites vs 0.191 at the previous 0.424275, fitted on the yield trend, REFIT_PLAN row 50); a separate RUE exponent fits to 0.044, not distinguishable from 0, so RUE_CO2_EXP stays 0
RUE_CO2_EXP = 0.0   # 2026-10-18: exponent on the CO2 ratio in the radiation-use-efficiency scale (paper Sec 2.5: eps_R and eps_W are both scaled with CO2); 0.0 = unscaled, the previous behaviour
CANOPY_N_POW = 1.0   # 2026-10-14: canopy clock rate = water**CANOPY_WATER_POW * n_stress**CANOPY_N_POW (measured on 86k day-pairs of Cycles daily interception: 1.35 and 3.85, rms 0.20); None = use the linear CANOPY_N_COEF form
N_STRESS_FULL_RATIO = 0.06
N_STRESS_FLOOR_RATIO = 0.2  # below N_STRESS_KNEE_RATIO the stress factor falls linearly to 0 at this ratio instead of at N_STRESS_FULL_RATIO (0 = off); Cycles corn never dilutes below ~0.2 of the critical curve
N_UPTAKE_FLOOR_MGKG = 0.3   # 2026-10-13 (was 1.0, 28-site sweep 0..1.0): minimum root-zone nitrate concentration the crop can draw down to (mg N/kg soil)
N_STRESS_AG_BASIS = False
N_AG_FRACTION = 0.88
N_STRESS_R0, N_STRESS_R1, N_STRESS_SMAX, N_STRESS_Q = 0.641, 0.281, 0.764, 0.90
if os.environ.get("NSTRESS_REFIT", "0") == "1":   # 2026-10-21: refit on Cycles' own daily plant states (nstress_refit_2026_10_21.py), removes the +0.017 / +0.024 bias at N=150 / 0
    N_STRESS_R0, N_STRESS_R1, N_STRESS_SMAX, N_STRESS_Q = 0.621, 0.247, 0.794, 0.668
N_STRESS_KNEE_RATIO = 0.26


def n_stress_from_ratio(ratio, crop):
    """N stress factor from the aboveground N concentration over the critical curve (the nitrogen nutrition index when the curve is Lemaire's). `n_stress_n0` set: growth proportional to the index above a structural floor (Ingestad 1979 as cited in Lemaire et al. 2008, relative growth rate linear in plant N concentration); unset: the law fitted to Cycles' daily states."""
    n0 = crop.get("n_stress_n0")
    if n0 is not None:
        return max(0.0, min(1.0, (ratio - n0) / (1.0 - n0)))
    return 1.0 - N_STRESS_SMAX * max(0.0, min(1.0, (N_STRESS_R0 - ratio) / (N_STRESS_R0 - N_STRESS_R1))) ** N_STRESS_Q
N_STRESS_GROWTH_POW = 1.0   # 2026-10-15 fit: growth uses n_stress**pow; Cycles grows ~13% more under N stress than (1-stress) x unstressed growth
N_STRESS_ZERO_RATIO = 0.86  # was 0.62; refit 2026-10-12 with SIXPOOL_ML_N_A 76 on 28 sites (fertilized corn bias -0.36 to +0.11)
N_STRESS_CRIT_FLOOR_MGHA = None   # biomass floor of the critical curve used for the N stress ratio only (None = NCRIT_FLOOR_MGHA); Cycles' implied critical concentration keeps rising below 1 Mg/ha (6.2% at 0.6-1, 7.1% at 0.3-0.6 against the 5.5% cap)
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
# shows is dominated by nitrogen stress, not water -- see MECHANISM_LOG.md
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

    CORRECTED 2026-09-29: this docstring previously claimed the factor "ranges from 0 at/below
    -5C through 1.0 around 30C" -- checked directly and that is false. The real curve crosses
    1.0 around 9.5C (RothC's own real calibration reference, roughly a UK annual mean
    temperature) and keeps climbing well past it for anything warmer: 1.90 at 15C, 2.82 at
    20C, 3.80 at 25C, 4.79 at 30C. That's real RothC behavior, not a bug in this function --
    RothC's own base decomposition rates are calibrated assuming this factor swings from near-0
    in winter to several-fold-above-1 in summer, averaged back down over a full annual cycle
    that includes cold months. This engine only ever samples the WARM half of that cycle
    (background N only accrues on days with actual crop growth, i.e. real growing-season days,
    never winter), so using the raw, unnormalized value here systematically over-credited
    background nitrogen by roughly 3x relative to what BACKGROUND_N_KG_HA_DAY was actually
    calibrated for -- see ROTHC_WEATHER_FACTOR_NORM below for the fix and how it was found."""
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


ROTHC_WEATHER_FACTOR_NORM = 2.025
# Real bug found and fixed 2026-09-29, via the pattern-assertion test suite (see
# pattern_assertions.py): rothc_temp_factor()'s raw output, multiplied directly into
# BACKGROUND_N_KG_HA_DAY as if it were a 0-1 "how warm was today" dimmer, was in fact
# averaging around 3x above 1.0 for any real growing season, since real RothC's own
# temperature curve is not bounded near 1 in warm conditions (see that function's own
# corrected docstring). Combined with rothc_moisture_factor()'s own real, correctly-bounded
# behavior, the two together were systematically over-crediting background soil nitrogen
# by a large, unintended margin -- caught because it made the nitrogen knob show ZERO
# effect on corn yield at Iowa, Kansas, Maryland, North Dakota, and even a tile-resolved
# Rock Springs, since background alone already exceeded real crop N demand before any
# fertilizer was added. The exact, hand-curated Rock Springs validation path still showed
# a weak-but-real nitrogen response, which is what let this go unnoticed for so long --
# it was close enough to the edge there that the bug happened not to fully swamp the signal
# for that one specific site, but any other real location tipped over into "N never
# matters," exactly the false, harmful classroom pattern this whole audit was built to
# catch.
#
# Fixed by normalizing the raw temp*moisture product against its own empirical average
# over a real reference record, rather than capping or removing the real temperature
# variability this mechanism exists to provide. The reference: every real growing day
# (the same days background actually accrues on: dGB_water_limited > 0) across the full,
# real, validated 37-year Rock Springs record (1980-2016), instrumented directly by
# running the real simulate_season() with a hook capturing every rothc_temp_factor()/
# rothc_moisture_factor() call, not a synthetic guess -- mean rothc_temp_factor 2.818,
# mean rothc_moisture_factor 0.688, mean combined weather_factor 2.025 (n=4630 real
# growing-day samples). Dividing by this constant makes a "typical" Rock Springs growing
# day read ~1.0 (matching what BACKGROUND_N_KG_HA_DAY was actually calibrated to assume
# in the first place, before this weather scaling was added on 2026-09-24), while
# preserving every bit of the real day-to-day and year-to-year relative variability the
# raw RothC shape provides -- a warmer/wetter-than-average day still credits more than a
# cooler/drier one, just around the right center of mass instead of three times too high.
#
# This constant is intentionally tied to ONE reference record (Rock Springs) rather than
# derived per-site, matching this project's own established practice for similar
# calibration constants (e.g. tillage_clay_frac's own Rock-Springs-topsoil default) --
# revisit if a second, independently-validated real-Cycles reference record ever becomes
# available to check it against.

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


# ---------------------------------------------------------------------------
# STATUS (2026-10-01, updated after a real fix, not just the first finding):
# the first multi-site test found N=0 and N=650 grain coming out byte-
# identical at every site tried (Rock Springs, Iowa, Kansas) -- background
# mineralization alone fully satisfying crop demand, eliminating any
# fertilizer response, contradicting real Cycles' own documented pattern
# (relative yield never hits exactly 1.0 at any real tested year). The
# INITIAL diagnosis (SIXPOOL_KS fit against a whole-9-layer-profile sum,
# therefore invalid at single-layer scope) was WRONG -- ks, as a rate
# constant, is valid to apply to any one layer's own REAL absolute Cs, the
# actual problem was that this mechanism's computed Cs0 wasn't using that
# real absolute value. Found and fixed by checking directly against real
# Cycles' own actual layer-1 SOIL ORG C stock (soilLayersCN.txt, Rock
# Springs: 11.417 Mg C/ha) -- see SIXPOOL_TOPSOIL_DEPTH_M's own comment and
# sixpool_init_state()'s docstring for the two further wrong values tried
# (a 0.20m guess, and layer0["thick"] itself) before landing on the correct
# fixed 0.05m depth, which matches that real reference almost exactly
# (11.422 computed) and is the actual real control volume SIXPOOL_KS/
# SIXPOOL_KRA/SIXPOOL_K_RTZ were all back-calculated against.
#
# Result after the fix: Rock Springs (both its hand-curated profile and
# its own STATSGO2-resolved one) and Kansas now show real, sensible,
# non-trivial nitrogen responses -- relative yield 0.72/0.75, close to and
# in Kansas's case slightly better than the RothC path's own 0.74/0.80 at
# the same site/years, and inside the real literature/Cycles-documented
# band.
#
# Iowa was first flagged as a separate, unresolved problem (its real SOC
# exceeding sixpool_csx_pct()'s own saturation ceiling) -- that diagnosis
# was tested directly (capping Cs at the ceiling) and found WRONG; it made
# no difference at all. The real explanation, found by building and
# running real Cycles input files for Iowa for the first time this
# project (no real ground truth existed there before): real Cycles ITSELF
# shows near-complete nitrogen saturation at Iowa in MOST years (relative
# yield exactly 1.0 in 12+ of 37 years checked, mean 0.946) -- Iowa's real,
# famously fertile prairie soil genuinely supplies enough background N
# that added fertilizer often changes little, in real Cycles' own
# simulation, not just this engine's. This mechanism's Iowa behavior
# (mean relative yield 0.999) is closer to that real 0.946 reference than
# the currently-shipped RothC path is at the same site (0.794, too
# responsive, not too flat) -- genuinely a better absolute-level match,
# not a regression. What neither mechanism captures is real Cycles' own
# YEAR-TO-YEAR variability in how saturated a given year gets (real years
# range 0.70-1.00; this mechanism's and RothC's own year-to-year pattern
# both correlate slightly NEGATIVELY with which real years are more or
# less responsive) -- the same category of gap already documented for
# Kansas's nitrogen-response muting (MECHANISM_LOG.md item 6),
# consistent with that item's own standing diagnosis that real multi-year
# soil-state carryover, not a single-season mechanism tweak, is the likely
# fix. Still opt-in, not adopted as a default -- the mean-level win at all
# three tested sites is real, but the missing year-to-year variability is
# a real, shared limitation with the existing RothC path, not resolved by
# switching to this mechanism.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Real six-pool soil carbon/nitrogen mineralization (Kemanian et al. 2024 SI
# Eq. SI.10-14), built 2026-10-01 as a PARALLEL, OPT-IN alternative to the
# RothC-based BACKGROUND_N_KG_HA_DAY proxy above -- selected via
# simulate_season(background_n_model="sixpool"); "rothc" (the existing
# mechanism) stays the default, byte-identical for every existing caller.
# NOT validated against real Cycles output yet, NOT a replacement for the
# RothC path until proven at least as good on the crops that already pass
# (corn, soybean) -- see MECHANISM_LOG.md's 2026-10-01 entries for the
# full back-calculation trail behind every constant below, and CLAUDE.md for
# the explicit scope decision this was built under.
#
# Scope (explicit, from Matt, 2026-10-01): NARROW first -- a single topsoil-
# layer two-pool (Cm, Cs) carbon system driving a real day-by-day nitrogen
# mineralization signal, for a single crop/season. Not yet extended to
# multi-layer tracking, residue carryover between rotation phases, or
# tillage's real six-pool mixing effect (tillage here still only applies the
# existing disclosed ft/ftx stand-in, same as the RothC path).
#
# Two pieces remain genuinely unresolved and are shipped as disclosed
# placeholders, per Matt's explicit go-ahead rather than holding the build
# for more searching:
#   - fA (microbial-size saturation stimulant): fixed at 1.0. Real Rock
#     Springs data shows the real Cm/Cs ratio sits persistently at 2.8-3.4%,
#     right at the stated 3% activation threshold -- "mostly on" is a
#     defensible placeholder, not a wild guess, but it is still a guess.
#   - eps_c (carbon-use efficiency, the same symbol in both of the SI's own
#     pool equations): fixed at 0.4, the midpoint of the real disclosed
#     0.33-0.44 range (SI Sec. V).
#   - The SI's own fra/frt/frz/frm per-source retention fractions are folded
#     into eps_c rather than resolved separately -- not back-calculable from
#     available data, since the back-calculated kra/k_rtz/krm below already
#     describe GROSS pool depletion (confirmed against annualSoilProfileC.txt's
#     own "RES C DECOMP"/"ROOT C DECOMP" columns), not net retention.
#
# Net nitrogen mineralized is approximated as (total carbon respired as CO2
# that day) / CN_RATIO_SOM, a flat-ratio simplification -- real Cycles almost
# certainly tracks N through pool-specific stoichiometry paralleling each
# carbon pool, but those N:C ratios are disclosed nowhere checked so far, and
# this single-ratio shortcut is a standard, defensible approximation used in
# simplified mineralization models generally, not invented for this engine.
# ---------------------------------------------------------------------------

# Cycles' annual root-biomass input to the soil is EXACTLY 5/3 of its root biomass at harvest for corn
# (annualSoilProfileC.txt ROOT BIOMASS IN vs harvest.txt ROOT BIOMASS: 1.66667, sd 0.00000 over 37 years
# at both Iowa and Rock Springs; soybean 1.68, winter wheat 1.64, silage corn 1.85 in CornSilageSoyWheat),
# i.e. roots return more carbon than their final standing biomass (in-season turnover/rhizodeposition).
# The engine's root carbon input only credited the final root biomass, ~0.6x of Cycles' (found 2026-10-07).
ROOT_C_INPUT_FACTOR = 5.0 / 3.0
# Root carbon input is sized from water-limited growth (False, shipped) or from growth after N stress (True, the
# physically correct version). Found 2026-10-12: with N stress ignored, the engine fed 2.3 Mg C/ha of root carbon to
# the six-pool state for a 0.74 Mg/ha N-starved crop (Indiana N=0), so low-nitrogen sites immobilized too much N.
# Fixing it makes net mineralization match Cycles at most sites but raises N=0 yield bias (+0.01 to +0.96 Mg/ha) because
# the shipped N_ML_N_A / stress floor were tuned with the bug in place; retuning (N_A 90-170, floor 0.3-0.4, respiration
# saturation exponent) did not beat the shipped 16-site result, so it stays off until the yield-per-N response is refit.
ROOT_C_REALIZED_GROWTH = True   # default on since 2026-10-12 (continuous-run refit); see the comment above

CARBON_FRACTION_DM = 0.42  # standard literature fraction of plant dry matter that is carbon;
# a general, widely-cited value, not Cycles-specific or site-specific.

SIXPOOL_EPS_C = 0.4  # disclosed placeholder, see module comment above.
SIXPOOL_FA = 1.0  # disclosed placeholder, see module comment above.
SIXPOOL_KS = 0.00032  # back-calculated 2026-10-01 against real ContinuousCorn output, moderate
# confidence (~20-35% real uncertainty band, confirmed via a held-out CornSilageSoyWheat test).
SIXPOOL_KRA = 0.048  # back-calculated, midpoint of ContinuousCorn's own 0.037/day and
# CornSilageSoyWheat's 0.0417-0.0427/day -- a real, unexplained ~17% cross-scenario gap.
SIXPOOL_K_RTZ = 0.0684  # back-calculated, strong cross-scenario agreement (0.0563 vs 0.0580/day,
# under 3% apart between ContinuousCorn and CornSilageSoyWheat).
SIXPOOL_KRM = 0.0246  # back-calculated from CornSilageSoyWheat's real manure years only (a
# genuine 2-variable joint fit separating it from k_ra) -- one scenario's worth of confidence,
# not yet cross-checked against a second independent manured run.
SIXPOOL_EPS_C_KM_PRODUCT = 0.0165  # back-calculated combined eps_c*fA*k_m rate (midpoint of the
# real 0.013-0.02/day range), itself already carrying the same fA~1 assumption used here, so
# dividing by SIXPOOL_EPS_C below to recover k_m alone needs no further fA correction.
SIXPOOL_KM = SIXPOOL_EPS_C_KM_PRODUCT / SIXPOOL_EPS_C
SIXPOOL_CN_VARIABLE = True   # SI Eq. SI.14 variable microbial C:N (see sixpool_step)
CN_RATIO_SOM = 11.0  # SUPERSEDED 2026-10-02, kept only as the pre-fix historical constant (see
SIXPOOL_CN_CRA = 86.0  # real STAND/FLAT RESID C:N, soilLayersCN.txt, Rock Springs ContinuousCorn.
SIXPOOL_CN_CRTZ = 52.0  # real root-tissue C:N, computed from CornRM.90.txt's ROOT BIOMASS/ROOT N.
SIXPOOL_CN_CRM = 30.0  # real MANURE RESID C:N, soilLayersCN.txt, CornSilageSoyWheat.
SIXPOOL_CN_CM = 9.7  # real MIC C:N, soilLayersCN.txt layer 1, Rock Springs ContinuousCorn.
SIXPOOL_CN_CS = 9.4  # real SOIL ORG C:N, soilLayersCN.txt layer 1, Rock Springs ContinuousCorn.
SIXPOOL_TOPSOIL_DEPTH_M = 0.05  # fixed at Cycles' own REAL layer-1 thickness for Rock Springs
# (GenericHagerstown.soil, confirmed directly: /tmp/cycles-run/input/GenericHagerstown.soil
# layer 1 = 0.05m) -- the exact real control volume SIXPOOL_KS/SIXPOOL_KRA/SIXPOOL_K_RTZ were
# all back-calculated against, not a convention picked for convenience. Two wrong values were
# tried and rejected first, see sixpool_init_state()'s own docstring for the full account:
# a 0.20m guess (inflated Rock Springs' own Cs ~4x past its real value, confirmed directly
# against soilLayersCN.txt's own layer-1 SOIL ORG C, 11.417 Mg C/ha vs. 11.422 computed at
# 0.05m -- essentially exact); and layer0["thick"] itself (wrong for a different, more
# precise reason: this project's own STATSGO2-resolved soil profiles use a genuinely
# different layer-boundary convention than Cycles' own real .soil file, even at the exact
# same coordinates -- 0.15m vs 0.05m for Rock Springs, 0.33m for Kansas/Iowa -- so "whatever
# a given lookup's layer0 happens to be" isn't the quantity SIXPOOL_KS was fit against).


SIXPOOL_FE_TEMP_TO, SIXPOOL_FE_TEMP_C = 37.5, 4.0   # 2026-10-22: c = 4 as documented (Stockle and Campbell 1989 Eq. 18), To the one fitted parameter; the earlier pair 36.098 / 2.177 was better by 0.02 Mg/ha grain MAE (plan batch 3). 2026-10-21: Campbell's temperature function, the form Stockle and Campbell 1989 Eq. 18 uses (there c = 4), fitted to Cycles' composite factor with start-of-day moisture (fe_timing_2026_10_21.py, R2 0.960); replaces a 16-point measured table that it reproduces to rms 0.011 (grain MAE gain +0.010 [+0.003,+0.018] at N=0, neutral at N=150, 24 sites)


def sixpool_fe_temp(tmean):
    if tmean <= 0.0:
        return 0.0
    t = tmean + SIXPOOL_FE_TEMP_C; o = SIXPOOL_FE_TEMP_TO + SIXPOOL_FE_TEMP_C
    return min(1.0, max(0.0, (2.0 * t * t * o * o - t ** 4) / o ** 4))


def sixpool_fe_moisture(relwet):
    """Real, back-calculated fE moisture response: a one-sided ramp (quadratic fit, R^2=0.926,
    n=12876) from a real nonzero floor at/below the wilting point (relwet<=0) up to a clean 1.0
    plateau by about 60% of the plant-available-water range -- confirmed to have NO anoxia/
    waterlogging decline out to 2.6x relative wetness, checked across two structurally
    different real soils (Rock Springs clay-rich subsoil, Western Kansas sandy topsoil). See
    MECHANISM_LOG.md's "Check 1" entry, 2026-10-01, for the full account. relwet =
    (theta-pwp)/(fc-pwp), the same quantity this engine's water-stress code already computes."""
    if relwet <= 0:
        return 0.157
    if relwet >= 0.6:
        return 1.0
    return max(0.0, min(1.0, 0.157 + 1.052 * relwet + 1.337 * relwet * relwet))


SIXPOOL_FE_MOISTURE_PTS = ((-0.3, 0.0), (0.0, 0.04), (0.05, 0.13), (0.15, 0.38), (0.3, 0.79), (0.45, 0.98),
                           (0.6, 1.0), (1.0, 0.97), (2.0, 0.90))
# Refit 2026-10-02 against 104,220 site-layer-days of Cycles' own FACTOR COMP. (soilLayersCN.txt) with
# Cycles' own per-layer SOIL TMP and water content, 16 sites: the old quadratic ramp (floor 0.157 at/below
# the wilting point) over-estimated dry-soil fE 2-5x and missed the mild decline above field capacity.


FE_MOISTURE_DOC = (0.22, 3.0)   # adopted 2026-10-22 (plan batch 4); (half response, power) = Cycles docs DECOMP_HALF_RESP 0.22, DECOMP_RESP_POWER 3.0 applied to relative wetness; None = the fitted table


def sixpool_fe_moisture_ml(relwet):
    """fE moisture response, per-layer mode (piecewise linear through SIXPOOL_FE_MOISTURE_PTS, flat beyond the ends).
    relwet = (theta-pwp)/(fc-pwp)."""
    if FE_MOISTURE_DOC is not None:
        r = max(relwet, 0.0)
        h, k = FE_MOISTURE_DOC
        return r ** k / (r ** k + h ** k)
    pts = SIXPOOL_FE_MOISTURE_PTS
    if relwet <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if relwet <= x1:
            return y0 + (y1 - y0) * (relwet - x0) / (x1 - x0)
    return pts[-1][1]


SIXPOOL_START_MOISTURE = True   # decomposition reads the layer water content at the START of the day (Cycles' composite factor does: R2 0.956 with yesterday's moisture, 0.856 with today's)


def sixpool_fe(tmean, relwet, ml=False):
    """Combined real environmental modulation factor, 0-1 (Kemanian et al. 2024's fE). ml=True uses the
    per-layer-mode moisture refit (sixpool_fe_moisture_ml)."""
    return max(0.0, min(1.0, sixpool_fe_temp(tmean) * (sixpool_fe_moisture_ml(relwet) if ml else sixpool_fe_moisture(relwet))))


def sixpool_csx_pct(clay_frac):
    """Real saturation capacity, Kemanian & Stockle (2010) Eq. 3 (C-Farm, Cycles' own
    predecessor model): the paper's own printed "Cx = 21.1+37.5*fclay" reads as "mg C kg-1
    soil," implausibly low taken literally -- corrected to g C/kg (i.e. percent*10), giving
    Csx(%) = 2.11+3.75*fclay. This EXACTLY matches Csx back-calculated independently from real
    Cycles ContinuousCorn output at Rock Springs' own three real clay fractions (21/37/55%) --
    two fully independent methods converging to 4-5 significant figures, not a single source
    trusted on faith. See MECHANISM_LOG.md, 2026-10-01, "Csx...fully resolved." clay_frac
    is a 0-1 fraction."""
    return 2.11 + 3.75 * clay_frac


def sixpool_bulk_density(sat):
    """Standard soil-physics identity: bulk density = particle density (2.65 Mg/m3, the
    standard value for mineral soil) * (1 - porosity), with porosity read directly off this
    engine's own Saxton-Rawls saturated water content (sat = porosity by volume). A general
    relationship, not a Cycles-specific or invented formula."""
    return 2.65 * (1.0 - sat)


def sixpool_fh(cs, csx):
    """Real SI Eq. SI.13 humification-saturation factor: fH = 1-(Cs/Csx)^6."""
    ratio = max(0.0, cs / csx) if csx > 0 else 0.0
    return max(0.0, 1.0 - ratio ** 6)


# Per-layer mode refit (2026-10-02): regressing Cycles' own annual SOM respiration (soilC.txt) on its own
# per-layer FACTOR COMP. (fE) x SOIL ORG C x fD(C SAT. RATIO), 528 site-years over 16 sites, the SI's
# fD form 1-1/(1+(a*r)^b) fits best at a=9.95, b=1.145, ks=0.000348 (rms log error 0.347; the old
# a=4.5, b=3, ks=0.00032 gives 0.563; no fD at all gives 0.393). Used only by the per-layer pool.
SIXPOOL_DIAG = None  # optional list; when set, sixpool_step appends (cs_loss, residue_decomp, residue_co2) per call
SIXPOOL_ML_EPS_H = 0.53
# Clay-dependent humified fraction of decomposed residue (opt-in, 2026-10-07): (a, b) in a + b*(1-exp(-5.5*clay_frac)),
# the C-Farm Eq. 4a clay shape (Kemanian & Stockle 2010) fitted to Cycles' humified/(humified+residue respired) over 16 sites:
# 0.370 + 0.152 g, rms 0.034 vs 0.047 for one constant. None keeps the flat SIXPOOL_ML_EPS_H.
SIXPOOL_ML_HUM_CLAY = (0.34145, 0.152)  # default since 2026-10-07: 16-site table with N_A 140 improved fertilized corn error 1.59 -> 1.55 and leaching, denitrification, N2O slightly; None restores the flat EPS_H
SIXPOOL_ML_RES_SCALE_SURF = 0.54     # 2026-10-27: share of the surface-residue carbon that becomes microbial biomass, relative to the shared efficiency; tuned to Schomberg et al. 1994 N immobilized per biomass lost when set
SIXPOOL_ML_RES_SCALE_BURIED = 0.54   # the same for buried root residue
DIAG_RESN = None   # (decomp_ra, N immobilized by surface residue decomposition, N released by it, decomp_rtz, N immobilized by buried, N released by it)
SIXPOOL_ML_FH_P = 12.0
SIXPOOL_ML_FH_FLOOR = 0.2  # Cycles still humifies ~0.12-0.17 of decomposed residue C at Cs/Csx >= 1 (Iowa 1980-83)
# Per-layer Cs decomposition (2026-10-02, supersedes the fD-form fit above, which fit the same data at
# rms 0.347): Cycles' annual SOM respiration regressed on its own per-layer FACTOR COMP. x SOIL ORG C,
# 528 site-years, with a free fD shape collapsed to a constant (b -> 0), so the best form is
# resp = KS * sum_i fE_i * Cs_i * exp(-Q * zmid_i), rms log error 0.204 (0.347 with the SI fD form and no
# depth term, 0.563 with the original constants); per-site mean bias within +/-0.27 except Wisconsin -0.39.
# 2026-10-23: Pravia et al. 2019 (Agric Syst 171:13-22) Eqs 3 and 4 as published: kx 0.00015 d-1, fs = 1 - 1/(1 + (Cs/Cx/0.22)^3), no depth term (depth enters through Cx and Cs/Cx); the fitted trio was 0.000208, (4.26, 2.53), q 0.108
SIXPOOL_ML_DEPTH_Q = 0.0  # 2026-10-15 designed fallow experiment (row 42): Cycles' respiration has almost no depth decay once Cs/Csx saturation is modeled; was 4.44
SIXPOOL_ML_KS = 0.00015  # 2026-10-15 joint refit (row 43); was 0.000680
SIXPOOL_ML_FD_SI = (1.0 / 0.22, 3.0)  # 2026-10-15 default: the SI Eq. SI.13 saturating form fitted to Cycles' per-layer respiration in designed fallow runs (row 42), rms 0.20 vs 0.54 for the power law; was None  # 2026-10-13: the SI form fitted to Cycles annual respiration (see comment above); None restores the power law
# (An fD-style Cs/Csx saturation term, sixpool_fd_ml with constants 9.95/1.145, was removed 2026-10-08: unused since the
# per-layer fit found no Cs/Csx dependence in SOM respiration; see sixpool_step's `fd = 1.0` for the ml_sub branch.)


def sixpool_fd(cs, csx):
    """Real SI Eq. SI.13 decomposition-saturation factor: fD = 1-1/(1+(4.5*Cs/Csx)^3)."""
    ratio = max(0.0, cs / csx) if csx > 0 else 0.0
    return max(0.0, 1.0 - 1.0 / (1.0 + (4.5 * ratio) ** 3))


SIXPOOL_DEPTH_DECAY_M = 0.5  # fitted 2026-10-02 against native Cycles season net mineralization at 16
# CONUS sites (run_validation_multisite.py / MECHANISM_LOG.md): the exponential decay length of
# a layer's weight in the decomposing-carbon stock. rms log error across sites 0.565 (fixed 0.05m
# topsoil pool) -> 0.320 (decay length 0.5m); 0.3-1.5m all within 0.35, so not a knife-edge value.
SIXPOOL_DEPTH_K = 0.279  # scale so the exact Rock Springs Hagerstown profile (the pool's original
# calibration reference) lands at 0.057m, ~ the old fixed 0.05m -- the fit and that sanity check agree.


def sixpool_effective_depth_m(profile_raw, soc_top_pct):
    """Effective decomposing-pool depth (m) for a soil profile given as [{thick, soc}, ...] (soc in
    %), replacing the fixed SIXPOOL_TOPSOIL_DEPTH_M when a caller supplies the whole profile. Real
    Cycles decomposes organic matter in every layer; the old single 0.05m pool only ever saw layer
    1's SOC, which is why Iowa (3.5% SOC through 0.6m) got under half of Cycles' mineralization."""
    z, stock = 0.0, 0.0
    for l in profile_raw:
        zm = z + l["thick"] / 2.0
        stock += l["thick"] * l["soc"] * math.exp(-zm / SIXPOOL_DEPTH_DECAY_M)
        z += l["thick"]
    return SIXPOOL_DEPTH_K * stock / soc_top_pct if soc_top_pct > 0 else SIXPOOL_TOPSOIL_DEPTH_M


def sixpool_init_state(layer0, clay_pct, soc_pct, depth_m=None):
    """Initializes the topsoil two-pool (+ residue) carbon state from the same real soil
    texture/SOC data the caller already used to build layer0's own hydraulic properties --
    deliberately scoped to layer0 only, the exact same control volume the existing RothC-based
    BACKGROUND_N_KG_HA_DAY mechanism already targets (n_pool_by_layer[0]), so this is a drop-in
    alternative at the same point, not a deeper or shallower profile. cra/crtz/crm (residue
    pools) all start at 0.0 -- no previous-crop residue carryover exists anywhere in this
    engine (consistent with the already-disclosed "soil layers always initialize at a fixed
    moisture fraction, no carbon spin-up by default" limitation), so the only real carbon
    input for a from-scratch single season is the live crop's own root growth, added day by
    day into crtz inside sixpool_step().

    Uses SIXPOOL_TOPSOIL_DEPTH_M (0.05m) -- NOT layer0["thick"], and NOT the earlier,
    wrong 0.20m guess either. Full real history, 2026-10-01: a fixed 0.20m depth was tried
    first, reasoning that layer0's thickness varying hugely across this project's already-
    resolved sites (Rock Springs' hand-curated profile: 0.05m; Iowa's resolved-tile profile:
    0.33m) looked like an arbitrary STATSGO2 artifact that shouldn't drive carbon-pool size.
    That specific number was wrong -- caught by checking against real Cycles' own actual
    layer-1 SOIL ORG C stock (soilLayersCN.txt, Rock Springs, 1980-01-01: 11.417 Mg C/ha):
    using layer0["thick"] (0.05m there) reproduces that real value almost exactly (11.422
    computed), so 0.20m had inflated it roughly 4x past reality -- exactly why Rock Springs
    itself (the very site SIXPOOL_KS was back-calculated against) showed complete,
    byte-identical N=0/N=650 yield after that "fix."

    Reverting to layer0["thick"] directly looked right (it fixed Rock Springs' hand-curated
    profile) but was ALSO wrong, for a different, more precise reason found testing it
    against every already-resolved multi-site soil (not just Rock Springs' two versions):
    this project's two soil-data sources use genuinely different layer-boundary conventions
    for the SAME real location -- Cycles' own real GenericHagerstown.soil defines Rock
    Springs' layer 1 at 0.05m, but this project's own STATSGO2 nearest-cell lookup
    (field_data.py, used by every multi-site panel) resolves the SAME coordinates to a
    0.15m-thick first layer, and Kansas/Iowa's own resolved layers are 0.33m. SIXPOOL_KS was
    back-calculated against ONE specific real reference (Cycles' real 0.05m Rock Springs
    layer), not against "whatever a given lookup's own layer boundary happens to be" -- so
    layer0["thick"] is the WRONG quantity to scale by whenever a caller's soil didn't come
    from that exact reference. Confirmed directly: at a correctly-fixed 0.05m depth, Rock
    Springs (both the hand-curated profile AND the STATSGO2-resolved one), and Kansas, all
    land at a defensible Cs/Csx ratio (0.60-0.68, matching the real Cycles reference); Iowa
    alone still sits above 1.0 (1.066) even at this correct depth -- a SEPARATE, genuine
    finding (Iowa's own real measured SOC, 3.488%, exceeds what the Csx(clay) formula says
    its particular texture should be able to hold at saturation), not a depth-scaling
    artifact, and not yet resolved -- see this module's own header comment."""
    bd = sixpool_bulk_density(layer0["sat"])
    csx_pct = sixpool_csx_pct(clay_pct / 100.0)
    depth_m = SIXPOOL_TOPSOIL_DEPTH_M if depth_m is None else depth_m
    csx = bd * depth_m * 100 * csx_pct
    cs0 = bd * depth_m * 100 * soc_pct
    return dict(cs=cs0, cm=0.03 * cs0, cra=0.0, crtz=0.0, crm=0.0, csx=csx, cra_age=9999.0, clay=clay_pct / 100.0)


CRA_MATURATION_TAU_DAYS = 1.0  # 2026-10-18: was 30.0 (a lag fitted 2026-10-02). Cycles shows no lag: its residue decays 4.7%/day from harvest day and net mineralization drops to about -1 kg N/ha/day for a week (immobilization), see ENGINE_REBUILD_PLAN.md 2026-10-18
# (soilLayersCN.txt, ContinuousCorn, Rock Springs) -- found while diagnosing the 2026-10-02
# multi-year sixpool-carryover instability (an undiminished stover pulse immediately
# decomposing at full rate the very next season, swamping the mineral-N pool). A hand-checked
# 10-day window right after a real harvest pulse showed decomposition ~13-22x slower than
# SIXPOOL_KRA predicts at the real driving weather of that window -- but a broad regression
# across all 37 years (n=10212 real day-pairs, implied k_ra = decomposed_amount/(fE*pool),
# matching SIXPOOL_KRA's own documented 0.04-0.044 almost exactly) showed no such problem in
# aggregate. Binning that same broad sample by REAL DAYS SINCE THE PRECEDING HARVEST PULSE
# resolved the contradiction: implied k_ra starts at only ~27% of its steady-state value in
# the first 10 days after a pulse, rises to ~73% by day 25-30, then plateaus (not cleanly at
# 100% -- real data settles around 75-85%, a real residual this simple exponential doesn't
# capture exactly). This is the real, well-documented "lag phase" before microbial
# colonization of fresh plant residue ramps up -- SIXPOOL_KRA itself was correctly fit to the
# real STEADY-STATE rate; what was missing was this real, separate, previously-undiscovered
# RAMP before that rate applies. Modeled as `1 - exp(-age/CRA_MATURATION_TAU_DAYS)` (least-
# squares fit to the real binned ratios, tau=29.8 rounded to 30) -- an honest, not-exact fit
# (slightly underfits the real early rise, slightly overfits the late plateau), applied only
# to decomp_ra (aboveground residue), not crtz/crm (root/manure), whose own real lag behavior
# wasn't checked this round. Completely inert for every currently-validated path: cra is
# always exactly 0.0 in the default (no multi-year carryover) mode, so this multiplier has
# nothing to act on there -- it only matters for the exploratory sixpool_initial_state
# carryover feature this was built to fix. See MECHANISM_LOG.md's 2026-10-02 entry for
# the full bin table and the broad-sample-vs-narrow-window reconciliation.


def cra_maturity_fraction(age_days):
    """Real, back-calculated fraction of steady-state decomposition rate a residue pool has
    reached, as a function of days since it was last added -- see CRA_MATURATION_TAU_DAYS's
    own docstring for the derivation. age_days=9999.0 (sixpool_init_state's own default,
    meaning "no residue has ever been added") correctly saturates to 1.0, a don't-care value
    since cra itself is 0.0 in that case."""
    return 1.0 - math.exp(-age_days / CRA_MATURATION_TAU_DAYS)


SIXPOOL_N_LIMIT_MM = True  # 2026-10-13: Cycles decomposition is limited by layer-1 mineral N concentration (measured on 28 sites, 53k days: residue decomposition relative to potential is flat above ~3 mg/kg and falls steeply below, 0.33 of plateau under 0.5 mg/kg, 0.6 at 0.5-1, 0.81 at 1-2)
SIXPOOL_N_HALF_MGKG = 0.623485  # refit 2026-10-15 (row 44); was 0.45  # half-saturation of c/(c+K)
SIXPOOL_N_FMIN = 0.516973  # refit 2026-10-15 (row 44); was 0.3   # floor: Cycles' decomposition stays at about a third of its plateau even below 0.5 mg/kg (a zero floor stalls the whole system)
SIXPOOL_N_POT_MULT = 1.17694  # refit 2026-10-15 with the stoichiometry path (row 44); was 1.6    # decomposition rates are potential (unlimited-N) rates times this when the limit is on


def n_conc_layer1(layers, nh4_kg_ha, no3_layers, no3_total):
    """Layer-1 mineral N concentration (mg N/kg soil) from the engine's NH4 surface pool and layer-1 nitrate."""
    l = layers[0]
    mass = sixpool_bulk_density(l["sat"]) * l["thick"] * 10.0   # kg soil per ha divided by 1e6 -> (kg N/ha)/(mg/kg) factor
    no3_0 = no3_layers[0] if no3_layers is not None else no3_total * min(1.0, l["thick"] / 1.0)
    return ((nh4_kg_ha or 0.0) + no3_0) / mass


def n_conc_layers(layers, nh4_kg_ha, no3_layers, no3_total):
    out = []
    for i, l in enumerate(layers):
        mass = sixpool_bulk_density(l["sat"]) * l["thick"] * 10.0
        no3_i = no3_layers[i] if no3_layers is not None else (no3_total if i == 0 else 0.0)
        out.append((((nh4_kg_ha or 0.0) if i == 0 else 0.0) + no3_i) / mass)
    return out


WEPS_DECAY = True      # 2026-10-27 step 5: residue decay as in WEPS (Steiner et al. 1999; WEPS Technical Documentation ch. 10): mass loss k x DD per day, DD = min(TF, MF)
WEPS_SURF, WEPS_ROOT = True, True   # which residue pools follow the WEPS law (surface residue, buried root residue)
WEPS_TO, WEPS_TB = 32.0, 0.0   # optimum and base temperature of the decomposition-day temperature function (WEPS Eq. 7)
N_LIMIT_STOICH = True  # 2026-10-27 step 5: residue decomposition limited so that net immobilization cannot exceed the mineral N of the layer (Kemanian et al. 2024: "if there is insufficient inorganic N ... decomposition is limited")


def weps_tf(t):
    """WEPS Eq. 7 (Taylor and Sexton 1972 form): temperature factor of a decomposition day, 0 at Tb and 1 at To."""
    d = t - WEPS_TB
    if d <= 0.0 or t >= 2 * WEPS_TO - WEPS_TB:
        return 0.0
    d0 = WEPS_TO - WEPS_TB
    return max(0.0, (2 * d ** 2 * d0 ** 2 - d ** 4) / d0 ** 4)


def weps_day(state, tx, tn, pp, layers, t_layers):
    """Decomposition days of the day for the surface residue (standing and flat share) and for each buried layer (WEPS Eqs 3 to 7). Standing moisture function MFs = P/4 + 0.4 MFs(t-1),
    zero after more than 4 dry days; flat residue takes the larger of MFs and theta/theta_fc of the surface layer; buried residue theta/theta_fc of its own layer."""
    dry = 0 if pp > 0.0 else state.get("weps_dry", 0) + 1
    mfs = min(1.0, pp / 4.0 + 0.4 * state.get("weps_mfs", 0.0))
    if dry > 4:
        mfs = 0.0
    state["weps_dry"], state["weps_mfs"] = dry, mfs
    tf_air = 0.5 * (weps_tf(tx) + weps_tf(tn))
    l0 = layers[0]
    mff = min(1.0, l0["theta"] / l0["fc"]) if l0["fc"] > 0 else 1.0
    fs = state.get("cra_fs", RES_STANDING_AT_HARVEST)
    dd_surf = fs * min(tf_air, mfs) + (1.0 - fs) * min(tf_air, max(mfs, mff))
    dd_bur = [min(weps_tf(t_layers[i]), min(1.0, l["theta"] / l["fc"]) if l["fc"] > 0 else 1.0) for i, l in enumerate(layers)]
    return dd_surf, dd_bur


def _sixpool_core(state, tmean, relwet, root_c_input_mg_ha, ft_eff=1.0, layers=None):
    """Advances the six-pool state by one day (mutating it in place) and returns the day's net
    nitrogen mineralized (kg N/ha) -- the quantity simulate_season() adds directly into
    n_pool_by_layer[0] in place of the RothC-based background_today term when
    background_n_model="sixpool". ft_eff is the same (1+tillage_ft(...)) multiplier the RothC
    path already computes, passed in rather than recomputed.

    Structure (Kemanian et al. 2024 SI Eq. SI.10-14, with the SI's own per-source fra/frt/frz/
    frm retention fractions folded into eps_c -- see this module's own header comment):
        dCra/dt  = 0 (no aboveground-residue input modeled in this v1 scope) - fE*kra*Cra
        dCrtz/dt = root_c_input - fE*k_rtz*Crtz
        dCm/dt   = eps_c*fH*(fE*kra*Cra + fE*k_rtz*Crtz + fE*krm*Crm) - fA*fE*ft*km*Cm
        dCs/dt   = eps_c*fA*fE*fH*km*Cm - fE*ft*fD*ks*Cs
    Net carbon respired as CO2 each day = whatever is NOT retained at each transfer (residue
    decomposition not humified into Cm; Cm turnover not humified into Cs; all of Cs's own
    decomposition, which has no further downstream pool -- matching real Cycles' own "SOM
    RESPIRED C" column, confirmed exactly equal to fE*fT*fD*ks*Cs).

    Net N mineralized (2026-10-02, replacing the original flat-CO2/CN_RATIO_SOM shortcut):
    computed per transfer using each pool's OWN real, disclosed C:N ratio (SIXPOOL_CN_* in the
    module header), not one ratio applied to the total. N is released when carbon leaves a pool
    (at that pool's own C:N) and consumed when carbon is retained into a receiving pool (at the
    receiving pool's own C:N) -- the standard decomposer mass-balance identity. Residue C:N
    (~86 for stand/flat, ~52 for root, ~30 for manure) runs far higher than Cm/Cs's own C:N
    (~9.4-9.7), so building microbial biomass out of residue carbon is a real, large net N SINK
    (immobilization) on most days, not a source -- this is why the function can and does return
    a negative value (simulate_season() floors the pool it feeds at zero after adding it, the
    same way a real mineral-N pool can't go physically negative). This single change is what
    lets the mechanism's own net N output decline as the Cm/Cs pools build toward their own
    steady state, instead of every bit of decomposed carbon counting as mineralized N regardless
    of whether it was actually retained into growing biomass."""
    if "ml" in state and layers is not None:
        return sixpool_ml_step(state, tmean, layers, root_c_input_mg_ha, ft_eff)
    cs, cm, cra, crtz, crm, csx = state["cs"], state["cm"], state["cra"], state["crtz"], state["crm"], state["csx"]
    cm0 = cm
    ml_sub = state.get("ml_sub", False)
    fe = sixpool_fe(tmean, relwet, ml_sub)
    if SIXPOOL_N_LIMIT_MM and not N_LIMIT_STOICH and state.get("n_conc1") is not None:
        _c = state["n_conc1"]
        _khalf = SIXPOOL_N_HALF_MGKG   # 2026-10-15 opt-in clay dependence of the N gate: heavy clay saturates at lower concentration, so fertilizer raises net N less
        _gate = SIXPOOL_N_POT_MULT * (SIXPOOL_N_FMIN + (1.0 - SIXPOOL_N_FMIN) * _c / (_c + _khalf))
        fe *= _gate
    fh = sixpool_fh(cs, csx)
    if ml_sub:
        _ratio = cs / csx if csx > 0 else 0.0
        _a, _b = SIXPOOL_ML_FD_SI
        fd = 1.0 - 1.0 / (1.0 + (_a * max(0.0, _ratio)) ** _b)  # the SI's saturating form: rises with Cs/Csx at low saturation, flat near saturation
        ks_use = SIXPOOL_ML_KS * math.exp(-SIXPOOL_ML_DEPTH_Q * state["zmid"])
    else:
        fd = sixpool_fd(cs, csx)
        ks_use = SIXPOOL_KS

    crtz += root_c_input_mg_ha  # the only real carbon input modeled in this v1 scope -- see
    # sixpool_init_state's own docstring for why cra/crm have no input pathway here.

    cra_age = state.get("cra_age", 9999.0)
    cra_maturity = cra_maturity_fraction(cra_age)
    state["cra_age"] = cra_age + 1.0  # ages one day regardless of whether cra is nonzero --
    # harmless, since maturity only matters when cra>0, and cra only ever becomes nonzero via
    # the harvest-crediting reset (simulate_season()) that also resets this to 0.0 at the
    # same moment the fresh pulse lands, so the two always stay in sync.

    _fer = fe
    if WEPS_DECAY and WEPS_SURF and state.get("weps_dd_surf") is not None and state.get("cra_k") is not None:
        decomp_ra = state["cra_k"] * state["weps_dd_surf"] * cra
    else:
        decomp_ra = _fer * SIXPOOL_KRA * cra_maturity * cra
    if WEPS_DECAY and WEPS_ROOT and state.get("weps_dd_bur") is not None and state.get("rtz_k") is not None:
        decomp_rtz = state["rtz_k"] * state["weps_dd_bur"] * crtz
    else:
        decomp_rtz = _fer * SIXPOOL_K_RTZ * crtz
    decomp_rm = _fer * SIXPOOL_KRM * crm
    _fs = state.get("res_fe_scale", 1.0)
    if _fs != 1.0:
        decomp_ra *= _fs; decomp_rtz *= _fs; decomp_rm *= _fs
    cra = max(0.0, cra - decomp_ra)
    _n_ra = decomp_ra * 1000 / state.get("cra_cn", SIXPOOL_CN_CRA)
    crtz = max(0.0, crtz - decomp_rtz)
    crm = max(0.0, crm - decomp_rm)

    gross_residue_decomp = decomp_ra + decomp_rtz + decomp_rm
    if ml_sub:
        _r = max(0.0, cs / csx) if csx > 0 else 0.0
        _eps_h = SIXPOOL_ML_EPS_H if SIXPOOL_ML_HUM_CLAY is None else (
            SIXPOOL_ML_HUM_CLAY[0] + SIXPOOL_ML_HUM_CLAY[1] * (1.0 - math.exp(-5.5 * state.get("clay", 0.2))))
        _gross_eff = decomp_ra * SIXPOOL_ML_RES_SCALE_SURF + decomp_rtz * SIXPOOL_ML_RES_SCALE_BURIED + decomp_rm
        cm_gain_from_residue = _eps_h * max(SIXPOOL_ML_FH_FLOOR, 1.0 - _r ** SIXPOOL_ML_FH_P) * _gross_eff
    else:
        cm_gain_from_residue = SIXPOOL_EPS_C * fh * gross_residue_decomp
    co2_residue = gross_residue_decomp - cm_gain_from_residue

    cm_loss = SIXPOOL_FA * fe * ft_eff * SIXPOOL_KM * cm
    cs_gain = SIXPOOL_EPS_C * SIXPOOL_FA * fe * fh * SIXPOOL_KM * cm
    co2_cm = max(0.0, cm_loss - cs_gain)

    cs_loss = fe * ft_eff * fd * ks_use * cs
    co2_cs = cs_loss  # Cs has no further downstream pool in this two-pool system -- all of
    # its loss is CO2, matching real Cycles' own "SOM RESPIRED C" column exactly.

    state["resp_mg_ha"] = co2_residue + co2_cm + cs_loss   # total C respired today (Mg C/ha): drives denitrification substrate (rebuild phase 4)
    cm = max(0.0, cm + cm_gain_from_residue - cm_loss)
    cs = max(0.0, cs + cs_gain - cs_loss)

    state["cs"], state["cm"], state["cra"], state["crtz"], state["crm"] = cs, cm, cra, crtz, crm

    n_released = (_n_ra
                  + decomp_rtz * 1000 / SIXPOOL_CN_CRTZ
                  + decomp_rm * 1000 / SIXPOOL_CN_CRM
                  + cm_loss * 1000 / SIXPOOL_CN_CM
                  + cs_loss * 1000 / SIXPOOL_CN_CS)
    n_immobilized = (cm_gain_from_residue * 1000 / SIXPOOL_CN_CM
                      + cs_gain * 1000 / SIXPOOL_CN_CS)
    if ml_sub and SIXPOOL_CN_VARIABLE:
        # SI Eq. SI.14: the C:N of newly formed microbial biomass depends on the C:N of the decomposing residue and on the soil mineral N concentration (8.5 to 11.25);
        # microbial N is tracked so that the N released when microbes turn over is the N they actually hold
        nm = state.get("nm")
        if nm is None:
            nm = cm0 * 1000 / SIXPOOL_CN_CM
        _n_dec = decomp_ra / state.get("cra_cn", SIXPOOL_CN_CRA) + decomp_rtz / SIXPOOL_CN_CRTZ + decomp_rm / SIXPOOL_CN_CRM
        cnd = gross_residue_decomp / _n_dec if _n_dec > 1e-15 else SIXPOOL_CN_CRTZ
        _xr = (cnd / 110.0) ** 3
        cn_new = 8.5 + 5.5 * (_xr / (1.0 + _xr)) * (0.5 / (1.0 + ((state.get("n_conc1") or 0.0) / 8.0) ** 3))
        n_in = cm_gain_from_residue * 1000 / cn_new
        if DIAG_RESN is not None and _gross_eff > 1e-15:
            DIAG_RESN.append((decomp_ra, n_in * decomp_ra * SIXPOOL_ML_RES_SCALE_SURF / _gross_eff, _n_ra, decomp_rtz, n_in * decomp_rtz * SIXPOOL_ML_RES_SCALE_BURIED / _gross_eff, decomp_rtz * 1000 / SIXPOOL_CN_CRTZ))
        n_loss_m = nm * cm_loss / cm0 if cm0 > 1e-12 else 0.0
        state["nm"] = max(0.0, nm + n_in - n_loss_m)
        n_released = _n_ra + decomp_rtz * 1000 / SIXPOOL_CN_CRTZ + decomp_rm * 1000 / SIXPOOL_CN_CRM + n_loss_m + cs_loss * 1000 / SIXPOOL_CN_CS
        n_immobilized = n_in + cs_gain * 1000 / SIXPOOL_CN_CS
    if ml_sub and SIXPOOL_CN_VARIABLE:
        state["res_net_n"] = (_n_ra + decomp_rtz * 1000 / SIXPOOL_CN_CRTZ + decomp_rm * 1000 / SIXPOOL_CN_CRM) - n_in
    else:
        state["res_net_n"] = (_n_ra + decomp_rtz * 1000 / SIXPOOL_CN_CRTZ + decomp_rm * 1000 / SIXPOOL_CN_CRM) - cm_gain_from_residue * 1000 / SIXPOOL_CN_CM
    state["gmin"], state["gimm"] = n_released, n_immobilized   # gross flows (kg N/ha), exposed for the ammonium and nitrate bookkeeping
    if ml_sub:
        if SIXPOOL_DIAG is not None:
            SIXPOOL_DIAG.append((cs_loss, gross_residue_decomp, co2_residue, n_released - n_immobilized, 0.0, cm_loss, decomp_ra, decomp_rtz, cm_gain_from_residue, cs_gain, co2_cm))
        return n_released - n_immobilized
    if SIXPOOL_DIAG is not None:
        SIXPOOL_DIAG.append((cs_loss, gross_residue_decomp, co2_residue, n_released, n_immobilized, cm_loss, decomp_ra, decomp_rtz, cm_gain_from_residue, cs_gain, co2_cm))
    return n_released - n_immobilized


SIXPOOL_ML_ROOT_DECAY_M = 0.25  # exponential depth distribution of root-carbon input (layer midpoint)
SIXPOOL_ML_TMEAN_INIT = 11.0  # initial annual-mean air temperature (C) for the soil-temperature model


SIXPOOL_ML_TILL_DEPTH_M = 0.15  # tillage disturbance factor applies only to layers starting above this depth


SOILT_DIFFUSIVITY_M2_DAY = 0.08   # thermal diffusivity; the SI quotes a damping depth of 0.13 to 0.25 m for the daily wave, i.e. 0.05 to 0.2 m2/day
SOILT_DEEP_M = 3.0


def hc_make(layer_thicks, tmean_init):
    """Heat-conduction grid for soil temperature: a geometric finite-volume grid (cells of 0.02 m growing by 25 percent) down to SOILT_DEEP_M, the surface held at the day's mean
    air temperature and the bottom at the running long-term mean. Layer temperatures are cell temperatures weighted by overlap with each soil layer."""
    h, z = [], 0.0
    w = 0.02
    while z < SOILT_DEEP_M - 1e-9:
        w = min(w, SOILT_DEEP_M - z); h.append(w); z += w; w *= 1.25
    n = len(h)
    mid = [sum(h[:i]) + h[i] / 2.0 for i in range(n)]
    D = SOILT_DIFFUSIVITY_M2_DAY
    g = [D / (mid[i + 1] - mid[i]) for i in range(n - 1)]          # conductance between cell i and i+1 (m2/day per m)
    g_top, g_bot = D / mid[0], D / (SOILT_DEEP_M - mid[-1])
    a, b, c = [0.0] * n, [0.0] * n, [0.0] * n
    for i in range(n):
        gl = g[i - 1] if i > 0 else g_top
        gu = g[i] if i < n - 1 else g_bot
        a[i] = -gl / h[i] if i > 0 else 0.0
        c[i] = -gu / h[i] if i < n - 1 else 0.0
        b[i] = 1.0 + (gl + gu) / h[i]
    cp = [0.0] * n
    for i in range(n):
        cp[i] = c[i] / b[i] if i == 0 else c[i] / (b[i] - a[i] * cp[i - 1])
    edges, z0 = [], 0.0
    for t in layer_thicks:
        edges.append((z0, z0 + t)); z0 += t
    wts = []
    for (e0, e1) in edges:
        ws, zc = [], 0.0
        for i in range(n):
            ov = max(0.0, min(zc + h[i], e1) - max(zc, e0)); zc += h[i]
            ws.append(ov)
        tot = sum(ws)
        wts.append([x / tot for x in ws] if tot > 0 else None)
    return dict(n=n, a=a, b=b, cp=cp, g_top=g_top / h[0], g_bot=g_bot / h[-1], T=[tmean_init] * n, tm=tmean_init, wts=wts)


def hc_step(hc, tair):
    """One day: implicit conduction step with the surface at tair; returns the layer temperatures."""
    n, a, b, cp, T = hc["n"], hc["a"], hc["b"], hc["cp"], hc["T"]
    hc["tm"] += (tair - hc["tm"]) / 365.0
    d = list(T)
    d[0] += hc["g_top"] * tair
    d[-1] += hc["g_bot"] * hc["tm"]
    dp = [0.0] * n
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        dp[i] = (d[i] - a[i] * dp[i - 1]) / (b[i] - a[i] * cp[i - 1])
    T[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        T[i] = dp[i] - cp[i] * T[i + 1]
    out = []
    for ws in hc["wts"]:
        out.append(sum(x * y for x, y in zip(ws, T)) if ws is not None else hc["tm"])
    return out


def sixpool_ml_init(layers, profile_raw):
    """Per-layer six-pool state (2026-10-02): one Cs/Cm/Crtz two-pool per soil layer (own clay ->
    Csx, own SOC, own bulk density, full layer thickness), plus a surface residue pool (cra, crm,
    cra_age) at the top level that decomposes in layer 0, matching Cycles' per-layer decomposition
    (a single lumped pool could not reproduce site-to-site respiration: rms log error 0.79)."""
    subs, z = [], 0.0
    for l, raw in zip(layers, profile_raw):
        sub = sixpool_init_state(l, raw["clay"], raw["soc"], depth_m=raw["thick"])
        sub["z0"], sub["zmid"], sub["ml_sub"] = z, z + raw["thick"] / 2.0, True
        subs.append(sub)
        z += raw["thick"]
    return dict(ml=subs, cs=sum(x["cs"] for x in subs), cm=sum(x["cm"] for x in subs),
                cra=0.0, crtz=0.0, crm=0.0, csx=sum(x["csx"] for x in subs), cra_age=9999.0, clay=subs[0].get("clay", 0.25))


def sixpool_step(state, tmean, relwet, root_c_input_mg_ha, ft_eff=1.0, layers=None):
    """One day of one pool set. With N_LIMIT_STOICH a probe pass on a copy finds the net immobilization the residue decomposition would cause; if it exceeds the mineral N of the layer
    (state['n_avail_kg_ha']) the residue decomposition rates are scaled so that it equals it, then the real pass runs."""
    na = state.get("n_avail_kg_ha")
    if N_LIMIT_STOICH and na is not None and "ml" not in state:
        _nd = len(SIXPOOL_DIAG) if SIXPOOL_DIAG is not None else 0
        probe = dict(state); probe["res_fe_scale"] = 1.0
        net = _sixpool_core(probe, tmean, relwet, root_c_input_mg_ha, ft_eff, layers)
        if SIXPOOL_DIAG is not None: del SIXPOOL_DIAG[_nd:]
        rn = probe.get("res_net_n", 0.0)
        if net < -na and rn < 0.0:
            other = net - rn
            state["res_fe_scale"] = max(0.0, min(1.0, (-na - other) / rn))
        else:
            state["res_fe_scale"] = 1.0
    return _sixpool_core(state, tmean, relwet, root_c_input_mg_ha, ft_eff, layers)


def sixpool_ml_step(state, tmean, layers, root_c_input_mg_ha, ft_eff=1.0):
    """Advance every layer's two-pool one day; returns total net N mineralized (kg N/ha). Layer 0
    carries the surface residue pools. Root carbon input is distributed over layers by an
    exponential depth weight."""
    subs = state["ml"]
    wts = [math.exp(-x["zmid"] / SIXPOOL_ML_ROOT_DECAY_M) * (x["z0"] >= 0) for x in subs]
    if CFORCE is not None:   # 2026-10-19 diagnostic: start-of-day carbon pools per layer set to Cycles' (surface residue, layer microbial, soil organic, root residue)
        _cf = CFORCE.get((_DIAG_YEAR, _DIAG_CTX.get("doy")))
        if _cf is not None:
            if CFORCE_LOG is not None and not CFORCE_LOG: CFORCE_LOG.append([(x["cs"], x["cm"], x["crtz"]) for x in subs] + [state["cra"]])
            if "surface" in CFORCE_WHICH: state["cra"] = _cf["surface"]
            for _i, _sub in enumerate(subs):
                if _i in _cf["layers"]:
                    _cs, _cm, _cr = _cf["layers"][_i]
                    if "cs" in CFORCE_WHICH: _sub["cs"] = _cs
                    if "cm" in CFORCE_WHICH: _sub["cm"] = _cm
                    if "root" in CFORCE_WHICH: _sub["crtz"] = _cr
    wsum = sum(wts) or 1.0
    total = 0.0
    resp_tot = 0.0
    _hc = state.get("hc")
    if _hc is None:
        _hc = state["hc"] = hc_make([2.0 * (x["zmid"] - x["z0"]) for x in subs], SIXPOOL_ML_TMEAN_INIT)
    _t_hc = hc_step(_hc, tmean)
    _dd_surf, _dd_bur = (None, None)
    if WEPS_DECAY and state.get("wx_day") is not None:
        _dd_surf, _dd_bur = weps_day(state, state["wx_day"][0], state["wx_day"][1], state["wx_day"][2], layers, _t_hc)
    for i, (sub, l) in enumerate(zip(subs, layers)):
        t_layer = _t_hc[i]
        if _dd_bur is not None:
            sub["weps_dd_bur"], sub["rtz_k"] = _dd_bur[i], state.get("rtz_k")
            if i == 0:
                sub["weps_dd_surf"], sub["cra_k"] = _dd_surf, state.get("cra_k")
        if N_LIMIT_STOICH and state.get("n_conc_layers") is not None:
            sub["n_avail_kg_ha"] = state["n_conc_layers"][i] * sixpool_bulk_density(l["sat"]) * l["thick"] * 10.0
        _th_fe = state["theta_start"][i] if (SIXPOOL_START_MOISTURE and state.get("theta_start") is not None) else l["theta"]
        relwet = ((_th_fe - l["pwp"]) / (l["fc"] - l["pwp"]) if l["fc"] > l["pwp"] else 1.0)
        sub["n_min"] = state.get("n_min")
        sub["n_conc1"] = state.get("n_conc1")
        if i == 0:
            sub["cra"], sub["crm"], sub["cra_age"] = state["cra"], state["crm"], state["cra_age"]
            sub["cra_cn"] = state.get("cra_cn", SIXPOOL_CN_CRA)
        ft = ft_eff if sub["z0"] < SIXPOOL_ML_TILL_DEPTH_M else 1.0
        if DIAG_FE is not None: DIAG_FE.append((_DIAG_YEAR, _DIAG_CTX.get("doy"), i, t_layer, relwet, sixpool_fe(t_layer, relwet, True)))
        _v = sixpool_step(sub, t_layer, relwet, root_c_input_mg_ha * wts[i] / wsum, ft)
        total += _v
        resp_tot += sub.get("resp_mg_ha", 0.0)
        if i == 0:
            state["cra"], state["crm"], state["cra_age"] = sub["cra"], sub["crm"], sub["cra_age"]
    state["gmin"] = sum(x.get("gmin", 0.0) for x in subs); state["gimm"] = sum(x.get("gimm", 0.0) for x in subs)
    state["cs"] = sum(x["cs"] for x in subs)
    state["cm"] = sum(x["cm"] for x in subs)
    if DIAG_CPOOL is not None: DIAG_CPOOL.append((_DIAG_YEAR, _DIAG_CTX.get("doy"), [x["cs"] for x in subs], [x["cm"] for x in subs], [x["crtz"] for x in subs], state["cra"]))
    state["resp_mg_ha"] = resp_tot
    if DIAG_RESP is not None:
        DIAG_RESP.append((_DIAG_YEAR, resp_tot, total))
    return total


N_DEMAND_REF = False   # opt-in: new-growth N concentration read at the unstressed reference biomass (paper Sec 2.5)


def n_critical_pct(biomass_mgha, crop, floor=None):
    """Whole-plant average/critical N concentration (%) at the given total biomass --
    the standard dilution-curve quantity, %Nc(W) = a*W^-b. Used two ways in
    simulate_season(): as the day-by-day stress-comparison THRESHOLD (is the plant's own
    actual tissue concentration above or below this), and, via n_marginal_demand_pct
    below, to size how much N a day's new growth actually needs -- the marginal rate,
    not this whole-plant average, is what a day-by-day uptake calculation should use for
    demand sizing, to avoid double-counting already-accumulated tissue's N."""
    biomass_mgha = max(biomass_mgha, 0.01)
    _fl = NCRIT_FLOOR_MGHA if floor is None else floor
    if crop.get("n_crit_lemaire"):   # Lemaire et al. 2008, Table 1: critical N dilution curve %Nc = a W^-b (a in %, W in Mg/ha): maize 3.4 / 0.37, sorghum 3.9 / 0.39, wheat 5.3 / 0.44
        _a, _b = crop["n_crit_lemaire"]
        return _a * (_fl ** (-_b) if (biomass_mgha < _fl and floor is not None) else 1.0) if biomass_mgha < _fl else _a * biomass_mgha ** (-_b)
    if biomass_mgha < _fl:
        return crop["n_max_conc"] * 100 * (_fl ** (-crop["n_dilution_slope"]) if floor is not None else 1.0)
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
    if crop.get("n_crit_lemaire"):
        _a, _b = crop["n_crit_lemaire"]
        return _a if biomass_mgha < NCRIT_FLOOR_MGHA else _a * (1 - _b) * biomass_mgha ** (-_b)
    if biomass_mgha < NCRIT_FLOOR_MGHA:
        return crop["n_max_conc"] * 100  # below the floor the curve is flat, so marginal = average
    return crop["n_max_conc"] * 100 * (1 - crop["n_dilution_slope"]) * biomass_mgha ** (-crop["n_dilution_slope"])


# _reference_n_demand() (the demand-precompute duplicate-loop function) was removed
# 2026-09-25, superseded by the day-by-day concentration-tracked nitrogen stress
# mechanism now in simulate_season()'s own main loop (see the comment above
# canopy_n_kg_ha there) -- it computed a season-total nitrogen demand for a since-
# retired season-total supply/demand ratio, and had no remaining callers once that
# ratio was replaced. See git history for the removed function if it's ever needed
# for reference.


NH3_FRAC_SYNTHETIC = 0.10  # IPCC 2006/2019 Refinement Tier-1 default FracGASF: 10% of applied
# synthetic mineral fertilizer N volatilizes as NH3/NOx when surface-applied -- a widely-cited
# general default (Table 11.3, Vol. 4), not derived from Cycles or this engine's own site data.
NH3_FRAC_MANURE = 0.20  # Same source's FracGASM: organic amendments (manure) volatilize at
# roughly twice the rate of mineral fertilizer, real and disclosed, not an invented multiplier.

MANURE_SOURCES = {
    # Real per-species manure composition, parsed directly from Cycles v1.4.4's own bundled
    # fert.txt (a FIXED_FERTILIZATION template catalog, 9 real manure SOURCE entries -- never
    # checked by this project before 2026-10-01 despite till.txt, its sibling operation-input
    # file, being mined extensively). nh4_frac is each species' N_NH4 fraction of its own total
    # N (N_Organic+N_NH4+N_NO3) -- the portion immediately plant-available the same day it's
    # applied, exactly the quantity manure_availability has stood in for with one flat 0.5
    # guess since this mechanism was first built. norg_frac is the remainder, kept here for
    # the record but NOT yet fed into any mineralization pathway (see manure_source's own
    # docstring below for why) -- a disclosed, not-yet-modeled simplification, same category
    # as every other "real data exists, only part of it is wired in" gap in this engine.
    # c_per_norg: kg organic C per kg organic N, C_Organic over N_Organic from the same catalog (2026-10-21), used to put the organic fraction into the surface residue pool.
    # Real cross-check this data corroborates rather than contradicts: the already-disclosed
    # SI Sec. IX Iowa case credits manure at "0.5 the availability of mineral N" -- Iowa is
    # real hog country, and Swine_Manure's own nh4_frac here is 0.553, strikingly close to
    # that independently-disclosed 0.5 figure for what was very plausibly the same manure type.
    "dairy": dict(nh4_frac=0.184, norg_frac=0.816, c_per_norg=13.9),
    "beef": dict(nh4_frac=0.250, norg_frac=0.750, c_per_norg=14.0),
    "veal": dict(nh4_frac=0.442, norg_frac=0.558, c_per_norg=14.1),
    "swine": dict(nh4_frac=0.553, norg_frac=0.447, c_per_norg=11.9),
    "sheep": dict(nh4_frac=0.368, norg_frac=0.632, c_per_norg=12.1),
    "goat": dict(nh4_frac=0.371, norg_frac=0.629, c_per_norg=11.8),
    "horse": dict(nh4_frac=0.300, norg_frac=0.700, c_per_norg=20.0),
    "chicken": dict(nh4_frac=0.200, norg_frac=0.800, c_per_norg=11.0),
    "turkey": dict(nh4_frac=0.135, norg_frac=0.865, c_per_norg=9.8),
}


MINERAL_SOURCES = {
    # Real per-product mineral-fertilizer NH4/NO3 split, parsed directly from the same
    # Cycles v1.4.4 fert.txt catalog MANURE_SOURCES already mines (17 real, non-manure
    # FIXED_FERTILIZATION SOURCE entries with nonzero total N; a further 3 -- Phosphorus,
    # Potassium, Sulphur -- carry zero N at all and are correctly excluded). Each fraction
    # is that source's own N_NH4 (or N_NO3) field divided by its total N fraction
    # (N_Organic+N_NH4+N_NO3+N_Charcoal, all as fractions of PRODUCT mass, not of applied N)
    # -- the same normalization MANURE_SOURCES already uses, cross-checked here against this
    # project's own already-shipped Dairy_Manure numbers (0.031+0.007=0.038 total N fraction,
    # 0.007/0.038=0.1842, matching MANURE_SOURCES["dairy"]["nh4_frac"]=0.184 exactly) before
    # trusting the same parse for these mineral entries. Added 2026-10-02 (continuing the same
    # NH4 trajectory investigation -- see volatilization_flux()
    # docstring and MECHANISM_LOG.md's 2026-10-02 entries) after finding this engine
    # treated every fresh mineral application as 100% NH4 on arrival, while real Cycles'
    # own ContinuousCorn.operation discloses UreaAmmoniumNitrate (UAN) specifically as
    # N_NH4=0.75/N_NO3=0.25 -- confirmed to trace exactly to this catalog's own
    # "32-00-00_Urea_Ammonium_Nitrate_Solution" entry (N_NH4=0.24, N_NO3=0.08 as fractions of
    # product mass; 0.24/0.32=0.75, 0.08/0.32=0.25, matching the operation file's own already-
    # normalized numbers to the fourth decimal). Most real products here are pure NH4-forming
    # (urea, anhydrous ammonia, ammonium sulfate, DAP, and every potassium/phosphorus-blended
    # NPK product that uses an ammonium N source) or pure NO3 (straight nitrate and the NPK
    # blends built on a nitrate N source) -- UAN and ammonium nitrate are the only two real
    # products in this catalog that genuinely split between both forms.
    "nitrate": dict(nh4_frac=0.0, no3_frac=1.0),
    "ammonium": dict(nh4_frac=1.0, no3_frac=0.0),
    "urea": dict(nh4_frac=1.0, no3_frac=0.0),
    "anhydrous_ammonia": dict(nh4_frac=1.0, no3_frac=0.0),  # 82-00-00_Anhydrous_Ammonia
    "uan": dict(nh4_frac=0.75, no3_frac=0.25),  # 32-00-00_Urea_Ammonium_Nitrate_Solution --
    # the real source already disclosed directly in ContinuousCorn.operation; see above.
    "ammonium_sulfate": dict(nh4_frac=1.0, no3_frac=0.0),  # 21-00-00_Ammonium_Sulfate
    "dap": dict(nh4_frac=1.0, no3_frac=0.0),  # 18-46-00_Di-Ammonium_Phoshate
    "potassium_nitrate": dict(nh4_frac=0.0, no3_frac=1.0),  # 13-00-44_Potassium_Nitrate
    "npk_30_15_0": dict(nh4_frac=1.0, no3_frac=0.0),
    "ammonium_nitrate": dict(nh4_frac=0.5, no3_frac=0.5),  # 33-00-00_Ammonium_Nitrate
    "npk_25_5_0": dict(nh4_frac=0.0, no3_frac=1.0),
    "npk_24_6_0": dict(nh4_frac=0.0, no3_frac=1.0),
    "npk_20_20_20": dict(nh4_frac=0.0, no3_frac=1.0),
    "potassium_ammonium_phosphate": dict(nh4_frac=1.0, no3_frac=0.0),  # 16-20-20
    "npk_15_15_0": dict(nh4_frac=1.0, no3_frac=0.0),
    "npk_15_15_15": dict(nh4_frac=1.0, no3_frac=0.0),
    "npk_13_13_13": dict(nh4_frac=1.0, no3_frac=0.0),
}


MINERAL_UREA_SHARE = {"urea": 1.0, "uan": 0.5}   # share of the applied N that is urea: UAN 32-0-0 is half urea N, a quarter ammonium N and a quarter nitrate N (the Cycles catalog lists urea as ammonium)
VOLAT_MACNACK_PH = None   # 2026-10-27: soil pH (assumed, the engine has no pH source) that switches volatilization to Macnack, Chim and Raun 2013 at fertilizer application, in place of the continuous wind law


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


DENITRIF_RELSAT_EXPONENT = 8.4433  # 2026-10-15 joint N-loss refit (opt_loss.py, REFIT_PLAN row 46); was 3.0   # fitted 2026-10-02 on 16 sites x 2 N rates x 37 years of native Cycles
DENITRIF_DEPTH_CAP_M = None  # if set, layer-1 denitrification is scaled by min(1, cap/thickness of layer 1)
DENITRIF_K_REL = 0.10113  # 2026-10-15 joint N-loss refit (row 46); was 0.012   # REFIT 2026-10-12 against Cycles v1.5.20 (was exponent 7, K 0.017594 on v1.4.4); the nitrification logistic and N2O factors below were refit the same day from v1.5.20's daily N output at 16 sites        # output (N.txt, water.txt, environ.txt); see denitrification_rate_rel()


def _denit_depth_factor(layers):
    if not DENITRIF_DEPTH_CAP_M:
        return 1.0
    return min(1.0, DENITRIF_DEPTH_CAP_M / layers[0]["thick"])


DENITRIF_THRESHOLD_FORM = True
DENITRIF_THR_K = 0.0101053  # 2026-10-15 N-loss fit (opt_loss2.py, REFIT_PLAN row 46); was 0.003880   # exp(-5.548)
DENITRIF_THR_REL = 0.46582
DENITRIF_THR_POW = 1.26959
DENITRIF_THR_TEXP = 0.372158


DENITRIF_RESP_K = 0.004137   # rebuild phase 4 (2026-10-16): fitted to Cycles' own daily denitrification with Cycles' own states as inputs (nlaw_denit2.py), 40 sites, N=0 and 150, held out by site
DENITRIF_RESP_REL_POW = 6.034
DENITRIF_RESP_NO3_POW = 0.725
DENITRIF_RESP_C_POW = 0.772


def denitrification_flux_resp(no3_total_kg_ha, theta_rel1, resp_mg_ha):
    """Daily denitrification (kg N/ha) = K * NO3^0.725 * Cresp^0.772 * rel1^6.03, Cresp = SOM plus residue respired carbon today (kg C/ha).
    A rate that depends only on layer-1 saturation (and temperature) explained none of the held-out daily variance (R2 0.01) even with Cycles'
    own states as input; adding the carbon respired (the electron-donor supply, which also carries the temperature signal) lifts held-out
    daily R2 to 0.50 and the site-total rms log error from 1.10 to 0.76. Form is the standard three-factor one (nitrate, carbon, anoxia)."""
    if no3_total_kg_ha <= 0.0:
        return 0.0
    c = max(resp_mg_ha * 1000.0, 0.0) + 1e-3
    return min(no3_total_kg_ha, DENITRIF_RESP_K * no3_total_kg_ha ** DENITRIF_RESP_NO3_POW * c ** DENITRIF_RESP_C_POW * min(max(theta_rel1, 0.02), 1.2) ** DENITRIF_RESP_REL_POW)


DENIT_STARTDAY = True
DENIT_SD = dict(K=0.367, kh=31.52, a=0.79, s0=0.736, sc=0.074)   # 2026-10-20: measured on Cycles' daily layer-1 states (denit_satvar_2026_10_20.py, start-of-day nitrate and saturation, R2 0.876)


DENIT_NLAYERS = 2   # layers that denitrify (Cycles' denitrification arrays are per layer; on Cycles' daily output layer 2 lifts R2 from 0.876 to 0.916, layers 3 and 4 add nothing)


def denitrification_layers(no3_start, theta_start, layers, sixpool_state, no3_now):
    """Per-layer denitrification (kg N/ha): the layer-1 law applied to each of the first DENIT_NLAYERS layers with that layer's own start-of-day
    nitrate and saturation and its own respired carbon (the six-pool profile carries respiration per layer)."""
    ml = sixpool_state.get("ml") if sixpool_state is not None else None
    out = []
    for i in range(min(DENIT_NLAYERS, len(layers))):
        r = ml[i].get("resp_mg_ha", 0.0) if (ml is not None and len(ml) > i) else (sixpool_state.get("resp_mg_ha", 0.0) if i == 0 else 0.0)
        if DENIT_APEX:
            out.append(denitrification_apex(no3_start[i], layers[i], theta_start[i], r, no3_now[i], (sixpool_state or {}).get("clay", 0.25)))
            continue
        out.append(denitrification_startday(no3_start[i], layers[i], theta_start[i], r, no3_now[i]))
    return out


DENIT_APEX = True   # ADOPTED 2026-10-23: per-layer denitrification as published for EPIC/APEX (Kemanian and Williams, CEAP 2011 APEX upgrades, Eqs 1 to 4); False restores the law fitted to Cycles (DENIT_SD)
DENIT_APEX_PARAMS = dict(rmax=32e-6, half=60.0, cresp=50.0, expo=60.0, amp=2.5, half_n2o=60.0)   # amp 2.5 is NOT sourced (class C suspect; the Cycles docs name POT_DENITRIF_RATE as a calibration multiplier without a default); the other four constants are as published; kg N/kg soil/d, mg N/kg, mg C/kg/d, steepness; amp scales the whole law (1.0 = as published)


def denitrification_apex(no3_start_kg_ha, layer, theta_start, resp_mg_ha, no3_now_kg_ha, fclay):
    """Rdn = rho dz Rmax fNO3 fresp fw (kg N/ha/d). fNO3 = NO3/(NO3 + 60) with NO3 in mg N/kg soil; fresp = min(1, CO2/50) with CO2 in mg C/kg soil/d;
    fw = 1/(1 + ((1 - Av)/(0.90 + 0.1 fclay))^-60) with Av the air-filled volume (m3/m3) at the start of the day."""
    if no3_start_kg_ha <= 0.0:
        return 0.0
    P = DENIT_APEX_PARAMS
    bd = sixpool_bulk_density(layer["sat"])
    mass = bd * layer["thick"] * 1e7                                  # kg soil/ha
    c = no3_start_kg_ha * 1e6 / mass                                  # mg N/kg
    co2 = max(resp_mg_ha * 1000.0, 0.0) * 1e6 / mass                  # mg C/kg soil/d
    av = max(layer["sat"] - theta_start, 0.0)
    fw = 1.0 / (1.0 + ((1.0 - av) / (0.90 + 0.1 * fclay)) ** (-P["expo"]))
    flux = P["amp"] * mass * P["rmax"] * (c / (c + P["half"])) * min(1.0, co2 / P["cresp"]) * fw
    return min(max(no3_now_kg_ha, 0.0), flux)


def denitrification_startday(no3_1_start, layer0, theta1_start, resp_mg_ha, no3_1_now):
    """Daily denitrification (kg N/ha), layer 1 only = K x respired C x c/(c + kh) x logistic(s), c the start-of-day layer-1 nitrate (mg/kg) and
    s = (theta - a pwp)/(sat - a pwp) the start-of-day layer-1 saturation measured above part of the wilting point. Cycles' flux acts on the START-of-day
    state (same-row states explain 0.65, start-of-day 0.75, with the pwp-shifted saturation and a logistic cutoff 0.876); the form is measured on
    Cycles, no published equation fits (Stockle and Campbell 1989 first-order form explains 0.07)."""
    if no3_1_start <= 0.0:
        return 0.0
    P = DENIT_SD
    c = no3_1_start / (sixpool_bulk_density(layer0["sat"]) * layer0["thick"] * 10.0)
    s = max(0.0, min(1.5, (theta1_start - P["a"] * layer0["pwp"]) / (layer0["sat"] - P["a"] * layer0["pwp"])))
    g = 1.0 / (1.0 + math.exp(max(-50.0, min(50.0, -(s - P["s0"]) / P["sc"]))))
    if DENIT_DAYCENT is not None:
        D = DENIT_DAYCENT
        g = 1.0 / (1.0 + math.exp(max(-50.0, min(50.0, -(s - D["s0"]) / D["sc"]))))
        flux = D["amp"] * min(1.15 * c ** 0.57, 0.1 * max(resp_mg_ha * 1000.0, 0.0) ** 1.3) * g   # the published numbers read as kg N/ha/d: that is the scale on which Cycles matches (amp 0.74 in denit_daycent_2026_10_22.py)
        return min(max(no3_1_now, 0.0), flux)
    return min(max(no3_1_now, 0.0), P["K"] * max(resp_mg_ha * 1000.0, 0.0) * c / (c + P["kh"]) * g)


DENIT_DAYCENT = None   # dict(amp, s0, sc): DAYCENT total N gas, min(1.15 NO3^0.57, 0.1 CO2^1.3) (Parton et al. 2001, Del Grosso 2000; g N/ha/d, NO3 mg/kg, CO2 kg C/ha/d) times a logistic in layer-1 saturation; None = the fitted law above


WINTERKILL_SOIL_T = True


def denitrification_rate_rel(theta_rel, tsoil_c):
    """Daily fractional denitrification of the NO3 pool as a function of topsoil RELATIVE saturation
    (theta/sat of layer 1) and soil temperature. Replaces denitrification_rate() (absolute layer-2
    theta, fitted on Rock Springs only) as the active mechanism: absolute theta does not transfer
    across soil textures (pooled across 16 sites it explains 9% of daily variance and misses
    site totals by a factor of 5; Iowa/Texas/Kansas were 2-12x low). Pooling all 16 sites, the
    implied rate (NO3 DENITRIF / prior-day PROF SOIL NO3) collapses onto ONE curve of layer-1
    relative saturation: 0.00001/day at 0.25, 0.0003 at 0.5, 0.002 at 0.75, 0.005 at 0.82, rising
    with roughly the 5th-7th power. Best pooled fit (grid over exponent, nitrate saturation and
    temperature form, daily R2 0.33, site-total rms log error 0.87 vs 1.61): rate = K * rel^7 *
    max(T,0)/15, linear in NO3 (a Michaelis-Menten nitrate term did not help). Annual totals fed
    Cycles' own NO3 pool: Iowa 50.9 vs 51.7, Texas 29.8 vs 30.0, Kansas 8.0 vs 7.4, Arkansas 11.4 vs
    12.5 kg N/ha (old formula: 31.9, 3.7, 0.6, 24.3). Known residual: cold snowmelt sites
    (Minnesota 30 vs 64, Wisconsin 3 vs 15) are under-predicted, likely thaw-period denitrification
    the temperature term zeroes out."""
    if theta_rel <= 0:
        return 0.0
    if DENITRIF_THRESHOLD_FORM:
        # step 12: fitted on Cycles' own daily layer-1 nitrate, water and soil temperature at 28 sites (teacher forced):
        # denitrification starts at a relative saturation of 0.514 and rises about linearly; site-total rms log error 0.54
        # against 1.06 for the power form below
        return max(0.0, min(1.0, DENITRIF_THR_K * max(0.0, min(theta_rel, 1.2) - DENITRIF_THR_REL) ** DENITRIF_THR_POW
                            * max(tsoil_c, 0.0) ** DENITRIF_THR_TEXP))
    return max(0.0, min(1.0, DENITRIF_K_REL * min(theta_rel, 1.2) ** DENITRIF_RELSAT_EXPONENT
                        * max(tsoil_c, 0.0) / 15.0))


SOIL_TEMP_LAG_K = 0.15  # reuses simulate_soil_temp()'s own already-validated lag-filter
# constant (2.65-day mean absolute error against real per-year planting dates) rather than
# inventing a second one for this unrelated use -- nitrification's own real driver is soil,
# not air, temperature, and this engine's main day loop otherwise only ever tracks air tmean.


NITRIF_RATIO_PARAMS = dict(k=0.2, r0=8.0, q=6.1948, f0=0.7952, s=0.0779)   # 2026-10-20: measured on Cycles' daily layer-1 states with the start-of-day NH4 and NO3 (previous day's end state) and the day's soil temperature and saturation (nitrif_timing_2026_10_20.py, R2 0.990; the earlier fit used end-of-day states, R2 0.83, and its constants were biased)


def nitrification_temp_factor(t):
    """Stockle and Campbell (1989) Eq. 11 (Watts and Hanks 1978), relative to the 35 C rate."""
    if t <= 0.0:
        return 0.0
    if t < 10.0:
        return 0.0105 * t + 0.00095 * t * t
    if t < 35.0:
        return 0.032 * t - 0.12
    return max(0.0, 4.5 - 0.1 * t) if t < 45.0 else 0.0


NITRIF_FW_DOC = False   # True: the nitrification moisture factor is Stockle and Campbell 1989 Eq. 8 instead of the fitted logistic cutoff


NITRIF_CAP_FIRST_ORDER = False   # the fitted first-order law with the CERES capacity index instead of the NO3:NH4 ratio term
NITRIF_CERES_CAPACITY = True   # with NITRIF_CERES: the CERES nitrification capacity (lag) index
NITRIF_CERES = False   # 2026-10-27 step 9: CERES nitrification (Godwin and Jones 1991 Eqs 13 and 14): fraction per day = min(0.8, A x 40 c / (c + 90)), A = min(moisture, temperature index)


def nitrification_flux_ratio(nh4_kg_ha, no3_surface_kg_ha, tsoil_c, sat_frac, layer0=None):
    """Daily nitrification (kg N/ha) = NH4 x k x fT(T) x fW(layer-1 saturation) / (1 + (NO3/NH4 / r0)^q). fT is the published
    Stockle and Campbell (1989) Eq. 11, which matches Cycles' temperature response in shape. Cycles' implied rate per kg NH4 is flat up to a surface
    NO3:NH4 of about 6 and collapses by 12 (no source gives this; it holds in every NH4 concentration bin and fits at R2 0.99 with start-of-day states), and drops sharply above a layer-1
    saturation of about 0.8 (no source gives the form; a logistic cutoff; Stockle and Campbell Eq. 8 tested 2026-10-22, NITRIF_FW_DOC, volatilization 1.25 to 1.91x). Parameters are measured on Cycles' own daily states."""
    if nh4_kg_ha <= 1e-9:
        return 0.0
    if NITRIF_CERES and layer0 is not None:
        c = nh4_kg_ha / (sixpool_bulk_density(layer0["sat"]) * layer0["thick"] * 10.0)   # ug N per g soil
        wfd = 1.111 * sat_frac if sat_frac < 0.9 else max(0.0, 10.0 - 10.0 * sat_frac)   # Stockle and Campbell 1989 Eq. 8 as the moisture index
        tf = min(1.0, nitrification_temp_factor(tsoil_c))
        if NITRIF_CERES_CAPACITY:
            # nitrification capacity index (Godwin and Jones 1991 listing): the nitrifier population grows by up to a factor 10 a day when ammonium, moisture and temperature allow
            # (RP2 = CNI exp(2.302 min(TF, WFD, SANC)), SANC = 1 - exp(-0.01313 NH4), clipped to 0.05 to 1) and falls when ammonium is depleted
            cni = layer0.get("_cni", 1.0)
            sanc = 1.0 - math.exp(-0.01313 * nh4_kg_ha)
            rp2 = min(1.0, max(0.05, cni * math.exp(2.302 * min(tf, wfd, sanc))))
        else:
            rp2 = 1.0
        a = min(rp2, wfd, tf)
        frac = min(0.8, a * 40.0 * c / (c + 90.0))
        rn = nh4_kg_ha * min(frac, max(0.0, (c - 0.5) / c))
        if NITRIF_CERES_CAPACITY:
            sanc2 = 1.0 - math.exp(-0.1363 * max(0.0, nh4_kg_ha - rn))
            xw = min(wfd, layer0.get("_wfy", wfd)); xt = max(tf, layer0.get("_tfy", tf))
            layer0["_cni"] = max(0.05, rp2 * min(xw, xt, sanc2)); layer0["_wfy"] = wfd; layer0["_tfy"] = tf
        return rn
    if NITRIF_CAP_FIRST_ORDER and layer0 is not None:
        # first-order nitrification with the CERES nitrification capacity index (Godwin and Jones 1991) in place of the NO3:NH4 ratio term fitted on Cycles
        P = NITRIF_RATIO_PARAMS
        fw = (1.111 * sat_frac if sat_frac < 0.9 else max(0.0, 10.0 - 10.0 * sat_frac)) if NITRIF_FW_DOC else 1.0 / (1.0 + math.exp(max(-50.0, min(50.0, (sat_frac - P["f0"]) / P["s"]))))
        tf = min(1.0, nitrification_temp_factor(tsoil_c))
        cni = layer0.get("_cni", 1.0)
        sanc = 1.0 - math.exp(-0.01313 * nh4_kg_ha)
        rp2 = min(1.0, max(0.05, cni * math.exp(2.302 * min(tf, fw, sanc))))
        rn = nh4_kg_ha * P["k"] * tf * fw * rp2
        sanc2 = 1.0 - math.exp(-0.1363 * max(0.0, nh4_kg_ha - rn))
        xw = min(fw, layer0.get("_wfy", fw)); xt = max(tf, layer0.get("_tfy", tf))
        layer0["_cni"] = max(0.05, rp2 * min(xw, xt, sanc2)); layer0["_wfy"] = fw; layer0["_tfy"] = tf
        return rn
    P = NITRIF_RATIO_PARAMS
    r = max(no3_surface_kg_ha, 0.0) / nh4_kg_ha
    x = (r / P["r0"]) ** P["q"] if r < 1e3 else 1e30
    if NITRIF_FW_DOC:
        fw = 1.111 * sat_frac if sat_frac < 0.9 else max(0.0, 10.0 - 10.0 * sat_frac)   # Stockle and Campbell 1989 Eq. 8
    else:
        fw = 1.0 / (1.0 + math.exp(max(-50.0, min(50.0, (sat_frac - P["f0"]) / P["s"]))))
    return nh4_kg_ha * P["k"] * nitrification_temp_factor(tsoil_c) * fw / (1.0 + x)


# Wind-driven volatilization (2026-10-20). Cycles zeroes volatilization at zero wind and is
# linear in it (volat_drivers_2026_10_20.py; log-linear fit on 920k daily rows, 24 sites,
# volat_form_2026_10_20.py): flux = exp(A) * c^B * theta1^C * wind * exp(E * T), c the layer-1
# NH4 concentration (mg/kg), R2 0.835 in log space, wind exponent 1.004 free. Cycles ignores pH,
# so there is no pH term (pH is an opt-in, see VOLAT_PH_SLOPE).
VOLAT_WIND_LN_A = -11.2896
VOLAT_WIND_B = 0.8588
VOLAT_WIND_C = -1.4581
VOLAT_WIND_E = 0.1456
VOLAT_AERO_PH = 5.75   # 2026-10-27: soil pH (assumed) that switches the daily NH3 loss to the Montes 2009 thermodynamics with an aerodynamic resistance; None keeps the fitted wind law
VOLAT_KD_L_KG = 0.0   # ammonium sorption coefficient of the soil, L water per kg soil equivalent (0 = none)
VOLAT_PH_SLOPE = 0.0   # ln-units of flux per pH unit above 7 (0 = off, as in Cycles); chemistry gives about ln(10) = 2.3 below pKa 9.25


def volatilization_flux(tsoil, nh4_kg_ha, layer0, wind_ms, ph=None):
    """Daily NH3 loss (kg N/ha) from the layer-1 ammonium pool; never more than the pool."""
    if nh4_kg_ha <= 0.0 or wind_ms <= 0.0:
        return 0.0
    if VOLAT_AERO_PH is not None:
        # Montes, Rotz and Chaoui 2009 Eqs 4, 10, 11 (dissociation and Henry constants) with an aerodynamic transfer, flux = gas-phase NH3 at the surface / r_a, r_a = 208 / u2 (FAO-56 Eq. 4)
        # as the paper recommends for field surfaces. TAN concentration is the ammonium of layer 1 in the soil water (no sorption unless VOLAT_KD_L_KG > 0).
        T = tsoil + 273.15
        ka = 10.0 ** (0.05 - 2788.0 / T)
        frac = 1.0 / (1.0 + 10.0 ** (-VOLAT_AERO_PH) / ka)
        kh = (0.2138 / T) * 10.0 ** (6.123 - 1825.0 / T)
        th_a = max(0.03, layer0["theta"])
        sol = th_a + VOLAT_KD_L_KG * sixpool_bulk_density(layer0["sat"])   # m3 of water-equivalent per m3 of soil
        c_tan = nh4_kg_ha * 0.1 / (sol * layer0["thick"])               # g N m-3 of soil water
        flux_g_m2_s = kh * frac * c_tan / (208.0 / wind_ms)
        return min(nh4_kg_ha, flux_g_m2_s * 86400.0 * 10.0)
    c = nh4_kg_ha / (sixpool_bulk_density(layer0["sat"]) * layer0["thick"] * 10.0)
    th = max(0.03, layer0["theta"])
    ln_f = (VOLAT_WIND_LN_A + VOLAT_WIND_B * math.log(max(c, 1e-6)) + VOLAT_WIND_C * math.log(th)
            + math.log(wind_ms) + VOLAT_WIND_E * tsoil)
    if ph is not None and VOLAT_PH_SLOPE:
        ln_f += VOLAT_PH_SLOPE * (ph - 7.0)
    return min(nh4_kg_ha, math.exp(ln_f))


# Nitrous oxide emission: N2O-N is a fixed share of each process flux: 1% of nitrified N and 10% of denitrified N (round literature-range values; the IPCC Tier 1 direct
# emission factor is 1% of N input). 2026-10-20: replaces a nitrate-concentration law back-calculated from Cycles' output (N2O_DENIT_A x NO3^0.816); against Cycles on 24 sites
# the constant share raises the site correlation of N2O from 0.80 to 0.87 at N=150 and from 0.54 to 0.80 at N=400. Output only: N2O does not feed back into any pool.
# N2O (2026-10-20, n2o_shares_2026_10_20.py, 920k Cycles daily rows). Cycles' shares are not constants: the N2O share of nitrification is 0.26 percent
# until layer-1 saturation passes about 0.8 and then rises to 8 percent (logistic centre 0.84, R2 0.77 against 0.15 for a constant); the N2O share of
# denitrification rises with the start-of-day layer-1 nitrate concentration (0.02 at 0 to 2 mg/kg, 0.4 above 80) and falls with saturation
# (A c^0.385 exp(-1.53 s), R2 0.77 against 0.65 for a constant). The earlier constants (0.01, 0.10) were set on end-of-day totals.
N2O_NIT = dict(a=0.0026, b=0.0696, s0=0.8394, w=0.0129)
N2O_DEN = dict(A=0.1155, p=0.3849, q=1.5325)


def n2o_from_nitrification(nitrified_kg_ha, sat_frac):
    P = N2O_NIT
    return nitrified_kg_ha * (P["a"] + P["b"] / (1.0 + math.exp(max(-50.0, min(50.0, -(sat_frac - P["s0"]) / P["w"])))))


N2O_APEX = True   # APEX Eq. 5 (Kemanian and Williams 2011): N2O share of denitrified N = fNO3 (1 - fw^0.5)(1 - fresp^0.33), same fNO3, fw and fresp as the denitrification law; no fitted constant


def n2o_from_denitrification(denitrified_kg_ha, no3_mgkg_start, sat_start, layer=None, resp_mg_ha=None, fclay=0.25):
    if denitrified_kg_ha <= 0.0:
        return 0.0
    if N2O_APEX and layer is not None and resp_mg_ha is not None:
        P = DENIT_APEX_PARAMS
        mass = sixpool_bulk_density(layer["sat"]) * layer["thick"] * 1e7
        co2 = max(resp_mg_ha * 1000.0, 0.0) * 1e6 / mass
        av = max(layer["sat"] * (1.0 - sat_start), 0.0)
        fw = 1.0 / (1.0 + ((1.0 - av) / (0.90 + 0.1 * fclay)) ** (-P["expo"]))
        fr = min(1.0, co2 / P["cresp"])
        return denitrified_kg_ha * (no3_mgkg_start / (no3_mgkg_start + P["half_n2o"])) * (1.0 - fw ** 0.5) * (1.0 - fr ** 0.33)
    P = N2O_DEN
    return denitrified_kg_ha * min(1.0, P["A"] * max(no3_mgkg_start, 1e-3) ** P["p"] * math.exp(-P["q"] * min(max(sat_start, 0.0), 1.2)))


IMMOB_FROM_NO3 = True   # opt-in: net immobilization (negative net mineralization) is drawn from NH4 first, then nitrate top-down (paper Sec 2.6: the microbial pool assimilates N from the ammonium and nitrate pools); False = NH4 only, the shortfall is dropped


def apply_net_min(nh4, no3, no3_layers, smin, sixpool_state=None):
    """Returns (nh4, no3) after a day's net mineralization. Positive goes to NH4. Negative takes NH4 first then nitrate (top layer down) when IMMOB_FROM_NO3, else only NH4 and the remainder is dropped."""
    if IMMOB_SPLIT == "prorata" and sixpool_state is not None and "gmin" in sixpool_state and IMMOB_FROM_NO3:
        # Cycles carries gross mineralization into ammonium and immobilization out of ammonium and nitrate (Kemanian 2024 Sec 2.6: the microbial pool "assimilates N from the
        # ammonium and nitrate pools"); the split is not documented, here in proportion to the two pools
        nh4 = nh4 + sixpool_state["gmin"]
        imm = sixpool_state["gimm"]; tot = nh4 + (sum(no3_layers) if no3_layers is not None else no3)
        if imm > 0 and tot > 1e-12:
            take = min(imm, tot); fn = nh4 / tot
            nh4 -= take * fn
            rest = take * (1.0 - fn)
            if no3_layers is not None:
                s_no3 = sum(no3_layers)
                if s_no3 > 1e-12:
                    for i in range(len(no3_layers)): no3_layers[i] -= rest * no3_layers[i] / s_no3
                no3 = sum(no3_layers)
            else:
                no3 -= rest
        return max(0.0, nh4), no3
    if smin >= 0 or not IMMOB_FROM_NO3:
        return max(0.0, nh4 + smin), no3
    need = -smin; t = min(nh4, need); nh4 -= t; need -= t
    if need > 0:
        if no3_layers is not None:
            for i in range(len(no3_layers)):
                t = min(no3_layers[i], need); no3_layers[i] -= t; need -= t
                if need <= 0: break
            no3 = sum(no3_layers)
        else:
            t = min(no3, need); no3 -= t
    if need > 1e-12 and N_UNMET is not None:
        N_UNMET.append((_DIAG_YEAR, _DIAG_CTX.get("doy"), need))   # immobilization the mineral pool could not supply (the engine drops it)
    return nh4, no3

DIAG_FALLOW_WATER = None   # diagnostics: appends the fallow-window daily water terms (see run_fallow_n_window); None = off


def run_fallow_n_window(layers, rows, nstate, sixpool_state=None, curve_number=75.0, slope_pct=0.0,
                        lat_deg=40.6875, de_state=None, model_denitrification=True, model_volatilization=True):
    """Bare-soil water balance PLUS the nitrogen dynamics that keep running with no crop: sixpool
    mineralization/immobilization (zero root carbon), nitrification, ammonia volatilization,
    denitrification and nitrate leaching, over an arbitrary weather window. Mutates `layers`,
    `nstate` ({n_nh4, n_no3, tsoil_lag}) and `sixpool_state` in place and returns
    (n_leached, n_denitrified, n_volatilized) totals for the window. Mirrors the in-season block in
    simulate_season() term for term (same rate functions), minus uptake and fertilizer.

    Built 2026-10-02 after the 16-site comparison showed Cycles carries 100-450 kg N/ha of standing
    nitrate through every January at Iowa/Minnesota/Illinois (ORG SOIL N mineralizes year-round,
    only ~48% of annual leaching and ~15% of denitrification fall in the crop window) while this
    engine started each season's mineral pool at zero, so leaching (Iowa 2 vs 41 kg N/ha) and
    denitrification (10 vs 52) could not be reproduced no matter how good the rate laws were."""
    leached = denit = volat = 0.0
    no3_layers = nstate.get("no3_layers")
    for w in rows:
        _dn_th0 = [l["theta"] for l in layers]
        _dn_no3_0 = list(no3_layers) if no3_layers is not None else [0.0] * len(layers)
        if sixpool_state is not None:
            sixpool_state["theta_start"] = _dn_th0
        if SNOW_MODEL:
            w = snow_adjust(layers, w, lat_deg)
        _rc = residue_cover_frac(sixpool_state)
        _eto0 = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], lat_deg)
        _re, _rev = residue_water_today(sixpool_state, w["pp"], _rc, _eto0, 0.0, w.get("snow_day", False))
        _th1_0 = zone_mean_theta(layers)
        drainage_mm, _roff, n_out = infiltrate(layers, w["pp"] - _re, curve_number, slope_pct, n_by_layer=no3_layers)
        if no3_layers is not None:
            leached += n_out
            nstate["n_no3"] = sum(no3_layers)
        eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], lat_deg)
        _ev_taken = soil_evaporation(layers, eto * (1.0 - _rc), 0.0, precip_mm=w["pp"] - _re, de_state=de_state, fallow=True, theta_start=_th1_0, snow_day=w.get('snow_day', False),
                         summer_time=summer_time_from_doy(w["doy"]))
        if DIAG_FALLOW_WATER is not None:   # (year, doy, precip after snow handling, residue rain evaporation, runoff, drainage, soil evaporation, ETo, profile water mm)
            DIAG_FALLOW_WATER.append((_DIAG_YEAR, w["doy"], w["pp"], _rev, _roff, drainage_mm, _ev_taken, eto, sum(l["theta"] * l["thick"] for l in layers) * 1000.0, _rc))
        _water_hook(layers, w["doy"], no3_layers)
        tmean = (w["tx"] + w["tn"]) / 2.0
        nstate["tsoil_lag"] += SOIL_TEMP_LAG_K * (tmean - nstate["tsoil_lag"])
        if sixpool_state is not None:
            relwet = ((layers[0]["theta"] - layers[0]["pwp"]) / (layers[0]["fc"] - layers[0]["pwp"])
                      if layers[0]["fc"] > layers[0]["pwp"] else 1.0)
            sixpool_state["n_min"] = nstate["n_nh4"] + nstate["n_no3"]
            sixpool_state["n_conc1"] = n_conc_layer1(layers, nstate["n_nh4"], no3_layers, nstate["n_no3"])
            sixpool_state["n_conc_layers"] = n_conc_layers(layers, nstate["n_nh4"], no3_layers, nstate["n_no3"])
            _dn0 = len(SIXPOOL_DIAG) if SIXPOOL_DIAG is not None else 0
            _DIAG_CTX["doy"] = w["doy"]
            sixpool_state["wx_day"] = (w["tx"], w["tn"], w["pp"])
            _smin = sixpool_step(sixpool_state, tmean, relwet, 0.0, 1.0, layers)
            if SIXPOOL_DIAG is not None and DIAG_NFLUX is not None:
                _new = SIXPOOL_DIAG[_dn0:]
                _gross = (sum(e[5] * 1000 / SIXPOOL_CN_CM + e[0] * 1000 / SIXPOOL_CN_CS for e in _new),                      # released from microbes and soil organic matter
                          sum(e[6] * 1000 / SIXPOOL_CN_CRA + e[7] * 1000 / SIXPOOL_CN_CRTZ for e in _new),                     # released from residue
                          sum(e[8] * 1000 / SIXPOOL_CN_CM + e[9] * 1000 / SIXPOOL_CN_CS for e in _new),                        # immobilized into microbes and soil organic matter
                          sum(e[6] + e[7] for e in _new))                                                                        # residue carbon decomposed (Mg C/ha)
            else:
                _gross = (0.0, 0.0, 0.0, 0.0)
            if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("netmin", ()):
                _smin = _FORCE_CUR["netmin"][w["doy"]]   # diagnostic: Cycles' own net mineralization flux in the fallow windows too
            nstate["n_nh4"], nstate["n_no3"] = apply_net_min(nstate["n_nh4"], nstate["n_no3"], no3_layers, _smin, sixpool_state)
        nit = nitrification_flux_ratio(nstate["n_nh4"], (no3_layers[0] if no3_layers is not None else nstate["n_no3"]), nstate["tsoil_lag"], layers[0]["theta"] / layers[0]["sat"], layers[0])
        vol = (volatilization_flux(nstate["tsoil_lag"], nstate["n_nh4"], layers[0], w["wind"], layers[0].get("ph"))
               if model_volatilization and VOLAT_MACNACK_PH is None else 0.0)
        nstate["n_nh4"] = max(0.0, nstate["n_nh4"] - nit - vol)
        nstate["n_no3"] += nit
        if no3_layers is not None:
            no3_layers[0] += nit
        nstate["n2o"] = nstate.get("n2o", 0.0) + n2o_from_nitrification(nit, layers[0]["theta"] / layers[0]["sat"])
        volat += vol
        profile_water_mm = sum(l["theta"] * l["thick"] * 1000 for l in layers)
        if no3_layers is None and profile_water_mm > 0 and nstate["n_no3"] > 0 and drainage_mm > 0:
            lost = min(nstate["n_no3"], drainage_mm * (nstate["n_no3"] / profile_water_mm))
            nstate["n_no3"] -= lost
            leached += lost
        if model_denitrification and sixpool_state is not None and no3_layers is not None:
            _no3_pre = nstate["n_no3"]
            _dl = denitrification_layers(_dn_no3_0, _dn_th0, layers, sixpool_state, no3_layers) if DENIT_STARTDAY else None
            d = (sum(_dl) if DENIT_STARTDAY else
                 denitrification_flux_resp(_no3_pre, (_SUBDAY_REL1_EFF if (SUBDAY_DENIT and _SUBDAY_REL1_EFF is not None) else layers[0]["theta"] / layers[0]["sat"]), sixpool_state.get("resp_mg_ha", 0.0)))
            if DIAG_DENIT is not None: DIAG_DENIT.append((_DIAG_YEAR, w["doy"], (_SUBDAY_REL1_EFF if (SUBDAY_DENIT and _SUBDAY_REL1_EFF is not None) else layers[0]["theta"] / layers[0]["sat"]), _no3_pre, sixpool_state.get("resp_mg_ha", 0.0), d, layers[0]["theta"] / layers[0]["sat"], tuple(no3_layers)))
            if d > 0 and _no3_pre > 0:
                if DENIT_STARTDAY:
                    for _i, _x in enumerate(_dl):
                        no3_layers[_i] -= _x
                else:
                    _f = d / _no3_pre
                    for i in range(len(no3_layers)):
                        no3_layers[i] *= (1.0 - _f)
                nstate["n_no3"] = max(0.0, _no3_pre - d)
                nstate["n2o"] = nstate.get("n2o", 0.0) + n2o_from_denitrification(d, _dn_no3_0[0] / (sixpool_bulk_density(layers[0]["sat"]) * layers[0]["thick"] * 10.0), _dn_th0[0] / layers[0]["sat"], layers[0], sixpool_state.get("resp_mg_ha", 0.0), sixpool_state.get("clay", 0.25))
                denit += d
        elif model_denitrification:
            # first fallow window of a run: the six-pool state does not exist yet, so the older layer-1 rate law acts (to be replaced by initializing the six-pool state first)
            if no3_layers is None:
                raise ValueError("denitrification needs per-layer nitrate")
            _no3_pre = nstate["n_no3"]
            d = no3_layers[0] * denitrification_rate_rel(layers[0]["theta"] / layers[0]["sat"], nstate["tsoil_lag"]) * _denit_depth_factor(layers)
            nstate["n2o"] = nstate.get("n2o", 0.0) + n2o_from_denitrification(d, _dn_no3_0[0] / (sixpool_bulk_density(layers[0]["sat"]) * layers[0]["thick"] * 10.0), _dn_th0[0] / layers[0]["sat"])
            no3_layers[0] -= d
            nstate["n_no3"] = max(0.0, nstate["n_no3"] - d)
            denit += d
        if DIAG_NFLUX is not None:
            DIAG_NFLUX.append((_DIAG_YEAR, w["doy"], locals().get("_smin", 0.0), nit, vol, locals().get("d", 0.0)) + tuple(locals().get("_gross", (0.0, 0.0, 0.0))))
        nstate["n_no3"], nstate["n_nh4"] = _npool_hook(no3_layers, nstate["n_no3"], nstate["n_nh4"], w["doy"])
    return leached, denit, volat


def _season_chain(weather_by_year, year_range, crop, plant_window, plant_min_soil_t, carry_n, initial_mineral_n, season_kwargs, cover=None, year_plan=None):
    """Shared engine of simulate_season_with_leadin() and simulate_continuous(): yields (year, result) for each year in
    year_range, carrying soil water, mineral N and six-pool carbon forward between years.
    cover (2026-10-21): optional dict(crop=, plant_doy=, kill_doy=), a cover crop planted on plant_doy after the main crop's harvest and killed on kill_doy of
    the next year, simulated as its own season on the shared soil (needs carry_n). Its residue and root carbon go to the six-pool state, its N uptake and
    water use come out of the same layers; its season losses are added to the year it ends in, and result["cover"] holds its biomass and N at kill."""
    if cover is not None and not carry_n:
        raise ValueError("a cover crop needs carry_n (shared mineral N state)")
    cover_planted = False
    result = None
    layers = None
    nstate = None
    sixpool_state = None
    for y in year_range:
        d = weather_by_year[y]
        doys = sorted(d)
        tsoil = simulate_soil_temp([(d[k]["tx"] + d[k]["tn"]) / 2 for k in doys], k=0.15)
        _yp = (year_plan or {}).get(y, {})   # 2026-10-23: optional per-year plan {year: dict(crop=, plant_doy=, kw={season kwargs overrides})}; None = unchanged behaviour
        ycrop = _yp.get("crop", crop)
        plant_doy = _yp.get("plant_doy") or find_planting_doy(dict(zip(doys, tsoil)), plant_window, plant_min_soil_t)
        rows = [d[k] for k in range(plant_doy, 300) if k in d]
        _spin0 = 1
        _cover_res = None
        global _FORCE_CUR, _DIAG_YEAR
        _FORCE_CUR = FORCE_SERIES.get(y) if FORCE_SERIES else None
        _DIAG_YEAR = y
        kw = dict(_yp["kw_replace"]) if "kw_replace" in _yp else dict(season_kwargs)   # kw_replace: a crop path with its own kwargs (soybean has no N model)
        kw.update(_yp.get("kw", {}))
        if "wue_co2_scale" not in kw:
            kw["wue_co2_scale"] = (CO2_PPM_BY_YEAR.get(y, CO2_REF_PPM) / CO2_REF_PPM) ** ycrop.get("wue_co2_exp", WUE_CO2_EXP)
        if "rue_co2_scale" not in kw:
            kw["rue_co2_scale"] = (CO2_PPM_BY_YEAR.get(y, CO2_REF_PPM) / CO2_REF_PPM) ** ycrop.get("rue_co2_exp", RUE_CO2_EXP)
        if layers is None:
            layers = crop["make_layers"]()
        fallow_tot = [0.0, 0.0, 0.0]
        de_state = dict(de=0.0, tew=compute_tew(layers[0]["fc"], layers[0]["pwp"]), rew=REW_DEFAULT_MM)
        if cover is not None and cover_planted and nstate is not None and (y - 1) in weather_by_year:
            _dp = weather_by_year[y - 1]
            _rye_rows = [_dp[k] for k in range(cover["plant_doy"], 367) if k in _dp] + [d[k] for k in range(1, cover["kill_doy"]) if k in d]
            _kwc = {k: v for k, v in kw.items() if k not in ("n_rate_kg_ha", "n_applications", "fertilizer_source", "n_credit_kg_ha", "manure_n_kg_ha", "initial_n_state", "sixpool_initial_state")}
            _kwc["n_rate_kg_ha"] = 0
            _ns = dict(nstate); _ns.pop("n2o", None)
            _kwc.update(initial_n_state=_ns, initial_layers=layers, spinup_rows=None)
            if sixpool_state is not None:
                _kwc["sixpool_initial_state"] = sixpool_state
            _cover_res = simulate_season(_rye_rows, cover["crop"], **_kwc)
            layers = _cover_res["final_layers"]
            nstate = dict(_cover_res["final_n_state"])
            sixpool_state = copy.deepcopy(_cover_res["sixpool_final_state"]) if "sixpool_final_state" in _cover_res else None
            fallow_tot = [_cover_res.get("n_leached_kg_ha", 0.0), _cover_res.get("n_denitrified_kg_ha", 0.0), _cover_res.get("n_volatilized_pool_kg_ha", 0.0)]
            _spin0 = cover["kill_doy"]
            de_state = dict(de=0.0, tew=compute_tew(layers[0]["fc"], layers[0]["pwp"]), rew=REW_DEFAULT_MM)
        spinup = [d[k] for k in range(_spin0, plant_doy) if k in d]
        if carry_n:
            if nstate is None:
                _nh4_0 = initial_mineral_n["nh4"] if initial_mineral_n else 0.0
                _no3_0 = list(initial_mineral_n["no3_layers"]) if initial_mineral_n else [0.0] * len(layers)
                nstate = dict(n_nh4=_nh4_0, n_no3=sum(_no3_0), tsoil_lag=(rows[0]["tx"] + rows[0]["tn"]) / 2.0,
                              no3_layers=(_no3_0 if kw.get("nitrate_per_layer") else None))
            lch, dn, vl = run_fallow_n_window(layers, spinup, nstate, sixpool_state, lat_deg=crop["lat_deg"], curve_number=season_kwargs.get("curve_number", 75.0), slope_pct=season_kwargs.get("slope_pct", 0.0),
                                              de_state=de_state,
                                              model_denitrification=kw.get("model_denitrification", True),
                                              model_volatilization=kw.get("model_volatilization", True))
            fallow_tot = [fallow_tot[0] + lch, fallow_tot[1] + dn, fallow_tot[2] + vl]
            n2o_pre = nstate.pop("n2o", 0.0) + (_cover_res.get("n2o_emitted_kg_ha", 0.0) if _cover_res is not None else 0.0)
            kw["initial_n_state"] = dict(nstate)
            if sixpool_state is not None:
                kw["sixpool_initial_state"] = sixpool_state
            result = simulate_season(rows, ycrop, spinup_rows=None, initial_layers=layers, **kw)
        else:
            result = simulate_season(rows, ycrop, spinup_rows=spinup, initial_layers=layers, **kw)
        result["plant_doy"] = plant_doy
        layers = result["final_layers"]
        last = result.get("last_doy") or 299
        _bridge_end = (cover["plant_doy"] if cover is not None else 367)
        cover_planted = cover is not None and last < cover["plant_doy"]
        bridge = [d[k] for k in range(last + 1, _bridge_end) if k in d] if carry_n else [d[k] for k in range(301, 367) if k in d]
        de_state = dict(de=0.0, tew=compute_tew(layers[0]["fc"], layers[0]["pwp"]), rew=REW_DEFAULT_MM)
        if carry_n:
            if "final_n_state" in result:
                nstate = dict(result["final_n_state"])
                sixpool_state = copy.deepcopy(result["sixpool_final_state"]) if "sixpool_final_state" in result else None
            else:   # a crop path without an N model (soybean): the mineral N and carbon state pass through the year unchanged
                nstate = dict(nstate); nstate.pop("n2o", None)
            lch, dn, vl = run_fallow_n_window(layers, bridge, nstate, sixpool_state, lat_deg=crop["lat_deg"], curve_number=season_kwargs.get("curve_number", 75.0), slope_pct=season_kwargs.get("slope_pct", 0.0),
                                              de_state=de_state,
                                              model_denitrification=kw.get("model_denitrification", True),
                                              model_volatilization=kw.get("model_volatilization", True))
            fallow_tot = [fallow_tot[0] + lch, fallow_tot[1] + dn, fallow_tot[2] + vl]
            result["fallow_n_leached"], result["fallow_n_denitrified"], result["fallow_n_volatilized"] = fallow_tot
            result["fallow_n2o"] = n2o_pre + nstate.pop("n2o", 0.0)
            result["end_n_state"] = dict(nstate)
            if _cover_res is not None:
                result["cover"] = dict(ag=_cover_res["ag"], total=_cover_res["total"], n_uptake=_cover_res.get("n_uptake_kg_ha", 0.0), n_leached=_cover_res.get("n_leached_kg_ha", 0.0))
        else:
            run_bare_fallow_window(layers, bridge, lat_deg=crop["lat_deg"], curve_number=season_kwargs.get("curve_number", 75.0), slope_pct=season_kwargs.get("slope_pct", 0.0), de_state=de_state)
        yield y, result


def simulate_season_with_leadin(weather_by_year, year, crop, lead_years=2, plant_window=(110, 131),
                                plant_min_soil_t=12.0, carry_n=False, initial_mineral_n=None, **season_kwargs):
    """Runs one target season preceded by `lead_years` real prior seasons of the SAME crop and
    management, carrying real soil-water state forward (initial_layers/final_layers plus a bare-
    fallow bridge from the last simulated day to year end), instead of resetting every layer to 50%
    of plant-available water each January. Found 2026-10-02 (run_validation_multisite.py, 16 CONUS
    sites vs native Cycles v1.4.4): Cycles carries deep-layer water across years, so a fresh start
    per year starves sandy and dry sites (Carolina 2.3 vs Cycles 9.2 Mg/ha at 150 kg N). N=150
    mean abs error across 16 sites: 1.95 (fresh) -> 1.38 (1 lead year) -> 1.31 (2 lead years) ->
    1.31 (full 37-year chain), so two prior years capture the whole effect at 3x the compute.

    carry_n=True (requires nh4_no3_split=True and background_n_model='sixpool' in season_kwargs)
    ALSO carries the standing NH4/NO3 pools and the six-pool carbon state between seasons and runs
    run_fallow_n_window() over the Jan-1-to-planting and harvest-to-Dec-31 gaps, so nitrate keeps
    forming and being lost off-season the way it does in Cycles. weather_by_year is
    {year: {doy: row}}. Returns the target year's simulate_season() result (plant_doy added; with
    carry_n also fallow_n_leached/fallow_n_denitrified/fallow_n_volatilized for the target year's
    own off-season windows). Years before the first available weather year are skipped, so early
    years just get fewer lead years."""
    result = None
    first = min(weather_by_year)
    for _y, result in _season_chain(weather_by_year, range(max(first, year - lead_years), year + 1), crop, plant_window,
                                    plant_min_soil_t, carry_n, initial_mineral_n, season_kwargs):
        pass
    return result


FORCE_SERIES = None   # module-swap diagnostic (2026-10-14): {year: {"canopy": {doy: v}, "water": {doy: mult}, "nstress": {doy: mult}}} from Cycles' own daily output; None = off
_FORCE_CUR = None
DIAG_AG = None   # diagnostics: appends aboveground biomass (Mg/ha) in step with DIAG_BIO
DIAG_BIO = None   # diagnostics: appends total biomass (Mg/ha, after the day's growth) in step with DIAG_STATE
DIAG_EVAP = None   # appends (year, doy, soil evaporation mm, residue evaporation mm, ETo, residue cover) per in-season day; None = off
DIAG_WATER = None   # appends (year, doy, water stress multiplier, thermal time) per day; None = off
DIAG_DRAIN = None   # appends (year, drainage mm, nitrate leached kg/ha) per infiltrate() call; None = off
DIAG_STATE = None   # state_calibration.py: appends (year, doy, canopy, n_stress, plant_n_kg_ha) per day; None = off
_DIAG_YEAR = None
THETA_FORCE = None   # rebuild phase 2 (2026-10-16): {year: {doy: [theta per layer]}} from Cycles' dailyWater; when set, end-of-day layer moisture is overwritten with Cycles' value in every window (spin-up, season, fallow)
NPOOL_FORCE = None   # rebuild phase 4 diagnostic: {year: {doy: (profile NO3, profile NH4 kg/ha)}} from Cycles' dailyN; overwrites the engine's mineral-N pools at end of day in every window


DIAG_NFLUX = None   # appends (year, doy, net mineralization, nitrification, volatilization, denitrification) per fallow-window day (kg N/ha); None = off
CFORCE = None   # {(year, doy): {'surface': Mg C/ha, 'layers': {i: (cs, cm, crtz)}}} start-of-day carbon pools from Cycles; None = off
CFORCE_LOG = None
DIAG_CPOOL = None   # appends (year, doy, [Cs per layer], [Cm per layer], [root residue C per layer], surface residue C) after each day's ml step; None = off
CFORCE_WHICH = ()   # subset of ('surface', 'cs', 'cm', 'root') to force
DIAG_FE = None   # appends (year, doy, layer, layer temperature, relative wetness, fE) per layer per day in sixpool_ml_step; None = off
_DIAG_CTX = {}
DIAG_NSEASON = None   # appends (year, doy, net mineralization, nitrification, volatilization, denitrification, nitrate leached, uptake, mineral pool at end of day) per in-season day (kg N/ha); None = off
NLAYER_FORCE = None   # diagnostic 2026-10-19: {year: {doy: ([nitrate kg/ha per layer], ammonium kg/ha)}} from Cycles' dailySoilLayersCN and dailyN; sets the engine's layer nitrate and ammonium at the end of every day (laws then act on Cycles' own state)
DIAG_NPOOL = None   # appends (year, doy, nitrate kg/ha, ammonium kg/ha) at the end of every simulated day (fallow and in-season); None = off
def _npool_hook(no3_layers, n_no3, n_nh4, doy):
    if DIAG_NPOOL is not None:
        DIAG_NPOOL.append((_DIAG_YEAR, doy, (sum(no3_layers) if no3_layers is not None else n_no3), n_nh4))
    if NLAYER_FORCE is not None and no3_layers is not None:
        s = NLAYER_FORCE.get(_DIAG_YEAR)
        if s is not None and doy in s:
            lay, nh4 = s[doy]
            for i in range(len(no3_layers)):
                no3_layers[i] = lay[i] if i < len(lay) else 0.0
            return sum(no3_layers), nh4
    if NPOOL_FORCE is not None and no3_layers is not None:
        s = NPOOL_FORCE.get(_DIAG_YEAR)
        if s is not None and doy in s:
            no3, nh4 = s[doy]
            tot = sum(no3_layers)
            if tot > 1e-9:
                for i in range(len(no3_layers)):
                    no3_layers[i] *= no3 / tot
            else:
                no3_layers[0] = no3
            return no3, nh4
    return n_no3, n_nh4


SUBDAY_DENIT = True  # denitrification reads the within-day time-weighted layer-1 saturation (rebuild step 1, 2026-10-16)
_SUBDAY_REL1_EFF = None
DIAG_SUBDAY = None   # sub-daily saturation diagnostic (list of per-call step records)
DIAG_RESP = None     # rebuild phase 4: list of (year, respired C Mg/ha, net N mineralized kg/ha) per six-pool day
DIAG_THETA = None    # rebuild phase 2: when a list, appends (year, doy, [theta per layer]) at end of every simulated day, so the daily layer water state can be scored against Cycles


DIAG_NO3 = None   # appends (year, doy, [nitrate kg/ha per layer]) per simulated day (per-layer nitrate mode only); None = off
def _water_hook(layers, doy, no3_layers=None):
    if THETA_FORCE is not None:
        s = THETA_FORCE.get(_DIAG_YEAR)
        if s is not None and doy in s:
            for l, t in zip(layers, s[doy]):
                l["theta"] = t
    if DIAG_THETA is not None:
        DIAG_THETA.append((_DIAG_YEAR, doy, [l["theta"] for l in layers]))
    if DIAG_NO3 is not None and no3_layers is not None:
        DIAG_NO3.append((_DIAG_YEAR, doy, list(no3_layers)))
DIAG_GROWTH = None   # temporary diagnostic list (floor_growth.py): appends (doy, GR, GT, dGB_water_limited) per day; None = off


def standard_kwargs(soil_raw, n_rate_kg_ha):
    """THE standard configuration (rebuild phase 1, 2026-10-16): the one flag set the scorecard scores and the release will ship.
    Previously this lived inline in run_validation_multisite.py while the pages ran bare defaults, so the scored and the shipped
    engine were different objects. Callers add only their own inputs (crop, weather); nothing here is crop-specific."""
    kw = dict(n_rate_kg_ha=n_rate_kg_ha, nh4_no3_split=True, model_denitrification=True, model_volatilization=True,
              background_n_model="sixpool", sixpool_topsoil_clay_pct=soil_raw[0]["clay"], sixpool_topsoil_soc_pct=soil_raw[0]["soc"],
              sixpool_profile_raw=soil_raw, nitrate_per_layer=True, sixpool_per_layer=True)
    if n_rate_kg_ha and n_rate_kg_ha > 0:
        kw["fertilizer_source"] = "uan"
    return kw


def simulate_continuous(weather_by_year, crop, years=None, plant_window=(110, 131), plant_min_soil_t=12.0, carry_n=False,
                        initial_mineral_n=None, cover=None, year_plan=None, **season_kwargs):
    """One continuous multi-year run from the first weather year (or years[0]), the way Cycles runs a 1980-2016 simulation:
    soil water, mineral N and carbon carry across every year with no re-start. Returns {year: result}. Each year costs one
    season, where simulate_season_with_leadin(lead_years=full) re-runs the whole history for every target year."""
    yrs = sorted(weather_by_year) if years is None else list(years)
    out = {}
    for y, r in _season_chain(weather_by_year, yrs, crop, plant_window, plant_min_soil_t, carry_n, initial_mineral_n, season_kwargs, cover=cover, year_plan=year_plan):
        out[y] = r
    return out

def simulate_season(weather_rows, crop, root_max_m=1.4, harvest_ttf=1.0, n_rate_kg_ha=None, record_history=False,
                     n_applications=None, n_credit_kg_ha=0.0, manure_n_kg_ha=0.0, manure_availability=0.5,
                     manure_source=None,
                     irrigation_trigger_frac=None, irrigation_amount_mm=25.0, irrigation_refill_layers=None, irrigation_window=(1, 366), irrigation_events=None,
                     tillage_doy=None, tillage_implement=None, tillage_clay_frac=0.21, tillage_mix_texture=True,
                     fert_placement_implement=None, soil_ph=None,
                     spinup_rows=None, curve_number=75.0, slope_pct=0.0, initial_layers=None,
                     soil_evap_model="faostandard", n_root_limited=False, wue_co2_scale=1.0, rue_co2_scale=1.0,
                     background_n_model="rothc", sixpool_topsoil_clay_pct=None, sixpool_topsoil_soc_pct=None,
                     sixpool_initial_state=None, sixpool_offseason_decay=False,
                     model_denitrification=False, nh4_no3_split=False, model_volatilization=False,
                     fertilizer_source=None, sixpool_profile_raw=None, sixpool_per_layer=False, initial_n_state=None,
                     nitrate_per_layer=False):
    """weather_rows: dicts with doy, tx, tn, solar, rhx, rhn, wind, pp, in planting-day order.

    model_denitrification: False by default (byte-identical to this parameter not existing --
    this engine had NO denitrification pathway at all before 2026-10-02). When True and
    nitrogen tracking is active, applies denitrification_rate()'s real, back-calculated daily
    loss to the standing mineral-N pool each day, driven by that day's own topsoil moisture --
    see denitrification_rate()'s own docstring for the derivation and its disclosed limits.

    nh4_no3_split: False by default (byte-identical to this parameter not existing). When True
    and nitrogen tracking is active with n_root_limited=False (the two aren't combined -- see
    below), replaces the single lumped mineral-N pool with two real sub-pools, NH4 and NO3,
    linked by nitrification_rate()'s own real, back-calculated temperature-driven daily
    conversion. Background mineralization and previous-crop credit/manure land entirely in the
    NH4 pool, matching how those forms actually enter the soil (organic-matter mineralization
    is ammonification, NH4 first, by definition; manure_availability/manure_source already
    represent the immediately-available, NH4-equivalent portion specifically). Dated/single-
    lump mineral fertilizer applications split between NH4 and NO3 per fertilizer_source (see
    its own docstring below) when given -- 100% NH4 otherwise (the historical assumption,
    correct for several real products like urea/anhydrous ammonia, but not universal: real
    UAN, for instance, arrives already 25% NO3, confirmed directly against Cycles' own
    ContinuousCorn.operation).
    Denitrification (model_denitrification) and leaching both draw from the NO3 pool only --
    found directly in Cycles' own real daily output (N.txt) that NH4 leaching is under 1% of
    total leaching across the full 37-year Rock Springs record (NO3 43.18 kg/ha vs. NH4 0.39
    kg/ha, cumulative), i.e. real Cycles treats NH4 as essentially non-leachable, consistent
    with real soil chemistry (NH4+ is a cation held by the soil's own cation-exchange capacity;
    NO3- is the mobile anion). Crop uptake draws from both pools together (plants take up
    either form), split proportionally to each pool's current size for bookkeeping. Before
    this, every loss pathway (denitrification, leaching) applied to the SAME lumped pool as a
    disclosed simplification -- most consequentially, freshly-applied fertilizer N (still
    almost entirely NH4, not yet nitrified) was treated as immediately as leachable as
    long-standing NO3, which real Cycles' own output shows it isn't. Mutually exclusive with
    n_root_limited (the per-layer nitrogen-tracking path) -- if both are set, nh4_no3_split is
    silently ignored and the old lumped-pool-by-layer mechanism runs unchanged, since that path
    is itself a separate, already-opt-in, not-default-validated mechanism not worth compounding
    two large changes into at once. See MECHANISM_LOG.md's 2026-10-02 entry for the full
    derivation and the real leaching-split evidence.

    model_volatilization: False by default (byte-identical to this parameter not existing).
    When True and nh4_no3_split is also active (it does nothing otherwise -- there's no real
    NH4 pool for it to act on without the split), applies volatilization_flux()'s,
    back-calculated daily ammonia loss directly to the standing NH4 pool each day, driven by
    that day's own topsoil temperature (the same tsoil_lag state nitrification already tracks).
    This is a different, better-grounded mechanism than fert_placement_implement/soil_ph above:
    those model volatilization as a one-time percentage lost at the single moment of
    application; this models it as the real, continuous, temperature-gated process it actually
    is, competing day by day with nitrification for the same NH4 pool (nitrified NH4 becomes
    NO3 and is no longer exposed to this loss pathway at all). See volatilization_flux()'s own
    docstring for the full derivation against real Cycles output, and MECHANISM_LOG.md's
    2026-10-02 entry for the comparison against the two prior mechanisms' real overestimate.
    Not mutually exclusive with fert_placement_implement/soil_ph in code (nothing stops a
    caller from setting both), but doing so would double-count the same real loss against two
    different approximations of it -- documented here as a real risk to avoid, not guarded by
    an exception, matching this engine's existing pattern for its other opt-in combinations.

    fertilizer_source: None by default (byte-identical to this parameter not existing -- every
    mineral application still lands 100% in NH4, the original assumption). When given a real
    key from MINERAL_SOURCES (uan/urea/anhydrous_ammonia/ammonium_nitrate/etc., parsed from the
    same Cycles v1.4.4 fert.txt catalog MANURE_SOURCES already mines -- see MINERAL_SOURCES'
    own comment for the full derivation), splits every mineral-fertilizer dose (the n_rate_kg_ha
    single lump, or each n_applications event) into its real NH4/NO3 fractions at the moment it
    lands, instead of assuming 100% NH4. Only meaningful alongside nh4_no3_split -- raises
    ValueError for an unrecognized key regardless, since a silent no-op on a typo'd source name
    would be worse than failing loudly. Found and fixed 2026-10-02, directly asked for after
    comparing this engine's own NH4 trajectory against Cycles' real PROF SOIL NH4 column
    uncovered that 100%-NH4 was never universally true -- see MECHANISM_LOG.md's
    2026-10-02 entries for the full account, including why this alone doesn't resolve the
    larger volatilization-rate gap that comparison was built to investigate (see
    volatilization_flux() docstring).

    background_n_model: "rothc" (default, byte-identical to this parameter not existing) keeps
    the existing RothC-weather-scaled flat-constant background-nitrogen mechanism. "sixpool"
    switches to the real two-pool (Cm, Cs) carbon-mineralization mechanism built 2026-10-01 --
    see sixpool_step()'s own docstring above for the full structure, and CLAUDE.md/
    MECHANISM_LOG.md for why it's opt-in, not the default, and what's still a disclosed
    placeholder in it. Requires sixpool_topsoil_clay_pct and sixpool_topsoil_soc_pct (the same
    real topsoil texture/SOC inputs a caller's own make_layers() already used to build
    layers[0] -- not re-derivable from the layers dict alone, which doesn't retain them).

    sixpool_initial_state: mirrors initial_layers' own real multi-year carryover pattern, but
    for the six-pool carbon state specifically rather than soil moisture -- a caller's own
    prior season's "sixpool_final_state" (from the result dict), fed back in as this season's
    own starting Cs/Cm/Cra/Crtz instead of always reinitializing fresh from soc%/clay%. None
    (the default) reproduces the exact existing single-season behavior. Only meaningful when
    background_n_model="sixpool"; ignored otherwise. Built 2026-10-01 specifically to test
    whether real multi-year carbon-pool persistence -- already the single most reliable lever
    this engine has found for soil-moisture state (see initial_layers' own docstring) -- also
    closes the one gap that's shown up at every site tested for the fresh-start six-pool
    mechanism: real year-to-year variation in which years are more or less nitrogen-limited is
    not captured by a pool that resets to the same starting guess every season. See
    MECHANISM_LOG.md for the actual chained-multi-year test and its result.

    sixpool_offseason_decay (default False, byte-identical when unused -- this never changes
    any already-shipped result, including wheat's own 0.490 validated correlation, which
    passes spinup_rows but was never asked to carry carbon state across years): when True
    (and background_n_model="sixpool"), the real spinup_rows window also drives real day-by-
    day Cra/Crtz/Cm/Cs decomposition (sixpool_step() itself, called with zero root-carbon
    input, no new formula needed) using that window's own real weather and this season's own
    evolving topsoil moisture -- the real fix for a problem found testing sixpool_initial_state
    chained across Iowa's full 37-year record WITHOUT this: with no off-season decomposition
    at all, a season's own harvested stover (credited into next season's Cra at the end of
    THIS function, unconditionally, see below) would carry forward completely undecomposed,
    which overshot the real nitrogen-saturation pattern just as badly as the original fresh-
    start mechanism undershot it (relative yield pinned at 1.0 every year). Real, disclosed
    limitation: spinup_rows only ever covers Jan1-through-planting in this project's own
    harnesses, not the real harvest-to-Dec31 tail of the actual off-season -- so this still
    underestimates total real decomposition time, a known, stated gap, not a hidden one.

    wue_co2_scale: a flat multiplier on the crop's water-use efficiency (eps_W in Eq. 5),
    representing rising atmospheric CO2's real effect on stomatal water-use efficiency.
    Disclosed directly by Kemanian et al. 2024 Sec. 2.5 ("Both eps_R and eps_W should be given
    for a reference atmospheric CO2 concentration and scaled accordingly as CO2 changes... For
    a discussion on the implications of optimization theory under changing CO2 see Bassiouni

    wue_co2_scale: a flat multiplier on the crop's water-use efficiency (eps_W in Eq. 5),
    representing rising atmospheric CO2's real effect on stomatal water-use efficiency.
    Disclosed directly by Kemanian et al. 2024 Sec. 2.5 ("Both eps_R and eps_W should be given
    for a reference atmospheric CO2 concentration and scaled accordingly as CO2 changes... For
    a discussion on the implications of optimization theory under changing CO2 see Bassiouni
    and Vico (2021)"), but the paper gives no exact scaling formula itself -- found 2026-10-01
    hunting for why real Cycles' own 37-year corn record shows a real, substantial rising yield
    trend (verified independent of CO2 itself via a real experiment: reran the actual Cycles
    binary with a flat 1980-level CO2 input, the trend barely moved) that this engine's GR/GT
    growth minimum didn't reproduce at all (model's own biomass trend ~0 vs real +0.10 Mg/ha/
    year) -- real Rock Springs weather genuinely warmed, got sunnier, AND got drier (rising
    VPD) over 1980-2016, and GT = eps_W/sqrt(Da)*TR_actual falls as VPD rises even as GR rises
    with solar, canceling most of the real trend in this engine specifically.

    The exact functional form (WUE proportional to CO2, not eps_R) comes from Bassiouni & Vico
    (2021, New Phytologist) itself, per a search-result summary of their stomatal-optimization
    result ("instantaneous transpiration efficiency should be proportional to atmospheric CO2
    concentration... approximately inversely proportional to the square root of leaf-to-air
    VPD") -- not a direct primary-source read (WebFetch is blocked for this sandbox's egress
    policy the same way it's blocked everywhere else in this project), flagged as such. eps_R
    (radiation use efficiency) is deliberately NOT scaled with CO2 here -- the well-established
    C4 literature (e.g. Leakey 2009) shows negligible photosynthetic/RUE response to CO2 for
    C4 crops like corn under non-drought conditions, since C4 photosynthesis is already CO2-
    saturated; only the stomatal/WUE pathway (general to C3 and C4 alike, per Bassiouni & Vico's
    own theory) is implemented.

    The reference CO2 concentration this scale is computed AGAINST (CO2_REF_PPM below) is this
    project's own calibration choice, not a value either source specifies -- chosen as this
    engine's own 1980-2016 Rock Springs validation-period mean (368.3 ppm) so that, averaged
    over the calibration record, the scaling nets to ~1.0 and each crop's existing
    calibration_factor still does its usual job of matching the mean, not absorbing a biased
    shift from an arbitrarily-chosen reference year.

    Verified against all four validated crops before shipping (corn's own real cold-kill-era
    baseline, see run_validation.py's calibration_factor comment, for exact before/after
    numbers): corn 0.691->0.777 and winter wheat 0.337->0.458 (real, substantial wins -- the
    second-largest single-mechanism correlation gain either crop has gotten this project, after
    cold-kill); soybean 0.9545->0.9471 (negligible, within noise); silage corn 0.2035->0.1170
    (a real cost, but silage corn's correlation is unreliable either way, both numbers far below
    the classroom-workable bar on an already-small 13-point sample). Also checked against the
    independent Kansas 37-year corn benchmark (real Cycles output, /tmp/cycles-run/output/
    KansasN150): 0.7757->0.7577, a small cost, consistent with Kansas's own accuracy gap being
    dominated by a different, already-diagnosed problem (root-zone water access), not this
    secular-trend issue. wue_co2_scale=1.0 (the default) reproduces every existing validated
    number byte-for-byte -- confirmed directly before any harness was changed to pass it.
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

    manure_source: optional real manure species key from MANURE_SOURCES (dairy/beef/veal/swine/
    sheep/goat/horse/chicken/turkey, parsed from Cycles v1.4.4's own bundled fert.txt -- see
    MANURE_SOURCES' own comment for the full account) -- raises ValueError for an unrecognized
    name. When given, OVERRIDES manure_availability with that species' real immediate (N_NH4)
    fraction of total N, rather than the flat 0.5 literature-disclosed default every manure
    application has used until now regardless of species. None (default) leaves
    manure_availability exactly as passed, byte-identical to pre-existing behavior -- verified
    directly. Real, disclosed limitation kept honest rather than quietly extended past what's
    actually modeled: each species' remaining organic-N fraction (norg_frac in MANURE_SOURCES)
    is NOT fed into any mineralization pathway here -- it is simply unavailable for the
    season, the same simplification this engine's flat-0.5 default already made for the whole
    manure amount, just now applied only to the genuinely slow-release portion instead of half
    of everything. A real eventual mineralization of that organic fraction (e.g. routed through
    the existing RothC-scaled background-N pathway) would need its own separate, deliberate
    build, not assumed free from this change.

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
    Nitrogen adequacy (2026-09-25, replacing the season-total quadratic-plateau this engine
    used from 2026-09-14 through 2026-09-25) is now a DAY-BY-DAY function of the plant's own
    actual tissue N concentration, matching a real mechanism found in CropSyst's own public
    source (crop/crop_N_common.cpp): N_reduction_factor = 1-(Ncrit-Nactual)/(Ncrit-Nmin),
    clipped to [0,1], with no limitation at all once Nactual reaches Ncrit. Ncrit(biomass) is
    the same real critical-N-dilution curve this engine already had (n_critical_pct(), from
    each crop's real N_MAX_CONCENTRATION/N_DILUTION_SLOPE); Nmin is each crop's real
    N_MIN_CONCENTRATION_STRAW value from GenericCrops.crop (a genuinely low, mostly-
    structural-tissue N floor -- 0.2% for corn/wheat/silage corn; not applicable/-999 for
    soybean, consistent with soybean's LEGUME exemption from N stress entirely). Both
    quantities are things this engine already tracks or already had real crop-file access
    to -- no new external dependency. This directly replaced the earlier day-by-day
    fertilizer-pool mechanic's own real failure mode (a hard, uncorrectable zero once the
    pool ran dry, producing an accelerating-then-cliff yield response instead of genuine
    diminishing returns) with something that fails the same way real plants do: gradually,
    as tissue concentration falls, not as a discrete pool-exhaustion event -- while also
    naturally reproducing genuine diminishing returns without needing an invented functional
    form (the old quadratic-plateau shape) layered on top to fake that behavior. Verified
    against real Cycles output before shipping: wheat (real Cycles' own dominant year-to-year
    driver is nitrogen, not water, -0.894 vs. 0.359 correlation with real max seasonal
    stress) improved 0.473 -> 0.523; corn tested with real nitrogen tracking under this same
    new mechanism scored 0.5095, essentially unchanged from the old mechanism's 0.5005 and
    still below the no-N-tracking default's 0.5495 -- confirming corn's already-established
    finding (real N stress correlates only weakly with real corn yield, -0.21) holds
    regardless of which N-stress mechanism is used, not an artifact of the old one's shape.
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
    that comparison this session (see MECHANISM_LOG.md item 6 for the full account,
    including a real test-harness bug that initially hid this finding and was caught and
    fixed before trusting it). Rock Springs' own 37-year validated record was NOT re-checked
    against a chained run before this was implemented -- carryover there would need the same
    real off-season weather (harvest day through next planting, spanning the calendar-year
    boundary) a caller must supply via spinup_rows, not something this function derives on
    its own.

    A caller chaining seasons must NOT pass the same crop dict's "make_layers" closure a
    shared, hand-built layers object the way this session's own early test scripts briefly
    did by mistake -- that let a since-removed internal precompute pass (an intentionally-
    independent, throwaway parallel trajectory used by the old season-total nitrogen-demand
    mechanism, see the comment above canopy_n_kg_ha below for why it's gone) mutate the same
    soil state the real main loop was also mutating, silently corrupting the result.
    initial_layers exists specifically so a caller never needs that workaround: this
    function deep-copies initial_layers internally before the main loop runs, so a caller's
    own object is never mutated regardless of what's passed in. When initial_layers is
    given, the result dict also carries
    "final_layers" -- the real ending soil state (theta, and any per-layer state a future
    mechanism might add), ready to feed into the next chained call's own initial_layers with
    no extraction step needed.

    soil_evap_model: UPDATED 2026-10-08 (the text here used to say CropSyst evaporation was "not the
    default" and "not validated"; both stopped being true on 2026-10-07). The module flag
    FORCE_CROPSYST_EVAP is True, which routes EVERY soil_evaporation() call (in-season, spin-up and
    fallow windows) through the CropSyst formula (soil_evaporation_cropsyst()) regardless of this
    parameter, so "faostandard" below is only reached when a caller sets FORCE_CROPSYST_EVAP = False
    (the embedded engines in engine-demo.html and model-validation.html do exactly that implicitly:
    they have no such flag and still run the FAO-56 Kr path). It was validated against Cycles on the
    16-site same-input table (N0 grain MAE 2.32 -> 2.03, Iowa net mineralization year-to-year
    correlation about 0.5 -> 0.9; see MECHANISM_LOG.md 2026-10-07). "faostandard" = the FAO-56
    Kr-based bare-soil evaporation mechanism (soil_evaporation()'s own default path); "cropsyst" = the
    fully-disclosed formula found 2026-09-28 (soil_evaporation_cropsyst()).

    n_root_limited (default False, byte-identical when unused): real CropSyst nitrogen uptake
    (Stockle, Martin & Campbell 1994, Eq. 26, already on disk as cropsyst.pdf) is "the minimum
    of crop nitrogen demand and potential nitrogen uptake," not demand alone -- this engine's
    existing mechanism only ever checked demand against the whole lumped n_pool, with no
    concept of a supply-side ceiling independent of total pool size. Cycles' own real Umax
    (max uptake per unit root length) isn't disclosed anywhere available to this project, so
    rather than invent that number, this builds the real STRUCTURAL insight a different, fully
    traceable way: nitrogen is tracked per SOIL LAYER (n_pool_by_layer, applications/background
    credit landing in the surface layer, transported downward in lockstep with real drainage
    via redistribute()'s own n_by_layer parameter -- see that function's docstring), and a
    day's potential uptake is capped at however much of the pool currently sits within reach of
    the crop's own real root_depth trajectory (layer_depth_fraction_within()) -- N that has
    leached below the roots genuinely can't be taken up that day, exactly the "root discovery"
    concept already fixed for water this session, applied to nitrogen for the first time. See
    MECHANISM_LOG.md for the four earlier, real, sourced angles on the Kansas nitrogen-
    response-muting problem that didn't work, and why this one was built instead."""
    layers = copy.deepcopy(initial_layers) if initial_layers is not None else crop["make_layers"]()
    root_max_m = crop.get("root_max_m", root_max_m)
    de_state = dict(de=0.0, tew=compute_tew(layers[0]["fc"], layers[0]["pwp"]), rew=REW_DEFAULT_MM)
    runoff_total = 0.0

    sixpool_state = None
    if background_n_model == "sixpool":
        if sixpool_initial_state is not None:
            sixpool_state = copy.deepcopy(sixpool_initial_state)  # never mutate the caller's own
            # object -- same discipline initial_layers already uses, see its own docstring.
        else:
            if sixpool_topsoil_clay_pct is None or sixpool_topsoil_soc_pct is None:
                raise ValueError("background_n_model='sixpool' requires sixpool_topsoil_clay_pct "
                                  "and sixpool_topsoil_soc_pct -- see simulate_season()'s own docstring.")
            if sixpool_per_layer and sixpool_profile_raw:
                sixpool_state = sixpool_ml_init(layers, sixpool_profile_raw)
            else:
              sixpool_state = sixpool_init_state(layers[0], sixpool_topsoil_clay_pct, sixpool_topsoil_soc_pct,
                                                depth_m=(sixpool_effective_depth_m(sixpool_profile_raw, sixpool_topsoil_soc_pct)
                                                         if sixpool_profile_raw else None))
        # Moved ahead of the spinup block above (2026-10-01) specifically so
        # sixpool_offseason_decay below can run during it -- see that parameter's own
        # docstring and MECHANISM_LOG.md for why.

    if spinup_rows:
        # A bare-soil (no canopy, no transpiration) water balance over real weather from
        # before the tracked season starts, replacing an always-reset-to-field-capacity
        # start -- see CLAUDE.md, 2026-09-22: a real Cycles vs. this-engine head-to-head at
        # a semi-arid site (western Kansas) showed an ~18x yield gap traced directly to this
        # assumption having no basis in a dry climate. Uses the SAME infiltrate() (now
        # runoff-aware) and soil_evaporation() the main loop uses, just with canopy_cover=0.
        for w in spinup_rows:
            if SNOW_MODEL:
                w = snow_adjust(layers, w, crop["lat_deg"])
            _rc = residue_cover_frac(sixpool_state)
            _eto0 = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
            _re, _rev = residue_water_today(sixpool_state, w["pp"], _rc, _eto0, 0.0, w.get("snow_day", False))
            _th1_0 = zone_mean_theta(layers)
            _, spin_runoff, _ = infiltrate(layers, w["pp"] - _re, curve_number, slope_pct)
            runoff_total += spin_runoff
            eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
            soil_evaporation(layers, eto * (1.0 - _rc), 0.0, precip_mm=w["pp"] - _re, de_state=de_state, theta_start=_th1_0, snow_day=w.get('snow_day', False),
                              use_cropsyst_formula=(soil_evap_model == "cropsyst"),
                              fallow=True, summer_time=summer_time_from_doy(w["doy"]))
            if sixpool_offseason_decay and sixpool_state is not None:
                # Real off-season Cra/Crtz/Cm/Cs decomposition -- reuses sixpool_step() itself
                # unmodified (root_c_input=0.0, no crop growing), the exact same formula the
                # main loop uses, just driven by real spinup-window weather and the SAME
                # evolving topsoil moisture this spinup loop is already tracking. Opt-in
                # (default False) specifically so this never silently changes any already-
                # shipped single-season result (e.g. wheat's own 0.490 validated correlation,
                # which passes spinup_rows but was never asked to carry carbon state across
                # years) -- see this parameter's own docstring for the full account of why it
                # exists and what it does and doesn't model (the real harvest-to-Dec31 tail of
                # the off-season isn't covered, only Jan1-to-planting, since that's the only
                # real weather window spinup_rows itself has ever carried in this project).
                tmean_spin = (w["tx"] + w["tn"]) / 2
                relwet_spin = ((layers[0]["theta"] - layers[0]["pwp"]) / (layers[0]["fc"] - layers[0]["pwp"])
                                if layers[0]["fc"] > layers[0]["pwp"] else 1.0)
                sixpool_state["wx_day"] = (w["tx"], w["tn"], w["pp"]); sixpool_state["rtz_k"] = crop.get("weps_k")
                sixpool_step(sixpool_state, tmean_spin, relwet_spin, 0.0, 1.0, layers)
    tillage_depth_m, tillage_mixing_efficiency = None, None
    if tillage_doy == "planting":   # row 55: tillage on the first season day (the planting day), whatever that year's date is
        tillage_doy = weather_rows[0]["doy"]
    if tillage_doy is not None:
        if tillage_implement not in TILLAGE_IMPLEMENTS:
            raise ValueError(f"Unknown tillage implement {tillage_implement!r} -- see TILLAGE_IMPLEMENTS for the real Cycles v1.4.4 implement catalog.")
        tillage_depth_m, tillage_disturb_rating, tillage_mixing_efficiency = TILLAGE_IMPLEMENTS[tillage_implement]
    tillage_ftx_val = tillage_ftx(tillage_clay_frac)
    tillage_dr = 0.0  # cumulative disturbance state -- see tillage_ft()/tillage_dr_decay() above

    # Real hydraulic-conductance-based transpiration/water-stress (campbell_water_uptake(),
    # 2026-09-25) is used for any crop whose dict carries all three real fields it needs --
    # lwp_stress_onset, lwp_wilting_point (both real GenericCrops.crop LWP_STRESS_ONSET/
    # LWP_WILTING_POINT), and a finite tr_max_mm_day (WUmax -- already a real per-crop field
    # in this engine, added 2026-09-23 for an unrelated fix, now load-bearing here too). CT is
    # computed once here, per crop, not per day (only CTc = CT*canopy_cover varies daily).
    # Any crop dict missing one of the three (e.g. a placeholder species borrowing another
    # crop's growth parameters but not its LWP thresholds) automatically falls back to the
    # engine's original root_zone_availability()/water_stress_response()/
    # extract_transpiration() trio below, byte-identical to this mechanism's own pre-2026-09-25
    # behavior -- see water_stress_response()'s own docstring for why that trio is kept, not
    # removed, despite being superseded as the primary path.
    crop_wumax = crop.get("tr_max_mm_day")
    crop_ct = (total_root_conductance(crop_wumax, crop["lwp_stress_onset"])
               if ("lwp_stress_onset" in crop and "lwp_wilting_point" in crop
                   and crop_wumax is not None and math.isfinite(crop_wumax))
               else None)

    tt_cum, biomass, ag_biomass = 0.0, 0.0, 0.0
    gj_rl = [0.0] * len(layers)   # root length by layer, cm root per cm2 of ground (Godwin and Jones RLV x layer depth), grown from root growth
    gj_rl_seeded = False
    biomass_ref = 0.0   # biomass of the same crop without N stress (paper Sec 2.5: new-growth N concentration is that of a crop growing without stress)
    tt_canopy, n_stress_prev = 0.0, 1.0
    tt_sen_extra = 0.0
    _ei_state, _ttdev_prev, _xc_h = None, 0.0, 0.0   # integrated canopy state
    water_stress_prev = 1.0
    eie_prev_day = 0.0
    eie_prev_day2 = 0.0
    ag_biomass_at_flowering = None  # captured the first day tt_cum crosses flowering_tt --
    # see the real f_G harvest-index fix below (Kemanian et al. 2007) for why.
    n_tracking_active = (crop.get("legume_n", False) or not crop.get("legume", False)) and (   # legume_n (2026-10-23): a legume runs the N path with stress off and fixation filling the unmet demand (Kemanian 2024 Sec 2.5); default off keeps the old exemption
        n_rate_kg_ha is not None or n_applications or n_credit_kg_ha or manure_n_kg_ha)
    if manure_source is not None:
        if manure_source not in MANURE_SOURCES:
            raise ValueError(f"Unknown manure source {manure_source!r} -- see MANURE_SOURCES for the real Cycles v1.4.4 fert.txt manure catalog.")
        manure_availability = MANURE_SOURCES[manure_source]["nh4_frac"]
    if fertilizer_source is not None:
        if fertilizer_source not in MINERAL_SOURCES:
            raise ValueError(f"Unknown fertilizer source {fertilizer_source!r} -- see MINERAL_SOURCES for the real Cycles v1.4.4 fert.txt mineral fertilizer catalog.")
        mineral_nh4_frac = MINERAL_SOURCES[fertilizer_source]["nh4_frac"]
        mineral_no3_frac = MINERAL_SOURCES[fertilizer_source]["no3_frac"]
    else:
        mineral_nh4_frac, mineral_no3_frac = 1.0, 0.0  # unchanged default: every mineral dose
        # lands 100% in NH4 when no real source is specified, exactly as before this parameter
        # existed -- see fertilizer_source's own docstring for why this isn't universally true.
    if VOLAT_MACNACK_PH is not None and soil_ph is None:
        soil_ph = VOLAT_MACNACK_PH
    volatilization_active = fert_placement_implement is not None or soil_ph is not None
    fert_mixing_efficiency = 0.0
    if fert_placement_implement is not None:
        if fert_placement_implement not in TILLAGE_IMPLEMENTS:
            raise ValueError(f"Unknown fertilizer placement implement {fert_placement_implement!r} -- see TILLAGE_IMPLEMENTS for the real Cycles v1.4.4 implement catalog.")
        fert_mixing_efficiency = TILLAGE_IMPLEMENTS[fert_placement_implement][2]
    if manure_n_kg_ha and manure_source is not None and sixpool_state is not None:
        # Organic fraction of the manure goes to the surface residue pool with its own C:N (Cycles decomposes it; the NH4 fraction is credited to the mineral pool above).
        _ms = MANURE_SOURCES[manure_source]
        _n_org = manure_n_kg_ha * _ms["norg_frac"]; _c_org = _n_org * _ms["c_per_norg"] / 1000.0
        _c_old = sixpool_state.get("cra", 0.0); _n_old = _c_old * 1000.0 / sixpool_state.get("cra_cn", SIXPOOL_CN_CRA)
        sixpool_state["cra_cn"] = (_c_old + _c_org) * 1000.0 / max(_n_old + _n_org, 1e-9)
        sixpool_state["cra"] = _c_old + _c_org
    if RES_SPLIT and sixpool_state is not None and "cra_fs" in sixpool_state:
        sixpool_state["cra_fs"] *= 1.0 - math.sqrt(TILLAGE_IMPLEMENTS["Planter_double_disk_opnr"][2])   # the planter pass of the Cycles operation file (mixing efficiency 0.0716) flattens its square root of the standing residue
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
        if VOLAT_MACNACK_PH is not None and fertilizer_source is not None:
            base_frac *= MINERAL_UREA_SHARE.get(fertilizer_source, 0.0)   # Macnack's data are surface urea: only the urea share of the product
        return 1.0 - base_frac * (1.0 - fert_mixing_efficiency)

    manure_retention = 1.0 - NH3_FRAC_MANURE * (1.0 - fert_mixing_efficiency) if volatilization_active else 1.0
    n_volatilized_total = 0.0 if volatilization_active else None
    applications_by_doy = {}
    mineral_day0_kg_ha = 0.0  # the single-lump mineral dose landing at day 0 (net of
    # volatilization retention) -- stays 0.0 when n_applications is used instead, since mineral
    # then lands on its own scheduled days via applications_by_doy in the main loop below, not
    # here. Tracked separately from n_pool/total_n_input_kg_ha (which also fold in
    # credit_and_manure) purely so the real NH4/NO3 split below can be applied to the mineral
    # portion only -- see fertilizer_source's own docstring; credit/manure still land entirely
    # in NH4 either way, unchanged.
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
            mineral_day0_kg_ha = total_n_input_kg_ha
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
    n_denitrified_total = 0.0 if (n_pool is not None and model_denitrification) else None
    n2o_total = 0.0
    n_uptake_total = 0.0 if n_pool is not None else None
    n_fixed_total = 0.0
    n_rhizo_total = 0.0
    root_hold_c = 0.0
    # n_pool_by_layer: the real per-layer tracking n_root_limited needs (see
    # simulate_season()'s own docstring) -- None whenever n_root_limited is False (the
    # default) or nitrogen tracking is off entirely, so every existing caller is unaffected.
    # The day-0 lump (n_pool as already computed above) transfers whole into the surface
    # layer; dated applications/background credit land there too, in the main loop below.
    n_pool_by_layer = None
    if n_pool is not None and n_root_limited:
        n_pool_by_layer = [0.0] * len(layers)
        n_pool_by_layer[0] = n_pool
    # NH4/NO3 split (2026-10-02) -- see simulate_season()'s own nh4_no3_split docstring for
    # the real leaching-split evidence motivating this. n_nh4/n_no3 start as a split of
    # whatever n_pool already holds at this point: the mineral day-0 lump (mineral_day0_kg_ha,
    # 0.0 when dated n_applications were used instead) divides per fertilizer_source's real
    # NH4/NO3 fractions (1.0/0.0 -- all NH4 -- when no source was given, the original
    # assumption); the remainder of n_pool (credit_and_manure, isolated here as n_pool minus
    # the mineral portion, since that local variable itself doesn't persist this far) lands
    # entirely in NH4 as before. n_pool itself is then kept as the scalar n_nh4+n_no3 view for
    # every existing piece of code that still reads it directly (the demand-capping comparisons
    # below), the same "kept in sync, never authoritative" pattern n_pool_by_layer already
    # established. Mutually exclusive with n_root_limited by construction (n_pool_by_layer is
    # not None whenever that's active).
    n_nh4 = ((mineral_day0_kg_ha * mineral_nh4_frac) + (n_pool - mineral_day0_kg_ha)
             if (n_pool is not None and nh4_no3_split and n_pool_by_layer is None) else None)
    n_no3 = (mineral_day0_kg_ha * mineral_no3_frac) if n_nh4 is not None else None
    tsoil_lag = ((weather_rows[0]["tx"] + weather_rows[0]["tn"]) / 2.0
                 if (n_nh4 is not None and weather_rows) else None)
    if initial_n_state is not None and n_nh4 is not None:
        # Standing mineral nitrogen carried in from the previous season/off-season (see
        # run_fallow_n_window() and simulate_season_with_leadin(carry_n=True)). Added ON TOP of
        # this season's own fertilizer/credit; deliberately NOT counted in total_n_input_kg_ha
        # (carried-in N is not new supply), so the single-season mass-balance identity gains a
        # carried-in term when this is used.
        n_nh4 += initial_n_state["n_nh4"]
        n_no3 += initial_n_state["n_no3"]
        n_pool = n_nh4 + n_no3
        tsoil_lag = initial_n_state["tsoil_lag"]
    no3_layers = None
    if nitrate_per_layer and n_nh4 is not None:
        # Per-layer nitrate (2026-10-02): NO3 is the mobile form, so it is tracked by layer and moved
        # by redistribute()'s own n_by_layer transport (water carries each layer's nitrate with it)
        # instead of one well-mixed profile reservoir. NH4 stays a single surface pool (held by
        # exchange sites, essentially non-leachable in Cycles). n_no3 stays the scalar SUM, kept in
        # sync, so every existing reader of it is unchanged.
        no3_layers = [0.0] * len(layers)
        if initial_n_state is not None and initial_n_state.get("no3_layers"):
            fresh = n_no3 - initial_n_state["n_no3"]
            no3_layers = list(initial_n_state["no3_layers"])
            no3_layers[0] += fresh
        else:
            no3_layers[0] = n_no3
    last_doy = None
    # Real, continuous NH4-pool ammonia volatilization (2026-10-02, see volatilization_flux()'s
    # own docstring) -- only meaningful alongside the NH4/NO3 split above, since it drains the
    # real NH4 sub-pool directly rather than approximating a one-time loss at application time.
    n_volatilized_pool_total = 0.0 if (n_nh4 is not None and model_volatilization) else None
    irrigation_total_mm = 0.0
    history = [] if record_history else None

    # Real, day-by-day concentration-tracked nitrogen stress (2026-09-25), replacing the
    # season-total quadratic-plateau this engine used from 2026-09-14 through today. Found
    # via CropSyst's own real, public source (crop/crop_N_common.cpp -- Cycles shares its
    # biophysical fundamentals with CropSyst, and unlike Cycles this repo has real .cpp
    # source, not just binaries): N_reduction_factor = 1-(Ncrit-Nactual)/(Ncrit-Nmin), a
    # DAY-BY-DAY function of the plant's own actual tissue N status (Nactual = cumulative
    # canopy N content / cumulative biomass), not a single season-total supply/demand ratio.
    # Ncrit(biomass) is n_critical_pct() -- already real, already had it. Nmin needed real
    # sourcing: Lemaire et al. 2008 ("Diagnosis tool for plant and crop N status in
    # vegetative stage," Eur. J. Agron. 28) -- the paper Matt supplied for exactly this --
    # turned out to define only ONE curve (the critical concentration itself) plus the
    # Nitrogen Nutrition Index (NNI = Na/Nc), not a separate Nmin curve; the closest real
    # concept in it is %Ns, the asymptotic structural-tissue concentration (Eq. 4-6, cited
    # at ~0.8% for grasses, not crop-specific). A better, already-available, crop-specific
    # source: Cycles' own real crop file has N_MIN_CONCENTRATION_STRAW (0.2% for corn/wheat/
    # silage corn, -999/not-applicable for soybean -- consistent with soybean's LEGUME
    # exemption from N stress entirely), a real disclosed low-tissue-N floor conceptually
    # matching CropSyst's Nmin exactly, just under a different field name. Used here as each
    # crop's own n_min_conc.
    #
    # This also structurally eliminates the whole class of bug the old _reference_n_demand()
    # duplicate-loop pattern was prone to (see the irrigation-desync bug found and fixed
    # 2026-09-25 in this same file's history) -- there is no second, parallel unconstrained
    # trajectory to keep in sync anymore, since nitrogen stress is now computed directly from
    # the SAME real state (biomass, canopy N content) the single main loop already tracks.
    #
    # Verified against the established benchmarks before shipping, not just derived: wheat
    # (the one crop where real Cycles output shows nitrogen, not water, is the dominant
    # driver) improved 0.473 -> 0.523, the largest jump this specific mechanism could produce
    # given the same real 90 kg N/ha fertilization event already wired in. Corn tested WITH
    # real nitrogen tracking (N=150, real ContinuousCorn.operation rate) under this new
    # mechanism scores 0.5095 -- essentially unchanged from the old season-total mechanism's
    # 0.5005, both still below the no-N-tracking default's 0.5495 -- confirming corn's own
    # earlier finding (real N stress correlates only weakly with real yield, -0.21, unlike
    # wheat's dominant -0.894) holds regardless of which N-stress mechanism is used, not an
    # artifact of the old mechanism's specific shape. Corn/soybean/silage corn's own DEFAULT
    # validation (n_rate_kg_ha=None) is completely unaffected either way, since this whole
    # block only runs when n_pool is not None.
    _wk_hc = hc_make([layers[0]["thick"]], SIXPOOL_ML_TMEAN_INIT)
    _V = crop.get("vern")
    vern_acc, pw_acc, post_acc, flowered, tt_dev = 0.0, 0.0, 0.0, False, 0.0
    winter_killed = False
    canopy_n_kg_ha = 0.0

    for w in weather_rows:
        _dn_th0 = [l["theta"] for l in layers]
        _dn_no3_0 = list(no3_layers) if no3_layers is not None else [0.0] * len(layers)
        if sixpool_state is not None:
            sixpool_state["theta_start"] = _dn_th0
        if SNOW_MODEL:
            w = snow_adjust(layers, w, crop["lat_deg"])
        last_doy = w["doy"]
        # Real cold-kill (2026-10-01): a single night below the crop's own real, disclosed
        # THRESHOLD_TEMPERATURE_FOR_COLD_DAMAGE (GenericCrops.crop -- corn 3C, soybean 2C,
        # winter wheat -10C) ends the season outright. Found diagnosing corn's single worst
        # Rock Springs overshoot year (1982, model 11.71 vs real 7.13 Mg/ha): real Cycles'
        # own CornRM.90.txt shows STAGE=KILLED in every one of the 37 years, almost always
        # right around 1818-1833 GDD (essentially tt_maturity=1800, ordinary maturity) --
        # except 1982 (killed at 1485.6 GDD, 82.5% of normal) and 1997 (1752.7, 97.3%).
        # Checked systematically against the real weather record: in BOTH years, and ONLY
        # those two years, a night below 3C occurred DURING reproductive growth (after
        # flowering_tt) before the crop would otherwise have matured -- a real, causal,
        # zero-false-positive signal across the full 37-year record, not a correlation
        # found by searching. Gated on tt_cum>=flowering_tt specifically because many years'
        # own early-season nights (right after planting, well before flowering) also drop
        # below the same threshold without any real consequence (confirmed: 1980 hits 1.24C
        # and 1985 hits 0.90C within 60 days of planting, neither killed) -- ungated, this
        # mechanism collapsed every year's yield by killing seedlings in spring (tested
        # directly: mean grain fell from 10.56 to 1.90 Mg/ha, correlation went negative).
        # Verified: with the flowering_tt gate, corn's Rock Springs correlation jumped
        # 0.505->0.691 (uncalibrated), the single largest movement any mechanism has
        # produced this session -- see run_validation.py's own calibration_factor comment
        # and MECHANISM_LOG.md for the full account.
        if (flowered if _V is not None else tt_cum >= crop.get("flowering_tt", math.inf)) and w["tn"] < crop.get("threshold_temp_cold_damage", -math.inf):
            break
        # Winterkill (2026-10-07): a night below the crop's own real MIN_TEMPERATURE_FOR_COLD_DAMAGE
        # (GenericCrops.crop; winter wheat -25C) kills the stand at any growth stage, no harvest.
        # Derived directly, not fitted: in 37 Rock Springs winters real Cycles' continuous winter
        # wheat dies in exactly the three whose coldest night is below -26.5C (1982 -26.58, 1985
        # -27.55, 1994 -27.36) and survives -23.38 and -23.19, consistent with the crop file's -25.
        # Opt-in via crop["winterkill_temp"] (None/absent = never), so no existing crop changes.
        # 2026-10-16 rebuild phase 6: the kill is driven by TOP-LAYER SOIL temperature, not air. Cycles' continuous winter wheat at 10 sites (340 winters, 7 kills) dies
        # only when layer-1 soil temperature falls below about -25 C (killed: -27.4 to -25.2; survivors never below -24.9) while the same stands survive air
        # nights of -40 C. The air rule killed 190 of 333 surviving winters; this rule 27 of 333 while catching 5 of the 7 real kills. Layer-1 temperature is
        # the same lag filter the six-pool uses (correlation 0.96 with Cycles' soil_temperature.1 winter minimum, bias -1.5 C: no snow insulation).
        _wk_tmean = (w["tx"] + w["tn"]) / 2.0
        _wk_soil = hc_step(_wk_hc, _wk_tmean)[0]
        if (_wk_soil if WINTERKILL_SOIL_T else w["tn"]) < crop.get("winterkill_temp", -math.inf):
            winter_killed = True
            break
        dtt = thermal_time_increment(w["tx"], w["tn"], crop["base_t"], crop["opt_t"], crop["max_t"])
        if not PLANT_DAY_TT and w is weather_rows[0]:
            dtt = 0.0   # Cycles' thermal_time is 0 on the planting date and accumulates from the next day; the engine had counted the planting day (a constant 10 to 17 C day lead over Cycles, wheat and corn)
        tt_cum += dtt
        if _V is None:
            tt_dev = tt_cum
        else:
            if not flowered:
                if vern_acc < _V["req"]:
                    vern_acc = min(_V["req"] + 2.5, vern_acc + vernalization_increment((w["tx"] + w["tn"]) / 2.0, _V))
                if vern_acc >= _V["req"]:
                    pw_acc += dtt * max(0.0, min(1.0, (photoperiod_hours(w["doy"], crop["lat_deg"], _V["twilight_deg"]) - _V["pmin"]) / (_V["pmax"] - _V["pmin"])))
                    if pw_acc >= _V["tt_flower_pmax"]:
                        flowered = True
            if flowered:
                post_acc += thermal_time_increment(w["tx"], w["tn"], _V["post"][0], _V["post"][1], _V["post"][2])
                tt_dev = crop["flowering_tt"] + (crop["tt_maturity"] - crop["flowering_tt"]) * min(1.0, post_acc / _V["gf_tt"])
            else:
                tt_dev = min(tt_cum, crop["flowering_tt"] - 1e-6)
        _wf = water_stress_prev ** crop.get("canopy_water_pow", CANOPY_WATER_POW)
        if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("wclock", ()):
            _wf = _FORCE_CUR["wclock"][w["doy"]] ** crop.get("canopy_water_pow", CANOPY_WATER_POW)
        if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("nclock", ()):
            n_stress_prev = _FORCE_CUR["nclock"][w["doy"]]
        _nf = n_stress_prev ** crop.get("canopy_n_pow", CANOPY_N_POW)
        tt_canopy += dtt * _nf * _wf
        tt_sen_extra += dtt * crop.get("senes_k", CANOPY_SENES_STRESS_K) * (1.0 - water_stress_prev * n_stress_prev)
        _ttm_season = crop.get("season_tt_end")   # 2026-10-23: TTf as the paper defines it, plant age in thermal time over the thermal time at maturity, with the season's own maturity (winter wheat: pre-pass)
        ttf = (tt_cum / _ttm_season) if _ttm_season else tt_dev / crop["tt_maturity"]
        if ttf >= harvest_ttf:
            break
        _shape = crop["canopy_shape_faithful"] if (CANOPY_FAITHFUL and "canopy_shape_faithful" in crop) else (CANOPY_SHAPE_FORCE if CANOPY_SHAPE_FORCE is not None else crop.get("canopy_shape", DEFAULT_CANOPY_SHAPE))
        _eix = crop["eix_faithful"] if (CANOPY_FAITHFUL and "eix_faithful" in crop) else crop["eix_cap"] if "eix_cap" in crop else (CANOPY_EIX_FORCE if CANOPY_EIX_FORCE is not None else crop.get("eix", 1.0))   # per-crop plateau (2026-10-17: wheat 0.86, Cycles' measured unstressed plateau)
        _form = crop.get("canopy_form", "closed")
        if _form in ("D", "H"):
            # Integrated-derivative forms (paper Eq. 6 text: 'the first derivative of Eq. (6) is used to estimate the rate of change ... the rate is reduced by N stress'). The expansion part of the
            # derivative is scaled by the stress rate, the senescence part is not. D evaluates the expansion derivative at the thermal clock (corn: offline daily canopy rms 0.136 -> 0.086 on 1776 Cycles
            # site-years with Cycles' stress forced); H evaluates it at the stress-slowed clock so a stressed canopy can catch up once stress eases (winter wheat: 0.200 -> 0.159 against 0.169 for D).
            _a, _b, _c, _d = _shape
            _x = (tt_cum / _ttm_season) if _ttm_season else tt_dev / crop["tt_maturity"]
            if _ei_state is None:
                _ei_state = _eix / (1 + math.exp(_a) + math.exp(_c)); _xc_h = _x
            _dx = (max(0.0, tt_cum - _ttdev_prev) / _ttm_season) if _ttm_season else max(0.0, tt_dev - _ttdev_prev) / crop["tt_maturity"]
            _xe = _xc_h if _form == "H" else _x
            _e1 = math.exp(_a + _b * _xe); _e2 = math.exp(_c + _d * _x); _den = (1 + _e1 + _e2) ** 2
            _ei_state = max(0.0, min(_eix, _ei_state + _eix * (-_b * _e1 * _nf * _wf - _d * _e2) / _den * _dx))
            _xc_h += _dx * _nf * _wf
            _ttdev_prev = tt_cum if _ttm_season else tt_dev
            _ei = _ei_state
        elif CANOPY_TWO_CLOCK:
            _ei = canopy_cover_two(tt_canopy / crop["tt_maturity"], (tt_dev + tt_sen_extra) / crop["tt_maturity"] - crop.get("senes_delay", CANOPY_SENES_DELAY), _eix, _shape)
        else:
            _ei = canopy_cover(tt_canopy / crop["tt_maturity"], _eix, _shape)
        eie = 0.0 if tt_cum < crop.get("tt_emergence", 0.0) else effective_canopy_cover(_ei, crop.get("plant_density_factor", 1.0))
        if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("canopy", ()):
            eie = _FORCE_CUR["canopy"][w["doy"]]
        root_depth = root_max_m * min(1.0, ttf / ROOT_TTF_FULL)

        # Tillage's soil-moisture mixing happens once, on tillage_doy itself, before
        # today's irrigation check and water balance -- see mix_tilled_layers() above.
        # The cumulative disturbance rating (tillage_dr) jumps by the real implement's
        # SOIL_DISTURB_RATIO the same day -- see tillage_ft()/tillage_dr_decay() above.
        if tillage_doy is not None and w["doy"] == tillage_doy:
            mix_tilled_layers(layers, tillage_depth_m, tillage_mixing_efficiency, sixpool_profile_raw if tillage_mix_texture else None)
            tillage_dr += tillage_disturb_rating
            if sixpool_state is not None and tillage_mixing_efficiency and "cra_fs" in sixpool_state:
                sixpool_state["cra_fs"] *= 1.0 - math.sqrt(tillage_mixing_efficiency)   # the pass flattens sqrt(mixing efficiency) of the standing residue (Cycles input guide)
            if sixpool_state is not None and "ml" in sixpool_state and tillage_mix_texture and tillage_mixing_efficiency > 0:
                # the per-layer carbon pools (extensive, Mg C/ha per layer) mix by the same coefficient, conserving the tilled-zone total
                _zone = []; _d = 0.0
                for _l, _x in zip(layers, sixpool_state["ml"]):
                    if _d >= tillage_depth_m: break
                    _zone.append((_x, _l["thick"], min(_l["thick"], tillage_depth_m - _d) / _l["thick"])); _d += _l["thick"]
                for _k in ("cs", "cm", "crtz", "crm", "csx"):
                    _den = sum(_t * _f for _x, _t, _f in _zone)
                    if _den <= 0: continue
                    _cbar = sum(_x[_k] * _f for _x, _t, _f in _zone) / _den
                    for _x, _t, _f in _zone:
                        _b = _f * tillage_mixing_efficiency
                        _x[_k] = _x[_k] * (1 - _b) + _cbar * _t * _b
                sixpool_state["cs"] = sum(_x["cs"] for _x in sixpool_state["ml"]); sixpool_state["cm"] = sum(_x["cm"] for _x in sixpool_state["ml"]); sixpool_state["csx"] = sum(_x["csx"] for _x in sixpool_state["ml"])
                # surface residue mixes into the tilled layers too (Cycles output: belowground residue 0.9 vs 0.02 Mg/ha right after a chisel pass): that share of the surface
                # residue carbon becomes incorporated residue in those layers (by thickness within the depth), decomposing there
                _tt = sum(_t * _f for _x, _t, _f in _zone)
                if _tt > 0 and sixpool_state["cra"] > 0:
                    _mv = sixpool_state["cra"] * tillage_mixing_efficiency; sixpool_state["cra"] -= _mv
                    for _x, _t, _f in _zone: _x["crtz"] += _mv * _t * _f / _tt

        # Irrigation (if requested) triggers off YESTERDAY's ending soil moisture, same
        # quantity water_stress is computed from below, and is added to today's water input
        # before infiltration/redistribution -- so irrigated water shows up in today's
        # available water exactly like an equivalent rain event would.
        irrigation_mm = 0.0
        if irrigation_trigger_frac is not None and irrigation_refill_layers is not None:
            # Cycles' AUTO_IRRIGATION (input.md): when the plant available water over the layers down to LAST_SOIL_LAYER has been depleted past the threshold, add the water
            # that brings those layers to field capacity; events only inside START_DOY..STOP_DOY
            if irrigation_window[0] <= w["doy"] <= irrigation_window[1]:
                _il = layers[:irrigation_refill_layers]
                _cap = sum((l["fc"] - l["pwp"]) * l["thick"] for l in _il)
                _av = sum(max(0.0, min(l["theta"], l["fc"]) - l["pwp"]) * l["thick"] for l in _il)
                if _cap > 0 and _av / _cap < irrigation_trigger_frac:
                    irrigation_mm = sum(max(0.0, l["fc"] - l["theta"]) * l["thick"] for l in _il) * 1000.0
                    irrigation_total_mm += irrigation_mm
        elif irrigation_trigger_frac is not None:
            pre_avail_frac = root_zone_availability(layers, root_depth)
            if pre_avail_frac < irrigation_trigger_frac:
                irrigation_mm = irrigation_amount_mm
                irrigation_total_mm += irrigation_mm
        if irrigation_events and w["doy"] in irrigation_events:   # dated irrigation (mm on that day of year), e.g. a recorded event schedule
            irrigation_mm += irrigation_events[w["doy"]]
            irrigation_total_mm += irrigation_events[w["doy"]]

        res_cover_today = residue_cover_frac(sixpool_state)
        _re_take, res_evap_today = residue_water_today(sixpool_state, w["pp"], res_cover_today, eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"]), eie, w.get("snow_day", False))
        _th1_0 = zone_mean_theta(layers)
        drainage_mm, runoff, n_leached_today = infiltrate(layers, w["pp"] + irrigation_mm - _re_take, curve_number,
                                                            slope_pct,
                                                            n_by_layer=(no3_layers if no3_layers is not None
                                                                        else n_pool_by_layer))
        runoff_total += runoff
        if no3_layers is not None:
            n_no3 = sum(no3_layers)
            n_leached_total += n_leached_today

        # NH4->NO3 nitrification (2026-10-02, see nitrification_rate()'s own docstring) --
        # runs before today's denitrification/leaching touch n_no3, so a fresh application
        # that landed yesterday gets one real day to start nitrifying before either loss
        # pathway can act on it, rather than being immediately as leachable/denitrifiable as
        # long-standing NO3. tsoil_lag reuses the same already-validated lag filter
        # simulate_soil_temp() uses for planting-date determination (SOIL_TEMP_LAG_K), tracked
        # here day by day since the main loop otherwise only ever carries air tmean.
        if n_nh4 is not None:
            _tmean_today = (w["tx"] + w["tn"]) / 2.0
            tsoil_lag = tsoil_lag + SOIL_TEMP_LAG_K * (_tmean_today - tsoil_lag)
            # Both draws computed off the same starting n_nh4 (not sequentially, which would
            # bias whichever ran second) -- real daily rates here are small enough (nitrification
            # up to ~0.145/day, volatilization up to ~0.044/day observed) that this is a safe
            # explicit-Euler approximation, the same one already used for every other daily
            # rate in this engine.
            nitrif_amt_today = nitrification_flux_ratio(n_nh4, (no3_layers[0] if no3_layers is not None else n_no3), tsoil_lag, layers[0]["theta"] / layers[0]["sat"], layers[0])
            volat_amt_today = (volatilization_flux(tsoil_lag, n_nh4, layers[0], w["wind"], layers[0].get("ph"))
                               if model_volatilization and VOLAT_MACNACK_PH is None else 0.0)
            n_nh4 = max(0.0, n_nh4 - nitrif_amt_today - volat_amt_today)
            n_no3 += nitrif_amt_today
            n2o_total += n2o_from_nitrification(nitrif_amt_today, layers[0]["theta"] / layers[0]["sat"])
            if no3_layers is not None:
                no3_layers[0] += nitrif_amt_today
            if n_volatilized_pool_total is not None:
                n_volatilized_pool_total += volat_amt_today

        # Real denitrification (2026-10-02, see denitrification_rate()'s own docstring) --
        # applied right after today's water balance/leaching, using the moisture state
        # infiltrate() just left layer[0] in, before uptake draws the pool down further.
        # When nh4_no3_split is active, draws from the NO3 pool specifically (denitrification
        # is an NO3-consuming process by definition) rather than the whole lumped pool, which
        # is still the disclosed-simplification default everywhere else.
        if model_denitrification and n_pool is not None:
            if sixpool_state is None or no3_layers is None or n_no3 is None or n_pool_by_layer is not None:
                raise ValueError("denitrification needs the six-pool background model with per-layer nitrate")
            _dl = denitrification_layers(_dn_no3_0, _dn_th0, layers, sixpool_state, no3_layers) if DENIT_STARTDAY else None
            denitrif_today = (sum(_dl) if DENIT_STARTDAY else
                              denitrification_flux_resp(n_no3, (_SUBDAY_REL1_EFF if (SUBDAY_DENIT and _SUBDAY_REL1_EFF is not None) else layers[0]["theta"] / layers[0]["sat"]), sixpool_state.get("resp_mg_ha", 0.0)))
            if DIAG_DENIT is not None: DIAG_DENIT.append((_DIAG_YEAR, w["doy"], (_SUBDAY_REL1_EFF if (SUBDAY_DENIT and _SUBDAY_REL1_EFF is not None) else layers[0]["theta"] / layers[0]["sat"]), n_no3, sixpool_state.get("resp_mg_ha", 0.0), denitrif_today, layers[0]["theta"] / layers[0]["sat"], tuple(no3_layers)))
            if denitrif_today > 0 and n_no3 > 0:
                _f = denitrif_today / n_no3
                n2o_total += n2o_from_denitrification(denitrif_today, _dn_no3_0[0] / (sixpool_bulk_density(layers[0]["sat"]) * layers[0]["thick"] * 10.0), _dn_th0[0] / layers[0]["sat"], layers[0], sixpool_state.get("resp_mg_ha", 0.0), sixpool_state.get("clay", 0.25))
                if DENIT_STARTDAY:
                    for _i, _x in enumerate(_dl):
                        no3_layers[_i] -= _x
                else:
                    for i in range(len(no3_layers)):
                        no3_layers[i] *= (1.0 - _f)
                n_no3 = max(0.0, n_no3 - denitrif_today)
            n_denitrified_total += denitrif_today
        if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("loss", ()) and no3_layers is not None and n_no3 is not None:
            # diagnostic (2026-10-15): replace the engine's daily nitrate-pathway loss (leaching + denitrification) by Cycles' value
            _eng_loss = n_leached_today + (denitrif_today if model_denitrification else 0.0)
            _delta = _FORCE_CUR["loss"][w["doy"]] - _eng_loss
            _tot = sum(no3_layers)
            if _tot > 1e-9:
                _d = max(-_tot * 0.0, min(_delta, _tot))
                if _d > 0:
                    for _i in range(len(no3_layers)):
                        no3_layers[_i] -= _d * no3_layers[_i] / _tot
                    n_no3 = max(0.0, n_no3 - _d)
                else:
                    no3_layers[0] += -_delta
                    n_no3 += -_delta
        eto = eto_fao56(w["doy"], w["tx"], w["tn"], w["solar"], w["rhx"], w["rhn"], w["wind"], crop["lat_deg"])
        _w0 = sum(l["theta"] * l["thick"] for l in layers) if (DIAG_EVAP is not None or record_history) else 0.0
        soil_evaporation(layers, eto * (1.0 - res_cover_today), eie, precip_mm=w["pp"] + irrigation_mm - _re_take, de_state=de_state, theta_start=_th1_0, snow_day=w.get('snow_day', False),
                          use_cropsyst_formula=(soil_evap_model == "cropsyst"), fallow=False)
        _sev_mm = (_w0 - sum(l["theta"] * l["thick"] for l in layers)) * 1000.0 if record_history else 0.0   # soil water lost to evaporation today (history only)
        if DIAG_EVAP is not None: DIAG_EVAP.append((_DIAG_YEAR, w["doy"], (_w0 - sum(l["theta"] * l["thick"] for l in layers)) * 1000.0, res_evap_today, eto, res_cover_today))

        tmean = (w["tx"] + w["tn"]) / 2
        temp_factor = transpiration_temp_factor(tmean, crop["tr_min_t"], crop["tr_threshold_t"])
        rad_temp_factor = radiation_temp_factor(tmean, crop["tr_min_t"], crop.get("rad_temp_floor", 0.0),
                                                 crop.get("rad_temp_plateau_t", crop["tr_threshold_t"]))
        GR = crop["rue"] * rue_co2_scale * rad_temp_factor * (((1.0 - (crop.get("growth_canopy_lag", GROWTH_CANOPY_LAG) - 1.0)) * eie_prev_day + (crop.get("growth_canopy_lag", GROWTH_CANOPY_LAG) - 1.0) * eie_prev_day2) if GROWTH_PREV_CANOPY else eie) * w["solar"]
        Da = max(VPD_FLOOR_KPA, 0.66 * 0.6108 * math.exp(17.27 * w["tx"] / (w["tx"] + 237.3)) * (1.0 - w["rhn"] / 100.0))   # reconstructed from the vapor pressure deficit column of Cycles' output
        TRp = (1 + (crop["kc"] - 1) * eie) * eie * eto
        TRp *= temp_factor

        if crop_ct is not None:
            # Real hydraulic-conductance mechanism -- see campbell_water_uptake()'s own
            # docstring above. Mutates layers in place and returns the real, physically-
            # limited transpiration directly, so no separate extract_transpiration() call
            # is needed (unlike the fallback branch below).
            TR_actual, water_stress = campbell_water_uptake(
                layers, root_depth, TRp, eie, crop_ct, crop["lwp_stress_onset"], crop["lwp_wilting_point"])
        else:
            avail_frac = root_zone_availability(layers, root_depth)
            water_stress = water_stress_response(avail_frac, crop.get("depletion_fraction", 0.5))
            TR_actual = min(TRp * water_stress, crop.get("tr_max_mm_day", math.inf))
            extract_transpiration(layers, root_depth, TR_actual)
        if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("water", ()):
            water_stress = _FORCE_CUR["water"][w["doy"]]
            TR_actual = TRp * water_stress
        _water_hook(layers, w["doy"], no3_layers)
        water_stress_prev = water_stress
        # tr_max_mm_day: real, disclosed per-crop TRANSPIRATION_MAX from GenericCrops.crop
        # (corn/silage corn 10, soybean/wheat 8 mm/day), a physical ceiling on daily
        # transpiration -- for the fallback branch above it's an explicit clamp; for the
        # Campbell mechanism it's already the real WUmax input CT itself was derived from
        # (the manual's own point: "any evaporative demand larger than the maximum uptake
        # rate will only induce stomatal closure"), so this second clamp is now redundant
        # there but kept as a harmless final safety net either way.
        TR_actual = min(TR_actual, crop.get("tr_max_mm_day", math.inf))

        GT = crop["wue"] * wue_co2_scale / math.sqrt(Da) * TR_actual
        dGB_water_limited = max(0.0, min(GR, GT)) * crop_ngf(crop) / 1000 * (crop["growth_stage_c"] * (1.0 - crop["growth_stage_a"] * math.exp(-ttf / crop["growth_stage_tau"])) if "growth_stage_a" in crop else 1.0)
        _lx0 = crop.get("late_rue_x0", LATE_RUE_X0); dGB_water_limited *= 1.0 - (1.0 - crop.get("late_rue_f", LATE_RUE_F)) * min(1.0, max(0.0, (ttf - _lx0) / max(1e-6, 1.0 - _lx0)))
        if _V is not None and flowered:
            # post-flowering temperature factor: Cycles' daily temperature_factor column is 0.99 below ~19 C mean and falls to 0.94 / 0.83 / 0.65 / 0.38 at 20.5 / 23.5 / 26.5 / 29.5 C
            # (5,376 post-flowering days, 3 sites); the disclosed TEMPERATURE_POST_FLOWERING optimum (20) and maximum (35) with 1.0 below the optimum reproduce it (0.93 / 0.77 / 0.57 / 0.37)
            _tm = (w["tx"] + w["tn"]) / 2.0
            dGB_water_limited *= 1.0 if _tm <= _V["post"][1] else max(0.0, (_V["post"][2] - _tm) / (_V["post"][2] - _V["post"][1]))
        if DIAG_GROWTH is not None: DIAG_GROWTH.append((w["doy"], GR, GT, dGB_water_limited))
        eie_prev_day2 = eie_prev_day
        eie_prev_day = eie

        n_stress = 1.0
        if n_pool is not None and _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("minn", ()) and w["doy"] == min(_FORCE_CUR["minn"]) and n_nh4 is not None and no3_layers is not None:
            _f_no3, _f_nh4 = _FORCE_CUR["minn"][w["doy"]]
            n_nh4 = _f_nh4
            _cur = sum(no3_layers)
            if _cur > 1e-9:
                no3_layers[:] = [v * _f_no3 / _cur for v in no3_layers]
            else:
                no3_layers[:] = [_f_no3] + [0.0] * (len(no3_layers) - 1)
            n_no3 = sum(no3_layers)
            n_pool = n_nh4 + n_no3
        if n_pool is not None:
            if w["doy"] in applications_by_doy:
                if n_pool_by_layer is not None:
                    n_pool_by_layer[0] += applications_by_doy[w["doy"]]
                elif n_nh4 is not None:
                    _dose_today = applications_by_doy[w["doy"]]
                    n_nh4 += _dose_today * mineral_nh4_frac
                    n_no3 += _dose_today * mineral_no3_frac  # see fertilizer_source's own
                    if no3_layers is not None:
                        no3_layers[0] += _dose_today * mineral_no3_frac
                    # docstring for why this isn't always 100% NH4
                else:
                    n_pool += applications_by_doy[w["doy"]]
            if background_n_model == "sixpool":
                # Real two-pool carbon mineralization, run EVERY day (unlike the RothC path's
                # dGB_water_limited>0 gate below) -- Cs/Cm decomposition is a soil process, not
                # conditional on the crop actively growing that day; root_c_input_today is
                # already naturally 0 on non-growing days via dGB_water_limited itself. See
                # sixpool_step()'s own docstring for the full structure.
                relwet_topsoil = ((layers[0]["theta"] - layers[0]["pwp"]) / (layers[0]["fc"] - layers[0]["pwp"])
                                   if layers[0]["fc"] > layers[0]["pwp"] else 1.0)
                root_c_input_today = (10.0 * dGB_water_limited * (n_stress_prev if ROOT_C_REALIZED_GROWTH else 1.0) * (1.0 - shoot_fraction(ttf, crop["fsti"], crop["fstf"], crop.get("ttf50")))
                                       * CARBON_FRACTION_DM * ROOT_C_INPUT_FACTOR)
                ft_eff = 1.0 + tillage_ft(tillage_dr, tillage_ftx_val)
                if ROOT_C_AT_HARVEST and crop.get("root_retained_frac", 1.0) < 1.0:
                    # the roots the plant keeps are alive until the crop ends and only then become residue (Cycles' dailyResidue: root residue 0.4 to 0.6 Mg/ha through the
                    # season, 2.97 right after harvest); only the share that leaves the plant (rhizodeposits, turnover) enters the soil pool daily
                    _rr_h = crop.get("root_retained_frac", 1.0)
                    root_hold_c += root_c_input_today * _rr_h
                    root_c_input_today = root_c_input_today * (1.0 - _rr_h)
                if DIAG_LOSTC is not None: DIAG_LOSTC.append((_DIAG_YEAR, root_c_input_today * (1.0 - 1.0 / ROOT_C_INPUT_FACTOR), root_c_input_today))
                sixpool_state["n_min"] = ((n_nh4 or 0.0) + (n_no3 or 0.0)) if n_nh4 is not None else n_pool
                sixpool_state["n_conc1"] = n_conc_layer1(layers, n_nh4 if n_nh4 is not None else 0.0, no3_layers, (n_no3 or 0.0) if n_nh4 is not None else n_pool)
                sixpool_state["n_conc_layers"] = n_conc_layers(layers, n_nh4 if n_nh4 is not None else 0.0, no3_layers, (n_no3 or 0.0) if n_nh4 is not None else n_pool)
                _DIAG_CTX["doy"] = w["doy"]
                sixpool_state["wx_day"] = (w["tx"], w["tn"], w["pp"]); sixpool_state["rtz_k"] = crop.get("weps_k")
                background_today = sixpool_step(sixpool_state, tmean, relwet_topsoil, root_c_input_today, ft_eff, layers)
                if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("netmin", ()):
                    background_today = _FORCE_CUR["netmin"][w["doy"]]
                # background_today can now be genuinely negative (net immobilization -- see
                # sixpool_step()'s own docstring, 2026-10-02) -- floored at 0 here because a
                # real mineral-N pool can't go physically negative (immobilization is
                # substrate-limited in reality; this simplified day-by-day accounting isn't),
                # not because a negative value is itself wrong.
                if n_pool_by_layer is not None:
                    n_pool_by_layer[0] = max(0.0, n_pool_by_layer[0] + background_today)
                elif n_nh4 is not None:
                    n_nh4, n_no3 = apply_net_min(n_nh4, n_no3, no3_layers, background_today, sixpool_state)  # background mineralization is
                    # ammonification -- NH4 first, by definition -- see nh4_no3_split's docstring
                else:
                    n_pool = max(0.0, n_pool + background_today)
            elif dGB_water_limited > 0:
                weather_factor = (rothc_temp_factor(tmean) * rothc_moisture_factor(layers[0]["theta"], layers[0]["fc"], layers[0]["pwp"])
                                   / ROTHC_WEATHER_FACTOR_NORM)  # see ROTHC_WEATHER_FACTOR_NORM's own docstring -- fixed 2026-09-29
                background_today = BACKGROUND_N_KG_HA_DAY * (1.0 + tillage_ft(tillage_dr, tillage_ftx_val)) * weather_factor
                if n_pool_by_layer is not None:
                    n_pool_by_layer[0] += background_today
                elif n_nh4 is not None:
                    n_nh4 += background_today
                else:
                    n_pool += background_today
            if n_pool_by_layer is not None:
                n_pool = sum(n_pool_by_layer)  # scalar view, kept in sync -- used below for the
                # demand-capping comparison exactly as before; n_pool_by_layer is the only
            elif n_nh4 is not None:
                n_pool = n_nh4 + n_no3  # scalar view, kept in sync the same way n_pool_by_layer's is
                # authoritative store when active, this is never written back to it
            # biomass is already in Mg/ha (the same units n_critical_pct/n_marginal_demand_pct's
            # own docstrings and NCRIT_FLOOR_MGHA expect) -- a real bug here, found 2026-09-28
            # while "nailing down corn": this block used to pass biomass*10 to both functions
            # (a stray, mislabeled "biomass_before_mg_ha" conversion that was never actually
            # Mg/ha) and separately applied the Mg-to-kg/pct conversion factor of 10 TWICE in
            # demand_today_kg_ha below, inflating daily nitrogen demand by roughly an order of
            # magnitude. Caught by the standard sanity check every other N mechanism in this
            # file is held to (a very-high n_rate should converge to the no-tracking baseline)
            # -- corn instead capped at the exact same ~133 kg/ha uptake and ~4.65 Mg/ha grain
            # whether given 150 or 2000 kg N/ha, since demand so badly outstripped any real
            # supply that more fertilizer could never matter. Verified fixed: N=150 through
            # N=2000 all now reproduce the unconstrained baseline exactly for a representative
            # year. Corn's own DEFAULT validation (n_rate_kg_ha=None) never executes this block
            # at all, so this fix does not change corn's validated 0.527 correlation -- but it
            # does change any crop (wheat, by default; corn/silage corn/soybean if a caller
            # turns nitrogen on, e.g. model-validation.html's own controls) that already wires
            # nitrogen in, since every one of them was running this same buggy math.
            if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("plantn", ()):
                canopy_n_kg_ha = _FORCE_CUR["plantn"][w["doy"]]   # diagnostic: plant N content forced to Cycles' own (force_uptake.py)
            n_crit_pct = n_critical_pct(biomass * 10, crop, crop.get("n_stress_crit_floor", N_STRESS_CRIT_FLOOR_MGHA))
            n_min_pct = crop.get("n_min_conc", 0.0) * 100
            n_actual_pct = (canopy_n_kg_ha / (biomass * 100) if biomass > 1e-6
                            else crop["n_max_conc"] * 100)
            if crop.get("n_stress_ag_basis", N_STRESS_AG_BASIS):
                # step 14: Cycles' stress is a function of the ABOVEGROUND nitrogen concentration over the critical curve at the
                # plant's biomass (167k daily corn records, 28 sites): 0.764 x ((0.641 - r)/0.36)^0.9 between r = 0.641 and 0.281,
                # flat below. Aboveground N is 0.87 to 0.89 of the plant total throughout the season.
                _ag_eff = ag_biomass
                _ag_pct = (N_AG_FRACTION * canopy_n_kg_ha / (_ag_eff * 100)) if _ag_eff > 1e-6 else crop["n_max_conc"] * 100
                _ratio = _ag_pct / n_crit_pct if n_crit_pct > 0 else 1.0
                n_stress = n_stress_from_ratio(_ratio, crop)
            else:
                _ratio = n_actual_pct / n_crit_pct if n_crit_pct > 0 else 1.0
                n_stress = max(0.0, min(1.0, (_ratio - N_STRESS_FULL_RATIO) / (N_STRESS_ZERO_RATIO - N_STRESS_FULL_RATIO)))
                if N_STRESS_FLOOR_RATIO > 0.0 and _ratio < N_STRESS_KNEE_RATIO:
                    _knee = (N_STRESS_KNEE_RATIO - N_STRESS_FULL_RATIO) / (N_STRESS_ZERO_RATIO - N_STRESS_FULL_RATIO)
                    n_stress = max(0.0, _knee * (_ratio - N_STRESS_FLOOR_RATIO) / (N_STRESS_KNEE_RATIO - N_STRESS_FLOOR_RATIO))
            if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("nstress", ()):
                n_stress = _FORCE_CUR["nstress"][w["doy"]]
            if crop.get("n_simultaneous", N_SIMULTANEOUS) and not crop.get("legume_n", False) and n_nh4 is not None and no3_layers is not None and dGB_water_limited > 0 and not (_FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("nstress", ())):
                # 2026-10-19: CropSyst-style simultaneous solve (Stockle, Martin, Campbell 1994, Eq. 29 and 30): the day's N factor is the one consistent with the day's uptake and the
                # growth it permits. Fixed point on F: growth = potential x F, demand from that growth, uptake = min(supply cap, demand), concentration after the uptake over the
                # above-ground biomass including the POTENTIAL growth (the dilution the plant is trying to make), critical curve at the biomass after realized growth, F = law(ratio).
                _acc = layer_depth_fraction_within(layers, root_depth)
                _reach = n_nh4 + sum(max(0.0, no3_layers[_i] - N_UPTAKE_FLOOR_MGKG * sixpool_bulk_density(layers[_i]["sat"]) * layers[_i]["thick"] * 10.0) * _acc[_i] for _i in range(len(layers)))
                _urs = crop.get("n_uptake_rate", N_UPTAKE_RATE_PER_DAY)
                _caps = _reach if _urs is None else _reach * _urs
                if crop.get("n_uptake_gj", GJ_N_UPTAKE):
                    _caps = min(_reach, gj_n_uptake_cap(layers, root_depth, no3_layers, n_nh4, max(GJ_SEED_ROOT_KG_HA, (biomass - ag_biomass) * 1e4 / (crop.get("root_retained_frac", 1.0) if GJ_ROOT_TOTAL else 1.0)), crop.get("gj_srl"), gj_rl if GJ_RLV_STATE else None))
                _sf_s = shoot_fraction(ttf, crop["fsti"], crop["fstf"], crop.get("ttf50")); _rr_s = crop.get("root_retained_frac", 1.0)
                _bf = (1.0 if _rr_s >= 1.0 else (_sf_s + (1.0 - _sf_s) * _rr_s))
                _mdp = n_marginal_demand_pct((biomass_ref if crop.get("n_demand_ref", N_DEMAND_REF) else biomass) * 10, crop) * crop.get("n_demand_scale", N_DEMAND_SCALE)
                _F = n_stress
                for _it in range(10):
                    _dem = dGB_water_limited * (_F ** N_STRESS_GROWTH_POW) * _bf * 100 * _mdp
                    _U = min(_caps, _dem)
                    _agp = ag_biomass + dGB_water_limited * _sf_s
                    _ratio_s = (N_AG_FRACTION * (canopy_n_kg_ha + _U) / (_agp * 100)) / n_critical_pct((biomass + dGB_water_limited * _F * _bf) * 10, crop, crop.get("n_stress_crit_floor", N_STRESS_CRIT_FLOOR_MGHA)) if _agp > 1e-6 else 1.0
                    _Fn = n_stress_from_ratio(_ratio_s, crop)
                    _F = 0.5 * _F + 0.5 * _Fn
                if N_SOLVE_DEBUG is not None: N_SOLVE_DEBUG.append((_DIAG_YEAR, w["doy"], _F, _ratio_s, _U, _dem, _caps, canopy_n_kg_ha, _agp, biomass, dGB_water_limited))
                n_stress = _F
            if crop.get("legume_n", False): n_stress = 1.0   # N demand above what the soil supplies is met by fixation (paper Sec 2.5): no N stress
            dGB_n_limited = dGB_water_limited * (n_stress ** N_STRESS_GROWTH_POW)
            n_stress_prev = n_stress
            _sf_now0 = shoot_fraction(ttf, crop["fsti"], crop["fstf"], crop.get("ttf50")); _rr0 = crop.get("root_retained_frac", 1.0)
            demand_today_kg_ha = dGB_n_limited * (1.0 if _rr0 >= 1.0 else (_sf_now0 + (1.0 - _sf_now0) * _rr0)) * 100 * n_marginal_demand_pct((biomass_ref if crop.get("n_demand_ref", N_DEMAND_REF) else biomass) * 10, crop) * crop.get("n_demand_scale", N_DEMAND_SCALE)
            if n_pool_by_layer is not None:
                # Real CropSyst-style min(demand, potential_uptake) (Eq. 26, Stockle/Martin/
                # Campbell 1994) -- potential_uptake is however much of the pool currently
                # sits within reach of the crop's own real root_depth, not the whole profile
                # regardless of root depth. See layer_depth_fraction_within()'s own docstring.
                access_frac = layer_depth_fraction_within(layers, root_depth)
                accessible_n = [n_pool_by_layer[i] * access_frac[i] for i in range(len(layers))]
                potential_uptake_kg_ha = sum(accessible_n)
                n_uptake_kg_ha = min(n_pool, demand_today_kg_ha, potential_uptake_kg_ha)
                if potential_uptake_kg_ha > 1e-9:
                    for i in range(len(layers)):
                        n_pool_by_layer[i] -= n_uptake_kg_ha * (accessible_n[i] / potential_uptake_kg_ha)
                n_leached_total += n_leached_today  # already computed by infiltrate() above,
                # in lockstep with the SAME drainage fluxes this call's water balance used --
                # replaces the profile-wide ratio formula below for this mechanism only
            elif n_nh4 is not None:
                # Uptake draws from both pools together (a real plant takes up either form),
                # split proportionally to each pool's own current share for bookkeeping, since
                # no real preference is disclosed or assumed. Leaching then uses the NO3
                # concentration specifically, not the combined pool -- see nh4_no3_split's
                # own docstring for the real evidence (NH4 leaching <1% of total in Cycles'
                # own output) motivating this over the old combined-pool ratio formula below.
                if no3_layers is not None:
                    # Plant takes up NH4 (surface pool) plus only the nitrate in layers its roots
                    # have actually reached (same real-root-depth access n_root_limited uses).
                    access = layer_depth_fraction_within(layers, root_depth)
                    if N_UPTAKE_FLOOR_MGKG:
                        # step 14: the crop cannot pull nitrate below a floor concentration. In Cycles' own output the root-zone
                        # mean nitrate concentration separates N-stressed from unstressed days: 57% stress below 0.5 mg/kg,
                        # 26% at 0.5-1, 0-4% above 1 (14 sites, N=0 and N=150, 80k season days).
                        _avail = [max(0.0, no3_layers[i] - N_UPTAKE_FLOOR_MGKG * sixpool_bulk_density(layers[i]["sat"]) * layers[i]["thick"] * 10.0) * access[i]
                                  for i in range(len(layers))]
                        reach_no3 = sum(_avail)
                    else:
                        _avail = [no3_layers[i] * access[i] for i in range(len(layers))]
                        reach_no3 = sum(_avail)
                    reachable = NH4_UPTAKE_W * n_nh4 + reach_no3
                    _ur = crop.get("n_uptake_rate", N_UPTAKE_RATE_PER_DAY)
                    _cap = reachable if _ur is None else reachable * _ur
                    if crop.get("n_uptake_gj", GJ_N_UPTAKE):
                        _cap = min(reachable, gj_n_uptake_cap(layers, root_depth, no3_layers, n_nh4, max(GJ_SEED_ROOT_KG_HA, (biomass - ag_biomass) * 1e4 / (crop.get("root_retained_frac", 1.0) if GJ_ROOT_TOTAL else 1.0)), crop.get("gj_srl"), gj_rl if GJ_RLV_STATE else None))
                    n_uptake_kg_ha = min(_cap, demand_today_kg_ha)
                    if _FORCE_CUR is not None and w["doy"] in _FORCE_CUR.get("uptake", ()):
                        n_uptake_kg_ha = min(reachable, _FORCE_CUR["uptake"][w["doy"]])   # diagnostic: Cycles' own daily plant N uptake
                    if reachable > 1e-9:
                        frac = n_uptake_kg_ha / reachable
                        n_nh4 = max(0.0, n_nh4 - NH4_UPTAKE_W * n_nh4 * frac)
                        for i in range(len(layers)):
                            no3_layers[i] = max(0.0, no3_layers[i] - _avail[i] * frac)
                    _rr_sink = crop.get("rhizo_rr", _rr0)   # a crop whose growth path keeps all root growth (wheat) names the lost share here; Cycles loses 40% of root growth for every crop
                    if RHIZO_N_UPTAKE and _rr_sink < 1.0 and n_uptake_kg_ha > 0:
                        # The root mass that leaves the plant (rhizodeposits, root turnover: 1 - root_retained_frac of root growth) carries N at the concentration of the retained roots,
                        # taken from the soil and returned to it as organic N. Sink = (lost / retained root mass) x root N = (1 - rr) / rr x (1 - N_AG_FRACTION) x uptake = 8.0% of
                        # uptake for corn. Measured on Cycles' daily budget at 24 sites: its mineral pool loses 0.082 (N=0) and 0.093 (N=150) x the plant N gain beyond the plant's
                        # own N (residual against plant N, corr -0.97 / -0.91); the new-growth concentration would give 14 to 15%.
                        _rh = n_uptake_kg_ha * crop.get("rhizo_root_n_share", 1.0 - N_AG_FRACTION) * (1.0 - _rr_sink) / _rr_sink   # root N share of plant N: corn 0.12, wheat 0.082 (Cycles daily output)
                        _left = reachable - n_uptake_kg_ha
                        if _left > 1e-9 and _rh > 0:
                            _rh = min(_rh, _left); _f2 = _rh / _left
                            n_nh4 = max(0.0, n_nh4 - NH4_UPTAKE_W * n_nh4 * _f2)
                            for i in range(len(layers)):
                                no3_layers[i] = max(0.0, no3_layers[i] - no3_layers[i] * access[i] * _f2)
                            n_rhizo_total += _rh
                    n_no3 = sum(no3_layers)
                    n_pool = n_nh4 + n_no3
                else:
                    n_uptake_kg_ha = min(n_pool, demand_today_kg_ha)
                    if n_pool > 1e-9:
                        n_nh4 = max(0.0, n_nh4 - n_uptake_kg_ha * (n_nh4 / n_pool))
                        n_no3 = max(0.0, n_no3 - n_uptake_kg_ha * (n_no3 / n_pool))
                profile_water_mm = sum(l["theta"] * l["thick"] * 1000 for l in layers)
                if no3_layers is None and profile_water_mm > 0 and n_no3 > 0 and drainage_mm > 0:
                    leached_kg_ha = drainage_mm * (n_no3 / profile_water_mm)
                    n_no3 = max(0.0, n_no3 - leached_kg_ha)
                    n_leached_total += leached_kg_ha
                n_pool = n_nh4 + n_no3
            else:
                n_uptake_kg_ha = min(n_pool, demand_today_kg_ha)
                n_pool -= n_uptake_kg_ha
                profile_water_mm = sum(l["theta"] * l["thick"] * 1000 for l in layers)
                if profile_water_mm > 0 and n_pool > 0 and drainage_mm > 0:
                    leached_kg_ha = drainage_mm * (n_pool / profile_water_mm)
                    n_pool = max(0.0, n_pool - leached_kg_ha)
                    n_leached_total += leached_kg_ha
            n_uptake_total += n_uptake_kg_ha
            if crop.get("legume_n", False):
                _fixed_today = max(0.0, demand_today_kg_ha - n_uptake_kg_ha)   # "without luxury consumption": fixation exactly fills the unmet new-growth demand
                n_fixed_total += _fixed_today
                canopy_n_kg_ha += _fixed_today
            canopy_n_kg_ha += n_uptake_kg_ha

        if DIAG_NSEASON is not None:
            DIAG_NSEASON.append((_DIAG_YEAR, w["doy"], locals().get("background_today", 0.0), locals().get("nitrif_amt_today", 0.0), locals().get("volat_amt_today", 0.0),
                                 locals().get("denitrif_today", 0.0), locals().get("n_leached_today", 0.0), locals().get("n_uptake_kg_ha", 0.0), (n_nh4 or 0.0) + (n_no3 or 0.0)))
        dGB = dGB_water_limited * (n_stress ** N_STRESS_GROWTH_POW)
        if DIAG_STATE is not None: DIAG_STATE.append((_DIAG_YEAR, w["doy"], eie, n_stress, canopy_n_kg_ha))
        if DIAG_WATER is not None: DIAG_WATER.append((_DIAG_YEAR, w["doy"], water_stress, tt_cum, TRp, TR_actual, tt_dev))
        _sf_now = shoot_fraction(ttf, crop["fsti"], crop["fstf"], crop.get("ttf50"))
        _rr = crop.get("root_retained_frac", 1.0)
        biomass += dGB * (1.0 if _rr >= 1.0 else (_sf_now + (1.0 - _sf_now) * _rr))
        if GJ_RLV_STATE and crop.get("n_uptake_gj", GJ_N_UPTAKE):
            _fl = root_length_fraction_by_layer(layers, root_depth)
            if not gj_rl_seeded:
                gj_rl_seeded = True
                _add0 = GJ_SEED_ROOT_KG_HA * 0.1 * GJ_SRL_M_PER_G * 100.0 / 1e4
                for _i in range(len(layers)): gj_rl[_i] += _add0 * _fl[_i]
            _add = dGB * 1e4 * (1.0 - _sf_now) * 0.1 * crop.get("gj_srl", GJ_SRL_M_PER_G) * 100.0 / 1e4   # kg/m2 -> kg/ha -> g/m2 -> cm/g -> per cm2
            for _i in range(len(layers)): gj_rl[_i] += _add * _fl[_i]
        biomass_ref += (max(0.0, GR) * crop_ngf(crop) / 1000 if crop.get("n_demand_ref_rad") else dGB_water_limited) * (1.0 if _rr >= 1.0 else (_sf_now + (1.0 - _sf_now) * _rr))
        if DIAG_BIO is not None: DIAG_BIO.append(biomass * 10.0)
        ag_biomass += dGB * shoot_fraction(ttf, crop["fsti"], crop["fstf"], crop.get("ttf50"))
        if DIAG_AG is not None: DIAG_AG.append(ag_biomass * 10.0)
        if ag_biomass_at_flowering is None and (flowered if _V is not None else tt_cum >= crop["flowering_tt"]):
            ag_biomass_at_flowering = ag_biomass

        if (NPOOL_FORCE is not None or NLAYER_FORCE is not None) and no3_layers is not None and n_no3 is not None and n_nh4 is not None:
            n_no3, n_nh4 = _npool_hook(no3_layers, n_no3, n_nh4, w["doy"])
            if n_pool is not None:
                n_pool = n_no3 + n_nh4
        if record_history:
            history.append(dict(doy=w["doy"], ttf=round(ttf, 4), canopy=round(eie, 4),
                                 water_stress=round(water_stress, 4), n_stress=round(n_stress, 4), n_pool=round(n_pool, 2) if n_pool is not None else None,
                                 ag_mg_ha=round(ag_biomass * 10, 4), n_plant=round(canopy_n_kg_ha, 2),
                                 theta=[round(l["theta"], 4) for l in layers],
                                 n_no3=round(n_no3, 3) if n_no3 is not None else None,
                                 n_nh4=round(n_nh4, 3) if n_nh4 is not None else None,
                                 no3_layers=[round(x, 3) for x in no3_layers] if no3_layers else None,
                                 netmin=round(locals().get("background_today", 0.0) or 0.0, 4), denit=round(locals().get("denitrif_today", 0.0) or 0.0, 4), leach=round(n_leached_today or 0.0, 4),
                                 nitr=round(locals().get("nitrif_amt_today", 0.0) or 0.0, 4),
                                 soil_evap_mm=round(_sev_mm, 3), res_evap_mm=round(res_evap_today, 3), transp_mm=round(TR_actual, 3), eto_mm=round(eto, 3), trp_mm=round(TRp, 3), gr=round(GR, 4), gt=round(GT, 4), dgb=round(dGB, 6)))

        if tillage_dr > 0:
            tillage_dr -= tillage_dr * tillage_dr_decay(layers)

    # Real f_G (Kemanian, Stockle, Huggins & Viega 2007, Field Crops Res. 103:208-216 --
    # the actual source Kemanian et al. 2024 cites for this exact HI equation, but doesn't
    # itself give the definition of f_G): "the ratio of aboveground biomass produced after
    # anthesis to that for the entire growing season" -- a real GROWTH ratio, not a thermal-
    # time fraction. REPLACES an earlier substitute (fpf, thermal-time progress since
    # flowering) that advances on schedule regardless of how much the crop actually grew --
    # under severe, sustained stress, thermal time keeps accumulating even while post-
    # flowering growth stalls to near zero, so fpf pushed HI toward its maximum (hi_x)
    # in exactly the years it should instead stay near its minimum (hi_o). Found 2026-09-30
    # diagnosing a 13x overshoot in the single worst real Kansas year (2012, real grain
    # 0.115 Mg/ha): day-by-day water stress already tracked real Cycles reasonably closely
    # after the root-uptake depth fix, so the remaining gap pointed at HI itself, not water
    # stress. ag_biomass_at_flowering is None only if flowering never occurred before
    # harvest -- f_G=0 in that case (no post-flowering growth happened at all, so HI is
    # correctly at its minimum), matching the formula's own limit as tt_cum->flowering_tt.
    if crop.get("hi_use_thermal_time_fraction", False):
        # Real, disclosed exemption (2026-09-30), same precedent as WHEAT's existing
        # hydraulic-conductance exemption: wheat's own already-documented anomaly (a real
        # winter dormancy period corn/soybean don't have) made the real growth-based f_G
        # below measurably regress its correlation (0.337->0.163) even though f_G is the
        # more physically correct quantity and helped corn/soybean. Falls back to the
        # original thermal-time-progress substitute for wheat specifically, not a claim
        # that thermal time is right in general -- see f_g's own branch below.
        flowering_frac = crop["flowering_tt"] / crop["tt_maturity"]
        f_g = max(0.0, min(1.0, (tt_dev - crop["tt_maturity"] * flowering_frac) / (crop["tt_maturity"] * (1 - flowering_frac))))
    elif ag_biomass_at_flowering is None or ag_biomass <= 0:
        f_g = 0.0
    else:
        f_g = max(0.0, min(1.0, (ag_biomass - ag_biomass_at_flowering) / ag_biomass))
    HI = crop["hi_x"] - (crop["hi_x"] - crop["hi_o"]) * math.exp(-crop["hi_slope"] * f_g)
    biomass_mg_ha = biomass * 10
    ag_biomass_mg_ha = ag_biomass * 10
    grain_mg_ha = ag_biomass * HI * 10 * crop.get("calibration_factor", 1.0)
    forage_mg_ha = ag_biomass_mg_ha * crop.get("forage_fraction", 0.95) * crop.get("calibration_factor", 1.0)
    if winter_killed:
        grain_mg_ha = 0.0
        forage_mg_ha = 0.0
    result = dict(total=biomass_mg_ha, ag=ag_biomass_mg_ha, grain=grain_mg_ha, forage=forage_mg_ha,
                  runoff_mm=runoff_total)
    result["winter_killed"] = winter_killed
    if n_leached_total is not None:
        result["n_leached_kg_ha"] = n_leached_total
    if irrigation_trigger_frac is not None:
        result["irrigation_mm"] = irrigation_total_mm
    result["tt_cum_end"] = tt_cum
    if record_history:
        result["history"] = history
    if n_uptake_total is not None:
        result["n_uptake_kg_ha"] = n_uptake_total
        result["n_rhizo_kg_ha"] = n_rhizo_total
        result["n_fixed_kg_ha"] = n_fixed_total
        result["n_plant_kg_ha"] = canopy_n_kg_ha
        result["n_remaining_kg_ha"] = sum(n_pool_by_layer) if n_pool_by_layer is not None else n_pool
        if n_nh4 is not None:
            result["n_nh4_remaining_kg_ha"] = n_nh4
            result["n_no3_remaining_kg_ha"] = n_no3
    if n_volatilized_total is not None:
        result["n_volatilized_kg_ha"] = n_volatilized_total
    if n_volatilized_pool_total is not None:
        result["n_volatilized_pool_kg_ha"] = n_volatilized_pool_total
    if n_denitrified_total is not None:
        result["n_denitrified_kg_ha"] = n_denitrified_total
    if n_nh4 is not None:
        result["n2o_emitted_kg_ha"] = n2o_total
    if sixpool_state is not None:
        # Real stover left in the field after grain harvest -- AG biomass minus grain removed,
        # a defensible proxy (real Cycles' own harvest.txt "AG RESIDUE" column is conceptually
        # the same quantity), converted to carbon and credited into Cra right at harvest, i.e.
        # into the state a caller gets back for a FUTURE chained season -- unconditional, not
        # gated behind sixpool_offseason_decay, since this can never affect THIS season's own
        # already-computed result (grain/ag/HI are all finalized above this point); it only
        # matters if a caller later feeds sixpool_final_state into sixpool_initial_state. Found
        # testing sixpool_initial_state chained across Iowa's real 37-year record: omitting
        # this entirely (the original v1 scope) made the chain's own carbon pool -- and
        # therefore its background-nitrogen supply -- drain unrealistically over decades, since
        # nothing was ever returning carbon that the live crop's own root growth didn't already
        # provide. See sixpool_offseason_decay's own docstring for the other half of this fix
        # (letting it decompose for real before the next season, not carry forward untouched).
        # What leaves the field: grain for a grain crop, the clipped forage for a crop harvested before maturity (harvest_ttf < 1, silage: Cycles removes 90 percent
        # of the harvestable above-ground biomass, so the residue is the remainder, not above-ground biomass minus grain).
        _removed_mg_ha = forage_mg_ha if harvest_ttf < 1.0 else grain_mg_ha
        ag_residue_mg_ha = max(0.0, ag_biomass_mg_ha - _removed_mg_ha)
        # Surface residue C:N (2026-10-21): the new residue's N is the plant's above-ground N when the crop is flagged residue_n_from_plant (a cover crop,
        # whole plant returned); otherwise the long-run constant SIXPOOL_CN_CRA measured on Cycles' corn residue. The pool keeps one blended C:N.
        _c_new = ag_residue_mg_ha * CARBON_FRACTION_DM
        if crop.get("legume_n") and _c_new > 1e-9:
            _n_new = max(canopy_n_kg_ha * (1.0 - crop.get("grain_n_share", 0.54) - crop.get("root_n_share", 0.065)), 1e-3)   # Cycles' soybean harvest N partition (24 sites, 857 crop-years): grain 0.54, roots 0.065, above-ground residue 0.39 of plant N
        elif crop.get("residue_grain_n") is not None and _c_new > 1e-9:
            _n_new = max(N_AG_FRACTION * canopy_n_kg_ha * (1.0 - crop["residue_grain_n"]), 1e-3)   # grain N share of above-ground N leaves with the grain; the rest returns with the residue
        elif crop.get("residue_n_from_plant") and _c_new > 1e-9:
            _n_new = max(N_AG_FRACTION * canopy_n_kg_ha, 1e-3)
        else:
            _n_new = _c_new * 1000.0 / SIXPOOL_CN_CRA
        _c_old = sixpool_state.get("cra", 0.0); _n_old = _c_old * 1000.0 / sixpool_state.get("cra_cn", SIXPOOL_CN_CRA)
        if (crop.get("residue_n_from_plant") or crop.get("residue_grain_n") is not None or crop.get("legume_n") or "cra_cn" in sixpool_state) and _c_old + _c_new > 1e-9:
            sixpool_state["cra_cn"] = (_c_old + _c_new) * 1000.0 / max(_n_old + _n_new, 1e-9)
        _fs_new = crop.get("standing_at_harvest", RES_STANDING_AT_HARVEST)
        _c_add = ag_residue_mg_ha * CARBON_FRACTION_DM
        if _c_old + _c_add > 1e-9:
            sixpool_state["cra_fs"] = (sixpool_state.get("cra_fs", _fs_new) * _c_old + _fs_new * _c_add) / (_c_old + _c_add)
            sixpool_state["cra_kf"] = (sixpool_state.get("cra_kf", RES_K_FLAT) * _c_old + crop.get("res_k_flat", RES_K_FLAT) * _c_add) / (_c_old + _c_add)
        if crop.get("weps_k") is not None and (_c_old < 1e-9 or sixpool_state.get("cra_k") is not None):
            sixpool_state["cra_k"] = (sixpool_state.get("cra_k", crop["weps_k"]) * _c_old + crop["weps_k"] * _c_add) / max(_c_old + _c_add, 1e-12)
        else:
            sixpool_state["cra_k"] = None
        sixpool_state["cra"] = sixpool_state.get("cra", 0.0) + ag_residue_mg_ha * CARBON_FRACTION_DM
        # Reset cra_age to 0 whenever fresh stover lands -- see CRA_MATURATION_TAU_DAYS's own
        # docstring (2026-10-02). A disclosed simplification when cra already held some
        # un-decomposed carryover from a prior pulse: treats the WHOLE pool as freshly "reset"
        # to age 0 rather than tracking a real mixed-age blend, since this pool only ever
        # receives one discrete addition per season, not a continuous trickle.
        sixpool_state["cra_age"] = 0.0
        if root_hold_c > 0.0:
            if "ml" in sixpool_state:
                _wts = [math.exp(-_x["zmid"] / SIXPOOL_ML_ROOT_DECAY_M) for _x in sixpool_state["ml"]]; _ws = sum(_wts)
                for _x, _wv in zip(sixpool_state["ml"], _wts): _x["crtz"] += root_hold_c * _wv / _ws
            else:
                sixpool_state["crtz"] += root_hold_c
            root_hold_c = 0.0
        result["sixpool_final_state"] = copy.deepcopy(sixpool_state)
    if n_nh4 is not None:
        result["final_n_state"] = dict(n_nh4=n_nh4, n_no3=n_no3, tsoil_lag=tsoil_lag,
                                       no3_layers=list(no3_layers) if no3_layers is not None else None)
        result["last_doy"] = last_doy
    if initial_layers is not None:
        result["final_layers"] = layers
    return result
