"""Designed experiment: which weather and soil inputs does Cycles' volatilization respond to? (2026-10-20) Kansas site, UAN 150 kg N/ha, one input perturbed at a time."""
import os,sys,json,re,shutil,subprocess,copy
os.environ.setdefault("REGIONAL","0"); os.environ["N_LEVELS"]="150"; sys.path.insert(0,'.')
import numpy as np, run_validation_multisite as m, field_data as fd
lat,lon=37.97,-100.87
wx0,_=fd.resolve_field_weather(lat,lon); soil0,_,_=fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
def run(tag,wmod=None,smod=None):
    wx=copy.deepcopy(wx0); soil=copy.deepcopy(soil0)
    if wmod:
        for y in wx:
            for d in wx[y]: wmod(wx[y][d])
    if smod:
        for l in soil: smod(l)
    m.write_inputs("vd_"+tag,lat,lon,wx,soil,cl)
    subprocess.run(["./Cycles",f"vd_{tag}N150"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/vd_{tag}N150/"
    rows=[l.strip().split(",") for l in open(d+"annualN.csv").readlines()[2:] if l.strip()]
    v=np.mean([float(r[10]) for r in rows if int(r[0])>=1982]); n=np.mean([float(r[9]) for r in rows if int(r[0])>=1982]); shutil.rmtree(d,ignore_errors=True)
    print(f"{tag:22s} volatilization {v:7.2f} kg N/ha/yr   nitrification {n:7.1f}")
run("base")
run("wind_x0",lambda r:r.__setitem__("wind",0.0))
run("wind_x2",lambda r:r.__setitem__("wind",r["wind"]*2))
run("rh_plus10",lambda r:(r.__setitem__("rhx",min(100,r["rhx"]+10)),r.__setitem__("rhn",min(100,r["rhn"]+10))))
run("solar_x1.3",lambda r:r.__setitem__("solar",r["solar"]*1.3))
run("temp_plus3",lambda r:(r.__setitem__("tx",r["tx"]+3),r.__setitem__("tn",r["tn"]+3)))
run("precip_x0.7",lambda r:r.__setitem__("pp",r["pp"]*0.7))
run("clay_x2",smod=lambda l:l.__setitem__("clay",min(60,l["clay"]*2)))
run("soc_x2",smod=lambda l:l.__setitem__("soc",l["soc"]*2))
