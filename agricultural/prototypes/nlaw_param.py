"""Rebuild phase 4: parametric N-loss laws from Cycles' own states (nlaw_table.py), compared against the HGB ceilings. Held out by site parity."""
import numpy as np, sys
from scipy.optimize import least_squares
z=np.load('/tmp/w/ntable.npz'); T=z['T']; C=list(z['cols']); ix={c:i for i,c in enumerate(C)}; col=lambda n:T[:,ix[n]].astype(np.float64)
tr=(col('site')%2==0); te=~tr
def fit_eval(name,mask,target,terms,p0,n=250000,seed=0):
    """terms(p, cols dict)->prediction; fit in linear space on a subsample of train rows, report held-out daily R2 and site-run annual rms log error."""
    rng=np.random.RandomState(seed); itr=rng.choice(np.where(mask&tr)[0],n,replace=False); ite=np.where(mask&te)[0]
    def sub(i): return {c:T[i,ix[c]].astype(np.float64) for c in C}
    D=sub(itr); y=col(target)[itr]
    r=least_squares(lambda p:terms(p,D)-y,p0,max_nfev=200)
    Dt=sub(ite); p=terms(r.x,Dt); yt=col(target)[ite]
    r2=1-((yt-p)**2).sum()/((yt-yt.mean())**2).sum()
    # annual totals per (site, N, year) over the masked days
    key=(Dt['site']*10+Dt['Nrate']/50)*10000+Dt['yr']; u,inv=np.unique(key,return_inverse=True)
    a=np.bincount(inv,yt); b=np.bincount(inv,p); ok=a>0.05
    rms=np.sqrt(np.mean(np.log((b[ok]+0.05)/(a[ok]+0.05))**2)); ratio=b.sum()/a.sum()
    print(f'{name:34s} held-out daily R2 {r2:.2f}  annual rms log {rms:.2f}  ratio {ratio:.2f}  params {np.round(r.x,3)}',flush=True)
    return r.x
pos=lambda x:np.maximum(x,1e-6)
resp=lambda D:pos(D['som']+D['res'])+1e-3
# --- denitrification
m=col('no3')>0.5
fit_eval('denit D0 NO3,Resp,rel1',m,'denit',lambda p,D:np.exp(p[0])*pos(D['no3'])**p[1]*resp(D)**p[2]*np.clip(D['rel1'],.02,1.2)**p[3],[-5.5,.7,.8,6])
fit_eval('denit D1 +rel mean5',m,'denit',lambda p,D:np.exp(p[0])*pos(D['no3'])**p[1]*resp(D)**p[2]*np.clip(D['rel1_mean5'],.02,1.2)**p[3],[-5.5,.7,.8,6])
fit_eval('denit D2 +rel1^a*mean5^b',m,'denit',lambda p,D:np.exp(p[0])*pos(D['no3'])**p[1]*resp(D)**p[2]*np.clip(D['rel1'],.02,1.2)**p[3]*np.clip(D['rel1_mean5'],.02,1.2)**p[4],[-5.5,.7,.8,3,3])
fit_eval('denit D3 +clay',m,'denit',lambda p,D:np.exp(p[0])*pos(D['no3'])**p[1]*resp(D)**p[2]*np.clip(D['rel1_mean5'],.02,1.2)**p[3]*(D['clay']/20)**p[4],[-5.5,.7,.8,6,0])
fit_eval('denit D4 +clay +soc',m,'denit',lambda p,D:np.exp(p[0])*pos(D['no3'])**p[1]*resp(D)**p[2]*np.clip(D['rel1_mean5'],.02,1.2)**p[3]*(D['clay']/20)**p[4]*(pos(D['soc1'])/1.5)**p[5],[-5.5,.7,.8,6,0,0])
fit_eval('denit D5 no3 layers1-2 only',m,'denit',lambda p,D:np.exp(p[0])*pos(D['no3_1']+D['no3_2'])**p[1]*resp(D)**p[2]*np.clip(D['rel1_mean5'],.02,1.2)**p[3]*(D['clay']/20)**p[4],[-5.5,.7,.8,6,0])
# --- nitrification
m2=col('nh4')>0.05
lg=lambda t,p:1/(1+np.exp(-p*(t-0)))
fit_eval('nit N0 NH4*logistic(T)',m2,'nit',lambda p,D:D['nh4']*p[0]/(1+np.exp(-p[1]*(D['T1']-p[2]))),[.14,.17,17])
fit_eval('nit N1 NH4_1*logistic(T)',m2,'nit',lambda p,D:D['nh4_1']*p[0]/(1+np.exp(-p[1]*(D['T1']-p[2]))),[.14,.17,17])
fit_eval('nit N2 NH4^a*logistic(T)*relF',m2,'nit',lambda p,D:pos(D['nh4'])**p[3]*p[0]/(1+np.exp(-p[1]*(D['T1']-p[2])))*np.clip(D['rel1'],.05,1.2)**p[4],[.14,.17,17,1,0.5])
# --- volatilization
fit_eval('vol V0 NH4_1*exp(T)',m2,'vol',lambda p,D:D['nh4_1']*np.exp(p[0]+p[1]*D['T1']),[-9,.17])
fit_eval('vol V1 NH4_1^a exp(T) ET0',m2,'vol',lambda p,D:pos(D['nh4_1'])**p[2]*np.exp(p[0]+p[1]*D['T1'])*pos(D['et0'])**p[3],[-9,.17,1,.8])
fit_eval('vol V2 +vpd, rel lag',m2,'vol',lambda p,D:pos(D['nh4_1'])**p[2]*np.exp(p[0]+p[1]*D['T1'])*(pos(D['et0'])**p[3])*np.clip(D['rel1_mean5'],.05,1.2)**p[4],[-9,.17,1,.8,0])
print('--- nitrification with product-ratio inhibition')
R=lambda D:pos(D['no3_1'])/pos(D['nh4_1'])
lgT=lambda D,p:1/(1+np.exp(-p[1]*(D['T1']-p[2])))
fit_eval('nit R1 ratio inhibition',m2,'nit',lambda p,D:D['nh4_1']*p[0]*lgT(D,p)/(1+(R(D)/p[3])**p[4]),[.12,.3,9,8,3])
fit_eval('nit R2 +NH4 saturation',m2,'nit',lambda p,D:D['nh4_1']*p[0]*lgT(D,p)/(1+(R(D)/p[3])**p[4])/(1+D['nh4_1']/p[5]),[.12,.3,9,8,3,30])
fit_eval('nit R3 +moisture',m2,'nit',lambda p,D:D['nh4_1']*p[0]*lgT(D,p)/(1+(R(D)/p[3])**p[4])/(1+D['nh4_1']/p[5])*np.clip(D['rel1'],.05,1.0)**p[6]*(1-0.0*D['rel1']),[.12,.3,9,8,3,30,0.0])
