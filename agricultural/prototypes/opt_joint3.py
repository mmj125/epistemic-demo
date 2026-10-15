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
    KS,PM,FM,HK,ND,EH=x
    return dict(SIXPOOL_ML_STOICH=True,SIXPOOL_ML_KS=float(KS),SIXPOOL_N_POT_MULT=float(PM),SIXPOOL_N_FMIN=float(FM),SIXPOOL_N_HALF_MGKG=float(HK),N_DEMAND_SCALE=float(ND),SIXPOOL_ML_HUM_CLAY=(float(EH),0.152))
pool=Pool(4);LOG=[]
def J(x):
    P=params(x);r=pool.map(task,[(s,N,P) for s in TR for N in (0,150)])
    mae=np.mean([q[0] for q in r]);bias=np.mean([q[1] for q in r]);LOG.append((list(map(float,x)),float(mae),float(bias)));print('x',np.round(x,6),'J %.4f bias %.3f'%(mae,bias),flush=True);return mae
if __name__=="__main__":
    x0=[cev.SIXPOOL_ML_KS,cev.SIXPOOL_N_POT_MULT,cev.SIXPOOL_N_FMIN,cev.SIXPOOL_N_HALF_MGKG,cev.N_DEMAND_SCALE,0.370]
    rng=np.random.default_rng(4);pts=[x0]
    for i in range(16):pts.append([x0[0]*math.exp(rng.uniform(-.4,.4)),rng.uniform(1.0,2.6),rng.uniform(0.1,0.6),x0[3]*math.exp(rng.uniform(-1.0,1.0)),x0[4]*math.exp(rng.uniform(-.3,.3)),rng.uniform(0.25,0.5)])
    sc=[J(p) for p in pts];best=pts[int(np.argmin(sc))]
    from scipy.optimize import minimize
    f=lambda z:J([math.exp(z[0]),z[1],z[2],math.exp(z[3]),z[4],z[5]]) if (z[1]>0.5 and 0<=z[2]<1 and z[4]>0.2 and 0.1<z[5]<0.7) else 9.0
    z0=[math.log(best[0]),best[1],best[2],math.log(best[3]),best[4],best[5]]
    st=[0.15,0.2,0.08,0.4,0.08,0.05]
    sim=[z0]+[[z0[j]+st[j] if j==i else z0[j] for j in range(6)] for i in range(6)]
    minimize(f,z0,method='Nelder-Mead',options=dict(maxfev=30,initial_simplex=np.array(sim)))
    json.dump(dict(log=LOG,best=min(LOG,key=lambda l:l[1]),train=TR),open(OUT,'w'),indent=0);print('BEST',min(LOG,key=lambda l:l[1]))
