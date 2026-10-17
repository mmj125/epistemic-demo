"""Year-level N stress comparison (corn, 24 sites, free engine): season-mean N multiplier (thermal time 300-1200) engine vs Cycles for each site-year; within-site correlation, sd of each, and mean. N=0 and 150."""
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
            dt=datetime.date.fromisoformat(x['date']); C.setdefault(dt.year,{})[dt.timetuple().tm_yday]=(1-float(x['nitrogen_stress'])/100,float(x['thermal_time']),float(x['aboveground_nitrogen']),float(x['aboveground_biomass']))
        shutil.rmtree(d,ignore_errors=True)
        E.DIAG_STATE=[]; m.engine(site,wx,soil,cl,N,"leadin"); S=E.DIAG_STATE; E.DIAG_STATE=None
        Ey={}
        for y,doy,eie,ns,pn in S: Ey.setdefault(y,{})[doy]=(ns,pn)
        for y in set(C)&set(Ey):
            com=[k for k in C[y] if k in Ey[y] and 300<=C[y][k][1]<1200]
            if len(com)>20: out.append((site,N,y,st.mean(C[y][k][0] for k in com),st.mean(Ey[y][k][0] for k in com),st.mean(C[y][k][2] for k in com),st.mean(Ey[y][k][1] for k in com)))
    return out
def corr(a,b):
    ma,mb=st.mean(a),st.mean(b); sa=sum((x-ma)**2 for x in a)**.5; sb=sum((y-mb)**2 for y in b)**.5
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/(sa*sb) if sa*sb else float('nan')
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    for N in (0,150):
        q=[r for r in R if r[1]==N]; sites=sorted(set(r[0] for r in q))
        wc=[];ratio=[];sdc=[];sde=[];mc=[];me=[];pc=[];pe=[]
        for s in sites:
            v=[r for r in q if r[0]==s]
            if len(v)>5:
                c=[r[3] for r in v]; e=[r[4] for r in v]; wc.append(corr(c,e)); sdc.append(st.pstdev(c)); sde.append(st.pstdev(e)); mc.append(st.mean(c)); me.append(st.mean(e))
                pc.append(st.mean(r[5] for r in v)); pe.append(st.mean(r[6] for r in v))
        print(f"N={N}: within-site corr of season-mean N mult (engine vs Cycles) mean {st.mean(x for x in wc if x==x):.2f}; mean within-site sd Cycles {st.mean(sdc):.3f} engine {st.mean(sde):.3f}; site-mean mult Cycles {st.mean(mc):.2f} engine {st.mean(me):.2f}; corr of site means {corr(mc,me):.2f}; plant N kg/ha Cycles {st.mean(pc):.0f} engine {st.mean(pe):.0f}")
