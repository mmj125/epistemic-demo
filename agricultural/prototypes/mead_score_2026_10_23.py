"""Mead (AmeriFlux US-Ne1/2/3) scorer: engine and Cycles v1.5.20 on the same inputs against tower and BIF observations.
Inputs: site soil from the BIF (texture; organic carbon 0 to 30 cm; deeper carbon assumed), the engine's gridded weather cell, the maize/soybean sequence,
planting days (documented 2014 to 2016, else the documented 2014 to 2021 mean), nitrogen (documented where recorded, else an assumed rate).
No engine constant is changed here."""
import os, sys, json, math, shutil, subprocess, csv, datetime as dt
os.environ.setdefault("REGIONAL", "0")
import numpy as np
import run_validation_multisite as m
import rhizo_engine as E
CY = m.CY
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "ameriflux")
Y0, Y1 = 1997, 2016
SITES = {"Ne1": dict(bif="US-Ne1_bif.json", seq="corn_cont", irrigated=True), "Ne2": dict(bif="US-Ne2_bif.json", seq="rot_odd_corn", irrigated=True),
         "Ne3": dict(bif="US-Ne3_bif.json", seq="rot_odd_corn", irrigated=False)}
PLANT_CORN, PLANT_SOY = 121, 134           # documented 2014 to 2021 means at Ne3
N_ASSUMED = 150.0                          # kg N/ha for maize in undocumented years, rainfed (documented 2015 to 2020 rates: 134, 157, 157)
N_ASSUMED_IRR = 200.0                      # irrigated maize (documented 2014 to 2016 totals at Ne1: about 190 to 250)
IRR_TRIGGER, IRR_DEPTH_M, IRR_START, IRR_STOP = 0.5, 1.0, 160, 240   # depletion trigger, refill depth, window (documented Ne1 events fall on days 161 to 234)

import re as _re0
def irrigation_events(bif):
    """{year: {doy: mm}} from the BIF irrigation records: depth parsed from the comment (inches), spread evenly over the event's days."""
    out = {}
    for e in bif.get("irrigation", []):
        txt = (e.get("DM_COMMENT") or "") + " "
        mm_ = _re0.search(r'(\d*\.\d+|\d+)\s*(?:"|\u201d|in\s*\.?(?=[\s,;]))', txt)
        if not mm_: continue
        mm = float(mm_.group(1)) * 25.4
        if not (3.0 <= mm <= 80.0): continue
        d0 = dt.date(int(e["DM_DATE_START"][:4]), int(e["DM_DATE_START"][4:6]), int(e["DM_DATE_START"][6:8]))
        de = e.get("DM_DATE_END"); d1 = dt.date(int(de[:4]), int(de[4:6]), int(de[6:8])) if de else d0
        n = max(1, (d1 - d0).days + 1)
        for k in range(n):
            d = d0 + dt.timedelta(days=k); out.setdefault(d.year, {}); out[d.year][d.timetuple().tm_yday] = out[d.year].get(d.timetuple().tm_yday, 0.0) + mm / n
    return out

def score_years(site): return range(2014, 2017) if SITES[site]["irrigated"] else range(2001, 2017)

def crop_in_year(site, y):
    s = SITES[site]["seq"]
    return "corn" if s == "corn_cont" else ("corn" if y % 2 == 1 else "soy")

