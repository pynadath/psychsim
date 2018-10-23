import copy
import csv
import logging
import os
import random
import unittest

from psychsim.pwl.keys import WORLD
if __name__ == '__main__':
    from simulation.region import Region
    from simulation.create import getConfig,createWorld
else:
    from .simulation.region import Region
    from .simulation.create import getConfig,createWorld

instance = 24
run = 1

class TestWorlds(unittest.TestCase):

    def test_creation(self):
        """
        Verify that all simulations created from the same instance are identical at time 1
        """
        os.chdir('Instances')
        for instance in os.listdir('.'):
            if instance[-2] == '3':
                os.chdir(os.path.join(instance,'Runs'))
                runs = os.listdir('.')
                base = {}
                if len(runs) > 1:
                    for run in runs:
                        inFile = os.path.join(run,'RunDataTable.tsv')
                        with open(inFile,'r') as csvfile:
                            reader = csv.DictReader(csvfile,delimiter='\t')
                            for row in reader:
                                if row['Timestep'] == '1':
                                    label = '%s %s' % (row['VariableName'],row['EntityIdx'])
                                    if label in base:
                                        self.assertEqual(row['Value'],base[label],
                                                         'Run %s deviates on value for %s on %s' % \
                                                         (run,label,instance))
                                    else:
                                        base[label] = row['Value']
                                else:
                                    break
                os.chdir(os.path.join('..','..'))
        os.chdir('..')

    def test_decisions(self):
        self.config = getConfig(999998)
        self.world = createWorld(self.config)
        

class TestDataPackage(unittest.TestCase):
    def setUp(self):
        self.root = os.getcwd()
        dirName = os.path.join(os.path.dirname(__file__),'Instances',
                               'Instance%d' % (instance),'Runs','run-%d' % (run))
        os.chdir(dirName)

    def tearDown(self):
        os.chdir(self.root)

    def test_census(self):
        """
        Verify that census counts all add up in the right way
        """
        population = {}
        with open('CensusTable.tsv','r') as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                if row['Region'] not in population:
                    population[row['Region']] = {}
                if not row['Field'] in population[row['Region']]:
                    population[row['Region']][row['Field']] = {}
                if row['Field'] == 'Population':
                    self.assertEqual(row['Value'],'')
                population[row['Region']][row['Field']][row['Value']] = int(row['Count'])
        self.assertEqual(len(population),17)
        total = population['All']
        # Make sure regional tables contain everything that is in total
        for region in range(16):
            name = Region.nameString % (region+1)
            self.assertEqual(len(population[name]),len(total))
            for field in population[name]:
                for value in population[name][field]:
                    self.assertIn(value,total[field])
        # Make sure regional counts add up to total counts
        for field in total:
            for value in total[field]:
                count = 0
                for region in range(16):
                    name = Region.nameString % (region+1)
                    count += population[name][field].get(value,0)
                self.assertEqual(count,total[field][value])
        # Make sure regional subcounts add up to regional population
        for region in range(16):
            name = Region.nameString % (region+1)
            for field in population[name]:
                count = sum(population[name][field].values())
                if field != 'Age' and field != 'Population':
                    count += population[name]['Age']['<18']
                self.assertEqual(count,population[name]['Population'][''],
                                 'Mismatch for field %s in %s' % (field,name))

    def testRegional(self):
        totals = []
        with open('PopulationTable.tsv','r') as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                totals.append(row)
        with open('RegionalTable.tsv','r') as csvfile:
            last = None
            total = {}
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                t = int(row['Timestep'])
                if t != last:
                    if last:
                        for field in total:
                            self.assertEqual(total[field],int(totals[last-1][field]))
                    total.clear()
                    last = t
                for field in totals[t-1]:
                    if field != 'Timestep' and field != 'Evacuees':
                        total[field] = int(row[field]) + total.get(field,0)
        
class TestGroundTruth(unittest.TestCase):
    def setUp(self):
        self.config = getConfig(999998)
        self.world = createWorld(self.config)

    def DONTtest_loop(self):
        keys = self.world.state.keys()
        seed = self.config.getint('Simulation','seedRun')
        self.assertEqual(seed,1)
        random.seed(seed)
        oldPhase = self.world.getState('Nature','phase').first()
        done = False
        while not done:
            today = self.world.getState(WORLD,'day').first()
            day = today
            while day == today:
                names = sorted(self.world.next())
                turn = self.world.agents[names[0]].__class__.__name__
                print('Day:',day,oldPhase,turn)
                for name in names:
                    agent = self.world.agents[name]
                    if name[:5] == 'Actor':
                        if oldPhase != 'none':
                            belief = agent.getBelief()
                            self.assertEqual(len(belief),1)
                            belief = next(iter(belief.values()))
                            model = self.world.getModel(name)
                            self.assertEqual(len(model),1)
                            model = next(iter(model.domain()))
                            actions = agent.getActions(belief)
                            self.assertGreater(len(actions),1)
                            location = self.world.getState(name,'location').first()
                            A = {}
                            for action in agent.actions:
                                if action['verb'] == 'moveTo':
                                    A[action['object']] = action
                                    if action['object'][:7] == 'shelter':
                                        if location == action['object']:
                                        
                                            self.assertNotIn(action,actions)
                                        else:
                                            self.assertIn(action,actions)
                                    elif action['object'] == agent.home:
                                        if location == agent.home:
                                            self.assertNotIn(action,actions)
                                        else:
                                            self.assertIn(action,actions)
                                else:
                                    A[action['verb']] = action
                            if agent.pet:
                                print(agent.name)
                                V = {}
                                for action in actions:
                                    hypo = copy.deepcopy(belief)
                                    self.world.step(action,hypo,keySubset=belief.keys(),horizon=0)
                                    V[action] = agent.reward(hypo,model)
                                Vmax = max(V.values())
                                for action in sorted(V):
                                    if action['verb'] == 'stayInLocation':
                                        print(action,location,V[action])
                                    else:
                                        print(action,V[action])
                                Astar = agent.decide(belief,horizon=1,model=model)['action']
                                print(Astar)
                newState = self.world.step(select=True)
                for key in newState.keys():
                    self.assertIn(key,newState.keyMap)
                day = self.world.getState(WORLD,'day').first()
                phase = self.world.getState('Nature','phase').first()
                if turn == 'Nature' and oldPhase != 'active':
                    self.assertNotEqual(phase,oldPhase)
                if phase == 'none':
                    if oldPhase == 'active':
                        # Completed one hurricane
                        done = True
                        break
                oldPhase = phase

if __name__ == '__main__':
#    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
    
