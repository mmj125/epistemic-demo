"""Scorecard metrics for the engine run with 0, 2 lead-in years versus the continuous chain (2026-10-14). Usage: python3 leadin_modes.py"""
import os,sys,subprocess,json
HERE=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,HERE)
import scorecard as S
def run(lead):
    procs=[];tmp={}
    for name,held in (("tuning","0"),("heldout","1")):
        out=f"/tmp/lead_{lead}_{name}.json";tmp[name]=out
        env=dict(os.environ,LEAD_YEARS=str(lead),OUT_JSON=out,N_LEVELS="0,150,400",ROOT_C="1")
        if held=="1":env["HELDOUT"]="1"
        procs.append(subprocess.Popen([sys.executable,os.path.join(HERE,"run_validation_multisite.py")],env=env,cwd=HERE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    for p in procs:p.wait()
    return {k:S.metrics(v) for k,v in tmp.items()}
R={l:run(l) for l in ("0","2")}
base=json.load(open(os.path.join(HERE,"scorecard_baseline.json")))
print('mode             | N=0 MAE tun/held | N=150 MAE tun/held | N=150 corr tun/held | N=150 bias tun/held | leach rms150 | denit rms150')
def line(n,m):
    print('%-16s | %.2f / %.2f      | %.2f / %.2f        | %.2f / %.2f         | %+.2f / %+.2f       | %.2f / %.2f | %.2f / %.2f'%(n,m['tuning']['mae0'],m['heldout']['mae0'],m['tuning']['mae150'],m['heldout']['mae150'],m['tuning']['corr150'],m['heldout']['corr150'],m['tuning']['bias150'],m['heldout']['bias150'],m['tuning']['leach_rms150'],m['heldout']['leach_rms150'],m['tuning']['denit_rms150'],m['heldout']['denit_rms150']))
line('continuous',base);line('2 lead-in years',R['2']);line('0 (fresh season)',R['0'])
json.dump(R,open('/tmp/w/leadin_modes.json','w'))
