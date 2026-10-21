import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']; Z=np.load('/tmp/w/site_l1.npz')
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
prev=lambda a: np.concatenate([[0],a[:-1]])
def L(k,j): return A[:,14+10*k+j]
site=A[:,9].astype(int); FC=Z['fc'][site]; PW=Z['pwp'][site]
cf=L(0,4); T=L(0,7); th=L(0,5)
sub=same&(T>0)&(np.random.default_rng(1).random(len(A))<0.15)
def rel(thv): return np.clip((thv-PW)/np.maximum(FC-PW,1e-3),0,None)
def run(nm,Tv,relv):
    f=lambda p:np.minimum(np.clip(Tv/p[0],0,None)**p[1],1.5)*(np.clip(relv,1e-6,None)**abs(p[3])/(np.clip(relv,1e-6,None)**abs(p[3])+abs(p[2])**abs(p[3])))
    r=least_squares(lambda p:(f(p)-cf)[sub],[31.5,1.35,0.123,1.72],max_nfev=300); pp=f(r.x)
    print(f" {nm:40s} R2 {1-((cf-pp)[sub]**2).sum()/((cf[sub]-cf[sub].mean())**2).sum():.3f}",np.round(r.x,3))
run("today's T, today's moisture",T,rel(th))
run("today's T, yesterday's moisture",T,rel(prev(th)))
run("yesterday's T, today's moisture",prev(T),rel(th))
run("yesterday's T and moisture",prev(T),rel(prev(th)))
run("today's T, mean of the two moistures",T,rel((th+prev(th))/2))
