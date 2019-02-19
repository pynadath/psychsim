#!/usr/bin/fish
cd (dirname (status -f))
../gt.sh -i 999999 -n 0 --rerun --pickle
python3 ../../.. ../Instances/Instance999999/Runs/run-0/scenario1.pkl -c
python3 ../../../tools/world2tex.py ../Instances/Instance999999/Runs/run-0/scenario1.pkl groundTruth -t "USC Ground Truth"