def soil_layers(site):
    """Uniform texture from the BIF, 1.8 m deep. Organic carbon: BIF 0 to 15 and 15 to 30 cm (g/kg, mean of the two sampling dates, as percent);
    deeper values are an ASSUMPTION (Mollisol decline), labelled in the output."""
    b = json.load(open(os.path.join(DATA, SITES[site]["bif"]))); t = b["soil_texture_pct"]
    clay, sand = float(t["SOIL_TEX_CLAY"]), float(t["SOIL_TEX_SAND"])
    import openpyxl, glob
    f = [x for x in glob.glob(os.path.join(DATA, "*BIF*.xlsx")) if f"US-{site}_BIF" in x][0]
    rows = [r for r in openpyxl.load_workbook(f, read_only=True, data_only=True)["AMF-BIF"].iter_rows(values_only=True)][1:]
    g = {}
    for s_, gid, grp, v, d in rows:
        if grp == "GRP_SOIL_CHEM": g.setdefault(gid, {})[v] = d
    soc = {}
    for r in g.values():
        if "SOIL_CHEM_C_ORG" in r: soc.setdefault((int(r["SOIL_CHEM_PROFILE_MIN"]), int(r["SOIL_CHEM_PROFILE_MAX"])), []).append(float(r["SOIL_CHEM_C_ORG"]) / 10.0)
    s0 = float(np.mean(soc[(0, 15)])); s1 = float(np.mean(soc[(15, 30)]))
    prof = [(0.15, s0), (0.15, s1), (0.30, 0.55 * s1), (0.40, 0.25 * s1), (0.80, 0.10 * s1)]
    return [dict(thick=th, clay=clay, sand=sand, soc=round(sc, 3)) for th, sc in prof], b

def plan(site, bif):
    """Per-year management: crop, planting day, nitrogen (kg N/ha, all at planting)."""
    out = {}
    plant_doc = {}
    for p in bif["planting"]:
        d = p["DM_DATE_START"]; y = int(d[:4]); doy = dt.date(y, int(d[4:6]), int(d[6:8])).timetuple().tm_yday
        c = (p["DM_COMMENT"] or "").lower()
        if "replant" in c or "fill" in c: continue
        plant_doc.setdefault(y, doy)
    n_doc = {2015: 134.5} if site == "Ne3" else {}
    irr_ev = irrigation_events(bif) if SITES[site]["irrigated"] else {}
    for y in range(Y0, Y1 + 1):
        c = crop_in_year(site, y)
        out[y] = dict(irr_events=irr_ev.get(y), crop=c, plant=plant_doc.get(y, PLANT_CORN if c == "corn" else PLANT_SOY), n=(n_doc.get(y, N_ASSUMED_IRR if SITES[site]["irrigated"] else N_ASSUMED) if c == "corn" else 0.0),
                      documented_plant=y in plant_doc, documented_n=y in n_doc)
    return out

CROPNAME = dict(corn="CornRM.90", soy="SoybeanMG.5")

def weather_for(site, b):
    lat, lon = float(b["location"]["LOCATION_LAT"]), float(b["location"]["LOCATION_LONG"])
    wx, _ = m.fd.resolve_field_weather(lat, lon)
    return lat, lon, {y: wx[y] for y in range(Y0, Y1 + 1)}

