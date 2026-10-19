"""Soil organic matter respiration and Cs change per site, engine vs Cycles (2026-10-19): corn N=0, 24 sites, 1982-2016 means. Cycles: dailySoilC soil_organic_matter_respired_carbon, humified_carbon, residue_respired_carbon (Mg C/ha); engine: SIXPOOL_DIAG cs_loss and humification inputs.
Ratios against the site's layer-1 Cs/Csx."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    C=rd(d+"dailySoilC.csv"); shutil.rmtree(d,ignore_errors=True)
    cy=[0,0,0,0]
    for r in C:
        if int(r['date'][:4])>=1982: cy[0]+=float(r['soil_organic_matter_respired_carbon']); cy[1]+=float(r['humified_carbon']); cy[2]+=float(r['residue_respired_carbon']); cy[3]+=1
    E.SIXPOOL_DIAG=[]; E.DIAG_NFLUX=[]; E.DIAG_NSEASON=[]; E.DIAG_CPOOL=[]; m.engine(site,wx,soil,cl,0,'leadin')
    # per-day aggregation: keep entries only for years >= 1982 using DIAG_CPOOL year markers is awkward; use all entries and divide by total days simulated
    D=E.SIXPOOL_DIAG; n=len(E.DIAG_CPOOL); E.SIXPOOL_DIAG=None; E.DIAG_NFLUX=None; E.DIAG_NSEASON=None; E.DIAG_CPOOL=None
    cs_loss=sum(e[0] for e in D); res_co2=sum(e[2] for e in D); cm_gain=sum(e[8] for e in D); cs_gain=sum(e[9] for e in D); co2_cm=sum(e[10] for e in D)
    l=soil[0]; csx=E.sixpool_csx_pct(l['clay']/100.0 if l['clay']>1 else l['clay']); 
    return site,l['soc']/csx,cy,(cs_loss,res_co2,cm_gain,cs_gain,co2_cm,n)
if __name__=="__main__":
    R=Pool(4).map(one,sorted(S)); R.sort(key=lambda x:x[1])
    print('Cs/Csx | Cycles per day: SOM respired, humified, residue respired (kg C/ha/day) | engine per day: Cs loss, residue CO2, microbial gain from residue, Cs gain, microbial CO2 | ratios engine/Cycles: Cs respiration, residue CO2')
    for site,r,cy,en in R:
        n=cy[3]; N=en[5]
        print(f' {r:.2f} | {cy[0]/n*1000:6.2f} {cy[1]/n*1000:6.2f} {cy[2]/n*1000:6.2f} | {en[0]/N*1000:6.2f} {en[1]/N*1000:6.2f} {en[2]/N*1000:6.2f} {en[3]/N*1000:6.2f} {en[4]/N*1000:6.2f} | {en[0]/N/(cy[0]/n):.2f} {en[1]/N/max(cy[2]/n,1e-9):.2f}  {site}')
