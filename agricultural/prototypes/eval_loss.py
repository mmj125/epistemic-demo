"""Held-out N-loss comparison (site-mean rms log error, geometric bias) for two run tags, excluding training sites. Usage: EXCL=train.json python3 eval_loss.py BASE CAND"""
import sys,os,json,glob,numpy as np
def load(tag):
    D={}
    for f in glob.glob(f'/tmp/w/{tag}_*_[0-9].json'):D.update(json.load(open(f)))
    return D
ex=set(json.load(open(os.environ['EXCL']))) if os.environ.get('EXCL') else set()
for tag in sys.argv[1:]:
    D=load(tag);print(tag)
    for N in (0,150,400):
        row=[]
        for k in ('leach','denit','volat','n2o'):
            r=[(v['res'][k]['real'],v['res'][k]['model']) for key,v in D.items() if key.endswith(f'|N{N}|leadin') and key.split('|')[0] not in ex and v['res'][k]['real']>0.3]
            a=np.array(r);lr=np.log(np.maximum(a[:,1],0.05)/a[:,0]);row.append('%s rms %.2f geo %.2f'%(k,np.sqrt((lr**2).mean()),np.exp(np.median(lr))))
        print('  N',N,' | '.join(row))
