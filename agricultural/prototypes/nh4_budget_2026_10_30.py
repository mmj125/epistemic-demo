"""NH4 pool budget (2026-10-30): annual nitrification and volatilization of the engine (wrapped flux functions) against Cycles (annualN.csv), corn, same sites, continuous 1980 to 2016. Usage: python3 nh4_budget_2026_10_30.py N NSITES"""
import os,sys,json,subprocess,shutil,csv
os.environ["CROPSEL"]="corn"; os.environ["REGIONAL"]="0"; os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
NR=int(sys.argv[1]) if len(sys.argv)>1 else 150; NS=int(sys.argv[2]) if len(sys.argv)>2 else 8
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
for _o in os.environ.get('OVR','').split(';'):
    if _o: _k,_v=_o.split('=',1); setattr(E,_k,eval(_v))
acc={"nit":0.0,"vol":0.0}
_n=E.nitrification_flux_ratio; _v=E.volatilization_flux
def nw(*a,**k):
    r=_n(*a,**k); acc["nit"]+=r; return r
def vw(*a,**k):
    r=_v(*a,**k); acc["vol"]+=r; return r
E.nitrification_flux_ratio=nw; E.volatilization_flux=vw
rows=[]
for site in sorted(S)[:NS]:
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    acc["nit"]=acc["vol"]=0.0
    r=m.engine(site,wx,soil,cl,NR,'leadin'); yrs=len(r)
    en=acc["nit"]/yrs; ev=acc["vol"]/yrs
    subprocess.run(["./Cycles",f"{site}N{NR}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{NR}/"
    A=[x for x in csv.DictReader(l for l in open(d+"annualN.csv") if not l.startswith('#'))]; shutil.rmtree(d,ignore_errors=True)
    cn=np.mean([float(a['nitrification']) for a in A]); cv=np.mean([float(a['volatilization']) for a in A])
    rows.append((en,ev,cn,cv))
a=np.array(rows)
print(f"corn N={NR}, {len(a)} sites, mean annual kg N/ha: nitrification engine {a[:,0].mean():.0f} Cycles {a[:,2].mean():.0f} (ratio {a[:,0].mean()/a[:,2].mean():.2f}); volatilization engine {a[:,1].mean():.1f} Cycles {a[:,3].mean():.1f} (ratio {a[:,1].mean()/a[:,3].mean():.2f})")
print("per-site nitrification engine/Cycles:",np.round(a[:,0]/a[:,2],2).tolist())
