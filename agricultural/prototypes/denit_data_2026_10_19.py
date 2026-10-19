"""Daily denitrification in Cycles against per-layer states (2026-10-19): corn N=0/150/400, 24 sites. Per day: Cycles' denitrification (profile, kg N/ha), per layer nitrate (kg N/ha from mg/kg x bulk density x thickness), composite_factor, water content / saturation, plus residue/respiration terms.
Saves /tmp/w/denit_data.npz with arrays (days x 4 layers; missing layers zero)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150,400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    Nn={r['date']:r for r in rd(d+"dailyN.csv")}; L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; W={r['date']:r for r in rd(d+"dailyWater.csv")}; Cc={r['date']:r for r in rd(d+"dailySoilC.csv")}; shutil.rmtree(d,ignore_errors=True)
    sat=[m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC)["sat"] for l in soil]; rows=[]
    for dt,l in L.items():
        if dt not in Nn or dt not in W or dt not in Cc or int(dt[:4])<1982: continue
        row=[N,float(Nn[dt]['denitrification']),float(Nn[dt]['N2O_from_denitrification']),float(Cc[dt]['soil_organic_matter_respired_carbon']),float(Cc[dt]['residue_respired_carbon'])]
        for i in range(1,5):
            if f'NO3.{i}' in l:
                th=float(l[f'soil_organic_carbon.{i}']); bd=float(l[f'bulk_density.{i}']); thick=float(l[f'thickness.{i}']) if f'thickness.{i}' in l else soil[i-1]['thick']
                row+= [float(l[f'NO3.{i}'])*bd*thick*10.0,float(l[f'NO3.{i}']),float(l[f'composite_factor.{i}']),float(W[dt][f'soil_moisture_content.{i}'])/sat[i-1]]
            else: row+=[0,0,0,0]
        rows.append(row)
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150,400)]),[])); np.savez('/tmp/w/denit_data.npz',A=A); print(A.shape)
