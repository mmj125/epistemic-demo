# Testing an independent Python reimplementation against Cycles

Short version: a from-scratch Python engine, built only from the published Cycles paper and SI plus public sources (FAO-56, Saxton and Rawls, CropSyst, SWAT, RothC) and back-fitting to Cycles output where nothing is published. It contains no Cycles code, binary or output. We would like you to try to break it.

## What to do (about 10 minutes)
1. Open `agricultural/prototypes/head-to-head.html` on the epiSTEMic site (not linked from the home page).
2. Pick a tile site, or upload your own Cycles `.weather` and `.soil` files (the engine then runs on exactly your inputs).
3. Choose corn or soybean, a nitrogen rate and Cycles version (v1.5.20 recommended). Download the zip of Cycles input files.
4. Run Cycles on them yourself (v1.5: `./Cycles NAME`, no `-b` flag; or use the Colab notebook linked on the page).
5. Drop Cycles' output files back on the page. Nothing leaves your browser. The page checks the engine read the same weather and soil as Cycles, then overlays yearly and daily results.

## Where it is accurate (Cycles v1.5.20, identical inputs, continuous corn 1980-2016)
- 16 tuning sites plus 12 held-out sites never used in fitting.
- Fertilized corn grain (150 kg N/ha): mean error about 1.0 to 1.2 Mg/ha (about 15%), year-to-year correlation about 0.8.
- Rock Springs sample scenarios, correlation: corn 0.73, soybean 0.88, silage corn 0.83, winter wheat 0.28.

## Where it is weak (please confirm or correct)
- Unfertilized corn: error about 0.9 Mg/ha, correlation 0.56 to 0.68.
- Nitrogen losses: leaching about 4x off; volatilization badly off at dry sites (Kansas 21 vs 76 kg N/ha); denitrification within about 2x.
- Winter wheat does not meet our classroom bar. Pasture and cover crops are not validated.

## Questions where your answer would help most
The remaining gaps are quantities the paper does not give. Full list with evidence: `QUESTIONS_FOR_DEVS.md`. The top ones:
1. How is soil nitrate leaching transported between layers, and how does Cycles keep NH4 un-nitrified in dry soil (our Kansas volatilization miss)?
2. What reduces radiation-use efficiency from the crop file's maximum to a day's actual value (we apply a flat 0.785 after the water/radiation minimum)?
3. What is the pasture cutting trigger, and how are mixed stands handled?
4. Residue evaporation and the cold-damage canopy reset: exact forms.

Contact: Matt Johnson, mmjohnson0505@gmail.com.
