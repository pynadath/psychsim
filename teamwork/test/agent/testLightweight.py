import bz2
import hotshot,hotshot.stats
import random
from teamwork.agent.Entities import PsychEntity
from teamwork.multiagent.PsychAgents import PsychAgents
from teamwork.multiagent.GenericSociety import GenericSociety
from teamwork.multiagent.pwlSimulation import PWLSimulation
from teamwork.agent.lightweight import PWLAgent
from teamwork.examples.TigerScenario import *
from teamwork.policy.pwlTable import PWLTable
from teamwork.policy.pwlPolicy import PWLPolicy

import unittest
import hotshot,hotshot.stats

# The following is needed to raise an exception for division by zero
# for some versions of Numeric Python
try:
    from numpy import seterr
    seterr(divide='raise')
except ImportError:
    pass

class probabilityIterator:
    def __init__(self,vector,factor=0.001,update='additive',epsilon=1e-8):
        self.value = copy.copy(vector)
        if update == 'multiplicative':
            self.value.getArray()[0] = 0.5
        else:
            self.value.getArray()[0] = 0.
        self.value.getArray()[1] = 1. - self.value.getArray()[0]
        self.factor = factor
        self.update = update
        self.epsilon = epsilon
        self.first = True

    def __iter__(self):
        return self

    def next(self):
        if self.first:
            self.first = False
            return self.value
        else:
            original = self.value.getArray()[0]
            if self.update == 'multiplicative':
                if original + self.epsilon >  0.5:
                    next = self.factor*(1.-original)
                    if next < self.epsilon:
                        raise StopIteration
                else:
                    next = 1. - original
            else:
                next = original + self.factor
                if next > 1.:
                    raise StopIteration
            self.value.getArray()[0] = next
            self.value.getArray()[1] = 1. - self.value.getArray()[0]
            return copy.copy(self.value)
            
