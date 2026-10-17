"""Wheat clock/stress/canopy decomposition (2026-10-17): force Cycles' daily nclock, wclock, nstress, canopy separately and in groups into the current wheat engine. 16 fresh sites, N=0 and 150,
within-site yearly MAE (grain, factor 1.0, documented HI), share removed vs free, and within-site correlation."""
import os,sys,json,csv,datetime,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY; KEYS={'K':'nclock','L':'wclock','N':'nstress','C':'canopy'}; MODES=['','K','L','KL','N','KLN','C','CN']
def series(fs,N):
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; F={}
    for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
        if x["date"][0]=="#" or x["biomass"]=="-999": continue
        dt=datetime.date.fromisoformat(x["date"]); py=dt.year if dt.month>=8 else dt.year-1; doy=dt.timetuple().tm_yday
        f=F.setdefault(py,{"canopy":{},"wclock":{},"nclock":{},"nstress":{}})
        f["canopy"][doy]=float(x["radiation_interception"]); f["wclock"][doy]=1-float(x["water_stress"])/100; f["nclock"][doy]=1-float(x["nitrogen_stress"])/100; f["nstress"][doy]=f["nclock"][doy]
    shutil.rmtree(d,ignore_errors=True); return F
def sub(F,mode):
    ks=[KEYS[c] for c in mode]; return {y:{k:(v if k in ks else {}) for k,v in d.items()} for y,d in F.items()}
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"+("F%d"%W.FALLN if W.FALLN else ""); m.write_inputs(fs,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        H=W.cycles_ref(fs,N); F=series(fs,N)
        for mode in MODES:
            E.FORCE_SERIES=sub(F,mode) if mode else None
            R=W.engine_chain(wx,soil,cl,N,1.0); E.FORCE_SERIES=None
            ys=[y for y in sorted(set(H)&set(R)) if y>1981]; x=[H[y]["grain"] for y in ys]; z=[R[y]["grain"] for y in ys]
            out[f"N{N}|{mode or 'free'}"]=dict(mae=st.mean(abs(i-j) for i,j in zip(x,z)),mean=st.mean(x),corr=W.corr(x,z),bias=st.mean(j-i for i,j in zip(x,z)))
    return site,out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[int(os.environ.get("OFF","0"))::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    json.dump(R,open("scorecards/2026-10-17_wheat_coupling_16sites.json","w"))
    for N in (0,150):
        base=st.mean(o[f"N{N}|free"]["mae"] for _,o in R); ref=st.mean(o[f"N{N}|free"]["mean"] for _,o in R)
        for mode in MODES:
            k=f"N{N}|{mode or 'free'}"; mae=st.mean(o[k]["mae"] for _,o in R); c=st.mean(o[k]["corr"] for _,o in R if o[k]["corr"]==o[k]["corr"])
            print(f"N={N} {mode or 'free':5s} MAE {mae:5.2f} ({100*mae/ref:3.0f}% of mean) removed {100*(base-mae)/base:+4.0f}%  bias {st.mean(o[k]['bias'] for _,o in R):+.2f}  corr {c:.2f}")
