"""Builds /tmp/cycles-ref15 (legacy harvest.txt layout) from a Cycles v1.5.20 directory so run_validation.py and
run_validation_rotation2.py can score the Rock Springs sample scenarios against v1.5.20:
  cd /tmp/cycles-run15 && ./Cycles ContinuousCorn && ./Cycles CornSilageSoyWheat
  python3 make_ref15.py && REF_DIR=/tmp/cycles-ref15 python3 run_validation.py
Cycles output is licensed, so nothing here is committed."""
import os, shutil
SRC, DST = "/tmp/cycles-run15", "/tmp/cycles-ref15"
os.makedirs(f"{DST}/input", exist_ok=True)
shutil.copy(f"{SRC}/input/RockSprings.weather", f"{DST}/input/")
for rot in ("ContinuousCorn", "CornSilageSoyWheat"):
    os.makedirs(f"{DST}/output/{rot}", exist_ok=True)
    rows = open(f"{SRC}/output/{rot}/harvest.csv").readlines()
    with open(f"{DST}/output/{rot}/harvest.txt", "w") as f:
        f.write("hdr\nunits\n")
        for l in rows[2:]:
            f.write(l.strip().replace(",", "\t") + "\n")
