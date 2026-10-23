"""Scoping for step 5 (2026-10-23): Cycles' own corn-soybean rotation against continuous corn at 24 sites, N=0 and 150 on corn, none on soybean. Bounds what a soybean N model and rotation support would have to reproduce:
corn yield after soybean vs continuous corn, soybean yield, nitrogen fluxes by crop phase. Cycles only; nothing from the engine."""
import os,sys,json,re,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); CY=m.CY
def rd(p): return [l.strip().split(",") for l in open(p).read().splitlines() if l and l[0]!='#']
def one(a):
    site,N=a; lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.N_LEVELS=[N]; m.write_inputs(site+"rot",lat,lon,wx,soil,cl)
    nm=f"{site}rot"; op=open(f"{CY}/input/{nm}N{N}.operation").read()
    corn=op; soy=re.sub(r"(?m)^YEAR\s+\S+","YEAR                                2",op.replace("CornRM.90","SoybeanMG.5"))
    soy=soy[soy.index("PLANTING"):]; a=soy.find("FIXED_FERTILIZATION"); soy=soy[:a].rstrip()+"\n" if a>=0 else soy
    soy=re.sub(r"(?m)^DOY\s+110","DOY                                 125",soy); soy=re.sub(r"(?m)^END_DOY\s+131","END_DOY                             146",soy)
    open(f"{CY}/input/{nm}N{N}.operation","w").write(corn.rstrip()+"\n\n"+soy)
    c=open(f"{CY}/input/{nm}N{N}.ctrl").read(); c=re.sub(r"ROTATION_SIZE\s+\d+","ROTATION_SIZE           2",c); open(f"{CY}/input/{nm}N{N}.ctrl","w").write(c)
    r=subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=CY,capture_output=True,text=True); d=f"{CY}/output/{nm}N{N}/"
    try:
        H=rd(d+"harvest.csv")[2:]; A=rd(d+"annualN.csv"); hdr=A[0]; A=A[2:]
    except Exception as e:
        return site,N,None,str(e)+r.stdout[-200:]
    shutil.rmtree(d,ignore_errors=True)
    hy={int(p[0][:4]):(p[2],float(p[5])) for p in H if len(p)>5}
    ay={int(p[0]):dict(zip(hdr,p)) for p in A if len(p)>5}
    return site,N,(hy,ay,hdr),""
if __name__=="__main__":
    R=Pool(4).map(one,[(s,N) for s in sorted(S) for N in (0,150)])
    bad=[r for r in R if r[2] is None]; print("failures",len(bad), bad[:1])
    hdr=next(r[2][2] for r in R if r[2]); print("annualN columns:",hdr)
    out={}
    for N in (0,150):
        cy=[];sy=[];lc=[];ls=[];fx=[];up_s=[];up_c=[]
        for s,n,res,_ in R:
            if n!=N or res is None: continue
            hy,ay,_h=res
            for y,(crop,g) in hy.items():
                if y<1982: continue
                if "Corn" in crop: cy.append(g)
                elif "Soy" in crop: sy.append(g)
                a=ay.get(y)
                if a:
                    lk=float(a.get("N_leached",0) or 0)+float(a.get("N_leached_(NO3+NH4)",0) or 0)
        print(f"N={N}: corn after soy mean {np.mean(cy):.2f} Mg/ha (n={len(cy)}), soybean mean {np.mean(sy):.2f} (n={len(sy)})")
    json.dump({f"{s}|{n}":(res[0],res[1]) for s,n,res,_ in R if res},open('/tmp/w/rot_cycles.json','w'))
