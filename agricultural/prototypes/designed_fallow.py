"""Designed bare-fallow experiment: engine vs Cycles v1.5.20 on identical synthetic inputs (2026-10-15, REFIT_PLAN row 42).
Constant seasonless weather, factorial soil organic C, clay, temperature and rain, no crop, no fertilizer, 6 years.
Reads Cycles' net mineralization and SOM respiration straight from its daily output (no confounding with weather, crops or stress),
runs the engine's fallow nitrogen window on the same inputs, and reports engine/Cycles ratios by factor. Usage: python3 designed_fallow.py [OUT.json]"""
import sys,os,json,itertools,subprocess,csv,math
import numpy as np
sys.path.insert(0,'.')
import cycles_engine_validate as cev
from cycles_engine_validate import saxton_rawls
import run_validation_multisite as m
CY=m.CY
TH=[float(x) for x in os.environ.get("DF_TH","0.20,0.20,0.30,0.30,0.50,0.50").split(",")];YRS=6;SPIN=2   # realistic STATSGO-like layering (a thin 0.05/0.10/0.15 m top triggered the equal-step evaporation artifact, row 42)
TEMPS=[5,10,15,20,25];RAINS=[0.5,1.5,4.0];SOCS=[0.8,1.6,3.2];CLAYS=[12,28,45]
def soil_raw(soc0,clay):
    out=[];z=0.0
    for t in TH:
        z+=t/2;out.append(dict(thick=t,clay=float(clay),sand=float(max(5,70-clay-10)),soc=max(0.1,soc0*math.exp(-z/0.5))));z+=t/2
    return out
def write(tag,T,rain,soc0,clay):
    s=soil_raw(soc0,clay)
    with open(f"{CY}/input/{tag}.soil","w") as f:
        f.write("CURVE_NUMBER        75\nSLOPE               0\nLAYER   THICK   CLAY    SAND    SOC     BD      FC      PWP     SON     NO3     NH4     ROCK    BYP_H   BYP_V   pH\n#       m       %       %       %       Mg/m3   m3/m3   m3/m3   kg/ha   kg/ha   kg/ha   m3/m3   -       -       -\n")
        for i,l in enumerate(s,1):f.write(f"{i}\t{l['thick']}\t{l['clay']}\t{l['sand']}\t{l['soc']:.4f}\t-999\t-999\t-999\t-999\t5\t1\t0.0\t0.0\t0.00\t6.5\n")
    with open(f"{CY}/input/{tag}.weather","w") as f:
        f.write("LATITUDE                40.000000\nALTITUDE                0.000000\nSCREENING_HEIGHT        10.0\nYEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND\n####    ###     mm      deg C   deg C   MJ/m2   %       %       m/s\n")
        for y in range(2001,2001+YRS):
            for d in range(1,366):f.write(f"{y}\t{d}\t{rain:.4f}\t{T+4:.2f}\t{T-4:.2f}\t14.0\t90.0\t50.0\t2.0\n")
    open(f"{CY}/input/{tag}.operation","w").write("TILLAGE\nYEAR 1\nDOY 1\nTOOL Planter_double_disk_opnr\nCROP_NAME N/A\nFRAC_THERMAL_TIME 0.0\nKILL_EFFICIENCY 0.0\n")
    c=open(f"{CY}/input/ContinuousCorn.ctrl").read().replace("ContinuousCorn.operation",f"{tag}.operation").replace("GenericHagerstown.soil",f"{tag}.soil").replace("RockSprings.weather",f"{tag}.weather").replace("SIMULATION_START_YEAR   1980","SIMULATION_START_YEAR   2001").replace("SIMULATION_END_YEAR     2016",f"SIMULATION_END_YEAR     {2000+YRS}")
    import re;c=re.sub(r"SOIL_LAYERS\s+\d+",f"SOIL_LAYERS             {len(s)}",c)
    open(f"{CY}/input/{tag}.ctrl","w").write(c);return s
