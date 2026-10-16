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

## Input audit, weather (2026-10-16): the engine's VPD was the wrong quantity
Checked every weather-derived quantity against Cycles' own dailyEnviron at 32 sites (10 years each). Reference ET: ratio 1.002 (sd 0.001), daily correlation 1.000 at every site, so ET0, radiation, wind and humidity handling are exact. Vapor pressure deficit is not: the engine's FAO-56 mean-es-less-ea is 15% below Cycles' reported column (ratio 0.853, sd 0.05). Cycles' VPD is exactly max(0.2, 0.66 x es(Tmax) x (1 - RHmin/100)) kPa: the ratio to 0.66 es(Tmax)(1-RHmin) has zero spread for Tmax above 22 C, and the 0.2 kPa floor accounts for every cold or humid-day deviation (3,297 days at exactly 0.2). Implied transpiration-use efficiency from Cycles' own unstressed days also sits closer to the file's 8.7 g/kg with this definition (90th percentile 8.33 vs 7.8).
Consequence: three fitted terms existed only to compensate (C1_VPD_POW 0.670 instead of the paper's 0.5, the heat penalty HEAT_A, and the growth conversion that went with them). With the exact VPD, exponent 0.5 and no heat term, correlations are identical on 24 fresh sites (grain 0.89 / 0.74 / 0.89 at N = 0 / 150 / 400) and one global level constant (NET_GROWTH_FRACTION 0.955) reproduces the old accuracy: N=150 grain MAE 1.02 vs 1.04, bias -0.01 vs -0.26; N=400 0.88 vs 0.80. Soybean (94 sites) 12% -> 13% grain error with bias -0.10 -> -0.03; wheat unchanged; pattern suite unchanged. Net effect: no accuracy change, three fitted terms removed, one definition made exact. Adopted (VPD_CYCLES_EXACT = True).
Open weather items found: ALTITUDE is written as 0 for every tile site because the tiles carry no elevation, so the pressure and clear-sky radiation terms are those of sea level at every site (Cycles and the engine agree because both are told 0; reality differs, up to 12% in pressure in the West). Precipitation, temperature, solar, humidity and wind are used as given.

## Input audit, soil (2026-10-16): one-factor-at-a-time in Cycles at 3 sites (Florida, Illinois, North Dakota), corn N=150
| Soil input changed | Effect on grain, N losses | Engine |
|---|---|---|
| pH 4.5 / 8.5 (we write 6.5 everywhere) | none, identical to 2 decimals | not used (correct) |
| ROCK 0.15 (we write 0) | none | not used (correct) |
| SLOPE 5 (we write 0) | none (denit 24.72 -> 24.72) | runoff slope term exists; no effect either way |
| CURVE_NUMBER 85 (we write 75) | grain -0.3 to -0.8, leaching down 7 to 45%, volatilization +6 to +25% | uses CN, fixed 75 (matches the reference) |
| BYP_H 0.5 / BYP_V 0.5 (we write 0) | large: leaching moves into a separate "bypass" flux (71 -> 0.9 leach + 69 bypass at the Florida site), denitrification -35 to -63%, N2O -20 to -63%, grain -1.5 Mg/ha at North Dakota | NOT modeled |
Findings: (1) the pH-driven volatilization option (soil_ph, Macnack et al.) is not a Cycles feature: v1.5.20 reads pH and ignores it; (2) rock fragments are ignored by Cycles as well; (3) preferential flow (BYP_H, BYP_V) is the one soil input with a large effect that the engine lacks, but the reference runs have it at 0, so it explains none of today's gaps; it only matters for real fields, and STATSGO2 does not provide it; (4) curve number matters and a real-site engine should take it from the hydrologic soil group (STATSGO2 has it), not a flat 75.
So the soil file holds no further clue for matching the current reference. The unexplained errors are not caused by a soil input the engine ignores.
Summary of the three-input audit: crops = two unused field groups (winter phenology: now implemented; grain/straw N: open); weather = VPD definition (fixed), altitude missing; soil = nothing to match, three real-site inputs (curve number, bypass flow, elevation) for the reality target. Not yet audited: the operation and control files (planting window conditions MIN_SMC and MIN_SOIL_TEMP, CLIPPING, DENSITY, residue fields, HYDROLOGY_OPTION).

## Input audit, operation, control and nudge files (2026-10-16)
Operation file, one factor at a time in Cycles, 3 sites (FL, IL, ND), corn N=150, base -> changed:
- STANDING_RESIDUE_AT_HARVEST 50 -> 0 / 100 (the share of stover left standing instead of flat): denitrification 5.4 -> 7.4 / 3.7, volatilization 60 -> 51 / 75, leaching 71 -> 81 / 57 (Florida); North Dakota grain 6.68 -> 7.87 / 5.93. RESIDUE_REMOVED 0 -> 80: denitrification -65% (FL), -63% (ND), grain -17% (ND). The engine has one lumped residue pool (cra), no standing/flat split and no removal fraction, so a management input that moves N losses by 15 to 65% is invisible to it.
- DENSITY 0.7 / 1.5: grain -5 to -8% / +4 to +6%, denitrification +40% / -34% (IL). The engine has Eq. 7 (plant_density_factor) and leaves it at 1.
- MIN_SMC 0.15: no effect. MIN_SOIL_TEMP 8 (from 12): grain +0.07 to +0.13 (earlier planting). Moldboard tillage: grain -0.15 to -0.7, volatilization +4 to +32%.
Control file: HYDROLOGY_OPTION 1, AUTOMATIC_NITROGEN 0, ADJUSTED_YIELDS 0, CO2 from co2.txt (the engine uses the same annual CO2). Nothing the engine ignores that matters for the reference.
Nudge file (ContinuousCorn.nudge) exposes Cycles' internal structure through its parameter names and comments, none of it used so far:
- KD_NO3 = 0.0 and KD_NH4 = 5.6 cm3/g: linear adsorption coefficients; ammonium is mostly sorbed (so non-leachable, as the output shows) and only the dissolved fraction is available.
- POT_DENITRIF_RATE and DENITRIF_HALF_RATE ("half saturation constant for denitrification"): denitrification is a potential rate times a hyperbolic nitrate term, consistent with the sub-linear nitrate exponent (0.4 to 0.7) fitted from Cycles' output; it should be applied per layer on concentrations.
- DECOMP_HALF_RESP ("half response to saturation, default 0.22") and DECOMP_RESP_POWER ("exponential response to saturation, default 3.0"): the decomposition moisture function. A first test against the reported composite factor (layer 1, binned by saturation and temperature) shows a large spread at fixed values, so the form is not a function of layer-1 saturation and temperature alone; unresolved.
- SOC_HUMIF_POWER (humification exponent), NITRIF_RATE, ROOT_PROGRESSION (rooting depth progression), RADIATION_USE_EFFICIENCY multipliers: confirm these processes are separate parameterized terms.
Summary of the full input audit: crop file (two unused groups), weather (VPD fixed), soil (nothing), operation (standing/flat residue and removal are large and unmodeled; density available but unused), nudge (denitrification, adsorption, decomposition-moisture structure disclosed by the parameter names).

## Residue A/B test (2026-10-16): the residue split is not the main driver of the current N-loss gap
Argument checked before building: the engine lumps all stover as flat residue, equivalent to Cycles with STANDING_RESIDUE_AT_HARVEST = 0. Re-ran the Cycles reference at 0% standing on the 24 fresh sites (N=150) and scored the SAME engine against both references (a mechanism that mattered would shrink the error against the matching reference):
| N=150 | Cycles 50% standing (default) | Cycles 0% standing | Engine | Engine MAE vs default | vs 0% standing |
|---|---|---|---|---|---|
| grain | 7.14 | 7.30 | 7.03 | 0.99 | 1.05 (worse) |
| denitrification | 15.18 | 17.65 | 7.93 | 9.13 | 11.27 (worse) |
| leaching | 5.73 | 6.93 | 5.75 | 4.61 | 4.73 (worse) |
| volatilization | 15.37 | 12.56 | 11.38 | 5.94 | 4.41 (26% better) |
| N2O | 2.86 | 3.01 | 1.94 | 1.61 | 1.63 (same) |
Only volatilization improves, by 26%; every other term gets slightly worse. The standing/flat split would be worth building for management realism (a user who varies residue removal) and perhaps 25% of volatilization error, but it is not where the engine's current gap lives. The largest remaining relative gap is denitrification: the engine produces 7.9 kg N/ha against Cycles' 15.2 (-48%).
Lesson: a large sensitivity of the reference to an input does not show that the engine's error comes from ignoring it, because the reference and the engine were run at the same default. The test that matters is whether re-referencing to the engine's implicit assumption removes error.

## Denitrification source sweep (2026-10-16): what the sources say
Sources read for the first time: the official Cycles user guide (github.com/PSUmodeling/Cycles, master branch docs/index.md, input.md, output.md; reachable by git clone and raw.githubusercontent.com, previously believed unreachable), the paper's text around the soil water and limitations sections, the SI, the nudge file. Findings:
1. HYDROLOGY_OPTION (input.md): 0 = daily cascade, 1 = hourly finite-difference integration, 2 = Crank-Nicolson sub-daily, 3 = CVode sub-daily. "The cascade method ... does not allow for water contents greater than field capacity or soil wetting from the bottom up. Cascade method can miss denitrification badly, but does a good job with the water balance." Our reference runs use option 1.
2. Measured (24 fresh sites, corn N=150, Cycles v1.5.20, same inputs): denitrification option 0 = 5.7, option 2 = 8.2, option 1 = 15.1 kg N/ha; leaching 12.1 / 9.1 / 5.7; N2O 1.5 / 1.9 / 2.8; grain 7.07 / 7.27 / 7.14. The engine (denitrification 7.9, leaching 5.75, grain 7.03) reproduces option 1's water balance and leaching but its denitrification sits at the cascade/option 2 level. So the denitrification gap is a sub-daily saturation effect: Cycles denitrifies during the hours a layer is saturated after rain, and an end-of-day state cannot see that. This also explains why no daily state (water, N pool, crop N) removed more than 6% of the error.
3. Paper (p.12): "Air-filled porosity is used in Cycles as a surrogate for oxygen availability." Tested as a law input (absolute layer-1 air-filled porosity, 5-day mean, profile minimum, threshold forms): held-out daily R2 0.41 to 0.59 against 0.57 for the current relative-saturation form; site-total rms log error worse (0.93 to 1.12 vs 0.83). Falsified at the daily-state level: do not repeat.
4. Paper Table 1: maximum denitrification rate knd in kg kg-1 d-1, "N removed from NO3 pool, kg kg-1 soil": a concentration-based rate. Nudge file: POT_DENITRIF_RATE and DENITRIF_HALF_RATE (half-saturation constant). Output definitions: composite_factor is "a function of temperature, moisture, and aeration".
5. SI, C-Farm papers, CropSyst papers: no denitrification equation (the SI has none).
Conclusion: the missing piece for denitrification is sub-daily saturation. The engine already integrates water at 24 sub-steps per day inside redistribute(); it just discards the within-day trajectory. Next step (a different kind from the last two law tests): expose the hourly layer saturation from the engine's own redistribution, apply the denitrification law at the sub-daily step (potential rate x hyperbolic nitrate x saturation response x carbon), and fit its few parameters in the full engine to Cycles' annual and daily totals on training sites, judged on held-out sites. Expected: denitrification bias from -48% toward 0; contingency: if the engine's own sub-daily saturation is too low (layers rarely saturate in its cascade), the water redistribution needs the hourly finite-difference treatment (option 1) rather than the cascade, a larger rebuild.

## 2026-10-16 user guide audit (step 2), harvest index law

Sources checked: Cycles docs (input.md, output.md, index.md, roar.md, bug_report.md), Cycles-utils defaults, crop files. Findings: the guide documents the harvest index law HI = Hmax - (Hmax-Hmin) exp(-Hk fG) with Hk = m(1-Hmin)/(Hmax-Hmin) (corn 0.8/0.15/1.3077, soybean 0.4/0.15/3.4, wheat 0.52/0.2/2.5), a graded cold damage law (1 - fc^3 on biomass and interception, delays phenology), a pasture clipping rule, and developer input defaults (curve number by hydrologic soil group, elevation, slope, bypass flow 0). Elevation, slope and bypass are not modeled for real fields.

Harvest index test (documented vs our fitted constants, same sites):
- corn, 24 fresh sites: N=150 grain MAE 1.03 vs 1.02, corr 0.74 both, bias -0.18 vs -0.10. Equivalent.
- soybean, 94 fresh sites, N=0: MAE 0.42 vs 0.41, corr 0.85 both. Equivalent.
- wheat, 30 sites, raw (factor 1.0): documented Hk 2.5 is WORSE (N=0 MAE 0.56 vs 0.41, N=150 1.70 vs 1.59); it removes a compensating bias, so wheat keeps its fitted value until the wheat N mechanism is fixed.
Decision: corn and soybean now use the documented constants (sourced, not fitted, no accuracy cost). Wheat unchanged. Cold damage law and pasture rule still to implement and score.

## 2026-10-16 step 1: sub-daily denitrification (adopted, default on)

Sources: Cycles guide (HYDROLOGY_OPTION semantics, denitrification in hours of saturation), the 2026-10-16 hydrology option finding (opt0 5.7 vs opt1 15.1 kg N/ha), the engine's own adaptive Eq. 1-2 redistribution.
Measurement: the engine's own redistribution steps already carry within-day saturation. Time-weighted layer-1 rel^6 over a day exceeds the end-of-day value by 1.0x to 2.75x depending on site (sandy sites most).
Change: redistribute() now returns, via _SUBDAY_REL1_EFF, the time-weighted (trapezoid over the adaptive steps) layer-1 saturation, in the same power as the denitrification law; denitrification_flux_resp reads it (SUBDAY_DENIT=True). No new parameter, no refit.
Results at N=150 (denitrification vs Cycles annualN):
- fit sites (24): rms log error 0.93 -> 0.65, model/real mean 0.54 -> 0.75
- held-out sites (24 disjoint fresh94): rms log 0.82 -> 0.62, ratio 1.09. Grain MAE 0.882 -> 0.875, leaching 0.49 -> 0.46 on fit sites. Yield neutral.
- Refitting K (x1.4) fixed the fit sites (0.55, ratio 0.94) but overshot held-out (0.68, ratio 1.38), so K is left at the one-step value.

## 2026-10-16 wheat: attribution rerun and the canopy clock (graded cold damage and grain/straw N not yet tested)

Sources checked: Cycles guide (cold damage, crop group 2 fields), GenericCrops.crop WinterWheat entry, Cycles daily wheat output (canopy, thermal time, vernalization, N stress, plant N), the engine's own daily history, prior wheat scorecards. Not checked this turn: SI/paper (no new wheat text expected), Cycles one-factor runs.

wheat_attrib.py fixed (it now writes the input and operation files) and rerun on 16 fresh sites (scorecards/wheat_attrib_2026-10-16.json). Within-site yearly error and correlation:
- N=0: free 0.41 MAE / corr 0.44; force Cycles canopy 0.27 / 0.59 (removes 33%); force N stress alone 0.63 / 0.55 (worse); force all three 0.24 / 0.79.
- N=150: free 1.61 / 0.35; force canopy 1.24 / 0.64 (removes 23%); force N stress alone worse; force all 1.04 / 0.78.
So wheat's year-to-year error lives in the canopy, and the N stress only helps once the canopy is right.

Canopy diagnosis (site f018, 1995; monthly rms of engine minus Cycles canopy is 0.14 in Jan rising to 0.34 in May at 6 sites): with the canopy clock unthrottled (N stress, water and N clock forced to 1) the engine canopy matches Cycles in the rise to three decimals (0.121 vs 0.121 at tt 350, 0.268 vs 0.270 at 439), then runs high at the plateau (0.97 vs 0.857; Cycles wheat peaks near 0.86, no crop-file field explains that). In the full engine the clock is slowed by nstress^3.25 (a corn fit): engine N stress sits near 0.33 all winter while Cycles reports 0, at the same plant N concentration (about 3%) and the same fall mineral N (about 5 kg/ha).
- Cycles wheat stress vs total-plant N ratio over the critical curve: median 0 above ratio 0.4, 60% at 0.3, 81% at 0.25. The engine rule (zero stress at 0.86, from corn) is far more aggressive.
Full-engine tests on 30 sites, raw (factor 1.0), which all FAILED to improve and were not adopted:
- zero-stress ratio 0.5 / full 0.2: N=150 MAE 1.59 -> 2.01, corr 0.43 -> 0.34
- zero 0.45 / full 0.15: worse again
- eix 0.86 for wheat: N=150 bias -0.57 -> -0.98, corr unchanged
- eix 0.86 plus the relaxed rule: N=150 MAE 1.91, corr 0.33
- AG-basis stress rule (N_STRESS_AG_BASIS): N=150 MAE 1.77, corr 0.36
Also tested earlier today: documented harvest-index slope for wheat (worse). Lesson for rule 6: the one-step Cycles stress curve for wheat is real, but dropping it into the engine makes wheat worse, so the stress rule is not the lever; some other state compensates.
Next (ranked, recommendation first): (1) force Cycles' clock rates (nclock, wclock hooks exist) and eix separately to learn which canopy sub-state carries the 0.6 -> 0.78 correlation; (2) test the graded cold-damage law on the canopy (Cycles wheat shows KILLED_COLD_DAMAGE stages and a Jan-Mar canopy the engine undershoots); (3) grain/straw N only after the canopy is understood.

## 2026-10-16 hydrology option audit (scorecards/2026-10-16_hydrology_option_24sites.json, 2026-10-16_hydro_audit_yearly.json; script hydro_audit.py)

Sources: Cycles guide (HYDROLOGY_OPTION 0 cascade, 1 hourly finite difference = the reference, "cascade can miss denitrification badly but does a good job with the water balance"), Cycles v1.5.20 runs at options 0, 1, 2 on the same tile inputs (corn N=150), the engine in its standard configuration (sub-daily denitrification on).
Site means (24 fresh sites), option 0 vs option 1: grain 7.07 vs 7.14 (site corr 0.96); leaching 12.1 vs 5.7 (2.1x); denitrification 5.7 vs 15.1 (0.38x); N2O 1.5 vs 2.8; volatilization 14.1 vs 15.4 (-9%). Option 2 sits between (leaching 9.1, denitrification 8.2).
Within-site yearly correlation, 12 fresh sites, 37 years:
- grain: engine~opt1 0.72, engine~opt0 0.71, opt0~opt1 0.80 (the option barely matters for yield)
- leaching: engine~opt1 0.69, engine~opt0 0.46, opt0~opt1 0.57
- denitrification: 0.51, 0.41, 0.83
- volatilization: 0.63, 0.64, 0.89
- N2O: 0.21, 0.19, 0.65
Means on these 12 sites (engine / opt1): leaching 7.0 / 8.7, denitrification 11.0 / 16.4, volatilization 9.9 / 13.9, N2O 1.8 / 2.9.
Conclusions: (1) the option matters only for the water-driven N losses (denitrification, leaching, N2O), not for yield or volatilization, so the reference convention is settled: the engine tracks option 1 better than option 0 for leaching and denitrification. (2) Volatilization is insensitive to hydrology, so its 0.71 level gap and 0.63 yearly agreement come from the NH4 pool or its rate law, not water. (3) N2O yearly agreement (0.21) is the weakest, and is far below what the option difference alone explains (0.65). (4) Denitrification yearly agreement (0.51) is still well below the 0.83 that two Cycles water schemes achieve with each other, so there is room.