def cycles_run(site, soil, pl, lat, lon, wx, keep=False):
    nm = f"mead{site}"
    cell_lat = m.lat_of(lat, lon)
    saved = m.N_LEVELS; m.N_LEVELS = [0]
    m.write_inputs(nm, lat, lon, wx, soil, cell_lat); m.N_LEVELS = saved
    R = Y1 - Y0 + 1
    ops = ["# Mead sequence, fixed planting days\n"]
    base = open(f"{CY}/input/ContinuousCorn.operation").read()
    plant_tpl = base[base.index("PLANTING"):base.index("TILLAGE")]
    for i, y in enumerate(range(Y0, Y1 + 1), 1):
        p = pl[y]; blk = plant_tpl
        import re
        blk = re.sub(r"(?m)^YEAR\s+\S+", f"YEAR                                {i}", blk, count=1)
        blk = re.sub(r"(?m)^DOY\s+\S+", f"DOY                                 {p['plant']}", blk, count=1)
        blk = re.sub(r"(?m)^END_DOY\s+\S+", f"END_DOY                             {p['plant']}", blk, count=1)
        blk = re.sub(r"(?m)^CROP\s+\S+", f"CROP                                {CROPNAME[p['crop']]}", blk, count=1)
        blk = re.sub(r"(?m)^MIN_SMC\s+\S+", "MIN_SMC                             -999", blk, count=1)
        blk = re.sub(r"(?m)^MIN_SOIL_TEMP\s+\S+", "MIN_SOIL_TEMP                       -999", blk, count=1)
        if SITES[site]["irrigated"] and not p.get("irr_events"): blk = re.sub(r"(?m)^USE_AUTO_IRR\s+\S+", "USE_AUTO_IRR                        1", blk, count=1)
        ops.append(blk.rstrip() + "\n\n")
        ops.append(f"TILLAGE\nYEAR                                {i}\nDOY                                 {p['plant']}\nTOOL                                Planter_double_disk_opnr\nCROP_NAME                           N/A\nFRAC_THERMAL_TIME                   0.0\nKILL_EFFICIENCY                     0.0\n\n")
        for doy_, mm_ in sorted((p.get("irr_events") or {}).items()):
            ops.append(f"FIXED_IRRIGATION\nYEAR                                {i}\nDOY                                 {int(doy_)}\nVOLUME                              {mm_:.2f}\n\n")
        if p["n"] > 0:
            ops.append(f"FIXED_FERTILIZATION\nYEAR                                {i}\nDOY                                 {p['plant']}\nSOURCE                              32-00-00_Urea_Ammonium_Nitrate_Solution\nMASS                                {p['n']/0.32:.2f}\nFORM                                Liquid\nMETHOD                              Broadcast\nDEPTH                               0.05\n\n")
    if SITES[site]["irrigated"]:
        for cn in sorted({CROPNAME[pl[y]["crop"]] for y in pl}):
            ops.append(f"AUTO_IRRIGATION\nCROP                                {cn}\nSTART_DOY                           {IRR_START}\nSTOP_DOY                            {IRR_STOP}\nWATER_DEPLETION                     {IRR_TRIGGER}\nDEPTH                               {IRR_DEPTH_M}\n\n")
    open(f"{CY}/input/{nm}M.operation", "w").write("".join(ops))
    c = open(f"{CY}/input/ContinuousCorn.ctrl").read().replace("ContinuousCorn.operation", f"{nm}M.operation").replace("GenericHagerstown.soil", f"{nm}.soil").replace("RockSprings.weather", f"{nm}.weather")
    c = re.sub(r"SOIL_LAYERS\s+\d+", f"SOIL_LAYERS             {len(soil)}", c)
    c = re.sub(r"SIMULATION_START_YEAR\s+\d+", f"SIMULATION_START_YEAR   {Y0}", c); c = re.sub(r"SIMULATION_END_YEAR\s+\d+", f"SIMULATION_END_YEAR     {Y1}", c)
    c = re.sub(r"ROTATION_SIZE\s+\d+", f"ROTATION_SIZE           {R}", c)
    open(f"{CY}/input/{nm}M.ctrl", "w").write(c)
    r = subprocess.run(["./Cycles", f"{nm}M"], cwd=CY, capture_output=True, text=True)
    out = f"{CY}/output/{nm}M"
    return out, r

import re
if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "cycles_probe":
    site = sys.argv[2]; soil, b = soil_layers(site); pl = plan(site, b); lat, lon, wx = weather_for(site, b)
    out, r = cycles_run(site, soil, pl, lat, lon, wx)
    print("rc", r.returncode, r.stdout[-300:], r.stderr[-300:]); print(sorted(os.listdir(out)) if os.path.isdir(out) else "no output dir")

def _irr_for(irr, p):
    """Documented events replace the auto rule in years that have them (the engine takes dated irrigation as mm by day of year)."""
    if p.get("irr_events"):
        return dict(irrigation_events={int(k): v for k, v in p["irr_events"].items()})
    return dict(irr)

