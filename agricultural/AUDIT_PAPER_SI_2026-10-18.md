# Audit of the engine against the paper and the SI, 2026-10-18

Purpose: compare every mechanism, equation and parameter the paper and SI state with what `prototypes/cycles_engine_validate.py` does, so that no mismatch or hole is left unexamined. This extends the coarse inventory in `AUDIT_2026-10-15.md`; where the two differ, this one is newer.

## 1. Sources read

- Kemanian et al. 2024, the whole text: Sections 2.1 to 2.9 (methods), 3 (evaluation), 4 (discussion), Table 1 (a list of variable names, no values), Eqs. 1 to 7.
- SI, all ten sections. Equations SI.1 to SI.14 were read from rendered page images, because text extraction mangles exponents and signs. Table SI.2 (RUE, TUE by species).
- Cycles guide (`docs/input.md`, `docs/output.md`), the crop file `GenericCrops.crop` (every field of CornRM.90), our Cycles v1.5.20 control file.
- Cycles daily and annual output for the numeric checks below.
- Cycles code was not read (licence and independence of the engine).

The paper gives 7 equations and the SI 14 (SI.15 is a statistic). Everything else in the paper is described in words. Most of the nitrogen cycle is in that second group.

## 2. Verdict key

- MATCH: implemented as stated, checked in code or numerically.
- MATCH, SOURCE TYPO FIXED: the source as printed is wrong, the engine uses the corrected form.
- EMPIRICAL: the source gives words only; the engine form was measured from Cycles output.
- DIFFERS: the engine does something other than the source states. The reason is given.
- MISSING: not implemented.

## 3. Source typos found

1. SI.2 prints `Q = (W - 0.2S)^2 / (W - 0.8S)`; the standard form has `+ 0.8S` (the printed form gives a negative denominator for W between 0.2S and 0.8S). Engine: `runoff_mm`, line 363, uses `+`.
2. SI.6 prints `CN_wet = CN_b / (0.4 - 0.006 CN_b)`, which is negative for CN_b above 67. The correct sign is `+`. Engine: `cn_wet`, line 281.
3. Paper Eq. 1 prints the exponent `2 + 3b`; the correct exponent is `2 + 3/b`. Checked numerically on 2026-10-18: the engine's `campbell_khe` (line 223) equals the numerical integral of Eq. 1 with `2 + 3/b` (ratio 1.000), and the printed exponent gives a value 10 orders of magnitude smaller.
4. SI.14: the formula as printed reproduces the SI's own worked example (residue C:N 55, 8 ppm mineral N gives 8.65; I get 8.653), but its maximum is 8.5 + 5.5 x 0.5 = 11.25, while the text says the maximum is 14. The formula and the text disagree.
5. SI.10 prints `frz kr Cra` where `frz kr Crz` is meant.

## 4. Energy and evapotranspiration

| Source | Statement | Engine | Verdict |
|---|---|---|---|
| Sec 2.3 | Reference ET by Penman-Monteith (Allen et al. 1998) | `eto_fao56`, line 132 | MATCH (0.4% error, r 1.000, audit 2026-10-15) |
| SI.1 | TRp = (1 + (kc - 1) eie) eie ETo | line 4424 | MATCH |
| SI Sec II | Linear temperature factor on TRp between a base and a threshold temperature | `transpiration_temp_factor`, line 1722, crop fields `tr_min_t`, `tr_threshold_t` | MATCH |
| Sec 2.2 | Evaporative demand allocated to canopy, residues, snow and soil by radiation interception | `soil_evaporation(eto*(1-residue cover), eie)`, line 686 | DIFFERS in detail: soil evaporation uses a measured law (`EVAP_LAW_PARAMS`, top 0.2 m zone), not an allocation by interception. Known: evaporation too high, residue cover too low |
| Sec 2.4 | Precipitation wets residues first | `residue_rain_evap_mm`, line 833 | MATCH in structure, constants measured |
| Sec 2.2 | Surface temperature from the prior day's temperature, air temperature, snow and soil cover | Soil temperature is a per-depth lag filter fitted to Cycles' soil temperature (`SIXPOOL_ML_TEMP_TABLE`, rms 0.85 to 1.09 C) | EMPIRICAL, and it has no snow or residue insulation (winter soil temperature is 1.5 C too cold, which matters for winterkill) |
| Sec 2.2 | Snow | `snow_adjust`, line 647: rain/snow at 1 C, sublimation equals ETo, melt law | EMPIRICAL, matched Cycles to 0.1 mm over 100 designed cases |
| Sec 2.2 | Long-wave radiation as in Allen et al. | inside `eto_fao56` | MATCH |

