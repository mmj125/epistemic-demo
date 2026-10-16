"""Draw a reproducible random set of new CONUS reference sites for the scaled-up validation (2026-10-15).
Usage: python3 bigset.py N SEED OUT.json   (sites are 0.5-degree weather-tile cells, rainfed corn region, soil in STATSGO2 coverage, not within 0.75 degrees of any existing site)"""
import sys,json,math,random
import field_data as fd
import run_validation_multisite as m
def draw(n,seed,exclude=(),mind=0.75):
    man=fd.load_manifest();cells=[tuple(c) for t in man['tiles'].values() for c in t['cells']]
    cells=[c for c in cells if 30.0<=c[0]<=48.5 and -103.0<=c[1]<=-70.0]
    old=list(m.SITES.values())+list(m.HELDOUT_SITES.values())+list(exclude)
    rng=random.Random(seed);rng.shuffle(cells);out={};
    for c in cells:
        if len(out)>=n:break
        if any(math.hypot(c[0]-a,c[1]-b)<mind for a,b in old+list(out.values())):continue
        try:soil,dist,name=fd.resolve_field_soil(c[0],c[1])
        except Exception:continue
        if dist>0.5 or not soil:continue
        out['b%03d_%d_%d'%(len(out),round(c[0]*10),round(-c[1]*10))]=(c[0],c[1])
    return out
if __name__=="__main__":
    n,seed,path=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
    import os
    ex=[tuple(v) for f in os.environ.get('EXCLUDE','').split(',') if f for v in json.load(open(f)).values()]
    s=draw(n,seed,ex,float(os.environ.get('MINDIST','0.75')));json.dump(s,open(path,'w'),indent=0);print(len(s),'sites ->',path);print(list(s.items())[:5])
