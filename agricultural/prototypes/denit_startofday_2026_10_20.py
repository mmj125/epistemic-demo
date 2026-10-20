import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
prev=lambda a: np.concatenate([[0],a[:-1]])
def L(k,j): return A[:,14+10*k+j]
y=A[:,3]; resp=(A[:,12]+A[:,13])*1000; som=A[:,12]*1000; res_=A[:,13]*1000
no3cp=prev(L(0,2)); s1=np.clip(L(0,5)/L(0,6),0,1.2)
m=same
def fn(p,N=no3cp,r=resp,s=s1): return abs(p[0])*r*N/(N+abs(p[1]))*s**abs(p[2])
sub=m&(np.random.default_rng(2).random(len(A))<0.3)
r=least_squares(lambda p:(fn(p)-y)[sub],[0.22,16,4.6],x_scale=[.1,2,1]); p=r.x
pred=fn(p); R2=lambda mk:1-((y-pred)[mk]**2).sum()/((y[mk]-y[mk].mean())**2).sum()
print("params",np.round(p,3),"R2 on all consecutive",round(R2(m),3))
# per N level and per site R2
for n in (0,150,400): print(" N",n,"R2",round(R2(m&(A[:,0]==n)),3),"mean act",y[m&(A[:,0]==n)].mean(),"mean pred",pred[m&(A[:,0]==n)].mean())
ss=[R2(m&(A[:,9]==i)) for i in range(24)]; print(" per-site R2 min/med/max",np.round([min(ss),np.median(ss),max(ss)],2))
# autocorrelation of residual
rs=y-pred; a=rs[1:][same[1:]]; b=rs[:-1][same[1:]]; print(" lag1 resid autocorr",np.corrcoef(a,b)[0,1])
# where is the error mass? by saturation bin and by flux size
print(" share of total squared error by sat bin:")
for lo in np.arange(0.4,1.2,0.1):
    mk=m&(s1>=lo)&(s1<lo+0.1)
    if mk.sum()>500: print(f"  sat {lo:.1f}-{lo+.1:.1f}: n {mk.sum():6d} act {y[mk].mean():.3f} pred {pred[mk].mean():.3f} sse share {((y-pred)[mk]**2).sum()/((y-pred)[m]**2).sum():.2f}")
