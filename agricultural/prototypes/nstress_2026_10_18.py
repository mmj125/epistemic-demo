"""N stress attribution (2026-10-18): engine vs Cycles daily N stress, plant N and mineral pool through the season, corn, N=0 and 150, continuous chain.
Usage (engine config comes from the environment, e.g. ENGINE_OVR="CROP.n_uptake_rate=None"): TAG=default python3 nstress_2026_10_18.py N_SITES"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json'))
def rd(path): return [r for r in csv.DictReader(open(path)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    C=rd(d+"dailyCornRM.90.csv"); Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    cy={}
    for r in C:
        if r['biomass']=='-999': continue
        dt=datetime.date.fromisoformat(r['date']); cy[(dt.year,dt.timetuple().tm_yday)]=(1-float(r['nitrogen_stress'])/100,float(r['total_nitrogen'])*1000)
    pool={}
    for r in Nn:
        dt=datetime.date.fromisoformat(r['date']); pool[(dt.year,dt.timetuple().tm_yday)]=float(r['profile_soil_NO3'])+float(r['profile_soil_NH4'])
    E.DIAG_STATE=[]; res=m.engine(site,wx,soil,cl,N,'leadin'); D=E.DIAG_STATE; E.DIAG_STATE=None
    en={}
    for y,doy,canopy,ns,pn in D:
        if y is not None: en[(y,doy)]=(ns,pn)
    yrs=sorted({k[0] for k in cy}&{k[0] for k in en}); rows=[]
    for y in yrs:
        ks=sorted(k for k in cy if k[0]==y and k in en)
        if len(ks)<40: continue
        c=np.array([cy[k] for k in ks]); e=np.array([en[k] for k in ks]); n=len(ks); q=[slice(0,n//3),slice(n//3,2*n//3),slice(2*n//3,n)]
        rows.append(dict(y=y,ns_c=c[:,0].mean(),ns_e=e[:,0].mean(),ns_c_t=[float(c[s,0].mean()) for s in q],ns_e_t=[float(e[s,0].mean()) for s in q],pn_c=c[:,1].max(),pn_e=e[:,1].max(),
                         pn_c_t=[float(c[s,1].mean()) for s in q],pn_e_t=[float(e[s,1].mean()) for s in q],pool_c=float(np.mean([pool.get(k,np.nan) for k in ks])),grain=res.get(y,{}).get('grain',np.nan)))
    return dict(site=site,N=N,rows=rows)
if __name__=="__main__":
    ks=sorted(S); n=int(sys.argv[1]); ks=[ks[i] for i in range(0,len(ks),max(1,len(ks)//n))][:n]
    with Pool(4) as p: R=p.map(one,[(k,N) for k in ks for N in (0,150)])
    tag=os.environ.get("TAG","default"); json.dump(R,open(f'/tmp/w/nstress_{tag}.json','w'),default=float)
    for N in (0,150):
        rr=[r for x in R if x['N']==N for r in x['rows']]; g=lambda k:np.mean([r[k] for r in rr]); gt=lambda k:np.mean([r[k] for r in rr],0)
        print(f"{tag} N={N} site-years {len(rr)}: season-mean N stress factor Cycles {g('ns_c'):.3f} engine {g('ns_e'):.3f} | thirds C {np.round(gt('ns_c_t'),3).tolist()} E {np.round(gt('ns_e_t'),3).tolist()}")
        print(f"      plant N at peak kg/ha C {g('pn_c'):.0f} E {g('pn_e'):.0f} | thirds C {np.round(gt('pn_c_t'),0).tolist()} E {np.round(gt('pn_e_t'),0).tolist()} | Cycles mean pool in season {g('pool_c'):.0f}")
        print(f"      year-to-year sd of season-mean N stress: Cycles {np.std([r['ns_c'] for r in rr]):.3f} engine {np.std([r['ns_e'] for r in rr]):.3f}; corr {np.corrcoef([r['ns_c'] for r in rr],[r['ns_e'] for r in rr])[0,1]:.2f}")
