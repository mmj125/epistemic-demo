import os,sys,json,csv,datetime,shutil,subprocess
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E
from wheat_coupling_2026_10_17 import sub
CY=m.CY
site=os.environ.get("SITE","f018_380_800"); Y=int(os.environ.get("Y","1995")); N=int(os.environ.get("N","150"))
S=json.load(open("sitesets/fresh94.json")); lat,lon=S[site]
wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
fs=site+"wheat"; m.write_inputs(fs,lat,lon,wx,soil,cl); open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
C={}; F={}
for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
    if x["date"][0]=="#" or x["biomass"]=="-999": continue
    dt=datetime.date.fromisoformat(x["date"]); py=dt.year if dt.month>=8 else dt.year-1; doy=dt.timetuple().tm_yday
    C[(py,dt)]=x
    f=F.setdefault(py,{"canopy":{},"wclock":{},"nclock":{},"nstress":{}}); f["wclock"][doy]=1-float(x["water_stress"])/100; f["nclock"][doy]=1-float(x["nitrogen_stress"])/100; f["nstress"][doy]=f["nclock"][doy]
shutil.rmtree(d,ignore_errors=True)
E.FORCE_SERIES=F; E.DIAG_STATE=[]; log=[]; _o=E.canopy_cover_two
E.canopy_cover_two=lambda xc,xt,eix=1.0,shape=None:(log.append((xc,xt)),_o(xc,xt,eix,shape) if shape is not None else _o(xc,xt,eix))[1]
W.engine_chain(wx,soil,cl,N,1.0); D=E.DIAG_STATE
eng={(y,doy):(eie,xc,xt) for (y,doy,eie,ns,pn),(xc,xt) in zip(D,log)}
print("date  Cycles: stage TT vern canopy Nstr Wstr | engine: canopy xc*1800 xt*1800")
for (py,dt),x in sorted(C.items()):
    if py!=Y-1 or dt.day not in (1,10,20): continue
    e=eng.get((py,dt.timetuple().tm_yday))
    print(dt, x["stage"][:10].ljust(10), "%7.1f %6.1f %.3f %5.1f %5.1f"%(float(x["thermal_time"]),float(x["vernalization"]),float(x["radiation_interception"]),float(x["nitrogen_stress"]),float(x["water_stress"])), "|", ("%.3f %7.1f %7.1f"%(e[0],e[1]*1800,e[2]*1800)) if e else "-")
