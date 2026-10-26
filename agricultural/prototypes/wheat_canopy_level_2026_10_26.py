"""Is Cycles' winter wheat canopy the documented shape times a function of the CURRENT stress factors, not an integral of stress-reduced rates? (2026-10-26) Per day: r = canopy / shape(TTf) against n^p w^q (log regression), TTf 0.25 to 0.95,
plus the same on the previous day's factors and on cumulative means, R2 each. Cycles output only, 24 held-out sites, N=0 and 90. Usage: FALLN=60 python3 wheat_canopy_level_2026_10_26.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
F_=json.load(open('sitesets/fresh94.json')); S24_=json.load(open('/tmp/w/s24.json')); S={k:F_[k] for k in sorted(F_) if k not in S24_}; S={k:S[k] for k in sorted(S)[::3][:24]}; CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def shape(x,eix=0.853): return eix/(1+np.exp(6-20*x)+np.exp(-16+16*x))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatlv"; m.write_inputs(fs,lat,lon,wx,soil,cl); rows=[]
    for N in (0,90):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; CR=[x for x in rd(d+"dailyWinterWheat.csv") if x["biomass"]!="-999"]; shutil.rmtree(d,ignore_errors=True)
        by={}
        for x in CR:
            dt=datetime.date.fromisoformat(x["date"]); y=dt.year if dt.month>=10 else dt.year-1; by.setdefault(y,[]).append(x)
        for y,L in by.items():
            if len(L)<150: continue
            tt=np.array([float(x["thermal_time"]) for x in L]); x=tt/tt.max(); ci=np.array([float(x_["radiation_interception"]) for x_ in L]); w=1-np.array([float(x_["water_stress"]) for x_ in L])/100; n=1-np.array([float(x_["nitrogen_stress"]) for x_ in L])/100
            cw=np.cumsum(w)/np.arange(1,len(w)+1); cn=np.cumsum(n)/np.arange(1,len(n)+1)
            for i in range(1,len(x)):
                if 0.25<=x[i]<=0.95 and ci[i]>0.02: rows.append([ci[i]/shape(x[i]),n[i],w[i],n[i-1],w[i-1],cn[i],cw[i],x[i]])
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[]),float); A=A[(A[:,0]>0.02)&(A[:,1]>0.02)&(A[:,2]>0.02)]; print(len(A),"days")
    y=np.log(A[:,0])
    def fit(cols,nm):
        X=np.column_stack([np.ones(len(A))]+[np.log(np.clip(A[:,c],1e-3,None)) for c in cols]); b=np.linalg.lstsq(X,y,rcond=None)[0]; pr=X@b
        print(f" {nm:34s} R2 {1-((y-pr)**2).sum()/((y-y.mean())**2).sum():.2f} exponents {np.round(b[1:],2)} const {b[0]:+.2f}")
    fit([1,2],"current n, w"); fit([3,4],"previous day n, w"); fit([5,6],"cumulative mean n, w"); fit([1],"current n only"); fit([2],"current w only"); fit([5],"cumulative n only")
    X=np.column_stack([np.ones(len(A)),np.log(np.clip(A[:,5],1e-3,None)),np.log(np.clip(A[:,1],1e-3,None)),A[:,7]]); b=np.linalg.lstsq(X,y,rcond=None)[0]; pr=X@b; print(" cumulative n, current n, TTf        R2 %.2f"%(1-((y-pr)**2).sum()/((y-y.mean())**2).sum()),np.round(b,2))
