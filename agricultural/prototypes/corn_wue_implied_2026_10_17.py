"""Implied transpiration-limited conversion in Cycles v1.5.20 corn (2026-10-17): y2 = dTotalBiomass(g/m2) x sqrt(VPD kPa) / actual transpiration (mm) on days with water stress (multiplier < 0.9, so the transpiration limit is the likely binding one) and N multiplier 1; compare the crop-file TRANSPIRATION_USE_EFFICIENCY 8.7 g/kg (times the net growth fraction 0.955 and CO2 scale) and look at its drift with thermal-time fraction, VPD, canopy, temperature. Also the same for unstressed days using potential transpiration. 24 sites, N=150,400."""
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
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; rows={}
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x['date'][0]=='#' or x['biomass']=='-999': continue
            rows[x['date']]=(float(x['biomass']),float(x['radiation_interception']),1-float(x['water_stress'])/100,1-float(x['nitrogen_stress'])/100,float(x['thermal_time'])/1800.0,float(x['potential_transpiration']))
        tr={};vpd={}
        for x in csv.DictReader(open(d+"dailyWater.csv")):
            if x['date'][0]!='#': tr[x['date']]=float(x['transpiration'])
        for x in csv.DictReader(open(d+"dailyEnviron.csv")):
            if x['date'][0]!='#': vpd[x['date']]=float(x['vapor_pressure_deficit'])
        shutil.rmtree(d,ignore_errors=True); ds=sorted(rows)
        for i in range(1,len(ds)):
            a,b=rows[ds[i-1]],rows[ds[i]]
            dB=(b[0]-a[0])*100
            if dB>0 and tr.get(ds[i],0)>0.3 and vpd.get(ds[i],0)>0.1 and b[3]>=0.999 and a[3]>=0.999:
                out.append((dB*vpd[ds[i]]**0.5/tr[ds[i]],b[2],b[4],vpd[ds[i]],b[1],(wx[int(ds[i][:4])][datetime.date.fromisoformat(ds[i]).timetuple().tm_yday]['tx']+wx[int(ds[i][:4])][datetime.date.fromisoformat(ds[i]).timetuple().tm_yday]['tn'])/2,tr[ds[i]]/b[5] if b[5]>0 else 1.0))
    return out
if __name__=="__main__":
    S=json.load(open("/tmp/w/s24.json"))
    with Pool(4) as p: R=sum(p.map(one,list(S.items())),[])
    import numpy as np
    A=np.array(R); print("days",len(A))
    for lab,k in (("water-stressed (mult<0.9)",A[:,1]<0.9),("unstressed",A[:,1]>=0.999)):
        a=A[k]; print(lab,"n",len(a),"median y2 %.2f mean %.2f (crop file TUE 8.7)"%(np.median(a[:,0]),a[:,0].mean()))
        for lo in np.arange(0.1,1.0,0.2):
            kk=(a[:,2]>=lo)&(a[:,2]<lo+.2)
            if kk.sum()>100: print(f"   ttf {lo:.1f}-{lo+.2:.1f}: n {kk.sum():6d} median y2 {np.median(a[kk,0]):.2f}")
