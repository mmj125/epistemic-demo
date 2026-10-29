"""Engine residue cover against Cycles' radiation_interception by residue (2026-10-26), 10 sites, continuous no-till corn N=150: rms, bias and May to August bias, for the engine's current cover law and the split law (RES_SPLIT).
Usage: ENGINE_OVR="RES_SPLIT=True" python3 residue_cover_check_2026_10_26.py"""
import os,sys,json,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
R=json.load(open('/tmp/w/respos.json')); F=json.load(open('sitesets/fresh94.json')); err=[]; mo=[]; ce=[]; cc=[]
for site,o in R.items():
    lat,lon=F[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    E.DIAG_FALLOW_WATER=[]; E.DIAG_EVAP=[]; E._DIAG_YEAR=None; m.engine(site,wx,soil,cl,150,'leadin'); eng={}
    for t in E.DIAG_FALLOW_WATER: 
        if t[0] is not None: eng[(t[0],t[1])]=t[9]
    for t in E.DIAG_EVAP:
        if t[0] is not None: eng[(t[0],t[1])]=t[5]
    E.DIAG_FALLOW_WATER=None; E.DIAG_EVAP=None
    for d,c in zip(o['date'],o['cov']):
        dt=datetime.date.fromisoformat(d); k=(dt.year,dt.timetuple().tm_yday)
        if dt.year>=1983 and k in eng: err.append(eng[k]-c); mo.append(dt.month); ce.append(eng[k]); cc.append(c)
e=np.array(err); mo=np.array(mo)
print(f"n {len(e)}  rms {np.sqrt((e**2).mean()):.3f}  bias {e.mean():+.3f}  May-Aug bias {e[(mo>=5)&(mo<=8)].mean():+.3f}  Oct-Mar bias {e[(mo>=10)|(mo<=3)].mean():+.3f}")

ce=np.array(ce); cc=np.array(cc)
print("month: Cycles cover, engine cover, rms")
for q in range(1,13):
    k=mo==q; print(f" {q:2d} {cc[k].mean():.3f} {ce[k].mean():.3f} rms {np.sqrt((e[k]**2).mean()):.3f}")
