import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']; y=A[:,1]
def L(k,j): return A[:,14+10*k+j]
no3=[L(k,0) for k in range(4)]; nh4=[L(k,1) for k in range(4)]; nh4c=[L(k,3) for k in range(4)]; cf=[L(k,4) for k in range(4)]; th=[L(k,5) for k in range(4)]; sat=[L(k,6) for k in range(4)]; T=[L(k,7) for k in range(4)]
def r2(p): return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
print("mean nitrif/day",y.mean(),"mean NH4 profile",sum(nh4).mean())
# 1) first order per layer x composite factor
for nl in (1,2,3,4):
    x=sum(cf[k]*nh4[k] for k in range(nl)); k1=(x*y).sum()/(x*x).sum(); print(f"first order x cf, layers 1..{nl}: k={k1:.4f} R2={r2(k1*x):.3f}")
x=sum(nh4); k1=(x*y).sum()/(x*x).sum(); print(f"first order, no env factor: k={k1:.4f} R2={r2(k1*x):.3f}")
x=sum(cf[k]*nh4[k] for k in range(4))
# MM in NH4 concentration
def f(p,nl=4):
    k,K=np.exp(p); return sum(k*cf[j]*nh4[j]*(1/(1+nh4c[j]/K)) for j in range(nl))
for nl in (1,2,4):
    r=least_squares(lambda p:f(p,nl)-y,[np.log(0.1),np.log(10)]); print(f"MM-in-conc, layers 1..{nl}: k={np.exp(r.x[0]):.3f} K={np.exp(r.x[1]):.2f} mg/kg R2={r2(f(r.x,nl)):.3f}")
# power on cf
def g(p): 
    k,q=p; return sum(k*cf[j]**q*nh4[j] for j in range(4))
r=least_squares(lambda p:g(p)-y,[0.1,1.0]); print(f"k cf^q NH4: k={r.x[0]:.3f} q={r.x[1]:.2f} R2={r2(g(r.x)):.3f}")
# subset: days with NH4>1
m=sum(nh4)>1; print("days NH4>1",m.mean())
x2=x[m]; y2=y[m]; k1=(x2*y2).sum()/(x2*x2).sum(); print("R2 on NH4>1 days, first order cf:",1-((y2-k1*x2)**2).sum()/((y2-y2.mean())**2).sum(),k1)
# ratio inhibition check: residual vs NO3/NH4 surface
r_=no3[0]/np.maximum(nh4[0],1e-6); 
for lo,hi in ((0,1),(1,3),(3,6),(6,10),(10,30),(30,1e9)):
    s=m&(r_>=lo)&(r_<hi)
    if s.sum()>200: print(f" NO3/NH4 L1 {lo}-{hi}: n={s.sum()} actual/pred {y[s].sum()/ (k1*x[s]).sum():.2f}")
print("---- by NH4 mg/kg layer 1")
k1=0.1132; p=k1*cf[0]*nh4[0]
for lo,hi in ((0,0.3),(0.3,1),(1,3),(3,10),(10,30),(30,100),(100,1e9)):
    s=(nh4c[0]>=lo)&(nh4c[0]<hi)
    if s.sum()>500: print(f" NH4 {lo}-{hi}: n={s.sum()} actual/pred {y[s].sum()/p[s].sum():.2f}  mean NH4 kg {nh4[0][s].mean():.2f}")
print("---- by N rate"); 
for n in (0,150,400):
    s=A[:,0]==n; print(f" N={n}: actual/pred {y[s].sum()/p[s].sum():.2f}")
