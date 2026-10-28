"""Mass balance for dated N applications (2026-10-28): every dose either lands or is reported as unapplied through engine_api. Usage: python3 test_dated_n_mass_balance_2026_10_28.py"""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import run_validation_multisite as m, engine_api as api, field_data as fd
lat,lon=42.0,-93.6
wx,_=fd.resolve_field_weather(lat,lon); soil,_,_=fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
api.load_site(json.dumps(dict(lat=cl,weather=dict(fields=["pp","tx","tn","solar","rhx","rhn","wind"],years={str(y):{str(d):[r[k] for k in ("pp","tx","tn","solar","rhx","rhn","wind")] for d,r in days.items()} for y,days in wx.items()}),soil=soil)))
bad=0
def un(crop,d1,f1,d2):
    cfg=dict(crop=crop,start_year=2000,end_year=2003,n_rate=150,n_timing="split",n_doy1=d1,n_frac1=f1,n_doy2=d2,fert_source="uan")
    R=json.loads(api.run(json.dumps(cfg)))
    return [round(r["n_unapplied"] or 0,1) for r in R["annual"]], R["notes"]
# (crop, doy1, share1 %, doy2, expected unapplied per year as a kg amount at the retained share is checked as zero / positive)
for crop,d1,f1,d2,expect_zero in (("corn",110,50,160,True),("corn",125,50,170,True),("corn",110,50,330,False),("corn",20,50,160,False),
                                   ("wheat",289,60,75,True),("wheat",289,60,200,False)):
    u,notes=un(crop,d1,f1,d2); ok=(max(u)<=0.5)==expect_zero and (expect_zero or any("not applied" in n for n in notes))
    print(("ok  " if ok else "FAIL"),crop,d1,f1,d2,"unapplied",u); bad+=not ok
print("FAILURES",bad)
