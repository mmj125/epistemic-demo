"""Draw a 100-site development validation set (not locked; used for rule 10 paired tests of fitted changes) (val100). Seeded, no overlap with
fresh94, holdout or original28. Candidate points: 0.5 degree grid inside the
lat/lon box spanned by the used sets, weather tile and STATSGO2 cell within
0.5 degree. Disjoint from holdout2 as well."""
import json, random, sys, os
sys.path.insert(0, os.path.join('.'))
import field_data as fd
S='sitesets/'
used=set()
box=[99,-99,99,-99]
for f in ('fresh94','holdout','original28','holdout2'):
    for v in json.load(open(S+f+'.json')).values():
        used.add((round(v[0],1),round(v[1],1)))
        if f!='original28':
            box=[min(box[0],v[0]),max(box[1],v[0]),min(box[2],v[1]),max(box[3],v[1])]
cand=[]
la=box[0]
while la<=box[1]+1e-9:
    lo=box[2]
    while lo<=box[3]+1e-9:
        p=(round(la,1),round(lo,1))
        if p not in used:
            try:
                w,dw=fd.resolve_field_weather(*p)
                c,ds,_=fd.resolve_field_soil(*p)
                if w is not None and dw<=0.5 and ds<=0.5 and c: cand.append(p)
            except Exception: pass
        lo+=0.5
    la+=0.5
print('box',box,'candidates',len(cand))
random.seed(20261102)
pick=random.sample(cand,100)
out={'v%03d_%d_%d'%(i,round(a*10),round(-b*10)):[a,b] for i,(a,b) in enumerate(sorted(pick))}
json.dump(out,open(S+'val100.json','w'),indent=0)
print(len(out))
