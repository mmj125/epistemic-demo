"""Nitrate transport test on Cycles' own daily output (2026-10-18): on each drainage day, compare the nitrate Cycles leaches out of the profile with what
well-mixed-reservoir rules would give from Cycles' own layer nitrate and moisture. Usage: N=150 SITES=a,b python3 leach_transport_2026_10_18.py"""
import os,sys,json,csv,shutil,subprocess,datetime
N=int(os.environ.get("N","150")); os.environ["N_LEVELS"]=str(N); os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
S=json.load(open('sitesets/fresh94.json')); sites=os.environ["SITES"].split(",")
def rd(path):
    return [x for x in csv.DictReader(open(path)) if x['date'][0]!='#']
for site in sites:
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N{N}/"
    W=rd(d+"dailyWater.csv"); C=rd(d+"dailySoilLayersCN.csv"); Nn=rd(d+"dailyN.csv"); shutil.rmtree(d,ignore_errors=True)
    nl=len([k for k in C[0] if k.startswith('NO3.')]); th=[float(C[0][f'thickness.{k+1}']) for k in range(nl)]; bd=[float(C[0][f'bulk_density.{k+1}']) for k in range(nl)]
    n=min(len(W),len(C),len(Nn)); no3=np.array([[float(C[i][f'NO3.{k+1}'])*bd[k]*th[k]*10 for k in range(nl)] for i in range(n)])   # kg N/ha per layer
    wat=np.array([[float(W[i][f'soil_moisture_content.{k+1}'])*th[k]*1000 for k in range(nl)] for i in range(n)])   # mm per layer
    dr=np.array([float(W[i]['drainage']) for i in range(n)]); lch=np.array([float(Nn[i]['NO3_leaching']) for i in range(n)])
    byp=np.array([float(W[i]['bypass']) for i in range(n)])
    P={}
    prev=lambda a:np.vstack([a[:1],a[:-1]])
    nb,wb=prev(no3)[:,-1],prev(wat)[:,-1]; P['bottom layer, previous day state']=dr*nb/np.maximum(wb,1e-6)
    P['bottom layer, same-day state, +drainage in volume']=dr*no3[:,-1]/np.maximum(wat[:,-1]+dr,1e-6)
    P['whole profile mean concentration, previous day']=dr*prev(no3).sum(1)/np.maximum(prev(wat).sum(1),1e-6)
    P['bottom layer, previous day, drainage mixed in (n/(w+dr))']=dr*nb/np.maximum(wb+dr,1e-6)
    ok=(lch>0.02)&(dr>0.5)&(nb>0.2)
    if ok.sum()>30:
        V=nb[ok]*dr[ok]/lch[ok]; x=dr[ok]; fr=1-lch[ok]/nb[ok]   # V = volume that reproduces Cycles if leached = n*dr/V ; fr = fraction of the layer nitrate left after the day
        print(f"  [{site}] effective mixing volume / previous-day layer water (wb), by drainage size, median over days:")
        for lo,hi in ((0.5,2),(2,5),(5,10),(10,20),(20,40),(40,1e9)):
            s_=(x>=lo)&(x<hi)
            if s_.sum()>3: print(f"     drainage {lo:g}-{hi:g} mm  n={int(s_.sum()):4d}  V/wb={np.median(V[s_]/wb[ok][s_]):.2f}  (V-dr)/wb={np.median((V[s_]-x[s_])/wb[ok][s_]):.2f}  frac N leached={np.median(lch[ok][s_]/nb[ok][s_]):.3f}  dr/wb={np.median(x[s_]/wb[ok][s_]):.3f}")
    sat=np.array([(1-bd[k]/2.65)*th[k]*1000 for k in range(nl)])   # saturated water per layer, mm (porosity from bulk density, particle density 2.65)
    Vs=sat[-1]; print(f"  [{site}] bottom layer: saturation {Vs:.0f} mm; median water {np.median(wat[:,-1]):.0f} mm ({np.median(wat[:,-1])/Vs:.2f} of sat); max water {wat[:,-1].max():.0f} mm")
    if ok.sum()>30: print(f"     median V / saturated volume = {np.median(V/Vs):.2f}  | V/Vs by drainage tercile:",[round(float(np.median((V/Vs)[(x>=lo)&(x<hi)])),2) for lo,hi in ((0.5,2),(2,6),(6,1e9)) if ((x>=lo)&(x<hi)).sum()>3])
    P['saturated bottom layer: n*dr/Vsat']=dr*nb/Vs; P['saturated bottom layer, drainage added: n*dr/(Vsat+dr)']=dr*nb/(Vs+dr)
    a=lch.sum(); print(f"{site} N={N} layers {nl} years {n/365:.0f}: Cycles leached {a/(n/365):.1f} kg/yr, drainage {dr.sum()/(n/365):.0f} mm/yr (bypass {byp.sum()/(n/365):.1f})")
    for k,v in P.items(): print(f"    {k:58s} {v.sum()/a:5.2f} x Cycles   daily corr {np.corrcoef(v,lch)[0,1]:.2f}")
