import numpy as np
A=np.load('/tmp/w/ndata.npz')['A']
def L(k,j): return A[:,14+10*k+j]
no3=[L(k,0) for k in range(4)]; nh4=[L(k,1) for k in range(4)]; no3c=[L(k,2) for k in range(4)]; nh4c=[L(k,3) for k in range(4)]; cf=[L(k,4) for k in range(4)]; th=[L(k,5) for k in range(4)]; sat=[L(k,6) for k in range(4)]; T=[L(k,7) for k in range(4)]
resp=(A[:,12]+A[:,13])*1000
def lookup(y,keys,mask):
    idx=np.zeros(len(y),dtype=np.int64); mult=1
    for kk,edges in keys: idx+=np.digitize(kk,edges)*mult; mult*=(len(edges)+1)
    f_=y[mask]; ii=idx[mask]; mean=np.bincount(ii,weights=f_)/np.maximum(np.bincount(ii),1); p_=mean[ii]
    return 1-((f_-p_)**2).sum()/((f_-f_.mean())**2).sum()
s1=th[0]/sat[0]; s2=th[1]/sat[1]; Te=np.arange(-5,32,3.0); Se=np.array([.3,.45,.6,.7,.8,.9,.95,1.0]); NC=np.array([0.5,2,5,10,25,60]); RE=np.array([0.5,2,5,10,20,50])
print("DENITRIFICATION: flux and fraction of top-2-layer nitrate")
n12=no3[0]+no3[1]; d=A[:,3]; fr=np.where(n12>0.3,d/np.maximum(n12,1e-9),0); mk=n12>0.3
print(" fraction ceilings: T",round(lookup(fr,[(T[0],Te)],mk),3),"| sat1",round(lookup(fr,[(s1,Se)],mk),3),"| T x sat1",round(lookup(fr,[(T[0],Te),(s1,Se)],mk),3),"| sat1 x sat2",round(lookup(fr,[(s1,Se),(s2,Se)],mk),3),
      "| sat1 x NO3c1",round(lookup(fr,[(s1,Se),(no3c[0],NC)],mk),3),"| T x sat1 x NO3c1",round(lookup(fr,[(T[0],Te),(s1,Se),(no3c[0],NC)],mk),3),"| sat1 x resp",round(lookup(fr,[(s1,Se),(resp,RE)],mk),3),"| T x sat1 x resp",round(lookup(fr,[(T[0],Te),(s1,Se),(resp,RE)],mk),3))
print(" flux ceilings:     sat1 x NO3c1",round(lookup(d,[(s1,Se),(no3c[0],NC)],mk),3),"| T x sat1 x NO3c1",round(lookup(d,[(T[0],Te),(s1,Se),(no3c[0],NC)],mk),3),"| T x sat1 x NO3c1 x resp",round(lookup(d,[(T[0],Te),(s1,Se),(no3c[0],NC),(resp,RE)],mk),3))
print("VOLATILIZATION fraction of start-of-day NH4 pool")
tot=sum(nh4); pre=tot+A[:,1]+A[:,2]; v=A[:,2]; fv=np.where(pre>0.3,v/np.maximum(pre,1e-9),0); mv=pre>0.3
print(" T",round(lookup(fv,[(T[0],Te)],mv),3),"| T x sat1",round(lookup(fv,[(T[0],Te),(s1,Se)],mv),3),"| T x NH4c1",round(lookup(fv,[(T[0],Te),(nh4c[0],NC)],mv),3),"| T x sat1 x NH4c1",round(lookup(fv,[(T[0],Te),(s1,Se),(nh4c[0],NC)],mv),3),"| T x sat1 x ratio",round(lookup(fv,[(T[0],Te),(s1,Se),(no3[0]/np.maximum(nh4[0],1e-6),RE)],mv),3))
print(" flux: T x sat1 x NH4pre",round(lookup(v,[(T[0],Te),(s1,Se),(pre,np.array([1,3,10,30,100]))],mv),3))
from scipy.optimize import least_squares
print("---- fitted forms for denitrification flux (all days)")
y=d; s1c=np.clip(s1,0,1.2); ok=np.isfinite(s1c)
def R2(p): return 1-((y[ok]-p[ok])**2).sum()/((y[ok]-y[ok].mean())**2).sum()
c1=no3c[0]; c12=(no3[0]+no3[1])/np.maximum(no3[0]/np.maximum(no3c[0],1e-9)+no3[1]/np.maximum(no3c[1],1e-9),1e-9)
def fit(name,fn,p0):
    r=least_squares(lambda p:(fn(p)-y)[ok],p0,max_nfev=400); print(f" {name:52s} R2 {R2(fn(r.x)):.3f}  params {np.round(r.x,4)}")
fit("P * resp * NO3c/(NO3c+K) * sat^p   (layer 1)",lambda p:p[0]*resp*c1/(c1+abs(p[1]))*s1c**p[2],[1e-3,5,6])
fit("P * resp * NO3c12/(NO3c12+K) * sat1^p  (layers 1-2 conc)",lambda p:p[0]*resp*c12/(c12+abs(p[1]))*s1c**p[2],[1e-3,5,6])
fit("P * resp^a * NO3c^b * sat1^p   (current engine form)",lambda p:p[0]*resp**p[1]*c1**p[2]*s1c**p[3],[1e-3,0.77,0.7,6])
fit("P * resp * NO3c/(NO3c+K) * MMsat(0.22? half h, power n)",lambda p:p[0]*resp*c1/(c1+abs(p[1]))/(1+(abs(p[2])/np.maximum(s1c,1e-3))**p[3]),[1e-3,5,0.5,6])
