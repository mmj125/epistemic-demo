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
