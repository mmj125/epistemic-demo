import numpy as np, sys
sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']; Z=np.load('/tmp/w/site_l1.npz')
rng=np.random.default_rng(1); idx=rng.choice(len(A),300000,replace=False); A=A[idx]
def L(k,j): return A[:,14+10*k+j]
site=A[:,9].astype(int); FC=Z['fc'][site]; PW=Z['pwp'][site]
cf=L(0,4); T=L(0,7); th=L(0,5); st=L(0,6); s=th/st; rel=(th-PW)/np.maximum(FC-PW,1e-3)
ok=(T>0)
print("n",ok.sum(),"cf range",cf.min(),cf.max())
import cycles_engine_validate as E
cur=np.array([E.sixpool_fe(t,r,True) for t,r in zip(T[ok][:60000],rel[ok][:60000])])
def R2(p,y): return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
print("current engine tables vs Cycles composite factor: R2 %.3f"%R2(cur,cf[ok][:60000]))
Tn=T[ok];cfn=cf[ok];sn=s[ok];reln=rel[ok]
def fit(nm,f,p0):
    r=least_squares(lambda p:f(p)-cfn,p0,max_nfev=300); print(f" {nm:58s} R2 {R2(f(r.x),cfn):.3f}",np.round(r.x,3)); return r.x
def fT_pow(p,t): return np.clip(t/p[0],0,None)**p[1]
def fT_c(p,t): To=p[0]; return np.clip((2*(t+4)**2*(To+4)**2-(t+4)**4)/(To+4)**4,0,None)
fW=lambda h,pw,x: x**pw/(x**pw+h**pw)
fit("fT power(T/To)^a, fW documented 0.22/3 on theta/sat",lambda p:np.minimum(fT_pow(p,Tn),1.5)*fW(0.22,3.0,sn),[31,1.5])
fit("fT power, fW(theta/sat) free half & power",lambda p:np.minimum(fT_pow(p[:2],Tn),1.5)*fW(abs(p[2]),abs(p[3]),sn),[31,1.5,0.22,3])
fit("fT Campbell(T+4) Eq18, fW documented",lambda p:fT_c(p,Tn)*fW(0.22,3.0,sn),[30])
fit("fT Eq18, fW free",lambda p:fT_c(p,Tn)*fW(abs(p[1]),abs(p[2]),sn),[30,0.22,3])
fit("fT power, fW free on relwet",lambda p:np.minimum(fT_pow(p[:2],Tn),1.5)*fW(abs(p[2]),abs(p[3]),np.clip(reln,0,None)),[31,1.5,0.2,2])
