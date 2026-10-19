"""Is Cycles' N stress tied to soil mineral N concentration (mg/kg, top layers)? (2026-10-19) Corn N=0, 24 sites. Residual (Cycles N factor - engine ratio law on Cycles' states) and the factor itself against mean NO3+NH4 concentration in layers 1-2 and 1-4 (dailySoilLayersCN)."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; rows=[]
    for r in rd(d+"dailyCornRM.90.csv"):
        if r['biomass']=='-999' or r['date'] not in L: continue
        tb=float(r['biomass']); ab=float(r['aboveground_biomass']); tn=float(r['total_nitrogen']); ttf=float(r['thermal_time'])/1800.0
        if ab<0.2: continue
        cf=1.0-float(r['nitrogen_stress'])/100.0 if float(r['nitrogen_stress'])>1.5 else 1.0-float(r['nitrogen_stress'])
        ratio=(E.N_AG_FRACTION*tn/(ab*10))/E.n_critical_pct(tb,rv.CORN,None); lw=1.0-E.N_STRESS_SMAX*min(1.0,max(0.0,(E.N_STRESS_R0-ratio)/(E.N_STRESS_R0-E.N_STRESS_R1)))**E.N_STRESS_Q
        l=L[r['date']]; ids=[i for i in (1,2,3,4) if f'NO3.{i}' in l]; c=[float(l[f'NO3.{i}'])+float(l[f'NH4.{i}']) for i in ids]; n3=[float(l[f'NO3.{i}']) for i in ids]
        rows.append((ttf,cf,lw,np.mean(c[:2]),np.mean(c),np.mean(n3[:2]),ratio,tb))
    shutil.rmtree(d,ignore_errors=True); return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/nconc.npy',A); ttf,cf,lw,c12,c14,n12,ratio,tb=A.T; res=cf-lw
    k=(ttf>=0.2)&(ttf<0.6)&(ratio<0.9); print(len(A),'days; early low-ratio days',k.sum())
    for name,x in (('min N layers 1-2',c12),('min N layers 1-4',c14),('NO3 layers 1-2',n12)):
        print(f' corr(residual,{name}) {np.corrcoef(x[k],res[k])[0,1]:+.3f}   corr(factor,{name}) {np.corrcoef(x[k],cf[k])[0,1]:+.3f}')
    print(' concentration bin (layers 1-2 NO3+NH4, mg/kg): n | Cycles factor | ratio-law factor | mean ratio')
    for lo,hi in ((0,1),(1,2),(2,4),(4,8),(8,16),(16,200)):
        kk=k&(c12>=lo)&(c12<hi)
        if kk.sum()>100: print(f'  {lo:3d}-{hi:3d}: {kk.sum():6d} | {cf[kk].mean():.3f} | {lw[kk].mean():.3f} | {ratio[kk].mean():.2f}')
