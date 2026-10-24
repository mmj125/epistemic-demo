DRAFT, 2026-10-24. For review by Matt before it goes to anyone. Numbers are from the repository at commit 00cfcee and from `PROVENANCE_LEDGER.md`; each is traceable to a script listed in `prototypes/INDEX.md`.

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

**Circularity.** Fitting a law to Cycles output and then reporting agreement with Cycles proves nothing. So the rule was: build each process from the sources first, compare with Cycles second, and fit to Cycles only where the sources are silent. A fitted element is labelled a suspect, with the source that would replace it.

**Adoption.** A documented law replaces a fitted one if, at every nitrogen rate, pooled correlation with Cycles stays above 0.8 and grain error rises by no more than about 0.05 Mg/ha. A change fitted to Cycles must show an improvement whose paired-bootstrap 95 percent interval on held-out sites excludes zero. Documented laws are swapped as a package, because in a system of compensating errors one-at-a-time swaps always look worse.

**Test sites.** Development used a small quick set and 94 sites that were never used to fit anything (`sitesets/fresh94.json`). A further 100 sites (`sitesets/holdout.json`) are locked for a single final report and have not been run.

## 3. Inputs and the reference runs

Weather is the gridded daily record for 1980 to 2016 at the nearest 0.5 degree cell. Soil is the nearest STATSGO2 profile. The reference runs of Cycles v1.5.20 use its hourly finite-difference hydrology option, the curve number runoff method and no flag. Cycles daily rows are end-of-day states, so a day's flux in the engine acts on the previous row's state.

## 4. Process by process

Each subsection gives what the sources state, what the engine does, and where a fit to Cycles output was needed and why.

### 4.1 Reference evapotranspiration, runoff and soil water

Documented and implemented as written: FAO-56 Penman-Monteith (checked against Cycles, error 0.4 percent, correlation 1.000); curve number runoff (SI.1 to SI.6); Campbell's hydraulic conductivity and the sub-daily redistribution with travel time (paper Eqs. 1 and 2); root water uptake at each layer's own potential (Campbell 1985 and CropSyst, class B); Saxton and Rawls 2006 soil hydraulic properties.

Fitted to Cycles, and why:

