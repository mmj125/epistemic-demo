"""Corn N=0 over-yield attribution (2026-10-17): 24 fresh sites, factor 1.0, no regional map. Force Cycles' daily states (separately and together) into the engine and report yearly grain MAE, bias
and within-site correlation versus Cycles v1.5.20, to see which state owns the N=0 gap (engine over-yields by about 0.8 Mg/ha). Modes: free, netmin, minn (mineral N pool), nstress, canopy, nstress+canopy,
all (canopy, water, nstress, wclock, nclock, netmin, minn). Usage: python3 corn_n0_attrib_2026_10_17.py"""
import os,sys,json,shutil,statistics as st
os.environ["N_LEVELS"]=os.environ.get("NS","0,150"); os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from mask_attrib_2026_10_16 import harv
from multiprocessing import Pool
import subprocess
CY=m.CY
MODES={"free":(),"netmin":("netmin",),"minn":("minn",),"nstress":("nstress","nclock"),"canopy":("canopy",),"nstress+canopy":("nstress","nclock","canopy"),"canopy+water":("canopy","water","wclock"),"water":("water","wclock"),"nclockonly":("nclock",),"nstressonly":("nstress",),"clocks":("wclock","nclock","nstress","water"),"all":("canopy","water","wclock","nstress","nclock","netmin","minn")}
if os.environ.get("MODES"): MODES={k:v for k,v in MODES.items() if k in os.environ["MODES"].split(",")}
def corr(a,b):
    if len(a)<3: return float("nan")
    ma,mb=st.mean(a),st.mean(b); sa=sum((x-ma)**2 for x in a)**.5; sb=sum((x-mb)**2 for x in b)**.5
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/(sa*sb) if sa*sb else float("nan")
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in [int(x) for x in os.environ.get('NS','0,150').split(',')]:
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
        H=harv(d); F=forcelib.force(site,N,("wclock","canopy","water","nstress","netmin","minn")); shutil.rmtree(d,ignore_errors=True)
        for name,ks in MODES.items():
            E.FORCE_SERIES=None if not ks else {y:{k:v[k] for k in ks if k in v} for y,v in F.items()}
            R=m.engine(site,wx,soil,cl,N,"leadin"); E.FORCE_SERIES=None
            ys=sorted(set(H)&set(R)); x=[H[y]["grain"] for y in ys]; z=[R[y]["grain"] for y in ys]
            out[f"N{N}|{name}"]=dict(mae=st.mean(abs(i-j) for i,j in zip(x,z)),bias=st.mean(j-i for i,j in zip(x,z)),corr=corr(x,z),cg=st.mean(x))
    return site,out
if __name__=="__main__":
    S=json.load(open(os.environ.get("SFILE","/tmp/w/s24.json")))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    json.dump(R,open(os.environ.get("AOUT","scorecards/2026-10-17_corn_n0_attrib_24sites.json"),"w"))
    for N in [int(x) for x in os.environ.get('NS','0,150').split(',')]:
        f=st.mean(o[f"N{N}|free"]["mae"] for _,o in R)
        for k in MODES:
            g=lambda q:st.mean(o[f"N{N}|{k}"][q] for _,o in R); c=st.mean(o[f"N{N}|{k}"]["corr"] for _,o in R if o[f"N{N}|{k}"]["corr"]==o[f"N{N}|{k}"]["corr"])
            print(f"N={N} {k:15s} MAE {g('mae'):.3f} ({100*(1-g('mae')/f):+5.1f}% vs free) bias {g('bias'):+.3f} corr {c:.2f}")
