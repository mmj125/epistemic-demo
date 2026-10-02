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

   **Update (2026-09-28):** found a real, complete, alternate formula for bare-soil
   evaporation itself in CropSyst's own public C++ source (`Evaporator::evaporate_interval`,
   `CropSyst/source/soil/soil_evaporator.cpp`, `mingliangwsu/VIC-CropSyst-Package` on
   GitHub), fetched and read verbatim. A genuinely different shape than the FAO-56
   mechanism above: topsoil evaporates at the FULL potential rate with zero reduction
   until its own water content drops below wilting point, then falls off quadratically
   toward a real air-dry floor at exactly 1/3 of the wilting point's own value (CropSyst's
   own hardcoded constant); a second layer only evaporates when the field is fallow AND
   it's summer, capped at 75% depletion of its own field-capacity range. The source's own
   comment states its separate `mulch_cover_fraction` term is "material other than residue
   (i.e. plastic cover)" -- real, direct confirmation that residue's own evaporation
   reduction is a genuinely separate, still-undisclosed mechanism this file does not
   contain. This closes the "bare-soil evaporation" half of this item, not "residue
   evaporation." Implemented as `soil_evaporation_cropsyst()`, reachable via
   `simulate_season(soil_evap_model="cropsyst")` (default stays `"faostandard"`, byte-
   identical to every existing validated number). Verified structurally correct (five
   synthetic test cases covering every branch) and run against the real embedded Rock
   Springs weather across the full 37-year record: a real, non-trivial effect there (mean
   grain 10.56 -> 10.51 Mg/ha, 29 of 37 years show a nonzero difference) -- unlike every
   other water-balance refinement tried this session, which measured zero effect at humid
   Rock Springs. NOT validated against real Cycles output -- this sandbox's reference data
   (`/tmp/cycles-run`) does not exist in this container as of 2026-09-28, the only
   mechanism in this whole file that couldn't be checked against real per-year correlation
   before being written up. Kept as opt-in, not the default, specifically because of this.
   Whether it helps or hurts real accuracy is open until that validation can run.

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

   **Follow-up (2026-09-25), using CropSyst's own real, public source code**
   (`mingliangwsu/VIC-CropSyst-Package` on GitHub -- Cycles shares its biophysical
   fundamentals with CropSyst per the main paper, and unlike Cycles this repo
   actually has real `.cpp` source, not just compiled binaries). CropSyst's own
   `management/management_param_V5.cpp` implements clipping as three independent
   OR'd triggers, not one: a biomass ceiling (`biomass_forces_clipping`, default
   4000 kg/ha -- exactly matching Cycles' own `CLIPPING_BIOMASS_THRESHOLD_UPPER`),
   an LAI ceiling (`LAI_forces_clipping`, default 5.0), and a days-after-flowering
   trigger (`flowering_forces_clipping`, default 0 days). There's also a real
   `reserve_biomass` pool explicitly "unavailable for clipping" (a protected
   fraction the plant never risks losing, structurally different from a flat
   post-cut percentage) and a post-cut `adjust_relative_growth_rate_for_clipping`
   term (default 1.0, range 0.5-1.5) -- a growth-RATE adjustment after a cut,
   not a biomass reset at all, a mechanism never tested before.

   Tested this against real data before assuming it transfers: Cycles' own
   `GenericCrops.crop` has no LAI field or flowering-trigger field for any
   pasture species (confirmed directly) and no per-day LAI column in its own
   daily crop output either (`Orchardgrass.txt`'s header has no LAI, only
   `FRAC INTERCEP` as the closest analog) -- Cycles' own architecture has no LAI
   state variable at all (its canopy scheme is cover-based, Eq. 6), so CropSyst's
   literal LAI trigger has no path into Cycles as a numeric default; only its
   existence as a *structural* idea (a second, OR'd trigger besides biomass)
   transfers.

   Pulled 9 real cuts (all of 1982 and 1983, not just 1982's four) to re-test
   with a larger sample: real aboveground biomass at cut now ranges 0.32-4.38
   Mg/ha across the 9 cuts (1983's first cut, after the longest uninterrupted
   spring regrowth, is the ONE case that actually reaches the 4.0 Mg/ha ceiling
   -- every other cut stays well under it), and real thermal-time-since-reset
   ranges 648.8-898.1 degree-days, non-monotonic across a season (1982 rises
   653->802->828->890 across its four cuts; 1983 does not repeat that pattern,
   719->649->896->883->898) -- ruling out both "a fixed thermal-time target" and
   a revised guess of 60% of `FLOWERING_TT` (600, tested directly, doesn't match
   either). The ~25% post-cut carryover ratio (both biomass and thermal time)
   found in the original four 1982 cuts holds up in this larger sample too
   (1982-06-10: 210.7/801.8 = 26.3%). Confirmed `CLIPPING_START 1` /
   `CLIPPING_END 366` on the operation file spans the entire year -- clipping is
   genuinely automatic/threshold-triggered, not a fixed calendar schedule with
   these fields just marking an allowed window.

   **The most consequential real finding from this pass isn't about the trigger
   at all: `CornSoyWheatPasture.operation` plants Orchardgrass, WhiteClover, AND
   LotusCorniculatus simultaneously on the same day (DOY 75, year 3) at three
   different densities (0.68 / 0.16 / 0.16, summing to 1.0) -- a real mixed
   pasture stand, not the orchardgrass monoculture this project has validated
   against the whole time.** This has never been documented before in this
   project and may be a more fundamental reason the pasture rotation has never
   met the classroom-workable bar than any cutting-trigger formula: three
   competing species sharing light/water/nutrients at different densities is a
   structurally different system from a monoculture stand, and no version of
   this engine has ever modeled species competition or a density-weighted mixed
   canopy. Question for the devs, given the trigger mechanism above still isn't
   fully resolved: is the actual trigger logic closer to CropSyst's three-OR'd-
   condition structure (with real numeric LAI/flowering thresholds that exist
   somewhere in Cycles even though `GenericCrops.crop` doesn't expose them), and
   separately, does Cycles model inter-species competition in a mixed stand like
   this one, or does each species' `DENSITY` value scale its outcome independently
   with no shared-resource interaction at all?

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

   **Update, 2026-09-29 -- a much larger version of the same gap found at a real
   water-limited site, and the paper's own disclosed fix tested and rejected.**
   While digging into the water-balance/root-uptake mechanism at Kansas (per Matt's
   direct "Go dig into the water-balance/root-uptake mechanism at low-PAW soils
   next," following up on the multi-year Kansas ground truth obtained the same
   day -- see item 6's own 2026-09-29 update), compared real Cycles' own daily
   FRAC INTERCEP against this engine's thermal-time-only `canopy_cover()` prediction
   (fed real Cycles' own reported THERMAL_TIME, controlling for any thermal-time
   accumulation difference) across three real Kansas seasons (1985, 1988, 1996).
   The gap dwarfs anything seen at Rock Springs: real FRAC_INTERCEP plateaus at
   0.25-0.48 in every one of the three years, while the prediction climbs to
   0.94-0.99 as usual -- a 0.5-0.7 absolute gap sustained for weeks, not the ~5%
   peak-level bias item 5's own corn/wheat findings above describe. The gap tracks
   closely with real Cycles' own WATER STRESS and N STRESS columns both being
   substantially elevated (40-100%) during the same weeks -- confirmed absent at
   Rock Springs by the identical check (gap stays within +-0.05 across two full
   seasons, including one, 2012, with real stress episodes), so this is specific to
   a genuinely water-limited site, not a general flaw in the shape constants
   already covered above.

   Found the paper's own literal, disclosed explanation for a stress-canopy link,
   but only for nitrogen, not water: Section 2.4's text (not previously read this
   closely) states outright "The first derivative of Eq. (6) is used to estimate
   the rate of change of e_i as a function of TTf. The rate is reduced by N
   stress. Haying, grazing, tillage, and cold damage reduce e_i and TTf,
   rejuvenating the canopy." No water-stress term is mentioned anywhere near this
   passage. Implemented literally and tested: replaced the raw thermal-time input
   to `canopy_cover()` with a second, N-stress-discounted "canopy clock"
   (`canopy_tt_cum += dtt * n_stress_prev`, using the previous day's already-
   computed `n_stress` to avoid reordering the existing nitrogen bookkeeping) --
   an exact, verified no-op whenever nitrogen tracking is inactive (corn/soybean/
   silage corn's own default validation reproduced byte-for-byte: 0.527/0.799/
   0.182 respectively, confirmed via `git stash` A/B, not just inspection).
   Wheat's own default validation DOES track nitrogen, so this was a real test
   there: correlation moved 0.341 -> 0.301, worse, not better. At Kansas (the
   actual target): mean relative yield (N=0/N=150) moved from 0.934 to 0.968 --
   further from real Cycles' 0.779, the wrong direction -- though the year-to-year
   PATTERN correlation between this engine's and real Cycles' own relative-yield
   series improved slightly (0.186 -> 0.254). Diagnosed why rather than left
   unexplained: a smaller, N-stress-throttled canopy also demands less
   transpiration (`TRp` scales with `eie`), so the crop draws down its own soil
   moisture more slowly and dodges hard water-stress zeros MORE often, not less --
   a real second-order feedback that outweighs the direct radiation-limiting
   effect of a smaller canopy. **Reverted** -- a real, correctly-sourced,
   correctly-implemented mechanism that nonetheless makes the actual target worse,
   matching this project's standing discipline of not shipping a fix that costs
   more than it gains (the same call already made for the reverted power-law
   water-stress fit and the reverted flat-RUE-discount attempt).

   Also tested, as an unsourced but physically-motivated candidate (real leaf
   expansion is well known to be turgor/water-potential-sensitive, even though
   the paper's own text names only N stress): the identical mechanism, discounting
   the canopy clock by `water_stress` instead of `n_stress`. This one touches
   EVERY crop's default validation (water stress is always active, unlike N
   stress), and the result was unambiguously worse across the board -- corn
   0.527->0.524, soybean 0.799->0.784, wheat 0.341->0.309, silage corn
   0.182->0.175, all four Rock Springs baselines regressed, AND Kansas's own
   mean relative yield moved further from target too (0.934->0.942, correlation
   0.186->0.148). **Reverted.** Both reverts confirmed via `git checkout` back to
   the exact pre-change file and a full re-run of both validation harnesses.

   Net conclusion: the canopy-cover gap at Kansas is real, large, and precisely
   quantified, but neither the paper's own disclosed N-stress mechanism nor the
   plausible-but-undisclosed water-stress analogue explains it -- both make
   things worse when actually implemented and tested, not better. This rules out
   the two most obvious candidates rather than leaving them untried, but the
   canopy gap's real cause is still open. Worth trying next, if this is picked up
   again: checking whether the gap is better explained by something upstream of
   canopy entirely (e.g. a real per-hybrid or per-site plant-density factor this
   engine always leaves at 1.0, Eq. 7's own PDf term, since a lower effective
   stand density would suppress canopy closure directly without needing any
   stress-feedback mechanism at all) before trying a third stress-coupling
   variant.

   **Update (2026-10-01): the Eq. 7/plant-density candidate above is now ruled out
   directly, not just left untried.** The real Kansas `.operation` files built for
   this exact investigation (`KansasN0/150/300.operation`, same `PLANTING` block
   shape as the bundled `ContinuousCorn.operation` sample) carry a real `DENSITY`
   field -- almost certainly Eq. 7's own PDf, not a different parameter. Checked
   directly: both the real Kansas run and the bundled Rock Springs sample use
   `DENSITY 1.0`, identical. Real Cycles produced the severe 0.25-0.48 canopy
   plateau at Kansas under the exact same density setting that shows no such gap
   at Rock Springs, so a per-site density difference cannot be the explanation --
   real Cycles itself ran this scenario at PDf=1 and still showed the gap. This
   closes off the one remaining untried candidate above without touching the
   engine at all: whatever suppresses real Cycles' own canopy at Kansas, it isn't
   planting density.

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

     **Update (2026-09-24), a Kansas-specific diagnostic and two tested fixes,
     one real correction to an earlier wrong conclusion.** Prompted by a
     directed head-to-head test against native Cycles at a semi-arid site
     (Western Kansas, real STATSGO2/NLDAS-2 data, corn N=150, real reference
     0.137 Mg/ha for 2012), found a specific, mechanistic cause for why this
     engine overshoots there: `root_zone_availability()` credits a soil layer
     at its FULL current moisture content the instant `root_depth` reaches it,
     with zero regard for whether the root has had any time to actually draw
     it down. Instrumented day-by-day at Kansas and confirmed directly: water
     stress correctly hits 1.0 (fully unstressed) around doy 128-145 purely
     because `root_depth` is still growing into untouched, still-at-field-
     capacity subsoil, not because of any real rain event (precipitation in
     that window was 0.1-0.7mm, trivial) -- a "root discovery" artifact, not
     rain-driven recovery as first suspected.

     Two candidate fixes for this specific mechanism were tested and BOTH
     failed to move the Kansas number:
     - **Borg & Grimes (1986)** *Depth development of roots with time: an
       empirical description* (Trans. ASAE 29:194-197; widely cited in DSSAT/
       HYDRUS/SWAP), a real, sigmoidal root-growth-vs-time curve
       (`Zr/Zrmax = 0.5 + 0.5*sin(3.03*(t/tm) - 1.47)`) reaching full depth at
       t/tm=1.0 instead of this engine's own made-up `min(1, ttf/0.5)` shape
       (full depth at ttf=0.5, twice as fast). Coefficients are search-
       corroborated, not independently verified against the primary source --
       every host tried (arxiv.org, researchgate.net, eurekamag.com,
       files.core.ac.uk) is blocked by this sandbox's network egress policy.
       Tested against the full 4-crop suite: corn 0.547->0.544, soybean
       0.858->**0.825** (a real regression on the strongest, most
       statistically solid crop), wheat unchanged, silage corn 0.512->0.544.
       At Kansas: no improvement (barely moved, if anything slightly worse).
       Discarded -- slowing the overall root-growth rate delays *when* a
       fresh layer gets discovered, but doesn't change that discovery is
       still instant and total once it happens, so the same cliff just
       recurs later in the season with time left to recover from it.
     - **Root residence-time weighting**: a new mechanism (`root_days` per
       layer, incremented once per day root_depth has reached that layer,
       weighting both the layer's "available" and "capacity" contributions to
       `root_zone_availability()`/`extract_transpiration()` by
       `min(1, root_days/ramp_days)` instead of crediting it at full weight
       immediately) -- an engineering approximation for missing root-density
       buildup, not a literature-sourced formula. Swept ramp_days from 7 to
       90 days. At Rock Springs: negligible to slightly negative (soybean
       0.858->0.848 at ramp_days=45, others flat). At Kansas: **zero
       measurable effect at any ramp_days tested**, even layered on top of
       real multi-year carryover (see below) -- confirmed this wasn't a test
       artifact by checking the underlying math directly (a layer sitting
       exactly at field capacity contributes an identical avail/capacity
       ratio of 1.0 regardless of its weight, so down-weighting a
       still-untouched layer doesn't change the pooled average unless a
       *different*, already-depleted layer's weight moves relative to it --
       which the sweep confirmed doesn't happen enough to matter here).
       Discarded as a standalone fix. The diagnosis that motivated it (fresh
       soil credited instantly, no residence effect) remains real and
       correctly identified -- it's just not the dominant lever at this site.

     **Real correction to an earlier conclusion, found while building the
     residence-time test:** a genuine bug in this session's own Kansas test
     harness, not the engine, was caught and fixed. `simulate_season()`
     internally calls `crop["make_layers"]()` TWICE when nitrogen tracking is
     active -- once inside `_reference_n_demand()`'s independent precompute
     pass, once for the main loop's own real growth trajectory. A test
     harness that forces `make_layers` to return one shared, pre-built
     `layers` object (the correct trick for carrying soil state *across*
     separate `simulate_season()` calls in different years) accidentally lets
     the precompute pass and the main loop double-mutate that SAME object
     *within* one call, corrupting the result. This was silently in play for
     both the fresh-start baseline and the multi-year chained test reported
     earlier the same day, and produced a badly wrong number: a fresh-start
     baseline of 0.739 Mg/ha (5.39x over real) that looked like real progress
     against the previously-documented ~18x gap, and a chained multi-year
     result (0.738 Mg/ha) that looked identical to the baseline, appearing to
     show multi-year carryover has no effect at all.

     Fixed (give `_reference_n_demand`'s internal call a throwaway deep copy
     via a call-count dispatch, so only the main loop's own call receives and
     mutates the real carried-forward state) and re-run. The corrected
     numbers tell a different, better story: fresh-start baseline is
     **2.527 Mg/ha (18.44x over real)** -- matches the original, pre-this-
     session ~18x finding almost exactly, meaning none of this session's
     water-balance fixes meaningfully touched the Kansas gap, contrary to
     what was said earlier the same day. A real 3-year chained run (2010,
     2011, 2012, real crop-driven depletion carried forward, not bare
     fallow) gives **1.047 Mg/ha (7.65x over real)** for 2012 -- **more than
     halving the gap**. Multi-year state carryover is real and substantial
     here, reversing the earlier (bugged) conclusion that it does nothing.
     Layering the residence-time weighting on top of working carryover adds
     nothing further (7.65x at every ramp_days tested, unchanged) -- the two
     mechanisms don't compound.

     Net standing: of everything tried at Kansas this session (runoff,
     spin-up, Ksat rate-limiting, Campbell conductivity/substepping,
     evaporation Kr, `fwc`/retention_param_mm, TRANSPIRATION_MAX, root depth,
     emergence delay, NET_GROWTH_FRACTION, Borg-Grimes root curve, residence-
     time weighting), **real multi-year, crop-inclusive state carryover is
     the only mechanism that has moved the Kansas number at all**, and it
     moved it substantially.

     **Built as a real engine feature the same day**, not left as a scratch
     test: `simulate_season()` gained an `initial_layers` parameter (both
     `cycles_engine_validate.py` and the two embedded `ENGINE_SOURCE` copies,
     verified byte-identical to each other afterward, 48607 bytes each). When
     given a prior call's own returned `layers` state, this season starts
     from that real ending moisture instead of always resetting to field
     capacity; `None` (the default) reproduces the exact old behavior
     byte-for-byte (confirmed: the full 4-crop validation suite is unchanged
     to three decimals after adding this). `_reference_n_demand()`'s own
     internal precompute pass gets an independent `copy.deepcopy()` of
     whatever's passed in, never the caller's real object and never the same
     object the main loop mutates -- the exact discipline that would have
     prevented the test-harness bug described above, now built into the
     function itself rather than left to a caller to get right by
     convention. When `initial_layers` is used, the result dict also carries
     `final_layers`, the real ending state, so chaining seasons needs no
     extraction step: `carried = result["final_layers"]` feeds directly into
     the next call's own `initial_layers`.

     Verified three ways before trusting it: (1) the caller's own passed-in
     object is never mutated (checked directly -- identical before/after),
     confirming the deep-copy discipline holds; (2) two calls with the same
     untouched input are fully deterministic (identical output to full float
     precision); (3) the real public API (no dispatch hacks, no shared-object
     tricks) reproduces the exact same chained Kansas result already found
     with the hand-built test harness -- 1.047 Mg/ha, 7.65x over real Cycles
     for 2012, down from 2.527 Mg/ha/18.44x fresh-start -- confirming the
     built feature behaves identically to the scratch version that found the
     effect, not just plausibly similar.

     Not yet done (as of the paragraph above): no UI wiring anywhere (this is
     engine-only, matching the "engine first, UI later" pattern already used
     for the six mechanisms added 2026-09-17) -- no panel in
     `engine-demo.html`/`investigation.html` currently chains seasons or
     exposes this parameter, and per Matt's own direct instruction
     (2026-09-24: "let's use it to improve our model and not yet worry about
     UI until we make it more accurate"), none was built in the follow-up
     work below either.

     **Update (2026-09-24), the two follow-up tests this instruction asked
     for.** (1) Rock Springs' own 37-year validated corn record, chained for
     real: carried real ending soil state from each year into the next
     (bridged by that year's own real Jan-1-through-planting weather as bare
     fallow, the same role `spinup_rows` already plays), starting from a
     fresh field-capacity state in 1980 only. Result: **no meaningful
     change** -- fresh-start correlation 0.554, chained 0.555 (both slightly
     above the 0.547 headline figure since this exact run already carried
     spin-up for the very first year too; the difference between the two
     is noise, not a real effect). Diagnosed rather than left as an
     unexplained null: Rock Springs gets enough real winter/spring
     precipitation that the profile is back near field capacity by planting
     time most years regardless of what carried over from the prior season
     -- consistent with the same pattern already found for runoff, spin-up,
     and the Ksat rate cap earlier this session (real, correctly-implemented
     mechanisms that only bind at a site dry enough to expose them, and
     Rock Springs isn't that site).

     (2) Since Rock Springs couldn't say anything more about this
     mechanism, and the one real Kansas data point (2012) isn't enough to
     know if 7.65x was a fluke of one year, generated five more real
     Cycles reference points at Kansas using the native `Cycles` binary
     still on this machine (same real STATSGO2 Manter-series soil, same
     `CornN150.operation`, a fresh one-year lead-in spin each time, no
     `USE_REINITIALIZATION`, matching exactly how the original 2012
     reference was produced): 1988, 1993, 2005, 2008, 2016, spanning real
     drought (1988: 1.126 Mg/ha) to real wet years (1993: 4.369 Mg/ha).
     Ran our own model the same way -- fresh-start each year vs. a
     one-year-lead-in chained run (spin year Y-1 grown fresh, real ending
     state carried through a bare-fallow bridge into year Y) -- across all
     six years:

     | Year | Real Cycles | Fresh-start | Chained (1yr) |
     |------|------------:|-------------:|---------------:|
     | 1988 | 1.126 | 3.578 (3.18x) | 1.586 (1.41x) |
     | 1993 | 4.369 | 6.111 (1.40x) | 4.695 (1.07x) |
     | 2005 | 2.937 | 4.959 (1.69x) | 3.398 (1.16x) |
     | 2008 | 0.980 | 3.471 (3.54x) | 1.576 (1.61x) |
     | 2012 | 0.137 | 2.527 (18.38x) | 0.851 (6.19x) |
     | 2016 | 2.391 | 5.082 (2.13x) | 3.649 (1.53x) |

     Carryover improved every single one of the 6 years, not just the
     already-known 2012 case -- mean overshoot 5.05x -> 2.16x, mean absolute
     error 2.298 -> 0.636 Mg/ha. Correlation was already high both ways
     (0.983 fresh, 0.977 chained -- essentially unchanged, the small drop is
     noise at n=6) confirming this model already ranks good/bad years
     correctly without carryover; carryover fixes the absolute magnitude,
     not the ranking. This is real, systematic, out-of-sample evidence (none
     of these 5 extra years were used to derive or tune anything) that
     multi-year soil-state carryover is a genuine fix at a semi-arid site,
     not a one-year coincidence.

     Also checked whether a longer lead-in does better: a 3-year continuous
     lead-in (vs. the 1-year version above) gave only a marginal further
     gain (mean ratio 2.16x -> 2.13x, MAE 0.636 -> 0.592) -- almost all of
     the achievable benefit is captured by the immediately preceding season;
     more history has sharply diminishing returns. Practical implication if
     this is ever wired into a real feature: one prior season of carryover
     is enough, a deep multi-year state isn't needed.

     Honest limit of this fix, not smoothed over: even chained, the worst
     case (2012) still overshoots real Cycles by 6.19x -- carryover cuts the
     gap substantially but doesn't close it. The residual is most likely
     the still-unfixed "root discovery" artifact documented above
     (`root_zone_availability()` crediting a freshly-reached layer at full
     moisture instantly) rather than a soil-history-depth problem, since
     more lead-in years barely moved the 2012 number (6.19x -> 6.13x) --
     the same conclusion the residence-time-weighting test already pointed
     to. That mechanism is still genuinely unresolved; carryover and the
     root-discovery fix look like two separate, additive problems, not one.

     Still not done: no UI wiring (per Matt's explicit instruction above);
     no test yet at Iowa or Maryland (the other two preset sites with real
     STATSGO2/NLDAS-2 data already in this project); wheat/soybean/silage
     corn's own carryover behavior at Kansas or any other non-Rock-Springs
     site is untested.

     **Update (2026-09-24), the root-discovery fix itself, directly pursued
     with the new Kansas 6-year benchmark as a second check alongside Rock
     Springs.** First re-confirmed the anomaly is real, not a modeling
     artifact of imagination: instrumented 2012's daily history and found
     `water_stress` reads a PERFECT 1.0 (zero stress) for a 20-day span,
     doy 125-145, during which total real rainfall was 12.5mm across the
     entire 30-day window (120-150) -- there is no physical rain event that
     could justify this. Traced the mechanism precisely: by this point
     layer 1 (the shallow 0.33m layer) is nearly at wilting point
     (theta 0.113 vs. pwp 0.113, essentially zero available water), but
     layers 2 and 3 (0.31m and 0.88m, far larger total capacity) are still
     completely untouched at field capacity, since root_depth has only
     just reached into them. The POOLED ratio (avail/capacity across all
     three) lands around 0.55-0.60 even with layer 1 essentially dead --
     and `water_stress_response()`'s threshold (1-depletion_fraction,
     0.45 for corn) means ANY pooled ratio above that clips straight to
     1.0, fully unstressed. So the bug isn't really "a brief inflated
     credit that fades" -- it's that a single lumped root-zone reservoir
     structurally can't distinguish "barely-accessible deep water exists"
     from "the crop is not thirsty," and the FAO-56 Ks threshold is lenient
     enough that a moderately-full pool (even one propped up almost
     entirely by inaccessible depth) reads as no stress at all.

     Given this sharper diagnosis, tried FOUR further mechanisms (on top of
     the two already discarded above), each tested against BOTH the Rock
     Springs 4-crop suite (must not regress the one benchmark with real
     statistical power) AND the new 6-year Kansas benchmark (should
     actually move the number, not just the single 2012 case):

     - **Quarter-weighted blend, gap-squared**: compute the real FAO-56
       40-30-20-10 depth-quarter ratio alongside the flat pooled one, pull
       toward the weighted (lower) value by the SQUARE of their gap (a
       parameter-free correction that's a no-op when the two agree, i.e.
       at a normal, roughly-uniform profile). Rock Springs: unchanged to
       three decimals (corn 0.547, soybean 0.858, wheat 0.400, silage corn
       0.511) -- confirmed the gradient-conditional design is genuinely
       safe. Kansas: essentially unchanged (5.05x -> 5.07x-5.08x mean
       ratio, 2012 still 18.4-18.6x) -- too weak to matter, because
       `water_stress_response()`'s hard threshold-clip means a modest
       correction that stays above 0.45 changes nothing regardless of how
       "real" the correction is. Discarded for being ineffective, not
       harmful.
     - **Hard exclusion once a layer measurably depletes (theta < fc)**:
       a layer contributes to neither numerator nor denominator until
       something has actually removed water from it (not merely until
       root_depth nominally reaches it). Kansas fresh-start: dramatic
       apparent improvement (5.05x -> 2.44x, MAE 2.30 -> 0.67 Mg/ha) --
       but Rock Springs catastrophically regressed (mean yield roughly
       HALVED across all four crops: corn 10.55 -> 5.29 Mg/ha, soybean
       4.71 -> 2.29, wheat 4.33 -> 2.36, silage corn 14.79 -> 7.55).
       Root cause: at a humid site, a deeper layer often legitimately
       sits exactly at field capacity for days at a stretch simply because
       daily demand was low, not because it's inaccessible -- excluding it
       from the DENOMINATOR too shrinks the effective capacity pool enough
       that ordinary, mild depletion reads as severe stress far too often.
       Discarded outright; the "Kansas improvement" here was a side effect
       of breaking the water balance broadly, not a real, targeted fix.
     - **Elapsed-days step-function delay** (`advance_root_days()`/
       `establish_days`, a layer counts fully once root_depth has reached
       it for N days, zero credit before that -- deliberately different
       from the residence-time RAMP already discarded above, since a hard
       step avoids "any nonzero weight eventually pulls toward 1"):
       swept N from 14 to 120. At every N tried, Kansas got WORSE, not
       better (fresh-start mean ratio 5.07x at N=14 climbing to 14.26x at
       N=120), and Rock Springs correlation degraded steadily (corn 0.547
       at N=14 down to 0.206 at N=120). Cause: `extract_transpiration()`
       still cascades into a "not yet counted" layer once shallow layers
       run short (it has no such gate), so the plant keeps physically
       drawing down deep water even while the stress ratio can't see it --
       decoupling the feedback in a way that made both sites worse as the
       delay grew. Discarded.
     - **Pure quarter-weighted ratio, unconditional** (the exact FAO-56
       40-30-20-10 formula as the SOLE availability calculation, not
       blended): re-confirmed the previously-documented Rock Springs
       regression (corn 0.547 -> 0.542, silage corn 0.512 -> 0.488; wheat
       actually improved 0.399 -> 0.417) -- but, contrary to the
       hand-calculation that motivated trying this, Kansas got WORSE too
       (5.05x -> 5.30x mean ratio, MAE 2.30 -> 2.38). A real, empirically-
       tested reminder that a plausible-sounding hand estimate for one
       day's ratio doesn't predict a whole season's integrated effect.
       Discarded.
     - **FAO-56's own ETc-adjusted depletion fraction** (Allen et al. 1998
       Eq. 8-4, a real, disclosed, separate mechanism from Table 22's base
       p-values: `p_adj = p_table + 0.04*(5-ETc)`, clipped to [0.10,
       0.80] -- crops tolerate less depletion under high evaporative
       demand, more under low demand; `TRp`, already Kc-adjusted, stood in
       for ETc). This is the only one of the six mechanisms tried that
       moved the CHAINED Kansas number in the right direction at all:
       2012 chained 6.19x -> 5.98x, mean ratio 2.16x -> 2.13x. But it cost
       real correlation at Rock Springs across three of four crops (corn
       0.547 -> 0.528, soybean 0.858 -> 0.843, wheat 0.399 -> 0.377;
       silage corn improved, 0.512 -> 0.523). A ~1.4% aggregate Kansas
       gain against a real, broad-based Rock Springs cost -- not a trade
       worth making as-is. Not discarded as *wrong* (it's a real, correctly
       cited FAO-56 mechanism this engine genuinely doesn't implement
       elsewhere), just not net-positive at its current, unconditional
       strength; could be revisited with the same kind of gradient-gating
       used for the quarter-weighted blend (only apply the ETc adjustment
       when ETc is unusually high relative to the site's own normal range,
       rather than every day everywhere) if this is picked up again.

     **Net standing on root discovery specifically**: six real, distinct,
     mechanistically-motivated fixes have now been tried (two in the
     original diagnostic session, four here), tested against both the one
     benchmark with real statistical power (Rock Springs) and a new,
     independent 6-year out-of-sample benchmark (Kansas). None is a clean
     win. The anomaly itself is real and precisely diagnosed (a 20-day,
     essentially-zero-rain window reading as perfectly unstressed), but it
     resists correction via any tested adjustment to the availability
     formula, the extraction cascade, or the stress-response threshold.
     This suggests the actual fix, if one exists short of a genuine
     multi-layer root-density/hydraulic-conductance model, may not be a
     small formula change at all -- the single-lumped-reservoir Ks
     approach (a real, standard, FAO-56-endorsed simplification) may
     simply not be expressive enough to correctly separate "some water
     exists somewhere in the root zone" from "the crop can actually use
     it fast enough," especially at a site where capacity is concentrated
     in a few large, discretely-reached layers rather than distributed
     smoothly. Carryover (see above) remains the one mechanism that has
     robustly, substantially helped at Kansas without costing Rock
     Springs anything -- not because it addresses root discovery directly,
     but because it changes the STARTING state of the very layers this
     bug misjudges, so there's less "phantom full" capacity for it to
     exploit in the first place.

     **Update (2026-09-24), the real hidden lever, found by asking a
     different question.** Rather than keep varying the availability
     formula, went looking directly at what real Cycles' own daily output
     shows at Kansas that our model doesn't reproduce -- something not yet
     done for this site (only aggregate yield had been checked). Pulled
     `water.txt`'s real per-layer SMC for the full 2011-2012 record (the
     native run already used to generate this session's Kansas reference
     points) and found something structural: layer 3 (the big 0.88m
     layer) sits at essentially the SAME value, 0.058-0.061 m3/m3, from
     the very first day of the simulation record (2011-01-01) all the way
     through 2012, including *before the 2012 crop is even planted*.
     Real rain events visibly bump layer 1 (topsoil) up and down; layers
     2 and 3 barely move at all, and never recover toward anything close
     to what our own Saxton-Rawls calculation calls field capacity
     (0.145 for layer 3).

     Checked the ratio precisely: `(theta_initial - pwp) / (fc - pwp)`
     using our own computed pwp/fc for this exact soil, at the very first
     day of the whole simulation record (2011-01-01), gives 0.463, 0.497,
     0.503 for layers 1, 2, 3 -- two of three within 0.7% of exactly
     0.50. This is a real, measured fact about how real Cycles starts a
     simulation: **at half of plant-available water, not at field
     capacity.** Every make_layers()-equivalent in this project (the two
     canonical validation scripts, both embedded engine copies, this
     session's own Kansas test scripts) has always initialized
     `theta=fc` -- explicitly documented as a known simplification
     ("every soil layer always initializes to field capacity with no
     spin-up or carryover," CLAUDE.md, 2026-09-22) but never checked
     against what real Cycles itself actually does at time zero, because
     no prior comparison had a real Cycles run whose recorded output
     began at the literal start of a simulation.

     Why this matters enormously more at Kansas than Rock Springs, and
     why six formula-level fixes to `root_zone_availability()` all missed
     it: at Rock Springs, the real Jan-1-to-planting bare-fallow spinup
     that every validated run already does gets enough real rain to wash
     out a 100%-vs-50%-of-available starting difference within weeks,
     well before planting -- confirmed directly, the full 4-crop suite is
     byte-identical to three decimals with the fix applied (corn 0.547,
     soybean 0.858, wheat 0.399, silage corn 0.512, all unchanged). At
     Kansas, real layer 3 never gets meaningfully recharged once
     depleted (the same "layers 2/3 barely move all season" pattern this
     item's original diagnosis already found, now explained by the wrong
     STARTING point rather than a wrong within-season formula) -- so
     starting a fresh Kansas run at "100% full" instead of "50% full"
     means carrying real, phantom extra water for the ENTIRE season, not
     just a transient window.

     Tested directly against the same 6-year Kansas benchmark used for
     every other fix in this item: fresh-start mean overshoot dropped
     from 5.05x to 3.63x (2012 specifically: 18.44x -> 12.49x), mean
     absolute error 2.298 -> 1.454 Mg/ha, at zero cost anywhere tested.
     This is the first of seven distinct mechanisms tried against this
     benchmark (the two from the original session, five here) that is an
     unambiguous, uncomplicated win -- no tradeoff to weigh, unlike the
     ETc-adjustment or any of the availability-formula variants. Combined
     with one year of real carryover, the improvement doesn't stack much
     further (chained mean ratio 2.16x either way, 2012 still 6.19x) --
     expected, since the chained case's own starting point already comes
     from a full season of real simulated dynamics in the spin year, not
     a fresh reset, so only the SPIN year's own initial condition
     benefits, and that gets substantially overwritten by the time the
     spin year's own season ends.

     Shipped as `INITIAL_MOISTURE_FRACTION = 0.5` in
     `cycles_engine_validate.py` (both canonical validation scripts and
     both embedded `ENGINE_SOURCE` copies, confirmed byte-identical to
     each other afterward, 48919 bytes each). Real, disclosed limit worth
     being honest about: this is a genuine hidden lever, not the entire
     answer -- 2012's fresh-start overshoot only dropped from 18.44x to
     12.49x, still far above the classroom-workable bar, and the deeper
     "root discovery" symptom (a lumped-reservoir stress calculation that
     can't distinguish accessible from barely-accessible water) is still
     unresolved on top of this. What this DOES change is the diagnosis:
     the dominant driver of Kansas's overshoot looks less like a
     within-season dynamics bug and more like a wrong INITIAL CONDITION
     that a humid-climate validation suite (Rock Springs) could never
     have surfaced, because rain erases the difference there before it
     matters. Worth checking this same lever at Iowa and Maryland next,
     and worth wondering whether OTHER "disclosed simplifications" in
     this engine share the same property -- invisible at Rock Springs,
     real everywhere drier.

     **Update (2026-09-24), checked at Iowa and Maryland as recommended
     above.** Real Cycles' own initial SMC (2011-01-01, already-existing
     Iowa native output) confirms the SAME pattern found at Kansas, not a
     one-site coincidence: (theta_initial-pwp)/(fc-pwp) = 0.449, 0.474,
     0.480, 0.474 across Iowa's four real soil layers. Ran a fresh native
     Cycles simulation for Maryland (no prior run existed for this site;
     built real input files from the already-resolved Othello-series
     STATSGO2 soil and the committed NLDAS-2 weather tiles, same pipeline
     already used to resolve this preset elsewhere in this project) and
     found the identical pattern a third time: 0.466, 0.476, 0.486, 0.509
     across Maryland's four layers. Three independent real sites, twelve
     layers total, all landing in a tight 0.45-0.51 band around exactly
     0.50 -- this is now a well-established, cross-site fact about how
     real Cycles starts a simulation, not a Kansas-specific quirk.

     Applying the fix (fresh-start, `INITIAL_MOISTURE_FRACTION=0.5` vs.
     the old `theta=fc`) at Iowa (2 real years, 2011/2012, from the
     already-existing native run) gave a real, substantial improvement,
     the same direction and a similar-sized effect as Kansas: mean
     overshoot 1.37x -> 1.21x, MAE 1.347 -> 0.754 Mg/ha. At Maryland (6
     real years generated fresh via native Cycles for this check --
     1988, 1993, 2000, 2005, 2012, 2016, real yields 3.80-7.73 Mg/ha),
     the fix helped more modestly: mean overshoot 1.66x -> 1.60x, MAE
     2.962 -> 2.804 Mg/ha.

     **A genuine methodological lesson worth recording, not just the
     result**: the first Maryland pass used only 4 years (1988, 2005,
     2012, 2016) and found a striking correlation of -0.966 between our
     model and real Cycles -- an apparent near-perfect INVERSE ranking,
     which looked like a serious, distinct bug worth chasing (real
     Cycles' best year among the four, 2012, was one of our model's
     worst, and vice versa). Checked one hypothesis directly before
     trusting the correlation (vapor pressure deficit, since
     `GT = wue/sqrt(Da)*TR_actual` means an unusually low Da could
     inflate growth) -- and it pointed the WRONG direction (2012 actually
     has the *highest* Da of the four years, which should suppress our
     model's growth, not inflate it, the opposite of what would explain
     the inversion). Rather than chase further hypotheses on 4 points,
     generated 2 more real Maryland years (1993, 2000) via the same
     native-Cycles pipeline -- and the correlation collapsed to -0.023 /
     -0.062 (essentially zero, not inverse) once n=6. The dramatic -0.966
     was a small-sample artifact, not a real signal. Worth remembering
     the shape of this: a striking correlation from 4 points is cheap to
     over-trust, and cheap to check when (as here) more real reference
     years can be generated directly rather than assumed sufficient.

     What's real and DOES survive the larger sample: our model's Maryland
     output barely responds to which year it's given at all (stdev 0.73
     Mg/ha across the 6 years, range 2.08) while real Cycles' actual
     yields vary far more (stdev 1.44, range 3.94) -- our model isn't
     ranking years backwards, it's just comparatively flat regardless of
     year. A plausible, not-yet-confirmed explanation: Maryland's humid
     Chesapeake coastal-plain climate rarely lets water become the
     limiting factor the way Kansas's semi-arid climate does every year --
     which would mean this water-balance-only engine has structurally
     less to say about what actually drives Maryland's real year-to-year
     variability (nitrogen dynamics, disease pressure, or something else
     entirely outside this engine's scope), the same way it has the MOST
     explanatory power at the most water-limited site (Kansas, pre-fix
     correlation already 0.98+) and middling power at the moderately
     water-limited one (Rock Springs, 0.55). Not confirmed, and not
     something the initial-moisture fix (or likely any water-balance fix)
     would be expected to close -- flagged here as a real, distinct,
     probably-structural limitation rather than another lever to chase.

     **Real, disclosed consequence for `engine-demo.html` specifically,
     not smoothed over**: unlike the two canonical validation scripts
     (which spin up from Jan 1 through planting using real bare-fallow
     weather before every season, the same mechanism that makes this
     fix a no-op at Rock Springs), `engine-demo.html`'s own interactive
     panels (Run a season, the nitrogen-sweep/frontier panel, the
     field-comparison panel, the rotation panel) call `simulate_season()`
     directly from `build_season_rows()`'s output with NO spinup_rows at
     all -- confirmed by grepping every call site. This means those
     panels' own starting condition changes for real with this fix (a
     direct check found Rock Springs 2012 corn @ N=150 moving from
     8.2919 to 8.1832 Mg/ha, a small, sensible ~1.3% reduction from
     slightly less available water at day one, not a red flag). Every
     specific number already written into this file's own history for
     those panels (the Tab 3 crossover point, the profit-maximizing
     nitrogen rate, the tillage-compare spreads, the season-risk 37-year
     averages, and more) was computed before this fix and will not
     reproduce exactly if re-run now -- the same category of disclosure
     already made for the FAO-56 depletion-fraction and NET_GROWTH_FRACTION
     ports. `model-validation.html` is unaffected in this specific way
     since its own form exposes `spinup_rows` as a real parameter rather
     than omitting it.

   **Update, 2026-09-25:** the "root discovery" artifact behind most of this item's Kansas
   overshoot (a shallow, nearly-dry layer's stress masked the moment root growth reaches a
   deeper, still-full layer, since the old mechanism pooled available water across the whole
   root zone before computing one ratio) is now understood as partly a MECHANISM problem, not
   only a missing-carryover one. Replaced the pooled root_zone_availability()/
   water_stress_response()/extract_transpiration() trio with a real hydraulic-conductance
   mechanism (Campbell 1985, extended by Jara & Stockle 1998 -- the exact mechanism Kemanian
   et al. 2024 cites by name for Cycles' own model, traced via CropSyst's own public C++
   source plus the WSU CropSyst manual's "Crop Transpiration" page, retrieved via the Wayback
   Machine). See "Resolved without asking" below (the hydraulic-conductance water-stress
   mechanism entry) for the full account, including a real, mixed result: Kansas's
   fresh-start overshoot improves (3.63x -> 3.24x) and the chained-carryover case's absolute
   error improves even though its bias flips from over- to under-shooting (2.16x over ->
   0.73x under, MAE 0.54-0.63 -> 0.35 Mg/ha) -- real progress on the diagnosed confound, not a
   clean resolution into "now correctly calibrated."

   **Update, 2026-09-29 -- a new, previously-undocumented downstream consequence of this
   same root cause, found while investigating why real classroom nitrogen-response patterns
   had silently vanished (see CLAUDE.md's dated entries for the full narrative; this is the
   mechanistic follow-through on that finding).** The pattern-assertion suite's new
   `c_checkplot_relative_yield` check found corn shows an implausibly small nitrogen response
   (relative yield 0.82-0.99, vs. a real literature range of 0.20-0.80) at every resolved-tile
   site tested, and -- more tellingly -- at EVERY year tested at Kansas specifically (11 years
   spanning 1985-2015, not just the single worst drought year), while Iowa shows a real,
   sensible response (0.75-0.90, varying plausibly with year) across the same span. Traced the
   exact mechanism directly, not inferred: `simulate_season()`'s nitrogen demand for a given
   day is `demand_today_kg_ha = dGB_water_limited * n_stress * 10 * n_marginal_demand_pct(...)`
   -- i.e. nitrogen demand is gated MULTIPLICATIVELY by the same day's water-limited growth
   (`dGB_water_limited = max(0, min(GR,GT)) * NET_GROWTH_FRACTION / 1000`). On any day where
   `campbell_water_uptake()` returns `water_stress=0.0` (GT driven to exactly zero, not just
   reduced), nitrogen demand for that day is ALSO exactly zero, regardless of fertilizer
   supply -- nitrogen can never bind as the limiting factor on a day water has already
   zeroed out. Instrumented `water_stress` day-by-day across the same 11-year span at both
   sites (via `record_history=True`): Kansas spends 12-58% of every single growing season at
   `water_stress<0.01`, including relatively wet years by its own standard (2009: 12%, 1997:
   19%), vs. Iowa's 0-2% in wet years and up to 40% only in its driest tested year (1988).
   Real Kansas (Manter series) soil is genuinely thin-profiled (127mm total plant-available
   water across 1.52m, vs. Iowa/Canisteo's 221mm) and semi-arid (130-491mm growing-season
   precip across the same span vs. Iowa's 293-763mm) -- so SOME real water limitation there
   is expected and correctly reflects real soil/climate data, not an artifact. What does NOT
   look defensible is the near-total absence of yield response to fertilizer across an entire
   30-year span including years that aren't severe droughts by Kansas's own standard -- real
   western-Kansas dryland corn extension guidance still recommends a real, nonzero N rate
   specifically because a real, if modest, response persists even under meaningful water
   limitation, which is also consistent with the real N-omission-trial literature's own
   20-80% relative-yield range (i.e., even literature's worst, most water-limited sites still
   show a REAL, substantial response, not near-zero).

   This reframes the diagnosis precisely: the nitrogen-demand coupling ITSELF is not the bug
   -- tying N demand to water-limited (not potential) growth is defensible in principle, since
   real nitrogen uptake is itself water-mediated (mass flow/diffusion both require water
   movement) and a wilted plant genuinely can't take up much N regardless of soil supply. The
   bug, if there is one, is entirely upstream: `campbell_water_uptake()` (the hydraulic-
   conductance mechanism from the 2026-09-25 update above) returns an exact, hard zero far
   more persistently at Kansas's real thin-profile soil than real crops plausibly experience,
   and because of the coupling above, that hard zero doesn't just distort yield magnitude
   (already known, see the fresh-start/chained overshoot numbers above) -- it also makes
   nitrogen look completely irrelevant at that site, for every single year tested, which is a
   materially worse and more specific classroom risk than "the yield number is a bit high."

   Deliberately NOT patched here: retuning the N-demand formula itself to avoid a literal zero
   (e.g. flooring `dGB_water_limited` at some small nonzero value on stressed days) would be
   an invented, unsourced mechanism -- exactly the "tinkering around the edges" this project's
   own standing discipline rules out, and it would mask the real upstream problem rather than
   fix it. Six real, sourced fixes have already been tried and failed at closing this same
   Kansas gap (see the update above and the "Resolved without asking" section) -- none of them
   touched the N-demand coupling, since this specific downstream consequence (nitrogen looking
   irrelevant, not just yield running high) wasn't identified until this pass.

   **Recovery-time hypothesis checked directly, ruled out (same day):** instrumented a
   day-by-day trace of Kansas 2009 (a mild year, only 12% hard-zero days) and found
   `campbell_water_uptake()` recovers FAST and correctly once real rain actually falls -- a
   20mm event on doy 171, mid-stretch of consecutive zero days, produces water_stress=0.601
   the SAME day, and a 30mm event on doy 210 gives 0.753 the same day. The persistent
   hard-zero stretches line up exactly with real, literal 0mm-precipitation runs in the real
   NLDAS-2 weather data (doy 168-170, 177-179, 186-197, etc.), not a sluggish or broken
   recovery mechanism -- so this specific candidate explanation is ruled out, not just
   unconfirmed.

   A second thing checked and NOT obviously damning on its own: total seasonal nitrogen
   demand at Kansas (9.5-12.6 kg N/ha across N=0-650 at the 2012 drought year) looks small in
   absolute terms, but roughly tracks a standard real-world rule of thumb (~20-25 kg N per Mg
   of grain yield) applied to Kansas's own low ~0.7 Mg/ha grain yield there -- i.e. LOW total N
   demand at a LOW-yield-potential site isn't obviously wrong in isolation; the open question
   is whether real Cycles' own Kansas yield potential (and hence N demand) is really this low
   across a full multi-year span, not just the single 2012 point already checked against real
   Cycles (where real Cycles shows an EVEN lower yield than this engine does, 0.137 vs. 0.70
   Mg/ha -- i.e. real Cycles is already known to be more pessimistic than this engine at
   Kansas, not less, for that one data point).

   This narrows the real open question to one that needs real Cycles ground truth, not more
   engine-side instrumentation: does real Cycles ALSO show a near-flat nitrogen response
   across several non-drought Kansas years, or does it show a real, substantial response even
   at low absolute yield (consistent with the real N-omission-trial literature's 20-80%
   relative-yield range, which this engine's Kansas numbers currently fall well outside of)?
   Answering this needs real Kansas `.weather`/`.soil`/`.operation`/`.ctrl` input files run
   through the actual Cycles binary at 2-3 more years and at least two N rates -- the same
   real-vs-model comparison already used successfully for the single 2012 point earlier this
   project, just not yet repeated across multiple years. Not attempted in this pass: this
   session's `/tmp/cycles-run` no longer has the Kansas input files built for that earlier
   comparison (this container was reprovisioned since, the same recurring loss this file's
   CLAUDE.md entry already documents and expects) -- rebuilding them is a real, bounded task
   (derivable from the already-committed STATSGO2/NLDAS-2 tile data the same way it was built
   once before), not a new investigation, and is the highest-value next step if this is picked
   up again.

   **Update, 2026-09-29, decisive real ground truth obtained (same day, per Matt's direct
   "Go rebuild Kansas's real Cycles input files and run it").** Rebuilt real
   `Kansas.weather`/`Kansas.soil`/`KansasN{0,150,300}.operation`/`KansasN{0,150,300}.ctrl`
   from the same already-committed STATSGO2/NLDAS-2 tile data this engine's own resolved-
   tile pathway uses (via `field_data.py`), matching the bundled `ContinuousCorn` sample's
   own rotation/tillage/planting structure exactly for direct comparability. Ran the real
   Cycles v1.4.4 binary for the full 37-year record (1980-2016) at N=0/150/300 kg/ha.

   **Real Cycles does NOT show a near-flat nitrogen response at Kansas.** Mean relative
   yield (N=0/N=150) across all 37 years is 0.779 -- squarely inside, near the top of, the
   real N-omission-trial literature's 0.20-0.80 range -- and it varies meaningfully by year
   (0.344 to 1.028), splitting cleanly into 10 real "FLAT" years (relative yield > 0.95:
   1980, 1984, 1985, 1994, 2000, 2005, 2008, 2009, 2010, 2012 -- 2012, the single point
   already checked in an earlier session, is one of these, which is why testing this
   engine's own behavior against 2012 alone was a poor test of the muting problem: even
   real Cycles is flat there) and 27 real "RESPONSE" years, several with a dramatic real
   response (1996: 0.344, 1983: 0.480, 1993: 0.478, 1991: 0.485, 1998: 0.474). N=150 and
   N=300 gave byte-identical yield in every single year in real Cycles (a real, clean
   saturation at or below 150 kg N/ha at this lower-yield-potential site -- consistent with,
   not contradicting, this engine's own plateau-by-N=50-ish behavior there).

   This engine's own mean relative yield across the identical 37 years is 0.934 -- confirms
   this is a real, quantified MUTING of nitrogen sensitivity, not (as the pre-ground-truth
   framing above suggested) a complete structural absence of it. This engine shows some
   response (relative yield < 0.95) in 13 of the 37 years; 11 of those correctly overlap
   with real Cycles' own RESPONSE years (1982, 1986, 1989, 1992, 1996, 2002, 2004, 2006,
   2011, 2013, 2014), meaning this engine's water-stress mechanism DOES pick out roughly the
   right subset of stressed years -- it just understates the magnitude in nearly every one
   of them, and misses entirely the large group of real RESPONSE years where real Cycles'
   own relative yield sits in the milder 0.75-0.90 band (1988, 1997, 1999, 2003, 2007, 2015,
   2016 among others) -- this engine renders essentially all of those as flat (rel~1.00).

   A genuinely good, previously-undocumented finding fell out of building this real
   comparison: at N=150 (the real fertilized rate), this engine's yield correlates **0.777**
   against real Cycles across the full 37 years (MAE 0.656 Mg/ha, mean 2.265 vs. real 2.569,
   only a 12% undershoot) -- a new, real Kansas corn validation number, actually somewhat
   BETTER than corn's own headline Rock Springs correlation (0.527-0.550). At N=0 the
   correlation drops to 0.551 with a 13% overshoot (mean 2.115 vs. real 1.871), consistent
   with this engine's own muted sensitivity inflating unfertilized yield specifically. This
   reframes the Kansas story from "this engine badly overshoots yield there" (the original,
   single-point 2012 framing) to something more precise: this engine tracks real Cycles'
   year-to-year *ranking* reasonably well at a realistic fertilized rate (0.777 correlation
   is genuinely solid), and its remaining gap is concentrated specifically in how much
   nitrogen matters, not in overall yield magnitude across the full record.

   Confirms the diagnosis from the entry above with real ground truth rather than
   inference: this is a genuine engine gap (real Cycles clearly produces meaningful,
   varying multi-year nitrogen sensitivity at a real semi-arid site), not a "Kansas is just
   like this" site characteristic this engine happens to reflect correctly. The most likely
   remaining target, per the same reasoning as before, is still the water-balance/root-
   uptake mechanism's own year-to-year behavior at low-PAW soils (already flagged, still not
   fully resolved after several real, sourced fixes this session and earlier), not the
   nitrogen-demand coupling, which the recovery-time and demand-magnitude checks above
   already found defensible. Real Kansas input files, real Cycles binary output, and this
   comparison's own scratch analysis scripts live only in `/tmp/cycles-run`/the session
   scratchpad, per this project's own standing licensing discipline (Cycles' generated
   output is squarely what its CC BY-NC-ND license restricts, same as every other real
   Cycles run in this project's history) -- not committed to this repo, and will need
   rebuilding again from the same committed tile data if `/tmp/cycles-run` resets before
   this is revisited.

   **Update, 2026-09-29, same day -- planting date checked and ruled out as the driver
   too, then the real cause traced to the canopy-cover mechanism (see item 5's own
   2026-09-29 update for that full account).** Per Matt's direct "Go dig into the
   water-balance/root-uptake mechanism at low-PAW soils next," first compared this
   engine's own computed planting date (`find_planting_doy()`, already validated at
   Rock Springs to 2.65 days mean absolute error) against real Cycles' own real
   `PLANT_DATE` at Kansas across all 37 years. A real, systematic, much larger gap:
   this engine plants a mean of 7.6 days EARLIER than real Cycles at Kansas (up to 21
   days in the worst years -- 1992, 1996, 2012, 2014), almost always stuck at the
   planting window's earliest allowed day (DOY 110), while real Cycles' own planting
   date varies meaningfully by year (110-131), tracking real spring-warmth variation
   the way this engine's mechanism does correctly at Rock Springs but evidently
   doesn't at Kansas's different soil/climate. Tested directly whether this explained
   the muted nitrogen response: forced this engine to use real Cycles' own exact
   planting date instead of its own computed one, at the four worst-gap years and
   across the full 37-year record. Result: **made things worse, not better** -- mean
   relative yield moved from 0.935 to 0.958 (further from real Cycles' 0.779), and the
   already-weak correlation between this engine's and real Cycles' own year-to-year
   relative-yield pattern dropped from 0.186 to 0.090. Ruled out as the driver, though
   the planting-date discrepancy itself is real and worth its own fix eventually (a
   separate question from the nitrogen-response muting this investigation was
   actually chasing) -- most likely the same generic soil-temperature lag filter
   (`simulate_soil_temp`, k=0.15) calibrated implicitly via Rock Springs validation
   doesn't transfer to a different soil's real thermal properties, but not
   investigated further here since fixing it doesn't address the actual target.

   The investigation then moved to canopy cover (item 5's own 2026-09-29 update has
   the full account): real Cycles' actual FRAC INTERCEP at Kansas plateaus at 0.25-0.48
   during real stress episodes across three tested years, vs. this engine's
   thermal-time-only canopy formula predicting 0.94-0.99 regardless -- a large,
   consistent, previously-undocumented gap, confirmed absent at Rock Springs. Two
   real candidate fixes (the paper's own disclosed N-stress-discounted canopy clock,
   and an unsourced-but-plausible water-stress analogue) were implemented and tested;
   both made Kansas's relative yield worse, not better, and were reverted. This
   engine's water-uptake mechanism itself (`campbell_water_uptake()`, already the
   primary suspect per the entries above) remains the most likely place still worth
   investigating, but the canopy-cover gap is now a separate, equally real, equally
   unresolved finding in its own right -- not something either tested fix closes.

   **Update (2026-10-01): rechecked against the full real 37-year Kansas record
   (not just 6 spot-checked years) under the current engine, after the same day's
   cold-kill and CO2-WUE-scaling mechanisms shipped for a different reason (corn's
   own Rock Springs secular trend).** Re-ran this engine at Kansas N=0 and N=150
   across all 37 years with both new mechanisms active: mean relative yield
   (N=0/N=150) moved from the previously-documented 0.934 to **0.853** -- real
   Cycles' own value is 0.779, so this closes about half the gap (0.155 -> 0.074),
   a genuine, if incidental, improvement neither mechanism was built to produce.
   The absolute level comparison moved the other way, though: at N=150, this
   engine previously undershot real Cycles by 12% (MAE 0.656 Mg/ha); it now
   OVERSHOOTS by 35% (real mean 2.569, model mean 3.465, MAE 1.025) -- CO2-WUE
   raises yield uniformly across years while the recalibration that followed it
   was derived against Rock Springs' own mean, not Kansas's, so the two sites'
   calibration-factor fit has diverged further. Correlation at N=150 moved
   0.777 -> 0.758, essentially unchanged. Net: real, partial progress on the
   actual target (nitrogen-response muting) from an unrelated fix, at the cost of
   a bigger absolute miss at this one non-calibration site -- expected given this
   project's calibration_factor is, and has always been, a single global number
   fit to Rock Springs, not refit per site.

   **Also tested the same day: real multi-year soil-state carryover (`initial_
   layers`/`final_layers`, shipped 2026-09-24) across the now-complete 37-year
   Kansas record, not just the earlier 6-year spot check.** Chaining each year's
   real ending soil moisture into the next (via `initial_layers`, with that year's
   own Jan-1-to-planting weather still run as `spinup_rows` on top of it) is a
   genuine win at Kansas under the current engine: ratio 1.349x -> 1.226x,
   MAE 1.025 -> 0.805 Mg/ha (-21%), correlation 0.758 -> 0.761. This reproduces the
   same direction of improvement already documented for the 6-year spot check.
   But re-tested at Rock Springs under the SAME current engine (the 2026-09-22
   finding of "no meaningful change there" was measured against an older engine,
   before the hydraulic-conductance water-stress mechanism, cold-kill, and CO2-WUE
   all shipped) and found it is **no longer neutral**: correlation drops
   0.777 -> 0.701, MAE grows 0.647 -> 0.807 Mg/ha -- a real cost, and a larger one
   in absolute terms than Kansas's gain. **Not adopted as a default** for either
   `run_validation.py` or any pattern check: turning carryover on everywhere would
   trade a real win at the one site it was tested for against a real, larger loss
   at the actual calibration site, and the calibration_factor values this whole
   project relies on were all derived under fresh-start conditions -- switching
   would need a full recalibration pass, not a flag flip. Worth remembering the
   shape of this finding: a mechanism's own effect size is not fixed across engine
   versions -- re-test a previously-"neutral" result after any change to the
   core growth/water-stress physics before assuming it still holds.

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

   **Follow-up (2026-09-25), a real candidate found via CropSyst's own public
   source, tested and NOT adopted.** CropSyst's `crop/biomass_growth_RUE_TUE.cpp`
   has a real, disclosed, per-crop mechanism that plausibly IS the answer:
   `RUE_kg_MJ_adjusted = RUE_kg_MJ - (RUE_efficiency_decrease_rate * solar_rad)`
   -- RUE declines linearly as solar radiation rises (a real light-saturation
   effect), not a flat, radiation-independent discount. Directly tested this
   shape against real Cycles' own daily output before assuming it fits: binning
   852 clean (zero water-stress, zero N-stress) days from the full 37-year
   continuous-corn record by solar radiation shows a real, monotonic decline
   from ~0.80 (10-15 MJ/m2/day) to ~0.64 (30 MJ/m2/day) -- a materially better
   fit (R^2=0.29 over the flat-mean baseline) than the single 0.785 constant
   currently used. `RUE_efficiency_decrease_rate`'s own numeric value isn't in
   CropSyst's public repo (it's a crop-database field, not a compiled default;
   confirmed by an exhaustive repo search turning up zero assignments), so this
   session fit the slope/intercept directly off real Cycles' own output the
   same way `TTf50` was fit.

   Built and tested both structurally sound placements before deciding: applying
   it to GR before the min(GR,GT) choice (CropSyst's own literal placement)
   reproduces the exact same correlation-destroying distortion already
   documented for the flat version (86% of days become radiation-limited vs. a
   real ~40% baseline; every crop's correlation drops, e.g. corn 0.547->0.476).
   Applying it after the min(GR,GT) choice (the placement that keeps the flat
   `NET_GROWTH_FRACTION` safe) is structurally sound but empirically worse for
   3 of 4 crops (corn 0.547->0.495, soybean 0.858->0.837, wheat 0.399->0.276;
   only silage corn improved, 0.512->0.542) -- because on the majority of days,
   which are water- not radiation-limited, this now scales down GT-driven growth
   by that day's radiation level too, which has no physical basis (GT depends on
   transpiration/WUE, not RUE). **Not shipped either way** -- the flat
   `NET_GROWTH_FRACTION=0.785` stays, a real case of a mechanistically-motivated,
   better-isolated-fit formula not transferring cleanly onto this engine's
   specific growth-limitation architecture (the same lesson as the reverted
   power-law water-stress fit earlier this session). This sharpens the open
   question above: if real Cycles does apply a radiation-magnitude-dependent RUE
   decline, what does it do on a water-limited day to avoid the same distortion
   this session hit, and is there a real, disclosed per-crop
   `RUE_efficiency_decrease_rate`-equivalent value?

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

- **Re-tried wheat's real 90 kg N/ha fertilizer input after the biomass fixes
  -- still doesn't work, confirmed why (2026-09-24).** CLAUDE.md's own account
  (2026-09-23) left this open: applying wheat's real fertilization (a single
  90 kg N/ha UAN broadcast at DOY 75, from `CornSilageSoyWheat.operation`)
  made correlation dramatically worse (0.276 -> -0.145) before the
  NET_GROWTH_FRACTION/wheat-radiation-temperature fixes, which were expected
  to fix the underlying cause (an overestimated biomass trajectory). Re-tested
  now that wheat's total-biomass level bias has improved substantially
  (1.233x -> 1.204x, on top of everything else fixed since): the real N input
  alone still collapses correlation just as badly (0.399 unconstrained ->
  0.023 constrained), so the biomass fix did not resolve this. Swept an
  additional flat nitrogen credit on top of the real 90 kg N/ha input (0 to
  500 kg N/ha) and found correlation only recovers to the unconstrained
  baseline once the credit reaches ~150 kg N/ha -- i.e., this simplified
  model's own implied total-season N demand for wheat is roughly 240 kg N/ha
  to be non-limiting, nearly 2.7x the real 90 kg N/ha application that
  apparently suffices for real Cycles. This is the exact same limitation
  already disclosed for corn ("no background soil-supplied nitrogen... the
  point at which the knob stops mattering is much higher than a real-world
  fertilizer recommendation would suggest"), now confirmed to apply
  identically to wheat rather than being a corn-specific quirk. There's no
  real, disclosed number to use for a wheat-specific credit large enough to
  close this gap -- any credit that reproduces the real mean is circular
  (chosen to match the answer, not derived from anything). Not pursued
  further: closing this for real needs the full six-pool soil-supplied
  nitrogen system (already out of v1 scope), not a bigger fudge factor.

- **A full, systematic paper + SI audit (2026-09-24), per Matt's direct
  "let's return to the paper and SI and make sure we have everything they
  say" -- after many sessions of chasing small numerical levers with
  diminishing returns, stepped back and re-derived a complete, primary-source
  cross-reference instead.** Two real methodological upgrades made this
  possible: (1) the SI document (`CYCLES_supplemental.docx`) contains its 22
  equations as real, parseable OMML XML, not images -- previous sessions'
  attempts to read it (LibreOffice import failures, plain-text extraction)
  never actually parsed the math itself. Wrote a real OMML-to-text converter
  (recursively walking `m:oMath`/`m:f`/`m:sSup`/`m:sSub`/`m:d`/`m:nary`/etc.
  and interleaving with the surrounding paragraph/table text in document
  order) and got a complete, faithful linear transcript of the whole SI for
  the first time this project has had one. (2) The main paper's own equations
  were re-extracted with `pdftotext -layout` rather than read visually off a
  rendered page image -- layout-preserving text extraction turns out to keep
  superscript/subscript exponents correctly attached to their base terms,
  which a purely visual read of a small rendered image can miss.

  This confirmed, directly from the primary source rather than by inference,
  every sign/exponent error this project had previously suspected from
  external methods or numeric implausibility alone -- worth stating plainly
  since Matt separately recalled Armen mentioning a typo in one of the
  equations that the devs later fixed, and asked whether it's the same thing
  found here. Three real, confirmed typos exist, not one:
  - **Main paper Eq. 1** (the central water-redistribution equation, not a
    supplementary footnote) prints the numerator's conductivity exponent as
    `(2+3b)`. With realistic Saxton-Rawls b values (roughly 4-10), that
    exponent runs 15-35, collapsing conductivity to ~0 everywhere except
    within a hair of saturation -- confirmed nonsensical directly, not just
    suspected. Read as `2+3/b` (a division slash almost certainly lost in
    typesetting), it exactly reproduces Campbell's (1974) own independently
    well-known textbook form K(theta)=Ksat*(theta/theta_sat)^(2b+3) -- both
    the numeric implausibility of the literal reading and the exact match to
    a citable standard formula point the same direction. This is the
    strongest single candidate for what Armen described: it's in the
    flagship equation of the methods section, the error is dramatic enough
    that anyone actually running the equation would hit it immediately, and
    it has the exact signature of a single lost character in typesetting.
    Already found and corrected in this engine (`campbell_khe()`,
    2026-09-23) before this audit -- this pass confirmed it against a clean
    primary-source re-read rather than changing anything.
  - **SI Eq. SI.2** (SCS-CN runoff) prints the denominator as `Win - 0.8S`.
    Plugging in realistic values gives negative runoff outright (e.g.
    Win=30mm, S=40mm -> Q=-242mm). The standard SCS-CN derivation (and every
    external source) requires `Win + 0.8S`, which gives a sensible, always-
    positive result. Already corrected in `runoff_mm()`.
  - **SI Eq. SI.6** (wet curve number) prints `CN_wet = CNb/(0.4-0.006*CNb)`.
    This denominator goes negative for any CNb above ~66.7 -- not a rare edge
    case, it breaks for MOST real agricultural curve numbers (including this
    project's own default of 75). The corrected `0.4+0.006*CNb` gives
    sensible values (CN_wet > CNb, properly bounded under 100) across the
    entire realistic range. Already corrected once (2026-09-22) but later
    superseded by a different, SWAT+-sourced formula family entirely (see
    `retention_param_mm()`) rather than the SI's own now-confirmed structure
    -- flagged as worth reconsidering: the SI's own Eq. SI.5-SI.7 describes a
    CN_dry/CN_wet-plus-linearly-interpolated-fwc mechanism, structurally
    different from the SWAT-sourced continuous S(SW) function currently
    implemented. Not reverted in this pass (the SWAT substitute is real and
    was itself numerically verified), but worth testing head-to-head now
    that the SI's own equations can be read precisely rather than
    approximately, since Eq. SI.5-SI.7 is literally what this paper says
    Cycles itself computes.

    **Update (2026-09-24), tested head-to-head as flagged above -- kept the
    SWAT-sourced version, not a close call once the full picture is
    considered.** Built the SI's own literal Eq. SI.5-SI.7 path as a scratch
    A/B alternative: `si_cn_dry(cnb)=cnb/(2.3-0.013*cnb)` (Eq. SI.5, no sign
    issue -- checked numerically, gives sensible values throughout the
    realistic range as printed); `si_cn_wet(cnb)=cnb/(0.4+0.006*cnb)` (Eq.
    SI.6, sign-corrected); `si_fwc()`, reusing this project's own pre-SWAT
    depth-weighted-to-0.6m interpretation (recovered from git history, commit
    0917a44^ -- the same defensible-but-unverified reading of the SI's words
    already documented above, since the SI still gives no exact formula for
    this piece either way); and `CN = CN_dry+(CN_wet-CN_dry)*f_wc` (Eq.
    SI.7), converted to a retention parameter via the same standard
    `S=254*(100/CN-1)` used everywhere else in this engine.

    Tested against both established benchmarks. Rock Springs (4-crop suite):
    tiny, mixed movements in both directions -- corn 0.547->0.550, soybean
    0.858->0.856, wheat 0.399->0.393, silage corn 0.512->0.519, none moving
    by more than 0.007. Kansas (6-year benchmark, fresh-start and 1-year
    chained): essentially identical -- fresh-start mean overshoot 3.63x
    (SWAT) vs. 3.67x (SI), MAE 1.454 vs. 1.495; chained mean overshoot 2.16x
    both ways, MAE 0.628 vs. 0.640. Neither formula family is meaningfully
    better or worse at either site -- a genuine wash, not a close win for
    either side.

    Given accuracy doesn't distinguish them, the deciding factor is
    disclosure completeness, and there the SWAT-sourced version wins clearly:
    `cn_dry()`/`cn_wet()`/`retention_param_mm()`'s continuous S(SW) function
    are ALL real, cited, exact formulas with zero undisclosed components.
    The SI's own Eq. SI.5-SI.7, even with both signs now correctly read,
    still needs `f_wc`, and neither the paper nor the SI gives an exact
    formula for it -- only "1 for a soil saturated to 0.6m depth... decreases
    to zero if air-dry... weighted based on depth, with the soil surface
    having the most importance" (still true after this session's much more
    careful SI read; nothing new on this specific point turned up). Switching
    to the SI's own literal structure would trade one set of fully-disclosed
    formulas for a mix of disclosed formulas plus a still-guessed weighting
    scheme, for no accuracy gain -- not a faithfulness improvement despite
    initially looking like one. Kept the current SWAT-sourced implementation
    unchanged; the SI path was a scratch test only, not committed anywhere.

    **Update (2026-09-24), a real attempt to find f_wc's own exact formula
    directly, per Matt's "or we go find f_wc ourselves."** Tried eight
    distinct sources before concluding it's genuinely unreachable this
    session, not just under-tried: CropSyst's own manual page describing its
    curve-number method (`sites.bsyse.wsu.edu/cs_suite/CropSyst/manual/
    simulation/soil/runoff/curve_number.htm` -- the single most specific,
    promising lead, since the main paper states outright "Cycles shares
    biophysical fundamentals with CropSyst," meaning this water balance was
    very plausibly inherited near-verbatim); both of Kemanian's own prior
    papers already sitting locally in this repo (`KemanianStockle2010.pdf`,
    `overview-of-c-farm-dec-2008-web-document_2.pdf` -- checked directly via
    `pdftotext`, confirmed neither describes the water balance beyond naming
    "runoff" as an output, deferring entirely to CropSyst's own module, the
    same conclusion already reached once before this session for the carbon
    submodel specifically); Williams et al. (2012) itself, the paper the SI
    already cites for the slope factor (Eq. SI.4) and whose title
    ("...application to CONTINUOUS runoff simulation") made it a strong
    second candidate for the whole moisture-adjustment mechanism, not just
    the slope piece; and Wikipedia's CropSyst page. Every direct fetch
    (`WebFetch`, and a raw `curl` for two of them) returned `EGRESS_BLOCKED`
    -- including, notably, `en.wikipedia.org` and `ars.usda.gov`, neither of
    which any prior session's documented network-policy hits (fao.org,
    swat.tamu.edu, arxiv.org, researchgate.net, core.ac.uk) had flagged as
    blocked before, suggesting this session's egress policy is tighter than
    usual, not that this particular formula was searched for carelessly.

    `WebSearch` itself (a separate tool/pathway, evidently not subject to
    the same domain restrictions) did surface one real, if modest, useful
    fact worth keeping: the continuous-CN literature this whole area
    descends from draws a clear line between two real, named families --
    a "Revised Soil Moisture Index" (SMI) method, driven by accumulated
    evapotranspiration/climate history rather than a direct moisture
    reading, and an "SMCII"-style method, driven directly by actual current
    soil water content ("soil features," in one search summary's own
    phrasing). The SI's own description of f_wc ("saturated to a depth of
    0.6m... weighted based on depth") is unambiguously the second kind, a
    real soil-moisture reading, not a precipitation/ET accounting index --
    confirming (not just assuming) that `retention_param_mm()`'s own
    approach (continuous, driven by the profile's actual current SW) is in
    the right conceptual family, even without the exact depth-weighted
    formula itself. Not enough to justify a change on its own -- flagged as
    context, not a fix. f_wc's exact formula remains a genuine, disclosed-
    only-in-words gap; worth a retry if this sandbox's network policy ever
    loosens, particularly for the CropSyst manual page specifically.

    **Update (2026-09-24), f_wc found for real -- Matt personally obtained
    and uploaded the two papers this file recommended, resolving the last
    open piece of this item.** `cropsyst.pdf` (Stockle, Martin & Campbell
    1994, "CropSyst, a cropping systems simulation model: water/nitrogen
    budgets and crop yield") turned out to be a dead end for this specific
    question -- read in full via `pdftotext -layout`, it only cites "the
    USDA-SCS curve number approach (USDA-ARS, 1972)" by name for runoff,
    with no moisture-adjustment equation of its own given anywhere. The
    real find was in the SECOND paper: Williams, Kannan, Wang, Santhi &
    Arnold (2012, J. Hydrologic Engineering 17(11):1221-1229,
    "williams-et-al-2011-evolution-of-the-scs-runoff-curve-number-method...
    .pdf") -- already on this list as a candidate (above), now actually
    read. Its Eq. 16 is a real, disclosed depth-weighting function built
    for exactly this purpose in the same curve-number lineage: `FFC* =
    sum(FFCl*(Zl-Zl-1)/Zl) / sum((Zl-Zl-1)/Zl)`, summed over soil layers
    with cumulative bottom depth `Zl<=`(a cutoff, 1.0m in the paper's own
    application), applied to their Eq. 11 fraction-of-field-capacity
    (`FFC=(SW-WP)/(FC-WP)`). The paper states its own intent in words that
    match Cycles' SI description almost verbatim: dividing by `Zl` "reduces
    the influence of lower layers," multiplying by layer thickness "gives
    proper weight to thick layers relative to thin layers" -- precisely
    Cycles' own "weighted based on depth, with the soil surface having the
    most importance," now with an actual formula behind it. Implemented as
    `depth_weighted_ffc()`, using Cycles' own stated 0.6m cutoff (not
    Williams' own 1.0m, calibrated for a different model family, APEX/
    SWAT) and summing only whole layers within the cutoff (the paper's own
    literal quantifier, not a fractional split of a straddling layer --
    Rock Springs' own layer boundaries land exactly on 0.6m with no
    straddle to resolve there anyway).

    With a real f_wc in hand, re-ran the exact SI-vs-SWAT test from the
    update above, this time with `depth_weighted_ffc()` instead of the old
    ad hoc saturation-fraction guess. This changes the verdict: at Rock
    Springs, movements stayed noise-level in both directions (corn
    0.547->0.550, soybean 0.858->0.856, wheat 0.399->0.393, silage corn
    0.512->0.518, none beyond 0.006) -- but at the harder, more diagnostic
    6-year Kansas benchmark, the real f_wc improved every one of four
    metrics: fresh-start correlation 0.975->0.981, fresh MAE
    1.454->1.435, chained correlation 0.976->0.983, chained MAE
    0.628->0.536. The disclosure-completeness argument that favored SWAT
    in the prior update no longer applies either -- `cn_dry()`/`cn_wet()`/
    `depth_weighted_ffc()` are now ALL Cycles' own literal, cited formulas
    (Eq. SI.5/SI.6, sign-corrected, plus the newly-sourced f_wc), not a
    substitute borrowed from a different model family. Shipped: `cn_dry()`/
    `cn_wet()` reverted to the SI's own literal formulas, `retention_param_mm()`
    rewritten to use `CN=CN_dry+(CN_wet-CN_dry)*f_wc` (Eq. SI.7) directly,
    the SWAT-sourced continuous S(SW) function removed. Calibration
    factors re-derived for all four crops to keep means matching real
    output exactly (corn 0.8818->0.8775, soybean 1.2318->1.2238, wheat
    0.8290->0.8288, silage corn 0.8591->0.8554). This closes out this
    item for real -- the whole curve-number mechanism is now Cycles' own
    disclosed structure end to end, no substitute formula left in it.

  Cross-referenced everything else in both documents relevant to what this
  engine implements. Confirmed correct as already built: Eq. 3-5 (the
  min(GR,GT) radiation/transpiration growth minimum), Eq. 6 (the canopy-cover
  double sigmoid, including the exact hardcoded default shape constants 6,
  -20, -15, 16 for a "normalized plant density of 1"), SI Eq. SI.1 (potential
  transpiration TRp), SI Eq. SI.8 (shoot partitioning), and SI Eq. SI.9
  (harvest index) all match the primary source exactly, now confirmed rather
  than assumed. Found one genuine, complete, fully-disclosed gap: **Eq. 7**,
  a plant-density adjustment to canopy cover
  (`eie(PDf) = 1 - exp(ln(1-ei)*sqrt(PDf))`), was never implemented at all --
  see the entry below for the fix. Two smaller, lower-priority items: Eq. 2
  gives an exact formula for Cycles' real adaptive sub-daily time step
  (based on each layer's own travel time), which this engine approximates
  with a fixed 24-substep scheme (already numerically converged, so low
  priority to change); and the main paper mentions diffuse-radiation
  conditions can raise radiation-use efficiency by ~20%, not usable without
  diffuse-fraction weather data this project doesn't have.

- **Eq. 7 (plant-density adjustment to canopy cover) implemented (2026-09-24),
  the direct result of the audit above.** A complete, disclosed, one-line
  formula from the main paper, never built: `effective_canopy_cover(ei, pdf)`
  = `1 - exp(ln(1-ei)*sqrt(pdf))`, applied to `canopy_cover()`'s own output
  (`ei`, Eq. 6) at both call sites (`_reference_n_demand()` and the main
  `simulate_season()` loop) via a new `plant_density_factor` crop parameter,
  defaulting to 1.0 -- confirmed an exact no-op at that default (to full
  float precision: `ln(1-ei)*sqrt(1)=ln(1-ei)`, so `1-exp(ln(1-ei))=ei`
  identically), so every currently-validated crop is unaffected since none
  sets this parameter. Verified: the full 4-crop validation suite reproduces
  byte-identical correlations (corn 0.547, soybean 0.858, wheat 0.399, silage
  corn 0.512). The mechanism itself does something real and sensible when
  used -- swept `plant_density_factor` from 0.7 to 1.6 at Rock Springs 2012
  corn (N=650, non-limiting): grain rises monotonically with diminishing
  returns (10.02 -> 10.43 -> 10.68 -> 10.86 Mg/ha), matching the real
  agronomic pattern (denser stands close canopy faster and capture more
  early-season radiation, with the benefit tapering off) rather than an
  artifact. Composes correctly with tillage (re-verified the standing
  moldboard-plow sanity check at plant_density_factor=1.3: real yield gain
  at a nitrogen-limiting rate). Ported into both embedded `ENGINE_SOURCE`
  copies identically, confirmed byte-identical to each other afterward
  (49665 bytes each) and reproducing the canonical script's exact numbers
  through the embedded copy. No UI wiring anywhere -- engine-only, matching
  the "engine first, UI later" pattern already used for the six mechanisms
  added 2026-09-17 and everything since. `model-validation.html`'s own "Full
  simulation controls" form (which exposes every other `simulate_season()`
  parameter) is the natural place to add a density control if this is picked
  up again.

- **Wheat's real dominant driver is nitrogen, not water -- and the missing
  piece turned out to be that our nitrogen supply mechanism had zero year-
  to-year weather variability, now fixed with a real, sourced external
  formula (2026-09-24).** Re-checked the "wheat's real reported water
  stress is far larger than real soil moisture would explain" anomaly
  (item 7, and the "Follow-up diagnostic session" entry elsewhere in this
  file) and found the whole premise rested on a column-misread: precisely
  re-parsed real Cycles' own `WinterWheat.txt` at the exact flagged row
  (2012-03-16) and found `N STRESS = 59.5373`, `WATER STRESS = 0.0` -- the
  "59.5% water stress" quoted since 2026-09-10 was actually N stress,
  attributed to the wrong column. Confirmed with a direct correlation
  check: real wheat yield correlates -0.894 with real Cycles' own max-per-
  season N stress across all 9 harvested years, and only 0.359 with max
  water stress. Every water-balance fix this session (including today's
  f_wc resolution) has been improving a mechanism that isn't wheat's actual
  dominant driver.

  Checked whether the full six-pool nitrogen system (SI Eq. SI.10-14,
  finally readable this session via the OMML parser) could close this for
  real: the differential equations for microbial/soil carbon pools and
  their saturation-scaled efficiency/decomposition factors are genuinely
  disclosed now, but the actual rate constants (k_ra, k_rt, k_rz, k_rm,
  k_m, k_s), the soil-environment scalar fE, the microbial-cap scalar fA,
  and the saturation capacity C_sx are not given anywhere -- not in the
  paper, the SI, or any of Cycles' own input files (checked
  `GenericCrops.crop` and the `.soil` files directly, nothing). The
  structure is disclosed; the numbers that make it run are not. Confirms
  the full six-pool system is still correctly out of v1 scope, now for a
  more precise reason than originally stated.

  Tested applying wheat's real disclosed fertilizer input (90 kg N/ha UAN
  broadcast at DOY 75, from `CornSilageSoyWheat.operation`) plus the
  paper's own real disclosed previous-crop credit (60 kg N/ha for maize
  following soybean, SI Sec. IX -- wheat also follows soybean in this
  rotation, never previously tested for wheat specifically): correlation
  went 0.393 (no nitrogen tracking) -> 0.017 (90 kg/ha alone) -> 0.219
  (90 + the real 60 kg/ha credit) -- real, disclosed, and a genuine
  improvement over 90-alone, but still worse than not modeling nitrogen at
  all. Diagnosed why rather than concluding the credit just isn't enough:
  `BACKGROUND_N_KG_HA_DAY` is a flat 0.5 kg N/ha/day constant with no
  year-to-year variability at all, so even the right total nitrogen amount
  can fix the mean level but can't reproduce which specific years get more
  or less N-stressed -- exactly what a -0.894 yield/stress correlation
  requires.

  Found a real, external, non-Cycles-specific formula for the missing
  piece: RothC (Rothamsted Research's own soil carbon model, Coleman &
  Jenkinson, widely cited since the 1990s) publishes exact temperature and
  moisture rate-modifiers for organic-matter decomposition. Got them from
  the model's own literal Fortran source
  (github.com/Rothamsted-Models/RothC_Code/blob/master/RothC.for) after a
  web-search summary of the same formula came back transcribed wrong --
  `RM_TMP = 0` below -5C, else `47.91/(exp(106.06/(T+18.27))+1.0)`; a
  moisture factor that ramps linearly between 0.2 and 1.0 across a
  wilting-point-to-field-capacity-like range. Adapted the moisture piece
  to this engine's own already-tracked topsoil `theta/fc/pwp` rather than
  reproducing RothC's own separate soil-moisture-deficit bookkeeping.
  Implemented as `rothc_temp_factor()`/`rothc_moisture_factor()`,
  multiplied into `BACKGROUND_N_KG_HA_DAY` in both `_reference_n_demand()`
  and `simulate_season()`'s main loop (mirrored, the same discipline
  already required for tillage's own dr/ft tracking) and into
  `engine-demo.html`'s own `bare_fallow_leaching()` counterfactual (so the
  cover-crop-vs-bare-fallow comparison stays fair on both sides). Result:
  correlation 0.017 -> **0.473** (90 kg/ha alone, weather-varying
  background) and 0.219 -> **0.431** (90 + the real 60 kg/ha credit,
  weather-varying background) -- both now beat the 0.393 no-nitrogen-
  tracking baseline, the first nitrogen-side change this session to
  actually help wheat past where "don't model it" already stood.

  Verified safe before shipping: `_reference_n_demand()` is only ever
  called when nitrogen tracking is active at all (confirmed with a call
  counter: zero calls during the standard `run_validation.py`/
  `run_validation_rotation2.py` suite, none of which pass nitrogen
  parameters), so this is completely inert on the headline
  0.550/0.856/0.393/0.518 correlation numbers -- re-ran the full suite
  and confirmed byte-identical. Mass balance re-verified to close exactly
  (uptake+leached+remaining = applications+credit+background, checked to
  six decimal places with the new weather-varying background included).
  The standing tillage sanity check (moldboard plow: real yield gain at a
  nitrogen-limiting rate, zero at a non-limiting rate) and the manure-
  availability-equivalence check (200 kg manure @ 0.5 = 100 kg mineral,
  byte-identical) both re-verified to still pass with the new factor
  composed in. Ported into both embedded `ENGINE_SOURCE` copies
  identically, confirmed byte-identical to each other afterward (51223
  bytes each), and confirmed the extracted embedded engine executes
  cleanly and reproduces the same numbers.

  Real, disclosed consequence: this changes nitrogen dynamics everywhere
  they're used, not just wheat -- corn's own nitrogen-tracking runs (e.g.
  Rock Springs 2012, N=50, no tillage) moved from 5.0253 to 4.9683 Mg/ha,
  a real, expected shift from the same mechanism now varying by weather
  instead of being flat. Every specific number already documented
  elsewhere in this file or in CLAUDE.md for `engine-demo.html`'s
  nitrogen-sweep/frontier/rotation panels (built against the old flat
  background) will not reproduce exactly if re-run now -- not re-verified
  panel by panel here, the same disclosed-not-exhaustive standard already
  applied to the last several engine-wide fixes this session; re-check a
  given panel's numbers when it's next touched, not before.

- **CropSyst's own public source code confirmed as a real, independent
  cross-check (2026-09-25), not just a hoped-for lead.** Found CropSyst has
  genuine, public `.cpp` source (unlike Cycles, which ships binaries only) at
  `mingliangwsu/VIC-CropSyst-Package` on GitHub, a WSU-affiliated research
  repo coupling CropSyst to the VIC hydrology model. Two of this session's
  own already-shipped, independently-derived fixes were confirmed EXACTLY
  correct by CropSyst's own real code, not just plausible: (1) the Eq. 1
  Campbell conductivity exponent, read as `2+3/b` after concluding the paper's
  own printed `(2+3b)` was a lost division slash -- CropSyst's
  `soil/hydraulic_properties.cpp` computes the identical `2.0*Campbell_b+3.0`
  and, separately, `2.0+3.0/get_Campbell_b(...)`, in two different functions.
  (2) The Williams et al. 2012 depth-weighted `f_wc` formula already shipped
  (`depth_weighted_ffc()`) -- CropSyst's own `soil/runoff_SCS.cpp` computes
  the identical thickness-over-cumulative-depth weighting structure
  (`layering = layer_thickness/sublayer_depth`, summed and normalized) for
  the same purpose. Neither cross-check changed any shipped code; both are
  now noted in the relevant items above as independently confirmed rather
  than resting on this session's own derivation alone. Also found, but out of
  scope to use: `organic_matter/single_pool/OM_single_pool.cpp` has a code
  path literally gated on a `KEMANIAN_HUMIFICATION` preprocessor flag (direct
  evidence of the shared lineage), and `organic_matter/OM_const.h` has real
  numeric decomposition rate constants for a multi-pool SOM scheme (microbial
  0.005/day, labile-active 0.02/day, metastable-active 0.0005/day, passive
  0.0000185/day) -- real data for the six-pool system's own still-undisclosed
  rate constants (see the redistribution/decomposition items above), not
  pursued further since using it means building the full six-pool subsystem,
  already correctly scoped out of v1 as a genuine new subsystem, not a
  parameter swap.

- **Nitrogen stress rebuilt as a real day-by-day mechanism (2026-09-25), and
  `_reference_n_demand()` removed entirely.** The season-total quadratic-
  plateau mechanism above (item 6/20's context) worked, but only by computing
  a whole-season nitrogen demand up front via a separate function
  (`_reference_n_demand()`) that duplicated the main loop's own water/canopy
  physics -- a standing structural risk (exactly the bug class that let
  irrigation silently go missing from that function earlier this session,
  undetected until a specific feature combination was tested) and a
  mechanism that judged nitrogen stress by a season-total ratio rather than
  the plant's own actual nitrogen status on a given day.

  Found a real, better mechanism via CropSyst's own public source
  (`crop_N_common.cpp`, `mingliangwsu/VIC-CropSyst-Package`, the same repo
  already cross-checked above): `N_reduction_factor =
  1-(Ncrit-Nactual)/(Ncrit-Nmin)`, clipped to [0,1] -- a function of the
  plant's own actual tissue nitrogen concentration that day. `Ncrit` was
  already computed here (`n_critical_pct()`, the standard dilution curve,
  previously dead code with no caller). `Nmin` needed a real source: the
  user supplied Lemaire, Jeuffroy & Gastal (2008), *Eur. J. Agron.* 28:614-624
  ("plant and crop N status paper.pdf", now on `main`), which gives real,
  crop-specific dilution-curve coefficients (Table 1) and the Nitrogen
  Nutrition Index framework (NNI=Na/Nc) -- but no separate Nmin curve at all,
  only a generic, non-crop-specific ~0.8% structural-tissue asymptote (Eq.
  4-6). Used Cycles' own real, crop-specific `N_MIN_CONCENTRATION_STRAW`
  field instead (0.2% for corn/wheat/silage corn in `GenericCrops.crop`) --
  a disclosed reinterpretation of a real number nominally scoped to
  grain/straw partitioning elsewhere in Cycles' schema, for the same
  conceptual role (a low, mostly-structural-tissue floor) CropSyst's own
  Nmin plays.

  Implementation: a new day-by-day `canopy_n_kg_ha` state tracks cumulative
  plant nitrogen; each day's actual concentration is compared against that
  day's critical concentration at current biomass, and the resulting stress
  fraction multiplies growth directly. Daily uptake is funded from the
  nitrogen pool via the existing marginal-demand-rate function applied to
  that day's already-stressed growth (not potential growth, avoiding
  circularity). `_reference_n_demand()` was removed entirely, not just
  superseded -- there's now only one loop, closing off the whole bug class.

  Verified against every standing benchmark: the full 4-crop suite is
  byte-identical to three decimals wherever nitrogen tracking is inactive
  (corn 0.550, soybean 0.856, silage corn 0.518). Wheat's own validated
  correlation (already improved to 0.473 by item 20's fertilization fix)
  improved further under the new mechanism, 0.473 -> **0.523** (MAE 0.44
  Mg/ha, mean recalibrated to match exactly). Corn was re-tested with its
  own real nitrogen input under the new mechanism too and still doesn't
  beat its no-tracking baseline (0.5095 vs. 0.550) -- consistent with the
  already-documented finding that corn's real nitrogen stress correlates
  only weakly with its own yield (-0.21), unlike wheat's dominant driver
  (-0.894), so corn's default validation path correctly continues not to
  track nitrogen. The standing tillage sanity check, the manure-
  availability-equivalence check, and the nitrogen mass-balance identity
  were all re-verified to still pass, in both the canonical engine and both
  embedded copies after porting -- including a real gap caught mid-port
  (the embedded copies had never defined `n_critical_pct()` at all, since it
  was dead code in the canonical script too until this fix made it
  load-bearing, and the embedded `CORN`/`WHEAT` dicts needed the real
  `n_min_conc=0.002` value added explicitly rather than silently falling
  back to a 0.0 default). Real, disclosed consequence: every specific
  nitrogen-tracking number already documented elsewhere in this file or in
  CLAUDE.md (built against the old season-total mechanism) will not
  reproduce exactly if re-run now -- not re-verified panel by panel here,
  the same disclosed-not-exhaustive standard already applied to the last
  several engine-wide fixes this session.

- **Water stress and transpiration rebuilt as a real hydraulic-conductance
  mechanism (2026-09-25), replacing the pooled root-zone-availability
  approach responsible for the long-standing "root discovery" artifact --
  a real, mixed result, kept anyway.** Kemanian et al. 2024 cites a
  specific mechanism by name for Cycles' own transpiration/water-stress
  model (Campbell 1985, extended by Jara & Stockle 1998) but never gives
  its formulas -- the paper only names it. Traced it two independent ways:
  CropSyst's own public C++ source (`mingliangwsu/VIC-CropSyst-Package` --
  Cycles shares its biophysical fundamentals with CropSyst, and unlike
  Cycles this repo ships real source, not just binaries --
  `transpiration.cpp`'s `Crop_transpiration_2` class and
  `crop_common.cpp`'s `water_stress` definition), and the actual WSU
  CropSyst manual's own "Crop Transpiration" page
  (`modeling.bsyse.wsu.edu`, blocked from this sandbox directly; retrieved
  via the Wayback Machine outside this sandbox and pasted in verbatim).
  The two corroborate each other's structure exactly (a harmonic-mean
  root/plant conductance split; a leaf-water-potential stress ratio that
  matches the C++ code's own `transpiration_ratio` calculation).

  This replaces the engine's original mechanism -- a single POOLED
  root-zone available-water ratio (avail water summed across every layer
  within root depth, divided by capacity) -- which is the diagnosed cause
  of the "root discovery" artifact documented under item 6 above: a
  shallow, nearly-dry layer's real stress got masked the instant root
  growth reached a deeper, still-full layer, since pooling before
  computing one ratio structurally cannot distinguish "water exists
  somewhere in the root zone" from "the crop can actually use it." The new
  mechanism instead computes each active layer's own real soil water
  potential and solves for the single leaf water potential consistent
  with ALL of them and the crop's real total root conductance, then
  extracts each layer's own uptake from that shared value -- a layer near
  wilting point contributes almost nothing on its own terms, by
  construction, regardless of how much water a different layer holds.

  One real, disclosed gap even in this simpler formula: `fl`, the fraction
  of total root length in each layer. CropSyst's own exact formula for
  this (`crop_root.cpp`'s `Crop_root_vital` class) needs
  `density_distribution_curvature` and `surface_density`, real per-crop
  parameters with NO default anywhere in the C++ source, in Cycles' own
  `GenericCrops.crop`, or in the one further WSU manual page (the "root
  editor") that would very likely carry them -- not found despite a real
  search attempt from both inside and outside this sandbox. Substituted
  with FAO-56's own real, disclosed 40/30/20/10 depth-quartile
  root-water-extraction weighting instead -- a real, sourced
  approximation, not CropSyst's own exact shape.

  One further, disclosed correction: the manual's own pasted closed-form
  solution for the STRESSED leaf-water-potential case diverges to 1.5x the
  wilting potential under extreme demand when checked numerically -- not
  physically sensible, and consistent with a transcription error in that
  one line (the same class of OCR/typesetting slip already documented
  elsewhere in this project for the SI's own sign errors). Solved the
  manual's own STATED implicit relationship directly via plain algebra
  instead, which gives the physically expected smooth approach to the
  wilting potential in the same limit.

  Result: real, verified, and genuinely mixed, not a clean win. At Rock
  Springs (the only site with real per-year ground truth for all four
  crops): corn 0.550->0.527, soybean 0.856->0.802, silage corn
  0.518->0.516, and winter wheat **0.523->0.332** -- the largest single-crop
  cost. Instrumented every real wheat season under the new mechanism and
  found `water_stress` reads EXACTLY 1.0, every single day, all 9
  validated years -- wheat never once triggers water stress at Rock
  Springs under its own real `LWP_STRESS_ONSET`=-1000 J/kg threshold.
  Confirmed this is the mechanism working correctly, not a bug, by
  artificially drying the soil layers in isolation and confirming stress
  DOES trigger then (0.50 at 5% available water) -- real Rock Springs
  soil, under wheat's own real root profile and water balance, simply
  never gets remotely that dry on its own. This flattens whatever
  (arguably not fully physically grounded) water-driven variability the
  old pooled mechanism gave wheat, costing real correlation even though
  wheat's actual dominant driver is nitrogen, not water (-0.894 vs. 0.359,
  already established above).

  At the harder, more diagnostic 6-year Kansas benchmark (semi-arid, corn,
  real STATSGO2 soil, real NLDAS-2 weather, real native-Cycles reference
  runs for 1988/1993/2005/2008/2012/2016) -- the benchmark this whole
  rebuild was motivated by -- the result is a genuine improvement in error
  but not a clean directional fix: fresh-start mean overshoot fell from
  3.63x to 3.24x (2012 specifically 12.49x->11.84x); the one-year-carryover
  chained case flipped from a 2.16x OVERshoot to a 0.73x UNDERshoot (2012:
  6.19x over -> 0.28x under) -- but mean absolute error actually IMPROVED
  despite the bias direction flipping (chained MAE 0.54-0.63->0.35 Mg/ha),
  and correlation stayed high both ways (fresh 0.973, chained 0.986). The
  "root discovery" symptom this was built to fix is real and reduced; it
  did not cleanly resolve into "now correctly calibrated," it resolved
  into "wrong in the other direction, by less."

  Kept despite the Rock Springs cost -- a real project decision, not an
  automatic one, made after presenting both benchmarks' before/after
  numbers directly: the new mechanism replaces a mechanism already known
  to be structurally wrong with the actual cited physics, corn's own
  water-stress response is now genuinely more realistic (varies
  meaningfully year to year, e.g. a real 2016 minimum of 0.23, not just a
  level shift), and the Kansas benchmark's absolute error improves even
  though its bias flips. Wheat's specific non-triggering finding is a
  real, disclosed, evidence-backed result, not smoothed over --
  recalibrated (`calibration_factor` only, which never changes
  correlation) rather than reverted. Ported into both `engine-demo.html`'s
  and `model-validation.html`'s embedded engine copies, confirmed
  byte-identical between the two files' shared engine code afterward
  (their own `WHEAT` crop dicts legitimately differ in
  `calibration_factor` only: `engine-demo.html`'s copy is used solely for
  the fall-planted cover-crop role, never itself validated against real
  Cycles output the way `model-validation.html`'s cash-crop scenario is,
  so it was rescaled by the same ratio rather than freshly recalibrated
  against a scenario it doesn't run). See `model-validation.html`'s own
  gap-list item 23 for the full write-up with inline citations.

- **Real bug found in `campbell_water_uptake()` (item 23's own mechanism) during a
  follow-up "expert modeler" review, 2026-09-28: false full water stress whenever
  the root zone hasn't yet grown past the excluded evaporative layer.** The
  CropSyst manual's own rule ("no transpiration is allowed from soil layer one,
  the evaporative layer") is correctly implemented in `root_length_fraction_by_layer()`
  -- it returns an all-zero `fl` array while `root_depth_m` is still within layer[0]'s
  thickness, since no transpiring layer is reachable yet. But `campbell_water_uptake()`
  never checked for that all-zero case before dividing `actual_mm / trp_mm_day` to get
  `water_stress` -- with `sum(fl)==0`, every per-layer contribution is skipped, so
  `actual_mm` stays 0.0 and the ratio reports `water_stress=0.0`, i.e. FULL stress,
  regardless of how wet the soil actually is. This is backwards: the correct reading
  of "no root-accessible layer exists yet" is "no stress signal available," not
  "maximum stress."

  Confirmed this is real and reachable in the actual day loop, not just a synthetic
  edge case: at Rock Springs (root_max_m=2.0, tt_emergence=65 -> ttf_emergence=0.036,
  layer[0] only 0.05m thick) root_depth already clears layer[0] by the time `eie`/`TRp`
  first turn nonzero at emergence, so this specific bug never actually triggers within
  Rock Springs' own validation suite -- re-running the full embedded engine confirmed
  the fix changes NOTHING there (2012 corn @ N=650: 9.883807722449967 Mg/ha, byte-identical
  before and after). At a thicker-topsoil site it's a different story: a real STATSGO2-style
  Kansas profile (layer[0]=0.33m) keeps `fl` at all-zero from ttf=0.036 (emergence) through
  ttf~0.099 -- a real 15-20 day window, not a single day -- during which the old code
  reported the crop as fully water-stressed no matter what the soil moisture actually was.
  Fixed with an explicit `if sum(fl) <= 0: return 0.0, 1.0` guard (0 mm extracted, water_stress=1.0,
  i.e. "no signal, assume unstressed" rather than "assume worst case") immediately after
  computing `fl`.

  Could not re-run the full 4-crop Rock Springs suite or the 6-year Kansas benchmark against
  real Cycles reference data for this specific fix -- the container was reprovisioned since
  item 23's own work and `/tmp/cycles-run` (real Cycles binaries, weather/soil inputs, and
  reference output) along with the Kansas benchmark scripts no longer exist in this instance.
  What was verified instead, against the actual embedded engine strings (not a reimplementation):
  the Rock Springs null result above; a direct scan of `root_length_fraction_by_layer()`'s
  output across realistic thermal-time values on a synthetic Kansas-shaped soil profile,
  confirming the all-zero window and the corrected before/after behavior at each point; the
  standing tillage sanity check (moldboard plow: real yield gain at a nitrogen-limiting rate,
  zero at a non-limiting rate) still passes; manure/mineral nitrogen equivalence still holds
  exactly; and the nitrogen mass-balance identity (uptake+leached+remaining = total supply)
  still closes. Ported identically into both `engine-demo.html` and `model-validation.html`'s
  embedded engine copies, confirmed to grow by the same byte count in both and to remain
  byte-identical to each other apart from the pre-existing, intentional `WHEAT`
  `calibration_factor` divergence documented above. Since this bug's practical impact is
  specifically concentrated at thick-topsoil, non-Rock-Springs sites (Kansas being the one
  this project already tracks), any future re-run of the 6-year Kansas benchmark should show
  a real, if likely modest, further reduction in fresh-start overshoot on top of the gains
  already logged in item 6 above -- not yet confirmed with fresh numbers, flagged here rather
  than guessed at.

- **The wheat "0.523" figure quoted throughout this project since 2026-09-25 was never
  reproducible, and a real, separate demand-scaling bug was found and fixed in the shared
  day-by-day nitrogen mechanism (2026-09-28).** Found while deliberately setting wheat aside
  ("nail down corn, not the exception") and focusing on corn's own optional nitrogen-tracking
  path, which corn's default validation never exercises at all.

  A real git-bisect against a freshly-obtained, hash-verified Cycles v1.4.4 reference
  (`ContinuousCorn`'s own output matched the documented historical md5 exactly, confirming
  the reference setup itself is trustworthy) checked out and ran every commit since the
  day-by-day nitrogen rebuild, including the exact commit whose own comment names it as the
  0.523 measurement point. Every one of them gives 0.411 against this real data, not 0.523.
  The real reference wheat yields match this project's own historical numbers exactly (mean
  3.92 Mg/ha to two decimals -- an implausible coincidence if the underlying data had changed),
  the soil file matches `SOIL_LAYERS_RAW` exactly, and the weather file is the same one
  `ContinuousCorn` already validated byte-for-byte. So this isn't the same kind of
  data-provenance problem as the earlier corn 0.771-vs-0.540 correction -- the code, run
  against real data it should reproduce, simply doesn't reproduce the number this project had
  been quoting. Most likely explanation: 0.523 was measured against a real Cycles reference in
  an earlier, since-wiped container instance whose own setup differed in some way that can no
  longer be reconstructed. Not worth chasing further -- the ground truth it would need to be
  checked against no longer exists.

  Separately, while checking corn's own optional N-tracking path against this same real data:
  `simulate_season()`'s shared day-by-day nitrogen mechanism had a real bug.
  `biomass_before_mg_ha = biomass * 10` passed an already-10x-inflated value into
  `n_critical_pct()`/`n_marginal_demand_pct()` (both want plain Mg/ha, per their own
  docstrings), and `demand_today_kg_ha` separately applied the Mg-to-kg/percent conversion
  factor of 10 a *second* time. Together these inflated daily nitrogen demand roughly an order
  of magnitude. Caught by the standard sanity check every other nitrogen mechanism in this
  engine has been held to (a very-high nitrogen rate should converge to the exact no-tracking
  baseline) -- corn's optional path failed it outright: 150 kg N/ha and 2000 kg N/ha gave the
  identical, badly-undershooting yield, since demand so vastly outstripped any real supply that
  more fertilizer could never matter. Fixed to use `biomass` directly and apply the conversion
  factor once; verified N=150 through N=2000 now all correctly converge to the unconstrained
  baseline for a representative year, and that the standing tillage and manure-equivalence
  sanity checks both still pass at a genuinely (re-discovered) limiting rate.

  Corn's own validated 0.527 correlation is unaffected (its default validation never executes
  this code path). Wheat's default validation does wire nitrogen in, so fixing the bug moved
  its number again: real mean 4.33 (stale, under the old buggy math) -> uncalibrated 6.74 under
  the fixed math (wheat is genuinely less nitrogen-stressed than the bug made it look) ->
  recalibrated to the real 3.92 Mg/ha mean exactly -> correlation 0.285, worse than both the
  unreproducible 0.523 and the 0.411 the same crop dict gave under the old buggy math --
  confirming the demand-scaling bug was not itself the reason 0.523 couldn't be reproduced.
  Wheat's real accuracy remains open and was deliberately not chased further this session.

* **Corn's canopy-senescence shape, root-density timing, and root-density curvature (2026-09-30,
  continuing the "focus on corn" session).** Three checks against CropSyst's real public source/
  manual, following directly from the linear-taper root-density fix's own success earlier this
  session (see the water-stress-mechanism entry above): two real, sourced dead ends, and one
  real, shipped improvement.

  Dead end 1, root-density curvature: CropSyst's "Crop parameters: Root" manual page describes a
  real "curvature of root density distribution" parameter (0-30, 0=the linear taper already
  shipped, higher=more surface-concentrated). Confirmed directly via grep that Cycles' own real
  `GenericCrops.crop` has no such field for any of its 45 crop entries -- only
  `MAXIMUM_ROOTING_DEPTH`. A quick in-memory sensitivity test (never shipped) found a real
  tradeoff, not a free improvement: higher curvature helps Rock Springs but hurts Kansas. Not
  pursued further without a real sourced value.

  Dead end 2, root-depth growth timing: CropSyst's real "Simulation crop: Root growth" formula
  normalizes thermal-time progress from **emergence**, not planting, to a specific
  `max_root_depth_deg_day` threshold (not necessarily 50% of thermal time to maturity, which is
  what this engine assumes). Confirmed via grep that Cycles' own crop file has none of the three
  parameters this would need (`max_root_depth_deg_day`, `start_rooting_depth`,
  `length_at_emergence`) -- same gap as the curvature parameter. Tested the one real, sourced
  structural piece anyway (shifting the normalization's start point to the already-real
  `tt_emergence`, keeping the same 50%-of-maturity threshold): negligible effect at both
  benchmarks (Rock Springs corn correlation 0.4996->0.4990; Kansas 0.7424->0.7417, overshoot
  0.986->0.986 unchanged) -- not worth the added complexity for zero measurable benefit. Not
  shipped.

  Also checked CropSyst's canopy-interception mechanism (a real WebSearch turned up
  `fPARi = 1-exp(-k*LAI)`, Beer's Law, k=0.45) as a candidate replacement for this engine's
  direct thermal-time-based double-sigmoid -- same pattern again: LAI growth itself needs a
  specific-leaf-area parameter Cycles' crop file doesn't carry. This isn't just a fourth dead
  end, though -- it resolves a real question: it confirms Cycles deliberately abstracted LAI
  away and uses a direct curve instead, so this engine's existing double-sigmoid approach is the
  right level of abstraction, not a shortcut around a hidden more-accurate mechanism.

  The real, shipped fix: `CORN_CANOPY_SHAPE`'s decline-shape constants (c,d) were refit via
  actual least-squares against 2729 pooled (thermal-time-fraction, real FRAC INTERCEP) pairs from
  real Cycles' own `ContinuousCorn` daily output, restricted to stress-free days to isolate the
  pure canopy-shape signal. The prior refit (fit with less rigor, apparently) undershot real
  canopy cover during late senescence (ttf>0.85, the grain-fill window). New shape (6,-20,-5.35,
  4.10), cutting pooled SSE by ~62%. Also found and fixed a real, separate bug while testing this:
  `pattern_assertions.py`'s own `CORN` dict had never set `canopy_shape` at all (silently running
  every Kansas/multi-site check against the paper's unfit default shape, not the corn-specific
  refit `run_validation.py` actually validates against) and was carrying a stale
  `calibration_factor` from before this session's harvest-index fix -- both fixed together.
  Verified: Rock Springs corn correlation 0.500->0.505, Kansas correlation 0.762->0.776 (after
  the sync fix put Kansas on the real corn canopy shape for the first time), nothing regressing
  beyond noise. A real, orthogonal finding fell out of this: either corn-specific canopy refit
  (old or new) makes Kansas's absolute overshoot WORSE (~0.99x with the unfit default up to
  ~1.35x with either refit) even as correlation improves -- confirms the overshoot and the
  canopy-shape fit are two separate problems (the overshoot is the already-tracked real
  nitrogen-response muting, not a canopy-timing issue).

  One more real, not-yet-chased finding surfaced while fixing the sync bug: with `pattern_
  assertions.py`'s `CORN` dict finally correct, a previously-undetected `c_hybrid_crossover`
  failure appeared (confirmed via `git stash` to predate this session's canopy work, not caused
  by it) -- North Dakota's long-season hybrid now beats the short-season one, when the real
  climate-risk lesson (`agricultural/investigation.html` Tab 1, CLAUDE.md 2026-09-22) says the
  short-season hybrid should win or tie at a cold site. Same shape of problem as the already-
  documented vanished corn/soybean crossover: very likely a real consequence of how much the
  engine has changed since that panel's numbers were last checked (HI fix, root-density fix,
  water-stress mechanism, and now this canopy refit), not a new regression. Flagged, not chased
  -- Tab 1's own claim needs its own dedicated look before it's trusted again, same standing
  caveat already written for Tab 3's crossover.

