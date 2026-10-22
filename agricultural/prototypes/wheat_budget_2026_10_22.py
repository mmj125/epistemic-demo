import os,sys,json,csv,shutil,subprocess,datetime
os.environ["REGIONAL"]="0"; os.environ["FALLN"]="60"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite_wheat as w, run_validation_multisite as m
from multiprocessing import Pool
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
S=json.load(open('sitesets/fresh94.json'))
def one(a):
    site,N=a; lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatB"; m.write_inputs(fs,lat,lon,wx,soil,cl); open(f"{w.CY}/input/{fs}N{N}.operation","w").write(w.OP+w.fert_text(N))
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=w.CY,capture_output=True); d=f"{w.CY}/output/{fs}N{N}/"
    fl=[f for f in os.listdir(d) if f.startswith("daily") and "Wheat" in f]
    if not fl: shutil.rmtree(d,ignore_errors=True); return N,None
    C=rd(d+fl[0]); DN={r['date']:r for r in rd(d+"dailyN.csv")}; shutil.rmtree(d,ignore_errors=True)
    R=w.engine_chain(wx,soil,cl,N,None); out=[]
    for y in sorted(R):
        if not 1985<=y<=2010: continue
        h=R[y]["history"]; rows=[r for r in C if r['date'].startswith(str(y)) and float(r['aboveground_biomass'])>0]
        if not rows: continue
        a=np.array([(float(r['aboveground_biomass']),float(r['total_nitrogen']),float(r['nitrogen_stress'])) for r in rows])
        start=datetime.date(y-1,10,15); cn=cnit=0.0
        for k in range(len(h)):
            dt=(start+datetime.timedelta(k)).isoformat()
            if dt in DN: cn+=float(DN[dt]['net_mineralization']); cnit+=float(DN[dt]['nitrification'])
        out.append([a[:,0].max(),a[:,1].max(),1-a[:,2].mean()/100,cn,cnit, max(x["ag_mg_ha"] for x in h),max(x["n_plant"] for x in h),np.mean([x["n_stress"] for x in h]),sum(x["netmin"] for x in h),sum(x["nitr"] for x in h)])
    return N,(np.mean(out,0) if out else None)
if __name__=="__main__":
    ks=sorted(S); sites=[k for k in sorted(json.load(open('/tmp/w/s24.json')))][:0]
    pick=["f070_340_915","f033_315_905","f082_350_765","f010_350_835","f018_380_800","f039_455_990","f006_485_975","f030_410_970"]
    R=Pool(4).map(one,[(s,N) for s in pick for N in (0,150)])
    for N in (0,150):
        a=np.mean([r[1] for r in R if r[0]==N and r[1] is not None],0)
        print(f"N={N} (8 sites, season windows Oct 15 to harvest): ag biomass Cycles {a[0]:.1f} engine {a[5]:.1f} | plant N {a[1]:.0f} vs {a[6]:.0f} | N factor {a[2]:.2f} vs {a[7]:.2f} | net min {a[3]:.0f} vs {a[8]:.0f} | nitrification {a[4]:.0f} vs {a[9]:.0f}")
