"""Daily growth check under forced canopy, water stress, N stress and planting pool (2026-10-15): compare the engine's daily biomass increment with
Cycles' own, split by which limiter the engine chose (radiation GR or transpiration GT). Needs the temporary DIAG_GROWTH hook in the engine.
Usage: python3 floor_growth.py"""
import sys,os,csv,json,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
def one(a):
    site,N=a;lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    F=S.force(site,N,('canopy','water','nstress','minn','wclock'));E.FORCE_SERIES=F
    E.DIAG_GROWTH=[];m.engine(site,wx,soil,cl,N,'leadin');D=E.DIAG_GROWTH;E.DIAG_GROWTH=None
    # split the flat list into seasons at doy decreases
    seasons=[];cur=[]
    for d in D:
        if cur and d[0]<=cur[-1][0]:seasons.append(cur);cur=[]
        cur.append(d)
    if cur:seasons.append(cur)
    rows={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);rows[(d.year,d.timetuple().tm_yday)]=(float(x['biomass']),float(x['nitrogen_stress']),float(x['water_stress']))
    out=[]
    for ss in seasons:
        # match season to a year by looking up its first doy in forced series: use water-stress forcing years order
        pass
    yrs=sorted(F)
    # seasons from the engine are chronological over all years in wx; map by order of years having Cycles output
    cyc_years=sorted({y for y,_ in rows})
    for y,ss in zip(sorted(wx)[:len(seasons)],seasons):
        for doy,GR,GT,dg in ss:
            a0=rows.get((y,doy-1));a1=rows.get((y,doy))
            if a0 and a1 and a1[0]-a0[0]>=0 and a1[0]>0.01:
                dc=(a1[0]-a0[0])/10.0;ns=1-a1[1]/100
                out.append((doy,GR,GT,dg*ns,dc,ns,1-a1[2]/100))
    return site,N,out
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,[(s,N) for N in (0,150) for s in S.ALL])
    json.dump(res,open('/tmp/w/floor_growth.json','w'))
    for N in (0,150):
        A=np.array([r for s,n,o in res if n==N for r in o])
        doy,GR,GT,de,dc,ns,ws=A.T;rad=GR<=GT
        print(f'N={N} days {len(A)}  engine/Cycles sum ratio {de.sum()/dc.sum():.3f}  daily corr {np.corrcoef(de,dc)[0,1]:.3f}')
        for nm,sel in (('radiation-limited days',rad),('transpiration-limited days',~rad)):
            print(f'   {nm}: {sel.mean():.2f} of days, ratio {de[sel].sum()/dc[sel].sum():.3f}, corr {np.corrcoef(de[sel],dc[sel])[0,1]:.3f}')
        for lo,hi in ((0,.5),(.5,.9),(.9,1.01)):
            s_=(ws>=lo)&(ws<hi);print(f'   water mult {lo}-{hi}: {s_.mean():.2f} of days ratio {de[s_].sum()/dc[s_].sum():.3f}')
        for lo,hi in ((0,.3),(.3,.7),(.7,1.01)):
            s_=(ns>=lo)&(ns<hi)
            if s_.sum()>20:print(f'   N mult {lo}-{hi}: {s_.mean():.2f} of days ratio {de[s_].sum()/dc[s_].sum():.3f}')
