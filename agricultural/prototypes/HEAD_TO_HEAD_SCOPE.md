# Head-to-head page: scope (2026-10-08, not built)

Purpose: let a Cycles developer (or any reviewer) check the engine against native Cycles on their own machine, with no Cycles binary or Cycles output ever bundled in our page (Cycles is CC BY-NC-ND). We write Cycles input files; they run their own binary; they drop the output files back in; the page overlays our engine on it.

## Flow
1. Choose inputs. Mode A: one of the 16 tile sites or a KML point (existing picker; real tile weather and STATSGO2 soil). Mode B: upload their own Cycles `.weather` and `.soil` files (the engine runs on exactly their inputs, no tiles involved).
2. Choose a scenario from the subset both sides can express (below). The page shows a plain summary of what will be simulated.
3. Download one zip: `site.weather`, `site.soil`, `scenario.operation`, `scenario.ctrl`, `README.txt` (the two commands to run). `GenericCrops.crop` is not shipped; the ctrl file names it and the README says to copy it from their Cycles install. Zip is built in the browser (store-only writer, about 40 lines, no library).
4. They run `./Cycles -b scenario` and drag the output files (`harvest.txt`, `N.txt`, `water.txt`, `soilC.txt`, `annualN.txt`, crop daily file) onto the page. Parsing is local; nothing leaves the browser.
5. Page runs our engine on the same inputs in Pyodide and shows the overlay.

## Scenario subset (v1)
Continuous corn (CornRM.90) or soybean, one UAN broadcast dose at a chosen DOY (0 to 400 kg N/ha), planter tillage, planting window 110 to 131 with soil temperature above 12 C, 1980 to 2016 or the weather file's own span. These are the cases the 16-site table already validates, and the engine settings match that harness (per-layer six-pool, nitrate by layer, lead-in years 2). Not in v1: rotations, cover crops, manure, irrigation, other tillage, wheat, silage corn (all either unvalidated or below the bar).

## Overlay (what the reviewer sees)
- Yearly grain, total biomass and planting date: Cycles vs engine, with MAE, correlation, mean ratio.
- Daily trajectory for a chosen year: crop biomass, canopy interception, root-zone moisture by layer, mineral N, water stress.
- Annual N fluxes: leaching, denitrification, N2O, volatilization, net mineralization.
- A "where we are weak" strip pulled from ACCURACY.md so the first thing they read is our known gaps.

## Decisions needed from you
1. Output format: v1.4.4 tab files first (all our references are built on them). Cycles v1.5.x writes csv with different columns; supporting it is a second parser, not hard, but doubles the test surface. Recommendation: v1.4.4 only, and say so on the page.
2. Mode B (their own weather and soil files) in v1? Recommendation yes: it is the strongest verification, since our tiles drop out of the argument. Cost: a `.soil` and `.weather` parser plus mapping Cycles layers into the engine's layer format.
3. Soybean in v1, or corn only? Corn only is smaller; soybean is validated (0.92) and adds a second crop at modest cost.
4. Where it lives: new file `agricultural/prototypes/head-to-head.html`, reusing `model-validation.html`'s engine string and site picker via the sync script, not linked from the splash page (same treatment as model-validation).

## Build plan and size
Order: (a) exporter and zip, tested by running the real binary on the exported files and checking the output matches our harness run; (b) parsers; (c) overlay charts using the existing canvas helpers; (d) Pyodide run and stats; (e) browser test with Playwright and real Pyodide as before. Roughly one long session for corn with Mode A, a second for Mode B and soybean. Biggest risk: engine runtime in Pyodide for a 37-year lead-in chain (the harness takes seconds natively; expect tens of seconds in the browser), so a year range selector and a progress bar are needed.

## Licensing notes
No Cycles binary, crop file or output is bundled or committed. The zip contains only files we generate from public NLDAS-2 and STATSGO2 data or from the reviewer's own uploads. The page should state that Cycles output stays on their machine.

## Decisions (accepted 2026-10-08)
1. Cycles v1.4.4 tab files only. 2. Mode B (their own `.weather` and `.soil`) in v1. 3. Corn and soybean. 4. New `head-to-head.html`, not linked from the splash page.
Hard requirement from Matt: a run must not take minutes.

