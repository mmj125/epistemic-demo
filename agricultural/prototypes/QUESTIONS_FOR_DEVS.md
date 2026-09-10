# Questions for the CYCLES developers

Running list, compiled while building an independent, from-scratch reimplementation
of CYCLES' published equations for classroom use (see CLAUDE.md, "Agricultural unit"
section, for the full context on why this is a from-scratch build rather than a port
of the real source). Intent: one short, specific list sent once we have a
classroom-workable tool, not an ongoing back-and-forth. Each item below is something
the public paper and its Supplemental Information don't specify precisely enough to
resolve from public information alone, verified by actually trying and checking
against real Cycles output before concluding the gap is real.

## Open

1. **Curve-number moisture adjustment (`fwc`).** SI Section III describes it only in
   words ("1 for a soil saturated to a depth of 0.6 m... decreases to zero if the
   soil is air dry... depth-weighted... surface having the most importance") with no
   actual formula. What's the exact functional form and depth-weighting?

2. **Bare-soil and residue evaporation.** The SI's own process flowchart (Figure
   SI.2) marks "Soil Evaporation" and "Residue Evaporation" with the same "detailed
   in this SI" marker used for vegetation transpiration, but no evaporation equation
   is actually present anywhere in the document (SI Section II is transpiration
   only). What's the actual formula?

3. **Shoot/root partitioning's `TTf50` parameter (Eq. SI.8-11).** The equation and
   its shape parameters (`fsti`, `fstf`) are given, but `TTf50` (the thermal-time
   fraction at half-max allocation) has no stated numeric value or way to derive it
   per crop. We used 0.5 (the literal reading of the parameter's own name) --
   confirm or correct.

4. **Perennial forage cutting trigger (`CLIPPING_BIOMASS_THRESHOLD_UPPER` /
   `HARVEST_TIMING` interaction).** For orchardgrass at Rock Springs, real cuts
   happen at total biomass of 3.27, 1.94, 3.29, 3.01 Mg/ha within one season --
   notably not consistently near the 4.0 Mg/ha upper threshold, and at irregular
   28-42 day intervals. Two attempts at "cut when biomass reaches the upper
   threshold OR thermal-time-since-last-cut reaches the `HARVEST_TIMING` fraction of
   maturity, whichever first" both overestimate annual yield by ~1.8x with
   near-zero/negative year-to-year correlation against real output. What's the
   actual trigger logic (and does cutting reset thermal time to zero, or something
   else)?

5. **Canopy-cover shape constants (Eq. 6's `a`, `b`, `c`, `d`) per crop.** The paper
   gives explicit defaults (6, -20, -15, 16) but states they "represent a normalized
   plant density (PDf) of 1" for the case demonstrated. Checked directly for winter
   wheat: at the point real Cycles shows 0.746 canopy cover (thermal-time fraction
   0.40), the same constants predict 0.886 -- a real, verified gap, not noise. Ruled
   out thermal-time accumulation as the cause first (our value: 1783.6 vs. real
   1740.76 by harvest, within 2.5% -- fine). Are there different shape constants per
   crop, or a correction beyond the stated `PDf` adjustment (Eq. 7) we're missing?

## Resolved without asking (kept here for the record, not blocking)

- Cycles' `HARVEST_INDEX` is grain ÷ *aboveground* biomass, not total -- worked out
  by checking real output arithmetic directly (11.61 / (26.17 - 3.48) = 0.5117,
  matching the real reported value).
- Two likely sign errors in the SI's typeset equations (curve-number runoff
  denominator; the wet-curve-number formula) were resolved by deriving from the
  external standard methods the SI itself cites (USDA-SCS 1972; Williams et al.
  2012), not by asking -- flagged in code, not on this list.
