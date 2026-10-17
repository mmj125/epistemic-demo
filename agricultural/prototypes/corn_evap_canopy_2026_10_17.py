"""Soil evaporation as a fraction of ETo*(1-residue cover), by canopy bin, Cycles v1.5.20 vs the engine (Cycles' canopy forced), corn in-season days, 24 sites, N=150. Shows whether Cycles' soil evaporation falls with canopy cover the way the engine's does."""
import os,sys,json,shutil,csv,datetime,subprocess,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
CY=m.CY
def rd(d,f):
    return csv.DictReader(open(d+f))
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); N=150
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; K={}
    def key(x):
        dt=datetime.date.fromisoformat(x['date']); return (dt.year,dt.timetuple().tm_yday)
    for x in rd(d,"dailyCornRM.90.csv"):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        K[key(x)]=dict(can=float(x['radiation_interception']),tt=float(x['thermal_time']))
    for x in rd(d,"dailyWater.csv"):
        if x['date'][0]!='#' and key(x) in K: K[key(x)]['se']=float(x['soil_evaporation']); K[key(x)]['pp']=float(x['infiltration'])
    for x in rd(d,"dailyEnviron.csv"):
        if x['date'][0]!='#' and key(x) in K: K[key(x)]['eto']=float(x['reference_evapotranspiration'])
    for x in rd(d,"dailyResidue.csv"):
        if x['date'][0]!='#' and key(x) in K: K[key(x)]['rc']=float(x['radiation_interception'])
    F=forcelib.force(site,N,("canopy",)); shutil.rmtree(d,ignore_errors=True)
    E.FORCE_SERIES={y:{"canopy":v["canopy"]} for y,v in F.items()}
    E.DIAG_EVAP=[]; m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_EVAP; E.DIAG_EVAP=None; E.FORCE_SERIES=None
    out=[]
    for y,doy,ev,rev,eto,rc in S:
        c=K.get((y,doy))
        if c and 'se' in c and 'eto' in c and 'rc' in c: out.append((c['can'],c['se'],c['eto'],c['rc'],ev,eto,rc))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    for lo in (0,.1,.2,.3,.4,.5,.6,.7,.8,.9):
        q=[r for r in R if lo<=r[0]<lo+.1]
        if len(q)>50:
            c=sum(r[1] for r in q)/sum(r[2]*(1-r[3]) for r in q); e=sum(r[4] for r in q)/sum(r[5]*(1-r[6]) for r in q)
            print(f"canopy {lo:.1f}-{lo+.1:.1f}: n {len(q)}  soil evap / (ETo (1-res cover)): Cycles {c:.3f} engine {e:.3f}  | (1-canopy) {1-lo-.05:.2f}")
