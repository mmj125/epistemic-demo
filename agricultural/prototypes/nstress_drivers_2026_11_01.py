"""What drives Cycles' reported daily nitrogen_stress beyond N concentration over the critical curve? (2026-11-01)
Uses existing Cycles corn output folders (N=0 and N=150, continuous chain). Features per growing day: ratio r_t = concentration / critical (Nmax 0.055 g/g x aboveground biomass^-0.4, biomass in Mg/ha),
lags and rolling means of r, daily uptake relative to its 7-day mean, profile soil nitrate plus ammonium (kg/ha) on the day before, thermal time. Gradient boosting with leave-sites-out cross validation;
reports R2 of reported stress for feature sets. A set that lifts R2 well above r_t alone names the missing driver."""
import glob, os, csv, sys, numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor as GB
from sklearn.model_selection import GroupKFold
O="/tmp/cycles-run15/output/"; rows=[]; grp=[]
dirs=[d for d in sorted(glob.glob(O+"*N0"))+sorted(glob.glob(O+"*N150")) if not any(k in os.path.basename(d) for k in ("sor","sil","soy","wh","rye"))]
for d in dirs[:int(sys.argv[1]) if len(sys.argv)>1 else 80]:
    try:
        D=[r for r in csv.DictReader(l for l in open(d+"/dailyCornRM.90.csv") if not l.startswith('#')) if r['biomass']!='-999']
        Nn={r['date']:r for r in csv.DictReader(l for l in open(d+"/dailyN.csv") if not l.startswith('#'))}
    except Exception: continue
    site=os.path.basename(d); prev={}; hist={}
    for r in D:
        y=r['date'][:4]; ab=float(r['aboveground_biomass']); 
        if ab<=0.3 or r['stage'] not in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'): continue
        conc=float(r['aboveground_nitrogen_concentration'])/1000; crit=0.055*ab**-0.4; ratio=conc/crit; s=float(r['nitrogen_stress'])/100
        h=hist.setdefault(y,[]); agn=float(r['aboveground_nitrogen'])
        up=agn-(h[-1][1] if h else agn)
        sn=Nn.get(r['date']); soil=(float(sn['profile_soil_NO3'])+float(sn['profile_soil_NH4'])) if sn else np.nan
        r1=h[-1][0] if h else ratio; r3=np.mean([x[0] for x in h[-3:]]) if h else ratio; r7=np.mean([x[0] for x in h[-7:]]) if h else ratio
        up7=np.mean([x[2] for x in h[-7:]]) if h else 0.0
        rows.append((s,ratio,r1,r3,r7,up,up7,(h[-1][3] if h else soil),soil,float(r['thermal_time']),ab,agn)); grp.append(site.rsplit('N',1)[0])
        h.append((ratio,agn,up,soil))
X=np.array(rows,float); g=np.array(grp); y=X[:,0]; ok=~np.isnan(X).any(1); X,y,g=X[ok],y[ok],g[ok]
print("days",len(y),"sites",len(set(g)),"mean stress",y.mean().round(3),"share stress>0",(y>0).mean().round(3))
SETS={"ratio now":[1],"+ lag1":[1,2],"+ lag3 and 7 mean":[1,2,3,4],"+ uptake":[1,5,6],"+ soil mineral N (prev day)":[1,7],"+ soil N now, uptake":[1,5,6,8],"+ thermal time, biomass":[1,9,10],"all":[1,2,3,4,5,6,7,8,9,10,11]}
for name,cols in SETS.items():
    pr=np.zeros_like(y)
    for tr,te in GroupKFold(5).split(X,y,g):
        m=GB(max_iter=200,learning_rate=0.08).fit(X[tr][:,cols],y[tr]); pr[te]=m.predict(X[te][:,cols])
    print(f"{name:32s} R2 {1-((y-pr)**2).sum()/((y-y.mean())**2).sum():.3f}")
