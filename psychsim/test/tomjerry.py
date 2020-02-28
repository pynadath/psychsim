import unittest

from psychsim.action import *
from psychsim.world import *
from psychsim.agent import Agent
from psychsim.pwl import *
from psychsim.reward import *

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
        self.run = self.jerry.addAction({'verb': 'run away'})
        self.trick = self.jerry.addAction({'verb': 'trick','object': self.tom.name})

    def addDynamics(self):
        """Create dynamics"""
        tree = makeTree(incrementMatrix(stateKey(self.jerry.name,'health'),-10))
        self.world.setDynamics(stateKey(self.jerry.name,'health'),self.hit,tree,enforceMin=True)

    def addModels(self,rationality=1.):
        self.tom.addModel('friend',rationality=rationality,parent=True)
        self.tom.setReward(maximizeFeature(stateKey(self.jerry.name,'health')),1.,'friend')
        self.tom.addModel('foe',rationality=rationality,parent=True)
        self.tom.setReward(minimizeFeature(stateKey(self.jerry.name,'health')),1.,'foe')

    def saveload(self):
        """Write scenario to file and then load from scratch"""
        self.world.save('/tmp/psychsim_test.psy')
        self.world = World('/tmp/psychsim_test.psy')
        self.tom = self.world.agents[self.tom.name]
        self.jerry = self.world.agents[self.jerry.name]

    def testEnumeratedState(self):
        self.addActions()
        self.world.defineVariable(self.tom.name,ActionSet)
        self.world.defineState(self.tom.name,'status',list,['dead','injured','healthy'])
        self.world.setState(self.tom.name,'status','healthy')
        goal = achieveFeatureValue(stateKey(self.tom.name,'status'),'healthy')
        self.tom.setReward(goal,1.)
        goal = achieveFeatureValue(stateKey(self.tom.name,'status'),'injured')
        self.jerry.setReward(goal,1.)
        self.saveload()
        self.assertEqual(len(self.world.state[None]),1)
        vector = self.world.state[None].domain()[0]
        tVal = self.tom.reward(vector)
        self.assertAlmostEqual(tVal,1.,8)
        jVal = self.jerry.reward(vector)
        self.assertAlmostEqual(jVal,0.,8)
        for action in self.tom.actions:
            encoding = self.world.value2float(self.tom.name,action)
            self.assertEqual(action,self.world.float2value(self.tom.name,encoding))

    def testBeliefModels(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.world.setOrder([self.tom.name])
        self.tom.addModel('optimist')
        self.tom.setBelief(stateKey(self.jerry.name,'health'),20,'optimist')
        self.tom.addModel('pessimist')
        self.world.setModel(self.jerry.name,True)
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'optimist': 0.5,'pessimist': 0.5})
        actions = {self.tom.name: self.hit}
        self.world.step(actions)
        vector = self.world.state[None].domain()[0]
        beliefs = self.jerry.getAttribute('beliefs',self.world.getModel(self.jerry.name,vector))
        for belief in beliefs.domain():
            model = self.world.getModel(self.tom.name,belief)
            if self.tom.models[model].has_key('beliefs'):
                nested = self.tom.models[model]['beliefs']
                self.assertEqual(len(nested),1)
                nested = nested.domain()[0]
                self.assertEqual(len(nested),1)
                self.assertAlmostEqual(nested[stateKey(self.jerry.name,'health')],10.,8)

    def testObservation(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.world.setOrder([self.tom.name])
        self.world.setModel(self.jerry.name,True)
        key = stateKey(self.jerry.name,'health')
        self.jerry.setBelief(key,Distribution({20: 0.5, 50: 0.5}))
        tree = makeTree({'if': thresholdRow(key,40),
                         True: {'distribution': [(KeyedVector({CONSTANT: 50}),.8),
                                                 (KeyedVector({CONSTANT: 20}),.2)]},
                         False: {'distribution': [(KeyedVector({CONSTANT: 50}),.2),
                                                  (KeyedVector({CONSTANT: 20}),.8)]}})
        self.jerry.defineObservation(key,tree)
        actions = {self.tom.name: self.hit}
        vector = self.world.state[None].domain()[0]
        omegaDist = self.jerry.observe(vector,actions)
        for omega in omegaDist.domain():
            new = KeyedVector(vector)
            model = self.jerry.index2model(self.jerry.stateEstimator(vector,new,omega))
            beliefs = self.jerry.models[model]['beliefs']
            if omega[key] > 30:
                # We observed a high value, so we should have a stronger belief in the higher value
                # which is now 40 after the hit
                for belief in beliefs.domain():
                    if beliefs[belief] > 0.5:
                        self.assertAlmostEqual(belief[key],40,8)
                    else:
                        self.assertAlmostEqual(belief[key],10,8)
            else:
                # We observed a low value, so we should have a stronger belief in the lower value
                # which is now 10 after the hit
                for belief in beliefs.domain():
                    if beliefs[belief] < 0.5:
                        self.assertAlmostEqual(belief[key],40,8)
                    else:
                        self.assertAlmostEqual(belief[key],10,8)

    def testUnobservedAction(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.addModels()
        self.world.setOrder([self.tom.name])
        self.world.setModel(self.jerry.name,True)
        self.jerry.setBelief(stateKey(self.jerry.name,'health'),50)
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'friend': 0.5,'foe': 0.5})
        tree = makeTree(True)
        self.jerry.defineObservation(self.tom.name,tree,self.hit,domain=ActionSet)
        tree = makeTree({'distribution': [(True,0.25),(False,0.75)]})
        self.jerry.defineObservation(self.tom.name,tree,self.chase,domain=ActionSet)
        vector = self.world.state[None].domain()[0]
        self.saveload()
        self.world.step({self.tom.name: self.hit})
        vector = self.world.state[None].domain()[0]

    def testRewardModels(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.addModels()
        self.world.setOrder([self.tom.name])
        # Add Jerry's model to the world (so that it gets updated)
        self.world.setModel(self.jerry.name,True)
        # Give Jerry uncertainty about Tom
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'friend': 0.5,'foe': 0.5})
        self.saveload()
        # Hitting should make Jerry think Tom is more of a foe
        actions = {self.tom.name: self.hit}
        self.world.step(actions)
        vector = self.world.state[None].domain()[0]
        belief01 = self.jerry.getAttribute('beliefs',self.world.getModel(self.jerry.name,vector))
        key = modelKey(self.tom.name)
        for belief in belief01.domain():
            if self.tom.index2model(belief[key]) == 'foe':
                prob01 = belief01[belief]
                break
        self.assertGreater(prob01,0.5)
        # If we think of Tom as even more of an optimizer, then our update should be stronger
        self.tom.setAttribute('rationality',10.,'foe')
        self.tom.setAttribute('rationality',10.,'friend')
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'friend': 0.5,'foe': 0.5})
        self.world.step(actions)
        vector = self.world.state[None].domain()[0]
        model = self.world.getModel(self.jerry.name,vector)
        belief10 = self.jerry.getAttribute('beliefs',model)
        key = modelKey(self.tom.name)
        for belief in belief10.domain():
            if self.tom.index2model(belief[key]) == 'foe':
                prob10 = belief10[belief]
                break
        self.assertGreater(prob10,prob01)
        # If we keep the same models, but get another observation, we should update even more
        self.world.step(actions)
        vector = self.world.state[None].domain()[0]
        model = self.world.getModel(self.jerry.name,vector)
        belief1010 = self.jerry.getAttribute('beliefs',model)
        key = modelKey(self.tom.name)
        for belief in belief1010.domain():
            if self.tom.index2model(belief[key]) == 'foe':
                prob1010 = belief1010[belief]
                break
        self.assertGreater(prob1010,prob10)

    def testDynamics(self):
        self.world.setOrder([self.tom.name])
        self.addStates()
        self.addActions()
        self.addDynamics()
        key = stateKey(self.jerry.name,'health')
        self.assertEqual(len(self.world.state[None]),1)
        vector = self.world.state[None].domain()[0]
        self.assertTrue(vector.has_key(stateKey(self.tom.name,'health')))
        self.assertTrue(vector.has_key(turnKey(self.tom.name)))
        self.assertTrue(vector.has_key(key))
        self.assertTrue(vector.has_key(CONSTANT))
        self.assertEqual(len(vector),4)
        self.assertEqual(vector[stateKey(self.tom.name,'health')],50)
        self.assertEqual(vector[key],50)
        outcome = self.world.step({self.tom.name: self.chase})
        for i in range(7):
            self.assertEqual(len(self.world.state[None]),1)
            vector = self.world.state[None].domain()[0]
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
        vector = self.world.state[None].domain()[0]
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

    def testReward(self):
        self.addStates()
        key = stateKey(self.jerry.name,'health')
        goal = makeTree({'if': thresholdRow(key,5),
                         True: KeyedVector({key: -2}),
                         False: KeyedVector({key: -1})})
        goal = goal.desymbolize(self.world.symbols)
        self.jerry.setReward(goal,1.)
        R = self.jerry.models[True]['R']
        self.assertEqual(len(R),1)
        newGoal = R.keys()[0]
        self.assertEqual(newGoal,goal)
        self.assertAlmostEqual(R[goal],1.,8)
        self.jerry.setReward(goal,2.)
        self.assertEqual(len(R),1)
        self.assertEqual(R.keys()[0],goal)
        self.assertAlmostEqual(R[goal],2.,8)

    def testTurnDynamics(self):
        self.addStates()
        self.addActions()
        self.world.setOrder([self.tom.name,self.jerry.name])
        self.assertEqual(self.world.maxTurn,1)
        self.saveload()
        vector = self.world.state[None].domain()[0]
        jTurn = turnKey(self.jerry.name)
        tTurn = turnKey(self.tom.name)
        self.assertEqual(self.world.next(),[self.tom.name])
        self.assertEqual(vector[tTurn],0)
        self.assertEqual(vector[jTurn],1)
        self.world.step()
        vector = self.world.state[None].domain()[0]
        self.assertEqual(self.world.next(),[self.jerry.name])
        self.assertEqual(vector[tTurn],1)
        self.assertEqual(vector[jTurn],0)
        self.world.step()
        vector = self.world.state[None].domain()[0]
        self.assertEqual(self.world.next(),[self.tom.name])
        self.assertEqual(vector[tTurn],0)
        self.assertEqual(vector[jTurn],1)
        # Try some custom dynamics
        self.world.setTurnDynamics(self.tom.name,self.hit,makeTree(noChangeMatrix(tTurn)))
        self.world.setTurnDynamics(self.jerry.name,self.hit,makeTree(noChangeMatrix(tTurn)))
        self.world.step()
        vector = self.world.state[None].domain()[0]
        self.assertEqual(self.world.next(),[self.tom.name])
        self.assertEqual(vector[tTurn],0)
        self.assertEqual(vector[jTurn],1)
        self.world.step({self.tom.name: self.chase})
        vector = self.world.state[None].domain()[0]
        self.assertEqual(self.world.next(),[self.jerry.name])
        self.assertEqual(vector[tTurn],1)
        self.assertEqual(vector[jTurn],0)

    def testStatic(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.addModels()
        self.world.setModel(self.jerry.name,True)
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'friend': 0.5,'foe': 0.5})
        self.world.setOrder([self.tom.name])
        vector = self.world.state[None].domain()[0]
        model = self.world.getModel(self.jerry.name,vector)
        belief0 = self.jerry.models[model]['beliefs']
        result = self.world.step({self.tom.name: self.hit})
        vector = self.world.state[None].domain()[0]
        model = self.world.getModel(self.jerry.name,vector)
        belief1 = self.jerry.models[model]['beliefs']
        key = modelKey(self.tom.name)
        for vector in belief0.domain():
            if self.tom.index2model(vector[key]) == 'friend':
                self.assertGreater(belief0[vector],belief1[vector])
            else:
                self.assertGreater(belief1[vector],belief0[vector])
        # Now with the static beliefs
        self.jerry.setAttribute('static',True,model)
        self.saveload()
        self.world.step()
        vector = self.world.state[None].domain()[0]
        model = self.world.getModel(self.jerry.name,vector)
        belief2 = self.jerry.models[model]['beliefs']
        for vector in belief1.domain():
            self.assertAlmostEqual(belief1[vector],belief2[vector],8)

if __name__ == '__main__':
    unittest.main()
