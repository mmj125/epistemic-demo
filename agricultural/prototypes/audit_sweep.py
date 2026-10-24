"""Relic audit (2026-10-14): move each fitted engine constant by 0.7x and 1.4x, run the 28-site scorecard, and report which metrics
improve. A constant whose neighbour beats its current value on the held-out sites too was fitted against an engine state that has
since changed. Usage: python3 audit_sweep.py   -> /tmp/w/audit_sweep.json (incremental), prints a table at the end."""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scorecard as S
import rhizo_engine as E
PARAMS = ["SIXPOOL_ML_N_B","SIXPOOL_ML_N_C","SIXPOOL_ML_KS","SIXPOOL_ML_EPS_H","SIXPOOL_N_HALF_MGKG","SIXPOOL_N_POT_MULT","SIXPOOL_N_FMIN",
          "SIXPOOL_ML_FD_R0","SIXPOOL_ML_ROOT_DECAY_M","DENITRIF_K_REL","NITRIF_RMAX","VOLATILIZATION_RATE_A","N2O_NITRIF_FRAC","N2O_DENIT_A",
          "RESIDUE_COVER_K","NET_GROWTH_FRACTION","ROOT_DENSITY_DECAY_M","SOIL_EVAP_SCALE"]
OUT = "/tmp/w/audit_sweep.json"
def run(overrides):
    tmp = {"tuning": "/tmp/aud_t.json", "heldout": "/tmp/aud_h.json"}
    procs = [subprocess.Popen([sys.executable, os.path.join(HERE, "scorecard.py"), "--worker", tmp[k], h, "0"] + overrides,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for k, h in (("tuning", "0"), ("heldout", "1"))]
    for p in procs: p.wait()
    return {k: S.metrics(v) for k, v in tmp.items()}
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
if "base" not in res: res["base"] = run([]); json.dump(res, open(OUT, "w"))
for p in PARAMS:
    v0 = getattr(E, p)
    for f in (0.7, 1.4):
        key = f"{p}x{f}"
        if key in res: continue
        res[key] = run([f"{p}={v0 * f!r}"]); json.dump(res, open(OUT, "w"))
        print("done", key, flush=True)
