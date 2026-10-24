"""Soil temperature: the engine's fitted lag table against a heat-conduction model with a published-range diffusivity (2026-10-20).
Cycles daily soil_temperature.1..N (dailyEnviron.csv), 24 sites, N=0, years 1982 on. Models: BASE = engine's per-layer lag filter and gain (SIXPOOL_ML_TEMP_TABLE);
HC(D) = implicit 1-D heat conduction, surface node = daily mean air temperature, constant temperature (long-term mean) at 3 m, thermal diffusivity D (m2/day), layers averaged by thickness.
Prints rms error (C) by layer and by season for each model."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def hc(air,D,thick,dz=0.05,zmax=3.0,tdeep=None):
    """D: a number, or (D_top, D_deep, z_switch_m)."""
    n=int(zmax/dz); tdeep=np.mean(air[:365]) if tdeep is None else tdeep
    z=(np.arange(n)+0.5)*dz
    Dn=np.full(n,float(D)) if not isinstance(D,tuple) else np.where(z<D[2],D[0],D[1])
    Di=np.concatenate([[Dn[0]],0.5*(Dn[1:]+Dn[:-1]),[Dn[-1]]])      # interface diffusivities (n+1)
    rl=Di[:-1]/dz**2; ru=Di[1:]/dz**2
    a=-rl.copy(); c=-ru.copy(); b=1+rl+ru
    a[0]=0.0; c[-1]=0.0; b[0]=1+ru[0]+2*rl[0]; b[-1]=1+rl[-1]+2*ru[-1]
    cp=np.zeros(n)
    for i in range(n): cp[i]=c[i]/b[i] if i==0 else c[i]/(b[i]-a[i]*cp[i-1])
    T=np.full(n,tdeep); out=[]
    edges=np.concatenate([[0],np.cumsum(thick)]); idx=[np.where((z>=edges[k])&(z<edges[k+1]))[0] for k in range(len(thick))]
    for t in air:
        d=T.copy(); d[0]+=2*rl[0]*t; d[-1]+=2*ru[-1]*tdeep
        dp=np.zeros(n)
        for i in range(n): dp[i]=d[i]/b[i] if i==0 else (d[i]-a[i]*dp[i-1])/(b[i]-a[i]*cp[i-1])
        T[-1]=dp[-1]
        for i in range(n-2,-1,-1): T[i]=dp[i]-cp[i]*T[i+1]
        out.append([T[ix].mean() if len(ix) else np.nan for ix in idx])
    return np.array(out)
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    En=rd(d+"dailyEnviron.csv"); shutil.rmtree(d,ignore_errors=True)
    nl=len([k for k in En[0] if k.startswith('soil_temperature.')]); thick=[l["thick"] for l in soil][:nl]
    air=np.array([(float(r['min_air_temperature'])+float(r['max_air_temperature']))/2 for r in En]); mo=np.array([int(r['date'][5:7]) for r in En]); yr=np.array([int(r['date'][:4]) for r in En])
    cyc=np.array([[float(r[f'soil_temperature.{k+1}']) for k in range(nl)] for r in En])
    # BASE
    zmid=np.cumsum(thick)-np.array(thick)/2; base=np.zeros((len(air),nl)); tl=[None]*nl; tm=[None]*nl
    for i,x in enumerate(air):
        for k in range(nl):
            kk,g=E.sixpool_ml_temp_params(zmid[k])
            if tl[k] is None: tl[k]=x; tm[k]=E.SIXPOOL_ML_TMEAN_INIT
            tl[k]+=kk*(x-tl[k]); tm[k]+=(x-tm[k])/365.0; base[i,k]=tm[k]+g*(tl[k]-tm[k])
    res={"BASE":base}
    for D in (0.05,0.08,0.12):
        E.SOILT_DIFFUSIVITY_M2_DAY=D; h=E.hc_make(thick,E.SIXPOOL_ML_TMEAN_INIT)
        res[f"engine HC D={D}"]=np.array([E.hc_step(h,x) for x in air])
    ok=yr>=1982
    return {k:(v[ok]-cyc[ok],mo[ok]) for k,v in res.items()},nl
if __name__=="__main__":
    R=Pool(4).map(one,sorted(S)); keys=list(R[0][0])
    print("rms error (C) against Cycles' soil temperature, layers 1,2,3 and all, by model")
    for k in keys:
        out=[]
        for L in range(3):
            e=np.concatenate([r[0][k][0][:,L] for r in R if r[1]>L]); out.append(np.sqrt(np.nanmean(e**2)))
        e=np.concatenate([r[0][k][0][:,0] for r in R]); mo=np.concatenate([r[0][k][1] for r in R])
        win=np.sqrt(np.nanmean(e[np.isin(mo,[12,1,2])]**2)); sum_=np.sqrt(np.nanmean(e[np.isin(mo,[6,7,8])]**2)); bias=np.nanmean(e[np.isin(mo,[12,1,2])]),np.nanmean(e[np.isin(mo,[6,7,8])])
        print(f" {k:14s} layer1 {out[0]:.2f} layer2 {out[1]:.2f} layer3 {out[2]:.2f} | layer1 winter rms {win:.2f} bias {bias[0]:+.2f} | summer rms {sum_:.2f} bias {bias[1]:+.2f}")
