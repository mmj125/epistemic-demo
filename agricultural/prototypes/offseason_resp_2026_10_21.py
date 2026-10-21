import os,sys,csv,shutil,subprocess,datetime
os.environ["REGIONAL"]="0"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m, cycles_engine_validate as E
from cover_chain_2026_10_21 import corn_crop
from multiprocessing import Pool
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
LOG=[]; _orig=E.sixpool_ml_step
def _w(state,tmean,layers,root_c,ft_eff=1.0):
    v=_orig(state,tmean,layers,root_c,ft_eff); LOG.append((E._DIAG_YEAR,E._DIAG_CTX.get("doy"),state.get("resp_mg_ha",0.0),v)); return v
E.sixpool_ml_step=_w
def one(si):
    site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"rp"; m.write_inputs(nm,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{nm}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N0/"
    S=rd(d+"dailySoilC.csv"); N=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    cyc=np.zeros((12,3)); 
    for a,b in zip(S,N):
        dt=datetime.date.fromisoformat(a['date'])
        if 1984<=dt.year<=2014: cyc[dt.month-1]+=[float(a['soil_organic_matter_respired_carbon']),float(a['residue_respired_carbon']),float(b['net_mineralization'])]
    cyc/=31
    del LOG[:]; kw=E.standard_kwargs(soil,0); r=E.simulate_continuous(wx,corn_crop(cl,soil),carry_n=True,**kw)
    eng=np.zeros((12,2)); yrs=set()
    for (y,doy,rs,v) in LOG:
        if y is not None and 1984<=y<=2014:
            mo=(datetime.date(2001,1,1)+datetime.timedelta(int(doy)-1)).month-1; eng[mo]+=[rs,v]
    eng/=31
    return eng,cyc
if __name__=="__main__":
    R=Pool(4).map(one,range(24)); e=np.mean([r[0] for r in R],0); c=np.mean([r[1] for r in R],0)
    print("N=0, 24 sites, all days (engine counts each simulated day, season and fallow). Mg C/ha respired per month: engine total | Cycles SOM + residue ; net N kg/ha per month engine | Cycles")
    for i in range(12): print(f" {i+1:2d}: {e[i,0]:.4f} | {c[i,0]+c[i,1]:.4f} (SOM {c[i,0]:.4f})   net N {e[i,1]:6.2f} | {c[i,2]:6.2f}")
    print("year: resp engine %.3f Cycles %.3f ; net N engine %.1f Cycles %.1f"%(e[:,0].sum(),(c[:,0]+c[:,1]).sum(),e[:,1].sum(),c[:,2].sum()))
