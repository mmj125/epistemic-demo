DRAFT, 2026-10-31, for Matt to edit before sending. Attach `SPROUT_METHODS_DRAFT.pdf`.

Subject: An independent reimplementation of Cycles from the paper and SI, and seven questions

Dear Dr. Kemanian and the Cycles team,

I am building a browser-based crop simulator for classrooms, and its engine (called SPROUT) is a from-scratch Python reimplementation of the Cycles equations. I wrote it from the 2024 paper and supplement, the Cycles input and output documentation, and the published science behind them, and I use Cycles v1.5.20 runs as the test of the result. In a few places the documents were silent and I set a constant from Cycles output; the attached document lists each of them, so that they can be replaced with documented values, and says process by process which parts come from which source.

How close it is. Over 94 development sites and 38 years, pooled correlation of annual grain yield with Cycles is 0.91 / 0.89 / 0.94 for corn at 0 / 150 / 400 kg N/ha, 0.87 / 0.86 / 0.91 for sorghum, 0.89 / 0.89 / 0.93 for silage, 0.96 for soybean, and 0.91 / 0.85 / 0.84 for winter wheat at 0 / 90 / 150 (60 sites). Because I chose between options on those sites, I also kept 100 sites locked and ran them once, before the canopy change described below (so those numbers describe the model of 2026-10-30 and are not re-scored): 99 had a Cycles harvest, and the correlations were 0.92 / 0.91 / 0.95 for corn, 0.92 / 0.88 / 0.90 for sorghum, 0.90 / 0.90 / 0.94 for silage, 0.95 for soybean and 0.95 / 0.87 / 0.85 for wheat. The lowest 95 percent lower bound is 0.80 (wheat at 150 kg N/ha). Against USDA county yields (94 counties, 1982 to 2016) its year-to-year agreement is comparable to Cycles' (0.43 against 0.38 for corn, 0.36 against 0.33 for soybean), and better than Cycles' only for silage on a held-out half of the sites. I have not yet re-run the comparison with the Mead flux towers on the current version, and I did not compare the locked sites with observations.

Where it falls short. Denitrification and nitrous oxide are 0.3 to 0.4 times Cycles' (I use the published APEX law), total nitrogen lost is 6 to 14 percent below yours for corn, leaching is 1.0 to 1.3 times (up to 1.6 for silage and wheat on the locked sites), on the development sites sorghum at no nitrogen is 13 percent low and soybean 8 percent high, both models exaggerate drought years in the county comparison, and winter wheat carries a plateau growth efficiency that is about 14 percent high.

One thing I did get from your runs rather than the documents, and would like you to confirm: designed runs of Cycles under constant weather match Eq. 6 with c = -16 and d = 15 (the paper prints -15 and 16) on TTf = thermal time / (MATURITY_TT - THERMAL_TIME_TO_EMERGENCE), taken half a day back, with an error ten to a hundred times smaller than with the printed constants, for corn, silage, sorghum and soybean. It also agrees with leaf area measured at the Mead towers, and it improved agreement with Cycles for four crops.

Things I could not get from the documents, in the attached list: the relation between Eq. 6 and the realised canopy interception (about 0.95 for corn where Eq. 6 peaks near 0.99), the base rates for microbial turnover and manure decomposition and the decomposition temperature optimum, the root nitrogen carried out with lost roots, whether N_MAX_CONCENTRATION is meant as a maximum curve (Cycles' realised above-ground N is about 0.7 to 0.76 of it for corn and soybean), the link between wheat canopy loss and nitrogen stress, the defaults behind POT_DENITRIF_RATE and DENITRIF_HALF_RATE (with the published APEX law SPROUT loses a little less total nitrogen than Cycles, leaches more and denitrifies less), and confirmation of how I read five printed forms in the paper and SI, which I may well have misread.

Two things I found that may be useful: forage yield is exactly 0.95 of above-ground biomass in harvest.csv whatever RESIDUE_REMOVED and STANDING_RESIDUE_AT_HARVEST are, and the harvest index slope constants I first fitted are exactly the guide's Hk.

Everything, including every test that failed, is in the public repository, and you can run it at https://mmj125.github.io/epistemic-demo/agricultural/prototypes/simulator.html. I would be grateful for any corrections.

With thanks,
Matt Johnson
