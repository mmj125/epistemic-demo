"""Soybean N split (2026-10-29): Cycles continuous SoybeanMG.5 against the engine's legume path, per site-year: total plant N, fixation, soil uptake, biomass, grain N. 24 sites, N=0 (soybean ignores N)."""
import os,sys,json,subprocess,shutil,csv
os.environ["CROPSEL"]="soy"; os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, engine_api as api
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+'soy'; m.write_inputs(fs,lat,lon,wx,soil,cl)
    subprocess.run(["./Cycles",f"{fs}N0"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N0/"
    H={}
    for r in csv.DictReader(l for l in open(d+"harvest.csv") if not l.startswith('#')):
        H[int(r['date'][:4])]=dict(bio=float(r['total_biomass'])-float(r['root_biomass']),N=float(r['total_nitrogen'])-float(r['root_nitrogen']),gN=float(r['grain_nitrogen']),fix=float(r['nitrogen_fixation']),grain=float(r['grain_yield']))
    shutil.rmtree(d,ignore_errors=True)
    res=m.engine(site,wx,soil,cl,0,'leadin')
    return site,H,{y:dict(grain=v.get('grain'),bio=v.get('ag'),plantn=v.get('n_plant_kg_ha'),fix=v.get('n_fixed_kg_ha'),upt=v.get('n_uptake_kg_ha')) for y,v in res.items()}
if __name__=="__main__":
    R=Pool(4).map(one,sorted(S)); rows=[]
    for s,H,E in R:
        for y,h in H.items():
            e=E.get(y)
            if y<1983 or not e or e['grain'] is None or e['plantn'] is None: continue
            rows.append((h['bio'],h['N'],h['gN'],h['fix'],h['grain'],e['bio'],e['plantn'],e['fix'] or 0,e['upt'] or 0,e['grain']))
    a=np.array(rows,float); print("n",len(a)); 
    n=["Cycles ag biomass","Cycles ag N","Cycles grain N","Cycles fixation","Cycles grain","eng biomass","eng plant N","eng fixation","eng soil uptake","eng grain"]
    for i,k in enumerate(n): print(f"{k:20s} mean {a[:,i].mean():8.2f}")
    cb,cN,cg,cf=a[:,0],a[:,1],a[:,2],a[:,3]
    print("Cycles N / (0.07 B^0.6 *1000) mean ratio %.3f sd %.3f"%(np.mean(cN/(70*cb**0.6)),np.std(cN/(70*cb**0.6))))
    print("Cycles grainN/agN %.3f ; Cycles fixation/agN %.3f ; Cycles seed N%% %.2f"%(np.mean(cg/cN),np.mean(cf/cN),np.mean(cg/(a[:,4]*1000)*100)))
    print("engine N / (0.07 B^0.6*1000) %.3f ; eng fix/plantN %.3f"%(np.mean(a[:,6]/(70*a[:,5]**0.6)),np.mean(a[:,7]/a[:,6])))
    print("corr plant N %.3f fix %.3f"%(np.corrcoef(cN,a[:,6])[0,1],np.corrcoef(cf,a[:,7])[0,1]))
