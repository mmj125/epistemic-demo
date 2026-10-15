"""What makes Cycles' potential transpiration exactly zero on a crop day with canopy cover (2026-10-15). Usage: python3 zeroTR_trigger.py"""
import sys,csv,json,datetime,numpy as np
sys.path.insert(0,'.')
import field_data as fd
S=json.load(open('/tmp/w/big240.json'));rows=[]
for site in list(S)[:80]:
    lat,lon=S[site];wx,_=fd.resolve_field_weather(lat,lon)
    W={x['date']:x for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N400/dailyWater.csv')) if x['date'][0]!='#'}
    L={x['date']:x for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N400/dailySoilLayersCN.csv')) if x['date'][0]!='#'}
    prevz=0;prevpp=0
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N400/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['crop']=='-' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);r=wx[d.year][d.timetuple().tm_yday];ei=float(x['radiation_interception']);cy=float(x['potential_transpiration'])
        if ei<0.2 or x['stage'] not in('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH'):prevz=0;continue
        w=W.get(x['date'])
        if w is None:continue
        nl=sum(1 for k in w if k.startswith('soil_moisture_content.'))
        th1=float(w['soil_moisture_content.1']);th2=float(w.get('soil_moisture_content.2',w['soil_moisture_content.1']))
        rows.append((cy==0,r['pp'],r['tx'],r['tn'],r['rhx'],r['rhn'],prevz,float(w['soil_evaporation']),float(w['transpiration']),th1,th2,ei,float(w['irrigation'])+r['pp']>0.5))
        prevz=1 if cy==0 else 0
A=np.array(rows,dtype=float);z=A[:,0]==1;print('days',len(A),'zero potential TR share %.1f%%'%(100*z.mean()))
names=['pp','tx','tn','rhx','rhn','prev-day zero','soil evap','transp','theta1','theta2','canopy']
for i,nm in enumerate(names,start=1):print('  %-14s zero days mean %8.2f  other days mean %8.2f'%(nm,A[z,i].mean(),A[~z,i].mean()))
print('share of zero days that had rain>0.5mm: %.2f ; share of non-zero days with rain: %.2f'%((A[z,1]>0.5).mean(),(A[~z,1]>0.5).mean()))
print('P(zero | prev day zero) %.2f ; P(zero | prev day not zero) %.2f'%(z[A[:,6]==1].mean(),z[A[:,6]==0].mean()))
print('transpiration on zero-potTR days: mean %.3f mm'%A[z,8].mean())
