"""Per-layer mass-flow N supply measured inside the engine (2026-10-18), no behavior change. Paper Sec 2.7: the water flux from the soil in each layer to the
species determines the species' access to mineral N. Here each layer's root water withdrawal (campbell_water_uptake) times that layer's nitrate concentration
(current water, or saturated volume) is summed per season day (in-season, after planting) and compared with the engine's actual N uptake and with Cycles' (44 kg/ha at
N=0, 165 at N=150 over 14 sites). Usage: python3 massflow_engine_2026_10_18.py N_SITES (engine config from the environment, e.g. ENGINE_OVR)."""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json'))
def one(a):
    site,N=a; lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    st=dict(before=None,wul=None,cur=0.0,sat=0.0,n=0.0); o_cw=E.campbell_water_uptake; o_hook=E._water_hook
    def cw(layers,*args,**kw):
        st['before']=[l['theta'] for l in layers]; r=o_cw(layers,*args,**kw)
        st['wul']=[(b-l['theta'])*l['thick']*1000.0 for b,l in zip(st['before'],layers)]; st['th0']=st['before']; return r
    def hook(layers,doy,no3_layers=None):
        if st['wul'] is not None and no3_layers is not None:
            for i,l in enumerate(layers):
                w0=st['before'][i]*l['thick']*1000.0; vs=l['sat']*l['thick']*1000.0
                if st['wul'][i]>0 and w0>1e-6:
                    st['cur']+=st['wul'][i]*no3_layers[i]/w0; st['sat']+=st['wul'][i]*no3_layers[i]/vs
            st['n']+=1
        st['wul']=None
        return o_hook(layers,doy,no3_layers)
    E.campbell_water_uptake=cw; E._water_hook=hook
    try: res=m.engine(site,wx,soil,cl,N,'leadin')
    finally: E.campbell_water_uptake=o_cw; E._water_hook=o_hook
    seasons=[y for y,v in res.items() if isinstance(v,dict) and v.get('n_uptake_kg_ha') is not None]
    upt=np.mean([res[y]['n_uptake_kg_ha'] for y in seasons]); k=max(len(seasons),1)
    return dict(site=site,N=N,cur=st['cur']/k,sat=st['sat']/k,upt=float(upt))
if __name__=="__main__":
    ks=sorted(S); n=int(sys.argv[1]); ks=[ks[i] for i in range(0,len(ks),max(1,len(ks)//n))][:n]
    with Pool(4) as p: R=p.map(one,[(k,N) for k in ks for N in (0,150)])
    for N in (0,150):
        r=[x for x in R if x['N']==N]; g=lambda k:np.mean([x[k] for x in r])
        print(f"N={N}: engine actual N uptake {g('upt'):.1f} kg/ha/season | per-layer mass-flow supply, current-water concentration {g('cur'):.1f}, saturated-volume concentration {g('sat'):.1f} | site corr(actual uptake, supply cur) {np.corrcoef([x['upt'] for x in r],[x['cur'] for x in r])[0,1]:.2f}")