def engine_run(site, soil, pl, lat, wx):
    import engine_api as api
    ml = api._make_layers(soil)
    corn = dict(api._CORN); corn.update(lat_deg=lat, make_layers=ml)
    LEG = os.environ.get("MEAD_LEGUME", "1") == "1"   # 2026-10-23: the legume N path (soil N first, fixation, residue N return); MEAD_LEGUME=0 is the earlier soybean path with no N model
    soy = dict(api._SOYBEAN_N if LEG else api._SOYBEAN); soy.update(lat_deg=lat, make_layers=ml)
    base = E.standard_kwargs(soil, 0); base["record_history"] = True
    irr = {}
    if SITES[site]["irrigated"]:
        z = 0.0; n = 0
        for l in soil:
            z += l["thick"]; n += 1
            if z >= IRR_DEPTH_M - 1e-9: break
        irr = dict(irrigation_trigger_frac=1.0 - IRR_TRIGGER, irrigation_refill_layers=n, irrigation_window=(IRR_START, IRR_STOP))
    yp = {}
    for y, p in pl.items():
        if p["crop"] == "corn":
            k = dict(n_rate_kg_ha=p["n"], fertilizer_source="uan") if p["n"] > 0 else dict(n_rate_kg_ha=0)
            k.update(_irr_for(irr, p)); yp[y] = dict(crop=corn, plant_doy=p["plant"], kw=k)
        else:
            kws = dict(record_history=True, **_irr_for(irr, p))
            if LEG: kws = dict(base, n_rate_kg_ha=0, **kws)
            yp[y] = dict(crop=soy, plant_doy=p["plant"], kw_replace=kws)
    return E.simulate_continuous(wx, corn, carry_n=True, year_plan=yp, **base)

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "engine_probe":
    site = sys.argv[2]; soil, b = soil_layers(site); pl = plan(site, b); lat, lon, wx = weather_for(site, b)
    r = engine_run(site, soil, pl, lat, wx)
    for y in (2001, 2002, 2003):
        v = r[y]; print(y, pl[y]["crop"], {k: (round(v[k], 2) if isinstance(v.get(k), (int, float)) else None) for k in ("grain", "ag", "total", "plant_doy")}, "hist days", len(v.get("history") or []))
    print(sorted(k for k in r[2001].keys())[:40])

# ------------------------------------------------------------------ observations
C_FRAC = 0.44            # gC per g dry matter, grain and residue (BIF notes 43.9 percent for foliage); an assumption for the conversion to Mg/ha
LAMBDA_MJ = 2.45         # latent heat of vaporisation, MJ/kg
K_EXT = 0.55             # light extinction coefficient to turn LAI into intercepted fraction; an assumption

def tower(site):
    rd = csv.reader(open(os.path.join(DATA, f"US-{site}_daily.csv"))); h = next(rd); rows = list(rd)
    ix = {n: i for i, n in enumerate(h)}
    def num(r, n):
        i = ix.get(n); 
        if i is None or i >= len(r) or r[i] == "": return np.nan
        return float(r[i])
    swc_cols = [n for n in h if n.startswith("SWC_") and "_PI_" not in n and not n.endswith("_SD")]
    ws_col = [n for n in h if n.startswith("WS_") and "_PI_" not in n][0]
    T = {}
    for r in rows:
        le = num(r, "LE_PI_F_1_1_1"); 
        if np.isnan(le): le = num(r, "LE_1_1_1")
        sw = [num(r, n) for n in swc_cols]; sw = [x for x in sw if not np.isnan(x)]
        T[r[0]] = dict(et=le * 86400.0 / (LAMBDA_MJ * 1e6) if not np.isnan(le) else np.nan, swc=float(np.mean(sw)) if sw else np.nan, p=num(r, "P_PI_F_1_1_1") * 24.0, ta=num(r, "TA_PI_F_1_1_1"), rh=num(r, "RH_PI_F_1_1_1"), ws=num(r, ws_col))
    return T, len(swc_cols)

def date_of(y, doy): return (dt.date(y, 1, 1) + dt.timedelta(days=int(doy) - 1)).isoformat()

