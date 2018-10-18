#!/usr/bin/fish
cd (dirname (status -f))
set -x PYTHONHASHSEED=1
python3 . -n 3 -i 0 -r 10
python3 . -n 3 -i 1 -r 10
python3 . -n 3 -i 2 -r 10
python3 . -n 3 -i 3 -r 10
python3 . -n 3 -i 4 -r 10
python3 . -n 3 -i 5 -r 10
python3 . -n 3 -i 6 -r 10
python3 . -n 3 -i 7 -r 10
python3 . -n 3 -i 8 -r 10
python3 . -n 3 -i 9 -r 10