## 5. Water in the soil

| Source | Statement | Engine | Verdict |
|---|---|---|---|
| SI.2 to SI.7 | Curve number runoff, slope factor, dry and wet bounds, moisture factor | lines 262 to 372 | MATCH, SOURCE TYPOS FIXED |
| SI Sec III | f_wc = 1 when saturated to 0.6 m, 0 when air dry, weighted toward the surface | `depth_weighted_ffc` (Williams et al. 2012 weighting) | EMPIRICAL: the SI gives words only; the weighting comes from a related model, not from Cycles |
| Sec 2.4 | Infiltrated water enters layer 1 up to saturation, then redistributes at a sub-daily step with `khe` (Eq. 1) and travel time (Eq. 2); the step is set by the slowest layer; after 24 h the profile is saturated top to bottom and the excess percolates | `redistribute`, line 409, `KHE_SCALE` = 1.0, up to 200 sub-steps | MATCH |
| Sec 2.4 | Vertical and lateral bypass | not modelled; soil files carry BYP_H = BYP_V = 0 | MATCH for our reference runs (a gap only if bypass is ever used) |
| Sec 2.4 | Green-Ampt infiltration as an alternative | not implemented | MISSING (our reference uses the curve number method, so no effect on validation) |
| Reference | Our Cycles control file has `HYDROLOGY_OPTION 1`, the hourly finite-difference scheme (the guide lists 0 cascade, 1 hourly, 2 Crank-Nicolson, 3 CVode) | drainage matches Cycles (site correlation 0.99) | Stated as a choice of reference; the cascade option (0) would give a different water balance and, per the guide, can miss denitrification |
| Sec 2.3 | Transpiration by the Campbell (1985) hydraulic approach; stomata close beyond a maximum liquid flux | `campbell_water_uptake`, line 1257, crop fields `lwp_stress_onset`, `lwp_wilting_point`, `tr_max_mm_day` | MATCH in structure (the equations are from Campbell and CropSyst, not from the paper); wheat was exempted until 2026-10-18 |
| Sec 2.7 | Water uptake of every species at the water potential of each layer at the start of the step; hydraulic lift emergent | per-layer uptake from each layer's own potential | MATCH |
| Sec 2.3 | Root distribution by layer | `root_length_fraction_by_layer`, line 1198 | EMPIRICAL (not given in the sources) |

## 6. Growth, canopy and yield

