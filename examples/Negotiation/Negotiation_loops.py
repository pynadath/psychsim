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
    totals = {'scotch':1,'tequila':1} #  1 and 1
    stacy = Agent('Stacy')
    david = Agent('David')
    agts = [stacy, david]

    # Player state, actions and parameters common to both players
    for i in range(2):
        me = agts[i]
        other = agts[1-i]
        world.addAgent(me)
        # State
        world.defineState(me.name,'scotchOwned',int,lo=0,hi=totals['scotch'])
        me.setState('scotchOwned',0)
        world.defineState(me.name,'scotchOffered',int,lo=0,hi=totals['scotch'])
        me.setState('scotchOffered',0)  
        world.defineState(me.name,'tequilaOwned',int,lo=0,hi=totals['tequila'])
        me.setState('tequilaOwned',0)
        world.defineState(me.name,'tequilaOffered',int,lo=0,hi=totals['tequila'])
        me.setState('tequilaOffered',0)  
        world.defineState(me.name,'agree',bool)
        me.setState('agree',False)  
        # Actions
        me.addAction({'verb': 'do nothing'})
        for amt in range(totals['scotch'] + 1):
            me.addAction({'verb': 'offerScotch','object': other.name,'amount': amt})
        for amt in range(totals['tequila'] + 1):
            me.addAction({'verb': 'offerTequila','object': other.name,'amount': amt})
        meAccept = me.addAction({'verb': 'accept offer','object': other.name})
        me.setLegal(meAccept,makeTree({'if': trueRow(stateKey(None, 'scotchOffer')),
                                         True: {'if': trueRow(stateKey(None, 'tequilaOffer')),
                                                True: True,
                                                False: False},
                                         False: False}))
        # Parameters
        me.setHorizon(4)
        # me.setParameter('discount',0.9)
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
    world.defineState(None,'scotchOffer',bool)
    world.setState(None,'scotchOffer',False)
    world.defineState(None,'tequilaOffer',bool)
    world.setState(None,'tequilaOffer',False)

    world.termination.append(makeTree({'if': trueRow(stateKey(None,'agreement')),
                                       True: True, 
                                       False: False}))



    #######################
    # A more flexible way to specify the payoffs would be better
    # for example we would want to capture that a person might want 
    # one scotch but no more and as many tequila as they could get
    # 
    # Also a more flexbile way to specify the model of the other is needed.
    # We specifically need ways to specify the model of the other
    # that supports abstraction and perhaps easy calculation 
    # eg "the other will accept any offer that includes at least one scotch"

    # Here I just give a simple contrary preferences
    # Goals for Stacy
    scotchGoalS = maximizeFeature(stateKey(stacy.name,'scotchOwned'))
    stacy.setReward(scotchGoalS,4.0)
    tequilaGoalS = maximizeFeature(stateKey(stacy.name,'tequilaOwned'))
    stacy.setReward(tequilaGoalS,1.0)
   
    # Goals for David
    scotchGoalD = maximizeFeature(stateKey(david.name,'scotchOwned'))
    david.setReward(scotchGoalD,1.0)
    tequilaGoalD = maximizeFeature(stateKey(david.name,'tequilaOwned'))
    david.setReward(tequilaGoalD,4.0)


# So the following would be a tree capturing both of Stacy's current goals:
#     scotch = stateKey(stacy.name,'scotchOwned')
#     tequila = stateKey(stacy.name,'tequilaOwned')
#     goal = makeTree(KeyedVector({scotch: -1.,tequila: 2.}))
#     stacy.setReward(goal,1.)

# The following would be more complicated, saying that the badness of scotch plateaus at 2
#     goal = makeTree({'if': thresholdRow(scotch,1.5),
#                      True: KeyedVector({CONSTANT: -2.,tequila: 2.}),
#                      False: KeyedVector({scotch: -1.,tequila: 2.})})
#     stacy.setReward(goal,1.)

    # Dynamics of offers
    agents = [david.name,stacy.name]
    for fruit in ['scotch','tequila']:
        for i in range(2):
            atom = Action({'subject': agents[i],'verb': 'offer%s' % (fruit.capitalize()),
                           'object': agents[1-i]})
            parties = [atom['subject'], atom['object']]
            for j in range(2):
                # Set offer amount
                offer = stateKey(parties[j],'%sOffered' % (fruit))
                amount = actionKey('amount') if j == 1 else '%d-%s' % (totals[fruit],actionKey('amount'))
                tree = makeTree({'if': trueRow('agreement'),
                                 True: noChangeMatrix(offer),
                                 False: setToConstantMatrix(offer,amount)})
                world.setDynamics(parties[j],'%sOffered' % (fruit),atom,tree)
                # reset agree flags whenever an offer is made
                agreeFlag = stateKey(parties[j],'agree')
                tree = makeTree({'if': trueRow('agreement'),
                                 True: noChangeMatrix(offer),
                                 False: setFalseMatrix(agreeFlag)})
                world.setDynamics(parties[j],'agree',atom,tree)
            # Offers set offer flag in world state
            tree = makeTree({'if': trueRow(stateKey(None,'%sOffer' % (fruit))),
                             True: noChangeMatrix(stateKey(None,'%sOffer' % (fruit))),
                             False: setTrueMatrix(stateKey(None,'%sOffer' % (fruit)))})
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
        for fruit in ['scotch','tequila']:
            # atom = Action({'subject': agents[i],'verb': 'accept offer', 'object': agents[1-i]})
            for j in range(2):
                offer = stateKey(parties[j],'%sOffered' % (fruit))
                owned = stateKey(parties[j],'%sOwned' % (fruit))
                tree = makeTree({'if': trueRow(stateKey(atom['object'],'agree')),
                                 False: noChangeMatrix(owned),
                                 True: setToFeatureMatrix(owned,offer)})
                world.setDynamics(parties[j],'%sOwned' % (fruit),atom,tree)


    # mental models
    # David's models of Stacy
    stacy.addModel('tequilaLover',R={scotchGoalS: 1.0,tequilaGoalS: 4.0},level=2,rationality=0.01)
    stacy.addModel('scotchLover',R={scotchGoalS: 4.0,tequilaGoalS: 1.0},level=2,rationality=0.01)
    world.setMentalModel(david.name,stacy.name,{'tequilaLover': 0.5,'scotchLover': 0.5})
    # Stacy's models of David
    david.addModel('tequilaLover',R={scotchGoalD: 1.0,tequilaGoalD: 4.0},level=2,rationality=0.01)
    david.addModel('scotchLover',R={scotchGoalD: 4.0,tequilaGoalD: 1.0},level=2,rationality=0.01)
    world.setMentalModel(stacy.name,david.name,{'tequilaLover': 0.5,'scotchLover': 0.5})


    
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
        world.explain(world.step())
        # print world.step()
        world.state.select()
        world.printState()
        print stacy.name, "'s beliefs about ", david.name
        stacy.printBeliefs()
        print david.name, "'s belief about ", stacy.name
        david.printBeliefs()
        if world.terminated():
            break



