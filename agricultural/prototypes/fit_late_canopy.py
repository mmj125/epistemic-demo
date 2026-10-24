"""Fit a stress-accelerated senescence clock to Cycles' own daily canopy (2026-10-14). Teacher-forced: Cycles' thermal time, N stress and water stress
drive the clocks, so the fit is independent of engine errors. canopy = eix/(1+exp(a+b*xclock)+exp(c+d*xsen)); xclock accumulates dtt*N^NP*W^WP
(current engine law, previous-day stress); xsen accumulates dtt*(1+kN*(1-N)+kW*(1-W)). Fit c,d,kN,kW on tuning sites, score canopy RMSE on held-out.
Usage: python3 fit_late_canopy.py"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.')
import rhizo_engine as E, run_validation_multisite as m
from scipy.optimize import least_squares
TT_MAT=1800.0;A,B=6.0,-20.0;EIX=0.99
NP,WP=E.CANOPY_N_POW,E.CANOPY_WATER_POW
def load(site,N):
    rows=[r for r in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')) if r['date'][0]!='#' and r['biomass']!='-999']
    out=[];prev=None;seas=[]
    for r in rows:
        y=r['date'][:4]
        if prev is not None and y!=prev:
            out.append(seas);seas=[]
        prev=y
        seas.append((float(r['thermal_time']),1-float(r['nitrogen_stress'])/100,1-float(r['water_stress'])/100,float(r['radiation_interception'])))
    if seas:out.append(seas)
    return out
def prep(site,N):
    P=[]
    for s in load(site,N):
        s=np.array(s)
        if len(s)<60:continue
        tt=s[:,0];dtt=np.diff(tt,prepend=tt[0]);dtt=np.maximum(dtt,0)
        n=s[:,1];w=s[:,2]
        nprev=np.concatenate([[1.0],n[:-1]]);wprev=np.concatenate([[1.0],w[:-1]])
        xclock=np.cumsum(dtt*nprev**NP*wprev**WP)/TT_MAT
        P.append(dict(tt=tt/TT_MAT,dtt=dtt,n=n,w=w,xclock=xclock,can=s[:,3]))
    return P
def predict(p,par):
    c,d,kN,kW=par
    xsen=np.cumsum(p['dtt']*(1+kN*(1-p['n'])+kW*(1-p['w'])))/TT_MAT
    return EIX/(1+np.exp(A+B*p['xclock'])+np.exp(c+d*xsen))
def resid(par,data,late):
    r=[]
    for p in data:
        msk=p['tt']>=late
        r.append((predict(p,par)-p['can'])[msk])
    return np.concatenate(r)
if __name__=="__main__":
    ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
    tune=[s for s in ALL if s in m.SITES];held=[s for s in ALL if s in m.HELDOUT_SITES]
    D={s:[x for N in (0,150,400) for x in prep(s,N)] for s in ALL}
    Dt=[x for s in tune for x in D[s]];Dh=[x for s in held for x in D[s]]
    LATE=0.4
    base=np.array([-16.0,16.0,0.0,0.0])
    rms=lambda r:float(np.sqrt(np.mean(r**2)))
    print('baseline (engine law, no stress in senescence)  late-canopy RMSE  tuning %.4f  held-out %.4f'%(rms(resid(base,Dt,LATE)),rms(resid(base,Dh,LATE))))
    for label,free in (('refit c,d only',[0,1]),('c,d + kN',[0,1,2]),('c,d + kN + kW',[0,1,2,3])):
        x0=base.copy()
        def f(z):
            par=base.copy();par[free]=z;return resid(par,Dt,LATE)
        sol=least_squares(f,base[free])
        par=base.copy();par[free]=sol.x
        print('%-18s c=%.3f d=%.3f kN=%.3f kW=%.3f   RMSE tuning %.4f held-out %.4f'%(label,*par,rms(resid(par,Dt,LATE)),rms(resid(par,Dh,LATE))))
        if label=='c,d + kN + kW': best=par
    json.dump(dict(par=best.tolist()),open('/tmp/w/late_canopy_fit.json','w'))
    # per-site late-canopy bias before/after on held-out
    print('per held-out site mean(pred-Cycles) late canopy: base -> fit')
    for s in held:
        a=np.concatenate([(predict(p,base)-p['can'])[p['tt']>=LATE] for p in D[s]]);b=np.concatenate([(predict(p,best)-p['can'])[p['tt']>=LATE] for p in D[s]])
        print('  %-13s %+.3f -> %+.3f'%(s,a.mean(),b.mean()))
