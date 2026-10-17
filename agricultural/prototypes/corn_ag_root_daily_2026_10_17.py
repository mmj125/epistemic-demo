"""Daily aboveground and root biomass, engine vs Cycles v1.5.20, by decile of the season, Cycles' canopy, water, N stress and clocks forced (so growth demand is identical), corn 24 sites, N=150 and 0. Shows whether the early-season total biomass overshoot is aboveground or root. Usage: ENGINE_OVR=... python3 corn_ag_root_daily_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ.setdefault("LEAD_YEARS","continuous"); os.environ.setdefault("YEAR_STEP","2"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
CY=m.CY; ALL=("canopy","water","wclock","nstress","nclock","netmin","minn")
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; C={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999':continue
            dt=datetime.date.fromisoformat(x['date']); C.setdefault(dt.year,{})[dt.timetuple().tm_yday]=(float(x['thermal_time']),float(x['aboveground_biomass']),float(x['root_biomass']))
        F=forcelib.force(site,N,("wclock","canopy","water","nstress","netmin","minn")); shutil.rmtree(d,ignore_errors=True)
        SH=int(os.environ.get("SHIFT","0"))
        if SH:
            for y,v in F.items():
                v["canopy"]={doy:v["canopy"].get(doy-SH,0.0) for doy in v["canopy"]}
        E.FORCE_SERIES={y:{k:v[k] for k in ALL if k in v} for y,v in F.items()}
        E.DIAG_STATE=[]; E.DIAG_BIO=[]; E.DIAG_AG=[]; m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_STATE; B=E.DIAG_BIO; A=E.DIAG_AG; E.DIAG_STATE=E.DIAG_BIO=E.DIAG_AG=None; E.FORCE_SERIES=None
        for (y,doy,eie,ns,pn),tb,ag in zip(D,B,A):
            c=C.get(y,{}).get(doy)
            if c and c[0]>0: out.append((N,min(9,int(c[0]/1800*10)),c[1],c[2],ag,tb-ag))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    for N in (0,150):
        print(f"N={N}: decile  Cycles AG/root   engine AG/root   ratio AG  ratio root")
        for dc in range(10):
            q=[r for r in R if r[0]==N and r[1]==dc]
            if len(q)>50:
                ca,cr,ea,er=[st.mean(r[i] for r in q) for i in (2,3,4,5)]
                print(f"   {dc}   {ca:6.2f} {cr:5.2f}    {ea:6.2f} {er:5.2f}    {ea/ca:5.2f}   {er/cr if cr>0.02 else float('nan'):5.2f}")
