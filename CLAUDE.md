epiSTEMic Platform — Primate Locomotion Investigation

What this project is

epiSTEMic is a browser-based platform for authentic computational science investigations targeting grades 6 through undergraduate. The core technical differentiator is Python running entirely in the browser via Pyodide (WebAssembly) — no backend, no login, no external dependencies. The platform is built-to-be-acquired, targeting educational publishers (Macmillan Learning, Cengage, Carolina Biological, HMH, Amplify) over a 5-7 year horizon. Funding path is non-dilutive: NSF STTR, DRK-12, Ben Franklin Technology Partners, KIZ tax credits. Penn State OTM invention disclosure is in progress. I-Corps regional cohort application is underway.

Collaborators: Kathy (Penn State, co-inventor, grantsmanship), Duke University biological anthropology researcher (provided primate datasets), Mr. Besong (high school physics teacher, climate investigation notebook).

Working principle throughout this project: The investigation is not a matching game. Mystery specimens are chosen so no single metric resolves the question. Students must synthesize multiple lines of quantitative evidence and make claims with explicitly stated uncertainty. This is intentional and must be preserved in all design decisions.

Current build state

The platform is multi-unit now. index.html at the repo root is the epiSTEMic splash page: logo, tagline, and a unit-selection grid. It is the live root at https://mmj125.github.io/epistemic-demo/. It links to two unit tiles — Biological Anthropology (live, links to anthropology/student-landing.html as the primary action, with a secondary "Instructor resources" link to anthropology/instructor.html) and Meteorology & Climate Science (Coming Soon, not yet clickable — the actual unit is still a Google Colab notebook, not part of this repo). A non-functional "Sign In" placeholder sits in the top corner; accounts are not built yet.

Each unit's files live in their own top-level folder so additional subjects can be added the same way. The anthropology unit is under anthropology/:

anthropology/instructor.html — teacher-facing resource page. Contains four module cards with slide deck downloads, specimen entry links, a downloadable lesson plan, and an instructor reference table with specimen identities. Explicitly not linked from student-facing pages (banner + footer both say so) — the splash page respects this by routing its primary click into student-landing.html, not here.

