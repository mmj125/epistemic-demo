"""Carbon-pool teacher forcing (2026-10-19): corn, 24 sites, N=0 (and 150), continuous chain. Each day the engine's per-layer soil organic C, microbial C and root residue C and the surface residue C are set to Cycles' (start of day = previous date's dailySoilLayersCN / dailyResidue values),
and Cycles' daily mineral N pools are forced too (NPOOL_FORCE), so only the N accounting and the decomposition rates act. Daily net mineralization, engine vs Cycles, by month, and the annual total."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=os.environ.get("NLEV","0"); sys.path.insert(0,'.')
NLEV=int(os.environ.get("NLEV","0"))
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NLEV}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NLEV}/"
    L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; Rz={r['date']:r for r in rd(d+"dailyResidue.csv")}; Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    nl=len([k for k in next(iter(L.values())) if k.startswith('microbial_carbon.')])
    CF={}; cyc={}; P={}
    dates=sorted(L)
    for a,b in zip(dates,dates[1:]):
        db=datetime.date.fromisoformat(b); l=L[a]; r=Rz.get(a)
        if r is None: continue
        CF[(db.year,db.timetuple().tm_yday)]={'surface':float(l['standing_residue_carbon'])+float(l['flat_residue_carbon']),'layers':{i:(float(l[f'soil_organic_carbon.{i+1}']),float(l[f'microbial_carbon.{i+1}']),float(l[f'residue_carbon.{i+1}'])) for i in range(nl)}}
    for r in Nn:
        dd=datetime.date.fromisoformat(r['date']); k=(dd.year,dd.timetuple().tm_yday); cyc[k]=float(r['net_mineralization']); P.setdefault(dd.year,{})[k[1]]=(float(r['profile_soil_NO3']),float(r['profile_soil_NH4']))
    out={}
    E.CFORCE_WHICH=tuple(os.environ.get('CFW','surface,cs,root').split(','))
    for mode in ('free','cforce'):
        E.CFORCE=CF if mode=='cforce' else None; E.NPOOL_FORCE=P if mode=='cforce' else None; E.DIAG_NFLUX=[]; E.DIAG_NSEASON=[]; E.SIXPOOL_DIAG=None
        m.engine(site,wx,soil,cl,NLEV,'leadin'); E.CFORCE=None; E.NPOOL_FORCE=None
        eng={}
        for y,doy,sm,*_ in E.DIAG_NFLUX:
            if y is not None: eng[(y,doy)]=sm
        for y,doy,nm,*_ in E.DIAG_NSEASON:
            if y is not None: eng[(y,doy)]=nm
        E.DIAG_NFLUX=None; E.DIAG_NSEASON=None; out[mode]=eng
    rows=[]
    for k,c in cyc.items():
        if k[0]>=1982 and k in out['free'] and k in out['cforce']: rows.append((k[1],c,out['free'][k],out['cforce'][k]))
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/cforce_%d_%s.npy'%(NLEV,os.environ.get('CFW','default').replace(',','')),A); print(len(A),'site-days; mean daily net mineralization (kg N/ha): Cycles %.4f | engine free %.4f | engine with Cycles carbon and N pools %.4f'%(A[:,1].mean(),A[:,2].mean(),A[:,3].mean()))
    mo=((A[:,0]-1)//30.5+1).astype(int)
    print('month | Cycles | free | forced | forced/Cycles')
    for k in range(1,13):
        s=mo==k
        if s.sum()>200: print(f'  {k:2d}: {A[s,1].mean():7.4f} | {A[s,2].mean():7.4f} | {A[s,3].mean():7.4f} | {A[s,3].mean()/max(abs(A[s,1].mean()),1e-9):.2f}')
    print('annual sum (kg/ha/yr): Cycles %.1f | free %.1f | forced %.1f'%(A[:,1].mean()*365,A[:,2].mean()*365,A[:,3].mean()*365))
