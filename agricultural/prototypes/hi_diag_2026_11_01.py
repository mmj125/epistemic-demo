"""Harvest index diagnostic (2026-11-01): Cycles' harvest.csv harvest_index against the engine's grain / above-ground biomass per site-year, with the implied fraction of growth after flowering
fG = -ln((Hmax - HI) / (Hmax - Hmin)) / Hk, and Cycles' mean water and N stress over days after flowering. CROPSEL soy or sorghum, N 150, 12 sites of the 24-site set."""
import os,sys,csv,json,shutil,subprocess,glob,datetime
CS=os.environ.get("CROPSEL","soy"); os.environ["CROPSEL"]=CS; os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="150"; os.environ.setdefault("REGIONAL","0"); sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
_orig=m.cev.standard_kwargs; m.cev.standard_kwargs=lambda *a,**k: {**_orig(*a,**k),'record_history':True}
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json'))
HX,HN,HK,FLOW,CF,SUF={"soy":(0.40,0.15,3.4,1250,"SoybeanMG.5","soy"),"corn":(0.8,0.15,1.3077,1000,"CornRM.90","")}.get(CS,(0.8,0.15,1.3077,1300,"SorghumMS","sor"))
def job(site):
    N=150; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); nm=f"{site}{SUF}N{N}"
    subprocess.run(["./Cycles",nm],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}/"
    f=glob.glob(d+f"daily{CF}.csv")[0]; D=[r for r in csv.DictReader(l for l in open(f) if not l.startswith('#'))]
    H=[l.strip().split(',') for l in open(d+"harvest.csv") if not l.startswith('#')]; shutil.rmtree(d,ignore_errors=True)
    hdr=H[0]; hi={}
    for r in H[2:]:
        if r and r[0]: dd=dict(zip(hdr,r)); hi[int(dd['date'][:4])]=(float(dd['harvest_index']),float(dd['grain_yield']),float(dd['total_biomass'])-float(dd['root_biomass']))
    st={}; agf={}; cc={}
    for r in D:
        if r['biomass']=='-999' or r['crop']=='FALLOW': continue
        y=int(r['date'][:4]); tt=float(r['thermal_time'])
        if tt>=FLOW:
            st.setdefault(y,[]).append((float(r['water_stress']),float(r['nitrogen_stress'])))
            agf.setdefault(y,float(r['aboveground_biomass'])); cc.setdefault(y,[]).append(float(r['radiation_interception']))
    res=m.engine(site,wx,soil,cl,N,"leadin"); rows=[]
    for y,v in hi.items():
        if y in res and res[y].get("grain") and res[y].get("ag") and y in st and v[0]>0:
            e=res[y]; hie=e["grain"]/e["ag"]; s=np.array(st[y]); hh=e.get("history") or []; MATT={"soy":2250,"sorghum":2050,"corn":1800}[CS]
            ie=next((i for i,x in enumerate(hh) if (x.get("ttf") or 0)>=FLOW/MATT),None)
            agf_e=hh[ie]["ag_mg_ha"] if ie is not None else np.nan
            post=[x for x in hh if (x.get('ttf') or 0)>=FLOW/MATT]; en=np.mean([x.get('n_stress') or 0 for x in post]) if post else np.nan; ew=np.mean([x.get('water_stress') or 0 for x in post]) if post else np.nan; ec=np.mean([x.get('canopy') or 0 for x in post]) if post else np.nan; edays=len(post)
            rows.append((v[0],hie,v[1],e["grain"],v[2],e["ag"],s[:,0].mean(),s[:,1].mean(),agf.get(y,np.nan),agf_e,en,ew,ec,edays,len(s),np.mean(cc[y]) if y in cc else np.nan))
    return rows
if __name__=="__main__":
    with Pool(4) as p: R=p.map(job,sorted(S)[:12])
    A=np.array([r for rs in R for r in rs]); print(CS,"site-years",len(A))
    fg=lambda h: -np.log(np.clip((HX-h)/(HX-HN),1e-6,1))/HK
    print("mean HI Cycles %.3f engine %.3f | implied fG Cycles %.3f engine %.3f | ag biomass Cycles %.2f engine %.2f | grain Cycles %.2f engine %.2f"%(A[:,0].mean(),A[:,1].mean(),fg(A[:,0]).mean(),fg(A[:,1]).mean(),A[:,4].mean(),A[:,5].mean(),A[:,2].mean(),A[:,3].mean()))
    print("above-ground biomass at flowering Cycles %.2f engine %.2f | after flowering Cycles %.2f engine %.2f | flowering share of final: Cycles %.3f engine %.3f"%(np.nanmean(A[:,8]),np.nanmean(A[:,9]),np.nanmean(A[:,4]-A[:,8]),np.nanmean(A[:,5]-A[:,9]),np.nanmean(A[:,8]/A[:,4]),np.nanmean(A[:,9]/A[:,5])))
    print("after flowering: N factor Cycles %.3f engine %.3f | water factor Cycles %.3f engine %.3f | canopy Cycles %.3f engine %.3f | days Cycles %.1f engine %.1f"%(1-A[:,7].mean()/100,np.nanmean(A[:,10]),1-A[:,6].mean()/100,np.nanmean(A[:,11]),np.nanmean(A[:,15]),np.nanmean(A[:,12]),np.nanmean(A[:,14]),np.nanmean(A[:,13])))
    print("corr HI C-E %.3f"%np.corrcoef(A[:,0],A[:,1])[0,1])
    for lo,hi in [(0,0.05),(0.05,0.2),(0.2,0.4),(0.4,1.01)]:
        k=(A[:,6]/100>=lo)&(A[:,6]/100<hi)
        if k.sum()>5: print(f"  Cycles mean water stress after flowering {lo}-{hi}: n {k.sum():4d} HI C {A[k,0].mean():.3f} E {A[k,1].mean():.3f} (diff {A[k,1].mean()-A[k,0].mean():+.3f})")
