import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
prev=lambda a: np.concatenate([[0],a[:-1]])
def L(k,j): return A[:,14+10*k+j]
y=A[:,1]; sub=same&(np.random.default_rng(4).random(len(A))<0.25)
def fT11(t): t=np.asarray(t,float); return np.where(t<=0,0.0,np.where(t<10,0.0105*t+0.00095*t*t,np.where(t<35,0.032*t-0.12,np.where(t<45,4.5-0.1*t,0.0))))
def layer(i,p):
    nh=prev(L(i,1)); no=prev(L(i,0)); r=no/np.maximum(nh,1e-9); s=np.clip(L(i,5)/np.maximum(L(i,6),1e-6),0,1.2)
    return p[0]*fT11(L(i,7))*nh/(1+(r/abs(p[1]))**abs(p[2]))/(1+np.exp(np.clip((s-p[3])/abs(p[4]),-50,50)))
def run(nm,layers_):
    f=lambda p:sum(layer(i,p) for i in layers_)
    r=least_squares(lambda p:(f(p)-y)[sub],[0.2,8.2,6.2,0.795,0.078],x_scale=[.1,2,2,.05,.02],max_nfev=300); pp=f(r.x)
    print(f" {nm:30s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.4f}",np.round(r.x,3))
run("layer 1 only",[0]); run("layers 1-2",[0,1]); run("layers 1-3",[0,1,2]); run("layers 1-4",[0,1,2,3])
print("mean NH4 by layer:",[round(L(i,1).mean(),2) for i in range(4)],"mean nitrification",y.mean())
