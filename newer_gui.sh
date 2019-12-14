#!/bin/sh
# demo mode
# ./shell.sh -i 90 -r 0 --demo
# test mode
#./shell.sh -i 90 -r 0 --test
# auto test mode (developer)
# ./shell
# shell.sh -i 90 -r 0 --autotest

export PYTHONPATH=~/Dropbox/GitHub/groundtruth
export PYTHONHASHSEED=1
python3  ${PYTHONPATH}/psychsim/domains/groundtruth/explore_simulation/gui_query.py $*

