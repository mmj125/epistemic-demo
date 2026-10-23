"""Wheat season-end thermal time, engine against Cycles per site-year (2026-10-23): does the engine's phenology (vernalization, photoperiod, flowering, grain filling) predict the thermal time at which Cycles' wheat matures? 24 sites, N=150, FALLN=60."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ["FALLN"]="60"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    fs=site+"wheatmt"; m.write_inputs(fs,lat,lon,wx,soil,cl); N=150
    open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N)); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    CR=rd(d+"dailyWinterWheat.csv"); shutil.rmtree(d,ignore_errors=True)
    cyc={}; last=None; n=0
    for x in CR:
        if x['biomass']=='-999':
            if last: cyc[int(last[0][:4])]=(last[1],n); last=None; n=0
            continue
        last=(x['date'],float(x['thermal_time'])); n+=1
    if last: cyc[int(last[0][:4])]=(last[1],n)
    R=W.engine_chain(wx,soil,cl,N,None); rows=[]
    for y1,res in R.items():
        h=res.get("history") or []
        if y1 in cyc and h and y1>=1983: rows.append([cyc[y1][0],h[-1]["ttf"]*1800.0,len(h),cyc[y1][1]])
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); print(len(A),"site-years")
    print(f"Cycles season-end thermal time mean {A[:,0].mean():.0f} sd {A[:,0].std():.0f}; engine mean {A[:,1].mean():.0f} sd {A[:,1].std():.0f}; corr {np.corrcoef(A[:,0],A[:,1])[0,1]:.3f}; bias {np.mean(A[:,1]-A[:,0]):+.0f}; rms {np.sqrt(np.mean((A[:,1]-A[:,0])**2)):.0f}")
    print(f"season length days: Cycles mean {A[:,3].mean():.0f} sd {A[:,3].std():.0f}; engine mean {A[:,2].mean():.0f} sd {A[:,2].std():.0f}; corr {np.corrcoef(A[:,2],A[:,3])[0,1]:.3f}; bias {np.mean(A[:,2]-A[:,3]):+.1f} days; rms {np.sqrt(np.mean((A[:,2]-A[:,3])**2)):.1f}")
    print(f"Cycles season-end thermal time vs season length corr {np.corrcoef(A[:,0],A[:,3])[0,1]:.2f}")
    np.save('/tmp/w/wheat_maturity.npy',A)
    k=(A[:,3]>200)&(A[:,2]>150); d=A[k,2]-A[k,3]
    print(f"seasons over 200 days in Cycles ({k.sum()} of {len(A)}): season length corr {np.corrcoef(A[k,2],A[k,3])[0,1]:.3f}, median abs difference {np.median(np.abs(d)):.1f} days, within 10 days {100*np.mean(np.abs(d)<=10):.0f}%, bias {d.mean():+.1f}; Cycles length sd {A[k,3].std():.1f}, engine {A[k,2].std():.1f}")
