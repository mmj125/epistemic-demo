"""Engine vs Cycles daily water stress multiplier by thermal-time bin (corn, 24 sites, free engine, N=150), to see whether the engine's water state is too severe/mild where the canopy clock uses it. Usage: ENGINE_OVR=... python3 corn_water_state_2026_10_17.py"""
import os,sys,json,shutil,csv,datetime,subprocess,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); N=150
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; C={}
    for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
        if x['date'][0]=='#' or x['biomass']=='-999':continue
        dt=datetime.date.fromisoformat(x['date']); C.setdefault(dt.year,{})[dt.timetuple().tm_yday]=(1-float(x['water_stress'])/100,float(x['thermal_time']))
    shutil.rmtree(d,ignore_errors=True)
    E.DIAG_WATER=[]; m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_WATER; E.DIAG_WATER=None
    out=[]
    for y,doy,w,tt,*_ in S:
        if y in C and doy in C[y]:
            out.append((int(C[y][doy][1]//300)*300,C[y][doy][0],w))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    for lo in range(0,1800,300):
        q=[r for r in R if r[0]==lo]
        if q: print(f"TT {lo}-{lo+300}: Cycles water mult {st.mean(r[1] for r in q):.3f} engine {st.mean(r[2] for r in q):.3f} (n {len(q)}); share days mult<0.8: Cycles {sum(r[1]<.8 for r in q)/len(q):.2f} engine {sum(r[2]<.8 for r in q)/len(q):.2f}")
