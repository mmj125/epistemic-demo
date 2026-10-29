#!/bin/bash
# resumable county run: call again after any restart
cd /home/user/epistemic-demo/agricultural/prototypes
[ -f /tmp/w/engine_county_runs_final.json ] && exit 0
RESUME=1 OUTRUN=/tmp/w/engine_county_runs_final.json flock -n /tmp/w/lock_county python3 county_runs_2026_10_20.py >> /tmp/w/cr_final.log 2>&1
