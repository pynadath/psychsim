from xml.dom.minidom import parseString
from teamwork.math.Keys import WorldKey,ModelKey
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.probability import Distribution
from teamwork.agent.Entities import PsychEntity
from teamwork.multiagent.PsychAgents import loadScenario
from teamwork.multiagent.GenericSociety import GenericSociety
import bz2
import os
import os.path
import sys
import unittest

class TestPWLTable(unittest.TestCase):
    def setUp(self):
        path = os.getcwd()
        name = None
        while name != 'teamwork':
            path,name = os.path.split(path)
        path = os.path.join(path,name,'examples','tiger','tiger.scn')
        self.scenario = loadScenario(path)
        self.scenario.generateWorlds()
        self.scenario.nullPolicy()

    def generateVector(self,probability=False):
        """
        @param probability: if C{True}, then make sure vector values are nonnegative and sum to 1. (default is C{False})
        @type probability: bool
        @return: a random vector
        @rtype: L{KeyedVector}
        """
        import random
        dimension = len(self.scenario.worlds)
        vector = {}
        if probability:
            # Keep track of probability mass
            total = 1.
            # Last value is completely determined by previous n-1
            dimension -= 1
        for world in range(dimension):
            key = WorldKey({'world': world})
            if probability:
                # Assign part of remaining mass
                value = random.random()*total
                total -= value
            else:
                # Assign random number from [-1,1]
                value = random.random()*2. - 1.
            vector[key] = value
        if probability:
            # Add remaining probability mass to final world
            key = WorldKey({'world': dimension})
            vector[key] = total
        return KeyedVector(vector)

    def DONTtestLevel0Estimator(self):
        T = self.scenario.getDynamicsMatrix()
        agent1 = self.scenario['Player 1']
        agent2 = self.scenario['Player 2']
        belief1 = self.scenario.state2world(agent1.entities.state)
        belief2 = self.scenario.state2world(agent2.entities.state)
        SE = self.scenario['Player 1'].getEstimator(self.scenario)
        options = {}
        options[agent2.name],explanation = agent2.applyPolicy(belief2)
        numerators = {}
        for omega in agent1.getOmega():
            numerators[omega] = {}
        for option1 in agent1.actions.getOptions():
            options[agent1.name] = option1
            action1 = agent1.makeActionKey(option1)
            joint = agent1.makeActionKey(options)
            next = T[joint]*belief1
            O = agent1.getObservationMatrix(options,self.scenario.getWorlds())
            for omega in agent1.getOmega():
                numerators[omega][action1] = KeyedVector()
                for world in next.keys():
                    numerators[omega][action1][world] = O[omega][world]*next[world]
        for omega in agent1.getOmega():
            for option1 in agent1.actions.getOptions():
                action1 = agent1.makeActionKey(option1)
                real = numerators[omega][action1]
                real *= 1./sum(real.getArray())
                rule = SE[omega][belief1]
                comp = rule['values'][action1]*belief1
                comp *= 1./sum(comp.getArray())
                self.assertEqual(len(real),len(comp))
                for world in real.keys():
                    self.assertAlmostEqual(real[world],comp[world],8)

    def DONTtestLevel1Estimator(self):
        agent1 = self.scenario['Player 1']
        agent2 = self.scenario['Player 2']
        oldWorlds = {}
        oldLookup = {}
        worlds,lookup = self.scenario.generateWorlds()
        oldWorlds.update(worlds)
        oldLookup.update(lookup)
        T = {}
        T.update(self.scenario.getDynamicsMatrix())
        SE2 = agent2.getEstimator()
        belief2 = self.scenario.state2world(agent2.entities.state)
        R1 = agent1.getRewardTable(self.scenario)
        R2 = agent2.getRewardTable(self.scenario)
        agent1.policy.project(R1,1,0)
        agent2.policy.project(R2,1,0)
        worlds,lookup = self.scenario.generateWorlds(perspective=agent1.name)
        self.verifyWorlds(worlds)
        self.verifyModels(agent2)
        for name,model in agent2.models.items():
            if belief2 == model['beliefs']:
                break
        else:
            self.fail()
        SE1 = agent1.getEstimator()
        belief1 = agent1.entities.state
        self.assertEqual(len(belief1),len(belief2))
        belief1 = Distribution()
        for old in agent1.entities.state.domain():
            new = KeyedVector(old)
            new[ModelKey({'entity': agent2.name})] = model['value']
            belief1[new] = agent1.entities.state[old]
        belief1 = self.scenario.state2world(belief1)
        numerators = {}
        for omega1 in agent1.getOmega():
            numerators[omega1] = {}
        for option1 in agent1.actions.getOptions():
            options = {}
            options[agent1.name] = option1
            action1 = agent1.makeActionKey(option1)
            for omega1 in agent1.getOmega():
                numerators[omega1][action1] = KeyedVector()
                for newKey,newWorld in worlds.items():
                    numerators[omega1][action1][newKey] = 0.
                    newModel = agent2.models[agent2.identifyModel(newWorld)]
                    for oldKey,oldWorld in worlds.items():
                        oldModel = agent2.identifyModel(oldWorld)
                        belief2 = agent2.models[oldModel]['beliefs']
                        options[agent2.name],explanation = agent2.applyPolicy(belief2)
                        joint = agent1.makeActionKey(options)
                        action2 = agent2.makeActionKey(options[agent2.name])
                        prob = belief1[oldKey]
                        prob *= T[joint][oldLookup[oldWorld.getState()]][oldLookup[newWorld.getState()]]
                        O1 = agent1.observe(newWorld.getState(),options)
                        prob *= O1[omega1]
                        O2 = agent2.observe(newWorld.getState(),options)
                        for omega2 in agent2.getOmega():
                            self.assertEqual(len(SE2[omega2].rules),1)
                            newBelief2 = SE2[omega2].rules[0]['values'][action2]*belief2
                            newBelief2 *= 1./sum(newBelief2.getArray())
                            if newModel['beliefs'] == newBelief2:
                                numerators[omega1][action1][newKey] += prob*O2[omega2]
                            else:
                                # Check whether this is closest belief
                                delta = newBelief2-newModel['beliefs']
                                delta = sum(map(abs,delta.getArray()))
                                for model2 in agent2.models.values():
                                    if sum(map(abs,(newBelief2-model2['beliefs']).getArray())) < delta:
                                        break
                                else:
                                    numerators[omega1][action1][newKey] += prob*O2[omega2]
                        print action1
                        print omega1
                        print newWorld.getState()
                        print newModel['beliefs']
                        print numerators[omega1][action1][newKey]
        for omega1 in agent1.getOmega():
            for option1 in agent1.actions.getOptions():
                print belief1,agent1.makeActionKey(option1),omega1
                action1 = agent1.makeActionKey(option1)
                rule = SE1[omega1][belief1]
                comp = rule['values'][action1]*belief1
                comp *= 1./sum(comp.getArray())
                print comp
                real = numerators[omega1][action1]
                real *= 1./sum(real.getArray())
                print real
                self.assertEqual(len(real),len(comp))
                for world in self.scenario.getWorlds().keys():
                    self.assertAlmostEqual(real[world],comp[world],8)

    def testLevel1(self):
        agent1 = self.scenario['Player 1']
        agent2 = self.scenario['Player 2']
        agent1.entities.nullPolicy()
        agent1.entities.generateWorlds()
        R1 = agent1.getRewardTable()
        self.assertEqual(len(R1.rules),1)
        agent2.entities.nullPolicy()
        agent2.entities.generateWorlds()
        R2 = agent2.getRewardTable()
        SE2 = self.scenario['Player 2'].getEstimator()
        agent1.policy.project(depth=1,horizon=0)
        agent2.policy.project(depth=1,horizon=0)
        agent2.entities.generateWorlds()
        agent1.getEntity(agent2.name).estimators.update(SE2)
        worlds,lookup = agent1.entities.generateWorlds(perspective=agent1.name)
        R1 = agent1.getRewardTable()
        agent1.estimators.clear()
        agent1.getEntity(agent2.name).estimators.update(SE2)
        SE1 = agent1.getEstimator()
        for omega,estimator in SE1.items():
            self.assertEqual(len(estimator.rules),1)
            for action,rhs in estimator.rules[0]['values'].items():
                self.assert_(not rhs is None)
        agent1.policy.project(None,2,0)
        agent1.policy.project(None,2,1)
