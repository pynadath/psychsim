import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent


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
            me.setParameter('discount',0.9)
        
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
            self.world.setDynamics(None,'round',action,tree)
            if (action['verb'] == 'take'):
                tree = makeTree(setTrueMatrix(stateKey(None,'gameOver')))
                self.world.setDynamics(None,'gameOver',action,tree)
                agts = ['Stacy','David']
                for i in range(2):
                    key = stateKey(agts[i],'money')
                    tree = makeTree(self.buildPayoff(0, key, self.payoff[agts[i]]))
                    self.world.setDynamics(agts[i],'money',action,tree)

# really need to ask david about these levels - if adding modesl with levels, can
# the true model point to these but have a different level

        for agent in self.world.agents.values():
            agent.addModel('Christian',R={},level=2,rationality=0.01)
            agent.addModel('Capitalist',R={},level=2,rationality=0.01)

    def buildPayoff(self,round,key,payoff):
        if (round == self.maxRounds - 1):
            return setToConstantMatrix(key,payoff[round])
        else:
            return {'if': equalRow(stateKey(None,'round'),round),
                    True: setToConstantMatrix(key,payoff[round]),
                    False: self.buildPayoff(round+1,key,payoff)}


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

payoffDict= {'Stacy': [2,3,4,1],
              'David': [1,1,3,1]}

trueModels = {'Stacy': 'Capitalist',
              'David': 'Capitalist'}
turnOrder=['Stacy','David']
negagts = Centipede(turnOrder, 4, payoffDict)
negagts.modeltest(trueModels,'Capitalist','Capitalist', 1.0)
negagts.runit("Capitalist and Correct beliefs")

