import numpy as np
A=np.load('/tmp/w/ndata.npz')['A']
def L(k,j): return A[:,14+10*k+j]
no3=L(0,0); nh4=L(0,1); th=L(0,5); sat=L(0,6); T=L(0,7); cf=L(0,4); y=A[:,1]
f=np.clip(th/sat,0,1.2)
def fT11(t): t=np.asarray(t,float); return np.where(t<=0,0.0,np.where(t<10,0.0105*t+0.00095*t*t,np.where(t<35,0.032*t-0.12,np.where(t<45,4.5-0.1*t,0.0))))
r=no3/np.maximum(nh4,1e-9)
pred=0.2774*fT11(T)*nh4/(1+(r/8.196)**6.561)/(1+nh4/391.1)/(1+np.exp(np.clip((f-0.7908)/0.0828,-50,50)))
res=y-pred; print("R2 full",1-(res**2).sum()/((y-y.mean())**2).sum())
# is the series ordered? check consecutive day in same site/N
same=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
print("ordered consecutive frac",same.mean())
m=(pred>0.01)
rr=np.where(m,y/np.maximum(pred,1e-9),np.nan)
print("ratio actual/pred: mean",np.nanmean(rr),"sd",np.nanstd(rr))
# lag-1 autocorrelation of log ratio
lr=np.log(np.where(m&(y>1e-6),y/np.maximum(pred,1e-9),np.nan))
a=lr[1:][same]; b=lr[:-1][same]; ok=np.isfinite(a)&np.isfinite(b); print("lag1 autocorr of log(actual/pred):",np.corrcoef(a[ok],b[ok])[0,1])
# dependence of log ratio on covariates
cov={"infiltration":A[:,6],"drainage":A[:,7],"transp":A[:,11],"SOMresp":A[:,12],"resid resp":A[:,13],"doy":A[:,8],"cf1":cf,"T":T,"fps":f,"nh4":nh4,"no3":no3,"cf2":L(1,4),"fps2":np.clip(L(1,5)/L(1,6),0,1.2),"T2":L(1,7),"nh4_2":L(1,1),"no3_2":L(1,0)}
ok=np.isfinite(lr)
for k,v in cov.items(): print(f" corr(log act/pred, {k:12s}) {np.corrcoef(lr[ok],v[ok])[0,1]:+.3f}")
# ratio vs nitrate change yesterday (fertilizer pulse): nh4 increase
dn=np.zeros_like(nh4); dn[1:]=nh4[1:]-nh4[:-1]
print(" corr with yesterday-to-today NH4 change",np.corrcoef(lr[ok],dn[ok])[0,1])
# by year-position: days since NH4 pulse >20 kg
print("---- timing: which state does the rate see?")
from scipy.optimize import least_squares
v=A[:,2]
def mk(nh4_,no3_,T_,f_):
    def fn(p):
        r_=no3_/np.maximum(nh4_,1e-9)
        return p[0]*fT11(T_)*nh4_/(1+(r_/abs(p[1]))**abs(p[2]))/(1+nh4_/abs(p[5]))/(1+np.exp(np.clip((f_-p[3])/abs(p[4]),-50,50)))
    return fn
def run(name,nh4_,no3_,T_,f_,msk):
    fn=mk(nh4_[msk],no3_[msk],T_[msk],f_[msk]); yy=y[msk]
    r_=least_squares(lambda p:fn(p)-yy,[0.28,8.2,6.5,0.79,0.08,400],x_scale=[.1,2,2,.05,.02,100],max_nfev=300)
    print(f" {name:50s} R2 {1-((fn(r_.x)-yy)**2).sum()/((yy-yy.mean())**2).sum():.3f}",np.round(r_.x,3))
idx=np.arange(len(A)); ok1=np.zeros(len(A),bool); ok1[1:]=same
sub=ok1&(np.random.default_rng(0).random(len(A))<0.25)
prev=lambda a: np.concatenate([[0],a[:-1]])
run("end-of-day states (as used)",nh4,no3,T,f,sub)
run("previous day end-of-day states",prev(nh4),prev(no3),prev(T),prev(f),sub)
run("reconstructed start-of-day (NH4+nit+vol, NO3-nit)",nh4+y+v,np.maximum(no3-y,0),T,f,sub)
run("previous-day NH4/NO3, today's T and saturation",prev(nh4),prev(no3),T,f,sub)
print("---- forms with start-of-day NH4/NO3 (previous-day end state), today's T and saturation; layer 1")
NH=prev(nh4); NO=prev(no3); rr_=NO/np.maximum(NH,1e-9)
msk=sub
def fitg(name,fn,p0,xs):
    r_=least_squares(lambda p:(fn(p)-y)[msk],p0,x_scale=xs,max_nfev=500)
    print(f" {name:60s} R2 {1-((fn(r_.x)-y)[msk]**2).sum()/((y[msk]-y[msk].mean())**2).sum():.4f}",np.round(r_.x,4)); return r_.x
W=lambda ff,p0,s: 1/(1+np.exp(np.clip((ff-p0)/abs(s),-50,50)))
fitg("power ratio, logistic moisture, no ks",lambda p:p[0]*fT11(T)*NH/(1+(rr_/abs(p[1]))**abs(p[2]))*W(f,p[3],p[4]),[0.21,8.2,6.1,0.795,0.078],[.1,2,2,.05,.02])
fitg("HARD cap R, logistic moisture",lambda p:np.minimum(p[0]*fT11(T)*NH*W(f,p[2],p[3]),np.maximum(0,(abs(p[1])*NH-NO)/(1+abs(p[1])))),[0.21,9,0.795,0.078],[.1,2,.05,.02])
fitg("logistic ratio",lambda p:p[0]*fT11(T)*NH*W(rr_,p[1],p[2])*W(f,p[3],p[4]),[0.21,8,1,0.795,0.078],[.1,2,.5,.05,.02])
fitg("power ratio, logistic T (old) instead of Eq 11",lambda p:p[0]/(1+np.exp(-p[5]*(T-p[6])))*NH/(1+(rr_/abs(p[1]))**abs(p[2]))*W(f,p[3],p[4]),[0.21,8.2,6.1,0.795,0.078,0.24,13.4],[.1,2,2,.05,.02,.05,2])
fitg("power ratio, moisture linear (1-fps^n)",lambda p:p[0]*fT11(T)*NH/(1+(rr_/abs(p[1]))**abs(p[2]))*np.clip(1-f**abs(p[3]),0,1),[0.21,8.2,6.1,8.0],[.1,2,2,2])
fitg("power ratio, ratio on NO3/(NO3+NH4) form (same), moisture (1-fps^n)",lambda p:p[0]*fT11(T)*NH/(1+(rr_/abs(p[1]))**abs(p[2]))*np.clip(1-f**abs(p[3]),0,1),[0.21,8.2,6.1,8.0],[.1,2,2,2])
