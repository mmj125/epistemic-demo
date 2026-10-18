"""Denitrification state attribution (2026-10-18): align Cycles' daily denitrification, nitrate, layer-1 saturation and respired carbon with the engine's
inputs to its denitrification law (denitrification_flux_resp) by (year, doy), and evaluate the engine law with Cycles' states swapped in one factor at a time.
Usage: python3 denit_states_2026_10_18.py N_SITES"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
if os.environ.get("SUBDAY")=="0": E.SUBDAY_DENIT=False   # feed the law end-of-day layer-1 saturation, the basis it was fitted on
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json'))
def rd(path): return [r for r in csv.DictReader(open(path)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    Nn=rd(d+"dailyN.csv"); Wt=rd(d+"dailyWater.csv"); Cc=rd(d+"dailySoilC.csv"); shutil.rmtree(d,ignore_errors=True)
    n=min(len(Nn),len(Wt),len(Cc)); h=m.saxton_rawls(soil[0]['sand'],soil[0]['clay'],soil[0]['soc']*m.OM_FROM_SOC); sat1=h['sat']
    dates=[Nn[i]['date'] for i in range(n)]
    cy=dict(y=np.array([float(Nn[i]['denitrification']) for i in range(n)]),no3=np.array([float(Nn[i]['profile_soil_NO3']) for i in range(n)]),
            rel=np.clip(np.array([float(Wt[i]['soil_moisture_content.1']) for i in range(n)])/sat1,0.02,1.2),
            resp=np.array([float(Cc[i]['residue_respired_carbon'])+float(Cc[i]['soil_organic_matter_respired_carbon']) for i in range(n)]))
    calls=[]; o=E.denitrification_flux_resp
    def w(no3,rel,resp):
        r=o(no3,rel,resp); f=sys._getframe(1); doy=f.f_locals['w']['doy']; calls.append((doy,no3,rel,resp,r)); return r
    E.denitrification_flux_resp=w; E.DIAG_THETA=[]; E.DIAG_NO3=[]
    try: m.engine(site,wx,soil,cl,N,'leadin')
    finally: E.denitrification_flux_resp=o
    TH=[(y,dd) for (y,dd,_) in E.DIAG_THETA]; E.DIAG_THETA=None
    NO3E={(y,dd):sum(v) for (y,dd,v) in E.DIAG_NO3 if y is not None}; E.DIAG_NO3=None
    idx={(datetime.date.fromisoformat(dt).year,datetime.date.fromisoformat(dt).timetuple().tm_yday):i for i,dt in enumerate(dates)}
    en=dict(y=np.zeros(n),no3=np.zeros(n),rel=np.full(n,0.02),resp=np.zeros(n)); j=0
    for doy,no3,rel,resp,r in calls:
        while j<len(TH) and TH[j][1]!=doy: j+=1
        if j>=len(TH): break
        i=idx.get(TH[j]); j+=1
        if i is not None: en['y'][i]=r; en['no3'][i]=no3; en['rel'][i]=rel; en['resp'][i]=resp
    yrs=n/365.25
    mc=[[] for _ in range(12)]; me=[[] for _ in range(12)]
    for i,dt in enumerate(dates):
        d0=datetime.date.fromisoformat(dt); k=(d0.year,d0.timetuple().tm_yday)
        if k in NO3E: mc[d0.month-1].append(cy['no3'][i]); me[d0.month-1].append(NO3E[k])
    law=lambda no3,rel,resp: np.array([o(a,b,c) for a,b,c in zip(no3,rel,resp)])
    mask=en['no3']>0   # days on which the engine evaluated its law
    out=dict(site=site,N=N,yrs=yrs,cyc=cy['y'].sum()/yrs,eng=en['y'].sum()/yrs)
    out['law_on_cycles_states']=law(cy['no3'],cy['rel'],cy['resp']).sum()/yrs
    for lab,(a,b,c) in {'nitrate_from_cycles':('cy','en','en'),'sat_from_cycles':('en','cy','en'),'resp_from_cycles':('en','en','cy'),'sat+resp_from_cycles':('en','cy','cy'),'nitrate+sat_from_cycles':('cy','cy','en'),'nitrate+resp_from_cycles':('cy','en','cy')}.items():
        pick=lambda who,k:(cy if who=='cy' else en)[k]
        out[lab]=np.where(mask,law(pick(a,'no3'),pick(b,'rel'),pick(c,'resp')),0.0).sum()/yrs
    out['means']=dict(no3_c=float(cy['no3'].mean()),no3_e=float(en['no3'][mask].mean()),rel6_c=float((cy['rel']**6.03).mean()),rel6_e=float((en['rel'][mask]**6.03).sum()/len(cy['rel'])),resp_c=float(cy['resp'].mean()*1000),resp_e=float(en['resp'][mask].sum()*1000/len(cy['resp'])))
    out['monthly_no3']=[[float(np.mean(a)) if a else float('nan') for a in mc],[float(np.mean(a)) if a else float('nan') for a in me]]
    return out
if __name__=="__main__":
    ks=sorted(S); n=int(sys.argv[1]); ks=[ks[i] for i in range(0,len(ks),max(1,len(ks)//n))][:n]+[x for x in ("f013_410_760","f038_440_700") if x not in ks]
    with Pool(4) as p: R=p.map(one,[(k,N) for k in ks for N in (0,150)])
    json.dump(R,open('/tmp/w/denit_states.json','w'),default=float)
    for N in (0,150):
        r=[x for x in R if x['N']==N]; mean=lambda k:np.mean([x[k] for x in r])
        print(f"\nN={N}  sites {len(r)}  kg N/ha/yr:  Cycles actual {mean('cyc'):.2f} | engine actual {mean('eng'):.2f} | engine law on Cycles' states {mean('law_on_cycles_states'):.2f}")
        for k in ('nitrate_from_cycles','sat_from_cycles','resp_from_cycles','nitrate+sat_from_cycles','nitrate+resp_from_cycles','sat+resp_from_cycles'): print(f"   engine law with Cycles' {k.replace('_from_cycles',''):14s} swapped in: {mean(k):.2f}")
        M=np.array([x['monthly_no3'] for x in r]); print('   monthly profile nitrate kg/ha, Cycles:',np.round(np.nanmean(M[:,0],0),0).tolist(),'\n   monthly profile nitrate kg/ha, engine:',np.round(np.nanmean(M[:,1],0),0).tolist())
        mm=lambda k:np.mean([x['means'][k] for x in r]); print(f"   mean state: nitrate kg/ha C {mm('no3_c'):.1f} E {mm('no3_e'):.1f} | rel1^6 C {mm('rel6_c'):.4f} E {mm('rel6_e'):.4f} | respired C kg/ha/d C {mm('resp_c'):.2f} E {mm('resp_e'):.2f}")
