"""Where does the fertilizer go? Per-site mean annual N budget at N=0 and N=150, engine vs Cycles v1.5.20, and the
fertilizer-driven difference (N150 minus N0). Usage: python3 n150_budget.py [site ...]; writes /tmp/w/n150_budget.json"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous")
import cycles_engine_validate as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
ALL=dict(m.SITES);ALL.update(m.HELDOUT_SITES)
def one(site):
    lat,lon=ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    out={}
    for N in (0,150):
        r=m.engine(site,wx,soil,cl,N,'leadin');ys=sorted(r)
        d=f'/tmp/cycles-run15/output/{site}N{N}'
        A={int(x['year']):x for x in csv.DictReader(open(d+'/annualN.csv')) if x['year'][0]!='#'}
        C={}
        for x in csv.DictReader(open(d+'/dailyCornRM.90.csv')):
            if x['date'][0]=='#' or x['total_nitrogen']=='-999':continue
            y=int(x['date'][:4]);C[y]=max(C.get(y,0),float(x['total_nitrogen']))
        H={}
        for x in csv.DictReader(open(d+'/harvest.csv')):
            if x['date'][0]=='#':continue
            H[int(x['date'][:4])]=float(x['grain_yield'])
        yy=[y for y in ys if y in A and y in C]
        g=lambda f:float(np.mean([f(y) for y in yy]))
        out[N]=dict(
          cyc=dict(uptake=g(lambda y:C[y]),leach=g(lambda y:float(A[y]['NO3_leaching'])+float(A[y]['NH4_leaching'])),denit=g(lambda y:float(A[y]['denitrification'])),
                   volat=g(lambda y:float(A[y]['volatilization'])),n2o=g(lambda y:float(A[y]['N2O_emission']))),
          eng=dict(uptake=g(lambda y:r[y].get('n_uptake_kg_ha',0)),leach=g(lambda y:r[y].get('n_leached_kg_ha',0)),denit=g(lambda y:r[y].get('n_denitrified_kg_ha',0)),
                   volat=g(lambda y:r[y].get('n_volatilized_pool_kg_ha',0)),n2o=g(lambda y:r[y].get('n2o_emitted_kg_ha',0))))
    return site,out
if __name__=="__main__":
    sites=sys.argv[1:] or list(ALL)
    with Pool(8) as p: res=dict(p.map(one,sites))
    json.dump(res,open('/tmp/w/n150_budget.json','w'))
    keys=('uptake','leach','denit','volat','n2o')
    print('mean over sites, kg N/ha/yr   (N150 - N0) engine | Cycles')
    for k in keys:
        e=np.mean([res[s][150]['eng'][k]-res[s][0]['eng'][k] for s in res]);c=np.mean([res[s][150]['cyc'][k]-res[s][0]['cyc'][k] for s in res])
        e0=np.mean([res[s][0]['eng'][k] for s in res]);c0=np.mean([res[s][0]['cyc'][k] for s in res])
        print('%-7s N0 eng %6.1f cyc %6.1f | fertilizer-driven eng %6.1f cyc %6.1f'%(k,e0,c0,e,c))
