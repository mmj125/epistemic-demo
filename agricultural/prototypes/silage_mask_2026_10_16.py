"""Silage corn calibration-factor attribution (2026-10-16): continuous silage corn (CornSilageRM.90, harvest at 85% of maturity, Kill_Crop on DOY 365), Cycles v1.5.20 vs the engine at factor 1.0,
24 fresh sites, N=0 and 150, free and with Cycles' daily canopy, water stress and N stress forced. Compares forage yield and total biomass."""
import os,sys,json,csv,glob,re,shutil,subprocess,datetime,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
_sk=E.standard_kwargs
E.standard_kwargs=lambda *a,**k:dict(_sk(*a,**k),harvest_ttf=0.85)
def patch(site,N):
    p=f"{CY}/input/{site}N{N}.operation"; t=open(p).read()
    t=t.replace("CornRM.90","CornSilageRM.90"); t=re.sub(r"(HARVEST_TIMING\s+)-999",r"\g<1>85",t); t=re.sub(r"(RESIDUE_REMOVED\s+)\d+",r"\g<1>90",t)
    t=t.rstrip()+"\n\nTILLAGE\nYEAR                                1\nDOY                                 365\nTOOL                                Kill_Crop\nCROP_NAME                           N/A\nFRAC_THERMAL_TIME                   0.0\nKILL_EFFICIENCY                     0.0\n"
    open(p,"w").write(t)
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    fs=site+"silage"; m.write_inputs(fs,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        patch(fs,N); subprocess.run(["./Cycles",f"{fs}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{fs}N{N}/"
        H={}
        for x in csv.DictReader(open(d+"harvest.csv")):
            if x["date"][0]=="#": continue
            H[int(x["date"][:4])]=dict(forage=float(x["forage_yield"]),total=float(x["total_biomass"]))
        F={}
        f=glob.glob(d+"daily*RM.90.csv")[0]
        for x in csv.DictReader(open(f)):
            if x["date"][0]=="#" or x["biomass"]=="-999": continue
            dt=datetime.date.fromisoformat(x["date"]); g=F.setdefault(dt.year,{"canopy":{},"water":{},"nstress":{}}); doy=dt.timetuple().tm_yday
            g["canopy"][doy]=float(x["radiation_interception"]); g["water"][doy]=1-float(x["water_stress"])/100; g["nstress"][doy]=1-float(x["nitrogen_stress"])/100
        shutil.rmtree(d,ignore_errors=True)
        for mode in ("free","forced"):
            E.FORCE_SERIES=None if mode=="free" else F
            R=m.engine(fs,wx,soil,cl,N,"leadin"); E.FORCE_SERIES=None
            ys=sorted(set(H)&set(R)); 
            out[f"N{N}|{mode}"]=dict(cf=st.mean(H[y]["forage"] for y in ys),ef=st.mean(R[y]["forage"] for y in ys),ct=st.mean(H[y]["total"] for y in ys),et=st.mean(R[y]["total"] for y in ys),
                                     corr=m.corr([H[y]["forage"] for y in ys],[R[y]["forage"] for y in ys]))
    return site,out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    json.dump(R,open("scorecards/2026-10-16_mask_silage_24sites.json","w"))
    for N in (0,150):
        for mode in ("free","forced"):
            k=f"N{N}|{mode}"; g=lambda q:st.mean(o[k][q] for _,o in R)
            print(f"N={N} {mode:6s} forage engine/Cycles {g('ef')/g('cf'):.3f} ({g('ef'):5.2f} vs {g('cf'):5.2f})  total biomass engine/Cycles {g('et')/g('ct'):.3f}  mean within-site forage corr {st.mean(o[k]['corr'] for _,o in R if o[k]['corr']==o[k]['corr']):.2f}")
