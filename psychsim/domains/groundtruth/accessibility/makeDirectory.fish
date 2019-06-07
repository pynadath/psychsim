set lo 1
if test (count $argv) -gt 0
	if test $argv[1] = "prescribe"
		set lo 9
	end
end
for i in (seq $lo 14)
	mkdir -p Instances/Instance$i/Runs/run-0
end
mkdir -p SimulationDefinition
