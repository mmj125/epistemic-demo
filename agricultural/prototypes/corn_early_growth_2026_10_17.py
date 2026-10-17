"""Early-season growth overshoot (2026-10-17): with Cycles' canopy, water, N stress and clocks forced, compare the engine's daily gross growth (dGB, g/m2/day) with Cycles' daily total biomass gain on matched days, binned by thermal-time fraction, binding limit (radiation GR vs transpiration GT in the engine), air temperature and solar radiation. Corn, 24 sites, N=150. Usage: ENGINE_OVR=... python3 corn_early_growth_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); os.environ.setdefault("LEAD_YEARS","continuous"); os.environ.setdefault("YEAR_STEP","2"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
CY=m.CY; ALL=("canopy","water","wclock","nstress","nclock","netmin","minn")
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); N=150
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; C={}; prev=None
    for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
        if x['date'][0]=='#' or x['biomass']=='-999': prev=None; continue
        dt=datetime.date.fromisoformat(x['date']); k=(dt.year,dt.timetuple().tm_yday); b=float(x['biomass'])
        if prev is not None: C[k]=((b-prev)*100.0,float(x['thermal_time'])/1800.0,float(x['temperature_factor']),float(x['radiation_interception']))
        prev=b
    F=forcelib.force(site,N,("wclock","canopy","water","nstress","netmin","minn")); shutil.rmtree(d,ignore_errors=True)
    E.FORCE_SERIES={y:{k:v[k] for k in ALL if k in v} for y,v in F.items()}
    E.DIAG_STATE=[]; E.DIAG_GROWTH=[]; m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_STATE; G=E.DIAG_GROWTH; E.DIAG_STATE=E.DIAG_GROWTH=None; E.FORCE_SERIES=None
    out=[]
    for (y,doy,eie,ns,pn),(gd,GR,GT,dGB) in zip(D,G):
        if gd!=doy: continue
        c=C.get((y,doy))
        if c and c[0]>0: out.append((c[1],c[0],dGB*1000.0*(ns**E.N_STRESS_GROWTH_POW),GR,GT,wx[y][doy]['solar'],(wx[y][doy]['tx']+wx[y][doy]['tn'])/2,c[3],E.clearness_diffuse_fraction(doy,lat,wx[y][doy]['solar'])))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    import numpy as np
    A=np.array(R); print("days",len(A))
    print("ratio engine gross growth / Cycles total gain, two-way: rows thermal-time fraction, columns Erbs diffuse fraction")
    fdb=[(0,.25),(.25,.4),(.4,.55),(.55,.75),(.75,1.01)]
    print("            "+"  ".join(f"fd {lo:.2f}-{hi:.2f}" for lo,hi in fdb))
    for lo in np.arange(0.1,1.0,0.2):
        row=[]
        for fl,fh in fdb:
            k=(A[:,0]>=lo)&(A[:,0]<lo+.2)&(A[:,8]>=fl)&(A[:,8]<fh)
            row.append(f"{A[k,2].sum()/A[k,1].sum():9.3f}" if k.sum()>300 else "      n/a")
        print(f" ttf {lo:.1f}-{lo+.2:.1f}: "+"  ".join(row))
    print("one-way by fd:"," ".join(f"{fl:.2f}-{fh:.2f}:{A[(A[:,8]>=fl)&(A[:,8]<fh),2].sum()/A[(A[:,8]>=fl)&(A[:,8]<fh),1].sum():.3f}" for fl,fh in fdb))
