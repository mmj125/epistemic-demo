"""Noise floor of the reference (REFIT_PLAN row 48). Runs native Cycles on perturbed copies of the same site inputs and compares to the unperturbed run,
using the scorecard error metric (per-site MAE over years). Perturbations: wx_nb (weather from the neighboring 0.5 degree cell), soil_nb (soil from the
neighboring cell), soil_pm (clay, sand, SOC scaled by a random +-10%). Usage: python3 noise_floor.py NSITES SHARD NSHARD OUT.json"""
import os,sys,json,random,statistics,copy
os.environ["N_LEVELS"]="0,150";os.environ.setdefault("BIGSET","/tmp/w/big240.json")
sys.path.insert(0,'.')
import run_validation_multisite as m
fd=m.fd
NS,SH,NSH,OUT=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
ALL={k:tuple(v) for k,v in json.load(open("/tmp/w/big240.json")).items()}
random.seed(5);sites=sorted(random.sample(sorted(ALL),NS))[SH::NSH]
OFF=[(0.5,0),(-0.5,0),(0,0.5),(0,-0.5)]
res={}
def run(tag,lat,lon,wx,soil,cl):
    out={}
    m.N_LEVELS=[0,150]
    m.write_inputs(tag,lat,lon,wx,soil,cl)
    for N in (0,150):
        m.NO_CACHE=True
        H,A=m._run_cycles_uncached(tag,N);out[N]={y:H[y]["grain"] for y in H}
    return out
for s in sites:
    lat,lon=ALL[s];rng=random.Random(hash(s)%10**6)
    wx,_=fd.resolve_field_weather(lat,lon);soil,_,_=fd.resolve_field_soil(lat,lon);cl=m.lat_of(lat,lon)
    base=run("nf0_"+s,lat,lon,wx,soil,cl)
    dl,dn=rng.choice(OFF)
    try:
        wx2,_=fd.resolve_field_weather(lat+dl,lon+dn);cl2=m.lat_of(lat+dl,lon+dn)
        p1=run("nf1_"+s,lat+dl,lon+dn,wx2,soil,cl2)
    except Exception as e: p1=None
    dl,dn=rng.choice(OFF)
    try:
        soil2,_,_=fd.resolve_field_soil(lat+dl,lon+dn);p2=run("nf2_"+s,lat,lon,wx,soil2,cl)
    except Exception as e: p2=None
    soil3=copy.deepcopy(soil);f=1+rng.uniform(-.1,.1);g=1+rng.uniform(-.1,.1);h=1+rng.uniform(-.1,.1)
    for l in soil3:
        l['clay']=min(95,l['clay']*f);l['sand']=min(95,l['sand']*g);l['soc']=(l['soc'] or 0.2)*h
    p3=run("nf3_"+s,lat,lon,wx,soil3,cl)
    res[s]=dict(base=base,wx_nb=p1,soil_nb=p2,soil_pm=p3)
    print(s,flush=True)
    json.dump(res,open(OUT,"w"))
