import os,sys
os.environ["REGIONAL"]="0"; os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; os.environ["CROPSEL"]="corn"
sys.path.insert(0,'.')
import run_validation_multisite as m, rhizo_engine as E, run_validation as rv
lat,lon=42.0,-93.6
wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
for weps in (False,True):
    E.WEPS_DECAY=weps; rv.CORN['weps_k']=0.01 if weps else None; E.DIAG_CPOOL=[]
    m.engine("x",wx,soil,cl,0,'leadin')
    d={}
    for r in E.DIAG_CPOOL: d.setdefault(r[0],{})[r[1]]=r[5]
    for y in (2005,2006):
        print(weps,y,[(k,round(v,2)) for k,v in sorted(d[y].items())][::25])
