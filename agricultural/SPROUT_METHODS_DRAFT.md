# How SPROUT was built

## 1. Purpose and thanks

SPROUT (Simulated Processes for Reasoning about Outcomes Under Treatments; in public, "a browser-based crop and soil simulator for teaching") is a daily-step crop, soil water, carbon and nitrogen model written in Python. It runs in a web browser through Pyodide, so a student can run 38 years of a crop at a chosen site with no installation. It simulates corn, silage corn, sorghum, soybean and winter wheat, with corn and soybean rotations, a cereal rye cover crop, tillage, irrigation, split nitrogen and manure.

SPROUT exists because of Cycles. Its purpose is to let students work with a model that behaves the way Cycles does, so we took Cycles as the reference throughout. We built it independently from the Cycles paper and supplement (Kemanian et al. 2024), the Cycles input and output documentation, and published science, and we used runs of Cycles v1.5.20 as the test of the result. In a small number of places the published sources were silent and we measured a constant on Cycles output. This document lists each of those places (Section 6), so that they can be replaced with documented values, and it records where our reading of a printed equation differs from what we implemented (Section 5), so that you can tell us if we have misread it.

Everything below was checked against the code and the data in the repository. Where something could not be checked, it says so.

## 2. How the build was organised

**Provenance classes.** Every constant and function in the engine is recorded in a ledger (`agricultural/PROVENANCE_LEDGER.md`, with a script that fails if any is missing), with a class:

- A: form and values documented in the paper, SI, Cycles documentation or a Cycles data file. We also use A for a few exact constants of Cycles that we identified with designed runs (snow, forage fraction).
- B: form and values from another published source.
- C: a documented or published form whose parameters we fitted to Cycles output.
- D: form and parameters both fitted to Cycles output, because no source gave them.
- E: our own assumption, convention or placeholder.
- O: a published form with one or two constants fitted to observations rather than to Cycles output.

The target was to leave nothing in class C or D. We have not reached it, and Section 6 lists every remaining item that depends on Cycles output, so the list is complete rather than a count.

**Order of work.** Each process was built from the sources first and compared with Cycles second. Where a quantity could only be set from Cycles, it is labelled and listed.

**Adoption rule.** A documented law replaces another if, at every nitrogen rate, pooled correlation with Cycles stays above 0.8 and the grain error rises by no more than about 0.05 Mg/ha. A change fitted to Cycles must show an improvement whose paired-bootstrap 95 percent interval on held-out sites excludes zero.

**Test sites.** Development used a 24-site quick set and 94 sites (`sitesets/fresh94.json`). No constant was fitted to the 94 sites, but they were used repeatedly to choose between options, so they are a development set and not a clean test. A further 100 sites (`sitesets/holdout.json`) are locked for a single final report and have not been run.

## 3. Inputs and the reference runs

Weather is the gridded daily record for 1980 to 2016 at the nearest 0.5 degree cell and soil is the nearest STATSGO2 profile. The Cycles reference runs use v1.5.20 with its hourly finite-difference hydrology option (HYDROLOGY_OPTION 1) and the curve number runoff method. Operation files set STANDING_RESIDUE_AT_HARVEST to 50 percent for corn, soybean and silage and 40 for wheat, RESIDUE_REMOVED to 0 for grain crops and MAXIMUM_SOIL_COVERAGE to 100. Cycles daily rows are end-of-day states, so in the comparison a day's flux in SPROUT acts on the previous row's state.

## 4. Process by process

Each subsection says what the sources state, what the engine does, the class, and where Cycles output or observations were used.

### 4.1 Evapotranspiration, runoff and soil water

Implemented as documented (class A): FAO-56 Penman-Monteith (agreement with Cycles reference ET within 0.4 percent, correlation 1.000); curve number runoff (SI.1 to SI.6, see Section 5 for our reading of two printed signs); Campbell's hydraulic conductivity and the sub-daily redistribution with travel time (paper Eqs. 1 and 2); the transpiration and water use efficiency growth terms. Root water uptake follows Campbell 1985 and CropSyst (class B). Soil hydraulic properties follow Saxton and Rawls 2006 (class B), with one option, the air-entry potential anchor, chosen by yield agreement with Cycles (class C).

