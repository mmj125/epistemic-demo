"""DAYCENT denitrification (Parton et al. 2001, Del Grosso 2000; bg-2018-126 supplement Eqs S7, S9, S10) against Cycles' daily layer-1
denitrification: D = min(1.15 NO3^0.57, 0.1 CO2^1.3) * f(WFPS), NO3 in mg/kg, CO2 in g C/ha/d, D in g N/ha/d. The nitrate and
respiration functions are fixed as published; only the saturation function (its typeset form is garbled in the supplement) is fitted, two parameters.
Odd/even site hold-out as in denit_refit_2026_10_21.py."""
import sys,numpy as np
sys.path.insert(0,'.')
import denit_mgmt_eval_2026_10_21 as V
from scipy.optimize import least_squares
exec(open('denit_refit_2026_10_21.py').read().split("FB,FI=")[0].split("B=V.load")[0])
B=V.load("base")
import cycles_engine_validate as E
def feats(D):
    prev=V.prev; sat=D["sat_1"]
    same=np.zeros(len(sat),bool); same[1:]=(D["site"][1:]==D["site"][:-1])&((D["yeardoy"][1:]-D["yeardoy"][:-1]==1)|((D["yeardoy"][1:]%1000==1)&(D["yeardoy"][:-1]%1000>=365)))
    return dict(y=D["denit"],c=prev(D["no3_1"]),th=prev(D["th_1"]),sat=sat,resp=(D["resp_som"]+D["resp_res"])*1000,same=same,site=D["site"].astype(int),yr=(D["yeardoy"]//1000).astype(int),cur=D["th_1"])
F=feats(B); m0=F["same"]&(F["yr"]>=1983)
S=np.clip(F["th"]/F["sat"],0,1.2)
c=np.maximum(F["c"],1e-6); co2=np.maximum(F["resp"]*1.0,1e-9)   # resp is kg C/ha/d (x1000 of Mg?) check scale below
print("median c mg/kg",np.median(c[m0]),"median resp (kg C/ha/d)",np.median(co2[m0]),"median denit kg/ha/d",np.median(F["y"][m0]))
odd=F["site"]%2==1; even=~odd
def dtot(p,cunit=1.0,cscale=1.0):
    fn=1.15*c**0.57; fc=0.1*(co2*cscale)**1.3                       # g N/ha/d
    w=0.5+np.arctan(0.6*np.pi*(10*S-p[0]*10))/np.pi if False else 1/(1+np.exp(np.clip(-(S-p[0])/abs(p[1]),-50,50)))
    return np.minimum(fn,fc)*w/1000.0                                 # kg N/ha/d
def r2(pred,msk): return 1-((F["y"]-pred)[msk]**2).sum()/((F["y"][msk]-F["y"][msk].mean())**2).sum()
for cs,lab in ((1.0,"CO2 as kg C/ha/d"),(1000.0,"CO2 as g C/ha/d (x1000)")):
    res=least_squares(lambda p:(dtot(p,cscale=cs)-F["y"])[m0&odd],[0.7,0.07],x_scale=[.1,.05],max_nfev=200)
    pr=dtot(res.x,cscale=cs); mk=m0&even
    n=len(set(zip(F["site"][mk],F["yr"][mk])))
    print(f"{lab:28s} p {np.round(res.x,3)} held-out R2 {r2(pr,mk):.3f}  annual Cycles {F['y'][mk].sum()/n:.1f} law {pr[mk].sum()/n:.1f} kg N/ha")

print("--- grid over saturation midpoint/width, free amplitude (best case for the published nitrate and respiration shapes)")
def best(cs,use):
    out=None
    for mid in np.arange(0.5,1.0,0.05):
        for wd in (0.03,0.05,0.08,0.12):
            w=1/(1+np.exp(np.clip(-(S-mid)/wd,-50,50)))
            fn=1.15*c**0.57; fc=0.1*(co2*cs)**1.3
            base={"min":np.minimum(fn,fc),"nitrate only":fn,"resp only":fc}[use]*w/1000.0
            a=(base[m0&odd]*F["y"][m0&odd]).sum()/max((base[m0&odd]**2).sum(),1e-30)
            pr=a*base; sc=r2(pr,m0&odd)
            if out is None or sc>out[0]: out=(sc,mid,wd,a,r2(pr,m0&even))
    return out
for cs,lab in ((1.0,"CO2 kg C/ha/d"),(1000.0,"CO2 g C/ha/d")):
    for use in ("min","nitrate only","resp only"):
        o=best(cs,use); print(f"{lab:16s} {use:13s} train R2 {o[0]:.3f} mid {o[1]:.2f} width {o[2]:.2f} amp x{o[3]:.2f} held-out R2 {o[4]:.3f}")

print("--- like for like on the same rows (odd train, even test), saturation as the engine reads it: s = (theta - a pwp)/(sat - a pwp)")
Dd=V.load("base")
pwp=Dd["pwp_1"]; th=V.prev(Dd["th_1"]); sat=Dd["sat_1"]
a_=0.79; s_=np.clip((th-a_*pwp)/(sat-a_*pwp),0,1.5)
cm=c; rsp=F["resp"]
def engine_law(): 
    P=E.DENIT_SD
    g=1/(1+np.exp(np.clip(-(s_-P["s0"])/P["sc"],-50,50)))
    return P["K"]*rsp*cm/(cm+P["kh"])*g/1.0
pe=engine_law(); print(f"engine law as shipped (K {E.DENIT_SD['K']}, kh {E.DENIT_SD['kh']}): even-site R2 {r2(pe,m0&even):.3f}, odd {r2(pe,m0&odd):.3f}")
def fitlaw(name,base_fn):
    best=None
    for s0 in np.arange(0.5,1.0,0.04):
        for sc in (0.03,0.05,0.074,0.1,0.15):
            g=1/(1+np.exp(np.clip(-(s_-s0)/sc,-50,50))); b=base_fn()*g
            amp=(b[m0&odd]*F["y"][m0&odd]).sum()/max((b[m0&odd]**2).sum(),1e-30); pr=amp*b
            sc_=r2(pr,m0&odd)
            if best is None or sc_>best[0]: best=(sc_,s0,sc,amp,r2(pr,m0&even))
    print(f"{name:44s} train R2 {best[0]:.3f} s0 {best[1]:.2f} sc {best[2]:.3f} amp x{best[3]:.3g} held-out R2 {best[4]:.3f}")
fitlaw("DAYCENT min(NO3^0.57, CO2^1.3), CO2 kg C",lambda: np.minimum(1.15*cm**0.57,0.1*rsp**1.3)/1000)
fitlaw("DAYCENT nitrate^0.57 x CO2^1.3 (product)",lambda: 1.15*cm**0.57*0.1*rsp**1.3/1000)
fitlaw("engine form c/(c+kh) x resp, kh fixed 31.5",lambda: rsp*cm/(cm+31.52))
fitlaw("engine form, nitrate MM kh 5 (DAYCENT-like low)",lambda: rsp*cm/(cm+5.0))

print("--- nitrate exponent free (DAYCENT min form, CO2 exponent 1.3 fixed), same split")
for pw in (0.57,0.8,1.0,1.2):
    fitlaw(f"DAYCENT min, nitrate exponent {pw}",lambda pw=pw: np.minimum(1.15*cm**pw,0.1*rsp**1.3)/1000)
for pw in (0.57,0.8,1.0):
    fitlaw(f"nitrate^{pw} x resp (linear in carbon)",lambda pw=pw: cm**pw*rsp)
