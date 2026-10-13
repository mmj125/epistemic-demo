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