## Measured run time (real Pyodide 0.26.2 under node, 2026-10-08)
Iowa, full 1980-2016 record, N=150, same settings as the 16-site harness (per-layer six-pool, nitrate by layer, 2 lead years, carried nitrogen state): 6.9 s for 37 years (native CPython: 2.3 s). Two nitrogen rates therefore take about 14 s. Budget: under 20 s for a full record in the browser. If a build exceeds it, fall back to a year-range selector, then to a single chained run (one pass carrying soil state, which the earlier lead-year test showed is as accurate as 2 lead years).

## Build log
2026-10-08 step (a) exporter built: `head-to-head.html` (corn only for now, soybean pending a validated continuous-soybean scenario; Mode B and parsers and overlay still to build). Verified in a real browser (Playwright): the exported weather, soil and operation files match the 16-site harness's files line for line numerically (13,520 weather lines, 9 soil lines, 50 operation lines, zero mismatches), the ctrl file differs only in file names, the zip passes `testzip`, and running the real Cycles v1.4.4 binary on the exported files gives a harvest.txt and N.txt byte-identical to the harness reference run (same md5).
2026-10-08 steps (b) parsers and (d) engine run built. Soybean added (continuous SoybeanMG.5, no fertilizer, planting window 120-140, planter pass day 120): engine vs Cycles at Rock Springs over the full record is 14% low with correlation 0.84; four-site sample earlier gave 0.82 to 0.96, with Kansas 45% high. Parsers read harvest.txt and annualN.txt for the comparison and keep N.txt, water.txt and the daily crop file for the overlay. The page embeds the same engine as the other two pages (added to `sync_engine_pages.py`). In real Chromium with real Pyodide, Central Iowa corn at N=150 reproduces the 16-site harness numbers exactly (grain 9.84 vs 10.25 Mg/ha, correlation 0.93; engine run 5.0 s for 37 years, 9.6 s wall including load), and soybean at Rock Springs ran in 1.7 s. Still to build: the daily overlay charts, Mode B (own .weather and .soil files).
Bug found on the way: the sync script only refreshed `calibration_factor` in the pages' crop dicts, so `engine-demo.html` and `model-validation.html` still had corn `rue` 2.2 after the harness moved to 2.332 (the multi-site recalibration). The sync now refreshes `rue` and `wue` for corn and soybean. Corn numbers on those two pages shift upward (about 6% on biomass) and any figure quoted for them before today is stale.
2026-10-08 step (c) daily overlay built: panel 5 plots Cycles' daily values against the engine's for a chosen year and quantity (aboveground biomass, canopy interception, water stress, nitrogen stress and profile mineral N for corn, soil moisture layers 1 to 4). The engine side comes from a one-season Pyodide run with `record_history`; `history` entries now also carry per-layer `theta` (canonical engine, pages resynced). Verified in real Chromium for Iowa corn 2012 (seven quantities) and Rock Springs soybean 2012 (five), no page errors. The Iowa mineral N overlay shows the known gap directly: engine about 500 kg N/ha against Cycles' about 300. Remaining: Mode B (own .weather and .soil files).
2026-10-08 Mode B built: upload your own Cycles `.weather` and `.soil` files. Parsers read latitude and daily weather (rejects -999 gaps and years with fewer than 365 days), and layer thickness, clay, sand, organic carbon plus the file's curve number and slope, which are now passed to the engine (the lead-in function now threads `curve_number` and `slope_pct` into its fallow windows too; defaults 75 and 0 leave every existing result unchanged). The export zip for your own files contains only the operation and control files, with the control file pointing at your file names. The engine ignores FC, PWP and bulk density you supply (it derives them from texture) and initial nitrate and ammonium; the page says so. Verified in real Chromium: exported Iowa files fed back as "own files" reproduce the tile-site result exactly (grain 9.84 vs 10.25 Mg/ha, correlation 0.93); on Cycles' own bundled Rock Springs sample files (RockSprings.weather, GenericHagerstown.soil) corn gives engine 9.50 vs Cycles 10.56 Mg/ha (ratio 0.90, correlation 0.83, planting day 0.82, 9.5 s). All scoped items are now built.
