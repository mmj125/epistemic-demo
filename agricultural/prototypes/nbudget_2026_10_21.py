"""Stage 1 of the in-season nitrate budget (2026-10-21): Cycles daily N pools and fluxes at 24 sites, N=0 and 150 (corn, continuous), saved to /tmp/w/nb.npz.
Columns: site N year doy no3 nh4 min imm netmin nitr volat denit leach_no3 leach_nh4 bypass plantN agN rootN stress."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m
from multiprocessing import Pool
COLS="site N year doy no3 nh4 min imm netmin nitr volat denit leach_no3 leach_nh4 bypass plantN agN rootN stress".split()
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
def one(si):
    site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"nb"; m.write_inputs(nm,lat,lon,wx,soil,cl); rows=[]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N{N}/"
        D=rd(d+"dailyN.csv"); C={r['date']:r for r in rd(d+"dailyCornRM.90.csv")}
        for a in D:
            dt=datetime.date.fromisoformat(a['date']); c=C.get(a['date'])
            rows.append([si,N,dt.year,dt.timetuple().tm_yday,float(a['profile_soil_NO3']),float(a['profile_soil_NH4']),float(a['mineralization']),float(a['immobilization']),float(a['net_mineralization']),float(a['nitrification']),float(a['volatilization']),float(a['denitrification']),float(a['NO3_leaching']),float(a['NH4_leaching']),float(a['NO3_bypass'])+float(a['NH4_bypass']),
                         float(c['total_nitrogen']) if c else np.nan,float(c['aboveground_nitrogen']) if c else np.nan,float(c['root_nitrogen']) if c else np.nan,float(c['nitrogen_stress']) if c else np.nan])
        shutil.rmtree(d,ignore_errors=True)
    return rows
if __name__=="__main__":
    R=Pool(4).map(one,range(24)); A=np.array([r for x in R for r in x]); np.savez("/tmp/w/nb.npz",A=A,cols=COLS); print(A.shape)
