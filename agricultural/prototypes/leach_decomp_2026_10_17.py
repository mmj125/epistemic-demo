"""Leaching = drainage x leachate concentration. Per site and N, yearly engine vs Cycles drainage (dailyWater drainage+bypass), NO3 leaching (dailyN) and leachate concentration. Tells whether the leaching error is water or nitrate."""
import os,sys,json,shutil,csv,datetime,subprocess,statistics as st
os.environ["N_LEVELS"]="150,400"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (150,400):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"
        C={}
        for x in csv.DictReader(open(d+"dailyWater.csv")):
            if x['date'][0]=='#': continue
            y=int(x['date'][:4]); C.setdefault(y,[0,0,0]); C[y][0]+=float(x['drainage']); C[y][1]+=float(x['bypass'])
        for x in csv.DictReader(open(d+"dailyN.csv")):
            if x['date'][0]=='#': continue
            y=int(x['date'][:4]); C.setdefault(y,[0,0,0]); C[y][2]+=float(x['NO3_leaching'])+float(x['NO3_bypass'])
        U={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['total_nitrogen']=='-999': continue
            y=int(x['date'][:4]); U[y]=max(U.get(y,0.0),float(x['total_nitrogen']))
        E.DIAG_DRAIN=[]; R=m.engine(site,wx,soil,cl,N,"leadin"); D=E.DIAG_DRAIN; E.DIAG_DRAIN=None
        shutil.rmtree(d,ignore_errors=True)
        Ed={}
        for y,dr,nl in D:
            if y is None: continue
            Ed.setdefault(y,[0,0]); Ed[y][0]+=dr; Ed[y][1]+=nl
        for y in set(C)&set(R):
            out.append((site,N,y,C[y][0],C[y][1],C[y][2],Ed.get(y,[0,0])[0],R[y].get("n_leached_kg_ha",0.0),U.get(y,0.0),R[y].get("n_uptake_kg_ha",0.0)))
    return out
def corr(a,b):
    ma,mb=st.mean(a),st.mean(b); sa=sum((x-ma)**2 for x in a)**.5; sb=sum((y-mb)**2 for y in b)**.5
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/(sa*sb) if sa*sb else float('nan')
if __name__=="__main__":
    S=json.load(open(os.environ.get("SFILE","/tmp/w/s24.json")))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    json.dump(R,open(os.environ.get("AOUT","/tmp/w/leach_decomp.json"),"w"))
    for N in (150,400):
        q=[r for r in R if r[1]==N]; sites=sorted(set(r[0] for r in q))
        cd=[st.mean(r[3]+r[4] for r in q if r[0]==s) for s in sites]; ed=[st.mean(r[6] for r in q if r[0]==s) for s in sites]
        cl=[st.mean(r[5] for r in q if r[0]==s) for s in sites]; el=[st.mean(r[7] for r in q if r[0]==s) for s in sites]
        up_c=st.mean(r[8] for r in q); up_e=st.mean(r[9] for r in q); print(f'   plant N uptake kg/ha: Cycles {up_c:.0f} engine {up_e:.0f}')
        wy=[corr([r[3]+r[4] for r in q if r[0]==s],[r[6] for r in q if r[0]==s]) for s in sites]
        wl=[corr([r[5] for r in q if r[0]==s],[r[7] for r in q if r[0]==s]) for s in sites]
        print(f"N={N}: drainage mm/yr Cycles {st.mean(cd):.0f} engine {st.mean(ed):.0f} (site corr {corr(cd,ed):.2f}, within-site yearly corr {st.mean(x for x in wy if x==x):.2f}); leaching kg/ha Cycles {st.mean(cl):.1f} engine {st.mean(el):.1f} (within-site {st.mean(x for x in wl if x==x):.2f}); leachate mg/L Cycles {st.mean(c/(d)*100 for c,d in zip(cl,cd) if d>1):.1f} engine {st.mean(e/d*100 for e,d in zip(el,ed) if d>1):.1f}")
