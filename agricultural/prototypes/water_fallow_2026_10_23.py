"""Off-season (fallow) water balance, engine against Cycles, corn N=150, 24 sites, joined by date (2026-10-23): profile water, soil evaporation, residue evaporation, runoff and drainage by month, for the bare-soil windows
(January 1 to planting, harvest to December 31). Engine terms from E.DIAG_FALLOW_WATER, Cycles from dailyWater.csv. Usage: python3 water_fallow_2026_10_23.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    W=rd(d+"dailyWater.csv"); shutil.rmtree(d,ignore_errors=True)
    nl=len([k for k in W[0] if k.startswith("soil_moisture_content.")]); th=[l["thick"] for l in soil][:nl]
    cyc={}
    for w in W:
        dt=datetime.date.fromisoformat(w['date'])
        pw=sum(float(w[f'soil_moisture_content.{i+1}'])*th[i]*1000 for i in range(nl))
        cyc[(dt.year,dt.timetuple().tm_yday)]=(pw,float(w['soil_evaporation']),float(w['residue_evaporation']),float(w['runoff']),float(w['drainage'])+float(w.get('bypass',0) or 0),float(w['infiltration']))
    E.DIAG_FALLOW_WATER=[]; m.engine(site,wx,soil,cl,150,'leadin'); D=E.DIAG_FALLOW_WATER; E.DIAG_FALLOW_WATER=None; rows=[]
    for (y,doy,pp,re,roff,drain,ev,eto,pw,rc) in D:
        if y is None or y<1982: continue
        k=(y,doy)
        if k in cyc:
            c=cyc[k]; month=(datetime.date(y,1,1)+datetime.timedelta(days=doy-1)).month
            rows.append([month,c[0],pw,c[1],ev,c[2],re,c[3],roff,c[4],drain,pp])
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/water_fallow.npy',A); print(len(A),"fallow days")
    print("month n | profile water mm Cycles engine (diff) | soil evap Cycles engine | residue evap Cycles engine | runoff Cycles engine | drainage Cycles engine   (mm/day)")
    for mo in range(1,13):
        k=A[:,0]==mo
        if k.sum()>200: print(f" {mo:2d} {k.sum():6d} | {A[k,1].mean():6.1f} {A[k,2].mean():6.1f} ({A[k,2].mean()-A[k,1].mean():+5.1f}) | {A[k,3].mean():.2f} {A[k,4].mean():.2f} | {A[k,5].mean():.2f} {A[k,6].mean():.2f} | {A[k,7].mean():.2f} {A[k,8].mean():.2f} | {A[k,9].mean():.2f} {A[k,10].mean():.2f}")
    print(f"all fallow days: profile water Cycles {A[:,1].mean():.1f} engine {A[:,2].mean():.1f}; evap {A[:,3].mean():.2f} {A[:,4].mean():.2f}; residue evap {A[:,5].mean():.2f} {A[:,6].mean():.2f}; runoff {A[:,7].mean():.2f} {A[:,8].mean():.2f}; drainage {A[:,9].mean():.2f} {A[:,10].mean():.2f}; precip {A[:,11].mean():.2f}")
