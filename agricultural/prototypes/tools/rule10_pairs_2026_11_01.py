"""Rule 10 paired test on val100: for each fitted change, site-level grain MAE vs Cycles of the OFF version minus the ON version
(positive = the change helps), mean over sites with a 95% paired site-bootstrap interval, by N rate. Also pooled r on and off.
Reads /tmp/w/<tag>_[0-3].json written by tools/run_val.sh."""
import json, glob, numpy as np
TESTS = [("corn water exponent 2.0 vs 1.0", "v_corn_on", "v_corn_w1"), ("silage water exponent 2.0 vs 1.0", "v_sil_on", "v_sil_w1"),
         ("soybean water exponent 2.0 vs 1.0", "v_soy_on", "v_soy_w1"), ("corn seed root 25 vs 10", "v_corn_on", "v_corn_s10"),
         ("silage seed root 25 vs 10", "v_sil_on", "v_sil_s10"), ("sorghum seed root 25 vs 10", "v_sor_on", "v_sor_s10"),
         ("sorghum N onset 0.9 vs 1.0", "v_sor_on", "v_sor_r1")]
def load(t):
    D = {}
    for f in glob.glob(f"/tmp/w/{t}_[0-3].json"): D.update(json.load(open(f)))
    return D
def pairs(D, n):
    return {k.split("|")[0]: np.array(v["res"]["grain"]["pairs"]) for k, v in D.items() if f"|N{n}|" in k}
rng = np.random.default_rng(0)
for name, on, off in TESTS:
    A, B = load(on), load(off)
    if not A or not B: print(name, "missing"); continue
    for n in sorted({int(k.split("|")[1][1:]) for k in A}):
        a, b = pairs(A, n), pairs(B, n); s = sorted(set(a) & set(b))
        if not s: continue
        d = np.array([np.abs(b[x][:, 1] - b[x][:, 0]).mean() - np.abs(a[x][:, 1] - a[x][:, 0]).mean() for x in s])
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
        r = lambda P: np.corrcoef(np.vstack([P[x] for x in s]).T)[0, 1]
        print(f"{name:36s} N={n:3d} sites={len(s):3d} MAE gain {d.mean():+.3f} [{np.percentile(bs,2.5):+.3f}, {np.percentile(bs,97.5):+.3f}] r on {r(a):.3f} off {r(b):.3f}")
