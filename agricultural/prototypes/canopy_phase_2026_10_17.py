"""Canopy law given Cycles' own clocks (2026-10-17): force nclock, wclock and nstress, leave the canopy to the engine, and compare engine and Cycles daily interception by thermal-time phase.
Corn, 12 fresh sites, N=0 and 150. Bins on Cycles' thermal time fraction (thermal_time / maturity). Prints mean Cycles, mean engine, mean difference and rms per bin."""
import os,sys,json,csv,shutil,datetime,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
CY=m.CY; TTM=float(os.environ.get("TTM","1800"))
KEYS=('nclock','wclock','nstress')
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        m._run_cycles_uncached(site,N); d=f"{CY}/output/{site}N{N}/"
        C={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": continue
            dt=datetime.date.fromisoformat(x["date"]); C[(dt.year,dt.timetuple().tm_yday)]=(float(x["thermal_time"]),float(x["radiation_interception"]),x["stage"])
        F=forcelib.force(site,N,('wclock','canopy','water','nstress')); shutil.rmtree(d,ignore_errors=True)
        F={y:{k:(v if k in KEYS else {}) for k,v in dd.items()} for y,dd in F.items()}
        E.FORCE_SERIES=F; E.DIAG_STATE=[]
        m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_STATE; E.DIAG_STATE=None; E.FORCE_SERIES=None
        rows=[]
        for (y,doy,eie,ns,pn) in D:
            if (y,doy) in C: tt,cc,stg=C[(y,doy)]; rows.append((tt/TTM,cc,eie,stg))
        out[N]=rows
    return site,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json")); items=list(S.items())[::2]
    with Pool(4) as p: R=p.map(one,items)
    for N in (0,150):
        rows=[r for _,o in R for r in o[N]]
        print(f"N={N} ({len(rows)} days)  ttf bin: Cycles canopy, engine canopy, mean diff (engine-Cycles), rms")
        for lo in [i/10 for i in range(0,13)]:
            b=[r for r in rows if lo<=r[0]<lo+0.1]
            if len(b)<30: continue
            print(f"  {lo:.1f}-{lo+0.1:.1f} n={len(b):5d}  {st.mean(r[1] for r in b):.3f}  {st.mean(r[2] for r in b):.3f}  {st.mean(r[2]-r[1] for r in b):+.3f}  {st.mean((r[2]-r[1])**2 for r in b)**.5:.3f}")
