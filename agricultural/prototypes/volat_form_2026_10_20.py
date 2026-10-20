"""Form of Cycles' daily volatilization against weather and layer-1 NH4 state (2026-10-20), 24 sites, corn N=0/150/400. Needs /tmp/w/ndata.npz (ndata_2026_10_19.py)."""
import os,sys,json
os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from scipy.optimize import least_squares
A=np.load('/tmp/w/ndata.npz')['A']; S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
cols={k:np.zeros(len(A)) for k in ("wind","tx","tn","rhx","rhn","solar","pp")}
for si,site in enumerate(SITES):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon)
    idx=np.where(A[:,9]==si)[0]
    for i in idx:
        w=wx[int(A[i,10])][int(A[i,8])]
        for k in cols: cols[k][i]=w[k]
np.savez('/tmp/w/ndata_wx.npz',**cols)
print("joined",len(A))
