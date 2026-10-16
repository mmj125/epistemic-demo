"""Multi-site model-error harness (2026-10-02). Feeds IDENTICAL tile weather + STATSGO2 soil
(field_data.py) to native Cycles v1.4.4 and to this engine at Rock Springs / Iowa / Kansas /
Maryland, continuous corn at N=0 and N=150 (UAN, DOY 110), 1980-2016, so any gap is model error,
not input error. Needs the Cycles binary and input/ files in /tmp/cycles-run (not committed:
licensed). Writes multisite_results.json. Run: python3 run_validation_multisite.py
"""
import os, sys, math, statistics, subprocess, shutil, json
P=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,P)
import field_data as fd
import cycles_engine_validate as cev
from cycles_engine_validate import *
import run_validation as rv
cev.N_DEMAND_SCALE = float(os.environ.get("N_DEMAND_SCALE", cev.N_DEMAND_SCALE))
cev.ROOT_DENSITY_DECAY_M = float(os.environ["ROOT_DECAY"]) if os.environ.get("ROOT_DECAY") else cev.ROOT_DENSITY_DECAY_M
cev.SURFACE_AIRDRY_FRAC = float(os.environ["AIRDRY"]) if os.environ.get("AIRDRY") else cev.SURFACE_AIRDRY_FRAC
cev.N_UPTAKE_RATE_PER_DAY = float(os.environ["UPTAKE_RATE"]) if os.environ.get("UPTAKE_RATE") else cev.N_UPTAKE_RATE_PER_DAY
cev.KHE_SCALE = float(os.environ["KHE"]) if os.environ.get("KHE") else cev.KHE_SCALE
cev.FORCE_CROPSYST_EVAP = os.environ.get("CS_EVAP", "1") == "1"
if os.environ.get("PSI_ANCHOR"): cev.PSI_E_FROM_ANCHOR = os.environ["PSI_ANCHOR"]=="1"   # only override when set (a default of off here silently disabled the engine default)
if os.environ.get("CS_AD"): cev.CROPSYST_AIRDRY_FRAC = float(os.environ["CS_AD"])
if os.environ.get("FE_POW"): cev.FE_TEMP_POW = float(os.environ["FE_POW"])
if os.environ.get("FE_K"): cev.FE_TEMP_CYCLES_K = float(os.environ["FE_K"])
if os.environ.get("PLANT_GATE"): cev.PLANT_MOISTURE_GATE = os.environ["PLANT_GATE"]=="1"
if os.environ.get("NGF"): cev.NET_GROWTH_FRACTION = float(os.environ["NGF"])
if os.environ.get("NLIM"): cev.SIXPOOL_N_LIMIT = os.environ["NLIM"]=="1"
if os.environ.get("NLIM_MIN"): cev.SIXPOOL_NLIM_MIN = float(os.environ["NLIM_MIN"])
if os.environ.get("NLIM_C"): cev.SIXPOOL_NLIM_CENTER = float(os.environ["NLIM_C"])
if os.environ.get("ROOT_POW"): cev.ROOT_TRI_POW = float(os.environ["ROOT_POW"])
if os.environ.get("N_A"): cev.SIXPOOL_ML_N_A = float(os.environ["N_A"])
if os.environ.get("EPS_H"): cev.SIXPOOL_ML_EPS_H = float(os.environ["EPS_H"])
if os.environ.get("CRA_TAU"): cev.CRA_MATURATION_TAU_DAYS = float(os.environ["CRA_TAU"])
if os.environ.get("HUM_CLAY"): cev.SIXPOOL_ML_HUM_CLAY = tuple(float(x) for x in os.environ["HUM_CLAY"].split(","))
for _o in os.environ.get("ENGINE_OVR","").split(";"):   # 2026-10-15: generic engine-constant overrides for scaled-up runs, NAME=VALUE;NAME=VALUE
    if _o:
        _k,_v=_o.split("=",1)
        if _k.startswith("CROP."): rv.CORN[_k[5:]]=eval(_v)   # crop-dict constant, e.g. CROP.tr_threshold_t=13
        else: setattr(cev,_k,eval(_v))
if os.environ.get("CONFIG")=="shipped":   # 2026-10-16 rebuild phase 1: score what engine-demo.html actually runs (bare simulate_season, no flags, no regional factor, fresh start each season)
    for _k,_v in (("REGIONAL","0"),("LEAD_YEARS","0"),("PER_LAYER","0"),("NITRATE_LAYERS","0"),("CARRY_N","0")): os.environ[_k]=_v
