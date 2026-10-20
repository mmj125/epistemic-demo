import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
prev=lambda a: np.concatenate([[0],a[:-1]])
rng=np.random.default_rng(2); sub=same&(rng.random(len(A))<0.3)
y=A[sub,3]
def L(k,j): return A[:,14+10*k+j]
resp=((A[:,12]+A[:,13])*1000)[sub]
def get(k):
    return dict(no3=L(k,0)[sub],no3p=prev(L(k,0))[sub],no3c=L(k,2)[sub],no3cp=prev(L(k,2))[sub],th=L(k,5)[sub],sat=L(k,6)[sub],T=L(k,7)[sub],thick=L(k,8)[sub])
D=[get(k) for k in range(4)]
d0=D[0]
def R2(p): return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
def fit(name,fn,p0,xs):
    r=least_squares(lambda p:fn(p)-y,p0,x_scale=xs,max_nfev=400); print(f" {name:64s} R2 {R2(fn(r.x)):.3f}  p {np.round(r.x,5)}"); return r.x
def fT(t): return np.where(t>10,np.exp(0.08*(t-15)),0.67*np.exp(0.43*(t-10)))
def FW(th_,sat_): d=np.clip(sat_-th_,0,None); return np.exp(0.304+2.94*d-47*d*d)
s1=np.clip(d0["th"]/d0["sat"],0,1.2)
print("mean",y.mean())
for lab,key in (("end-of-day nitrate","no3"),("START-of-day nitrate","no3p")):
    N=d0[key]; Nc=d0["no3c" if key=="no3" else "no3cp"]
    print("==",lab)
    fit("S&C Eq12-14 layer 1",lambda p:N*(1-np.exp(-abs(p[0])*fT(d0["T"])*FW(d0["th"],d0["sat"]))),[0.01],[0.01])
    fit("NO3 K fT sat^n",lambda p:N*abs(p[0])*fT(d0["T"])*s1**abs(p[1]),[0.001,6],[0.001,2])
    fit("NO3 K fT sat^n resp^m",lambda p:N*abs(p[0])*fT(d0["T"])*s1**abs(p[1])*np.maximum(resp,1e-6)**abs(p[2]),[0.001,6,0.5],[0.001,2,0.3])
    fit("engine-like K resp^a NO3c^b sat^n",lambda p:abs(p[0])*np.maximum(resp,1e-6)**p[1]*np.maximum(Nc,1e-6)**p[2]*s1**abs(p[3]),[1e-3,0.77,0.7,6],[1e-3,.2,.2,2])
    fit("K resp NO3c/(NO3c+Kh) sat^n",lambda p:abs(p[0])*resp*Nc/(Nc+abs(p[1]))*s1**abs(p[2]),[1e-3,5,6],[1e-3,2,2])
print("== response to saturation: shape and ML ceiling")
N=d0["no3cp"]
g=lambda p,s: s**abs(p[0])
fit("K resp MM sat^n (ref)",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*s1**abs(p[2]),[1e-3,16,4.5],[1e-3,2,2])
fit("K resp MM  1/(1+(h/sat)^pw) (decomp-style)",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))/(1+(abs(p[2])/np.maximum(s1,1e-3))**abs(p[3])),[1e-3,16,0.7,6],[1e-3,2,.1,2])
fit("K resp MM  logistic(sat)",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))/(1+np.exp(np.clip(-(s1-p[2])/abs(p[3]),-50,50))),[1e-3,16,0.8,0.08],[1e-3,2,.05,.02])
fit("K resp MM sat^n fT(Eq13) ",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*s1**abs(p[2])*fT(d0["T"]),[1e-3,16,4.5],[1e-3,2,2])
try:
    from sklearn.ensemble import HistGradientBoostingRegressor as H
    X=np.column_stack([resp,N,d0["no3p"],s1,d0["T"],d0["thick"],D[1]["no3cp"],D[1]["th"]/D[1]["sat"],D[1]["T"],A[sub,8],A[sub,6],A[sub,7]])
    n=len(y); k=int(.7*n); m=H(max_iter=300).fit(X[:k],y[:k]); print(" ML test R2",round(m.score(X[k:],y[k:]),3))
    X2=X[:,:5]; m2=H(max_iter=300).fit(X2[:k],y[:k]); print(" ML test R2 (resp,NO3c,NO3,sat,T only)",round(m2.score(X2[k:],y[k:]),3))
except Exception as e: print(e)
print("== sub-daily saturation: infiltration raises the saturation the flux sees")
inf=A[sub,6]; thk=d0["thick"]
for lab,sfun in (("s + a*infil/(thick*sat*1000), clipped 1.2",lambda a: np.clip(s1+abs(a)*inf/(thk*np.maximum(d0["sat"],.05)*1000),0,1.2)),):
    fit("K resp MM sat_eff^n  ("+lab+")",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*sfun(p[3])**abs(p[2]),[0.2,16,4.5,0.5],[1e-2,2,1,.2])
sat_inf=np.clip(s1+inf/(thk*np.maximum(d0["sat"],.05)*1000),0,1.2)
fit("K resp MM max(s, infil-based)^n",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*np.maximum(s1,sat_inf*abs(p[3]))**abs(p[2]),[0.2,16,4.5,1.0],[1e-2,2,1,.2])
rain=inf>0.1
print(" mean residual share on rain days:",(y[rain].sum()/y.sum()),"rain-day fraction",rain.mean())
