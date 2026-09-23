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

## Resolved without asking (kept here for the record, not blocking)

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
