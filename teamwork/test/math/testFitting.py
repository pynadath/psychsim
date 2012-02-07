from teamwork.agent.Entities import *
from teamwork.action.PsychActions import *
from teamwork.multiagent.GenericSociety import *
from teamwork.multiagent.sequential import *
from teamwork.reward.MinMaxGoal import *
from teamwork.examples.InfoShare.PortClasses import *

from teamwork.math.Keys import *
from teamwork.math.fitting import *

import copy
import unittest

class TestFitting(unittest.TestCase):
    debug = None
    increment = 0.25
    
    def setUp(self):
        """Creates the instantiated scenario used for testing"""
        society = GenericSociety()
        society.importDict(classHierarchy)
        entities = []
        self.instances = {'FirstResponder':['FirstResponder'],
                          'World':['World'],
                          'FederalAuthority':['FederalAuthority'],
                          'Shipper':['Shipper'],
                          }
        for cls,names in self.instances.items():
            for name in names:
                entity = society.instantiateEntity(cls,name)
                entities.append(entity)
        self.entities = SequentialAgents(entities)
        self.entities.applyDefaults()
        self.entities.compileDynamics()
        
        self.entity = self.entities['FirstResponder']
        for action in self.entity.actions.getOptions():
            if action[0]['type'] == 'inspect':
                break
        else:
            self.fail('No inspect action found')
        self.action = action
        self.order = self.entity.policy.getSequence(self.entity)
