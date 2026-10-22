# Nitrification moisture form from the literature (DAYCENT, Parton et al. 1996, 2001; supplement of bg-2018-126, Eq. S4)
# against the fitted logistic, on Cycles' own daily layer-1 states with start-of-day NH4 and NO3 (previous day's end state).
# Only k (and, for the ratio term, r0 and q) are refitted; the moisture shape is fixed by the source.
import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']
def L(k,j): return A[:,14+10*k+j]
no3=L(0,0); nh4=L(0,1); th=L(0,5); sat=L(0,6); T=L(0,7); y=A[:,1]
f=np.clip(th/sat,0,1.2)
def fT11(t): t=np.asarray(t,float); return np.where(t<=0,0.0,np.where(t<10,0.0105*t+0.00095*t*t,np.where(t<35,0.032*t-0.12,np.where(t<45,4.5-0.1*t,0.0))))
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
prev=lambda a: np.concatenate([[0],a[:-1]])
NH=prev(nh4); NO=prev(no3); R=NO/np.maximum(NH,1e-9)
rng=np.random.default_rng(0); sub=same&(rng.random(len(A))<0.25)
def dc(w,a,b,c,d):
    w=np.clip(w,c+1e-6,b-1e-6)
    return np.clip(((w-b)/(a-b))**(d*(b-a)/(a-c))*((w-c)/(a-c))**d,0,None)
FW={"logistic (fitted)":lambda p,w:1/(1+np.exp(np.clip((w-p[0])/abs(p[1]),-50,50))),
    "DAYCENT medium":lambda p,w:dc(w,0.60,1.27,0.0012,2.84),
    "DAYCENT sandy":lambda p,w:dc(w,0.55,1.70,-0.007,3.22),
    "Eq. 8 Stockle-Campbell":lambda p,w:np.where(w<0.9,1.111*w,np.maximum(0,10-10*w))}
def r2(pred): return 1-((pred-y)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum()
for nm,fw in FW.items():
    for ratio in (True,False):
        def model(p):
            m=p[0]*fT11(T)*NH*fw(p[3:5],f)
            if ratio: m=m/(1+(R/abs(p[1]))**abs(p[2]))
            return m
        p0=[0.21,8.2,6.1,0.795,0.078]
        res=least_squares(lambda p:(model(p)-y)[sub],p0,x_scale=[.1,2,2,.05,.02],max_nfev=400)
        print(f"{nm:26s} ratio term {str(ratio):5s} R2 {r2(model(res.x)):.4f} k={res.x[0]:.3f}")

# free-form moisture shape: actual / (k fT NH ratio-term), binned by saturation and by relative wetness
base=0.206*fT11(T)*NH/(1+(R/8.2177)**6.1948)
ok=sub&(base>0.02)
ratio=y/np.maximum(base,1e-9)
print("saturation bin   n    median(actual/base)   logistic")
for lo in np.arange(0.2,1.05,0.1):
    m=ok&(f>=lo)&(f<lo+0.1)
    if m.sum()>50: print(f" {lo:.1f}-{lo+0.1:.1f} {m.sum():7d}  {np.median(ratio[m]):.3f}   {1/(1+np.exp((lo+0.05-0.7952)/0.0779)):.3f}")
