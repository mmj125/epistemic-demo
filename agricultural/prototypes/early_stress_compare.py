"""Early-season stress timing: engine vs Cycles v1.5.20 multipliers and canopy over thermal-time windows. Usage: python3 early_stress_compare.py N"""
import sys,os,csv,json,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
N=int(sys.argv[1]) if len(sys.argv)>1 else 0
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
orig=m.simulate_continuous
def sc(*a,**k):
    k['record_history']=True;return orig(*a,**k)
m.simulate_continuous=sc
WIN=((0.0,0.15),(0.15,0.3),(0.3,0.5),(0.5,0.8))
def one(site):
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    r=m.engine(site,wx,soil,cl,N,'leadin')
    C={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date'])
        C[(d.year,d.timetuple().tm_yday)]=(float(x['thermal_time']),1-float(x['nitrogen_stress'])/100,1-float(x['water_stress'])/100,float(x['radiation_interception']))
    acc=np.zeros((len(WIN),9))
    for y,res in r.items():
        for h in (res.get('history') or []):
            c=C.get((y,h['doy']))
            if not c: continue
            f=c[0]/1800.0
            for i,(a,b) in enumerate(WIN):
                if a<=f<b: acc[i]+=[h['n_stress'],c[1],h['water_stress'],c[2],h['canopy'],c[3],1,0,0]
    return site,acc
if __name__=="__main__":
    with Pool(8) as p: res=dict(p.map(one,list(ALL)))
    out={s:a.tolist() for s,a in res.items()}
    json.dump(out,open(f'/tmp/w/early_N{N}.json','w'))
    print('done')
