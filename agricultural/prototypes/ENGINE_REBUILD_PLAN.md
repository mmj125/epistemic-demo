# Engine rebuild plan (started 2026-10-16)

Target: an engine whose outputs resemble Cycles v1.5.20 because its mechanisms are right, not because its outputs were fitted. Cycles is the proxy for reality. Pedagogy and UI stay frozen until the exit criteria below are met.

## Rules of the rebuild
1. Allowed fit: a process-level relationship (daily flux against a state the engine itself computes) with a physically motivated form, checked on held-out sites. Where a published equation exists, use it and cite it.
2. Not allowed: a multiplier on a final output (grain, biomass), or any per-crop, per-site or per-region factor whose job is to match a mean. This includes calibration_factor and the regional grain factor (regional_params.G_REBASE). They go to 1.0. A gap they were hiding is attributed with state forcing and fixed as a mechanism.
3. One configuration. The scored engine and the shipped engine are the same object (one defaults dict, enforced by sync_engine_pages.py).
4. One mechanism set for every crop, with all parameters read from GenericCrops.crop. No per-crop mechanism exemptions chosen by score.
5. Reference is Cycles v1.5.20. Constants fitted to v1.4.4 output are refit.
6. Held-out evaluation only: paired bootstrap on fresh sites. The locked 100-site holdout (sitesets/holdout.json) stays unopened until the final report.
7. Before every step: expected change, contingency, and whether a higher-level diagnostic should come first.

## Phases
| Phase | Work | Gate |
|---|---|---|
| 1 | Unify configuration, score the shipped engine, scripted reference rebuild with hashes, committed scorecard JSON | shipped config scored (done, see below); rebuild script exists |
| 2 | Water-state scorecard: daily per-layer theta rms against Cycles on many sites, plus state forcing attribution at scale | names the lever or rules water out |
| 3 | Crop-agnostic growth core: fit the daily growth conversion with Cycles' canopy, water, N stress and mineralization forced, across many sites and crops | held-out gain over 5% adopted, else documented as floor |
| 4 | Nitrogen and carbon on one per-layer state (mineralization, nitrification, denitrification, volatilization, leaching, N2O), refit to v1.5.20 | site-level N-loss rms log error toward 0.7 |
| 5 | Remove masks one at a time (calibration factors, regional g, wheat exemption), attribute each loss | each removal costs under 5% held-out, or its mechanism is found |
| 6 | Crop scope: corn, soybean, winter wheat, sorghum, one cool-season cover crop. Silage corn and pasture dropped until a multi-site reference exists | each crop clears 0.6 held-out with the shared physics |
| 7 | Management levers (irrigation passes; tillage fails, so isolate event order), then planting date and split N | lever effects match Cycles' effects, not just levels |
| 8 | Final report on the locked holdout; tag a release; freeze | engine error at most 2x the measured Cycles noise floor at N=150 and N=400, N0 correlation at least 0.6 |

## Phase 1 result (2026-10-16)
Same 16 tile sites, every second year, N=0 and 150, against Cycles v1.5.20 on identical inputs. Harness config = sixpool, per-layer carbon and nitrate, lead-in, regional factors. Shipped config = what engine-demo.html calls: bare simulate_season, no flags.

| Metric | Harness | Shipped |
|---|---|---|
| N=150 grain MAE (Mg/ha) / corr / bias | 0.99 / 0.84 / -0.08 | 1.76 / 0.79 / -0.75 |
| N=150 total biomass MAE | 2.13 | 3.26 |
| N=0 grain MAE / corr / bias | 0.46 / 0.90 / -0.05 | 2.09 / 0.24 / -1.33 |
| N=150 leaching MAE (kg N/ha) | 5.10 | 7.67 |
| N=150 denitrification MAE, mean bias | 11.9, -3.6 | 21.3, -21.3 (mechanism absent) |
| N=150 volatilization MAE, mean bias | 6.5, -0.3 | 11.9, -11.9 (mechanism absent) |

