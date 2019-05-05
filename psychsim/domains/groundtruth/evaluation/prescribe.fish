#!/usr/bin/fish
cd (dirname (status -f))
cd ..
./gt.sh -i 81 -n 6 -r 1 --pickle -d INFO --singlerun
./gt.sh -i 82 -n 6 -r 1 --pickle -d INFO --singlerun
./gt.sh -i 83 -n 6 -r 1 --pickle -d INFO --singlerun
./gt.sh -i 84 --seasons 1 -r 1 --pickle -d INFO --singlerun
./gt.sh -i 85 --seasons 1 -r 1 --pickle -d INFO --singlerun
./gt.sh -i 86 --seasons 1 -r 1 --pickle -d INFO --singlerun
