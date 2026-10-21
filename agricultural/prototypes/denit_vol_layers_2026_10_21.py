import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']; Z=np.load('/tmp/w/site_l1.npz'); W=np.load('/tmp/w/ndata_wx.npz')
prev=lambda a: np.concatenate([[0],a[:-1]])
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
def L(k,j): return A[:,14+10*k+j]
site=A[:,9].astype(int); PW=Z['pwp'][site]
y=A[:,3]; resp=(A[:,12]+A[:,13])*1000
sub=same&(np.random.default_rng(2).random(len(A))<0.3)
def law(i,K,kh=31.5,a=0.79,s0=0.736,sc=0.074):
    N=prev(L(i,2)); th=L(i,5); st=L(i,6)
    s=np.clip(prev((th-a*PW)/np.maximum(st-a*PW,1e-6)),0,1.5)
    return K*resp*N/(N+kh)/(1+np.exp(np.clip(-(s-s0)/sc,-50,50)))
def run(nm,f,p0):
    r=least_squares(lambda p:(f(p)-y)[sub],p0,max_nfev=300,x_scale=[.1]*len(p0)); pp=f(r.x)
    print(f" {nm:48s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(r.x,3))
print("DENITRIFICATION: layer 1 plus deeper layers, own K per extra layer (same shape)")
run("layer 1",lambda p:law(0,p[0]),[0.37])
run("layer 1 + layer 2 (K2 free)",lambda p:law(0,p[0])+law(1,p[1]),[0.37,0.1])
run("layers 1-3 (K2,K3 free)",lambda p:law(0,p[0])+law(1,p[1])+law(2,p[2]),[0.37,0.1,0.05])
run("layers 1-4",lambda p:law(0,p[0])+law(1,p[1])+law(2,p[2])+law(3,p[3]),[0.37,0.1,0.05,0.02])
run("all layers, one K",lambda p:sum(law(i,p[0]) for i in range(4)),[0.3])
# volatilization from deeper layers
v=A[:,2]; wind=W['wind']
sv=same&(np.random.default_rng(3).random(len(A))<0.3)&(wind>0)
def vol(i,lnA,B,C,E):
    c=prev(L(i,3)); th=L(i,5); T=L(i,7)
    return np.exp(lnA)*np.maximum(c,1e-6)**B*np.maximum(th,.03)**C*wind*np.exp(E*T)*(c>0)
def runv(nm,f,p0):
    r=least_squares(lambda p:(f(p)-v)[sv],p0,max_nfev=300,x_scale=[1,.1,.1,.01]+[1]*(len(p0)-4)); pp=f(r.x)
    print(f" {nm:48s} R2 {1-((v-pp)[sv]**2).sum()/((v[sv]-v[sv].mean())**2).sum():.3f}",np.round(r.x,3))
print("VOLATILIZATION: layer 1 plus layer 2")
runv("layer 1",lambda p:vol(0,*p[:4]),[-11.29,0.86,-1.46,0.146])
runv("layer 1 + layer 2 (scale free)",lambda p:vol(0,*p[:4])+np.exp(p[4])*vol(1,*p[:4]),[-11.29,0.86,-1.46,0.146,-3.0])
