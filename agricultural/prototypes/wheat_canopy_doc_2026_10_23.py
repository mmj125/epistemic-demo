"""Does the documented canopy shape (paper Eq. 6, hard-coded a,b,c,d = 6,-20,-15,16) fit Cycles' winter wheat canopy with only a maximum cover and a thermal-time scale free? (2026-10-23)
Cycles wheat daily output, 24 sites, N=150 with FALLN=60, unstressed days only (water and N stress under 2 percent). Fits: (1) documented shape, free eix and TTm; (2) all four shape numbers free (the best any form can do);
(3) the engine's current refit shape (5,-14,-15,16) with free eix, TTm. x = Cycles' thermal_time / TTm."""
import os,sys,json,csv,shutil,subprocess
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from scipy.optimize import least_squares
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    fs=site+"wheatcd"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=150
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    CR=rd(d+"dailyWinterWheat.csv"); shutil.rmtree(d,ignore_errors=True); rows=[]
    for x in CR:
        if x['biomass']=='-999': continue
        rows.append((float(x['thermal_time']),float(x['radiation_interception']),float(x['water_stress']),float(x['nitrogen_stress']),x['stage']))
    return rows
if __name__=="__main__":
    R=sum(Pool(4).map(one,sorted(S)),[]); A=np.array([(r[0],r[1],r[2],r[3]) for r in R]); print(len(A),"days; max thermal_time",A[:,0].max())
    k=(A[:,2]<2)&(A[:,3]<2)&(A[:,0]>0); T=A[k,0]; Y=A[k,1]; print(len(T),"unstressed days")
    f=lambda x,a,b,c,d,e,tm: e/(1+np.exp(a+b*x/tm)+np.exp(c+d*x/tm))
    def fit(free,init,fixed):
        def res(p):
            q=dict(fixed); q.update(dict(zip(free,p))); return f(T,q['a'],q['b'],q['c'],q['d'],q['e'],q['tm'])-Y
        r=least_squares(res,[init[n] for n in free]); q=dict(fixed); q.update(dict(zip(free,r.x))); return q,np.sqrt(np.mean(r.fun**2))
    doc=dict(a=6,b=-20,c=-15,d=16); ini=dict(e=0.9,tm=2200.0,a=6,b=-20,c=-15,d=16)
    for name,free,fixed in (("documented shape, free eix and TTm",["e","tm"],doc),("engine refit shape (5,-14,-15,16), free eix and TTm",["e","tm"],dict(a=5,b=-14,c=-15,d=16)),("all six free",["a","b","c","d","e","tm"],{})):
        q,rms=fit(free,ini,fixed); print(f"{name:52s} rms {rms:.4f}  "+" ".join(f"{n}={q[n]:.2f}" for n in ("a","b","c","d","e","tm")))
