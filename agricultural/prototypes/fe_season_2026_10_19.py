"""Decomposition environmental factor fE by month, engine vs Cycles (2026-10-19): corn N=0, 24 sites, continuous chain, layers 1 and 2. Cycles' composite_factor.i (dailySoilLayersCN) against the engine's fE per layer (DIAG_FE), joined by date.
Also the engine layer temperature and relative wetness. Looks for the cold-season mineralization offset."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; shutil.rmtree(d,ignore_errors=True)
    E.DIAG_FE=[]; m.engine(site,wx,soil,cl,0,'leadin'); D=E.DIAG_FE; E.DIAG_FE=None; last={}
    for y,doy,i,t,rw,fe in D:
        if y is None or doy is None or i>1 or y<1982: continue
        last[(y,doy,i)]=(t,rw,fe)
    rows=[]
    for (y,doy,i),(t,rw,fe) in last.items():
        dt=(datetime.date(y,1,1)+datetime.timedelta(days=doy-1)).isoformat()
        if dt in L and f'composite_factor.{i+1}' in L[dt]: rows.append((dt[5:7],i,float(L[dt][f'composite_factor.{i+1}']),fe,t,rw))
    return rows
if __name__=="__main__":
    R=sum(Pool(4).map(one,sorted(S)),[]); A=np.array([(int(a),b,c,d,e,f) for a,b,c,d,e,f in R]); np.save('/tmp/w/fe_season.npy',A); print(len(A),'layer-days')
    for i in (0,1):
        print(f'layer {i+1}: month | Cycles composite factor | engine fE | ratio | engine layer T | engine relwet')
        for mo in (11,12,1,2,3,4,5,8,9,10):
            k=(A[:,1]==i)&(A[:,0]==mo)
            if k.sum()>300: print(f'  {mo:2d}: {A[k,2].mean():.4f} | {A[k,3].mean():.4f} | {A[k,3].mean()/max(A[k,2].mean(),1e-9):.2f} | {A[k,4].mean():5.1f} | {A[k,5].mean():.2f}  (n {k.sum()})')