##        self.order = self.entity.entities.keyOrder[:]
##        self.order.remove([self.entity.name])
##        self.order.insert(0,[self.entity.name])

        self.features = {self.entity.name:{'waitTime':1,
                                           'reputation':1,
                                           },
                         'Shipper':{'containerDanger':1,
                                    },
                         'FederalAuthority':{},
                         'World':{'socialWelfare':1,
                                  },
                         }
        self.keys = []
        for entity,features in self.features.items():
            for feature in features.keys():
                self.keys.append(StateKey({'entity':entity,
                                           'feature':feature}))
        
    def generateFirstState(self):
        state = KeyedVector({keyConstant:1.})
        for key in self.keys:
            count = self.features[key['entity']][key['feature']]
            if count == 1:
                state[key] = 0.5
            else:
                state[key] = 0.
        return state
    
    def generateNextState(self,state):
        for key in self.keys:
            count = self.features[key['entity']][key['feature']]
            if count > 1:
                if state.has_key(key):
                    if state[key] < float(count)*self.increment:
                        state[key] += self.increment
                        break
                    else:
                        state[key] = 0.
                else:
                    state[key] = self.increment
                    break
        else:
            return None
        return state
    
    def generateLoop(self,cmd):
        # Loop through possible states to test values
        done = {}
        state = self.generateFirstState()
        while state:
            for key in self.keys:
                try:
                    value = state[key]
                except KeyError:
                    value = 0.
                self.entity.setRecursiveBelief(key['entity'],key['feature'],
                                               value)
            # Execute state
            cmd(state)
            state = self.generateNextState(state)

    def verifyDynamics(self,state,tree,action):
        """Verifies that the given dynamics tree

        Checks that the result of applying the tree in the given state
        produces the same result as directly applying the action to
        the entity (using the performAct method)"""
        # Apply the dynamics tree
        delta = tree[state]*state
        state += delta
        # Apply the action
        self.entity.entities.performAct({self.entity.name:action})
        self.checkState(state)

    def checkState(self,state):
        """Verifies that the state vector is the same as the real state"""
        for key in self.keys:
            try:
                value = state[key]
            except KeyError:
                value = 0.
            if isinstance(key,StateKey):
                real = self.entity.getBelief(key['entity'],
                                             key['feature'])
                msg = '%s:\n%f != %f' % \
                      (key.simpleText(),real,value)
                self.assertAlmostEqual(float(real),value,5,msg)

    def DONTtestGetKeys(self):
        keyList = getActionKeys(self.entity,self.order)
        self.assertEqual(keyList,[])
            
    def testExpandPolicy(self):
        """Tests the expansion of an entity's lookup policy tree"""
        keyList = [] # getActionKeys(self.entity,self.order)
        for turn in self.order:
            for name in turn:
                if name != self.entity.name:
                    policy = expandPolicy(self.entity,name,keyList)
                    entity = self.entity.getEntity(name)
                    self.generateLoop(lambda state,s=self,e=entity,p=policy:\
                                      s.verifyPolicyEffect(e,state,p))

    def verifyPolicyEffect(self,entity,state,policy):
        """Verifies the PWL policy in the given state"""
        act,exp = entity.applyPolicy()
        state += policy[state]*state
        self.entity.entities.performAct({entity.name:act})
        self.checkState(state)
        
    def testGetLookahead(self):
        """Tests the decision-tree compilation of the lookahead delta"""
        entity = self.entity
        for action in entity.actions.getOptions():
            # Loop through each action
            length = len(self.order)
            result = getLookaheadTree(entity,action,
                                      self.order[:length])
            self.generateLoop(lambda state,s=self,t=result['transition'],
                              a=action,l=length:\
                              s.verifyLookahead(state,t,a,l))

    def verifyLookahead(self,state,tree,action,length):
        "Verifies the given lookahead (delta only) tree"""
        # Apply the delta tree
        state = tree[state]*state
        # Explicit simulation of lookahead
        for t in range(length):
            if t == 0:
                self.entity.entities.performAct({self.entity.name:action})
            else:
                result = self.entity.entities.microstep()
                self.assertEqual(self.order[t],result['decision'].keys())
        self.checkState(state)

    def testValueTree(self):
        """Tests the expected value decision tree"""
        # Check the basic goal vector
        # (should probably be in different test case)
        goals = self.entity.getGoalTree()
        realValue = self.entity.applyGoals()
        state = self.entities.getState()
        self.assertAlmostEqual(float(goals[state]*state),float(realValue),5)
        # Check expected value tree
        for action in self.entity.actions.getOptions():
            tree = self.entity.policy.getValueTree(action)
            self.generateLoop(lambda state,s=self,t=tree,a=action:\
                              s.verifyValue(state,t,a))

    def verifyValue(self,state,tree,action):
        """Verifies the PWL expected reward calculation in the given state"""
        # Apply the delta tree
        value = (tree[state]*state)
        # Explicit simulation of lookahead
        total,exp = self.entity.actionValue(action,len(self.order))
        self.assertAlmostEqual(value,float(total),5)

    def verifyPolicy(self,entity,state,policy):
        """Verifies the PWL policy in the given state"""
        act,exp = entity.applyPolicy()
        self.assertEqual(act,policy[state])
        
    def testBuildPolicy(self):
        """Test compilation of lookahead into decision tree"""
        policy = self.entity.policy.buildPolicy()
        self.generateLoop(lambda state,s=self,p=policy:\
                          s.verifyPolicy(s.entity,state,p))
        
    def DONTtestFindAll(self):
        """Tests the fitting procedure"""
        for desired in self.entity.actions.getOptions():
            act,exp = self.entity.applyPolicy()
            constraints = findAllConstraints(self.entity,desired,self.order)
            if act == desired:
                # Desired action already preferred
                self.assertEqual(len(constraints),1)
                constraint = constraints[0]
                self.assertEqual(constraint['slope'],{})
                self.assertEqual(constraint['solution'],{})
            else:
                # Must fit to desired action
                for constraint in constraints:
                    for goal in self.entity.getGoals():
                        try:
                            slope = constraint['slope'][goal.toKey()]
                        except KeyError:
                            continue
                        weight = self.entity.getGoalWeight(goal)
                        try:
                            delta = -constraint['delta']/slope - epsilon
                        except ZeroDivisionError:
                            continue
                        change = None
                        if (slope > 0. and goal.isMax()) or \
                               (slope < 0. and not goal.isMax()):
                            if weight + delta < Interval.CEILING:
                                new = weight+delta
                                change = 1
                            else:
                                continue
                        elif (slope < 0. and goal.isMax()) or \
                                 (slope > 0. and not goal.isMax()):
                            if weight > delta:
                                new = weight-delta
                                change = 1
                            else:
                                continue

                        self.entity.setGoalWeight(goal,new)
                        act,exp = self.entity.applyPolicy()
                        self.assertEqual(act,desired)
                        self.entity.setGoalWeight(goal,weight)
        
if __name__ == '__main__':
    unittest.main()
