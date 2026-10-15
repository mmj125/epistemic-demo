"""Cycles' daily temperature_factor vs daily mean temperature, pooled over sites (2026-10-15). Usage: python3 tempfactor_check.py"""
import sys,csv,json,datetime,numpy as np
sys.path.insert(0,'.')
import field_data as fd, cycles_engine_validate as E, run_validation as rv
S=json.load(open('/tmp/w/big240.json'));rows=[]
for site in list(S)[:40]:
    wx,_=fd.resolve_field_weather(*S[site])
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N400/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['crop']=='-' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);r=wx.get(d.year,{}).get(d.timetuple().tm_yday)
        if r is None:continue
        rows.append(((r['tx']+r['tn'])/2,r['tx'],r['tn'],float(x['temperature_factor']),float(x['radiation_interception'])))
A=np.array(rows);print(len(A))
crop=rv.CORN;print('engine tr_min_t',crop['tr_min_t'],'tr_threshold_t',crop['tr_threshold_t'],'rad floor',crop.get('rad_temp_floor'),crop.get('rad_temp_plateau_t'))
for lo in range(0,34,2):
    m=(A[:,0]>=lo)&(A[:,0]<lo+2)
    if m.sum()>200:
        eng=np.mean([E.transpiration_temp_factor(t,crop['tr_min_t'],crop['tr_threshold_t']) for t in A[m,0]])
        print('Tmean %2d-%2d n=%6d  Cycles factor mean %.3f sd %.3f   engine transp factor %.3f   engine radiation factor %.3f'%(lo,lo+2,m.sum(),A[m,3].mean(),A[m,3].std(),eng,np.mean([E.radiation_temp_factor(t,crop['tr_min_t'],crop.get('rad_temp_floor',0.0),crop.get('rad_temp_plateau_t',crop['tr_threshold_t'])) for t in A[m,0]])))
print('\nwarm side: factor by Tmax and by Tmean (rows with Tmean>=22)')
w=A[A[:,0]>=22]
for nm,col in (('Tmax',1),('Tmean',0)):
    for lo in range(24,42,2):
        m=(w[:,col]>=lo)&(w[:,col]<lo+2)
        if m.sum()>150:print(' %s %2d-%2d n=%6d factor %.3f sd %.3f'%(nm,lo,lo+2,m.sum(),w[m,3].mean(),w[m,3].std()))
print('\ncool side: factor by Tmin for Tmean 8-14')
c=A[(A[:,0]>=8)&(A[:,0]<14)]
for lo in range(-6,14,2):
    m=(c[:,2]>=lo)&(c[:,2]<lo+2)
    if m.sum()>100:print(' Tmin %3d-%3d n=%5d factor %.3f sd %.3f'%(lo,lo+2,m.sum(),c[m,3].mean(),c[m,3].std()))
