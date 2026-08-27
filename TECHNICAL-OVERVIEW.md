# Computation in the Browser

How this platform runs the same kind of analysis a working scientist would — reading real satellite data, fitting trends, measuring bone geometry from images — without asking a student to install anything, make an account, or sit on a network that allows it.

This is a reference for explaining the technical approach to someone outside the project, not a running engineering log (see `TECHNICAL-NOTES.md` for that) and not a pitch. It's meant to hold up as a plain description of what was actually built and what was actually traded to build it.

Every investigation in this platform does real computation: it reads actual measured data, runs actual statistics, produces actual numbers a student didn't already know. None of that is simulated or pre-baked. What's different from how a scientist would normally do this work is *where* it runs and *what it takes to get there* — not the substance of the work itself. This document is about that difference: which real tools this replaces, how, and what's genuinely lost in the trade.

## Python, without installing Python

**Pyodide** is a full build of CPython — the standard Python interpreter — compiled to WebAssembly and shipped as part of the page. It runs the same Python code a scientist would write locally, inside the browser tab, on the student's own machine, with no server involved once it's loaded.

What that replaces: installing Python and a scientific stack locally, or getting an account and a working session on something like Google Colab. What it costs: a real download (tens of megabytes) the first time a page uses it, a smaller package ecosystem than a full local install, and slower performance than native Python on heavy numerical loops. For the calculations these investigations actually run — regression, unit conversion, basic statistics — that cost doesn't show up. It would for something more demanding.

## Getting real data small enough to ship

The satellite and reanalysis datasets behind the meteorology unit (CERES, ERA5) arrive as scientific files hundreds of megabytes to over a gigabyte in size, at full native resolution, in a format no browser can open. Nobody needs that much file to see the pattern a lesson is built around — so before any of it reaches a student, it goes through a one-time conversion: cut down to a resolution still fine enough to show every pattern being taught, converted from 64-bit floating point to 16-bit integers, then compressed the way a .zip file is. What ships to the browser is what's left after that.

- **~800 MB** — the original CERES file
- **~40 MB** — what the browser actually loads
- **14.57°C** — the global mean temperature recovered from the shrunk data, matching the published value

That conversion step is the one place in this whole system that still runs in Colab. It's worth being precise about what that means: Colab isn't eliminated from the system, it's eliminated from **the student's workflow**. The heavy tool still exists and still does real work — it just runs once, offline, by whoever is preparing the unit, using an environment that already has the right libraries installed, rather than by every student every time they open the page.

## Charting: kept where it worked, replaced where it didn't

Plotly — a real charting library, loaded straight into the page from a CDN, no install — draws most of the charts here: scatter plots, box plots, time series. That's a direct replacement for the usual workflow of opening a notebook and writing plotting code by hand; the charts are just pre-built and parameterized instead.

It broke down for one specific case: drawing a data grid onto a curved map projection. Plotly's geographic plotting places one marker per grid cell, and there's no single marker size that's correct everywhere on a curved projection — cells compress near the projection's center and spread out toward its edge, so a marker sized for one is wrong for the other. The fix wasn't a workaround for a missing feature; it was a more correct approach: for every pixel of the output image, work out which latitude and longitude it corresponds to under the current projection, and look up that cell's value directly. That's exact by construction, for any projection, regardless of how the region is shaped or where it sits on the globe.

## Bone cross-sectional geometry, without ImageJ

Measuring a bone's cross-sectional area and its moments of inertia from a scan image is normally done in ImageJ with the MomentMacro plugin — a real, standard, capable tool, and also one more piece of software a teacher has to get installed correctly on however many classroom machines, before any student can measure anything. A canvas-based tool built into the page now does the same job: threshold the image (using the same Otsu auto-thresholding method), then compute the cross-sectional area and moments in a single pass over the pixels.

It was checked two ways before being trusted: against the closed-form geometry of a known ellipse shape (under 1.2% error), and against real specimen images compared directly to ImageJ's own output. It writes the same tab-separated file format the rest of the tool already reads, so nothing downstream needed to change to use it.

## The pattern, side by side

| Normally reached for | What runs here instead | What's genuinely different |
|---|---|---|
| Colab or a local Python install, to load and process the raw dataset | A one-time offline conversion — still Colab, just once, not per student — produces a small file the page reads directly | Only the prepared version is in the tool; the full-resolution source isn't |
| Plotly's or matplotlib's geographic plotting, for a projected map | A canvas raster — every output pixel is projected back to a lat/lon and its cell looked up directly | Only the three projections these investigations need are implemented |
| ImageJ with the MomentMacro plugin, for bone cross-sectional geometry | A canvas tool that thresholds the image and computes the same geometry in one pass | Validated against ImageJ's own output and known shapes — not a general substitute for ImageJ |

## What this doesn't do

- **No open-ended computation.** A live Colab session can run whatever a student or teacher thinks to write. This platform only offers the specific analyses that have been deliberately built into it — that's a real ceiling, not a hidden one.
- **Lower resolution than the source, on purpose and irreversibly.** The data-shrinking step throws away detail a browser doesn't need to show the pattern being taught. Anyone who needs the full native-resolution dataset for a different purpose has to go get it themselves — it isn't recoverable from what ships here.
- **Each in-browser replacement only covers what's been tested.** The cross-sectional geometry tool and the map renderer were checked against known cases and real specimen data, not proven equivalent to ImageJ or a GIS package across every input those mature tools handle.
- **Not a research environment.** This is built for a specific instructional purpose. It isn't a substitute for real scientific computing tools for someone doing original research with their own data.

## The pattern, stated once

Same approach in every case: do the heavy lifting once, offline, where a full toolchain already exists; ship only what a browser needs; build a small custom tool only where an off-the-shelf one genuinely fell short, and check it against the thing it replaced. It's also the reason this runs on a school Chromebook that blocks Colab outright.
