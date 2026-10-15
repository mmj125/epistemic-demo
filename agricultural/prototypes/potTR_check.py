"""Engine potential transpiration (formula applied to Cycles' own daily canopy) vs Cycles' potential_transpiration column, per site (2026-10-15). Usage: python3 potTR_check.py"""
import sys,csv,json,datetime,numpy as np
sys.path.insert(0,'.')
import field_data as fd, cycles_engine_validate as E, run_validation as rv, run_validation_multisite as m
S=json.load(open('/tmp/w/big240.json'));S.update(json.load(open('/tmp/w/old28.json')))
crop=rv.CORN;out=[]
for site in list(S)[:110]:
    lat,lon=S[site];wx,_=fd.resolve_field_weather(lat,lon);cl=m.lat_of(lat,lon)
    ce=[];cy=[];meta=[]
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N400/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['crop']=='-' or x['biomass']=='-999':continue
        d=datetime.date.fromisoformat(x['date']);r=wx.get(d.year,{}).get(d.timetuple().tm_yday)
        if r is None:continue
        ei=float(x['radiation_interception']);eto=E.eto_fao56(d.timetuple().tm_yday,r['tx'],r['tn'],r['solar'],r['rhx'],r['rhn'],r['wind'],cl)
        tf=E.transpiration_temp_factor((r['tx']+r['tn'])/2,crop['tr_min_t'],crop['tr_threshold_t'])
        ce.append(((1+(crop['kc']-1)*ei)*ei*eto*tf,(1+(crop['kc']-1)*ei)*ei*eto,eto,ei));cy.append(float(x['potential_transpiration']));meta.append(((r['tx']+r['tn'])/2,(r['rhx']+r['rhn'])/2,r['wind']))
    ce=np.array(ce);cy=np.array(cy);meta=np.array(meta)
    out.append((site,ce[:,0].sum()/cy.sum(),ce[:,1].sum()/cy.sum(),np.mean(meta[:,0]),np.mean(meta[:,1]),np.mean(meta[:,2]),lat))
A=np.array([o[1:] for o in out])
print('sites',len(out));print('ratio engine/Cycles potential TR: with temp factor mean %.2f sd %.2f | without temp factor mean %.2f sd %.2f'%(A[:,0].mean(),A[:,0].std(),A[:,1].mean(),A[:,1].std()))
for i,nm in enumerate(['Tmean','RH','wind','lat'],start=2):print('  corr(ratio without temp factor, %s) %+.2f ; with %+.2f'%(nm,np.corrcoef(A[:,1],A[:,i])[0,1],np.corrcoef(A[:,0],A[:,i])[0,1]))
r=A[:,1];print('ratio quantiles (no temp factor): ',np.round(np.quantile(r,[0,.1,.25,.5,.75,.9,1]),2))
for o in sorted(out,key=lambda o:-o[2])[:6]+sorted(out,key=lambda o:o[2])[:4]:print('  %-14s ratio %.2f  Tmean %.1f RH %.0f wind %.1f lat %.1f'%(o[0],o[2],o[3],o[4],o[5],o[6]))
