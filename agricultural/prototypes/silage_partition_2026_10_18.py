"""Silage corn partition audit (2026-10-18): from Cycles' own output, forage_yield against aboveground and total biomass at harvest (CornSilageRM.90, harvest at 85 percent of maturity)."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]="150"; os.environ["CROPSEL"]="silage"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('sitesets/fresh94.json'))
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl); subprocess.run(["./Cycles",f"{site}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{site}N150/"
    Hh=list(csv.reader(open(d+"harvest.csv"))); hh=Hh[0]; D=[r for r in csv.DictReader(open(d+"dailyCornSilageRM.90.csv")) if r['date'][0]!='#']; shutil.rmtree(d,ignore_errors=True)
    ix={k:hh.index(k) for k in ('total_biomass','root_biomass','forage_yield','aboveground_residue','grain_yield')}
    last={}
    for r in D:
        if r['aboveground_biomass'] not in ('-999',) and r['stage'] in ('VEGETATIVE_GROWTH','REPRODUCTIVE_GROWTH','MATURITY'): last[r['date'][:4]]=r
    out=[]
    for r in Hh[2:]:
        if not r or r[0][0]=='#': continue
        y=r[0][:4]
        if y not in last: continue
        f=float(r[ix['forage_yield']]); t=float(r[ix['total_biomass']]); rt=float(r[ix['root_biomass']]); res=float(r[ix['aboveground_residue']]); ab=float(last[y]['aboveground_biomass'])
        if f>0.5: out.append((f,t,rt,res,ab))
    return out
if __name__=="__main__":
    ks=sorted(S)[::7][:14]
    with Pool(4) as p: R=p.map(one,ks)
    A=np.array([x for r in R for x in r]); print('seasons',len(A))
    f,t,rt,res,ab=A.T
    print('forage / total biomass          mean %.3f sd %.3f'%((f/t).mean(),(f/t).std()))
    print('root / total biomass            mean %.3f'%((rt/t).mean()))
    print('aboveground (daily, last day) / total  mean %.3f'%((ab/t).mean()))
    print('forage / aboveground (daily)    mean %.3f sd %.3f'%((f/ab).mean(),(f/ab).std()))
    print('forage + residue left / aboveground  mean %.3f'%(((f+res)/ab).mean()))
    print('mean Mg/ha: forage %.2f total %.2f root %.2f residue left %.2f'%(f.mean(),t.mean(),rt.mean(),res.mean()))
