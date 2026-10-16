"""Joint refit of the N-loss and N-demand constants on yield plus site-mean loss errors (REFIT_PLAN row 45). Params: DENITRIF_K_REL, DENITRIF_RELSAT_EXPONENT,
N_DEMAND_SCALE, N2O_NITRIF_FRAC, N2O_DENIT_A, KHE_SCALE. Training: random sites, first NYR years, N = 0/150/400, regionalization off.
Usage: python3 opt_loss.py NSITES OUT.json"""
import sys,os,json,random,math,numpy as np
os.environ["REGIONAL"]="0";os.environ["LEAD_YEARS"]="continuous"
sys.path.insert(0,'.')
import run_validation_multisite as m
import cycles_engine_validate as cev
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
    vp,ha,ce,ng=x
    return dict(C1_VPD_POW=float(vp),HEAT_A=float(ha),WUE_CO2_EXP=float(ce),NET_GROWTH_FRACTION=float(ng))
pool=Pool(4);LOG=[]
def score(r):
    ymae=np.mean([q[2][0] for q in r]);L=[]
    for N in (150,400):
        for i in range(1,5):
            a=np.array([(q[2][i][0],q[2][i][1]) for q in r if q[1]==N and q[2][i][0]>0.3])
            L.append(math.sqrt(np.mean(np.log(np.maximum(a[:,1],0.05)/a[:,0])**2)))
    return ymae,ymae,0.0
def J(x):
    P=params(x);r=pool.map(task,[(s,N,P) for s in TR for N in (0,150,400)]);j,ym,ll=score(r)
    LOG.append((list(map(float,x)),j,ym,ll));print('x',np.round(x,5),'J %.4f yieldMAE %.3f lossRMSlog %.3f'%(j,ym,ll),flush=True);return j
if __name__=="__main__":
    x0=[cev.C1_VPD_POW,cev.HEAT_A,cev.WUE_CO2_EXP,cev.NET_GROWTH_FRACTION]
    from scipy.optimize import minimize
    f=lambda z:J([z[0],z[1],z[2],z[3]]) if (0.3<z[0]<0.7 and 0<=z[1]<0.01 and -0.2<z[2]<1.5 and 0.6<z[3]<1.1) else 9.0
    sim=[x0]+[[x0[j]+st if j==i else x0[j] for j in range(4)] for i,st in enumerate([-0.09,-0.003,-0.7,0.05])]
    minimize(f,x0,method='Nelder-Mead',options=dict(maxfev=45,initial_simplex=np.array(sim)))
    json.dump(dict(log=LOG,best=min(LOG,key=lambda l:l[1]),train=TR),open(OUT,'w'),indent=0);print('BEST',min(LOG,key=lambda l:l[1]))
