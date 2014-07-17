import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent



if __name__ == '__main__':

    # Create scenario
    maxRounds=8
    world = World()
    totals = {'apple':1,'pear':2} 
    batna_prePref = totals['apple'] + totals['pear']
    stacy = Agent('Stacy')
    david = Agent('David')
    agts = [stacy, david]

    # Player state, actions and parameters common to both players
    for i in range(2):
        me = agts[i]
        other = agts[1-i]
        world.addAgent(me)
        # State
        world.defineState(me.name,'appleOwned',int,lo=0,hi=totals['apple'])
        me.setState('appleOwned',0)
        world.defineState(me.name,'appleOffered',int,lo=0,hi=totals['apple'])
        me.setState('appleOffered',0)  
        world.defineState(me.name,'pearOwned',int,lo=0,hi=totals['pear'])
        me.setState('pearOwned',0)
        world.defineState(me.name,'pearOffered',int,lo=0,hi=totals['pear'])
        me.setState('pearOffered',0)  

        world.defineState(me.name,'Batna',int,lo=0,hi=10)
        me.setState('Batna', batna_prePref)
        world.defineState(me.name,'BatnaOwned',int,lo=0,hi=10)
        me.setState('BatnaOwned',0)  

        world.defineState(me.name,'agree',bool)
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
    #world.setOrder([{agts[0].name,agts[1].name}])
    # Turn order: Uncomment the following if you want agents to act sequentially
    world.setOrder([agts[0].name,agts[1].name])

    # World state
    world.defineState(None,'agreement',bool)
    world.setState(None,'agreement',False)
    world.defineState(None,'appleOffer',bool)
    world.setState(None,'appleOffer',False)
    world.defineState(None,'pearOffer',bool)
    world.setState(None,'pearOffer',False)
    world.defineState(None,'round',int,description='The current round of the negotiation')
    world.setState(None,'round',0)
    world.defineState(None,'rejectedNegotiation',bool,
                      description='Have one of the players walked out?')
    world.setState(None, 'rejectedNegotiation', False)


# dont terminate so agent sees benefit of early agreement
#    world.addTermination(makeTree({'if': trueRow(stateKey(None,'agreement')),
#                                   True: True, 
#                                   False: False}))

#    world.addTermination(makeTree({'if': trueRow(stateKey(None,'rejectedNegotiation')),
#                                   True: True, 
#                                   False: False}))

    world.addTermination(makeTree({'if': thresholdRow(stateKey(None,'round'),maxRounds),
                                   True: True, False: False}))



    #######################
    # A more flexible way to specify the payoffs would be better
    # for example we would want to capture that a person might want 
    # one apple but no more and as many pear as they could get
    # 
    # Also a more flexbile way to specify the model of the other is needed.
    # We specifically need ways to specify the model of the other
    # that supports abstraction and perhaps easy calculation 
    # eg "the other will accept any offer that includes at least one apple"

    # Here I just give a simple contrary preferences
    # Goals for Stacy
    appleGoalS = maximizeFeature(stateKey(stacy.name,'appleOwned'))
    stacy.setReward(appleGoalS,4.0)
    pearGoalS = maximizeFeature(stateKey(stacy.name,'pearOwned'))
    stacy.setReward(pearGoalS,1.0)
    BatnaGoalS = maximizeFeature(stateKey(stacy.name,'BatnaOwned'))
    stacy.setReward(BatnaGoalS,6.0)
   
    # Goals for David
    appleGoalD = maximizeFeature(stateKey(david.name,'appleOwned'))
    david.setReward(appleGoalD,1.0)
    pearGoalD = maximizeFeature(stateKey(david.name,'pearOwned'))
    david.setReward(pearGoalD,4.0)
    BatnaGoalD = maximizeFeature(stateKey(david.name,'BatnaOwned'))
    david.setReward(BatnaGoalD,0.1)


# So the following would be a tree capturing both of Stacy's current goals:
#     apple = stateKey(stacy.name,'appleOwned')
#     pear = stateKey(stacy.name,'pearOwned')
#     goal = makeTree(KeyedVector({apple: -1.,pear: 2.}))
#     stacy.setReward(goal,1.)

