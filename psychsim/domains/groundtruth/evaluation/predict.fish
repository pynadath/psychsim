#!/usr/bin/fish
cd (dirname (status -f))
cd ..
if test (count $argv) -gt 0
	if test $argv[1] = "predict"
#		./gt.sh -i 51 -n 7 -r 1 --reload 77 --max --pickle -d INFO --singlerun
		./gt.sh -i 52 -n 7 -r 1 --reload 135 --max --pickle -d INFO --singlerun
#		./gt.sh -i 53 -n 7 -r 1 --reload 147 --max --pickle -d INFO --singlerun
		./gt.sh -i 54 --seasons 2 -r 1 --reload 172 --max --pickle -d INFO --singlerun
		./gt.sh -i 55 --seasons 2 -r 1 --reload 181 --max --pickle -d INFO --singlerun
		./gt.sh -i 56 --seasons 2 -r 1 --reload 168 --max --pickle -d INFO --singlerun
	else
		echo "Unknown command:" $argv
	end
else
	./gt.sh -i 51 -n 6 -r 2 --pickle -d INFO --singlerun
	./gt.sh -i 52 -n 6 -r 2 --pickle -d INFO --singlerun
	./gt.sh -i 53 -n 6 -r 2 --pickle -d INFO --singlerun
	./gt.sh -i 54 --seasons 1 -r 2 --pickle -d INFO --singlerun
	./gt.sh -i 55 --seasons 1 -r 2 --pickle -d INFO --singlerun
	./gt.sh -i 56 --seasons 1 -r 2 --pickle -d INFO --singlerun
end