- **Soil evaporation (class O).** The paper divides evaporative demand among canopy, residue, snow and soil using radiation interception but gives no formula for the soil term. The form and three constants were first measured on Cycles output, then tested against USDA NASS county yields, which we treat as the arbiter where they disagree with Cycles. Of six settings tested, the adopted law gave the best rainfed eastern corn (level 1.00 of observed, within-site r 0.50); the FAO-56 two-stage form gave 0.92 and 0.40. A law fitted to Mead tower evapotranspiration was tried and not adopted.
- **Residue cover and position (class A structure, class B cover law, one class E choice).** Surface residue is split into standing and flat. The standing share at harvest is the operation-file input; a tillage pass flattens the square root of its mixing efficiency of the standing residue (Cycles input guide). Ground cover is Fc = 1 - exp(-K M) (Gregory 1982). K is 0.40 per Mg/ha for corn, the upper end of the range we found for maize (about 0.30 in the WEPS documentation) and close to the 0.384 we saw in Cycles output; soybean uses the same value as an assumption (class E). Standing and flat residue decay at the same rate, which is what we measured in Cycles output (ratio 1.13).
- **Residue water store (class A structure, class B capacity).** The paper says rain wets residue first and that residue takes its share of evaporative demand. The engine holds a water store in the residue, filled by rain up to a capacity and emptied by reference evapotranspiration times cover times one minus canopy. The capacity is 3.10 kg water per kg, the maximal water content of maize stem particles (5 cm, 20 C) in Iqbal et al. 2013 (Table 2; wheat 2.33, soybean 2.16). This is an immersion value, so it is an upper bound for field residue.
- **Snow (class A by behaviour).** Rain and snow split at 1.0 C, degree-day melt over a triangular daily temperature wave (melt base -1.0 C, 2.5 mm per C) and sublimation equal to reference ET. The constants are those of Cycles, identified by designed runs that reproduce its snow water to 0.1 mm over 100 cases.
- **Moisture adjustment of the curve number (SI.7).** Described in words in the SI. We used the depth weighting in Williams et al. 2011 (partly class E).
- **Root distribution (class E).** Not given in the sources we have; exponential density with a 0.3 m scale. A CropSyst-style linear taper was built and tested and was worse against Cycles and against county yields.
- **Soil temperature.** Layered implicit heat conduction with a damping depth inside the range quoted in the SI (class B form, parameter inside that range). It has no snow or residue insulation, so winter soil is about 1.5 C colder than Cycles'. A simple lag filter is used only to set planting dates (class E).

### 4.2 Crop growth

Implemented as documented (class A): growth is the lesser of a radiation-limited and a transpiration-limited term (paper Eqs. 3 to 5) with crop-file efficiencies at a growth scalar of 1.0; the double-sigmoid canopy (Eq. 6) with the plant density adjustment (Eq. 7); thermal time, vernalization and photoperiod from the crop file; the shoot partition (SI Eq. 8); the planting window from the operation file.

Three things in the implementation go beyond the printed equations, and we list them so they are visible: radiation-limited growth is multiplied by a temperature ramp (the same ramp as transpiration unless the crop sets its own); the canopy used for growth on a given day is the previous day's canopy; and nitrogen stress (a nitrogen nutrition index) multiplies growth as well as slowing canopy expansion. The paper states that the rate of canopy change is reduced by N stress; we did not find a statement about the other points, so they are our choices (class E).

