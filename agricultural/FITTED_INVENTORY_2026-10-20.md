# Fitted and compensating items in the engine, 2026-10-20

Method. `agricultural/prototypes/inventory_2026_10_20.py` sorts every module-level constant of `cycles_engine_validate.py` by name rules and the provenance written in its own comments. Classes are a first pass by hand-written name lists, so a few names may sit in the wrong class; the counts are close, not exact. Crop dictionaries (`engine_api.py`) are covered separately below.

## Counts (242 constants)

| Class | Count | Meaning |
|---|---|---|
| DOC | 24 | documented in the paper, SI, crop file, guide, or a standard reference |
| ENG | 18 | engine design choice or numerical setting |
| C | 56 | constant fitted or measured on Cycles' output, form from the paper or literature |
| D | 38 | whole law identified from Cycles' output (form and constants) |
| LEG | 37 | superseded legacy constant, overridden by a newer path |
| OFF | 38 | option switched off by default |
| DIAG | 31 | diagnostic hook, no model effect |

Of the 136 constants that run in the default configuration (DOC, ENG, C, D), 94 (69%) are Cycles-derived, 24 (18%) are documented, 18 (13%) are engine choices. A further 106 (44% of all constants) are dead or diagnostic and make the module harder to audit.

## Class D, laws identified from Cycles' output (38)

| Law | Names | Documented alternative |
|---|---|---|
| Nitrification (NO3:NH4 ratio shut-off near 9) | `NITRIF_RATIO_*` | guide names `NITRIF_RATE`; the ratio rule is real structure (tested 2026-10-19) but has no source |
| Denitrification (nitrate x respired C x layer-1 saturation) | `DENITRIF_RESP_*`, `DENITRIF_MM_PARAMS` | guide: `POT_DENITRIF_RATE`, `DENITRIF_HALF_RATE` (Michaelis-Menten); respired C is a real driver |
| Volatilization | `VOLATILIZATION_RATE_A..D` | IPCC fractions already in `NH3_FRAC_*`; Macnack 2013 is in the repo |
| N2O | `N2O_*` | IPCC emission factors |
| Soil evaporation and residue cover | `EVAP_LAW_*`, `RESIDUE_*` | CropSyst and FAO-56 forms are documented |
| Snow | `SNOW_*` | published degree-day values are 2 to 4 mm per degree C; ours (rain above 1 C, melt base -1 C, 2.5) already sit in that range |
| Solute volume | `SOLUTE_VOL_SAT` | paper Sec 2.4 gives no equation |
| VPD column | `VPD_CYCLES_EXACT`, `VPD_FLOOR_KPA`, `VPD_DAYTIME_ALPHA` | reconstructed from Cycles' output; check the SI for the printed formula |
| Decomposition temperature and moisture response | `SIXPOOL_FE_TEMP_PTS_MEASURED`, `SIXPOOL_FE_MOISTURE_PTS` | guide documents `DECOMP_HALF_RESP` 0.22 and `DECOMP_RESP_POWER` 3.0 (form to confirm) |
| Soil temperature by depth | `SIXPOOL_ML_TEMP_TABLE` | SI mentions thermal amplitude, conductivity and damping depth; paper Sec 2.2 describes snow and residue cover |
| Humification and respiration saturation | `SIXPOOL_ML_HUM_CLAY`, `SIXPOOL_ML_FD_SI` | SI.12 and SI.13; replacing with printed SI values barely moves net mineralization (2026-10-19) |

## Class C, constants fitted on Cycles' output (56), by cluster

- Six-pool carbon and N rates and depth profile (`SIXPOOL_KS`, `KRA`, `K_RTZ`, `KRM`, `ML_N_A/B/C`, `N_HALF`, `N_FMIN`, `DEPTH_*`, `ML_FH_P`, `ML_FH_FLOOR`): C-Farm (Kemanian and Stockle 2010, in the repo) and White et al 2014 publish base parameters; not yet compared.
- C:N ratios (`SIXPOOL_CN_*`): measured at Rock Springs from Cycles' state; SI.14 gives the bounds 8.5 to 14 and a mineral-N rule.
- Canopy and N stress (`CANOPY_FAITHFUL` shapes, `CANOPY_WATER_POW`, `CANOPY_N_POW`, `N_STRESS_*`, `N_AG_FRACTION`): measured on Cycles' unstressed or stressed days.
- Heat penalty and CO2 (`C1_HEAT_T0`, `C1_VPD_POW`, `HEAT_A`, `WUE_CO2_EXP`, `CO2_REF_PPM`): fitted growth-law terms, the likeliest to be compensating something.
- Partition and root C (`TTF50_SHOOT_PARTITION` 0.42, `ROOT_C_INPUT_FACTOR` 5/3, root retention 0.6).
- N demand and uptake (`N_DEMAND_SCALE` 0.70, `N_UPTAKE_FLOOR_MGKG`).
- Water set-up (`PSI_E_FROM_ANCHOR`, `INITIAL_MOISTURE_FRACTION`, `KHE_SCALE`, `SOIL_EVAP_SCALE`).

## Crop dictionaries

- Corn, silage, sorghum, soybean: `canopy_shape_faithful` and `eix_faithful` are Cycles-measured. Soybean `hi_x` 0.4, `hi_o` 0.15, `hi_slope` 3.4 are fitted to Cycles' SoybeanMG.5 at 94 sites (`soy_hi_fit.py`, REFIT row 53); the crop file's own values should be tested first. Corn `hi_slope` 1.3077 against the crop file's 1.0 is an empirical correction.
- Wheat: `n_demand_scale` 0.874562, `net_growth_fraction` 0.95, `eix_cap` 0.93, `ttf50` 0.32 are tuned and labelled suspects.
- All crop `calibration_factor` values are 1.0.

## Compensations known or suspected

1. `n_uptake_rate` 0.03 (stands in for an unknown supply limit; nitrate floor and leaching depend on it).
2. Wheat suspects above.
3. Corn `hi_slope` 1.3077.
4. The evaporation, residue cover and canopy chain (evaporation too high, residue cover too low, canopy too large).
5. Root retention 0.6 with root C input 5/3.
6. Heat penalty and CO2 terms.
7. Soil temperature bias (winter +0.5 to +0.6 C warm, summer -0.7 to -0.9 C cold in the decomposition temperature).
8. Cold-season net mineralization 17 to 35% above Cycles', hidden by crop over-uptake (2026-10-19 forcing runs).

## Data tables copied from the Cycles distribution

`TILLAGE_IMPLEMENTS` (86 implements), `MANURE_SOURCES`, `MINERAL_SOURCES` and `CO2_PPM_BY_YEAR` come from Cycles' input files. They are inputs, not fitted, but the licence (CC BY-NC-ND 4.0) should be checked before the engine ships commercially.

## Cheapest cleanups (no accuracy cost expected)

1. Delete the 69 LEG and OFF constants and 31 diagnostic hooks after a coverage run confirms they are unreachable from the default configuration.
2. Snow: use published degree-day values.
3. SI.12 and SI.13 saturation constants.
4. SI.14 microbial C:N.
5. IPCC emission factors for N2O.
6. Test the crop file's own soybean harvest index.

## Needs a decision before work

How will a replacement for D-class laws be validated when the only reference is Cycles? Options: published ranges for N losses, observed county yields, or field data.

## Stale note

`CLAUDE.md` gave soybean harvest index as 0.5, 0.311, 0.58; the code and `soy_hi_fit.py` use 0.4, 0.15, 3.4. Corrected 2026-10-20.
