"""What does Cycles' N factor depend on? (2026-10-19) Corn, 24 sites, N=0 and 150, daily features from Cycles output only: ttf, biomass, ag biomass, plant N, ag N conc, ratio (engine law input), engine-law factor, growth today, uptake today, water factor, canopy,
mean temperature, mineral N pool, layer 1-2 mineral N concentration, previous-day factor, days since emergence. Saves the table; fits gradient boosting to the factor with and without the previous-day factor and reports importances."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    Nn={r['date']:r for r in rd(d+"dailyN.csv")}; L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; rows=[]; prev=None; day=0
    for r in rd(d+"dailyCornRM.90.csv"):
        if r['biomass']=='-999': prev=None; day=0; continue
        day+=1; dt=datetime.date.fromisoformat(r['date']); tb=float(r['biomass']); ab=float(r['aboveground_biomass']); tn=float(r['total_nitrogen']); an=float(r['aboveground_nitrogen']); conc=float(r['aboveground_nitrogen_concentration'])/10.0
        cf=1.0-float(r['nitrogen_stress'])/100.0; wf=1.0-float(r['water_stress'])/100.0; can=float(r['radiation_interception']); ttf=float(r['thermal_time'])/1800.0
        if prev is not None and ab>0.15 and r['date'] in Nn and r['date'] in L:
            crit=E.n_critical_pct(tb,rv.CORN,None); ratio=conc/crit; law=1.0-E.N_STRESS_SMAX*min(1.0,max(0.0,(E.N_STRESS_R0-ratio)/(E.N_STRESS_R0-E.N_STRESS_R1)))**E.N_STRESS_Q
            l=L[r['date']]; ids=[i for i in (1,2,3,4) if f'NO3.{i}' in l]; c12=np.mean([float(l[f'NO3.{i}'])+float(l[f'NH4.{i}']) for i in ids[:2]])
            pool=float(Nn[r['date']]['profile_soil_NO3'])+float(Nn[r['date']]['profile_soil_NH4'])
            tm=(wx[dt.year][dt.timetuple().tm_yday]['tx']+wx[dt.year][dt.timetuple().tm_yday]['tn'])/2
            rows.append((N,cf,prev[0],ttf,tb,ab,tn,conc,ratio,law,tb-prev[1],tn-prev[2],wf,can,tm,pool,c12,day,conc/ (E.N_AG_FRACTION*0+rv.CORN['n_max_conc']*100)))
        prev=(cf,tb,tn)
    shutil.rmtree(d,ignore_errors=True); return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150)]),[])); np.save('/tmp/w/nfeat.npy',A); print(len(A),'days')
    names=['N','cf','cf_prev','ttf','tb','ab','tn','conc','ratio','law','dB','dN','wf','canopy','tmean','pool','c12','day','conc_over_max']
    from sklearn.ensemble import GradientBoostingRegressor
    rng=np.random.default_rng(0); idx=rng.permutation(len(A)); tr,te=idx[:len(A)*7//10],idx[len(A)*7//10:]
    for label,drop in (('all features',['cf']),('without previous-day factor',['cf','cf_prev']),('without prev factor and law/ratio',['cf','cf_prev','law','ratio','conc','conc_over_max'])):
        cols=[i for i,n in enumerate(names) if n not in drop]; g=GradientBoostingRegressor(n_estimators=150,max_depth=4,subsample=0.5,random_state=0).fit(A[tr][:,cols],A[tr,1])
        r=g.predict(A[te][:,cols])-A[te,1]; imp=sorted(zip(g.feature_importances_,[names[i] for i in cols]),reverse=True)[:6]
        print(f'{label}: held-out rms {np.sqrt(np.mean(r**2)):.4f} | top: '+', '.join(f'{n} {v:.2f}' for v,n in imp))
    print('baselines held-out: engine law rms %.4f, previous day rms %.4f'%(np.sqrt(np.mean((A[te,9]-A[te,1])**2)),np.sqrt(np.mean((A[te,2]-A[te,1])**2))))
