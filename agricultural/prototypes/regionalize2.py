"""Out-of-fold test: predict each site's optimal (log m, log g) from site covariates and score the engine with the predicted values (2026-10-15). Usage: python3 regionalize2.py"""
import sys,json,glob,pickle,numpy as np
sys.path.insert(0,'.')
exec(open('regionalize.py').read().split("best={}")[0])
sites2,best=pickle.load(open('/tmp/w/regionalize_best'+os.environ.get('PK','')+'.pkl','rb'))
S={}
for sj in ('big240','old28'):S.update({k:tuple(v) for k,v in json.load(open(f'/tmp/w/{sj}.json')).items()})
cp='/tmp/w/cov2.pkl'
import os
if os.path.exists(cp):X=pickle.load(open(cp,'rb'))
else:
    X={}
    for s in sites:
        lat,lon=S[s];wx,_=fd.resolve_field_weather(lat,lon);soil,_,_=fd.resolve_field_soil(lat,lon);ys=sorted(wx)
        pp=np.mean([sum(r['pp'] for r in wx[y].values()) for y in ys]);gs=np.mean([sum(r['pp'] for d,r in wx[y].items() if 121<=d<=273) for y in ys])
        tm=np.mean([np.mean([(r['tx']+r['tn'])/2 for r in wx[y].values()]) for y in ys]);gt=np.mean([np.mean([(r['tx']+r['tn'])/2 for d,r in wx[y].items() if 121<=d<=273]) for y in ys])
        sol=np.mean([np.mean([r['solar'] for d,r in wx[y].items() if 121<=d<=273]) for y in ys]);rh=np.mean([np.mean([(r['rhx']+r['rhn'])/2 for d,r in wx[y].items() if 121<=d<=273]) for y in ys])
        wn=np.mean([np.mean([r['wind'] for d,r in wx[y].items() if 121<=d<=273]) for y in ys])
        tot=sum(l['thick'] for l in soil);top=soil[:3]
        clay=np.mean([l['clay'] for l in top]);sand=np.mean([l['sand'] for l in top]);soc=np.mean([(l['soc'] or 0.2) for l in top])
        X[s]=[lat,lon,pp,gs,tm,gt,sol,rh,wn,clay,sand,soc,sum((l['soc'] or 0.2)*l['thick'] for l in soil)/tot,sum(l['clay']*l['thick'] for l in soil)/tot,tot,soc/(2.11+3.75*clay/100)]
    pickle.dump(X,open(cp,'wb'))
XX=np.array([X[s] for s in sites]);lm=np.log([best[s][0] for s in sites]);lg=np.log([best[s][1] for s in sites])
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import KFold
def oof(mk,y,seed=0):
    p=np.zeros(len(y))
    for tr,te in KFold(5,shuffle=True,random_state=seed).split(XX):
        p[te]=mk().fit(XX[tr],y[tr]).predict(XX[te])
    return p
def score(mhat,ghat):
    out=[]
    for k,s in enumerate(sites):
        out.append(np.mean([np.abs(ghat[k]*interp(s,N,mhat[k])-pairs(B,s,N)[:,0]).mean() for N in Ns]))
    return np.mean(out)
J0=np.mean([np.mean([np.abs(pairs(B,s,N)[:,1]-pairs(B,s,N)[:,0]).mean() for N in Ns]) for s in sites])
print('baseline J %.4f'%J0)
cfg={'gboost d2':lambda:GradientBoostingRegressor(n_estimators=120,max_depth=2,learning_rate=0.05,subsample=0.8,random_state=0),
     'gboost d3':lambda:GradientBoostingRegressor(n_estimators=150,max_depth=3,learning_rate=0.05,subsample=0.8,random_state=0),
     'ridge':lambda:make_pipeline(StandardScaler(),RidgeCV(alphas=np.logspace(-2,3,20)))}
for nm,mk in cfg.items():
    for seed in (0,1):
        pm=np.exp(oof(mk,lm,seed));pg=np.exp(oof(mk,lg,seed))
        pm=np.clip(pm,0.6,1.4);pg=np.clip(pg,0.8,1.25)
        print('%-10s seed %d  out-of-fold J %.4f  (%.1f%% better)   R2 log m %.2f  log g %.2f'%(nm,seed,score(pm,pg),100*(J0-score(pm,pg))/J0,1-((lm-np.log(pm))**2).sum()/((lm-lm.mean())**2).sum(),1-((lg-np.log(pg))**2).sum()/((lg-lg.mean())**2).sum()))
# per-N results for the best config
pm=np.clip(np.exp(oof(cfg['gboost d2'],lm,0)),0.6,1.4);pg=np.clip(np.exp(oof(cfg['gboost d2'],lg,0)),0.8,1.25)
for N in Ns:
    b=np.mean([np.abs(pairs(B,s,N)[:,1]-pairs(B,s,N)[:,0]).mean() for s in sites]);a=np.mean([np.abs(pg[k]*interp(s,N,pm[k])-pairs(B,s,N)[:,0]).mean() for k,s in enumerate(sites)])
    print('  N=%d MAE %.3f -> %.3f'%(N,b,a))
