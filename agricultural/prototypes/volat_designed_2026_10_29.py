"""Designed Cycles runs (2026-10-29): response of ammonia volatilization to soil pH (soil file) and to the fertilizer rate. Cycles only, 3 sites, N=150 operation, first 3 years of daily volatilization after the application."""
import re,subprocess,shutil,csv,glob,os,numpy as np
CY="/tmp/cycles-run15"
sites=sorted(os.path.basename(p)[:-len("N150.ctrl")] for p in glob.glob(CY+"/input/f00[0-5]_*N150.ctrl") if re.fullmatch(r"f\d+_\d+_\d+N150\.ctrl",os.path.basename(p)))[:3]
def run(site,ph,mass_scale=1.0):
    nm=f"{site}N150v"; soil=open(f"{CY}/input/{site}.soil").read().split("\n"); out=[]
    for l in soil:
        p=l.split("\t")
        if len(p)>=15 and re.match(r"\d+$",p[0]): p[14]=str(ph)
        out.append("\t".join(p))
    open(f"{CY}/input/{nm}.soil","w").write("\n".join(out))
    op=open(f"{CY}/input/{site}N150.operation").read()
    op=re.sub(r"(?m)^MASS\s+(\S+)",lambda m:f"MASS                                {float(m.group(1))*mass_scale}",op)
    open(f"{CY}/input/{nm}.operation","w").write(op)
    c=open(f"{CY}/input/{site}N150.ctrl").read().replace(f"{site}N150.operation",f"{nm}.operation").replace(f"{site}.soil",f"{nm}.soil"); open(f"{CY}/input/{nm}.ctrl","w").write(c)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    A=[r for r in csv.DictReader(l for l in open(d+"annualN.csv") if not l.startswith('#'))]
    shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","operation","soil"): os.remove(f"{CY}/input/{nm}.{e}")
    return np.array([float(a['volatilization']) for a in A]), np.array([float(a['fertilization']) for a in A])
if __name__=="__main__":
    for ph in (5.5,6.5,7.5,8.5):
        V=np.array([run(s,ph)[0] for s in sites]); print(f"soil pH {ph}: mean annual volatilization {V.mean():.2f} kg N/ha (sites: {', '.join(f'{x:.2f}' for x in V.mean(1))})")
    for sc in (0.5,1.0,2.0):
        V=np.array([run(s,6.5,sc)[0] for s in sites]); F=np.array([run(s,6.5,sc)[1] for s in sites]); print(f"fertilizer x{sc}: volatilization {V.mean():.2f}, fertilizer applied {F.mean():.1f}")

def cross(si,sj):
    """soil of site si with weather of site sj (operation of si)"""
    nm=f"x{si[:4]}{sj[:4]}v"
    c=open(f"{CY}/input/{si}N150.ctrl").read().replace(f"{si}.soil",f"{si}.soil").replace(f"{si}.weather",f"{sj}.weather")
    open(f"{CY}/input/{nm}.ctrl","w").write(c.replace(f"{si}N150.operation",f"{si}N150.operation"))
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    A=[r for r in csv.DictReader(l for l in open(d+"annualN.csv") if not l.startswith('#'))]
    shutil.rmtree(d,ignore_errors=True); os.remove(f"{CY}/input/{nm}.ctrl")
    return np.mean([float(a['volatilization']) for a in A])

def swapcols(base,donor,cols,weather=None):
    """soil of `base` with the given columns (names) replaced by `donor`'s per-layer values; weather of `weather` (default base)."""
    hdr=None
    def parse(site):
        L=[l.split("\t") if "\t" in l else l.split() for l in open(f"{CY}/input/{site}.soil").read().split("\n")]
        return L
    B=parse(base); D=parse(donor); names=None
    for r in B:
        if r and r[0]=="LAYER": names=r
    idx=[names.index(c) for c in cols]
    drows=[r for r in D if r and r[0].isdigit()]; out=[]; k=0
    for r in B:
        if r and r[0].isdigit():
            rr=list(r); dr=drows[min(k,len(drows)-1)]
            for i in idx: rr[i]=dr[i]
            k+=1; out.append("\t".join(rr))
        else: out.append("\t".join(r))
    nm="swapv"; open(f"{CY}/input/{nm}.soil","w").write("\n".join(out))
    c=open(f"{CY}/input/{base}N150.ctrl").read().replace(f"{base}.soil",f"{nm}.soil")
    if weather: c=c.replace(f"{base}.weather",f"{weather}.weather")
    open(f"{CY}/input/{nm}.ctrl","w").write(c)
    subprocess.run(["./Cycles",nm],cwd=CY,capture_output=True); d=f"{CY}/output/{nm}/"
    A=[r for r in csv.DictReader(l for l in open(d+"annualN.csv") if not l.startswith('#'))]
    shutil.rmtree(d,ignore_errors=True)
    for e in ("ctrl","soil"): os.remove(f"{CY}/input/{nm}.{e}")
    return np.mean([float(a['volatilization']) for a in A])
