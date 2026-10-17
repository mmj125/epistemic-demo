# epiSTEMic

Browser-based computational science investigations (grades 6 to undergrad). Python runs in the browser via Pyodide, no backend, no login. Static site on GitHub Pages from `main`. Pre-funding proof of concept; accounts, LMS passback and any backend are deferred to a future hired engineer. Do not scaffold them.

Full history of every decision through 2026-10-17 is in `CLAUDE_ARCHIVE_2026-10-17.md` (691 KB, search it, do not read it whole). Check it before re-deriving anything old, and treat any number in it as possibly stale until checked against code or data.

## Working with Matt

- Lead with what is wrong or missing, then give a concrete path forward. Stress-test, do not echo, do not flatter.
- No em or en dashes. No titles of the form "Phrase: longer phrase".
- Conserve usage. Ask before anything large.
- "Do X" means act, no option menu. A question ("what would you do") means a short ranked list with a recommendation.
- When told to continue autonomously: run experiments, report one short paragraph. Do not stop to ask. Do not run more than the budget Matt sets.
- Adopt a change only if the held-out paired-bootstrap CI excludes zero. Report a negative result in one line.
- When blocked, go back to the sources (equations, inputs, paper, SI, literature, Cycles output). That found the one real gain on 2026-10-17; tuning terms found none.

## Agricultural unit: the current job

Goal: a from-scratch Python reimplementation of Cycles (`agricultural/prototypes/cycles_engine_validate.py`) accurate enough to replace it, measured against Cycles v1.5.20 on identical weather and soil.

**Done when** (Matt, 2026-10-17; my reading, confirm if wrong):
1. Five crops reach correlation above 0.8 against Cycles on held-out sites, at multiple N rates where N matters.
2. Leaching is much better (today: rms log error 0.6 at N=150 and 0.4 at N=400 on the 94 fresh sites; engine leaches about 0.7x Cycles at N=400).

Which five crops is not yet fixed. Candidates with Cycles reference: corn, soybean, winter wheat, silage corn, plus one more (sorghum or pasture species). Decide with Matt before building a reference for a new one.

Model only. No UI, pedagogy, lesson copy or classroom framing until the engine is accurate.

