"""Site-offset analysis on a scaled-up site set: which site covariates (climate, soil) explain the per-site N=150 / N=0 / N=400 yield bias of the engine against Cycles? Leave-one-site-out R2 for linear, ridge and small-tree models (2026-10-15). Usage: python3 site_offset.py TAG[,TAG2] [JSON of sites for each tag ...]"""
import sys,json,glob,numpy as np
import field_data as fd
import run_validation_multisite as m
tags=sys.argv[1].split(',');sets=sys.argv[2].split(',')
D={};S={}
for t,sj in zip(tags,sets):
    for f in glob.glob(f'/tmp/w/{t}_[0-9]*.json'):D.update(json.load(open(f)))
    S.update({k:tuple(v) for k,v in json.load(open(sj)).items()})
def cov(site):
    lat,lon=S[site];wx,_=fd.resolve_field_weather(lat,lon);soil,_,_=fd.resolve_field_soil(lat,lon)
    ys=sorted(wx);pp=np.mean([sum(r['pp'] for r in wx[y].values()) for y in ys])
    gs=np.mean([sum(r['pp'] for d,r in wx[y].items() if 121<=d<=273) for y in ys])
    tm=np.mean([np.mean([(r['tx']+r['tn'])/2 for r in wx[y].values()]) for y in ys])
    gt=np.mean([np.mean([(r['tx']+r['tn'])/2 for d,r in wx[y].items() if 121<=d<=273]) for y in ys])
    sol=np.mean([np.mean([r['solar'] for d,r in wx[y].items() if 121<=d<=273]) for y in ys])
    gdd=np.mean([sum(max(0,min(r['tx'],30)-10+max(0,min(r['tn'],30)-10) -10)/2 for d,r in wx[y].items()) for y in ys])
    wt=[l['thick'] for l in soil];tot=sum(wt)
    top=[l for l in soil][:3]
    clay1=np.mean([l['clay'] for l in top]);sand1=np.mean([l['sand'] for l in top]);soc1=np.mean([l['soc'] or 0.2 for l in top])
    soc_p=sum((l['soc'] or 0.2)*l['thick'] for l in soil)/tot;clay_p=sum(l['clay']*l['thick'] for l in soil)/tot
    return [lat,lon,pp,gs,tm,gt,sol,gdd,clay1,sand1,soc1,soc_p,clay_p,tot]
names=['lat','lon','ann_pp','gs_pp','tmean','gs_tmean','gs_solar','gdd','clay_top','sand_top','soc_top','soc_prof','clay_prof','depth']
sites=sorted(set(k.split('|')[0] for k in D))
X=np.array([cov(s) for s in sites])
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut,cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
for N in (0,150,400):
    y=np.array([D[f'{s}|N{N}|leadin']['res']['grain']['model']-D[f'{s}|N{N}|leadin']['res']['grain']['real'] for s in sites])
    cy=np.array([D[f'{s}|N{N}|leadin']['res']['grain']['real'] for s in sites])
    print('\nN=%d  n=%d  site bias sd %.2f  mean |bias| %.2f'%(N,len(y),y.std(),np.abs(y).mean()))
    for nm,mod in (('ridge',make_pipeline(StandardScaler(),RidgeCV(alphas=np.logspace(-2,3,20)))),('gboost(depth2)',GradientBoostingRegressor(n_estimators=150,max_depth=2,learning_rate=0.05,subsample=0.8,random_state=0))):
        p=cross_val_predict(mod,X,y,cv=LeaveOneOut())
        r2=1-((y-p)**2).sum()/((y-y.mean())**2).sum();print('  %-15s LOO R2 %+.3f   residual mean |bias| %.3f (from %.3f)'%(nm,r2,np.abs(y-p).mean(),np.abs(y).mean()))
    gb=GradientBoostingRegressor(n_estimators=150,max_depth=2,learning_rate=0.05,subsample=0.8,random_state=0).fit(X,y)
    imp=sorted(zip(gb.feature_importances_,names),reverse=True)[:5];print('  top features:',[(n,round(i,2)) for i,n in imp])
    print('  corr with bias:',[(n,round(np.corrcoef(X[:,i],y)[0,1],2)) for i,n in sorted(enumerate(names),key=lambda t:-abs(np.corrcoef(X[:,t[0]],y)[0,1]))[:5]])
