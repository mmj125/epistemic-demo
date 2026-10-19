import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']; y=A[:,1]
def L(k,j): return A[:,14+10*k+j]
no3=[L(k,0) for k in range(4)]; nh4=[L(k,1) for k in range(4)]; cf=[L(k,4) for k in range(4)]
def R2(p): return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
def rk(k): return no3[k]/np.maximum(nh4[k],1e-3)
def inhib(r,r0,q): 
    x=np.clip(r/abs(r0),0,50); return 1/(1+x**q)
def fitit(name,fn,p0):
    r=least_squares(lambda p:fn(p)-y,p0,max_nfev=300); print(f" {name:60s} R2 {R2(fn(r.x)):.3f} params {np.round(r.x,3)}")
fitit("layer-1 only: k cf1 NH4_1 /(1+(r1/r0)^q)",lambda p:p[0]*cf[0]*nh4[0]*inhib(rk(0),p[1],p[2]),[0.1,8,5])
fitit("per layer k cf_k NH4_k /(1+(r_k/r0)^q)  layers 1-4",lambda p:sum(p[0]*cf[k]*nh4[k]*inhib(rk(k),p[1],p[2]) for k in range(4)),[0.1,8,5])
fitit("per layer layers 1-2",lambda p:sum(p[0]*cf[k]*nh4[k]*inhib(rk(k),p[1],p[2]) for k in range(2)),[0.1,8,5])
tot_no3=sum(no3); tot_nh4=sum(nh4)
fitit("profile ratio: k cf1 NH4prof /(1+(R/r0)^q)",lambda p:p[0]*cf[0]*tot_nh4*inhib(tot_no3/np.maximum(tot_nh4,1e-3),p[1],p[2]),[0.1,20,5])