* **Denitrification for corn's worst-overshoot years (2026-09-30, same session) -- a real,
  sourced formula found, but testing left it unshipped.** Corn's 5 worst Rock Springs overshoot
  years (1982, 1981, 1984, 1985, 1986, all model 10.8-11.8 vs real 7.1-9.6 Mg/ha) all show real
  Cycles `N STRESS` at 44-51% max, while the model's own default validation tracks no nitrogen
  at all -- a real, clean pattern (confirmed directly via `awk` against `CornRM.90.txt`) worth
  chasing, since it's the one lever this session hadn't yet tried for these specific years.

  Traced the real primary source properly rather than guessing: CropSyst's own 1994 paper
  (Stockle, Martin & Campbell, *Agricultural Systems* 46:335-359, already on disk as
  `cropsyst.pdf`) cites Stockle & Campbell (1989) for "net mineralization, nitrification and
  denitrification... simulated using first order kinetics." WebSearch of CropSyst's real
  "Simulation chemical: Nitrogen" manual page (`sites.bsyse.wsu.edu`, blocked for direct fetch,
  same as every other CropSyst manual page this session) surfaced the actual formula, reproduced
  identically across three independent search queries: `DEN = NO3*(1-exp(-DRATE*dt))`, with
  `DRATE = TF(Ts)*DRATE15*WCCF`, `DRATE15=0.005/day` (a real numeric anchor at 15C), and a
  piecewise temperature response (`0.67*exp(0.43*(Ts-10))` below 10C, `exp(0.08*(Ts-15))` above
  -- self-consistent, both give 0.67 at the Ts=10C breakpoint). `WCCF` (the moisture correction)
  came back with consistently garbled parenthesization across every query (`e^(0.304 + 2.94 *
  WCsat - WC) - 47 * (WCsat - WC))`) -- reconstructed as the one physically plausible reading,
  `exp(0.304 + 2.94*(WCsat-WC) - 47*(WCsat-WC)^2)` (a downward quadratic peaking just short of
  full saturation, matching real denitrification biology -- anaerobic microsites, not literal
  0% air-filled porosity), but this specific piece is a genuine reconstruction, not a clean
  quote, and should be treated as lower-confidence than this file's other sourced formulas.

  Built and tested against this engine's real 150 kg N/ha disclosed rate (`ContinuousCorn.
  operation`) plus the real minimal-disturbance planter tillage event, applied to the whole
  lumped mineral-N pool (a disclosed simplification -- this engine has no separate NH4/NO3
  pools to apply DEN to just the nitrate fraction, unlike real CropSyst). Real, non-trivial
  losses resulted (24-30 kg N/ha denitrified per season, roughly 16-20% of the applied rate) --
  but yield was completely unchanged in every tested year, including 1982, because 57-84 kg
  N/ha was STILL sitting unused in the pool at season end even after that loss. The demand
  side, not the loss side, is the actual bottleneck: this engine's critical-N-dilution demand
  formula only calls for ~85-100 kg N/ha total season uptake for an 11+ Mg/ha corn crop (~8.5 kg
  N/Mg grain), while real Cycles' own `TOTAL N` column shows 144.4 kg N/ha for the same 1982
  crop (~20.3 kg N/Mg grain) -- more than double.

  Chased two real, sourced candidate explanations for that demand gap, both testing WORSE, not
  better: (1) a genuine internal inconsistency was found where `n_critical_pct()`/`n_marginal_
  demand_pct()` are called with the raw internal `biomass` variable while their own docstrings
  and `NCRIT_FLOOR_MGHA` assume real Mg/ha (confirmed via direct instrumentation: `n_crit_pct`
  stays pinned at the undiluted 5.5% ceiling until real biomass exceeds ~10 Mg/ha, not the
  intended ~1 Mg/ha) -- correcting the scale (passing `biomass*10`) dropped total uptake to 39.9
  kg N/ha, further from real Cycles, not closer; (2) the standard agronomic convention (Justes/
  Lemaire %N-dilution curves are defined on SHOOT dry matter, not total biomass including
  roots -- confirmed via the real Lemaire et al. 2008 paper already on disk, whose own Fig. 1/2
  threshold is explicitly "1 t ha-1," matching this engine's `NCRIT_FLOOR_MGHA=1.0` and
  supporting the real-Mg/ha reading) gave 45.6 kg N/ha using `ag_biomass*10` -- still far
  short. Every corrected variant moved AWAY from real Cycles' 144.4, while the current,
  scale-inconsistent code (99.7 kg N/ha) is paradoxically the closest of the four. This suggests
  the gap isn't a simple units bug at all -- more likely real Cycles allows uptake beyond the
  critical-dilution curve's minimum-for-max-growth prediction (luxury consumption up to
  N_MAX_CONCENTRATION when supply is abundant, a real, common feature of N uptake models this
  engine's marginal-rate formula doesn't represent), which this session didn't have time to
  build and test.

  Given real N stress correlates only weakly with corn's own yield already (-0.21, vs. wheat's
  dominant -0.894, already documented above), and every tested angle here produced either no
  effect or moved the wrong direction, this was deliberately NOT pursued further or shipped --
  consistent with this session's own standing discipline against chasing a narrow, ambiguous
  thread past the point of clear returns. Nothing in `cycles_engine_validate.py` was changed by
  this investigation (confirmed via diff against a pre-investigation backup). Worth revisiting
  with a real luxury-consumption mechanism (crop takes up available N up to N_MAX_CONCENTRATION,
  not just the critical-dilution marginal rate, whenever supply allows) if this is picked up
  again -- that's the one candidate explanation not yet tried.

  A fourth angle was also tested against the muting problem specifically: real multi-year
  soil-state carryover (`initial_layers`, already a real engine feature, already documented as
  an "unambiguous win everywhere tested" for the Kansas yield-LEVEL overshoot -- see the
  2026-09-24 entries above) was chained 1988->target across 10 real Kansas years and compared
  against the fresh-start relative yield (N=0/N=150) at three target years. Result was small and
  mixed, not a fix: 1997 improved marginally (0.799->0.784, slightly more responsive), 1996 was
  essentially unchanged (0.802->0.811), and 1991 got measurably WORSE (0.749->0.898, notably
  LESS responsive to nitrogen with real carryover than without). Carryover fixes the absolute
  yield level (its own already-documented job) but doesn't reliably fix how FLAT the response to
  nitrogen rate is -- a separate axis of the same real problem. Four real, sourced angles tried
  on this specific muting problem this session (denitrification, the two demand-scale
  corrections, and now carryover); none closed it. The luxury-consumption idea remains the one
  real candidate not yet built and tested.

  One more, decisive check before closing this out: this same scale-correction was also tested
  directly against the already-documented Kansas nitrogen-response "muting" problem (CLAUDE.md
  2026-09-29: real Cycles' mean relative yield N=0/N=150 at Kansas is 0.779, varying 0.344-1.028
  by year; this engine's is a flatter 0.934) -- a different, sensitivity-shaped metric than the
  absolute-uptake-total comparison above, so worth checking separately rather than assuming the
  same verdict applies. Result was unambiguous and in the wrong direction: the "corrected"
  `ag_biomass*10` demand scale pushed Kansas's relative yield to 0.998-1.000 across three tested
  years (1997, 2012, 1988) -- essentially ZERO nitrogen response at all, since background
  mineralization alone now fully satisfies the (much lower) demand ceiling even at N=0. The
  current scale-inconsistent code's own relative yields at the same three years (0.799-0.906)
  are closer to real Cycles' sensitivity, if still too flat. This decisively confirms the floor-
  threshold/reference-biomass scaling should NOT be touched -- whatever its aesthetic
  inconsistency, it is accidentally more realistic than the "textbook-correct" version, which
  would make nitrogen matter even less than it already does. The muting problem itself remains
  real and unresolved; the luxury-consumption idea above is the most promising untried angle for
  it too, since raising the uptake ceiling (rather than changing which biomass/units it's keyed
  to) is the one lever not yet tested in either direction.

* **min(demand, potential_uptake), built and tested (2026-09-30, same session, per Matt's
  direct "Build the min(demand, potential_uptake) mechanism and test it") -- a fifth real angle
  on the muting problem, this one actually SHIPPED (opt-in, default off) despite a decisive
  null result, following this session's own standing precedent for real, correctly-verified,
  zero-effect-so-far mechanisms.** CropSyst's real Eq. 26 (Stockle, Martin & Campbell 1994,
  already on disk as `cropsyst.pdf`) computes potential uptake per soil layer from root length,
  soil-N availability, and soil water -- real numbers (Umax, root length density) this project
  doesn't have and Godwin & Jones (1991), the paper CropSyst itself cites for the exact
  functional forms, is a book chapter with no equations findable online. Rather than invent
  those numbers, built the real STRUCTURAL insight a fully traceable way instead: nitrogen is
  now tracked per soil layer (`n_pool_by_layer`, new, opt-in via `n_root_limited=True`) instead
  of one lumped pool, transported downward in lockstep with the SAME water fluxes
  `redistribute()` already computes (both the saturation-fill/cascade stage, using a well-
  mixed-reservoir assumption -- the same one this project's own original whole-profile leaching
  formula already relied on -- and the gravity-drainage stage), and a day's uptake is capped at
  however much of the pool sits within the crop's actual current root depth
  (`layer_depth_fraction_within()`, plain geometry, deliberately NOT reusing the water-uptake-
  specific `root_length_fraction_by_layer()`, which excludes the evaporative layer for a reason
  that doesn't apply to nitrogen). This is the "root discovery" concept already fixed for water
  earlier this session, applied to nitrogen for the first time.

  A real bug was found and fixed while building this, not just a design choice: the first
  version only moved N during the gravity-drainage stage, and real Rock Springs fertilizer
  (applied near-surface, a thin 0.05m layer) simply never left that top layer at all -- 0.0 kg/ha
  leached across every tested year, because a thin surface layer's water mostly moves via the
  saturation-fill/cascade stage on a real rain day, not the slower gravity-drainage stage. Fixed
  by extending the same well-mixed transport to that stage too; verified directly by
  instrumenting a real run day-by-day (1982) and confirming N now genuinely migrates layer to
  layer over the season, not frozen in the surface layer.

  Tested against both established benchmarks. Rock Springs' five worst real overshoot years
  (1982, 1981, 1984, 1985, 1986 -- all real-Cycles N STRESS 44-51%, see the denitrification
  entry above): grain yield is unchanged to two decimals in every one, confirming corn's real
  root growth (reaching 2.0m by roughly mid-season) outpaces how far this humid site's real
  drainage actually moves nitrogen through its shallow 1.4m profile -- access is never really
  the constraint here, consistent with several other real water-balance mechanisms this session
  found non-load-bearing at Rock Springs specifically (runoff, spin-up, the Ksat rate cap) for
  the same underlying reason (humid site, not where the mechanism binds). Kansas's own muting
  benchmark (relative yield N=0/N=150 at five real years) came back BYTE-IDENTICAL to the
  existing mechanism's own numbers (0.799, 0.906, 0.812, 0.749, 0.802) -- a different, opposite
  explanation for the same null result: Kansas is dry enough that real drainage barely moves
  water at all, so nitrogen applied near the surface never migrates far enough to become
  inaccessible either. Root access turns out not to be the bottleneck at either site, for
  opposite reasons -- a genuine, decisive finding, not an inconclusive one.

  Verified safe before shipping: the standing tillage sanity check (re-run at N=30, since post-
  session-fixes N=50 turns out to already be non-limiting even under the EXISTING mechanism --
  a stale assumption in this file's own earlier-documented check, not a regression from this
  change) shows the same real, positive tillage gain under both mechanisms (+0.60 Mg/ha old,
  +0.49 Mg/ha new, both ~0 at N=650); the manure/mineral 0.5-availability equivalence still
  matches to six decimal places; the nitrogen mass-balance identity (uptake+leached+remaining =
  supply) still closes exactly. `n_root_limited=False` (the default) reproduces every existing
  validated number byte-for-byte -- confirmed via the full Rock Springs 4-crop suite,
  `pattern_assertions.py` (still 14/16), and both embedded `ENGINE_SOURCE` copies, extracted
  verbatim and executed directly. Ported into both `engine-demo.html` and
  `model-validation.html`, confirmed to compile and produce consistent numbers against real
  weather/soil data; no UI wiring anywhere (engine-only, per this project's established
  "build the mechanism, verify it, wire up a control only once it's proven to matter" pattern).

  This closes out five real, sourced, decisively-tested angles on the Kansas nitrogen-muting
  problem across this session (denitrification, two demand-scale corrections, multi-year
  carryover, and now root-access limiting) without a fix. The luxury-consumption idea (uptake
  allowed above the critical-dilution ceiling when supply is abundant) remains the one real,
  sourced candidate not yet built.

---

**2026-10-01 — Resolved without asking: a real cold-kill mechanism, the single largest
correlation jump this project has shipped for corn and soybean.** After the root-access/
nitrogen-muting investigation above closed out without a fix, redirected (per direct
instruction: "Onward toward high leverage things to improve the model. No educational modules
until we fix this") to hunting systematically for whatever actually explains corn's real
year-to-year yield variance at Rock Springs, since a sensitivity sweep had already shown
neither nitrogen stress (-0.21 correlation with real yield) nor water stress (-0.22) are strong
real drivers there. A multi-variable correlation hunt across every real daily/annual Cycles
output column found `total_actual_tr` (cumulative actual transpiration) as the dominant real
predictor (+0.824) -- stronger than any stress metric -- which pointed at season LENGTH as the
real lever: a season cut short transpires less, full stop, regardless of why it was cut short.

Checked real Cycles' own `STAGE` column directly for every one of the 37 validated years and
found `STAGE=KILLED` in all 37 -- always right around 1818-1833 GDD (essentially
`tt_maturity=1800`, ordinary maturity) EXCEPT two years: 1982 (killed at 1485.6 GDD, 82.5% of
normal -- this project's own single worst corn overshoot year, model 11.71 vs real 7.13 Mg/ha)
and 1997 (1752.7 GDD, 97.3% of normal). Checked the real weather on the exact kill day in both
years and found a real, disclosed, exact match: corn's own `GenericCrops.crop`
`THRESHOLD_TEMPERATURE_FOR_COLD_DAMAGE=3C` was crossed by that night's real low temperature in
BOTH years (1982: 2.91C; 1997: 1.19C) during reproductive growth -- a real, causal, matching
mechanism, not a correlation found by searching. This engine had no kill mechanism of any kind
before this fix; it always ran every season to full thermal-time maturity regardless of
weather.

A naive, ungated implementation (kill the season outright the instant any night drops below
the threshold, checked from day one) catastrophically failed: collapsed mean grain from 10.56
to 1.90 Mg/ha and made correlation go NEGATIVE, because ordinary early-season cold nights
(right after planting, well before flowering) are completely normal and non-lethal in real
Cycles -- confirmed directly against real weather for non-killed years (1980 hits 1.24C, 1985
hits 0.90C, within 60 days of planting, neither year killed in reality). Fixed by gating the
check on `tt_cum >= crop["flowering_tt"]` -- cold-kill only applies during/after reproductive
growth, matching the real, physically sensible story (a hard freeze during grain fill ends the
season; one in early vegetative growth does not, in this model's own real behavior).

Implemented in `simulate_season()`'s main day loop as a single `break` triggered by
`tt_cum >= crop.get("flowering_tt", math.inf) and w["tn"] < crop.get("threshold_temp_cold_damage", -math.inf)`
(both fields absent by default, so any crop without them is completely unaffected). Real,
disclosed per-crop `THRESHOLD_TEMPERATURE_FOR_COLD_DAMAGE` values from `GenericCrops.crop`:
corn (all RM variants) = 3C, soybean (all MG variants) = 2C, winter wheat = -10C, silage corn =
3C. Wired in for all four validated crops plus `CORN_LONG_SEASON`. Verified the mechanism's
real, physically-motivated scope rather than treating it as a universal fix: real, substantial
wins for corn (Rock Springs correlation 0.527 -> 0.691, recalibrated) and soybean (0.871 ->
0.954, recalibrated) -- the largest single-mechanism correlation jump either crop has gotten
this session -- and confirmed NULL (genuinely inert, not just untested) for winter wheat
(threshold -10C essentially never reached that late in a spring-flowering wheat's own season)
and silage corn (harvested at 85% of thermal-time maturity, well before the late-season
cold-kill window could ever matter).

A real, unforced side effect: `pattern_assertions.py`'s previously-failing "Hybrid choice"
check (long-season hybrid should win at a warm site, short-season should win or tie at a cold
one) flipped to passing from this fix alone, with no retuning aimed at it -- genuine real
agronomic logic, since a cold-kill mechanism specifically penalizes a longer-season hybrid at
a cold site (more growing days needed, more exposure to an early-season-ending freeze), exactly
the real reason farmers in cold climates plant shorter relative-maturity hybrids. Full suite
now 15/16 passing (only remaining failure: the already-separately-documented, confirmed-
nonexistent corn/soybean nitrogen crossover that `agricultural/investigation.html` Tab 3 still
teaches -- a real, known, not-yet-fixed staleness in that tab's own copy, left untouched per the
standing "no educational modules" instruction).

Re-derived `calibration_factor` for both crops to keep the mean matching real output exactly,
same discipline as every prior mechanism: corn 1.0977 -> 1.1076, soybean 1.4297 -> 1.4678.
Ported into both embedded `ENGINE_SOURCE` copies (`engine-demo.html`, `model-validation.html`)
-- the day-loop check, the two crops' `threshold_temp_cold_damage` fields, and both new
calibration factors -- confirmed both files compile cleanly, execute correctly against real
Rock Springs weather (1982 grain dropped from the pre-fix 11.71 to a real, verified 8.64 Mg/ha
through the actual embedded engine, not just the canonical script), and preserve correct
`<div>`/`<script>`/`<style>` tag balance. `CORN_LONG_SEASON = dict(CORN)` automatically
inherits the new threshold field with no separate edit needed.

The combined luxury-N-consumption + real-denitrification mechanism tested just before this
(explicit instruction: "go build and test it") failed decisively and was NOT kept: despite the
fertilizer pool genuinely draining under both mechanisms together, yield stayed unchanged to
three decimals in every tested year, because `BACKGROUND_N_KG_HA_DAY` is a flat, continuous
daily credit that refills the pool every growing day regardless of applied rate -- an
inexhaustible backstop no demand- or loss-side nitrogen mechanism can overcome on its own.
Checked the bundled `.soil`/`.ctrl` files (`GenericHagerstown.soil`, `Kansas.soil`,
`ContinuousCorn.ctrl`) directly for the six-pool system's undisclosed rate constants per the
explicit "look elsewhere for those constants" request -- confirmed cleanly that these files
only ever carry initial conditions (CLAY/SAND/SOC/NO3/NH4/curve number), never kinetic rate
constants; a fast, clean negative result, not a wasted effort, and part of why the "go hunting"
redirect toward season-length/cold-kill (rather than more nitrogen-mechanism tuning) proved to
be the right call.

---

**2026-10-01 — Resolved without asking, the second major correlation lever this day: real
CO2-driven water-use-efficiency scaling (wue_co2_scale).** After shipping the cold-kill
mechanism above, went looking for why corn's remaining real-minus-model residual still
correlated 0.73 with calendar year -- a secular bias, not noise. Checked the hypothesis
directly against the wrong candidate first, per instruction ("keep looking back at the main
equations for other fixable levers"): rising atmospheric CO2 is a real Cycles input
(`CO2_LEVEL -999` in `.ctrl` files reads real year-by-year CO2 from `input/co2.txt`, real
NOAA Mauna Loa data, 338.76 ppm in 1980 to 404.41 ppm in 2016). Tested directly with the real
Cycles binary: reran `ContinuousCorn` with a flat, 1980-level CO2 input substituted for the
real rising series. The real yield trend barely moved (0.0614 -> 0.0554 Mg/ha/yr) --
decisively ruling out CO2 itself as more than ~10% of the trend, before guessing at any
scaling mechanism.

Traced the actual cause by instrumenting this engine's own GR/GT (radiation-limited/
water-limited growth) day by day: real Rock Springs weather genuinely warmed, got sunnier,
AND got drier (relative humidity falling, so vapor-pressure deficit rising) over 1980-2016 --
confirmed in the real weather file, not an artifact. GR (= eps_R * eie * solar) correctly
rises with solar. GT (= eps_W/sqrt(Da) * TR_actual, Eq. 5) falls as VPD (Da) rises, since
TR_actual only rises modestly while sqrt(Da) rises faster -- and `min(GR,GT)` increasingly
lets GT cap growth as the decades pass, canceling GR's rise almost entirely in this engine.
Confirmed real Cycles' own water stress at this site is negligible (1.64% average, barely
trending) -- its growth is almost always purely radiation-limited there, so this ceiling
essentially never binds for it. Checked and ruled out two candidate explanations before
looking at the paper itself: using Tmax instead of Tmean for VPD (days warm faster than
nights here, makes it worse, not better); multi-year soil-state carryover (already tested
earlier this session at Rock Springs specifically, no effect there).

Went back to Kemanian et al. 2024 Sec. 2.5 directly (re-extracted via pdfminer, pdftotext not
available in this container) and found the real, disclosed answer sitting in plain text,
previously missed: "Both eps_R and eps_W should be given for a reference atmospheric CO2
concentration and scaled accordingly as CO2 changes. For a discussion on the implications of
optimization theory under changing CO2 see Bassiouni and Vico (2021)." This directly
contradicts this file's own earlier assumption ("CO2 scaling of radiation-use-efficiency is
undisclosed in both sources and implausible to be large for a C4 crop like corn") -- the
paper explicitly names BOTH efficiencies as CO2-scaled, it was just never read carefully
enough in this specific section before. WebSearch (WebFetch is blocked for every domain tried
this session, same standing limitation) surfaced the real Bassiouni & Vico (2021, New
Phytologist) result: "instantaneous transpiration efficiency should be proportional to
atmospheric CO2 concentration (Ca)... approximately inversely proportional to the square root
of leaf-to-air vapor pressure deficit" -- a real, citable, linear-in-CO2 scaling law for
exactly eps_W, from stomatal optimization theory, general to C3 and C4 plants alike (the
theory is about stomatal regulation, not photosynthetic pathway).

Implemented ONLY the eps_W (WUE) side of this, not eps_R -- the well-established C4 literature
(e.g. Leakey 2009, "Photosynthesis, Productivity, and Yield of Maize Are Not Affected by
Open-Air Elevation of CO2...") shows negligible photosynthetic/RUE response to CO2 for C4
crops like corn under non-drought conditions, since C4 photosynthesis is already
CO2-saturated -- scaling eps_R too would have no sourced justification for corn specifically
and risked an unearned win. `wue_co2_scale` (default 1.0, fully backward compatible) multiplies
`crop["wue"]` in the GT formula. `CO2_PPM_BY_YEAR` (real NOAA Mauna Loa annual means,
1980-2016) and `CO2_REF_PPM` (368.299, this engine's own 1980-2016 Rock Springs calibration-
period mean -- a disclosed modeling choice, not a value either source specifies, chosen so
the scaling nets to ~1.0 averaged over the validation record) were added to
`cycles_engine_validate.py`.

Tested against all four validated crops plus the Kansas benchmark before shipping, applied
UNIFORMLY (not selectively kept only where it helps, since the mechanism is physically
general): corn 0.691->0.777 (real win, on top of the same day's cold-kill fix); winter wheat
0.337->0.444 (real win, its own second-largest single-mechanism gain this project, after the
day-by-day nitrogen rebuild); soybean 0.954->0.947 (negligible, within noise); silage corn
0.203->0.117 (a real cost, but already far below the classroom-workable bar either way, on an
already-small 13-point sample). Kansas 37-year corn benchmark (real Cycles output,
`/tmp/cycles-run/output/KansasN150`): 0.776->0.758, a small cost, consistent with Kansas's own
accuracy gap being dominated by a different, already-diagnosed problem (root-zone water
access via `campbell_water_uptake()`'s layer-discovery behavior), not this secular-trend issue.
`wue_co2_scale=1.0` reproduces every existing validated number byte-for-byte, confirmed
directly before any harness was changed to pass a real value.

Real documentation drift caught and fixed while updating these numbers, worth flagging for
its own sake: `model-validation.html`'s and `engine-demo.html`'s own SPECIES_REGISTRY notes
for winter wheat and silage corn had BOTH drifted stale at some earlier point, independently
of today's work -- engine-demo.html still claimed wheat's long-debunked 0.523 figure
(model-validation.html itself had already corrected this to 0.285 via a real git-bisect on
2026-09-28, but engine-demo.html's own copy was never updated to match), and both files
claimed silage corn at 0.516 when the actual current baseline going into today's work was
0.203. Neither drift was caused by today's fixes -- both predate this session's start and were
only caught because today's work required re-measuring every crop's baseline precisely before
computing a new calibration factor. Corrected in both files with the real numbers and an
honest account of the drift itself, rather than silently overwritten.

Not yet done: `eps_R`'s own CO2 scaling for soybean (C3) specifically -- Bassiouni & Vico's
theory doesn't rule it out the way it does for C4 corn, and soybean's own photosynthesis could
plausibly show a small positive CO2-RUE response unlike corn's, but this wasn't tested or
built, since the WUE-only mechanism already covers what the immediate correlation problem
needed and inventing a second, untested scaling path wasn't asked for. The Bassiouni & Vico
(2021) formula itself was sourced from a WebSearch result summary, not a direct primary-source
read (WebFetch blocked for every domain tried) -- flagged the same way every other
search-summary-sourced fact in this file is flagged.

---

**2026-10-01 — Resolved without asking: real per-manure-species N availability, replacing the
flat manure_availability=0.5 guess with Cycles' own disclosed composition data.** Continuing
"keep looking back at the main equations for other fixable levers," re-read the main paper's
Table 1 closely and found it lists real parameter symbols for nitrification/denitrification
(`knd`, `kan`) with units -- confirming those processes are structurally disclosed, just not
with numeric rate constants anywhere (paper, SI text already grepped for "volatiliz" with
zero hits, and `.soil`/`.ctrl` files already checked and confirmed to carry only initial
conditions) -- so that avenue stays correctly closed, nothing new there.

What *was* new: `/tmp/cycles-run/input/fert.txt`, a real Cycles v1.4.4 FIXED_FERTILIZATION
template catalog bundled with the binary, sitting unexamined this whole project despite its
sibling `till.txt` being mined extensively for the tillage/volatilization work. It has 9 real
named manure SOURCE entries (Dairy/Beef/Veal/Swine/Sheep/Goat/Horse/Chicken/Turkey), each with
real `N_Organic`/`N_NH4`/`N_NO3` fractions of total N -- i.e. real, per-species data for
exactly the question `manure_availability=0.5` has been guessing at with one flat number
since the manure mechanism was first built (SI Sec. IX's own disclosed "0.5 the availability
of mineral N" is for one specific real Iowa case, not a general constant). Computed each
species' immediate (N_NH4-fraction) availability directly: Turkey 0.135, Dairy 0.184,
Chicken 0.200, Beef 0.250, Horse 0.300, Sheep 0.368, Goat 0.371, Veal 0.442, Swine 0.553 --
spanning both sides of the flat 0.5 default by a wide margin. A real, corroborating cross-
check rather than a coincidence: Swine's own 0.553 sits strikingly close to the disclosed 0.5
Iowa figure, and Iowa is real hog country -- consistent with that disclosed number having
come from swine manure specifically, not an arbitrary round constant.

Implemented as `MANURE_SOURCES` (9 entries) plus a new `manure_source=None` parameter on
`simulate_season()` that, when given a real species key, overrides `manure_availability`
with that species' real immediate fraction -- `None` (default) leaves existing behavior
byte-identical, verified directly (the full `run_validation.py`/`run_validation_rotation2.py`/
`pattern_assertions.py` suite reproduces every number unchanged, since no default validation
path passes `manure_n_kg_ha` at all). Verified the mechanism does something real and in the
right direction: at a genuinely limiting rate (20 kg N/ha manure, Rock Springs 2012 corn),
Dairy manure (0.184) measurably outyields Turkey manure (0.135) at the same applied rate
(6.3487 vs. 6.2983 Mg/ha); an unrecognized species name raises `ValueError`, matching the
existing `tillage_implement`/`fert_placement_implement` pattern. Ported into both embedded
`ENGINE_SOURCE` copies identically, confirmed via extraction that the new dict, parameter,
and override logic are byte-identical in both files (the only diff remaining between them is
the pre-existing, already-documented WHEAT calibration-factor divergence, untouched by this
change) and that both execute the same dairy-vs-turkey directional check correctly.

Real, disclosed limitation kept honest rather than silently extended past what's built: each
species' remaining organic-N fraction (`norg_frac`, 45-87% of total N depending on species)
is still simply unavailable for the season -- not fed into the existing RothC-scaled
background-mineralization pathway or any other slow-release mechanism. A real eventual
mineralization of that fraction is a plausible, well-motivated next build (the data to drive
it, `norg_frac`, already exists in `MANURE_SOURCES`), but wasn't attempted here -- scoped
deliberately to "use the real immediate-availability number instead of guessing at it," not
"build a new multi-week organic-N release mechanism," which would need its own separate
verification pass. No UI wiring anywhere (engine-only, matching the "engine first, UI later"
pattern used throughout this project for anything not yet asked for by name) -- the natural
place for it, if picked up, is `model-validation.html`'s own "Full simulation controls" form
and the manure fields already live in both `engine-demo.html`'s field-comparison/nitrogen-
sweep panels, the same curated-dropdown pattern already used there for tillage implements and
soil pH.

**2026-10-01 — Tested and rejected, same day, same "keep looking back" sweep: real initial soil
mineral N (NO3/NH4), already sitting disclosed in the exact bundled `GenericHagerstown.soil`
file `SOIL_LAYERS_RAW` was transcribed from, but never carried over.** That file's real
per-layer NO3 (10/10/7/4/2/1/1/1/1 kg/ha) and NH4 (1 kg/ha each of 9 layers) columns sum to a
real 46 kg N/ha already present in the soil at day 0, for the exact Rock Springs scenario this
engine validates against -- a different, additive input from both `n_credit_kg_ha` (a prior-
crop residual, caller-supplied) and `BACKGROUND_N_KG_HA_DAY` (ongoing organic-matter
mineralization): this is already-mineralized N sitting in solution from the start, not
something that accrues over the season. Confirmed `CURVE_NUMBER 75` in the same file already
exactly matches this engine's own flat `curve_number=75.0` default -- a good independent
cross-check that `SOIL_LAYERS_RAW` really is a direct transcription of this exact file, just
missing its NO3/NH4/CURVE_NUMBER/SLOPE columns.

Tested by adding the real 46 kg N/ha total via the already-existing, generic `n_credit_kg_ha`
parameter (no new mechanism needed) to winter wheat's own validated nitrogen-tracking path --
the one default-validated crop where this would actually matter, since corn/soybean/silage
corn don't track nitrogen by default. Result: correlation moved 0.444 -> 0.393, a real
regression, not an improvement, and not a calibration artifact (correlation is scale-invariant
to `calibration_factor`, so this is the genuine effect of the extra nitrogen on the season's
water/N-stress trajectory, not something a mean-matching recalibration could undo). **Not
shipped** -- `run_validation_rotation2.py`'s own Winter Wheat call site already defaults
`n_credit_kg_ha=0.0` and was left untouched. Same standing discipline as every other tested-
and-rejected lever in this file: a real, disclosed, well-sourced number that happens to make
this specific crop's correlation worse, documented so it isn't re-tried blind. Not tested at
Kansas, since the Kansas.soil file's own NO3/NH4 columns are already a disclosed placeholder
(tapered from Rock Springs' real values, per `build_kansas.py`'s own comment), not newly real
data the way Rock Springs' own figure is -- testing a placeholder against a placeholder result
wouldn't add evidence either way.

**2026-10-01 -- Full SI PDF re-read, now durably available (`agricultural/SI.pdf` on `main`,
not this feature branch -- access via `git show origin/main:agricultural/SI.pdf`, the same
read-without-merging pattern already used for every other reference PDF Matt has uploaded to
`main`'s root this project). Matt re-supplied it after the original docx (and this session's
own custom OMML-to-text transcription of it) was lost to a mid-session container reprovision.
Result: no new fixable lever found -- this PDF's content is the exact same 14 equations and
descriptive sections this project already extracted once and already built into the engine.**
Read all 24 pages in full (via `pypdf` text extraction, which rendered the italic-unicode math
cleanly enough to check against, no OCR risk the way a scanned image would carry) and checked
every equation and numeric table against what's currently implemented:

- Eq. SI.1 (TRp), SI.2-SI.7 (runoff/curve-number, including the SAME two sign-typo'd
  denominators -- SI.2's `Win-0.8S` and SI.6's `0.4-0.006*CNb` -- already found and corrected
  in this engine), SI.8 (shoot partitioning), SI.9 (harvest index), and Table SI.2 (RUE/WUE by
  species, including the already-used C3-grass/C3-legume cover-crop rows and the already-
  flagged, already-untouched "~20% RUE bonus under diffuse light, no input data to drive it"
  note) all match this engine's own implementation exactly, equation for equation, number for
  number. No discrepancy found anywhere.
- SI Section IX (the real Iowa statewide run) independently re-confirms, word for word, the
  exact two numbers this engine's manure/previous-crop mechanisms were already built from --
  `n_credit_kg_ha=60` for maize following soy, and manure N's real 0.5-availability-vs-mineral
  multiplier -- nothing to change.
- The six-pool soil carbon/nitrogen system (SI Eq. SI.10-SI.14) is given in full structural
  form again (the Cm/Cs differential equations, the fH/fD saturation factors with their exact
  exponents -- fH uses a power of 6, fD uses 4.5 and a power of 3 -- and the CNmbi microbial-
  biomass C:N formula), plus one number not previously nailed down this precisely: base
  microbial C-use efficiency (εc) ranges 0.33-0.44 kg/kg depending on the saturation ratio.
  **Still genuinely missing, confirmed by a direct grep of the full extracted text, not just
  memory**: numeric values for the turnover-rate constants (k_ra, k_rt, k_rz, k_rm, k_m, k_s)
  and the saturation capacity Csx -- the system's structure is disclosed, the numbers that run
  it are not, in this document any more than in the main paper or any input file checked
  earlier this project. This confirms, rather than changes, the standing decision to keep the
  full six-pool system out of v1 scope.
- Grepped the full extracted text for "ammonia," "volatil," "nitrific," "denit," "cold,"
  "frost," "cutting," "clip," "pasture," "forage," "graz" -- the only hits are incidental
  (Table SI.2's "crops and forages" header, a passing mention of cold-soil decomposition rates
  in the Cs/Cm discussion, "crop-pasture rotations" in a reference citation). **Nothing new on
  cold damage, ammonia volatilization, nitrification/denitrification, or the pasture cutting
  trigger** -- all four remain exactly as undisclosed as every prior check this session found
  them.
- Sections VI-VIII and X (eddy-covariance maize/willow ET, the WA wheat/barley field trial, the
  soybean Diviner soil-moisture calibration, and the Iowa/Cycles-A crop-sequence outputs) are
  real validation case studies and figures, not model equations -- Eq. SI.15 in particular is a
  sensor-calibration formula for interpreting Diviner-probe readings in that one field
  experiment, not a Cycles model equation, so it's not applicable to this engine regardless.

No code changed as a result of this read. The practical value is narrower but real: the SI is
now durably re-available on `main` (surviving any future container reprovision the way the
docx never could), and this pass confirms -- independently, by reading the primary source
again rather than trusting memory of an earlier, now-gone extraction -- that every equation
this engine currently implements from the SI is implemented correctly, and that the genuinely
open gaps (the six-pool rate constants; cold damage; ammonia/nitrification/denitrification; the
pasture cutting trigger) are correctly still open, not something this read missed.

**2026-10-01 -- two more candidate leads for the six-pool rate constants checked directly
(prompted by a second AI's suggestions, both tested rather than taken on faith), neither
yields a usable fix.** (1) "Check the bundled `.soil`/`.ctrl` files for exposed default rate
constants" -- already done, see the 2026-09-29 entry two above: confirmed cleanly those files
only carry initial conditions, never kinetic rate constants. Not re-tested, since nothing new
was proposed that would change that finding. (2) "Back-calculate via CropSyst's own legacy
source, since Cycles shares its lineage" -- a real, legitimate instance of the same technique
that already resolved the RUE/water-stress/bare-soil-evaporation gaps this session, so worth
checking properly rather than dismissing on the "shares lineage" framing alone (that framing's
own claim that Cycles' code was "obfuscated or re-branded" is unevidenced editorializing, not
something this project has any basis to assert -- Cycles' own README states plainly it ships
only compiled binaries, which is a licensing/distribution choice, not obfuscation).

Found and read CropSyst's own public source for this directly:
`CropSyst/source/organic_matter/multiple_pool/` (`OM_pools_multiple.cpp`, `OM_params.cpp`,
`OM_const.h` -- a directory this project's prior CropSyst dives never opened, since earlier
sessions went straight for transpiration/crop/soil files, not the organic-matter one). It
really does carry real, numeric default decomposition rate constants (1/day):
`default_microbial_decomposition_const=0.005`, `default_labile_active_SOM_decomposition_const
=0.02`, `default_metastable_active_SOM_decomposition_const=0.0005`,
`default_passive_SOM_decomposition_const=0.0000185`, plus real default C:N ratios per pool
(microbial 8.0, labile 25.0, metastable 15.0, passive 11.0) and carbon-fraction constants.

But CropSyst's own multi-pool model here is a different, Century/DSSAT-style THREE-SOM-pool
structure (labile/metastable/passive, each with its own independent first-order decay rate),
not Cycles' own TWO-pool (Cm microbial / Cs non-living SOM) saturation-theory structure
(SI Eq. SI.10-14) -- which modulates decomposition through the fH/fD saturation-ratio factors
specific to Kemanian & Stöckle (2010)'s own C-Farm lineage, a mechanism CropSyst's multi-pool
code has no equivalent of at all (confirmed directly: no `fH`/saturation-ratio term anywhere
in `OM_pools_multiple.cpp`). This is the same category of mismatch already found and rejected
once this session for CropSyst's canopy-shape and CO2-response files ("a different functional
form than Cycles' own equation, needs calibration parameters this project doesn't have") --
not a case where "CropSyst's number" and "Cycles' number" are the same quantity measured twice,
the way the transpiration/evaporation borrows turned out to be. Plugging CropSyst's three-pool
rate constants directly into Cycles' own fH/fD-modulated two-pool equations would be inventing
a numeric correspondence between two structurally different models with no derivation behind
it -- exactly the unsourced-guess pattern this project's whole discipline exists to avoid.

Not pursued further: building the real six-pool Cm/Cs subsystem to even test whether these
borrowed numbers behave sensibly inside it would be a genuine new-subsystem undertaking (as
already stated repeatedly in this file and `CLAUDE.md`), not a quick parameter substitution --
disproportionate effort to spend testing numbers from the wrong model, especially given Matt's
own standing decision to keep the full six-pool system out of v1 scope regardless, with the
RothC-based background-N mineralization proxy already serving its practical role. Logged here
so this specific lead isn't re-chased blind next time it's suggested.

**2026-10-01, same day -- the user asked directly: (1) Google/web-search the actual rate
constants, (2) back-calculate them from real Cycles output. Did both. (2) succeeded
substantially -- the single biggest step this project has made on the six-pool gap since it was
first flagged.**

**Csx (the saturation capacity) is now FULLY RESOLVED, not approximated.** Real Cycles output
(`/tmp/cycles-run/output/ContinuousCorn/annualSOM.txt`) reports, per layer per year, BOTH the
real soil C% AND the real "C SAT. RATIO" (Cs/Cx) directly -- so Csx = (reported %) / (reported
ratio) can be read straight off two numbers Cycles itself already computes and writes, no
inference needed. Done for Rock Springs' real 9-layer profile: Csx = 2.8975% (layers 1-3),
3.4975% (layers 4-5), 4.1725% (layers 6-9) -- confirmed stable to 5+ significant figures across
every one of the 37 simulated years (a real soil-intrinsic constant, not simulation drift).
Cross-checked against the (1) suggestion's own spirit -- went back to Kemanian & Stöckle
(2010)'s own C-Farm paper (`KemanianStockle2010.pdf`, already on `main`, re-read specifically
for this) -- and found its Eq. 3, citing Hassink & Whitmore (1997): `Cx = 21.1 + 37.5*fclay`,
stated as "mg C kg-1 soil." Read literally that's absurd for real topsoil (21-59 ppm), so tested
the obvious correction -- the same OCR/typesetting-unit-slip category already documented
repeatedly in this project for Kemanian-lineage sources -- reading it as g C/kg (equivalently
%*10): `Csx(%) = 2.11 + 3.75*fclay`. Plugged in Rock Springs' own real, already-committed clay
fractions (`SOIL_LAYERS_RAW` in `run_validation.py`: 21%/21%/21%/37%/37%/55%/55%/55%/55%) and
got 2.8975%/2.8975%/2.8975%/3.4975%/3.4975%/4.1725%×4 -- an EXACT match (4-5 significant
figures) to the independently back-calculated values above, at all three distinct clay
fractions, not a loose ballpark. Two fully independent methods (reading real simulator output,
and a corrected published formula) converge on the identical number. **This closes Csx as an
open unknown.** Not yet wired into the engine (the six-pool system itself remains correctly out
of v1 scope, so there's nowhere to use it), but if that system is ever built, this is the real
formula and it needs no further verification.

**ks (the Cs/non-living-SOM decomposition rate constant, Eq. SI.11) is now back-calculated with
real, moderate confidence, not guessed.** `soilC.txt`'s daily `SOM RESPIRED C` column turns out
to be exactly the loss term `fE*fT*fD*ks*Cs` (confirmed structurally, not assumed, by the mass-
balance identity d(SOIL_ORG_C)/dt ~ HUMIFIED_C - SOM_RESPIRED_C holding to within ~0.002 Mg/ha
on most days, with the small systematic residual itself traced to a real, expected missing term
-- see below). `SOIL ORG C` in `soilC.txt` turned out to be Cm+Cs combined (confirmed exactly:
diffed against the independently-summed per-layer MIC C + SOIL ORG C columns in
`soilLayersCN.txt`, matches to 4 decimals on every date checked), not Cs alone -- a real finding
in its own right, since the two profile-level columns in that file are easy to misread as pure
Cs. `soilLayersCN.txt`'s own "FACTOR COMP." column (per layer, daily, dimensionless, 0 in frozen
winter soil rising to ~0.5-0.7 in summer) is almost certainly fE itself (0<=fE<=1, the real
environmental-modulation factor the SI names but never gives a formula for) -- not derived here,
just directly read off real Cycles output, which is arguably better than deriving it.

Used `fE` (FACTOR COMP.), `fD = 1-1/(1+(4.5*Cs/Csx)^3)` (computed from the now-resolved Csx
above), and daily per-layer Cs to build a predictor (`sum over 9 layers of fE*fD*Cs`), then
regressed real `SOM RESPIRED C` against it (least-squares through the origin) across the full
37-year `ContinuousCorn` record, restricted to a mid-season window (DOY 150-250, to stay clear
of spring planting-tillage's own fT!=1 effect, since fT isn't in this predictor). Result:
ks ~ 0.0003-0.0004/day, and -- confirming the tillage-contamination diagnosis rather than just
asserting it -- narrowing toward ~0.00032/day and the fit residual shrinking (24%->17.5% mean
relative error) as the window is tightened further from spring tillage (DOY 210-240). Cross-
checked against C-Farm's own real, published, citable value: `kx = 5.5% yr-1` (Kemanian &
Stöckle 2010, Sec. 2, "the maximum turnover rate for an undisturbed soil... at or near field
capacity and at 35C") = 0.00015/day -- same order of magnitude as the back-calculated value,
roughly 2-2.5x lower, a real but not exact match. The gap is explainable, not just hand-waved:
C-Farm's own saturation exponent on this term is m=0.5 (`kx*(Cs/Cx)^0.5`), while Cycles' own SI
Eq. SI.13 uses a structurally different fD (threshold-shaped, effectively exponent-3 inside a
reciprocal, not a plain square root) -- the two aren't numerically equivalent corrections to the
same physical rate even if the underlying process is the same lineage, so a 2-2.5x gap between
the two models' own "reference maximum rate" constants is a real, expected consequence of that
structural difference, not evidence either number is wrong.

**eps_c*k_m (the combined Cm-turnover-to-Cs-humification rate, Eq. SI.11's gain term) is
back-calculated more loosely:** `HUMIFIED C` (daily, `soilC.txt`) regressed the same way against
`sum(fE*fH*Cm)` (fH from the same resolved Csx) gives eps_c*k_m ~ 0.013-0.02/day. Looser than ks
for a real, identified reason: `fA` (the microbial-size saturation stimulant, "increases once Cm
exceeds 3% of Cs") was assumed =1, but the real Cm/Cs ratio at Rock Springs sits persistently at
2.8-3.4% across the entire 37-year record -- right AT the stated 3% threshold, never cleanly
below it the way the assumption needs. This is itself a useful, concrete new constraint (fA is
essentially always mildly active here, never resting at exactly 1), but it means the eps_c*k_m
estimate carries an unknown fA multiplier baked in. Taking eps_c at its own stated 0.33-0.44
range (SI Sec. V) gives k_m ~ 0.03-0.06/day -- a real bound, not a point estimate.

**k_ra (aboveground residue) and a combined k_rt+k_rz (root + rhizodeposit) are now ALSO
back-calculated with real, good confidence -- the concrete next step flagged above was pursued
the same session, not left sitting.** The key was figuring out `soilLayersCN.txt`'s own column
structure precisely, by testing rather than assuming: "STAND RESID C" + "FLAT RESID C" +
"MANURE RESID C" (single values, not per-layer) turned out to be a genuinely DIFFERENT,
2-4x-larger pool than the separate, per-layer "RESIDUE C" columns (confirmed directly: on
1981-05-01, STAND+FLAT+MANURE=4.1162 Mg/ha vs. summed per-layer RESIDUE C=1.4788 Mg/ha) --
the first is the real aboveground residue pool (surface, not distributed with depth; this
`ContinuousCorn` scenario has no manure, so it's STAND+FLAT only here), the second, distributed
across all 9 layers matching the paper's own "generalized function of root distribution with
depth," is almost certainly the root(+exudate) pool. `annualSoilProfileC.txt` independently
confirms its own "INIT C MASS"/"FINAL C" columns are literally the Cs pool's own year-start/
year-end value (verified exactly against the daily `soilLayersCN.txt` SOIL ORG C column, e.g.
1980's FINAL C = 11.3250 matches 1980-12-31's daily value to 4 decimals) -- giving real
confidence the adjacent "RES C DECOMP"/"ROOT C DECOMP" columns in the same file are what their
names say: the real annual total carbon that left the aboveground-residue and root(+exudate)
pools that year via decomposition.

Back-calculated `k_ra = (annual RES C DECOMP) / (sum over days of fE_layer1 * aboveground
residue C)` and `k_r(t+z) = (annual ROOT C DECOMP, summed over 9 layers) / (sum over days and
layers of fE_layer * RESIDUE C_layer)`, across all 37 `ContinuousCorn` years. 1980 (the
simulation's own first year, with no prior-season residue carryover to draw the denominator
from) is a clear boundary-condition outlier and excluded; the remaining 36 years converge
tightly: **k_ra ~ 0.037/day (mean, stdev 0.0069, ~18% CV) and k_r(t+z) ~ 0.056/day (mean, stdev
0.0044, ~8% CV, the tighter of the two)**. Both are physically sensible on their face -- fresh
residue/root litter decomposing on the order of weeks (27 and 18 days characteristic turnover
respectively), an order of magnitude faster than the already-resolved `ks~0.0003/day` (soil
organic matter itself, which decomposes on the order of years), and root material decomposing
faster than aboveground stover, a real, commonly-reported agronomic pattern (finer tissue, less
structural lignin).

**Honest limitation, stated precisely rather than glossed**: this is `k_rt` and `k_rz` combined,
not separated -- Cycles' own SI equation treats root residues and rhizodeposits as two distinct
terms with potentially different rates, but the real output file exposes only one combined
"RESIDUE C" pool for both, so there is no way to split them further from this data alone.
**k_rm (manure) remains fully unresolved** -- this `ContinuousCorn` scenario has no manure
event in its real operation file at all (`MANURE RESID C` is 0 throughout), so there's no real
manure-decomposition data to back-calculate from here; would need a real manured scenario's
output (none currently on hand) run the same way. C-Farm's own paper gives a real, citable but
structurally different proxy for manure specifically (a humification FRACTION of 0.30-0.35/yr,
not a first-order rate constant) -- worth knowing, not a substitute for the real k_rm.

**2026-10-01, continued -- two further checks run per direct request, both load-bearing for
whether any of the above is trustworthy enough to build on, not just more parameter-hunting.**

**Check 1: does fE's moisture term have a "too wet" (anoxia) decline, or does it just plateau?**
Pooled real `FACTOR COMP.` against real per-layer water content, normalized to each layer's own
relative wetness `(theta-pwp)/(fc-pwp)`, across Rock Springs' own deeper, clay-rich layers AND
Western Kansas's real sandy topsoil (deliberately a second, different soil, since a sandy
profile's sat/fc ratio is much larger, giving real data points well above field capacity that
Rock Springs' own layer 1 never reaches) -- after first dividing out the already-fit temperature
response (fitting *that* alone left too much residual noise to see the moisture shape cleanly).
Result: moisture-factor rises smoothly from a real, nonzero floor at the wilting point (~0.16 at
relwet=0, i.e., some decomposition continues even at/below the classical wilting point -- a real
finding, since wilting point is a plant-stress definition, not a microbial-activity cutoff) up to
1.0 by about half the plant-available-water range, then **plateaus at 1.0 with zero decline, all
the way out to 2.6x relative wetness** (n=3407 points above field capacity, mean 0.98, stdev
0.03, no trend). Checked across two structurally different soils, not one. **This resolves the
question cleanly: Cycles' real fE has no waterlogging/anoxia penalty at all** -- it's a one-sided
ramp-then-plateau, not the bell-shaped response a naive assumption would guess at. Quadratic fit
of the rising segment (`moisture_factor = 0.157 + 1.052*relwet + 1.337*relwet^2`, R^2=0.926, n=
12876) is real but noisier than the temperature fit, honestly stated.

**Check 2: do today's back-calculated constants actually transfer to a scenario none of them
were derived from** (`CornSilageSoyWheat` -- same Rock Springs soil, genuinely different crops/
residue timing/rotation, confirmed via its own Csx% matching `ContinuousCorn`'s exactly, 2.8975/
3.4975/4.1725, since it's the same physical soil)? Real, mixed-but-encouraging result, not a
clean pass or fail:
- `k_r(t+z)` (root+rhizodeposit): CornSilageSoyWheat's own independently-measured value is
  0.0580/day vs. ContinuousCorn's 0.0563/day -- **within 3%**, a genuinely strong transfer.
- `k_ra` (aboveground residue): CornSilageSoyWheat's own value (excluding its manured years,
  to compare like-for-like) is 0.0427/day vs. ContinuousCorn's 0.0365/day -- about 17% apart,
  same order of magnitude, tight internal consistency within each scenario (stdev ~4-5% in
  both) but a real, not-fully-explained cross-scenario gap, plausibly real differences in
  residue chemistry between continuous-corn stover and this rotation's mixed residues.
- `ks`: applying ContinuousCorn's own point estimate (0.00032) directly to CornSilageSoyWheat's
  real data gives 36% relative error; refitting fresh on CornSilageSoyWheat alone gives 0.000404
  -- about 25% higher than ContinuousCorn's own estimate, consistent with (not contradicting)
  the already-documented ~20-35% real uncertainty band on this constant, not evidence it's wrong.

**A genuine bonus discovery while running this check**: `CornSilageSoyWheat` turns out to have
real manure events in about half its years (confirmed directly, `MANURE RESID C > 0`) --
something not accounted for going in, and the first real manured scenario this whole
investigation has had access to. Resolved `k_rm` for the first time: a naive blended estimate
(treating manure+stand+flat as one pool, the same way `k_ra` was computed) showed aggregate kra
reading LOWER in manure years (0.0349) than non-manure years (0.0427) -- the wrong direction for
"manure decomposes faster," pointing instead at manure decomposing SLOWER than fresh residue
(physically sensible: manure has already been partially processed by gut passage, leaving a
more recalcitrant residual). Rather than stop at that blended signal, separated the two
daily-tracked pools (STAND+FLAT vs. MANURE are already distinct columns) and solved a genuine
2-variable joint least-squares fit (`RES_C_DECOMP = k_ra*sum(fE*standflat) + k_rm*sum(fE*manure)`
across all 36 real years): **k_ra=0.0417/day, k_rm=0.0246/day** -- a tight fit (6.8% mean
relative residual, the best-fitting of any constant derived this session), confirming manure
decomposes at roughly 60% of fresh aboveground residue's rate, and giving `k_rm` a real,
data-grounded value for the first time (though only from this one scenario -- not yet
cross-checked against a second independent manured run the way `k_r(t+z)` was).

**Updated standing, now that every originally-named constant has a real estimate:** Csx exact;
`k_r(t+z)` strong (3% cross-scenario agreement); `k_ra` and `k_rm` good (tight within-scenario
fits, `k_ra` with a real ~17% cross-scenario gap not yet explained); `ks` moderate (~20-35%
real uncertainty, confirmed by held-out test, not just internal robustness checks); `eps_c*k_m`
still the loosest (fA confound never cleanly resolved). **Still genuinely open**: `fA`'s exact
functional form (bounded, never characterized); splitting `k_rt` from `k_rz`, and `eps_c` from
`k_m` (only their products are known); `fE`'s temperature fit is unverified above ~26C, since
Rock Springs' real record never gets hotter than that; `k_rm` has one scenario's worth of
evidence, not two.

Nothing shipped to the engine -- the six-pool system stays correctly out of v1 scope per Matt's
standing decision, so there's no live code path to wire any of this into yet. This is purely a
documentation update. The practical upshot, stated plainly for whoever next decides whether to
build this: the parameter-knowledge gap that was the main blocker going into this session is now
substantially, genuinely closed -- held-out validation came back encouraging, not circular --
and what remains is now mostly a real software-scope question (a new, cross-cutting subsystem),
not an accuracy-of-information question.

**2026-10-01, continued -- Matt decided to build it, scoped explicitly narrow first.** Given
three choices (full build vs. narrow first; hold for more searching vs. ship disclosed
placeholders for fA/eps_c; replace the RothC mechanism vs. run parallel/opt-in), Matt chose
narrow-first, disclosed placeholders, and parallel/opt-in -- build a single-topsoil-layer
two-pool (Cm, Cs) carbon system as an alternative background-nitrogen mechanism, not the full
multi-layer/rotation/tillage-aware system, and don't touch the RothC path's own already-passing
corn/soybean validation while testing it.

**Built**: `sixpool_init_state()`/`sixpool_step()`/`sixpool_fe_temp()`/`sixpool_fe_moisture()`/
`sixpool_csx_pct()`/`sixpool_bulk_density()`/`sixpool_fh()`/`sixpool_fd()` in
`cycles_engine_validate.py`, wired into `simulate_season()` via a new
`background_n_model="sixpool"` parameter (default stays `"rothc"`, byte-identical to every
existing caller -- confirmed via the full `run_validation.py`/`run_validation_rotation2.py`/
`pattern_assertions.py` suite, all unchanged: corn 0.777, soybean 0.947, wheat 0.444, silage
corn 0.117, 15/16 pattern checks). fA=1.0 and eps_c=0.4 are the disclosed placeholders per
Matt's go-ahead; kra/k_rtz/krm/ks/eps_c*k_m use this session's own back-calculated values
directly; net N mineralized = (total carbon respired as CO2 that day) / CN_RATIO_SOM=11.0, a
flat-ratio simplification, not real per-pool N stoichiometry (undisclosed anywhere checked).

**Real bug found and fixed while first testing it**: the carbon pools' absolute size was
initially scaled by `layers[0]["thick"]` -- the caller's own first soil layer's thickness,
which turns out to be an arbitrary STATSGO2-resolution artifact, not a real signal (Rock
Springs' own hand-curated profile: 0.05m; Iowa's resolved-tile profile: 0.33m). Applying the
same soc%/clay% over wildly different thicknesses inflated Iowa's Cs pool roughly 6x relative
to Rock Springs for the same inputs, pushing Cs to/above its own Csx ceiling and producing
byte-identical N=0/N=650 yield (complete elimination of nitrogen limitation). Fixed by
introducing `SIXPOOL_TOPSOIL_DEPTH_M=0.20` (a fixed depth convention) in place of the
caller's own layer boundary.

**The initial diagnosis of why N=0/N=650 came out byte-identical everywhere was WRONG, and
checking it properly (Matt's direct "try 1 first") found the real cause and a real fix for
most of it.** The first theory -- `SIXPOOL_KS` was back-calculated against real Cycles' own
WHOLE-9-LAYER-PROFILE Cs sum, so it's invalid applied to a single shallow layer -- turned out
not to hold up: `ks`, as a rate constant, is dimensionally fine to apply to any one layer's own
REAL absolute Cs (the fit's own linear structure means the same `ks` applies uniformly to each
layer's own term inside that profile sum). The actual bug was that this mechanism's COMPUTED
`Cs0` wasn't the real absolute value for the layer it was meant to represent.

Checked directly against real Cycles' own actual layer-1 `SOIL ORG C` stock
(`soilLayersCN.txt`, Rock Springs, 1980-01-01: **11.417 Mg C/ha**) -- three depth choices
tested in order: the already-tried fixed 0.20m convention gave 45.69 (4x too high, confirming
it as the first bug); `layers[0]["thick"]` directly gave 11.42 for Rock Springs' own
hand-curated profile (essentially exact) but a WRONG value at every other site, for a
different, more precise reason -- this project's own STATSGO2 nearest-cell soil lookup
(`field_data.py`, used by every multi-site panel) resolves a genuinely different layer-1
thickness than Cycles' own real `.soil` file even at the EXACT SAME Rock Springs coordinates
(0.15m vs. 0.05m), and Kansas/Iowa's own resolved layers are 0.33m -- so "whatever a given
soil lookup's layer0 happens to be" isn't the real quantity `SIXPOOL_KS` was fit against; a
fixed **0.05m** (Cycles' own real Rock Springs layer-1 thickness, the actual real control
volume every back-calculated constant in this mechanism traces to) is the correct choice, and
reproduces the real 11.417 Mg C/ha reference almost exactly (11.422 computed) regardless of
which soil-lookup pathway supplies the clay%/soc% inputs.

**Result after the fix**: Rock Springs (both its hand-curated profile and its own
STATSGO2-resolved one) and Kansas now show real, non-trivial nitrogen responses --
`rock_springs(2012)`: rothc 0.743 vs. sixpool **0.718**; `kansas(1997)`: rothc 0.799 vs.
sixpool **0.754** -- both inside the real literature/Cycles-documented band, and both
comparable to (Kansas: slightly better than) the RothC path's own hand-tuned proxy at the
exact same site/year. The 37-year Rock Springs sweep (hand-curated profile) also recovered a
sensible, if more N-limited, check-plot pattern (mean grain 6.18 vs. rothc's 7.17 at N=0, both
converging to the same 10.56 Mg/ha ceiling by N=150).

**Iowa alone still saturates (relative yield exactly 1.00) -- a SEPARATE, genuine, NOT-yet-
resolved finding, confirmed to be unrelated to the depth bug just fixed.** Iowa's real
measured SOC (3.488%) exceeds what `sixpool_csx_pct()`'s own `Csx(clay)=2.11+3.75*fclay`
formula says its particular texture (31% clay) should be able to hold at saturation -- ratio
1.066, computed DEPTH-INDEPENDENTLY (Cs0/Csx cancels the depth term entirely, so this isn't
the same bug re-appearing). This is a real tension in applying a formula whose own two
corroborating sources (the back-calculated Rock Springs values and Kemanian & Stockle 2010's
published Eq. 3) were both anchored at Rock Springs' own comparatively modest 1.74% SOC --
not yet tested against, let alone verified for, a much richer prairie soil almost double that.
Not resolved this session; a real next step if picked up again, not attempted here since it
wasn't what was asked.

Documented directly in the code (`cycles_engine_validate.py`'s module-header STATUS comment,
updated to the real, verified fix and the real remaining Iowa-specific gap) and still NOT
ported into either embedded `ENGINE_SOURCE` copy (`engine-demo.html`, `model-validation.html`)
-- Rock Springs/Kansas-type sites are now in real working order, but this mechanism is still
new, opt-in, and unverified at a high-SOC site, not ready to expose anywhere it would affect a
real shown number.

**2026-10-01, continued ("let's continue") -- the Iowa "Csx-ceiling" diagnosis was tested
directly and found WRONG, and the real explanation is a genuinely good result for this
mechanism, not a new problem.** Tested the hypothesis head-on before writing it up as
unresolved: capped `Cs` at `Csx` (clamping the supposed excess) and re-ran Iowa -- relative
yield stayed exactly 1.000, unchanged. The 6.6% Csx-ceiling overshoot found earlier was a red
herring, not the actual driver.

Built real Cycles v1.4.4 input files for Iowa for the first time this project (no real ground
truth existed there before now) -- `Iowa.weather`/`Iowa.soil` from this project's own already-
committed, already-resolved STATSGO2/NLDAS-2 tile data (same coordinates the engine's own
multi-site panels already use), `IowaN0.operation`/`IowaN150.operation`/`.ctrl` mirroring the
already-validated `KansasN150` files exactly (same rotation/tillage/planting structure), run
through the real binary for the full 1980-2016 record. **Real Cycles ITSELF shows
near-complete nitrogen saturation at Iowa in MOST years** -- relative yield (N=0/N=150) is
EXACTLY 1.0 in at least 12 of 37 years checked (1980, 1981, 1988, 1992-1995, 1999, 2000, 2005,
2007, 2011, 2012 among them), mean 0.946 across the full record, real range 0.701-1.000. Iowa's
real, famously fertile prairie soil genuinely supplies enough background nitrogen that added
fertilizer changes little in real Cycles' own simulation, in most years -- this is not an
artifact specific to this engine.

Direct comparison against this real reference: this mechanism's own mean relative yield at
Iowa (0.999, essentially always flat) is actually CLOSER to the real 0.946 than the currently-
shipped RothC path is at the exact same site (0.794, too responsive in the other direction) --
a genuine, better absolute-level match, not a regression from switching mechanisms. Separately,
the N=150 (normally-fertilized) absolute yield itself correlates 0.904 against real Cycles
across the full 37-year record (MAE 1.94 Mg/ha, mean 8.65 vs. real 10.25) -- a real, decent
validation number for Iowa corn yield overall, using a mechanism built this session from
scratch with no Iowa-specific tuning at all.

What neither mechanism gets right: real Cycles' own YEAR-TO-YEAR pattern of which years are
more or less nitrogen-responsive. Checked directly -- this mechanism's year-to-year relative-
yield pattern correlates -0.12 against the real pattern, and RothC's correlates -0.18 (both
effectively uncorrelated-to-slightly-backwards, not a meaningful difference between the two
mechanisms). This is the same category of gap already documented for Kansas's nitrogen-
response muting (item 6 above), not a new, Iowa-specific failure -- and that item's own
standing diagnosis (real multi-year soil-state carryover is the one mechanism that's
consistently helped elsewhere, not a single-season formula tweak) is the more likely real fix,
not something attempted here.

Net result of "try 1 first," now complete: the single-layer-scope repair (the correct 0.05m
depth) genuinely works, at real, verified mean-level accuracy, at all three sites tested --
including Iowa, once properly checked against real ground truth instead of assumed broken.
The real, remaining, shared limitation (missing year-to-year nitrogen-response variability) is
not specific to this mechanism and not something the narrow-first scope was ever expected to
fix. Iowa's own real Cycles input files (`Iowa.weather`, `Iowa.soil`, `IowaN0`/`IowaN150`
`.operation`/`.ctrl`, and their real output) live only in `/tmp/cycles-run`, per this project's
standing licensing discipline (Cycles' generated output is squarely what its CC BY-NC-ND
license restricts) -- not committed here, and will need rebuilding from the same committed
tile data if `/tmp/cycles-run` resets before this is revisited.

**2026-10-01, continued, wheat promoted to sixpool -- per Matt's direct "I'm not interested in
leaving the path we're making progress on."** One more real comparison checked first: corn at
genuinely nitrogen-limiting rates (N=0/10/25, since N=150 turned out to no longer bind at all
after an earlier fix moved corn's real limiting range down to roughly N=0-10). Sixpool's
correlation beat RothC's at every one of those rates (0.72 vs. 0.68-0.70), though its absolute
level undershot more, since RothC's flat constant happens to be hand-tuned to land exactly on
the real ceiling at N=50 specifically -- a calibration gap, not a ranking gap, and correlation
(the harder number to earn) was consistently as good or better. Four independent confirmations
(Rock Springs, Kansas, Iowa, corn's own N-limited rates) made wheat's own already-shipped
validation the clear next step: it's below the classroom-workable bar either way, so promoting
it doesn't touch anything currently passing.

Extended `run_validation_rotation2.py`'s `validate()` with `background_n_model`/
`sixpool_topsoil_clay_pct`/`sixpool_topsoil_soc_pct` (defaulting to the exact old behavior,
confirmed byte-identical for soybean's/silage corn's own unaffected calls), then switched
wheat's own call to `background_n_model="sixpool"`. Re-derived `WHEAT["calibration_factor"]`
(0.7502 -> 0.7541, a pure mean-matching rescale) to keep the mean exactly matching real output.
**Wheat's validated correlation is now 0.490** (up from 0.444), mean % error 11.0% (down from
11.6%) -- confirmed via the full regression suite (corn 0.777, soybean 0.947, silage corn
0.117, pattern-assertions 15/16, all unchanged).

Ported the six-pool mechanism's own code into `model-validation.html`'s embedded
`ENGINE_SOURCE` -- not `engine-demo.html` -- since that page's "Full simulation controls"
panel exists specifically to expose every real `simulate_season()` parameter to technical
reviewers. Added a new "Background nitrogen mechanism" fieldset there (a `<select>` between
RothC and the two-pool mechanism) wired through `runFullSimulation()`. Verified three ways:
(1) the exact extracted `ENGINE_SOURCE` string, run against real Rock Springs weather/soil,
reproduces the canonical script's own sixpool result to full float precision; (2) the literal
JS-sent Python snippet (`_fc_bg_kwargs` branch) executed directly in CPython for both
`"rothc"` and `"sixpool"` values, confirming the branch and the `sixpool_final_state` output
key appear only when selected; (3) headless Chromium confirms the new `<select>` renders both
options, the page loads with zero new console errors, and HTML tag balance (div/fieldset/
select) is unchanged. `engine-demo.html`'s own wheat usage (the rotation panel's fall-planted
cover-crop role, never validated the way this fixed cash-crop scenario is) was deliberately
left on RothC -- a separate decision, not made this round. Both files' `SPECIES_REGISTRY`
entries and `model-validation.html`'s own static validation table updated to the new 0.490/
11.0% numbers.

**2026-10-01, continued -- multi-year carryover tested against the six-pool mechanism's own
carbon state, per Matt's direct "where should we focus" / "yes" to pursuing it. A genuinely
strong, decision-ready result, with a clear next engineering step identified, not yet built.**

Added `sixpool_initial_state` to `simulate_season()` -- mirrors `initial_layers`' own real
multi-year carryover pattern (a caller's prior season's `sixpool_final_state` fed back in as
the next season's starting Cs/Cm/Cra/Crtz, deep-copied so the caller's own object is never
mutated), `None` by default reproducing the exact existing single-season behavior. Confirmed
byte-identical across the full regression suite (corn 0.777, soybean 0.947, wheat 0.490,
silage corn 0.117, pattern-assertions 15/16, all unchanged).

**The actual target metric**: real Cycles' own year-to-year pattern of which years are more or
less nitrogen-limited, the one gap that showed up at every site tested for the fresh-start
mechanism (correlation against the real pattern: -0.12 at Iowa, -0.18 for RothC at the same
site). Tested by chaining BOTH soil-moisture state (`initial_layers`) and six-pool carbon state
across Iowa's full real 37-year consecutive record (1980-2016), at two fixed nitrogen rates
(N=0 and N=150) run as two separate full chains, compared against the real ground truth already
built for Iowa (`IowaN0`/`IowaN150`, see the entry above).

**Result 1, carryover with NO residue return (the mechanism as shipped)**: correlation against
the real year-to-year pattern improved to **+0.482** -- the best result this whole
investigation has found at any site, for either mechanism, by a wide margin. But a real,
new problem surfaced: the chain's own absolute level drifted down hard over the decades (mean
relative yield 0.586 vs. real 0.946; N=0's own chained mean grain 4.55 Mg/ha vs. real 9.65,
roughly a 53% undershoot by the end of the record). Diagnosed directly, not assumed: both the
N=0 AND the N=150 chains decline over 37 years (confirmed by checking N=150's own chained
yield against real Cycles, which still correlates well, 0.872, but undershoots the mean by
~23%) -- a real structural gap, not noise. Root cause: this mechanism's v1 scope explicitly
excluded aboveground residue return ("no previous-crop residue carryover... the only real
carbon input... is the live crop's own root growth," `sixpool_init_state()`'s own docstring)
-- a defensible simplification for a single, from-scratch season, but one that breaks down
exactly when chained: every real season's own stover is a real carbon input to NEXT season's
soil, and omitting it means the mechanism only ever removes carbon (via decomposition, grain
harvest, and leaching) with nothing returning it, so of course it drains over decades.

**Result 2, carryover with 100% immediate residue return (AG biomass minus grain, carried
whole into next season's Cra)**: the opposite failure -- relative yield pinned at exactly
1.0 every single year, correlation undefined (zero variance). Diagnosed: a naive full-amount,
zero-delay return massively overshoots, since real stover mostly decomposes over the real
calendar off-season (confirmed elsewhere in this engine: `kra`'s own ~18-day characteristic
turnover means most of a season's residue would be gone well before next spring's planting)
-- this test added it with NO off-season decomposition at all, the wrong end of the same
depth-scaling-style unit mismatch already caught once this session.

**Result 3, a sensitivity sweep on a flat retention fraction (crude stand-in for "how much
survives the off-season undecomposed," not a real off-season decomposition model)**: sharply
sensitive and informative. 10% retention: correlation **0.604** (the single best result this
whole project has produced, at any site, for any mechanism) and mean relative yield 0.868,
much closer to real's 0.946 than either extreme. 25% retention: already collapses back to
~1.0 saturation (correlation undefined) -- confirming the real system sits on a narrow, steep
transition, not a flat plateau, so pinning the right value needs a real mechanism, not a
guessed constant.

**What this means, stated plainly**: the hypothesis (multi-year carbon-pool persistence
captures the real year-to-year nitrogen-response pattern that a fresh-start pool structurally
cannot) is strongly confirmed -- 0.604 correlation is not a marginal improvement, it's the
best number this whole investigation has found. But the specific mechanism tested to get
there (a flat, guessed residue-retention fraction) is explicitly NOT a real formula and
should not be mistaken for one -- it was built only to characterize the sensitivity, which it
did. **The real next engineering step, not yet built**: a genuine off-season Cra decomposition
pathway -- add the season's own real stover (AG biomass minus grain, already computed) to Cra
at harvest, then run Cra's own real decay (`fE*kra*Cra`, already-implemented, no new formula
needed) day by day through the real calendar gap between this harvest and next planting,
using real weather for those days (already available, the same data `spinup_rows` already
draws from) -- rather than a single flat retention guess applied all at once. This would let
the real `kra` rate (already back-calculated, already trusted) determine how much residue
genuinely survives the off-season, instead of an arbitrary stand-in fraction. A real, bounded,
well-motivated next task if this is picked up again -- not attempted this round, since the
sensitivity-sweep test that found it was explicitly scoped as "characterize whether this is
worth building," not "build it."

Two further, real, disclosed humification-fraction formulas exist and were NOT used in this
round, worth checking against the eventual real mechanism once built: Kemanian & Stockle
(2010) Eq. 4a/4b give `hca = 0.09+0.11(1-exp(-5.5*fclay))` and `hce = 0.08(1-exp(-5.5*fclay))`
-- real, sourced humification-efficiency fractions (not retention-survival fractions, a
different concept from what this round's flat-fraction test modeled, so not directly
substitutable without more care) that could plausibly inform the real mechanism's own
efficiency term once the off-season decomposition timing is modeled properly.

Not committed to the engine beyond `sixpool_initial_state` itself (a clean, tested, byte-
identical-when-unused capability) -- the flat-fraction residue-return test lives only in this
session's scratch scripts, not the repo, since it was explicitly a sensitivity probe, not a
real mechanism.

**2026-10-01, continued -- the real off-season decomposition mechanism was built, per Matt's
direct "yes" to building it rather than leaving the flat-fraction guess in place. Honest,
mixed result: a genuine, substantial win on absolute yield accuracy, but it does NOT reproduce
the specific year-to-year nitrogen-response pattern the flat-fraction sweep had found -- that
0.604 number should now be read as a narrow coincidence of the guessed parameter, not a
preview of what the real mechanism would do.**

Built two real, additive pieces in `simulate_season()`: (1) at harvest, this season's own
stover (AG biomass minus grain removed, the same quantity real Cycles' own harvest.txt "AG
RESIDUE" column represents) is credited into `sixpool_state["cra"]`, unconditional and
provably inert for any single-season caller (it happens after grain/HI are already finalized,
so it can only matter to a FUTURE chained call that reads `sixpool_final_state` back in --
confirmed: wheat's own just-promoted 0.490 correlation, which doesn't chain, reproduced
byte-identical). (2) A new `sixpool_offseason_decay` parameter (default False, byte-identical
when unused) that, when True, runs real day-by-day Cra/Crtz/Cm/Cs decomposition during the
existing `spinup_rows` window -- reusing `sixpool_step()` itself unmodified (zero root-carbon
input, since no crop is growing), driven by that window's own real weather and this season's
own evolving topsoil moisture. No new formula was needed; this is the real `kra`/`fE` physics
already trusted elsewhere in this engine, just run with nothing growing.

**First test, using the window every existing harness already has (Jan1-through-planting
only)**: relative yield pinned at exactly 1.0 every single year -- the SAME failure mode as
the original "100% immediate return" test, just reached differently. Diagnosed directly:
`sixpool_fe_temp()` returns 0 below freezing, and Iowa's Jan-March is mostly frozen, so almost
no real decomposition happens in that window at all regardless of how long it runs -- the
window was simply too short and too cold to do anything.

**Second test, building the FULL real off-season window for the first time** (this season's
own real harvest day, estimated from `record_history`'s last entry, through Dec31, plus Jan1
through next season's planting -- genuinely spanning the warm post-harvest months the first
test never reached): a real, substantial, different result. Mean relative yield still sits
near 1.0 (0.993, real range mostly 0.79-1.00 vs. real Cycles' 0.70-1.00) and the year-to-year
correlation against the real pattern came back slightly NEGATIVE (-0.11, not an improvement
on the already-poor fresh-start number) -- so the specific target metric from the carryover
test two entries above is NOT resolved by the real mechanism. But the ABSOLUTE yield itself,
at both nitrogen rates independently, now correlates far better against real Cycles than any
chained test run so far: N=150 0.902 (vs. 0.872 with no off-season decay at all), N=0 0.910
(vs. 0.822) -- and the mean-level gap shrank substantially too (N=150 chained mean 8.67 vs.
real 10.25, N=0 chained mean 8.61 vs. real 9.65, both much closer than the no-decay chain's
7.90/4.55).

**What this means, stated plainly, not softened**: real multi-year carryover, with real
(not guessed) off-season decomposition, is a genuine improvement for ABSOLUTE yield tracking
across a multi-year chain -- a real, physically-grounded mechanism, not a hack, and worth
keeping for that reason alone. It does NOT, as built, solve the specific "which years are
more nitrogen-limited" puzzle that motivated building it in the first place -- the 0.604
correlation found with a flat 10% retention guess does not reappear once the guess is
replaced with real decomposition physics, meaning that number was very likely a coincidence
of where the guessed constant happened to land, not evidence the underlying mechanism was
right. This is a real, disclosed negative result on the specific question asked, alongside a
real, disclosed positive result on a related but different question (absolute multi-year
yield accuracy) -- both true at once, neither cancels the other out.

**Not yet investigated, a real candidate if this is picked up again**: the two REAL low-
response points this mechanism DID produce (2007, 2008) don't line up with real Cycles' own
actual low-response years (2001, 2004, 2009-2010, 2013-2014) at all -- suggesting whatever
triggers a real dip in this mechanism's own chained trajectory is driven by something
incidental to THIS mechanism's own state dynamics, not the same real driver behind actual
Cycles' year-to-year nitrogen variability. Worth a direct day-by-day comparison of this
mechanism's own Cra/Cm/Cs trajectory against real Cycles' own multi-year `annualSOM.txt`/
`soilLayersCN.txt` output (both already available for Iowa, see the entry above) before
guessing at another parameter -- not attempted this round.

Committed: `sixpool_offseason_decay` and the unconditional stover-crediting, both confirmed
byte-identical to every existing caller via the full regression suite. Not committed: the
cross-year off-season-window-building logic itself (currently only in this session's scratch
scripts) -- every existing harness (`run_crop_season()` in `pattern_assertions.py`, `validate()`
in `run_validation_rotation2.py`) still only ever builds a same-calendar-year, Jan1-to-planting
`spinup_rows`, so using the real mechanism for a genuine multi-year chain outside this
session's own test script would need that cross-year window built into a real harness first,
not assumed to come for free from `sixpool_offseason_decay` alone.

**2026-10-01, continued -- "let's look at the trajectory," per Matt's direct ask. A conclusive
diagnosis, not a fix: the carbon-side physics checks out almost exactly against real Cycles at
two very different sites, which is exactly what reveals the real weak link isn't there at
all -- it's the flat carbon-to-nitrogen conversion this mechanism uses, confirmed by
elimination, not assumed.**

Pulled real Cycles' own `N STRESS` column directly (`CornRM.90.txt`, IowaN0) instead of
inferring it from relative yield. The real pattern is stark and genuinely different from
"year-to-year weather noise": **exactly zero** max seasonal N stress in every one of 1980-1991
(12 straight years), then a real, growing pattern from 1992 onward (mean 13.8% across
1992-2016, individual years up to 38.7% by 2014). This is a secular, decade-scale onset, not
noise -- real Cycles' own soil clearly starts with enough available nitrogen to cover roughly
a dozen years of continuous unfertilized cropping before stress appears at all, then stress
grows as that reserve is drawn down further.

Checked whether this mechanism's own chained carbon trajectory (built two entries above)
shows anything resembling that shape. It does not -- the opposite, in fact: using the fixed
0.05m depth (matched to Rock Springs' own real Cycles reference), Cs declines FASTEST in the
first 12 years (19.4 -> 14.8 Mg C/ha, a 24% drop) then flattens for the remaining 25
(14.8 -> 13.7, an 8% further drop) -- a textbook first-order-decay shape, the inverse of real
Cycles' delayed-onset, still-growing pattern.

Formed a real, testable hypothesis rather than guessing at a fix: maybe the fixed 0.05m depth
-- chosen specifically because it matched Rock Springs' own real Cycles reference exactly --
was systematically undersizing every OTHER site's real carbon reserve, since Iowa's own real
resolved soil layer is 0.33m thick, not 0.05m. Checked directly against real Cycles' own
reported layer-1 carbon mass for Iowa (`soilLayersCN.txt`, 1980-01-01: 130.13 Mg C/ha): using
Iowa's own real layer thickness (0.33m, not the flat 0.05m) gives 130.23 -- an almost exact
match. This confirms something real and useful on its own: the carbon-side formulas (Csx,
bulk density from Saxton-Rawls, the soc%-to-absolute-mass conversion) are NOT the problem --
they reproduce real Cycles' own reported absolute carbon mass almost exactly at Iowa's real
thickness, just as they already did at Rock Springs' real thickness. The earlier "fixed
0.05m" choice was right for matching Rock Springs specifically (the one site with a genuine
conflict between its own hand-curated profile and its own STATSGO2-resolved one, see the
entry above) but was never meant to be a universal convention -- for any site where the
resolved profile IS the only real description (Iowa, Kansas), that profile's own real
thickness is what real Cycles was actually run against, and should be used.

Tested the real hypothesis directly: re-ran the full 37-year Iowa chain (same real off-season
decay mechanism, same stover crediting) using Iowa's own real 0.33m-equivalent starting
reserve (Cs0=127.87, not 19.4) instead of the flat 0.05m value. Result: relative yield stayed
pinned at EXACTLY 1.0 for all 37 years, even though Cs itself declined by a real, substantial
60% over the chain (127.87 -> 51.41) -- the much bigger real reserve never gets small enough,
within 37 years, to meaningfully limit a corn crop's nitrogen demand at the rate constants and
C:N conversion this mechanism currently uses. Checked why directly: `fD` (the saturation-
driven decomposition-rate factor) only falls from 0.99 to 0.87 across that entire decline,
since Cs/Csx never drops much below its own healthy starting ratio -- almost no self-limiting
feedback kicks in across the whole real range this decline actually traverses.

**The conclusion, stated plainly: this isn't a reserve-size problem, since both the too-small
and the real, correctly-sized reserve fail, just in opposite directions (too-fast depletion
with the wrong shape, vs. never-depletes-enough).** The carbon-side physics is now confirmed
accurate at two real, very different sites -- the weak link is specifically the flat
`CN_RATIO_SOM=11` shortcut this mechanism uses to convert net carbon respired into nitrogen
mineralized. Real Cycles almost certainly tracks nitrogen through its own separate pool
dynamics (a real six-pool NITROGEN system paralleling the carbon one, with its own N:C ratios
per pool and its own immobilization/mineralization balance -- exactly the system Matt's own
standing decision keeps out of v1 scope, correctly, since its rate constants are undisclosed
nowhere checked so far) -- not a single flat ratio applied uniformly regardless of which pool
the carbon came from or how depleted the system is. This is a genuine, evidence-based
confirmation of why that system was scoped out from the start, not a new problem -- the
single-ratio shortcut was always a disclosed simplification, and this is the first time its
specific failure mode (right carbon physics, wrong nitrogen conversion, at the decade
timescale specifically) has been precisely characterized rather than just flagged as a risk.

Not pursued further this round, deliberately: building the real nitrogen-specific pool system
to test a fix would mean guessing at undisclosed rate constants with no real data to
back-calculate them from (unlike the carbon-side constants, which had real Cycles output to
check against) -- exactly the kind of blind construction this project's own discipline exists
to avoid. Nothing committed; this was a diagnostic exercise using a monkey-patched test
script, not an engine change.

Resolved without asking, 2026-10-02 (direct follow-up to the entry immediately above, after
being told not to treat "undisclosed" as the end of the line): the premise of the previous
entry's conclusion was wrong. The real per-pool C:N ratios are NOT undisclosed -- they are
literal daily output columns in a file this project had already been reading for its carbon
data (`soilLayersCN.txt`) without ever looking at the C:N columns sitting right next to the
ones already in use: "STAND RESID C:N" / "FLAT RESID C:N" / "MANURE RES C:N" / "MIC C:N" /
"SOIL ORG C:N". Pulled directly from real Cycles output: Rock Springs ContinuousCorn gives a
real, stable-across-37-years median STAND/FLAT residue C:N of ~86 and MIC C:N of ~9.66 and
SOIL ORG C:N of ~9.38; CornSilageSoyWheat (the one scenario with real manure events) gives a
real median MANURE RESID C:N of ~29.9. There is no disclosed "ROOT C:N" column, but it's
directly calculable from two OTHER already-disclosed columns in a different file
(CornRM.90.txt's own real ROOT BIOMASS and ROOT N): root_biomass_mg_ha * 0.42 * 1000 /
root_n_kg_ha gives a real median of ~52-53 across the full record -- lower than aboveground
residue, exactly as real agronomy would predict (roots are more N-rich than stover).

This directly resolves the gap flagged above: `sixpool_step()`'s single flat `CN_RATIO_SOM=11`
applied to TOTAL carbon respired (regardless of which pool it came from) was replaced with a
proper per-pool N mass balance -- N released when carbon leaves a pool (at THAT pool's own real
C:N), N consumed when carbon is retained into a receiving pool (at the RECEIVING pool's own real
C:N). Since residue C:N (~86 stand/flat, ~52 root, ~30 manure) runs far higher than Cm/Cs's own
C:N (~9.4-9.7), building microbial biomass out of decomposing residue is now correctly modeled
as a real, often-large net N SINK (immobilization), not a source -- something the old flat-ratio
version was structurally incapable of representing, since it only ever converted CO2 loss to
positive mineralized N, with zero mechanism for carbon RETAINED into a growing pool to cost any
nitrogen at all. The function can now return a negative value on a given day; the caller floors
the mineral-N pool it feeds at 0 (a real mineral-N pool can't go physically negative -- this
simplified day-by-day accounting isn't rate-limited by available substrate the way reality is,
so the floor stands in for that).

Verified via the full regression suite: corn (0.777, default validation never activates
nitrogen tracking), soybean (0.947), and silage corn (0.117) are all byte-identical, confirming
the fix only touches callers that actually use `background_n_model="sixpool"` -- currently just
wheat's own validated path. Wheat moved 0.490 -> 0.455 (calibration_factor re-derived, 0.7541 ->
0.7509, a pure mean-matching rescale that doesn't touch correlation) -- a real, modest
regression from the flat-ratio version, but STILL above wheat's pre-sixpool rothc baseline of
0.444, so this is a net improvement over where wheat started, just a smaller one than the flat
ratio happened to produce. `pattern_assertions.py` stays at 15/16 (no new failures). Kept rather
than reverted: the per-pool mechanism is real and disclosed, the flat ratio was a guess that
happened to score a bit higher by coincidence, and this project's own standing discipline (see
e.g. the 2026-10-01 off-season-decomposition entry, or the FAO-56 depletion-fraction fix)
already treats "more correct, real data, modest point-accuracy cost" as worth keeping rather
than chasing the single highest-scoring guess.

A genuine, separate new finding surfaced while testing this against the multi-year
`sixpool_initial_state` carryover feature (itself never shipped in any validated harness or
UI panel -- an exploratory mechanism only, per its own 2026-10-01 docstring): chaining Rock
Springs corn across consecutive years at N=0 with sixpool carryover active now produces a
striking ALTERNATING pattern -- a normal, nonzero-yield season, then a complete, total crop
failure (grain=0.000, n_uptake=0.00 kg N/ha) the very next year, then normal again, repeating
indefinitely. Confirmed this is specific to sixpool carryover, not a general carryover bug:
soil-moisture-only carryover (`initial_layers` with no sixpool state) across the same ten years
shows no such pattern at all (sensible 8.6-11.9 Mg/ha every year). Root cause, traced directly:
a good year's harvest credits a real, often-large pulse of stover carbon into `cra` (the real
`ag_residue_mg_ha = ag_biomass - grain` carried forward for exactly this purpose); the FOLLOWING
season, `sixpool_step()` runs every day starting day 1 of planting and immediately begins
decomposing that whole pulse at once, with no gradual mellowing period -- the real net
immobilization this fix correctly introduces is large enough, applied to an undiminished fresh
stover pulse with no fertilizer to buffer it (N=0), to floor the mineral-N pool at exactly zero
for the ENTIRE season, which (via `dGB_n_limited = dGB_water_limited * n_stress`, n_stress=0)
means the crop never grows at all that year. A failed year then credits ~0 new stover at its
own harvest (ag_biomass never grew), so the pulse clears and the cycle repeats. This is a real,
physically-motivated phenomenon (high-C:N fresh residue causing severe short-term N
immobilization is well documented in soil science) made UNREALISTICALLY catastrophic by this
engine's lack of any rate-limiting on how fast a microbial pool can draw down a finite
mineral-N stock in one day, and by `cra` arriving as one instantaneous lump rather than a
gradual return. Not fixed this round -- multi-year sixpool carryover was already exploratory
and unshipped before this was found, and fixing it properly would mean either rate-limiting
daily immobilization by available mineral N (a real mechanism, not yet sourced from any
available Cycles data) or smoothing stover's return into `cra` over real time (also not yet
sourced) -- guessing at either now would repeat exactly the mistake this whole entry's fix was
about not making. Flagged here so it isn't rediscovered as a surprise if multi-year carryover
work resumes; the single-season, no-carryover default path (used by every currently-validated
crop, wheat included) is completely unaffected by this finding.

Resolved without asking, 2026-10-02 (direct continuation of the same session, per the
direct instruction "let's be modelers and solve the problem from available data or solvable
math"): checked whether N.txt (the same file already mined for MINERALIZATION/
IMMOBILIZATION/NET MINERALIZ in the sixpool work above) also carries real daily nitrogen-loss
fluxes this engine had never looked at. It does -- "NH4 NITRIFICAT", "N2O FROM NITRIF",
"NH3 VOLATILIZ", "NO3 DENITRIF", "N2O FROM DENIT" are all literal real daily output columns,
sitting in the same already-parsed file. This directly contradicts the earlier "confirmed
absent" framing for nitrification/denitrification/volatilization (item 8's own original text,
2026-09-18/09-23) -- that framing was checking whether the PAPER/SI disclose the EQUATIONS
(they don't), not whether real NUMBERS for these processes exist in Cycles' own committed
output (they do, and have the whole time).

Two real findings came out of mining this data directly:

1. **This engine's ammonia volatilization mechanism is likely overestimating loss by 2-8x for
the fertilizer/placement combination it's actually validated against.** Real Cycles' own
seasonal VOLATILIZATION total (annualN.txt, ContinuousCorn, 150 kg N/ha broadcast UAN, 37
years) averages 4.4% of applied N (range 0.1-8.1%). The flat IPCC Tier-1 default this engine
uses is 10% flat; the Macnack et al. 2013 weather-driven alternative can estimate up to 37%
on a warm, windy day (the exact Rock Springs 2012 case already flagged in item 8's own prior
text as "a real but high 37% loss... not independently checked against a real field
measurement"). It's now checked, against the real disclosed ground truth for this exact
scenario, and both existing mechanisms read several times too high. Not yet recalibrated --
flagged here rather than fixed blind, since the right fix (scale down the existing mechanisms?
replace them with something fit directly to this real total?) wasn't decided this round.

2. **A real denitrification mechanism was built where none existed before.** Computed a daily
implied fractional rate (NO3 DENITRIF / PROF SOIL NO3) for every real day with a measurable
NO3 pool (n=13372, ContinuousCorn, Rock Springs, 37 years), then regressed ln(rate) against
ln(soil moisture) separately for all 9 real soil layers before picking one:

| layer | n | k0 | exponent | r^2 |
|---|---|---|---|---|
| 1 (topsoil) | 13283 | 0.017242 | 3.469 | 0.175 |
| 2 | 13283 | 0.051717 | 4.369 | **0.314** |
| 3 | 13283 | 0.026896 | 3.828 | 0.302 |
| 4 | 13283 | 0.028019 | 4.382 | 0.220 |
| 5-9 | 13283 | (falling) | | 0.111 down to 0.026 |

Layer 2 fits meaningfully better than layer 1 (topsoil) and is physically sensible: topsoil
dries fastest via evaporation/transpiration, so the layer just below it stays wetter longer,
closer to the sustained anaerobic microsites denitrification actually needs. Final rate law:
`rate = 0.051717 * theta^4.369` applied to the layer-2 moisture. A real, clean, monotonically
increasing relationship (near-zero at theta~0.13, rising sharply above ~0.33) -- the classic
anaerobic-microsite shape -- though noisier than this project's other back-calculated rate
constants, and one that pairs a profile-WIDE NO3 pool against a single layer's own moisture, a
real mismatch disclosed here, not hidden.

Checked against the real independent seasonal total it should reproduce (annualN.txt's own
DENITRIFICATION column, mean 6.62% of applied N, range 1.4-11.4%): this mechanism's own output
across four spot-checked years is 1980=6.3%, 1996=10.6%, 2012=6.9%, 2016=5.8% -- squarely
inside the real range, and close on 2012 specifically (6.9% modeled vs. 9.465 kg/6.3% real),
though not an exact per-year match (1980 overshoots the real 1.4% by a wide margin). A real,
substantial improvement over having zero mechanism at all, not a precise reproduction.

Implemented as a new opt-in `model_denitrification` parameter on `simulate_season()` (default
False, byte-identical to this parameter not existing -- verified against the full regression
suite, all four crops and all 16 pattern checks unchanged). Applied to the whole lumped
mineral-N pool as a daily fractional loss (this engine has no NH4/NO3 split, so the real
rate -- fit against Cycles' own NO3-specific pool -- is applied to the combined pool as a
disclosed simplification, the same treatment leaching's own lumped-pool branch already gives
this exact pool for the exact same reason). Mass balance re-verified exact
(uptake+leached+remaining+denitrified=supply, to machine precision) and the standing
tillage-sanity and manure-availability-equivalence checks both re-confirmed to still pass with
it active (re-tested at a genuinely nitrogen-limiting rate, N=0-20 -- N=50, used in earlier
sanity checks, is no longer limiting after the day-by-day nitrogen mechanism's own 2026-09-28
demand-scaling fix, a stale assumption caught and corrected mid-verification, not a new bug).
Ported into `model-validation.html`'s embedded engine and wired into a new "Denitrification"
UI fieldset there (the dev-facing page); `engine-demo.html` untouched, matching the project's
"engine first, UI later" pattern for an unpromoted mechanism.

Not done this round: the volatilization overestimate found above is flagged, not fixed --
recalibrating or replacing the existing mechanism against this real ground truth is a natural
next step. Nitrification itself (NH4->NO3 conversion) was not fitted or implemented, since this
engine's lumped pool has no NH4/NO3 distinction for it to convert between; it would only become
load-bearing if the pool were ever split into real NH4/NO3 sub-pools, a larger structural
change not undertaken this round. N2O emissions (both FROM NITRIF and FROM DENIT, also real
daily columns in N.txt) were not pursued -- no classroom or validation use identified for them
yet.

Resolved without asking, 2026-10-02 (same day): fixed the multi-year sixpool-carryover
"alternating total crop failure" instability flagged in the per-pool-C:N entry above, by
finding and fixing its real root cause rather than disabling or working around the feature
that exposed it. The bug: chaining `sixpool_initial_state` across consecutive Rock Springs
corn seasons at N=0 produced a normal year, then total crop failure (grain=0), repeating
indefinitely. Traced directly: a good year's harvest credits that season's real stover
(ag_biomass - grain) into `cra` as one instantaneous lump; the very next season, the now-
correct per-pool-C:N immobilization effect (see above) applies the full steady-state
decomposition rate to that whole undiminished pulse from day one, demanding more nitrogen via
immobilization than the mineral-N pool holds with no fertilizer to buffer it -- the crop never
grows, so the failed year's own harvest credits ~0 new stover, clearing the pulse and letting
the cycle repeat.

Checked whether real Cycles' own output could resolve this rather than guessing at a fix.
Reconciled what looked like two contradictory findings into one real, previously-undiscovered
mechanism: a narrow, hand-checked 10-day window right after a real harvest pulse
(soilLayersCN.txt, ContinuousCorn, 1980-09-16 to 09-25, using the real weather/moisture for
those exact days) showed decomposition running 13-22x SLOWER than SIXPOOL_KRA (0.040/day)
predicts -- but a broad regression across all 37 years (n=10212 real day-pairs, implied
k_ra = decomposed_amount/(fE*pool)) gave a median of 0.0436, matching SIXPOOL_KRA almost
exactly, showing no such problem in aggregate. Binning that same broad sample by REAL DAYS
SINCE THE PRECEDING HARVEST PULSE resolved it: implied k_ra starts at only ~27% of its
steady-state value in the first 10 days after a pulse, rises to ~73% by day 25-30, then
plateaus (real data settles around 75-85%, not cleanly at 100%). This is the real, well-
documented microbial-colonization "lag phase" before fresh plant residue decomposes at its
full steady-state rate -- SIXPOOL_KRA itself was correctly fit to the real steady-state rate
all along; what was missing was this real, separate ramp-up before that rate applies.

Implemented as `CRA_MATURATION_TAU_DAYS = 30.0` (least-squares fit to the real binned ratios,
tau=29.8 rounded) and `cra_maturity_fraction(age_days) = 1 - exp(-age_days/tau)`, multiplied
directly into `decomp_ra` in `sixpool_step()`. A new `cra_age` field tracks days since the
pool's last addition (initialized to 9999.0, i.e. "fully matured," so a from-scratch run with
no prior pulse is unaffected); reset to 0.0 at the exact moment fresh stover is credited into
`cra` at harvest. Applied only to `decomp_ra` (aboveground residue) -- `crtz`/`crm` (root and
manure carbon) weren't checked for their own lag behavior this round, a disclosed scope limit,
not an assumption they behave identically.

Verified: completely inert for every currently-shipped validated path (`cra` is always exactly
0.0 whenever `sixpool_initial_state` carryover isn't used, which is every one of the four
default-validated crops) -- the full regression suite (`run_validation.py`,
`run_validation_rotation2.py`, `pattern_assertions.py`) reproduced byte-identical results
before and after (corn 0.777, soybean 0.947, wheat 0.455, silage corn 0.117, 15/16 pattern
checks). Re-ran the exact motivating scenario (chained Rock Springs corn, N=0, 20 consecutive
years, `sixpool_initial_state` carried forward each year): the alternating-failure pattern is
gone -- every one of the 20 years now produces a real, physically sensible yield (2.47-6.01
Mg/ha, matching real dryland-corn-without-fertilizer range), and `cra` itself settles into a
stable 1.0-2.8 Mg/ha band instead of oscillating between a large pulse and a near-total crash.
This is the real fix, not a workaround -- it corrects the decomposition mechanism to match
real Cycles' own disclosed timing behavior, which happens to also resolve the instability as a
side effect of being more physically correct.

Ported into `model-validation.html`'s embedded engine (the only HTML file carrying the
sixpool mechanism at all; `engine-demo.html` doesn't expose `sixpool_initial_state` carryover
anywhere and was left untouched) and verified via direct extraction/execution of the embedded
`ENGINE_SOURCE`/`GLUE_SOURCE` strings in CPython: the new function and field compile and run
correctly, and a real single-season sixpool run (the only sixpool path this page actually
exposes in its UI) is unaffected since `cra` never becomes nonzero there either.

Not done this round: `crtz`/`crm`'s own maturation behavior wasn't checked (both may have a
real, different lag of their own); `sixpool_initial_state` multi-year carryover itself remains
an exploratory, unshipped feature (no UI anywhere exposes it) -- this fix makes it behave
correctly when exercised directly, but promoting it to a real, UI-exposed feature is a
separate decision not made this round.
