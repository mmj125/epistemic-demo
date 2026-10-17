"""Engine vs Cycles per-layer soil moisture (dailyWater.csv soil_moisture_content.X) during the corn season, by thermal-time bin, with Cycles' canopy forced (same demand). Reports mean (engine - Cycles) theta as a fraction of the layer's plant-available range (fc-pwp) so layers are comparable. 24 sites, N=150."""
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
    W={}
    rd=csv.DictReader(open(d+"dailyWater.csv")); cols=[c for c in rd.fieldnames if c.startswith("soil_moisture_content")]
    for x in rd:
        if x['date'][0]=='#':continue
        dt=datetime.date.fromisoformat(x['date']); k=(dt.year,dt.timetuple().tm_yday)
        if k in TT: W[k]=[float(x[c]) for c in cols]
    F=forcelib.force(site,N,("canopy",)); shutil.rmtree(d,ignore_errors=True)
    E.FORCE_SERIES={y:{"canopy":v["canopy"]} for y,v in F.items()}
    E.DIAG_THETA=[]; m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_THETA; E.DIAG_THETA=None; E.FORCE_SERIES=None
    lay=soil if isinstance(soil,list) else None
    out=[]
    for y,doy,th in S:
        k=(y,doy)
        if k in W and k in TT: out.append((int(TT[k]//300)*300,th,W[k]))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    for lo in range(0,1800,300):
        q=[r for r in R if r[0]==lo]
        row=[]
        for i in range(9):
            v=[r[1][i]-r[2][i] for r in q if len(r[1])>i and len(r[2])>i]
            row.append(f"{st.mean(v):+.3f}" if v else "  n/a")
        print(f"TT {lo}: mean theta engine-Cycles by layer 1..9 (m3/m3): "+" ".join(row))
