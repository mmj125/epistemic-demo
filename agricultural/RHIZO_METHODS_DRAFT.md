DRAFT, updated 2026-10-28. For review by Matt before it goes to anyone. Sections 2, 5, 6 and 9 were rewritten on 2026-10-28 for the current engine; sections 7 and 8 carry the scorecard of the same date. Each number is traceable to a script listed in `prototypes/INDEX.md` and to `PROVENANCE_LEDGER.md`.

# How Rhizo was built

## 1. What this is

Rhizo is a daily-step crop, soil water, carbon and nitrogen model written from scratch in Python (one engine file, `rhizo_engine.py`, plus a thin interface layer, `engine_api.py`). It runs in a web browser through Pyodide, so a student or scientist can run 38 years of a crop at a chosen site with no installation. It simulates corn, silage corn, sorghum, soybean and winter wheat, with corn and soybean rotations, a cereal rye cover crop, tillage, irrigation, split nitrogen and manure.

Its equations come from the Cycles paper and supplement (Kemanian et al. 2024), the Cycles input and output documentation, and published science (Campbell 1985, CropSyst, FAO-56, Saxton and Rawls 2006, Pravia et al. 2019, EPIC and APEX, Godwin and Jones 1991, Stockle and Campbell 1989, Macnack et al. 2013, IPCC). Cycles v1.5.20 was used as a test of the result and, where the published sources are silent, as a source of measurements. This document says which is which for every process.

## 2. The rules the build followed

**Where a number came from.** Every constant and function in the engine is classified in a ledger (`agricultural/PROVENANCE_LEDGER.md`, 170 constants and 88 functions, with a script that fails if any is missing):

- A: form and values documented in the paper, SI, Cycles documentation or a Cycles data file.
- B: form and values from another published source.
- C: a documented or published form whose parameters we fitted to Cycles output.
- D: form and parameters both fitted to Cycles output, because no source gave them.
- E: our own assumption, convention or placeholder.
- O: a published form with one or two constants fitted to real observations, not to Cycles output.

On 2026-10-28 no live item is class D and six rows are class C (listed in section 6). Most of the earlier class D and C items turned out, on a second look, to have a source: the Cycles guide, the SI, Pravia 2019, WEPS, Godwin and Jones 1991, SWAT or a measurement paper.

**Circularity.** Fitting a law to Cycles output and then reporting agreement with Cycles proves nothing. So the rule was: build each process from the sources first, compare with Cycles second, and fit to Cycles only where the sources are silent. A fitted element is labelled a suspect, with the source that would replace it.

**Adoption.** A documented law replaces a fitted one if, at every nitrogen rate, pooled correlation with Cycles stays above 0.8 and grain error rises by no more than about 0.05 Mg/ha. A change fitted to Cycles must show an improvement whose paired-bootstrap 95 percent interval on held-out sites excludes zero. Documented laws are swapped as a package, because in a system of compensating errors one-at-a-time swaps always look worse.

**Test sites.** Development used a small quick set and 94 sites that were never used to fit anything (`sitesets/fresh94.json`). A further 100 sites (`sitesets/holdout.json`) are locked for a single final report and have not been run.

## 3. Inputs and the reference runs

Weather is the gridded daily record for 1980 to 2016 at the nearest 0.5 degree cell. Soil is the nearest STATSGO2 profile. The reference runs of Cycles v1.5.20 use its hourly finite-difference hydrology option, the curve number runoff method and no flag. Cycles daily rows are end-of-day states, so a day's flux in the engine acts on the previous row's state.

## 4. Process by process

Each subsection gives what the sources state, what the engine does, the class of every item (Sec 2), and where Cycles output or observations were used and why. Classes are those of `PROVENANCE_LEDGER.md` on 2026-10-28.

### 4.1 Reference evapotranspiration, runoff and soil water

