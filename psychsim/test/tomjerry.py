import pickle
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
        self.tom = self.world.addAgent('Tom')
        self.jerry = self.world.addAgent('Jerry')

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
        self.nop = self.tom.addAction({'verb': 'doNothing'})
        self.run = self.jerry.addAction({'verb': 'run away'})
        self.trick = self.jerry.addAction({'verb': 'trick','object': self.tom.name})
        self.world.setOrder([self.tom.name,self.jerry.name])

    def addDynamics(self):
        """Create dynamics"""
        tree = makeTree(incrementMatrix(stateKey(self.jerry.name,'health'),-10))
        self.world.setDynamics(stateKey(self.jerry.name,'health'),self.hit,tree,enforceMin=True)

    def addModels(self,rationality=1.):
        model = next(iter(self.tom.models.keys()))
        self.tom.addModel('friend',rationality=rationality,parent=model)
        self.tom.setReward(maximizeFeature(stateKey(self.jerry.name,'health'),self.jerry.name),1.,'friend')
        self.tom.addModel('foe',rationality=rationality,parent=model)
        self.tom.setReward(minimizeFeature(stateKey(self.jerry.name,'health'),self.jerry.name),1.,'foe')

    def saveload(self):
        """Write scenario to file and then load from scratch"""
        with open('/tmp/psychsim_test.pkl','wb') as f:
            pickle.dump(self.world,f)
        with open('/tmp/psychsim_test.pkl','rb') as f:
            self.world = pickle.load(f)
        self.tom = self.world.agents[self.tom.name]
        self.jerry = self.world.agents[self.jerry.name]

    def DONTtestEnumeratedState(self):
        self.addActions()
        self.world.defineState(self.tom.name,'status',list,['dead','injured','healthy'])
        self.world.setState(self.tom.name,'status','healthy')
        goal = achieveFeatureValue(stateKey(self.tom.name,'status'),'healthy',self.tom.name)
        self.tom.setReward(goal,1.)
        goal = achieveFeatureValue(stateKey(self.tom.name,'status'),'injured',self.tom.name)
        self.jerry.setReward(goal,1.)
        self.saveload()
        self.assertEqual(len(self.world.state),1)
        tVal = self.tom.reward(self.world.state)
        self.assertAlmostEqual(tVal,1.,8)
        jVal = self.jerry.reward(self.world.state)
        self.assertAlmostEqual(jVal,0.,8)
        key = stateKey(self.tom.name,ACTION)
        for action in self.tom.actions:
            encoding = self.world.value2float(key,action)
            self.assertEqual(action,self.world.float2value(key,encoding))

    def DONTtestBeliefModels(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.world.setOrder([self.tom.name])
        self.tom.addModel('optimist')
        self.tom.resetBelief('optimist')
        self.tom.setBelief(stateKey(self.jerry.name,'health'),20,'optimist')
        self.tom.addModel('pessimist')
        self.world.setModel(self.jerry.name,'%s0' % (self.jerry.name))
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'optimist': 0.5,'pessimist': 0.5})
        actions = {self.tom.name: self.hit}
        self.world.step(actions,updateBeliefs=True)
        beliefs = self.jerry.getAttribute('beliefs',self.world.getModel(self.jerry.name).first())
        model = self.world.getModel(self.tom.name,beliefs).first()
        if 'beliefs' in self.tom.models[model]:
            nested = self.tom.models[model]['beliefs']
            self.assertAlmostEqual(nested[stateKey(self.jerry.name,'health')].expectation(),10.,8)

    def testObservation(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.tom.models[next(iter(self.tom.models))]['static'] = True
        key = stateKey(self.jerry.name,'health')
        # Add observation
        oHealth = self.jerry.defineObservation('perceivedHealth')
        tree = makeTree({'if': thresholdRow(key,40),
                         True: {'distribution': [(setToConstantMatrix(oHealth,50),.8),
                                                 (setToConstantMatrix(oHealth,20),.2)]},
                         False: {'distribution': [(setToConstantMatrix(oHealth,50),.2),
                                                  (setToConstantMatrix(oHealth,20),.8)]}})
        self.jerry.setO('perceivedHealth',None,tree)
        self.world.setFeature(oHealth,20)
        self.jerry.defineActionObservable(self.tom.name)
        self.jerry.defineActionObservable(self.jerry.name)
        # Add uncertainty about health
        self.jerry.setBelief(key,Distribution({20: 0.5, 50: 0.5}),'%s0' % (self.jerry.name))
        # See what happens if Tom hits Jerry
        actions = {self.tom.name: self.hit}
        self.world.step(actions,updateBeliefs=True)
        for model,beliefs in self.jerry.getBelief().items():
            omega = beliefs[oHealth]
            health = beliefs[key]
            self.assertEqual(len(omega),1)
            omega = omega.first()
            if omega > 30:
                # We observed a high value, so we should have a stronger belief in the higher value
                # which is now 40 after the hit
                for belief in health.domain():
                    if health[belief] > 0.5:
                        self.assertAlmostEqual(belief,40,8)
                    else:
                        self.assertAlmostEqual(belief,10,8)
            else:
                # We observed a low value, so we should have a stronger belief in the lower value
                # which is now 10 after the hit
                for belief in health.domain():
                    if health[belief] < 0.5:
                        self.assertAlmostEqual(belief,40,8)
                    else:
                        self.assertAlmostEqual(belief,10,8)

    def DONTtestUnobservedAction(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.addModels()
        self.world.setOrder([self.tom.name])
        self.world.setModel(self.jerry.name,'%s0' % (self.jerry.name))
        omega = self.jerry.defineObservation('%sAct' % (self.tom.name),domain=ActionSet)
        tree = makeTree(setToFeatureMatrix(omega,stateKey(self.tom.name,ACTION)))
        self.jerry.setO('%sAct' % (self.tom.name),self.hit,tree)
        tree = makeTree({'distribution': [(setToFeatureMatrix(omega,stateKey(self.tom.name,ACTION)),0.25),
            (setToConstantMatrix(omega,self.nop),0.75)]})
        self.jerry.setO('%sAct' % (self.tom.name),self.chase,tree)
        self.jerry.setBelief(stateKey(self.jerry.name,'health'),50)
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'friend': 0.5,'foe': 0.5},'%s0' %( self.jerry.name))
#        vector = self.world.state.domain()[0]
        self.saveload()
        self.world.step({self.tom.name: self.hit})
