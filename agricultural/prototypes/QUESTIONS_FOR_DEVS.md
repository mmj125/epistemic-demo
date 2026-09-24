# Questions for the CYCLES developers

Running list, compiled while building an independent, from-scratch reimplementation
of CYCLES' published equations for classroom use (see CLAUDE.md, "Agricultural unit"
section, for the full context on why this is a from-scratch build rather than a port
of the real source). Intent: one short, specific list sent once we have a
classroom-workable tool, not an ongoing back-and-forth. Each item below is something
the public paper and its Supplemental Information don't specify precisely enough to
resolve from public information alone, verified by actually trying and checking
against real Cycles output before concluding the gap is real.

## Open

2. **Bare-soil and residue evaporation.** The SI's own process flowchart (Figure
   SI.2) marks "Soil Evaporation" and "Residue Evaporation" with the same "detailed
   in this SI" marker used for vegetation transpiration, but no evaporation equation
   is actually present anywhere in the document (SI Section II is transpiration
   only). What's the actual formula?

   **Update (2026-09-23):** implemented FAO-56's real, standard two-stage
   evaporation-reduction coefficient (Allen et al. 1998 Eq. 73-74, Kr driven by
   cumulative depletion since the surface was last wetted) in place of the old
   no-memory proxy -- a real, sourced, correctly-behaving mechanism (verified via
   a synthetic dry-down test showing the expected Stage-1-then-decelerating-
   Stage-2 shape), but it measured zero effect on any validated crop's
   correlation, since Rock Springs' rainfall resets the depletion counter before
   Stage 2 ever triggers in this record. This closes the "Kr" half of the real
   FAO-56 method; still open, unaddressed by that fix: Cycles' own actual
   evaporation formula (still undisclosed), the exact per-texture REW table
   (a single disclosed 9mm default is used instead), and FAO-56's own
   Kcmax-based potential-demand term (Eq. 72, not implemented -- this engine's
   own non-intercepted-radiation proxy still drives the potential-demand side).

