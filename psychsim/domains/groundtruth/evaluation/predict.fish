#!/usr/bin/fish
set instances 24  27  53  52 51  55  56  54 81 83 82 86 84 85
set runs       1   0   1   1  1   1   1   1  1  1  1  1  1  1
set span      82 565 147 135 77 181 168 172

cd (dirname (status -f))
cd ..
if test (count $argv) -gt 0
	if test $argv[1] = "predict"
		./gt.sh -i 51 -n 7 -r 1 --reload 77 --max --pickle -d INFO --singlerun
		./gt.sh -i 52 -n 7 -r 1 --reload 135 --max --pickle -d INFO --singlerun
		./gt.sh -i 53 -n 7 -r 1 --reload 147 --max --pickle -d INFO --singlerun
		./gt.sh -i 54 --seasons 2 -r 1 --reload 172 --max --pickle -d INFO --singlerun
		./gt.sh -i 55 --seasons 2 -r 1 --reload 181 --max --pickle -d INFO --singlerun
		./gt.sh -i 56 --seasons 2 -r 1 --reload 168 --max --pickle -d INFO --singlerun
	else if test $argv[1] = "distribution"
		set instance 3
		set run 2
		while true
			echo "Instance" $instances[$instance] "Run" $run
			# Make directory if it does not already exist
			if not test -e Instances/Instance$instances[$instance]/Runs/run-$run
				mkdir Instances/Instance$instances[$instance]/Runs/run-$run
			end
			if not test -e  Instances/Instance$instances[$instance]/Runs/run-$run/$argv[2]
				# Copy over original hurricanes
				cp Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/HurricaneTable.tsv Instances/Instance$instances[$instance]/Runs/run-$run
				# Copy over original scenario file
				cp Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/scenario$span[$instance].pkl Instances/Instance$instances[$instance]/Runs/run-$run
				if test $instance -gt 5
					# long-term
					echo "Long-term"
					if test $argv[2] = 'Output'
						./gt.sh -i $instances[$instance] --seasons 2 -r $run --reload $span[$instance] --pickle -d INFO --singlerun	
					else if test $argv[2] = 'Counterfactual'
						./gt.sh -i $instances[$instance] --seasons 2 -r $run --reload $span[$instance] --pickle -d INFO --singlerun	--phase1predictlong
					else
						echo "Unknown run type" $argv[2]
						break
					end	
				else
					# short-term
					echo "Short-term"
					if test $argv[2] = 'Output'
						./gt.sh -i $instances[$instance] -n 7 -r $run --reload $span[$instance] --pickle -d INFO --singlerun --hurricane Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/HurricaneInput.tsv		
					else if test $argv[2] = 'Counterfactual'
						./gt.sh -i $instances[$instance] -n 7 -r $run --reload $span[$instance] --pickle -d INFO --singlerun --hurricane Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/HurricaneInput.tsv	--phase1predictshort
					end
					echo -n "Diff"
					diff -w Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/OutputMax/HurricaneTable.tsv Instances/Instance$instances[$instance]/Runs/run-$run
				end
				rm Instances/Instance$instances[$instance]/Runs/run-$run/scenario$span[$instance].pkl
				bzip2 Instances/Instance$instances[$instance]/Runs/run-$run/*.pkl
				mkdir Instances/Instance$instances[$instance]/Runs/run-$run/$argv[2]
				mv Instances/Instance$instances[$instance]/Runs/run-$run/*.* Instances/Instance$instances[$instance]/Runs/run-$run/$argv[2]
			end
			# Move on to next instance
			set instance (math $instance + 1)
			if test $instance -gt 8
				# Finished a round of runs
				set instance 3
				set run (math $run + 1)
			end
		end
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
