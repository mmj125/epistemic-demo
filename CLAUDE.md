epiSTEMic Platform — Primate Locomotion Investigation

What this project is

epiSTEMic is a browser-based platform for authentic computational science investigations targeting grades 6 through undergraduate. The core technical differentiator is Python running entirely in the browser via Pyodide (WebAssembly) — no backend, no login, no external dependencies. The platform is built-to-be-acquired, targeting educational publishers (Macmillan Learning, Cengage, Carolina Biological, HMH, Amplify) over a 5-7 year horizon. Funding path is non-dilutive: NSF STTR, DRK-12, Ben Franklin Technology Partners, KIZ tax credits. Penn State OTM invention disclosure is in progress. I-Corps regional cohort application is underway.

Collaborators: Kathy (Penn State, co-inventor, grantsmanship), Duke University biological anthropology researcher (provided primate datasets), Mr. Besong (high school physics teacher, climate investigation notebook).

Working principle throughout this project: The investigation is not a matching game. Mystery specimens are chosen so no single metric resolves the question. Students must synthesize multiple lines of quantitative evidence and make claims with explicitly stated uncertainty. This is intentional and must be preserved in all design decisions.

Current build state

Three HTML files are live at https://mmj125.github.io/epistemic-demo/:

instructor.html — teacher-facing resource page (currently the root URL via index.html redirect). Contains four module cards with slide deck downloads, specimen entry links, and an instructor reference table with specimen identities. Slide files are in GitHub as .pptx.pdf double extensions; download links in instructor.html need updating to match (change .pptx to .pptx.pdf in the four href attributes).

student-landing.html — student-facing landing page with "phone call from someone who found bones" narrative framing, six locomotor type cards with IMI ranges, four YouTube video embeds showing locomotion types, and four specimen cards linking to the investigation.

investigation.html — the main investigation tool, single file with URL parameter switching (?specimen=MS11 through MS14). Contains five tabs: Limb Proportions, Body Mass, Olecranon Index, Bone Geometry, Build Argument. Loads 478-specimen limb length dataset and 111-specimen CSG dataset as embedded JSON. Runs Pyodide for scatter/box plots via Plotly. Has Claude API call for AI formative feedback on student arguments. Reveal is gated behind argument submission.

The five investigation tabs in detail

Tab 1 (Limb Proportions): Configurable scatter plot and IMI box plot from 478 primate specimens across four superfamilies. Students enter four limb measurements (humerus, radius, femur, tibia), IMI calculates live, mystery specimen plots as a star. Grouping by superfamily/common name/genus. Axes fully configurable.

Tab 2 (Body Mass): Femoral head SI diameter input, five taxon-specific regression equations output simultaneously. Equations: Lemurs exp(2.548×ln(FHSI)+1.696)÷1000, South American Monkeys exp(2.729×ln(FHSI)+1.420)÷1000, Old World Monkeys exp(2.388×ln(FHSI)−4.560), Apes 10^(2.6465×log₁₀(FHSI)−2.4093), Humans 10^(1.7125×log₁₀(FHSI)−1.048). Contextual note auto-generates based on whether human estimate is biologically plausible.

Tab 3 (Olecranon Index): OL and UL inputs, OUI calculates live, plots as triangle on a canvas number line against six locomotor group ranges from Drapeau (2004). Groups staggered at three heights to prevent label overlap. Note explicitly states mid-range overlap means OUI alone cannot resolve classification.

Tab 4 (Bone Geometry): ImageJ link bar at top. Drag-and-drop upload for femur and humerus log files (tab-separated ImageJ MomentMacro output: Name, CA, Imax, Imin, Imax/Imin, J). Three switchable charts: log-scale J scatter with 1:1 reference line, Imax/Imin box plots, log-scale cortical area box plots. Femur/humerus/both toggle on box plots.

Tab 5 (Build Argument): Four structured prompts (claim, supporting evidence, conflicting evidence, adaptation/natural selection). Summary pills show all measurements student collected across tabs. Claude API call generates 240-290 word formative feedback that reads all four analyses, does not reveal identity, pushes back on single-metric arguments. Reveal unlocks after feedback returns.

The four mystery specimens

MS-11: Alouatta seniculus (Red Howler Monkey), Rio Verde Forest Reserve Colombia. IMI in arboreal quadruped range. Body mass 5-10kg distinguishes from larger species with similar IMI.

MS-12: Presbytis obscura (Dusky Leaf Monkey), Bukit Hijau National Park Malaysia. IMI ~90-91 in dense cercopithecoid overlap zone. Multiple locomotor strategies produce similar values.

MS-13: Indri indri, West African forest (deliberate misdirection — Indri is Malagasy). IMI ~66.5 clusters near humans and sifaka for entirely different evolutionary reasons. Two misdirections: field context wrong, IMI human-like but animal is a vertical clinger and leaper.

MS-14: Erythrocebus patas (Patas Monkey), Kiboko Savanna Sub-Saharan Africa. IMI overlaps with arboreal cercopithecoids despite highly terrestrial cursorial lifestyle. Fastest primate on ground ~55km/h. Habitat context is essential.

Datasets embedded in investigation.html

Limb length: 478 specimens, four superfamilies (Hominoidea, Cercopithecoidea, Ceboidea, Lemuroidea), 21 common names. Fields: superfamily, genus, species, common_name, sex, humerus, radius, femur, tibia, forelimb, hindlimb, imi. Source: two Excel files (Limb_Length_Dataset_A and B) from Duke University collaborator.

CSG: 111 specimens, 11 species (Human, Chimp, Gorilla, Baboon, Orangutan, Siamang, Brown Capuchin, Sifaka, Squirrel Monkey, Howler Monkey, Crab-eating Macaque). Fields: common_name, femur_ca, humerus_ca, femur_j, humerus_j, femur_imax_imin, humerus_imax_imin. Log scale used throughout because size range spans two orders of magnitude.

What is deliberately deferred

Instructor view/dashboard: deferred to v1.5. CSV export is interim solution. LMS integration (LTI 1.3) deferred to v1.5. Learning objectives and NGSS alignment not yet written. Climate investigation (v0.2) uses Google Colab as transitional environment because CERES dataset is 800MB and Cartopy/NetCDF4 are incompatible with Pyodide.

Immediate outstanding issues

The instructor.html slide download links need .pptx changed to .pptx.pdf in four href attributes to match actual GitHub filenames. The student-landing.html needs to be linked from somewhere since it's no longer the root URL. Consider adding a "Student Investigation" button to the instructor page that links to student-landing.html.

How Matt works

Lead with what is wrong or missing before affirming anything. Provide comparables and explicit tradeoffs. Assume the project succeeds. Do not echo his framing. Stress-test ideas rather than validate them. Never use em dashes. Never create titles in the format "Phrase: longer phrase."
