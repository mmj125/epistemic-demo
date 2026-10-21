"""Daily Cycles states for the denitrification law under management (2026-10-21): per site and treatment (base, irrig, till, manure) the daily denitrification, layer 1 and 2 nitrate, moisture,
thickness, saturation (pedotransfer on the site soil, static), and respired carbon (soil organic matter + residue). Output /tmp/w/dm_<treat>.npz, columns documented in COLS."""
import os,sys,json,csv,shutil,subprocess
os.environ.setdefault("REGIONAL","0"); os.environ["LEAD_YEARS"]="continuous"; sys.path.insert(0,'/home/user/epistemic-demo/agricultural/prototypes')
import numpy as np, mgmt_response_2026_10_21 as G, run_validation_multisite as m
from multiprocessing import Pool
COLS="site yeardoy denit no3_1 no3_2 th_1 th_2 thick_1 thick_2 sat_1 sat_2 fc_1 fc_2 pwp_1 pwp_2 resp_som resp_res pp infil".split()
def rd(p): return [r for r in csv.DictReader(open(p)) if not r['date'].startswith('#')]
def one(args):
    si,site,treats=args
    lat,lon=G.S[site]; wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon); m.REG_LON=lon
    nm=site+"dm"; m.write_inputs(nm,lat,lon,wx,soil,cl)
    z=0
    for i,l in enumerate(soil):
        z+=l["thick"]
        if z>=1.0: break
    G.LL[0]=i+1
    sr=[m.saxton_rawls(l["sand"],l["clay"],l["soc"]*m.OM_FROM_SOC) for l in soil[:2]]
    if len(sr)<2: sr=sr*2
    out={}
    for t in treats:
        N=0 if t=="manure" else 150
        p=f"{m.CY}/input/{nm}N{N}.operation"; txt=open(p).read()
        if t!="base": open(p,"w").write(G.variant(t,txt))
        subprocess.run(["./Cycles",f"{nm}N{N}"],cwd=m.CY,capture_output=True); d=f"{m.CY}/output/{nm}N{N}/"
        D=rd(d+"dailyN.csv"); L=rd(d+"dailySoilLayersCN.csv"); W=rd(d+"dailyWater.csv"); C=rd(d+"dailySoilC.csv"); E=rd(d+"dailyEnviron.csv")
        rows=[]
        for a,b,c,e,f in zip(D,L,W,C,E):
            y=int(a['date'][:4]); doy=int(a['date'][5:7])*0+0
            rows.append([si,y*1000+int(__import__('datetime').date.fromisoformat(a['date']).timetuple().tm_yday),float(a['denitrification']),float(b['NO3.1']),float(b.get('NO3.2',0)),float(c['soil_moisture_content.1']),float(c.get('soil_moisture_content.2',0)),float(b['thickness.1']),float(b.get('thickness.2',1)),sr[0]['sat'],sr[1]['sat'],sr[0]['fc'],sr[1]['fc'],sr[0]['pwp'],sr[1]['pwp'],float(e['soil_organic_matter_respired_carbon']),float(e['residue_respired_carbon']),float(f['precipitation']),float(c['infiltration'])])
        shutil.rmtree(d,ignore_errors=True); open(p,"w").write(txt); out[t]=rows
    return out
if __name__=="__main__":
    treats=sys.argv[1].split(","); sites=sorted(G.S)
    R=Pool(4).map(one,[(i,s,treats) for i,s in enumerate(sites)])
    for t in treats:
        A=np.array([r for o in R for r in o[t]]); np.savez(f"/tmp/w/dm_{t}.npz",A=A,cols=COLS); print(t,A.shape)
