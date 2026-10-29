# Evaluation protocol against observations (pre-registered 2026-10-28, before the split was scored)

Purpose: report agreement with observations that no constant was tuned on, and say which constants were.

## Data and split
- USDA NASS county yields, 94 fresh sites, 1982 to 2016, as in `COUNTY_YIELD_CHECK_2026-10-20.md`.
- Sites are sorted by site id. Even positions are the development half, odd positions the test half. The rule was fixed before any half was scored. Years are not split.
- Cycles v1.5.20 runs on the same sites are the comparator, not the target.

## What was tuned on county data
Only the soil evaporation law (three parameters, `EVAP_LAW_PARAMS`), by choosing among six settings on 2026-10-26 using all counties. Deposition (8 kg N/ha/yr) was adopted from a measurement, and the county data could not discriminate. No other constant was chosen with county data.

## Procedure
1. Re-choose the evaporation setting among the same six on the development half only (corn, within-site r, then level).
2. Report the final engine on the test half for corn, soybean, silage and wheat: median within-site detrended r, level (engine / observed), anomaly RMSE in standard-deviation units, and the paired difference to Cycles with a bootstrap 95% interval over sites.
3. If the setting chosen on the development half differs from the adopted one, report the test-half result for both and keep the adopted one only if its test-half within-site r is within 0.02 of the other.
4. Report the development half beside the test half so a drop is visible.

## Claims allowed if the test half agrees
Only what the test half supports. If the engine minus Cycles interval on the test half includes zero, the claim is "comparable to Cycles", not "better".

## Not covered here
Plot-scale N response trials and long-term experiments (next step), and the Mead towers, which chose TTf50 and the senescence timing and are therefore not independent for those constants.