| Source | Statement | Engine | Verdict |
|---|---|---|---|
| Eq. 3 to 5 | GB = min(GR, GT); GR = eR eie St (total solar radiation); GT = eW TR / sqrt(Da) | lines 4395 to 4455 | MATCH in form. VPD exponent 0.5 with no heat penalty (`VPD_CYCLES_EXACT`), TUE 8.7 and RUE 2.2 read from the crop file |
| Eq. 3 to 5, as implemented | Not in the paper | GR reads the previous day's canopy (`GROWTH_PREV_CANOPY`); a radiation temperature ramp (`radiation_temp_factor`); `NET_GROWTH_FRACTION` 0.955; `crop["growth_stage_*"]` terms | DIFFERS. These are measured corrections; see finding 2 |
| Sec 2.5 | CO2 scaling of eR and eW from a reference concentration | `wue_co2_scale` | MATCH in intent |
| Sec 3 discussion | An ad hoc temperature adjustment of stomatal conductance is included | `transpiration_temp_factor`, `radiation_temp_factor` | MATCH |
| Eq. 6 | Double-sigmoid canopy, a, b, c, d = 6, -20, -15, 16, eix a crop parameter | `CANOPY_SHAPE_FORCE` = (6, -20, -16, 16), `CANOPY_EIX_FORCE` = 0.99 applied to all crops (the corn dict's own `canopy_shape` is dead) | DIFFERS slightly: see finding 2 |
| Eq. 6 text | The rate of change is the first derivative, reduced by N stress | `canopy_form` D or H integrates the derivative; the stress factor is `n_stress**CANOPY_N_POW` (3.25) times a water factor `**1.35` | MATCH in structure. The water factor is not in the paper; it was measured from 86k Cycles day pairs |
| Eq. 7 | Plant density adjustment eie = 1 - exp(ln(1 - ei) sqrt(PDf)) | `effective_canopy_cover`, line 1705 | MATCH |
| Sec 2.5 | Cold damage, haying, grazing, tillage reduce the canopy and thermal time | Cold damage after flowering ends the season when the minimum temperature falls below `threshold_temp_cold_damage`; the crop file's `MIN_TEMPERATURE_FOR_COLD_DAMAGE` is unused for corn | DIFFERS: finding 8 |
| SI.8 | fst = fsti + (fstf - fsti) / (1 + (TTf50/TTf)^4) | `shoot_fraction`, line 1771 | MATCH; TTf50 = 0.32 is not given in the SI, so it was fitted |
| SI.9 | HI = HIx - (HIx - HIo) exp(-kHI fpf); crop file kHI = 1.0 | `hi_slope` 1.3077 | DIFFERS from the crop file, EMPIRICAL (tested 2026-10-18: with fpf from aboveground biomass after the first reproductive day, kHI 1.0 under-predicts Cycles' HI by 0.064, rms 0.065 over 517 seasons; kHI 1.3077 gives rms 0.010) |
| Sec 3 | Phenology from thermal time with base, optimum and maximum temperatures; photoperiod and vernalization for winter wheat | crop fields in the engine, `E.WINTER_PHENOLOGY` for wheat | MATCH |
| Table SI.2 | RUE and TUE by species (maize 2.2 g/MJ and 8.5 g/kg; the rest of the table was scrambled by text extraction and is not quoted) | crop file values (corn RUE 2.2, TUE 8.7) | MATCH for RUE; TUE 8.7 in the crop file against 8.5 in the table (the crop file is what Cycles runs, and the engine's TUE of 8.7 was confirmed against Cycles' implied value at 12 sites) |

## 7. Nitrogen in the plant

| Source | Statement | Engine | Verdict |
|---|---|---|---|
| Sec 2.5 | N demand from the dilution curve (Lemaire); concentration of new growth set for a crop growing without water stress; adjusted by plant density | `n_marginal_demand_pct`, reference biomass rule (`n_demand_ref`), scale 0.70 | MATCH, with a measured scale of 0.68 to 0.75 of the crop-file curve that the paper does not mention |
| Sec 2.5 | Luxury uptake allowed, no compensatory uptake for past demand | demand is new growth times marginal concentration | MATCH (checked in code 2026-10-18) |
| Sec 2.5 | Legumes fix N above what the soil supplies, without luxury uptake | soybean is exempt from N limitation | MATCH in effect (a simplification) |
| Sec 2.5 | N to harvestable parts per Kemanian et al. 2007; crop fields `N_MAX/MIN_CONCENTRATION_GRAIN/STRAW`, `N_PARTITIONING_FACTOR` | not used; grain N harvest index (0.56 to 0.58) was measured instead | MISSING: finding 1 |
| Sec 2.7 | The water flux from each layer determines access to mineral N | 3% of the reachable pool per day, capped by demand | DIFFERS: the literal per-layer mass flow reading was implemented (`N_ACCESS_MASSFLOW`) and starves the crop; see finding 5 |
| Sec 2.5 | N stress reduces the canopy rate and acts on HI through the post-flowering share | `n_stress` multiplies the canopy clock and also growth (`N_STRESS_GROWTH_POW` = 1) | EMPIRICAL: the stress function (ratio of aboveground N concentration to the critical curve, R2 0.894) was measured from 167k daily Cycles records; growth given Cycles' own states is within about 3% |

## 8. Soil carbon and nitrogen

| Source | Statement | Engine | Verdict |
|---|---|---|---|
| SI.10, SI.11 | Microbial and soil organic C pools with fE, fH, fD, fA, fT, residue pools with fra, frt, frz, frm | `sixpool_step`, line 2489: Cm, Cs, aboveground residue, root plus rhizodeposit residue, manure; per layer | MATCH in structure. fra, frt, frz, frm are folded into one efficiency; roots and rhizodeposits are one pool |
| SI.12 | fH = 1 - (Cs/Csx)^6 | textbook `sixpool_fh` is correct, but the default path uses `eps_h * max(0.2, 1 - r^12)` with a clay-dependent humified fraction | DIFFERS, EMPIRICAL: Cycles still humifies 0.12 to 0.17 of decomposed residue C at Cs/Csx of 1 or more, which the printed formula cannot do |
| SI.13 | fD = 1 - 1/(1 + (4.5 Cs/Csx)^3) | default path uses the same form with fitted (4.26, 2.53) | DIFFERS, EMPIRICAL (fitted to Cycles' respiration in designed fallow runs, rms 0.20) |
| SI.11 text | fA rises exponentially once Cm exceeds 3% of Cs | `SIXPOOL_FA` = 1.0 | MISSING (placeholder). Cm is initialized at exactly 3% of Cs, so the rule matters only if Cm grows past that |
| SI text | Microbial C use efficiency 0.33 to 0.44 depending on saturation; frm about 1.4 fra; frz about fra/1.4 | efficiency 0.4 placeholder, humified fraction 0.34 + 0.152 (1 - exp(-5.5 clay)) | DIFFERS, EMPIRICAL |
| SI.14 | C:N of new microbial biomass between 8.5 and 11.25 by residue C:N and mineral N | constants: microbial 9.7, soil organic 9.4 | MISSING. Effect is small: for corn residue the SI gives 8.5 to 9.4 against the 9.7 the engine uses (about 10% less immobilization per unit carbon) |
| Sec 2.6 | Residue and manure C:N come from the material | constants 86 (aboveground), 52 (root), 30 (manure) | DIFFERS: finding 1 |
| Sec 2.6 | Decomposition halts if mineral N cannot meet microbial demand | decomposition is gated by `c/(c+K)` of layer-1 mineral N with a floor of 0.517 | DIFFERS, EMPIRICAL: measured in Cycles (it never halts completely); the shortfall in immobilization is drawn from NH4 then nitrate and then dropped |
| Sec 2.6 | Cs and Ns are of microbial origin; N pools mirror C pools; first-order residue decay | MATCH | MATCH |
| Table 1 | Csx is a function of clay | `sixpool_csx_pct`, line 2262 | EMPIRICAL (resolved 2026-10-01) |
| Sec 2.6 | Turnover controlled by temperature, moisture and aeration; tillage disaggregation and re-aggregation | `sixpool_fe` (fitted), `tillage_ft`, line 1973 | EMPIRICAL |
| Sec 2.6 | Ammonia oxidation by comammox not simulated | nitrification is a measured flux law (`nitrification_flux_ratio`, line 3004) | MATCH in scope |

## 9. Nitrogen losses and transport

| Source | Statement | Engine | Verdict |
|---|---|---|---|
| Sec 2.4 | Water flows between layers are stored and used for solute transport | leaching by layer with the water flux | MATCH; the concentration is the saturated layer volume (measured 2026-10-18, ratio 0.96 to 1.03, `SOLUTE_VOL_SAT`) |
| Table 1 | Maximum nitrification and denitrification rates per kg of soil; guide: potential denitrification rate and half-saturation constant | measured laws (nitrification flux ratio; denitrification as nitrate x respired carbon x layer-1 saturation) | EMPIRICAL: finding 6 |
| Sec 2.6 | NH4 volatilization, N2O from nitrification and denitrification | `volatilization_rate`, `n2o_from_*`, lines 3125 to 3154 | EMPIRICAL |

## 10. Crop file fields and soil file fields not used by the engine

- Corn: `N_MAX_CONCENTRATION_GRAIN`, `N_MIN_CONCENTRATION_GRAIN`, `N_MAX_CONCENTRATION_STRAW`, `N_MIN_CONCENTRATION_STRAW`, `N_PARTITIONING_FACTOR`, `MIN_TEMPERATURE_FOR_COLD_DAMAGE`.
- Soil file: `BYP_H`, `BYP_V` (zero in our runs).
- Everything else in the corn entry is read: phenology temperatures and thermal times, partitioning, harvest index limits, RUE, TUE, KC, LWP, transpiration limits, rooting depth, dilution curve.

## 11. Findings, ranked by how much error they plausibly carry

1. **The plant to residue N link is not closed.** Residue C:N is a constant (86, 52, 30) and the crop file's grain and straw N fields are unused, so straw N does not come from the plant N the simulation just computed. In Cycles the residue C:N depends on plant N status (measured fresh residue N of 9.5 and 7.0 kg per Mg at the two N rates tested, implied C:N 53 and 71; the engine uses 86 for both). This sets how much N the next crop's decomposition releases or immobilizes, and it is a plausible home of the year-to-year N stress that the engine under-represents (sd 0.016 to 0.024 against 0.036) and of the immobilization response to fertilizer. Not yet tested.
2. **The canopy plateau and the growth scalar compensate each other.** On Cycles' own unstressed corn days the canopy follows Eq. 6 with a = 6.04, b = -20.5, c = -14.95, d = 14.6 and a plateau of 0.951 (rms 0.0022 against the median curve). The engine uses plateau 0.99 and c, d = -16, 16 (rms 0.0277) and carries `NET_GROWTH_FRACTION` 0.955; 0.99 x 0.955 = 0.945, about Cycles' plateau. Moving the plateau into the canopy (0.951) with the growth scalar at 1.0 was tested on 94 held-out sites: grain MAE +0.017, +0.028, +0.026 at N=0, 150, 400 (worse; the first two intervals exclude zero). Not adopted. The pair stays a documented compensation; transpiration demand is about 4% too high at full cover as a result.
3. **SI.14 variable microbial C:N is missing**, with a small effect (about 10% on immobilization per unit carbon) that is consistent with the 9.7 measured from Cycles' pools.
4. **fH and fD differ from the SI as printed**, and the differences are measured from Cycles (humification does not go to zero at saturation). The SI formulas cannot be the whole law.
5. **Access to mineral N by water flux has no equation.** The literal reading starves the crop (grain bias -1.2 and -2.6 Mg/ha at N=0 and N=150). The 3% per day cap stands in. Logged in `prototypes/MECHANISM_LOG.md`.
6. **Nitrification, denitrification and volatilization are empirical laws.** Denitrification is a three-way compensation (nitrate pool, sub-day saturation, a law that is too weak at high nitrate); see the plan entry of 2026-10-18.
7. **Soil temperature has no snow or residue insulation** (winter bias -1.5 C), which enters winterkill and the cold-season decomposition rates.
8. **Cold damage is a single threshold that ends the season**, where the paper says it reduces canopy and thermal time and the crop file carries a minimum temperature that is unused for corn.
9. **fA is a placeholder.** Low risk while Cm stays under 3% of Cs.
10. **Dead configuration.** The corn dict's `canopy_shape` (-5.35, 4.1) and `eix` are overridden by `CANOPY_SHAPE_FORCE` and `CANOPY_EIX_FORCE` for every crop; this misled the audit itself until the override was found. It should be removed or documented where it is read.

## 12. What the audit did not check

- Tillage implement parameters (mixing efficiency, disturbance ratio) beyond their use in `tillage_ft` and `mix_tilled_layers`.
- Manure and fermentation pools in detail (manure fractions are from Cycles' fertilizer catalog).
- The crop sequence builder (Cycles-A) and the SI applications (Iowa fields, Chesapeake), which are uses of the model and not mechanisms.
- Multi-species communities and pasture mixtures.
