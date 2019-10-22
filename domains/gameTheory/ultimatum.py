import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent


    # Create scenario


class Ultimatum:

    def __init__(self):
        self.world = World()
        stacy = Agent('Stacy')
        david = Agent('David')
        agts = [stacy, david]
        totalAmt = 4
        # Player state, actions and parameters common to both players
        for i in range(2):
            me = agts[i]
            other = agts[1-i]
            self.world.addAgent(me)
            self.world.defineState(me.name,'offered',int,lo=0,hi=totalAmt)
            self.world.defineState(me.name,'money',int,lo=0,hi=totalAmt)
            me.setState('offered',0)  
            me.setState('money',0)  
            if (me.name == 'Stacy'):
                for amt in range(totalAmt + 1):
                    me.addAction({'verb': 'offer','object': other.name,'amount': amt})
            else:
                mePass = me.addAction({'verb': 'accept','object': other.name})
                mePass = me.addAction({'verb': 'reject','object': other.name})
            # Parameters
            me.setHorizon(2)
            me.setAttribute('discount',0.9)
            # me.setAttribute('discount',1.0)
        
            # Levels of belief
        david.setRecursiveLevel(3)
        stacy.setRecursiveLevel(3)

        self.world.setOrder(['Stacy','David'])

        # World state
        self.world.defineState(None,'gameOver',bool,description='The current round')
        self.world.setState(None,'gameOver',False)

        self.world.addTermination(makeTree({'if': trueRow(stateKey(None,'gameOver')),
                                            True: True, False: False}))
        # offer dynamics
        atom = Action({'subject': 'Stacy','verb': 'offer', 'object': 'David'})
        parties = [atom['subject'], atom['object']]
        for j in range(2):
            offer = stateKey(parties[j],'offered')
            amount = actionKey('amount') if j == 1 else '%d-%s' % (totalAmt,actionKey('amount'))
            tree = makeTree(setToConstantMatrix(offer,amount))
            self.world.setDynamics(parties[j],'offered',atom,tree)
        # accept dynamics
        atom = Action({'subject': 'David','verb': 'accept', 'object': 'Stacy'})
        parties = [atom['subject'], atom['object']]
        for j in range(2):
            offer = stateKey(parties[j],'offered')
            money = stateKey(parties[j],'money')
            tree = makeTree(setToFeatureMatrix(money,offer))
            self.world.setDynamics(parties[j],'money',atom,tree)
        tree=makeTree(setTrueMatrix(stateKey(None,'gameOver')))
        self.world.setDynamics(None,'gameOver',atom,tree)
        # reject dynamics
        atom = Action({'subject': 'David','verb': 'reject', 'object': 'Stacy'})
        tree=makeTree(setTrueMatrix(stateKey(None,'gameOver')))
        self.world.setDynamics(None,'gameOver',atom,tree)

# really need to ask david about these levels - if adding modesl with levels, can
# the true model point to these but have a different level
        for agent in self.world.agents.values():
            agent.addModel('Christian',R={},level=2,rationality=25.,selection='distribution')
            agent.addModel('Capitalist',R={},level=2,rationality=25.,selection='distribution')
            # agent.addModel('Christian',R={},level=2,rationality=10.,selection='distribution')
            # agent.addModel('Capitalist',R={},level=2,rationality=10.,selection='distribution')
            # agent.addModel('Christian',R={},level=2,rationality=10.,selection='distribution')
            # agent.addModel('Capitalist',R={},level=2,rationality=10.,selection='random')



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
        print weakBelief
        belief = {'Christian': weakBelief,'Capitalist': weakBelief}
        belief[davidBeliefAboutStacy] = strongerBelief
        self.world.setMentalModel('David','Stacy',belief)
        belief = {'Christian': weakBelief,'Capitalist': weakBelief}
        belief[stacyBeliefAboutDavid] = strongerBelief
        self.world.setMentalModel('Stacy','David',belief)

    def runit(self,Msg):
        print Msg
        for t in range(2):
            self.world.explain(self.world.step(),level=2)
            # print self.world.step()
            self.world.state.select()
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

payoffDict= {'Stacy': [],
              'David': []}

trueModels = {'Stacy': 'Capitalist',
              'David': 'Capitalist'}
turnOrder=['Stacy','David']
negagts = Ultimatum()
negagts.modeltest(trueModels,'Capitalist','Capitalist', 1.0)
negagts.runit("Capitalist and Correct beliefs")

