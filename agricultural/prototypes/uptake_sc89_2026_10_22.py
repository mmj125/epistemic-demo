"""Stockle and Campbell 1989 Eq. 17 and 18 (Michaelis-Menten uptake per root length with the Campbell temperature function, optimum 25 C) against Cycles' daily
uptake (2026-10-22). L per layer = root biomass x depth weight (exponential, scale h); rhizosphere concentration = bulk solution concentration (first-order case)."""
import numpy as np
from scipy.optimize import least_squares
A=np.load('/tmp/w/up2.npz')["A"]
site,N,year,doy,U,pn,ag,rt,st,tr,Ts=A[:,:11].T
def L_(i,k): return A[:,11+7*i+k]
nl=4
no3=[L_(i,0) for i in range(nl)]; nh4=[L_(i,1) for i in range(nl)]; th=[L_(i,2) for i in range(nl)]; thick=[L_(i,3) for i in range(nl)]; bd=[L_(i,4) for i in range(nl)]
F=1-st/100
same=np.zeros(len(U),bool); same[1:]=(site[1:]==site[:-1])&(N[1:]==N[:-1])&(year[1:]==year[:-1])&(doy[1:]-doy[:-1]==1)
ok=(U>0)&(rt>0)&(ag>0.2)
def fT(T,To=25.0): return np.clip((2*(T+4)**2*(To+4)**2-(T+4)**4)/(To+4)**4,0,None)
def sc89(p,Tfun=True):
    k,K,h=abs(p[0]),abs(p[1]),abs(p[2]); z=np.zeros(len(U)); parts=[]; tot=np.zeros(len(U))
    for i in range(nl):
        zm=z+thick[i]/2; w=np.exp(-zm/max(h,0.05))*thick[i]; parts.append(w); tot=tot+w; z=z+thick[i]
    s=0
    for i in range(nl):
        csol=(no3[i]+nh4[i])*bd[i]/np.maximum(th[i],0.02)   # mg N per L solution
        s=s+(parts[i]/np.maximum(tot,1e-9))*csol/(csol+K)
    return k*rt*s*(fT(Ts) if Tfun else 1.0)
def pool_cap(p):
    pool=sum((no3[i]+nh4[i])*bd[i]*thick[i]*10 for i in range(nl)); return abs(p[0])*pool
odd=(site.astype(int)%2==1)
def daily(name,f,p0,xs,mask):
    tr_=mask&odd; te=mask&~odd
    r=least_squares(lambda p:(f(p)-U)[tr_],p0,x_scale=xs,max_nfev=400); pr=f(r.x)
    R2=lambda mk:1-((U-pr)[mk]**2).sum()/((U[mk]-U[mk].mean())**2).sum()
    print(f"  {name:36s} params {np.round(r.x,4)}  daily R2 train {R2(tr_):.3f} test {R2(te):.3f}"); return r.x
for lab,mask in (("N-short days (factor < 0.6)",ok&(F<0.6)),("unstressed days (factor > 0.9)",ok&(F>0.9)),("all alive days",ok)):
    print(lab,"n =",mask.sum())
    daily("SC89 Eq.17 x Eq.18 (fitted Umax L, K, h)",sc89,[0.3,1.0,0.3],[0.1,0.5,0.1],mask)
    daily("SC89 without temperature function",lambda p:sc89(p,False),[0.3,1.0,0.3],[0.1,0.5,0.1],mask)
    daily("pool cap k*pool (engine form)",pool_cap,[0.03],[0.01],mask)
# weekly on N-short stretches
st_=[j for j in range(1,len(U)-7) if all(same[j:j+7]) and (F[j:j+7]<0.6).all() and (U[j:j+7]>=0).all() and (rt[j:j+7]>0).all()]
sel=[];last=-10
for j in st_:
    if j>=last+7: sel.append(j); last=j
sel=np.array(sel); print("weekly stretches on N-short days:",len(sel))
p=daily.__defaults__ if False else None
Us=np.array([U[j:j+7].sum() for j in sel]); S_=site[sel].astype(int); trw=S_%2==1
def weekly(name,f,p0,xs):
    fv=lambda p:np.array([f(p)[j:j+7].sum() for j in sel])
    r=least_squares(lambda p:(fv(p)-Us)[trw],p0,x_scale=xs,max_nfev=200); pr=fv(r.x)
    R2=lambda mk:1-((Us-pr)[mk]**2).sum()/((Us[mk]-Us[mk].mean())**2).sum()
    print(f"  {name:36s} weekly R2 train {R2(trw):.3f} test {R2(~trw):.3f}")
weekly("SC89 Eq.17 x Eq.18",sc89,[0.3,1.0,0.3],[0.1,0.5,0.1])
weekly("pool cap",pool_cap,[0.03],[0.01])
