"""Extract Cycles v1.5.20 daily winter wheat canopy inputs (16 fresh sites, N=0 and 150, FALLN=60 chain) for the offline canopy-form test. Writes /tmp/w/wheat_canopy_daily.json."""
import os,sys,json,csv,datetime,shutil,subprocess
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ.setdefault("FALLN","60"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"+("F%d"%W.FALLN if W.FALLN else ""); m.write_inputs(fs,lat,lon,wx,soil,cl); out=[]
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"; Y={}
        for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": continue
            dt=datetime.date.fromisoformat(x["date"]); py=dt.year if dt.month>=8 else dt.year-1
            Y.setdefault(py,[]).append((dt.timetuple().tm_yday,float(x["thermal_time"]),float(x["radiation_interception"]),1-float(x["water_stress"])/100,1-float(x["nitrogen_stress"])/100))
        shutil.rmtree(d,ignore_errors=True)
        E.DIAG_WATER=[]; W.engine_chain(wx,soil,cl,N,1.0); DW=E.DIAG_WATER; E.DIAG_WATER=None
        td={}
        seasons={}
        for y,doy,w,tt,trp,tra,tdv in DW: seasons.setdefault(y,[]).append((doy,tdv))
        for y,L in seasons.items():
            d0=L[0][0]; yr=y
            for doy,tdv in L:
                if doy<d0 and yr==y: yr=y+1
                td[(yr,doy)]=tdv
        for y,L in Y.items():
            if len(L)>=60 and y>1981:
                rows=[]
                for doy,tt,ci,w,n in L:
                    yr=y if doy>=200 else y+1
                    rows.append((doy,tt,ci,w,n,td.get((yr,doy))))
                out.append(dict(site=site,N=N,y=y,d=rows))
    return out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[0::6][:16]
    with Pool(4) as p: R=sum(p.map(one,[(k,S[k]) for k in ks]),[])
    json.dump(R,open("/tmp/w/wheat_canopy_daily.json","w")); print(len(R),"site-years")
