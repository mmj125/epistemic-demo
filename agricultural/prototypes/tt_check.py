"""Thermal-time check (2026-10-15): Cycles' daily thermal_time increment vs the engine's thermal_time_increment, by daily mean temperature.
Usage: python3 tt_check.py"""
import sys,os,csv,datetime,numpy as np
sys.path.insert(0,'.');os.environ.setdefault("LEAD_YEARS","continuous");sys.argv=['x']
import swap_test as S, cycles_engine_validate as E, run_validation_multisite as m
crop=m.rv.CORN
print('engine params',crop['base_t'],crop['opt_t'],crop['max_t'],'subdaily',E.THERMAL_TIME_SUBDAILY)
pts=[]
for site in ('new_york','wisconsin','iowa','georgia'):
    lat,lon=S.ALL[site];wx,_=m.fd.resolve_field_weather(lat,lon)
    W={(y,d):w for y,rows in wx.items() for d,w in rows.items()}
    prev=None;py=None
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N150/dailyCornRM.90.csv')):
        if x['date'][0]=='#':continue
        d=datetime.date.fromisoformat(x['date']);tt=float(x['thermal_time']);k=(d.year,d.timetuple().tm_yday)
        if prev is not None and py==d.year and x['stage'] in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH','PRE_EMERGENCE') and k in W:
            w=W[k];pts.append((site,(w['tx']+w['tn'])/2,w['tx'],w['tn'],tt-prev,E.thermal_time_increment(w['tx'],w['tn'],crop['base_t'],crop['opt_t'],crop['max_t'])))
        prev=tt;py=d.year
A=np.array([p[1:] for p in pts],float)
print('days',len(A),'total Cycles',A[:,3].sum().round(0),'engine',A[:,4].sum().round(0))
for lo,hi in ((-5,8),(8,12),(12,16),(16,20),(20,24),(24,28),(28,40)):
    s=(A[:,0]>=lo)&(A[:,0]<hi)
    if s.sum()>20:print(f'tmean {lo:3d}-{hi:3d} n={s.sum():5d} Cycles {A[s,3].mean():6.2f} engine {A[s,4].mean():6.2f}')
for site in ('new_york','wisconsin','iowa','georgia'):
    s=np.array([p[0]==site for p in pts]);print(site,'Cycles',A[s,3].sum().round(0),'engine',A[s,4].sum().round(0))
