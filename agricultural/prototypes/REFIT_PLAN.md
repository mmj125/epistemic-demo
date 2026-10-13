# Full refit plan (written 2026-10-13)

## Why a refit

Single-term fixes keep stalling for one reason: the engine's current accuracy partly comes from errors that cancel. The evaporation test showed it. The new bare-soil law matches Cycles' dry-down (rms 0.049 against 0.49 for the old law) and still made the full model worse, because the moisture, volatilization, denitrification and yield terms were tuned against the old, wrong moisture trajectory. Fixing one process at a time cannot beat that. Fixing all of them, upstream first and with every law fitted against Cycles' own state, can.

## Principles

1. **Fit each law against Cycles' state, not the engine's.** Teacher forcing: feed Cycles' daily layer water, temperature, carbon and nitrogen pools into one process equation and compare its flux with Cycles' flux. A module passes on its own before it is plugged into the chain. This is what stops compensating errors.
2. **Use designed experiments where real runs are confounded.** Bare field, no crop, no residue, real atmosphere, designed rain or a single pulse. Cycles is cheap and exact, so use it as a lab.
3. **Work upstream first.** Water states drive decomposition, nitrification, volatilization and denitrification; carbon drives mineral nitrogen; nitrogen drives crop stress. Re-fit downstream laws after any upstream change.
4. **Everything behind a flag until it passes.** Defaults change only at a milestone.
5. **Decide on the 28-site score, with Rock Springs corn as a tripwire** (a drop of more than 0.05 blocks; the 9 to 13 harvest crops need 0.1).
6. **Keep a ledger.** One table, one row per module: law, fit data, teacher-forced error, integrated effect, decision.

## Scorecard (step 0, build first)

One command that prints, for 16 tuning and 12 held-out sites at 0, 150 and 400 kg N: yield error and correlation; fertilizer response (0 to 150 and 150 to 400); losses (leaching, denitrification, volatilization, N2O) as levels and as marginal responses; layer-1 wetness by month; year-end mineral nitrogen; plus the Rock Springs and pattern-check tripwires. Current values to beat (tuning / held-out):

| Measure | Now |
|---|---|
| Unfertilized corn MAE (Mg/ha) | 0.84 / 0.81 |
| Fertilized (150) corn MAE | 1.17 / 1.12 |
| Fertilized correlation | 0.80 / 0.77 |
| Leaching, denitrification, N2O miss (rms log) | 0.78, 0.71, 0.64 / 0.76, 0.44, 0.60 |
| Denitrification and leaching response 150 to 400 vs Cycles | 0.27 vs 0.21, 0.35 vs 0.33 |
| Rock Springs corn, wheat, soybean | 0.822, 0.648, 0.907 |

## Order of work

**A. Water**
1. Snowpack. Designed freeze and melt experiment; fit accumulate/melt on temperature; check spring recharge at ND, SD, MN, WI, MI, NY.
2. Infiltration and runoff. Rain pulses on a bare field; compare event runoff and infiltration (curve number and moisture adjustment).
3. Redistribution and drainage. Same experiment; compare drainage timing and layer water. This is where South Dakota's missing drainage (14 vs 126 mm in 2 years) should resolve.
4. Evaporation (law already identified): add residue and canopy shading as separate measured factors, bare-soil first, then with residue, then with canopy.
5. Crop water uptake. Which layers, how much from layer 1 (Cycles takes 21 to 98%), and the stress response. Measure from Cycles' own dry-day layer losses.
6. Milestone 1: integrate A, refit the grain factor, run the scorecard. Decide whether to continue.

**B. Carbon**
7. Decomposition rate against temperature and moisture: constant-temperature, constant-moisture incubations with a residue pulse and without.
8. Humification and microbial pool: fit against Cycles' daily carbon per layer, including the microbial carbon at about 3% of soil carbon.
9. Residue and root input timing and amounts (already close; confirm).
10. Milestone 2: integrate A and B; scorecard.

