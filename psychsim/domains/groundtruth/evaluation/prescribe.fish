#!/usr/bin/fish
argparse --name=prescribe 'e/evaluate' -- $argv
cd (dirname (status -f))
cd ..
if set -q _flag_e
	set instances 24  27  53  52 51  55  56  54 81  83  82  86  84  85
	set runs       1   0   1   1  1   1   1   1  1   1   1   1   1   1
	set span      82 565 147 135 77 181 168 172 79 133 130 173 176 189
	set run 1
	for team in A B
		for constraint in Constrained Unconstrained
			for metric in Casualties Dissatisfaction
				for instance in (seq 9 14)
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
						if test $instance -gt 11
							# long-term
							echo "Long-term"
							./gt.sh -i $instances[$instance] --seasons 2 -r $run --reload $span[$instance] --pickle -d INFO --singlerun	--prescription evaluation/Phase1Prescribe/[$team]/[$instance]/[$constraint]Prescription[$metric].tsv
						else
							# short-term
							echo "Short-term"
							./gt.sh -i $instances[$instance] -n 7 -r $run --reload $span[$instance] --pickle -d INFO --singlerun --hurricane Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/HurricaneInput.tsv	--prescription evaluation/Phase1Prescribe/[$team]/[$instance]/[$constraint]Prescription[$metric].tsv
						end
						rm Instances/Instance$instances[$instance]/Runs/run-$run/scenario$span[$instance].pkl
						bzip2 Instances/Instance$instances[$instance]/Runs/run-$run/*.pkl
						mkdir Instances/Instance$instances[$instance]/Runs/run-$run/[$team]_[$constraint]_[$metric]
						mv Instances/Instance$instances[$instance]/Runs/run-$run/*.* Instances/Instance$instances[$instance]/Runs/run-$run/[$team]_[$constraint]_[$metric]
					end
				end
			end
		end
	end
else
	echo "no evaluate"
#	./gt.sh -i 81 -n 6 -r 1 --pickle -d INFO --singlerun
#	./gt.sh -i 82 -n 6 -r 1 --pickle -d INFO --singlerun
#	./gt.sh -i 83 -n 6 -r 1 --pickle -d INFO --singlerun
#	./gt.sh -i 84 --seasons 1 -r 1 --pickle -d INFO --singlerun
#	./gt.sh -i 85 --seasons 1 -r 1 --pickle -d INFO --singlerun
#	./gt.sh -i 86 --seasons 1 -r 1 --pickle -d INFO --singlerun
end
