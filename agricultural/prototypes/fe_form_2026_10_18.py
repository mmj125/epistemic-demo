"""Form of Cycles' composite decomposition factor (composite_factor.1, dailySoilLayersCN) against layer-1 saturation S = theta/theta_sat and soil temperature (2026-10-18).
Cycles run only (corn, N=150, 24 sites, continuous chain). theta_sat from Saxton and Rawls (engine routine) on the site's layer-1 sand, clay, SOC (OM = 1.724 SOC)."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    CN=rd(d+"dailySoilLayersCN.csv"); W=rd(d+"dailyWater.csv"); Ev=rd(d+"dailyEnviron.csv"); shutil.rmtree(d,ignore_errors=True)
    l0=soil[0]; sr=E.saxton_rawls(l0['sand'],l0['clay'],l0['soc']*1.724); pwp,fc,sat=sr['pwp'],sr['fc'],sr['sat']
    rows=[]
    for a,b,c in zip(CN,W,Ev):
        try: rows.append((float(a['composite_factor.1']),float(b['soil_moisture_content.1']),float(c['soil_temperature.1']),sat,fc,pwp,float(a['NO3.1'])+float(a['NH4.1']),float(a['residue_carbon.1'])))
        except: pass
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack(Pool(4).map(one,sorted(S))); np.save('/tmp/w/fe_form2.npy',A); print('rows',len(A))
