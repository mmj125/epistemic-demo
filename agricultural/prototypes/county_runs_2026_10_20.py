"""Engine annual yields for the 94 fresh sites, through engine_api, for the county-yield comparison (2026-10-20).
Corn N=150, silage N=150, soybean, winter wheat N=150 (fall 60 + spring). Saves /tmp/w/engine_county_runs.json {site: {crop: {year: yield}}}."""
import sys,json,os
sys.path.insert(0,'.')
from multiprocessing import Pool
import field_data as fd
F=["pp","tx","tn","solar","rhx","rhn","wind"]
S=json.load(open('sitesets/fresh94.json'))
def one(site):
    import engine_api as api
    lat,lon=S[site]; wx,_=fd.resolve_field_weather(lat,lon); soil,_,_=fd.resolve_field_soil(lat,lon)
    import os
    import cycles_engine_validate as E
    for _o in os.environ.get('OVR','').split(';'):
        if _o:
            _k,_v=_o.split('=',1)
            if _k.startswith('CROP.'): api._CORN[_k[5:]]=eval(_v)
            else: setattr(E,_k,eval(_v))
    am=float(os.environ.get('AWC_MULT','1'))
    if am!=1.0:
        _orig=E.saxton_rawls
        def _sr(sand,clay,om,*a,**k):
            h=dict(_orig(sand,clay,om,*a,**k)); h['fc']=h['pwp']+am*(h['fc']-h['pwp']); return h
        E.saxton_rawls=_sr
    if os.environ.get('SOILSET')=='ssurgo':
        sd=json.load(open('sitesets/fresh94_ssurgo_soil.json'))
        if site not in sd: return site,{}
        soil=[{k:v for k,v in l.items() if k!='ph'} for l in sd[site]]
    deep=float(os.environ.get('DEEP','0'))
    if deep:
        tot=sum(l['thick'] for l in soil)
        if tot<deep: soil=[dict(l) for l in soil]; soil[-1]['thick']+=deep-tot
    api.load_site(json.dumps(dict(lat=lat,weather=dict(fields=F,years={str(y):{str(d):[r[k] for k in F] for d,r in days.items()} for y,days in wx.items()}),soil=soil)))
    out={}
    for crop,n in ((("corn",150),) if os.environ.get("CORNONLY") else (("corn",150),("silage",150),("soybean",0),("wheat",150))):
        try:
            r=json.loads(api.run(json.dumps(dict(crop=crop,start_year=1980,end_year=2016,n_rate=n,n_timing="planting"))))
            out[crop]={a["year"]:a["grain"] for a in r["annual"]}
        except Exception as e: out[crop]={"error":str(e)[:80]}
    return site,out
if __name__=="__main__":
    with Pool(4) as p: R=dict(p.map(one,sorted(S)))
    json.dump(R,open(os.environ.get('OUTRUN','/tmp/w/engine_county_runs.json'),'w')); print("sites",len(R),"errors",sum(1 for v in R.values() for c in v.values() if 'error' in c))
