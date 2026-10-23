"""Bound on the nitrate-surplus hypothesis (2026-10-23): force Cycles' daily profile NO3 and NH4 into the engine in every window (E.NPOOL_FORCE) and compare annual
denitrification, N2O, leaching and volatilization with Cycles, for the published APEX law at amplitude 2.5 and 1.0 and for the old fitted law. 24 sites, corn, N=0 and 150, years 1983 on."""
import os, sys, json, csv, shutil, subprocess
os.environ.setdefault("REGIONAL", "0"); os.environ["LEAD_YEARS"] = "continuous"; sys.path.insert(0, '/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from cover_chain_2026_10_21 import corn_crop
from multiprocessing import Pool
S = json.load(open('/tmp/w/s24.json')); SITES = sorted(S)
CONF = {"free, APEX 2.5": dict(force=False, apex=True, amp=2.5), "forced pool, APEX 2.5": dict(force=True, apex=True, amp=2.5),
        "forced pool, APEX 1.0": dict(force=True, apex=True, amp=1.0), "forced pool, old fitted law": dict(force=True, apex=False, amp=2.5)}
def annual(d):
    A = {}
    for line in open(d + "annualN.csv").readlines()[2:]:
        q = line.strip().split(",")
        if len(q) >= 12: A[int(q[0])] = dict(leach=float(q[4]) + float(q[5]), denit=float(q[8]), volat=float(q[10]), n2o=float(q[11]))
    return A
def one(site):
    lat, lon = S[site]; wx, _ = m.fd.resolve_field_weather(lat, lon); soil, _, _ = m.fd.resolve_field_soil(lat, lon); cl = m.lat_of(lat, lon); m.REG_LON = lon
    nm = site + "np"; m.write_inputs(nm, lat, lon, wx, soil, cl); out = {}
    for N in (0, 150):
        subprocess.run(["./Cycles", f"{nm}N{N}"], cwd=m.CY, capture_output=True); d = f"{m.CY}/output/{nm}N{N}/"
        A = annual(d); F = {}
        for r in csv.DictReader(open(d + "dailyN.csv")):
            if r["date"][0] == "#": continue
            y = int(r["date"][:4]); doy = (__import__("datetime").date.fromisoformat(r["date"])).timetuple().tm_yday
            F.setdefault(y, {})[doy] = (float(r["profile_soil_NO3"]), float(r["profile_soil_NH4"]))
        shutil.rmtree(d, ignore_errors=True)
        out[f"cyc{N}"] = A
        for cn, c in CONF.items():
            E.DENIT_APEX = c["apex"]; E.DENIT_APEX_PARAMS = dict(E.DENIT_APEX_PARAMS, amp=c["amp"]); E.NPOOL_FORCE = F if c["force"] else None
            kw = E.standard_kwargs(soil, N)
            r = E.simulate_continuous(wx, corn_crop(cl, soil), carry_n=True, **kw); E.NPOOL_FORCE = None
            f = lambda v, k, fk: (v.get(k) or 0.0) + v.get(fk, 0.0)
            out[f"{cn}|{N}"] = {y: dict(grain=v["grain"], leach=f(v, "n_leached_kg_ha", "fallow_n_leached"), denit=f(v, "n_denitrified_kg_ha", "fallow_n_denitrified"), n2o=f(v, "n2o_emitted_kg_ha", "fallow_n2o"), volat=f(v, "n_volatilized_pool_kg_ha", "fallow_n_volatilized")) for y, v in r.items()}
        E.DENIT_APEX = True; E.DENIT_APEX_PARAMS = dict(E.DENIT_APEX_PARAMS, amp=2.5)
    return site, out
if __name__ == "__main__":
    R = Pool(4).map(one, SITES); json.dump(R, open('/tmp/w/npool_force.json', 'w'))
    for N in (0, 150):
        print(f"== N={N}: annual mean over site-years 1983 on (engine | Cycles), engine/Cycles ratio and rms log error (+0.5 offset)")
        for cn in CONF:
            row = []
            for k in ("denit", "n2o", "leach", "volat"):
                e = []; c = []
                for site, o in R:
                    for y, v in o[f"{cn}|{N}"].items():
                        if y >= 1983 and y in o[f"cyc{N}"]: e.append(v[k]); c.append(o[f"cyc{N}"][y][k])
                e = np.array(e); c = np.array(c)
                row.append(f"{k} {e.mean():5.1f}|{c.mean():5.1f} x{e.mean()/max(c.mean(),1e-9):.2f} rms {np.sqrt(np.mean((np.log(e+0.5)-np.log(c+0.5))**2)):.2f}")
            print(f"  {cn:28s} " + "  ".join(row))