Reading it: the shipped engine is much worse than the number we have been quoting, mainly at N=0 (corr 0.24) and in every N-loss term, which the page does not model. Also, the harness numbers are partly in-sample: the regional net-N multiplier and grain factor were fitted on these sites, so the harness N=0 grain (corr 0.90) overstates what a mechanism-only engine would do. Phase 5 will show how much of it is mask.

## Phase 1 completed (2026-10-16)
- `cycles_engine_validate.standard_kwargs()` is now the single standard flag set; the harness calls it (checked identical to the previous inline config on Arkansas, grain 7.6106 both ways). The pages are re-synced to the new engine source but still call bare defaults until release, so "shipped" in the table above stays a documented gap, not a hidden one. Closing it means rewriting the page glue to call the standard configuration, scheduled with the release, not before.
- `build_reference.py` (setup / run / verify) downloads v1.5.20, checks the zip sha256 (8b928999...), writes inputs from committed tiles, runs, and records md5 per run in `reference_manifest.json`. The local binary matches the zip's.
- Committed scorecard JSONs live in `scorecards/`.

## Phase 2 result (2026-10-16): water state is not the lever
Daily per-layer moisture, engine (standard config, continuous run) against Cycles dailyWater, 24 fresh sites, N=150, in plant-available-water fraction. Median rms by depth: 0-0.3 m 0.23, 0.3-0.6 m 0.26, 0.6-1.0 m 0.18, below 1.0 m 0.15; bias is small (median -0.09 to +0.02). A third of layer-sites exceed 0.3 rms, concentrated in sands (Mandarin, Autryville, Grayling), where PAW is tiny and the normalization amplifies error.

Attribution: Cycles' daily layer moisture forced into the engine in every window (spin-up, season, fallow), mean abs error free -> forced, 24 sites:

| | N=0 | N=150 |
|---|---|---|
| grain (Mg/ha) | 0.38 -> 0.37 (+3%) | 1.08 -> 0.95 (+12%) |
| leaching | 0.98 -> 1.22 (-24%) | 3.98 -> 5.24 (-32%) |
| denitrification | 1.11 -> 1.02 (+8%) | 12.2 -> 12.5 (-2%) |
| volatilization | 1.85 -> 1.76 (+5%) | 6.5 -> 6.05 (+7%) |
| N2O | 0.13 -> 0.12 (+6%) | 1.70 -> 1.88 (-11%) |

Rule 2b applies (under 30% removed): water state is NOT the lever. Caveats: forcing sets moisture at end of day but the engine's own drainage flux still drives nitrate transport, which is why leaching gets worse (state and flux disagree); forcing a consistent drainage too is a follow-up, not expected to change the verdict for denitrification (-2%). REGIONAL=0 gives nearly the same errors as REGIONAL=1 on these sites (N=0 grain 0.38 vs 0.37, N=150 1.08 vs 1.03), so the regional factors currently buy only about 5% here.
Decision: go to Phase 3 (growth conversion) and the nitrogen side (Phase 4); the dominant remaining error is not water. Denitrification (MAE 12 on a mean of 15 kg N/ha) and volatilization (6.5 on 15) are the largest relative gaps and sit with the N-state, not the water state.

## Mask removal, first pass (2026-10-16): regional factors removed
94 fresh sites (never used for fitting), N=0/150/400, every second year, regional net-N multiplier and grain factor on vs off, paired bootstrap on per-site MAE:
- Grain MAE: N=0 0.47 -> 0.49 (+0.018, CI +0.005 to +0.034), N=150 0.96 -> 0.98 (+0.022, CI +0.002 to +0.042), N=400 0.66 -> 0.66 (-0.004, CI -0.033 to +0.019). Total biomass unchanged. Correlation unchanged to two decimals. Rule 4a (loss under 5%): leave off permanently. Harness default is now REGIONAL=0. The regional model explained 14% on the sites it was fitted on and about 2 to 4% on fresh sites; it was fitting site noise.
- Still masks, scheduled for Phase 5 after Phase 3: NET_GROWTH_FRACTION 1.0445 and the wheat and silage corn calibration factors; N_DEMAND_SCALE 0.75 is a measured demand ratio, not a score fit, but is on the watch list.

