import sys,os,csv,numpy as np,datetime
sys.path.insert(0,'.');os.environ["LEAD_YEARS"]="continuous"
import rhizo_engine as E, run_validation_multisite as m
E.ROOT_C_REALIZED_GROWTH=True
for a in os.environ.get('OVR','').split(';'):
    if a: setattr(E,a.split('=')[0],eval(a.split('=',1)[1]))
site=sys.argv[1];N=int(sys.argv[2]);years=[int(x) for x in sys.argv[3:]]
allsites=dict(m.SITES);allsites.update(m.HELDOUT_SITES);lat,lon=allsites[site]
wx,_=m.fd.resolve_field_weather(lat,lon);soil,_,_=m.fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
orig=m.simulate_continuous
def sc(*a,**k):
    k['record_history']=True;return orig(*a,**k)
m.simulate_continuous=sc
res=m.engine(site,wx,soil,cl,N,'leadin')
d=f'/tmp/cycles-run15/output/{site}N{N}'
C={r['date']:r for r in csv.DictReader(open(d+'/dailyCornRM.90.csv')) if r['date'][0]!='#'}
Nn={r['date']:r for r in csv.DictReader(open(d+'/dailyN.csv')) if r['date'][0]!='#'}
for y in years:
    h=res[y]['history']
    print('== %s %d N%d'%(site,y,N))
    print(' doy | mineralN E  C | plantN E  C | Nstress E  C | AGB E  C')
    for x in h[::10]:
        dt=(datetime.date(y,1,1)+datetime.timedelta(x['doy']-1)).isoformat()
        c=C.get(dt);n=Nn.get(dt)
        if not c or c['biomass']=='-999': continue
        me=(x['n_no3'] or 0)+(x['n_nh4'] or 0)
        print(' %3d | %6.1f %6.1f | %5.1f %5.1f | %4.2f %4.2f | %5.1f %5.1f'%(x['doy'],me,float(n['profile_soil_NO3'])+float(n['profile_soil_NH4']),x['n_plant'],float(c['total_nitrogen']),1-x['n_stress'],float(c['nitrogen_stress'])/100,x['ag_mg_ha'],float(c['aboveground_biomass'])))
