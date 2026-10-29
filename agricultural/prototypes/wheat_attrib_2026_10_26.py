"""Winter wheat attribution with Cycles' own daily states forced into the engine (2026-10-26): 24 fresh94 sites outside the 24-site tuning set, N=90 with FALLN=60. Cycles dailyWinterWheat.csv radiation_interception (canopy, C), 1 - water_stress (water factor, W)
and 1 - nitrogen_stress (N factor, N, plus the N clock for the canopy) are forced alone and together; reports engine / Cycles grain and above-ground total biomass, and the share of the free-run grain MAE removed. Usage: FALLN=60 python3 wheat_attrib_2026_10_26.py"""
import os,sys,json,csv,shutil,subprocess,datetime,statistics as st
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
F_=json.load(open('sitesets/fresh94.json')); S24_=json.load(open('/tmp/w/s24.json')); S={k:F_[k] for k in sorted(F_) if k not in S24_}; S={k:S[k] for k in sorted(S)[::3][:24]}; CY=m.CY
MODES=["","C","W","N","CWN"]
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def series(CR,keys):
    F={}
    for x in CR:
        if x["biomass"]=="-999": continue
        d=datetime.date.fromisoformat(x["date"]); y=d.year if d.month>=10 else d.year-1; doy=d.timetuple().tm_yday
        f=F.setdefault(y,{"canopy":{},"water":{},"nstress":{},"wclock":{},"nclock":{}})
        if "C" in keys: f["canopy"][doy]=float(x["radiation_interception"])
        if "W" in keys: f["water"][doy]=1-float(x["water_stress"])/100; f["wclock"][doy]=1-float(x["water_stress"])/100
        if "N" in keys: f["nstress"][doy]=1-float(x["nitrogen_stress"])/100; f["nclock"][doy]=1-float(x["nitrogen_stress"])/100
    return F
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatattr"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=90
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
    H=W.cycles_ref(fs,N)
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; CR=rd(d+"dailyWinterWheat.csv"); shutil.rmtree(d,ignore_errors=True)
    out={}
    for mode in MODES:
        E.FORCE_SERIES=series(CR,mode) if mode else None
        R=W.engine_chain(wx,soil,cl,N,None); ys=[y for y in sorted(set(H)&set(R)) if y>1981]
        out[mode]=[[H[y]["grain"],R[y]["grain"],H[y]["total"],R[y]["total"]] for y in ys]
    return out
if __name__=="__main__":
    R=Pool(4).map(one,sorted(S))
    base=np.array([np.abs(np.array(r[""])[:,1]-np.array(r[""])[:,0]).mean() for r in R])
    for mode in MODES:
        A=np.vstack([np.array(r[mode]) for r in R]); mae=np.array([np.abs(np.array(r[mode])[:,1]-np.array(r[mode])[:,0]).mean() for r in R])
        print(f"{mode or 'free':5s} grain engine/Cycles {A[:,1].mean()/A[:,0].mean():.3f}  total biomass {A[:,3].mean()/A[:,2].mean():.3f}  grain MAE {mae.mean():.3f} ({100*(1-mae.mean()/base.mean()):+.0f}% vs free)  corr {np.corrcoef(A[:,0],A[:,1])[0,1]:.3f}")
