"""Implied daily RUE (g/MJ intercepted) from Cycles' own output on days with no water or N stress, by daily mean temperature (2026-10-15). Usage: python3 implied_rue_temp.py"""
import sys,csv,json,datetime,numpy as np
sys.path.insert(0,'.')
import field_data as fd
S=json.load(open('/tmp/w/big240.json'));rows=[]
for site in list(S)[:60]:
    wx,_=fd.resolve_field_weather(*S[site]);prev=None
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N400/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['crop']=='-' or x['biomass']=='-999':prev=None;continue
        b=float(x['biomass']);d=datetime.date.fromisoformat(x['date']);r=wx.get(d.year,{}).get(d.timetuple().tm_yday)
        if prev is not None and r is not None:
            ei=float(x['radiation_interception']);ws=float(x['water_stress']);ns=float(x['nitrogen_stress'])
            if ei>0.3 and ws<0.5 and ns<0.5 and r['solar']>5:
                rows.append(((r['tx']+r['tn'])/2,(b-prev)*100/(ei*r['solar']),float(x['temperature_factor']),r['solar']))
        prev=b
A=np.array(rows);print(len(A),'clean days')
print('Tmean bin   n   implied RUE median   mean   Cycles temperature_factor mean   RUE/factor')
for lo in range(14,36,2):
    m=(A[:,0]>=lo)&(A[:,0]<lo+2)
    if m.sum()>150:print(' %2d-%2d %6d   %.3f   %.3f   %.3f    %.3f'%(lo,lo+2,m.sum(),np.median(A[m,1]),A[m,1].mean(),A[m,2].mean(),np.median(A[m,1])/A[m,2].mean()))
