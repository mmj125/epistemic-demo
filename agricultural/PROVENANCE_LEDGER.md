Provenance ledger for the epiSTEMic crop engine (first pass, 2026-10-22)

Principle (Matt, 2026-10-22): Cycles is the test set, not the training set. Build each process from the paper, the SI, the Cycles documentation and the published literature. Compare with Cycles to show similarity. Fit to Cycles output only when the sources are silent, and label the result a suspect.

Classes
- A: form and parameters documented in the Kemanian et al. 2024 paper, the SI, the Cycles input and output docs, or a Cycles data file (crop file, fertilizer file, tillage file).
- B: form and parameters from other published or public sources (Saxton and Rawls, FAO-56, Stockle and Campbell, CropSyst's public source, IPCC, Macnack).
- C: documented or published form, parameters fitted to Cycles output.
- D: form and parameters both fitted to Cycles output because the sources are silent.
- E: engine assumption, placeholder or convention, neither documented nor fitted.

How this was built: every module-level constant of `cycles_engine_validate.py` (170) and every function (88) was read with its own comment or docstring, and classified from what the code says about itself. Entries marked (check) rest on an inference I have not verified in the code path. `ledger_coverage_2026_10_22.py` lists constants this file does not mention, so it can be kept complete. Numbers quoted for fit quality are from the code comments and may be stale.

Water and energy
| Process | Code | Class | Source or note |
|---|---|---|---|
| Reference evapotranspiration | `eto_fao56` | A | Paper names FAO-56 Penman-Monteith |
| Soil hydraulic properties | `saxton_rawls`, `PSI_E_FROM_ANCHOR` | B, option chosen by yield score against Cycles (C) | Saxton and Rawls 2006; the anchor option was adopted because 16-site grain MAE improved |
| Initial soil moisture | `INITIAL_MOISTURE_FRACTION` 0.5 | E | |
| Curve number runoff | `cn_dry`, `cn_wet`, `retention_param_mm`, `runoff_mm` | A | SI Eq. SI.1 to SI.6, sign-corrected |
| Moisture adjustment of the curve number | `depth_weighted_ffc`, `FWC_NO_UPPER_CLIP` | A form from words only, so partly E | SI Eq. SI.7 is described in words in both sources |
| Redistribution of water | `redistribute`, `campbell_khe`, `KHE_SCALE`, `REDISTRIBUTE_SUBSTEPS` | A (Eq. 1, 2), numeric controls E | |
| Soil evaporation | `soil_evaporation`, `EVAP_LAW_PARAMS`, `EVAP_ZONE_DEPTH_M`, `SOIL_EVAP_SCALE` | D (check which of the two implementations is active) | Paper gives no formula; the Cycles law was measured |
| Soil evaporation, CropSyst form | `soil_evaporation_cropsyst`, `CROPSYST_AIRDRY_FRAC`, `REW_DEFAULT_MM` | B | CropSyst's public source; FAO-56 Table 19 |
| Residue cover and rain interception | `RESIDUE_COVER_*`, `RESIDUE_RAIN_EVAP_*`, `residue_cover_frac` | D | Fitted to Cycles' residue and evaporation |
| Snowpack | `SNOW_*`, `snow_adjust` | D | Measured from designed experiments on Cycles v1.5.20 |
| Potential transpiration and water use efficiency | growth section | A | SI Sec. II, crop file TUE |
| Water stress and root water uptake | `water_stress_response`, `campbell_water_uptake`, `layer_water_potential`, `total_root_conductance`, `LEAF_WATER_POTENTIAL_AT_FC` | B | CropSyst manual and Campbell 1985 |
| Root distribution | `ROOT_TRI_POW`, `ROOT_DENSITY_DECAY_M`, `ROOT_TTF_FULL` | E | Stated as engine assumptions in the code |
| Soil temperature | `hc_make`, `hc_step`, `SOILT_DIFFUSIVITY_M2_DAY` | B form, parameter chosen inside the SI's quoted damping depth (E) | |
| Soil temperature lag filter | `simulate_soil_temp`, `SOIL_TEMP_LAG_K` | E (checked against planting dates) | |

Crop growth
| Process | Code | Class | Source or note |
|---|---|---|---|
| Radiation and transpiration limited growth | growth section of `simulate_season` | A | Paper Sec. 2.5, crop file RUE and TUE |
| Growth level scalar | `crop_ngf`, `ngf_faithful` 1.0 | A | `NET_GROWTH_FRACTION` 0.955 is a fallback not used by the five crops (D) |
| CO2 effect on water use efficiency | `WUE_CO2_EXP` 0.197, `RUE_CO2_EXP` 0 | A form, D exponent | Paper says efficiencies scale with CO2; exponent measured on Cycles' fixed-CO2 runs |
| CO2 record | `CO2_PPM_BY_YEAR`, `CO2_REF_PPM` | B | |
| Canopy expansion and senescence | `canopy_cover`, `effective_canopy_cover`, `DEFAULT_CANOPY_SHAPE` | A | Paper Eq. 6 and 7 |
| Canopy plateau and shape per crop | `CANOPY_FAITHFUL`, `CANOPY_SHAPE_FORCE`, `CANOPY_EIX_FORCE`, `CORN_CANOPY_SHAPE` | D | Measured on Cycles' unstressed days |
| Canopy response to water and N stress | `CANOPY_WATER_POW` 1.35, `CANOPY_N_POW` 3.25, `CANOPY_TWO_CLOCK`, `GROWTH_PREV_CANOPY` | D | Measured on 86k day pairs of Cycles' interception |
| Thermal time, vernalization, photoperiod | `thermal_time_increment`, `vernalization_increment`, `WINTER_PHENOLOGY` | A | Crop file fields; sub-daily integration is B |
| Shoot allocation | `shoot_fraction` | A form (SI Eq. 8 to 11), C parameter `TTF50_SHOOT_PARTITION` 0.42 | Fitted to Cycles' realised shoot share |
| Root growth leaving the plant | `root_retained_frac` 0.6, `ROOT_C_INPUT_FACTOR` 5/3 | D | Measured; later shown to be a rule for every crop (plan 2026-10-22) |
| Harvest index | HI law in `simulate_season` | A, C for `hi_slope` 1.3077 and the soybean constants | Guide law; empirical correction rms 0.010 vs 0.065 |
| Cold damage | single threshold ending the season | E | Cycles docs: a daily minimum below the threshold multiplies biomass and interception by 1 - 0.99^3 per day (input docs, MIN_TEMPERATURE_FOR_COLD_DAMAGE), not a season-ending kill |
| Planting date rule | `find_planting_doy` | A | Operation file soil temperature window |
| Silage harvest timing and forage removal | `harvest_ttf` 0.85, 90% removal | A (operation file) and D (the 90% removal was read from Cycles' behaviour) (check) | |

Nitrogen cycle
| Process | Code | Class | Source or note |
|---|---|---|---|
| N dilution curve | `n_critical_pct`, `n_marginal_demand_pct` | A | Crop file N_MAX_CONCENTRATION, N_DILUTION_SLOPE; Lemaire |
| N demand scale | `N_DEMAND_SCALE` 0.70 | D | Constant 0.69 to 0.77 of the crop-file curve at every biomass class (plan 2026-10-22) |
| N stress response | `N_STRESS_R0/R1/SMAX/Q`, `N_STRESS_GROWTH_POW`, `N_AG_FRACTION` 0.88 | D | Reproduces Cycles' factor on Cycles' states within 0.02; the source gives no curve |
| Uptake and growth solved together | `N_SIMULTANEOUS` | B form | CropSyst 1994 Eqs. 29 and 30 |
| Supply limit on uptake | `n_uptake_rate` 0.03 (crop dicts), `N_UPTAKE_FLOOR_MGKG` 0.3 | D | CropSyst Eq. 26 form and mass flow tested 2026-10-22, neither explains Cycles |
| Lost-root N sink | `RHIZO_N_UPTAKE`, wheat keys `rhizo_rr`, `rhizo_root_n_share` | C | Structural formula; root N share read from Cycles output (corn 0.12, wheat 0.082) |
| Six-pool carbon and nitrogen structure | `sixpool_step`, `sixpool_ml_step` | A | SI Eq. SI.10 to SI.14 |
| Saturation capacity | `sixpool_csx_pct` | B | C-Farm, Kemanian and Stockle 2010 Eq. 3 |
| Humification and decomposition saturation | `sixpool_fh` (power 6), `sixpool_fd`, `SIXPOOL_ML_FD_SI` | A form (SI.13), C parameters | |
| Decomposition rate constants | `SIXPOOL_KS`, `_KRA`, `_K_RTZ`, `_KRM`, `_KM`, `SIXPOOL_ML_KS`, `SIXPOOL_ML_DEPTH_Q`, `SIXPOOL_DEPTH_*` | D | Back-calculated from Cycles output |
| Microbial efficiency | `SIXPOOL_EPS_C` 0.4, `SIXPOOL_FA` 1.0, `SIXPOOL_ML_EPS_H` | E placeholders; `SIXPOOL_ML_HUM_CLAY` is C | C-Farm Eq. 4a shape fitted to Cycles |
| Pool C:N ratios | `SIXPOOL_CN_*` | D | Read from Cycles output files (Rock Springs) |
| Environmental factor, temperature | `SIXPOOL_FE_TEMP_*` | C | Campbell function (Stockle and Campbell 1989 Eq. 18) fitted to Cycles' composite factor |
| Environmental factor, moisture | `SIXPOOL_FE_MOISTURE_PTS` | D | Table measured on Cycles |
| N limitation of decomposition | `SIXPOOL_N_*` | D | Measured on 28 sites |
| Residue decay timing | `CRA_MATURATION_TAU_DAYS` 1.0 | D | |
| Nitrification | `nitrification_temp_factor` B (Stockle and Campbell 1989 Eq. 11); `NITRIF_RATIO_PARAMS` D | B + D | Law reproduces Cycles' states to 0.8 to 1.0 |
| Denitrification | `DENIT_SD`, `DENIT_NLAYERS` | D | The documented per-layer Michaelis-Menten form explained 0.01 to 0.17 of Cycles' daily denitrification |
| N2O | `N2O_NIT`, `N2O_DEN` | D | |
| Volatilization | `VOLAT_WIND_*` | D | Cycles ignores pH; wind law measured |
| Application losses and IPCC fractions | `NH3_FRAC_SYNTHETIC`, `NH3_FRAC_MANURE`, `macnack_ammonia_loss_pct` | B | IPCC 2006/2019, Macnack et al. 2013 |
| Nitrate transport | `SOLUTE_VOL_SAT` | D | Leaching proportional to saturated water volume, ratio 0.96 to 1.03 |
| Immobilization split | `IMMOB_FROM_NO3`, `IMMOB_SPLIT` | E | Paper says both pools; the split is undocumented |
| Fertilizer and manure composition | `MINERAL_SOURCES`, `MANURE_SOURCES` | A | Cycles fertilizer catalog |
| Manure organic fraction into the residue pool | in `simulate_season` | E | Added 2026-10-21 |

Management
| Process | Code | Class | Source or note |
|---|---|---|---|
| Tillage implements | `TILLAGE_IMPLEMENTS` | A | Cycles tillage file |
| Tillage speed-up of decomposition | `tillage_ft`, `tillage_ftx` | A | Paper formulas |
| Decay of tillage disturbance | `tillage_dr_decay` | A (2% per day) with E moisture scaling | |
| Tillage mixing of moisture, texture, carbon, residue | `mix_tilled_layers` and the block in `simulate_season` | A in words (paper Sec. 2.6), details E | Checked against Cycles' carbon profiles 2026-10-21 |
| Irrigation | `irrigation_refill_layers` rule | A | Cycles input docs, AUTO_IRRIGATION |
| Cover crop | rye crop dict, `cover` chain | A | WinterRye crop file values |

Counts from the table above (60 rows): by first-listed class A 24, B 9, C 2, D 18, E 7; counting every class a row mentions A 24, B 9, C 7, D 21, E 12.

Sources still needed (ranked by how many D entries they could replace)
1. N uptake and root N access: no source found that reproduces Cycles. Tested and failed against Cycles' daily uptake: the pool cap (engine), mass flow, the CropSyst Eq. 26 shape, and Stockle and Campbell 1989 Eqs. 17 and 18 (plan 2026-10-22). Godwin and Jones 1991 and Stockle and Debaeke 1997 are not in the repo and untested; low expected value.
2. Nitrogen losses: a published volatilization model with wind dependence, and a published N2O model (Cycles-L paper cites sources in its Sec. 2; the SI may name them).
3. Evaporation and residue cover: Campbell 1985 chapters on evaporation and residue (Matt can copy sections).
4. Decomposition environmental factors: Kemanian et al. 2011 and Pravia et al. 2019.
5. Snow: whatever the SI cites for snow accumulation and melt, if anything.

Remaining constants: legacy, conventions and experiment flags
| Constant | Class | Status |
|---|---|---|
| `DENITRIF_RELSAT_EXPONENT`, `DENITRIF_K_REL`, `DENITRIF_THRESHOLD_FORM`, `DENITRIF_THR_*`, `DENITRIF_RESP_*`, `DENITRIF_DEPTH_CAP_M` | D | Older fitted denitrification laws, superseded by `DENIT_SD` while `DENIT_STARTDAY` is on. `run_fallow_n_window` still falls back to the older `denitrification_rate_rel` in the first fallow window of a run when no six-pool state exists: an inconsistency to remove |
| `SUBDAY_DENIT` | D | Denitrification reads time-weighted within-day saturation (rebuild step 1) |
| `SNOW_MODEL`, `SNOW_RAIN_TEMP_C`, `SNOW_MELT_BASE_C`, `SNOW_MELT_DDF` | D | Same entry as the snowpack row above |
| `BACKGROUND_N_KG_HA_DAY`, `ROTHC_WEATHER_FACTOR_NORM`, `CN_RATIO_SOM` | E | Legacy RothC-style background mineralization; not used when the six-pool path is on |
| `CARBON_FRACTION_DM` 0.42, `OM_FROM_SOC` 1.72 | B | Standard literature conversions |
| `CROP_WATER_POTENTIAL_K_SEC_PER_DAY`, `EVAPORATIVE_LAYER_DEPTH_M` | B | CropSyst manual; Stockle, Martin and Campbell |
| `NCRIT_FLOOR_MGHA` 1.0 | E | Convention: dilution curve flat below 1 Mg/ha |
| `VPD_FLOOR_KPA` 0.2 | E (check) | |
| `THERMAL_TIME_SUBDAILY`, `WINTERKILL_SOIL_T` | E | Numerical and cold-damage switches |
| `NH4_UPTAKE_W`, `IMMOB_SPLIT`, `ROOT_C_AT_HARVEST`, `RHIZO_N_UPTAKE`, `NSTRESS_REFIT` | experiment switches | Defaults reproduce the adopted engine; non-default settings failed the adoption rule (plan 2026-10-22) |

Function index for the rows above (so each law can be found by name): nitrification `nitrification_flux_ratio`; denitrification `denitrification_startday`, `denitrification_layers`, `denitrification_flux_resp`, `denitrification_rate_rel`; N2O `n2o_from_nitrification`, `n2o_from_denitrification`; volatilization `volatilization_flux`; net mineralization bookkeeping `apply_net_min`; environmental factors `sixpool_fe`, `sixpool_fe_temp`, `sixpool_fe_moisture`, `sixpool_fe_moisture_ml`, `rothc_temp_factor`, `rothc_moisture_factor`; residue `residue_rain_evap_mm`, `cra_maturity_fraction`; evaporation `soil_evaporation_zone`, `compute_tew`; root water `extract_transpiration`, `root_zone_availability`, `root_length_fraction_by_layer`, `layer_depth_fraction_within`; temperature factors `transpiration_temp_factor`, `radiation_temp_factor`, `canopy_cover_two`, `photoperiod_hours`; fallow and chain drivers `run_fallow_n_window`, `run_bare_fallow_window`, `simulate_continuous`, `simulate_season_with_leadin`, `standard_kwargs`; helpers `n_conc_layer1`, `n_conc_layers`, `sixpool_bulk_density`, `sixpool_effective_depth_m`, `sixpool_init_state`, `sixpool_ml_init`, `slope_factor`, `summer_time_from_doy`, `zone_mean_theta`, `infiltrate`.
