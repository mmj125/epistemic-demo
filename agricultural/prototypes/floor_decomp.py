"""Decompose the error floor that remains when canopy, water, N stress and the planting-day pool are all forced to Cycles' values (2026-10-15).
grain = AG * HI * cf. For each site-year compare engine and Cycles total biomass, aboveground biomass (grain + residue), partition (AG/total) and HI,
then replace one factor at a time by Cycles' value and read the remaining grain MAE. Usage: python3 floor_decomp.py"""
import sys,os,csv,json,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, rhizo_engine as E, run_validation_multisite as m
from multiprocessing import Pool
E.ROOT_C_REALIZED_GROWTH=True
def one(a):
    site,N=a;lat,lon=S.ALL[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=S.force(site,N,('canopy','water','nstress','minn','wclock'))
    r=m.engine(site,wx,soil,cl,N,'leadin')
    H={}
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N{N}/harvest.csv')):
        if x['date'][0]=='#':continue
        H[int(x['date'][:4])]=(float(x['total_biomass']),float(x['grain_yield'])+float(x['aboveground_residue']),float(x['grain_yield']),float(x['harvest_index']))
    cf=m.rv.CORN.get('calibration_factor',1.0)
    rows=[]
    for y in r:
        if y in H and H[y][2]>0.05 and r[y]['grain']>0:
            Tc,Ac,Gc,HIc=H[y];Te,Ae,Ge=r[y]['total'],r[y]['ag'],r[y]['grain'];HIe=Ge/Ae/cf if Ae>0 else 0
            rows.append((y,Tc,Ac,Gc,HIc,Te,Ae,Ge,HIe))
    return site,N,rows,cf
if __name__=="__main__":
    with Pool(4) as p: res=p.map(one,[(s,N) for N in (0,150) for s in S.ALL])
    json.dump(res,open('/tmp/w/floor_decomp.json','w'))
    held=set(m.HELDOUT_SITES)
    for N in (0,150):
        for g,sel in (('tuning',lambda s:s not in held),('held-out',lambda s:s in held)):
            R=[(x,cf) for s,n,rows,cf in res if n==N and sel(s) for x in rows]
            a=np.array([x for x,cf in R]);cf=R[0][1]
            Tc,Ac,Gc,HIc,Te,Ae,Ge,HIe=[a[:,i] for i in range(1,9)]
            mae=lambda g_:np.abs(g_-Gc).mean()
            print(f'N={N} {g:8s} n={len(a)} grain MAE {mae(Ge):.2f} bias {np.mean(Ge-Gc):+.2f} | total {Te.mean():.1f} vs {Tc.mean():.1f}  AG {Ae.mean():.1f} vs {Ac.mean():.1f}  partition {np.mean(Ae/Te):.3f} vs {np.mean(Ac/Tc):.3f}  HI {HIe.mean():.3f} vs {HIc.mean():.3f}')
            print(f'    force AG->Cycles: MAE {mae(Ac*HIe*cf):.2f} | force HI: {mae(Ae*HIc*cf):.2f} | both: {mae(Ac*HIc*cf):.2f} | force total only (engine partition, HI): {mae(Tc*(Ae/Te)*HIe*cf):.2f} | total+partition+HI exact (cf only): {mae(Ac*HIc*cf):.2f}')
