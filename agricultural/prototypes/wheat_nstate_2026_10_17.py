"""Wheat N state by month, engine free run vs Cycles (2026-10-17): mean N stress multiplier (1 = none), plant N (kg/ha) and biomass-weighted view, 16 fresh sites, N=0 and N=150 (FALLN=60)."""
import os,sys,json,csv,datetime,shutil,subprocess,numpy as np
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ.setdefault("FALLN","60"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatF%d"%W.FALLN; m.write_inputs(fs,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; C={}
        for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": continue
            dt=datetime.date.fromisoformat(x["date"]); py=dt.year if dt.month>=8 else dt.year-1
            C[(py,dt.timetuple().tm_yday)]=(1-float(x["nitrogen_stress"])/100,float(x["total_nitrogen"]),dt.month)
        shutil.rmtree(d,ignore_errors=True)
        E.DIAG_STATE=[]; W.engine_chain(wx,soil,cl,N,1.0); D=E.DIAG_STATE; E.DIAG_STATE=None
        out[N]=[(C[(y,doy)][2],C[(y,doy)][0],ns,C[(y,doy)][1],pn) for (y,doy,eie,ns,pn) in D if (y,doy) in C]
    return out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    for N in (0,150):
        A=np.array([r for o in R for r in o[N]])
        print(f"N={N}: month  Cycles stress mult | engine | Cycles plant N | engine")
        for mo in (10,11,12,1,2,3,4,5,6):
            b=A[:,0]==mo
            if b.sum(): print(f"  {mo:2d}  {A[b,1].mean():.2f} | {A[b,2].mean():.2f} | {A[b,3].mean():6.1f} | {A[b,4].mean():6.1f}   (n={b.sum()})")