4. **Perennial forage cutting trigger (`CLIPPING_BIOMASS_THRESHOLD_UPPER` /
   `HARVEST_TIMING` interaction).** For orchardgrass at Rock Springs (real
   `GenericCrops.crop` values verified directly: `MATURITY_TT=1500`,
   `CLIPPING_BIOMASS_THRESHOLD_UPPER=4` Mg/ha, `CLIPPING_BIOMASS_THRESHOLD_LOWER=1`
   Mg/ha, `HARVEST_TIMING=60`%, `STANDING_RESIDUE_AT_HARVEST=50`%,
   `RESIDUE_REMOVED=80`%), we've now ruled out four candidate trigger mechanisms
   with real data, not just two:
   - **Fixed absolute biomass threshold**: real pre-cut aboveground biomass across
     1982's four cuts is 2.24, 1.27, 2.25, 2.10 Mg/ha -- none within reach of the
     4.0 Mg/ha upper threshold (closest is 56% of it).
   - **Fixed thermal-time-since-last-cut threshold**: real Cycles' own daily
     THERMAL TIME column resets at each cut, but the thermal time accumulated
     between resets varies from 442 to 802 degree-days across the four 1982
     cuts -- there's no fixed value that would fit `HARVEST_TIMING=60%` of
     `MATURITY_TT` (which would predict a fixed ~900).
   - **Growth-rate plateau** (cut when regrowth stalls, regardless of absolute
     level): checked the daily aboveground biomass trajectory for all four days
     leading into each cut -- growth is steady and still increasing right up to
     the cut day every time, no slowdown.
   - **A simple fixed reset fraction after cutting**: comparing real Cycles' own
     pre-cut aboveground biomass (from `harvest.txt`'s TOTAL BIOMASS minus ROOT
     BIOMASS) against the very next value in the daily crop file (which already
     reflects the post-cut state) gives a strikingly consistent ~25% carryover
     ratio for 3 of the 4 real 1982 cuts (0.250, 0.250, 0.250) -- notably not the
     `STANDING_RESIDUE_AT_HARVEST=50%` crop-file value read naively, and not the
     literal `AG RESIDUE` harvest.txt column either (which nets out to ~5% of
     aboveground biomass and is evidently a separate "litter left on the ground"
     accounting, not the living carryover that continues to grow -- the
     harvest.txt FORAGE YIELD + AG RESIDUE columns already sum to 100% of AG
     biomass, so neither represents what's left standing). The same daily file's
     thermal-time reset also lands at a similar ~25-33% fraction of its pre-cut
     value in the same three cuts. One of the four cuts (1982-07-08, the one
     with by far the shortest pre-cut biomass, 1.27 Mg/ha) is an outlier on both
     measures at once (~34% and ~33%), suggesting a distinct rule may apply near
     the `CLIPPING_BIOMASS_THRESHOLD_LOWER=1` boundary. Implementing the 25%
     reset fraction (replacing an earlier attempt's 50% guess) on top of the
     unchanged dual biomass-OR-thermal-time trigger did not fix correlation
     (-0.276 -> 0.156, still not classroom-workable) and made the level bias
     worse (ratio 1.825 -> 3.305), since the larger residual regrows faster and
     causes more frequent cuts than reality.

   With all four mechanical hypotheses now ruled out by direct comparison against
   real per-cut data, what's left is either something not in the disclosed
   management parameters at all (a scheduling constraint, e.g. a minimum days-
   between-cuts rule, or a seasonal/photoperiod adjustment to the thermal-time
   target) or a genuinely different formula than "biomass OR thermal-time,
   whichever first." What is the actual trigger logic, and is the post-cut reset
   (both biomass and thermal time) really a fixed ~25% carryover, or does it
   depend on which threshold fired?

5. **Canopy-cover shape constants (Eq. 6's `a`, `b`, `c`, `d`) per crop.** The paper
   gives explicit defaults (6, -20, -15, 16) but states they "represent a normalized
   plant density (PDf) of 1" for the case demonstrated. Checked directly for winter
   wheat: at the point real Cycles shows 0.746 canopy cover (thermal-time fraction
   0.40), the same constants predict 0.886 -- a real, verified gap, not noise. Ruled
   out thermal-time accumulation as the cause first (our value: 1783.6 vs. real
   1740.76 by harvest, within 2.5% -- fine). Are there different shape constants per
   crop, or a correction beyond the stated `PDf` adjustment (Eq. 7) we're missing?
   Follow-up: even for corn itself the stated defaults run ~5% high at peak canopy
   (real 0.943 vs. predicted 0.990) -- negligible for grain corn (harvest happens
   well into senescence, after growth has already stopped) but compounds into a
   real, growing error for a crop harvested mid-peak-growth (confirmed directly:
   silage corn's aboveground biomass ratio to real output grows from 1.00 at
   mid-season to 1.25 by its 85%-of-maturity harvest point, tracking almost exactly
   with the compounding canopy-cover gap). A corn-specific refit (6, -20, -12, 12)
   helps the level bias but not silage corn's underlying correlation problem (item 6).

6. **Silage corn's and winter wheat's weak year-to-year correlation (0.50 and
   0.25) turn out to be two distinct problems, not one, after directly comparing
   our computed water stress against real Cycles' own WATER STRESS output column
   (day-by-day, not just season totals) -- worth being specific since we ruled out
   several things and want to avoid the devs re-suggesting them:

   - **Silage corn**: the *magnitude* of stress is right (our model and real
     Cycles both show severe stress, and real layer 1-3 soil moisture is
     genuinely down near wilting point, e.g. 0.13-0.17 m3/m3, during the real
     2016 stress peak -- a bona fide drought, nothing anomalous), but the
     *timing* is off by about 11 days (our stress onsets 2016-07-11, real onsets
     2016-06-30) and the within-event shape differs (real stress oscillates/dips
     through late July where ours rises smoothly). We tested three independent,
     principled fixes across all four already-validated crops (corn, soybean,
     wheat, silage corn) to see if any single recalibration closed this without
     breaking corn/soybean, which currently pass: (a) raising the "readily
     available water" stress-onset threshold from 0.5 toward 0.8, (b) slowing
     the root-growth-vs-thermal-time curve (root_depth = root_max*min(1,ttf/K)
     for K from 0.3 to 1.0), (c) widening bare-soil evaporation's extraction
     depth from one 5cm layer to FAO-56's standard evaporable-surface-layer
     depth Ze (0.10-0.30m, Allen et al. 1998 -- a real public constant, not a
     guess). None of the three meaningfully moved silage corn's correlation, and
     all three made corn/soybean modestly worse as the parameter increased. This
     points at the soil water *redistribution* physics itself (Eq. 1-2's actual
     sub-daily, capacitance-weighted flow, which our engine approximates with a
     same-day cascading bucket) rather than the crop-side stress-response
     formula -- see item 7 below, which is really the same underlying gap.

     **Update (2026-09-24, tested and discarded):** with the redistribution
     physics substantially improved since the above was written (real
     Saxton-Rawls secondary parameters, the closed-form Campbell Eq. 1
     conductivity function, sub-daily substepping), re-checked this specific
     gap directly against real Cycles' own `water.txt` per-layer output for
     2016. Silage corn's onset had actually drifted to 2016-07-14 (worse than
     the 11-day gap above) under this week's other changes; instrumenting the
     cause showed `root_zone_availability()` averages soil moisture *uniformly*
     across the whole root zone (1.55m by mid-season for silage corn), while
     the real per-layer data shows the top ~0.20m already near wilting point
     for weeks before the whole-profile average reflects it -- the flat average
     dilutes an already-dry topsoil against comparatively moist deeper layers.
     Found a real, citable fix for exactly this shape of problem: FAO-56
     Chapter 8's own "40-30-20-10 percent water extraction pattern... from the
     upper to lower quarters of the root zone," so re-weighted
     `root_zone_availability()` by depth-quarter using those real fractions
     instead of a flat average. Tested three weightings (40/30/20/10 as
     stated, an aggressive 70/20/10/0, and a mild 35/30/20/15) against the full
     four-crop suite. The standard 40/30/20/10 weighting did move silage
     corn's onset date the right direction (2016-07-14 -> 2016-07-11, a real
     3-day improvement, though still 11 days short of real Cycles' 2016-06-30)
     -- but every weighting tested, including the mildest, made aggregate
     correlation *worse* for every one of the four validated crops (baseline
     corn 0.547/soybean 0.858/wheat 0.399/silage corn 0.512; 40/30/20/10 gave
     0.543/0.852/0.385/0.488; the mild variant gave 0.537/0.856/0.377/0.502;
     the aggressive variant was worse still). Discarded, matching this
     project's standing discipline of not shipping a fix that improves one
     specific case at the expense of overall correlation (the same call
     already made once this session for a flat RUE-discount attempt and once
     for a fitted power-law water-stress curve). The idea itself remains
     physically well-motivated and real (unlike a guessed shape), so it's
     recorded here rather than silently dropped -- if this is revisited, note
     that the direction of the fix is right (weighting toward the topsoil
     helps this specific timing case) but naive depth-quarter weighting
     trades away accuracy elsewhere across the 9-37-year records for all four
     crops, not just this one drought event; a more targeted approach
     (perhaps blending flat and quarter-weighted only when the profile shows a
     steep enough moisture gradient) might be worth trying instead of a
     constant weighting applied every day regardless of profile shape.

   - **Winter wheat**: a much stranger anomaly, not a timing/shape issue at all.
     Real wheat yield correlates -0.89 with real Cycles' own max-per-season
     WATER STRESS across the 9 harvested years (1988-2015) -- confirming stress
     genuinely is the dominant driver of real yield variation, not a red
     herring. But our model's max-per-season stress only correlates 0.37 against
     real Cycles' max-per-season stress, and shows *zero* stress in three years
     (2003, 2009, 2012) where real Cycles reports 27-60%. Tracing the worst case
     (2012, real max stress 59.5% on 2012-03-16) against real Cycles' own
     water.txt output for that exact date: layer-1 soil moisture is 0.305 m3/m3
     against a field capacity of 0.339 -- only mildly depleted, about 83% of
     field capacity -- while the crop is still early vegetative growth
     (thermal time 755 of 1800 to maturity, 42%). No standard depletion-fraction
     stress function we're aware of would produce 60% stress from that mild a
     deficit. We first suspected our thermal-time engine was desynced from a
     real winter dormancy period Cycles might model that ours doesn't -- ruled
     out by comparing day-by-day thermal-time accumulation (not just the harvest
     total) against real Cycles' own THERMAL TIME column for the full
     1987-10-15 to 1988-07-07 season: every checkpoint matches within 1-3%,
     including both trajectories going flat in December-January. So the
     phenological calendar itself is fine. What's left: either (a) wheat's real
     root-growth-vs-thermal-time curve is far shallower/slower early on than
     the shape we're using for every crop (meaning a much smaller root zone is
     being checked for depletion, and that thin zone dries out fast even from
     modest rain gaps), or (b) wheat's actual water-stress function is far more
     sensitive/nonlinear than a linear depletion ramp, or (c) something early
     season-specific (cold soil restricting uptake, a minimum-root-depth floor)
     that isn't a "water stress" mechanism in the way we've modeled it at all.
     What is wheat's actual root growth function, and does WATER STRESS for
     wheat reflect soil moisture alone or something else layered on top?

     **Update (2026-09-24):** checked hypothesis (a) directly against the real
     crop file rather than guessing further -- `GenericCrops.crop` has no
     per-species root-growth-RATE parameter at all, for wheat or any other
     crop; `MAXIMUM_ROOTING_DEPTH` (already wired in for every crop) is the
     only real root-related field that exists. So (a) can't be resolved with
     disclosed data as stated -- there's no real number to swap in for a
     species-specific curve shape, only the same generic
     `root_depth=root_max*min(1,ttf/0.5)` shape every crop already shares.
     This doesn't rule out a real underlying root-growth-rate difference in
     actual Cycles, only that it isn't in the one crop-parameter file we have
     access to -- narrows the open question to (b) or (c), or a genuinely
     undisclosed root-growth formula.

7. **The soil water redistribution scheme (Eq. 1-2) -- largely resolved, one piece
   still open.** Originally: the paper gives the real capacitance-weighted flow
   equation (khe as a function of saturated hydraulic conductivity ks, air-entry
   potential psi_e, and the moisture-release-curve exponent b) but we lacked a
   verified source for Saxton and Rawls (2006)'s own secondary formulas for those
   three soil-texture-dependent quantities. **Update:** Matt independently obtained
   the real Saxton & Rawls (2006) paper directly (a PDF, since this sandbox's own
   network policy blocked every mirror tried), and we implemented and verified all
   three secondary parameters against the paper's own Table 3 worked examples to
   the displayed precision. Separately, derived a real closed-form solution to
   Eq. 1's own literal integral (substituting Campbell's 1974 power-law moisture-
   release curve collapses both the numerator and denominator to simple power
   functions), verified against brute-force numerical integration to ~1e-15
   relative error, and implemented with 24-substep-per-day numerical integration
   (Eq. 2's own adaptive step-size scheme approximated by a fixed, sufficiently
   fine count -- checked directly that 24 is already converged: 96 and 480
   substeps move nothing beyond the third decimal). This IS now real redistribution
   physics, not the bucket approximation described above. What's left open: this
   is still a same-day (not truly sub-daily/multi-day) integration of the governing
   rate law, and its effect on the four validated crops' correlations was small and
   mixed (a genuine, if modest, net improvement for corn/soybean/silage-corn, no
   improvement for wheat) -- consistent with our own finding that wheat's anomaly
   (above) looks like a separate, crop-specific issue on top of this, not primarily
   a redistribution-physics gap.

