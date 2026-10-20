import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']; W=np.load('/tmp/w/ndata_wx.npz')
def L(k,j): return A[:,14+10*k+j]
same=np.zeros(len(A),bool); same[1:]=(A[1:,9]==A[:-1,9])&(A[1:,0]==A[:-1,0])&(A[1:,8]-A[:-1,8]==1)
prev=lambda a: np.concatenate([[0],a[:-1]])
v=A[:,2]; nh4c=L(0,3); th=L(0,5); sat=L(0,6); T=L(0,7); wind=W['wind']
rng=np.random.default_rng(3); sub=same&(rng.random(len(A))<0.3)&(wind>0)&(prev(nh4c)>0.01)
def run(name,c,th_,T_):
    c=c[sub];t=th_[sub];T_=T_[sub];w=wind[sub];yy=v[sub]
    fn=lambda p:np.exp(p[0])*np.maximum(c,1e-6)**p[1]*np.maximum(t,.03)**p[2]*w**abs(p[4])*np.exp(p[3]*T_)
    r=least_squares(lambda p:fn(p)-yy,[-11.3,0.8,-1.45,0.15,1.0],x_scale=[1,.1,.1,.01,.1],max_nfev=400)
    print(f" {name:46s} R2 {1-((fn(r.x)-yy)**2).sum()/((yy-yy.mean())**2).sum():.3f}  p {np.round(r.x,4)}  total ratio {fn(r.x).sum()/yy.sum():.3f}")
run("end-of-day NH4 conc, today's theta, T",nh4c,th,T)
run("start-of-day NH4 conc, today's theta, T",prev(nh4c),th,T)
run("start-of-day NH4 conc, prev theta, prev T",prev(nh4c),prev(th),prev(T))
print("---- extra drivers on top of start-of-day form")
pp=W['pp']; rh=(W['rhx']+W['rhn'])/2; sol=W['solar']; tx=W['tx']; tn=W['tn']; ta=(tx+tn)/2
c=prev(nh4c)[sub]; t=th[sub]; Tt=T[sub]; w=wind[sub]; yy=v[sub]
base=lambda p:np.exp(p[0])*np.maximum(c,1e-6)**p[1]*np.maximum(t,.03)**p[2]*w*np.exp(p[3]*Tt)
def fx(name,extra,p0e):
    fn=lambda p:base(p)*extra(p[4:]) 
    r=least_squares(lambda p:fn(p)-yy,[-11.1,0.85,-1.42,0.145]+p0e,x_scale=[1,.1,.1,.01]+[0.1]*len(p0e),max_nfev=400)
    print(f" {name:40s} R2 {1-((fn(r.x)-yy)**2).sum()/((yy-yy.mean())**2).sum():.3f}  p {np.round(r.x,4)}")
rainy=(pp[sub]>0.1).astype(float)
fx("+ rain day indicator",lambda q:np.exp(q[0]*rainy),[-1.0])
fx("+ rain mm",lambda q:np.exp(q[0]*pp[sub]),[-0.1])
fx("+ RH",lambda q:np.exp(q[0]*(rh[sub]-60)),[-0.01])
fx("+ solar",lambda q:np.exp(q[0]*sol[sub]),[0.02])
fx("+ Tair-minus-Tsoil",lambda q:np.exp(q[0]*(ta[sub]-Tt)),[0.05])
fx("+ rain + RH + solar",lambda q:np.exp(q[0]*rainy+q[1]*(rh[sub]-60)+q[2]*sol[sub]),[-1,-0.01,0.02])
fx("+ rain + RH + solar + Tair-Tsoil",lambda q:np.exp(q[0]*rainy+q[1]*(rh[sub]-60)+q[2]*sol[sub]+q[3]*(ta[sub]-Tt)),[-1,-0.01,0.02,0.05])
print("---- ML ceiling for volatilization (start-of-day)")
try:
    from sklearn.ensemble import HistGradientBoostingRegressor as H
    from sklearn.inspection import permutation_importance
    mm=same&(wind>0); idx=np.where(mm)[0]; rng2=np.random.default_rng(5); idx=rng2.choice(idx,200000,replace=False)
    F={"nh4c_prev":prev(nh4c),"nh4_prev":prev(L(0,1)),"no3_prev":prev(L(0,0)),"th":th,"fps":th/sat,"T":T,"wind":wind,"pp":pp,"rh":rh,"solar":sol,"tx":tx,"tn":tn,"doy":A[:,8],"thick":L(0,8),"bd":L(0,9),"cf":L(0,4),"infil":A[:,6],"nh4_2":prev(L(1,1)),"th2":L(1,5),"nit":A[:,1]}
    X=np.column_stack([F[k][idx] for k in F]); yy=v[idx]; n=len(idx); tr=slice(0,150000); te=slice(150000,n)
    mdl=H(max_iter=300).fit(X[tr],yy[tr]); print(" test R2 all features",round(mdl.score(X[te],yy[te]),3))
    pi=permutation_importance(mdl,X[te][:30000],yy[te][:30000],n_repeats=3,random_state=0)
    for k,im in sorted(zip(F,pi.importances_mean),key=lambda z:-z[1])[:10]: print(f"   {k:10s} {im:.3f}")
