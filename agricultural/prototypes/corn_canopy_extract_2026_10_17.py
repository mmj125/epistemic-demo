"""Extract Cycles v1.5.20 daily corn canopy inputs for the offline canopy-form test (24 sites, N=0 and 150): per site-year arrays of doy, thermal_time, interception, water and N stress multipliers. Writes /tmp/w/canopy_daily_24.json."""
import os,sys,json,shutil,csv,datetime,subprocess
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; Y={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999':continue
            dt=datetime.date.fromisoformat(x['date']); Y.setdefault(dt.year,[]).append((dt.timetuple().tm_yday,float(x['thermal_time']),float(x['radiation_interception']),1-float(x['water_stress'])/100,1-float(x['nitrogen_stress'])/100))
        shutil.rmtree(d,ignore_errors=True)
        for y,L in Y.items():
            if len(L)>=30: out.append(dict(site=site,N=N,y=y,d=L))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    json.dump(R,open("/tmp/w/canopy_daily_24.json","w")); print(len(R),"site-years")
