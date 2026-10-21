import os,sys,csv,shutil,subprocess,datetime
os.environ["REGIONAL"]="0"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m, cycles_engine_validate as E
from cover_chain_2026_10_21 import corn_crop
from multiprocessing import Pool
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
def one(si):
    site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"fe"; m.write_inputs(nm,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{nm}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N0/"
    En=rd(d+"dailyEnviron.csv"); L=rd(d+"dailySoilLayersCN.csv"); W=rd(d+"dailyWater.csv"); shutil.rmtree(d,ignore_errors=True)
    cyc=np.zeros((12,4)); cnt=np.zeros(12)
    for a,b,w in zip(En,L,W):
        dt=datetime.date.fromisoformat(a['date'])
        if 1984<=dt.year<=2014:
            cyc[dt.month-1]+=[float(a['soil_temperature.1']),float(b['composite_factor.1']),float(w['soil_moisture_content.1']),1]; cnt[dt.month-1]+=1
    cyc[:,:3]/=cnt[:,None]
    E.DIAG_FE=[]; kw=E.standard_kwargs(soil,0)
    r=E.simulate_continuous(wx,corn_crop(cl,soil),carry_n=True,**kw)
    eng=np.zeros((12,4)); ec=np.zeros(12)
    for (y,doy,i,t,rw,fe) in E.DIAG_FE:
        if i==0 and 1984<=y<=2014:
            mo=(datetime.date(2001,1,1)+datetime.timedelta(int(doy)-1)).month-1; eng[mo]+=[t,fe,rw,1]; ec[mo]+=1
    eng[:,:3]/=np.maximum(ec,1)[:,None]
    return eng,cyc
if __name__=="__main__":
    R=Pool(4).map(one,range(24)); e=np.mean([r[0] for r in R],0); c=np.mean([r[1] for r in R],0)
    print("N=0 layer 1, 24 sites. month: soil T engine|Cycles   composite factor engine|Cycles   (engine fe uses its relwet; Cycles theta shown for reference)")
    for i in range(12): print(f" {i+1:2d}: {e[i,0]:6.2f} | {c[i,0]:6.2f}      {e[i,1]:.4f} | {c[i,1]:.4f}   ratio {e[i,1]/c[i,1]:.2f}")
