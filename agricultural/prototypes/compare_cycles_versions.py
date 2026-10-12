"""Cycles v1.4.4 vs v1.5.x on IDENTICAL inputs at the 16 multi-site locations (continuous corn, N=0 and N=150).
Tile weather and STATSGO2 soil come from field_data.py, exactly as in run_validation_multisite.py. The v1.4.4
reference is that harness's cache (/tmp/cycles-run/cache_*.json). v1.5 needs its own input format:
SIMULATION_START_YEAR/SOIL_LAYERS/HYDROLOGY_OPTION in the ctrl, ROCK and pH columns in the soil file, a restructured
operation file with the fertilizer named from its catalog (UAN 32-00-00, so MASS is product kg/ha = N / 0.32).
Needs a v1.5 release directory (binary + input/) at CY15 and /tmp/cycles-run for the 1.4.4 cache. Neither is committed
(Cycles is CC BY-NC-ND). Writes cycles_version_compare.json."""
import os, sys, json, math, statistics, subprocess, datetime, re
P = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, P)
import field_data as fd
import run_validation_multisite as ms
CY15 = os.environ.get("CY15", "/tmp/claude-0/work/c15/r")
CY14 = ms.CY
ROCK, PH = 0.0, 6.5   # v1.5-only soil inputs: no rock, near-neutral pH (v1.4.4 has neither)

def write15(site, wx, soil_raw, cell_lat, N):
    w = open(f"{CY15}/input/{site}.weather", "w")
    w.write(f"LATITUDE                {cell_lat:.6f}\nALTITUDE                0.000000\nSCREENING_HEIGHT        10.0\n")
    w.write("YEAR    DOY     PP      TX      TN      SOLAR   RHX     RHN     WIND\n####    ###     mm      degC    degC    MJ/m2   %       %       m/s\n")
    for y in sorted(wx):
        for d in sorted(wx[y]):
            r = wx[y][d]; w.write(f"{y}\t{d:03d}\t{r['pp']:.4f}\t{r['tx']:.2f}\t{r['tn']:.2f}\t{r['solar']:.4f}\t{r['rhx']:.2f}\t{r['rhn']:.2f}\t{r['wind']:.3f}\n")
    w.close()
    s = open(f"{CY15}/input/{site}.soil", "w")
    s.write("CURVE_NUMBER        75\nSLOPE               0\n")
    s.write("LAYER   THICK   CLAY    SAND    SOC     BD      FC      PWP     SON     NO3     NH4     ROCK    BYP_H   BYP_V   pH\n#       m       %       %       %       Mg/m3   m3/m3   m3/m3   kg/ha   kg/ha   kg/ha   m3/m3   -       -       -\n")
    for i, l in enumerate(soil_raw, 1):
        no3 = min(max(1, round(10 * l['thick'] / 0.05 * 0.25)), 10)
        s.write(f"{i}\t{l['thick']}\t{l['clay']}\t{l['sand']}\t{l['soc']}\t-999\t-999\t-999\t-999\t{no3}\t1\t{ROCK}\t0.0\t0.00\t{PH}\n")
    s.close()
    op = open(f"{CY15}/input/ContinuousCorn.operation").read()
    if N > 0: op = op.replace("468.75", f"{N / 0.32:.2f}", 1)
    else:
        a = op.index("FIXED_FERTILIZATION"); op = op[:a].rstrip() + "\n"
    open(f"{CY15}/input/{site}N{N}.operation", "w").write(op)
    c = open(f"{CY15}/input/ContinuousCorn.ctrl").read().replace("ContinuousCorn.operation", f"{site}N{N}.operation").replace("GenericHagerstown.soil", f"{site}.soil").replace("RockSprings.weather", f"{site}.weather")
    c = re.sub(r"SOIL_LAYERS\s+\d+", f"SOIL_LAYERS             {len(soil_raw)}", c)
    open(f"{CY15}/input/{site}N{N}.ctrl", "w").write(c)

def read15(site, N):
    subprocess.run(["./Cycles", f"{site}N{N}"], cwd=CY15, capture_output=True)
    out = f"{CY15}/output/{site}N{N}"; H = {}; A = {}
    for line in open(f"{out}/harvest.csv").readlines()[2:]:
        p = line.strip().split(",")
        if len(p) > 10: H[int(p[0][:4])] = dict(total=float(p[3]), grain=float(p[5]), plant=p[2])
    for line in open(f"{out}/annualN.csv").readlines()[2:]:
        p = line.strip().split(",")
        if len(p) >= 12: A[int(p[0])] = dict(leach=float(p[4]) + float(p[5]), denit=float(p[8]), volat=float(p[10]), n2o=float(p[11]))
    return H, A

def doy(s): y, m, d = map(int, s.split("-")); return datetime.date(y, m, d).timetuple().tm_yday
def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b); sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((a[i] - ma) * (b[i] - mb) for i in range(len(a))) / (sa * sb) if sa and sb else float("nan")

if __name__ == "__main__":
    out = {}
    _only = [x for x in os.environ.get('SITES', '').split(',') if x]
    for site, (lat, lon) in ms.SITES.items():
        if _only and site not in _only: continue
        wx, _ = fd.resolve_field_weather(lat, lon); soil, _, name = fd.resolve_field_soil(lat, lon); cl = ms.lat_of(lat, lon)
        for N in (0, 150):
            write15(site, wx, soil, cl, N)
            H5, A5 = read15(site, N)
            H4, A4 = ms.run_cycles(site, N)   # cached v1.4.4
            ys = sorted(set(H4) & set(H5)); row = {}
            for var, f4, f5 in (("grain", lambda y: H4[y]["grain"], lambda y: H5[y]["grain"]), ("total_biomass", lambda y: H4[y]["total"], lambda y: H5[y]["total"]),
                                ("plant_doy", lambda y: doy(H4[y]["plant"]), lambda y: doy(H5[y]["plant"]))):
                a = [f4(y) for y in ys]; b = [f5(y) for y in ys]
                row[var] = dict(v144=statistics.mean(a), v15=statistics.mean(b), mae=statistics.mean(abs(x - z) for x, z in zip(a, b)), corr=corr(a, b), n=len(ys))
            if N == 150:
                yy = [y for y in ys if y in A4 and y in A5]
                for k in ("leach", "denit", "volat", "n2o"):
                    a = [A4[y][k] for y in yy]; b = [A5[y][k] for y in yy]
                    row[k] = dict(v144=statistics.mean(a), v15=statistics.mean(b), mae=statistics.mean(abs(x - z) for x, z in zip(a, b)), corr=corr(a, b), n=len(yy))
            out[f"{site}|N{N}"] = row
            print(site, N, {k: (round(v["v144"], 2), round(v["v15"], 2), round(v["corr"], 2)) for k, v in row.items()}, flush=True)
    json.dump(out, open(os.path.join(P, "cycles_version_compare.json"), "w"), indent=1)
