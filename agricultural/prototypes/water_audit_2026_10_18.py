"""Soil water audit (2026-10-18): engine against Cycles per in-season day, corn, N=150, 24 sites, continuous chain, by Cycles' canopy stage (radiation_interception of the crop:
under 0.2, 0.2 to 0.6, over 0.6). Compares ETo, soil evaporation, residue evaporation, residue cover (dailyResidue radiation_interception), transpiration, and layer 1 to 3 moisture.
Usage: python3 water_audit_2026_10_18.py   (ENGINE_OVR as usual)"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def key(s): d=datetime.date.fromisoformat(s); return (d.year,d.timetuple().tm_yday)
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    Wt=rd(d+"dailyWater.csv"); En=rd(d+"dailyEnviron.csv"); Re=rd(d+"dailyResidue.csv"); Cr=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    C={}
    for w_,e_,r_,c_ in zip(Wt,En,Re,Cr):
        if c_['biomass']=='-999' or c_['stage'] not in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH','MATURITY'): continue
        C[key(w_['date'])]=dict(soil=float(w_['soil_evaporation']),res=float(w_['residue_evaporation']),tr=float(w_['transpiration']),eto=float(e_['reference_evapotranspiration']),rcov=float(r_['radiation_interception']),
                                can=float(c_['radiation_interception']),th=[float(w_[k]) for k in ('soil_moisture_content.1','soil_moisture_content.2','soil_moisture_content.3') if k in w_],pp=float(e_['precipitation']))
    E.DIAG_EVAP=[]; E.DIAG_THETA=[]; E.DIAG_WATER=[]; m.engine(site,wx,soil,cl,150,'leadin'); EV=E.DIAG_EVAP; TH=E.DIAG_THETA; WA=E.DIAG_WATER; E.DIAG_EVAP=E.DIAG_THETA=E.DIAG_WATER=None
    thd={(y,doy):t for (y,doy,t) in TH if y is not None}; wad={(y,doy):(tra,trp) for (y,doy,ws,tc,trp,tra,td) in WA if y is not None}
    rows=[]
    for (y,doy,se,re_,eto,rc) in EV:
        k=(y,doy)
        if y is None or k not in C or k not in thd: continue
        c=C[k]; t=thd[k]; tra,trp=wad.get(k,(np.nan,np.nan))
        pad=lambda v:(list(v)+[np.nan]*3)[:3]
        rows.append((c['can'],c['soil'],se,c['res'],re_,c['eto'],eto,c['rcov'],rc,c['tr'],tra,*pad(c['th']),*pad(t),c['pp']))
    return rows
if __name__=="__main__":
    with Pool(4) as p: R=p.map(one,sorted(S))
    A=np.array([r for rr in R for r in rr],float); print('in-season days',len(A),'sites',len(R))
    names=['can','cy_soil','en_soil','cy_res','en_res','cy_eto','en_eto','cy_rcov','en_rcov','cy_tr','en_tr','cy_th1','cy_th2','cy_th3','en_th1','en_th2','en_th3','pp']
    ix={n:i for i,n in enumerate(names)}
    for lab,lo,hi in (('canopy < 0.2',-1,0.2),('canopy 0.2 to 0.6',0.2,0.6),('canopy > 0.6',0.6,2)):
        s=(A[:,0]>=lo)&(A[:,0]<hi); B=A[s]; g=lambda n:np.nanmean(B[:,ix[n]])
        print(f"{lab:18s} days {s.sum():6d} | ETo C {g('cy_eto'):.2f} E {g('en_eto'):.2f} | soil evap/day C {g('cy_soil'):.3f} E {g('en_soil'):.3f} ratio {g('en_soil')/g('cy_soil'):.2f} | residue evap C {g('cy_res'):.3f} E {g('en_res'):.3f} | residue cover C {g('cy_rcov'):.3f} E {g('en_rcov'):.3f} | transp C {g('cy_tr'):.2f} E {g('en_tr'):.2f}")
        print(f"{'':18s} theta1 C {g('cy_th1'):.3f} E {g('en_th1'):.3f} (E-C {g('en_th1')-g('cy_th1'):+.3f}) | theta2 C {g('cy_th2'):.3f} E {g('en_th2'):.3f} ({g('en_th2')-g('cy_th2'):+.3f}) | theta3 {g('en_th3')-g('cy_th3'):+.3f}")
    print('season totals per day-weighted mean: soil evap C %.3f E %.3f; residue evap C %.3f E %.3f; transp C %.2f E %.2f'%tuple(np.nanmean(A[:,ix[n]]) for n in ('cy_soil','en_soil','cy_res','en_res','cy_tr','en_tr')))
