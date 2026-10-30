"""Designed Cycles runs (2026-10-29): peak radiation interception of continuous corn against MAXIMUM_SOIL_COVERAGE and DENSITY, to identify the canopy plateau structure. Cycles only."""
import re,subprocess,shutil,csv,glob,os,numpy as np
CY="/tmp/cycles-run15"
sites=sorted(os.path.basename(p)[:-len("N150.ctrl")] for p in glob.glob(CY+"/input/f00[0-5]_*N150.ctrl") if re.fullmatch(r"f\d+_\d+_\d+N150\.ctrl",os.path.basename(p)))[:4]
def run(site,msc,dens,suf=""):
    nm=f"{site}{suf}N150t"; op=open(f"{CY}/input/{site}{suf}N150.operation").read()
    op=re.sub(r"(?m)^MAXIMUM_SOIL_COVERAGE\s+\S+",f"MAXIMUM_SOIL_COVERAGE               {msc}",op); op=re.sub(r"(?m)^DENSITY\s+\S+",f"DENSITY                             {dens}",op)
    open(f"{CY}/input/{nm}.operation","w").write(op)
    c=open(f"{CY}/input/{site}{suf}N150.ctrl").read().replace(f"{site}{suf}N150.operation",f"{nm}.operation"); open(f"{CY}/input/{nm}.ctrl","w").write(c)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"; f=[x for x in glob.glob(d+"daily*.csv") if not any(t in x for t in ("Environ","N.csv","Water","Residue","Soil","SOM"))][0]; pk=[]; yr={}
    for r in csv.DictReader(l for l in open(f) if not l.startswith('#')):
        if r['radiation_interception'] in ('-999',''): continue
        y=r['date'][:4]; yr[y]=max(yr.get(y,0),float(r['radiation_interception']))
    shutil.rmtree(d,ignore_errors=True)
    for p in (f"{CY}/input/{nm}.ctrl",f"{CY}/input/{nm}.operation"): os.remove(p)
    v=np.array(list(yr.values())); return np.percentile(v,[50,90,100])
if __name__=="__main__":
    import sys
    for suf in ("","sil","sor","soy"):
        for msc in (100,90):
            A=np.array([run(s,msc,1.0,suf) for s in sites]); print(f"{suf or 'corn':5s} MSC {msc}: peak interception max across years {A[:,2].mean():.3f}, ratio to MSC {A[:,2].mean()/(msc/100):.3f}")