#        agent1.policy.project(None,2,2)
#        agent1.policy.project(None,2,3)
        print agent1.policy.getTable()
        worlds,lookup = self.scenario.generateWorlds()
        print self.scenario.simulate(5)

    def verifyWorlds(self,worlds):
        names = worlds.keys()
        for i in range(len(names)-1):
            worldI = worlds[names[i]]
            for j in range(i+1,len(names)):
                worldJ = worlds[names[j]]
                self.assertEqual(len(worldI),len(worldJ))
                for key in worldI.keys():
                    self.assert_(worldJ.has_key(key))
                    if abs(worldI[key]-worldJ[key]) > 1e-8:
                        break
                else:
                    # Equal across all keys
                    self.fail()

    def verifyModels(self,agent):
        names = agent.models.keys()
        for i in range(len(names)-1):
            modelI = agent.models[names[i]]
            beliefsI = modelI['beliefs']
            for j in range(i+1,len(names)):
                modelJ = agent.models[names[j]]
                self.assertEqual(modelI.keys(),modelJ.keys())
                self.assertEqual(modelI['goals'],modelJ['goals'])
                beliefsJ = modelJ['beliefs']
                self.assertEqual(beliefsI.keys(),beliefsJ.keys())
                for key in beliefsI.keys():
                    if abs(beliefsI[key]-beliefsJ[key]) > 1e-8:
                        break
                else:
                    # Equal across all keys
                    self.fail()

    def DONTtestLevel0results(self):
        agent1 = self.scenario['Player 1']
        agent2 = self.scenario['Player 2']
        belief2 = self.scenario.state2world(agent2.entities.state)
        SE = agent2.getEstimator(self.scenario)
        options = {}
        options[agent2.name],explanation = agent2.applyPolicy(belief2)
        self.assertEqual(len(agent1.policy.tables),1)
        self.assertEqual(len(agent1.policy.tables[0]),1)
        R1 = agent1.getRewardTable(self.scenario)
        R2 = agent2.getRewardTable(self.scenario)
        T = 9
        for horizon in range(T):
            print 'Horizon =',horizon
            agent1.policy.project(R1,1,horizon)
            agent2.policy.project(R2,1,horizon)
            table = agent1.policy.getTable()
            print 'Rules =',len(table.rules)
            print table
            print agent2.policy.getTable()
            sys.stdout.flush()
            total = self.scenario.simulate(T-1)
            print 'ER =',total
            sys.stdout.flush()

        
    def DONTtestLevel0(self):
        agent1 = self.scenario['Player 1']
        agent2 = self.scenario['Player 2']
        belief2 = self.scenario.state2world(agent2.entities.state)
        SE = agent2.getEstimator(self.scenario)
        options = {}
        options[agent2.name],explanation = agent2.applyPolicy(belief2)
        self.assertEqual(len(agent1.policy.tables),1)
        self.assertEqual(len(agent1.policy.tables[0]),1)
        R1 = agent1.getRewardTable(self.scenario)
        agent1.policy.project(R1,1,0)
        self.assertEqual(len(agent1.policy.tables),2)
        self.assertEqual(len(agent1.policy.tables[1]),1)
        table = agent1.policy.getTable()
        for iteration in range(100):
            belief1 = self.generateVector(probability=True)
            rule = table[belief1]
            best1 = agent1.makeActionKey(rule['rhs'])
            values = []
            Vstar = None
            for options[agent1.name] in agent1.actions.getOptions():
                action1 = agent1.makeActionKey(options[agent1.name])
                EV = R1[belief1]['values'][action1]*belief1
                if action1 == best1:
                    Vstar = EV
                values.append(EV)
                computed = rule['values'][action1]*belief1
                self.assertAlmostEqual(EV,computed,8)
            self.assertFalse(Vstar is None)
            self.assertAlmostEqual(Vstar,max(values))
        SE = agent1.getEstimator(self.scenario)
##        T = 6
##        for horizon in range(1,T):
##             agent1.policy.project(R1,1,horizon)
##        for horizon in range(T):
##             agent2.policy.project(R2,1,horizon)
##        print self.scenario.simulate(T-1)
#             print agent1.policy.getTable()

    def verifyEqual(self,t1,t2):
        self.assertEqual(len(t1.rules),len(t2.rules))
        for rule1 in t1.rules:
            for rule2 in t2.rules:
                if rule1['lhs'] == rule2['lhs']:
                    V1 = rule1['values']
                    V2 = rule2['values']
                    self.assertEqual(len(V1),len(V2))
                    for action in V1.keys():
                        self.assert_(V2.has_key(action))
                        self.assertEqual(len(V1[action]),len(V2[action]))
                        for world,value1 in V1[action].items():
                            self.assert_(V2[action].has_key(world))
                            self.assertAlmostEqual(value1,V2[action][world])
                    break
            else:
                self.fail('No matching rule for %s' % (rule1['lhs']))

if __name__ == '__main__':
    unittest.main()
