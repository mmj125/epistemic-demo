"""Canopy trajectory, engine against Cycles by TTf (2026-10-31), corn, 24-site set, N=150, continuous chain. Cycles: daily radiation_interception against thermal_time / 1800.
Engine: history 'canopy' against 'ttf'. All days, and days where Cycles' water and N stress are both under 2 percent (the shape of the law without stress feedback).
CANOPY_SHAPE env 'a,b,c,d' overrides E.CANOPY_SHAPE_FORCE (the printed Eq. 6 constants are 6,-20,-15,16; the engine uses 6,-20,-16,16).
Usage: CANOPY_SHAPE=6,-20,-15,16 TAG=c15 python3 canopy_traj_2026_10_31.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; os.environ["CROPSEL"]="corn"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
if os.environ.get("CANOPY_SHAPE"): E.CANOPY_SHAPE_FORCE=tuple(float(x) for x in os.environ["CANOPY_SHAPE"].split(","))
from multiprocessing import Pool
_orig=m.cev.standard_kwargs
m.cev.standard_kwargs=lambda *a,**k: {**_orig(*a,**k),'record_history':True}
S=json.load(open('/tmp/w/s24.json')); N=150
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    D=[r for r in csv.DictReader(open(d+"dailyCornRM.90.csv")) if r['date'][0]!='#']; shutil.rmtree(d,ignore_errors=True)
    C=[]
    for x in D:
        if x['biomass']=='-999': continue
        C.append((float(x['thermal_time'])/1800.0,float(x['radiation_interception']),float(x['water_stress']),float(x['nitrogen_stress'])))
    res=m.engine(site,wx,soil,cl,N,"leadin"); Eg=[]
    for y,r in res.items():
        for h in (r.get("history") or []):
            if h.get("ttf") is not None and h.get("canopy") is not None: Eg.append((h["ttf"],h["canopy"]))
    return C,Eg
if __name__=="__main__":
    with Pool(4) as p: R=p.map(one,sorted(S))
    C=np.array([c for a,_ in R for c in a]); Eg=np.array([e for _,b in R for e in b])
    un=(C[:,2]<2)&(C[:,3]<2)
    bins=[(0,.1),(.1,.2),(.2,.3),(.3,.4),(.4,.5),(.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.01)]
    print(f"{os.environ.get('TAG','base')}: sites {len(R)}; TTf bin | Cycles all | Cycles unstressed | engine all | engine/Cycles (all) | n Cycles days")
    for lo,hi in bins:
        mc=(C[:,0]>=lo)&(C[:,0]<hi); me=(Eg[:,0]>=lo)&(Eg[:,0]<hi); mu=mc&un
        a=C[mc,1].mean() if mc.any() else float('nan'); u=C[mu,1].mean() if mu.any() else float('nan'); e=Eg[me,1].mean() if me.any() else float('nan')
        print(f"  {lo:.1f}-{hi:.1f} | {a:.3f} | {u:.3f} | {e:.3f} | {e/a:.3f} | {mc.sum()}")
    # integrated canopy over TTf 0..1 (season light interception proxy)
    ic=np.mean([C[mm,1].mean() for mm in [((C[:,0]>=lo)&(C[:,0]<hi)) for lo,hi in bins]]); ie=np.mean([Eg[mm,1].mean() for mm in [((Eg[:,0]>=lo)&(Eg[:,0]<hi)) for lo,hi in bins]])
    print(f"  mean over bins: Cycles {ic:.3f} engine {ie:.3f} ratio {ie/ic:.3f}")
