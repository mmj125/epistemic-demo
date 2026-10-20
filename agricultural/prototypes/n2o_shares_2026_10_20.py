import numpy as np
A=np.load('/tmp/w/ndata.npz')['A']
def L(k,j): return A[:,14+10*k+j]
den=A[:,3]; n2od=A[:,5]; nit=A[:,1]; n2on=A[:,4]
m=den>1e-4
r=n2od[m]/den[m]; print("N2O_denit/denit: mean %.4f sd %.4f; pooled ratio %.4f"%(r.mean(),r.std(),n2od[m].sum()/den[m].sum()))
s=np.clip(L(0,5)/L(0,6),0,1.2)[m]
for lo in np.arange(0.3,1.2,0.1):
    k=(s>=lo)&(s<lo+0.1)
    if k.sum()>200: print(f" sat {lo:.1f}: n {k.sum():6d} ratio {n2od[m][k].sum()/den[m][k].sum():.4f}")
T=L(0,7)[m]
for lo in range(0,30,5):
    k=(T>=lo)&(T<lo+5)
    if k.sum()>200: print(f" T {lo}: ratio {n2od[m][k].sum()/den[m][k].sum():.4f}")
mn=nit>1e-4; print("N2O_nit/nit pooled %.4f"%(n2on[mn].sum()/nit[mn].sum()), "sd of ratio %.4f"%(n2on[mn]/nit[mn]).std())
for n in (0,150,400):
    k=m&(A[:,0]==n); print(" N",n,"ratio denit %.4f"%(n2od[k].sum()/den[k].sum()))
print("== ratio vs layer-1 nitrate concentration (start-of-day) and saturation")
prev=lambda a: np.concatenate([[0],a[:-1]])
no3c=prev(L(0,2))[m]; sat_=np.clip(L(0,5)/L(0,6),0,1.2)[m]; dd=den[m]; nn=n2od[m]
cb=[0,2,5,10,20,40,80,1e9]; sb=[0,0.5,0.65,0.8,1.3]
print("          sat:"+"".join(f"{sb[j]:>9}-{sb[j+1]:<5}" for j in range(len(sb)-1)))
for i in range(len(cb)-1):
    row=[]
    for j in range(len(sb)-1):
        k=(no3c>=cb[i])&(no3c<cb[i+1])&(sat_>=sb[j])&(sat_<sb[j+1])
        row.append(f"{nn[k].sum()/dd[k].sum():.3f}({k.sum():>6})" if k.sum()>200 else "     -       ")
    print(f" NO3c {cb[i]:>3}-{cb[i+1] if cb[i+1]<1e8 else 'inf':<4}"+"  ".join(row))
print("== fits for the N2O share of denitrification")
from scipy.optimize import least_squares
sp=prev(np.clip(L(0,5)/L(0,6),0,1.2))[m]
def R2(p): return 1-((nn-p)**2).sum()/((nn-nn.mean())**2).sum()
def fit(nm,f,p0,xs):
    r=least_squares(lambda p:f(p)-nn,p0,x_scale=xs,max_nfev=300); print(f" {nm:48s} R2 {R2(f(r.x)):.3f}",np.round(r.x,4)); return r.x
fit("constant share",lambda p:p[0]*dd,[0.15],[.1])
fit("A c^p exp(-q s)",lambda p:dd*p[0]*np.maximum(no3c,1e-3)**p[1]*np.exp(-p[2]*sp),[0.1,0.3,1.0],[.05,.1,.3])
fit("A c/(c+k) exp(-q s)",lambda p:dd*p[0]*no3c/(no3c+abs(p[1]))*np.exp(-p[2]*sp),[0.4,20,1.0],[.1,5,.3])
fit("A c/(c+k) (1 - b s)",lambda p:dd*p[0]*no3c/(no3c+abs(p[1]))*np.clip(1-p[2]*sp,0,1),[0.4,20,0.5],[.1,5,.2])
fit("A c/(c+k) s^-q",lambda p:dd*p[0]*no3c/(no3c+abs(p[1]))*np.maximum(sp,.1)**(-abs(p[2])),[0.2,20,1.0],[.1,5,.3])
print("== N2O share of nitrification")
mn=nit>1e-3; nn2=n2on[mn]; nt=nit[mn]; sn_=np.clip(L(0,5)/L(0,6),0,1.2)[mn]; Tn=L(0,7)[mn]
print(" pooled",nn2.sum()/nt.sum())
for lo in np.arange(0.2,1.2,0.1):
    k=(sn_>=lo)&(sn_<lo+0.1)
    if k.sum()>200: print(f"  sat {lo:.1f}: ratio {nn2[k].sum()/nt[k].sum():.4f} n {k.sum()}")
for lo in range(0,30,5):
    k=(Tn>=lo)&(Tn<lo+5)
    if k.sum()>200: print(f"  T {lo}: ratio {nn2[k].sum()/nt[k].sum():.4f}")
sn2=np.clip(L(0,5)/L(0,6),0,1.2)[mn]
fit_=lambda nm,f,p0,xs: (lambda r:(print(f" {nm:44s} R2 {1-((nn2-f(r.x))**2).sum()/((nn2-nn2.mean())**2).sum():.3f}",np.round(r.x,4)),r.x)[1])(least_squares(lambda p:f(p)-nn2,p0,x_scale=xs,max_nfev=300))
fit_("constant",lambda p:p[0]*nt,[0.004],[.001])
fit_("a + b max(0,s-s0)",lambda p:nt*(abs(p[0])+abs(p[1])*np.clip(sn2-p[2],0,None)),[0.003,0.3,0.7],[.001,.1,.05])
fit_("a + b max(0,s-s0)^2",lambda p:nt*(abs(p[0])+abs(p[1])*np.clip(sn2-p[2],0,None)**2),[0.003,1.0,0.7],[.001,.3,.05])
fit_("a + b/(1+exp(-(s-s0)/w))",lambda p:nt*(abs(p[0])+abs(p[1])/(1+np.exp(np.clip(-(sn2-p[2])/abs(p[3]),-50,50)))),[0.003,0.1,0.85,0.05],[.001,.05,.05,.02])
