"""One-command scorecard for the refit (REFIT_PLAN.md, step 0).

    python3 scorecard.py                      # full run: 16 tuning + 12 held-out sites, N = 0/150/400, plus tripwires
    python3 scorecard.py --quick              # every 3rd year, 6 sites per set, no tripwires (about 1 minute)
    python3 scorecard.py NAME=VALUE ...       # override engine constants for this run, e.g. EVAP_LAW_CYCLES=True
    python3 scorecard.py --save               # store this run as the baseline (scorecard_baseline.json)
    python3 scorecard.py --no-tripwires

Needs the Cycles v1.5.20 reference outputs in /tmp/cycles-run15 (the harness builds and caches them on first use).
Prints yield error and correlation by nitrogen rate, fertilizer response, nitrogen losses (levels and marginal
responses), and the Rock Springs and pattern-check tripwires; with a baseline present it shows the change from it.
"""
import os, sys, json, math, re, subprocess, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "scorecard_baseline.json")
QUICK_SITES_T = "rock_springs,iowa,kansas,indiana,georgia,minnesota"
QUICK_SITES_H = "south_dakota,iowa_west,kentucky,louisiana,north_dakota,virginia"


def worker(out_json, heldout, overrides, quick):
    sys.path.insert(0, HERE)
    os.environ["OUT_JSON"] = out_json
    os.environ["LEAD_YEARS"] = "continuous"
    os.environ["N_LEVELS"] = "0,150,400"
    if heldout:
        os.environ["HELDOUT"] = "1"
    if quick:
        os.environ["YEAR_STEP"] = "3"
        os.environ["SITES"] = QUICK_SITES_H if heldout else QUICK_SITES_T
    import cycles_engine_validate as E
    E.ROOT_C_REALIZED_GROWTH = True
    for a in overrides:
        k, v = a.split("=", 1)
        setattr(E, k, eval(v))
    import runpy
    runpy.run_path(os.path.join(HERE, "run_validation_multisite.py"), run_name="__main__")


def corr(a, b):
    if len(a) < 3:
        return float("nan")
    try:
        return st.correlation(a, b)
    except Exception:
        return float("nan")


def metrics(path):
    d = json.load(open(path))
    sites = sorted(set(k.split("|")[0] for k in d))
    g = lambda s, N, m: d.get(f"{s}|N{N}|leadin", {}).get("res", {}).get(m)
    out = {"n_sites": len(sites)}
    for N in (0, 150, 400):
        rows = [g(s, N, "grain") for s in sites if g(s, N, "grain")]
        out[f"mae{N}"] = st.mean(r["mae"] for r in rows)
        out[f"corr{N}"] = st.mean(r["corr"] for r in rows if r["corr"] == r["corr"])
        out[f"bias{N}"] = st.mean(r["model"] - r["real"] for r in rows)
    for a, b, tag, scale in ((0, 150, "resp0_150", 100 / 150), (150, 400, "resp150_400", 100 / 250)):
        pairs = [((g(s, b, "grain")["model"] - g(s, a, "grain")["model"]) * scale, (g(s, b, "grain")["real"] - g(s, a, "grain")["real"]) * scale)
                 for s in sites if g(s, a, "grain") and g(s, b, "grain")]
        out[tag + "_model"] = st.mean(p[0] for p in pairs); out[tag + "_cycles"] = st.mean(p[1] for p in pairs)
        out[tag + "_corr"] = corr([p[0] for p in pairs], [p[1] for p in pairs])
    for m in ("leach", "denit", "volat", "n2o"):
        for N in (0, 150, 400):
            l = [math.log((g(s, N, m)["model"] + .1) / (g(s, N, m)["real"] + .1)) for s in sites if g(s, N, m)]
            out[f"{m}_rms{N}"] = math.sqrt(st.mean([x * x for x in l])) if l else float("nan")
        pairs = [((g(s, 400, m)["model"] - g(s, 150, m)["model"]) / 250, (g(s, 400, m)["real"] - g(s, 150, m)["real"]) / 250)
                 for s in sites if g(s, 150, m) and g(s, 400, m)]
        if pairs:
            out[f"{m}_marg_model"] = st.mean(p[0] for p in pairs); out[f"{m}_marg_cycles"] = st.mean(p[1] for p in pairs)
        out[f"{m}_abs400"] = st.mean(abs(g(s, 400, m)["model"] - g(s, 400, m)["real"]) for s in sites if g(s, 400, m))
    return out


def _run_script(name, overrides):
    shim = ("import sys, runpy; sys.path.insert(0, %r); import cycles_engine_validate as E\n" % HERE
            + "".join("setattr(E, %r, eval(%r))\n" % tuple(a.split("=", 1)) for a in overrides)
            + "runpy.run_path(%r, run_name='__main__')" % os.path.join(HERE, name))
    return subprocess.run([sys.executable, "-c", shim], cwd=HERE, capture_output=True, text=True).stdout


