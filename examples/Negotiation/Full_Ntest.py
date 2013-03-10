import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent


    # Create scenario
class Negotiate:



    def __init__(self,turnOrder):

        self.maxRounds=8
        self.world = World()
        totals = {'apple':1,'pear':2} 
        batna_prePref = totals['apple'] + totals['pear']
        stacy = Agent('Stacy')
        david = Agent('David')
        agts = [stacy, david]

        # Player state, actions and parameters common to both players
        for i in range(2):
            me = agts[i]
            other = agts[1-i]
            self.world.addAgent(me)
            # State
            self.world.defineState(me.name,'appleOwned',int,lo=0,hi=totals['apple'])
            me.setState('appleOwned',0)
            self.world.defineState(me.name,'appleOffered',int,lo=0,hi=totals['apple'])
            me.setState('appleOffered',0)  
            self.world.defineState(me.name,'pearOwned',int,lo=0,hi=totals['pear'])
            me.setState('pearOwned',0)
            self.world.defineState(me.name,'pearOffered',int,lo=0,hi=totals['pear'])
            me.setState('pearOffered',0)  

            self.world.defineState(me.name,'Batna',int,lo=0,hi=10)
            me.setState('Batna', batna_prePref)
            self.world.defineState(me.name,'BatnaOwned',int,lo=0,hi=10)
            me.setState('BatnaOwned',0)  

            self.world.defineState(me.name,'agree',bool)
            me.setState('agree',False)  
            # Actions
            me.addAction({'verb': 'do nothing'})
            for amt in range(totals['apple'] + 1):
                tmp = me.addAction({'verb': 'offerApple','object': other.name,'amount': amt})
                me.setLegal(tmp,makeTree({'if': trueRow(stateKey(None, 'agreement')),
                                          False: {'if': trueRow(stateKey(None, 'rejectedNegotiation')),
                                                  True: False,
                                                  False: True},
                                          True: False}))


            for amt in range(totals['pear'] + 1):
                tmp = me.addAction({'verb': 'offerPear','object': other.name,'amount': amt})
                me.setLegal(tmp,makeTree({'if': trueRow(stateKey(None, 'agreement')),
                                          False: {'if': trueRow(stateKey(None, 'rejectedNegotiation')),
                                                  True: False,
                                                  False: True},
                                          True: False}))

            meReject = me.addAction({'verb': 'rejectNegotiation','object': other.name})
            me.setLegal(meReject,makeTree({'if': trueRow(stateKey(None, 'agreement')),
                                           False: {'if': trueRow(stateKey(None, 'rejectedNegotiation')),
                                                   True: False,
                                                   False: True},
                                           True: False}))

            meAccept = me.addAction({'verb': 'accept offer','object': other.name})
            me.setLegal(meAccept,makeTree({'if': trueRow(stateKey(None, 'appleOffer')),
                                           True: {'if': trueRow(stateKey(None, 'pearOffer')),
                                                  True: {'if': trueRow(stateKey(None, 'agreement')),
                                                         False: {'if': trueRow(stateKey(None, 'rejectedNegotiation')),
                                                                 True: False,
                                                                 False: True},
                                                         True: False},
                                                  False: False},
                                           False: False}))
            # Parameters
            me.setHorizon(6)
            me.setParameter('discount',0.9)
        
            # Levels of belief
        david.setRecursiveLevel(3)
        stacy.setRecursiveLevel(3)

            # Turn order: Uncomment the following if you want agents to act in parallel
            # world.setOrder([{agts[0].name,agts[1].name}])
            # Turn order: Uncomment the following if you want agents to act sequentially

        self.world.setOrder(turnOrder)

        # World state
        self.world.defineState(None,'agreement',bool)
        self.world.setState(None,'agreement',False)
        self.world.defineState(None,'appleOffer',bool)
        self.world.setState(None,'appleOffer',False)
        self.world.defineState(None,'pearOffer',bool)
        self.world.setState(None,'pearOffer',False)
        self.world.defineState(None,'round',int,description='The current round of the negotiation')
        self.world.setState(None,'round',0)
        self.world.defineState(None,'rejectedNegotiation',bool,
                          description='Have one of the players walked out?')
        self.world.setState(None, 'rejectedNegotiation', False)


