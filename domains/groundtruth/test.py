import copy
import csv
import logging
import os
import random
import unittest

from psychsim.pwl.keys import WORLD
from psychsim.domains.groundtruth.region import Region
import psychsim.domains.groundtruth.__main__ as gt

instance = 24
run = 0

class TestDataPackage(unittest.TestCase):
    def setUp(self):
        dirName = os.path.join(os.path.dirname(__file__),'Instances',
                               'Instance%d' % (instance),'Runs','run-%d' % (run))
        os.chdir(dirName)

    def test_census(self):
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
                    
        
class TestGroundTruth(unittest.TestCase):
    def setUp(self):
        self.config = gt.getConfig(999998)
        self.world = gt.createWorld(self.config)

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
    
