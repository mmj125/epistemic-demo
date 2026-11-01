"""Configuration audit (2026-11-01). Run from prototypes/ next to check_parity_2026_10_19.py.
1. Each crop's engine_api dictionary against the Cycles crop file (phenology, efficiencies, transpiration, partitioning, harvest index): any mismatch is printed.
2. Keys the sorghum configuration inherits from the corn dictionary without overriding them (found 2026-11-01: `gj_seed_root` was inherited unnoticed).
3. Planting windows: crop key `plant_window` against the DOY and END_DOY of the Cycles operation files for each crop.
Needs /tmp/cycles-run15 (crop file and operation files)."""
import re,sys,glob
sys.path.insert(0,'.')
import engine_api as api
CF="/tmp/cycles-run15/input/GenericCrops.crop"; cf=open(CF).read()
def block(name):
    i=cf.index(name+"\n"); j=cf.find("\nNAME",i+10); d={}
    for l in cf[i:j if j>0 else None].split("\n"):
        m=re.match(r"([A-Z_0-9]+)\s+(\S+)",l)
        if m:
            try: d[m.group(1)]=float(m.group(2))
            except ValueError: pass
    return d
MAP={"base_t":"BASE_TEMPERATURE_FOR_DEVELOPMENT","opt_t":"OPTIMUM_TEMPERATURE_FOR_DEVELOPMENT","max_t":"MAX_TEMPERATURE_FOR_DEVELOPMENT","tt_emergence":"THERMAL_TIME_TO_EMERGENCE","flowering_tt":"FLOWERING_TT","tt_maturity":"MATURITY_TT","rue":"RADIATION_USE_EFFICIENCY","wue":"TRANSPIRATION_USE_EFFICIENCY","kc":"KC","tr_min_t":"MIN_TEMPERATURE_FOR_TRANSPIRATION","tr_threshold_t":"THRESHOLD_TEMPERATURE_FOR_TRANSPIRATION","lwp_stress_onset":"LWP_STRESS_ONSET","lwp_wilting_point":"LWP_WILTING_POINT","tr_max_mm_day":"TRANSPIRATION_MAX","root_max_m":"MAXIMUM_ROOTING_DEPTH","hi_x":"MAXIMUM_HARVEST_INDEX","hi_o":"MINIMUM_HARVEST_INDEX","fsti":"INITIAL_PARTITIONING_TO_SHOOT","fstf":"FINAL_PARTITIONING_TO_SHOOT"}
CROPS={"corn":("CornRM.90",dict(api._CORN),""),"silage":("CornSilageRM.90",dict(api._SILAGE),"sil"),"sorghum":("SorghumMS",{**api._CORN,**api._SORGHUM_OVER},"sor"),"soybean":("SoybeanMG.5",dict(api._SOYBEAN_N),"soy"),"wheat":("WinterWheat",dict(api._WHEAT),None)}
for k,(nm,d,suf) in CROPS.items():
    cb=block(nm); bad=[]
    for ek,ck in MAP.items():
        if ek in d and ck in cb and abs(float(d[ek])-cb[ck])>1e-9: bad.append(f"{ek}={d[ek]} (crop file {cb[ck]})")
        if ek not in d and ck in cb: bad.append(f"{ek} missing (crop file {cb[ck]})")
    pw=d.get("plant_window",(110,131))
    op=None
    if suf is not None:
        try:
            t=open(f"/tmp/cycles-run15/input/f001_450_1020{suf}N0.operation").read(); a=re.search(r"(?m)^DOY\s+(\d+)",t); b=re.search(r"(?m)^END_DOY\s+(\d+)",t); op=(int(a.group(1)),int(b.group(1)))
        except OSError: pass
    print(f"{k:8s} crop-file mismatches: {bad if bad else 'none'} | plant window engine {tuple(pw)} operation file {op}{'' if op is None or tuple(pw)==op else '  <-- MISMATCH'}")
print("note: the wheat base_t 0 in the dictionary is dead: the wheat chain runs on WINTER_PHENOLOGY base_t 2.0 (a base_t=2 override changed no result on 30 sites, 2026-11-01).")
print("sorghum keys inherited from corn without override:",sorted(x for x in api._CORN if x not in api._SORGHUM_OVER))
