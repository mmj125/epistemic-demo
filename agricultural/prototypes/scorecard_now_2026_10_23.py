"""One uniform scorecard at the current defaults (2026-10-23): five crops, pooled r, grain level and MAE, and N-loss levels in kg N/ha per year, engine against Cycles v1.5.20.
Spring crops: 94 fresh sites, YEAR_STEP=2, continuous chain; wheat: 60 sites, FALLN=60. Inputs are the run files named below."""
import json, glob, sys, numpy as np
RUN = dict(corn="cur_corn", silage="cur_silage", sorghum="cur_sorghum", soybean="cur2_soy")
def load(pre):
    D = {}
    for f in glob.glob(f"/tmp/w/{pre}_[0-3].json"): D.update(json.load(open(f)))
    return D
def row(label, P, loss=None):
    P = np.vstack(P); r = np.corrcoef(P[:, 0], P[:, 1])[0, 1]; mae = np.abs(P[:, 1] - P[:, 0]).mean(); bias = (P[:, 1] - P[:, 0]).mean()
    s = f"{label:16s} n={len(P):5d}  r {r:.3f}  Cycles mean {P[:,0].mean():5.2f}  bias {bias:+.2f} ({100*bias/P[:,0].mean():+.0f}%)  MAE {mae:.2f}"
    if loss: s += "  | " + "  ".join(f"{k} {v[1]:.1f}/{v[0]:.1f}" for k, v in loss.items())
    print(s)
for crop, pre in RUN.items():
    try: D = load(pre)
    except Exception as e: print(crop, "missing", e); continue
    if not D: print(crop, "no files"); continue
    levels = sorted({int(k.split("|")[1][1:]) for k in D})
    for n in levels:
        P = []; L = {}
        for k, v in D.items():
            if f"|N{n}|" not in k: continue
            P.append(np.array(v["res"]["grain"]["pairs"]))
            for q in ("leach", "denit", "volat", "n2o"):
                if q in v["res"]: L.setdefault(q, []).append((v["res"][q]["real"], v["res"][q]["model"]))
        loss = {q: (np.mean([a for a, b in x]), np.mean([b for a, b in x])) for q, x in L.items()} if L else None
        row(f"{crop} N={n}", P, {q: (loss[q][0], loss[q][1]) for q in loss} if loss else None)
def lw(pre):
    D = {}
    for o in (0, 1):
        for r in json.load(open(f"/tmp/w/{pre}_{o}.json")): D[r[0]] = r[2]
    return D
A = lw("cur2_wheat")
for key in ("N0|calib", "N90|calib", "N150|calib"):
    row(f"wheat {key[:-6]}", [np.array(A[s][key]["grain"]["pairs"]) for s in sorted(A)])
print("(loss columns are engine/Cycles in kg N/ha per year; wheat harness records no N losses)")
# metrics beyond pooled r (CCC, Nash-Sutcliffe, site-mean and within-site correlation, anomaly spread, bias by yield tercile, N response), added 2026-10-23
import runpy
print()
sys.argv = ["metrics_panel", "corn=cur_corn", "silage=cur_silage", "sorghum=cur_sorghum"]
runpy.run_path("metrics_panel_2026_10_23.py", run_name="__main__")
