"""Corn denitrification attribution against Cycles' daily layer-1 states (2026-10-27). For each site (N=150, continuous chain) compares, by month, Cycles' daily denitrification,
profile nitrate, layer-1 saturation and respired carbon with the engine's (E.DIAG_DENIT). Usage: NS=8 python3 denit_attrib_2026_10_27.py"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; os.environ["CROPSEL"]=os.environ.get("CROPSEL","corn"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json')); ks=sorted(S)[::max(1,94//int(os.environ.get("NS","8")))][:int(os.environ.get("NS","8"))]
def rd(path): return [r for r in csv.DictReader(open(path)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; N=150
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    Nn=rd(d+"dailyN.csv"); Wt=rd(d+"dailyWater.csv"); Cc=rd(d+"dailySoilC.csv"); shutil.rmtree(d,ignore_errors=True)
    n=min(len(Nn),len(Wt),len(Cc)); h=m.saxton_rawls(soil[0]['sand'],soil[0]['clay'],soil[0]['soc']*m.OM_FROM_SOC); sat1=h['sat']
    cy={}
    for i in range(n):
        dt=datetime.date.fromisoformat(Nn[i]['date']); cy[(dt.year,dt.timetuple().tm_yday)]=(float(Nn[i]['denitrification']),float(Nn[i]['profile_soil_NO3']),float(Wt[i]['soil_moisture_content.1'])/sat1,float(Cc[i]['residue_respired_carbon'])+float(Cc[i]['soil_organic_matter_respired_carbon']))
    E.DIAG_DENIT=[]; m.engine(site,wx,soil,cl,N,'leadin'); en={}
    for _t in E.DIAG_DENIT:
        y,dd,rel,no3,resp,den=_t[:6]
        if y is not None: en[(y,dd)]=(den,no3,rel,resp)
    E.DIAG_DENIT=None
    rows=[]
    for k in cy:
        if k in en and k[0]>1985: rows.append((datetime.date(k[0],1,1)+datetime.timedelta(k[1]-1)).month, ) if False else rows.append(((datetime.date(k[0],1,1)+datetime.timedelta(k[1]-1)).month,)+cy[k]+en[k])
    return rows
if __name__=="__main__":
    with Pool(4) as p: R=p.map(one,ks)
    A=np.array([r for rr in R for r in rr]); mo=A[:,0]
    print("month | Cycles denit, engine denit (kg N/ha/d) | profile NO3 C / E | layer-1 rel. saturation C / E | respired C Cycles / engine (Mg C/ha/d)")
    for k in range(1,13):
        s=mo==k
        if s.any(): print(f"{k:5d} | {A[s,1].mean():.3f} {A[s,5].mean():.3f} | {A[s,2].mean():6.1f} {A[s,6].mean():6.1f} | {A[s,3].mean():.2f} {A[s,7].mean():.2f} | {A[s,4].mean():.4f} {A[s,8].mean():.4f}")
    print(f"all   | {A[:,1].mean():.3f} {A[:,5].mean():.3f} (x{A[:,5].mean()/A[:,1].mean():.2f}) | {A[:,2].mean():6.1f} {A[:,6].mean():6.1f} | {A[:,3].mean():.2f} {A[:,7].mean():.2f} | {A[:,4].mean():.4f} {A[:,8].mean():.4f}")
