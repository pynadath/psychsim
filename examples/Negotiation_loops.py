import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent



if __name__ == '__main__':

    # Create scenario
    world = World()
    totals = {'apple':1,'pear':1} #  1 and 1
    stacy = Agent('Stacy')
    david = Agent('David')
    agts = [stacy, david]

    # Player state, actions and parameters common to both players
    for i in range(2):
        me = agts[i]
        other = agts[1-i]
        world.addAgent(me)
        # State
        world.defineState(me.name,'applesOwned',int,lo=0,hi=totals['apple'])
        me.setState('applesOwned',0)
        world.defineState(me.name,'applesOffered',int,lo=0,hi=totals['apple'])
        me.setState('applesOffered',0)  
        world.defineState(me.name,'pearsOwned',int,lo=0,hi=totals['pear'])
        me.setState('pearsOwned',0)
        world.defineState(me.name,'pearsOffered',int,lo=0,hi=totals['pear'])
        me.setState('pearsOffered',0)  
        world.defineState(me.name,'agree',bool)
        me.setState('agree',False)  
        # Actions
        me.addAction({'verb': 'do nothing'})
        for amt in range(totals['apple'] + 1):
            me.addAction({'verb': 'offerApple','object': other.name,'amount': amt})
        for amt in range(totals['pear'] + 1):
            me.addAction({'verb': 'offerPear','object': other.name,'amount': amt})
        meAccept = me.addAction({'verb': 'accept offer','object': other.name})
        me.setLegal(meAccept,makeTree({'if': trueRow(stateKey(None, 'applesOffer')),
                                         True: {'if': trueRow(stateKey(None, 'pearsOffer')),
                                                True: True,
                                                False: False},
                                         False: False}))
        # Parameters
        me.setHorizon(3)
        # me.setParameter('discount',0.9)
        me.setParameter('discount',0.2)

    # Turn order: Uncomment the following if you want agents to act in parallel
    #world.setOrder([{agts[0].name,agts[1].name}])
    # Turn order: Uncomment the following if you want agents to act sequentially
    world.setOrder([agts[0].name,agts[1].name])

    # World state
    world.defineState(None,'agreement',bool)
    world.setState(None,'agreement',False)
    world.defineState(None,'applesOffer',bool)
    world.setState(None,'applesOffer',False)
    world.defineState(None,'pearsOffer',bool)
    world.setState(None,'pearsOffer',False)

    world.termination.append(makeTree({'if': trueRow(stateKey(None,'agreement')),
                                       True: True, 
                                       False: False}))



    #######################
    # A more flexible way to specify the payoffs would be better
    # for example we would want to capture that a person might want 
    # one apple but no more and as many pears as they could get
    # 
    # Also a more flexbile way to specify the model of the other is needed.
    # We specifically need ways to specify the model of the other
    # that supports abstraction and perhaps easy calculation 
    # eg "the other will accept any offer that includes at least one apple"

    # Here I just give a simple contrary preferences
    # Goals for Stacy
    goal = maximizeFeature(stateKey(stacy.name,'applesOwned'))
    stacy.setReward(goal,2.0)
    goal = maximizeFeature(stateKey(stacy.name,'pearsOwned'))
    stacy.setReward(goal,1.0)
   
    # Goals for David
    goal = maximizeFeature(stateKey(david.name,'applesOwned'))
    david.setReward(goal,2.0)
    goal = maximizeFeature(stateKey(david.name,'pearsOwned'))
    david.setReward(goal,4.0)


# So the following would be a tree capturing both of Stacy's current goals:
#     apples = stateKey(stacy.name,'applesOwned')
#     pears = stateKey(stacy.name,'pearsOwned')
#     goal = makeTree(KeyedVector({apples: -1.,pears: 2.}))
#     stacy.setReward(goal,1.)

# The following would be more complicated, saying that the badness of apples plateaus at 2
#     goal = makeTree({'if': thresholdRow(apples,1.5),
#                      True: KeyedVector({CONSTANT: -2.,pears: 2.}),
#                      False: KeyedVector({apples: -1.,pears: 2.})})
#     stacy.setReward(goal,1.)

    # Dynamics of offers
    agents = [david.name,stacy.name]
    for fruit in ['apple','pear']:
        for i in range(2):
            atom = Action({'subject': agents[i],'verb': 'offer%s' % (fruit.capitalize()),
                           'object': agents[1-i]})
            parties = [atom['subject'], atom['object']]
            for j in range(2):
                # Set offer amount
                offer = stateKey(parties[j],'%ssOffered' % (fruit))
                amount = actionKey('amount') if j == 1 else '%d-%s' % (totals[fruit],actionKey('amount'))
                tree = makeTree({'if': trueRow('agreement'),
                                 True: noChangeMatrix(offer),
                                 False: setToConstantMatrix(offer,amount)})
                world.setDynamics(parties[j],'%ssOffered' % (fruit),atom,tree)
                # reset agree flags whenever an offer is made
                agreeFlag = stateKey(parties[j],'agree')
                tree = makeTree({'if': trueRow('agreement'),
                                 True: noChangeMatrix(offer),
                                 False: setFalseMatrix(agreeFlag)})
                world.setDynamics(parties[j],'agree',atom,tree)
            # Offers set offer flag in world state
            tree = makeTree({'if': trueRow(stateKey(None,'%ssOffer' % (fruit))),
                             True: noChangeMatrix(stateKey(None,'%ssOffer' % (fruit))),
                             False: setTrueMatrix(stateKey(None,'%ssOffer' % (fruit)))})
            world.setDynamics(None,'%ssOffer' % (fruit) ,atom,tree)

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
                offer = stateKey(parties[j],'%ssOffered' % (fruit))
                owned = stateKey(parties[j],'%ssOwned' % (fruit))
                tree = makeTree({'if': trueRow(stateKey(atom['object'],'agree')),
                                 False: noChangeMatrix(owned),
                                 True: setToFeatureMatrix(owned,offer)})
                world.setDynamics(parties[j],'%ssOwned' % (fruit),atom,tree)



    
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
    
    for t in range(7):
        # world.explain(world.step())
        # print world.step()
        world.state.select()
        # world.printState()


