# CLAUDE.md sections retired 2026-10-23

Text removed verbatim from CLAUDE.md when it was condensed on 2026-10-23, kept so nothing is lost. Numbers here are dated and may be stale (rule 4); the current figures are in CLAUDE.md and the last entries of `agricultural/prototypes/ENGINE_REBUILD_PLAN.md`. Earlier history is in `CLAUDE_ARCHIVE_2026-10-17.md`.

## Done-when 2 and the pooled correlation paragraphs (2026-10-18 to 2026-10-23)

**Done when** (Matt, 2026-10-18):
1. Five crops reach POOLED correlation above 0.8 against Cycles over held-out site-years (all sites and years pooled, per N rate, and across rates), at several N rates where N matters. Pooled, not within-site: Cycles disagrees with itself at only 0.80 within-site yearly correlation between its own water schemes.
2. Leaching is much better (2026-10-18, 94 sites, continuous chain, rms log error with +0.5 offset: 0.55 at N=0, 0.62 at N=150, 0.34 at N=400, from 0.72 / 0.80 / 0.32 the same morning; means engine/Cycles 6.8/4.6, 18.3/13.3, 92.7/84.8 kg N/ha, so N=0 and N=150 still over-leach 1.5x and 1.4x; site correlation about 0.95).

Pooled correlation now (2026-10-18, held-out, 94 sites, about 1,775 site-years per N rate, continuous chain, factors 1.0): corn 0.955 / 0.929 / 0.965 at N=0/150/400 (0.969 all rates); soybean 0.945; silage corn 0.917 / 0.889 / 0.934 (0.944 all; forage level at factor 1.0 and the correct 85 percent harvest +19 / +9 / +8% at N=0/150/400, total biomass +9 / +1 / 0%; the 25 to 30% high figures reported earlier on 2026-10-18 were a runner bug, the engine had been harvested at full maturity while Cycles harvests at 85%); sorghum (SorghumMS, values read from the crop file, no tuning) 0.935 / 0.895 / 0.927 (0.948 all; level +1 / -2 / -5%); winter wheat 0.933 / 0.866 / 0.871 at N=0/90/150 over 58 sites (0.924 all rates; Cycles reference now built with the same 60 kg fall plus spring N as the engine, `FALLN=60`; adopted change versus the old wheat default, paired MAE gain 0.068 [0.021,0.122], 0.187 [0.099,0.283], 0.230 [0.125,0.351], 44 / 42 / 39 of 58 sites better; sets `SITEOFF=0,1`). All five crops pass at every N rate. Earlier wheat figures at N=90/150 (0.64 to 0.79) compared the engine's fall+spring N with a spring-only Cycles reference and are void.

Update 2026-10-21 (94 fresh sites, wheat 58, held out, continuous chain, factors 1.0, after the 2026-10-20/21 N-process rebuild: wind-driven volatilization, start-of-day nitrification, two-layer denitrification, nitrate- and saturation-dependent N2O, Campbell decomposition temperature with start-of-day moisture): pooled correlation corn 0.954 / 0.924 / 0.966 at N=0/150/400, soybean 0.943 (N=0 only; its path has no N model, so none of these changes reach it and its output is identical), silage corn 0.915 / 0.898 / 0.940, sorghum 0.934 / 0.884 / 0.927, winter wheat 0.927 / 0.841 / 0.861 at N=0/90/150. All five crops still pass criterion 1 at every N rate. Versus the engine before the rebuild (paired grain MAE gain, CI): corn +0.017 [+0.012,+0.023] at N=0, neutral at N=150 and 400; silage +0.074 [+0.039,+0.117] at N=0, neutral at 150 and 400; sorghum +0.032 [+0.016,+0.052] / +0.064 [+0.030,+0.102] / +0.004 [+0.001,+0.007]; wheat +0.020 [+0.007,+0.036] / +0.014 [-0.008,+0.034] / +0.012 [-0.003,+0.029]; no crop worse. Leaching (corn engine/Cycles level 1.35 / 1.34 / 1.22, rms log 0.50 / 0.58 / 0.31; Cycles against itself under a neighbouring weather cell: 0.23 to 0.31) is within about twice its noise floor; silage leaching stays poor (1.7x to 2.0x at N=0 and 150, rms log 0.83 to 1.2). Silage residue fix later on 2026-10-21 (the engine returned above-ground biomass minus grain as residue; Cycles removes 90 percent of the clipped forage): silage pooled r 0.932 / 0.919 / 0.954, forage MAE gain +0.128 [+0.037,+0.235] / +0.196 [+0.080,+0.324] / -0.010, leaching rms log 0.58 / 0.94 / 0.47, denitrification 0.70 / 0.74 / 0.60 (was 0.83 / 1.19 / 1.06 and 1.17 / 1.33 / 0.97). Details in `ENGINE_REBUILD_PLAN.md` 2026-10-20 and 2026-10-21 entries; lesson: Cycles daily rows are end-of-day states, fit fluxes on start-of-day states.

