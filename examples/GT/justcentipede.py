import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent


    # Create scenario
class Centipede:



    def __init__(self,turnOrder,maxRounds,payoyff):

        self.maxRounds=maxRounds
        self.payoff = payoff
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
            mePass = me.addAction({'verb': 'pass','object': other.name})
            meTake = me.addAction({'verb': 'take','object': other.name})
            # Parameters
            me.setHorizon(6)
            me.setParameter('discount',0.9)
        
            # Levels of belief
        david.setRecursiveLevel(3)
        stacy.setRecursiveLevel(3)

        self.world.setOrder(turnOrder)

        # World state
        self.world.defineState(None,'round',int,description='The current round')
        self.world.setState(None,'round',0)

        self.world.addTermination(makeTree({'if': thresholdRow(stateKey(None,'round'),self.maxRounds),
                                   True: True, False: False}))

        # Dynamics
        for action in stacy.actions | david.actions:
            tree = makeTree(incrementMatrix(stateKey(None,'round'),1))
            self.world.setDynamics(None,'round',action,tree)
            if (action['verb'] == 'take'):
                tree = makeTree(setTrueMatrix(stateKey(None,'agreement')))
                self.world.setDynamics(None,'agreement',action,tree)
                tree = buildPayoff(self.maxRounds, payoff[action['subject']])
                self.world.setDynamics(action['subject'],'money',action,tree)
                tree = buildPayoff(self.maxRounds, payoff[action['object']])
                self.world.setDynamics(action['object'],'money',action,tree)

# really need to ask david about these levels - if adding modesl with levels, can
# the true model point to these but have a different level

        for agent in self.world.agents.values():
            agent.addModel('Christian',R={},level=2,rationality=0.01)
            agent.addModel('Capitalist',R={},level=2,rationality=0.01)

    def buildPayoff(round,key):
        if (round == self.maxRound):
            return maketree(setToConstant(key,self.payoff[round]))
        else:
            return {'if': equalRow(stateKey(None,'round'),round)
                    True: maketree(setToConstant(key,self.payoff[round])),
                    False: buildPayoff(round+1,key)}


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
                    me.setReward(maximizeFeature(stateKey(agent.name,'money')),1.0,model)
                elif name == 'Christian':
                    me.setReward(maximizeFeature(stateKey(agent.name,'money')),1.0,model)
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
            self.world.explain(self.world.step(),level=1)
            # print self.world.step()
            self.world.state.select()
            # self.world.printState()
            if self.world.terminated():
                break        

# Parameters
#           me.setHorizon(6)
#           me.setParameter('discount',0.9)
# Levels of belief
#        david.setRecursiveLevel(3)
#        stacy.setRecursiveLevel(3)
#        level 2 models
# Rounds
#        self.maxRounds=4
#  
# Rationality = .01

# TEST Runs Scripting

payoffDict= {'Stacy': [],
              'David': []}

trueModels = {'Stacy': 'Capitalist',
              'David': 'Capitalist'}
turnOrder=['Stacy','David']
negagts = Centipede(turnOrder, 4, payoffDict)
negagts.modeltest(trueModels,'Capitalist','Christian', 1.0)
negagts.runit("Capitalist and Correct beliefs")

