"""Cycles reference for corn + cereal rye cover crop (2026-10-21): rye (WinterRye) planted DOY 288 after corn, killed by Kill_Crop tillage at DOY 105, corn planted from DOY 110.
Compares with the same site's corn-alone Cycles run: rye biomass and N at kill, corn yield, leaching."""
import os,sys,json,csv,shutil,subprocess,re
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, run_validation_multisite as m
from multiprocessing import Pool
S=json.load(open('/tmp/w/s24.json')); SITES=sorted(S)
KILL=("TILLAGE\nYEAR                                1\nDOY                                 105\nTOOL                                Kill_Crop\nCROP_NAME                           WinterRye\nFRAC_THERMAL_TIME                   0.0\nKILL_EFFICIENCY                     0.0\n\n")
RYE=("\nPLANTING\nYEAR                                1\nDOY                                 288\nEND_DOY                             -999\nCROP                                WinterRye\nMAX_SMC                             -999\nMIN_SMC                             -999\nMAX_SOIL_TEMP                       -999\nMIN_SOIL_TEMP                       -999\nUSE_AUTO_IRR                        0\nUSE_AUTO_FERT                       0\nDENSITY                             1.0\nCLIPPING_START                      1\nCLIPPING_END                        366\nMAXIMUM_SOIL_COVERAGE               100\nSTANDING_RESIDUE_AT_HARVEST         50\nRESIDUE_REMOVED                     0\nCLIPPING_BIOMASS_THRESHOLD_LOWER    0.5\nCLIPPING_BIOMASS_THRESHOLD_UPPER    999\nCLIPPING_BIOMASS_DESTINY            RETURN\nHARVEST_TIMING                      -999\nKILL_AFTER_HARVEST                  1\n")
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
def one(site):
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"cv"; m.write_inputs(nm,lat,lon,wx,soil,cl); out={}
    for N in (0,150):
        p=f"{m.CY}/input/{nm}N{N}.operation"; t=open(p).read(); a=t.index("PLANTING"); t=t[:a]+KILL+t[a:]+RYE; open(p,"w").write(t)
        subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N{N}/"
        files=os.listdir(d)
        ry=[f for f in files if 'Rye' in f]; rye={}
        if ry:
            for r in rd(d+ry[0]):
                if r['date'][5:]=='04-14' and r['aboveground_biomass']!='-999': rye[int(r['date'][:4])]=(float(r['aboveground_biomass']),float(r['root_biomass']),float(r['aboveground_nitrogen']))
        H={}
        for line in open(d+"harvest.csv").readlines()[2:]:
            q=line.strip().split(",")
            if len(q)>=11 and 'Corn' in q[1]: H[int(q[0][:4])]=float(q[5])
        A={}
        for line in open(d+"annualN.csv").readlines()[2:]:
            q=line.strip().split(",")
            if len(q)>=12: A[int(q[0])]=float(q[4])+float(q[5])
        shutil.rmtree(d,ignore_errors=True)
        base,_=m.run_cycles(site,N)    # corn alone (cached)
        _,Abase=m.run_cycles(site,N)
        out[N]=dict(rye=rye,H=H,A=A,Hb={y:v['grain'] for y,v in base.items()},Ab={y:v['leach'] for y,v in Abase.items()},files=ry)
    return site,out
if __name__=="__main__":
    R=Pool(4).map(one,SITES)
    for N in (0,150):
        ys=lambda o:[y for y in sorted(set(o['H'])&set(o['Hb'])) if y>=1983]
        rb=[];rr=[];rn=[];dy=[];dl=[];yb=[];lb=[]
        for site,o in R:
            o=o[N]; 
            if not o['rye']: print("no rye file",site,o['files']); continue
            for y in ys(o):
                if y in o['rye']: rb.append(o['rye'][y][0]); rr.append(o['rye'][y][1]); rn.append(o['rye'][y][2]); dy.append(o['H'][y]-o['Hb'][y]); dl.append(o['A'][y]-o['Ab'][y]); yb.append(o['Hb'][y]); lb.append(o['Ab'][y])
        print(f"N={N}: rye above-ground at kill {np.mean(rb):.2f} Mg/ha (sd {np.std(rb):.2f}), roots {np.mean(rr):.2f}, N in shoots {np.mean(rn):.1f} kg/ha | corn yield change {np.mean(dy):+.2f} Mg/ha ({100*np.mean(dy)/np.mean(yb):+.1f}%), leaching change {np.mean(dl):+.1f} kg N/ha ({100*np.mean(dl)/max(np.mean(lb),1e-9):+.0f}%) n={len(rb)}")
    json.dump({s:{str(N):{k:v for k,v in o[N].items() if k!='files'} for N in o} for s,o in R},open('/tmp/w/cover_ref.json','w'))