def cycles_parse(out, soil):
    def rd(f):
        L = open(os.path.join(out, f)).read().splitlines(); h = L[0].split(","); return h, [l.split(",") for l in L[2:]]
    h, rows = rd("dailyWater.csv"); ix = {n: i for i, n in enumerate(h)}
    th = np.array([t["thick"] for t in soil]); th = th / th.sum()
    W = {}
    for r in rows:
        sm = np.array([float(r[ix[f"soil_moisture_content.{k}"]]) for k in range(1, len(soil) + 1)])
        W[r[0]] = dict(et=float(r[ix["soil_evaporation"]]) + float(r[ix["residue_evaporation"]]) + float(r[ix["transpiration"]]), theta=float((sm * th).sum()))
    H = {}
    for f in os.listdir(out):
        if f.startswith("daily") and (f.startswith("dailyCorn") or f.startswith("dailySoy")):
            h2, r2 = rd(f); i2 = {n: i for i, n in enumerate(h2)}
            for r in r2:
                v = float(r[i2["radiation_interception"]]); 
                if v > -990: H[r[0]] = dict(fi=v, ag=float(r[i2["aboveground_biomass"]]))
    h3, r3 = rd("harvest.csv"); i3 = {n: i for i, n in enumerate(h3)}
    Y = {}
    for r in r3:
        y = int(r[0][:4]); Y[y] = dict(grain=float(r[i3["grain_yield"]]), ag=float(r[i3["total_biomass"]]) - float(r[i3["root_biomass"]]), crop=r[i3["crop"]], plant=r[i3["planting_date"]])
    return W, H, Y

def engine_parse(res, soil):
    th = np.array([t["thick"] for t in soil]); th = th / th.sum()
    D = {}; Y = {}
    for y, r in res.items():
        Y[y] = dict(grain=r.get("grain", 0.0), ag=r.get("ag", 0.0))
        for h in r.get("history") or []:
            d = date_of(y, h["doy"])
            D[d] = dict(et=h["soil_evap_mm"] + h["res_evap_mm"] + h["transp_mm"], theta=float((np.array(h["theta"]) * th).sum()), fi=h["canopy"], ag=h["ag_mg_ha"])
    return D, Y

def lai_of(fi): return -math.log(max(1e-6, 1.0 - min(fi, 0.999))) / K_EXT

def corr(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); k = ~(np.isnan(a) | np.isnan(b))
    return float(np.corrcoef(a[k], b[k])[0, 1]) if k.sum() > 3 else float("nan")

