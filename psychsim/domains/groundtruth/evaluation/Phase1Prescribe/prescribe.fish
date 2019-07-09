#!/usr/bin/fish
argparse --name=prescribe 'e/evaluate' -- $argv
cd (dirname (status -f))
cd ../..
if set -q _flag_e
	set instances 24  27  53  52 51  55  56  54 81  83  82  86  84  85
	set runs       1   0   1   1  1   1   1   1  1   1   1   1   1   1
	set span      82 565 147 135 77 181 168 172 79 133 130 173 176 189
	set target     0   0   0   0  0   0   0   0  Actor0066 Actor0044 Actor0051 Actor0072 Actor0160 Actor0132

	function simulate
		set label $argv[1]
		set instance $argv[2]
		set run $argv[3]
		echo "Instance" $instances[$instance] "Run" $run "Label" $label
		# Make directory if it does not already exist
		if not test -e Instances/Instance$instances[$instance]/Runs/run-$run
			mkdir Instances/Instance$instances[$instance]/Runs/run-$run
		end
		if not test -e Instances/Instance$instances[$instance]/Runs/run-$run/$label
			echo "Initializing..."
			# Copy over original hurricanes
			cp Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/HurricaneTable.tsv Instances/Instance$instances[$instance]/Runs/run-$run
			# Copy over original scenario file
			cp Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/scenario(math $span[$instance]+1).pkl Instances/Instance$instances[$instance]/Runs/run-$run
			# Execute simulation
			echo "./gt.sh -i $instances[$instance] -r $run --reload "(math $span[$instance]+1)" --pickle -d INFO --singlerun $argv[4..-1]"
			if ./gt.sh -i $instances[$instance] -r $run --reload (math $span[$instance]+1) --pickle -d INFO --singlerun $argv[4..-1]
				# Successful simulation
				echo "Success"
				bzip2 Instances/Instance$instances[$instance]/Runs/run-$run/*.pkl
				mkdir Instances/Instance$instances[$instance]/Runs/run-$run/$label
				mv Instances/Instance$instances[$instance]/Runs/run-$run/*.* Instances/Instance$instances[$instance]/Runs/run-$run/$label
			else
				# Failed simulation
				echo "Failure"
				rm Instances/Instance$instances[$instance]/Runs/run-$run/scenario(math $span[$instance]+1).pkl
			end
		end
	end
	# Generate baseline outcomes
	for instance in (seq 9 14)
		if test $instance -gt 11
			# long-term
			set params --seasons 2
		else
			# short-term
			set params -n 7 --hurricane Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/HurricaneInput.tsv
		end
		simulate Actual $instance $runs[$instance] $params
	end
	# Run prescriptions
	for team in A B
		for instance in (seq 9 11)
			if test $instance -gt 11
				# long-term
				set questions Offseason Inseason Individual
			else 
				# short-term
				set questions Constrained Unconstrained Individual
			end
			for question in questions
				for metric in Casualties Dissatisfaction
					if test $question = "Individual" 
						and test $metric = "Dissatisfaction"
						# Individual prescriptions don't target dissatisfaction
						continue
					end 
					if test $instance -gt 11
						if test $question = "Individual"
							set params --seasons 2  --target $target[$instance] evaluation/Phase1Prescribe/$team/$instance/"$question"Prescription"$metric".tsv
						else
							set params --seasons 2 --prescription evaluation/Phase1Prescribe/$team/$instance/"$question"Prescription"$metric".tsv
						end
					else 
						if test $question = "Individual"
							set params -n 7 --hurricane Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/HurricaneInput.tsv --target $target[$instance] evaluation/Phase1Prescribe/$team/$instance/"$question"Prescription"$metric".tsv
						else
							set params -n 7 --hurricane Instances/Instance$instances[$instance]/Runs/run-$runs[$instance]/Input/HurricaneInput.tsv --prescription evaluation/Phase1Prescribe/$team/$instance/"$question"Prescription"$metric".tsv
						end
					end
					simulate $team$question$metric $instance $runs[$instance] $params
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