except Exception as e: print("ML failed",e)
print("---- order of operations")
mass=L(0,9)*L(0,8)*10.0
nit=A[:,1]
for name,cc in (("after nitrification: (NH4_prev - nit)",np.maximum(prev(L(0,1))-nit,0)/mass),("before: NH4_prev",prev(L(0,1))/mass),("mid: NH4_prev - nit/2",np.maximum(prev(L(0,1))-nit/2,0)/mass),("end-of-day after both: NH4_end",L(0,1)/mass)):
    sel=same&(rng.random(len(A))<0.3)&(wind>0)&(cc>0.005)
    c=cc[sel];t=th[sel];Tt=T[sel];w=wind[sel];yy=v[sel]
    fn=lambda p:np.exp(p[0])*np.maximum(c,1e-6)**p[1]*np.maximum(t,.03)**p[2]*w*np.exp(p[3]*Tt)
    r=least_squares(lambda p:fn(p)-yy,[-11.1,0.85,-1.42,0.145],x_scale=[1,.1,.1,.01],max_nfev=300)
    print(f" {name:42s} R2 {1-((fn(r.x)-yy)**2).sum()/((yy-yy.mean())**2).sum():.3f}  p {np.round(r.x,4)}")
print("---- extra terms")
no3c=prev(L(0,2))
sel=same&(rng.random(len(A))<0.3)&(wind>0)&(prev(nh4c)>0.01)&(no3c>0.01)
c=prev(nh4c)[sel];t=th[sel];Tt=T[sel];w=wind[sel];yy=v[sel];n3=no3c[sel];txx=tx[sel];tnn=tn[sel];dd=A[sel,8]
base=lambda p:np.exp(p[0])*np.maximum(c,1e-6)**p[1]*np.maximum(t,.03)**p[2]*w*np.exp(p[3]*Tt)
def fx(name,extra,p0e):
    fn=lambda p:base(p)*extra(p[4:])
    r=least_squares(lambda p:fn(p)-yy,[-11.1,0.85,-1.42,0.145]+p0e,x_scale=[1,.1,.1,.01]+[0.1]*len(p0e),max_nfev=400)
    print(f" {name:34s} R2 {1-((fn(r.x)-yy)**2).sum()/((yy-yy.mean())**2).sum():.3f}  p {np.round(r.x,4)}")
fx("none",lambda q:1.0,[])
fx("NO3 conc power",lambda q:n3**q[0],[-0.1])
fx("tx (air max) exp",lambda q:np.exp(q[0]*txx),[0.01])
fx("NO3 power + tx",lambda q:n3**q[0]*np.exp(q[1]*txx),[-0.1,0.01])
fx("ratio NO3/NH4 power",lambda q:(n3/c)**q[0],[-0.1])
fx("doy seasonal sin",lambda q:np.exp(q[0]*np.sin(2*np.pi*(dd-80)/365)+q[1]*np.cos(2*np.pi*(dd-80)/365)),[0.1,0.1])
tr=A[sel,11]
fx("transpiration exp (canopy proxy)",lambda q:np.exp(q[0]*tr),[-0.1])
fx("transpiration + seasonal",lambda q:np.exp(q[0]*tr+q[1]*np.sin(2*np.pi*(dd-80)/365)+q[2]*np.cos(2*np.pi*(dd-80)/365)),[-0.1,0.1,0.1])
fx("1/(1+tr/a) canopy shelter",lambda q:1/(1+np.maximum(tr,0)/abs(q[0])),[1.0])
print("---- wind exponent fixed at 1, start-of-day concentration (adopt)")
sel=same&(rng.random(len(A))<0.5)&(wind>0)&(prev(nh4c)>0.0)
c=prev(nh4c)[sel];t=th[sel];Tt=T[sel];w=wind[sel];yy=v[sel]
fn=lambda p:np.exp(p[0])*np.maximum(c,1e-6)**p[1]*np.maximum(t,.03)**p[2]*w*np.exp(p[3]*Tt)
r=least_squares(lambda p:fn(p)-yy,[-11.1,0.85,-1.42,0.145],x_scale=[1,.1,.1,.01],max_nfev=400)
print("R2",1-((fn(r.x)-yy)**2).sum()/((yy-yy.mean())**2).sum(),"p",np.round(r.x,4),"ratio",fn(r.x).sum()/yy.sum())
