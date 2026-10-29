DRAFT, 2026-10-28, for Matt to edit before sending. Attach `RHIZO_METHODS_DRAFT.md` (or its .docx).

Subject: An independent reimplementation of Cycles from the paper and SI, and six questions

Dear Dr. Kemanian and the Cycles team,

I am building a browser-based crop simulator for classrooms, and its engine (called SPROUT) is a from-scratch Python reimplementation of the Cycles equations. I wrote it from the 2024 paper and supplement, the Cycles input and output documentation, and the published science behind them, and I use Cycles v1.5.20 as the test set, not as the training set. The attached document says, process by process, which parts come from which source.

How close it is. Over 94 sites and 38 years, pooled correlation of annual grain yield with Cycles is 0.90 / 0.89 / 0.94 for corn at 0 / 150 / 400 kg N/ha, 0.88 / 0.85 / 0.89 for sorghum, 0.89 / 0.89 / 0.93 for silage, 0.94 for soybean, and 0.91 / 0.85 / 0.85 for winter wheat (60 sites). Against USDA county yields (94 counties, 1982 to 2016) its year-to-year agreement is comparable to Cycles' (0.43 against 0.38 for corn, 0.36 against 0.33 for soybean), and better than Cycles' only for silage on a held-out half of the sites. Against the Mead flux towers it was slightly further from the measured grain than Cycles was when I last ran it (mean error 1.1 against 0.9 Mg/ha), and I have not yet traced why.

Where it falls short. Denitrification and nitrous oxide are 0.3 to 0.4 times Cycles' (I use the published APEX law), total nitrogen lost is close to yours but leaching is 1.0 to 1.3 times, both models exaggerate drought years, and winter wheat carries a plateau growth efficiency that is too high.

Seven things I could not get from the documents, in the attached list: the relation between Eq. 6 and the realised canopy interception (about 0.95 for corn where Eq. 6 peaks near 0.99), the base rates for microbial turnover and manure decomposition and the decomposition temperature optimum, the root nitrogen carried out with lost roots, soybean nitrogen demand, the link between wheat canopy loss and nitrogen stress, the defaults behind POT_DENITRIF_RATE and DENITRIF_HALF_RATE (with the published APEX law SPROUT loses the same total nitrogen as Cycles but leaches more and denitrifies less), and confirmation of three sign and exponent corrections I made in the SI.

Two things I found that may be useful: forage yield is exactly 0.95 of above-ground biomass in harvest.csv whatever RESIDUE_REMOVED and STANDING_RESIDUE_AT_HARVEST are, and the harvest index slope constants I first fitted are exactly the guide's Hk.

Everything, including every test that failed, is in the public repository, and you can run it at https://mmj125.github.io/epistemic-demo/agricultural/prototypes/simulator.html. I would be grateful for any corrections.

With thanks,
Matt Johnson
