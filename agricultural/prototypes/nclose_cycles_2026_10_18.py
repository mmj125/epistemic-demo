"""Does Cycles' mineral N budget close? (2026-10-18) Cycles output only, corn N=0, 24 sites. Daily: d(NO3+NH4) vs net mineralization, plant N uptake (change in total_nitrogen when positive), leaching, bypass, volatilization,
denitrification, N2O terms; reports the mean daily residual for several accounting variants, and the annual sums of each flux."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    Nn=rd(d+"dailyN.csv"); C=rd(d+"dailyCornRM.90.csv"); shutil.rmtree(d,ignore_errors=True)
    pn={r['date']:(float(r['total_nitrogen']),float(r['nitrogen_fixation']),float(r['nitrogen_auto_added'])) for r in C if r['total_nitrogen']!='-999'}
    rows=[]; prev=None; pp=None
    for r in Nn:
        f=lambda k:float(r[k]); pool=f('profile_soil_NO3')+f('profile_soil_NH4')
        up=0.0
        if r['date'] in pn and pp is not None: up=pn[r['date']][0]-pp
        pp=pn[r['date']][0] if r['date'] in pn else None
        if prev is not None:
            rows.append((pool-prev, f('net_mineralization'), up, f('NO3_leaching'), f('NH4_leaching'), f('NO3_bypass'), f('NH4_bypass'), f('volatilization'), f('denitrification'), f('N2O_from_nitrification'), f('N2O_from_denitrification'), f('nitrification'), f('mineralization'), f('immobilization'), f('soil_organic_nitrogen')))
        prev=pool
    return np.array(rows)
if __name__=="__main__":
    A=np.vstack([a for a in Pool(4).map(one,sorted(S)) if len(a)]); np.save('/tmp/w/nclose_cycles.npy',A)
    dP,nm,up,l3,l4,b3,b4,vo,de,n2n,n2d,ni,mi,im,son=A.T
    print('rows',len(A),' mean per day (kg N/ha): dPool %.4f | netmin %.4f | uptake(+) %.4f | leach NO3 %.4f NH4 %.4f | bypass %.4f %.4f | volat %.4f | denit %.4f | N2O nit %.5f den %.5f'%tuple(x.mean() for x in (dP,nm,np.maximum(up,0),l3,l4,b3,b4,vo,de,n2n,n2d)))
    up=np.maximum(up,0)
    out=l3+l4+b3+b4+vo+de
    for lab,res in (('dPool - (netmin - uptake - leach - bypass - volat - denit)',dP-(nm-up-out)),
                    ('... also minus N2O (nit + den)',dP-(nm-up-out-n2n-n2d)),
                    ('... uptake ignored',dP-(nm-out)),
                    ('... net min replaced by (mineralization + immobilization)',dP-(mi+im-up-out)),
                    ('... net min replaced by (mineralization - immobilization)',dP-(mi-im-up-out))):
        print(f'  {lab:70s} mean residual {res.mean():+.5f}/day ({365*res.mean():+.2f}/yr), rms {np.sqrt((res**2).mean()):.4f}')
