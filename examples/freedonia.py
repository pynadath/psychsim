import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser

from psychsim.pwl import *
from psychsim.action import Action,ActionSet
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent

def scenarioCreationUseCase():
    """
    An example of how to create a scenario
    @return: the scenario created
    @rtype: L{World}
    """
    # Create scenario
    world = World()

    # Agents
    free = Agent('Freedonia')
    world.addAgent(free)
    sylv = Agent('Sylvania')
    world.addAgent(sylv)

    # User state
    world.defineState(free.name,'troops',int,lo=200000,hi=400000,
                      description='Number of troops %s has left' % (free.name))
    free.setState('troops',381940)
    world.defineState(free.name,'offered',int,lo=0,hi=100,
                      description='Percentage of disputed territory that %s last offered to %s' % (sylv.name,free.name))
    free.setState('offered',0)  # Percentage of disputed territory offered *to* me
    world.defineState(free.name,'territory',int,lo=0,hi=100,
                      description='Percentage of disputed territory currently owned by %s' % (free.name))
    free.setState('territory',13)  # Percentage of disputed territory

    # Agent state
    world.defineState(sylv.name,'troops',int,lo=200000,hi=400000,
                      description='Number of troops %s has left' % (sylv.name))
    sylv.setState('troops',461432)
    world.defineState(sylv.name,'offered',int,lo=0,hi=100,
                      description='Percentage of disputed territory that %s last offered to %s' % (free.name,sylv.name))
    sylv.setState('offered',0)  # Percentage of disputed territory offered *to* me

    # World state illustration of Boolean feature
    world.defineState(None,'treaty',bool)
    world.setState(None,'treaty',False)
    # World state illustration of enumerated state feature
    world.defineState(None,'model',list,['Slantchev','Powell','Smith/Stam'])
    world.setState(None,'model','Powell')

    # Conditions for game over
    world.termination.append(makeTree({'if': trueRow(stateKey(None,'treaty')),
                                       True: True, False: False}))

    # Turn order: Uncomment the following if you want agents to act in parallel