def report(site, keep_cycles=False):
    soil, b = soil_layers(site); pl = plan(site, b); lat, lon, wx = weather_for(site, b)
    res = engine_run(site, soil, pl, lat, wx); ED, EY = engine_parse(res, soil)
    out, r = cycles_run(site, soil, pl, lat, lon, wx)
    CW, CH, CYld = cycles_parse(out, soil)
    if not keep_cycles: shutil.rmtree(out, ignore_errors=True)
    T, nsens = tower(site)
    print(f"===== {site}: soil 0-15 cm clay {soil[0]['clay']:.0f}% C {soil[0]['soc']:.2f}%; weather cell; tower SWC sensors {nsens}")
    # ---- seasonal ET per year
    print("year crop  days | ET mm/day over days with tower ET: tower  engine  cycles | season total mm (mean daily x days): tower engine cycles")
    rows = []
    for y in score_years(site):
        ds = [d for d in ED if d.startswith(str(y))]
        ok = [d for d in ds if d in CW and d in T and not np.isnan(T[d]["et"])]
        if len(ok) < 30: continue
        t = np.mean([T[d]["et"] for d in ok]); e = np.mean([ED[d]["et"] for d in ok]); c = np.mean([CW[d]["et"] for d in ok]); n = len(ds)
        rows.append((y, t, e, c, n)); print(f"{y} {pl[y]['crop']:5s} {n:3d} | {t:5.2f} {e:5.2f} {c:5.2f} | {t*n:5.0f} {e*n:5.0f} {c*n:5.0f}")
    R = np.array([[x[1], x[2], x[3], x[4]] for x in rows])
    print(f"  mean daily ET: tower {R[:,0].mean():.2f}  engine {R[:,1].mean():.2f}  Cycles {R[:,2].mean():.2f} mm/d;  interannual r vs tower: engine {corr(R[:,0],R[:,1]):.2f}  Cycles {corr(R[:,0],R[:,2]):.2f};  engine vs Cycles {corr(R[:,1],R[:,2]):.2f}")
    # ---- daily dynamics (7-day means) within growing seasons
    def roll(x, k=7): x = np.asarray(x, float); return np.array([np.nanmean(x[max(0, i - k + 1):i + 1]) if np.any(~np.isnan(x[max(0, i - k + 1):i + 1])) else np.nan for i in range(len(x))])
    dts = sorted(d for d in ED if int(d[:4]) in score_years(site) and d in CW and d in T)
    te = roll([T[d]["et"] for d in dts]); ee = roll([ED[d]["et"] for d in dts]); ce = roll([CW[d]["et"] for d in dts])
    print(f"  7-day ET, all in-season days: r tower~engine {corr(te,ee):.2f}  tower~Cycles {corr(te,ce):.2f}  engine~Cycles {corr(ee,ce):.2f}  (n={len(dts)})")
    # ---- soil water: within-year anomalies of the profile mean
    def anom(vals, dts):
        out = np.full(len(dts), np.nan); yrs = np.array([d[:4] for d in dts])
        for y in set(yrs):
            k = yrs == y; v = np.array(vals, float)[k]; out[k] = v - np.nanmean(v)
        return out
    ts = anom([T[d]["swc"] for d in dts], dts); es = anom([ED[d]["theta"] for d in dts], dts); cs = anom([CW[d]["theta"] for d in dts], dts)
    print(f"  soil water within-season anomalies (profile mean): r tower~engine {corr(ts,es):.2f}  tower~Cycles {corr(ts,cs):.2f}  engine~Cycles {corr(es,cs):.2f}")
    # ---- yield and above-ground biomass
    print("  yield (Mg/ha dry matter; observed from gC m-2 at 44% C): year crop | grain obs engine Cycles | above-ground obs engine Cycles")
    prod = {}
    for p in sorted(b["production"], key=lambda r: r["AG_PROD_DATE_START"]):
        prod.setdefault(int(p["AG_PROD_DATE_START"][:4]), {})[p["AG_PROD_CROP_ORGAN"]] = float(p["AG_PROD_CROP"]) / C_FRAC / 100.0
    for y in sorted(prod):
        o = prod[y]; og = o.get("Fruits", np.nan); ot = o.get("Total", np.nan)
        print(f"  {y} {pl[y]['crop']:5s} | {og:5.2f} {EY[y]['grain']:5.2f} {CYld.get(y,{}).get('grain',np.nan):5.2f} | {ot:5.2f} {EY[y]['ag']:5.2f} {CYld.get(y,{}).get('ag',np.nan):5.2f}")
    # ---- canopy: LAI measured, models via interception
    obs = {l["LAI_DATE"]: float(l["LAI_TOT"]) for l in b["lai"]}
    pairs = [(v, lai_of(ED[f"{d[:4]}-{d[4:6]}-{d[6:]}"]["fi"]), lai_of(CH[f"{d[:4]}-{d[4:6]}-{d[6:]}"]["fi"])) for d, v in obs.items() if f"{d[:4]}-{d[4:6]}-{d[6:]}" in ED and f"{d[:4]}-{d[4:6]}-{d[6:]}" in CH]
    P = np.array(pairs)
    _mo = np.array([int(d[4:6]) for d, v in obs.items() if f"{d[:4]}-{d[4:6]}-{d[6:]}" in ED and f"{d[:4]}-{d[4:6]}-{d[6:]}" in CH])
    if len(P) > 3:
        for _m in (6, 7, 8, 9):
            _k = _mo == _m
            if _k.sum() >= 3: print(f"  LAI month {_m} (n={_k.sum()}): observed {P[_k,0].mean():.2f} engine {P[_k,1].mean():.2f} Cycles {P[_k,2].mean():.2f}")
    if len(P) > 3:
        print(f"  LAI (n={len(P)} dates 2001-2007; models via fi, k={K_EXT}): r obs~engine {corr(P[:,0],P[:,1]):.2f} obs~Cycles {corr(P[:,0],P[:,2]):.2f}; mean obs {P[:,0].mean():.2f} engine {P[:,1].mean():.2f} Cycles {P[:,2].mean():.2f}; max obs {P[:,0].max():.2f} engine {P[:,1].max():.2f} Cycles {P[:,2].max():.2f}")
    return dict(site=site)

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "report":
    for s_ in sys.argv[2:]: report(s_)

