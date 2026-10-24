# Prototype folder index (2026-10-24)

The engine is named Rhizo; its file `rhizo_engine.py` was `cycles_engine_validate.py` until 2026-10-24 (plan, logs and the frozen pages still use the old name).

About 220 scripts remain here. Most are dated one-shot diagnostics (name ends in a date) that the plan entries cite as evidence for a number; they are not part of the engine and need not be read. Run guards and tools by name from this folder. A script deleted on 2026-10-23 was never imported or cited anywhere (list in `../../CLAUDE_ARCHIVE_2026-10-23.md`); git history has it.

## The engine and what ships
- `rhizo_engine.py`: the engine (every process, flag and switch).
- `engine_api.py`: the browser-facing configuration (`schema`, `load_site`, `run`), crop dictionaries, rotation, cover crop.
- `simulator.html`, `field_selector.js`: the user interface; `engine-demo.html`, `model-validation.html`, `head-to-head.html`: frozen older pages (do not resync).
- `run_validation.py`, `run_validation_rotation2.py`: crop dictionaries and the Rock Springs crash guard.

## Runners against Cycles
- `run_validation_multisite.py` (corn, soy, silage, sorghum; env `CROPSEL`, `ENGINE_OVR`, `N_LEVELS`, `YEAR_STEP`, `OUT_JSON`), `run_validation_multisite_wheat.py` (winter wheat, `FALLN=60`), `field_data.py`, `sitesets/` (`fresh94.json`, `holdout.json` locked).
- `paired_fr_2026_10_17.py` (paired bootstrap of two runs), `scorecard.py`, `scorecard_now_2026_10_23.py` (five-crop table at current defaults plus the panel), `metrics_panel_2026_10_23.py` (concordance, Nash-Sutcliffe, within-site, N response).

## Regression guards (run after every engine change)
- `snapshot_2026_10_20.py` (`save FILE` / `check FILE`: numbers and daily hashes), `check_parity_2026_10_19.py` (API against harness, must print WORST 0.0), `ledger_coverage_2026_10_22.py` (every constant and function is in `../PROVENANCE_LEDGER.md`).

## Attribution and diagnostics that are still live
- `attrib_ag_2026_10_18.py` (force Cycles' canopy, water, N stress into the engine), `canopy_gap_2026_10_19.py` (canopy by thermal-time tenth), `water_trace_2026_10_23.py` (the water stress formula on Cycles' states), `water_budget_2026_10_23.py` and `water_fallow_2026_10_23.py` (in season and bare soil water terms by month), `wheat_nbudget_2026_10_23.py`, `wheat_growth_eff_2026_10_23.py`, `wheat_clock_2026_10_23.py`, `wheat_maturity_tt_2026_10_23.py`, `rotation_scope_2026_10_23.py` and `rotation_engine_2026_10_23.py` (rotation against Cycles), `mgmt_response_2026_10_21.py` (irrigation, tillage, manure responses), `npool_force_losses_2026_10_23.py`.
- Observations: `mead_score_2026_10_23.py` (towers), `county_runs_2026_10_20.py` and `county_compare_2026_10_20.py` (NASS county yields), `tools/` (AmeriFlux reducers, BIF extractor, Pyodide tests).
- Documented-law tests that adopted or rejected a process: `denit_apex_2026_10_22.py`, `denit_daycent_2026_10_22.py`, `nitrif_daycent_2026_10_22.py`, `uptake_*_2026_10_22.py`.

## Records
- `ENGINE_REBUILD_PLAN.md` (dated entries, newest last; the place to look first), `MECHANISM_LOG.md`, `REFIT_PLAN.md`, `FOR_CYCLES_DEVS.md`, `scorecards/`, `../PROVENANCE_LEDGER.md`, `../AUDIT_PAPER_SI_2026-10-18.md`.
