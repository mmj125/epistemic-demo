"""Summarize a scaled-up site run (bigset runs): per-site MAE/corr/bias by N, response, losses (2026-10-15). Usage: python3 bigmetrics.py TAG"""
import sys,json,glob,math,statistics as st
tag=sys.argv[1];d={}
for f in sorted(glob.glob(f'/tmp/w/{tag}_[0-9]*.json')):d.update(json.load(open(f)))
sites=sorted(set(k.split('|')[0] for k in d));print('sites',len(sites))
g=lambda s,N,m:d.get(f'{s}|N{N}|leadin',{}).get('res',{}).get(m)
for N in (0,150,400):
    r=[g(s,N,'grain') for s in sites if g(s,N,'grain')]
    c=[x['corr'] for x in r if x['corr']==x['corr']]
    print('N=%3d  MAE %.3f  corr %.3f  bias %+.3f  mean Cycles yield %.2f  rel MAE %.1f%%'%(N,st.mean(x['mae'] for x in r),st.mean(c),st.mean(x['model']-x['real'] for x in r),st.mean(x['real'] for x in r),100*st.mean(x['mae']/max(x['real'],0.3) for x in r)))
for a,b in ((0,150),(150,400)):
    p=[((g(s,b,'grain')['model']-g(s,a,'grain')['model']),(g(s,b,'grain')['real']-g(s,a,'grain')['real'])) for s in sites if g(s,a,'grain') and g(s,b,'grain')]
    sc=100/(b-a);print('response %d-%d per 100 kg: engine %.2f Cycles %.2f  site corr %.2f'%(a,b,sc*st.mean(x for x,_ in p),sc*st.mean(y for _,y in p),st.correlation([x for x,_ in p],[y for _,y in p])))
for m in ('leach','denit','volat','n2o'):
    l=[math.log((g(s,150,m)['model']+.1)/(g(s,150,m)['real']+.1)) for s in sites if g(s,150,m)]
    print('%s N=150 rms log error %.2f'%(m,math.sqrt(st.mean(x*x for x in l))))
rows=sorted(((g(s,150,'grain')['model']-g(s,150,'grain')['real'],s,g(s,150,'grain')['real']) for s in sites if g(s,150,'grain')))
print('worst +',[(s,round(b,2),round(r,1)) for b,s,r in rows[-4:]]);print('worst -',[(s,round(b,2),round(r,1)) for b,s,r in rows[:4]])
