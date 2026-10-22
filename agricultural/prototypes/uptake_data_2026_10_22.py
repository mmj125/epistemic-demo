"""Cycles daily uptake data (2026-10-22): per site and N (0,150), daily plant N gain (uptake), layer nitrate and ammonium concentration (mg/kg), layer moisture, transpiration,
root and above-ground biomass, N stress, PWP/FC/sat of the site layers, layer thickness and bulk density. Saved /tmp/w/up.npz."""
import os,sys,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m
from multiprocessing import Pool
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
NL=4
def one(si):
    site=sorted(G.S)[si]; lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"up"; m.write_inputs(nm,lat,lon,wx,soil,cl); rows=[]
    hyd=[m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC) for l in soil]
    for N in (0,150):
        subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N{N}/"
        L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; W={r['date']:r for r in rd(d+"dailyWater.csv")}; Cr=rd(d+"dailyCornRM.90.csv")
        prev=None
        for r in Cr:
            try: pn=float(r['total_nitrogen']); ag=float(r['aboveground_biomass']); rt=float(r['root_biomass'])
            except: prev=None; continue
            if pn<0 or rt<0: prev=None; continue
            dt=r['date']; l=L[dt]; w=W[dt]
            row=[si,N,int(dt[:4]),datetime.date.fromisoformat(dt).timetuple().tm_yday, pn-(prev if prev is not None else pn), pn, ag, rt, float(r['nitrogen_stress']), float(w['transpiration'])]
            for i in range(1,NL+1):
                row+= [float(l.get('NO3.%d'%i,0)),float(l.get('NH4.%d'%i,0)),float(w.get('soil_moisture_content.%d'%i,0)),float(l.get('thickness.%d'%i,0)),float(l.get('bulk_density.%d'%i,1.4)),
                       hyd[i-1]['fc'] if i-1<len(hyd) else 0,hyd[i-1]['pwp'] if i-1<len(hyd) else 0]
            rows.append(row); prev=pn
        shutil.rmtree(d,ignore_errors=True)
    return rows
if __name__=="__main__":
    R=Pool(4).map(one,range(24)); A=np.array([r for x in R for r in x]); np.savez("/tmp/w/up.npz",A=A); print(A.shape)