#    world.setOrder([[free.name,sylv.name]])
    # Turn order: Uncomment the following if you want agents to act sequentially
    world.setOrder([free.name,sylv.name])

    # User actions
    free.addAction({'verb': 'do nothing'})
    freeBattle = free.addAction({'verb': 'attack','object': sylv.name})
    freeOffer25 = free.addAction({'verb': 'offer','object': sylv.name,'amount': 25})
    freeOffer50 = free.addAction({'verb': 'offer','object': sylv.name,'amount': 50})
    freeOffer75 = free.addAction({'verb': 'offer','object': sylv.name,'amount': 75})
    freeAccept = free.addAction({'verb': 'accept offer','object': sylv.name})

    # Agent actions
    sylv.addAction({'verb': 'do nothing'})
    sylvBattle = sylv.addAction({'verb': 'attack','object': free.name})
    sylvOffer25 = sylv.addAction({'verb': 'offer','object': free.name,'amount': 25})
    sylvOffer50 = sylv.addAction({'verb': 'offer','object': free.name,'amount': 50})
    sylvOffer75 = sylv.addAction({'verb': 'offer','object': free.name,'amount': 75})
    sylvAccept = sylv.addAction({'verb': 'accept offer','object': free.name})

    # Restrictions on when actions are legal
    for action in filter(lambda a: a.match({'verb': 'battle'}),free.actions | sylv.actions):
        subject = world.agents[action['subject']]
        subject.legal[action] = makeTree({'if': trueRow(stateKey(None,'treaty')),
                                          True: False,  # Illegal if treaty is True
                                          False: True}) # Legal if treaty is False
    for action in filter(lambda a: a.match({'verb': 'offer'}),free.actions | sylv.actions):
        subject = world.agents[action['subject']]
        subject.legal[action] = makeTree({'if': trueRow(stateKey(None,'treaty')),
                                          True: False,  # Illegal if treaty is True
                                          False: True}) # Legal if treaty is False
    for action in filter(lambda a: a.match({'verb': 'accept offer'}),free.actions | sylv.actions):
        subject = world.agents[action['subject']]
        subject.legal[action] = makeTree({'if': trueRow(stateKey(None,'treaty')),
                                          True: False,  # Illegal if treaty is True
                                          False: {'if': thresholdRow(stateKey(subject.name,'offered'),1),
                                                  True: True,     # Legal if treaty is False and an offer has been made
                                                  False: False}}) # Illegal if no offer has been made

    # Goals for Freedonia
    goalFTroops = maximizeFeature(stateKey(free.name,'troops'))
    free.setReward(goalFTroops,1e-4)
    goalFTerritory = maximizeFeature(stateKey(free.name,'territory'))
    free.setReward(goalFTerritory,2.)

    # Goals for Sylvania
    goalSTroops = maximizeFeature(stateKey(sylv.name,'troops'))
    sylv.setReward(goalSTroops,1e-4)
    goalSTerritory = minimizeFeature(stateKey(free.name,'territory'))
    sylv.setReward(goalSTerritory,0.1)

    # Horizons
    free.setHorizon(2)
    sylv.setHorizon(2)

    # Levels of belief
    free.setRecursiveLevel(2)
    sylv.setRecursiveLevel(2)

    # Dynamics of battle
    freeTroops = stateKey(free.name,'troops')
    freeTerr = stateKey(free.name,'territory')
    sylvTroops = stateKey(sylv.name,'troops')
    # Effect of F attacking S on F's troops
    tree = makeTree({'if': greaterThanRow(freeTroops,sylvTroops),
                     True: scaleMatrix(freeTroops,0.99),
                     False: scaleMatrix(freeTroops,0.98),
                     })
    world.setDynamics(free.name,'troops',freeBattle,tree)
    # Effect of F attacking S on S's troops
    tree = makeTree({'if': greaterThanRow(sylvTroops,freeTroops),
                     True: scaleMatrix(sylvTroops,0.97),
                     False: scaleMatrix(sylvTroops,0.96),
                     })
    world.setDynamics(sylv.name,'troops',freeBattle,tree)
    # Effect of S attacking F on F's troops
    tree = makeTree({'if': greaterThanRow(freeTroops,sylvTroops),
                     True: scaleMatrix(freeTroops,0.97),
                     False: scaleMatrix(freeTroops,0.96),
                     })
    world.setDynamics(free.name,'troops',sylvBattle,tree)
    # Effect of S attacking F on S's troops
    tree = makeTree({'if': greaterThanRow(sylvTroops,freeTroops),
                     True: scaleMatrix(sylvTroops,0.99),
                     False: scaleMatrix(sylvTroops,0.98),
                     })
    world.setDynamics(sylv.name,'troops',sylvBattle,tree)

    # Effect of F attacking S on F's territory
    tree = makeTree({'if':greaterThanRow(freeTroops,sylvTroops),
                     True: {'distribution': [(approachMatrix(freeTerr,0.2,100), 0.8),
                                             (approachMatrix(freeTerr,0.1,0), 0.2)]},
                     False: {'distribution': [(approachMatrix(freeTerr,0.2,100), 0.6),
                                             (approachMatrix(freeTerr,0.1,0), 0.4)]}})
    world.setDynamics(free.name,'territory',freeBattle,tree)
    # Effect of S attacking F on F's territory
    tree = makeTree({'if':greaterThanRow(freeTroops,sylvTroops),
                     True: {'distribution': [(approachMatrix(freeTerr,0.2,0), 0.6),
                                             (approachMatrix(freeTerr,0.1,100), 0.4)]},
                     False: {'distribution': [(approachMatrix(freeTerr,0.2,0), 0.8),
                                             (approachMatrix(freeTerr,0.1,100), 0.2)]}})
    world.setDynamics(free.name,'territory',sylvBattle,tree)

    # Dynamics of offers
    for atom in [Action({'subject': free.name,'verb': 'offer','object': sylv.name}),
                 Action({'subject': sylv.name,'verb': 'offer','object': free.name})]:
        offer = stateKey(atom['object'],'offered')
        amount = actionKey('amount')
        tree = makeTree({'if': trueRow(stateKey(None,'treaty')),
                         True: noChangeMatrix(offer),
                         False: setToConstantMatrix(offer,amount)})
        world.setDynamics(atom['object'],'offered',atom,tree)
    # Dynamics of treaties
    for action in filter(lambda a: a.match({'verb': 'accept offer'}),free.actions | sylv.actions):
        # Accepting an offer means that there is now a treaty
        tree = makeTree({'if': trueRow(stateKey(None,'treaty')),
                         True: noChangeMatrix(stateKey(None,'treaty')),
                         False: setTrueMatrix(stateKey(None,'treaty'))})
        world.setDynamics(None,'treaty',action,tree)
        # Accepting offer sets territory
        offer = stateKey(action['subject'],'offered')
        territory = stateKey(free.name,'territory')
        if action['subject'] == free.name:
            # Freedonia accepts sets territory to last offer
            tree = makeTree({'if': thresholdRow(offer,0.),
                             True: {'if': trueRow(stateKey(None,'treaty')),
                                    True: noChangeMatrix(territory),
                                    False: setToFeatureMatrix(territory,offer)},
                             False: noChangeMatrix(territory)})
            world.setDynamics(free.name,'territory',action,tree)
        else:
            # Sylvania accepts sets territory to 1-last offer
            tree = makeTree({'if': thresholdRow(offer,0.),
                             True: {'if': trueRow(stateKey(None,'treaty')),
                                    True: noChangeMatrix(territory),
                                    False: setToFeatureMatrix(territory,offer,pct=-1.,shift=100.)},
                             False: noChangeMatrix(territory)})
            world.setDynamics(free.name,'territory',action,tree)

    # Dynamics of world model (for illustration purposes only)
    tree = makeTree({'if': equalRow(stateKey(None,'model'),'Slantchev'),
                     True: setToConstantMatrix(stateKey(None,'model'),'Powell'),
                     False: setToConstantMatrix(stateKey(None,'model'),'Slantchev')})
    world.setDynamics(None,'model',freeOffer25,tree)

    # Models of Freedonia
    free.addModel('dove',R={goalFTroops: 1e-4,goalFTerritory: 0.1},level=1,rationality=0.01)
    free.addModel('true',level=1,rationality=0.01)
    free.addModel('hawk',R={goalFTroops: 1e-4,goalFTerritory: 0.3},level=1,rationality=0.01)
    world.setMentalModel(sylv.name,free.name,{'true': 0.6,'dove': 0.3,'hawk': 0.1})
    return world

