"""Waterlogging probe (2026-10-15): relate Cycles' o2_factor to layer saturation. Usage: python3 o2_probe.py"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, cycles_engine_validate as E
def soil(site):
    L=[]
    for ln in open(f'/tmp/cycles-run15/input/{site}.soil'):
        p=ln.split()
        if len(p)>=6 and p[0].isdigit():
            thick,clay,sand,soc=map(float,p[1:5]);hyd=E.saxton_rawls(sand,clay,soc)
            L.append(dict(thick=thick,sat=hyd['sat'],fc=hyd['fc']))
    return L
rows=[]
for site in S.ALL:
    L=soil(site);n=len(L)
    W={x['date']:x for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyWater.csv')) if x['date'][0]!='#'}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999' or x['stage'] not in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'):continue
        w=W[x['date']];th=[float(w[f'soil_moisture_content.{i+1}']) for i in range(n)]
        rel=[th[i]/L[i]['sat'] for i in range(n)]
        ttf=float(x['thermal_time'])/1800.0;rd=2.0*min(1.0,ttf/0.5)
        # root-zone weights
        top=0.0;wts=[]
        for i in range(n):
            ov=max(0.0,min(rd,top+L[i]['thick'])-top);wts.append(ov);top+=L[i]['thick']
        tw=sum(wts) or 1.0
        rz=sum(r*w_ for r,w_ in zip(rel,wts))/tw
        rows.append((site,float(x['o2_factor']),rz,max(rel[:3]),rel[0],rel[1] if n>1 else rel[0],float(x['water_stress']),float(x['temperature_factor'])))
A=np.array([r[1:] for r in rows],float)
o2,rz,mx,r1,r2,ws,tf=A.T
print('days',len(A),'o2 range',o2.min(),o2.max(),'frac o2>0.01',(o2>0.01).mean())
for nm,v in (('root-zone mean rel sat',rz),('max rel sat top3',mx),('layer1 rel sat',r1),('layer2 rel sat',r2)):
    print('  corr(o2, %-24s) %+.2f'%(nm,np.corrcoef(o2,v)[0,1]))
print('o2 vs root-zone mean relative saturation')
for lo,hi in ((0,.5),(.5,.6),(.6,.7),(.7,.8),(.8,.85),(.85,.9),(.9,.95),(.95,1.01),(1.01,2)):
    m=(rz>=lo)&(rz<hi)
    if m.sum()>20:print('  rz %.2f-%.2f n=%6d  mean o2 %.3f  p90 %.3f'%(lo,hi,m.sum(),o2[m].mean(),np.percentile(o2[m],90)))
json.dump([list(map(lambda v:v if isinstance(v,str) else float(v),r)) for r in rows[::7]],open('/tmp/w/o2_rows.json','w'))