# The following would be more complicated, saying that the badness of apple plateaus at 2
#     goal = makeTree({'if': thresholdRow(apple,1.5),
#                      True: KeyedVector({CONSTANT: -2.,pear: 2.}),
#                      False: KeyedVector({apple: -1.,pear: 2.})})
#     stacy.setReward(goal,1.)

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
                world.setDynamics(parties[j],'%sOffered' % (fruit),atom,tree)
                # reset agree flags whenever an offer is made
                agreeFlag = stateKey(parties[j],'agree')
                tree = makeTree(setFalseMatrix(agreeFlag))
                world.setDynamics(parties[j],'agree',atom,tree)
            # Offers set offer flag in world state
            tree = makeTree(setTrueMatrix(stateKey(None,'%sOffer' % (fruit))))
            world.setDynamics(None,'%sOffer' % (fruit) ,atom,tree)
 

    # agents = [david.name,stacy.name]
    # Dynamics of agreements
    for i in range(2):
        atom = Action({'subject': agents[i],'verb': 'accept offer', 'object': agents[1-i]})

        # accept offer sets accept
        tree = makeTree(setTrueMatrix(stateKey(atom['subject'],'agree')))
        world.setDynamics(atom['subject'],'agree',atom,tree)

        # accept offer sets agreement if object has accepted
        tree = makeTree({'if': trueRow(stateKey(atom['object'],'agree')),
                         True:  setTrueMatrix(stateKey(None,'agreement')),
                         False: noChangeMatrix(stateKey(None,'agreement'))})
        world.setDynamics(None,'agreement',atom,tree)

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
                world.setDynamics(parties[j],'%sOwned' % (fruit),atom,tree)
        # rejecting give us batna and ends negotiation
        atom = Action({'subject': agents[i],'verb': 'rejectNegotiation',
                       'object': agents[1-i]})

        tree = makeTree(setToFeatureMatrix(stateKey(atom['subject'],'BatnaOwned') ,stateKey(atom['subject'], 'Batna')))
        world.setDynamics(atom['subject'],'BatnaOwned' ,atom,tree)

        tree = makeTree(setToFeatureMatrix(stateKey(atom['object'],'BatnaOwned') ,stateKey(atom['object'], 'Batna')))
        world.setDynamics(atom['object'],'BatnaOwned' ,atom,tree)

        tree = makeTree(setTrueMatrix(stateKey(None,'rejectedNegotiation')))
        world.setDynamics(None,'rejectedNegotiation' ,atom,tree)
 

    for action in stacy.actions | david.actions:
            tree = makeTree(incrementMatrix(stateKey(None,'round'),1))
            world.setDynamics(None,'round',action,tree)

    # mental models
    # David's models of Stacy
    stacy.addModel('pearLover',R={appleGoalS: 1.0,pearGoalS: 4.0,BatnaGoalS:6.0},level=2,rationality=0.01)
    stacy.addModel('appleLover',R={appleGoalS: 4.0,pearGoalS: 1.0,BatnaGoalS:0.1},level=2,rationality=0.01)
    world.setMentalModel(david.name,stacy.name,{'pearLover': 0.5,'appleLover': 0.5})
    # Stacy's models of David
    david.addModel('pearLover',R={appleGoalD: 1.0,pearGoalD: 4.0,BatnaGoalD: 6.0},level=2,rationality=0.01)
    david.addModel('appleLover',R={appleGoalD: 4.0,pearGoalD: 1.0,BatnaGoalD: 0.1},level=2,rationality=0.01)
    world.setMentalModel(stacy.name,david.name,{'pearLover': 0.5,'appleLover': 0.5})


    
    # Save scenario to compressed XML file
    world.save('default.psy')

    # Create configuration file
    # config = SafeConfigParser()
    # f = open('default.cfg','w')
    # config.write(f)
    # f.close()

    # Test saved scenario
    world = World('default.psy')
    # world.printState()
    
    for t in range(maxRounds + 1):
        world.explain(world.step())
        # print world.step()
        world.state.select()
        world.printState()
        if world.terminated():
            break



