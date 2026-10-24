"""Daily growth ratio by temperature (2026-10-18). Cycles run per site (corn, continuous, N=NLEV); its daily canopy, water factor and N factor are forced into the engine (E.FORCE_SERIES);
engine daily gain (E.DIAG_GROWTH, column 3) against Cycles' daily change in total biomass, summed in daily mean temperature bins. Usage: [ENGINE_OVR-like env HEAT_T0, HEAT_A, HEAT_GT] python3 heat_check_2026_10_18.py N_SITES N"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
NS=int(sys.argv[1]); NLEV=int(sys.argv[2]); os.environ["N_LEVELS"]=str(NLEV)
import numpy as np, run_validation_multisite as m, rhizo_engine as E
if os.environ.get("HEAT_T0"): E.HEAT_T0=float(os.environ["HEAT_T0"]); E.VPD_CYCLES_EXACT=False if os.environ.get("HEAT_ON_EXACT")!="1" else True
if os.environ.get("HEAT_A"): E.HEAT_A=float(os.environ["HEAT_A"])
if os.environ.get("HEAT_GT"): E.HEAT_GT=os.environ["HEAT_GT"]=="1"
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); KEY={'canopy':'canopy','water':'water','nstress':'nstress'}
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{NLEV}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{NLEV}/"
    D=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    F={}; B={}
    for x in D:
        if x['biomass']=='-999': continue
        dt=datetime.date.fromisoformat(x['date']); y=dt.year; doy=dt.timetuple().tm_yday
        f=F.setdefault(y,{'canopy':{},'water':{},'nstress':{}})
        f['canopy'][doy]=float(x['radiation_interception']); f['water'][doy]=1-float(x['water_stress'])/100; f['nstress'][doy]=1-float(x['nitrogen_stress'])/100
        B[(y,doy)]=(float(x['biomass']),float(x['temperature_factor']),1-float(x['nitrogen_stress'])/100,float(x['thermal_time']))
    E.FORCE_SERIES=F; E.DIAG_GROWTH=[]
    res=m.engine(site,wx,soil,cl,NLEV,'leadin'); G=E.DIAG_GROWTH; E.DIAG_GROWTH=None; E.FORCE_SERIES=None
    segs=[];cur=[]
    for g in G:
        if cur and g[0]<cur[-1][0]: segs.append(cur);cur=[]
        cur.append(g)
    if cur: segs.append(cur)
    ys=sorted(res)
    if len(segs)!=len(ys): return site,None
    rows=[]
    for y,sg in zip(ys,segs):
        for (doy,GR,GT,dgb) in sg:
            if (y,doy) in B and (y,doy-1) in B and doy in wx[y]:
                w=wx[y][doy]; rows.append(((w['tx']+w['tn'])/2,dgb*10.0*(B[(y,doy)][2]**E.N_STRESS_GROWTH_POW),B[(y,doy)][0]-B[(y,doy-1)][0],B[(y,doy)][1],GR,GT,B[(y,doy)][3]))
    return site,np.array(rows)
if __name__=="__main__":
    ks=sorted(S)[:NS]
    with Pool(4) as p: R=p.map(one,ks)
    A=np.vstack([a for s,a in R if a is not None and len(a)]); A=A[A[:,2]>0.02]
    print(f"sites ok {sum(1 for s,a in R if a is not None)} of {NS}; growth days {len(A)}; overall engine/Cycles {A[:,1].sum()/A[:,2].sum():.3f}")
    print('  by Cycles thermal time (C-day):')
    for lo,hi in ((0,200),(200,400),(400,600),(600,800),(800,1000),(1000,1300),(1300,1700),(1700,3000)):
        s_=(A[:,6]>=lo)&(A[:,6]<hi)
        if s_.sum()>40: print(f'    TT {lo:4d}-{hi:4d}: n {s_.sum():6d} engine/Cycles {A[s_,1].sum()/A[s_,2].sum():.3f}')
    lim=A[:,4]<=A[:,5]
    print(f'  radiation-limited days (GR<=GT): n {lim.sum()} engine/Cycles {A[lim,1].sum()/A[lim,2].sum():.3f} | water-limited days: n {(~lim).sum()} engine/Cycles {A[~lim,1].sum()/A[~lim,2].sum():.3f}')
    for lo,hi in ((0,10),(10,15),(15,20),(20,24),(24,27),(27,30),(30,33),(33,45)):
        s=(A[:,0]>=lo)&(A[:,0]<hi)
        if s.sum()>40: print(f"  Tmean {lo:2d}-{hi:2d}: n {s.sum():6d} engine/Cycles {A[s,1].sum()/A[s,2].sum():.3f}  Cycles temperature_factor mean {A[s,3].mean():.3f}")
