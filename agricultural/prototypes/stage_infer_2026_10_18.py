"""Infer the early-season growth term (2026-10-18). Cycles run per site (corn, continuous), its daily canopy, water and N factor forced into the engine; per growing day: engine gross gain x N factor
(Mg/ha) vs Cycles' change in total biomass, with thermal-time fraction (Cycles TT / engine tt_maturity), Cycles' canopy, cumulative Cycles biomass, tmean and solar. Saves /tmp/w/stage_N{N}.npz.
Usage: python3 stage_infer_2026_10_18.py N_SITES N"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
NS=int(sys.argv[1]); NLEV=int(sys.argv[2]); os.environ["N_LEVELS"]=str(NLEV)
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NLEV}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NLEV}/"
    D=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    F={}; B={}
    for x in D:
        if x['biomass']=='-999': continue
        dt=datetime.date.fromisoformat(x['date']); y=dt.year; doy=dt.timetuple().tm_yday
        f=F.setdefault(y,{'canopy':{},'water':{},'nstress':{}})
        f['canopy'][doy]=float(x['radiation_interception']); f['water'][doy]=1-float(x['water_stress'])/100; f['nstress'][doy]=1-float(x['nitrogen_stress'])/100
        B[(y,doy)]=(float(x['biomass']),float(x['thermal_time']),float(x['radiation_interception']),1-float(x['nitrogen_stress'])/100)
    E.FORCE_SERIES=F; E.DIAG_GROWTH=[]
    res=m.engine(site,wx,soil,cl,NLEV,'leadin'); G=E.DIAG_GROWTH; E.DIAG_GROWTH=None; E.FORCE_SERIES=None
    segs=[];cur=[]
    for g in G:
        if cur and g[0]<cur[-1][0]: segs.append(cur);cur=[]
        cur.append(g)
    if cur: segs.append(cur)
    ys=sorted(res)
    if len(segs)!=len(ys): return site,None
    rows=[]
    for y,sg in zip(ys,segs):
        for (doy,GR,GT,dgb) in sg:
            if (y,doy) in B and (y,doy-1) in B and doy in wx[y]:
                w=wx[y][doy]; b=B[(y,doy)]
                rows.append((dgb*10.0*b[3]**E.N_STRESS_GROWTH_POW, b[0]-B[(y,doy-1)][0], b[1]/rv.CORN['tt_maturity'], b[2], B[(y,doy-1)][0], (w['tx']+w['tn'])/2, w['solar'], GR, GT, y, doy))
    return site,np.array(rows)
if __name__=="__main__":
    ks=sorted(S)[:NS]
    with Pool(4) as p: R=p.map(one,ks)
    out={s:a for s,a in R if a is not None and len(a)}
    np.savez(f'/tmp/w/stage_N{NLEV}.npz',**out); print('saved',len(out),'sites; days',sum(len(a) for a in out.values()))