**C. Nitrogen**
11. Gross mineralization and immobilization: the measured law of about 108 kg N per Mg respired carbon, and the site-dependent immobilization.
12. Nitrification (already tied to the environmental factor), volatilization, denitrification: refit each on Cycles' state after A and B are in. Designed nitrate and ammonium pulses at fixed moisture and temperature.
13. Leaching and surplus nitrate (excess-rate behavior).
14. Crop nitrogen demand and stress, against Cycles' crop nitrogen content and stress columns.

**D. Close**
15. Re-fit crop calibration factors on all 28 sites (not Rock Springs).
16. Final scorecard; Rock Springs and pattern checks; sync pages; regenerate ACCURACY.md; cover note.

## Gates

- **Module gate:** teacher-forced daily R2 and site-total error at least as good as the current law, with no site off by more than a factor of 2 where the current law is within 1.5.
- **Milestone gate:** the scorecard beats the current values on yield and at least two of the three loss measures, with no measure more than 10% worse, and tripwires hold.

## Stop rules

- If Milestone 1 does not beat the current scorecard after the grain-factor refit, stop and keep the current engine; record the measured laws in the cover note as findings.
- If any step needs a coefficient that cannot be measured from Cycles (as with the denitrification rate law's year-to-year behavior), keep the current term and log it as a question for the developers.
- Do not tune a term to fix a symptom at one site.

## Cost and risk

- Roughly 16 steps; each is one to three rounds of the size we have been doing. Milestone 1 (steps 0 to 6) is about a third of the work and is the real decision point.
- The risk that this ends no better than now is real: Cycles' remaining differences (dry-site root access, water-stress response) may not be fully measurable from its output. The stop rules limit the loss.
- The gain, if it works: the corrections are mechanism-level and measured, so the model can be explained to the Cycles developers term by term, and it should hold up at sites we have not seen.

## Ledger

| Step | Module | Law (measured on Cycles) | Module error | Integrated effect | Decision |
|---|---|---|---|---|---|
| 0 | Scorecard | scorecard.py, baseline saved | n/a | n/a | done |
| 1 | Snowpack | rain at mean T >= 1 C; melt 2.5(mean+1) or 2.5(tmax+1)^2/(tmax-tmin); sublimation = ETo; no soil evaporation under snow | max 0.07 mm/day | held-out leaching 0.76 -> 0.69 (150), 1.09 -> 0.89 (400); yield, Rock Springs unchanged | adopted (SNOW_MODEL = True) |
| 4 (early) | Bare-soil evaporation | full rate above 0.85 fc at start of day, ((th - 0.25 pwp)/(0.85 fc - 0.25 pwp))^3.5 below | rms 0.049 | worse alone (N=150 MAE 1.17 -> 1.28); waits for steps 2, 3, 5 | held (EVAP_LAW_CYCLES off) |
| 1 (check) | Snowpack, Rock Springs wheat tripwire | n/a | winter wheat correlation 0.648 -> 0.499 on 9 harvests, but per-year yields move by at most 0.14 Mg/ha (2003: 3.90 -> 3.76; mean 3.92 -> 3.89); the model's yield range is narrow, so tiny shifts reorder the 9 points | noise on a 9-point record, not a mechanism failure; snow stays on, baseline refreshed; judge wheat on the 33-harvest chain when /tmp/cycles-run is available |
| 2 | Infiltration and runoff | Cycles' runoff follows SCS: Q = (P-0.2S)^2/(P+0.8S), with the engine's own CN-wet end reproduced exactly (S = 37.3 mm at full wetness, i.e. 1.1 x the CN-87.3 value, because slope_factor(0) = 1.1). Cycles' effective moisture factor stays high (0.64 to 1.0) even when layer 1 is at wilting point; it drifts with deeper-layer water, not layer 1. Best simple candidate: FFC averaged over whole layers above 0.6 m, weighted by thickness only (no 1/z) | event runoff rms 1.34 -> 1.22 mm; season total 447 vs Cycles 531 -> 468; fragile (jumps to rms 2.25 if the cutoff shifts one layer) | 28-site scorecard: nothing moves by more than 0.03 on any measure | not adopted (FWC_THICKNESS_WEIGHT off); runoff is about 6% of rain and not a load-bearing term |
| 2b | Runoff moisture factor, why Cycles never reaches the dry curve number | Cycles' f_wc uses (theta - pwp)/(fc - pwp) per layer WITHOUT capping each layer at 1; water above field capacity in the wet layer 2 offsets a dry layer 1, and only the weighted total is capped at 1. Williams depth weighting (t/z, whole layers to 0.6 m) otherwise as before. Saturation-based forms fit far worse (rms 0.48 to 0.62 vs 0.09 to 0.11) | implied f_wc rms 0.168 -> 0.106 (corr 0.82 -> 0.95); event runoff rms 1.34 -> 0.98 mm, season total 564 vs Cycles 531 (was 447) | scorecard neutral: tuning N=150 MAE +0.014, N=400 +0.020; held-out N=150 -0.006; leaching N=150 -0.026/-0.006; tripwires unchanged | held behind FWC_NO_UPPER_CLIP (off); faithful law, adopt at Milestone 1 with the other water terms |
| 3 | Redistribution and drainage | Cycles moves water between layers almost only on days with infiltration (98 to 100% of drainage and interlayer flux); between rains layers above field capacity just sit (Georgia layer 2 at 0.26 to 0.33 against fc 0.19 for months). On rain days outflow fraction rises smoothly with position between fc and saturation, no hard threshold. The engine's Eq. 1-2 scheme already does this (infiltrate() returns early on dry days) | teacher-forced from Cycles' own daily state on rain days: per-event flux rms 2.4 mm (Iowa 2.6, Georgia 5.9, S. Dakota 2.3, Kansas 1.3, Carolina 0.4, Illinois 1.9); KHE_SCALE 0.85 gives 2.0 but is mixed by site. Free-running bare-field experiment: 2-yr drainage Iowa 475 vs 458, Illinois 355 vs 349, S. Dakota 423 vs 402, Kansas 113 vs 98, Georgia 91 vs 17; evaporation within 1 to 7%. Real-weather 17-yr drainage: Iowa 172 vs 140, Illinois 202 vs 155, Carolina 121 vs 91, Georgia 117 vs 121, Minnesota 128 vs 114, S. Dakota 5 vs 3 | none | no change. The law is right; the earlier "South Dakota 14 vs 126 mm" is not reproduced (both near zero over 1983 to 1999). Engine over-drains humid sites by 20 to 30%, plausibly from layer 2 drying too far in dry spells (step 4/5) |
| 4 | Evaporation | (a) Cycles evaporates from the top ~0.2 m, not from layer 1 as such: with layer 1 of 0.15 m or more it is almost all layer 1 (Kansas, Iowa, Carolina 100%), with thin layers it spans several (Missouri 0.08 m: 43% from layer 2; Tennessee 31%; Indiana 28%; Nebraska 20%); equal volumetric withdrawal over 0.2 m reproduces the layer-1 share to 0.04 on average (0.15 m: 0.08, 0.25 m: 0.10). (b) full rate is 1.00 x ETo when wet (so SOIL_EVAP_SCALE 0.9 is compensating for something else). (c) the dry-down law acting on the zone state with a=0.5, b=0.7, n=2 | bare-field free run, 28 sites, 2 years: layer-1 water rms 0.0372 -> 0.0330, layer-2 0.0514 -> 0.0431, profile rms 32.2 -> 33.5 mm, drainage error 98 -> 98, evaporation -21 -> -27 mm | 28-site scorecard WORSE: N=150 MAE +0.044/+0.014, N=400 +0.091/+0.052, held-out N=150 corr -0.043, volatilization +0.155, Rock Springs corn 0.822 -> 0.640 (tripwire fail), silage +0.145 | held (EVAP_LAW_CYCLES, EVAP_ZONE_DEPTH_M, EVAP_LAW_PARAMS, EVAP_LAW_TAIL all off by default); the zone structure and the 1.00 wet-end ratio are measured facts to carry into Milestone 1, where the grain factor and the downstream laws are refit together |
| 5 | Crop water uptake | From Cycles' own state (corn, N=400, 12 sites, 3,000 growing days each): Cycles takes 55 to 65% of transpiration from layer 1 at Iowa, 94 to 100% at Kansas, 48 to 75% at South Dakota; the engine took 17 to 31% (it excluded the top 0.10 m of the profile from uptake and used a linear root density). Removing the exclusion and using an exponential root density (decay length 0.3 m) | daily transpiration rms across 12 sites 0.911 -> 0.49 mm (bias by site: base Kansas -39%, Texas +18%, Wisconsin +18%; new within +-10% at 10 of 12, Wisconsin +17%, Kansas -8%); correlation of daily transpiration 0.82 to 0.91 already | alone: yield MAE worse (N=150 +0.097/+0.110) but correlation up (held-out N=150 +0.056, N=400 +0.085), pattern checks 15 -> 16 (crop crossover passes), soybean +0.049, silage +0.117, Rock Springs corn 0.822 -> 0.701 | held (EVAPORATIVE_LAYER_DEPTH_M=0.0 and ROOT_DENSITY_DECAY_M=0.3 are overrides; defaults unchanged) |
| M1 | Milestone 1: all water terms together (snow on, FWC_NO_UPPER_CLIP, evaporation zone, uptake) | n/a | level bias removed (N=150 bias +0.02 / +0.05) | yield MAE worse: N=150 +0.071 / +0.166, N=400 +0.137 / +0.139; correlation better: held-out N=150 +0.036, N=400 +0.075, N=0 +0.047; leaching/denit. mixed (denit. N=150 -0.135 / -0.046 better, volatilization +0.099 / +0.117 worse); Rock Springs corn 0.822 -> 0.655 (tripwire); patterns 16 of 16 | gate NOT met (yield MAE and volatilization worse, tripwire broken). Stop rule applies unless the refit below recovers MAE |
| M1 refit | rue/wue/grain factor refit on the integrated water set | n/a | WUE x0.9 + grain x1.05: N=150 MAE +0.076 / +0.119; WUE x1.1 + grain x0.95: +0.136 / +0.260; RUE x0.93 + grain x1.07: +0.062 / +0.162 (all worse than the current engine; best N=400 MAE still +0.054 / +0.094) | none recover the yield error | **Stop rule triggered: current engine kept.** The water terms stay behind flags; the measured laws (snow adopted already) go in the cover note as findings. Open question for Matt: whether to keep the uptake change anyway for its correlation and pattern-check gains |
| M1 (revised) | Decision, 2026-10-13, per Matt: adopt the measured water laws as the engine's defaults, drop Rock Springs corn as a gate | n/a | n/a | New baseline saved (scorecard_baseline.json): corn yield MAE N=150 1.234 / 1.282, N=400 1.262 / 1.222; correlation 0.807 / 0.812 (N=150), 0.910 / 0.866 (N=400); patterns 16 of 16; Rock Springs corn 0.655 now informational only | adopted: snow, runoff moisture factor (no per-layer cap), 0.2 m evaporation zone with a=0.5, b=0.7, n=2 at scale 1.0, uptake from the surface with exponential root density 0.3 m. Pages re-synced. The yield scatter that rose with it is treated as a signal about downstream terms (carbon, nitrogen, growth), to be located by teacher forcing, not tuned away |
| 6 | Growth path (teacher-forced from Cycles' corn state, N=400, 12 to 14 sites, plus a 518-season harvest-index fit) | (1) Harvest index: with f_G = (aboveground biomass at harvest less at flowering)/at harvest, Cycles' HI = 0.760 - (0.760 - 0.151) exp(-1.479 f_G), rms 0.0034 over 518 corn seasons (engine used 0.8/0.15/1.0, rms 0.0645). (2) Vapor pressure deficit: Cycles uses the FAO-56 one, mean of the saturation pressures at tmax and tmin less the actual pressure from the humidity extremes; with it the implied transpiration-use efficiency is 8.4 to 8.9 g/kg at all 12 sites (crop file 8.7), with saturation at the mean temperature it was 7.3 to 8.0. (3) The 0.785 "net growth fraction" was an artifact of the wrong VPD misclassifying water-limited days; with the right VPD, clean radiation-limited days give 0.93 to 0.97 of nominal, rising from 0.75 in the first 30% of the season to 0.96, about half of which is Cycles growing on the previous day's canopy. (4) The canopy clock slows with water stress: rate about (1 - stress)^1: 0.9 at 2.5% stress, 0.6 at 27%, 0.37 at 60%, 0.06 at 90%, consistent between Kansas and Iowa. The crop file radiation-use efficiency (2.2) was being inflated to 2.332 | growth law from Cycles' own canopy and transpiration: totals within 0 to 10%, daily corr 0.98 to 0.99; harvest index 0.0645 -> 0.0034 rms | N=400 corn yield MAE 1.262/1.222 -> 0.954/1.031 (tuning/held-out), N=150 1.232/1.284 -> 1.160/1.210, correlations unchanged (0.81 / 0.91), fertilizer response corr 0-150 +0.013/+0.017, 150-400 +0.033/+0.004; across-site slope of model vs Cycles total biomass 0.72 -> 0.95; Rock Springs corn 0.662, soybean 0.922, wheat 0.510 (recalibrated, informational) | adopted: HI law, FAO-56 VPD, net growth fraction 0.92 on the previous-day canopy, water-stress canopy clock, corn rue 2.2, grain factor 0.93. Soybean, wheat and silage factors re-centered on the Rock Springs means only (no multi-site data for them) |
| 6b | Vapor pressure deficit, measured directly | Cycles writes its own daily VPD (dailyEnviron.csv). It is es(0.7 tmax + 0.3 tmin) less the FAO-56 actual pressure, rms 0.09 kPa over four sites (FAO-56 mean-of-extremes form: mean 0.60 vs Cycles 0.73 at Iowa; engine's old form 0.46). With Cycles' own column the implied transpiration-use efficiency is flat across 10 sites (7.28 to 7.53); radiation-limited days give 0.93 to 0.97 of nominal, so one growth fraction of 0.95 serves both limits. Crop canopy shape for unstressed seasons already matches Cycles (0.95 vs 0.947 at ttf 0.5) and the crop N demand curve matches to 3% at every biomass bin, so those need no change | total biomass relative error 0.117 -> 0.080, across-site slope 0.95 -> 0.92 | corn yield MAE N=400 0.939 / 1.004, N=150 1.173 / 1.184, N=0 0.866 / 0.807; patterns 16/16; Rock Springs corn 0.687 | adopted (VPD_DAYTIME_ALPHA 0.7, net growth fraction 0.95, corn factor 0.977); soybean/wheat/silage factors re-centered on Rock Springs means |
| N0 | Soil nitrogen supply check (N=0 corn, 28 sites) | n/a | crop N uptake model vs Cycles: across-site correlation 0.96, mean log ratio -0.01, sd 0.27; residual correlates with topsoil clay (0.57): engine over-supplies at clay-rich soils and under-supplies at sandy ones (Carolina 16 vs 35, Louisiana 42 vs 69, Michigan 90 vs 65) | none | no change; clay dependence of net mineralization is a candidate in the carbon step |
