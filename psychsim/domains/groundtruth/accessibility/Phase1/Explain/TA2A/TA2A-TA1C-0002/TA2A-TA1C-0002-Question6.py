import csv
import os.path
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    root = os.path.join(os.path.dirname(__file__),'..','..','..','..','..','Instances','Instance24','Runs','run-1')
    data = accessibility.loadRunData(24,1,82)
    world = accessibility.loadPickle(24,1)
    with open(os.path.join(root,'ActorPostTable.tsv'),'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if int(row['Timestep']) > 82:
                break
            matches = accessibility.findMatches(row,world)
            assert len(matches) == 1
            name = next(iter(matches))
            value = data[name]['%s\'s resources' % (name)][int(row['Timestep'])]
            assert int(5.1*value) == int(row['Wealth'])
            if row['Age'] == '31' and row['Residence'] == 'Region08':
                print(row['Timestep'],int(5.1*value),int(row['Wealth']))
                print(int(5.1*world.agents[name].getState('resources').expectation()))