- **Harvest index (class A).** The guide gives HI = Hmax - (Hmax - Hmin) exp(-Hk fG) with Hk = m (1 - Hmin) / (Hmax - Hmin). With the crop-file values this gives 1.3077 for corn, silage and sorghum, 3.4 for soybean and 2.5 for winter wheat.
- **Shoot partition mid-point TTf50 (class O).** SI Eq. 8 needs TTf50. We found no printed value for it. 0.42 was fitted to Cycles' realised shoot share (a shared value for corn, silage and sorghum). We then tested it on measured above-ground biomass at the Mead towers (120 points, June to September): the squared relative error is 0.0264 at 0.30, 0.0103 at 0.42, 0.0115 at 0.50 and 0.0162 at 0.56, so the observations bracket 0.42 to 0.50. Because the original value came from Cycles, it is also listed in Section 6.
- **Canopy plateau per crop (class C).** With epsilon_ix = 1 and the paper's constants, Eq. 6 peaks near 0.99. Cycles' realised interception on unstressed days is lower for some crops, and we used plateau parameters of 0.95 for corn and silage, 0.924 for soybean, 0.949 for sorghum and 0.853 for winter wheat, fitted to Cycles output, with a senescence constant of -16. Using epsilon_ix = 1 with a senescence constant of -15 on 94 corn sites raised bias by 2 to 5 points and grain error by 0.02, 0.11 and 0.25 Mg/ha at N = 0, 150 and 400, so we kept the fitted plateaus. For reference, maximum interception measured at a Nebraska site (Kukal and Irmak 2020, Table 2) is 0.92 and 0.97 for short and long season maize, 0.99 for soybean, 1.00 for sorghum and 0.97 for winter wheat. Our corn and silage plateaus are inside that range; our soybean, sorghum and wheat plateaus are 5 to 12 percent below the measured maxima. County yield levels for soybean and wheat are already above the observations in both models, so we did not raise them. This is question 1 in Section 9.
- **Senescence timing of maize (class O).** The senescence term of Eq. 6 is moved later by 0.12 in thermal-time fraction, with the senescence clock accelerated by water and nitrogen stress, fitted to measured leaf area at the three Mead towers (maize 2001 to 2007, 80 points) and checked leaving one year and one site out. The stress term rests on a single stressed site.
- **CO2 effect (class A form, class O exponents).** The paper says efficiencies respond to CO2. The exponents are from free-air enrichment syntheses (Ainsworth and Long 2021): C3 crops 0.38 on both efficiencies (about +14 percent at 550 ppm), C4 crops 0.45 on water use efficiency and none on radiation use efficiency.
- **Root growth leaving the plant (class C).** Cycles output implies that about 40 percent of root growth does not stay in root biomass; this is an inference from the output, not a documented constant. The engine retains 0.6. Tests of 0.5 and 0.7 changed pooled correlation by less than 0.006.
- **Winter wheat clock (class A).** The thermal-time fraction is thermal time since planting over thermal time at maturity. For winter wheat the season-end thermal time in Cycles' output ranges from 1183 to 3226 degree days across 814 site-years (mean 1858), so the engine runs each season twice, once to find the season's own end and once to use it. This was the largest single gain for wheat.
- **Growth efficiency of wheat (open).** Unstressed wheat in SPROUT makes about 14 percent more biomass per unit of intercepted radiation than Cycles. A growth scalar of 0.95 is kept for wheat as a labelled suspect; removing it makes yield worse. We have not found the cause.
- **Silage harvest (class A by behaviour).** Harvest at 85 percent of maturity (operation file). Forage yield is 0.95 times above-ground biomass minus root: harvest.csv reports this ratio to within 0.0005 in 111 harvest rows at three sites, and designed runs changing RESIDUE_REMOVED and STANDING_RESIDUE_AT_HARVEST left it unchanged. We have not compared it with real stubble heights.
- **Cold damage (class E).** The documentation describes a cold damage factor that depends on temperature. We implemented a single-threshold rule (a night below the crop's cold damage threshold after flowering ends the crop). We did not implement the graded factor.

### 4.3 Nitrogen in the plant

- **Demand (class B).** The critical dilution curve of Lemaire, Jeuffroy and Gastal 2008 (corn and silage 3.4 and 0.37, sorghum 3.9 and 0.39, winter wheat 5.3 and 0.44), with the new-growth concentration read at the biomass reached without N stress (paper Sec 2.5) and luxury uptake allowed. An earlier scale on demand (0.70 to 0.75), measured on Cycles, was removed for corn, silage, sorghum and wheat.
- **Stress (class B form, class E constant).** Growth is proportional to the nitrogen nutrition index above a floor of 0.2 of the critical curve (the linear relation of relative growth rate to plant N concentration, Ingestad 1979 as cited by Lemaire et al. 2008). The floor is an assumption; we chose 0.2 because Cycles corn never dilutes below about that ratio, so it is not independent of Cycles.
- **Supply limit on uptake (class B form, class C exponent).** The paper says water flux determines access to mineral N and gives no equation. The engine uses the Godwin and Jones 1991 availability function (1 - exp(-kC), root length density times a soil water factor times 0.006 kg N/ha per cm of root). The water factor exponent is 1 where their text gives 2; we set it to 1 because 2 reduced yield too much when tested against Cycles. Doubling the 0.006 constant changes yield by under 1 percent.
- **Uptake and growth solved together (class B).** CropSyst 1994 Eqs. 29 and 30.
- **Legume path for soybean (class A mechanism, class D constants).** Soil N is taken first, fixation fills the unmet demand, and residue N comes from plant N (paper Sec 2.5). The N demand scale (0.74), plant N (203 kg/ha), grain share (0.54) and root share (0.065) were read from Cycles' harvest file over 857 soybean crop-years and are class D.
- **Other nitrogen constants read from Cycles (class C or D).** The share of plant N in the above-ground part (0.88) and the root N carried out with lost roots (0.12 of plant N for corn, 0.082 for wheat) were measured on Cycles. The grain share of above-ground N (0.70 for corn and sorghum, 0.75 for wheat) is a literature harvest index that we have not re-verified. The grain and straw N concentration fields of the crop file are not used.

### 4.4 Soil carbon, nitrogen and decomposition

The six-pool structure with first-order residue decay (SI Eqs. 10 to 14), the saturation factors fH and fD (SI.12 and SI.13), the saturation capacity of soil carbon as a function of clay (Hassink and Whitmore, as in Pravia et al. 2019), the tillage speed-up of decomposition and the 2 percent per day decay of its disturbance, and the moisture response as a Hill function with half-response 0.22 and power 3 (Cycles documentation) are implemented (class A and B).

- **Microbial carbon use efficiency (class A).** The SI gives 0.33 to 0.44. The engine uses 0.44 times the saturation factor fH. An earlier clay-dependent fit to Cycles was removed because it was neutral.
- **Saturation factor fH (class C).** SI Eq. SI.12 as we read it prints an exponent of 6 and no floor. The engine uses an exponent of 12 and a floor of 0.2, which we had fitted to Cycles' humification near saturation. On the 24-site quick set, corn and silage were essentially unchanged when we used 6 and no floor (grain MAE for corn 0.58 / 1.18 / 1.05 against 0.59 / 1.18 / 1.05 at N = 0 / 150 / 400). We did not complete the test for wheat. We ask in Section 9 which is intended.
- **Per-source efficiency and the aging factor fA.** The SI's per-source retention fractions (fra, frt, frz, frm) are folded into a single efficiency, and fA is set to 1.0 (a placeholder, class E).
- **Decay rates (mixed).** Surface residue decays as in CERES (Godwin and Jones 1991): 20 percent carbohydrate, 70 percent cellulose and 10 percent lignin at 0.8, 0.05 and 0.0095 per day times the environmental factor (class B). We note that the chapter's text gives 0.8 per day for carbohydrate while the Fortran listing printed in it uses 0.2; we used the text. The WEPS law of Steiner et al. 1999 is kept as an option and still governs buried root residue. The base rate of soil organic matter turnover is 0.00015 per day (Pravia et al. 2019, class B). The microbial turnover rate and the manure rate were back-calculated from Cycles output (class C), and the temperature optimum of the decomposition factor (37.5 C in the Campbell function of Stockle and Campbell 1989) was fitted to Cycles' composite factor (class C). The CERES law replaced WEPS on 2026-10-29: on 94 corn sites the paired grain error improved by 0.20 and 0.42 Mg/ha at N = 150 and 400 (intervals exclude zero) and worsened by 0.06 at N = 0, with silage and wheat neutral to slightly better. We have not yet checked the resulting residue cover against field data.
- **Pool carbon to nitrogen ratios.** Soil organic matter and microbes use 10.0 (the Cycles guide gives 10:1 for soil organic matter; for microbes the SI gives a range, see below). The C:N ratios of roots (52), manure (30) and above-ground residue (86) were read from Cycles (class D). Residue N is the plant's above-ground N minus grain N.
- **Variable microbial C:N (SI.14).** Implemented as a switch (on). We could not reconcile the printed mineral-N factor with the stated range (maximum 8.5 + 5.5 x 0.5 = 11.25, stated 14), and the printed factor increases with mineral N whereas we expected the opposite. We implemented the factor 0.5 / (1 + (N/8)^3), which decreases with mineral N; a switch for the printed form is in the code. Both reproduce the SI worked example (8.65 at N = 8 ppm). This is question 4 in Section 9.
- **Nitrification (class B).** Johnsson et al. 1987 (SOILN Eq. 9): transfer from ammonium to nitrate at k 0.2 per day, none when the nitrate to ammonium ratio exceeds 8, with SOILN's moisture response and the Stockle and Campbell temperature function.
- **Atmospheric nitrogen deposition (off by default).** An option adds 8 kg N/ha/yr, half ammonium and half nitrate, to the top layer daily. Cycles has none, so the default is zero and a student sees Cycles-like zero-nitrogen yields. We do not give a literature source for the 8 kg here; it is a placeholder for a typical Corn Belt value.

### 4.5 Nitrogen losses

- **Denitrification (class A form, amplitude 1.0).** The EPIC and APEX law as published (Kemanian and Williams, APEX upgrades Eqs. 1 to 4) with an amplitude of 1.0. An amplitude of 2.5 had been fitted to Cycles and was removed. At 1.0, SPROUT's denitrification is 0.3 to 0.4 times Cycles' for corn at 150 and 400 kg N. Two other published laws were tried with their constants unchanged: CERES (Godwin and Jones 1991 Eqs 15 to 18) matches Cycles' denitrification and leaching within 8 percent for corn at 150 kg N but gives 5.9 times Cycles' denitrification with no fertilizer; SOILN (Johnsson et al. 1987 Eqs 15 and 16) gives 0.3 times at high N. Neither is adopted. The Cycles documentation names POT_DENITRIF_RATE and DENITRIF_HALF_RATE only as calibration multipliers, so we could not apply the defaults.
- **Total nitrogen lost.** For corn the sum of leaching, denitrification and volatilization (per year, N = 0 / 150 / 400) is 8.9 / 38.7 / 177.9 kg N/ha in SPROUT and 9.9 / 46.0 / 190.2 in Cycles, so SPROUT loses about 10, 16 and 6 percent less in total. The partition differs more (Section 7).
- **Nitrous oxide (class A and class E).** The share of denitrified N is APEX Eq. 5, with no fitted constant (tested on 149,000 daily states of Cycles: ratio 0.079 against Cycles' 0.081). The share of nitrified N is a constant 0.4 percent. We could not find a published value that fixes this number, so it is an assumption (class E) that affects only the reported N2O. The emission factor at N = 150 is about 0.65 percent of applied N (IPCC default for EF1 is 1.0).
- **Volatilization (class B form, class C pH).** Daily NH3 loss = Kh F C_TAN / r_a (Genermont and Cellier 1997, Eqs. 3 to 5 and 13; Montes, Rotz and Chaoui 2009 for Ka and Kh; r_a from FAO-56). Soil pH is the one calibrated input, as Genermont and Cellier say it must be; we set it (5.5) by comparison with Cycles' volatilization at N = 150 and 400, so it is class C.
- **Nitrate transport (class B).** Godwin and Jones 1991 Eq. 1.
- **Application losses (class B).** IPCC fractions and Macnack et al. 2013.

### 4.6 Management

Tillage implements and fertilizer and manure composition are read from the Cycles data files (class A). Irrigation follows the documented automatic-irrigation rule. The cover crop uses the WinterRye crop-file values on the wheat configuration. Dated fertilizer applications are applied on the day given; a dose dated up to 60 days before a spring crop's planting day lands on planting day, and any dose that never meets a growing-season day is reported in the run output.

## 5. Places where we read a printed equation differently

The following are differences between the printed form and what we implemented, given as our reading. We would value your confirmation, and we have not assumed that any of them is an error rather than our misunderstanding.

1. SI.2 prints (Win - 0.2S)^2 / (Win - 0.8S). In the standard curve number form the denominator is Win + 0.8S. We implemented the standard form. As printed, the denominator is negative for Win between 0.2S and 0.8S.
2. SI.6 prints CN_b / (0.4 - 0.006 CN_b) for the wet-condition curve number. The denominator is zero at CN 66.7 and negative above it. We implemented the form with a plus sign, which keeps CN_wet(100) = 100.
3. Paper Eq. 1 prints the exponent as 2 + 3b where psi_e / psi_s appears, while defining theta = theta_sat (psi_e / psi)^(1/b). Campbell 1985 gives 2 + 3/b. We implemented 2 + 3/b. For b = 5 and psi_e / psi = 0.1 the two exponents give conductivities that differ by about 14 orders of magnitude, so the printed form would not be usable and we assume a typesetting issue.
4. SI.14 reproduces its worked example (8.65), but its maximum, 8.5 + 5.5 x 0.5 = 11.25, differs from the 14 stated in the text. We also do not know the intended direction of the mineral-N term (Section 4.4).
5. SI.10 writes the rhizodeposit term with C_ra where we read C_rz, and the text near it uses f_rm where we read f_rz. We implemented what we think is intended.

## 6. Everything that still depends on Cycles output

This is the complete list. Class C items use a documented or published form with parameters set from Cycles; class D items use a form and parameters set from Cycles; class E items are assumptions that were chosen with Cycles in view.

- Canopy plateau per crop (C), the shoot partition mid-point TTf50 of 0.42 (O, original value from Cycles) and the retained fraction of root growth 0.6 (C).
- The six-pool microbial turnover rate, manure decomposition rate, temperature optimum of the decomposition factor, and the fH exponent and floor (C).
- C:N of roots, manure and above-ground residue (D).
- Soybean N demand scale, plant N, grain share and root share (D); shares of plant N in above-ground tissue (0.88) and in lost roots (C).
- The N stress floor of 0.2 (E, chosen with Cycles in view).
- The exponent on soil water in the uptake supply term (C), and the air-entry potential anchor of the soil hydraulic option (C).
- The pH used in volatilization (C).
- Winter wheat: a growth scalar of 0.95 that hides a plateau growth efficiency about 14 percent high (labelled suspect).
- Soil evaporation form and constants (O, first measured on Cycles, then tested on county yields).

Two exact constants of Cycles that we found with designed runs and may be of use: forage yield is 0.95 times above-ground biomass minus root in every row of harvest.csv, and the snow constants (rain below 1.0 C, melt base -1.0 C, 2.5 mm per C) reproduce Cycles' snow water to 0.1 mm. The engine uses both.

## 7. How well it agrees

On 94 sites, 38 years each, with continuous crop chains (the final engine of 2026-10-29). Pooled correlation of annual grain yield with Cycles v1.5.20 at N = 0 / 150 / 400 kg N/ha (wheat 0 / 90 / 150, 60 sites):

| Crop | Pooled r | Bias | Grain MAE (Mg/ha) |
|---|---|---|---|
| Corn | 0.900 / 0.891 / 0.943 | -5% / 0% / -2% | 0.68 / 1.12 / 0.94 |
| Silage corn | 0.885 / 0.894 / 0.929 | +11% / +2% / +1% | 1.20 / 1.70 / 1.62 |
| Sorghum | 0.880 / 0.846 / 0.887 | -6% / -8% / -6% | 0.67 / 1.24 / 1.26 |
| Soybean | 0.944 | +10% (+0.31 Mg/ha) | 0.48 |
| Winter wheat | 0.909 / 0.854 / 0.847 | -1% / 0% / -4% | 0.38 / 0.65 / 0.80 |

Pooled correlation does not measure the response to nitrogen. On the last panel of response checks (run before the residue changes of 2026-10-29), the 0 to 150 kg response matched Cycles and the 150 to 400 kg response was 63 to 79 percent of Cycles' for corn, silage and sorghum.

Nitrogen losses relative to Cycles (corn, kg N/ha per year at N = 0 / 150 / 400): leaching 4.6 vs 4.6, 15.0 vs 13.3, 107.0 vs 84.8; denitrification 0.8 vs 2.6, 6.9 vs 18.3, 21.1 vs 65.8; volatilization 3.5 vs 2.7, 16.8 vs 14.4, 49.8 vs 39.6; nitrous oxide 0.24 vs 0.50, 1.21 vs 3.56, 4.04 vs 15.74.

Against observations, on NASS county yields (94 sites, 1982 to 2016, protocol in `EVALUATION_PROTOCOL_2026_10_28.md`), the within-site correlation of detrended yield is 0.43 for corn against 0.38 for Cycles (difference +0.033, 95 percent interval -0.008 to +0.073), 0.36 against 0.33 for soybean (+0.033 [+0.009, +0.057]), 0.39 against 0.34 for silage (+0.063 [+0.014, +0.123]) and 0.23 against 0.23 for wheat (+0.032 [-0.017, +0.079]). On the odd-numbered half of the sites in the sorted list the differences are corn +0.026 [-0.034, +0.080], soybean +0.025 [-0.013, +0.065], silage +0.059 [+0.018, +0.106] and wheat +0.043 [-0.018, +0.097]. The defensible statement is that the two models are comparable, with SPROUT better only for silage. The mean level is 0.98 of the observed county corn mean (Cycles 0.89), 1.45 for soybean (Cycles 1.31), 1.48 for wheat (Cycles 1.45) and 1.15 for silage (Cycles 1.10). In extreme years (eastern corn) both models exaggerate drought: 1988 observed -23 percent, SPROUT -35, Cycles -43; 2012 observed -12, SPROUT -39, Cycles -41; neither reproduces 1993 (observed -17, SPROUT +3, Cycles +7).

The Mead flux-tower comparison was last run on 2026-10-28 with settings that have since changed and has not been re-run, so we do not report its numbers here.

For scale, Cycles disagrees with itself by a mean absolute grain error of 0.17 Mg/ha when the soil properties are perturbed by 10 percent at random, 0.74 Mg/ha at N = 150 under a neighbouring weather cell and 1.4 Mg/ha under a neighbouring soil map unit. SPROUT's grain errors against Cycles (0.4 to 1.7 Mg/ha) are of the same order as the last two and larger than the first.

## 8. Where SPROUT and Cycles still differ

- Denitrification and nitrous oxide are about 0.3 to 0.4 times Cycles' for corn at 150 and 400 kg N (wheat 0.2 to 0.3, soybean 0.36), leaching is 1.0 to 1.3 times and volatilization 1.2 to 1.3 times. Total N lost is 6 to 16 percent lower in SPROUT (Section 4.5).
- Soil water was measured on 2026-10-29 before the CERES residue law: SPROUT was wetter than Cycles in every layer and month (by 0.01 to 0.05 m3/m3), with a surface residue carbon stock 3 to 8 times Cycles', a decomposition factor 1.2 to 1.5 times and winter respiration 2.3 times. The CERES law was adopted to address the stock; water and respiration after it are not re-measured.
- Sorghum runs 6 to 8 percent below Cycles at every N rate.
- Winter wheat: the growth scalar of 0.95 hides a plateau growth efficiency about 14 percent high, and wheat denitrification is 0.2 to 0.3 times Cycles'.
- Soybean and wheat county levels are 1.45 and 1.48 of observed, shared with Cycles.
- Drought years are over-reduced (2012: -39 percent against -12 observed).
- Not yet compared with Cycles as treatment effects: tillage, irrigation, split nitrogen, manure and the planting window; also the rye cover crop and wheat in rotation. In an earlier test (2026-10-23, not re-run) the irrigation response of denitrification had the wrong sign.
- Not implemented: Green-Ampt infiltration, bypass flow, the graded cold damage factor, grazing and multi-species mixtures, the SI's source-specific carbon efficiency multipliers, and use of the crop-file grain and straw N concentration fields.

## 9. Questions that would help most

1. The relation between Eq. 6 and the realised canopy interception (plateau per crop, any density term), which would settle the canopy plateaus of all five crops.
2. The base rates for microbial turnover and manure decomposition, and the temperature optimum, in the six-pool carbon model (Pravia et al. 2019 gives kx only), and whether the exponent in SI.12 is 6 with no floor.
3. The root nitrogen carried out of the plant with lost roots, how much of root growth is retained, and the C:N ratios used for roots, manure and residue.
4. The intended direction of the mineral-N factor in SI.14 and the intended maximum.
5. Soybean nitrogen demand and fixation rules, whether wheat canopy loss is tied to nitrogen stress, and how the grain and straw N concentration fields of the crop file enter the model.
6. The defaults behind the calibration multipliers POT_DENITRIF_RATE and DENITRIF_HALF_RATE, and the carbon term of denitrification. With the published APEX law (Rmax 32e-6, half-saturation 60 mg/kg, respiration threshold 50) SPROUT's total N lost is 6 to 16 percent below Cycles' for corn, and it leaches 1.0 to 1.3 times as much and denitrifies 0.3 to 0.4 times as much.
7. Confirmation of our reading of the printed forms in Section 5.

## 10. Reproducing it

Everything is in the public repository. `rhizo_engine.py` is the engine (the file keeps the name the model had before it was called SPROUT); `engine_api.py` is the interface; `agricultural/PROVENANCE_LEDGER.md` classifies every constant; `agricultural/prototypes/ENGINE_REBUILD_PLAN.md` holds the dated record of every test, including those that failed; `scorecards/` and `sitesets/` hold results and site lists.

## 11. References

Ainsworth, E. A., and Long, S. P. 2021. Free-air CO2 enrichment synthesis, Global Change Biology.

Campbell, G. S. 1985. Soil Physics with BASIC. Elsevier.

Genermont, S., and Cellier, P. 1997. A mechanistic model for estimating ammonia volatilization from slurry applied to bare soil. Agricultural and Forest Meteorology 88:145 to 167.

Godwin, D. C., and Jones, C. A. 1991. Nitrogen dynamics in soil-plant systems. In Modeling Plant and Soil Systems (Hanks and Ritchie, eds.).

Gregory, J. M. 1982. Soil cover prediction with various amounts and types of crop residue. Transactions of the ASAE.

Iqbal, A., Beaugrand, J., Garnier, P., and Recous, S. 2013. Tissue density determines the water storage characteristics of crop residues. Plant and Soil 367:285 to 299.

Johnsson, H., Bergstrom, L., Jansson, P.-E., and Paustian, K. 1987. Simulated nitrogen dynamics and losses in a layered agricultural soil. Agriculture, Ecosystems and Environment 18:333 to 356.

Kemanian, A. R., Shi, Y., White, C. M., Montes, F., Stockle, C. O., et al. 2024. The Cycles agroecosystem model: Fundamentals, testing, and applications. Computers and Electronics in Agriculture 227:109510.

Kukal, M. S., and Irmak, S. 2020. Light interactions, use and efficiency in row crop canopies under optimal growth conditions. Agricultural and Forest Meteorology 284:107887.

Lemaire, G., Jeuffroy, M.-H., and Gastal, F. 2008. Diagnosis tool for plant and crop N status in vegetative stage. European Journal of Agronomy 28:614 to 624.

Macnack, N., et al. 2013. Nitrogen application loss factors (as used in the repository).

Montes, F., Rotz, C. A., and Chaoui, H. 2009. Process modeling of ammonia volatilization from ammonium solution and manure surfaces: a review with recommended models. Transactions of the ASABE.

Pravia, M. V., Kemanian, A. R., Terra, J. A., Shi, Y., Macedo, I., and Goslee, S. 2019. Soil carbon saturation, productivity, and carbon and nitrogen cycling in crop-pasture rotations. Agricultural Systems 171:13 to 22.

Saxton, K. E., and Rawls, W. J. 2006. Soil water characteristic estimates by texture and organic matter for hydrologic solutions. Soil Science Society of America Journal.

Steiner, J. L., et al. 1999. Crop residue decomposition in no-tillage small-grain fields. Soil Science Society of America Journal.

Stockle, C. O., and Campbell, G. S. 1989. Simulation of crop response to water and nitrogen: an example using spring wheat. Transactions of the ASAE.

Williams, J. R., Kannan, N., Wang, X., Santhi, C., and Arnold, J. G. 2011. Evolution of the SCS runoff curve number method and its application to continuous runoff simulation.
