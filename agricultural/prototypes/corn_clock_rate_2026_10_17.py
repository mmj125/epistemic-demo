"""Mean canopy-clock rate (N mult^3.25 x water mult^1.35, same-day values) of the free engine vs Cycles' own multipliers, by thermal-time bin, corn, 24 sites, N=0 and 150. Shows whether the engine's stress states slow the expansion clock more or less than Cycles' do."""
import os,sys,json,shutil,csv,datetime,subprocess,statistics as st
os.environ["N_LEVELS"]="0,150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; C={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999':continue
            dt=datetime.date.fromisoformat(x['date']); C.setdefault(dt.year,{})[dt.timetuple().tm_yday]=(1-float(x['nitrogen_stress'])/100,1-float(x['water_stress'])/100,float(x['thermal_time']))
        shutil.rmtree(d,ignore_errors=True)
        E.DIAG_STATE=[]; E.DIAG_WATER=[]; m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_STATE; Wt=E.DIAG_WATER; E.DIAG_STATE=None; E.DIAG_WATER=None
        ew={(y,doy):w for y,doy,w,tt,trp,tra,_td in Wt}
        for y,doy,eie,ns,pn in S:
            if y in C and doy in C[y] and (y,doy) in ew:
                c=C[y][doy]; out.append((site,N,int(c[2]//300)*300,c[0]**3.25*c[1]**1.35,ns**3.25*ew[(y,doy)]**1.35,c[0],ns,c[1],ew[(y,doy)]))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    for N in (0,150):
        for lo in range(0,1800,300):
            q=[r for r in R if r[1]==N and r[2]==lo]
            if q: print(f"N={N} TT {lo}: clock rate Cycles {st.mean(r[3] for r in q):.3f} engine {st.mean(r[4] for r in q):.3f}  | N mult C {st.mean(r[5] for r in q):.2f} E {st.mean(r[6] for r in q):.2f} | W mult C {st.mean(r[7] for r in q):.2f} E {st.mean(r[8] for r in q):.2f}")

    print("per-site mean water mult, N=150, TT 0-900 (Cycles, engine, gap):")
    import collections
    g=collections.defaultdict(list)
    for r in R:
        if r[1]==150 and r[2]<900: g[r[0]].append((r[7],r[8]))
    rows=sorted(((st.mean(b for a,b in v)-st.mean(a for a,b in v),k,st.mean(a for a,b in v),st.mean(b for a,b in v)) for k,v in g.items()))
    for gap,k,a,b in rows: print(f"  {k}: C {a:.2f} E {b:.2f} gap {gap:+.2f}")