### Rules
1. No calibration factor that masks a mechanism error. Attribute the gap (force Cycles' states into the engine), fit the mechanism from Cycles' own daily output, keep factors at 1.0. Factors still carried (silage corn 0.67, wheat 1.15 was removed) are suspects.
2. No site is special. Rock Springs is a crude crash guard only. Quote only multi-site results: 94 fresh sites (`sitesets/fresh94.json`), 24-site quick set, paired bootstrap, `scorecard.py`. `sitesets/holdout.json` (100 sites) is locked until the final report.
3. Quote N=0 results only from the continuous chain (`LEAD_YEARS=continuous`); short lead-ins over-yield unfertilized corn.
4. Check any figure against code or data before relying on it. Stale numbers have misled us repeatedly.
5. Before each substantial step: expected change and why, the contingency, and whether a higher-level diagnostic should come first.
6. Do not repeat the same kind of step after two failures; change kind (attribution, input audit, structural change).
7. Before a new mechanism, read the sources: `GenericCrops.crop` (all fields), the Cycles guide (`git clone --depth 1 https://github.com/PSUmodeling/Cycles`, read `docs/input.md`, `docs/output.md`), the paper and SI (committed PDFs, `git show origin/main:<file>`), Cycles daily and annual output, `ENGINE_REBUILD_PLAN.md`, `REFIT_PLAN.md`, `QUESTIONS_FOR_DEVS.md`. State which were checked.
8. Recommend only what is best, not what continues the thread.

### Current state (2026-10-17, held-out unless noted)
- Corn, 94 fresh sites, continuous chain, no regional map, factor 1.0: grain MAE 0.444 / 0.936 / 0.742 Mg/ha at N=0/150/400, bias +0.07 / +0.21 / -0.18, correlation about 0.84 / 0.81 / 0.90.
- Corn N demand: new-growth N concentration is read at the biomass the crop would have without N stress (paper Sec 2.5), scale 1.0, aboveground N stress law (REFIT row 14b), uptake about 3% of the pool per day (`n_demand_ref`, `n_stress_ag_basis`, `n_uptake_rate`).
- Wheat: canopy form H adopted (`canopy_form="H"`), documented harvest index law with real post-anthesis growth share, factor 1.0, 16 held-out sites N=0 MAE 0.369, N=150 1.318. Use `FALLN=60` for continuous wheat (spring-only N is bistable in Cycles).
- Soybean: factor 1.0, harvest index fitted from Cycles (hi_x 0.5, hi_o 0.311, slope 0.58), N=0 bias -3.6%, site-mean MAE 0.23. Silage corn within 7 to 13% free, 1 to 3% with states forced.
- Attribution (24 sites, corn): forcing Cycles' canopy removes 29/34/22% of grain MAE at N=0/150/400, N stress 10/15/1%, mineral pool 0/7/0%, water stress makes it worse (engine is under-stressed on water and compensated elsewhere). All four states forced still leave 13 to 47%: the daily growth conversion and level.
- Losses: held-out N loss budgets match Cycles at N=0/150 on average, engine leaches too little at N=400. Denitrification about 0.64 to 0.70 of Cycles (rate law fits 0.54 on Cycles' own states, so the error is the states feeding it: layer-1 saturation, nitrate). Volatilization at N=400 about 0.75x. Year-to-year agreement of N losses is weak (within-site corr 0.3 to 0.4).
- Root cause of what remains at N=150: engine year-to-year N stress varies too little (sd 0.016 to 0.024 vs 0.036, corr 0.3) and the canopy is too large; the system is a set of compensating errors (evaporation too high, residue cover too low, canopy too big, root retention 0.6, harvest index offset), so fixing one alone breaks the balance. A consistent core (root retention 1.0, stage factor 1.14(1-0.42exp(-ttf/0.57)), hi_x 0.82) is documented in the plan but over-yields in the free run.
- Practical floor: Cycles disagrees with itself by MAE 0.17 (random 10% soil change), 0.74 at N=150 under a neighbouring weather cell, 1.4 under a neighbouring soil map unit. Engine N=150 error is 0.93.

### Next work, in order
1. Leaching (Matt's second criterion): attribute leaching against Cycles' `N.txt` and `water.txt` (drainage, nitrate by layer, timing), at N=150 and 400, before changing anything.
2. Year-to-year N stress at N=150: mineralization versus uptake timing, using Cycles' daily mineral N.
3. Bring soybean, wheat, silage corn and the fifth crop to the same held-out standard (correlation above 0.8, several N rates).
4. Replace Rock Springs tripwires with multi-site regression guards; final report on the locked holdout.

### How to run
- Cycles v1.5.20 lives in `/tmp/cycles-run15` (not committed; CC BY-NC-ND, never commit its binary or output). `/tmp` is wiped on container reprovision; ask Matt to re-supply the release, `curl` of `https://github.com/PSUmodeling/Cycles/releases/download/v1.5.20/Cycles_debian_1.5.20.zip` works. Run Cycles with no flag.
- Multi-site harness: `run_validation_multisite.py` (env `BIGSET`, `ENGINE_OVR="CROP.key=value;..."`, `N_LEVELS`, `YEAR_STEP`, `LEAD_YEARS=continuous`, `REGIONAL=0`, `OUT_JSON`). 94 sites take about 10 minutes on 4 cores. Paired comparison: `paired_fr_2026_10_17.py BASE NEW`. Attribution with forced Cycles states: `corn_n0_attrib_2026_10_17.py` (`MODES=free,minn,nstress,canopy,water,all`).
- After any engine change run `agricultural/prototypes/sync_engine_pages.py` (rebuilds the embedded engines in `engine-demo.html`, `model-validation.html`, `head-to-head.html`).
- Validate Pyodide-facing glue with the exact embedded Python run in CPython, and a mocked pyodide in headless Chromium. Two concurrent `pyodide.runPythonAsync` calls share one global namespace: always `await` them in sequence.
- Delete Cycles output after parsing; keep disk free.

### Key files
- `agricultural/prototypes/ENGINE_REBUILD_PLAN.md` (dated entries, newest last), `REFIT_PLAN.md`, `QUESTIONS_FOR_DEVS.md`, `scorecards/`, `sitesets/`, `agricultural/ACCURACY.md`.
- Reference PDFs on `main`: Kemanian et al. 2024 paper and `agricultural/SI.pdf`, C-Farm papers, Saxton and Rawls 2006, Lemaire 2008, Macnack 2013, FAO-56 chapter 8, CropSyst papers.
- Public pages (`engine-demo.html`, `model-validation.html`, `head-to-head.html`) carry the engine but not the regional grain factor. Do not link `head-to-head.html` or `model-validation.html` from the splash page.
- Licensing: Cycles is CC BY-NC-ND 4.0. The engine is independently built from the published paper, SI and public sources, not from Cycles code. Permission from the developers is unconfirmed; "free to end users" does not resolve the noncommercial clause because epiSTEMic is a for-profit company. Never commit Cycles binaries or generated output.

## Other units (all static, Pyodide or plain JS)

- **Anthropology** (`anthropology/`, live): 5 mystery specimens (MS11 to MS14, MS1), 5-tab investigation, randomized end-of-unit `assessment.html` (seeded PRNG, instructor key auto-computed), AI formative feedback via Cloudflare Worker (`cloudflare-worker/worker.js`, key held server-side, Gemini). Data: 478-specimen limb dataset, 111-specimen CSG dataset from Duke (open, no license needed). Instructor page is not linked from student pages.
- **Meteorology** (`meteorology/`, live): 5-tab guided investigation over `energy-balance-sandbox.html` (iframe deep links `?var=&region=&type=&run=1&embed=1`). CERES EBAF 2001 to 2025 and ERA5 (t2m, sst, siconc, tp, strd), coarse 2 degree plus fine 1 degree tiles, gzip int16. Instructor page not built.
- **Engineering** (`engineering/`, in progress): cantilever truss tool (`truss-designer.html`) and 7-tab `investigation.html`; load is 0.75 kg (7.3575 N) per face; score = deflection, cost ($1/cm rod plus $10/connector), peak member force (N). The bridge designer lives only on branch `claude/epistemic-demo-engineering-unit-80h6xo`, not on `main`. Solver validated against MASTAN2.
- **Agricultural guided investigation** (`agricultural/investigation.html`, 7 tabs, embeds `engine-demo.html` panels): paused by Matt's priority. Tab 3 crossover claim is stale; do not touch until the engine is accurate.
- **Materials science** (`materials-science/investigation.html`, "Modeling the Messy"): six ported activities from `CAMEL/modeling_the_messy.ipynb` for Kathy's PA Department of Education talk. `CAMEL/` is archived external material (Wes and Becca), not linked from the splash page.
- Splash page `index.html` links the units; shared logo `logo.png`.

## Business and repo notes

- Built to be acquired (educational publishers), non-dilutive funding path (NSF STTR, DRK-12, Ben Franklin, KIZ), Penn State OTM disclosure in progress. Collaborators: Kathy (Penn State), Duke researcher, Mr. Besong, Wes and Becca.
- Funding sequencing and unit-portfolio sequencing are open founder decisions; do not treat them as settled.
- Repo `.git` carries about 120 MB of dead blobs from past binary uploads. Not worth rewriting history. Check `du -sh .git` after adding datasets; the repo is near 1 GB with the agricultural weather tiles.
- GitHub web upload mis-files and silently corrupts large binaries; use GitHub Desktop. GitHub Releases assets have no CORS, so host data in the repo.
- The container resets mid-session; `/tmp` and the scratchpad are lost. Commit and push anything worth keeping. Before working, `git fetch`, check `git diff --stat HEAD`, then fast-forward.
- Develop on the branch named in the session; do not open a pull request unless asked.
