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
    Kd,ex,ND,Nn,Nd,KH=x
    return dict(DENITRIF_K_REL=float(Kd),DENITRIF_RELSAT_EXPONENT=float(ex),N_DEMAND_SCALE=float(ND),N2O_NITRIF_FRAC=float(Nn),N2O_DENIT_A=float(Nd),KHE_SCALE=float(KH))
pool=Pool(4);LOG=[]
def score(r):
    ymae=np.mean([q[2][0] for q in r]);L=[]
    for N in (150,400):
        for i in range(1,5):
            a=np.array([(q[2][i][0],q[2][i][1]) for q in r if q[1]==N and q[2][i][0]>0.3])
            L.append(math.sqrt(np.mean(np.log(np.maximum(a[:,1],0.05)/a[:,0])**2)))
    return ymae/0.8+0.5*float(np.mean(L)),ymae,float(np.mean(L))
def J(x):
    P=params(x);r=pool.map(task,[(s,N,P) for s in TR for N in (0,150,400)]);j,ym,ll=score(r)
    LOG.append((list(map(float,x)),j,ym,ll));print('x',np.round(x,5),'J %.4f yieldMAE %.3f lossRMSlog %.3f'%(j,ym,ll),flush=True);return j
if __name__=="__main__":
    x0=[cev.DENITRIF_K_REL,cev.DENITRIF_RELSAT_EXPONENT,cev.N_DEMAND_SCALE,cev.N2O_NITRIF_FRAC,cev.N2O_DENIT_A,cev.KHE_SCALE]
    rng=np.random.default_rng(6);pts=[x0]
    for i in range(14):pts.append([x0[0]*math.exp(rng.uniform(-.2,1.2)),rng.uniform(4.5,8.5),x0[2]*math.exp(rng.uniform(-.25,.15)),x0[3]*math.exp(rng.uniform(0,1.2)),x0[4]*math.exp(rng.uniform(0,1.2)),math.exp(rng.uniform(-.4,.7))])
    sc=[J(p) for p in pts];best=pts[int(np.argmin(sc))]
    from scipy.optimize import minimize
    f=lambda z:J([math.exp(z[0]),z[1],z[2],math.exp(z[3]),math.exp(z[4]),math.exp(z[5])]) if (2<z[1]<12 and 0.5<z[2]<2) else 9.0
    z0=[math.log(best[0]),best[1],best[2],math.log(best[3]),math.log(best[4]),math.log(best[5])]
    st=[0.25,0.6,0.06,0.25,0.25,0.2]
    sim=[z0]+[[z0[j]+st[j] if j==i else z0[j] for j in range(6)] for i in range(6)]
    minimize(f,z0,method='Nelder-Mead',options=dict(maxfev=28,initial_simplex=np.array(sim)))
    json.dump(dict(log=LOG,best=min(LOG,key=lambda l:l[1]),train=TR),open(OUT,'w'),indent=0);print('BEST',min(LOG,key=lambda l:l[1]))