# ------------------------------------------------------------------ variants: engine settings against the same tower and Cycles
def tower_rain_weather(wx, T):
    """Copy of the weather with each day's rain replaced by the tower's measured rain where the tower has it (hourly records, so mean x 24)."""
    import copy
    w2 = copy.deepcopy(wx)
    for y in w2:
        for doy, r in w2[y].items():
            p = T.get(date_of(y, doy), {}).get("p", np.nan)
            if not np.isnan(p): r["pp"] = max(0.0, p)
    return w2

def tower_adjusted_weather(wx, T):
    """Gridded weather with the daily mean temperature and humidity shifted to the tower's (gridded diurnal ranges kept) and wind set to the tower's where it has
    a value, else scaled by the median tower/gridded wind ratio. Solar and rain are the gridded ones. A hybrid for isolating forcing from model physics."""
    import copy
    w2 = copy.deepcopy(wx); ratios = []
    for y in wx:
        for doy, r in wx[y].items():
            t = T.get(date_of(y, doy), {})
            if t and not np.isnan(t.get("ws", np.nan)) and r["wind"] > 0: ratios.append(t["ws"] / r["wind"])
    k = float(np.median(ratios)) if ratios else 1.0
    for y in w2:
        for doy, r in w2[y].items():
            t = T.get(date_of(y, doy), {})
            ta, rh, ws = t.get("ta", np.nan), t.get("rh", np.nan), t.get("ws", np.nan)
            if not np.isnan(ta):
                dT = ta - (r["tx"] + r["tn"]) / 2.0; r["tx"] += dT; r["tn"] += dT
            if not np.isnan(rh):
                dR = rh - (r["rhx"] + r["rhn"]) / 2.0; r["rhx"] = float(min(100.0, max(5.0, r["rhx"] + dR))); r["rhn"] = float(min(r["rhx"], max(5.0, r["rhn"] + dR)))
            r["wind"] = ws if not np.isnan(ws) else r["wind"] * k
    print(f"  tower-adjusted weather: wind scale for days without tower wind {k:.2f}")
    return w2

def _cache(site, wxvar=None):
    import pickle
    f = f"/tmp/w/mead_ref_{site}{'_' + wxvar if wxvar else ''}.pkl"
    if os.path.exists(f): return pickle.load(open(f, "rb"))
    soil, b = soil_layers(site); pl = plan(site, b); lat, lon, wx = weather_for(site, b)
    if wxvar == "towerrain": wx = tower_rain_weather(wx, tower(site)[0])
    if wxvar == "toweradj": wx = tower_adjusted_weather(wx, tower(site)[0])
    out, r = cycles_run(site, soil, pl, lat, lon, wx); CW, CH, CYld = cycles_parse(out, soil); shutil.rmtree(out, ignore_errors=True)
    T, _ = tower(site); obj = (soil, b, pl, lat, lon, wx, CW, CH, CYld, T); pickle.dump(obj, open(f, "wb")); return obj

