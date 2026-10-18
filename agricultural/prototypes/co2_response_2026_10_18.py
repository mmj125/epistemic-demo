"""Cycles' own CO2 response (2026-10-18). Paper Sec 2.5: eps_R and eps_W are given at a reference CO2 and scaled as CO2 changes. Runs Cycles corn at N=400 (no N stress) with CO2_LEVEL fixed at 300, 400, 500 ppm
on the first sites of the 24-site set; reports mean total biomass and grain, the log-log response exponent (d ln biomass / d ln CO2) overall and by dryness (mean seasonal water stress)."""
import os,sys,json,csv,shutil,subprocess,re
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="400"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); LV=(300,400,500)
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,co2=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); ctrl=f"{m.CY}/input/{site}N400.ctrl"; t=open(ctrl).read(); t=re.sub(r"(?m)^CO2_LEVEL\s+\S+",f"CO2_LEVEL               {co2}",t); open(ctrl,'w').write(t)
    subprocess.run(["./Cycles",f"{site}N400"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N400/"
    H=rd(d+"harvest.csv"); D=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    tb=np.mean([float(r['total_biomass']) for r in H[1:] if r['total_biomass']!='-999']); gy=np.mean([float(r['grain_yield']) for r in H[1:]])
    ws=np.mean([float(r['water_stress']) for r in D if r['water_stress']!='-999' and r['stage'] in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH')])
    return site,co2,tb,gy,ws
if __name__=="__main__":
    ks=sorted(S)[:int(sys.argv[1])]
    with Pool(4) as p: R=p.map(one,[(k,c) for k in ks for c in LV])
    by={}
    for s,c,tb,gy,ws in R: by.setdefault(s,{})[c]=(tb,gy,ws)
    ex=[];rows=[]
    for s,v in by.items():
        if len(v)<3: continue
        e=np.log(v[500][0]/v[300][0])/np.log(500/300); eg=np.log(v[500][1]/v[300][1])/np.log(500/300); rows.append((v[400][2],e,eg)); print(f"{s:16s} water stress {v[400][2]:5.1f}%  biomass {v[300][0]:.2f}/{v[400][0]:.2f}/{v[500][0]:.2f}  exponent biomass {e:+.3f} grain {eg:+.3f}")
    A=np.array(rows); print('mean exponent biomass %.3f grain %.3f ; corr(exponent, water stress) %.2f'%(A[:,1].mean(),A[:,2].mean(),np.corrcoef(A[:,0],A[:,1])[0,1]))
