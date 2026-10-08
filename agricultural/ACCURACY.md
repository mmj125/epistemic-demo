# Engine accuracy statement (2026-10-08)

The from-scratch engine (`prototypes/cycles_engine_validate.py`) was compared with native Cycles v1.4.4 run on identical inputs: the same tile weather and STATSGO2 soil at 16 CONUS sites, continuous corn, 1980-2016. Differences are model error, not input error. Reproduce with `prototypes/run_validation_multisite.py` (about 80 s, needs a local Cycles v1.4.4 release in `/tmp/cycles-run`).

## Corn grain, 16 sites, mean over sites
| Nitrogen rate | Mean absolute error | Year-to-year correlation | Sites with correlation 0.7 or better |
|---|---|---|---|
| 0 kg N/ha | 1.04 Mg/ha | 0.32 | 4 of 16 |
| 150 kg N/ha | 1.11 Mg/ha (about 13%) | 0.82 | 13 of 16 |
| 400 kg N/ha | 1.06 Mg/ha | 0.86 | 15 of 16 |

Water-limited sites (Kansas, Texas, Arkansas) are within a few percent of Cycles' mean yield. Humid sites run about 4 to 7% low.

## Rock Springs sample scenarios
Corn 0.795, soybean 0.921, winter wheat 0.510 (9 harvests), silage corn 0.124. Only corn and soybean clear the classroom bar (about 0.6 to 0.7).

## Nitrogen losses at 150 kg N/ha
Typical miss is a factor of about 3 (rms log error: leaching 1.28, denitrification 1.20, N2O 1.08, volatilization 0.98).

## Known weak spots
- Unfertilized corn: yield level overshoots (+0.5 Mg/ha) and years are poorly ranked (correlation 0.32).
- Wisconsin year ranking (0.43); Carolina dry years (engine stresses too hard, about 2.6 Mg/ha low).
- Nitrogen losses, as above; soil nitrate supply is off at high-organic-matter sites.
- Winter wheat and silage corn do not meet the bar; pasture is not implemented.
- Topography, ammonia chemistry beyond the fitted rate, and the full six-pool soil system are simplified or absent.

## What was tried and rejected
See `prototypes/QUESTIONS_FOR_DEVS.md` for every mechanism tested against this table, including those that did not help (flatter respiration temperature response, drier topsoil floor, nitrogen limitation of decomposition, lower soil nitrogen supply).