CY=os.environ.get("CY_DIR","/tmp/cycles-run15")  # a local Cycles v1.5.20 release directory (binary + input/), not committed. Reference moved from v1.4.4 to v1.5.20 on 2026-10-12.
SITES=dict(rock_springs=fd.PRESET_SITES["rock_springs"],iowa=fd.PRESET_SITES["iowa"],
           kansas=fd.PRESET_SITES["kansas"],maryland=fd.PRESET_SITES["maryland"],
           # 12 further CONUS sites (added 2026-10-02) so any fit is checked off the original four
           nebraska=(41.0,-98.0),illinois=(40.2,-89.0),ohio=(40.5,-83.5),minnesota=(44.5,-94.5),
           georgia=(32.5,-83.5),texas=(32.0,-97.5),michigan=(43.0,-84.5),carolina=(35.2,-79.0),
           missouri=(38.5,-92.5),indiana=(40.0,-86.5),arkansas=(35.0,-91.5),wisconsin=(44.0,-89.5))
# 12 held-out sites (added 2026-10-12): never used in any fit; HELDOUT=1 swaps them in for the 16 tuning sites
HELDOUT_SITES=dict(south_dakota=(44.0,-97.5),north_dakota=(47.0,-97.5),iowa_west=(41.8,-95.8),colorado=(40.2,-103.5),
                   oklahoma=(36.2,-97.5),kentucky=(37.5,-85.5),tennessee=(35.8,-88.9),mississippi=(33.5,-90.8),
                   louisiana=(31.0,-92.0),alabama=(32.5,-86.5),virginia=(37.5,-77.5),new_york=(42.8,-76.5))
if os.environ.get("HELDOUT")=="1": SITES=HELDOUT_SITES
if os.environ.get("BIGSET"): SITES={k:tuple(v) for k,v in json.load(open(os.environ["BIGSET"])).items()}   # 2026-10-15: scaled-up random site set from bigset.py
CROPSEL=os.environ.get('CROPSEL','corn')   # 'soy' = continuous soybean (SoybeanMG.5, no N), 2026-10-15
N_LEVELS=[int(x) for x in os.environ.get('N_LEVELS','0,150').split(',')]
def lat_of(lat,lon):
    m=fd.load_manifest(); _,_,k=fd.tile_for_point(lat,lon); d,e=fd.load_tile_bytes(m,k)
    best=min(e["cells"],key=lambda c:math.hypot(c[0]-lat,c[1]-lon)); return best[0]
def write_inputs(site,lat,lon,wx,soil_raw,cell_lat):
    w=open(f"{CY}/input/{site}.weather","w")
    w.write(f"LATITUDE                {cell_lat:.6f}\nALTITUDE                0.000000\nSCREENING_HEIGHT        10.0\n")
    w.write("YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND\n####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s\n")
    for y in sorted(wx):
        for d in sorted(wx[y]):
            r=wx[y][d]; w.write(f"{y}\t{d}\t{r['pp']:.4f}\t{r['tx']:.2f}\t{r['tn']:.2f}\t{r['solar']:.4f}\t{r['rhx']:.2f}\t{r['rhn']:.2f}\t{r['wind']:.3f}\n")
    w.close()
    s=open(f"{CY}/input/{site}.soil","w")
    s.write("CURVE_NUMBER        75\nSLOPE               0\n")
    s.write("LAYER   THICK   CLAY    SAND    SOC     BD      FC      PWP     SON     NO3     NH4     ROCK    BYP_H   BYP_V   pH\n#       m       %       %       %       Mg/m3   m3/m3   m3/m3   kg/ha   kg/ha   kg/ha   m3/m3   -       -       -\n")
    for i,l in enumerate(soil_raw,1):
        no3=max(1,round(10*l['thick']/0.05*0.25)) ; s.write(f"{i}\t{l['thick']}\t{l['clay']}\t{l['sand']}\t{l['soc']}\t-999\t-999\t-999\t-999\t{min(no3,10)}\t1\t0.0\t0.0\t0.00\t6.5\n")
    s.close()
    base=open(f"{CY}/input/{'h2h_central_iowa_soy' if CROPSEL=='soy' else 'ContinuousCorn'}.operation").read()
    for N in N_LEVELS:
        op=base.replace('468.75','%.2f'%(N/0.32),1) if N>0 else base
        if N==0:
            a=op.find("FIXED_FERTILIZATION"); op=(op[:a].rstrip()+"\n") if a>=0 else op
        open(f"{CY}/input/{site}N{N}.operation","w").write(op)
        import re as _re
        c=open(f"{CY}/input/ContinuousCorn.ctrl").read().replace("ContinuousCorn.operation",f"{site}N{N}.operation").replace("GenericHagerstown.soil",f"{site}.soil").replace("RockSprings.weather",f"{site}.weather")
        c=_re.sub(r"SOIL_LAYERS\s+\d+",f"SOIL_LAYERS             {len(soil_raw)}",c)
        open(f"{CY}/input/{site}N{N}.ctrl","w").write(c)
