"""Carbon pool states per layer, engine (free) vs Cycles (2026-10-19): corn N=0, 24 sites, continuous chain. Mean over 1982 on of soil organic C, microbial C, root residue C per layer and the surface residue C; ratio engine/Cycles, and the change over the record (first year to last year)."""
import os,sys,json,csv,shutil,subprocess,datetime
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, rhizo_engine as E
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N0"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N0/"
    L={r['date']:r for r in rd(d+"dailySoilLayersCN.csv")}; shutil.rmtree(d,ignore_errors=True)
    nl=len([k for k in next(iter(L.values())) if k.startswith('microbial_carbon.')])
    E.DIAG_CPOOL=[]; m.engine(site,wx,soil,cl,0,'leadin'); D=E.DIAG_CPOOL; E.DIAG_CPOOL=None; last={}
    for y,doy,cs,cm,cr,cra in D:
        if y is not None and doy is not None and y>=1981: last[(y,doy)]=(cs,cm,cr,cra)
    rows=[]
    for (y,doy),(cs,cm,cr,cra) in last.items():
        dt=(datetime.date(y,1,1)+datetime.timedelta(days=doy-1)).isoformat()
        if dt in L and doy%10==0:
            l=L[dt]
            for i in range(min(nl,len(cs))): rows.append((y,i,cs[i],float(l[f'soil_organic_carbon.{i+1}']),cm[i],float(l[f'microbial_carbon.{i+1}']),cr[i],float(l[f'residue_carbon.{i+1}']),cra,float(l['standing_residue_carbon'])+float(l['flat_residue_carbon'])))
    return rows
if __name__=="__main__":
    A=np.array(sum(Pool(4).map(one,sorted(S)),[])); np.save('/tmp/w/cpool_state.npy',A); print(len(A),'layer samples')
    print('layer | Cs engine/Cycles | Cm engine/Cycles | root residue engine/Cycles   (means over 1982 on, Mg C/ha: Cs, Cm, Cr Cycles)')
    for i in range(4):
        k=A[:,1]==i; print(f'  {i+1}: {A[k,2].mean()/A[k,3].mean():.3f} | {A[k,4].mean()/A[k,5].mean():.2f} | {A[k,6].mean()/max(A[k,7].mean(),1e-9):.2f}   ({A[k,3].mean():.1f}, {A[k,5].mean():.3f}, {A[k,7].mean():.3f})')
    k=A[:,1]==0; print('surface residue C engine %.3f Cycles %.3f'%(A[k,8].mean(),A[k,9].mean()))
    print('Cs total all layers engine/Cycles by year (first, mid, last):')
    for y in (1982,1995,2010):
        kk=A[:,0]==y
        if kk.sum()>0: print(f'   {y}: {A[kk,2].sum()/A[kk,3].sum():.4f}')