8. **Cold damage's exact effect on canopy and thermal time is disclosed
   qualitatively but never quantified anywhere we could find.** The main paper
   states plainly that "haying, grazing, tillage, and cold damage reduce
   [interception] and [thermal-time fraction], rejuvenating the canopy" (Sec. 2.4)
   -- the same category of effect as a cutting/grazing event, not a simple growth-
   rate penalty. Real, per-crop `MIN_TEMPERATURE_FOR_COLD_DAMAGE`/
   `THRESHOLD_TEMPERATURE_FOR_COLD_DAMAGE` values exist in `GenericCrops.crop` and
   are dramatically differentiated by crop (corn/soybean: threshold ~2-3 deg C, min
   -5 deg C; winter wheat: threshold -10 deg C, min -25 deg C) -- real data,
   currently unused entirely. Checked how often this would actually trigger before
   investing further: corn's real threshold is crossed on 246 days across the full
   37-year Rock Springs record (its own min is never reached), and wheat's is
   crossed on 610 days across its real fall-to-summer seasons -- this is not a rare
   edge case for either crop. Searched the general crop-modeling literature (not
   just Cycles' own sources) for a portable cold-damage function: confirmed linear/
   trapezoidal threshold-to-minimum response functions are the standard shape used
   elsewhere (STICS, WOFOST), and a real "Frost Damage Index" concept exists
   specifically for wheat canopy-cover loss with a base temperature of -9 deg C
   (strikingly close to Cycles' own -10 deg C wheat threshold, a real corroborating
   cross-check) -- but no source found gives an implementable formula for the
   MAGNITUDE of the canopy/thermal-time "rejuvenation," only its qualitative shape
   and plausible threshold range. This is the same open category of problem as
   item 4 (the pasture cutting trigger) -- a real, disclosed "reset" mechanism
   whose exact reset magnitude isn't recoverable from any source tried. Not
   implemented rather than guessed at, per this project's own standing discipline.
   What is the actual formula (or its Kemanian & Stockle 2010 / Camargo & Kemanian
   2016 citable source, if one exists) for how much cold damage reduces interception
   and thermal-time fraction?

9. **What reduces `RADIATION_USE_EFFICIENCY` from its stated "Maximum eR" (Table
   SI.2's own heading) to a day's actual value?** A real, consistent gap exists even
   under warm, zero-stress conditions -- backed out directly from real Cycles'
   own daily BIOMASS output (dB[Mg/ha]*100 / (FRAC_INTERCEP*solar_MJ) = implied
   g/MJ). The original estimate (corn 0.744, silage corn 0.754, wheat 0.736,
   soybean 0.640) turned out to be partly a measurement artifact -- many sampled
   days were actually water-limited or ambiguous in this engine's own water
   balance, not purely radiation-limited the way the method assumed. Restricting
   to the cleanest, most unambiguous days (this engine's own GT/GR ratio > 1.5)
   gives a smaller but still real residual gap of 0.785 (n=23, stdev 0.039).
   **The workaround is now implemented** (`NET_GROWTH_FRACTION` in
   `cycles_engine_validate.py`, see the "Resolved" entry below) as a discount
   applied AFTER the min(GR, GT) choice rather than to GR beforehand -- this
   fixes the resulting biomass-level bias with zero effect on grain correlation
   (verified, not assumed), sidestepping the correlation-breaking problem a flat
   discount on GR alone caused (it makes radiation the binding constraint far
   more often, moving a synthetic corn test from 38-46% radiation-limited days to
   81-85%, which washes out the model's sensitivity to real, water-driven
   year-to-year yield variation). This closes the practical problem but NOT the
   underlying question: a CO2-reference scaling (the paper notes "εR... should be
   given for a reference atmospheric CO2 concentration and scaled accordingly as
   CO2 changes") is one candidate, but doesn't obviously explain why the effect
   would be roughly constant rather than varying by simulation year. **What is
   the real conversion (or additional factor) that turns "Maximum eR" into the
   value actually used day to day, and does real Cycles apply it before or after
   the radiation/water co-limitation choice** (the distinction that made this
   workaround succeed where a naive one failed)?

## Resolved without asking (kept here for the record, not blocking)

- **Real per-crop `THERMAL_TIME_TO_EMERGENCE` wired in -- confirmed correct, a tiny effect.**
  Real Cycles' own daily crop output has an explicit `PRE_EMERGENCE` stage with EXACTLY zero
  biomass from planting through this threshold (verified directly against real output: corn's
  own biomass column is 0.000000 through thermal time 64.47, then 0.001000 the very next day
  at 69.997 -- a hard cutoff at the crop file's own real value, 65). This engine's canopy-cover
  formula, by contrast, gives a small but nonzero value even at ttf=0 (e.g. eie~0.0025 for
  corn), so some (tiny) growth was happening before real Cycles would allow any at all. Gated
  `eie` to exactly 0 before `crop.get("tt_emergence", 0.0)` is reached, which zeroes both
  radiation- and transpiration-limited growth exactly (both terms are literally multiplied by
  `eie`). Real per-crop values wired in: corn/silage corn 65, soybean 70, wheat 100
  (degree-days). Effect on the four validated crops' correlations: none to three decimals
  (0.544/0.846/0.276/0.510-0.511 unchanged); means shifted by ~0.01 Mg/ha at most, small enough
  that each crop's `calibration_factor` only needed a 4th-decimal nudge. Kept regardless, same
  standard as `TRANSPIRATION_MAX` and root depth -- real, disclosed, verified correct against
  real output, genuinely negligible at this model's current precision but not wrong to have.
- **Real per-crop `MAXIMUM_ROOTING_DEPTH` wired in -- confirmed correct, currently a null
  result everywhere we've tested it.** `root_max_m` (the parameter controlling how deep a
  crop's roots can reach for soil moisture) had been a single hardcoded 1.4m shared by every
  crop, when the real, disclosed per-crop values differ substantially: corn/wheat 2.0m,
  soybean 1.5m, silage corn 1.55m. Wired in via `crop.get("root_max_m", root_max_m)`,
  overriding the shared default when a crop dict sets its own value. Ran the full validation
  suite and got byte-for-byte the same correlations and means as before (to 3 decimals) --
  traced this to a real, satisfying explanation rather than assuming the fix did nothing: the
  hand-curated Rock Springs soil profile this project's own validation harnesses use is
  exactly 1.4m deep (9 layers summing to 1.4m precisely, apparently why 1.4m was chosen as
  the old shared default in the first place), so no crop's real 1.5-2.0m root system can ever
  reach soil this engine doesn't model in the first place. Checked independently: the real
  STATSGO2-resolved soil cell nearest Rock Springs (Hazleton series) is 1.42m, and even Iowa's
  own real Canisteo cell (a deep prairie soil, used elsewhere in this project) only reaches
  1.52m -- every real soil profile this project has access to for any site caps out well
  short of 2.0m, so this isn't a Rock-Springs-specific coincidence. Confirmed the mechanism
  itself works correctly with a synthetic test (Iowa's own real 1.52m soil profile, Rock
  Springs' real 2012 drought-year weather): root_max_m=2.0 measurably outyields root_max_m=1.4
  (+0.14 Mg/ha) once the profile is deep enough to expose the difference. Kept the real values
  regardless of the current null result, same standard as `TRANSPIRATION_MAX` earlier the same
  day -- this would matter immediately if a genuinely deep-soil site or a more complete soil
  profile (below ~1.5m) is ever added.
- **Shoot/root partitioning's `TTf50` parameter, formerly item 3.** The equation and
  its shape parameters (`fsti`, `fstf`) are given (Eq. SI.8-11) but `TTf50` (the
  thermal-time fraction at half-max allocation) had no stated numeric value -- we'd
  used 0.5, the literal reading of the parameter's own name, as a placeholder.
  Resolved with real data instead of a guess: the equation implies the
  INSTANTANEOUS (marginal) shoot fraction of a day's new growth equals
  `shoot_fraction(ttf)` exactly (since `dAG = dGB*shoot_fraction(ttf)` and
  `dTotal = dGB`), so day-to-day differences in real Cycles' own daily AG BIOMASS/
  BIOMASS output give real, direct (ttf, marginal-fraction) data points to fit
  against. Pulled 5174 such points from four independent real daily-output files
  (two separate corn seasons, soybean, wheat) and fit `TTf50` against each
  independently: every one converged tightly to 0.315-0.335 (corn 0.320 and 0.317,
  soybean 0.316, wheat 0.335), a ~11x reduction in sum-of-squared-error versus 0.5
  (pooled fit: 0.3205, rounded to 0.32). Re-derived each validated crop's
  `calibration_factor` afterward to keep mean yield matching real output (the same
  residual-scale-correction step this project always takes after a shoot/root or
  canopy fix) -- correlation is scale-invariant under that step, so it's not
  double-counted. Net effect: wheat's correlation improved meaningfully (0.223 ->
  0.276, the largest single movement from any water/canopy fix this session), while
  corn/soybean/silage corn each moved slightly down (corn 0.546->0.544, soybean
  0.857->0.846, silage corn 0.523->0.510) -- kept despite the small net-negative
  spread on three of four crops, since this is a real, direct, strongly
  cross-validated measurement of the actual underlying quantity (not an inferred or
  guessed shape the way the reverted power-law water-stress fit was), and the
  literal-name 0.5 it replaces was never anything but a placeholder.
- **Curve-number moisture adjustment (`fwc`), formerly item 1.** SI Section III
  describes it only in words ("1 for a soil saturated to a depth of 0.6 m...
  decreases to zero if the soil is air dry... depth-weighted... surface having the
  most importance"), no exact formula. Rather than keep waiting on this, replaced it
  entirely with a real, independently sourced formula: SWAT's own soil-moisture-based
  retention-parameter equation (Neitsch et al., SWAT theoretical documentation, Eq.
  2:1.1.11-2:1.1.13) -- a continuous function of the whole soil profile's actual
  water content, anchored at three real points (dry/CN1 as an asymptote, field
  capacity/CN3, and CN=99 at full saturation), not the 0.6m-depth-weighted guess this
  replaces. Verified by reproducing all three anchor points to full float precision
  before trusting it (`retention_param_mm()` in `cycles_engine_validate.py`). Effect
  on the four validated crops' correlations was small and mixed (corn -0.003, soybean
  +0.003, wheat +0.007, silage corn -0.007) -- kept anyway since it's a real,
  disclosed, better-sourced mechanism, the same standard already applied to the
  runoff/spin-up/Ksat-rate-cap fixes that also moved little or nothing. This sandbox's
  network policy still blocks the primary SWAT source directly (swat.tamu.edu,
  swatplus.gitbook.io) -- the equation came from web-search summaries, not a direct
  read, so worth a final cross-check against the primary document if it's ever
  reachable.
- Cycles' `HARVEST_INDEX` is grain ÷ *aboveground* biomass, not total -- worked out
  by checking real output arithmetic directly (11.61 / (26.17 - 3.48) = 0.5117,
  matching the real reported value).
- Two likely sign errors in the SI's typeset equations (curve-number runoff
  denominator; the wet-curve-number formula) were resolved by deriving from the
  external standard methods the SI itself cites (USDA-SCS 1972; Williams et al.
  2012), not by asking -- flagged in code, not on this list.
- **Radiation-limited growth under cold temperatures.** GenericCrops.crop's
  `RADIATION_USE_EFFICIENCY` is explicitly labeled "Maximum eR" in the paper's own
  Table SI.2 heading -- neither source says what reduces it from that maximum to a
  day's actual value, and until now this engine applied it uncorrected. Diagnosed
  by backing out a day's ACTUAL radiation-use efficiency directly from real Cycles'
  own daily BIOMASS output (any day with zero N/water stress and canopy cover in a
  clean 0.15-0.85 range gives `dB[Mg/ha]*100 / (FRAC_INTERCEP * solar_MJ)` = implied
  g/MJ, no back-solving through yield needed) across the full real record for four
  crops. A real, if smaller, gap exists even on warm days for every crop
  (implied/nominal ratio ~0.64-0.75) -- tested as a flat multiplicative correction
  and found to make every crop's correlation WORSE despite fixing the mean, so it
  was NOT implemented and remains open (below). The gap that DOES generalize is on
  cold days specifically: wheat's raw, temperature-unadjusted implied RUE averages
  under 0.35 of nominal across its cold fall-to-spring record, and this correlates
  far better with each crop's own EXISTING `transpiration_temp_factor`
  (`tr_min_t`/`tr_threshold_t`, pooled corr 0.69 across corn/soybean/wheat) than
  with a thermal-time-style factor (corr 0.53). Implemented by reusing that exact
  factor -- already computed for transpiration -- as a second multiplier on
  radiation-limited growth (`GR`), not inventing new per-crop cold thresholds.
  Verified: also feeding this engine real Cycles' own exact FRAC_INTERCEP
  trajectory in place of its own computed canopy cover (a direct substitution
  test) still showed total biomass running ~25-40% high all season before this
  fix, ruling out canopy shape as an alternative explanation. Re-derived each
  crop's `calibration_factor` afterward (mean already landed almost exactly on
  real output even before recalibrating). Net effect on the four validated
  crops' correlations: corn 0.544->0.547 (essentially flat), soybean
  0.846->0.858, wheat 0.276->0.397 (the single largest correlation jump this
  project has seen from any one fix), silage corn 0.510->0.512 (flat) -- and the
  mean-level match improved substantially for all four without any further
  tuning. A genuinely open question remains: **what actually causes the
  remaining ~25-35% warm-day gap between "Maximum eR" and a day's real, used
  value** (a CO2-reference scaling? a further, undisclosed conversion? something
  else?) -- real, measured, and consistently non-trivial to fit as a flat
  constant, so left as a disclosed, still-open item rather than guessed at
  further.
- **The warm-day radiation-use-efficiency gap itself, item 9's leftover --
  resolved as a post-limitation growth-conversion loss, not a discount on `GR`.**
  Re-diagnosed the ~25% warm-day gap and found the original measurement partly
  conflated water-limited days with radiation-limited ones (this engine's own
  GT/GR ratio, computed with nominal RUE, correlates smoothly with the implied-
  RUE ratio: 0.62 at GT/GR 0.6-0.9 up to 0.80 at GT/GR > 1.33). The cleanest,
  most unambiguous subset (GT/GR > 1.5, n=23, stdev 0.039) gives a real residual
  gap of 0.785, not the original ~0.74. Confirmed directly why item 9 was right
  to decline a flat discount on `GR`: doing so makes radiation the binding
  constraint far more often (a synthetic corn test moved from a real 38-46%
  radiation-limited baseline to 81-85%), which destroys the model's sensitivity
  to real, water-driven year-to-year yield variation -- the actual mechanism
  behind the correlation damage, not just an observed side effect. The fix:
  apply the 0.785 fraction to `min(GR, GT)` (`NET_GROWTH_FRACTION` in
  `cycles_engine_validate.py`) AFTER the limiting choice is made, not to `GR`
  before it. Since nothing else in this engine's day loop depends on cumulative
  biomass (canopy cover and root depth are pure functions of thermal time; soil-
  moisture extraction depends only on realized transpiration, not on how much
  biomass it produced), this is mathematically a uniform rescaling of the
  season's growth trajectory -- verified directly, not just reasoned, that it
  reproduces every validated crop's grain correlation to three decimals,
  completely unchanged. Re-derived each crop's `calibration_factor` to absorb
  the mean shift. Directly closes the gap `model-validation.html`'s own
  "Beyond final yield" table has repeatedly flagged: corn's uncalibrated total
  biomass error dropped from 32.2% to 7.0%, aboveground biomass from 32.7% to
  7.6%, both with zero change to grain's own correlation. Item 9's actual
  question -- what real mechanism produces this gap, and whether Cycles itself
  applies it before or after the radiation/water co-limitation choice -- remains
  open; this is a verified fix to the model's output, not an identification of
  the real cause.
- **Wheat needed its own radiation-temperature response, separate from the shared
  fix above -- a modest, real refinement.** Checked whether the shared 0.785
  fraction (item above) actually held for all four crops before assuming so:
  soybean's own clean-day (GT/GR > 1.5) implied ratio is 0.786 (n=5) and silage
  corn's is 0.806 (n=19), both matching corn almost exactly. Wheat's does not --
  n=117 clean days give mean 0.471, stdev 0.256, roughly half the shared value
  and far noisier. Traced why: every one of wheat's clean days fell in
  November-April (its real fall-to-early-summer season never reaches genuinely
  warm, unambiguous radiation-limited conditions), and the implied-RUE ratio
  within that subset still correlates strongly with temperature (corr 0.85) even
  after the existing cold-temperature fix is applied. A larger, cleaner sample
  (n=401, raw ratio with no temp correction pre-applied) regresses linearly
  against daily mean temperature as `ratio = 0.202 + 0.0375*tmean`, reaching the
  shared 0.785 plateau at ~15.55°C, not at wheat's own 12°C transpiration
  threshold (a real, distinct value never independently validated for
  radiation). The nonzero floor at 0°C (real Cycles keeps wheat growing at about
  a quarter of its eventual rate even near freezing, not zero) is real too.
  Implemented as a second temperature-response curve applied only to radiation-
  limited growth, defaulting to a no-op for any crop that doesn't set its own
  floor/plateau (verified: corn's reference number is byte-for-byte unchanged).
  Modest but real result for wheat: correlation 0.397 -> 0.399, total-biomass
  level bias 1.233x -> 1.204x of real output.

- **The critical-N-dilution curve's flat-below-1-Mg/ha threshold -- tested and not
  changed.** Checked whether the biomass threshold at which N concentration stops
  being flat at N_MAX_CONCENTRATION and starts declining (assumed to be exactly
  1 Mg/ha, matching the standard literature convention) actually matches real
  Cycles output. Pulled real (biomass, AG N CONCN) pairs at N STRESS=0 (so the
  crop is growing at its unconstrained potential, the only fair comparison)
  across corn, soybean, and wheat's own real daily crop-output files and grid-
  searched the best-fit threshold per crop, holding N_MAX_CONCENTRATION/
  N_DILUTION_SLOPE fixed at each crop's own real disclosed values. Each crop's
  best-fit threshold moved the fit meaningfully (corn 0.70, soybean 1.50, wheat
  0.15 -- 21-78% SSE reduction each), but the three values are wildly
  inconsistent with each other and with 1.0, with no real disclosed constant to
  anchor any one of them. Not implemented: this would be curve-fitting a free
  parameter per crop with no citable justification, the same category of
  mistake as the earlier reverted power-law water-stress fit. `n_max_conc`/
  `n_dilution_slope` are real, disclosed GenericCrops.crop values and stay
  exactly as they are; only the assumed threshold (never itself a disclosed
  Cycles parameter) was tested and left unchanged.

- **WHEAT was missing its own real `n_max_conc`/`n_dilution_slope` values in
  `run_validation_rotation2.py` -- fixed (2026-09-24).** While checking the
  N-dilution curve above, found the canonical validation script's WHEAT dict
  never had these two fields set at all, unlike CORN/SOYBEAN -- a real
  completeness gap (the embedded `ENGINE_SOURCE` copies in `engine-demo.html`/
  `model-validation.html` already had the correct real values, 0.07/0.45, so
  only the canonical script needed the fix). Added the real GenericCrops.crop
  values. Zero effect on validation (confirmed: all four crops' correlations
  unchanged to three decimals), since nothing calls `simulate_season()` for
  wheat with nitrogen tracking active anywhere in this project -- a pure
  data-completeness fix, not a behavior change.
