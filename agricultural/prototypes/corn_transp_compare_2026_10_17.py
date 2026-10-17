"""With Cycles' daily canopy forced into the engine (so demand is comparable), compare the engine's potential and actual transpiration and water multiplier with Cycles' potential_transpiration, transpiration (dailyWater.csv) and water stress, by thermal-time bin. Corn, 24 sites, N=150. Usage: ENGINE_OVR=... python3 corn_transp_compare_2026_10_17.py"""
import os,sys,json,shutil,csv,datetime,subprocess,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); N=150
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; C={}
    for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        dt=datetime.date.fromisoformat(x['date']); C.setdefault(dt.year,{})[dt.timetuple().tm_yday]=[1-float(x['water_stress'])/100,float(x['thermal_time']),float(x['potential_transpiration']),None]
    for x in csv.DictReader(open(d+"dailyWater.csv")):
        if x['date'][0]=='#':continue
        dt=datetime.date.fromisoformat(x['date'])
        if dt.year in C and dt.timetuple().tm_yday in C[dt.year]: C[dt.year][dt.timetuple().tm_yday][3]=float(x['transpiration'])
    F=forcelib.force(site,N,("canopy",)); shutil.rmtree(d,ignore_errors=True)
    E.FORCE_SERIES={y:{"canopy":v["canopy"]} for y,v in F.items()}
    E.DIAG_WATER=[]; m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_WATER; E.DIAG_WATER=None; E.FORCE_SERIES=None
    out=[]
    for y,doy,w,tt,trp,tra,_td in S:
        if y in C and doy in C[y] and C[y][doy][3] is not None:
            c=C[y][doy]; out.append((int(c[1]//300)*300,c[0],w,c[2],trp,c[3],tra))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    for lo in range(0,1800,300):
        q=[r for r in R if r[0]==lo]
        if q: print(f"TT {lo}: water mult C {st.mean(r[1] for r in q):.3f} E {st.mean(r[2] for r in q):.3f} | TRp C {st.mean(r[3] for r in q):.2f} E {st.mean(r[4] for r in q):.2f} | actual transp C {st.mean(r[5] for r in q):.2f} E {st.mean(r[6] for r in q):.2f} mm/d")
