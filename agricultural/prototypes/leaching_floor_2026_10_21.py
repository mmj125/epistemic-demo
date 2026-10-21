import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
def ann(d):
    rows=[l.strip().split(",") for l in open(d+"annualN.csv").readlines()[2:] if l.strip()]
    hdr=open(d+"annualN.csv").readline().strip().split(",")
    ix={h:i for i,h in enumerate(hdr)}
    out={}
    for r in rows:
        y=int(r[0])
        if y>=1982: out[y]=(float(r[ix.get('NO3_leaching',ix.get('leaching',3))]) if ('NO3_leaching' in ix or 'leaching' in ix) else np.nan, float(r[10]) if len(r)>10 else np.nan)
    return out
def run(site,dlat,dlon,tag):
    lat,lon=S[site]; lat+=dlat; lon+=dlon
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(S[site][0],S[site][1]); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=f"{site}{tag}"; m.write_inputs(nm,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{nm}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N150/"
    hdr=open(d+"annualN.csv").readline().strip().split(","); rows=[l.strip().split(",") for l in open(d+"annualN.csv").readlines()[2:] if l.strip()]
    ix={h:i for i,h in enumerate(hdr)}; ks=[h for h in hdr if 'leach' in h.lower()]
    v=np.mean([sum(float(r[ix[k]]) for k in ks) for r in rows if int(r[0])>=1982]); shutil.rmtree(d,ignore_errors=True); return v
def one(site):
    return site,run(site,0,0,"_b"),run(site,0.5,0.0,"_n"),run(site,0.0,0.5,"_e")
if __name__=="__main__":
    R=Pool(4).map(one,SITES)
    b=np.array([r[1] for r in R]); n=np.array([r[2] for r in R]); e=np.array([r[3] for r in R])
    f=lambda x,y: np.sqrt(np.mean((np.log(x+.5)-np.log(y+.5))**2))
    print("Cycles leaching N=150, mean kg/ha: base %.1f north-cell %.1f east-cell %.1f"%(b.mean(),n.mean(),e.mean()))
    print("rms log (+0.5) base vs north cell %.2f, base vs east cell %.2f"%(f(b,n),f(b,e)))
