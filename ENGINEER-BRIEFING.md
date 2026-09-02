# epiSTEMic — Engineering Briefing

Written for the first conversation with a new engineer, before he's read a line of code. Purpose: get him oriented fast on what exists, why it's built the way it is, and what's actually being asked of him (accounts, LMS integration). Skips anything a competent engineer already knows; explains the parts that are specific to this project or to ed-tech generally.

## The one fact that explains everything else

**Every page in this repo is a static file. There is no backend, no database, no server-side code, with one narrow exception described below.** The whole site is hosted on GitHub Pages, which serves files, full stop, it doesn't run code.

This isn't a skill gap or something nobody's gotten around to. It's a deliberate constraint for this phase: pre-funding, proof-of-concept, needs to cost nothing to host and deploy with zero ops overhead while the pedagogy gets validated with real classrooms. The moment real accounts, rosters, or LMS integration are needed, that constraint has to go, that's this engineer's actual job. Worth saying explicitly in the meeting: he's not being asked to work within the current architecture, he's being asked to replace its central constraint.

## What he already knows — don't over-explain these

Vanilla JS (no framework anywhere in this codebase, deliberately, to keep every unit a single self-contained file), `fetch`, Promises/async-await, the Canvas 2D API, git/GitHub/PRs, JSON, REST conventions, general OAuth/session/JWT concepts. All used throughout, all standard.

## What he probably hasn't seen before

**Pyodide.** This is the platform's actual technical differentiator, worth leading with. It's real CPython, with numpy/pandas, compiled to WebAssembly and run directly in the browser, not a JS reimplementation, not a server running Python behind an API. A student's browser downloads the Python runtime once (~10MB+) and then every computation, every chart, happens client-side with no round trip. This is *why* no backend has been needed so far for the actual investigations, the "backend" work already happens, just inside the browser.

**GitHub Pages as 100% of current hosting.** Static files only. No Node server, no PHP, nothing that executes on request. Whatever he builds for accounts/LMS needs real hosting somewhere else (Pages can't run it), a real architecture decision he'll need to make.

**The one exception: a Cloudflare Worker.** `cloudflare-worker/worker.js` is the *only* server-side code anywhere in this project. It exists for one reason: the AI feedback feature calls Google's Gemini API, which needs a secret key, and a key can't sit in a public static page. The Worker holds the key and proxies the request. That's the entire scope of "backend" that currently exists, one stateless proxy function, no database behind it. Worth pointing to as a concrete example of how the team has handled needing *some* server behavior without standing up a full backend, and worth asking him directly whether edge functions like this are part of how he'd want to build the real backend, or whether accounts/rostering need something heavier (a real server + database). That's genuinely open, not decided.

**A custom data-shipping pipeline (meteorology unit specifically).** Real NASA satellite data and ERA5 reanalysis data get pre-processed offline (in Colab, not in this repo), quantized to `int16`, gzip-compressed, and shipped as flat binary files with a JSON manifest describing byte offsets per variable. The browser fetches the compressed binary, decompresses it with the native `DecompressionStream` API, and reads it directly as typed arrays. This exists because the real datasets are hundreds of MB to ~1GB and needed to fit within what a static site can reasonably serve. He likely won't need to touch this for the accounts/LMS work, but he'll see it in the codebase and it's not obvious from the file alone why it's shaped this way.

**iframe-based embedding with URL deep-links.** Rather than duplicating a ~1900-line data-analysis tool across multiple guided-lesson pages, later pages embed the tool via `<iframe src="tool.html?var=X&region=Y&run=1">`, with the tool itself reading those query params to pre-configure and optionally auto-run. Keeps one source of truth instead of forked copies. Worth knowing before he considers refactoring any of it into components, this pattern is intentional, not a workaround.

**localStorage is doing something that looks like access control but isn't.** A few places in the anthropology unit use `localStorage` flags to "gate" content, e.g., an end-of-unit assessment stays visually locked until a student finishes the main investigation. This is entirely client-side, easily bypassed by clearing storage or opening a private window, and everyone building it has known that the whole time; it was never meant as real enforcement, just a nudge. **This is exactly the kind of thing his real accounts system needs to replace with actual server-side checks.** Worth flagging directly so he doesn't mistake it for a security model already in place, or assume it needs to be preserved as-is.

**LTI 1.3.** The standard protocol for LMS integration (Canvas, Brightspace, Schoology, Google Classroom, Moodle all speak it, with varying completeness). If he hasn't worked in ed-tech, he likely hasn't touched this specifically, it's not general OAuth, though it's built on similar primitives. The two extensions that matter here: Names and Role Provisioning Services (rostering, who's in this class) and Assignment and Grade Services (writing a grade back into the LMS gradebook). One thing worth telling him directly: Canvas and Brightspace have mature, full LTI Advantage support; Google Classroom's has historically been narrower and newer, don't assume parity across LMSs without checking each one's actual current conformance.

**Why student data handling isn't a free architecture choice here.** FERPA applies to any US student's education records, and most K-12 districts require a signed data privacy agreement, often the Student Data Privacy Consortium's standardized National Data Privacy Agreement, before any tool touches real student accounts. Higher ed institutions instead commonly require a HECVAT (a security/privacy questionnaire) before approving a new vendor. This isn't optional compliance theater, it directly shapes what can be stored, where, and for how long, and it's worth deciding early whether the first real rollout targets K-12 (heavier compliance) or higher ed (lighter, different track) since the current pilot audience is split, undergraduate anthropology, high-school-level meteorology.

## What exists today

Three units, each a self-contained set of static HTML/JS files under its own top-level folder (`anthropology/`, `meteorology/`, `engineering/`), all linked from the root `index.html` splash page:

- **Anthropology** (live): students analyze real primate skeletal data against a "mystery specimen," get AI-generated formative feedback (via the Cloudflare Worker) on their written argument, and unlock a randomized, anti-cheating end-of-unit assessment.
- **Meteorology** (live): a real-data research sandbox (NASA CERES + ERA5 reanalysis) wrapped in a guided, tab-based investigation that builds toward open-ended student research.
- **Engineering** (newest, built in a separate session, less context on this one): an `investigation.html` guided unit plus a standalone `truss-designer.html` tool.

## The open questions that are actually his to help answer

These are genuinely undecided, not things to walk in with a pre-built answer for:

1. **Teacher-only accounts, or full student accounts?** Teacher accounts with rosters and a dashboard is a meaningfully smaller, lower-compliance build than individual student logins with tracked profiles. This is the single biggest scope fork in the whole project.
2. **Which LMS first, and which LTI services?** Rostering alone is a much smaller lift than rostering plus grade passback plus deep content integration.
3. **What does "the backend" actually become?** Given everything today is static, does the real answer look like edge functions (extending the Cloudflare Worker pattern already in place) plus a lightweight database, or a conventional server? This is squarely his call to make and defend.
4. **How does instructor-configurable curriculum fit the data model?** Teachers have already asked for the ability to skip specific modules or swap the end-of-unit assessment type per class. That's not just "add a login", it implies a real concept of a class/section with its own configuration, which is more schema than authentication alone.

## Where to actually start reading

`CLAUDE.md` at the repo root, loaded automatically by Claude Code but worth him reading directly too, is the living architecture doc, kept current all the way through this project's development. `TECHNICAL-NOTES.md` is the debugging cheat sheet, real problems hit and how they were solved, worth skimming before he re-derives something already answered. The live site is at the GitHub Pages URL in `index.html`, worth him clicking through all three units before reading any code.
