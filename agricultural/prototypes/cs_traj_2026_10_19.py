"""Soil organic C trajectories, engine vs Cycles (2026-10-19): corn N=0, 24 sites, continuous chain, from the first simulated day. Per year: mean Cs (all layers and layer 1+2) in each model relative to its own first value, and the engine/Cycles ratio."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=os.environ.get("NLEV","0"); sys.path.insert(0,'.')
NLEV=int(os.environ.get("NLEV","0"))
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NLEV}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NLEV}/"
    L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; shutil.rmtree(d,ignore_errors=True)
    nl=len([k for k in next(iter(L.values())) if k.startswith('microbial_carbon.')])
    E.DIAG_CPOOL=[]; m.engine(site,wx,soil,cl,NLEV,'leadin'); D=E.DIAG_CPOOL; E.DIAG_CPOOL=None; last={}
    for y,doy,cs,cm,cr,cra in D:
        if y is not None and doy is not None: last[(y,doy)]=cs
    cyc={}; 
    for dt,l in L.items():
        d_=datetime.date.fromisoformat(dt); cyc[(d_.year,d_.timetuple().tm_yday)]=[float(l[f'soil_organic_carbon.{i+1}']) for i in range(nl)]
    rows=[]
    for k,cs in last.items():
        if k in cyc and k[1]==200 and nl>=2 and len(cs)>=2: rows.append((k[0],cs[0],cyc[k][0],cs[1],cyc[k][1],sum(cs[:nl]),sum(cyc[k])))
    first=min(cyc)
    return site,rows,sum(cyc[first]),first
if __name__=="__main__":
    R=Pool(4).map(one,sorted(S)); yrs=sorted(set(r[0] for s_,rows,_,_ in R for r in rows))
    print('year | layer 1: engine/Cycles, Cycles vs own first, engine vs own first | layer 2: same')
    b=None
    for y in yrs:
        a=np.array([r[1:] for s_,rows,_,_ in R for r in rows if r[0]==y])
        if b is None: b=a.mean(0)
        if y in (1980,1981,1982,1985,1990,2000,2010,2016): print(f' {y}: {a[:,0].sum()/a[:,1].sum():.4f} {a[:,1].mean()/b[1]:.4f} {a[:,0].mean()/b[0]:.4f} | {a[:,2].sum()/a[:,3].sum():.4f} {a[:,3].mean()/b[3]:.4f} {a[:,2].mean()/b[2]:.4f}')
