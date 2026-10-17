"""What drives Cycles' implied daily conversion (2026-10-17): on unstressed corn days (water and N multipliers 1, previous day too), y = dTotalBiomass(g/m2) / (previous-day canopy x solar MJ/m2), 24 sites, N=150 and 400. Binned by thermal-time fraction, mean temperature, solar and canopy, and a multiple regression with standardized coefficients. Usage: python3 corn_conversion_drivers_2026_10_17.py"""
import os,sys,json,csv,datetime,shutil,subprocess
os.environ["N_LEVELS"]="150,400"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E
from multiprocessing import Pool
CY=m.CY
def one(a):
    site,(lat,lon)=a
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); out=[]
    for N in (150,400):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; rows=[]
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999': rows.append(None); continue
            dt=datetime.date.fromisoformat(x['date']); rows.append((dt.year,dt.timetuple().tm_yday,float(x['biomass']),float(x['radiation_interception']),1-float(x['water_stress'])/100,1-float(x['nitrogen_stress'])/100,float(x['temperature_factor']),float(x['thermal_time'])/1800.0))
        env={}
        for x in csv.DictReader(open(d+"dailyEnviron.csv")):
            if x['date'][0]!='#': env[x['date']]=float(x['vapor_pressure_deficit'])
        shutil.rmtree(d,ignore_errors=True)
        for i in range(2,len(rows)):
            r,p=rows[i],rows[i-1]
            if not (r and p): continue
            y,doy,b,c,w,n,tf,ttf=r
            if w>=0.999 and n>=0.999 and p[4]>=0.999 and p[5]>=0.999 and p[3]>0.03 and b-p[2]>0:
                wd=wx[y][doy]; tm=(wd['tx']+wd['tn'])/2
                out.append(((b-p[2])*100/(p[3]*wd['solar']),ttf,tm,wd['solar'],p[3],tf,wd['tx']-wd['tn'],wd['rhx'],wd['rhn'],E.clearness_diffuse_fraction(doy,lat,wd['solar'])))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    import numpy as np
    A=np.array(R); y=A[:,0]; print("days",len(A),"mean conversion %.3f"%y.mean())
    def b(col,name,edges):
        print(name); 
        for lo,hi in zip(edges[:-1],edges[1:]):
            k=(A[:,col]>=lo)&(A[:,col]<hi)
            if k.sum()>100: print(f"   {lo:.2f}-{hi:.2f}: n {k.sum():6d} conversion {y[k].mean():.3f}")
    b(1,"by thermal-time fraction",[0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.01]); b(2,"by mean temperature",[0,10,14,18,22,26,30,40]); b(3,"by solar",[0,10,15,20,25,35]); b(4,"by previous-day canopy",[0.03,.1,.2,.4,.6,.8,1.01]); b(5,"by Cycles temperature_factor",[0,.5,.8,.95,.99,1.01])
    b(9,"by Erbs diffuse fraction",[0,.2,.3,.4,.5,.6,.8,1.01])
    for nm,cols in (("ttf+tmean+solar",[1,2,3]),("ttf+tmean+diffuse",[1,2,9]),("tmean+diffuse",[2,9]),("ttf+tmean+solar+diffuse+canopy",[1,2,3,9,4])):
        X=A[:,cols]; Xs=(X-X.mean(0))/X.std(0); Xs=np.column_stack([np.ones(len(Xs)),Xs]); be=np.linalg.lstsq(Xs,y,rcond=None)[0]; print(nm,"R2 %.3f"%(1-((y-Xs@be)**2).sum()/((y-y.mean())**2).sum()),[round(float(c),3) for c in be[1:]])
    X=np.column_stack([A[:,1],A[:,2],A[:,3],A[:,4],A[:,6],A[:,7]]); names=["ttf","tmean","solar","canopy_prev","diurnal range","rh max"]
    Xs=(X-X.mean(0))/X.std(0); Xs=np.column_stack([np.ones(len(Xs)),Xs]); beta=np.linalg.lstsq(Xs,y,rcond=None)[0]; r2=1-((y-Xs@beta)**2).sum()/((y-y.mean())**2).sum()
    print("standardized regression R2 %.3f: "%r2+", ".join(f"{n} {c:+.3f}" for n,c in zip(names,beta[1:])))
