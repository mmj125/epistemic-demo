"""Fit the six-pool nitrogen constants to the 96 designed fertilized-corn runs (REFIT_PLAN row 44): annual net N mineralization, crop N uptake and grain
versus Cycles v1.5.20. Params: KS, A, B, N_POT_MULT, N_FMIN, N_HALF_MGKG. Usage: python3 opt_designed.py OUT.json"""
import sys,os,json,math,csv,itertools
os.environ["REGIONAL"]="0";os.environ["LEAD_YEARS"]="continuous"
import numpy as np
sys.path.insert(0,'.')
import run_validation_multisite as m,cycles_engine_validate as E,designed_crop as D
from multiprocessing import Pool
CY=m.CY;YS=[y for y in D.YRS if y>=1983]
def cyc(site,N):
    d=f"{CY}/output/{site}N{N}"
    Nn=list(csv.reader(open(d+'/dailyN.csv')));i=Nn[0].index('net_mineralization')
    nm=np.mean([sum(float(r[i]) for r in Nn[2:] if r[0].startswith(str(y))) for y in YS])
    C=list(csv.reader(open(d+'/dailyCornRM.90.csv')));ht=C[0].index('total_nitrogen')
    up=np.mean([max([float(r[ht]) for r in C[2:] if r[0].startswith(str(y))] or [0]) for y in YS])
    H={}
    for line in open(d+'/harvest.csv').readlines()[2:]:
        p=line.strip().split(',')
        if len(p)>=11:H[int(p[0][:4])]=float(p[5])
    return nm,up,np.mean([H.get(y,0) for y in YS])
DES=[(Tm,rain,soc0,clay,N) for Tm,rain,soc0,clay in itertools.product(D.TMS,D.RAINS,D.SOCS,D.CLAYS) for N in D.NS]
TARGET={}
def target(k):
    if k not in TARGET:
        Tm,rain,soc0,clay,N=k;TARGET[k]=cyc(f"dx_{Tm}_{int(rain*10)}_{int(soc0*10)}_{clay}",N)
    return TARGET[k]
def task(args):
    k,P=args;Tm,rain,soc0,clay,N=k
    for a,v in P.items():setattr(E,a,v)
    rec=[];o=E.sixpool_ml_step
    def w(*a,**kw):
        r=o(*a,**kw);rec.append(r);return r
    E.sixpool_ml_step=w
    try:res=m.engine("dx",D.wx_of(Tm,rain),D.soil_of(soc0,clay),40.0,N,'leadin')
    finally:E.sixpool_ml_step=o
    nm=sum(rec)/len(D.YRS);up=np.mean([res[y].get('n_uptake_kg_ha',0) for y in YS]);gr=np.mean([res[y]['grain'] for y in YS])
    tn,tu,tg=target(k)
    return abs(nm-tn),abs(up-tu),abs(gr-tg),nm-tn,up-tu,gr-tg
def params(x):
    KS,A,B,PM,FM,HK=x
    return dict(SIXPOOL_ML_KS=float(KS),SIXPOOL_ML_N_A=float(A),SIXPOOL_ML_N_B=float(B),SIXPOOL_N_POT_MULT=float(PM),SIXPOOL_N_FMIN=float(FM),SIXPOOL_N_HALF_MGKG=float(HK))
pool=Pool(4);LOG=[]
def J(x):
    P=params(x);r=np.array(pool.map(task,[(k,P) for k in DES]))
    j=r[:,0].mean()/20+r[:,1].mean()/40+r[:,2].mean()/1.0
    LOG.append((list(map(float,x)),float(j),r.mean(0).tolist()));print('x',np.round(x,5),'J %.4f  |dnetmin| %.1f |dup| %.1f |dgrain| %.2f  bias nm %.1f up %.1f gr %.2f'%(j,*r[:,:3].mean(0),*r[:,3:].mean(0)),flush=True);return j
if __name__=="__main__":
    for k in DES:target(k)
    x0=[E.SIXPOOL_ML_KS,E.SIXPOOL_ML_N_A,E.SIXPOOL_ML_N_B,E.SIXPOOL_N_POT_MULT,E.SIXPOOL_N_FMIN,E.SIXPOOL_N_HALF_MGKG]
    J(x0);rng=np.random.default_rng(3);best=x0;bj=LOG[0][1]
    for i in range(24):
        x=[x0[0]*math.exp(rng.uniform(-.5,.5)),x0[1]*math.exp(rng.uniform(-.4,.4)),x0[2]*math.exp(rng.uniform(-.7,.7)),rng.uniform(1.0,3.0),rng.uniform(0.0,0.6),math.exp(rng.uniform(math.log(0.1),math.log(2.0)))]
        j=J(x)
        if j<bj:bj,best=j,x
    from scipy.optimize import minimize
    f=lambda z:J([math.exp(z[0]),z[1],z[2],z[3],z[4],math.exp(z[5])]) if (z[1]>20 and z[2]>0 and z[3]>0.5 and 0<=z[4]<1 ) else 9.0
    z0=[math.log(best[0]),best[1],best[2],best[3],best[4],math.log(best[5])]
    sim=[z0]+[[z0[j]+(0.15 if j in(0,5) else (0.12*z0[j] if j in (1,2) else 0.2 if j==3 else 0.08)) if j==i else z0[j] for j in range(6)] for i in range(6)]
    minimize(f,z0,method='Nelder-Mead',options=dict(maxfev=40,initial_simplex=np.array(sim)))
    json.dump(dict(log=LOG,best=min(LOG,key=lambda l:l[1])),open(sys.argv[1],'w'));print('BEST',min(LOG,key=lambda l:l[1]))
