# Technical Notes

A running cheat sheet of technical problems hit on this project and how they were solved. Not for outside readers — this is a reference for picking a solution back up later without re-deriving it. Add to it as new problems get solved; don't prune old entries just because they're not the current focus.

Format per entry: **Problem** → **Solution** → key file(s)/technique, plus any gotcha worth not re-learning the hard way.

---

## Cross-cutting

**Problem:** No backend, no accounts, no external services at runtime — the platform's core rule — but real tools need real data and real computation.
**Solution:** Everything ships as static files next to the HTML (embedded JSON for small datasets, manifest+gzip binary for large ones). Python runs client-side via Pyodide where Python-specific libraries are actually needed (Plotly rendering in the anthropology unit); plain JS everywhere else. No server, ever, for anything a student does.

**Problem:** Paid/keyed APIs (Gemini) can't be called directly from a public static page without exposing the key.
**Solution:** Cloudflare Worker proxy (`cloudflare-worker/worker.js`) holds the key server-side, page calls the worker instead of the API directly. `FEEDBACK_ENDPOINT` in `investigation.html` points at the deployed worker.
**Not yet done:** meteorology unit will need the same treatment whenever it eventually gets an AI feedback loop (for the future open-ended research phase, not the current guided sandbox).
**Corrected assumption, logged so it isn't repeated:** earlier notes here and in CLAUDE.md claimed the meteorology Colab notebook has a feedback cell that calls Anthropic with an exposed key. That was wrong — that notebook predates public genAI and has no AI/API calls anywhere in it. There is nothing to fix there; any future meteorology AI feedback is new-feature work against the sandbox, not a patch to an existing notebook cell.

**Problem:** Accounts/login and LMS grade passback (Canvas/Brightspace/Google Classroom) are real, wanted features, not things Matt has ruled out.
**Solution/scope decision:** deferred entirely to a future hired software engineer, post-funding — this project is currently bootstrapped proof-of-concept work ("vibecoding") meant to produce lessons good enough for user/teacher feedback, not production infrastructure. Don't scaffold auth, a database, or any backend during this phase; keep new units static and no-login like anthropology and meteorology already are. When it does get built, LTI 1.3 is the standard that covers Canvas/Brightspace/Classroom with one integration instead of three.

---

## Anthropology unit

**Problem:** No backend means no server-side gate on "did the student finish the investigation" before unlocking the assessment.
**Solution:** localStorage flag (`epistemic_argument_feedback_received`), set once Tab 5's feedback call succeeds, read by both `student-landing.html` and `investigation.html`'s own assessment nudge. Not real enforcement — a student can clear storage or switch browsers — but replaces an always-clickable link with an actual gate.

**Problem:** Assessment answers get passed down between students/sections/semesters if everyone sees the same numbers.
**Solution:** `assessment.html` generates a randomized transfer specimen client-side using a seeded PRNG (mulberry32), seed lives in the URL. Randomization is template-based across three archetypes (`suspensory_ceboid`, `cursorial_cercopithecoid`, `leaping_lemuroid`), each with its own genuine multi-metric tension — not independent-per-field randomization, which risks generating a specimen that trivially resolves on one metric or is biologically implausible.
**Gotcha:** the anti-sharing property only holds if each student opens the assessment fresh. A URL with `?seed=` already in it hands over the same specimen — distribute the bare link.

**Problem:** Reveal button (Tab 5) needs to reward a *revised* argument, not just a first attempt, without a backend to track submission history.
**Solution:** In-page counter (`argumentSubmitCount`), reveal only arms once it hits 2.

**Problem:** MorphoSource 3D mesh viewers (multiple iframes on one page, e.g. bone-viewer + femur + ulna tabs) — one mesh silently failed to render, no error, just blank.
**Solution:** WebGL context exhaustion — too many simultaneous live WebGL contexts across hidden-but-still-loaded iframes hit a browser-imposed limit. Fixed by lazy-loading: only the active tab's iframe gets a real `src`, others get `about:blank` (`ms1ManageMeshViewers()` in the MS1 preview prototype).

