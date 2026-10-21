"""Refit the layer-1 denitrification law on pooled base + irrigated Cycles daily states, odd/even site hold-out (2026-10-21)."""
import sys,numpy as np
sys.path.insert(0,'.')
import cycles_engine_validate as E
from scipy.optimize import least_squares
import denit_mgmt_eval_2026_10_21 as V
B=V.load("base"); I=V.load("irrig")
def feats(D):
    prev=V.prev; sat=D["sat_1"]; bd=np.vectorize(E.sixpool_bulk_density)(sat)
    same=np.zeros(len(sat),bool); same[1:]=(D["site"][1:]==D["site"][:-1])&((D["yeardoy"][1:]-D["yeardoy"][:-1]==1)|((D["yeardoy"][1:]%1000==1)&(D["yeardoy"][:-1]%1000>=365)))
    return dict(y=D["denit"],c=prev(D["no3_1"]),th=prev(D["th_1"]),sat=sat,pwp=D["pwp_1"],fc=D["fc_1"],resp=(D["resp_som"]+D["resp_res"])*1000,rsom=D["resp_som"]*1000,rres=D["resp_res"]*1000,same=same,site=D["site"].astype(int),yr=(D["yeardoy"]//1000).astype(int),cur=D["th_1"])
FB,FI=feats(B),feats(I)
def mk(F,tr=None):
    m=F["same"]&(F["yr"]>=1983)
    return m if tr is None else m&tr
def form(name):
    def f(p,F,sx=None):
        c=F["c"]; s=np.clip((F["th"]-abs(p[3])*F["pwp"])/(F["sat"]-abs(p[3])*F["pwp"]),0,1.5)
        g=1/(1+np.exp(np.clip(-(s-p[4])/abs(p[5]),-50,50)))
        r=F["resp"]
        if name=="som_res": r=abs(p[6])*F["rsom"]+F["rres"]
        if name=="nores": r=F["rsom"]
        return abs(p[0])*r*c/(c+abs(p[1]))*g
    return f
P0=[0.367,31.52,0,0.79,0.736,0.074,1.0]
def sse(f,p,Fs,tr):
    return np.concatenate([(f(p,F)-F["y"])[mk(F,tr)] for F in Fs])
odd=lambda F:(F["site"]%2==1); even=lambda F:(F["site"]%2==0)
def annual(F,pred,tr):
    m=mk(F,tr); n=len(set(zip(F["site"][m],F["yr"][m]))); return pred[m].sum()/n
for name in ("base_form","som_res","nores"):
    f=form(name)
    for lab,fit_sets in (("fit base only",[FB]),("fit base+irrig",[FB,FI])):
        res=least_squares(lambda p:sse(f,p,fit_sets,odd(FB)),P0,x_scale=[.1,10,1,.1,.1,.05,.5],max_nfev=300)
        p=res.x
        # held out (even sites): level and change
        out=[]
        for F in (FB,FI):
            pr=f(p,F); m=mk(F,even(F)); out.append((annual(F,F["y"],even(F)),annual(F,pr,even(F)),1-((F["y"]-pr)[m]**2).sum()/((F["y"][m]-F["y"][m].mean())**2).sum()))
        print(f"{name:10s} {lab:15s} held-out base: Cycles {out[0][0]:.1f} law {out[0][1]:.1f} R2 {out[0][2]:.3f} | irrig: Cycles {out[1][0]:.1f} law {out[1][1]:.1f} R2 {out[1][2]:.3f} | change Cycles {out[1][0]-out[0][0]:+.1f} law {out[1][1]-out[0][1]:+.1f} | p {np.round(p,3)}")

print("== two-layer form: layer 2 gets a fitted share rho of the profile respiration, own saturation, same K, kh, a, s0, sc")
def feats2(D,F):
    prev=V.prev; F=dict(F); F["c2"]=prev(D["no3_2"]); F["th2"]=prev(D["th_2"]); F["sat2"]=D["sat_2"]; F["pwp2"]=D["pwp_2"]; return F
FB2,FI2=feats2(B,FB),feats2(I,FI)
def f2(p,F):
    out=0
    for k,(c,th,sat,pwp,rw) in enumerate(((F["c"],F["th"],F["sat"],F["pwp"],1.0),(F["c2"],F["th2"],F["sat2"],F["pwp2"],abs(p[6])))):
        s=np.clip((th-abs(p[3])*pwp)/(sat-abs(p[3])*pwp),0,1.5); g=1/(1+np.exp(np.clip(-(s-p[4])/abs(p[5]),-50,50)))
        out=out+abs(p[0])*rw*F["resp"]*c/(c+abs(p[1]))*g
    return out
P2=[0.2,31.5,0,0.79,0.736,0.074,0.5]
for lab,sets in (("fit base only",[FB2]),("fit base+irrig",[FB2,FI2])):
    res=least_squares(lambda p:np.concatenate([(f2(p,F)-F["y"])[mk(F,odd(F))] for F in sets]),P2,x_scale=[.1,10,1,.1,.1,.05,.3],max_nfev=300); p=res.x
    out=[]
    for F in (FB2,FI2):
        pr=f2(p,F); m=mk(F,even(F)); out.append((annual(F,F["y"],even(F)),annual(F,pr,even(F)),1-((F["y"]-pr)[m]**2).sum()/((F["y"][m]-F["y"][m].mean())**2).sum()))
    print(f"two-layer {lab:15s} held-out base: Cycles {out[0][0]:.1f} law {out[0][1]:.1f} R2 {out[0][2]:.3f} | irrig: Cycles {out[1][0]:.1f} law {out[1][1]:.1f} R2 {out[1][2]:.3f} | change Cycles {out[1][0]-out[0][0]:+.1f} law {out[1][1]-out[0][1]:+.1f} | p {np.round(p,3)}")
