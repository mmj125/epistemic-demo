# One-at-a-time sensitivity of the engine's outputs (2026-10-13)

Method: each parameter set to 75% and 125% of its current value, everything else fixed; six sites (Rock Springs, Iowa, Kansas, Indiana, Georgia, Minnesota), 12 weather years each, corn at 0 and 150 kg N/ha. Entry = elasticity, percent change in the output per percent change in the parameter (central difference over the two runs). Baseline means: unfertilized grain 3.39 Mg/ha, fertilized 8.25, nitrogen response 4.86, leaching 11.6, volatilization 15.5, denitrification 27.0, N2O 4.5 kg N/ha. Reproduce with the driver described in DECISION_KEY.md (perturb a module constant with `fit2`-style attribute overrides, `YEAR_STEP=3`).

| Parameter | N0 grain | N150 grain | N response | Leaching | Volat. | Denit. | N2O |
|---|---|---|---|---|---|---|---|
| N_DEMAND_SCALE | 0.10 | 0.31 | 0.45 | -2.26 | -0.31 | -2.70 | -4.12 |
| SIXPOOL_ML_N_A (gross mineralization) | 1.32 | 0.25 | -0.49 | 2.79 | 0.52 | 2.43 | 3.42 |
| NET_GROWTH_FRACTION | 0.76 | 0.89 | 0.98 | -0.65 | -0.21 | -1.05 | -1.65 |
| WUE multiplier | 0.50 | 0.56 | 0.61 | -0.46 | -0.14 | -0.80 | -1.37 |
| SIXPOOL_ML_FD_R0 | -0.24 | -0.02 | 0.13 | -1.04 | -0.14 | -0.70 | -1.26 |
| SIXPOOL_ML_KS | 0.25 | 0.02 | -0.13 | 1.01 | 0.14 | 0.69 | 1.18 |
| Grain calibration factor | 0.84 | 0.92 | 0.97 | -0.20 | 0.08 | -0.18 | -0.18 |
| SIXPOOL_ML_N_B (immobilization) | -0.42 | -0.12 | 0.09 | -0.77 | -0.16 | -0.74 | -0.88 |
| SOIL_EVAP_SCALE | -0.30 | -0.17 | -0.08 | -0.19 | 0.83 | -0.26 | -0.27 |
| DENITRIF_RELSAT_EXPONENT | 0.02 | 0.02 | 0.02 | 0.72 | 0.03 | -0.63 | 0.09 |
| VOLATILIZATION_RATE_A | -0.01 | -0.02 | -0.03 | -0.03 | 0.71 | -0.16 | -0.37 |
| DENITRIF_K_REL | -0.02 | -0.01 | -0.01 | -0.70 | -0.01 | 0.51 | 0.05 |
| N_STRESS_ZERO_RATIO | -0.65 | -0.44 | -0.30 | 0.19 | 0.06 | 0.31 | 0.49 |
| Nitrification factor k | -0.01 | 0.01 | 0.02 | 0.06 | -0.50 | 0.20 | 0.39 |
| RUE multiplier | 0.29 | 0.38 | 0.43 | -0.29 | -0.08 | -0.41 | -0.43 |
| SIXPOOL_KRA (residue decay) | -0.05 | -0.02 | 0.00 | -0.34 | 0.23 | -0.11 | -0.09 |
| SIXPOOL_ML_N_C | -0.11 | -0.03 | 0.02 | -0.21 | -0.05 | -0.20 | -0.24 |
| RESIDUE_COVER_K | 0.07 | 0.04 | 0.01 | 0.21 | -0.15 | 0.08 | 0.08 |
| CRA_MATURATION_TAU_DAYS | 0.00 | 0.00 | -0.01 | 0.12 | -0.05 | 0.01 | 0.00 |
| ROOT_C_INPUT_FACTOR | 0.04 | 0.01 | -0.02 | 0.09 | 0.02 | 0.07 | 0.06 |
| SIXPOOL_K_RTZ | -0.01 | -0.01 | -0.01 | 0.03 | -0.01 | 0.01 | 0.00 |
| SIXPOOL_ML_ROOT_DECAY_M | -0.02 | 0.00 | 0.00 | -0.03 | -0.01 | -0.03 | -0.03 |

What it says
- Yield outputs are set by the calibration and growth terms (grain factor, NET_GROWTH_FRACTION, water-use and radiation-use efficiency) and, for unfertilized corn, by the gross mineralization coefficient and the nitrogen-stress threshold.
- Loss outputs are set far more by the crop's nitrogen demand scale and the gross mineralization coefficient (elasticity 2 to 4) than by their own rate constants (0.5 to 0.7). N_DEMAND_SCALE was fitted from one site's uptake ratio.
- Residue and root timing terms (maturation lag, root input factor, root turnover, root depth decay, residue cover) move nothing by more than 0.35, so they are not worth further tuning.