Update 2026-10-21 (late, N budget): Cycles' calendar-year N budget shows its mineral pool loses about 9% more than the plant keeps (root growth that leaves the plant carries soil N); the engine did not debit it, which inflated the mineral pool 1.3x to 1.5x. Fixed in `RHIZO_N_UPTAKE` (no new constant). 94 sites, same code off vs on: corn N=0 grain MAE gain +0.078 [+0.051,+0.109], silage +0.115 [+0.069,+0.166], sorghum +0.051 [+0.024,+0.079]; N=150 and 400 neutral; pooled r unchanged or up; leaching 1.35/1.34/1.22 to 1.24/1.21/1.10 of Cycles (corn); silage and sorghum N=150 bias now -0.43 / -0.36 Mg/ha (N stress calibration to revisit). Management responses against Cycles (24 sites, `mgmt_response_2026_10_21.py`): manure organic N and carbon now enter the residue pool (grain +5.0 vs +4.9), tillage mixes texture, carbon and residue between layers, irrigation follows AUTO_IRRIGATION; the denitrification sign under irrigation (+2.5 vs -2.7) and tillage denitrification size remain open (engine in-season nitrate still +12 to 20%). Note: `n_uptake_rate` 0.03 is set in the crop dicts (the module default None is overridden). Wheat (2026-10-22): the same lost-root sink exists in Cycles' wheat budget (0.057 x plant N measured, 0.055 predicted from a root N share of 0.082) and is now in the wheat harness (`WHEAT_RHIZO`): 58 sites, grain MAE gain +0.028 [+0.004,+0.052] / +0.088 [+0.054,+0.124] / -0.005 [-0.036,+0.027] at N=0/90/150, pooled r 0.929 / 0.851 / 0.863. Not adopted and left behind switches (default off): retained roots entering residue at harvest (`ROOT_AT_HARVEST`, leaching and denitrification better, corn and sorghum grain significantly worse) and the N stress refit (`NSTRESS_REFIT`, silage N=150 significantly worse). The Cycles-L archive on Zenodo (8087162) holds only the PIHM coupling, no crop or N code; the CropSyst Eq. 26 uptake form and mass flow do not explain Cycles' daily uptake (plan 2026-10-22).

