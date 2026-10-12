# Decision key for the last accuracy round (2026-10-12)

Baseline: 16 tuning sites + 12 held-out, Cycles v1.5.20, after the carbon-saturation supply fix (c1b000d).

1. Kansas / Texas / Arkansas water and nitrate. 1a surface wetness engine vs Cycles: engine wetter by >0.1 -> 1b evaporation (off >15%: fix evaporation/residue link; else runoff/infiltration); wetness matches -> 1c denitrification rate at equal wetness (engine >2x: add texture term; else nitrate pool too large -> branch 2/3).
2. Kansas / Georgia volatilization. 2a NH4 pool after fertilizer: engine NH4 gone in ~2 weeks, Cycles persists -> add moisture term to nitrification; pools match -> refit volatilization by texture.
3. Leaching misses (Arkansas, Illinois). 3a annual drainage off >25% -> water, go to 1; matches -> 3b nitrate by layer: wrong depth -> layer transport; matches -> supply timing.
4. Unfertilized corn year-ranking. 4a net mineralization year correlation <0.6 -> weather response of respiration; >=0.6 -> 4b N uptake at 0 N: engine >1.5x -> tighten low-supply N stress; else report as known limit.
5. Ship gate: held-out not worse; 150 kg N grain MAE <=1.25; 15/16 pattern checks and Rock Springs scenarios unchanged; revert otherwise and record.
6. Stop rule: one fix attempt per branch; then re-measure, update ACCURACY.md and FOR_CYCLES_DEVS.md, send.

## Results log
- 2026-10-12 Test 1a (surface wetness, engine vs Cycles, 1983-1999): mean difference Kansas -0.03, Texas -0.02, Arkansas +0.03 (Iowa +0.05, with a heavy wet tail: 70% of days above 0.65 saturation vs 39%). Wetness matches at the three problem sites, so the key goes to 1c.
- Test 1c (denitrification rate law fed Cycles' own nitrate pool and wetness): exponent 3 gives rms log error 0.70 over 16 sites; exponent 6 to 7 gives 0.52 to 0.53 (Kansas still 2x high). End-to-end with the engine's own pools the best exponents did not help (denit rms log 0.92 -> 0.95 to 0.97; Kansas 46 -> 32 vs 7.9, Minnesota and Texas better, Iowa worse 89 -> 111 vs 79, leaching mean 8.8 -> 6.7). Ship gate not met; exponent left at 3. Conclusion: the rate law is not the main error. Cycles' implied rate at equal wetness is about 10x lower at Kansas, Carolina and Georgia (sandy, low organic matter) than at clay sites, which a single wetness curve cannot capture.
- Pools: Dec 31 mineral N, Cycles / engine: Kansas 878/779, Iowa 471/322, Arkansas 137/33, Texas 67/6, Illinois 101/108, Minnesota 171/185. Crop uptake matches (ratio 0.96 to 1.03) except Kansas 1.45 and Texas 1.14. So the Texas and Arkansas gaps are nitrate left after the season, not rates or uptake.
