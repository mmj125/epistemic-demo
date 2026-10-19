"""Wheat trajectory with Cycles' canopy, water and N factor forced (2026-10-19): daily above-ground growth, engine vs Cycles, by Cycles' stage and by month, N=0 and 150, 16 fresh sites, FALLN=60.
Locates where the N=150 over-growth (forced total biomass 1.112) builds up."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ["FALLN"]="60"; sys.path.insert(0,'.')
import numpy as np, wheat_attrib as A, run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def cyc(fs,N):
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; C={}
    for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
        if x['date'][0]=='#' or x['biomass']=='-999': continue
        C[x['date']]=(float(x['aboveground_biomass']),x['stage'],float(x['grain_biomass']),float(x['reserve_biomass']),float(x['nitrogen_stress']))
    return C
def one(a):
    site,(lat,lon)=a; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatT"; m.write_inputs(fs,lat,lon,wx,soil,cl); rows=[]
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); P=A.series(fs,N)
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True)
        C=cyc(fs,N)
        E.FORCE_SERIES={y:{k:v[k] for k in ("canopy","water","nstress")} for y,v in P.items()}
        R=W.engine_chain(wx,soil,cl,N,1.0); E.FORCE_SERIES=None
        for ye,res in R.items():
            prev_e=None; prev_c=None
            for h in res["history"]:
                yr=ye-1 if h["doy"]>=288 else ye
                try: dt=(datetime.date(yr,1,1)+datetime.timedelta(days=h["doy"]-1)).isoformat()
                except ValueError: continue
                if dt in C and yr>=1981:
                    e=h["ag_mg_ha"]; c=C[dt]
                    if prev_e is not None and prev_c is not None: rows.append((N,int(dt[5:7]),1 if c[1].startswith('REPRO') else 0,e-prev_e,c[0]-prev_c[0],e,c[0]))
                    prev_e=e; prev_c=c
    return rows
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=sum(p.map(one,[(k,S[k]) for k in ks]),[])
    X=np.array(R); np.save('/tmp/w/wheat_traj.npy',X)
    for N in (0,150):
        print(f'N={N}: daily above-ground growth sum, engine / Cycles (Mg/ha per season-day basis), by stage and month')
        s=X[:,0]==N
        for st,lab in ((0,'vegetative'),(1,'reproductive')):
            k=s&(X[:,2]==st); print(f'  {lab:12s}: engine {X[k,3].sum()/1.0:9.1f} Cycles {X[k,4].sum():9.1f} ratio {X[k,3].sum()/X[k,4].sum():.3f}')
        for mo in (10,11,12,1,2,3,4,5,6):
            k=s&(X[:,1]==mo)
            if k.sum()>200: print(f'   month {mo:2d}: ratio {X[k,3].sum()/X[k,4].sum():.3f}  (Cycles growth {X[k,4].sum():8.1f})')
        k=s&(X[:,2]==1); print('  end-of-season ag biomass mean engine %.2f Cycles %.2f'%(X[s][X[s][:,1]==6][:,5].mean(),X[s][X[s][:,1]==6][:,6].mean()) if (X[s][:,1]==6).any() else '')
