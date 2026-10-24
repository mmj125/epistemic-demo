"""Joint refit of the N-loss and N-demand constants on yield plus site-mean loss errors (REFIT_PLAN row 45). Params: DENITRIF_K_REL, DENITRIF_RELSAT_EXPONENT,
N_DEMAND_SCALE, N2O_NITRIF_FRAC, N2O_DENIT_A, KHE_SCALE. Training: random sites, first NYR years, N = 0/150/400, regionalization off.
Usage: python3 opt_loss.py NSITES OUT.json"""
import sys,os,json,random,math,numpy as np
os.environ["REGIONAL"]="0";os.environ["LEAD_YEARS"]="continuous"
sys.path.insert(0,'.')
import run_validation_multisite as m
import rhizo_engine as cev
from multiprocessing import Pool
NS=int(sys.argv[1]);OUT=sys.argv[2];NYR=int(os.environ.get("NYR","12"))
ALL={}
for f in ("/tmp/w/big240.json","/tmp/w/old28.json"):ALL.update({k:tuple(v) for k,v in json.load(open(f)).items()})
random.seed(11);TR=sorted(random.sample(sorted(ALL),NS))
CACHE={}
def setup(site):
    if site not in CACHE:
        lat,lon=ALL[site];wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon)
        ys=sorted(wx)[:NYR];CACHE[site]=({y:wx[y] for y in ys},soil,m.lat_of(lat,lon))
    return CACHE[site]
KEYS=[("leach","n_leached_kg_ha"),("volat","n_volatilized_pool_kg_ha"),("denit","n_denitrified_kg_ha"),("n2o","n2o_emitted_kg_ha")]
def task(args):
    site,N,P=args
    for k,v in P.items():setattr(cev,k,v)
    wx,soil,cl=setup(site);H,A=m.run_cycles(site,N);E=m.engine(site,wx,soil,cl,N,'leadin')
    ys=sorted(set(H)&set(E));mae=float(np.mean([abs(H[y]['grain']-E[y]['grain']) for y in ys]))
    yy=[y for y in ys if y in A];out=[mae]
    for k,ek in KEYS:out.append((float(np.mean([A[y][k] for y in yy])),float(np.mean([E[y].get(ek,0.0) for y in yy]))))
    return site,N,out
def params(x):
    A,B,C,D=x
    return dict(VOLATILIZATION_RATE_A=float(A),VOLATILIZATION_RATE_B=float(B),VOLATILIZATION_RATE_C=float(C),VOLATILIZATION_RATE_D=float(D))
pool=Pool(4);LOG=[]
def score(r):
    ymae=np.mean([q[2][0] for q in r]);L=[]
    for N in (0,150,400):
        for i in (2,):
            a=np.array([(q[2][i][0],q[2][i][1]) for q in r if q[1]==N and q[2][i][0]>0.3])
            L.append(math.sqrt(np.mean(np.log(np.maximum(a[:,1],0.05)/a[:,0])**2)))
    return ymae/0.8+0.5*float(np.mean(L)),ymae,float(np.mean(L))
def J(x):
    P=params(x);r=pool.map(task,[(s,N,P) for s in TR for N in (0,150,400)]);j,ym,ll=score(r)
    LOG.append((list(map(float,x)),j,ym,ll));print('x',np.round(x,5),'J %.4f yieldMAE %.3f lossRMSlog %.3f'%(j,ym,ll),flush=True);return j
if __name__=="__main__":
    x0=[cev.VOLATILIZATION_RATE_A,cev.VOLATILIZATION_RATE_B,cev.VOLATILIZATION_RATE_C,cev.VOLATILIZATION_RATE_D]
    from scipy.optimize import minimize
    f=lambda z:J([math.exp(z[0]),z[1],z[2],z[3]]) if (0.02<z[1]<0.3 and -0.02<z[2]<0.01 and -3<z[3]<0.5) else 9.0
    z0=[math.log(x0[0]),x0[1],x0[2],x0[3]]
    sim=[z0]+[[z0[j]+st if j==i else z0[j] for j in range(4)] for i,st in enumerate([0.4,0.03,0.002,0.3])]
    minimize(f,z0,method='Nelder-Mead',options=dict(maxfev=40,initial_simplex=np.array(sim)))
    json.dump(dict(log=LOG,best=min(LOG,key=lambda l:l[1]),train=TR),open(OUT,'w'),indent=0);print('BEST',min(LOG,key=lambda l:l[1]))
