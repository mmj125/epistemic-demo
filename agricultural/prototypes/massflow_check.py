"""Does Cycles' daily plant N uptake follow mass flow (transpiration x soil nitrate concentration)? (2026-10-15). Usage: python3 massflow_check.py"""
import csv,glob,os,numpy as np
R=[]
for d in sorted(glob.glob('/tmp/cycles-run15/output/*N*')):
    s=os.path.basename(d)
    if not s.endswith(('N0','N150','N400')) or s.startswith(('h2h','iowaX')):continue
    W={x['date']:x for x in csv.DictReader(open(d+'/dailyWater.csv')) if x['date'][0]!='#'}
    L={x['date']:x for x in csv.DictReader(open(d+'/dailySoilLayersCN.csv')) if x['date'][0]!='#'}
    prev=None
    for x in csv.DictReader(open(d+'/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['crop']=='-' or x['biomass']=='-999':continue
        tn=float(x['total_nitrogen']);dt=x['date']
        if prev is not None and dt in W and dt in L:
            l=L[dt];w=W[dt];nl=sum(1 for k in l if k.startswith('thickness.'))
            no3=0;wat=0;nh4=0
            for i in range(1,nl+1):
                th=float(l['thickness.%d'%i]);bd=float(l['bulk_density.%d'%i]) if 'bulk_density.%d'%i in l else 1.4
                no3+=float(l['NO3.%d'%i])*bd*th*10;nh4+=float(l['NH4.%d'%i])*bd*th*10
                wat+=float(w['soil_moisture_content.%d'%i])*th*1000
            tr=float(w['transpiration'])
            if wat>0 and tr>0.1:R.append((s,tn-prev,tr*no3/wat,no3,nh4,float(x['nitrogen_stress'])/100,float(x['aboveground_biomass'])))
        prev=tn
A=np.array([r[1:] for r in R]);print('days',len(A))
up,mf,no3,nh4,st,ag=A.T
ok=(up>0)
for nm,m in (('stressed (>0.15)',st>0.15),('mild (0.02-0.15)',(st>0.02)&(st<=0.15)),('unstressed',st<=0.02)):
    m=m&ok
    print('%-18s n=%6d  uptake/massflow median %.2f  p25 %.2f p75 %.2f   uptake median %.2f kg/d, massflow median %.2f'%(nm,m.sum(),np.median(up[m]/mf[m]),np.percentile(up[m]/mf[m],25),np.percentile(up[m]/mf[m],75),np.median(up[m]),np.median(mf[m])))
# fraction of days uptake exceeds massflow
print('uptake > massflow on %.0f%% of stressed days, %.0f%% of unstressed days'%(100*np.mean(up[ok&(st>0.15)]>mf[ok&(st>0.15)]),100*np.mean(up[ok&(st<=0.02)]>mf[ok&(st<=0.02)])))
pool=no3+nh4
print('\nuptake as fraction of whole-profile mineral N (NO3+NH4), by stress class')
for nm,m in (('stressed (>0.15)',st>0.15),('mild',(st>0.02)&(st<=0.15)),('unstressed',st<=0.02)):
    m=m&ok&(pool>0.05);f=up[m]/pool[m]
    print('%-18s n=%6d median %.3f p25 %.3f p75 %.3f   median pool %.1f kg/ha'%(nm,m.sum(),np.median(f),np.percentile(f,25),np.percentile(f,75),np.median(pool[m])))
for lo,hi in ((0,2),(2,5),(5,10),(10,20),(20,50),(50,500)):
    m=ok&(pool>=lo)&(pool<hi)&(ag>1);f=up[m]/pool[m]
    print('pool %3d-%3d kg/ha: n=%6d fraction/day median %.3f  uptake median %.2f  stress mean %.2f'%(lo,hi,m.sum(),np.median(f),np.median(up[m]),st[m].mean()))
