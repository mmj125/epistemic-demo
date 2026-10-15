"""Season water balance, engine vs Cycles, at N=400 for the sandiest and clayiest sites of the scaled-up set (2026-10-15). Usage: python3 water_texture.py"""
import os,sys,csv,json,pickle,numpy as np
os.environ.setdefault('LEAD_YEARS','continuous');os.environ['YEAR_STEP']='2'
sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
def one(site):
    S=json.load(open('/tmp/w/big240.json'));lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    rec=[];o=E.campbell_water_uptake
    def w(layers,rd,trp,eie,*a,**k):
        r=o(layers,rd,trp,eie,*a,**k);f=sys._getframe(1);ww=f.f_locals.get('w')
        rec.append((ww['doy'] if ww else -1,trp,eie,r[0],r[1]));return r
    E.campbell_water_uptake=w
    try:m.write_inputs(site,lat,lon,wx,soil,cl);res=m.engine(site,wx,soil,cl,400,'leadin')
    finally:E.campbell_water_uptake=o
    # split engine records into seasons
    seasons=[];cur=[];last=-1
    for r in rec:
        if r[0]<last and cur:seasons.append(cur);cur=[]
        cur.append(r);last=r[0]
    if cur:seasons.append(cur)
    eng=np.array([[sum(x[1] for x in s),sum(x[3] for x in s),np.mean([x[2] for x in s]),np.average([x[4] for x in s],weights=[max(x[1],1e-6) for x in s]),len(s),np.mean([x[1] for x in s])] for s in seasons])
    d=f'/tmp/cycles-run15/output/{site}N400/'
    W={x['date']:float(x['transpiration']) for x in csv.DictReader(open(d+'dailyWater.csv')) if x['date'][0]!='#'}
    ys={}
    for x in csv.DictReader(open(d+'dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['crop']=='-' or x['biomass']=='-999':continue
        y=x['date'][:4];t=ys.setdefault(y,[0,0,[],[],[]])
        t[0]+=float(x['potential_transpiration']);t[1]+=W.get(x['date'],0);t[2].append(float(x['radiation_interception']));t[3].append(1-float(x['water_stress'])/100);t[4].append(float(x['potential_transpiration']))
    cyc=np.array([[t[0],t[1],np.mean(t[2]),np.average(t[3],weights=np.maximum(t[4],1e-6)),len(t[2]),np.mean(t[4])] for t in ys.values()])
    gs=[r for y in wx for d,r in wx[y].items() if 121<=d<=273];cv=dict(rh=np.mean([(r['rhx']+r['rhn'])/2 for r in gs]),wind=np.mean([r['wind'] for r in gs]),solar=np.mean([r['solar'] for r in gs]),tx=np.mean([r['tx'] for r in gs]),lat=lat,lon=lon)
    return site,eng.mean(0),cyc.mean(0),cv,len(seasons)
if __name__=="__main__":
    C=pickle.load(open('/tmp/w/covcache.pkl','rb'));S=json.load(open('/tmp/w/big240.json'))
    r=sorted(S,key=lambda s:C[s][1]);sel=r[:10]+r[-10:]
    with Pool(4) as p:R=p.map(one,sel)
    print('cols: season potential transpiration mm | actual transpiration mm | mean canopy | water-stress multiplier (1 = none)')
    rat=np.array([x[1][5]/x[2][5] for x in R]);print('per-site potTR/day ratio engine/Cycles:');
    for k in ('rh','wind','solar','tx','lat','lon'):print('  corr(ratio, %s) %+.2f'%(k,np.corrcoef(rat,[x[3][k] for x in R])[0,1]))
    print('  corr(ratio, clay) %+.2f'%np.corrcoef(rat,[C[x[0]][1] for x in R])[0,1])
    for x in sorted(R,key=lambda x:-x[1][5]/x[2][5])[:5]+sorted(R,key=lambda x:-x[1][5]/x[2][5])[-3:]:print('  %-14s ratio %.2f rh %.0f wind %.1f lat %.1f lon %.1f'%(x[0],x[1][5]/x[2][5],x[3]['rh'],x[3]['wind'],x[3]['lat'],x[3]['lon']))
    print('top-ratio sites: engine [potTR, actTR, canopy, stressmult, days, potTR/day] vs Cycles');
    for x in sorted(R,key=lambda x:-x[1][5]/x[2][5])[:4]:print('  ',x[0],np.round(x[1],2),np.round(x[2],2))
    for grp,rows in (('sandy',R[:10]),('clayey',R[10:])):
        e=np.mean([x[1] for x in rows],0);c=np.mean([x[2] for x in rows],0)
        print('%-7s clay %.0f  engine  %6.0f %6.0f %5.2f %5.2f days %3.0f potTR/day %.2f   Cycles %6.0f %6.0f %5.2f %5.2f days %3.0f potTR/day %.2f'%(grp,np.mean([C[x[0]][1] for x in rows]),*e,*c))
