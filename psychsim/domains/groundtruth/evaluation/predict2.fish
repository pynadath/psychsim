#!/usr/bin/fish
set instances 100 101
set runs        2   1
set span       82 366

cd (dirname (status -f))
cd ..

set instance 1
set run 4
while true
	echo "Instance" $instances[$instance] "Run" $run
	if not test -e  Instances/Instance$instances[$instance]/Runs/run-$run
		# Make directory if it does not already exist
		mkdir Instances/Instance$instances[$instance]/Runs/run-$run
		# Copy over original hurricanes
		cp Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/HurricaneTable.tsv Instances/Instance$instances[$instance]/Runs/run-$run
		if test $instance -gt 1
			# long-term
			echo "Long-term"
			# link to original scenario file
			ln -s "../../../Instance$instances[$instance]/Runs/run-$runs[$instance]/scenario$span[$instance].pkl" Instances/Instance$instances[$instance]/Runs/run-$run
			if test (count $argv) -gt 0
				if test $argv[1] = 'Counterfactual'
					touch Instances/Instance$instances[$instance]/Runs/run-$run/counterfactual.txt
					./gt.sh $instances[$instance] --seasons 2 -r $run --reload $span[$instance] -d DEBUG --singlerun	--phase2predictlong
				else
					echo "Unknown run type" $argv[1]
					break
				end
			else
				./gt.sh $instances[$instance] --seasons 2 -r $run --reload $span[$instance] -d DEBUG --singlerun	
			end	
		else
			# short-term
			echo "Short-term"
			# link to original scenario file
			ln -s "../../../Instance$instances[$instance]/Runs/run-$runs[$instance]/scenario0.pkl" Instances/Instance$instances[$instance]/Runs/run-$run
			set t (math $span[$instance] - 1)
			ln -s "../../../Instance$instances[$instance]/Runs/run-$runs[$instance]/state"$t"Nature.pkl" Instances/Instance$instances[$instance]/Runs/run-$run
			if test (count $argv) -gt 0
				if test $argv[1] = 'Counterfactual'
					touch Instances/Instance$instances[$instance]/Runs/run-$run/counterfactual.txt
					./gt.sh $instances[$instance] -n 7 -r $run --reload $span[$instance] -d DEBUG --singlerun --hurricane Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/HurricaneInput.tsv	--phase2predictshort
				else
					echo "Unknown run type" $argv[1]
					break
				end
			else
				./gt.sh $instances[$instance] -n 7 -r $run --reload $span[$instance] -d DEBUG --singlerun --hurricane Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/HurricaneInput.tsv		
			end
		end
	end
	# Move on to next instance
	set instance (math $instance + 1)
	if test $instance -gt (count $instances)
		# Finished a round of runs
		break
		set instance 1
		set run (math $run + 1)
	end
end