anthropology/student-landing.html — student-facing landing page with "phone call from someone who found bones" narrative framing, six locomotor type cards with IMI ranges, four YouTube video embeds showing locomotion types, four specimen cards linking to the investigation, and a separate, visually distinct "After You Finish The Investigation" section linking to assessment.html (kept apart from the specimen grid so it reads as a later summative step, not a 5th mystery specimen). That section is locked by default (greyed card, no link) and only unlocks into a clickable assessment.html link once a localStorage flag (epistemic_argument_feedback_received, set by investigation.html's submitArgument() on the first successful feedback response) is present. There's no backend or login, so this is client-side state per browser, not enforced completion — a student can clear storage or switch devices/browsers to bypass it — but it replaces what used to be an always-clickable link with only a text note asking students to finish first.

anthropology/investigation.html — the main investigation tool, single file with URL parameter switching (?specimen=MS11 through MS14). Contains five tabs: Limb Proportions, Body Mass, Olecranon Index, Bone Geometry, Build Argument. Loads 478-specimen limb length dataset and 111-specimen CSG dataset as embedded JSON. Runs Pyodide for scatter/box plots via Plotly. AI formative feedback on student arguments calls the Gemini API (gemini-3.5-flash, free tier) through a Cloudflare Worker proxy (cloudflare-worker/worker.js) so the API key never sits in this public page. Reveal (Tab 5) is gated behind a revised argument submission, not just the first one — see Tab 5 detail below.

anthropology/lesson-plan.pdf, anthropology/slides-*.pptx.pdf, anthropology/MomentMacro_CSATS.txt — instructor-facing downloads, all linked from instructor.html.

anthropology/assessment.html — end-of-unit assessment, linked from instructor.html (opens in a new tab, not a download). Generates a randomized transfer specimen client-side on load using a seeded PRNG (mulberry32); the seed lives in the URL so a reload keeps the same specimen but a fresh visit gets a new one. No two students (or sections, or semesters) get the same underlying numbers by default — this is the deliberate fix for the standard problem of assessment answers getting passed down. Randomization is template-based across three archetypes (suspensory_ceboid, cursorial_cercopithecoid, leaping_lemuroid), each with its own genuine multi-metric tension (mirroring the four mystery specimens' design), not naive independent-field randomization — that would risk generating a specimen that trivially resolves on one metric or is biologically implausible. Real embedded DATA and CSG_DATA (duplicated from investigation.html, not fetched) form the comparative backdrop in every chart; only the focal specimen's own numbers are generated. Five "data displays" (limb proportion scatter with a species/superfamily view toggle, IMI box plot, body mass table, an interactive click-to-mark OUI number line, CSG box plots with a CA/Imax-Imin toggle) plus ten questions across four parts: reading the displays (with an evidence-selection checklist per question — deliberately not every display is useful for every question), comparing to the student's own earlier mystery specimen, a full claim/evidence/conflicting-evidence/adaptation argument, and a reflection. Submission generates a printable summary (student responses + the exact specimen data they worked from) and a gated "reveal instructor grading reference" section that is auto-computed from that student's specific random values using the same classification logic as the rest of the platform (IMI category ranges, OUI_GROUPS from Drapeau 2004, the CSG interpretation heuristics), not written by hand per student. No backend or login; degrades gracefully if the Plotly CDN fails (each chart's render is independently wrapped, so one failure doesn't take down the body mass table, the OUI canvas, or the rest of the form). Operational note for instructors: the anti-sharing property only holds if students each open the assessment fresh — sharing the literal URL with a ?seed= already in it hands over the same specimen, so distribute the bare assessment.html link, not a URL a previous student generated.

logo.png at the repo root is the shared platform logo, referenced by both index.html and anthropology/instructor.html (via a relative ../logo.png path). Keep it at root rather than duplicating it per unit as more units are added.

The five investigation tabs in detail

Tab 1 (Limb Proportions): Configurable scatter plot and IMI box plot from 478 primate specimens across four superfamilies. Students enter four limb measurements (humerus, radius, femur, tibia), IMI calculates live, mystery specimen plots as a star. Grouping by superfamily/common name/genus. Axes fully configurable.

Tab 2 (Body Mass): Femoral head SI diameter input, five taxon-specific regression equations output simultaneously. Equations: Lemurs exp(2.548×ln(FHSI)+1.696)÷1000, South American Monkeys exp(2.729×ln(FHSI)+1.420)÷1000, Old World Monkeys exp(2.388×ln(FHSI)−4.560), Apes 10^(2.6465×log₁₀(FHSI)−2.4093), Humans 10^(1.7125×log₁₀(FHSI)−1.048). Contextual note auto-generates based on whether human estimate is biologically plausible.

Tab 3 (Olecranon Index): OL and UL inputs, OUI calculates live, plots as triangle on a canvas number line against six locomotor group ranges from Drapeau (2004). Groups staggered at three heights to prevent label overlap. Note explicitly states mid-range overlap means OUI alone cannot resolve classification.

Tab 4 (Bone Geometry): ImageJ link bar at top. Drag-and-drop upload for femur and humerus log files (tab-separated ImageJ MomentMacro output: Name, CA, Imax, Imin, Imax/Imin, J). Three switchable charts: log-scale J scatter with 1:1 reference line, Imax/Imin box plots, log-scale cortical area box plots. Femur/humerus/both toggle on box plots.

Tab 5 (Build Argument): Four structured prompts (claim, supporting evidence, conflicting evidence, adaptation/natural selection). Summary pills show all measurements student collected across tabs. Submission calls FEEDBACK_ENDPOINT (a Cloudflare Worker, see cloudflare-worker/worker.js) which holds the Gemini API key server-side and forwards to gemini-3.5-flash. Generates 240-290 word formative feedback that reads all four analyses, does not reveal identity, pushes back on single-metric arguments. The "Reveal identity" button and Identity Revealed panel live here (moved off Tab 1's sidebar so the unlock sits next to the action that earns it) and only arm after the student's second, revised argument submission gets feedback — the first submission's feedback alone does not unlock it, tracked via an in-page submission counter (argumentSubmitCount).

The four mystery specimens

MS-11: Alouatta seniculus (Red Howler Monkey), Rio Verde Forest Reserve Colombia. IMI in arboreal quadruped range. Body mass 5-10kg distinguishes from larger species with similar IMI.

MS-12: Presbytis obscura (Dusky Leaf Monkey), Bukit Hijau National Park Malaysia. IMI ~90-91 in dense cercopithecoid overlap zone. Multiple locomotor strategies produce similar values.

MS-13: Indri indri, West African forest (deliberate misdirection — Indri is Malagasy). IMI ~66.5 clusters near humans and sifaka for entirely different evolutionary reasons. Two misdirections: field context wrong, IMI human-like but animal is a vertical clinger and leaper.

MS-14: Erythrocebus patas (Patas Monkey), Kiboko Savanna Sub-Saharan Africa. IMI overlaps with arboreal cercopithecoids despite highly terrestrial cursorial lifestyle. Fastest primate on ground ~55km/h. Habitat context is essential.

Datasets embedded in anthropology/investigation.html

Limb length: 478 specimens, four superfamilies (Hominoidea, Cercopithecoidea, Ceboidea, Lemuroidea), 21 common names. Fields: superfamily, genus, species, common_name, sex, humerus, radius, femur, tibia, forelimb, hindlimb, imi. Source: two Excel files (Limb_Length_Dataset_A and B) from Duke University collaborator.

CSG: 111 specimens, 11 species (Human, Chimp, Gorilla, Baboon, Orangutan, Siamang, Brown Capuchin, Sifaka, Squirrel Monkey, Howler Monkey, Crab-eating Macaque). Fields: common_name, femur_ca, humerus_ca, femur_j, humerus_j, femur_imax_imin, humerus_imax_imin. Log scale used throughout because size range spans two orders of magnitude.

What is deliberately deferred

Instructor view/dashboard: deferred to v1.5. CSV export is interim solution. LMS integration (LTI 1.3) deferred to v1.5. A lesson plan with learning objectives now exists (anthropology/lesson-plan.pdf), written for an intro undergraduate biological anthropology course and framed against AAAS Vision and Change core competencies rather than NGSS (NGSS is K-12 only and doesn't fit that audience). If a K-12 version of this or another unit is built later, it would need its own NGSS-aligned pass. Accounts/login: deferred, but the splash page now has a placeholder for it. Climate investigation (meteorology unit) still uses Google Colab as transitional environment because CERES dataset is 800MB and Cartopy/NetCDF4 are incompatible with Pyodide — it is not yet part of this repo; the splash page's meteorology tile is a non-clickable "Coming Soon" placeholder until it is.

Immediate outstanding issues

FEEDBACK_ENDPOINT in anthropology/investigation.html now points at the deployed Cloudflare Worker (https://epistemic-feedback.mmjohnson0505.workers.dev/, source in cloudflare-worker/worker.js). Confirm the GEMINI_API_KEY secret is set on that worker if Tab 5 feedback stops working. When the meteorology unit is ready to bring into the repo, it should get its own top-level folder (meteorology/, matching anthropology/) and the splash page's meteorology tile needs to change from a static "Coming Soon" div to a real link.

How Matt works

Lead with what is wrong or missing before affirming anything. Provide comparables and explicit tradeoffs. Assume the project succeeds. Do not echo his framing. Stress-test ideas rather than validate them. Never use em dashes. Never create titles in the format "Phrase: longer phrase."
