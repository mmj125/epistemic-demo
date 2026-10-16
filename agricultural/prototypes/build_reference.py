"""Scripted Cycles v1.5.20 reference rebuild (rebuild phase 1, 2026-10-16). Nothing here lives only in /tmp by accident:
 python3 build_reference.py setup                      download the release zip, verify its sha256, unpack to $CY_DIR (default /tmp/cycles-run15)
 python3 build_reference.py run SITESET.json [N,N,..]  write inputs from the committed tiles, run Cycles, cache harvest/annualN, record md5 of every run in reference_manifest.json
 python3 build_reference.py verify                     recompute the md5 of every recorded run and report drift
The manifest (committed) is the provenance: release hash, per-run output hashes. The cache files themselves are regenerable and are not committed."""
import os,sys,json,hashlib,subprocess,zipfile,urllib.request
P=os.path.dirname(os.path.abspath(__file__)); CY=os.environ.get("CY_DIR","/tmp/cycles-run15")
URL="https://github.com/PSUmodeling/Cycles/releases/download/v1.5.20/Cycles_debian_1.5.20.zip"
ZIP_SHA256="8b9289998a3ccd42c27cc7403bbc4b8751a03b193b5d0f39f0181c6010c63a81"
MAN=os.path.join(P,"reference_manifest.json")
def sha(path,algo="sha256"):
    h=hashlib.new(algo)
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def setup():
    os.makedirs(CY,exist_ok=True); z=os.path.join(CY,"Cycles_debian_1.5.20.zip")
    if not os.path.exists(z): urllib.request.urlretrieve(URL,z)
    got=sha(z)
    if got!=ZIP_SHA256: sys.exit(f"zip hash mismatch: {got}")
    zipfile.ZipFile(z).extractall(CY); os.chmod(os.path.join(CY,"Cycles"),0o755); print("Cycles v1.5.20 ready in",CY)
def run(setfile,Ns):
    os.environ["CY_DIR"]=CY; os.environ["N_LEVELS"]=",".join(map(str,Ns)); sys.path.insert(0,P)
    import run_validation_multisite as m
    S=json.load(open(setfile)); man=json.load(open(MAN)) if os.path.exists(MAN) else dict(release="v1.5.20",zip_sha256=ZIP_SHA256,binary_sha256=sha(os.path.join(CY,"Cycles")),runs={})
    for site,(lat,lon) in S.items():
        wx,_=m.fd.resolve_field_weather(lat,lon); soil,_,_=m.fd.resolve_field_soil(lat,lon); cl=m.lat_of(lat,lon)
        m.write_inputs(site,lat,lon,wx,soil,cl)
        for N in Ns:
            m.run_cycles(site,N)
            h=os.path.join(CY,"output",f"{site}N{N}","harvest.csv")
            if os.path.exists(h): man["runs"][f"{site}N{N}"]=sha(h,"md5")
            else: man["runs"][f"{site}N{N}"]=sha(os.path.join(CY,f"cache15_{site}N{N}.json"),"md5")   # output dir was cleaned; hash the parsed cache instead
    json.dump(man,open(MAN,"w"),indent=0,sort_keys=True); print(len(man["runs"]),"runs recorded")
def verify():
    man=json.load(open(MAN)); bad=0
    for k,v in man["runs"].items():
        h=os.path.join(CY,"output",k,"harvest.csv"); c=os.path.join(CY,f"cache15_{k}.json")
        p=h if os.path.exists(h) else c
        if not os.path.exists(p) or sha(p,"md5")!=v: bad+=1; print("DRIFT or missing:",k)
    print("verified",len(man["runs"])-bad,"of",len(man["runs"]))
if __name__=="__main__":
    a=sys.argv[1:]
    {"setup":setup,"verify":verify}.get(a[0],lambda:run(a[1],[int(x) for x in (a[2] if len(a)>2 else "0,150,400").split(",")]))()