## Phase 4, step 1 (2026-10-16): denitrification was missing its carbon term
Method: test each engine rate law one step at a time with Cycles' own states as inputs (nlaw_data.py builds per-layer NO3, NH4, theta, soil T, drainage and fluxes for 40 sites; nlaw_denit2.py fits, held out by site). The old law (layer-1 NO3 x rel-saturation^6 x temperature) has held-out daily R2 0.01 even with Cycles' own states, so no refit of its constants could have worked. The implied daily rate has day-to-day autocorrelation 0.86 and correlates 0.47 with SOM respiration and -0.38 with total NO3, so the missing drivers are a carbon substrate and a sub-linear nitrate response. New law: d = 0.004137 x NO3^0.725 x Cresp^0.772 x rel1^6.03 (Cresp = SOM plus residue respired C, kg C/ha/day, from the six-pool state). Held-out daily R2 0.50, site-total rms log error 0.76 (was 1.10).
In the full engine on the 94 fresh sites (regional off, paired bootstrap), denitrification MAE: N=0 2.17 -> 1.59, N=150 12.6 -> 10.5, N=400 44.0 -> 34.3 (all CIs exclude zero); correlation 0.59/0.38/0.37 -> 0.71/0.63/0.68; grain, leaching, volatilization unchanged. Remaining: mean bias is -45% at N=150 and -17% at N=400 because the engine's standing nitrate pool is lower than Cycles' (a net-mineralization and N-state problem, next).

## Phase 4, step 2 (2026-10-16): carbon is right, nitrogen release is 23% short
Annual respired C and net N mineralization, engine vs Cycles, 24 fresh sites, N=150, continuous run: respired C median ratio 0.98 (site range 0.28 to 1.35, year-to-year correlation 0.70); net N mineralization median ratio 0.77 (range 0.14 to 1.35, year correlation 0.58). So the six-pool carbon state is not the problem; the N release per unit carbon is. A one-step regression with Cycles' own carbon flows (held out by site, R2 0.95) gives net N = 0.145 x SOM-respired C - 0.069 x humified C + 0.0055 x residue-respired C (kg per kg), a physically sensible set. The engine does not use those coefficients: its default path is the explicit per-pool C:N stoichiometry (SIXPOOL_ML_STOICH), so SIXPOOL_ML_N_A/B/C are inert there (checked: overriding them changes nothing, results identical to 4 decimals on 24 sites). The 23% shortfall therefore lives in the stoichiometry inputs (pool C:N ratios, humification fraction, residue C:N), not in a coefficient.
Next: log gross mineralization and immobilization from the engine and compare with Cycles' N.txt columns (Cycles: mineralization 81 to 315, immobilization -52 to -143 kg N/ha/yr), then fit the humified-fraction and residue C:N against Cycles' own pool C:N columns. Expected gain: net N ratio to about 1.0, which should lift the standing nitrate pool and with it denitrification (still -45% at N=150) and leaching.

## Phase 4, step 3 (2026-10-16): the pool-forcing diagnostic, and what it ruled out
Two forcing designs on the same 24 fresh sites (engine standard config, regional off):
1. Forcing Cycles' daily profile NO3 and NH4 STATES in every window made things much worse (N=0 grain MAE 0.40 -> 4.5; volatilization 1.9 -> 4.3). Not interpretable as "pool is not the lever": a pool is a state that already includes Cycles' own crop uptake, so overwriting it each day hands the engine's crop a constantly refilled free N supply. The design was wrong, not the engine. Hook kept (NPOOL_FORCE) with this warning.
2. Forcing the net mineralization FLUX (all windows, including fallow, now supported) is the clean test. Mean abs error free -> forced: N=0 grain 0.40 -> 0.30 (+24%), N=150 grain 1.06 -> 0.95 (+11%), leaching 3.89 -> 3.37 (+13%), denitrification 9.48 -> 9.25 (+2%), volatilization 6.51 -> 6.35 (+3%), N2O -2%. Rule: under 30% removed, so net mineralization is NOT the main lever for the N losses, and the planned gross/immobilization breakdown (step 2 of the previous message) is demoted. It would buy at most about a quarter of the N=0 grain error.
Inference to test next (from the confounded run, so a hypothesis only): with a Cycles-sized nitrate pool available the engine crop takes far more N than Cycles' crop does (+4 Mg/ha at N=0), which points at plant-side N uptake (root access, uptake rate cap, N stress response) rather than soil supply. That is the Phase 3 territory, and it is also where the remaining denitrification bias may sit (nitrate drawn down too fast by the crop).

