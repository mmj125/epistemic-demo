import os,sys,csv,shutil,subprocess,datetime
os.environ["REGIONAL"]="0"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m, cycles_engine_validate as E
from cover_chain_2026_10_21 import corn_crop
from multiprocessing import Pool
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
def one(si):
    site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"rs"; m.write_inputs(nm,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{nm}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N0/"
    L=rd(d+"dailySoilLayersCN.csv"); shutil.rmtree(d,ignore_errors=True)
    nl=len([k for k in L[0] if k.startswith('residue_carbon.')])
    cyc=np.zeros((12,3)); cnt=np.zeros(12)
    for b in L:
        dt=datetime.date.fromisoformat(b['date'])
        if 1984<=dt.year<=2014:
            cyc[dt.month-1]+=[float(b['standing_residue_carbon'])+float(b['flat_residue_carbon']),sum(float(b['residue_carbon.%d'%i]) for i in range(1,nl+1)),1]; cnt[dt.month-1]+=1
    cyc[:,:2]/=cnt[:,None]
    E.DIAG_CPOOL=[]; kw=E.standard_kwargs(soil,0)
    r=E.simulate_continuous(wx,corn_crop(cl,soil),carry_n=True,**kw)
    eng=np.zeros((12,3)); ec=np.zeros(12)
    for (y,doy,cs,cm,crtz,cra) in E.DIAG_CPOOL:
        if 1984<=y<=2014:
            mo=(datetime.date(2001,1,1)+datetime.timedelta(int(doy)-1)).month-1; eng[mo]+=[cra,sum(crtz),1]; ec[mo]+=1
    eng[:,:2]/=np.maximum(ec,1)[:,None]
    return eng,cyc
if __name__=="__main__":
    R=Pool(4).map(one,range(24)); e=np.mean([r[0] for r in R],0); c=np.mean([r[1] for r in R],0)
    print("N=0, 24 sites, mean residue carbon (Mg C/ha). month: surface (standing+flat) engine cra | Cycles    in-soil residue engine crtz | Cycles")
    for i in range(12): print(f" {i+1:2d}: {e[i,0]:6.3f} | {c[i,0]:6.3f}      {e[i,1]:6.3f} | {c[i,1]:6.3f}")
