"""What explains the early N=0 stress Cycles has beyond the engine's ratio law? (2026-10-19) Residual (Cycles N factor - engine law on Cycles' states) against mineral N pool, daily uptake, and previous-day N factor, corn N=0, 24 sites."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    Nn={r['date']:r for r in rd(d+"dailyN.csv")}; rows=[]; prev=None
    for r in rd(d+"dailyCornRM.90.csv"):
        if r['biomass']=='-999': prev=None; continue
        tb=float(r['biomass']); ab=float(r['aboveground_biomass']); tn=float(r['total_nitrogen']); ttf=float(r['thermal_time'])/1800.0; cf=1.0-float(r['nitrogen_stress'])/100.0 if float(r['nitrogen_stress'])>1.5 else 1.0-float(r['nitrogen_stress'])
        if prev is not None and ab>0.2 and r['date'] in Nn:
            ratio=(E.N_AG_FRACTION*tn/(ab*10))/E.n_critical_pct(tb,rv.CORN,None); lw=1.0-E.N_STRESS_SMAX*min(1.0,max(0.0,(E.N_STRESS_R0-ratio)/(E.N_STRESS_R0-E.N_STRESS_R1)))**E.N_STRESS_Q
            pool=float(Nn[r['date']]['profile_soil_NO3'])+float(Nn[r['date']]['profile_soil_NH4'])
            rows.append((ttf,cf,lw,pool,tn-prev[0],tb-prev[1],prev[2],ratio,tb))
        prev=(tn,tb,cf)
    shutil.rmtree(d,ignore_errors=True); return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/nresid.npy',A); print(len(A),'days')
    ttf,cf,lw,pool,du,db,cfp,ratio,tb=A.T; res=cf-lw; k=(ttf>=0.2)&(ttf<0.6)&(ratio<0.9)
    print('early N=0 days (ttf .2-.6, ratio<0.9): n %d, mean residual (Cycles - law) %.3f'%(k.sum(),res[k].mean()))
    for name,x in (('mineral pool',pool),('uptake today',du),('growth today',db),('previous-day Cycles factor',cfp),('total biomass',tb),('ratio',ratio)):
        c=np.corrcoef(x[k],res[k])[0,1]; print(f'  corr(residual, {name:28s}) {c:+.3f}')
    for lo,hi in ((0,5),(5,10),(10,20),(20,40),(40,1000)):
        kk=k&(pool>=lo)&(pool<hi)
        if kk.sum()>100: print(f'  pool {lo}-{hi}: n {kk.sum()} residual {res[kk].mean():+.3f}')