Update 2026-10-23 (denitrification): the engine's denitrification is now the published EPIC/APEX law (Kemanian and Williams, CEAP 2011 APEX upgrades Eqs 1 to 4; `DENIT_APEX=True`) with one unsourced amplitude 2.5 (labelled suspect, class C); `DENIT_APEX=False` restores the law fitted to Cycles. Pooled r unchanged for corn, silage, sorghum (94 sites) and wheat (60): corn 0.953 / 0.922 / 0.965, silage 0.932 / 0.920 / 0.954, sorghum 0.939 / 0.884 / 0.925, wheat 0.925 / 0.849 / 0.860; grain MAE cost 0.00 to 0.06 Mg/ha; denitrification and N2O at N=0 improve sharply and the denitrification and N2O responses to tillage, late planting and manure take the right sign. Open costs: baseline leaching up (corn 8.9 vs Cycles 6.1 kg N/ha), sorghum denitrification worse at N=150 and 400, irrigation response of denitrification still the wrong sign, and the nitrate surplus upstream (engine nitrate at planting +58 percent at N=0, entering in the off-season) that the fitted law was cancelling. Plan entry 2026-10-23 has the numbers.

Update 2026-10-23 (scorecard at current defaults, after APEX denitrification and N2O, Pravia decomposition constants, legume path): 94 fresh sites, pooled r corn 0.959 / 0.921 / 0.965 at N=0/150/400, silage 0.937 / 0.920 / 0.954, sorghum 0.945 / 0.887 / 0.925, soybean 0.943, wheat 0.920 / 0.847 / 0.858 (N=0/90/150, 60 sites); bias -9 to +4% except sorghum N=0 -14% and wheat N=0 -16%; corn leaching engine/Cycles 4.9/4.6, 15.3/13.3, 93.1/84.8 kg N/ha (silage N=150 16.7/11.7); denitrification 0.75x and N2O 0.5x of Cycles at N>=150; the wheat harness records no N losses (continuous soybean now runs the legume N path: pooled r 0.959, N losses recorded, plan 2026-10-23 last entry). County yields (NASS) and Mead observations unchanged or consistent with Cycles (plan 2026-10-23 last entry). This supersedes the earlier Update paragraphs above where they differ.

## Rule 1 as written

