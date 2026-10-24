"""What controls Cycles' o2_factor beyond root-zone relative saturation? (2026-10-15) Usage: python3 o2_fit.py"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, rhizo_engine as E
def soil(site):
    L=[]
    for ln in open(f'/tmp/cycles-run15/input/{site}.soil'):
        p=ln.split()
        if len(p)>=6 and p[0].isdigit():
            thick,clay,sand,soc=map(float,p[1:5]);hyd=E.saxton_rawls(sand,clay,soc);L.append(dict(thick=thick,sat=hyd['sat'],fc=hyd['fc']))
    return L
F=[];Y=[];SITE=[]
for site in S.ALL:
    L=soil(site);n=len(L)
    W={x['date']:x for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyWater.csv')) if x['date'][0]!='#'}
    En={x['date']:x for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyEnviron.csv')) if x['date'][0]!='#'}
    hist=[];run=0;prev=None
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999' or x['stage'] not in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'):hist=[];run=0;prev=None;continue
        w=W[x['date']];e=En[x['date']]
        th=[float(w[f'soil_moisture_content.{i+1}']) for i in range(n)];rel=[th[i]/L[i]['sat'] for i in range(n)]
        ttf=float(x['thermal_time'])/1800.0;rd=2.0*min(1.0,ttf/0.5);top=0.0;wts=[]
        for i in range(n):
            ov=max(0.0,min(rd,top+L[i]['thick'])-top);wts.append(ov);top+=L[i]['thick']
        rz=sum(r*w_ for r,w_ in zip(rel,wts))/(sum(wts) or 1.0)
        run=run+1 if rz>0.8 else 0
        hist.append(rz);lag1=hist[-2] if len(hist)>1 else rz;lag3=np.mean(hist[-4:-1]) if len(hist)>1 else rz
        F.append([rz,max(rel[:3]),rel[0],rel[1] if n>1 else rel[0],float(e['soil_temperature.1']),ttf,lag1,lag3,run,float(w['drainage']),float(e['precipitation'])]);Y.append(float(x['o2_factor']));SITE.append(site)
F=np.array(F);Y=np.array(Y);SITE=np.array(SITE)
names=['rz','max3','rel1','rel2','Tsoil','ttf','rz_lag1','rz_lag3','run>0.8','drain','precip']
held=set(S.m.HELDOUT_SITES) if hasattr(S,'m') else set()
import run_validation_multisite as m
held=set(m.HELDOUT_SITES);tr=np.array([s not in held for s in SITE])
def r2(y,p):return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
from sklearn.ensemble import GradientBoostingRegressor
for nm,cols in (('rz only',[0]),('rz+lags',[0,6,7]),('rz+lags+run',[0,6,7,8]),('rz+Tsoil+ttf',[0,4,5]),('all',list(range(11)))):
    g=GradientBoostingRegressor(n_estimators=120,max_depth=3,subsample=0.5).fit(F[tr][:,cols],Y[tr])
    print('%-14s train-site R2 %.3f  held-out-site R2 %.3f'%(nm,r2(Y[tr],g.predict(F[tr][:,cols])),r2(Y[~tr],g.predict(F[~tr][:,cols]))))
g=GradientBoostingRegressor(n_estimators=120,max_depth=3,subsample=0.5).fit(F[tr],Y[tr])
print('importances',dict(zip(names,np.round(g.feature_importances_,3))))
