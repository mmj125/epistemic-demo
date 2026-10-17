"""Wheat season N: plant N at harvest and per Mg biomass, engine vs Cycles (2026-10-17). 16 fresh sites, N=0 and 150, continuous winter wheat, current engine."""
import os,sys,json,csv,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"; m.write_inputs(fs,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
        PN={}; B={}; NS={}
        for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": continue
            y=int(x["date"][:4]); PN[y]=max(PN.get(y,0),float(x["total_nitrogen"])); B[y]=max(B.get(y,0),float(x["biomass"])); NS[y]=max(NS.get(y,0),float(x["nitrogen_stress"]))
        shutil.rmtree(d,ignore_errors=True)
        R=W.engine_chain(wx,soil,cl,N,1.0); ys=[y for y in sorted(set(PN)&set(R)) if y>1981 and not R[y].get("winter_killed")]
        out[N]=dict(cup=st.mean(PN[y] for y in ys),eup=st.mean(R[y].get("n_uptake_kg_ha",0) for y in ys),cb=st.mean(B[y] for y in ys),eb=st.mean(R[y]["total"] for y in ys),cns=st.mean(NS[y] for y in ys),
                    corr=m.corr([PN[y] for y in ys],[R[y].get("n_uptake_kg_ha",0) for y in ys]))
    return site,out
if __name__=="__main__":
    S=json.load(open("sitesets/fresh94.json")); ks=sorted(S)[::6][:16]
    with Pool(4) as p: R=p.map(one,[(k,S[k]) for k in ks])
    for N in (0,150):
        g=lambda q:st.mean(o[N][q] for _,o in R)
        print(f"N={N}: plant N engine {g('eup'):.1f} vs Cycles {g('cup'):.1f}; biomass {g('eb'):.2f} vs {g('cb'):.2f}; N per Mg biomass engine {g('eup')/g('eb'):.2f} Cycles {g('cup')/g('cb'):.2f}; Cycles max N stress {g('cns'):.0f}%; within-site yearly corr of plant N {st.mean(o[N]['corr'] for _,o in R if o[N]['corr']==o[N]['corr']):.2f}")
