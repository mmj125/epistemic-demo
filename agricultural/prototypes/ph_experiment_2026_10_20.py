"""Designed experiment: how does Cycles' ammonia volatilization respond to soil pH? (2026-10-20) Same site, weather, N (UAN, 150 kg N/ha), only the soil pH column changes.
Prints mean annual volatilization and nitrification, the ratio to pH 6.5, and the ratio of the NH3 share of ammoniacal N, 1/(1+10^(pKa-pH)), pKa = 0.09018 + 2729.92/(T+273.15) at 15 C."""
import os,sys,json,re,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, field_data as fd
SITES={"Iowa":(42.0,-93.6),"Kansas":(37.97,-100.87),"PA":(40.7093,-77.9478)}
PH=(5.0,5.5,6.0,6.5,7.0,7.5,8.0,8.5)
def share(ph,T=15.0): return 1/(1+10**((0.09018+2729.92/(T+273.15))-ph))
for name,(lat,lon) in SITES.items():
    wx,_=fd.resolve_field_weather(lat,lon); soil,_,_=fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    m.write_inputs("phx_"+name,lat,lon,wx,soil,cl); res={}
    f=f"{m.CY}/input/phx_{name}.soil"; base_txt=open(f).read()
    for ph in PH:
        open(f,"w").write(re.sub(r"(\t)6\.5\n",r"\g<1>%s\n"%ph,base_txt))
        subprocess.run(["./Cycles",f"phx_{name}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/phx_{name}N150/"
        rows=[l.strip().split(",") for l in open(d+"annualN.csv").readlines()[2:] if l.strip()]
        res[ph]=(np.mean([float(r[10]) for r in rows if int(r[0])>=1982]),np.mean([float(r[9]) for r in rows if int(r[0])>=1982]),np.mean([float(r[11]) for r in rows if int(r[0])>=1982]))
        shutil.rmtree(d,ignore_errors=True)
    b=res[6.5]
    print(name,"| pH: volatilization kg N/ha/yr, ratio to pH 6.5 | NH3 share ratio | nitrification | N2O")
    for ph in PH: print(f"  pH {ph}: {res[ph][0]:6.2f}  x{res[ph][0]/b[0]:5.2f} | share x{share(ph)/share(6.5):5.2f} | nitrif {res[ph][1]:6.1f} | N2O {res[ph][2]:.2f}")
