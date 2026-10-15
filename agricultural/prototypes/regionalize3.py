"""Write out-of-fold predicted per-site (m, g) as JSON for a true engine validation pass (2026-10-15)."""
import sys,json
sys.argv=['x']
src=open('regionalize2.py').read().split("J0=np.mean")[0]
exec(src)
pm=np.clip(np.exp(oof(lambda:GradientBoostingRegressor(n_estimators=150,max_depth=3,learning_rate=0.05,subsample=0.8,random_state=0),lm,0)),0.6,1.4)
pg=np.clip(np.exp(oof(lambda:GradientBoostingRegressor(n_estimators=150,max_depth=3,learning_rate=0.05,subsample=0.8,random_state=0),lg,0)),0.8,1.25)
json.dump({s:float(v) for s,v in zip(sites,pm)},open('/tmp/w/reg1_m.json','w'));json.dump({s:float(v) for s,v in zip(sites,pg)},open('/tmp/w/reg1_g.json','w'));print('written',len(sites),pm.mean(),pg.mean())
