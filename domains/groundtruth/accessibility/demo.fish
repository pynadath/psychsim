#!/usr/bin/fish
cd (dirname (status -f))
set -x PYTHONHASHSEED=1

echo "1. Census"
python3 census.py 21 -r 2 --region 7 --day 91 population age gender

echo "2. Environmental data"
python3 environmental.py 21 -r 2 --hurricane 1 Category Location

echo "3. Brief from expert observer"
python3 brief.py 21 -r 2

echo "4. Interview"
python3 survey.py 21 -r 2 interview.tsv --samples 1 -o RequestInterview.tsv --seed 1

echo "5. Survey"
python3 survey.py 21 -r 2 survey.tsv --samples 10 --seed 1

echo "6. Ethnographic observation"
python3 ethnographic.py 21 -r 2 --samples 2

echo "7. Information soliciting task"
python3 solicit.py 21 -r 2 --samples 10

echo "8. Information flow data"
python3 flow.py 21 -r 2 --samples 10

echo "9. Interaction data"
python3 interaction.py 21 -r 2 --samples 20

echo "10. Event journal"
python3 journal.py 21 -r 2 --samples 1

echo "11. Passive data collection"
python3 passive.py 21 -r 2 --day 90 Casualties

echo "12. Laboratory experiment"
python3 laboratory.py 21 -r 2 --samples 1

echo "13. Randomized trial"
python3 trial.py 21 -r 2 --seed 1

echo "14. Experiment"
python3 experiment.py 21 -r 2 --seed 1