def tripwires(overrides=()):
    t = {}
    r = _run_script("run_validation.py", overrides)
    m = re.search(r"Year-to-year correlation:\s*([-\d.]+)", r)
    t["rs_corn"] = float(m.group(1)) if m else float("nan")
    r = _run_script("run_validation_rotation2.py", overrides)
    cs = re.findall(r"correlation:\s*([-\d.]+)", r)
    for name, v in zip(("rs_soybean", "rs_wheat", "rs_silage"), cs):
        t[name] = float(v)
    r = _run_script("pattern_assertions.py", overrides)
    m = re.search(r"(\d+)/(\d+) checks passed", r)
    t["patterns_passed"] = int(m.group(1)) if m else -1
    return t


ROWS = [
    ("Yield (mean per-site MAE Mg/ha | mean per-site correlation | bias)", None),
    ("mae0", "N=0 MAE"), ("corr0", "N=0 corr"), ("bias0", "N=0 bias"),
    ("mae150", "N=150 MAE"), ("corr150", "N=150 corr"), ("bias150", "N=150 bias"),
    ("mae400", "N=400 MAE"), ("corr400", "N=400 corr"),
    ("Fertilizer response (Mg/ha per 100 kg N, site mean; correlation across sites)", None),
    ("resp0_150_model", "0-150 engine"), ("resp0_150_cycles", "0-150 Cycles"), ("resp0_150_corr", "0-150 corr"),
    ("resp150_400_model", "150-400 engine"), ("resp150_400_cycles", "150-400 Cycles"), ("resp150_400_corr", "150-400 corr"),
    ("Nitrogen losses (rms log error of site means at N=0 | 150 | 400)", None),
    ("leach_rms0", "leaching N=0"), ("leach_rms150", "leaching N=150"), ("leach_rms400", "leaching N=400"),
    ("denit_rms0", "denit. N=0"), ("denit_rms150", "denit. N=150"), ("denit_rms400", "denit. N=400"),
    ("volat_rms150", "volat. N=150"), ("n2o_rms150", "N2O N=150"), ("n2o_rms400", "N2O N=400"),
    ("Marginal loss per kg N, 150 to 400 (engine | Cycles) and mean abs error at N=400 (kg N/ha)", None),
    ("leach_marg_model", "leaching engine"), ("leach_marg_cycles", "leaching Cycles"), ("leach_abs400", "leaching abs err"),
    ("denit_marg_model", "denit. engine"), ("denit_marg_cycles", "denit. Cycles"), ("denit_abs400", "denit. abs err"),
]


def show(res, base):
    for key, label in ROWS:
        if label is None:
            print("\n" + key); continue
        line = "  %-18s" % label
        for setname in ("tuning", "heldout"):
            v = res[setname].get(key)
            b = base[setname].get(key) if base and setname in base else None
            cell = "%8.3f" % v if v is not None else "     n/a"
            if b is not None and v is not None and abs(v - b) > 5e-4:
                cell += " (%+.3f)" % (v - b)
            else:
                cell += "         "
            line += "  %-3s %s" % ("tun" if setname == "tuning" else "held", cell)
        print(line)
    t = res.get("tripwires")
    if t:
        print("\nTripwires (Rock Springs correlation; pattern checks passed)")
        bt = base.get("tripwires") if base else None
        print("  " + "   ".join("%s %s%s" % (k, ("%.3f" % v if isinstance(v, float) else v),
                                           (" (%+.3f)" % (v - bt[k]) if bt and k in bt and isinstance(v, float) and abs(v - bt[k]) > 5e-4 else "")) for k, v in t.items()))


def main():
    args = sys.argv[1:]
    if args and args[0] == "--worker":
        worker(args[1], args[2] == "1", args[4:], args[3] == "1"); return
    quick = "--quick" in args; save = "--save" in args; notrip = "--no-tripwires" in args or quick
    overrides = [a for a in args if "=" in a and not a.startswith("--")]
    tmp = {"tuning": f"/tmp/scorecard_tuning_{os.getpid()}.json", "heldout": f"/tmp/scorecard_heldout_{os.getpid()}.json"}
    procs = []
    for setname, held in (("tuning", "0"), ("heldout", "1")):
        procs.append(subprocess.Popen([sys.executable, __file__, "--worker", tmp[setname], held, "1" if quick else "0"] + overrides,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    trip = None if notrip else tripwires(overrides)
    for p in procs:
        p.wait()
    res = {s: metrics(tmp[s]) for s in tmp}
    if trip is not None:
        res["tripwires"] = trip
    base = json.load(open(BASELINE)) if os.path.exists(BASELINE) and not quick else None
    print("Scorecard%s%s  (sites: %d tuning, %d held-out)" % (" [quick]" if quick else "", (" overrides: " + " ".join(overrides)) if overrides else "", res["tuning"]["n_sites"], res["heldout"]["n_sites"]))
    show(res, base)
    if save and not quick:
        json.dump(res, open(BASELINE, "w"), indent=1); print("\nsaved baseline ->", BASELINE)
    for p in tmp.values():
        if os.path.exists(p):
            os.remove(p)


if __name__ == "__main__":
    main()
