"""Cycles' implied radiation use efficiency versus radiation regime (2026-10-17). Cycles daily corn biomass gain / (previous-day interception x solar), unstressed days (water and N stress < 2%), 16+ sites,
N=150. Binned by solar and by clearness index kt = Rs/Ra, then fit RUE = R0 (1 + a fd) with the Erbs diffuse fraction fd(kt) (SI: high-diffuse seasons operate at about 20% higher RUE, Stockle and Kemanian 2008).
Usage: python3 corn_rue_diffuse_2026_10_17.py"""
import os,sys,json,csv,datetime,math,shutil,subprocess,numpy as np
os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import run_validation_multisite as m
def ra(doy,lat):
    phi=math.radians(lat); dr=1+0.033*math.cos(2*math.pi/365*doy); decl=0.409*math.sin(2*math.pi/365*doy-1.39)
    ws=math.acos(max(-1,min(1,-math.tan(phi)*math.tan(decl)))); return (24*60/math.pi)*0.082*dr*(ws*math.sin(phi)*math.sin(decl)+math.cos(phi)*math.cos(decl)*math.sin(ws))
def erbs(kt): return 1-0.09*kt if kt<=0.22 else (0.9511-0.1604*kt+4.388*kt**2-16.638*kt**3+12.336*kt**4 if kt<=0.8 else 0.165)
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json")); ks=sorted(S)[:24]; CY=m.CY; rows=[]
    for site in ks:
        lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); m.REG_LON=lon
        soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.write_inputs(site,lat,lon,wx,soil,cl)
        subprocess.run(["./Cycles",f"{site}N150"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N150/"; C={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": continue
            dt=datetime.date.fromisoformat(x["date"]); C[(dt.year,dt.timetuple().tm_yday)]=(float(x["biomass"]),float(x["radiation_interception"]),float(x["water_stress"])/100,float(x["nitrogen_stress"])/100)
        shutil.rmtree(d,ignore_errors=True)
        for (y,doy),v in C.items():
            p=C.get((y,doy-1))
            if p is None or y not in wx or doy not in wx[y] or p[1]<0.3: continue
            w=wx[y][doy]; tm=(w["tx"]+w["tn"])/2
            if v[0]-p[0]>0.02 and v[2]<0.02 and v[3]<0.02 and 17<=tm<=30:
                R=ra(doy,cl); kt=w["solar"]/R if R>0 else 0
                rows.append(((v[0]-p[0])*100/(p[1]*w["solar"]),kt,w["solar"],erbs(min(kt,1.0))))
    A=np.array(rows); rue,kt,sol,fd=A.T; print("days",len(A))
    for lo,hi in [(0,.3),(.3,.4),(.4,.5),(.5,.6),(.6,.7),(.7,1.2)]:
        s=(kt>=lo)&(kt<hi)
        if s.sum()>150: print(f"  kt {lo:.1f}-{hi:.1f}: implied RUE {np.median(rue[s]):.2f}  mean Erbs fd {fd[s].mean():.2f}  (n={s.sum()})")
    X=np.c_[np.ones(len(fd)),fd]; co=np.linalg.lstsq(X,rue,rcond=None)[0]; r=rue-X@co
    print("RUE = %.3f * (1 + %.3f fd)  [R0 %.3f, a %.3f]  R2 %.3f ; constant-RUE R2 0"%(co[0],co[1]/co[0],co[0],co[1]/co[0],1-r.var()/rue.var()))
    b,a=np.polyfit(np.log(np.clip(kt,.05,1)),np.log(rue),1); r2=np.log(rue)-(a+b*np.log(np.clip(kt,.05,1))); print("power in kt: RUE = %.2f kt^%.2f  R2(log) %.3f"%(np.exp(a),b,1-r2.var()/np.log(rue).var()))
