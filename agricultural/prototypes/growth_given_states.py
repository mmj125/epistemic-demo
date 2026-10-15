"""Daily growth conversion under forced canopy and water stress (N=400): engine dGB vs Cycles' daily biomass gain, by temperature, solar, VPD proxy, site clay (2026-10-15). Usage: python3 growth_given_states.py"""
import os,sys,csv,json,pickle,datetime,numpy as np
os.environ['LEAD_YEARS']='continuous';sys.path.insert(0,'.')
import run_validation_multisite as m, cycles_engine_validate as E, forcelib
from multiprocessing import Pool
def one(site):
    S=json.load(open('/tmp/w/big240.json'));S.update(json.load(open('/tmp/w/old28.json')));lat,lon=S[site]
    wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    E.FORCE_SERIES=forcelib.force(site,400,['canopy','water','wclock']);E.DIAG_GROWTH=[]
    m.write_inputs(site,lat,lon,wx,soil,cl);m.engine(site,wx,soil,cl,400,'leadin')
    g=E.DIAG_GROWTH;E.DIAG_GROWTH=None
    yrs=sorted(wx);y=yrs[0]-1;last=999;eng={}
    for doy,GR,GT,dGB in g:
        if doy<last:y+=1
        last=doy;eng[(y,doy)]=(GR,GT,dGB*10)
    out=[];prev=None
    for x in csv.DictReader(open(f'/tmp/cycles-run15/output/{site}N400/dailyCornRM.90.csv')):
        if x['date'][0]=='#' or x['crop']=='-' or x['biomass']=='-999':prev=None;continue
        b=float(x['biomass']);d=datetime.date.fromisoformat(x['date']);k=(d.year,d.timetuple().tm_yday)
        if prev is not None and k in eng and k[0] in wx:
            r=wx[d.year][d.timetuple().tm_yday];ei=float(x['radiation_interception'])
            if ei>0.3 and float(x['nitrogen_stress'])<5:
                es=(r['rhx']+r['rhn'])/2;tm=(r['tx']+r['tn'])/2
                es_=0.6108*np.exp(17.27*tm/(tm+237.3));vpd=es_*(1-es/100)
                out.append((tm,r['solar'],vpd,eng[k][2],(b-prev),eng[k][0],eng[k][1],ei,float(x['water_stress']),float(x['potential_transpiration'])))
        prev=b
    return site,np.array(out)
if __name__=="__main__":
    C=pickle.load(open('/tmp/w/covcache.pkl','rb'));S=json.load(open('/tmp/w/big240.json'));sites=list(S)[:80]
    with Pool(4) as p:R=p.map(one,sites)
    R=[r for r in R if len(r[1])];A=np.vstack([r[1] for r in R]);clay=np.concatenate([[C[s][1]]*len(a) for s,a in R])
    # Cycles dB in Mg/ha: column 4 was computed as (b-prev)*100/10*0.1*10 = (b-prev)*10?  recompute: biomass is Mg/ha already
    cy=A[:,4];keep=A[:,9]>0;print('days with Cycles potential TR zero: %.1f%%'%(100*(~keep).mean()))
    A=A[keep];cy=cy[keep];clay=clay[keep]
    print('pooled days',len(A),' engine dGB (Mg/ha/d) mean %.3f  Cycles dB mean %.3f  ratio %.3f'%(A[:,3].mean(),cy.mean(),A[:,3].sum()/cy.sum()))
    pickle.dump((A,clay),open('/tmp/w/growth_given.pkl','wb'))
    for nm,col,edges in (('Tmean',0,range(10,36,3)),('VPD',2,[0,0.5,1,1.5,2,3,4,6]),('solar',1,[5,10,15,20,25,30])):
        print(nm)
        for lo,hi in zip(list(edges)[:-1],list(edges)[1:]):
            mk=(A[:,col]>=lo)&(A[:,col]<hi)
            if mk.sum()>300:print('  %5.1f-%5.1f n=%6d engine/Cycles daily growth %.3f'%(lo,hi,mk.sum(),A[mk,3].sum()/cy[mk].sum()))
    print('clay quintile')
    q=np.quantile(clay,np.linspace(0,1,6))
    for lo,hi in zip(q[:-1],q[1:]):
        mk=(clay>=lo)&(clay<=hi);print('  clay %2.0f-%2.0f n=%6d engine/Cycles %.3f'%(lo,hi,mk.sum(),A[mk,3].sum()/cy[mk].sum()))
