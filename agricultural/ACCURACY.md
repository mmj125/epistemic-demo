# Engine accuracy statement (re-baselined to Cycles v1.5.20, 2026-10-12)

The from-scratch engine (`prototypes/cycles_engine_validate.py`) was compared with native Cycles v1.5.20 (the current release) run on identical inputs: the same tile weather and STATSGO2 soil at 16 CONUS sites, continuous corn, 1980-2016. Differences are model error, not input error. Reproduce with `prototypes/run_validation_multisite.py` (about 80 s, needs a local Cycles v1.5.20 release in `/tmp/cycles-run15`).

## Corn grain, 16 sites, mean over sites
| Nitrogen rate | Mean absolute error | Year-to-year correlation | Sites with correlation 0.7 or better |
|---|---|---|---|
| 0 kg N/ha | 0.95 Mg/ha | 0.49 | 5 of 16 |
| 150 kg N/ha | 1.22 Mg/ha (about 15%) | 0.80 | 13 of 16 |
| 400 kg N/ha | 1.06 Mg/ha (not re-run after the 2026-10-12 supply fix) | 0.88 | 15 of 16 |

Since 2026-10-12 the engine is run as one continuous chain from 1980, the way Cycles runs a 1980-2016 simulation (`simulate_continuous`), instead of a fresh start with two lead-in years. Soil nitrogen declines over decades under continuous unfertilized corn in Cycles (New York 13.6 to 2.8 Mg/ha over 20 years); a two-year lead-in could not reproduce that, which was the main cause of the earlier unfertilized overshoot.

Overall engine mean yield is about 5% below Cycles' at 150 kg N/ha (7.66 vs 8.02 Mg/ha). The per-site statements from the v1.4.4 table (water-limited sites within a few percent, humid sites 4 to 7% low) have not been re-checked against v1.5.20.

## Nitrogen losses were biased low; fixed 2026-10-12 (supply now depends on soil carbon saturation)
Before: at 150 kg N/ha the engine's mean losses were 2 to 3 times too low (leaching 3.3 vs Cycles 9.0, denitrification 9.5 vs 21.4, N2O 1.7 vs 3.7 kg N/ha over 16 sites), which would teach that fertilizer is safer than it is. Cause (found by comparing monthly net mineralization and annual carbon terms with Cycles): the engine's soil nitrogen supply was too flat across sites. Cycles' soil-organic-matter respiration varies 23-fold across sites (0.14 to 3.3 Mg C/ha/yr) and rises about in proportion to the layer's carbon saturation ratio; the engine varied about 5-fold. Fix: respiration now scales with that ratio (`SIXPOOL_ML_FD_P = 1`, `FD_R0 = 0.573`), with net-N coefficients 120 and 40. Result at the 16 tuning sites, 150 kg N/ha, means Cycles vs engine: leaching 9.0 vs 8.8, denitrification 21.3 vs 17.1, N2O 3.7 vs 4.2 kg N/ha (bias removed). Held-out 12 sites: leaching 4.8 vs 3.1 (was 1.8), denitrification 18.6 vs 20.0 (was 12.3), N2O 4.3 vs 5.8 (was 2.3). Grain unchanged (150 kg N: 1.22 Mg/ha tuning, 1.03 held-out; 0 kg N: 0.95 tuning, 0.98 held-out vs 0.87 before). Site rankings of losses were already good (rank correlation 0.72 to 0.93). What remains is site-specific scatter, not bias: Kansas denitrification 46 vs 7.9 and volatilization 24 vs 76 (soil too wet and nitrate handling in dry soil), Texas denitrification 7 vs 36, Arkansas leaching 3 vs 21, Illinois leaching 20 vs 9.

## Held-out sites (12 sites never used in any fit, 2026-10-12)
Same harness, no refitting, 12 further CONUS sites (South Dakota, North Dakota, western Iowa, Colorado, Oklahoma, Kentucky, Tennessee, Mississippi, Louisiana, Alabama, Virginia, New York). After the continuous-run refit the held-out sites score as well as the sites the model was tuned on.

| Measure | 16 tuning sites | 12 held-out sites |
|---|---|---|
| Grain, 0 kg N/ha, mean absolute error (correlation) | 0.98 Mg/ha (0.56) | 0.87 Mg/ha (0.68) |
| Grain, 150 kg N/ha, mean absolute error | 1.23 Mg/ha | 1.03 Mg/ha |
| Grain, 150 kg N/ha, correlation (sites at 0.7 or better) | 0.80 (13 of 16) | 0.79 (9 of 12) |
| Grain, 150 kg N/ha, mean bias | +0.32 | -0.17 |
| Grain, 400 kg N/ha, mean absolute error (correlation) | 1.06 Mg/ha (0.88) | 1.08 Mg/ha (0.82) |
| rms log error: leaching / volatilization / denitrification / N2O | 1.15 / 0.42 / 0.94 / 1.03 | 1.26 / 0.52 / 0.72 / 0.96 |

