"""Rebuild phase 6 attribution: which Cycles state, forced into the engine, removes the WITHIN-site year-to-year wheat error? 16 fresh sites, N=0 and 150.
Forces (separately and together) Cycles' daily N stress, canopy interception, water stress over each wheat season (planting year y keys Oct-Dec of y plus Jan-Jun of y+1)."""
import os,sys,json,csv,datetime,shutil,subprocess,statistics as st,math
os.environ["N_LEVELS"]="0,90,150"; os.environ.setdefault("REGIONAL","0")
sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
CY=m.CY
def series(fs,N):
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    F={}
    for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
        if x["date"][0]=="#" or x["biomass"]=="-999": continue
        dt=datetime.date.fromisoformat(x["date"]); py=dt.year if dt.month>=8 else dt.year-1; doy=dt.timetuple().tm_yday
        f=F.setdefault(py,{"canopy":{},"water":{},"nstress":{}})
        f["canopy"][doy]=float(x["radiation_interception"]); f["water"][doy]=1-float(x["water_stress"])/100; f["nstress"][doy]=1-float(x["nitrogen_stress"])/100
    shutil.rmtree(d,ignore_errors=True); return F
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"; out={}; m.write_inputs(fs,lat,lon,wx,soil,cl)
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+(W.FERT%(N/0.32) if N>0 else ""))
        H=W.cycles_ref(fs,N); P=series(fs,N)
        for mode in ("free","nstress","canopy","water","all"):
            keys=("canopy","water","nstress") if mode=="all" else (mode,)
            E.FORCE_SERIES=None if mode=="free" else {y:{k:v[k] for k in keys} for y,v in P.items()}
            R=W.engine_chain(wx,soil,cl,N,1.0); E.FORCE_SERIES=None
            ys=[y for y in sorted(set(H)&set(R)) if y>1981]
            x=[H[y]["grain"] for y in ys]; z=[R[y]["grain"] for y in ys]
            out[f"N{N}|{mode}"]=dict(mae=st.mean(abs(i-j) for i,j in zip(x,z)),mean=st.mean(x),corr=W.corr(x,z))
    return site,out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    json.dump(R,open("/tmp/w/wheat_attrib.json","w"))
    for N in (0,150):
        base=st.mean(o[f"N{N}|free"]["mae"] for _,o in R); ref=st.mean(o[f"N{N}|free"]["mean"] for _,o in R)
        for mode in ("free","nstress","canopy","water","all"):
            mae=st.mean(o[f"N{N}|{mode}"]["mae"] for _,o in R); c=st.mean(o[f"N{N}|{mode}"]["corr"] for _,o in R if o[f"N{N}|{mode}"]["corr"]==o[f"N{N}|{mode}"]["corr"])
            print(f"N={N} {mode:8s} yearly MAE {mae:5.2f} ({100*mae/ref:3.0f}% of mean)  removed {100*(base-mae)/base:+4.0f}%  within-site corr {c:.2f}")
