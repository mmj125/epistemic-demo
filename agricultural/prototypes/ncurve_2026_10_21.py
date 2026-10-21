"""Cycles' crop N concentration against biomass on unstressed days (N=400, nitrogen_stress ~0), 12 sites (2026-10-21)."""
import os,sys,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m
from multiprocessing import Pool
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
def one(si):
    site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"nc"; m.write_inputs(nm,lat,lon,wx,soil,cl); rows=[]
    for N in (0,150,400):
        subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N{N}/"
        for r in rd(d+"dailyCornRM.90.csv"):
            try: rows.append([si]+[float(r[k]) for k in ("aboveground_biomass","root_biomass","aboveground_nitrogen","root_nitrogen","aboveground_nitrogen_concentration","nitrogen_stress","thermal_time","grain_biomass")]+[N,int(r['date'][:4]),__import__('datetime').date.fromisoformat(r['date']).timetuple().tm_yday])
            except: pass
        shutil.rmtree(d,ignore_errors=True)
    return rows
if __name__=="__main__":
    R=Pool(4).map(one,range(0,24,2)); A=np.array([r for x in R for r in x]); np.savez("/tmp/w/ncurve.npz",A=A); print(A.shape)