print("---- by month")
mo=((A[:,8]-1)//30.5).astype(int)+1
for q in range(1,13):
    s=mo==q; print(f" m{q}: actual/pred {y[s].sum()/p[s].sum():.2f} mean actual {y[s].mean():.3f}")
print("---- other layers' NH4 share"); print([ (nh4[k].mean()) for k in range(4)], "nitrate",[no3[k].mean() for k in range(4)])
print("---- start-of-day pool form")
tot=sum(nh4); pre=tot+y+A[:,2]; m=pre>0.3
frac=np.where(m,y/np.maximum(pre,1e-9),0)
for nm,xx in (("cf L1",cf[0]),("cf L1,2 mean",(cf[0]+cf[1])/2),("cf NH4-weighted",sum(cf[k]*nh4[k] for k in range(4))/np.maximum(tot,1e-9))):
    k_=(xx[m]*frac[m]).sum()/(xx[m]**2).sum(); pr=k_*xx
    print(f" {nm}: k={k_:.4f}  R2 on fraction (NH4pre>0.3) {1-((frac[m]-pr[m])**2).sum()/((frac[m]-frac[m].mean())**2).sum():.3f}; R2 on flux {r2(np.where(m,pr*pre,0)):.3f}")
for lo,hi in ((0,1),(1,3),(3,6),(6,10),(10,30),(30,1e9)):
    s=m&(r_>=lo)&(r_<hi)
    if s.sum()>200: print(f"  NO3/NH4 {lo}-{hi}: frac/(k cf) {frac[s].mean()/(0.1*cf[0][s]).mean():.2f}")
for n in (0,150,400):
    s=m&(A[:,0]==n); print(f"  N={n}: mean frac {frac[s].mean():.3f} mean cf1 {cf[0][s].mean():.3f}")
print("---- what drives the fraction (log-linear, layer-1 concentrations, pre-pool > 1 kg)")
m2=(pre>1)&(frac>1e-4)&(cf[0]>0.02)&(nh4c[0]>0.05)&(no3[0]>0.05)
X=np.c_[np.ones(m2.sum()),np.log(cf[0][m2]),np.log(nh4c[0][m2]),np.log(L(0,2)[m2]),np.log(tot[m2])]
yy=np.log(frac[m2]); b,res,_,_=np.linalg.lstsq(X,yy,rcond=None); print("coef [const, ln cf1, ln NH4c1, ln NO3c1, ln NH4profile]",b.round(3)," R2",1-((yy-X@b)**2).sum()/((yy-yy.mean())**2).sum())
for cols,name in (([0,1],"cf only"),([0,1,3],"cf+NO3c"),([0,1,2],"cf+NH4c"),([0,1,4],"cf+NH4profile"),([0,1,2,3],"cf+NH4c+NO3c")):
    b2=np.linalg.lstsq(X[:,cols],yy,rcond=None)[0]; print(f" {name:16s} coef {b2.round(2)} R2 {1-((yy-X[:,cols]@b2)**2).sum()/((yy-yy.mean())**2).sum():.3f}")
print("---- Michaelis-Menten on pre-pool (kg/ha profile)")
cfw=sum(cf[k]*nh4[k] for k in range(4))/np.maximum(tot,1e-9)
for nm,cc in (("cf L1",cf[0]),("cf NH4-weighted",cfw),("cf L1 ^0.65",cf[0]**0.65)):
    def h(p): V,K=np.exp(p); return V*cc*pre/(K+pre)
    r=least_squares(lambda p:h(p)-y,[np.log(1.0),np.log(20.0)]); print(f" {nm:16s} Vmax={np.exp(r.x[0]):.3f} kg/ha/day K={np.exp(r.x[1]):.1f} kg/ha  R2 {r2(h(r.x)):.3f}")
    # then ratio check
    p_=h(r.x); 
    for lo,hi in ((0,3),(3,10),(10,30),(30,1e9)):
        s=(r_>=lo)&(r_<hi)&(pre>0.3)
        if s.sum()>300: print(f"    NO3/NH4 {lo}-{hi}: actual/pred {y[s].sum()/p_[s].sum():.2f}")
print("---- ceiling of any T x saturation function for the nitrified fraction (binned lookup), pre pool > 1 kg")
mm=pre>1; T1=T[0]; s1=th[0]/np.maximum(sat[0],1e-6)
def lookup_r2(keys):
    idx=np.zeros(len(y),dtype=np.int64); mult=1
    for kk,edges in keys:
        b=np.clip(np.digitize(kk,edges),0,len(edges)); idx+=b*mult; mult*=(len(edges)+1)
    f_=frac[mm]; ii=idx[mm]; sums=np.bincount(ii,weights=f_); cnt=np.bincount(ii); mean=sums/np.maximum(cnt,1); p_=mean[ii]
    return 1-((f_-p_)**2).sum()/((f_-f_.mean())**2).sum()
Te=np.arange(-5,32,2.0); Se=np.arange(0.1,1.0,0.1); Re=np.array([1,3,6,10,30]); Ne=np.array([5,20,60,150])
print(" T only",round(lookup_r2([(T1,Te)]),3)," sat only",round(lookup_r2([(s1,Se)]),3)," T x sat",round(lookup_r2([(T1,Te),(s1,Se)]),3))
print(" T x sat x NO3/NH4 ratio",round(lookup_r2([(T1,Te),(s1,Se),(r_,Re)]),3)," cf1 x ratio",round(lookup_r2([(cf[0],np.arange(0.05,0.9,0.05)),(r_,Re)]),3)," T x sat x NH4 pool",round(lookup_r2([(T1,Te),(s1,Se),(tot,Ne)]),3))
