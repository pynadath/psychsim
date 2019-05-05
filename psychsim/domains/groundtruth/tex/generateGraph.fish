#!/usr/bin/fish
argparse -n "generateGraph" "c/config=" -- $argv
if not set -q _flag_c
	set _flag_c 999999
end
cd (dirname (status -f))
../gt.sh -i $_flag_c -n 0 --rerun --pickle
python3 ../../.. ../Instances/Instance$_flag_c/Runs/run-0/scenario1.pkl -c
python3 ../../../tools/world2tex.py ../Instances/Instance$_flag_c/Runs/run-0/scenario1.pkl groundTruth -t "USC Ground Truth"
