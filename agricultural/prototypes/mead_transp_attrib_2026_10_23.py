"""Mid-season transpiration attribution at Mead Ne3: canopy, potential transpiration, water stress and actual transpiration, engine against Cycles, same inputs."""
import os, sys, datetime as dt
sys.argv = ["x"]
import numpy as np
import mead_score_2026_10_23 as M
site = "Ne3"
soil, b, pl, lat, lon, wx, CW, CH, CYld, T = M._cache(site)
res = M.engine_run(site, soil, pl, lat, wx)
# Cycles crop daily: potential transpiration, water stress, interception, from a fresh run (cached parse has only fi, ag)
out, r = M.cycles_run(site, soil, pl, lat, lon, wx)
C = {}
for f in os.listdir(out):
    if f.startswith(("dailyCorn", "dailySoy")):
        L = open(os.path.join(out, f)).read().splitlines(); h = L[0].split(","); ix = {n: i for i, n in enumerate(h)}
        for l in L[2:]:
            p = l.split(",")
            if float(p[ix["radiation_interception"]]) > -990: C[p[0]] = dict(fi=float(p[ix["radiation_interception"]]), trp=float(p[ix["potential_transpiration"]]), ws=float(p[ix["water_stress"]]), temp=float(p[ix["temperature_factor"]]))
import shutil; shutil.rmtree(out, ignore_errors=True)
for crop in ("corn", "soy"):
    print(f"== {crop} years 2001-2016: 20-day means. canopy fi | potential transp mm/d | water stress (1 = none) | actual transp mm/d | actual/potential   (engine / Cycles)")
    for lo in range(140, 280, 20):
        E_ = []; C_ = []
        for y, rr in res.items():
            if y < 2001 or pl[y]["crop"] != crop: continue
            for h in rr["history"]:
                if lo <= h["doy"] < lo + 20:
                    d = (dt.date(y, 1, 1) + dt.timedelta(days=h["doy"] - 1)).isoformat()
                    if d in C and d in CW:
                        E_.append((h["canopy"], h["trp_mm"], h["water_stress"], h["transp_mm"]))
                        wsc = C[d]["ws"]; wsc = 1.0 - wsc / 100.0 if wsc >= 0 else np.nan   # Cycles reports stress in percent
                        C_.append((C[d]["fi"], C[d]["trp"], wsc, np.nan))
        if len(E_) < 20: continue
        e = np.nanmean(np.array(E_), 0); c = np.nanmean(np.array(C_), 0)
        # Cycles actual transpiration from dailyWater is in CW as et total; use transp only from the stored cycles daily for actual
        print(f"  {lo:3d}-{lo+19}: fi {e[0]:.2f}/{c[0]:.2f} | pot {e[1]:.2f}/{c[1]:.2f} | stress {e[2]:.2f}/{c[2]:.2f} | actual {e[3]:.2f}/ (see ET table)")
