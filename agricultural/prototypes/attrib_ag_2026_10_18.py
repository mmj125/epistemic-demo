"""Above-ground excess attribution (2026-10-18), corn (grain) and silage corn (forage), continuous chain. For each site and N rate Cycles is run and its daily canopy (radiation_interception),
water factor (1 - water_stress) and N factor (1 - nitrogen_stress) are forced into the engine alone and together (E.FORCE_SERIES). Reports, per mode, engine over Cycles for the harvested yield and for
above-ground biomass at harvest, and the share of the free-run yield MAE removed.
Usage: CROPSEL=corn|silage CFILE=CornRM.90|CornSilageRM.90 MODES=",C,W,N,CWN" python3 attrib_ag_2026_10_18.py   (RR=1.0 sets root_retained_frac 1.0)"""
import os,sys,json,csv,shutil,subprocess,datetime,statistics as st
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]=os.environ.get("NS","0,150,400"); sys.path.insert(0,'.')
CS=os.environ.get("CROPSEL","corn"); CFILE=os.environ.get("CFILE","CornRM.90"); MODES=os.environ.get("MODES",",C,W,N,CWN").split(",")
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E, run_validation as rv
if os.environ.get("RR"): rv.CORN["root_retained_frac"]=float(os.environ["RR"])
for _kv in filter(None,os.environ.get("MODKV","").split(";")): setattr(E,_kv.split("=")[0],float(_kv.split("=")[1]))   # module constants, e.g. TTF50_SHOOT_PARTITION=0.42
for _kv in filter(None,os.environ.get("CROPKV","").split(";")): rv.CORN[_kv.split("=")[0]]=float(_kv.split("=")[1])   # extra crop-dict overrides, e.g. growth_stage_a=0.52
import run_validation_rotation2 as r2
if os.environ.get("NGF"): rv.CORN["ngf_faithful"]=float(os.environ["NGF"]); r2.CORN_SILAGE["ngf_faithful"]=float(os.environ["NGF"])   # growth scalar sweep for both crops
from multiprocessing import Pool
NSL=[int(x) for x in os.environ.get('NS','0,150,400').split(',')]
S=json.load(open('/tmp/w/s24.json')); KEY={'C':'canopy','W':'water','N':'nstress'}
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    D=[r for r in csv.DictReader(open(d+f"daily{CFILE}.csv")) if r['date'][0]!='#']; HC=list(csv.reader(open(d+"harvest.csv"))); shutil.rmtree(d,ignore_errors=True)
    hh=HC[0]; yi=hh.index('forage_yield' if CS=='silage' else 'grain_yield'); real={}
    for r in HC[2:]:
        if r and r[0][0]!='#': real[int(r[0][:4])]=float(r[yi])
    F={}; lastag={}
    for x in D:
        if x['biomass']=='-999': continue
        dt=datetime.date.fromisoformat(x['date']); y=dt.year; doy=dt.timetuple().tm_yday
        f=F.setdefault(y,{'canopy':{},'water':{},'nstress':{},'nclock':{},'wclock':{}})
        f['canopy'][doy]=float(x['radiation_interception']); f['water'][doy]=1-float(x['water_stress'])/100; f['nstress'][doy]=1-float(x['nitrogen_stress'])/100
        if x['stage'] in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH','MATURITY'): lastag[y]=float(x['aboveground_biomass'])
    out={}
    for mode in MODES:
        ks=[KEY[c] for c in mode]
        E.FORCE_SERIES={y:{k:(v if k in ks else {}) for k,v in f.items() if k in ('canopy','water','nstress')} for y,f in F.items()} if mode else None
        res=m.engine(site,wx,soil,cl,N,'leadin'); E.FORCE_SERIES=None
        ys=[y for y in sorted(set(real)&set(res)) if y>1981 and real[y]>0.3 and y in lastag]
        eng=[res[y]['forage' if CS=='silage' else 'grain'] for y in ys]; agE=[res[y]['ag'] for y in ys]; r_=[real[y] for y in ys]; agC=[lastag[y] for y in ys]
        out[mode or 'free']=dict(real=r_,eng=eng,agE=agE,agC=agC)
    return site,N,out
if __name__=="__main__":
    ks=sorted(S)
    with Pool(4) as p: R=p.map(one,[(k,N) for k in ks for N in NSL])
    tag=os.environ.get("TAG",CS); json.dump(R,open(f'/tmp/w/attr_ag_{tag}.json','w'))
    print(f"{CS} rr={os.environ.get('RR','0.6 (config)')} sites {len(ks)}")
    for N in NSL:
        base=None
        for mode in [x or 'free' for x in MODES]:
            r=[];e=[];ac=[];ae=[]
            for s,n,o in R:
                if n==N: r+=o[mode]['real']; e+=o[mode]['eng']; ac+=o[mode]['agC']; ae+=o[mode]['agE']
            r,e,ac,ae=map(np.array,(r,e,ac,ae)); mae=np.abs(e-r).mean(); base=base or mae
            print(f"  N={N:3d} {mode:5s} yield Cycles {r.mean():6.2f} engine {e.mean():6.2f} ratio {e.mean()/r.mean():.3f} MAE {mae:.3f} ({100*(1-mae/base):+4.0f}% vs free) | above-ground ratio {ae.mean()/ac.mean():.3f} | corr {np.corrcoef(r,e)[0,1]:.3f}")
