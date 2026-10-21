import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']; Z=np.load('/tmp/w/site_l1.npz')
prev=lambda a: np.concatenate([[0],a[:-1]])
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
def L(k,j): return A[:,14+10*k+j]
site=A[:,9].astype(int); FC=Z['fc'][site]; PW=Z['pwp'][site]; ST=Z['sat'][site]
y=A[:,3]; resp=(A[:,12]+A[:,13])*1000; N=prev(L(0,2)); th=L(0,5)
sub=same&(np.random.default_rng(2).random(len(A))<0.3)
def run(nm,v,p0=[0.4,30,0.8,0.08]):
    sp=prev(v)
    f=lambda p:abs(p[0])*resp*N/(N+abs(p[1]))/(1+np.exp(np.clip(-(sp-p[2])/abs(p[3]),-50,50)))
    r=least_squares(lambda p:(f(p)-y)[sub],p0,x_scale=[.1,2,.1,.03],max_nfev=400); pp=f(r.x)
    print(f"  {nm:44s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(r.x,3))
print("logistic cutoff on different saturation variables (start of day)")
run("theta/sat",th/ST,[0.3,20,0.88,0.1])
run("(theta-0.79 pwp)/(sat-0.79 pwp)",(th-0.79*PW)/(ST-0.79*PW),[0.4,30,0.74,0.07])
run("theta/fc  (EPIC: fraction of field capacity)",th/np.maximum(FC,1e-3),[0.4,30,1.0,0.1])
run("(theta-pwp)/(fc-pwp)",(th-PW)/np.maximum(FC-PW,1e-3),[0.4,30,1.0,0.1])
run("(theta-fc)/(sat-fc)",(th-FC)/np.maximum(ST-FC,1e-3),[0.4,30,0.5,0.1])
print(" sample fc,pwp,sat:",[(round(a,3),round(b,3),round(c,3)) for a,b,c in zip(Z['fc'][:6],Z['pwp'][:6],Z['sat'][:6])])