# rain / infiltration
inf=A[:,6]; dr=A[:,7]
for nm,mk in (("rain day",inf>0.1),("no rain",inf<=0.1)): print(f" {nm}: act {y[m&mk].mean():.3f} pred {pred[m&mk].mean():.3f} R2 {R2(m&mk):.3f}")
# does yesterday's saturation or peak help? use max(s today, s yesterday)
sprev=prev(s1)
for nm,s_ in (("sat today",s1),("sat yesterday",sprev),("max of both",np.maximum(s1,sprev)),("mean of both",(s1+sprev)/2)):
    rr=least_squares(lambda p:(fn(p,s=s_)-y)[sub],[0.22,16,4.6],x_scale=[.1,2,1]); pp=fn(rr.x,s=s_); print(f"  {nm:14s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3))
# respiration variants
for nm,r_ in (("SOM only",som),("residue only",res_),("total",resp),("prev total",prev(resp)),("total + 0.5 residue",resp+0.5*res_)):
    rr=least_squares(lambda p:(fn(p,r=r_)-y)[sub],[0.22,16,4.6],x_scale=[.1,2,1]); pp=fn(rr.x,r=r_); print(f"  resp {nm:20s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3))
print("== all-start-of-day combinations")
def tryit(nm,N,r_,s_,extra=None):
    f_=lambda p:abs(p[0])*r_*N/(N+abs(p[1]))*s_**abs(p[2])
    rr=least_squares(lambda p:(f_(p)-y)[sub],[0.3,20,5],x_scale=[.1,2,1]); pp=f_(rr.x); print(f"  {nm:44s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3)); return rr.x,pp
tryit("N prev, resp today, sat prev",no3cp,resp,sprev)
tryit("N prev, resp prev, sat prev",no3cp,prev(resp),sprev)
tryit("N today, resp today, sat prev",L(0,2),resp,sprev)
tryit("N prev, resp today, sat prev2 (2 days back)",no3cp,resp,prev(sprev))
# prev-day nitrate AFTER today's leaching? try N prev minus nothing; also layer-1 NO3 mass based
pp_,_=tryit("N prev, resp today, sat prev (again)",no3cp,resp,sprev)
print("== start-of-day saturation plus the day's infiltration")
thk=L(0,8); sat1=L(0,6)
def trya(nm,sfun,p0=[0.3,20,5,0.5],xs=[.1,2,1,.2]):
    f_=lambda p:abs(p[0])*resp*no3cp/(no3cp+abs(p[1]))*np.clip(sfun(p[3]),0,1.2)**abs(p[2])
    rr=least_squares(lambda p:(f_(p)-y)[sub],p0,x_scale=xs); pp=f_(rr.x); print(f"  {nm:50s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3))
trya("sprev + a*infil/(thick*sat*1000)",lambda a:sprev+abs(a)*inf/(thk*np.maximum(sat1,.05)*1000))
trya("max(sprev, s_today)",lambda a:np.maximum(sprev,s1))
trya("sprev + a*(s_today-sprev)",lambda a:sprev+a*(s1-sprev))
# drainage out of layer 1 is layer-1 flux? use column 7 drainage (profile?) skip
print("== nitrate dependence with start-of-day saturation")
N=no3cp
def tf(nm,f_,p0,xs):
    rr=least_squares(lambda p:(f_(p)-y)[sub],p0,x_scale=xs,max_nfev=500); pp=f_(rr.x)
    print(f"  {nm:52s} R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3),
      "| R2 by N:",[round(1-((y-pp)[m&(A[:,0]==n)]**2).sum()/((y[m&(A[:,0]==n)]-y[m&(A[:,0]==n)].mean())**2).sum(),2) for n in (0,150,400)]); return rr.x
tf("MM  K resp N/(N+Kh) sprev^n",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*sprev**abs(p[2]),[0.3,20,5],[.1,2,1])
tf("Hill  N^h/(N^h+K^h)",lambda p:abs(p[0])*resp*N**abs(p[3])/(N**abs(p[3])+abs(p[1])**abs(p[3]))*sprev**abs(p[2]),[0.3,20,5,1],[.1,2,1,.2])
tf("resp^a  MM",lambda p:abs(p[0])*np.maximum(resp,1e-6)**abs(p[3])*N/(N+abs(p[1]))*sprev**abs(p[2]),[0.3,20,5,1],[.1,2,1,.2])
tf("resp^a N^b sat^n (engine form)",lambda p:abs(p[0])*np.maximum(resp,1e-6)**abs(p[3])*np.maximum(N,1e-6)**abs(p[1])*sprev**abs(p[2]),[0.05,0.4,5,0.9],[.05,.1,1,.2])
tf("MM + logistic sat",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))/(1+np.exp(np.clip(-(sprev-p[2])/abs(p[3]),-50,50))),[0.2,16,0.8,0.1],[.1,2,.05,.02])
tf("MM + decomp-style sat 1/(1+(h/s)^pw)",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))/(1+(abs(p[2])/np.maximum(sprev,1e-3))**abs(p[3])),[0.3,20,0.8,6],[.1,2,.1,2])
tf("MM x sprev^n x fT(T layer1)",lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*sprev**abs(p[2])*np.exp(p[3]*L(0,7)),[0.3,20,5,0.0],[.1,2,1,.02])
print("== residual structure (N>=150), best form MM resp NO3c_prev sat_prev^n")
mk=m&(A[:,0]>=150)&(y>1e-4)
f_=lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*sprev**abs(p[2])
rr=least_squares(lambda p:(f_(p)-y)[sub&(A[:,0]>=150)],[0.3,20,5],x_scale=[.1,2,1]); pp=f_(rr.x)
lr=np.log(y[mk]/np.maximum(pp[mk],1e-9))
cov={"sat2 prev":prev(np.clip(L(1,5)/L(1,6),0,1.2)),"sat3 prev":prev(np.clip(L(2,5)/L(2,6),0,1.2)),"NO3c2 prev":prev(L(1,2)),"NO3c3 prev":prev(L(2,2)),"T1":L(0,7),"T2":L(1,7),"cf1":L(0,4),"cf2":L(1,4),"thick1":L(0,8),"bd1":L(0,9),"doy":A[:,8],"infil":inf,"drain":dr,"transp":A[:,11],"resp":resp,"resp/SOMresp":res_/np.maximum(resp,1e-9),"NO3c1 prev":N,"sat1 prev":sprev,"sat1 today":s1,"sat change":s1-sprev,"NH4c1":prev(L(0,3)),"year":A[:,10]}
for k,v in cov.items(): print(f"  corr(log act/pred, {k:14s}) {np.corrcoef(lr,v[mk])[0,1]:+.3f}")
print("== per-site fits (N>=150): does the saturation reference differ by site?")
out=[]
for i in range(24):
    ms=sub|(m&(np.random.default_rng(i).random(len(A))<0.5)); ms=ms&(A[:,9]==i)&(A[:,0]>=150)
    if ms.sum()<2000: continue
    f2=lambda p:abs(p[0])*resp*N/(N+21.0)*sprev**abs(p[1])
    r2=least_squares(lambda p:(f2(p)-y)[ms],[0.3,5],x_scale=[.1,1]); pp=f2(r2.x)
    out.append((i,r2.x[0],abs(r2.x[1]),1-((y-pp)[ms]**2).sum()/((y[ms]-y[ms].mean())**2).sum(),L(0,6)[ms].mean(),L(0,8)[ms].mean(),L(0,9)[ms].mean()))
for o in out: print("  site %2d K %.3f n %.2f R2 %.2f  sat1 %.3f thick %.3f bd %.2f"%o)
print(" corr(K, bd) %.2f corr(K, thick) %.2f corr(n,sat) %.2f"%(np.corrcoef([o[1] for o in out],[o[6] for o in out])[0,1],np.corrcoef([o[1] for o in out],[o[5] for o in out])[0,1],np.corrcoef([o[2] for o in out],[o[4] for o in out])[0,1]))
print("== saturation reference: engine Saxton-Rawls sat vs porosity from bulk density")
th1=L(0,5); bd1=L(0,9); satSR=L(0,6)
for nm,sat_ref in (("Saxton-Rawls sat (as before)",satSR),("1 - bd/2.65",1-bd1/2.65),("1 - bd/2.60",1-bd1/2.60),("1 - bd/2.70",1-bd1/2.70)):
    sp=prev(np.clip(th1/sat_ref,0,1.2))
    f3=lambda p:abs(p[0])*resp*N/(N+abs(p[1]))*sp**abs(p[2])
    rr=least_squares(lambda p:(f3(p)-y)[sub],[0.3,20,5],x_scale=[.1,2,1]); pp=f3(rr.x)
    print(f"  {nm:30s} pooled R2 {1-((y-pp)[sub]**2).sum()/((y[sub]-y[sub].mean())**2).sum():.3f}",np.round(rr.x,3),
      " mean ratio sat_ref/SR %.3f"%np.mean(sat_ref/satSR))
print(" site mean of SR sat vs 1-bd/2.65:")
print(np.round([ (L(0,6)[A[:,9]==i].mean(), (1-bd1/2.65)[A[:,9]==i].mean()) for i in range(0,24,3)],3).tolist())
