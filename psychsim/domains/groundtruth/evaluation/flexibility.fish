#!/usr/bin/fish
cd (dirname (status -f))
cd ..
./gt.sh -i 30 -n 6 -r 10 --pickle -d INFO
./gt.sh -i 31 -n 6 -r 10 --pickle -d INFO
./gt.sh -i 32 -n 6 -r 10 --pickle -d INFO
./gt.sh -i 33 -n 6 -r 10 --pickle -d INFO
./gt.sh -i 34 -n 6 -r 10 --pickle -d INFO
./gt.sh -i 35 -n 6 -r 10 --pickle -d INFO
./gt.sh -i 36 -n 6 -r 10 --pickle -d INFO
./gt.sh -i 37 -n 6 -r 10 --pickle -d INFO