class TestPWLAgent(unittest.TestCase):
    """Uses the tiger scenario to test PWL policy generation
    """
    profile = False
    
    
    def setUp(self):
        """Creates the instantiated scenario used for testing"""
        society = GenericSociety()
        society.importDict(classHierarchy)
        # Instantiate scenario
        agents = []
        agents.append(society.instantiate('Tiger','Tiger',PsychEntity))
        agents.append(society.instantiate('Dude','Player 1',PsychEntity))
        agents.append(society.instantiate('Dude','Player 2',PsychEntity))
        self.full = PsychAgents(agents)
        self.full.applyDefaults()
        # Make into PWL agents
        self.scenario = PWLSimulation(self.full)
        state = self.scenario.getState()
        # Initialize dynamics
        keyList = self.scenario.state.domain()[0].keys()
        keyList.sort()
        actions = {}
        for act1 in self.scenario['Player 1'].actions.getOptions():
            actions['Player 1'] = act1
            for act2 in self.scenario['Player 2'].actions.getOptions():
                actions['Player 2'] = act2
                actionKey = ' '.join(map(str,actions.values()))
                if act1[0]['type'] == 'Listen' and act2[0]['type'] == 'Listen':
                    dynamics = self.full.getDynamics({'Player 1':act1})
                elif act1[0]['type'] != 'Listen':
                    dynamics = self.full.getDynamics({'Player 1':act1})
                else:
                    dynamics = self.full.getDynamics({'Player 2':act2})
                tree = dynamics['state'].getTree()
                tree.unfreeze()
                tree.fill(keyList)
                tree.freeze()
                dynamics['state'].args['tree'] = tree
                self.full.dynamics[actionKey] = dynamics
        self.frozen = True
        # Find reachable worlds at 0-level
        self.worlds,self.lookup = self.full.generateWorlds()
        total = 0
        for world,state in self.worlds.items():
            self.assert_(isinstance(world,WorldKey))
            self.assert_(world['world'] == 0 or world['world'] == 1)
            key = StateKey({'entity':'Tiger','feature':'position'})
            self.assertAlmostEqual(state[key],float(world['world']),3)
            total += world['world']
        self.assertEqual(total,1)
        for name in ['Player 1','Player 2']:
            self.scenario[name].beliefs = KeyedVector()
            for key,world in self.worlds.items():
                self.scenario[name].beliefs[key] = self.scenario.state[world]
        state = KeyedVector()
        for key,world in self.worlds.items():
            state[key] = self.scenario.state[world]
        self.scenario.state = state
        self.transition = self.full.getDynamicsMatrix(self.worlds,self.lookup)
        self.reward = {}
        self.observations = {}
        for actions in self.full.generateActions():
            actionKey = ' '.join(map(str,actions.values()))
            # Transform reward function into matrix representation
            tree = rewardDict[actions.values()[0][0]['type']+\
                              actions.values()[1][0]['type']]
            vector = KeyedVector()
            for key,world in self.worlds.items():
                vector[key] = tree[world]
            vector.freeze()
            self.reward[actionKey] = vector
            # Transform observation probability into matrix representation
            tree = observationDict[actions.values()[0][0]['type']+\
                                   actions.values()[1][0]['type']]
            matrix = KeyedMatrix()
            for colKey,world in self.worlds.items():
                new = tree[world]*world
                for vector,prob in new.items():
                    for omega in Omega.values():
                        if vector[omega] > 0.5:
                            matrix.set(omega,colKey,prob)
            matrix.freeze()
            self.observations[actionKey] = matrix
        # Seed policies with a very naive one --- best joint action
        self.best = {'key':None,'value':None}
        for key,vector in self.reward.items():
            value = vector*state
            if self.best['key'] is None or value > self.best['value']:
                self.best['key'] = key
                self.best['value'] = value
        for actions in self.full.generateActions():
            if self.best['key'] == ' '.join(map(str,actions.values())):
                self.best['action'] = actions
                break
        else:
            raise UserWarning,'Unknown joint action: %s' % (self.best['key'])
        # Set up null policy
        for name,option in self.best['action'].items():
            self.scenario[name].policy = PWLPolicy(self.scenario[name])
            table = PWLTable()
            table.rules = {0:option}
            table.values = {0:{}}
            actions = copy.copy(self.best['action'])
            for alternative in self.scenario[name].actions.getOptions():
                actions[name] = alternative
                actionKey = ' '.join(map(str,actions.values()))
                value = self.reward[actionKey]
                table.values[0][str(alternative)] = value
            self.scenario[name].policy.tables.append([table])

    def generateState(self):
        """
        @return: a random state vector for the scenario of interest
        @rtype: L{KeyedVector}
        """
        state = copy.copy(self.scenario.state)
        key = state.keys()
        state.getArray()[0] = random.random()
        state.getArray()[1] = 1. - state.getArray()[0]
        return state

    def testEstimator(self):
        agent = self.scenario['Player 1']
        other = self.scenario['Player 2']
        # Check that initial beliefs are correct
        for world in self.worlds.keys():
            self.assertAlmostEqual(agent.beliefs[world],0.5,3)
        agent.setEstimator(self.transition,self.observations)
        yrOption,exp = other.policy.execute()
        self.assertEqual(len(yrOption),1)
        self.assertEqual(yrOption[0]['actor'],other.name)
        self.assertEqual(yrOption[0]['type'],'Listen')
        self.assertEqual(yrOption[0]['object'],None)
        actions = {other.name: yrOption}
        self.verifyEstimator(agent,actions)
            
    def verifyEstimator(self,agent,actions):
        for myOption in agent.actions.getOptions():
            actions[agent.name] = myOption
            actionKey = ' '.join(map(str,actions.values()))
            for omega in self.observations[actionKey].keys():
                beliefs = agent.stateEstimator(agent.beliefs,myOption,omega)
                normalization = 0.
                for world,prob in agent.beliefs.items():
                    normalization += prob*self.observations[actionKey][omega][world]
                for world,prob in beliefs.items():
                    new = agent.beliefs[world]*self.observations[actionKey][omega][world]/normalization
                    self.assertAlmostEqual(prob,new,3)

    def testProject(self):
        agent = self.scenario['Player 1']
        other = self.scenario['Player 2']
        # R
        R = other.policy.getTable()
        for index in range(len(R)):
            yrAction = other.policy.getTable().rules[index]
            R.values[index].clear()
            for myAction in agent.actions.getOptions():
                actions = {agent.name:myAction,
                           other.name:yrAction} 
                actionKey = ' '.join(map(str,actions.values()))
                R.values[index][str(myAction)] = copy.copy(self.reward[actionKey])
        # SE
        agent.setEstimator(self.transition,self.observations)
        other.setEstimator(self.transition,self.observations)
        # Horizon = 0
        V = R.getTable()
        V.rules.clear()
        self.verifyPolicy(V)
        policy = V.max()
        self.verifyMax(V,policy)
        self.verifyPolicy(policy)
        agent.policy.project(R,depth=1)
        self.verifyPolicy()
        print 'Horizon: 0'
        print agent.policy.getTable()
        table = agent.policy.getTable()
        self.verifyPrune(table)
        for horizon in range(1,8):
            print 'Horizon:',horizon
            self.deepVerify(R)
            if horizon == 7:
                prof = hotshot.Profile("tiger%d.prof" % (horizon))
                prof.start()
            start = time.time()
            agent.policy.project(R,depth=1)
            print time.time()-start
            if horizon == 7:
                prof.stop()
                prof.close()
                stats = hotshot.stats.load("tiger%d.prof" % (horizon))
                stats.strip_dirs()
                stats.sort_stats('time', 'calls')
                stats.print_stats(20)
            policy = agent.policy.getTable()
            print 'Rules:',len(policy.rules)
            self.verifyPolicy()
            policy.prune(rulesOnly=True)
            print policy

    def deepVerify(self,R):
        agent = self.scenario['Player 1']
        other = self.scenario['Player 2']
        previous = agent.policy.getTable()
        # Compute new value function: V_a(b) = R(a,b) + ...
        V = R.getTable()
        Vstar = previous.star()
        self.verifyStar(Vstar,previous)
        old = Vstar.getTable()
        Vstar.prune()
        self.verifyStar(Vstar,previous)
        self.verifyPrune(Vstar,old)
        for omega,SE in agent.estimators.items():
            # ... + \sum_\omega V^*(SE_a(b,\omega))
            product = Vstar.__mul__(SE,debug=True)