def run_cycles(site,N):
    # Cached 2026-10-08: the Cycles reference for a site/N never changes between engine experiments (same tile inputs),
    # so run the binary once and reuse the parsed result. Delete {CY}/cache_*.json to force a re-run.
    cache=f"{CY}/cache15_{site}N{N}.json"
    if os.path.exists(cache) and os.environ.get("NO_CACHE","0")!="1":
        d=json.load(open(cache)); return {int(k):v for k,v in d["H"].items()},{int(k):v for k,v in d["A"].items()}
    H,A=_run_cycles_uncached(site,N)
    json.dump(dict(H=H,A=A),open(cache,"w")); return H,A
def _run_cycles_uncached(site,N):
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True)   # v1.5: no -b (there it means "set a break point")
    out=f"{CY}/output/{site}N{N}"; H={}
    for line in open(f"{out}/harvest.csv").readlines()[2:]:
        p=line.strip().split(",")
        if len(p)<11: continue
        H[int(p[0][:4])]=dict(total=float(p[3]),grain=float(p[5]),plant=p[2],tr=float(p[10]),evap=float("nan"))
    A={}
    for line in open(f"{out}/annualN.csv").readlines()[2:]:
        p=line.strip().split(",")
        if len(p)>=12: A[int(p[0])]=dict(leach=float(p[4])+float(p[5]),denit=float(p[8]),volat=float(p[10]),n2o=float(p[11]))
    return H,A
REG_LON=None
def doy_of(s):
    import datetime; y,m,d=map(int,s.split("-")); return datetime.date(y,m,d).timetuple().tm_yday
def corr(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b); sa=math.sqrt(sum((x-ma)**2 for x in a)); sb=math.sqrt(sum((x-mb)**2 for x in b))
    return sum((a[i]-ma)*(b[i]-mb) for i in range(len(a)))/(sa*sb) if sa and sb else float('nan')
def engine(site,wx,soil_raw,cell_lat,N,mode,lead_years=2):
    if os.environ.get('NETMULT_JSON'):
        import json as _j; cev.SIXPOOL_NET_MULT=_j.load(open(os.environ['NETMULT_JSON'])).get(site,1.0)
    crop=dict(rv.CORN); crop["lat_deg"]=cell_lat
    if CROPSEL=='soy':
        import run_validation_rotation2 as _r2; crop=dict(_r2.SOYBEAN); crop['lat_deg']=cell_lat
    if os.environ.get("REGIONAL","1")=="1" and CROPSEL!='soy':   # 2026-10-15 (default ON since the fresh-site validation, REFIT_PLAN row 38): regionalized net-N multiplier and grain factor from site covariates (regional_params.py)
        import importlib; _rp=importlib.import_module(os.environ.get('REGMOD','regional_params'))
        _m,_g=_rp.regional_params(wx,soil_raw,REG_LON); cev.SIXPOOL_NET_MULT=_m; crop["calibration_factor"]=crop["calibration_factor"]*_g
    if os.environ.get("LWP_WILT"): crop["lwp_wilting_point"]=float(os.environ["LWP_WILT"])
    if os.environ.get("GRAINSITE_JSON"):   # 2026-10-15: per-site grain calibration multiplier (regionalized)
        import json as _j2; crop["calibration_factor"]=crop["calibration_factor"]*_j2.load(open(os.environ["GRAINSITE_JSON"])).get(site,1.0)
    for _k,_e in (("calibration_factor","GRAIN_MULT"),("rue","RUE_MULT"),("wue","WUE_MULT")):
        if os.environ.get(_e): crop[_k]=crop[_k]*float(os.environ[_e])
    def ml():
        L=[]
        for l in soil_raw:
            h=saxton_rawls(l["sand"],l["clay"],l["soc"]*OM_FROM_SOC)
            L.append(dict(thick=l["thick"],fc=h["fc"],pwp=h["pwp"],sat=h["sat"],theta=h["pwp"]+INITIAL_MOISTURE_FRACTION*(h["fc"]-h["pwp"]),ksat_mm_day=h["ksat_mm_day"],psi_e_kpa=h["psi_e_kpa"],B=h["B"]))
        return L
    crop["make_layers"]=ml
    kw=cev.standard_kwargs(soil_raw,N)   # the single standard configuration lives in the engine module
    if CROPSEL=='soy' or os.environ.get('CONFIG')=='shipped': kw=dict(n_rate_kg_ha=N) if CROPSEL!='soy' else {}
    res={}
    carry=os.environ.get("CARRY_N","1")=="1" and CROPSEL!='soy'
    lead_env=os.environ.get("LEAD_YEARS","continuous")
    first_year=min(wx)
    ystep=int(os.environ.get("YEAR_STEP","1"))
    if os.environ.get("FORCE_KEYS"):   # 2026-10-15: teacher-forcing diagnostic on any site set
        import forcelib; cev.FORCE_SERIES=forcelib.force(site,N,os.environ["FORCE_KEYS"].split(","))
    cont=simulate_continuous(wx,crop,carry_n=carry,**kw) if lead_env=="continuous" else None   # one run from the first year, as Cycles does
    for y in sorted(wx):
        if (y-first_year)%ystep: continue   # quick mode: every ystep-th year only
        lead=(y-first_year) if lead_env=="full" else (0 if cont is not None else int(lead_env))   # "full" = start from the first weather year, as Cycles does
        r=cont[y] if cont is not None else simulate_season_with_leadin(wx,y,crop,lead_years=lead,carry_n=carry,**kw)
        if carry and "fallow_n_leached" in r:   # add the off-season windows so totals are calendar-year like Cycles' annualN.txt
            r["n_leached_kg_ha"]=r.get("n_leached_kg_ha",0.0)+r["fallow_n_leached"]
            r["n_denitrified_kg_ha"]=r.get("n_denitrified_kg_ha",0.0)+r["fallow_n_denitrified"]
            r["n2o_emitted_kg_ha"]=r.get("n2o_emitted_kg_ha",0.0)+r.get("fallow_n2o",0.0)
            r["n_volatilized_pool_kg_ha"]=r.get("n_volatilized_pool_kg_ha",0.0)+r["fallow_n_volatilized"]
        res[y]=r
    return res
