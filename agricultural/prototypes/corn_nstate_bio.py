"""Corn N state trajectory (2026-10-17): engine (free, continuous chain, factor 1.0) versus Cycles v1.5.20, same dates, 24 sites, N=0 and 150. Per decile of the season (Cycles thermal time over its season maximum)
reports mean N stress multiplier (1 = none) and total plant N (kg/ha) for both, and the within-decile site-year correlation of the engine and Cycles N stress. Usage: python3 corn_nstate_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ.setdefault("LEAD_YEARS","continuous"); os.environ.setdefault("YEAR_STEP","2"); sys.path.insert(0,'.')
import run_validation_multisite as m, rhizo_engine as E, forcelib
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); rows=[]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
        C={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": continue
            dt=datetime.date.fromisoformat(x["date"]); C[(dt.year,dt.timetuple().tm_yday)]=(float(x["thermal_time"]),1-float(x["nitrogen_stress"])/100,float(x["total_nitrogen"]),float(x["biomass"]),float(x["radiation_interception"]))
        FS=forcelib.force(site,N,('wclock','canopy','water','nstress')) if os.environ.get('FORCE') else None
        shutil.rmtree(d,ignore_errors=True)
        E.FORCE_SERIES=({y:{k:v[k] for k in ('canopy','water','nstress','wclock','nclock')} for y,v in FS.items()} if FS else None)
        E.DIAG_STATE=[]; E.DIAG_BIO=[]; m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_STATE; B=E.DIAG_BIO; E.DIAG_STATE=None; E.DIAG_BIO=None; E.FORCE_SERIES=None
        tmax={}
        for (y,doy),v in C.items(): tmax[y]=max(tmax.get(y,0),v[0])
        for (y,doy,eie,ns,pn),eb in zip(D,B):
            c=C.get((y,doy))
            if c and tmax[y]>0: rows.append((N,y,min(9,int(10*c[0]/tmax[y])),c[1],ns,c[2],pn,c[3],eb,c[4],eie))
    return rows
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    A=[r for rr in R for r in rr]; json.dump(A,open("/tmp/w/corn_nstate.json","w"))
    for N in (0,150):
        print(f"N={N}: decile  Cycles Nstress  engine Nstress | Cycles plantN  engine plantN | corr(N stress)")
        for b in range(10):
            s=[r for r in A if r[0]==N and r[2]==b]
            if len(s)<50: continue
            cs=[r[3] for r in s]; es=[r[4] for r in s]; cp=[r[5] for r in s]; ep=[r[6] for r in s]
            ma,mb=st.mean(cs),st.mean(es); den=(sum((x-ma)**2 for x in cs)*sum((y-mb)**2 for y in es))**.5
            cr=sum((x-ma)*(y-mb) for x,y in zip(cs,es))/den if den else float('nan')
            cb=st.mean(r[7] for r in s); eb=st.mean(r[8] for r in s); cc=st.mean(r[9] for r in s); ec=st.mean(r[10] for r in s)
            print(f"      biomass Cycles {cb:5.2f} engine {eb:5.2f} | canopy Cycles {cc:.2f} engine {ec:.2f}")
            print(f"   {b}   {ma:6.3f}  {mb:6.3f} | {st.mean(cp):6.1f}  {st.mean(ep):6.1f} | {cr:5.2f}  (n={len(s)})")
