"""N conservation audit (2026-10-29): per year of a continuous run, change in soil N (mineral + organic pools, living plant excluded) against inputs minus losses minus plant uptake plus N returned to residue pools. A nonzero residual is N created or destroyed by the bookkeeping. Usage: python3 balance_audit_2026_10_29.py CROP N"""
import os,sys,json
CROP=sys.argv[1] if len(sys.argv)>1 else "corn"; NR=int(sys.argv[2]) if len(sys.argv)>2 else 150
os.environ["CROPSEL"]=CROP; os.environ["REGIONAL"]="0"; os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
S=json.load(open('/tmp/w/s24.json'))
def org_n(st):
    ml=st["ml"]
    n=sum(x["cm"]/E.SIXPOOL_CN_CM+x["cs"]/E.SIXPOOL_CN_CS+x["crtz"]/E.SIXPOOL_CN_CRTZ+x.get("crm",0)/E.SIXPOOL_CN_CRM for x in ml)
    n+=st["cra"]/st.get("cra_cn",E.SIXPOOL_CN_CRA)
    return n*1000.0
def min_n(v):
    ns=v["final_n_state"]; return float(ns["n_nh4"])+float(ns["n_no3"])
rows=[]
for site in sorted(S)[:int(os.environ.get("NS","6"))]:
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    r=m.engine(site,wx,soil,cl,NR,'leadin'); prev=None
    for y in sorted(r):
        v=r[y]
        if v.get("sixpool_final_state") is None: continue
        s1=org_n(v["sixpool_final_state"])+min_n(v)
        if prev is not None:
            loss=(v.get("n_leached_kg_ha",0)+v.get("fallow_n_leached",0)+v.get("n_denitrified_kg_ha",0)+v.get("fallow_n_denitrified",0)+v.get("n_volatilized_pool_kg_ha",0)+v.get("fallow_n_volatilized",0))
            fert=NR; up=v.get("n_uptake_kg_ha",0)+v.get("n_rhizo_kg_ha",0)
            rows.append((site,y,s1-prev,fert,loss,up,v.get("n_plant_kg_ha",0)))
        prev=s1
A=np.array([[r[2],r[3],r[4],r[5],r[6]] for r in rows]); d,f,l,u,pl=A.T
print(f"{CROP} N={NR}: {len(A)} site-years. mean dN_soil {d.mean():+.1f}, fert {f.mean():.1f}, losses {l.mean():.1f}, uptake {u.mean():.1f}, plant N {pl.mean():.1f}")
res=d-(f-l-u)
print(f"residual before returns (dN - (F - L - U)) mean {res.mean():+.1f} sd {res.std():.1f}  (should equal N returned in residues and roots)")
