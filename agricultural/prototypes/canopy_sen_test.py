"""Senescence clock test (2026-10-17), clocks and N stress forced from Cycles, canopy left to the engine. Variants of the second (senescence) argument of canopy_cover_two:
base: development clock; B: the stressed expansion clock; C_k: development clock plus k times the accumulated expansion lag. Reports daily canopy error by phase, corn, 12 fresh sites."""
import os,sys,json,csv,shutil,datetime,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, rhizo_engine as E, forcelib
from multiprocessing import Pool
CY=m.CY; TTM=1800.0; KEYS=('nclock','wclock','nstress')
_orig=E.canopy_cover_two
VARS={"base":None,"B":("B",0),"C0.5":("C",0.5),"C1":("C",1.0),"C2":("C",2.0),"C4":("C",4.0)}
def patch(v):
    if v is None: E.canopy_cover_two=_orig; return
    kind,k=v
    if kind=="B": E.canopy_cover_two=lambda xc,xt,eix=1.0,shape=E.DEFAULT_CANOPY_SHAPE:_orig(xc,xc,eix,shape)
    else: E.canopy_cover_two=lambda xc,xt,eix=1.0,shape=E.DEFAULT_CANOPY_SHAPE:_orig(xc,xt+k*max(0.0,xt-xc),eix,shape)
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        m._run_cycles_uncached(site,N); d=f"{CY}/output/{site}N{N}/"; C={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": continue
            dt=datetime.date.fromisoformat(x["date"]); C[(dt.year,dt.timetuple().tm_yday)]=(float(x["thermal_time"]),float(x["radiation_interception"]))
        F=forcelib.force(site,N,('wclock','canopy','water','nstress')); shutil.rmtree(d,ignore_errors=True)
        F={y:{k:(v if k in KEYS else {}) for k,v in dd.items()} for y,dd in F.items()}
        for vn,v in VARS.items():
            patch(v); E.FORCE_SERIES=F; E.DIAG_STATE=[]
            m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_STATE; E.DIAG_STATE=None; E.FORCE_SERIES=None; patch(None)
            out[f"{N}|{vn}"]=[(C[(y,doy)][0]/TTM,C[(y,doy)][1],eie) for (y,doy,eie,ns,pn) in D if (y,doy) in C]
    return site,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json")); items=list(S.items())[::2]
    with Pool(4) as p: R=p.map(one,items)
    for N in (0,150):
        for vn in VARS:
            rows=[r for _,o in R for r in o[f"{N}|{vn}"]]
            tot=st.mean((r[2]-r[1])**2 for r in rows)**.5
            late=[r for r in rows if r[0]>=0.7]; l=st.mean((r[2]-r[1])**2 for r in late)**.5; ls=st.mean(r[2]-r[1] for r in late)
            mid=[r for r in rows if 0.25<=r[0]<0.7]; mm=st.mean((r[2]-r[1])**2 for r in mid)**.5
            print(f"N={N} {vn:5s} rms all {tot:.3f}  mid {mm:.3f}  late(>=0.7) rms {l:.3f} bias {ls:+.3f}")
