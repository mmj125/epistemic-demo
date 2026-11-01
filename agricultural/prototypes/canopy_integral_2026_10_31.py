"""Does Cycles' canopy follow the stress-weighted integral of the derivative of Eq. 6 (paper: 'the first derivative of Eq. 6 is used to estimate the rate of change of the canopy ... the rate is reduced by N stress')?
Uses the canopy law read from the unstressed constant-weather designed run (plateau 0.952, a 6.10, b -20.83, c -16.07, d 15.55) and Cycles' own daily thermal time, N stress and water stress from realistic runs of 12 sites at N=0 and 150.
Compares, per day, the predicted canopy against Cycles' radiation_interception: no stress, and the integral with rate multiplier (1-N)^p (1-W)^q for several p, q."""
import os,sys,json,csv,shutil,subprocess,numpy as np
os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m
S=json.load(open('/tmp/w/s24.json')); sites=sorted(S)[:12]
P,A,B,C,Dd=0.952,6.10,-20.83,-16.07,15.55
def f(x): return P/(1+np.exp(A+B*x)+np.exp(C+Dd*x))
def fp(x):
    u=np.exp(A+B*x); v=np.exp(C+Dd*x); return -P*(B*u+Dd*v)/(1+u+v)**2
def seasons(site,N):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    D=[r for r in csv.DictReader(open(d+"dailyCornRM.90.csv")) if r['date'][0]!='#']; shutil.rmtree(d,ignore_errors=True)
    out={}
    for r in D:
        if r['biomass']=='-999' or r['crop']=='FALLOW': continue
        out.setdefault(r['date'][:4],[]).append((float(r['thermal_time'])/1800.0,float(r['radiation_interception']),float(r['nitrogen_stress'])/100,float(r['water_stress'])/100,r['stage'],r['date']))
    return out
if __name__=="__main__":
    from multiprocessing import Pool
    jobs=[(s,N) for s in sites for N in (0,150)]
    with Pool(4) as p: R=p.starmap(seasons,jobs)
    variants=[("law of x, no stress",None)]+[(f"integral (1-N)^{pp} (1-W)^{qq}",(pp,qq)) for pp,qq in ((0,0),(1,0),(1,1),(2,1),(3,1),(1,0.5),(2,0.5),(3,0.5))]
    for lbl,v in variants:
        err=[];errl=[]
        for out in R:
            for y,rs in out.items():
                xs=np.array([r[0] for r in rs]); ys=np.array([r[1] for r in rs])
                if v is None: pred=f(np.minimum(xs,1.0))
                else:
                    pred=np.zeros(len(xs)); e=0.0
                    for i in range(1,len(xs)):
                        dx=max(xs[i]-xs[i-1],0.0); mult=(1-rs[i][2])**v[0]*(1-rs[i][3])**v[1]
                        e=max(0.0,e+fp(xs[i])*dx*mult); pred[i]=e
                m_=(xs<=1.0)
                err+=list((pred-ys)[m_]); 
        err=np.array(err); print(f"{lbl:34s} rms {np.sqrt((err**2).mean()):.4f} mean err {err.mean():+.4f}  n {len(err)}",flush=True)
