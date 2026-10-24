"""Daily growth conversion at N=150 with Cycles' canopy, water stress, N stress and clocks forced into the engine (2026-10-17): ratio of engine to Cycles daily biomass gain, binned by Cycles' own
temperature_factor and o2_factor columns and by season stage. 24 sites, corn, continuous chain. Usage: python3 corn_growth_given_states_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess,numpy as np
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); os.environ.setdefault("LEAD_YEARS","continuous"); os.environ.setdefault("YEAR_STEP","2"); sys.path.insert(0,'.')
import run_validation_multisite as m, rhizo_engine as E, forcelib
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); rows=[]
    N=150
    subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
    C={}; 
    for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
        if x["date"][0]=="#" or x["biomass"]=="-999": continue
        dt=datetime.date.fromisoformat(x["date"]); C[(dt.year,dt.timetuple().tm_yday)]=(float(x["thermal_time"]),float(x["biomass"]),float(x["temperature_factor"]),float(x["o2_factor"]),float(x["radiation_interception"]),float(x["water_stress"])/100,float(x["potential_transpiration"]))
    FS=forcelib.force(site,N,('wclock','canopy','water','nstress')); shutil.rmtree(d,ignore_errors=True)
    E.FORCE_SERIES={y:{k:v[k] for k in ('canopy','water','nstress','wclock','nclock')} for y,v in FS.items()}
    E.DIAG_STATE=[]; E.DIAG_BIO=[]; m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_STATE; B=E.DIAG_BIO; E.DIAG_STATE=None; E.DIAG_BIO=None; E.FORCE_SERIES=None
    tmax={}
    for (y,doy),v in C.items(): tmax[y]=max(tmax.get(y,0),v[0])
    pe=None
    for (y,doy,eie,ns,pn),eb in zip(D,B):
        c=C.get((y,doy)); pc=C.get((y,doy-1))
        if c and pc and pe is not None and pe[0]==y and pe[1]==doy-1:
            dc=c[1]-pc[1]; de=eb-pe[2]
            if dc>0.005 and de>=0: rows.append((min(9,int(10*c[0]/tmax[y])),c[2],c[3],de/dc,c[4],c[5],(wx[y][doy]["tx"]+wx[y][doy]["tn"])/2,c[6],wx[y][doy]["solar"],c[1]))
        pe=(y,doy,eb)
    return rows
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=p.map(one,list(S.items()))
    A=np.array([r for rr in R for r in rr]); print("day pairs",len(A)); np.save("/tmp/w/corn_growth_given.npy",A)
    def tab(name,col,edges):
        print(name)
        for lo,hi in zip(edges[:-1],edges[1:]):
            s=A[(A[:,col]>=lo)&(A[:,col]<hi)]
            if len(s)>200: print(f"   {lo:.2f}-{hi:.2f}: median engine/Cycles daily gain {np.median(s[:,3]):.2f}  mean {s[:,3].mean():.2f} (n={len(s)})")
    tab("by season decile",0,[0,1,2,3,4,5,6,7,8,9,10]); tab("by Cycles temperature_factor",1,[0,.2,.4,.6,.8,.95,1.01]); tab("by Cycles o2_factor",2,[0,.5,.8,.95,.999,1.01]); tab("by Cycles water stress (0=none)",5,[-.01,.01,.1,.3,.6,1.01]); tab("by Cycles canopy",4,[0,.1,.3,.5,.7,.9,1.01])
