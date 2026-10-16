import sys,os,csv,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
sys.argv=['x'];import swap_test as S
import cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
orig=m.simulate_continuous
def sc(*a,**k):
    k['record_history']=True;return orig(*a,**k)
m.simulate_continuous=sc
def one(args):
    site,N=args
    E.CANOPY_N_POW=3.85;E.CANOPY_WATER_POW=1.35
    lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=S.force(site,N,('wclock',))
    r=m.engine(site,wx,soil,cl,N,'leadin')
    C={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);C[(d.year,d.timetuple().tm_yday)]=(float(x['radiation_interception']),float(x['thermal_time']))
    bins=np.zeros((10,3))
    for y,res in r.items():
        for h in (res.get('history') or []):
            c=C.get((y,h['doy']))
            if not c: continue
            b=min(9,int(c[1]/1800*10))
            bins[b]+=[h['canopy'],c[0],1]
    return bins
if __name__=="__main__":
    for N in (150,0):
        with Pool(8) as p: res=p.map(one,[(s,N) for s in S.ALL])
        B=sum(res)
        print('N=%d  thermal-time decile: engine canopy | Cycles canopy | ratio'%N)
        for i in range(10): print('  %d0-%d0%%  %.3f  %.3f  %.2f   (n=%d)'%(i,i+1,B[i,0]/max(B[i,2],1),B[i,1]/max(B[i,2],1),B[i,0]/max(B[i,1],1e-9),B[i,2]))