# dont terminate so agent sees benefit of early agreement
#    world.addTermination(makeTree({'if': trueRow(stateKey(None,'agreement')),
#                                   True: True, 
#                                   False: False}))

#    world.addTermination(makeTree({'if': trueRow(stateKey(None,'rejectedNegotiation')),
#                                   True: True, 
#                                   False: False}))

        self.world.addTermination(makeTree({'if': thresholdRow(stateKey(None,'round'),self.maxRounds),
                                   True: True, False: False}))

    # Dynamics of offers
        agents = [david.name,stacy.name]
        for i in range(2):
            for fruit in ['apple','pear']:
                atom = Action({'subject': agents[i],'verb': 'offer%s' % (fruit.capitalize()),
                               'object': agents[1-i]})
                parties = [atom['subject'], atom['object']]
                for j in range(2):
                    # Set offer amount
                    offer = stateKey(parties[j],'%sOffered' % (fruit))
                    amount = actionKey('amount') if j == 1 else '%d-%s' % (totals[fruit],actionKey('amount'))
                    tree = makeTree(setToConstantMatrix(offer,amount))
                    self.world.setDynamics(parties[j],'%sOffered' % (fruit),atom,tree)
                    # reset agree flags whenever an offer is made
                    agreeFlag = stateKey(parties[j],'agree')
                    tree = makeTree(setFalseMatrix(agreeFlag))
                    self.world.setDynamics(parties[j],'agree',atom,tree)
                # Offers set offer flag in world state
                tree = makeTree(setTrueMatrix(stateKey(None,'%sOffer' % (fruit))))
                self.world.setDynamics(None,'%sOffer' % (fruit) ,atom,tree)
 

    # agents = [david.name,stacy.name]
    # Dynamics of agreements
        for i in range(2):
            atom = Action({'subject': agents[i],'verb': 'accept offer', 'object': agents[1-i]})

            # accept offer sets accept
            tree = makeTree(setTrueMatrix(stateKey(atom['subject'],'agree')))
            self.world.setDynamics(atom['subject'],'agree',atom,tree)

            # accept offer sets agreement if object has accepted
            tree = makeTree({'if': trueRow(stateKey(atom['object'],'agree')),
                             True:  setTrueMatrix(stateKey(None,'agreement')),
                             False: noChangeMatrix(stateKey(None,'agreement'))})
            self.world.setDynamics(None,'agreement',atom,tree)

        # Accepting offer sets ownership
            parties = [atom['subject'], atom['object']]
            for fruit in ['apple','pear']:
                # atom = Action({'subject': agents[i],'verb': 'accept offer', 'object': agents[1-i]})
                for j in range(2):
                    offer = stateKey(parties[j],'%sOffered' % (fruit))
                    owned = stateKey(parties[j],'%sOwned' % (fruit))
                    tree = makeTree({'if': trueRow(stateKey(atom['object'],'agree')),
                                     False: noChangeMatrix(owned),
                                     True: setToFeatureMatrix(owned,offer)})
                    self.world.setDynamics(parties[j],'%sOwned' % (fruit),atom,tree)
        # rejecting give us batna and ends negotiation
            atom = Action({'subject': agents[i],'verb': 'rejectNegotiation',
                           'object': agents[1-i]})

            tree = makeTree(setToFeatureMatrix(stateKey(atom['subject'],'BatnaOwned') ,stateKey(atom['subject'], 'Batna')))
            self.world.setDynamics(atom['subject'],'BatnaOwned' ,atom,tree)

            tree = makeTree(setToFeatureMatrix(stateKey(atom['object'],'BatnaOwned') ,stateKey(atom['object'], 'Batna')))
            self.world.setDynamics(atom['object'],'BatnaOwned' ,atom,tree)

            tree = makeTree(setTrueMatrix(stateKey(None,'rejectedNegotiation')))
            self.world.setDynamics(None,'rejectedNegotiation' ,atom,tree)
 

        for action in stacy.actions | david.actions:
            tree = makeTree(incrementMatrix(stateKey(None,'round'),1))
            self.world.setDynamics(None,'round',action,tree)
        for agent in self.world.agents.values():
            agent.addModel('pearLover',R={},level=2,rationality=0.01)
            agent.addModel('appleLover',R={},level=2,rationality=0.01)




    def modeltest(self,trueModels,davidBeliefAboutStacy,stacyBeliefAboutDavid,strongerBelief):
        for agent in self.world.agents.values():
            for model in agent.models.keys():
                if model is True:
                    name = trueModels[agent.name]
                else:
                    name = model
                if name == 'appleLover':
                    agent.setReward(maximizeFeature(stateKey(agent.name,'appleOwned')),4.0,model)
                    agent.setReward(maximizeFeature(stateKey(agent.name,'pearOwned')),1.0,model)
                    agent.setReward(maximizeFeature(stateKey(agent.name,'BatnaOwned')),0.1,model)
                elif name == 'pearLover':
                    agent.setReward(maximizeFeature(stateKey(agent.name,'appleOwned')),1.0,model)
                    agent.setReward(maximizeFeature(stateKey(agent.name,'pearOwned')),4.0,model)
                    agent.setReward(maximizeFeature(stateKey(agent.name,'BatnaOwned')),0.1,model)
        weakBelief = 1.0 - strongerBelief          
        belief = {'pearLover': weakBelief,'appleLover': weakBelief}
        belief[davidBeliefAboutStacy] = strongerBelief
        self.world.setMentalModel('David','Stacy',belief)
        belief = {'pearLover': weakBelief,'appleLover': weakBelief}
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
#        pearLover and appleLover are level 2 models

