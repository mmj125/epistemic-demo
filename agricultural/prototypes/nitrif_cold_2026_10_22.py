"""Nitrification law against Cycles' own daily states by month, corn (24 sites) and wheat (8 sites), N=0 and 150 (2026-10-22)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["REGIONAL"]="0"; os.environ["N_LEVELS"]="0,150"; os.environ["FALLN"]="60"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m, run_validation_multisite_wheat as w, cycles_engine_validate as E
from multiprocessing import Pool
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
S=json.load(open('sitesets/fresh94.json'))
def one(a):
    crop,site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"nc"+crop; m.write_inputs(nm,lat,lon,wx,soil,cl)
    if crop=="wheat": open(f"{w.CY}/input/{nm}N{N}.operation","w").write(w.OP+w.fert_text(N))
    subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N{N}/"
    if not os.path.exists(d+"dailyN.csv"): return crop,N,None
    DN=rd(d+"dailyN.csv"); L=rd(d+"dailySoilLayersCN.csv"); En=rd(d+"dailyEnviron.csv"); W=rd(d+"dailyWater.csv"); shutil.rmtree(d,ignore_errors=True)
    h=m.saxton_rawls(soil[0]["sand"],soil[0]["clay"],soil[0]["soc"]*m.OM_FROM_SOC); sat=h["sat"]
    rows=[]; prev=None
    for a_,b,e,wt in zip(DN,L,En,W):
        dt=datetime.date.fromisoformat(a_['date'])
        nh4=float(b['NH4.1'])*float(b['bulk_density.1'])*float(b['thickness.1'])*10; no3s=float(b['NO3.1'])*float(b['bulk_density.1'])*float(b['thickness.1'])*10
        if prev is not None and dt.year>=1984:
            law=E.nitrification_flux_ratio(prev[0],prev[1],float(e['soil_temperature.1']),float(wt['soil_moisture_content.1'])/sat)
            rows.append([dt.month,float(a_['nitrification']),law,float(e['soil_temperature.1'])])
        prev=(nh4,no3s)
    return crop,N,np.array(rows)
if __name__=="__main__":
    ks=sorted(S); cs=[k for k in sorted(json.load(open('/tmp/w/s24.json')))]
    ws=["f070_340_915","f082_350_765","f010_350_835","f018_380_800","f039_455_990","f006_485_975","f030_410_970","f012_380_990"]
    jobs=[("corn",s,N) for s in cs for N in (0,150)]+[("wheat",s,N) for s in ws for N in (0,150)]
    R=Pool(4).map(one,jobs)
    for crop in ("corn","wheat"):
        for N in (0,150):
            A=np.vstack([r[2] for r in R if r[0]==crop and r[1]==N and r[2] is not None])
            print(f"{crop} N={N}: law/Cycles by month (sum over days; law on Cycles' own states) and mean soil T")
            print("   "+"  ".join(f"{mo:2d}:{A[A[:,0]==mo,2].sum()/max(A[A[:,0]==mo,1].sum(),1e-9):.2f}" for mo in range(1,13)),"| year %.2f"%(A[:,2].sum()/A[:,1].sum()))
