import sys,os,csv,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, cycles_engine_validate as E, run_validation_multisite as m
E.ROOT_C_REALIZED_GROWTH=True
for site in ('indiana','maryland','mississippi','missouri','kentucky','iowa','kansas'):
    lat,lon=S.ALL[site];wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    H={int(x['date'][:4]):float(x['grain_yield']) for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/harvest.csv')) if x['date'][0]!='#'}
    out=[]
    for sc in (None,0.71,1.5):
        E.O2_STRESS_SCALE=sc;r=m.engine(site,wx,soil,cl,150,'leadin');ys=[y for y in r if y in H]
        out.append(np.mean([r[y]['grain']-H[y] for y in ys]))
    print('%-12s bias off %+.2f  0.71 %+.2f  1.5 %+.2f   Cycles mean %.2f'%(site,*out,np.mean(list(H.values()))))