##             product.prune(debug=False)
            self.verifyProduct(Vstar,omega,product)
            Vnew = V.__add__(product,debug=False)
            self.verifySum(V,product,Vnew)
            Vnew.prune()
            self.verifySum(V,product,Vnew)
            V = Vnew
        self.verifyPrune(V,inspect='values')
        self.verifyPolicy(V,Vstar)
        policy = V.max()
        self.verifyMax(V,policy)
        self.verifyPolicy(policy,Vstar)
        old = policy.getTable()
        policy.pruneAttributes()
        self.verifyPrune(policy,old)
        self.verifyPolicy(policy,Vstar)

    def verifyMax(self,raw,maxed):
        for beliefs in probabilityIterator(self.scenario.state):
            # Find rules that trigger
            rawIndex = raw.index(beliefs)
            self.assert_(raw.values.has_key(rawIndex))
            maxIndex = maxed.index(beliefs)
            self.assert_(maxed.rules.has_key(maxIndex),'Missing: (%d) %s' % (maxIndex,maxed.factorString(maxIndex)))
            self.assert_(maxed.values.has_key(maxIndex))
            # Iterate through actions
            best = None
            for option,V in raw.values[rawIndex].items():
                value = V*beliefs
                if best is None or value > best:
                    best = value
                self.assert_(maxed.values[maxIndex].has_key(option))
                maxValue = maxed.values[maxIndex][option]
                self.failUnlessEqual(V,maxValue,'Failed on rule %d\n%s' % \
                                         (rawIndex,maxed.index2factored(maxIndex)))
            option = maxed.rules[maxIndex]
            value = maxed.values[maxIndex][option]*beliefs
            self.assertAlmostEqual(best,value,5,
                                   'Failed on rule %d (%f vs. %f)' % (rawIndex,best,value))

    def verifyPolicy(self,policy=None,Vstar=None,debug=False):
        agent = self.scenario['Player 1']
        other = self.scenario['Player 2']
        yrOption,exp = other.policy.execute()
        if policy is None:
            policy = agent.policy.tables[-1][-1]
        if Vstar is None and len(agent.policy.tables[-1]) > 1:
            Vstar = agent.policy.tables[-1][-2].star()
            Vstar.prune()
        for beliefs in probabilityIterator(self.scenario.state):
            index = policy.index(beliefs)
            actions = {other.name:yrOption}
            best = None
            results = {}
            for option in agent.actions.getOptions():
                actions[agent.name] = option
                actionKey = ' '.join(map(str,actions.values()))
                results[str(option)] = self.reward[actionKey]*beliefs
                if Vstar:
                    # Project next time step
                    partial = {}
                    newState = self.transition[actionKey]*beliefs
                    for omega,O in self.observations[actionKey].items():
                        prob = O*newState
                        newBeliefs = agent.stateEstimator(beliefs,option,omega)
                        projection = Vstar[newBeliefs]*newBeliefs
                        results[str(option)] += prob*projection
                        partial[str(omega)] = {'probability':prob,
                                               'state':newState.getArray(),
                                               'beliefs':newBeliefs.getArray(),
                                               'value': projection,
                                               'V': Vstar[newBeliefs].getArray(),
                                               }
                if policy.values.has_key(index):
                    # Checking value function
                    value = policy.values[index][str(option)]*beliefs
                    self.assertAlmostEqual(value,results[str(option)],3)
            if policy.rules.has_key(index):
                best = str(policy[beliefs])
                for option,value in results.items():
                    self.failIf(results[best]+1e-10 < value)

    def verifySum(self,A,B,total):
        agent = self.scenario['Player 1']
        for index,table in total.values.items():
            for option in agent.actions.getOptions():
                self.assert_(table.has_key(str(option)),
                             'Only %d entries' % (len(table)))
        for beliefs in probabilityIterator(self.scenario.state):
            for option in agent.actions.getOptions():
                index = A.index(beliefs)
                realValue = A.values[index][str(option)]*beliefs
                index = B.index(beliefs)
                realValue += B.values[index][str(option)]*beliefs
                index = total.index(beliefs)
                testValue = total.values[index][str(option)]*beliefs
                self.assertAlmostEqual(realValue,testValue,5)
                
    def verifyProduct(self,V,omega,product,debug=False):
        agent = self.scenario['Player 1']
        other = self.scenario['Player 2']
        yrOption,exp = other.policy.execute()
        actions = {other.name:yrOption}
        for index,table in product.values.items():
            for option in agent.actions.getOptions():
                if not table.has_key(str(option)):
                    print 'Rule %d missing %s' % (index,str(option))
                    factors = product.index2factored(index)
                    for i in range(len(product.attributes)):
                        print product.attributes[i][0].getArray(),bool(factors[i])
                self.assert_(table.has_key(str(option)))
        for beliefs in probabilityIterator(self.scenario.state):
            self.assertAlmostEqual(sum(beliefs.getArray()),1.,5)
            if debug:
                print 'Beliefs:',beliefs.getArray(),omega
            beliefs.getArray()[0] = 0.5
            beliefs.getArray()[1] = 0.5
            index = product.index(beliefs)
            if debug:
                for attr in product.attributes:
                    print '\t',attr[0].getArray()
                print product.index2factored(index)
            self.assert_(product.values.has_key(index))
            for myOption in agent.actions.getOptions():
                self.assert_(product.values[index].has_key(str(myOption)))
                rhs = product.values[index][str(myOption)]
                value =  rhs*beliefs
                # Compute value from first principles
                actions[agent.name] = myOption
                actionKey = ' '.join(map(str,actions.values()))
                new = copy.copy(beliefs)
                for oldWorld in new.keys():
                    new[oldWorld] = 0.
                for oldWorld,oldProb in beliefs.items():
                    for newWorld in new.keys():
                        newProb = oldProb*self.transition[actionKey][newWorld][oldWorld]*self.observations[actionKey][omega][newWorld]
                        new[newWorld] += newProb
                normalization = sum(new.getArray())
                for world,prob in new.items():
                    new[world] = prob/normalization
                # Compute value at next time step
                real = V[new]*new
                # Compute probability of receiving observation
                obs = self.observations[actionKey][omega]*beliefs
                real *= obs
                if debug:
                    print 'New:',new.getArray()
                    print 'V0:',V[new].getArray()
                    print 'V0(b):',V[new]*new
                    print 'O:',obs
                    print 'Real:',real
                    print 'Computed RHS:',rhs.getArray()
                    print 'Computed Product:',value
                self.assertAlmostEqual(value,real,5)
        
    def verifyStar(self,star,old):
        for beliefs in probabilityIterator(self.scenario.state):
            myReward = star[beliefs]*beliefs
            index = old.index(beliefs)
            for option,value in old.values[index].items():
                self.failIf(value*beliefs > myReward+0.000001)

    def verifyPrune(self,table,old=None,inspect='rules'):
        missing = {}
        if inspect == 'values':
            keyList = table.values.keys()
        else:
            keyList = table.rules.keys()
        for index in keyList:
            missing[index] = True
        for beliefs in probabilityIterator(self.scenario.state):
            if self._verifyPrune(table,beliefs,missing,old,inspect):
                break
        else:
            for beliefs in probabilityIterator(self.scenario.state,factor=0.5,update='multiplicative'):
                if self._verifyPrune(table,beliefs,missing,old,inspect):
                    break
            else:
                for rule in missing.keys():
                    print table.factorString(rule)
                self.fail('Able to hit only %d/%d rules' % \
                          (len(keyList)-len(missing),len(keyList)))

    def _verifyPrune(self,table,beliefs,missing,old=None,inspect='rules'):
        index = table.index(beliefs)
        if inspect == 'values':
            self.assert_(table.values.has_key(index)) 
        else:
            self.assert_(table.rules.has_key(index))
        if missing.has_key(index):
            del missing[index]
            if len(missing) == 0:
                return True
        if old:
            if inspect == 'values':
                self.assertEqual(table.values[index],
                                 old.values[old.index(beliefs)])
            else:
                self.assertEqual(table.rules[index],
                                 old.rules[old.index(beliefs)])
        return False
        
    def DONTtestXML(self):
        for agent in self.scenario.members():
            doc = agent.__xml__()
            agent = PWLAgent()
            agent.parse(doc.documentElement)
            self.assertEqual(agent.name,agent.name)
            self.assertEqual(agent.beliefs,agent.beliefs)
            self.assertEqual(len(agent.dynamics.keys()),
                             len(agent.dynamics.keys()))
            for action in agent.dynamics.keys():
                self.assert_(agent.dynamics.has_key(action))
                self.assertEqual(agent.dynamics[action],
                                 agent.dynamics[action])
        
if __name__ == '__main__':
    unittest.main()