# Rounds
#        self.maxRounds=8

#        totals = {'apple':1,'pear':2} 
#       batna_prePref = totals['apple'] + totals['pear']
# batna pref set to 0.1
# Agreements must leave nothing on the table
# Rationality = .01


trueModels = {'Stacy': 'appleLover',
              'David': 'pearLover'}
turnOrder=['Stacy','David']
negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'appleLover','pearLover', 0.75)
negagts.runit("Integrative and correct beliefs")

negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'pearLover','appleLover', 0.75)
negagts.runit("Integrative and incorrect beliefs")

negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'pearLover','pearLover', 0.75)
negagts.runit("Integrative and David has incorrect beliefs")

    
trueModels = {'Stacy': 'appleLover',
              'David': 'appleLover'}
negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'appleLover','appleLover', 0.75)
negagts.runit("Distributive and correct beliefs")

negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'pearLover','pearLover', 0.75)
negagts.runit("Distributive and incorrect beliefs")

negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'pearLover','appleLover', 0.75)
negagts.runit("Distributive and David has incorrect beliefs")


turnOrder=['David','Stacy']
trueModels = {'Stacy': 'appleLover',
              'David': 'pearLover'}
negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'appleLover','pearLover', 0.75)
negagts.runit("Integrative and correct beliefs")

negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'pearLover','appleLover', 0.75)
negagts.runit("Integrative and incorrect beliefs")

negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'pearLover','pearLover', 0.75)
negagts.runit("Integrative and David has incorrect beliefs")

    
trueModels = {'Stacy': 'appleLover',
              'David': 'appleLover'}
negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'appleLover','appleLover', 0.75)
negagts.runit("Distributive and correct beliefs")

negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'pearLover','pearLover', 0.75)
negagts.runit("Distributive and incorrect beliefs")

negagts = Negotiate(turnOrder)
negagts.modeltest(trueModels,'pearLover','appleLover', 0.75)
negagts.runit("Distributive and David has incorrect beliefs")



