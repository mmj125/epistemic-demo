import os,sys,json,csv,shutil,subprocess
os.environ["REGIONAL"]="0"; os.environ["LEAD_YEARS"]="continuous"; os.environ["CROPSEL"]="corn"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json')); ks=sorted(S)[::10][:9]
NN=int(os.environ.get("NN","150"))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NN}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NN}/"
    H=[r for r in csv.DictReader(open(d+"harvest.csv")) if r['date'][0]!='#']; shutil.rmtree(d,ignore_errors=True)
    R=m.engine(site,wx,soil,cl,NN,'leadin')
    if site==ks[0]: print(sorted(R[1990].keys()))
    cy={int(h['date'][:4]):h for h in H}
    ys=[y for y in R if y in cy and y>=1985]
    f=lambda k:np.mean([float(cy[y][k]) for y in ys])
    cb=f('total_biomass'); eb=np.mean([R[y]['total'] for y in ys]); eu=np.mean([R[y]['n_uptake_kg_ha'] for y in ys]); ca=f('total_nitrogen')-f('root_nitrogen')
    return site,cb,eb,ca,eu,f('grain_yield'),np.mean([R[y]['grain'] for y in ys])
    return site,f('total_nitrogen'),f('grain_nitrogen'),f('nitrogen_in_residue'),f('root_nitrogen'),f('cumulative_nitrogen_stress'),ys,R
if __name__=="__main__":
    with Pool(3) as p: out=p.map(one,ks)
    print("site | biomass Cyc eng | agN Cyc eng | agN/biomass^0.6 Cyc eng | grain Cyc eng")
    for (site,cb,eb,ca,eu,cg,eg) in out: print(site,round(cb,1),round(eb,1),round(ca),round(eu),round(ca/cb**0.6,1),round(eu/eb**0.6,1),round(cg,1),round(eg,1))
