import os,sys,json,csv,shutil,subprocess,datetime
os.environ["REGIONAL"]="0"; os.environ["FALLN"]="60"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite_wheat as w, run_validation_multisite as m
from multiprocessing import Pool
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
S=json.load(open('sitesets/fresh94.json'))
def one(a):
    site,N=a; lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,name=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheatC"; m.write_inputs(fs,lat,lon,wx,soil,cl); open(f"{w.CY}/input/{fs}N{N}.operation","w").write(w.OP+w.fert_text(N))
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=w.CY,capture_output=True); d=f"{w.CY}/output/{fs}N{N}/"
    fl=[f for f in os.listdir(d) if f.startswith("daily") and "Wheat" in f]
    if not fl: shutil.rmtree(d,ignore_errors=True); return []
    C={r['date']:r for r in rd(d+fl[0])}; DN=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    rows=[]
    for y in range(1985,2011):
        win=[r for r in DN if datetime.date(y-1,10,20).isoformat()<=r['date']<=datetime.date(y,7,31).isoformat()]
        if len(win)<250: continue
        pn=[float(C[r['date']]['total_nitrogen']) for r in win if r['date'] in C and float(C[r['date']]['total_nitrogen'])>=0]
        if not pn: continue
        up=max(pn)
        fert=0.0
        if N>0: fert=w.FALLN*0+ (N-w.FALLN)   # spring N (DOY 75); the fall N (DOY 289, Oct 16) is also inside the window
        fert=N if N>0 else 0.0
        pool0=float(win[0]['profile_soil_NO3'])+float(win[0]['profile_soil_NH4']); pool1=float(win[-1]['profile_soil_NO3'])+float(win[-1]['profile_soil_NH4'])
        nm=sum(float(r['net_mineralization']) for r in win); lo=sum(float(r['NO3_leaching'])+float(r['NH4_leaching'])+float(r['NO3_bypass'])+float(r['NH4_bypass'])+float(r['denitrification'])+float(r['volatilization']) for r in win)
        res=(pool1-pool0)-(fert+nm-up-lo)
        rows.append([up,res])
    return rows
if __name__=="__main__":
    pick=["f070_340_915","f082_350_765","f010_350_835","f018_380_800","f039_455_990","f006_485_975","f030_410_970","f012_380_990"]
    R=Pool(4).map(one,[(s,0) for s in pick]); A=np.array([r for x in R for r in x])
    sl=np.polyfit(A[:,0],A[:,1],1)
    print(f"N=0 wheat, {len(A)} site-years: mean plant N {A[:,0].mean():.0f}, mean budget residual {A[:,1].mean():+.1f}; residual = {sl[0]:+.3f} x plant N {sl[1]:+.1f}; corr {np.corrcoef(A[:,0],A[:,1])[0,1]:+.2f}")
