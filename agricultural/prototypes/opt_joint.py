"""Joint refit of the six-pool constants on the real objective (grain MAE vs Cycles at N=0 and N=150, regionalization off), 2026-10-15 (REFIT_PLAN row 43).
Training: random subset of the 268 reference sites, first 17 weather years only (fast). Search: random Latin sample then Nelder-Mead. Usage: python3 opt_joint.py NSITES OUT.json"""
import sys,os,json,random,math,numpy as np
os.environ["REGIONAL"]="0";os.environ["LEAD_YEARS"]="continuous"
sys.path.insert(0,'.')
import run_validation_multisite as m
import cycles_engine_validate as cev
from multiprocessing import Pool
NS=int(sys.argv[1]);OUT=sys.argv[2];NYR=int(os.environ.get("NYR","17"))
ALL={}
for f in ("/tmp/w/big240.json","/tmp/w/old28.json"):ALL.update({k:tuple(v) for k,v in json.load(open(f)).items()})
random.seed(5);TR=sorted(random.sample(sorted(ALL),NS))
CACHE={}
def setup(site):
    if site not in CACHE:
        lat,lon=ALL[site];wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon)
        ys=sorted(wx)[:NYR];CACHE[site]=({y:wx[y] for y in ys},soil,m.lat_of(lat,lon))
    return CACHE[site]
def task(args):
    site,N,P=args
    for k,v in P.items():setattr(cev,k,v)
    wx,soil,cl=setup(site)
    H,_=m.run_cycles(site,N)
    E=m.engine(site,wx,soil,cl,N,'leadin')
    ys=sorted(set(H)&set(E));a=np.array([H[y]['grain'] for y in ys]);b=np.array([E[y]['grain'] for y in ys])
    return np.abs(a-b).mean(),(b-a).mean()
def params(x):
    KS,A,B=x[0],x[1],x[2]
    return dict(SIXPOOL_ML_FD_SI=(4.26,2.53),SIXPOOL_ML_DEPTH_Q=0.108,SIXPOOL_ML_KS=float(KS),SIXPOOL_ML_N_A=float(A),SIXPOOL_ML_N_B=float(B))
pool=Pool(4);LOG=[]
def J(x):
    P=params(x);r=pool.map(task,[(s,N,P) for s in TR for N in (0,150)])
    mae=np.mean([q[0] for q in r]);bias=np.mean([q[1] for q in r]);LOG.append((list(map(float,x)),float(mae),float(bias)));print('x',np.round(x,6),'J %.4f bias %.3f'%(mae,bias),flush=True);return mae
if __name__=="__main__":
    base=task_base=None
    rng=np.random.default_rng(1);pts=[[1.04e-4,100,33]]
    for i in range(14):pts.append([math.exp(rng.uniform(math.log(0.6e-4),math.log(2.2e-4))),rng.uniform(70,150),rng.uniform(15,70)])
    sc=[J(p) for p in pts];best=pts[int(np.argmin(sc))]
    from scipy.optimize import minimize
    f=lambda z:J([math.exp(z[0]),z[1],z[2]]) if (z[1]>30 and z[2]>0) else 9.0
    r=minimize(f,[math.log(best[0]),best[1],best[2]],method='Nelder-Mead',options=dict(maxfev=25,xatol=1e-3,fatol=1e-3,initial_simplex=np.array([[math.log(best[0]),best[1],best[2]],[math.log(best[0])+0.2,best[1],best[2]],[math.log(best[0]),best[1]+12,best[2]],[math.log(best[0]),best[1],best[2]+8]])))
    json.dump(dict(log=LOG,best=LOG[int(np.argmin([l[1] for l in LOG]))],train=TR),open(OUT,'w'),indent=0);print('BEST',min(LOG,key=lambda l:l[1]))
