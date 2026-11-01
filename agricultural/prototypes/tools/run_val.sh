#!/bin/bash
# usage: run_val.sh TAG CROPSEL "ENGINE_OVR" "CROPOVR"  (resumable, runs the 100-site validation set val100 in 4 shards)
cd /home/user/epistemic-demo/agricultural/prototypes
for i in 0 1 2 3; do
 RESUME=1 REGIONAL=0 LEAD_YEARS=continuous N_LEVELS=${N_LEVELS:-0,150,400} YEAR_STEP=2 BIGSET=/tmp/w/shardval_$i.json OUT_JSON=/tmp/w/$1_$i.json CROPSEL=$2 ENGINE_OVR="$3" CROPOVR="$4" \
  flock -n /tmp/w/lock_$1_$i python3 run_validation_multisite.py >> /tmp/w/$1_$i.log 2>&1 &
done
wait