def _roll(x, k=7):
    x = np.asarray(x, float); return np.array([np.nanmean(x[max(0, i - k + 1):i + 1]) if np.any(~np.isnan(x[max(0, i - k + 1):i + 1])) else np.nan for i in range(len(x))])

def quick(site, ovr="", label=None, bins=True, wxvar=None):
    soil, b, pl, lat, lon, wx, CW, CH, CYld, T = _cache(site, wxvar)
    saved = {}
    for o in filter(None, ovr.split(";")):
        k, v = o.split("=", 1); saved[k] = getattr(E, k); setattr(E, k, eval(v))
    try:
        res = engine_run(site, soil, pl, lat, wx)
    finally:
        for k, v in saved.items(): setattr(E, k, v)
    ED, EY = engine_parse(res, soil)
    rows = []
    for y in score_years(site):
        ds = [d for d in ED if d.startswith(str(y))]
        ok = [d for d in ds if d in CW and d in T and not np.isnan(T[d]["et"])]
        if len(ok) < 30: continue
        rows.append((np.mean([T[d]["et"] for d in ok]), np.mean([ED[d]["et"] for d in ok]), np.mean([CW[d]["et"] for d in ok]), len(ds)))
    R = np.array(rows); dts = sorted(d for d in ED if int(d[:4]) in score_years(site) and d in CW and d in T)
    te = _roll([T[d]["et"] for d in dts]); ee = _roll([ED[d]["et"] for d in dts]); ce = _roll([CW[d]["et"] for d in dts])
    def anom(vals):
        out = np.full(len(dts), np.nan); yrs = np.array([d[:4] for d in dts])
        for y in set(yrs):
            k = yrs == y; v = np.array(vals, float)[k]; out[k] = v - np.nanmean(v)
        return out
    ts = anom([T[d]["swc"] for d in dts]); es = anom([ED[d]["theta"] for d in dts])
    err = ee - te; k = ~np.isnan(err)
    print(f"[{label or ovr or 'default'}] mean ET tower {R[:,0].mean():.2f} engine {R[:,1].mean():.2f} Cycles {R[:,2].mean():.2f} mm/d | interannual r {corr(R[:,0],R[:,1]):.2f} (Cycles {corr(R[:,0],R[:,2]):.2f}) | 7-day r tower~engine {corr(te,ee):.2f} (Cycles {corr(te,ce):.2f}) | 7-day rmse {np.sqrt(np.mean(err[k]**2)):.2f} (Cycles {np.sqrt(np.nanmean((ce-te)**2)):.2f}) | soil water r {corr(ts,es):.2f}")
    if bins:
        import datetime as _dt
        line = "   ET by 20-day bin (tower/engine/Cycles), maize years: "
        for lo in range(120, 240, 20):
            t = []; e = []; c = []
            for d in ED:
                y = int(d[:4])
                if y < 2001 or pl[y]["crop"] != "corn" or d not in CW or d not in T or np.isnan(T[d]["et"]): continue
                dd = _dt.date.fromisoformat(d).timetuple().tm_yday
                if lo <= dd < lo + 20: t.append(T[d]["et"]); e.append(ED[d]["et"]); c.append(CW[d]["et"])
            line += f"{lo}:{np.mean(t):.1f}/{np.mean(e):.1f}/{np.mean(c):.1f} "
        print(line)
    yl = "   grain obs/engine/Cycles: "
    prod = {int(p["AG_PROD_DATE_START"][:4]): float(p["AG_PROD_CROP"]) / C_FRAC / 100.0 for p in b["production"] if p["AG_PROD_CROP_ORGAN"] in ("Fruits",)}
    for y in sorted(prod): yl += f"{y}:{prod[y]:.1f}/{EY[y]['grain']:.1f}/{CYld[y]['grain']:.1f} "
    print(yl)
    return ED, EY

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "quick":
    quick(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "", wxvar=(sys.argv[4] if len(sys.argv) > 4 else None), label=(sys.argv[5] if len(sys.argv) > 5 else None))
