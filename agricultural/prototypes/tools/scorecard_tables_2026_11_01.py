"""Generate the scorecard tables from saved run files, so no number is typed by hand.
usage: scorecard_tables_2026_11_01.py [RUNDIR=/tmp/w] [OUT=scorecards/2026-11-01_consolidated]
Reads cons_{corn,silage,sorghum,soy}_[0-3].json (multisite harness) and wheat_ms.json (wheat harness, 'calib' tag).
Per crop and N rate: n sites, pooled r with 95% site-bootstrap interval, bias %, grain MAE (Mg/ha), N-loss ratio engine/Cycles,
within-site yearly r (median over sites), and the 150-to-400 N response as a share of Cycles'. Writes JSON and a markdown table."""
import json, glob, sys, os, numpy as np
RD = sys.argv[1] if len(sys.argv) > 1 else "/tmp/w"
OUT = sys.argv[2] if len(sys.argv) > 2 else "scorecards/2026-11-01_consolidated"
rng = np.random.default_rng(1)
def load(pre):
    D = {}
    for f in sorted(glob.glob(f"{RD}/{pre}_[0-3].json")): D.update(json.load(open(f)))
    return D
def by_site(D):   # {N: {site: {pairs, loss}}}
    S = {}
    for k, v in D.items():
        s, n = k.split("|")[0], int(k.split("|")[1][1:])
        S.setdefault(n, {})[s] = v["res"]
    return S
def wheat():
    R = json.load(open(f"{RD}/wheat_ms.json")); S = {}
    for site, _, res in R:
        for key, row in res.items():
            if not key.endswith("|calib"): continue
            S.setdefault(int(key.split("|")[0][1:]), {})[site] = row
    return S
def stats(S):
    sites = sorted(S); P = {s: np.array(S[s]["grain"]["pairs"]) for s in sites}
    allp = np.vstack(list(P.values())); r = lambda A: np.corrcoef(A[:, 0], A[:, 1])[0, 1]
    bs = []
    for _ in range(500):
        idx = rng.integers(0, len(sites), len(sites)); bs.append(r(np.vstack([P[sites[i]] for i in idx])))
    ws = [np.corrcoef(p[:, 0], p[:, 1])[0, 1] for p in P.values() if len(p) > 4 and p[:, 0].std() > 0 and p[:, 1].std() > 0]
    d = dict(n_sites=len(sites), n_pairs=len(allp), r=r(allp), r_lo=float(np.percentile(bs, 2.5)), r_hi=float(np.percentile(bs, 97.5)),
             bias_pct=100 * (allp[:, 1] - allp[:, 0]).mean() / allp[:, 0].mean(), mae=float(np.abs(allp[:, 1] - allp[:, 0]).mean()),
             within_site_r_median=float(np.median(ws)) if ws else None, cycles_mean=float(allp[:, 0].mean()), engine_mean=float(allp[:, 1].mean()))
    for q in ("leach", "denit", "volat", "n2o"):
        x = [(S[s][q]["real"], S[s][q]["model"]) for s in sites if q in S[s]]
        if x: d["ratio_" + q] = float(np.mean([b for a, b in x]) / np.mean([a for a, b in x]))
    return d
def response(SS, lo, hi):   # mean grain change between two N rates, engine / Cycles, on sites present at both
    c = sorted(set(SS[lo]) & set(SS[hi])); e = lambda s, n, j: np.mean(np.array(SS[n][s]["grain"]["pairs"])[:, j])
    dc = np.mean([e(s, hi, 0) - e(s, lo, 0) for s in c]); de = np.mean([e(s, hi, 1) - e(s, lo, 1) for s in c])
    return float(de / dc) if dc else None
res = {}
for crop, pre in (("corn", "cons_corn"), ("silage", "cons_silage"), ("sorghum", "cons_sorghum"), ("soybean", "cons_soy")):
    D = load(pre)
    if not D: continue
    SS = by_site(D)
    if crop == "soybean": SS = {150: SS[150]}   # legume path has no N input, the three N rates are identical runs
    res[crop] = {str(n): stats(SS[n]) for n in sorted(SS)}
    if 150 in SS and 400 in SS: res[crop]["response_150_400"] = response(SS, 150, 400)
    if 0 in SS and 150 in SS: res[crop]["response_0_150"] = response(SS, 0, 150)
try:
    SS = wheat(); res["wheat"] = {str(n): stats(SS[n]) for n in sorted(SS)}
    res["wheat"]["response_0_90"] = response(SS, 0, 90); res["wheat"]["response_90_150"] = response(SS, 90, 150)
except Exception as e: print("wheat missing:", e)
json.dump(res, open(OUT + ".json", "w"), indent=1)
L = ["| Crop | N | Sites | Pooled r [95% CI] | Bias % | MAE Mg/ha | Within-site r vs Cycles (median) | Leach | Denit | Volat | N2O |", "|---|---|---|---|---|---|---|---|---|---|---|"]
f = lambda x, p=2: "" if x is None else f"{x:.{p}f}"
for crop, d in res.items():
    for n, s in d.items():
        if not isinstance(s, dict): continue
        L.append(f"| {crop} | {n} | {s['n_sites']} | {s['r']:.3f} [{s['r_lo']:.3f}, {s['r_hi']:.3f}] | {s['bias_pct']:+.1f} | {s['mae']:.2f} | {f(s['within_site_r_median'])} | "
                 + " | ".join(f(s.get('ratio_' + q)) for q in ("leach", "denit", "volat", "n2o")) + " |")
L += ["", "N response, engine as a share of Cycles' mean grain change:"]
for crop, d in res.items():
    for k, v in d.items():
        if k.startswith("response") and v is not None: L.append(f"- {crop} {k[9:].replace('_', ' to ')}: {v:.2f}")
open(OUT + ".md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
