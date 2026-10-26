"""Shoot partition constant TTf50 against published maize root to shoot ratios (2026-10-26). Published: Amos and Walters 2006 (45 studies): R/S falls from 0.68 at emergence to 0.16 at physiological maturity (128 days after emergence), 0.41 at 24 days, exponential
a + b exp(-k DAE) (constants solved from those three published values); Ordonez et al. 2020 (Iowa, 17 site-years, sampled at maturity): maximum R:S 0.04 to 0.13. Engine: for 12 fresh94 sites (1990 to 2010) the daily growth GB is recovered from the aboveground
increment, the shoot share is recomputed with each TTf50 (SI Eq. 8, fsti 0.45, fstf 0.95), root biomass is root_retained_frac (0.6) of the root share; R/S by days after emergence (emergence at TTf 65/1800). Usage: python3 partition_rs_2026_10_26.py"""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation as rv, rhizo_engine as E, run_validation_multisite as m
from scipy.optimize import brentq, least_squares
F=json.load(open('sitesets/fresh94.json')); ks=sorted(F)[::8][:12]; SEAS=[]
for site in ks:
    lat,lon=F[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    crop=dict(rv.CORN); crop["lat_deg"]=cl
    for l in [0]: pass
    def ml():
        L=[]
        for l in soil:
            h=m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC); L.append(dict(thick=l["thick"],fc=h["fc"],pwp=h["pwp"],sat=h["sat"],theta=h["pwp"]+m.INITIAL_MOISTURE_FRACTION*(h["fc"]-h["pwp"]),ksat_mm_day=h["ksat_mm_day"],psi_e_kpa=h["psi_e_kpa"],B=h["B"]))
        return L
    crop["make_layers"]=ml
    kw=E.standard_kwargs(soil,150); kw["record_history"]=True
    res=E.simulate_continuous({y:wx[y] for y in wx if 1988<=y<=2010},crop,carry_n=True,**kw)
    for y,r in res.items():
        if y<1990: continue
        H=r.get("history") or []
        if len(H)<100: continue
        ttf=np.array([h["ttf"] for h in H]); ag=np.array([h["ag_mg_ha"] for h in H],float)
        SEAS.append((ttf,ag))
print(len(SEAS),"seasons")
# published R/S curve constants from the three values
def solve():
    f=lambda p:[p[0]+p[1]-0.68,p[0]+p[1]*np.exp(-24*p[2])-0.41,p[0]+p[1]*np.exp(-128*p[2])-0.16]
    s=least_squares(f,[0.1,0.58,0.03]); return s.x
a,b,k=solve(); print("published R/S = %.3f + %.3f exp(-%.4f DAE)"%(a,b,k),"residuals",np.round(np.array([a+b-0.68,a+b*np.exp(-24*k)-0.41,a+b*np.exp(-128*k)-0.16]),3))
sf=lambda t,t50:0.45+0.5/(1+(t50/np.maximum(t,1e-6))**4)
def curve(t50,rr=0.6):
    DAE=np.arange(10,129,6); out=[]
    for ttf,ag in SEAS:
        d=np.diff(ag,prepend=0.0); fs0=sf(ttf,0.42); gb=np.where(fs0>0,d/fs0,0.0); fs=sf(ttf,t50); S=np.cumsum(gb*fs); R=rr*np.cumsum(gb*(1-fs))
        em=np.argmax(ttf>=65/1800.0); row=[]
        for dae in DAE:
            i=em+dae
            row.append(R[i]/S[i] if i<len(S) and S[i]>0.02 else np.nan)
        out.append(row)
    return DAE,np.nanmean(np.array(out,float),axis=0)
pub=lambda dae:a+b*np.exp(-k*dae)
print("TTf50 | R/S engine at DAE 24, 60, 90, 128 | rms against the published curve (DAE 10 to 128), rr 0.6 and rr 1.0")
for t50 in (0.15,0.25,0.32,0.42,0.50,0.60,0.75,0.90):
    DAE,c=curve(t50); DAE,c1=curve(t50,1.0); ok=~np.isnan(c)
    print(f" {t50:.2f} | "+" ".join(f"{c[list(DAE).index(d)]:.2f}" for d in (22,58,88,124))+f" | {np.sqrt(np.mean((c[ok]-pub(DAE[ok]))**2)):.3f} | {np.sqrt(np.mean((c1[ok]-pub(DAE[ok]))**2)):.3f}")
print("published at 22, 58, 88, 124:",[round(pub(d),2) for d in (22,58,88,124)])
best=min(np.arange(0.05,1.2,0.01),key=lambda t:np.sqrt(np.nanmean((curve(t)[1]-pub(curve(t)[0]))**2))); print("best TTf50 (rr 0.6):",round(float(best),2))