#        vector = self.world.state.domain()[0]

    def DONTtestRewardModels(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.addModels()
        self.world.setOrder([self.tom.name])
        # Add Jerry's model to the world (so that it gets updated)
#        self.world.setModel(self.jerry.name,True)
        # Give Jerry uncertainty about Tom
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'friend': 0.5,'foe': 0.5})
        self.saveload()
        # Hitting should make Jerry think Tom is more of a foe
        actions = {self.tom.name: self.hit}
        self.world.step(actions)
        vector = self.world.state.domain()[0]
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
        vector = self.world.state.domain()[0]
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
        vector = self.world.state.domain()[0]
        model = self.world.getModel(self.jerry.name,vector)
        belief1010 = self.jerry.getAttribute('beliefs',model)
        key = modelKey(self.tom.name)
        for belief in belief1010.domain():
            if self.tom.index2model(belief[key]) == 'foe':
                prob1010 = belief1010[belief]
                break
        self.assertGreater(prob1010,prob10)

    def DONTtestDynamics(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.tom.models[next(iter(self.tom.models))]['static'] = True
        self.jerry.models[next(iter(self.jerry.models))]['static'] = True
        self.assertEqual(len(self.world.state),1)
        self.assertTrue(stateKey(self.tom.name,'health') in self.world.state)
        self.assertTrue(stateKey(self.jerry.name,'health') in self.world.state)
        self.assertTrue(modelKey(self.tom.name) in self.world.state)
        self.assertTrue(modelKey(self.jerry.name) in self.world.state)
        self.assertTrue(turnKey(self.tom.name) in self.world.state)
        self.assertTrue(turnKey(self.jerry.name) in self.world.state)
        self.assertTrue(stateKey(self.tom.name,ACTION) in self.world.state)
        self.assertTrue(stateKey(self.jerry.name,ACTION) in self.world.state)
        self.assertEqual(len(self.world.state.keys()),8)
        self.assertEqual(self.world.state[stateKey(self.tom.name,'health')].expectation(),50)
        self.assertEqual(self.world.state[stateKey(self.jerry.name,'health')].expectation(),50)
        for i in range(7):
            outcome = self.world.step({self.tom.name: self.hit})
            outcome = self.world.step({self.jerry.name: self.run})
            self.assertEqual(len(self.world.state),1)
            self.assertTrue(stateKey(self.tom.name,'health') in self.world.state)
            self.assertTrue(stateKey(self.jerry.name,'health') in self.world.state)
            self.assertTrue(modelKey(self.tom.name) in self.world.state)
            self.assertTrue(modelKey(self.jerry.name) in self.world.state)
            self.assertTrue(turnKey(self.tom.name) in self.world.state)
            self.assertTrue(turnKey(self.jerry.name) in self.world.state)
            self.assertTrue(stateKey(self.tom.name,ACTION) in self.world.state)
            self.assertTrue(stateKey(self.jerry.name,ACTION) in self.world.state)
            self.assertEqual(len(self.world.state.keys()),8)
            self.assertEqual(self.world.state[stateKey(self.tom.name,'health')].expectation(),50)
            self.assertEqual(self.world.state[stateKey(self.jerry.name,'health')].expectation(),max(50-10*(i+1),0))
            self.saveload()

    def DONTtestRewardOnOthers(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.world.setOrder([self.tom.name])
        # Create Jerry's goals
        goal = maximizeFeature(stateKey(self.jerry.name,'health'),self.jerry.name)
        self.jerry.setReward(goal,1.)
        jVal = -self.jerry.reward(self.world.state)
        # Create Tom's goals from scratch
        minGoal = minimizeFeature(stateKey(self.jerry.name,'health'),self.jerry.name)
        self.tom.setReward(minGoal,1.)
        self.saveload()
        tRawVal = self.tom.reward(self.world.state)
        self.assertAlmostEqual(jVal,tRawVal,8)
        # Create Tom's goals as a function of Jerry's
        self.tom.models[True]['R'].clear()
        self.tom.setReward(self.jerry.name,-1.)
        self.saveload()
        tFuncVal = self.tom.reward(self.world.state)
        self.assertAlmostEqual(tRawVal,tFuncVal,8)
        # Test effect of functional reward on value function
        self.tom.setHorizon(1)
        self.saveload()
        vHit = self.tom.value(self.world.state,self.hit)['V']
        vChase = self.tom.value(self.world.state,self.chase)['V']
        self.assertAlmostEqual(vHit,vChase+.1,8)

    def DONTtestReward(self):
        self.addStates()
        key = stateKey(self.jerry.name,'health')
        goal = makeTree({'if': thresholdRow(key,5),
                         True: KeyedVector({key: -2}),
                         False: KeyedVector({key: -1})})
        self.jerry.setReward(goal,1.)
        R = self.jerry.models['%s0' % (self.jerry.name)]['R']
        self.assertEqual(len(R),1)
        print(R)
        self.assertEqual(next(iter(R.keys())),goal,'%s != %s' % (str(next(iter(R.keys()))),str(goal)))
        self.assertAlmostEqual(R[goal],1.,8)
        self.jerry.setReward(goal,2.)
        self.assertEqual(len(R),1)
        self.assertEqual(R.keys()[0],goal)
        self.assertAlmostEqual(R[goal],2.,8)

    def DONTtestTurnDynamics(self):
        self.addStates()
        self.addActions()
        self.world.setOrder([self.tom.name,self.jerry.name])
        self.assertEqual(self.world.maxTurn,1)
        self.saveload()
        jTurn = turnKey(self.jerry.name)
        tTurn = turnKey(self.tom.name)
        self.assertEqual(self.world.next(),{self.tom.name})
        dist = self.world.state[tTurn]
        self.assertEqual(len(dist),1)
        self.assertEqual(dist.first(),0)
        dist = self.world.state[jTurn]
        self.assertEqual(len(dist),1)
        self.assertEqual(dist.first(),1)
        self.world.step()
        self.assertEqual(self.world.next(),{self.jerry.name})
        dist = self.world.state[tTurn]
        self.assertEqual(len(dist),1)
        self.assertEqual(dist.first(),1)
        dist = self.world.state[jTurn]
        self.assertEqual(len(dist),1)
        self.assertEqual(dist.first(),0)
        self.world.step()
        self.assertEqual(self.world.next(),{self.tom.name})
        self.assertEqual(self.world.state[tTurn],0)
        self.assertEqual(self.world.state[jTurn],1)
        # Try some custom dynamics
        self.world.setTurnDynamics(self.tom.name,self.hit,makeTree(noChangeMatrix(tTurn)))
        self.world.setTurnDynamics(self.jerry.name,self.hit,makeTree(noChangeMatrix(tTurn)))
        self.world.step()
        self.assertEqual(self.world.next(),[self.tom.name])
        self.assertEqual(self.world.state[tTurn],0)
        self.assertEqual(self.world.state[jTurn],1)
        self.world.step({self.tom.name: self.chase})
        self.assertEqual(self.world.next(),[self.jerry.name])
        self.assertEqual(self.world.state[tTurn],1)
        self.assertEqual(self.world.state[jTurn],0)

    def DONTtestStatic(self):
        self.addStates()
        self.addActions()
        self.addDynamics()
        self.addModels()
#        self.world.setModel(self.jerry.name,True)
        self.world.setOrder([self.tom.name])
        self.world.setMentalModel(self.jerry.name,self.tom.name,{'friend': 0.5,'foe': 0.5})
        model = self.world.getModel(self.jerry.name)
        self.assertEqual(len(model),1)
        model = model.first()
        belief0 = self.jerry.models[model]['beliefs']
        self.world.step()
        model = self.world.getModel(self.jerry.name)
        self.assertEqual(len(model),1)
        model = model.first()
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
        model = self.world.getModel(self.jerry.name)
        self.assertEqual(len(model),1)
        model = model.first()
        belief2 = self.jerry.models[model]['beliefs']
        for vector in belief1.domain():
            self.assertAlmostEqual(belief1[vector],belief2[vector],8)

if __name__ == '__main__':
    unittest.main()
