"""Identify Cycles' daily N demand law for corn from its own columns (2026-10-17). Unstressed days only (N stress multiplier >= 0.99, N=150 and 400, 12 sites, day pairs with positive growth).
d(total N), d(aboveground N), d(root N) against d(total biomass), d(aboveground biomass), d(root biomass): marginal concentrations versus aboveground and total biomass, power-law fits and
candidate demand laws (crop file a=5.5%, b=0.4): fit exponent b and prefactor, R2 in log space. Usage: python3 corn_ndemand_law_2026_10_17.py"""
import os,sys,json,csv,shutil,subprocess,numpy as np
os.environ["N_LEVELS"]="150,400"; sys.path.insert(0,'.')
import run_validation_multisite as m
S=json.load(open("/tmp/w/s24.json")); ks=sorted(S)[:12]; CY=m.CY; R=[]
for site in ks:
    lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs(site,lat,lon,wx,soil,cl)
    for N in (150,400):
        subprocess.run(["./Cycles",f"{site}N{N}"],cwd=CY,capture_output=True); d=f"{CY}/output/{site}N{N}/"; prev=None
        for x in csv.DictReader(open(d+"dailyCornRM.90.csv")):
            if x["date"][0]=="#" or x["biomass"]=="-999": prev=None; continue
            v=dict(B=float(x["biomass"]),A=float(x["aboveground_biomass"]),Rt=float(x["root_biomass"]),Nt=float(x["total_nitrogen"]),Na=float(x["aboveground_nitrogen"]),Nr=float(x["root_nitrogen"]),ns=1-float(x["nitrogen_stress"])/100,fix=float(x["nitrogen_fixation"]))
            if prev is not None and v["ns"]>=0.99 and prev["ns"]>=0.99: R.append((N,prev["B"],prev["A"],v["B"]-prev["B"],v["A"]-prev["A"],v["Rt"]-prev["Rt"],v["Nt"]-prev["Nt"],v["Na"]-prev["Na"],v["Nr"]-prev["Nr"],prev["Nt"],prev["Na"]))
            prev=v
        shutil.rmtree(d,ignore_errors=True)
A=np.array(R); print("unstressed day pairs",len(A))
Wt,Wa,dB,dA,dR,dNt,dNa,dNr=A[:,1],A[:,2],A[:,3],A[:,4],A[:,5],A[:,6],A[:,7],A[:,8]
def pf(x,y,name,mask):
    x,y=x[mask],y[mask]; b,a=np.polyfit(np.log(x),np.log(y),1); r=np.log(y)-(a+b*np.log(x)); print(f"  {name}: conc = {np.exp(a):.2f} * W^{b:.3f}  R2 {1-r.var()/np.log(y).var():.3f} n={len(x)}")
mk=(dA>1e-4)&(dNa>1e-3)&(Wa>0.3); print("aboveground marginal N concentration (%) of new aboveground growth, vs aboveground biomass:"); pf(Wa,dNa/dA/10,"AG marginal vs W_ag",mk)
mk2=(dB>1e-4)&(dNt>1e-3)&(Wt>0.3); print("total marginal (%) of new total growth vs total biomass:"); pf(Wt,dNt/dB/10,"total marginal vs W_tot",mk2)
print("   same vs aboveground biomass:"); pf(Wa,dNt/dB/10,"total marginal vs W_ag",mk2&(Wa>0.3))
mk3=(dR>1e-4)&(dNr>1e-4)&(Wt>0.3)
if mk3.sum()>50: print("root marginal N conc (%):",np.median(dNr[mk3]/dR[mk3]/10).round(3))
print("crop file (engine): total marginal = 5.5*0.6 W^-0.4 = 3.3 W^-0.4 at W_tot; engine scale 0.8746 -> 2.89")
for lo,hi in [(0.3,1),(1,3),(3,8),(8,16),(16,40)]:
    s=mk2&(Wt>=lo)&(Wt<hi)
    if s.sum()>30: print(f"  W_tot {lo}-{hi}: Cycles marginal total conc {np.median(dNt[s]/dB[s]/10):.2f}%  engine marginal {5.5*0.6*np.median(Wt[s])**-0.4*0.8746:.2f}%  (n={s.sum()})")