**Problem:** Needed cross-sectional bone geometry (CA, Imax, Imin, J) without requiring every teacher to install and learn ImageJ + the MomentMacro plugin.
**Solution:** In-browser CSG tool (`anthropology/prototypes/csg-measure-prototype.html`) — canvas-based image threshold + Otsu auto-threshold + single-pass pixel-moment calculation, algebraically equivalent to ImageJ's two-pass rotate-and-recompute approach but simpler to compute. Validated against closed-form ellipse geometry (<1.2% error) and real specimen images. Outputs the exact same tab-separated format the existing Tab 4 parser already expects, so no downstream code changed.

**Problem:** A boot-order bug where a function that could throw (Plotly-dependent draw calls) ran before state-setup code in the same handler — when Plotly's CDN failed, everything *after* the throwing call silently never ran.
**Solution:** Recurring lesson, hit more than once: always place non-Plotly-dependent setup before `Plotly.newPlot()` calls, or wrap Plotly calls in their own try/catch that can't block subsequent code.

---

## Meteorology unit

**Problem:** Real CERES energy-balance data is a NetCDF file 100s of MB to ~800MB — the original Colab notebook's own dependency — and Cartopy/NetCDF4 don't run in Pyodide, which is why the notebook couldn't just be ported directly.
**Solution:** Two-tier resolution architecture. One always-loaded coarse dataset (2°, whole globe, every month, ~40MB) for scanning and time series; separate fine-resolution (1°, native CERES resolution) tiles, 30°×30° each, 72 tiles cover the globe, fetched only for whichever tiles a selected region overlaps, capped at 12 tiles (~17MB) before falling back to coarse. A full global dataset at 1° was tested and confirmed too large (~183MB) before this was built — don't re-test that, it's already answered.
**Files:** `meteorology/prototypes/energy-balance-sandbox.html` (`buildFineGrid`, `fineTileRange`, `computeTrendGrid` — the latter takes optional lat/lon/grid-source overrides so the same function serves both tiers).