- **Soil evaporation (class D).** The paper says evaporative demand is divided among canopy, residue, snow and soil by radiation interception but gives no formula for the soil term. We measured the response on Cycles output. A published alternative (FAO-56 two-stage, and CropSyst's form) was built and tested, including against flux towers at Mead, Nebraska; neither improved spring water.
- **Residue cover (class C).** The form is Gregory 1982, Fc = 1 - exp(-A M). We found that Cycles' own interception by residue follows 1 - exp(-0.384 M_flat - 0.084 M_standing), and 0.384 matches Gregory's maize value within 4 percent, so the form and magnitude are published. The engine has one residue pool, so it carries the blend, 0.27. The rain-interception term for residue has no source and is fitted (class D).
- **Snow (class D).** Rain and snow split at 1 C, sublimation equal to reference ET and a melt law, matched to Cycles to 0.1 mm over 100 designed experiments, because no equation is published.
- **Moisture adjustment of the curve number (SI.7).** Described in words only in the paper and SI. We used the depth weighting from Williams et al. 2012, which is a related model's form, not Cycles' (class E in part).
- **Root distribution and soil temperature.** Not given in the sources. Root distribution is our assumption (E). Soil temperature is a per-depth lag filter with its constants kept inside the damping depth quoted in the SI.

### 4.2 Crop growth

Documented and implemented: growth is the lesser of a radiation-limited term and a transpiration-limited term (paper Eqs. 3 to 5) with the crop-file radiation use efficiency and transpiration use efficiency at a growth scalar of 1.0; the double-sigmoid canopy (Eq. 6, constants 6, -20, -16, 16 for every crop) with the plant density adjustment (Eq. 7); thermal time, vernalization and photoperiod from the crop file; the shoot partition (SI Eq. 8); harvest index (SI Eq. 9); the planting date window from the operation file.

Fitted to Cycles, and why:

- **Shoot partition constant TTf50 (class C).** SI Eq. 8 needs a mid-point TTf50 and the SI does not give its value. Fitted on Cycles' realised shoot share (0.42, rms 0.001 to 0.005). An earlier version used stage terms to hide a wrong TTf50; those were removed.
- **Harvest index slope (class C).** The crop file gives kHI = 1.0. With the guide's law and the post-flowering biomass share, 1.0 under-predicts Cycles' harvest index by 0.064; 1.3077 fits (rms 0.010 over 517 seasons). We do not know what Cycles does differently, so this is an empirical correction.
- **Canopy plateau per crop (class D).** The paper says the maximum interception is a crop parameter but the crop file does not list it. We measured the maximum on Cycles' unstressed days for each crop (winter wheat 0.853).
- **Canopy response to water and N stress (class D).** The paper says N stress reduces the rate of canopy change; the form of the water and N effects is not given. The exponents (1.35 for water, 3.25 for N) were measured on 86,000 day pairs of Cycles' interception.
- **CO2 effect (class D exponent).** The paper says efficiencies scale with CO2; the exponent (0.197 on water use efficiency, 0 on radiation use efficiency) was measured on Cycles runs at fixed CO2.
- **Root growth leaving the plant (class D).** Cycles removes about 40 percent of root growth from biomass before it reaches the soil (we keep 0.6 and send 5/3 of root mass to soil carbon); read from Cycles output for all crops.
- **Winter wheat clock.** The paper and SI define the thermal-time fraction as thermal time since planting over thermal time at maturity. For winter wheat that maturity changes with the season (1183 to 3226 degree days), so the engine runs the season twice, once to find the season's own maturity and once to use it. This is documented and is the largest single gain for wheat.
- **Growth efficiency of wheat (open).** The engine's unstressed wheat growth makes about 14 percent more biomass per unit of intercepted radiation than Cycles does. We keep a growth scalar of 0.95 for wheat as a labelled suspect. Removing it makes yield worse. The cause is not found.

### 4.3 Nitrogen in the plant

Documented: N demand from the Lemaire dilution curve with the crop-file concentration and slope, new-growth concentration set for growth without water stress, luxury uptake allowed with no compensation for past demand, and (paper Sec 2.5) legumes fixing N only where the soil cannot supply demand, with no stress. The legume path (soil N first, fixation fills the unmet demand, residue N from plant N) is implemented that way.

Fitted to Cycles, and why:

- **N demand scale (class D).** Cycles' realised demand is 0.69 to 0.77 of the crop-file dilution curve at every biomass class. The paper does not mention this, so we carry a scale (0.70 for corn, 0.74 for soybean, 0.75 for wheat).
- **N stress function (class D).** The sources say stress follows the ratio of aboveground N concentration to the critical curve but give no curve; we measured it on 167,000 daily Cycles records (R2 0.894).
- **Supply limit on uptake (class D).** The paper says water flux determines access to mineral N and gives no equation. We built the literal per-layer mass-flow reading, the CropSyst form, and the Stockle and Campbell equations. Each starved the crop or failed to match Cycles. We use a cap of 3 percent of the reachable pool per day, kept as a suspect. This was the process we could least explain from sources.
- **Soybean N constants (class D).** Plant N (203 kg N/ha), grain share (0.54), root share (0.065) and the residue split were read from Cycles' harvest file over 857 soybean crop-years. The mechanism is the paper's; the three constants are not given.
- **Uptake and growth solved together (class B).** CropSyst 1994 Eqs. 29 and 30.

### 4.4 Soil carbon, nitrogen and decomposition

Documented: the six-pool structure with first-order residue decay (SI Eqs. 10 to 14); saturation capacity of soil carbon as a function of clay (Kemanian and Stockle 2010); the tillage speed-up of decomposition and the decay of tillage disturbance; the moisture response as a Hill function with the Cycles documentation's half-response 0.22 and power 3; the temperature response as the Campbell function (Stockle and Campbell 1989) with c = 4; and, since the Pravia et al. 2019 paper was added, the decomposition saturation function and the base rate (0.00015 per day) as published.

Fitted to Cycles, and why:

- **Residue and microbial rate constants and carbon to nitrogen ratios (class D).** The paper's parameter table lists reference rates without values and we found no public value. Back-calculated from Cycles output files. Pravia 2019 gives the soil organic matter rate but not the residue or microbial rates.
- **Humification fraction and microbial efficiency (class C/E).** The SI's humification formula cannot represent Cycles' behaviour at saturation, where Cycles still humifies 12 to 17 percent of decomposed carbon. We carry a clay-dependent fraction fitted to Cycles, and a placeholder microbial efficiency.
- **Variable microbial C:N (SI.14).** Not implemented; a constant 9.7 measured from Cycles' pools is used. Effect about 10 percent on immobilisation per unit carbon.
- **Nitrification (class B form, class D terms).** The temperature factor is Stockle and Campbell Eq. 11. The moisture and NO3:NH4 ratio terms have no source; the DAYCENT and Stockle and Campbell forms were tested and reproduced Cycles' daily layer states with R2 0.74, 0.78 and 0.57, against 0.99 for the fitted logistic. We use the fitted one and label it.

### 4.5 Nitrogen losses

- **Denitrification (class A form, class C amplitude).** The EPIC and APEX law as published (Kemanian and Williams, APEX upgrades Eqs. 1 to 4) is used with no fitted terms except one amplitude of 2.5 on the whole law, which has no source and is a suspect. The Cycles documentation names a potential denitrification rate as a calibration multiplier with no default.
- **Nitrous oxide from denitrification (class A).** APEX Eq. 5, with no fitted constant. Tested on Cycles' own daily states over 149,000 denitrification days: Cycles' N2O to denitrification ratio averages 0.081, Eq. 5 gives 0.079.
- **Nitrous oxide from nitrification (class D).** Fitted logistic in saturation; no source found.
- **Volatilization (class D).** The temperature slope (0.1456 per degree C) is close to the thermodynamic expectation (about 0.12), but the wind and moisture terms have no source.
- **Nitrate transport (class D).** Leaching is proportional to the saturated layer volume (ratio to Cycles 0.96 to 1.03).
- **Application losses (class B).** IPCC fractions and Macnack et al. 2013.

### 4.6 Management

Tillage implements and fertilizer and manure composition are read from the Cycles data files (class A). Irrigation follows the documented automatic-irrigation rule. The cover crop is the WinterRye crop-file values on the wheat configuration (untested against Cycles). The tillage mixing of moisture, texture, carbon and residue is described in words (Sec 2.6) and its details are our own.

## 5. Where the published sources are wrong or silent

Errors found in the printed sources (the engine uses the corrected form in each case):

1. SI.2 prints a minus sign in the runoff denominator that makes it negative; the standard form has plus 0.8S.
2. SI.6 prints CN_wet with a sign that is negative for curve numbers above 67; the correct sign is plus.
3. Paper Eq. 1 prints the exponent as 2 + 3b; the correct exponent is 2 + 3/b. Checked numerically: with the printed exponent the conductivity is ten orders of magnitude too small.
4. SI.14 reproduces the SI's own worked example, but its maximum (11.25) disagrees with the stated maximum (14).
5. SI.10 prints one residue carbon term with the wrong subscript.

Quantities the sources do not give and we measured (everything classed D or C above): soil evaporation, snow, the canopy plateau and stress exponents, the CO2 exponents, TTf50, the harvest index slope, the N demand scale, the N stress curve, the supply cap on uptake, the residue and microbial decomposition rates and C:N ratios, the nitrification moisture and ratio terms, the N2O share from nitrification, volatilization, nitrate transport, and the denitrification amplitude. These are the 18 class D and 7 class C items in the ledger.

## 6. What the measured constants are, honestly

When Cycles output was used we measured a relationship in designed runs or in daily states and fitted a parameter. That is a statement about Cycles, not about the world. The consequence is that agreement with Cycles on these processes is partly built in, and the real test of each is whether it works on observations or on sites and years the fit never saw. We therefore report the processes whose form comes from sources separately from those that were fitted, and list for each fitted item the source that would replace it:

- crop-file maximum canopy cover and the plateau (developers)
- TTf50 and the harvest index constants (developers)
- the potential denitrification rate multiplier and the supply cap on N uptake (developers, or Godwin and Jones availability functions)
- the residue and microbial decomposition rates and C:N ratios (Pravia 2019 tables or the parameter file)
- the residue as a water-holding layer (a published source; the paper is silent)
- the nitrification ratio term and volatilization wind terms (published models)

## 7. How well it agrees

On 94 sites not used to fit anything, 38 years each, with continuous crop chains. Pooled correlation of annual grain yield with Cycles v1.5.20 at N = 0 / 150 / 400 kg N/ha (wheat 0 / 90 / 150):

| Crop | Pooled r | Bias | Grain MAE (Mg/ha) |
|---|---|---|---|
| Corn | 0.959 / 0.921 / 0.965 | -9% / 0% / -6% | 0.47 / 0.95 / 0.85 |
| Silage corn | 0.937 / 0.920 / 0.954 | -9% / -5% / -7% | 0.88 / 1.70 / 1.61 |
| Sorghum | 0.945 / 0.887 / 0.925 | -14% / -5% / -11% | 0.51 / 1.09 / 1.16 |
| Soybean | 0.959 | -0.04 Mg/ha | 0.33 |
| Winter wheat (60 sites) | 0.927 / 0.874 / 0.871 | 0% / +3% / -1% | 0.35 / 0.65 / 0.74 |

Nitrogen losses relative to Cycles (corn, kg N/ha per year at N = 0 / 150 / 400): leaching 4.9 vs 4.6, 15.3 vs 13.3, 93.1 vs 84.8; denitrification 2.6 vs 2.6, 13.8 vs 18.3, 50.2 vs 65.8; volatilization 3.0 vs 2.7, 14.2 vs 14.4, 38.1 vs 39.6; nitrous oxide 0.3 vs 0.5, 1.7 vs 3.6, 7.0 vs 15.7.

Against observations: on NASS county yields (94 sites) the engine's within-site correlation is 0.43 against 0.38 for Cycles, and the engine's level is 0.93 of the observed; against the Mead flux towers the engine's yields are as close to the tower measurements as Cycles'. Both models run 16 to 47 percent high on evapotranspiration there, because the gridded weather is warmer, drier and windier than the towers.

How much disagreement is normal: Cycles disagrees with itself by a mean absolute grain error of 0.17 Mg/ha when the soil is perturbed by 10 percent at random, 0.74 under a neighbouring weather cell and 1.4 under a neighbouring soil map unit. The engine's errors of 0.5 to 1.7 are in that range.

## 8. Where the engine and Cycles still differ

- Bias is negative at most sites, largest at high-yield sites and at 400 kg N/ha. With Cycles' own water, canopy and N states forced into the engine, above-ground biomass matches at N of 150 and above and grain is 2.5 percent low. The remaining error is the engine's water stress being too strong (6 to 10 percent) because spring soil water is 0.01 to 0.02 m3/m3 too dry, built by soil evaporation about 10 percent high and residue evaporation 30 to 50 percent low.
- The yield response from 150 to 400 kg N/ha is 63 to 79 percent of Cycles'. Pooled correlation hides this. The cause is a coupled shortfall in canopy, water and N together.
- Denitrification is 0.75 times and nitrous oxide 0.5 times Cycles' at N of 150 and above; the irrigation response of denitrification has the wrong sign.
- Winter wheat: the growth scalar of 0.95 hides a plateau growth efficiency about 14 percent high.
- Untested: the rye cover crop against Cycles; wheat in rotation; Green-Ampt infiltration, bypass flow, comammox, grazing and multi-species mixtures are not implemented.

## 9. What would help most

1. The crop-file maximum canopy cover and the TTf50, harvest index and N demand constants Cycles uses. These would replace seven fitted values with documented ones.
2. The potential denitrification rate multiplier and the access-to-mineral-N rule in Sec 2.7, the two fitted items we could least reproduce from sources.
3. The rate constants and C:N ratios for the residue and microbial pools.
4. Confirmation of the three sign and exponent corrections in section 5.

## 10. Reproducing it

Everything is in the public repository. `rhizo_engine.py` is the engine; `engine_api.py` the interface; `agricultural/PROVENANCE_LEDGER.md` classifies every constant; `agricultural/prototypes/ENGINE_REBUILD_PLAN.md` holds the dated record of every test, including those that failed; `scorecards/` and `sitesets/` hold the results and site lists. The live simulator is at https://mmj125.github.io/epistemic-demo/agricultural/prototypes/simulator.html.
