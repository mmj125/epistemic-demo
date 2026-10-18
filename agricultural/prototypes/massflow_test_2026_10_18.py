"""Does mass flow limit Cycles' N uptake? (2026-10-18) Paper Sec 2.4: the water flux from each layer determines each species' access to mineral N.
Per season day from Cycles' own output: uptake = diff of crop total_nitrogen (kg/ha); mass-flow supply = transpiration (mm) x profile nitrate concentration (mg/L,
nitrate kg/ha / profile water mm x 100), also with the saturated-volume concentration. Compare in-season sums and daily relation, N=0 and 150.
Usage: python3 massflow_test_2026_10_18.py N_SITES"""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    C=rd(d+"dailyCornRM.90.csv"); W=rd(d+"dailyWater.csv"); L=rd(d+"dailySoilLayersCN.csv"); Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    nl=len([k for k in L[0] if k.startswith('NO3.')]); th=np.array([float(L[0][f'thickness.{k+1}']) for k in range(nl)]); bd=np.array([float(L[0][f'bulk_density.{k+1}']) for k in range(nl)])
    n=min(len(C),len(W),len(L),len(Nn))
    tn=np.array([float(C[i]['total_nitrogen']) if C[i]['biomass']!='-999' else np.nan for i in range(n)])   # kg/ha already
    up=np.diff(tn,prepend=np.nan); tr=np.array([float(W[i]['transpiration']) for i in range(n)])
    no3=np.array([[float(L[i][f'NO3.{k+1}'])*bd[k]*th[k]*10 for k in range(nl)] for i in range(n)]).sum(1)
    wat=np.array([[float(W[i][f'soil_moisture_content.{k+1}'])*th[k]*1000 for k in range(nl)] for i in range(n)]).sum(1)
    sat=((1-bd/2.65)*th*1000).sum()
    prev=lambda a:np.concatenate([[np.nan],a[:-1]])
    mf=tr*prev(no3)/np.maximum(prev(wat),1e-6); mfs=tr*prev(no3)/sat
    ok=np.isfinite(up)&(up>-0.5)&(tr>0.05)
    yrs=sorted({C[i]['date'][:4] for i in range(n) if ok[i]})
    rows=[]
    for y in yrs:
        s=np.array([ok[i] and C[i]['date'][:4]==y for i in range(n)])
        if s.sum()>40: rows.append((up[s].sum(),mf[s].sum(),mfs[s].sum(),tn[s].max()))
    return dict(site=site,N=N,rows=rows,corr=float(np.corrcoef(up[ok],mf[ok])[0,1]) if ok.sum()>20 else np.nan)
if __name__=="__main__":
    ks=sorted(S); n=int(sys.argv[1]); ks=[ks[i] for i in range(0,len(ks),max(1,len(ks)//n))][:n]
    with Pool(4) as p: R=p.map(one,[(k,N) for k in ks for N in (0,150)])
    for N in (0,150):
        rr=np.array([r for x in R if x['N']==N for r in x['rows']]); 
        print(f"N={N}: site-years {len(rr)}: in-season Cycles uptake {rr[:,0].mean():.1f} kg/ha | mass-flow supply (current water) {rr[:,1].mean():.1f} | (saturated volume) {rr[:,2].mean():.1f} | ratio uptake/supply median {np.median(rr[:,0]/rr[:,1]):.2f} (p10 {np.percentile(rr[:,0]/rr[:,1],10):.2f}, p90 {np.percentile(rr[:,0]/rr[:,1],90):.2f}); corr uptake vs supply across site-years {np.corrcoef(rr[:,0],rr[:,1])[0,1]:.2f}; daily corr mean {np.nanmean([x['corr'] for x in R if x['N']==N]):.2f}")
