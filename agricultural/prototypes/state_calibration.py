"""State-level calibration of the coupled canopy x nitrogen pair (2026-10-15). Objective: free-running daily canopy, nitrogen multiplier and plant N vs Cycles' own
daily series (about 100 points per site-year, not one grain number). Coordinate descent on the 16 tuning sites at N = 0/150; held-out states and grain checked after.
Usage: python3 state_calibration.py [max_evals]  -> /tmp/w/statecal_*.json"""
import sys,os,csv,json,datetime,time,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import rhizo_engine as E, run_validation_multisite as m, swap_test as S
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
TUNE=list(m.SITES);HELD=list(m.HELDOUT_SITES)
# name: (lo, hi, rel_step)  (multiplicative, log space)
PAR={'SIXPOOL_ML_N_A':(0.6,1.5,0.10),'SIXPOOL_ML_N_B':(0.5,1.8,0.12),'SIXPOOL_ML_N_C':(0.4,2.0,0.2),'N_DEMAND_SCALE':(0.7,1.2,0.05),'CANOPY_N_POW':(0.5,1.6,0.1),
     'CANOPY_WATER_POW':(0.6,1.5,0.1),'N_STRESS_ZERO_RATIO':(0.6,1.15,0.06),'N_STRESS_KNEE_RATIO':(0.7,1.8,0.12),'FE_TEMP_POW':(0.8,2.0,0.1),'CRA_MATURATION_TAU_DAYS':(0.15,1.5,0.25),'GRAIN_MULT':(0.9,1.25,0.03)}
P0={k:float(getattr(E,k)) for k in PAR if k!='GRAIN_MULT'};P0['GRAIN_MULT']=1.0
REF={}
GRAIN_W=float(os.environ.get('GRAIN_W','0'))   # >0 adds grain MAE to the objective (joint fit)
TAG=os.environ.get('TAG','statecal')
def ref(site,N):
    if (site,N) not in REF:
        d={}
        for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
            if x['date'][0]=='#' or x['biomass']=='-999':continue
            dt=datetime.date.fromisoformat(x['date']);d[(dt.year,dt.timetuple().tm_yday)]=(float(x['radiation_interception']),1-float(x['nitrogen_stress'])/100,float(x['total_nitrogen']))
        REF[(site,N)]=d
    return REF[(site,N)]
def one(a):
    site,N,p=a
    for k,v in p.items():
        if k=='GRAIN_MULT':os.environ['GRAIN_MULT']=str(v)
        else:setattr(E,k,v)
    lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=None;E.DIAG_STATE=[];r=m.engine(site,wx,soil,cl,N,'leadin');D=E.DIAG_STATE;E.DIAG_STATE=None
    R=ref(site,N);e=[];c=[]
    for y,doy,eie,ns,pn in D:
        v=R.get((y,doy))
        if v:e.append((eie,ns,pn));c.append(v)
    e=np.array(e);c=np.array(c)
    H={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')) if x['date'][0]!='#'}
    ys=[y for y in r if y in H];gm=float(np.abs(np.array([H[y] for y in ys])-np.array([r[y]['grain'] for y in ys])).mean())
    return site,N,float(np.sqrt(np.mean((e[:,0]-c[:,0])**2))),float(np.sqrt(np.mean((e[:,1]-c[:,1])**2))),float(np.sqrt(np.mean((e[:,2]-c[:,2])**2))),gm
def score(pool,p,sites):
    res=pool.map(one,[(s,N,p) for N in (0,150) for s in sites],chunksize=2)
    a=np.array([[r[2],r[3],r[4]/150.0,r[5]] for r in res])
    return float(a[:,:3].sum(axis=1).mean()+GRAIN_W*a[:,3].mean()),a.mean(axis=0)
if __name__=="__main__":
    maxe=int(sys.argv[1]) if len(sys.argv)>1 else 60
    with Pool(4) as pool:
        best=dict(P0);J0,d0=score(pool,best,TUNE);Jh0,dh0=score(pool,best,HELD)
        print('baseline tune J %.4f (canopy %.3f nmult %.3f plantN %.3f | grain MAE %.3f)  held J %.4f (grain %.3f)'%(J0,d0[0],d0[1],d0[2],d0[3],Jh0,dh0[3]),flush=True)
        J=J0;ev=0;t0=time.time();hist=[]
        for sweep in range(3):
            moved=False
            for k,(lo,hi,st) in PAR.items():
                for sgn in (1,-1):
                    if ev>=maxe:break
                    p=dict(best);v=best[k]*np.exp(sgn*st)
                    v=min(max(v,P0[k]*lo),P0[k]*hi)
                    if abs(v-best[k])<1e-12:continue
                    p[k]=v;Jn,dn=score(pool,p,TUNE);ev+=1
                    print('eval %2d %-24s -> %.4g  J %.4f (%s) %.1f min'%(ev,k,v,Jn,'ACCEPT' if Jn<J-1e-4 else 'no',(time.time()-t0)/60),flush=True)
                    if Jn<J-1e-4:
                        best,J,moved=p,Jn,True;hist.append((ev,k,v,J));break
            json.dump(dict(best=best,J=J,P0=P0,hist=hist),open('/tmp/w/'+TAG+'_best.json','w'))
            if not moved or ev>=maxe:break
        Jt,dt=score(pool,best,TUNE);Jh,dh=score(pool,best,HELD)
        print('FINAL tune J %.4f -> %.4f (canopy %.3f nmult %.3f plantN %.3f | grain %.3f -> %.3f)'%(J0,Jt,dt[0],dt[1],dt[2],d0[3],dt[3]))
        print('FINAL held J %.4f -> %.4f (grain %.3f -> %.3f)'%(Jh0,Jh,dh0[3],dh[3]))
        print('params',{k:round(v,4) for k,v in best.items()})