Before the refit (fresh start with two lead-in years) the held-out unfertilized error was 1.44 Mg/ha with correlation 0.34 and bias +0.63; the tuning sites looked better (0.86) only because they had been tuned. Weakest held-out fertilized sites: New York, Louisiana, Alabama.

## Rock Springs sample scenarios, measured against v1.5.20 (2026-10-12)
Corn 0.732, soybean 0.875, winter wheat 0.280 (12 harvests), silage corn 0.827 (13 harvests). Means: corn 11.45 vs Cycles 10.14 Mg/ha, wheat 3.88 vs 2.69 (crop calibration factors were set against v1.4.4 means and have not been re-derived; correlation does not depend on them). Against v1.4.4 the same scenarios were 0.795, 0.921, 0.510 and 0.124. Corn, soybean and silage corn clear the classroom bar (about 0.6 to 0.7); wheat does not. Reproduce with `prototypes/make_ref15.py` and `REF_DIR=/tmp/cycles-ref15`.

## Nitrogen losses at 150 kg N/ha
Typical miss: denitrification and nitrous oxide are now within a factor of about 2 to 2.8 after the 2026-10-12 refit to v1.5.20 (rms log error: denitrification 0.86, N2O 1.02); volatilization was refit the same day with a topsoil moisture term and fell from 0.95 to 0.46 (Kansas 21 vs 76 and Georgia 38 vs 20 kg N/ha are the largest misses); leaching (1.40) is still off by a factor of about 4. Before the refit (rates fitted to v1.4.4) the figures were leaching 1.34, denitrification 1.34, N2O 1.30, volatilization 0.98. The refit changed the denitrification saturation exponent from 7 to 3 (v1.5 depends less steeply on wetness), slowed nitrification, and raised the N2O fractions; corn grain is unchanged (N=150 error 1.17 Mg/ha, correlation 0.80). What remains is in the nitrogen pools and processes, not the rate constants: volatilization at the dry sites (Kansas 76 vs 8 kg N/ha, Carolina 23 vs 6, Georgia 20 vs 8), denitrification at wet sites (Minnesota 87 vs 28, Texas 36 vs 7), and leaching at Arkansas (21 vs 3.5).

## Known weak spots
- Unfertilized corn: yield level overshoots (+0.5 Mg/ha) and years are poorly ranked (correlation 0.32).
- Wisconsin year ranking (0.43); Carolina dry years (engine stresses too hard, about 2.6 Mg/ha low).
- Nitrogen losses, as above; soil nitrate supply is off at high-organic-matter sites.
- Winter wheat and silage corn do not meet the bar; pasture is not implemented.
- Topography, ammonia chemistry beyond the fitted rate, and the full six-pool soil system are simplified or absent.

## What was tried and rejected
See `prototypes/QUESTIONS_FOR_DEVS.md` for every mechanism tested against this table, including those that did not help (flatter respiration temperature response, drier topsoil floor, nitrogen limitation of decomposition, lower soil nitrogen supply).

## Cycles v1.4.4 versus v1.5.20 (2026-10-12)

The numbers above are against v1.5.20. Earlier work was measured against v1.4.4; to see whether that mattered, `prototypes/compare_cycles_versions.py` runs both versions on identical inputs at the same 16 sites (continuous corn, N=0 and N=150, 1980-2016). v1.5 needs its own input format, so the script translates the files; v1.5 also has two soil inputs v1.4.4 lacks (rock fraction set to 0, pH set to 6.5). Note that `-b` means "batch" in v1.4.4 but "set a break point" in v1.5, so the v1.5 runs use no flag.

- Yield and phenology agree: mean grain ratio v1.5/v1.4.4 is 0.996 (N=0) and 0.998 (N=150); year-to-year correlation between the two versions averages 0.96 or better; planting day within 0.3 days.
- Nitrogen losses (N=150) differ: leaching +40%, denitrification +30%, nitrous oxide +54%, volatilization -3%. The gap is concentrated at the wet, fine-textured sites (Iowa leaching 41 vs 63 kg N/ha, denitrification 52 vs 79; Minnesota denitrification 64 vs 87; Arkansas leaching 12 vs 21).
- The differences are model changes in v1.5, not input differences: changing the pH input (5.5, 6.5, 7.5) leaves every output identical, and rock fraction is set to 0, as in v1.4.4. (Other hydrology options change leaching and denitrification much more, 0: leaching 117, denitrification 19; 2: 107 and 37, at Iowa N=150, but option 1 is what the v1.4.4 hourly-infiltration setting maps to in the v1.5 sample files.)

So the yield comparison does not depend on the version, but the nitrogen-loss comparison does. The head-to-head page now writes v1.5 input files and reads v1.5 `.csv` output only, and the Colab notebook fetches v1.5.20. Tested end to end against v1.5.20 for corn and soybean at central Iowa. The table above is the 16-site run against v1.5.20 (the earlier v1.4.4 figures were N=0 1.04 Mg/ha and 0.32, N=150 1.11 and 0.82, N=400 1.06 and 0.86).
