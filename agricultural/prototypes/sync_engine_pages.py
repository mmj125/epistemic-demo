"""Rebuilds the embedded Python engine inside engine-demo.html and model-validation.html from the canonical
cycles_engine_validate.py (2026-10-08). Each page's ENGINE_SOURCE = the canonical file verbatim (backticks in
comments/docstrings swapped for apostrophes so the JS template literal stays valid) + that page's own tail
(SOIL_LAYERS_RAW, make_layers, crop dicts, CROPS). The tail is preserved from the page; only the crop
calibration factors are refreshed from the validation harnesses. Run: python3 sync_engine_pages.py
Why this exists: before this, the pages held hand-ported partial copies that drifted from the engine being tuned
(missing CropSyst evaporation, 5/3 root carbon, clay humification, N coefficient 140, lead-in chain, ...).
Check: python3 sync_engine_pages.py --check  (exits 1 if a page differs from what a sync would write)."""
import re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_validation as rv
import run_validation_rotation2 as r2

MARK = "const ENGINE_SOURCE = String.raw`"
HEADER = ("# ===== Synced verbatim from cycles_engine_validate.py by sync_engine_pages.py (do not hand-edit this block;\n"
          "# edit the canonical file and re-run the sync). Page-specific soil/crop definitions follow the engine. =====\n")
TAIL_MARK = "SOIL_LAYERS_RAW = ["
# page-specific crop calibration: harness value (validated against Cycles) times the page's historical ratio
PAGES = {
    "model-validation.html": dict(corn=rv.CORN["calibration_factor"], soy=r2.SOYBEAN["calibration_factor"], wheat=r2.WHEAT["calibration_factor"], wheat_cold=True),
    "engine-demo.html":      dict(corn=rv.CORN["calibration_factor"], soy=r2.SOYBEAN["calibration_factor"], wheat=round(r2.WHEAT["calibration_factor"] * 0.6427, 4), wheat_cold=False),
}

def canonical():
    return open(os.path.join(HERE, "cycles_engine_validate.py")).read().replace("`", "'")

def set_cal(tail, name, value):
    # replace calibration_factor=<number> inside the "NAME = dict(" block only
    i = tail.index(name + " = dict(")
    m = re.compile(r"calibration_factor=[0-9.]+").search(tail, i)
    return tail[:m.start()] + "calibration_factor=%s" % repr(float(value)) + tail[m.end():]

def build(page_text, cfg):
    i = page_text.index(MARK) + len(MARK)
    j = page_text.index("`;", i)
    old = page_text[i:j]
    tail = old[old.index(TAIL_MARK):]
    tail = set_cal(tail, "CORN", cfg["corn"])
    tail = set_cal(tail, "SOYBEAN", cfg["soy"])
    tail = set_cal(tail, "WHEAT", cfg["wheat"])
    if cfg["wheat_cold"] and "threshold_temp_cold_damage" not in tail[tail.index("WHEAT = dict("):tail.index("WHEAT = dict(") + 4000].split("\nWINTER_RYE")[0]:
        k = tail.index("WHEAT = dict(") + len("WHEAT = dict(")
        tail = tail[:k] + "threshold_temp_cold_damage=-10, " + tail[k:]
    new = "\n" + HEADER + canonical() + "\n" + tail
    return page_text[:i] + new + page_text[j:]

def main():
    check = "--check" in sys.argv
    bad = False
    for page, cfg in PAGES.items():
        path = os.path.join(HERE, page)
        t = open(path).read()
        n = build(t, cfg)
        if check:
            if n != t: print(page, "DIFFERS from a fresh sync"); bad = True
            else: print(page, "in sync")
        else:
            open(path, "w").write(n); print(page, "synced (%d -> %d bytes)" % (len(t), len(n)))
    if bad: sys.exit(1)

if __name__ == "__main__":
    main()