if __name__=="__main__":
    out={}
    _only=[x for x in os.environ.get("SITES","").split(",") if x]
    for site,(lat,lon) in SITES.items():
        if _only and site not in _only: continue
        wx,wd=fd.resolve_field_weather(lat,lon); soil,sd,name=fd.resolve_field_soil(lat,lon); cl=lat_of(lat,lon)
        REG_LON=lon
        fsite=site+('soy' if CROPSEL=='soy' else '')
        write_inputs(fsite,lat,lon,wx,soil,cl)
        for N in N_LEVELS:
            H,A=run_cycles(fsite,N)
            for mode in ["leadin"]:
                E=engine(site,wx,soil,cl,N,mode)
                ys=sorted(set(H)&set(E))
                row={}
                for var,gr,ge in [("grain",lambda y:H[y]["grain"],lambda y:E[y]["grain"]),("total_biomass",lambda y:H[y]["total"],lambda y:E[y]["total"]),
                                  ("plant_doy",lambda y:doy_of(H[y]["plant"]),lambda y:E[y]["plant_doy"])]:
                    a=[gr(y) for y in ys]; b=[ge(y) for y in ys]
                    row[var]=dict(real=statistics.mean(a),model=statistics.mean(b),mae=statistics.mean(abs(x-z) for x,z in zip(a,b)),corr=corr(a,b),n=len(ys))
                    if var=="grain": row[var]["pairs"]=[[round(x,4),round(z,4)] for x,z in zip(a,b)]   # (Cycles, engine) per year, for global re-centering in eval_big.py
                if True:
                    for k,ek in [("leach","n_leached_kg_ha"),("volat","n_volatilized_pool_kg_ha"),("denit","n_denitrified_kg_ha"),("n2o","n2o_emitted_kg_ha")]:
                        yy=[y for y in ys if y in A]; a=[A[y][k] for y in yy]; b=[E[y].get(ek,0.0) for y in yy]
                        row[k]=dict(real=statistics.mean(a),model=statistics.mean(b),mae=statistics.mean(abs(x-z) for x,z in zip(a,b)),corr=corr(a,b),n=len(yy))
                out[f"{site}|N{N}|{mode}"]=dict(soil=name,soil_dist=sd,wx_dist=wd,res=row)
                print(site,N,mode,name,{k:(round(v['real'],2),round(v['model'],2),round(v['corr'],2)) for k,v in row.items()},flush=True)
    json.dump(out,open(os.environ.get("OUT_JSON") or os.path.join(P,"multisite_results.json"),"w"),indent=1)