## Phase 4, step 4 (2026-10-16): the crop-side N hypothesis is falsified for the N losses
Forced Cycles' daily plant N (total_nitrogen) and/or N stress in the growing season, 24 fresh sites, MAE free -> forced:
- N=0 grain 0.40 -> 0.26 with plant N (+36%), 0.33 with N stress (+17%); N=150 grain 1.06 -> 0.79 with N stress (+26%), worse with plant N alone (1.29).
- Leaching, denitrification, volatilization: 0% to 2% better or worse (denit 9.48 -> 9.49 at N=150).
Tally of every attribution so far for denitrification MAE at N=150: water state +/-2%, net mineralization flux +2%, crop N +/-0%, even Cycles' exact NO3 pool only +6% (8.9 vs 9.5). None of the states is the lever; the denitrification law itself is: with Cycles' own states as input it explains 50% of held-out daily variance, so half the variance is driven by something the law does not see. Volatilization and nitrification show the same signature and are the next law tests. Grain: N stress and plant N are borderline levers (17% to 36%), which belongs to Phase 3, not to the loss terms.

## Phase 4, step 5 (2026-10-16): law structure tests for denitrification, nitrification, volatilization
Method: nlaw_table.py builds a 3.8-million-row daily table (94 fresh sites x N0/150/400) of Cycles' own fluxes and the states and drivers that could explain them. nlaw_ceiling.py fits a gradient-boosted model held out by site to find the achievable ceiling and which driver groups matter; nlaw_param.py fits compact parametric laws and scores them against it.
| Law | Old held-out daily R2 | Ceiling | New parametric | Key finding |
|---|---|---|---|---|
| Nitrification | 0.26 to 0.51 | 0.90 | 0.81 (annual rms log 0.76 -> 0.29) | the implied rate is flat (about 0.1/day) while surface NO3:NH4 is below about 5 and collapses to zero past about 10 (a near step at ratio 9): nitrification stops once nitrate has built up relative to ammonium. Plus saturation in NH4 and a temperature logistic. |
| Volatilization | 0.28 | 0.74 | 0.60 | evaporative demand (ET0^1.9) and a 5-day mean wetness term (exponent -0.86) |
| Denitrification | 0.53 (respiration law) | 0.82 | 0.58 (annual rms log 0.83 -> 0.71 with profile-max saturation, clay, NH4) | wet layers below layer 1 matter, coarse soil lowers it |
Full-engine results on the 94 fresh sites (paired bootstrap, regional off): nitrification ratio law ADOPTED. Volatilization MAE N=400 17.4 -> 12.7 (CI -7.6 to -2.1), N=150 6.5 -> 5.6, correlation 0.61 -> 0.82 at N=400; denitrification 10.5 -> 10.0 at N=150, 34.3 -> 34.0 at N=400 (small, CI excludes zero); grain 0.96 -> 0.94 at N=150; leaching slightly worse at N=150 (6.69 -> 7.10, CI +0.17 to +0.67).
Tested and kept OPT-IN (mixed in the full engine on 24 sites): the evaporative-demand volatilization law (VOLAT_ET_MODEL: N=0 1.83 -> 1.69 but N=150 6.17 -> 6.73 and N=400 14.1 -> 14.9; the one-step gain does not carry because the engine's NH4 trajectory differs) and the extended denitrification law (DENITRIF_E2: N=150 bias -6.7 -> -2.4 and rms log 0.94 -> 0.76, N=400 MAE 35.7 -> 29.2, but N=0 denitrification overshoots, MAE 0.32 -> 1.08, and N=400 leaching and N2O move the wrong way).
Lesson worth keeping: a law that gains a lot in the one-step test (Cycles' states as input) can gain little or lose in the full engine, because the engine feeds the law its own states. Every law change is therefore judged in the full engine on held-out sites, never on the one-step R2 alone.

## Phase 6 baseline (2026-10-16): multi-crop on the same footing, and what it found
Method: run_validation_multisite_wheat.py. Continuous winter wheat (planted DOY 288, 90 kg N/ha UAN at DOY 75 is the Cycles sample's rate; N=0, 90, 150) on 30 fresh sites, engine standard configuration against Cycles v1.5.20 on identical tile inputs. Each engine run is reported with its calibration_factor and with it forced to 1.0.
- Soybean, 94 fresh sites, N=0 (cached references): grain Cycles mean 3.16, MAE 0.39 (12%), bias -0.10, corr 0.84; biomass MAE 13%. Corn at N=150 is 13%. These two are genuinely at the same level; the gap is the other crops.
- Wheat first run: MAE 58% to 64% of the Cycles mean at every N, correlation 0.1 to 0.34. Calibration on or off made no difference (raw vs calibrated within a few percent), so this is mechanism, not a mask.
- Finding 1 (fixed): the winterkill rule used air minimum temperature (-25 C). In Cycles' own output (10 sites, 340 winters, 7 kills) stands die only when top-layer SOIL temperature falls below about -25 C (killed: -27.4 to -25.2; survivors never below -24.9) and survive air nights of -40 C. The air rule killed 190 of 333 surviving winters. The engine now applies the same -25 to its own layer-1 soil temperature (lag filter, correlation 0.96 with Cycles' winter soil minimum, bias -1.5 C): 27 false kills of 333 and 5 of 7 real kills caught. Wheat error 58-64% -> 39-48%, corr 0.1-0.3 -> 0.3-0.4. Sites at 37 to 45 N now track well (corr 0.7 to 0.86 at many).
- Finding 2 (open, the next mechanism): south of about 35 N the engine's wheat matures in about 140 days against Cycles' 224 (and 237 vs 263 even in Iowa), so it ends the season far too early (Florida 3.5 vs 8.4 Mg/ha, Texas 2.0 vs 5.8). The crop file discloses a vernalization requirement (THERMAL_TIME_VERNALIZATION 230, thresholds -4 / 1.5 / 15 C, devernalization above 27 C), photoperiod bounds 8 to 18 h, THERMAL_TIME_FLOWERING_AT_PMAX 340 and THERMAL_TIME_GRAIN_FILLING 500. Cycles' own daily output shows the mechanism: vernalization accumulates (232.5 by 30 January at a Texas site) and thermal time keeps accumulating through winter (TT 2108 when the reproductive stage starts in April), so flowering is gated by vernalization completion plus photoperiod-scaled thermal time, not by the nominal FLOWERING_TT 1250. The engine's single-threshold phenology cannot produce this.
Next: implement vernalization and photoperiod phenology from the disclosed crop-file parameters, fitting only the undisclosed functional forms from Cycles' daily output (stage-onset dates across many sites), then re-score wheat with calibration forced to 1.0.

## Crop-file audit (2026-10-16): the unused fields are the missing mechanisms
Read all 44 crops in GenericCrops.crop and counted which fields carry real values (not -999) per crop, then grepped the engine for each. Two groups of fields are present in the file and absent from the engine:
1. Winter-crop phenology, 12 fields, real values for only WinterWheat, WinterBarley, WinterRye and Pennycress (the other 40 crops use the simple FLOWERING_TT / MATURITY_TT model): PHOTOPERIOD_MIN/MAX (8, 18 h), THERMAL_TIME_VERNALIZATION (230), VERNALIZATION thresholds LOWER/OPTIMAL/UPPER (-4, 1.5, 15 C), DEVERNALIZATION_TEMPERATURE (27 C), THERMAL_TIME_FLOWERING_AT_PMAX (340), THERMAL_TIME_GRAIN_FILLING (500), TEMPERATURE_POST_FLOWERING LOWER/OPTIMAL/UPPER (7, 20, 35 C). Zero references in the engine.
   Check against Cycles' own daily output (Texas site, 8 winters): between vernalization complete and the reproductive stage, thermal time accumulates 842 unweighted, but weighted by a linear photoperiod factor (P - 8)/(18 - 8), with P the day length including twilight, it is 279 (P = geometric day length) to 359 (6 degree twilight), against the disclosed 340 (CV 8 to 9%). So flowering = vernalization complete, then photoperiod-weighted thermal time reaching 340; then 500 thermal time of grain filling with the post-flowering temperature response. Almost nothing to fit.
2. Grain and straw nitrogen, 5 fields, 14 of 44 crops: N_MAX/MIN_CONCENTRATION_GRAIN, N_MAX/MIN_CONCENTRATION_STRAW, N_PARTITIONING_FACTOR (wheat 0.73, corn -0.12). The engine uses only a whole-plant dilution curve, so grain N demand, removal in harvest and remobilization are not modeled; plausibly part of the N=0 yield error (forcing N stress removed 17 to 36% of it).
Conclusion: the crop file is a complete spec and the engine reads less than half of it. Order of work: (1) winter phenology (fixes wheat, and three other crops for free), (2) grain/straw N, (3) re-run the same audit on the remaining shared fields (KC, HARVEST_INDEX_SLOPE_MULTIPLIER).

## Phase 6, step 2 (2026-10-16): winter wheat phenology implemented
Engine: crop["vern"] (WINTER_PHENOLOGY) switches a crop to the disclosed winter model: vernalization accumulates until 230; then thermal time weighted by a linear photoperiod factor (day length with a 4.6 degree twilight allowance, 8 to 18 h) accumulates to 340 = flowering; then 500 thermal time of grain filling with the 7/20/35 C post-flowering response, which also sets the development clock that drives canopy senescence, partitioning and harvest. Plus a post-flowering temperature factor on growth (1.0 up to 20 C, falling to 0 at 35 C). Crops without the key are byte-identical to before.
What was disclosed and what was fitted: disclosed = 230, 8/18 h, 340, 500, 7/20/35, base temperature 2. Fitted from Cycles' own output (not in any source): the vernalization increment (K = 10.0 times a tent of daily mean temperature, L = -4.5, O = 7.8, U = 15.9, corr 0.99; the fitted optimum differs from the file's 1.5 C) and the twilight allowance (4.6 degrees, between the 279 and 359 that 0 and 6 degrees give against 340).
Result, 30 fresh sites, season length: engine 229 / 230 / 221 / 261 days against Cycles 224 / 223 / 224 / 263 (before: 140 / 139 / 141 / 237).
Wheat error as a share of the Cycles mean (grain, calibration forced to 1.0): original air-temperature winterkill 58 to 64% -> soil-temperature winterkill 39 to 48% -> + vernalization 35 to 44% -> + post-flowering temperature factor 35 to 40%; bias is now near zero (N=150 grain -0.38, biomass -0.02). Where the remaining error lives: across-site means are good (site-mean error 24 to 27%, across-site correlation 0.97 at N=0 and 0.84 at N=150) but WITHIN-site year-to-year tracking is weak (mean correlation 0.43), the same signature as the earlier finding that wheat yield tracks nitrogen stress (-0.89 in Cycles). North of 44 N the engine is 33% low, south of 36 N 17% high.
Next: grain and straw nitrogen (N_MAX/MIN_CONCENTRATION_GRAIN/STRAW, N_PARTITIONING_FACTOR), the second unused group, since year-to-year wheat yield is an N-supply and N-demand story. Then the same harness for sorghum and a cover crop.
