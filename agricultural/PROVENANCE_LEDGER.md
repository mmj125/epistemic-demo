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
| Residue cover and rain interception | `RESIDUE_COVER_*`, `RESIDUE_RAIN_EVAP_*`, `residue_cover_frac` | C for cover (Gregory 1982 form Fc = 1 - exp(-Am M)); D for the rain-interception term | Cover K 0.27 explained 2026-10-23 on Cycles' own output (24 sites, 285k residue days): Cycles' radiation interception by residue = 1 - exp(-0.384 M_flat - 0.084 M_standing) (rms 0.003; M from carbon / 0.4), and 0.384 matches Gregory's maize value (about 0.40 per Mg/ha; wheat 0.45 to 0.54, sunflower 0.20) within 4 percent. Standing residue (median 45 percent of surface mass) covers about a fifth as much. The engine has one surface pool, so 0.27 is the blend (0.384 x 0.55 + 0.084 x 0.45). Single-K error against Cycles' cover: rms 0.019 overall, up to 0.03 in May to August (standing residue is left standing then), mean -0.02 (engine cover slightly low in summer). Standing/flat split not built: payoff bounded at about 2 to 3 percent of ETo in soil evaporation. Rain interception term still fitted to Cycles. |
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
| Cold damage | single threshold ending the season after flowering (`threshold_temp_cold_damage`), opt-in winter kill (`winterkill_temp`) | E | Cycles docs (input.md, MIN_TEMPERATURE_FOR_COLD_DAMAGE / THRESHOLD_TEMPERATURE_FOR_COLD_DAMAGE) describe a graded daily damage, factor 1 - f^3 with f = 1 - (T - Tmin)/(Tthresh - Tmin), applied to above-ground biomass and interception, plus a harvest trigger after flowering (the harvest trigger is what the engine implements). Tested 2026-10-23 against Cycles v1.5.20 output: on 58 winter-wheat nights below -10 C with 0.02 Mg/ha or more live biomass (five northern sites, 36 winters) none shows a measurable biomass loss, and on 427 corn nights where the formula with the weather-file minimum predicts more than 10 percent loss the median biomass ratio is 1.000; the formula as written is not visible in Cycles' output, so it is not implemented (it would move the engine away from Cycles). Reason unknown (a different temperature variable, canopy or surface temperature, is the likely cause) |
| Planting date rule | `find_planting_doy` | A | Operation file soil temperature window |
| Silage harvest timing and forage removal | `harvest_ttf` 0.85, 90% removal | A (operation file) and D (the 90% removal was read from Cycles' behaviour) (check) | |

Nitrogen cycle
| Process | Code | Class | Source or note |
|---|---|---|---|
| N dilution curve | `n_critical_pct`, `n_marginal_demand_pct` | A | Crop file N_MAX_CONCENTRATION, N_DILUTION_SLOPE; Lemaire |
| N demand scale | `N_DEMAND_SCALE` 0.70 | D | Constant 0.69 to 0.77 of the crop-file curve at every biomass class (plan 2026-10-22) |
| N stress response | `N_STRESS_R0/R1/SMAX/Q`, `N_STRESS_GROWTH_POW`, `N_AG_FRACTION` 0.88 | D | Reproduces Cycles' factor on Cycles' states within 0.02; the source gives no curve |
| Uptake and growth solved together | `N_SIMULTANEOUS` | B form | CropSyst 1994 Eqs. 29 and 30 |
| Supply limit on uptake | `n_uptake_rate` 0.03 (crop dicts), `N_UPTAKE_FLOOR_MGKG` 0.3 | D | CropSyst Eq. 26 form and mass flow tested 2026-10-22, neither explains Cycles Retested 2026-10-23 on the current engine (94 sites): removing the cap (`CROP.n_uptake_rate=None`) still over-yields, N=0 grain MAE 0.50 to 0.95 (bias +0.19 to +0.76), N=150 0.95 to 1.20, pooled r 0.95 to 0.92; leaching level improves (1.33 to 0.88, 1.31 to 1.18). Fourth failed route (CropSyst Eq. 26, mass flow, Stockle and Campbell Eq. 17, now the cap removal). Owner of the source: Godwin and Jones 1991 availability functions (not in the repo), or the Kemanian lab. Closed under rule 6. |
| Lost-root N sink | `RHIZO_N_UPTAKE`, wheat keys `rhizo_rr`, `rhizo_root_n_share` | C | Structural formula; root N share read from Cycles output (corn 0.12, wheat 0.082) |
| Six-pool carbon and nitrogen structure | `sixpool_step`, `sixpool_ml_step` | A | SI Eq. SI.10 to SI.14 |
| Saturation capacity | `sixpool_csx_pct` | B | C-Farm, Kemanian and Stockle 2010 Eq. 3 |
| Humification and decomposition saturation | `sixpool_fh` (power 6), `sixpool_fd`, `SIXPOOL_ML_FD_SI` | A form (SI.13), C parameters | Since 2026-10-23 `SIXPOOL_ML_FD_SI` is Pravia 2019 Eq. 4 as published, fs = 1 - 1/(1 + (Cs/Cx/0.22)^3), no fitted parameter (class A). Cx = 0.021 + 0.038 fclay (Pravia Eq. 1) matches `sixpool_csx_pct`. |
| Decomposition rate constants | `SIXPOOL_KS`, `_KRA`, `_K_RTZ`, `_KRM`, `_KM`, `SIXPOOL_ML_KS`, `SIXPOOL_ML_DEPTH_Q`, `SIXPOOL_DEPTH_*` | D | Back-calculated from Cycles output Source hunt 2026-10-23: the paper's parameter table lists the reference rates without values; Pravia et al. 2019 (Agric Syst 171:13-22) is paywalled and Clivot et al. 2019 (PMC6937324) is a different model (Lloyd-Taylor, Moyano) with no comparable k. No public value found. Owner: Pravia 2019 tables or the Kemanian lab parameter file. UPDATE 2026-10-23, Pravia 2019 (now in the repo): kx 0.00015 d-1 (Eq. 3) adopted as `SIXPOOL_ML_KS`, depth term `SIXPOOL_ML_DEPTH_Q` set to 0 (not in the published form); package changes 94 sites vs before: corn grain MAE 0.503/0.947/0.850 to 0.472/0.955/0.850 (bias +0.19/+0.14 to -0.18/-0.02 at N=0/150), silage 0.937/1.640 to 0.879/1.696 (N=150 cost 0.056), sorghum 0.502/1.121 to 0.507/1.097, wheat 0.410/0.784/0.766 to 0.447/0.741/0.792; pooled r unchanged or up everywhere; leaching level corn 1.33/1.31/1.16 to 1.08/1.15/1.10 and rms log 0.47/0.57/0.29 to 0.40/0.50/0.27; denitrification at N=0 1.36 to 0.98; N2O at N=150/400 lower (0.55 to 0.48, 0.47 to 0.44). Still class D: `SIXPOOL_KRA`, `_K_RTZ`, `_KRM`, `_KM` (Pravia gives no residue or microbial rates). |
| Microbial efficiency | `SIXPOOL_EPS_C` 0.4, `SIXPOOL_FA` 1.0, `SIXPOOL_ML_EPS_H` | E placeholders; `SIXPOOL_ML_HUM_CLAY` is C | C-Farm Eq. 4a shape fitted to Cycles |
| Pool C:N ratios | `SIXPOOL_CN_*` | D | Read from Cycles output files (Rock Springs) |
| Environmental factor, temperature | `SIXPOOL_FE_TEMP_*` | C | Campbell function (Stockle and Campbell 1989 Eq. 18) with the documented c = 4 (2026-10-22); only To (37.5) is fitted, to Cycles' composite factor. The earlier two-parameter fit (36.098, 2.177) is 0.02 Mg/ha better in grain MAE |
| Environmental factor, moisture | `FE_MOISTURE_DOC` | A | 2026-10-22: Hill form r^3/(r^3+0.22^3) on relative wetness, the Cycles docs' DECOMP_HALF_RESP 0.22 and DECOMP_RESP_POWER 3.0 (reading of 'saturation' as relative wetness is an assumption, suspect with its test: grain neutral, leaching 1.24 to 1.19x). The 9-point table `SIXPOOL_FE_MOISTURE_PTS` (class D) stays as the off switch |
| N limitation of decomposition | `SIXPOOL_N_*` | D | Measured on 28 sites |
| Residue decay timing | `CRA_MATURATION_TAU_DAYS` 1.0 | D | |
| Nitrification | `nitrification_temp_factor` B (Stockle and Campbell 1989 Eq. 11); `NITRIF_RATIO_PARAMS` D | B + D | Law reproduces Cycles' states to 0.8 to 1.0. Moisture and ratio terms tested against literature 2026-10-22 (`nitrif_daycent_2026_10_22.py`, refit of k only, R2 on Cycles' daily layer-1 states with the ratio term): fitted logistic 0.990, DAYCENT bell (Parton et al. 1996, 2001; medium and sandy texture parameters) 0.74 and 0.78, Stockle and Campbell Eq. 8 0.57. Cycles' response is about 1.1 at saturation 0.2 to 0.4, 1.0 at 0.5 to 0.6, 0.69 / 0.42 / 0.02 in the 0.7 to 0.8, 0.8 to 0.9, 0.9 to 1.0 bins (roughly 1 - S^4); the NO3:NH4 ratio term is worth 0.35 of R2 and has no published source found |
| Denitrification | `DENIT_APEX`, `DENIT_APEX_PARAMS`, `denitrification_apex` (default since 2026-10-23); the older fitted law `DENIT_SD`, `DENIT_NLAYERS` stays behind `DENIT_APEX=False` | A + C | EPIC/APEX denitrification as published (Kemanian and Williams, CEAP 2011 APEX upgrades Eqs 1 to 4): Rmax 32e-6 kg N/kg soil/d, fNO3 = NO3/(NO3+60), fresp = min(1, CO2/50), fw from air volume with exponent 60 and a texture term (class A). The one unsourced constant is the amplitude 2.5 on the whole law (class C suspect; the Cycles docs name POT_DENITRIF_RATE as a calibration multiplier with no default, so its owner is the Cycles input documentation or the developers' calibration files). Adopted after 94-site corn, silage and sorghum and 60-site wheat checks: pooled r unchanged (corn 0.953 / 0.922 / 0.965, silage 0.932 / 0.920 / 0.954, sorghum 0.939 / 0.884 / 0.925, wheat 0.925 / 0.849 / 0.860), grain MAE cost at most 0.063 (corn N=0), denitrification and N2O rms log at N=0 roughly halved (silage 0.70 to 0.39, sorghum 0.75 to 0.41), management responses of denitrification and N2O improved in 3 of 4 treatments. Costs: sorghum denitrification at N=150 and 400 rms log 0.56 to 0.85 and 0.59 to 0.95, leaching level up (corn baseline 7.8 to 8.9 kg N/ha against Cycles 6.1, sorghum N=150 1.13x to 1.36x), irrigation response of denitrification still the wrong sign. The first fallow window of a run still uses the older rate law (no six-pool state yet) |
| N2O | denitrification share: `N2O_APEX` (default since 2026-10-23) with the APEX Eq. 5 form fNO3 (1 - fw^0.5)(1 - fresp^0.33), no fitted constant; the older fitted share `N2O_DEN` stays behind `N2O_APEX=False`. Nitrification share: `N2O_NIT` (fitted logistic in saturation) | A (denitrification share), D (nitrification share, source still needed) | Test 2026-10-23 on Cycles' own daily states (24 sites, 149k denitrification days): Cycles' N2O/denitrification ratio mean 0.081, Eq. 5 mean 0.079, daily corr 0.73, nitrate-bin levels match (0.006/0.028/0.108/0.162/0.233 vs 0.003/0.022/0.088/0.180/0.241). Cycles keeps a share of about 0.02 near saturation where Eq. 5 goes to 0. Engine, 94 sites: grain and r identical (N2O is not fed back). N2O vs Cycles: N=0 level 1.19 to 0.84, rms log 0.17 to 0.14; N=150 0.78 to 0.55, 0.45 to 0.58; N=400 0.67 to 0.47, 0.65 to 0.90 (worse where engine denitrification is already 0.8x to 0.9x of Cycles'). |
| Volatilization | `VOLAT_WIND_*` | D | Cycles ignores pH; wind law measured Plausibility 2026-10-23: the fitted temperature slope 0.1456 per C compares with a thermodynamic expectation of about 0.12 per C near 15 C (NH4+/NH3 pKa slope about 0.032 per C, i.e. 0.075 in ln units, plus a Henry constant slope of about 0.048; both coefficients recalled from memory, not checked against a source), so the form is physically plausible; wind linearity and the moisture exponent have no source. |
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

Function index for the rows above (so each law can be found by name): nitrification `nitrification_flux_ratio`; denitrification `denitrification_startday`, `denitrification_apex`, `denitrification_layers`, `denitrification_flux_resp`, `denitrification_rate_rel`; N2O `n2o_from_nitrification`, `n2o_from_denitrification`; volatilization `volatilization_flux`; net mineralization bookkeeping `apply_net_min`; environmental factors `sixpool_fe`, `sixpool_fe_temp`, `sixpool_fe_moisture`, `sixpool_fe_moisture_ml`, `rothc_temp_factor`, `rothc_moisture_factor`; residue `residue_rain_evap_mm`, `cra_maturity_fraction`; evaporation `soil_evaporation_zone`, `soil_evaporation_fao56` (switch `SOIL_EVAP_DOC`: FAO-56 two-stage Kr, tested 2026-10-23 against the Mead towers, no gain in spring), `compute_tew`; root water `extract_transpiration`, `root_zone_availability`, `root_length_fraction_by_layer`, `layer_depth_fraction_within`; temperature factors `transpiration_temp_factor`, `radiation_temp_factor`, `canopy_cover_two`, `photoperiod_hours`; fallow and chain drivers `run_fallow_n_window`, `run_bare_fallow_window`, `simulate_continuous`, `simulate_season_with_leadin`, `standard_kwargs`; helpers `n_conc_layer1`, `n_conc_layers`, `sixpool_bulk_density`, `sixpool_effective_depth_m`, `sixpool_init_state`, `sixpool_ml_init`, `slope_factor`, `summer_time_from_doy`, `zone_mean_theta`, `infiltrate`.
