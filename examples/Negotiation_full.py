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
    totals = {'apple':3,'pear':2}
    # Stacy state
    stacy = Agent('Stacy')
    world.addAgent(stacy)
    world.defineState(stacy.name,'applesOwned',int,lo=0,hi=totals['apple'])
    stacy.setState('applesOwned',0)
    world.defineState(stacy.name,'applesOffered',int,lo=0,hi=totals['apple'])
    stacy.setState('applesOffered',0)  
    world.defineState(stacy.name,'pearsOwned',int,lo=0,hi=totals['pear'])
    stacy.setState('pearsOwned',0)
    world.defineState(stacy.name,'pearsOffered',int,lo=0,hi=totals['pear'])
    stacy.setState('pearsOffered',0)  


    # David state
    david = Agent('David')
    world.addAgent(david)

    world.defineState(david.name,'applesOwned',int,lo=0,hi=totals['apple'])
    david.setState('applesOwned',0)
    world.defineState(david.name,'applesOffered',int,lo=0,hi=totals['apple'])
    david.setState('applesOffered',0)  
    world.defineState(david.name,'pearsOwned',int,lo=0,hi=totals['pear'])
    david.setState('pearsOwned',0)
    world.defineState(david.name,'pearsOffered',int,lo=0,hi=totals['pear'])
    david.setState('pearsOffered',0)  

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

    # Turn order: Uncomment the following if you want agents to act in parallel
#    world.setOrder([[stacy.name,david.name]])
    # Turn order: Uncomment the following if you want agents to act sequentially
    world.setOrder([stacy.name,david.name])

    # Stacy actions
    stacy.addAction({'verb': 'do nothing'})
    stacy.addAction({'verb': 'offerApple','object': david.name,'amount': 0})
    stacy.addAction({'verb': 'offerApple','object': david.name,'amount': 1})
    stacy.addAction({'verb': 'offerApple','object': david.name,'amount': 2})
    stacy.addAction({'verb': 'offerApple','object': david.name,'amount': 3})

    stacy.addAction({'verb': 'offerPear','object': david.name,'amount': 0})
    stacy.addAction({'verb': 'offerPear','object': david.name,'amount': 1})
    stacy.addAction({'verb': 'offerPear','object': david.name,'amount': 2})

    stacyAccept = stacy.addAction({'verb': 'accept offer','object': david.name})

    # David actions
    david.addAction({'verb': 'do nothing'})
    david.addAction({'verb': 'offerApple','object': stacy.name,'amount': 0})
    david.addAction({'verb': 'offerApple','object': stacy.name,'amount': 1})
    david.addAction({'verb': 'offerApple','object': stacy.name,'amount': 2})
    david.addAction({'verb': 'offerApple','object': stacy.name,'amount': 3})

    david.addAction({'verb': 'offerPear','object': stacy.name,'amount': 0})
    david.addAction({'verb': 'offerPear','object': stacy.name,'amount': 1})
    david.addAction({'verb': 'offerPear','object': stacy.name,'amount': 2})

    davidAccept = david.addAction({'verb': 'accept offer','object': stacy.name})


    david.setLegal(davidAccept,makeTree({'if': trueRow(stateKey(None, 'applesOffer')),
                                         True: {'if': trueRow(stateKey(None, 'pearsOffer')),
                                                True: True,
                                                False: False},
                                         False: False}))


    stacy.setLegal(stacyAccept, makeTree({'if': trueRow(stateKey(None, 'applesOffer')),
                                          True: {'if': trueRow(stateKey(None, 'pearsOffer')),
                                                 True: True,
                                                 False: False},
                                          False: False}))

    david.setHorizon(4)
    stacy.setHorizon(4)
    stacy.setParameter('discount',0.9)
    david.setParameter('discount',0.9)
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
    goal = minimizeFeature(stateKey(stacy.name,'applesOwned'))
    stacy.setReward(goal,1.)
    goal = maximizeFeature(stateKey(stacy.name,'pearsOwned'))
    stacy.setReward(goal,2.)
   
    # Goals for David
    goal = maximizeFeature(stateKey(david.name,'applesOwned'))
    david.setReward(goal,2.)
    goal = minimizeFeature(stateKey(david.name,'pearsOwned'))
    david.setReward(goal,1.)

    # Dynamics of offers
    agents = [david.name,stacy.name]
    for fruit in ['apple','pear']:
        for i in range(2):
            atom = Action({'subject': agents[i],'verb': 'offer%s' % (fruit.capitalize()),
                           'object': agents[1-i]})
            offer = stateKey(atom['object'],'%ssOffered' % (fruit))
            amount = actionKey('amount')

            tree = makeTree({'if': trueRow('agreement'),
                             True: noChangeMatrix(offer),
                             False: setToConstantMatrix(offer,amount)})
            world.setDynamics(atom['object'],'%ssOffered' % (fruit),atom,tree)

            offer = stateKey(atom['subject'],'%ssOffered' % (fruit))
            tree = makeTree({'if': trueRow('agreement'),
                             True: noChangeMatrix(offer),
                             False: setToConstantMatrix(offer,'%d-%s' % (totals[fruit],actionKey('amount')))})
            world.setDynamics(atom['subject'],'%ssOffered' % (fruit),atom,tree)
            # Offers set offer flag in world state
            tree = makeTree({'if': trueRow(stateKey(None,'%ssOffer' % (fruit))),
                             True: noChangeMatrix(stateKey(None,'%ssOffer' % (fruit))),
                             False: setTrueMatrix(stateKey(None,'%ssOffer' % (fruit)))})
            world.setDynamics(None,'%ssOffer' % (fruit) ,atom,tree)


    # Dynamics of agreements
    
    agents = [david.name,stacy.name]
    for i in range(2):
        atom = Action({'subject': agents[i],'verb': 'accept offer', 'object': agents[1-i]})

        # accept offer sets agreement if both apples and pears have been offered
        tree = makeTree({'if': trueRow(stateKey(None,'agreement')),
                         True: noChangeMatrix(stateKey(None,'agreement')),
                         False: setTrueMatrix(stateKey(None,'agreement'))})
        world.setDynamics(None,'agreement',atom,tree)
        # Accepting offer sets ownership
        for fruit in ['apple','pear']:
            atom = Action({'subject': agents[i],'verb': 'accept offer', 'object': agents[1-i]})
            offer = stateKey(atom['object'],'%ssOffered' % (fruit))
            owned = stateKey(atom['object'],'%ssOwned' % (fruit))
            tree = makeTree({'if': trueRow('agreement'), # this test shouldn't be necessary
                             False: setToFeatureMatrix(owned,offer),
                             True: setToFeatureMatrix(owned,offer)})
            world.setDynamics(atom['object'],'%ssOwned' % (fruit),atom,tree)
            offer = stateKey(atom['subject'],'%ssOffered' % (fruit))
            owned = stateKey(atom['subject'],'%ssOwned' % (fruit))
            tree = makeTree({'if': trueRow('agreement'),  # this test shouldn't be necessary
                             False: setToFeatureMatrix(owned,offer),
                             True: setToFeatureMatrix(owned,offer)})
            world.setDynamics(atom['subject'],'%ssOwned' % (fruit),atom,tree)


    
    # Save scenario to compressed XML file
    world.save('default.psy')

    # Create configuration file
    # config = SafeConfigParser()
    # f = open('default.cfg','w')
    # config.write(f)
    # f.close()

    # Test saved scenario
    world = World('default.psy')
    world.printState()
    
    for t in range(7):
        world.explain(world.step())
        world.state.select()
        world.printState()


