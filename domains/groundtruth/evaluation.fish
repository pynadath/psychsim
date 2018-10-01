#!/usr/bin/fish
cd (dirname (status -f))
python3 package.py $HOME/Downloads/CDF-USC-Flexibility-MainEffects.zip -a 0 1 2 3 4 5 6 7 8 9
python3 package.py $HOME/Downloads/CDF-USC-Complexity.zip 11 12 13 14 15 16 17 18 19 20
python3 package.py $HOME/Downloads/CDF-USC-Plausibility.zip 0 1 2 3 4 5 6 7 8 9 11 12 13 14 15 16 17 18 19 20



