#!/bin/bash
# Usage: ladder.sh LABEL "N1 N2 ..." [SECS]. Appends everything to results.log
L=$1; shift; S=${2:-60}
for n in $1; do
  echo "=== $L N=$n secs=$S $(date +%H:%M:%S)" | tee -a results.log
  timeout $((S+120)) python3 bots.py $n $S chicago 2>&1 | tee -a results.log
  sleep 8
done
