"""Layer-wise forms for Cycles' o2_factor (2026-10-15). Usage: python3 o2_param2.py"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, rhizo_engine as E, run_validation_multisite as m
def soil(site):
    L=[]
    for ln in open(f'/tmp/cycles-run15/input/{site}.soil'):
        p=ln.split()
        if len(p)>=6 and p[0].isdigit():
            thick,clay,sand,soc=map(float,p[1:5]);hyd=E.saxton_rawls(sand,clay,soc);L.append((thick,hyd['sat'],hyd['fc']))
    return L
rows=[]
for site in S.ALL:
    L=soil(site);n=len(L)
    W={x['date']:x for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyWater.csv')) if x['date'][0]!='#'}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999' or x['stage'] not in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'):continue
        w=W[x['date']];th=np.array([float(w[f'soil_moisture_content.{i+1}']) for i in range(n)])
        thick=np.array([l[0] for l in L]);sat=np.array([l[1] for l in L]);fc=np.array([l[2] for l in L])
        ttf=float(x['thermal_time'])/1800.0;rd=max(0.05,2.0*min(1.0,ttf/0.5));top=np.concatenate([[0],np.cumsum(thick)[:-1]])
        ov=np.clip(np.minimum(rd,top+thick)-top,0,None)
        rows.append((site,th,sat,fc,ov,float(x['o2_factor'])))
site=np.array([r[0] for r in rows]);y=np.array([r[5] for r in rows])
held=set(m.HELDOUT_SITES);tr=np.array([s not in held for s in site])
def feat(kind,m0,q):
    out=np.empty(len(rows))
    for k,(s,th,sat,fc,ov,_) in enumerate(rows):
        if kind=='sat':v=th/sat
        else:v=(th-fc)/np.maximum(sat-fc,1e-6)+0.0
        st=np.clip((v-m0)/(1-m0),0,1)**q if kind=='sat' else np.clip(v/1.0,0,1)**q if m0==0 else np.clip((v-m0)/(1-m0),0,1)**q
        out[k]=(st*ov).sum()/max(ov.sum(),1e-9)
    return out
def r2(yy,p):return 1-((yy-p)**2).sum()/((yy-yy.mean())**2).sum()
res=[]
for kind,m0s in (('sat',(0.5,0.6,0.7,0.75,0.8,0.85)),('fc',(0.0,0.2,0.4,0.6))):
    for m0 in m0s:
        for q in (1,2):
            f=feat(kind,m0,q);A=np.c_[f[tr],np.ones(tr.sum())];c=np.linalg.lstsq(A,y[tr],rcond=None)[0]
            res.append((r2(y[~tr],c[0]*f[~tr]+c[1]),r2(y[tr],c[0]*f[tr]+c[1]),kind,m0,q,c))
res.sort(key=lambda t:-t[0])
for t in res[:6]:print('held-out R2 %.3f  train %.3f  %s m0 %.2f q %d  scale %.2f int %.3f'%(t[0],t[1],t[2],t[3],t[4],t[5][0],t[5][1]))
