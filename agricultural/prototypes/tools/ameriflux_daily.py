"""Reduce an AmeriFlux BASE or FLUXNET zip to a small daily CSV (run on your own computer, then commit the result).

    python3 ameriflux_daily.py AMF_US-Ne3_BASE-BADM_*.zip            # writes US-Ne3_daily.csv next to the zip
    python3 ameriflux_daily.py a.zip b.zip c.zip

Python 3 standard library only. It reads the half-hourly (HH) or hourly (HR) CSV inside the zip, treats -9999 as missing, and writes one row per
day: the mean of every variable that is present (TA, SW_IN, RN, LE, H, G, NEE, FC, GPP*, RECO*, SWC*, TS*, VPD, WS ...), except P which is the daily sum.
A day needs at least 40 percent of its records for a variable, otherwise that cell is blank. Units are unchanged from AmeriFlux (W m-2, umol m-2 s-1,
degC, mm per record for P), so a daily mean flux times 86400 gives per-day totals. Data are CC-BY-4.0: cite the site DOI (US-Ne1 10.17190/AMF/1246084,
US-Ne2 10.17190/AMF/1246085, US-Ne3 10.17190/AMF/1246086) and acknowledge AmeriFlux when publishing."""
import csv, io, os, re, sys, zipfile
from collections import defaultdict

SUM_VARS = ("P", "P_F")
MIN_FRAC = 0.40

def pick(names):
    cand = [n for n in names if re.search(r"_(HH|HR)_.*\.csv$", n) and "BADM" not in n and "BIF" not in n and "VARINFO" not in n.upper()]
    if not cand:
        cand = [n for n in names if n.lower().endswith(".csv") and re.search(r"(HH|HR)", n)]
    if not cand:
        raise SystemExit("no half-hourly or hourly csv found; files are: " + ", ".join(names))
    return sorted(cand)[0]

def reduce_zip(path):
    z = zipfile.ZipFile(path)
    inner = pick(z.namelist())
    site = re.search(r"(US-[A-Za-z0-9]+|[A-Z]{2}-[A-Za-z0-9]+)", os.path.basename(inner) or os.path.basename(path)).group(1)
    with z.open(inner) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
        lines = (ln for ln in text if not ln.startswith("#"))
        rd = csv.reader(lines)
        head = next(rd)
        ts = head.index("TIMESTAMP_START") if "TIMESTAMP_START" in head else 0
        keep = [i for i, h in enumerate(head) if i != ts and not h.startswith("TIMESTAMP") and not re.search(r"_(QC|SE|N|RANDUNC|JOINTUNC)", h) and not h.endswith("_FLAG")]
        sums = defaultdict(lambda: defaultdict(float)); cnt = defaultdict(lambda: defaultdict(int)); nrec = defaultdict(int)
        for row in rd:
            if len(row) <= ts: continue
            day = row[ts][:8]; nrec[day] += 1
            for i in keep:
                if i >= len(row): continue
                try: v = float(row[i])
                except ValueError: continue
                if v <= -9998: continue
                sums[day][i] += v; cnt[day][i] += 1
    names = [head[i] for i in keep]
    out = os.path.join(os.path.dirname(os.path.abspath(path)), f"{site}_daily.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date"] + names)
        for day in sorted(sums):
            row = [f"{day[:4]}-{day[4:6]}-{day[6:8]}"]
            n = nrec[day]
            for i in keep:
                c = cnt[day].get(i, 0)
                if c == 0 or c < MIN_FRAC * n: row.append("")
                else:
                    v = sums[day][i]
                    row.append(f"{v if head[i] in SUM_VARS else v / c:.5g}")
            w.writerow(row)
    print(f"{path}: {site}, {len(sums)} days, {len(names)} variables -> {out} ({os.path.getsize(out)/1024:.0f} KB)")

if __name__ == "__main__":
    if len(sys.argv) < 2: raise SystemExit(__doc__)
    for p in sys.argv[1:]: reduce_zip(p)
