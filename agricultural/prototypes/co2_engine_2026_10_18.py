"""Engine CO2 response on the same sites as co2_response_2026_10_18.py (N=400, corn, continuous chain): CO2 held flat at 300/400/500 ppm in every year. Prints log-log exponents of above-ground biomass and grain."""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
E.WUE_CO2_EXP=float(os.environ.get('WUE_EXP',E.WUE_CO2_EXP)); E.RUE_CO2_EXP=float(os.environ.get('RUE_EXP',E.RUE_CO2_EXP))
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); LV=(300,400,500)
def one(a):
    site,co2=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    E.CO2_PPM_BY_YEAR={y:float(co2) for y in range(1900,2100)}
    res=m.engine(site,wx,soil,cl,400,'leadin'); ys=[y for y in res if y>1981]
    return site,co2,np.mean([res[y]['ag'] for y in ys]),np.mean([res[y]['grain'] for y in ys])
if __name__=="__main__":
    ks=sorted(S)[:int(sys.argv[1])]
    with Pool(4) as p: R=p.map(one,[(k,c) for k in ks for c in LV])
    by={}
    for s,c,ag,gy in R: by.setdefault(s,{})[c]=(ag,gy)
    ea=[];eg=[]
    for s,v in by.items():
        a=np.log(v[500][0]/v[300][0])/np.log(500/300); g=np.log(v[500][1]/v[300][1])/np.log(500/300); ea.append(a); eg.append(g); print(f"{s:16s} exponent above-ground {a:+.3f} grain {g:+.3f}")
    print('mean exponent above-ground %.3f grain %.3f'%(np.mean(ea),np.mean(eg))); json.dump(ea,open('/tmp/w/co2eng_%s_%s.json'%(os.environ.get('WUE_EXP'),os.environ.get('RUE_EXP')),'w'))
