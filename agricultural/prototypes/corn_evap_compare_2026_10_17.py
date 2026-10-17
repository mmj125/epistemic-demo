"""Engine vs Cycles in-season soil + residue evaporation (dailyWater.csv soil_evaporation, residue_evaporation) by thermal-time bin, Cycles' canopy forced. Corn, 24 sites, N=150."""
import os,sys,json,shutil,csv,datetime,subprocess,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); N=150
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; TT={}
    for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        dt=datetime.date.fromisoformat(x['date']); TT[(dt.year,dt.timetuple().tm_yday)]=float(x['thermal_time'])
    RC={}
    for x in csv.DictReader(open(d+"dailyResidue.csv")):
        if x["date"][0]=="#":continue
        dt=datetime.date.fromisoformat(x["date"]); RC[(dt.year,dt.timetuple().tm_yday)]=(float(x["radiation_interception"]),float(x["aboveground_residue_biomass"]))
    W={}
    for x in csv.DictReader(open(d+"dailyWater.csv")):
        if x['date'][0]=='#':continue
        dt=datetime.date.fromisoformat(x['date']); k=(dt.year,dt.timetuple().tm_yday)
        if k in TT: W[k]=(float(x['soil_evaporation']),float(x['residue_evaporation']),float(x['transpiration']))
    F=forcelib.force(site,N,("canopy",)); shutil.rmtree(d,ignore_errors=True)
    E.FORCE_SERIES={y:{"canopy":v["canopy"]} for y,v in F.items()}
    E.DIAG_EVAP=[]; m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_EVAP; E.DIAG_EVAP=None; E.FORCE_SERIES=None
    return [(int(TT[(y,doy)]//300)*300,W[(y,doy)],(ev,rev),rc,RC[(y,doy)][0],eto,RC[(y,doy)][1],1-__import__('math').exp(-E.RESIDUE_COVER_K*RC[(y,doy)][1])) for y,doy,ev,rev,eto,rc in S if (y,doy) in W and (y,doy) in RC]
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    for lo in range(0,1800,300):
        q=[r for r in R if r[0]==lo]
        if q: print(f"TT {lo}: soil evap C {st.mean(r[1][0] for r in q):.2f} E {st.mean(r[2][0] for r in q):.2f} | residue evap C {st.mean(r[1][1] for r in q):.2f} E {st.mean(r[2][1] for r in q):.2f} mm/d | residue cover C(reported) {st.mean(r[4] for r in q):.2f} C(1-exp(-.27B)) {st.mean(r[7] for r in q):.2f} E {st.mean(r[3] for r in q):.2f}; Cycles AG residue {st.mean(r[6] for r in q):.2f} Mg/ha")
