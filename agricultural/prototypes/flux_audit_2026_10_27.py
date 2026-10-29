"""Annual C and N flux audit against Cycles definitions (2026-10-27): net N mineralization (the gross columns from this script are unreliable: probe-pass state), and see resp3/cmtraj notes in the plan. Usage: python3 flux_audit_2026_10_27.py"""
import os,sys,json,csv,shutil,subprocess
os.environ["REGIONAL"]="0"; os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; os.environ["CROPSEL"]="corn"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json')); ks=sorted(S)[::10][:9]
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    N=[r for r in csv.DictReader(open(d+"dailyN.csv")) if r['date'][0]!='#']; shutil.rmtree(d,ignore_errors=True)
    ny=len(N)/365.25
    c={k:sum(float(r[k]) for r in N)/ny for k in ('mineralization','immobilization','net_mineralization','nitrification')}
    acc=[0.0,0.0]; _ss=E.sixpool_step
    def ss(state,*a,**k):
        r=_ss(state,*a,**k); acc[0]+=state.get('gmin',0.0); acc[1]+=state.get('gimm',0.0); return r
    E.DIAG_RESP=[]; E.sixpool_step=ss; m.engine(site,wx,soil,cl,150,'leadin'); E.sixpool_step=_ss
    return site,c['mineralization'],c['immobilization'],c['net_mineralization'],c['nitrification'],acc[0]/ny,acc[1]/ny,sum(t[2] for t in E.DIAG_RESP)/ny
if __name__=="__main__":
    with Pool(3) as p: R=p.map(one,ks)
    print("site | Cycles gross min, imm, net, nitrif | engine gross min, imm (per year)")
    for r in R: print(r[0],*[round(x,1) for x in r[1:]])
    print("(last col: engine net N from DIAG_RESP)");print("mean",*np.round(np.mean([r[1:] for r in R],0),1))
