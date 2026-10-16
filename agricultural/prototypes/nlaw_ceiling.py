"""Rebuild phase 4: what is the ceiling for each N-loss law given Cycles' own daily states, and which drivers matter? Held out by site (odd site ids)."""
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
z=np.load('/tmp/w/ntable.npz'); T=z['T']; C=list(z['cols']); ix={c:i for i,c in enumerate(C)}
col=lambda n:T[:,ix[n]]
tr=(col('site')%2==0); te=~tr
GROUPS={'moisture_now':['rel1','rel2','relmax'],'moisture_lag':['rel1_l1','rel1_l2','rel1_l3','rel1_max5','rel1_mean5'],'nitrate':['no3','no3_1','no3_2'],'ammonium':['nh4','nh4_1'],'temperature':['T1','Tair'],
        'carbon_resp':['som','res','hum'],'water_flux':['drain','drain_l1','pp','infil'],'demand':['et0','vpd'],'soil':['clay','sat1','soc1']}
ALL=[c for g in GROUPS.values() for c in g]
def run(target,mask,feats,label,n=300000,seed=0):
    rng=np.random.RandomState(seed); idx=np.where(mask&tr)[0]; idx=rng.choice(idx,min(n,len(idx)),replace=False); jt=np.where(mask&te)[0]
    X=T[:,[ix[f] for f in feats]]; y=col(target)
    m=HGB(max_iter=200,learning_rate=0.1,max_leaf_nodes=31).fit(X[idx],y[idx]); p=m.predict(X[jt])
    r2=1-((y[jt]-p)**2).sum()/((y[jt]-y[jt].mean())**2).sum()
    return r2,m,jt,p
for target,mask in (('denit',col('no3')>0.5),('nit',col('nh4')>0.05),('vol',col('nh4')>0.05)):
    r2,_,jt,p=run(target,mask,ALL,'all'); print(f'== {target}: HGB ceiling held-out daily R2 {r2:.2f}  (n test {len(jt)})')
    out=[]
    for g,fs in GROUPS.items():
        r,_,_,_=run(target,mask,[f for f in ALL if f not in fs],g,n=150000); out.append((g,r))
    base=run(target,mask,ALL,'all',n=150000)[0]
    print('   drop-group R2 (base %.2f): '%base+'  '.join(f'{g} {r:.2f}' for g,r in sorted(out,key=lambda x:x[1])))
