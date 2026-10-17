"""Calibration-factor mask attribution (2026-10-16). Runs corn (24 fresh sites, factor 1.0, no regional g) and winter wheat (16 fresh sites, factor 1.0) with and without Cycles' daily canopy, water stress
and N stress forced in, and compares engine and Cycles on total biomass (incl. roots), grain and grain/total. If forced total biomass matches (ratio near 1) and grain does not, the factor is covering the
harvest-index (or root/shoot) law; if total biomass is off in the same direction, it is covering the daily conversion. Usage: python3 mask_attrib_2026_10_16.py"""
import os,sys,json,csv,datetime,shutil,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite_wheat as W, run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
CY=m.CY
def harv(d):
    H={}
    for x in csv.DictReader(open(d+"harvest.csv")):
        if x["date"][0]=="#": continue
        H[int(x["date"][:4])]=dict(total=float(x["total_biomass"]),grain=float(x["grain_yield"]),hi=float(x["harvest_index"]))
    return H
def wseries(fs,N):
    subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
    F={}
    for x in csv.DictReader(open(d+"dailyWinterWheat.csv")):
        if x["date"][0]=="#" or x["biomass"]=="-999": continue
        dt=datetime.date.fromisoformat(x["date"]); py=dt.year if dt.month>=8 else dt.year-1; doy=dt.timetuple().tm_yday
        f=F.setdefault(py,{"canopy":{},"water":{},"nstress":{}})
        f["canopy"][doy]=float(x["radiation_interception"]); f["water"][doy]=1-float(x["water_stress"])/100; f["nstress"][doy]=1-float(x["nitrogen_stress"])/100
    H=harv(d); shutil.rmtree(d,ignore_errors=True); return F,H
def summ(H,R,skip=0):
    ys=[y for y in sorted(set(H)&set(R)) if y>skip]
    ys2=[y for y in ys if H[y]["hi"]>0.05]
    return dict(cag=st.mean(H[y]["grain"]/H[y]["hi"] for y in ys2),eag=st.mean(R[y]["ag"] for y in ys2),chi=st.mean(H[y]["hi"] for y in ys2),ehi=st.mean(R[y]["grain"]/R[y]["ag"] for y in ys2 if R[y]["ag"]>0),ct=st.mean(H[y]["total"] for y in ys),et=st.mean(R[y]["total"] for y in ys),cg=st.mean(H[y]["grain"] for y in ys),eg=st.mean(R[y]["grain"] for y in ys),n=len(ys))
def corn(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
        H=harv(d); F=forcelib.force(site,N,("wclock","canopy","water","nstress")); shutil.rmtree(d,ignore_errors=True)
        for mode in ("free","forced"):
            E.FORCE_SERIES=None if mode=="free" else {y:{k:v[k] for k in ("canopy","water","nstress","wclock","nclock")} for y,v in F.items()}
            R=m.engine(site,wx,soil,cl,N,"leadin"); E.FORCE_SERIES=None
            out[f"N{N}|{mode}"]=summ(H,R)
    return site,out
def wheat(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"wheat"; out={}; m.write_inputs(fs,lat,lon,wx,soil,cl)
    for N in (0,150):
        open(f"{CY}/input/{fs}N{N}.operation","w").write(W.OP+W.fert_text(N))
        P,H=wseries(fs,N)
        for mode in ("free","forced"):
            E.FORCE_SERIES=None if mode=="free" else P
            R=W.engine_chain(wx,soil,cl,N,1.0); E.FORCE_SERIES=None
            out[f"N{N}|{mode}"]=summ(H,R,1981)
    return site,out
def report(name,R):
    print(name)
    for N in (0,150):
        for mode in ("free","forced"):
            k=f"N{N}|{mode}"; ct=st.mean(o[k]["ct"] for _,o in R); et=st.mean(o[k]["et"] for _,o in R); cg=st.mean(o[k]["cg"] for _,o in R); eg=st.mean(o[k]["eg"] for _,o in R)
            print(f"  N={N} {mode:6s} total biomass engine/Cycles {et/ct:.3f} ({et:5.2f} vs {ct:5.2f})  grain engine/Cycles {eg/cg:.3f} ({eg:5.2f} vs {cg:5.2f})  grain share of total: engine {eg/et:.3f} Cycles {cg/ct:.3f} | aboveground engine/Cycles {st.mean(o[k]['eag'] for _,o in R)/st.mean(o[k]['cag'] for _,o in R):.3f}, HI engine {st.mean(o[k]['ehi'] for _,o in R):.3f} Cycles {st.mean(o[k]['chi'] for _,o in R):.3f}, root share engine {1-st.mean(o[k]['eag'] for _,o in R)/et:.3f} Cycles {1-st.mean(o[k]['cag'] for _,o in R)/ct:.3f}")
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: RC=p.map(corn,list(S.items()))
    json.dump(RC,open("scorecards/2026-10-16_mask_corn_24sites.json","w")); report("corn, factor 1.0",RC)
    S2=json.load(open("sitesets/fresh94.json")); ks=sorted(S2)[::6][:16]
    with Pool(4) as p: RW=p.map(wheat,[(k,S2[k]) for k in ks])
    json.dump(RW,open("scorecards/2026-10-16_mask_wheat_16sites.json","w")); report("winter wheat, factor 1.0",RW)