Documented and implemented as written (class A): FAO-56 Penman-Monteith (checked against Cycles, error 0.4 percent, correlation 1.000); curve number runoff (SI.1 to SI.6); Campbell's hydraulic conductivity and the sub-daily redistribution with travel time (paper Eqs. 1 and 2); the transpiration and water use efficiency growth section. Root water uptake at each layer's own potential follows Campbell 1985 and CropSyst (class B). Soil hydraulic properties are Saxton and Rawls 2006 (class B), with one option, the air-entry potential anchor, that was chosen by yield score against Cycles (class C).

- **Soil evaporation (class O).** The paper divides evaporative demand among canopy, residue, snow and soil by radiation interception but gives no formula for the soil term. The form and three constants were first measured on Cycles output and then tested against USDA county yields, which are the arbiter (Matt's rule, 2026-10-26): of six settings the adopted law gave the best rainfed eastern corn (level 1.00 of observed, within-site r 0.50). A law fitted to the Mead tower's canopy-free evapotranspiration was tried and not adopted because it moved the county level and correlation away from the observations. The FAO-56 two-stage form gave level 0.92 and r 0.40.
- **Residue cover and position (class A structure, class B cover law).** Surface residue is split into standing and flat. The standing share at harvest is the operation-file input (50 percent for corn, soybean and silage, 40 for wheat); a tillage pass flattens the square root of its mixing efficiency of the standing residue (Cycles input guide). Ground cover is Gregory 1982, Fc = 1 - exp(-K M), with K 0.40 per Mg/ha for maize (inside Gregory's 0.45 to 0.54 for complete samples, and consistent with the 0.384 we saw in Cycles output).
- **Residue water store (class A structure, class B capacity).** The paper says rain wets residues first and that residue takes its share of evaporative demand. The engine holds a water store in the residue, filled by rain up to a capacity and emptied by reference evapotranspiration times cover times one minus canopy. The capacity is 3.10 kg water per kg residue, the maximal water content of maize residue in Iqbal et al. 2013 (Plant and Soil 367:285, Table 2; wheat 2.33, soybean 2.16). It is an immersion value for 5 cm particles at 20 C, so an upper bound for field residue.
- **Snow (class B).** Rain and snow split at 1.0 C, degree-day melt over a triangular daily temperature wave with the SWAT defaults (melt base 0.5 C, 4.5 mm per C), and sublimation equal to reference ET (the paper's allocation of demand to snow). Earlier values (melt base -1.0 C, 2.5 mm per C) reproduced Cycles' snow water to 0.1 mm over 100 designed runs; the swap to the published defaults cost corn nothing and winter wheat 0.006 to 0.014 Mg/ha of grain error.
- **Moisture adjustment of the curve number (SI.7).** Described in words only. The depth weighting is from Williams et al. 2012, a related model's form (class A in form, partly E).
- **Root distribution (class E).** Not given in the sources. Exponential density with a 0.3 m scale. The CropSyst linear taper, which both the CropSyst manual and Stockle et al. 2003 describe, was built and tested, alone and with the Godwin and Jones squared water factor, and was worse against Cycles and against county yields, so the exponential form stays as an engine assumption supported by those tests.
- **Soil temperature.** A per-depth lag filter with constants kept inside the damping depth quoted in the SI (class B form, parameter inside the SI range).

### 4.2 Crop growth

Documented and implemented (class A): growth is the lesser of a radiation-limited and a transpiration-limited term (paper Eqs. 3 to 5) with the crop-file efficiencies at a growth scalar of 1.0; the double-sigmoid canopy (Eq. 6) with the plant density adjustment (Eq. 7); thermal time, vernalization and photoperiod from the crop file; the shoot partition (SI Eq. 8); the planting window from the operation file. The canopy response to water and nitrogen stress is the paper's form (Sec 2.5: the rate of canopy change is reduced by N stress and by nothing else), which replaced exponents measured on 86,000 day pairs of Cycles output.

- **Harvest index (class A).** The guide gives HI = Hmax - (Hmax - Hmin) exp(-Hk fG) with Hk = m (1 - Hmin) / (Hmax - Hmin). With the crop-file values Hk is 1.3077 for corn, silage and sorghum, 3.4 for soybean and 2.5 for winter wheat, which are the constants the engine carries. They were first found by fitting Cycles' harvest index (rms 0.010) and only later recognised as the documented slope.
- **Shoot partition mid-point TTf50 (class O).** SI Eq. 8 needs TTf50 and no source gives it. 0.42 was first fitted to Cycles' realised shoot share; it was then tested on measured above-ground biomass at the Mead towers (120 points, June to September), where the squared relative error is 0.0264 at 0.30, 0.0103 at 0.42, 0.0115 at 0.50 and 0.0162 at 0.56, so the observations bracket 0.42 to 0.50. Published root to shoot ratios prefer a lower value but compare standing roots, which exclude rhizodeposit and turnover that the engine books separately.
- **Canopy plateau per crop (class C).** The maximum canopy cover epsilon_ix is a crop parameter and the operation file sets MAXIMUM_SOIL_COVERAGE to 100. With epsilon_ix = 1 and the paper's constants Eq. 6 peaks near 0.99, but Cycles' realised interception on unstressed days is about 0.95 for corn and silage, 0.924 for soybean, 0.949 for sorghum and 0.853 for winter wheat. The engine uses those measured plateaus with the senescence constant -16. Testing the paper's form (epsilon_ix 1, c = -15) on 94 corn sites raised bias by 2 to 5 points and grain error by 0.02, 0.11 and 0.25 Mg/ha at N = 0, 150 and 400, so it was not adopted. Observed maximum interception at a Nebraska site (Kukal and Irmak 2020, Table 2) is 0.92 and 0.97 for short and long season maize, 0.99 soybean, 1.00 sorghum and 0.97 winter wheat: corn and silage fall inside that range, while soybean, sorghum and wheat are 6 to 13 percent below it. County yield levels for soybean and wheat are already above the observations, so the three were not raised. See question 1 in Sec 9.
- **Senescence timing of maize (class O).** The senescence term of Eq. 6 moved later by 0.12 in thermal-time fraction, with the senescence clock accelerated by water and nitrogen stress, fitted to measured leaf area at the three Mead towers (maize 2001 to 2007, 80 points) and checked leaving one year and one site out. It rests on a single stressed site for the stress term.
- **CO2 effect (class A form, class O exponents).** The paper says efficiencies scale with CO2. The exponents come from free-air enrichment experiments (Ainsworth and Long 2021): C3 crops 0.38 on both efficiencies (+14 percent at 550 ppm), C4 crops 0.45 on water use efficiency and none on radiation use efficiency.
- **Root growth leaving the plant (class C).** Cycles removes about 40 percent of root growth from biomass; the engine keeps 0.6. Tests of 0.5 and 0.7 changed pooled correlation by less than 0.006. Root carbon reaches the soil once; an earlier 5/3 factor counted lost roots twice and was removed on 2026-10-27.
- **Winter wheat clock (class A).** The thermal-time fraction is thermal time since planting over thermal time at maturity. For winter wheat that maturity changes with the season (1183 to 3226 degree days), so the engine runs the season twice, once to find the season's own maturity and once to use it. This was the largest single gain for wheat.
- **Growth efficiency of wheat (open).** Unstressed wheat makes about 14 percent more biomass per unit of intercepted radiation than Cycles. A growth scalar of 0.95 is kept for wheat as a labelled suspect; removing it makes yield worse. The cause is not found.
- **Silage harvest (class A).** Harvest at 85 percent of maturity (operation file). Forage yield is 0.95 of above-ground biomass: Cycles' harvest.csv reports exactly 0.9500 in every row, whatever RESIDUE_REMOVED (90 or 70) and STANDING_RESIDUE_AT_HARVEST (0, 50 or 100) are, so it is a constant of Cycles' forage harvest, confirmed by designed runs. We have not checked it against real stubble heights.

### 4.3 Nitrogen in the plant

- **Demand (class B).** The critical dilution curve of Lemaire, Jeuffroy and Gastal 2008 (corn and silage 3.4 and 0.37, sorghum 3.9 and 0.39, winter wheat 5.3 and 0.44), with new-growth concentration read at the biomass reached without N stress (paper Sec 2.5) and luxury uptake allowed. The scales measured on Cycles (0.70 to 0.75) were dropped for 1.0.
- **Stress (class B form, class E constant).** Growth proportional to the nitrogen nutrition index above a structural floor of 0.2 (relative growth rate linear in plant N concentration, Ingestad 1979 as cited by Lemaire et al. 2008). The floor is one assumption that no observation constrains, because the Mead towers and the county yields are nitrogen sufficient.
- **Supply limit on uptake (class B form, class C exponent).** The paper says water flux determines access to mineral N and gives no equation. The engine uses the Godwin and Jones 1991 availability function (1 - exp(-kC), root length density times a soil water factor times 0.006 kg N/ha per cm of root). The water factor exponent is 1, not their 2: the engine's spring soil is 0.01 to 0.02 m3/m3 too dry and 2 starves the crop. Doubling the 0.006 constant changes yield by under 1 percent, so the cap is not what limits the N response.
- **Uptake and growth solved together (class B).** CropSyst 1994 Eqs. 29 and 30.
- **Legume path for soybean (class A mechanism, class C constants).** Soil N first, fixation fills the unmet demand, residue N from plant N (paper Sec 2.5). The N demand scale of 0.74, plant N, grain share and root share were read from Cycles' harvest file over 857 soybean crop-years.
- **Lost-root N sink (class C).** The root nitrogen carried out with lost roots (a share of 0.12 of plant N for corn and 0.082 for wheat) was read from Cycles output.

### 4.4 Soil carbon, nitrogen and decomposition

The six-pool structure with first-order residue decay (SI Eqs. 10 to 14) and the saturation factors fH and fD (SI.12 and SI.13, class A); saturation capacity of soil carbon as a function of clay (Hassink and Whitmore, Pravia et al. 2019, class B); the tillage speed-up of decomposition and the 2 percent per day decay of its disturbance (class A); the moisture response as a Hill function with the Cycles documentation's half-response 0.22 and power 3 (class A).

- **Microbial carbon use efficiency (class A).** The SI states 0.33 to 0.44 depending on the saturation ratio, which is a maximum of 0.44 times fH = 1 - (Cs/Cx)^6. The engine uses 0.44; an earlier clay-dependent fit to Cycles, which is 0.44 at clay 0.2, was neutral against it and has been removed. The C-Farm humification coefficient (0.09 to 0.20) was tried in its place and rejected, because it belongs to a different flux in this pool structure (bias +40 percent at zero N).
- **Decay rates (mixed).** Residue decay follows the WEPS law of Steiner et al. 1999 (mass loss k times decomposition days; class B), and the base rate of soil organic matter turnover is Pravia 2019's 0.00015 per day (class B). The microbial turnover rate and the manure rate are still back-calculated from Cycles output (class C), because neither source gives them. The decomposition temperature response is the Campbell function (Stockle and Campbell 1989, c = 4) with its optimum of 37.5 C fitted to Cycles' composite factor (class C).
- **Pool carbon to nitrogen ratios (class B).** 10.0 for microbes and stabilised soil C (Cycles guide 10:1, SOILN). The SI's variable microbial C:N (Eq. SI.14) is not implemented. Residue N is the plant's above-ground N minus grain N.
- **Nitrification (class B).** Johnsson et al. 1987 (SOILN Eq. 9): transfer from ammonium to nitrate at k 0.2 per day, none when the nitrate to ammonium ratio exceeds 8, with SOILN's moisture response and the Stockle and Campbell temperature function.
- **Atmospheric nitrogen deposition (class O).** 8 kg N/ha/yr, half ammonium and half nitrate, added daily to the top layer. Measured deposition in Iowa agricultural fields is 7.7 kg (a lower bound); wet deposition in the upper Midwest is 3 to 7 kg. Cycles has no deposition, so this is the one place the engine deliberately departs from Cycles in the nitrogen budget: it raises zero-nitrogen yield by about 0.27 Mg/ha for corn.

### 4.5 Nitrogen losses

- **Denitrification (class A).** The EPIC and APEX law as published (Kemanian and Williams, APEX upgrades Eqs. 1 to 4) with an amplitude of 1.0. An amplitude of 2.5 had been fitted to Cycles. At 1.0 the nitrate leaching of corn is 6.7 and 19.0 kg N/ha/yr at N = 0 and 150, inside the published range for tile-drained Corn Belt corn, and denitrification is 0.6 to 0.7 times Cycles'.
- **Nitrous oxide (class A and class B).** The share of denitrified N is APEX Eq. 5, with no fitted constant (tested on 149,000 daily states of Cycles: ratio 0.079 against Cycles' 0.081). The share of nitrified N is a constant 0.4 percent (nitrification N2O yield of 0.1 to 0.5 percent, Bateman and Baggs 2005, recalled and not checked); the logistic in saturation that had been fitted to Cycles was removed. The emission factor at N = 150 is about 0.9 percent of applied N (IPCC EF1 1.0).
- **Volatilization (class B form, class C pH).** Daily NH3 loss = Kh F C_TAN / r_a (Genermont and Cellier 1997, Eqs. 3 to 5 and 13; Montes, Rotz and Chaoui 2009 for Ka and Kh; r_a from FAO-56), linear in wind as the friction-velocity form requires. Soil pH is the one calibrated input, as Genermont and Cellier say it must be.
- **Nitrate transport (class B).** Godwin and Jones 1991 Eq. 1.
- **Application losses (class B).** IPCC fractions and Macnack et al. 2013.

### 4.6 Management

Tillage implements and fertilizer and manure composition are read from the Cycles data files (class A). Irrigation follows the documented automatic-irrigation rule. The cover crop is the WinterRye crop-file values on the wheat configuration (untested against Cycles). Dated fertilizer applications are applied on the day given; a dose dated up to 60 days before a spring crop's planting day lands on planting day, and any dose that never meets a growing-season day is reported in the run output.

## 5. Where the published sources are wrong or silent

Errors found in the printed sources (the engine uses the corrected form in each case):

1. SI.2 prints a minus sign in the runoff denominator that makes it negative; the standard form has plus 0.8S.
2. SI.6 prints CN_wet with a sign that is negative for curve numbers above 67; the correct sign is plus.
3. Paper Eq. 1 prints the exponent as 2 + 3b; the correct exponent is 2 + 3/b. Checked numerically: with the printed exponent the conductivity is ten orders of magnitude too small.
4. SI.14 reproduces the SI's own worked example, but its maximum (11.25) disagrees with the stated maximum (14).
5. SI.10 prints one residue carbon term with the wrong subscript.

Quantities that were measured on Cycles earlier and now have a source (2026-10-27 and 2026-10-28): soil evaporation (county yields), the canopy stress response (paper Sec 2.5), N demand (Lemaire et al. 2008), the N stress curve, the supply cap on uptake (Godwin and Jones 1991), residue decay (WEPS, Steiner et al. 1999), nitrification (Johnsson et al. 1987), volatilization (Genermont and Cellier 1997, Montes et al. 2009), nitrate transport, the CO2 exponents (FACE meta-analysis, Ainsworth and Long 2021), denitrification amplitude (APEX, 1.0) and N2O (IPCC, APEX), the N2O share from nitrification (constant 0.4 percent), snow (SWAT defaults), residue water capacity (Iqbal et al. 2013), the microbial C use efficiency (SI, 0.44) and the harvest index slope. The last one deserves a note for the developers: the engine's slope constants (1.3077, 3.4, 2.5) were first found by fitting and were later seen to equal Hk = m (1 - Hmin) / (Hmax - Hmin) with the crop file values.

## 6. What is still measured on Cycles, and what we would ask

Six items are still fitted to Cycles output (class C), and a few have a source that conflicts with Cycles:

- the crop canopy plateau. The paper's Eq. 6 with epsilon_ix = 1 peaks near 0.99, but Cycles' realised interception on unstressed days is about 0.95 for corn and silage (0.924 soybean, 0.949 sorghum, 0.853 winter wheat). Is there a factor between Eq. 6 and the interception, such as Eq. 7 with a plant density other than 1? Measured maxima at a Nebraska site (Kukal and Irmak 2020) are 0.92 to 0.97 for maize, 0.99 soybean, 1.00 sorghum and 0.97 wheat.
- the six-pool base rates for microbial turnover and manure decomposition, and the temperature optimum (37.5 C) of the decomposition factor.
- the share of root nitrogen carried by the roots that leave the plant (0.12 for corn, 0.082 for wheat) and the retained fraction of root growth (0.6).
- soil hydraulic option for the air-entry potential, and the exponent on soil water in the nitrogen uptake supply term.
- soybean nitrogen demand (a scale of 0.74 on the Lemaire curve).
- winter wheat: a growth scalar of 0.95 hides a plateau growth efficiency about 14 percent high.

Two exact constants of Cycles that we found by designed runs and that may be of use: forage yield is 0.9500 times above-ground biomass in every row of harvest.csv whatever RESIDUE_REMOVED and STANDING_RESIDUE_AT_HARVEST are, and the snow constants (rain below 1.0 C, melt base -1.0 C, 2.5 mm per C) reproduce Cycles' snow water to 0.1 mm. The engine uses the first and has moved to the SWAT defaults for the second.

## 7. How well it agrees

On 94 sites not used to fit anything, 38 years each, with continuous crop chains. Pooled correlation of annual grain yield with Cycles v1.5.20 at N = 0 / 150 / 400 kg N/ha (wheat 0 / 90 / 150):

| Crop | Pooled r | Bias | Grain MAE (Mg/ha) |
|---|---|---|---|
| Corn | 0.907 / 0.859 / 0.902 | +12% / +7% / +6% | 0.66 / 1.34 / 1.36 |
| Silage corn | 0.876 / 0.894 / 0.927 | +30% / +5% / +3% | 1.55 / 1.75 / 1.65 |
| Sorghum | 0.891 / 0.813 / 0.838 | +9% / -5% / 0% | 0.66 / 1.37 / 1.53 |
| Soybean | 0.945 | +9% (+0.29 Mg/ha) | 0.47 |
| Winter wheat (60 sites) | 0.902 / 0.851 / 0.833 | +14% / +4% / -1% | 0.43 / 0.66 / 0.79 |

The positive bias at zero nitrogen is mostly the 8 kg N/ha/yr of atmospheric deposition that Rhizo includes (measured in Iowa, 7.7 kg) and Cycles does not. Silage at N=0 is +12% without it.

Nitrogen losses relative to Cycles (corn, kg N/ha per year at N = 0 / 150 / 400): leaching 6.7 vs 4.6, 19.0 vs 13.3, 115.8 vs 84.8; denitrification 0.84, 0.72 and 0.60 of Cycles'; volatilization 1.26, 0.98 and 0.99; nitrous oxide 0.63, 0.48 and 0.39. Rhizo's leaching sits inside the published range for tile-drained Corn Belt corn (8 to 29 kg at low to high N in Minnesota, 29 to 48 in Iowa) and its nitrous oxide emission factor at 150 kg N is about 0.9 percent of applied N (IPCC 1.0). Denitrification was lowered from an amplitude fitted to Cycles to the published one, which is why it is below Cycles'.

Against observations (re-run on the final engine, 2026-10-28): on NASS county yields (94 sites, 1982 to 2016) the engine's within-site correlation of detrended yield is 0.43 for corn against 0.38 for Cycles (difference +0.041, 95 percent interval -0.006 to +0.085), 0.36 against 0.33 for soybean (+0.034 [+0.010, +0.057]), 0.38 against 0.34 for silage (+0.062 [+0.003, +0.130]) and 0.21 against 0.23 for wheat (+0.012 [-0.041, +0.063]). The engine's level is 1.01 of the observed county corn mean (east 1.03, west 0.83), and 1.45 for soybean, 1.53 for wheat and 1.17 for silage, so soybean and wheat are too high in both models. Against the Mead flux towers (US-Ne1, Ne2, Ne3, gridded weather), the engine is no longer as close as Cycles: grain mean absolute error is 1.10 against 0.86 Mg/ha over 10 site-years (it was 0.91 against 0.86 on 2026-10-23), and above-ground biomass 3.28 against 2.34 Mg/ha over 15. The engine's mean evapotranspiration is nearer the towers than Cycles' at Ne1 (4.94 against 5.34 mm/day, tower 3.81) and equal at Ne2 and Ne3, but both models are 16 to 47 percent high because the gridded weather is warmer, drier and windier than the towers. The new gap is not yet attributed; the changes since 2026-10-23 that raise yield are atmospheric N deposition, the evaporation law and the residue store.

How much disagreement is normal: Cycles disagrees with itself by a mean absolute grain error of 0.17 Mg/ha when the soil is perturbed by 10 percent at random, 0.74 under a neighbouring weather cell and 1.4 under a neighbouring soil map unit. The engine's errors of 0.5 to 1.7 are in that range.

## 8. Where the engine and Cycles still differ

- Bias is negative at most sites, largest at high-yield sites and at 400 kg N/ha. With Cycles' own water, canopy and N states forced into the engine, above-ground biomass matches at N of 150 and above and grain is 2.5 percent low. The remaining error is the engine's water stress being too strong (6 to 10 percent) because spring soil water is 0.01 to 0.02 m3/m3 too dry, built by soil evaporation about 10 percent high and residue evaporation 30 to 50 percent low.
- The yield response from 150 to 400 kg N/ha is 63 to 79 percent of Cycles'. Pooled correlation hides this. The cause is a coupled shortfall in canopy, water and N together.
- Denitrification is 0.75 times and nitrous oxide 0.5 times Cycles' at N of 150 and above; the irrigation response of denitrification has the wrong sign.
- Winter wheat: the growth scalar of 0.95 hides a plateau growth efficiency about 14 percent high.
- Untested: the rye cover crop against Cycles; wheat in rotation; Green-Ampt infiltration, bypass flow, comammox, grazing and multi-species mixtures are not implemented.

## 9. What would help most

1. The relation between Eq. 6 and the realised canopy interception (plateau per crop, any density term), which would settle the canopy plateau of all five crops.
2. The base rates for microbial turnover and manure decomposition, and the temperature optimum, in the six-pool carbon model (the Pravia 2019 tables give kx only).
3. The root nitrogen carried out of the plant with lost roots, and how much of root growth is retained.
4. Soybean nitrogen demand and fixation rules, and whether wheat canopy loss is tied to nitrogen stress.
5. Confirmation of the three sign and exponent corrections in section 5.

## 10. Reproducing it

Everything is in the public repository. `rhizo_engine.py` is the engine; `engine_api.py` the interface; `agricultural/PROVENANCE_LEDGER.md` classifies every constant; `agricultural/prototypes/ENGINE_REBUILD_PLAN.md` holds the dated record of every test, including those that failed; `scorecards/` and `sitesets/` hold the results and site lists. The live simulator is at https://mmj125.github.io/epistemic-demo/agricultural/prototypes/simulator.html.
