"""Column audit (2026-10-15): for every numeric daily column in Cycles' outputs, season-mean per site-year (planting to harvest), correlated with the
engine's unforced grain error (engine - Cycles) at N=150; pooled and within-site. Usage: python3 column_audit.py"""
import csv,json,glob,os,collections,datetime,numpy as np
ph={s:rows for s,k,rows in json.load(open('/tmp/w/phenology.json'))}
files=['dailyCornRM.90','dailyWater','dailyEnviron','dailyN','dailySoilC','dailyResidue','dailySoilLayersCN']
feat=collections.defaultdict(dict)  # (col)->{(site,year):value}
err={}
for s,rows in ph.items():
    G={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{s}N150/harvest.csv')) if x['date'][0]!='#'}
    P={int(x['date'][:4]):(datetime.date.fromisoformat(x['planting_date']),datetime.date.fromisoformat(x['date'])) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{s}N150/harvest.csv')) if x['date'][0]!='#'}
    for y,pd,hd,pe,he,g in rows:
        if y in G:err[(s,y)]=g-G[y]
    for f in files:
        path=f'/tmp/cycles-run15/output/{s}N150/{f}.csv'
        if not os.path.exists(path):continue
        acc=collections.defaultdict(lambda:collections.defaultdict(list))
        for x in csv.DictReader(open(path)):
            if x['date'][0]=='#':continue
            d=datetime.date.fromisoformat(x['date']);y=d.year
            if y not in P or not (P[y][0]<=d<=P[y][1]):continue
            for c,v in x.items():
                if c in('date','crop','stage'):continue
                try:fv=float(v)
                except:continue
                if fv==-999:continue
                acc[c][y].append(fv)
        for c,dd in acc.items():
            for y,vs in dd.items():feat[f+':'+c][(s,y)]=float(np.mean(vs))
keys=sorted(err)
E=np.array([err[k] for k in keys]);S=np.array([k[0] for k in keys])
out=[]
for c,dd in feat.items():
    ks=[k for k in keys if k in dd]
    if len(ks)<800:continue
    x=np.array([dd[k] for k in ks]);e=np.array([err[k] for k in ks]);ss=np.array([k[0] for k in ks])
    if x.std()<1e-9:continue
    pooled=np.corrcoef(x,e)[0,1]
    xs=x.copy();es=e.copy()
    for s in set(ss):
        m=ss==s;xs[m]-=x[m].mean();es[m]-=e[m].mean()
    within=np.corrcoef(xs,es)[0,1] if xs.std()>1e-9 else 0
    out.append((c,pooled,within,len(ks)))
out.sort(key=lambda t:-max(abs(t[1]),abs(t[2])))
print('column                                      pooled   within-site   n')
for c,a,b,n in out[:28]:print('%-42s %+.2f    %+.2f      %d'%(c,a,b,n))
