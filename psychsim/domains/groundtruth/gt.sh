#!/bin/sh
export PYTHONPATH=/home/david/psychsim
export PYTHONHASHSEED=1
python3 ${PYTHONPATH}/psychsim/domains/groundtruth/simulation.py $*
