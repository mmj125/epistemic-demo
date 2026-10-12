# Engine accuracy statement (re-baselined to Cycles v1.5.20, 2026-10-12)

The from-scratch engine (`prototypes/cycles_engine_validate.py`) was compared with native Cycles v1.5.20 (the current release) run on identical inputs: the same tile weather and STATSGO2 soil at 16 CONUS sites, continuous corn, 1980-2016. Differences are model error, not input error. Reproduce with `prototypes/run_validation_multisite.py` (about 80 s, needs a local Cycles v1.4.4 release in `/tmp/cycles-run`).

## Corn grain, 16 sites, mean over sites
| Nitrogen rate | Mean absolute error | Year-to-year correlation | Sites with correlation 0.7 or better |
|---|---|---|---|
| 0 kg N/ha | 1.03 Mg/ha | 0.33 | 4 of 16 |
| 150 kg N/ha | 1.14 Mg/ha (about 14%) | 0.80 | 13 of 16 |
| 400 kg N/ha | 1.09 Mg/ha | 0.87 | 15 of 16 |

Overall engine mean yield is about 5% below Cycles' at 150 kg N/ha (7.66 vs 8.02 Mg/ha). The per-site statements from the v1.4.4 table (water-limited sites within a few percent, humid sites 4 to 7% low) have not been re-checked against v1.5.20.

## Rock Springs sample scenarios (still measured against v1.4.4 output, not yet re-run on v1.5.20)
Corn 0.795, soybean 0.921, winter wheat 0.510 (9 harvests), silage corn 0.124. Only corn and soybean clear the classroom bar (about 0.6 to 0.7).

## Nitrogen losses at 150 kg N/ha
Typical miss: denitrification and nitrous oxide are now within a factor of about 2 to 2.8 after the 2026-10-12 refit to v1.5.20 (rms log error: denitrification 0.86, N2O 1.02); leaching (1.40) and volatilization (0.95) are still off by a factor of 2.5 to 4. Before the refit (rates fitted to v1.4.4) the figures were leaching 1.34, denitrification 1.34, N2O 1.30, volatilization 0.98. The refit changed the denitrification saturation exponent from 7 to 3 (v1.5 depends less steeply on wetness), slowed nitrification, and raised the N2O fractions; corn grain is unchanged (N=150 error 1.17 Mg/ha, correlation 0.80). What remains is in the nitrogen pools and processes, not the rate constants: volatilization at the dry sites (Kansas 76 vs 8 kg N/ha, Carolina 23 vs 6, Georgia 20 vs 8), denitrification at wet sites (Minnesota 87 vs 28, Texas 36 vs 7), and leaching at Arkansas (21 vs 3.5).

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
