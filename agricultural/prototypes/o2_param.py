"""Parametric fit of Cycles' o2_factor on relative saturation of root-zone layers (2026-10-15). Usage: python3 o2_param.py"""
import sys,os,csv,json,itertools,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, rhizo_engine as E, run_validation_multisite as m
def soil(site):
    L=[]
    for ln in open(f'/tmp/cycles-run15/input/{site}.soil'):
        p=ln.split()
        if len(p)>=6 and p[0].isdigit():
            thick,clay,sand,soc=map(float,p[1:5]);hyd=E.saxton_rawls(sand,clay,soc);L.append(dict(thick=thick,sat=hyd['sat']))
    return L
D=[]
for site in S.ALL:
    L=soil(site);n=len(L)
    W={x['date']:x for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyWater.csv')) if x['date'][0]!='#'}
    prev=None
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999' or x['stage'] not in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'):prev=None;continue
        w=W[x['date']];rel=[float(w[f'soil_moisture_content.{i+1}'])/L[i]['sat'] for i in range(n)]
        ttf=float(x['thermal_time'])/1800.0;rd=max(0.1,2.0*min(1.0,ttf/0.5));top=0.0;rr=[]
        for i in range(n):
            if top<rd:rr.append(rel[i])
            top+=L[i]['thick']
        mx=max(rr);mx_avg=mx if prev is None else 0.5*(mx+prev);prev=mx
        D.append((site,mx,mx_avg,float(x['o2_factor']),int(x['date'][:4])))
site=np.array([d[0] for d in D]);mx=np.array([d[1] for d in D]);mxa=np.array([d[2] for d in D]);y=np.array([d[3] for d in D])
held=set(m.HELDOUT_SITES);tr=np.array([s not in held for s in site])
def model(v,m0,q,sm):return sm*np.clip((v-m0)/(1-m0),0,1)**q
def r2(yy,p):return 1-((yy-p)**2).sum()/((yy-yy.mean())**2).sum()
best=None
for vn,v in (('max root-zone rel sat',mx),('2-day avg',mxa)):
    b=None
    for m0 in np.arange(0.4,0.85,0.025):
        for q in (0.5,0.75,1,1.5,2,3):
            for sm in (0.6,0.8,1.0):
                s=((y[tr]-model(v[tr],m0,q,sm))**2).sum()
                if b is None or s<b[0]:b=(s,m0,q,sm)
    _,m0,q,sm=b
    print('%-22s m0 %.3f q %.2f smax %.2f   train R2 %.3f  held-out R2 %.3f'%(vn,m0,q,sm,r2(y[tr],model(v[tr],m0,q,sm)),r2(y[~tr],model(v[~tr],m0,q,sm))))
    if best is None or vn.startswith('max'):best=(m0,q,sm)
print('use',best)
json.dump(dict(m0=best[0],q=best[1],smax=best[2]),open('/tmp/w/o2_params.json','w'))