def cycles_result(tag):
    subprocess.run(["./Cycles",tag],cwd=CY,capture_output=True)
    d=f"{CY}/output/{tag}";N=list(csv.reader(open(f"{d}/dailyN.csv")));C=list(csv.reader(open(f"{d}/dailySoilC.csv")))
    hn=N[0];ic=hn.index("net_mineralization");id_=hn.index("denitrification");iv=hn.index("volatilization");il=hn.index("NO3_leaching");ino=hn.index("profile_soil_NO3");inh=hn.index("profile_soil_NH4")
    rows=N[2:];yr={}
    for r in rows:
        y=int(r[0][:4]);a=yr.setdefault(y,[0,0,0,0]);a[0]+=float(r[ic]);a[1]+=float(r[id_]);a[2]+=float(r[iv]);a[3]+=float(r[il])
    cr={}
    ir=C[0].index("soil_organic_matter_respired_carbon")
    for r in C[2:]:cr[int(r[0][:4])]=cr.get(int(r[0][:4]),0)+float(r[ir])
    ys=[y for y in sorted(yr) if y>=2001+SPIN]
    return dict(netmin=float(np.mean([yr[y][0] for y in ys])),denit=float(np.mean([yr[y][1] for y in ys])),volat=float(np.mean([yr[y][2] for y in ys])),leach=float(np.mean([yr[y][3] for y in ys])),somresp=float(np.mean([cr[y] for y in ys])),
                no3_end=float(rows[-1][ino]),nh4_end=float(rows[-1][inh]))
def engine_result(s,T,rain):
    layers=[]
    for l in s:
        h=saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC)
        layers.append(dict(thick=l["thick"],fc=h["fc"],pwp=h["pwp"],sat=h["sat"],theta=h["pwp"]+m.INITIAL_MOISTURE_FRACTION*(h["fc"]-h["pwp"]),ksat_mm_day=h["ksat_mm_day"],psi_e_kpa=h["psi_e_kpa"],B=h["B"]))
    state=cev.sixpool_ml_init(layers,s)
    nst=dict(n_nh4=1.0,n_no3=sum([5.0]*len(s)),tsoil_lag=float(T),no3_layers=[5.0]*len(s))
    out=[]
    for y in range(YRS):
        rows=[dict(doy=d,pp=rain,tx=T+4.0,tn=T-4.0,solar=14.0,rhx=90.0,rhn=50.0,wind=2.0) for d in range(1,366)]
        p0=nst["n_nh4"]+sum(nst["no3_layers"]);c0=sum(x["cs"]+x["cm"] for x in state["ml"])
        lea,den,vol=cev.run_fallow_n_window(layers,rows,nst,sixpool_state=state,lat_deg=40.0,de_state=None)
        p1=nst["n_nh4"]+sum(nst["no3_layers"])
        c1=sum(x["cs"]+x["cm"] for x in state["ml"]);out.append((p1-p0+lea+den+vol,den,vol,lea,c0-c1))
    o=np.array(out[SPIN:]).mean(0)
    return dict(netmin=float(o[0]),denit=float(o[1]),volat=float(o[2]),leach=float(o[3]),somresp=float(o[4]))
if __name__=="__main__":
    res=[]
    for T,rain,soc0,clay in itertools.product(TEMPS,RAINS,SOCS,CLAYS):
        tag=f"df_{T}_{int(rain*10)}_{int(soc0*10)}_{clay}"
        s=write(tag,T,rain,soc0,clay)
        try:cy=cycles_result(tag);en=engine_result(s,T,rain)
        except Exception as e:print(tag,'ERR',repr(e)[:200]);continue
        res.append(dict(T=T,rain=rain,soc0=soc0,clay=clay,cy=cy,en=en))
        print(tag,'netmin cy %.1f en %.1f | denit cy %.2f en %.2f | leach cy %.1f en %.1f'%(cy['netmin'],en['netmin'],cy['denit'],en['denit'],cy['leach'],en['leach']),flush=True)
    json.dump(res,open(sys.argv[1] if len(sys.argv)>1 else '/tmp/w/designed_fallow.json','w'))
