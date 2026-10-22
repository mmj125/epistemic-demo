import os,sys,json,csv,shutil,subprocess,datetime
os.environ["REGIONAL"]="0"; os.environ["FALLN"]="60"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite_wheat as w, run_validation_multisite as m
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
site=sys.argv[1]; N=int(sys.argv[2]); S=json.load(open('sitesets/fresh94.json')); lat,lon=S[site]
wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
fs=site+"wheatA"; m.write_inputs(fs,lat,lon,wx,soil,cl); open(f"{w.CY}/input/{fs}N{N}.operation","w").write(w.OP+w.fert_text(N))
subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=w.CY,capture_output=True); d=f"{w.CY}/output/{fs}N{N}/"
files=[f for f in os.listdir(d) if f.startswith('daily') and 'Wheat' in f]; print(files)
C=rd(d+files[0]); DN=rd(d+'dailyN.csv'); DNd={r['date']:r for r in DN}
R=w.engine_chain(wx,soil,cl,N,None)
def cyc_year(y):
    rows=[r for r in C if r['date'].startswith(str(y)) and r['biomass'] not in ('-999',)]
    try:
        a=[(float(r['nitrogen_stress']),float(r['water_stress']),float(r['aboveground_biomass']),float(r['total_nitrogen'])) for r in rows if float(r['aboveground_biomass'])>0]
    except: return None
    if not a: return None
    a=np.array(a); return 1-a[:,0].mean()/100, 1-a[:,1].mean()/100, a[:,2].max(), a[:,3].max()
print("year | Cycles: N factor, water factor, max ag biomass, max plant N | engine: N factor, water factor, max ag, max plant N")
for y in sorted(R)[:14]:
    c=cyc_year(y); h=R[y]["history"]
    e=(np.mean([x["n_stress"] for x in h]),np.mean([x["water_stress"] for x in h]),max(x["ag_mg_ha"] for x in h),max(x["n_plant"] for x in h))
    d0=datetime.date(y-1,1,1)+datetime.timedelta(h[0]["doy"]-1) if False else None
    start=datetime.date(y-1,10,15); cn=0.0; cl_=0.0; cnit=0.0
    for k in range(len(h)):
        dt=(start+datetime.timedelta(k)).isoformat()
        if dt in DNd: cn+=float(DNd[dt]['net_mineralization']); cnit+=float(DNd[dt]['nitrification'])
    en=sum(x["netmin"] for x in h); eni=sum(x["nitr"] for x in h)
    print(y, None if c is None else tuple(round(v,2) for v in c), "|", tuple(round(float(v),2) for v in e), "| net min season Cycles %.0f engine %.0f ; nitrification Cycles %.0f engine %.0f"%(cn,en,cnit,eni))
shutil.rmtree(d,ignore_errors=True)