1. No calibration factor that masks a mechanism error. Attribute the gap (force Cycles' states into the engine), fit the mechanism from Cycles' own daily output, keep factors at 1.0. Factors still carried are suspects: silage corn 0.67 was removed 2026-10-18 (factor now 1.0; the multi-site runs are 8 to 19% high at 1.0 but the Rock Springs silage rotation reads +44%, an open rotation or manure mismatch the factor was hiding), wheat `net_growth_fraction` 1.057 with `eix_cap` 0.86 (same pattern as the corn pair removed 2026-10-18), the shared `NET_GROWTH_FRACTION` 0.955 (now unused by the five crops except as a fallback). Wheat 1.15 was removed earlier.

## Current state (2026-10-17), growth law, next work (2026-10-18)

### Current state (2026-10-17, held-out unless noted)
- Corn, 94 fresh sites, continuous chain, no regional map, factor 1.0: grain MAE 0.449 / 0.900 / 0.744 Mg/ha at N=0/150/400, bias +0.05 / -0.03 / -0.18, correlation about 0.84 / 0.81 / 0.90. Leaching rms log error 0.62 / 0.71 / 0.29 (mean 7.9 / 20.0 / 92.5 vs Cycles 4.6 / 13.3 / 84.8 kg N/ha); drainage already matches (site corr 0.99).
- Corn N demand: new-growth N concentration is read at the biomass the crop would have without N stress (paper Sec 2.5), scale 0.70 (one global value, measured: corn and silage corn 0.68, wheat 0.75 of the crop-file curve; wheat is pinned at 0.8746 as a labelled suspect), net immobilization is drawn from NH4 then nitrate (`IMMOB_FROM_NO3`, paper Sec 2.6), aboveground N stress law (REFIT row 14b), uptake about 3% of the pool per day (`n_demand_ref`, `n_stress_ag_basis`, `n_uptake_rate`).
- Wheat: canopy form H adopted (`canopy_form="H"`), documented harvest index law with real post-anthesis growth share, factor 1.0, 16 held-out sites N=0 MAE 0.369, N=150 1.318. Use `FALLN=60` for continuous wheat (spring-only N is bistable in Cycles).
- Soybean: factor 1.0, harvest index fitted from Cycles (hi_x 0.4, hi_o 0.15, slope 3.4, 94 sites, `soy_hi_fit.py`), N=0 bias -3.6%, site-mean MAE 0.23. Silage corn within 7 to 13% free, 1 to 3% with states forced.
- Attribution (24 sites, corn): forcing Cycles' canopy removes 29/34/22% of grain MAE at N=0/150/400, N stress 10/15/1%, mineral pool 0/7/0%, forcing Cycles' water stress raises engine yield by 0.6 Mg/ha at N=150, so Cycles' water stress is MILDER than the engine's (engine is over-stressed on water, corrected 2026-10-18). All four states forced still leave 13 to 47%: the daily growth conversion and level.
- Losses (2026-10-18, 94 sites): nitrate leaves a layer in proportion to its SATURATED water volume (`SOLUTE_VOL_SAT`, measured on Cycles' daily output, ratio 0.96 to 1.03). Denitrification is HIGH, not low: engine/Cycles 2.4x / 1.4x / 1.4x at N=0/150/400 (the old 0.64 to 0.70 was stale), N2O 1.8x / 1.1x / 1.5x, volatilization 1.2x / 0.9x / 0.8x. Net mineralization matches Cycles; the engine carries a December 31 nitrate pool 1.5x to 2x Cycles' at moderate-leaching sites. The documented per-layer Michaelis-Menten form (no carbon term) explains almost none of Cycles' held-out daily denitrification (R2 0.01 to 0.17 vs 0.50 for the engine's nitrate x respired carbon x layer-1 saturation law), so keep that law and look at the states feeding it (layer-1 saturation, respiration, nitrate). Year-to-year agreement of N losses is weak (within-site corr 0.3 to 0.4).
- Root cause of what remains at N=150: engine year-to-year N stress varied too little (sd 0.016 to 0.024 vs 0.036, corr 0.3, measured before the 2026-10-18 changes; re-measured 2026-10-18 on 17 sites at N=150: season-mean N factor within-site sd 0.033 vs Cycles 0.038, and the dry-year link of the paper is reproduced, within-site corr with the water factor -0.52 vs -0.52, and per site-year the season-mean N factor correlates 0.81 / 0.76 with Cycles' at N=0 / 150, with thirds of the season at N=150 matching (Cycles 0.996 / 0.959 / 0.855, engine 1.000 / 0.961 / 0.851); only N=0 mid season is off, engine 0.493 against Cycles 0.396 with plant N equal, so N stress is no longer the N=150 lever) and the canopy is too large; the system is a set of compensating errors (evaporation too high, residue cover too low, canopy too big, root retention 0.6, harvest index offset), so fixing one alone breaks the balance. A consistent core (root retention 1.0, stage factor 1.14(1-0.42exp(-ttf/0.57)), hi_x 0.82) is documented in the plan but over-yields in the free run.
- Practical floor: Cycles disagrees with itself by MAE 0.17 (random 10% soil change), 0.74 at N=150 under a neighbouring weather cell, 1.4 under a neighbouring soil map unit. Engine N=150 error is 0.93.

### Growth law, settled 2026-10-18 (read before touching growth, partition or scalars)
Cycles' growth is simple: the paper's law at scalar 1.0 (crop-file RUE and TUE), the SI Eq. 8 shoot partition with a shared TTf50 of 0.42 (not a crop-file field; fitted on Cycles' realised shoot share to rms 0.0007 to 0.005 for corn, silage corn and sorghum, identical across site halves and N rates), and 40 percent of root growth leaving biomass (`root_retained_frac` 0.6, the 5/3 root input to soil). Adopted: `TTF50_SHOOT_PARTITION` 0.42, `ngf_faithful` 1.0 for corn, silage corn, sorghum and soybean (wheat keeps its tuned pair and `ttf50` 0.32 until checked). With Cycles' canopy, water and N factor forced, above-ground biomass matches at N>=150 (corn 1.002, silage 1.007, sorghum 1.002, soybean 1.016 at N=0); grain is 2.5 percent low (harvest index, fG timing residual; the engine uses the guide's HI law with Hk 1.3077 exactly, do not refit hi_slope); N=0 is 6 percent low even when forced. The earlier 0.955 scalar, the 'growth conversion 9 percent too high' finding and the inferred early-season stage term were all compensating the wrong TTf50 (the stage term stays opt-in via `growth_stage_a/c/tau`, do not use). Free-run cost, 94 sites versus the same morning's configuration: pooled correlation unchanged within 0.005 (all crops still above 0.88), but N=0 over-yields (bias corn +0.38, silage +0.96, sorghum +0.22 Mg/ha; MAE worse by 0.11 / 0.21 / 0.07, CIs exclude zero), N=150 and 400 mixed and mostly not significant (silage N=150 +0.109 [0.048,0.174]), soybean +0.008 [0.003,0.012]. Cause of the N=0 cost is a state the earlier early overshoot was hiding (engine mid-season N stress at N=0 is 0.493 against Cycles' 0.396 with equal plant N; free above-ground 1.137 against 0.936 forced); fix that next.

### Next work, in order
0. Criterion 1 is met on the 58-wheat-site and 94-site sets. Before the final report: confirm on the locked holdout, then the shared canopy (forcing Cycles' canopy is the largest remaining lever for corn, 22 to 34% of grain MAE) and early-season water stress (`corn_water_state_2026_10_17.py`; the engine is too water-stressed, which forces a tuned canopy water exponent, 0.3 vs measured 1.35, in the compensation-free package X, see plan 2026-10-18). Wheat still has northern cold sites 0.6 to 1.0 low (unchecked against the fixed reference).
0b. Paper and SI audit (`agricultural/AUDIT_PAPER_SI_2026-10-18.md`, every equation, mechanism and crop-file field checked against the engine): top open holes in order are (1) residue C:N is constant and the crop file's grain and straw N fields are unused, so the plant to residue N link is not closed (untested, plausible home of the missing year-to-year N stress); (2) DONE 2026-10-18 (Matt's call): the canopy plateau 0.99 x growth scalar 0.955 pair is replaced per crop by Cycles' measured canopy (`CANOPY_FAITHFUL`, plateau and Eq. 6 shape from unstressed Cycles days, growth scalar 1.0; corn 0.951, silage 0.946, sorghum 0.949, soybean 0.924). Cost: pooled correlation unchanged (at most -0.005), corn grain MAE +0.017 / +0.028 / +0.026 (bias now +0.16 / +0.21 / +0.07, to be attributed to a named mechanism, plausibly the growth-stage terms and harvest-index offset tuned while 0.955 was in place), silage MAE +0.025 / +0.077 / +0.113 at N=0/150/400 with the correct 85 percent harvest (CIs exclude zero; an earlier reported silage improvement was an artifact of the harvest bug), soybean and sorghum neutral. Attribution afterwards (24 sites, Cycles' states forced, `attrib_ag_2026_10_18.py`): with canopy, water and N stress all forced the engine's above-ground biomass is still +2.6 / +9.3 / +8.8% (corn) and +3 / +11 / +11% (silage) high at growth scalar 1.0, about +4% at 0.955 and about 0% at 0.92 (N=150, 400), so the daily growth conversion is about 9% too high, while forcing Cycles' water stress raises yield by 5 to 8%, so the engine's water stress is too strong; the two nearly cancel in the free run (corn yield ratio 1.00 / 1.01 / 1.01). So the 0.955 scalar was partly a real level constant, not only a plateau stand-in: the scalar was re-measured from forced states after the residue cover fix (2026-10-18, 24 sites, above-ground ratio): corn, silage and sorghum 0.955, soybean 0.92 (`ngf_faithful`). Paired 94-site change versus scalar 1.0: corn grain MAE gain +0.022 [0.012,0.034] / +0.050 [0.023,0.079] / +0.020 [-0.031,0.069] at N=0/150/400, silage +0.056 / +0.174 / +0.229 (CIs exclude zero, bias +0.64 / +0.71 / +0.62 Mg/ha), sorghum and soybean neutral (CIs include zero) but their free-run level drops (soybean bias -0.28 Mg/ha, about -9%; sorghum N=400 -0.59, about -7%), because their free canopy and water states are not Cycles'. Pooled correlations unchanged. The public pages' own crop dictionaries do not carry the new keys, so the pages keep their previous canopy; (3) SI.14 variable microbial C:N missing (small); (4) cold damage is a single threshold that ends the season; (5) soil temperature has no snow or residue insulation. Corn `canopy_shape` and `eix` in the crop dict are dead keys (overridden by `CANOPY_SHAPE_FORCE`, `CANOPY_EIX_FORCE`). Harvest index `hi_slope` 1.3077 against the crop file's 1.0 is an accurate empirical correction (rms 0.010 vs 0.065).
1. Leaching (Matt's second criterion, in progress): transport is fixed. Denitrification is a three-way compensation (plan 2026-10-18): engine nitrate 1.5x Cycles' at N=0, `SUBDAY_DENIT` saturation 1.25x to 1.3x too wet, law under-powered at high nitrate (0.49x of Cycles on Cycles' states at N=150, 0.86x at N=0). Cause found and tested: the engine's nitrate floor in July and August is 18 to 19 kg/ha at N=0 against Cycles' 8 to 9, because uptake is capped at 3% of the pool per day. Demand-limited uptake (`ENGINE_OVR="CROP.n_uptake_rate=None"`) nearly closes the leaching gap (means 4.9 / 14.6 vs Cycles 4.6 / 13.3, rms log 0.39 / 0.47) but grain over-yields by +0.5 / +0.8 Mg/ha (MAE 0.735 / 1.217); a 0.10 cap and a nitrate floor (0.5, 1.0 mg/kg) also fail on grain. NOT adopted. Attribution of why (plan 2026-10-18): once uptake is unrestricted the engine takes up 10 to 14% more N than Cycles and its mid and late season N stress is too weak (N=150: 0.988 vs 0.940 and 0.875 vs 0.808), so the 3% cap stands in for a supply limit. Paper Sec 2.5 (demand = new-growth N concentration, no compensatory uptake) is already what the engine does; paper Sec 2.7 says the water flux from each layer sets access to mineral N but gives no equation. The literal per-layer mass-flow reading is implemented as `N_ACCESS_MASSFLOW` (default False, with `CROP.n_uptake_rate=None`): season totals are plausible (N=0 supply 55 vs Cycles' uptake 44 kg/ha) but daily flux is far below peak demand and the crop starves (grain bias -1.2 / -2.6 Mg/ha). The missing equation is an open mechanism to work out ourselves (`MECHANISM_LOG.md`, 2026-10-18); the developers are not available to ask. Then refit the nitrate exponent of the denitrification law with `SUBDAY_DENIT` off. Also the infiltration-overflow stage still divides by sat + overflow (small).
2. Year-to-year N stress at N=150: mineralization versus uptake timing, using Cycles' daily mineral N.
3. Bring soybean, wheat, silage corn and the fifth crop to the same held-out standard (correlation above 0.8, several N rates).
4. Replace Rock Springs tripwires with multi-site regression guards; final report on the locked holdout.

## Scripts removed from agricultural/prototypes on 2026-10-23

Never imported by another script and never named in any tracked text file (99 scripts, 0.4 MB, plus the superseded Cycles 1.4.4 archive `agricultural/Cycles_debian_1.4.4 (1).zip`). They remain in git history.

- ceiling_swap.py
- co2_engine_2026_10_18.py
- corn_ag_root_daily_2026_10_17.py
- corn_agn_2026_10_19.py
- corn_bias_covariates_2026_10_17.py
- corn_canopy_clock_2026_10_17.py
- corn_canopy_diag_2026_10_17.py
- corn_canopy_extract_2026_10_17.py
- corn_canopy_form_test_2026_10_17.py
- corn_clock_rate_2026_10_17.py
- corn_components_2026_10_17.py
- corn_conversion_drivers_2026_10_17.py
- corn_early_growth_2026_10_17.py
- corn_evap_canopy_2026_10_17.py
- corn_evap_compare_2026_10_17.py
- corn_growth_lag_2026_10_17.py
- corn_hi_law_2026_10_17.py
- corn_layer_theta_2026_10_17.py
- corn_marginal_n_2026_10_17.py
- corn_mass_inventory_2026_10_17.py
- corn_nconc_2026_10_19.py
- corn_nresid_2026_10_19.py
- corn_nstress_law_check_2026_10_17.py
- corn_nstress_year_2026_10_17.py
- corn_shoot_partition_2026_10_17.py
- corn_transp_compare_2026_10_17.py
- corn_water_by_demand_2026_10_18.py
- corn_wue_implied_2026_10_17.py
- county_drought_2026_10_20.py
- cover_rye_detail_2026_10_21.py
- cs_traj_2026_10_19.py
- csresp_2026_10_19.py
- cycles_cn_2026_10_19.py
- denit_startofday_2026_10_20.py
- denit_states_2026_10_19.py
- denit_volat_forms_2026_10_19.py
- early_stress_compare.py
- eval_big2.py
- eval_loss.py
- eval_pair.py
- fe_engine_vs_cycles_2026_10_21.py
- fe_forms_2026_10_21.py
- growth_given_states.py
- harvest_dec31_pool_compare.py
- implied_rue_temp.py
- leach_decomp_2026_10_17.py
- leach_layers_2026_10_17.py
- leadin_modes.py
- mead_transp_attrib_2026_10_23.py
- monthly_terms_compare_n.py
- nbudget_2026_10_18.py
- nclose_cycles_2026_10_18.py
- netmin268.py
- netmin_attrib.py
- nflux_2026_10_18.py
- nitrate_profile_2026_10_21.py
- nitrif_forms_2026_10_19.py
- nitrif_layer_ratio_2026_10_19.py
- nlaw_denit.py
- nlayer_2026_10_18.py
- nmin_scorecard.py
- npool_attrib.py
- npool_year_2026_10_18.py
- nstress_feat_2026_10_19.py
- nunmet_2026_10_19.py
- offseason_2026_10_21.py
- offseason_fe_2026_10_21.py
- offseason_month_2026_10_21.py
- offseason_res_2026_10_21.py
- offseason_resp_2026_10_21.py
- ph_experiment_2026_10_20.py
- planting_pool_compare.py
- plantn_attrib.py
- potTR_check.py
- regional_params_l3.py
- regional_params_s3.py
- regional_params_s3c.py
- regionalize3.py
- regionalize4.py
- residue_audit_2026_10_18.py
- residue_data_2026_10_21.py
- satcheck.py
- ssurgo_soil_2026_10_20.py
- tempfactor_check.py
- water_attrib.py
- wheat_attrib_2026_10_22.py
- wheat_budget_2026_10_22.py
- wheat_canopy_extract_2026_10_17.py
- wheat_canopy_fit_2026_10_17.py
- wheat_clock_scan_2026_10_17.py
- wheat_cold_2026_10_17.py
- wheat_nbudget_2026_10_17.py
- wheat_nstate_2026_10_17.py
- wheat_resid_2026_10_17.py
- wheat_sink_2026_10_22.py
- wheat_temp_2026_10_19.py
- wheat_timeline.py
- wheat_traj_2026_10_19.py
- zeroTR_trigger.py
