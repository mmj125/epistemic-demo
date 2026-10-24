"""Refit of the N stress law on Cycles' own daily plant states (N=0,150,400, 12 sites), odd/even site hold-out (2026-10-21).
factor = 1 - SMAX * clip((R0 - r)/(R0 - R1), 0, 1)^Q, r = above-ground N concentration / critical concentration at total biomass."""
import sys,numpy as np
sys.path.insert(0,'.')
import rhizo_engine as E, run_validation as rv
from scipy.optimize import least_squares
crop=dict(rv.CORN)
A=np.load('/tmp/w/ncurve.npz')["A"]; site,ag,rt,agn,rtn,conc,st,tt,gr,N=A[:,0],A[:,1],A[:,2],A[:,3],A[:,4],A[:,5],A[:,6],A[:,7],A[:,8],A[:,9]
ok=(ag>0.3)&(st>=0)&(rt>0)&(agn>0)
site,ag,rt,agn,st,N=[x[ok] for x in (site,ag,rt,agn,st,N)]
crit=np.array([E.n_critical_pct(b, crop, crop.get("n_stress_crit_floor", E.N_STRESS_CRIT_FLOOR_MGHA)) for b in ag+rt])
r=(agn/(ag*10))/crit; F=1-st/100
def law(p,r): return 1-abs(p[0])*np.clip((p[1]-r)/(p[1]-p[2]),0,1)**abs(p[3])
P0=[E.N_STRESS_SMAX,E.N_STRESS_R0,E.N_STRESS_R1,E.N_STRESS_Q]
odd=(site.astype(int)//2)%2==1
def rep(lab,p,mask):
    out=[]
    for n in (0,150,400):
        k=mask&(N==n); out.append(f"N={n}: Cycles {F[k].mean():.3f} law {law(p,r[k]).mean():.3f} mae {np.abs(law(p,r[k])-F[k]).mean():.3f}")
    print(f"  {lab}: "+" | ".join(out))
print("current constants",np.round(P0,3)); rep("train(odd)",P0,odd); rep("test(even)",P0,~odd)
for wt,lab in ((1,"unweighted"),):
    res=least_squares(lambda p:(law(p,r)-F)[odd],P0,x_scale=[.1,.05,.05,.2])
    print("refit on odd sites",np.round(res.x,3)); rep("train(odd)",res.x,odd); rep("test(even)",res.x,~odd)
    res2=least_squares(lambda p:(law(p,r)-F)[~odd],P0,x_scale=[.1,.05,.05,.2]); print("refit on even sites",np.round(res2.x,3)); rep("train(even)",res2.x,~odd); rep("test(odd)",res2.x,odd)
    res3=least_squares(lambda p:(law(p,r)-F),P0,x_scale=[.1,.05,.05,.2]); print("refit on all",np.round(res3.x,3)); rep("all",res3.x,np.ones(len(F),bool))
