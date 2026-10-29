"""Controlled N closure test (2026-10-29): a spun-up soil state run through one bare-fallow year with no inputs and no plant. Closure requires change in (mineral + organic N) = minus (leached + denitrified + volatilized). Residual is N created or destroyed by the bookkeeping. 24 sites."""
import os,sys,json,copy
os.environ["CROPSEL"]="corn"; os.environ["REGIONAL"]="0"; os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
S=json.load(open('/tmp/w/s24.json'))
for _o in os.environ.get('OVR','').split(';'):
    if _o: _k,_v=_o.split('=',1); setattr(E,_k,eval(_v))
def org_n(st):
    n=sum(x["cm"]/E.SIXPOOL_CN_CM+x["cs"]/E.SIXPOOL_CN_CS+x["crtz"]/E.SIXPOOL_CN_CRTZ+x.get("crm",0)/E.SIXPOOL_CN_CRM for x in st["ml"])
    return (n+st["cra"]/st.get("cra_cn",E.SIXPOOL_CN_CRA))*1000.0
def _mn(ns):
    nl=ns.get('no3_layers'); return float(ns['n_nh4'])+(float(sum(nl)) if nl else float(ns['n_no3']))
out=[]
for site in sorted(S)[:int(os.environ.get("NS","12"))]:
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    r=m.engine(site,wx,soil,cl,150,'leadin'); ys=sorted(r)
    for y in ys[5:35:6]:
        v=r[y]; lay=copy.deepcopy(v["final_layers"]); ns=copy.deepcopy(v["final_n_state"]); sp=copy.deepcopy(v["sixpool_final_state"])
        _w=wx.get(y+1) or wx.get(y); nrows=[_w[d] for d in sorted(_w)]
        n0=1
        n0=org_n(sp)+_mn(ns) if not isinstance(ns["n_nh4"],(list,tuple)) else None
        if n0 is None: continue
        if os.environ.get('PRIME'): E.run_fallow_n_window(lay,nrows[0:1],ns,sixpool_state=sp)
        for k in range(0,len(nrows)-29,30):
            na=org_n(sp)+_mn(ns); mn0=_mn(ns)
            L,D,V=E.run_fallow_n_window(lay,nrows[k:k+30],ns,sixpool_state=sp)
            n1=org_n(sp)+_mn(ns)
            out.append((site,y,n1-na,L,D,V,k//30,mn0))
A=np.array([[o[2],o[3],o[4],o[5],o[6]] for o in out]); d,L,D,V,n0=A.T; mn=np.array([o[7] for o in out])
for mo in range(12):
    q=n0==mo; r_=d[q]+L[q]+D[q]+V[q]; print(f"window {mo}: mean mineral N at start {mn[q].mean():6.1f}  residual {r_.mean():+7.2f}  max {np.abs(r_).max():6.1f}")
n0=np.ones_like(n0)
res=d+(L+D+V)
q0=[(o[0],o[1],round(o[2]+o[3]+o[4]+o[5],1)) for o in out if o[6]==0]
q0.sort(key=lambda t:-abs(t[2])); print('window0 largest',q0[:8]); print('window0 median',float(np.median([t[2] for t in q0])), 'n>5:',sum(abs(t[2])>5 for t in q0),'of',len(q0))
print(f"{len(A)} fallow years: mean N stock {n0.mean():.0f} kg/ha; dN {d.mean():+.2f}, leached {L.mean():.2f}, denitrified {D.mean():.2f}, volatilized {V.mean():.2f}")
print(f"closure residual (dN + losses): mean {res.mean():+.3f}, sd {res.std():.3f}, max abs {np.abs(res).max():.3f} kg N/ha")
