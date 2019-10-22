import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent
from psychsim.reward import *

    # Create scenario
class Centipede:



    def __init__(self,turnOrder,maxRounds,payoff):

        self.maxRounds=maxRounds
        self.payoff = payoff
        print self.payoff
        self.world = World()
        stacy = Agent('Stacy')
        david = Agent('David')
        agts = [stacy, david]

        # Player state, actions and parameters common to both players
        for i in range(2):
            me = agts[i]
            other = agts[1-i]
            self.world.addAgent(me)
            # State
            self.world.defineState(me.name,'money',int)
            me.setState('money',0)  
            mePass = me.addAction({'verb': 'pass','object': other.name})
            meTake = me.addAction({'verb': 'take','object': other.name})
            # Parameters
            me.setHorizon(6)
            me.setAttribute('discount',1.)
            # me.setAttribute('discount',0.9)
        
            # Levels of belief
        david.setRecursiveLevel(3)
        stacy.setRecursiveLevel(3)

        self.world.setOrder(turnOrder)
        # World state
        self.world.defineState(None,'round',int,description='The current round')
        self.world.setState(None,'round',0)
        self.world.defineState(None,'gameOver',bool,description='whether game is over')
        self.world.setState(None,'gameOver',False)

        self.world.addTermination(makeTree({'if': thresholdRow(stateKey(None,'round'),self.maxRounds),
                                            True: True, 
                                            False: {'if': trueRow(stateKey(None,'gameOver')),
                                                    True: True,
                                                    False: False}}))

        # Dynamics
        for action in stacy.actions | david.actions:
            tree = makeTree(incrementMatrix(stateKey(None,'round'),1))
            self.world.setDynamics(stateKey(None,'round'),action,tree)
            if (action['verb'] == 'take'):
                tree = makeTree(setTrueMatrix(stateKey(None,'gameOver')))
                self.world.setDynamics(stateKey(None,'gameOver'),action,tree)
                agts = ['Stacy','David']
                for i in range(2):
                    key = stateKey(agts[i],'money')
                    tree = makeTree(self.buildPayoff(0, key, self.payoff[agts[i]]))
                    self.world.setDynamics(stateKey(agts[i],'money'),action,tree)
            elif action['verb'] == 'pass':
                agts = ['Stacy','David']
                for i in range(2):
                    key = stateKey(agts[i],'money')
                    tree = makeTree({'if': equalRow(stateKey(None,'round'),self.maxRounds-1),
                                     True: setToConstantMatrix(key,self.payoff[agts[i]][self.maxRounds]),
                                     False: noChangeMatrix(key)})
                    self.world.setDynamics(stateKey(agts[i],'money'),action,tree)
                

# really need to ask david about these levels - if adding modesl with levels, can
# the true model point to these but have a different level

        for agent in self.world.agents.values():
            agent.addModel('Christian',R={},level=2,rationality=10.,selection='distribution')
            agent.addModel('Capitalist',R={},level=2,rationality=10.,selection='distribution')
            # agent.addModel('Christian',R={},level=2,rationality=0.01)
            # agent.addModel('Capitalist',R={},level=2,rationality=0.01)

    def buildPayoff(self,rnd,key,payoff):
        if (rnd == self.maxRounds - 1):
            return setToConstantMatrix(key,payoff[rnd])
        else:
            return {'if': equalRow(stateKey(None,'round'),rnd),
                    True: setToConstantMatrix(key,payoff[rnd]),
                    False: self.buildPayoff(rnd+1,key,payoff)}


    def modeltest(self,trueModels,davidBeliefAboutStacy,stacyBeliefAboutDavid,strongerBelief):
        agts = self.world.agents.values()
        for i in range(2):
            me = agts[i]
            other = agts[1-i]
            for model in me.models.keys():
                if model is True:
                    name = trueModels[me.name]
                else:
                    name = model
                if name == 'Capitalist':
                    me.setReward(maximizeFeature(stateKey(me.name,'money')),1.0,model)
                elif name == 'Christian':
                    me.setReward(maximizeFeature(stateKey(me.name,'money')),1.0,model)
                    me.setReward(maximizeFeature(stateKey(other.name,'money')),1.0,model)

        weakBelief = 1.0 - strongerBelief          
        belief = {'Christian': weakBelief,'Capitalist': weakBelief}
        belief[davidBeliefAboutStacy] = strongerBelief
        self.world.setMentalModel('David','Stacy',belief)
        belief = {'Christian': weakBelief,'Capitalist': weakBelief}
        belief[stacyBeliefAboutDavid] = strongerBelief
        self.world.setMentalModel('Stacy','David',belief)

    def runit(self,Msg):
        print Msg
        for t in range(self.maxRounds + 1):
            self.world.explain(self.world.step(),level=2)
            # self.world.explain(self.world.step(),level=1)
            # print self.world.step()
            #self.world.state.select()
            # self.world.printState()
            if self.world.terminated():
                break        

# Parameters
#           me.setHorizon(6)
#           me.setAttribute('discount',0.9)
# Levels of belief
#        david.setRecursiveLevel(3)
#        stacy.setRecursiveLevel(3)
#        level 2 models
# Rounds
#        self.maxRounds=4
#  
# Rationality = .01

# TEST Runs Scripting

for payoffDict in [{'Stacy': [2,0,3,1,3],
                    'David': [0,2,0,4,3]},
                   {'Stacy': [2,4,3,1,3],
                    'David': [0,2,0,4,3]},
                   {'Stacy': [2,0,3,1,3],
                    'David': [0,1,2,4,3]},
                   {'Stacy': [2,0,1,3,3],
                    'David': [0,2,0,4,3]},
                   {'Stacy': [2,0,1,2,3],
                    'David': [0,2,0,3,4]}]:
    trueModels = {'Stacy': 'Capitalist',
                  'David': 'Capitalist'}
    turnOrder=['Stacy','David']

    # The following tests the dynamics by running through every possible action sequence
    # for length in range(len(payoffDict['Stacy'])):
    #     negagts = Centipede(turnOrder, len(payoffDict['Stacy'])-1, payoffDict)
    #     world = negagts.world
    #     state = world.state
    #     while not world.terminated():
    #         agent = world.agents[negagts.world.next()[0]]
    #         if world.getState(None,'round').expectation() == length:
    #             verb = 'take'
    #         else:
    #             verb = 'pass'
    #         for action in agent.getActions(state):
    #             if action['verb'] == verb:
    #                 break
    #         else:
    #             raise NameError,'Unable to find %s for %s' % (verb,agent.name)
    #         print action
    #         world.step({agent.name: action})
    #     world.printState(state)
    # break
        
    negagts = Centipede(turnOrder, len(payoffDict['Stacy'])-1, payoffDict)
    negagts.modeltest(trueModels,'Capitalist','Capitalist', 1.0)
    negagts.runit("Capitalist and Correct beliefs")

