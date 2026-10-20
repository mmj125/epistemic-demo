import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']
rng=np.random.default_rng(2); A=A[rng.choice(len(A),300000,replace=False)]
y=A[:,3]
def L(k,j): return A[:,14+10*k+j]
no3=[L(k,0) for k in range(4)]; th=[L(k,5) for k in range(4)]; sat=[L(k,6) for k in range(4)]; T=[L(k,7) for k in range(4)]; thick=[L(k,8) for k in range(4)]
resp=(A[:,12]+A[:,13])*1000
top=np.cumsum([0]+[thick[k] for k in range(3)],axis=0) if False else None
def R2(p): return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
def fT(t): return np.where(t>10,np.exp(0.08*(t-15)),0.67*np.exp(0.43*(t-10)))
def FW(th_,sat_):
    d=np.clip(sat_-th_,0,None); return np.exp(0.304+2.94*d-47*d*d)
def fit(name,fn,p0,xs):
    r=least_squares(lambda p:fn(p)-y,p0,x_scale=xs,max_nfev=300); print(f" {name:62s} R2 {R2(fn(r.x)):.3f}  p {np.round(r.x,5)}"); return r.x
print("mean denit",y.mean())
# layers within the top 30 cm (cumulative thickness)
cum=np.zeros_like(y); inc=[]
for k in range(4):
    cum=cum+thick[k]; inc.append(cum<=0.30+1e-9)
l1=lambda p:1-np.exp(-p[0]*fT(T[0])*FW(th[0],sat[0]))
fit("S&C Eq12-14 layer 1: NO3 (1-exp(-K15 fT F))",lambda p:no3[0]*(1-np.exp(-abs(p[0])*fT(T[0])*FW(th[0],sat[0]))),[0.01],[0.01])
fit("S&C Eq12-14 summed over layers within 30 cm",lambda p:sum(np.where(inc[k],no3[k]*(1-np.exp(-abs(p[0])*fT(T[k])*FW(th[k],sat[k]))),0) for k in range(4)),[0.01],[0.01])
fit("S&C with free water exponent: F^n, layer 1",lambda p:no3[0]*(1-np.exp(-abs(p[0])*fT(T[0])*FW(th[0],sat[0])**p[1])),[0.01,1.0],[0.01,1.0])
s1=np.clip(th[0]/sat[0],0,1.2)
fit("layer 1: NO3 * K * fT * sat^n",lambda p:no3[0]*abs(p[0])*fT(T[0])*s1**abs(p[1]),[0.001,6],[0.001,2])
fit("layer 1: NO3 * K * fT * sat^n * resp^m",lambda p:no3[0]*abs(p[0])*fT(T[0])*s1**abs(p[1])*np.maximum(resp,1e-6)**abs(p[2]),[0.001,6,0.5],[0.001,2,0.3])
c=L(0,2)
fit("layer 1: engine-like K resp^a NO3c^b sat^n (4 free)",lambda p:abs(p[0])*np.maximum(resp,1e-6)**p[1]*np.maximum(c,1e-6)**p[2]*s1**abs(p[3]),[1e-3,0.77,0.7,6],[1e-3,.2,.2,2])
