import unittest

from psychsim.world import *
from psychsim.agent import Agent
from psychsim.pwl import *

class TestAgents(unittest.TestCase):

    def setUp(self):
        # Create world
        self.world = World()
        # Create agents
        self.tom = Agent('Tom')
        self.world.addAgent(self.tom)
        self.jerry = Agent('Jerry')
        self.world.addAgent(self.jerry)

    def addStates(self):
        """Create state features"""
        self.world.defineState(self.tom.name,'health',int,lo=0,hi=100,
                               description='%s\'s wellbeing' % (self.tom.name))
        self.world.setState(self.tom.name,'health',50)
        self.world.defineState(self.jerry.name,'health',int,lo=0,hi=100,
                               description='%s\'s wellbeing' % (self.jerry.name))
        self.world.setState(self.jerry.name,'health',50)

    def addActions(self):
        """Create actions"""
        self.chase = self.tom.addAction({'verb': 'chase','object': self.jerry.name})
        self.hit = self.tom.addAction({'verb': 'hit','object': self.jerry.name})

    def addDynamics(self):
        """Create dynamics"""
        tree = makeTree(incrementMatrix(stateKey(self.jerry.name,'health'),-10))
        self.world.setDynamics(self.jerry.name,'health',self.hit,tree,enforceMin=True)

    def saveload(self):
        """Write scenario to file and then load from scratch"""
        self.world.save('/tmp/psychsim_test.psy')
        self.world = World('/tmp/psychsim_test.psy')
        self.tom = self.world.agents[self.tom.name]
        self.jerry = self.world.agents[self.jerry.name]

    def testBeliefs(self):
        self.addStates()
        self.addActions()
        vector = self.world.state.domain()[0]
        actions = {self.tom.name: self.hit}
        keyJ = stateKey(self.jerry.name,'health')
        keyT = stateKey(self.tom.name,'health')
        self.tom.setBelief(keyJ,incrementMatrix(keyJ,-10))
        self.saveload()
        print self.tom.getBelief(vector)

    def testDynamics(self):
        self.world.setOrder([self.tom.name])
        self.addStates()
        self.addActions()
        self.addDynamics()
        key = stateKey(self.jerry.name,'health')
        self.assertEqual(len(self.world.state),1)
        vector = self.world.state.domain()[0]
        self.assertTrue(vector.has_key(stateKey(self.tom.name,'health')))
        self.assertTrue(vector.has_key(turnKey(self.tom.name)))
        self.assertTrue(vector.has_key(key))
        self.assertTrue(vector.has_key(CONSTANT))
        self.assertEqual(len(vector),4)
        self.assertEqual(vector[stateKey(self.tom.name,'health')],50)
        self.assertEqual(vector[key],50)
        outcome = self.world.step({self.tom.name: self.chase})
        for i in range(7):
            self.assertEqual(len(self.world.state),1)
            vector = self.world.state.domain()[0]
            self.assertTrue(vector.has_key(stateKey(self.tom.name,'health')))
            self.assertTrue(vector.has_key(turnKey(self.tom.name)))
            self.assertTrue(vector.has_key(key))
            self.assertTrue(vector.has_key(CONSTANT))
            self.assertEqual(len(vector),4)
            self.assertEqual(vector[stateKey(self.tom.name,'health')],50)
            self.assertEqual(vector[key],max(50-10*i,0))
            outcome = self.world.step({self.tom.name: self.hit})
            self.saveload()

    def testRewardOnOthers(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.world.setOrder([self.tom.name])
        vector = self.world.state.domain()[0]
        # Create Jerry's goals
        goal = maximizeFeature(stateKey(self.jerry.name,'health'))
        self.jerry.setReward(goal,1.)
        jVal = -self.jerry.reward(vector)
        # Create Tom's goals from scratch
        minGoal = minimizeFeature(stateKey(self.jerry.name,'health'))
        self.tom.setReward(minGoal,1.)
        self.saveload()
        tRawVal = self.tom.reward(vector)
        self.assertAlmostEqual(jVal,tRawVal,8)
        # Create Tom's goals as a function of Jerry's
        self.tom.models[True]['R'].clear()
        self.tom.setReward(self.jerry.name,-1.)
        self.saveload()
        tFuncVal = self.tom.reward(vector)
        self.assertAlmostEqual(tRawVal,tFuncVal,8)
        # Test effect of functional reward on value function
        self.tom.setHorizon(1)
        self.saveload()
        vHit = self.tom.value(vector,self.hit)['V']
        vChase = self.tom.value(vector,self.chase)['V']
        self.assertAlmostEqual(vHit,vChase+.1,8)

if __name__ == '__main__':
    unittest.main()
