"""Nitrate by layer, engine vs Cycles (dailySoilLayersCN NO3.k), monthly mean over all years, N=150, one site. Usage: SITE=f018_380_800 python3 leach_layers_2026_10_17.py"""
import os,sys,json,shutil,csv,subprocess,datetime,statistics as st
os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
S=json.load(open('/tmp/w/s24.json')); site=os.environ.get("SITE","f018_380_800"); N=int(os.environ.get("NN","150")); lat,lon=S[site]
wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
m.write_inputs(site,lat,lon,wx,soil,cl)
subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
C={}
for x in csv.DictReader(open(d+"dailySoilLayersCN.csv")):
    if x['date'][0]=='#': continue
    dt=datetime.date.fromisoformat(x['date']); k=sorted(c for c in x if c.startswith('NO3.'))
    C.setdefault((dt.year,dt.month),[]).append([float(x[c]) for c in k])
shutil.rmtree(d,ignore_errors=True)
E.DIAG_NO3=[]; m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_NO3; E.DIAG_NO3=None
Ev={}
for y,doy,v in D:
    if y is None: continue
    mo=(datetime.date(y,1,1)+datetime.timedelta(doy-1)).month; Ev.setdefault((y,mo),[]).append(v)
nl=len(next(iter(C.values()))[0]); print("layers Cycles",nl,"engine",len(next(iter(Ev.values()))[0]))
for mo in range(1,13):
    c=[st.mean(st.mean(r[j] for r in C[(y,mo)]) for y in range(1980,2017) if (y,mo) in C and (y,mo) in Ev) for j in range(nl)]
    e=[st.mean(st.mean(r[j] for r in Ev[(y,mo)]) for y in range(1980,2017) if (y,mo) in C and (y,mo) in Ev) for j in range(min(nl,len(next(iter(Ev.values()))[0])))]
    print(mo,"Cycles",[round(x,1) for x in c],"engine",[round(x,1) for x in e])
