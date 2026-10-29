"""Designed Cycles runs (2026-10-29): how does Cycles' soybean above-ground N respond to N_MAX_CONCENTRATION and N_DILUTION_SLOPE? Cycles only, 6 sites."""
import re,subprocess,shutil,csv,glob,os,numpy as np
CY="/tmp/cycles-run15"
sites=sorted(os.path.basename(p)[:-len("soyN150.ctrl")] for p in glob.glob(CY+"/input/*soyN150.ctrl"))[:6]
crop=open(f"{CY}/input/GenericCrops.crop").read(); i=crop.index("SoybeanMG.5"); j=crop.find("\nNAME",i+10); j=j if j>0 else len(crop)
def run(site,nmax,slope,tag):
    b=crop[i:j]; b=re.sub(r"(?m)^N_MAX_CONCENTRATION\s+\S+",f"N_MAX_CONCENTRATION                         {nmax}",b); b=re.sub(r"(?m)^N_DILUTION_SLOPE\s+\S+",f"N_DILUTION_SLOPE                            {slope}",b)
    open(f"{CY}/input/X{tag}.crop","w").write(crop[:i]+b+crop[j:])
    c=open(f"{CY}/input/{site}soyN150.ctrl").read().replace("GenericCrops.crop",f"X{tag}.crop"); nm=f"{site}soyN150{tag}"; open(f"{CY}/input/{nm}.ctrl","w").write(c)
    for ext in (".operation",): shutil.copy(f"{CY}/input/{site}soyN150{ext}",f"{CY}/input/{nm}{ext}")
    c=open(f"{CY}/input/{nm}.ctrl").read().replace(f"{site}soyN150.operation",f"{nm}.operation"); open(f"{CY}/input/{nm}.ctrl","w").write(c)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"; out=[]
    for r in csv.DictReader(l for l in open(d+"harvest.csv") if not l.startswith('#')):
        out.append((float(r['total_biomass'])-float(r['root_biomass']),float(r['total_nitrogen'])-float(r['root_nitrogen']),float(r['grain_nitrogen']),float(r['nitrogen_fixation'])))
    shutil.rmtree(d,ignore_errors=True)
    for p in (f"{CY}/input/{nm}.ctrl",f"{CY}/input/{nm}.operation",f"{CY}/input/X{tag}.crop"): os.remove(p)
    return np.array(out)
for nmax,slope in ((0.07,0.4),(0.035,0.4),(0.07,0.2),(0.07,0.6)):
    A=np.vstack([run(s,nmax,slope,"t") for s in sites]); B,N,G,F=A.T
    print(f"nmax {nmax} slope {slope}: n {len(A)} mean biomass {B.mean():.2f} agN {N.mean():.1f} grainN {G.mean():.1f} fix {F.mean():.1f}; agN/(1000*nmax*B^(1-slope)) = {np.mean(N/(1000*nmax*B**(1-slope))):.3f} (sd {np.std(N/(1000*nmax*B**(1-slope))):.3f})")
