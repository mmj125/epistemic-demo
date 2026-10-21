import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)[:12]
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    R={r['date']:r for r in rd(d+"dailyResidue.csv")}; C={r['date']:r for r in rd(d+"dailySoilC.csv")}; W={r['date']:r for r in rd(d+"dailyWater.csv")}; En={r['date']:r for r in rd(d+"dailyEnviron.csv")}; N={r['date']:r for r in rd(d+"dailyN.csv")}
    print(list(R[next(iter(R))].keys())[:20]) if site==SITES[0] else None
    shutil.rmtree(d,ignore_errors=True); rows=[]
    for dt in R:
        if dt not in C or dt not in W or dt not in En or int(dt[:4])<1982: continue
        date=datetime.date.fromisoformat(dt)
        rows.append([SITES.index(site),int(dt[:4]),date.timetuple().tm_yday,float(C[dt]['residue_respired_carbon']),float(C[dt]['soil_organic_matter_respired_carbon']),float(R[dt]['aboveground_residue_biomass']),float(R[dt]['belowground_residue_biomass']),float(R[dt]['root_residue_biomass']),float(R[dt]['standing_residue_moisture']),float(R[dt]['flat_residue_moisture']),float(En[dt]['soil_temperature.1']),float(W[dt]['soil_moisture_content.1']),float(R[dt]['aboveground_residue_nitrogen']),float(N[dt].get('N_mineralization',N[dt].get('mineralization',0.0))) if True else 0.0])
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,SITES),[])); np.save('/tmp/w/resdata.npy',A); print(A.shape)
