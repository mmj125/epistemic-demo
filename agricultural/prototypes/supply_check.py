"""Annual soil carbon and net nitrogen terms, engine vs Cycles v1.5.20, N=0, 16 sites (needs /tmp/cycles-run15 outputs). Uses SIXPOOL_DIAG. Set FDP to try SIXPOOL_ML_FD_P."""
import os,sys,csv,statistics as st
sys.path.insert(0,'.')
import rhizo_engine as CE
CE.SIXPOOL_ML_FD_P=float(os.environ.get("FDP","0"))
import run_validation_multisite as m
CE.SIXPOOL_DIAG=[]
orig=CE.simulate_season; state={'n':0}
def wrap(*a,**k):
    state['n']+=1
    if k.pop('_last',False) or state.get('last')==state['n']: CE.SIXPOOL_DIAG.clear()
    return orig(*a,**k)
# simulate_season_with_leadin: lead_years=2 -> 3 calls; clear on 3rd
state['last']=3
CE.simulate_season=wrap
orig_l=CE.simulate_season_with_leadin
def wl(*a,**k):
    state['n']=0; return orig_l(*a,**k)
CE.simulate_season_with_leadin=wl; m.simulate_season_with_leadin=wl
def ld(d,f): return [r for r in csv.DictReader(open(f'/tmp/cycles-run15/output/{d}/{f}')) if r['date'][0]!='#']
print('site      | SOMresp C/E | humified C/E | resresp C/E | netmin C/E   (Mg C/ha; kg N/ha)')
YRS=(1990,1999,2008)
for site,(lat,lon) in m.SITES.items():
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
    sc=ld(f'{site}N0','dailySoilC.csv'); dn=ld(f'{site}N0','dailyN.csv')
    acc=[]
    for y in YRS:
        wx2={yy:wx[yy] for yy in wx if yy<=y and yy>=y-2}
        E=m.engine(site,{yy:wx[yy] for yy in wx2},soil,cl,0,'leadin',lead_years=2)
        # engine() loops over all years in wx2; the last call per year is the target only for y; keep only last year's diag
        D=CE.SIXPOOL_DIAG
        cs=sum(d[0] for d in D)/1; res=sum(d[1] for d in D); cor=sum(d[2] for d in D); nn=sum(d[3] for d in D); hum=sum(d[8]+d[9] for d in D)
        c=lambda col:sum(float(r[col]) for r in sc if r['date'].startswith(str(y)))
        n=sum(float(r['net_mineralization']) for r in dn if r['date'].startswith(str(y)))
        acc.append((c('soil_organic_matter_respired_carbon'),cs,c('humified_carbon'),hum,c('residue_respired_carbon'),cor,n,nn))
    a=[st.mean(x[i] for x in acc) for i in range(8)]
    print(f"{site:12s} {a[0]:5.2f}/{a[1]:5.2f} | {a[2]:5.2f}/{a[3]:5.2f} | {a[4]:5.2f}/{a[5]:5.2f} | {a[6]:5.0f}/{a[7]:5.0f}",flush=True)
