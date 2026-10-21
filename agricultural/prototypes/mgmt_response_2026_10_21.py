"""Management-response check (2026-10-21): for each treatment, the change from the N=150 corn baseline (manure: from N=0) in Cycles against the engine, same 24 sites.
Treatments: till (Chisel_st_pt before the planter), late (planting window +25 d), irrig (auto irrigation, 50% depletion, 1 m), manure (N=0 plus Dairy_Manure at 150 kg total N).
Measures per site-year: grain, leaching (NO3+NH4), denitrification, N2O, volatilization."""
import os,sys,json,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from cover_chain_2026_10_21 import corn_crop
from multiprocessing import Pool
E.TILLAGE_IMPLEMENTS["Chisel+planter"]=(0.25,19+5,1-(1-0.265919)*(1-0.071554))
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
TREATS=sys.argv[1].split(",") if len(sys.argv)>1 else ["till","late","irrig","manure"]
TILL="TILLAGE\nYEAR                                1\nDOY                                 +0\nTOOL                                Chisel_st_pt\nCROP_NAME                           N/A\nFRAC_THERMAL_TIME                   0.0\nKILL_EFFICIENCY                     0.0\n\n"
IRR="\nAUTO_IRRIGATION\nCROP                                CornRM.90\nSTART_DOY                           150\nSTOP_DOY                            260\nWATER_DEPLETION                     0.5\nDEPTH                               1.0\n"
MAN="\nFIXED_FERTILIZATION\nYEAR                                1\nDOY                                 +0\nSOURCE                              Dairy_Manure\nMASS                                3947.4      # kg/ha\nFORM                                Solid\nMETHOD                              Broadcast\nDEPTH                               0.05\n"
def variant(t,txt):
    if t=="till": i=txt.index("TILLAGE"); return txt[:i]+TILL+txt[i:]
    if t=="late": return txt.replace("DOY                                 110","DOY                                 135").replace("END_DOY                             131","END_DOY                             156")
    if t=="irrig": return txt.replace("USE_AUTO_IRR                        0","USE_AUTO_IRR                        1")+IRR.replace("@LL@",str(LL[0]))
    if t=="manure": return txt+MAN
def parse(d):
    H={};A={}
    for line in open(d+"harvest.csv").readlines()[2:]:
        q=line.strip().split(",")
        if len(q)>=11: H[int(q[0][:4])]=float(q[5])
    for line in open(d+"annualN.csv").readlines()[2:]:
        q=line.strip().split(",")
        if len(q)>=12: A[int(q[0])]=dict(leach=float(q[4])+float(q[5]),denit=float(q[8]),volat=float(q[10]),n2o=float(q[11]))
    return H,A
LL=[3]
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"mg"; m.write_inputs(nm,lat,lon,wx,soil,cl); out={}
    z=0.0
    for i,l in enumerate(soil):
        z+=l["thick"]
        if z>=1.0: break
    LL[0]=i+1   # layers down to about 1 m
    def eng(N,**ex):
        kw=E.standard_kwargs(soil,N); pw=ex.pop("plant_window",(110,131)); kw.update(ex); kw["tillage_clay_frac"]=soil[0]["clay"]/100.0
        r=E.simulate_continuous(wx,corn_crop(cl,soil),carry_n=True,plant_window=pw,**kw); o={}
        for y,v in r.items():
            f=lambda k,fk:(v.get(k) or 0.0)+v.get(fk,0.0)
            o[y]=dict(grain=v["grain"],leach=f("n_leached_kg_ha","fallow_n_leached"),denit=f("n_denitrified_kg_ha","fallow_n_denitrified"),n2o=f("n2o_emitted_kg_ha","fallow_n2o"),volat=f("n_volatilized_pool_kg_ha","fallow_n_volatilized")+(v.get("n_volatilized_kg_ha") or 0.0)*0)
        return o
    def cyc(t,N):
        p=f"{m.CY}/input/{nm}N{N}.operation"; txt=open(p).read(); open(p,"w").write(variant(t,txt))
        subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N{N}/"; H,A=parse(d); shutil.rmtree(d,ignore_errors=True); open(p,"w").write(txt)
        return {y:dict(grain=H[y],**A[y]) for y in H if y in A}
    for t in TREATS:
        N=0 if t=="manure" else 150
        kwt={"till":dict(tillage_implement="Chisel+planter",tillage_doy="planting"),"late":dict(plant_window=(135,156)),"irrig":dict(irrigation_trigger_frac=0.5,irrigation_refill_layers=LL[0],irrigation_window=(150,260)),"manure":dict(manure_n_kg_ha=150.0,manure_source="dairy")}[t]
        out[t]=dict(eb=eng(N,**(dict(tillage_implement="Planter_double_disk_opnr",tillage_doy="planting") if t=="till" else {})),et=eng(N,**kwt),cb=None,ct=cyc(t,N))
        b,_=m.run_cycles(site,N); _,Ab=m.run_cycles(site,N); out[t]["cb"]={y:dict(grain=b[y]["grain"],**Ab[y]) for y in b if y in Ab}
    return site,out
if __name__=="__main__":
    R=Pool(4).map(one,SITES)
    json.dump(R,open('/tmp/w/mgmt_resp.json','w'))
    for t in TREATS:
        print(f"== {t}")
        for k in ("grain","leach","denit","n2o","volat"):
            de=[];dc=[];eb=[];cb=[]
            for site,o in R:
                x=o[t]
                for y in x['ct']:
                    if y>=1983 and y in x['cb'] and y in x['eb'] and y in x['et']:
                        de.append(x['et'][y][k]-x['eb'][y][k]); dc.append(x['ct'][y][k]-x['cb'][y][k]); eb.append(x['eb'][y][k]); cb.append(x['cb'][y][k])
            r=np.corrcoef(de,dc)[0,1] if np.std(de)>0 and np.std(dc)>0 else float('nan')
            print(f"  {k:6s} change engine {np.mean(de):+8.3f} | Cycles {np.mean(dc):+8.3f}  (baseline level engine {np.mean(eb):.2f} | Cycles {np.mean(cb):.2f}), year corr of change {r:.2f}, n={len(de)}")
