"""Which covariates and how small a model keep the out-of-fold gain? (2026-10-15)"""
import sys
sys.argv=['x']
exec(open('regionalize2.py').read().split("J0=np.mean")[0])
names=['lat','lon','ann_pp','gs_pp','tmean','gs_tmean','gs_solar','gs_rh','gs_wind','clay_top','sand_top','soc_top','soc_prof','clay_prof','depth','sat_ratio']
J0=np.mean([np.mean([np.abs(pairs(B,s,N)[:,1]-pairs(B,s,N)[:,0]).mean() for N in Ns]) for s in sites])
mk=lambda n,d,lr:(lambda:GradientBoostingRegressor(n_estimators=n,max_depth=d,learning_rate=lr,subsample=0.8,random_state=0))
def run(cols,mkr,label):
    global XX
    X0=XX;XX=X0[:,cols]
    pm=np.clip(np.exp(oof(mkr,lm,0)),0.6,1.4);pg=np.clip(np.exp(oof(mkr,lg,0)),0.8,1.25)
    sc=score(pm,pg);XX=X0;print('%-46s J %.4f  (%.1f%% better)'%(label,sc,100*(J0-sc)/J0))
full=list(range(16))
gb=GradientBoostingRegressor(n_estimators=150,max_depth=3,learning_rate=0.05,subsample=0.8,random_state=0)
imp=np.zeros(16)
for y in (lm,lg):imp+=gb.fit(XX,y).feature_importances_
order=np.argsort(-imp);print('importance order:',[(names[i],round(imp[i]/2,2)) for i in order[:10]])
run(full,mk(150,3,0.05),'all 16 features, 150 trees depth 3')
for k in (10,8,6,5,4):run(list(order[:k]),mk(150,3,0.05),'top %d features, 150 trees depth 3'%k)
run(list(order[:6]),mk(40,3,0.15),'top 6 features, 40 trees depth 3 (compact)')
run(list(order[:6]),mk(30,2,0.2),'top 6 features, 30 trees depth 2 (smaller)')
