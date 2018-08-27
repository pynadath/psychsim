import copy
import logging
import random
import unittest

from psychsim.pwl.keys import WORLD
import psychsim.domains.disaster.groundtruth.__main__ as gt

class TestGroundTruth(unittest.TestCase):
    def setUp(self):
        self.config = gt.getConfig(999998)
        self.world = gt.createWorld(self.config)

    def test_loop(self):
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
                print('Day:',day,oldPhase,self.world.agents[names[0]].__class__.__name__)
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
                                    self.world.step(action,hypo,belief.keys(),horizon=0)
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
                day = self.world.getState(WORLD,'day').first()
                phase = self.world.getState('Nature','phase').first()
                if phase == 'none':
                    if oldPhase == 'active':
                        # Completed one hurricane
                        done = True
                        break
                oldPhase = phase

if __name__ == '__main__':
#    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
    
