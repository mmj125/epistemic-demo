import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; os.environ["N_LEVELS"]="0,150"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import run_validation_multisite as m
S=json.load(open('/tmp/w/s24.json')); site=sorted(S)[9]  # f021 (index 9? check)
site=[s for s in sorted(S) if s.startswith('f021')][0]
exec(open('/tmp/w/cover_ref.py').read().split("def rd")[0].split("S=json")[0])
KILL=("TILLAGE\nYEAR                                1\nDOY                                 105\nTOOL                                Kill_Crop\nCROP_NAME                           WinterRye\nFRAC_THERMAL_TIME                   0.0\nKILL_EFFICIENCY                     0.0\n\n")
src=open('/tmp/w/cover_ref.py').read(); RYE=src.split('RYE=(')[1].split('\ndef rd')[0].rsplit(')',1)[0]; RYE=eval('('+RYE+')')
def rd(p): return [r for r in csv.DictReader(open(p)) if r['date'][0]!='#']
lat,lon=S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
nm=site+"cv"; m.write_inputs(nm,lat,lon,wx,soil,cl)
for N in (0,150):
    p=f"{m.CY}/input/{nm}N{N}.operation"; t=open(p).read(); a=t.index("PLANTING"); t=t[:a]+KILL+t[a:]+RYE; open(p,"w").write(t)
    subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N{N}/"
    ry=[f for f in os.listdir(d) if 'Rye' in f][0]; R=rd(d+ry)
    print("N",N,"site",site)
    for yr in ("1990","1991","1995"):
        rows=[r for r in R if r['date'].startswith(yr) and r['aboveground_biomass']!='-999']
        pick=[r for r in rows if r['date'][5:] in ('01-01','03-01','04-01','04-14')]
        print(" ",yr,[ (r['date'][5:],r['stage'],round(float(r['aboveground_biomass']),2),round(float(r['radiation_interception']),2),r['nitrogen_stress'],r['water_stress'],round(float(r['thermal_time']))) for r in pick])
    # planting date of rye in preceding fall
    fall=[r for r in R if r['date'].startswith("1989-1") and r['aboveground_biomass']!='-999']
    print("  fall 1989 first rye day",fall[0]['date'] if fall else None, "corn harvest dates:", [l.split(',')[0][:10] for l in open(d+'harvest.csv').readlines()[2:5]])
    shutil.rmtree(d,ignore_errors=True)
