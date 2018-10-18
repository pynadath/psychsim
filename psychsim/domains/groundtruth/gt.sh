#!/bin/sh
export PYTHONPATH=/home/david/psychsim
export PYTHONHASHSEED=1
python3 /home/david/psychsim/psychsim/domains/groundtruth/simulation.py $*
