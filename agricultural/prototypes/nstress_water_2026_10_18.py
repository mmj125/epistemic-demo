"""Does the engine's yearly N stress track water stress the way Cycles' does (2026-10-18)? Paper Sec 2.5: new-growth N concentration is set from a crop growing WITHOUT WATER stress,
so dry years should carry less N stress. Per site and N rate, within-site correlation over years of season-mean N stress with Cycles' season-mean water stress, for Cycles and for the engine.
Usage: python3 nstress_water_2026_10_18.py N_SITES   (corn, continuous chain, 24-site set; engine config from ENGINE_OVR)"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(path): return [r for r in csv.DictReader(open(path)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    C=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    cy={}
    for r in C:
        if r['biomass']=='-999' or r['stage'] not in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'): continue
        dt=datetime.date.fromisoformat(r['date']); cy[(dt.year,dt.timetuple().tm_yday)]=(1-float(r['nitrogen_stress'])/100,1-float(r['water_stress'])/100)
    E.DIAG_STATE=[]; m.engine(site,wx,soil,cl,N,'leadin'); D=E.DIAG_STATE; E.DIAG_STATE=None
    en={(y,doy):ns for y,doy,canopy,ns,pn in D if y is not None}
    out=[]
    for y in sorted({k[0] for k in cy}):
        ks=[k for k in cy if k[0]==y and k in en]
        if len(ks)<40 or y<1982: continue
        out.append((y,float(np.mean([cy[k][0] for k in ks])),float(np.mean([en[k] for k in ks])),float(np.mean([cy[k][1] for k in ks]))))
    return site,N,out
if __name__=="__main__":
    ks=sorted(S); n=int(sys.argv[1]); ks=ks[:n]
    with Pool(4) as p: R=p.map(one,[(k,N) for k in ks for N in (0,150)])
    for N in (0,150):
        cc=[];ce=[];sc=[];se=[]
        for s,n_,o in R:
            if n_!=N or len(o)<10: continue
            A=np.array([x[1:] for x in o]); 
            if A[:,0].std()>0.01 and A[:,2].std()>0.01: cc.append(np.corrcoef(A[:,0],A[:,2])[0,1])
            if A[:,1].std()>0.01 and A[:,2].std()>0.01: ce.append(np.corrcoef(A[:,1],A[:,2])[0,1])
            sc.append(A[:,0].std()); se.append(A[:,1].std())
        print(f"N={N}: sites {len(cc)} | within-site corr(N stress factor, water factor): Cycles median {np.median(cc):+.2f} mean {np.mean(cc):+.2f}; engine median {np.median(ce):+.2f} mean {np.mean(ce):+.2f} | within-site sd of season-mean N factor: Cycles {np.mean(sc):.3f} engine {np.mean(se):.3f}")