**Problem:** Trend maps need real geographic projections; Cartopy's out (see above), and Plotly's own `scattergeo` markers don't work either.
**Solution first tried, and why it failed:** placing one marker per grid cell on a `scattergeo` trace. Works under equirectangular (constant screen-distance-per-degree) but breaks visibly under any curved projection — no fixed marker size can be right both near a stereographic projection's center (where cells compress) and at a region's outer edge (where they spread out). Rendered as a diverging spiral (global extent) or concentric rings with gaps (regional). Two rounds of marker-size tuning didn't fix it because the approach itself was wrong.
**What actually worked:** self-rendered raster. For every output canvas pixel, inverse-project (Snyder's standard forward/inverse formulas) back to a lat/lon and look up that cell directly — correct by construction for any projection, no marker involved. Implemented for equirectangular, orthographic, stereographic.
**Gotcha:** stereographic is mathematically unbounded near its antipode (radius → ∞). A global selection under stereographic (this happened when an unimplemented "Natural earth" dropdown option silently fell through to the stereographic code path) rendered as a nonsensical pinwheel. Fixed by treating points beyond ~100° from the projection center as not-visible.
**Gotcha 2:** coastlines need clipping to the *selected region's* bounds, not just the projection's own visibility range — those are very different things (a polar stereographic's visible range includes mid-latitude coastlines even when the selected region is Arctic-only). Missing this clip showed as coastline fragments extending past the edge of the colored data.

**Problem:** No coastline/geographic reference data, and no external tile server allowed (same no-backend rule).
**Solution:** `registry.npmjs.org` bypasses this sandbox's network proxy restrictions even though most external hosts are blocked. Installed `world-atlas` + `topojson-client` via npm, decoded the 110m-resolution land data to a flat array of `[lon,lat]` polylines offline, bundled as a static 76KB JSON file (`sample-data/coastlines_110m.json`) — not fetched from a live server at runtime.

**Problem:** Canvas needs to render crisply regardless of the viewer's screen pixel density, and a rectangular CSS border around a circular (stereographic/orthographic) projection looks like a mismatched box.
**Solution:** Canvas backing-store resolution scales with `devicePixelRatio` (capped at 2x) instead of a fixed logical size. Border is conditional on projection type — kept for equirectangular (a real rectangle), dropped for the circular projections.

**Problem:** Synthetic proxy data with independent per-cell-per-month noise compressed terribly (2.5MB/tile against a ~600KB target) regardless of noise amplitude.
**Solution:** 312 independently-seeded monthly snapshots per tile have no cross-snapshot redundancy for gzip's LZ77 to exploit, no matter how small each one is individually. Generating interannual noise once per *year* instead (still spatially smooth within a snapshot, still real year-to-year variability, seasonal cycle still varies every month deterministically) got tiles to ~1.4MB.
**Note:** this was for the synthetic placeholder data, since replaced by real CERES data — but the same compression lesson would apply again if synthetic data is ever needed for a future unit.

**Problem:** Getting the real ~40MB coarse CERES file from a local computer into the repo via GitHub's website.
**Solution that didn't work:** GitHub's web upload silently fails/is unreliable above roughly 25MB. A retry got mangled into garbled text after the `.gz` extension triggered the OS's own archive handler to silently decompress it, and the resulting garbage got pasted through GitHub's "create new file" text editor instead of uploaded as binary.
**Solution that worked:** strip the file extension entirely before it leaves the source environment (Colab) — nothing recognizes a bare extensionless file as something to "helpfully" auto-process — then push via **GitHub Desktop**, not the website upload widget. GitHub Desktop handles anything up to git's real 100MB limit with no surprises.
**Gotcha:** GitHub's web upload also silently drops files into the wrong folder when a batch is uploaded across multiple separate actions — confirmed on the 72 regional tile files, half of which landed one directory level too high. Cheap to fix after the fact (`git mv`), but worth avoiding — use GitHub Desktop for anything with more than a couple of files or any file of meaningful size.

**Problem:** Converting a real CERES NetCDF file requires a Python environment with `xarray` that already has the file — this sandbox has no route to NASA Earthdata or Google Drive (proxy blocks non-allowlisted hosts).
**Solution:** conversion runs wherever the file already lives (Colab, in practice), producing the small manifest+binary output in the same format the tool already reads, sent back rather than the raw source. One-time, human-in-the-loop — appropriate for a dataset updated roughly once a year (new CERES edition), not a live feed.
**Verification pattern used and worth reusing:** decompressed byte counts checked against manifest-declared byte layout exactly; the tool's own area-weighted global mean recomputed and checked against a known published value (ISR ≈ 340 W/m² globally); full arrays recomputed independently in numpy and diffed against the tool's output.

**Problem:** A real regional trend map (Great Lakes area, ~5°×2°) rendered as solid color with no coastline or graticule at all — traced to three separate bugs from one test case.
**Solution 1 — no coastline data existed for the region at any resolution:** the bundled coastline file (`world-atlas`'s "land" layer) only encodes land-vs-ocean boundaries — lakes aren't a "land" feature at all, so the Great Lakes are absent regardless of resolution. Switched to `sane-topojson` (the same map data Plotly.js's own geo traces use), merging its `land` and `lakes` objects, at 50m resolution.
**Solution 2 — coastline segments crossing the region boundary were dropped entirely:** the per-point region clip (added for the earlier "coastlines extending past the disk" fix) required *both* endpoints of a segment to be inside the box. A small enough region can have zero interior vertices even with better data, while the true line still visibly crosses it. Now draws if *either* endpoint is inside (small overdraw past the edge on the outside endpoint, clearly the better tradeoff).
**Solution 3 — graticule step size was fixed at a 5° minimum:** any region smaller than that got zero parallels. Replaced with a step picker that guarantees ~2+ divisions regardless of region size (`niceGraticuleStep()`), with label decimal precision bumped for sub-1° steps.
**Solution 4 — lines/labels were invisible against the saturated end of the color scale:** a flat dark gray/brown line at any reasonable opacity disappears against near-black maroon or navy (the RdBu extremes), which a region dominated by one trend direction hits often. Fixed with a white halo behind every line and label (`haloStroke()`/`haloText()`) — standard cartography technique, guarantees contrast regardless of fill color.

**Not yet done for this unit:** instructor resource page, guided investigations (outline exists, see CLAUDE.md's meteorology section — on hold pending feedback from Max), end-of-unit assessment, poster template, AI feedback/reveal loop for the later open-ended research phase, promotion to a top-level `meteorology/` folder with a real splash-page link.

**Terminology, logged so it isn't misread again:** this unit's planned "notebook" is a pedagogical science notebook (student log of what was studied/found/means, claim-evidence-reasoning style) — not a Jupyter/code notebook. Pyodide has nothing to do with it.