def scenarioSimulationUseCase(world,debug=1):
    free = world.agents['Freedonia']
    sylv = world.agents['Sylvania']
    if options.debug > 0:
        world.printState()

    # Force Freedonia to attack in first step
    freeBattle = Action({'subject': free.name,'verb': 'attack','object': sylv.name})
    world.explain(world.step({free.name: freeBattle}),options.debug)
    world.state.select()
    if options.debug > 0:
        world.printState()
        # Display Sylvania's posterior beliefs
        sylv.printBeliefs()

    # Sylvania free to decide in second step
    world.explain(world.step(),options.debug)
    world.state.select()
    if options.debug > 0:
        world.printState()

if __name__ == '__main__':
    # Grab command-line arguments
    parser = OptionParser()
    # Optional argument that sets the level of explanations when running the simulation
    parser.add_option('-d','--debug',action='store',
                      dest='debug',type='int',default=1,
                      help='level of explanation detail [default: %default]')
    # Optional argument that sets the filename for the output file
    parser.add_option('-o','--output',action='store',type='string',
                      dest='output',default='default',
                      help='scenario file [default: %default]')
    (options, args) = parser.parse_args()
    
    world = scenarioCreationUseCase()

    # Create configuration file
    config = SafeConfigParser()
    config.add_section('Game')
    config.set('Game','rounds','15')
    assert world.agents.has_key('Freedonia')
    config.set('Game','user','Freedonia')
    f = open('default.cfg','w')
    config.write(f)
    f.close()

    # Save scenario to compressed XML file
    if options.output[-4:] != '.psy':
        options.output = '%s.psy' % (options.output)
    world.save(options.output)

    # Test saved scenario
    world = World(options.output)
    scenarioSimulationUseCase(world,options.debug)
