import sys
from ConfigParser import SafeConfigParser
from argparse import ArgumentParser

from psychsim.pwl import *
from psychsim.action import *
from psychsim.world import World,stateKey,actionKey
from psychsim.agent import Agent

def scenarioCreationUseCase(fCost=1000,sCost=1000,fCollapse=0.1,sCollapse=0.1,territory=13,
                            fTroops=381940,sTroops=461432,maxRounds=15,model='powell'):
    """
    An example of how to create a scenario
    @param sCost: number of troops Sylvania loses in battle
    @param fCost: number of troops Sylvania loses in battle
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
    world.defineState(free.name,'troops',int,lo=0,hi=500000,
                      description='Number of troops %s has left' % (free.name))
    free.setState('troops',fTroops)
    world.defineState(free.name,'territory',int,lo=0,hi=100,
                      description='Percentage of disputed territory owned by %s' % (free.name))
    free.setState('territory',territory)  # Percentage of disputed territory
    world.defineState(free.name,'cost',int,lo=0,hi=50000,
                      description='Number of troops %s loses in an attack' % (free.name))
    free.setState('cost',fCost)
    world.defineState(free.name,'position',int,lo=0,hi=100,
                      description='Military position of %s' % (free.name))
    free.setState('position',50)
    world.defineState(free.name,'offered',int,lo=0,hi=100,
                      description='Percentage of disputed territory that %s last offered to %s' % (sylv.name,free.name))
    free.setState('offered',0)

    # Agent state
    world.defineState(sylv.name,'troops',int,lo=0,hi=500000,
                      description='Number of troops %s has left' % (sylv.name))
    sylv.setState('troops',sTroops)
    world.defineState(sylv.name,'cost',int,lo=0,hi=50000,
                      description='Number of troops %s loses in an attack' % (sylv.name))
    sylv.setState('cost',sCost)
    world.defineState(sylv.name,'offered',int,lo=0,hi=100,
                      description='Percentage of disputed territory that %s last offered to %s' % (free.name,sylv.name))
    sylv.setState('offered',0)

    # World state
    world.defineState(None,'treaty',bool,
                      description='Have the two sides reached an agreement?')
    world.setState(None,'treaty',False)
    # Stage of negotiation, illustrating the use of an enumerated state feature
    world.defineState(None,'phase',list,['offer','respond','rejection','end','paused','engagement'],
                      description='The current stage of the negotiation game')
    world.setState(None,'phase','paused')
    # Round of negotiation
    world.defineState(None,'round',int,description='The current round of the negotiation')
    world.setState(None,'round',0)

    # Game over if there is a treaty
    world.addTermination(makeTree({'if': trueRow(stateKey(None,'treaty')),
                                   True: True, False: False}))
    # Game over if Freedonia has no territory
    world.addTermination(makeTree({'if': thresholdRow(stateKey(free.name,'territory'),1),
                                   True: False, False: True}) )
    # Game over if Freedonia has all the territory
    world.addTermination(makeTree({'if': thresholdRow(stateKey(free.name,'territory'),99),
                                   True: True, False: False})) 
    # Game over if number of rounds exceeds limit
    world.addTermination(makeTree({'if': thresholdRow(stateKey(None,'round'),maxRounds),
                                   True: True, False: False}))

    # Turn order: Uncomment the following if you want agents to act in parallel
#    world.setOrder([{free.name,sylv.name}])
    # Turn order: Uncomment the following if you want agents to act sequentially
    world.setOrder([free.name,sylv.name])

    # User actions
    freeBattle = free.addAction({'verb': 'attack','object': sylv.name})
    for amount in [25,50,75]:
        free.addAction({'verb': 'offer','object': sylv.name,'amount': amount})
    if model == 'powell':
        # Powell has null stages
        freeNOP = free.addAction({'verb': 'continue'})
    elif model == 'slantchev':
        # Slantchev has both sides receiving offers
        free.addAction({'verb': 'accept offer','object': sylv.name})
        free.addAction({'verb': 'reject offer','object': sylv.name})

    # Agent actions
    sylvBattle = sylv.addAction({'verb': 'attack','object': free.name})
    sylvAccept = sylv.addAction({'verb': 'accept offer','object': free.name})
    sylvReject = sylv.addAction({'verb': 'reject offer','object': free.name})
    if model == 'powell':
        # Powell has null stages
        sylvNOP = sylv.addAction({'verb': 'continue'})
    elif model == 'slantchev':
        # Slantchev has both sides making offers
        for amount in range(0,100,11):
            sylv.addAction({'verb': 'offer','object': free.name,'amount': amount})

    # Restrictions on when actions are legal, based on phase of game
    for action in filterActions({'verb': 'offer'},free.actions | sylv.actions):
        agent = world.agents[action['subject']]
        agent.setLegal(action,makeTree({'if': equalRow(stateKey(None,'phase'),'offer'),
                                        True: True,     # Offers are legal in the offer phase
                                        False: False})) # Offers are illegal in all other phases
    if model == 'powell':
        # Powell has a special rejection phase
        for action in [freeNOP,freeBattle]:
            free.setLegal(action,makeTree({'if': equalRow(stateKey(None,'phase'),'rejection'),
                                        True: True,     # Attacking and doing nothing are legal only in rejection phase
                                        False: False})) # Attacking and doing nothing are illegal in all other phases

    # Once offered, agent can respond
    if model == 'powell':
        # Under Powell, only Sylvania has to respond, and it can attack
        responses = [sylvBattle,sylvAccept,sylvReject]
    elif model == 'slantchev':
        # Under Slantchev, only accept/reject
        responses = filterActions({'verb': 'accept offer'},free.actions | sylv.actions)
        responses += filterActions({'verb': 'reject offer'},free.actions | sylv.actions)
    for action in responses:
        agent = world.agents[action['subject']]
        agent.setLegal(action,makeTree({'if': equalRow(stateKey(None,'phase'),'respond'),
                                        True: True,     # Offeree must act in the response phase
                                        False: False})) # Offeree cannot act in any other phase

    if model == 'powell':
        # NOP is legal in exactly opposite situations to all other actions
        sylv.setLegal(sylvNOP,makeTree({'if': equalRow(stateKey(None,'phase'),'end'),
                                        True: True,     # Sylvania does not do anything in the null phase after Freedonia responds to rejection
                                        False: False})) # Sylvania must act in its other phases
    if model == 'slantchev':
        # Attacking legal only under engagement phase
        for action in filterActions({'verb': 'attack'},free.actions | sylv.actions):
            agent = world.agents[action['subject']]
            agent.setLegal(action,makeTree({'if': equalRow(stateKey(None,'phase'),'engagement'),
                                            True: True,     # Attacking legal only in engagement
                                            False: False})) # Attacking legal every other phase

    # Goals for Freedonia
    goalFTroops = maximizeFeature(stateKey(free.name,'troops'))
    free.setReward(goalFTroops,1.)
    goalFTerritory = maximizeFeature(stateKey(free.name,'territory'))
    free.setReward(goalFTerritory,10.)

    # Goals for Sylvania
    goalSTroops = maximizeFeature(stateKey(sylv.name,'troops'))
    sylv.setReward(goalSTroops,1.)
    goalSTerritory = minimizeFeature(stateKey(free.name,'territory'))
    sylv.setReward(goalSTerritory,100.)

    # Horizons
    free.setHorizon(4)
    sylv.setHorizon(4)

    if model == 'slantchev':
        # Discount factors
        free.setParameter('discount',0.9)
        sylv.setParameter('discount',0.9)

    # Levels of belief
    free.setRecursiveLevel(2)
    sylv.setRecursiveLevel(2)

    # Dynamics of battle
    freeTroops = stateKey(free.name,'troops')
    freeTerr = stateKey(free.name,'territory')
    sylvTroops = stateKey(sylv.name,'troops')
    # Effect of fighting
    for action in filterActions({'verb': 'attack'},free.actions | sylv.actions):
        # Effect on troops (cost of battle)
        tree = makeTree(addFeatureMatrix(freeTroops,stateKey(free.name,'cost'),-1.))
        world.setDynamics(free.name,'troops',action,tree)
        tree = makeTree(addFeatureMatrix(sylvTroops,stateKey(sylv.name,'cost'),-1.))
        world.setDynamics(sylv.name,'troops',action,tree)
        if model == 'powell':
            # Effect on territory (probability of collapse)
            tree = makeTree({'distribution': [
                        ({'distribution': [(setToConstantMatrix(freeTerr,100),1.-fCollapse), # Sylvania collapses, Freedonia does not
                                           (noChangeMatrix(freeTerr),         fCollapse)]},  # Both collapse
                         sCollapse),
                        ({'distribution': [(setToConstantMatrix(freeTerr,0),fCollapse),      # Freedonia collapses, Sylvania does not
                                           (noChangeMatrix(freeTerr),       1.-fCollapse)]}, # Neither collapse
                         1.-sCollapse)]})
            world.setDynamics(free.name,'territory',action,tree)
        elif model == 'slantchev':
            # Effect on position
            pos = stateKey(free.name,'position')
            tree = makeTree({'distribution': [(incrementMatrix(pos,1),1.-fCollapse), # Freedonia wins battle
                                              (incrementMatrix(pos,-1),fCollapse)]}) # Freedonia loses battle
            world.setDynamics(free.name,'position',action,tree)

    # Dynamics of offers
    for index in range(2):
        atom =  Action({'subject': world.agents.keys()[index],'verb': 'offer',
                        'object': world.agents.keys()[1-index]})
        offer = stateKey(atom['object'],'offered')
        amount = actionKey('amount')
        tree = makeTree({'if': trueRow(stateKey(None,'treaty')),
                         True: noChangeMatrix(offer),
                         False: setToConstantMatrix(offer,amount)})
        world.setDynamics(atom['object'],'offered',atom,tree)

    # Dynamics of treaties
    for action in filterActions({'verb': 'accept offer'},free.actions | sylv.actions):
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
            tree = makeTree(setToFeatureMatrix(territory,offer))
            world.setDynamics(free.name,'territory',action,tree)
        else:
            # Sylvania accepts sets territory to 1-last offer
            tree = makeTree(setToFeatureMatrix(territory,offer,pct=-1.,shift=100.))
            world.setDynamics(free.name,'territory',action,tree)

    # Dynamics of phase
    # OFFER -> RESPOND
    for index in range(2):
        action = Action({'subject': world.agents.keys()[index],'verb': 'offer',
                         'object': world.agents.keys()[1-index]})
        tree = makeTree(setToConstantMatrix(stateKey(None,'phase'),'respond'))
        world.setDynamics(None,'phase',action,tree)
    # RESPOND -> REJECTION or ENGAGEMENT
    for action in filterActions({'verb': 'reject offer'},free.actions | sylv.actions):
        if model == 'powell':
            tree = makeTree(setToConstantMatrix(stateKey(None,'phase'),'rejection'))
        elif model == 'slantchev':
            tree = makeTree(setToConstantMatrix(stateKey(None,'phase'),'engagement'))
        world.setDynamics(None,'phase',action,tree)
    # accepting -> OFFER
    for action in filterActions({'verb': 'accept offer'},free.actions | sylv.actions):
        tree = makeTree(setToConstantMatrix(stateKey(None,'phase'),'offer'))
        world.setDynamics(None,'phase',action,tree)
    # attacking -> OFFER
    for action in filterActions({'verb': 'attack'},free.actions | sylv.actions):
        tree = makeTree(setToConstantMatrix(stateKey(None,'phase'),'offer'))
        world.setDynamics(None,'phase',action,tree)
        tree = makeTree(incrementMatrix(stateKey(None,'round'),1))
        world.setDynamics(None,'round',action,tree)
    if model == 'powell':
        # REJECTION -> END
        for atom in [freeNOP,freeBattle]:
            tree = makeTree(setToConstantMatrix(stateKey(None,'phase'),'end'))
            world.setDynamics(None,'phase',atom,tree)
        # END -> OFFER
        atom =  Action({'subject': sylv.name,'verb': 'continue'})
        tree = makeTree(setToConstantMatrix(stateKey(None,'phase'),'offer'))
        world.setDynamics(None,'phase',atom,tree)
        tree = makeTree(incrementMatrix(stateKey(None,'round'),1))
        world.setDynamics(None,'round',atom,tree)
    
    # # Models of Freedonia
    # free.addModel('dove',R={goalFTroops: 1e-4,goalFTerritory: 0.1},level=1,rationality=0.01)
    # free.addModel('true',level=1,rationality=0.01)
    # free.addModel('hawk',R={goalFTroops: 1e-4,goalFTerritory: 0.3},level=1,rationality=0.01)
    # world.setMentalModel(sylv.name,free.name,{'true': 0.6,'dove': 0.3,'hawk': 0.1})
    return world

def scenarioSimulationUseCase(world,offer=10,rounds=1,debug=1):
    """
    @param offer: the initial offer for Freedonia to give (default is 10)
    @type offer: int
    @param rounds: the number of complete rounds, where a round is two turns each, following Powell (default is 1)
    @type rounds: int
    @param debug: the debug level to use in explanation (default is 1)
    @type debug: int
    """
    free = world.agents['Freedonia']
    sylv = world.agents['Sylvania']
    world.setState(None,'phase','offer')
    if debug > 0:
        world.printState()

    for t in range(rounds*2):
        assert len(world.state) == 1
        if not world.terminated(world.state.domain()[0]):
            if t == 0:
                # Force Freedonia to make low offer in first step
                world.explain(world.step({free.name: Action({'subject':free.name,'verb':'offer','object': sylv.name,'amount': offer})}),debug)
            else:
                # Freedonia is free to choose
                world.explain(world.step(),debug)
            world.state.select()
            if debug > 0:
                world.printState()
                # Display Sylvania's posterior beliefs
                # sylv.printBeliefs()

        assert len(world.state) == 1
        if not world.terminated(world.state.domain()[0]):
            # Sylvania free to decide in second step
            world.explain(world.step(),debug)
            world.state.select()
            if debug > 0:
                world.printState()

if __name__ == '__main__':
    # Grab command-line arguments
    parser = ArgumentParser()
    # Optional argument that sets the filename for the output file
    parser.add_argument('-o',action='store',
                      dest='output',default='default',
                      help='scenario file [default: %(default)s]')
    group = parser.add_argument_group('Creation Options','Control the parameters of the created scenario.')
    # Optional argument that sets the theoretical model
    group.add_argument('-m',action='store',
                     dest='model',choices=['powell','slantchev'],default='powell',
                     help='theoretical model for the game [default: %(default)s]')
    # Optional argument that sets the cost of battle to Freedonia
    group.add_argument('-f',action='store',
                     dest='fcost',type=int,default=2837,
                     help='cost of battle to Freedonia [default: %(default)s]')
    # Optional argument that sets the cost of battle to Sylvania
    group.add_argument('-s',action='store',
                     dest='scost',type=int,default=1013,
                     help='cost of battle to Sylvania [default: %(default)s]')
    # Optional argument that sets the initial amount of territory owned by Freedonia
    group.add_argument('-i',action='store',
                     dest='initial',type=int,default=13,
                     help='Freedonia\'s initial territory percentage [default: %(default)s]')
    # Optional argument that sets the maximum number of rounds to play
    group.add_argument('-r',action='store',
                     dest='rounds',type=int,default=15,
                     help='Maximum number of rounds to play [default: %(default)s]')
    # Optional argument that sets Freedonia's initial troops
    group.add_argument('--freedonia-troops',action='store',
                     dest='ftroops',type=int,default=381940,
                     help='number of Freedonia troops [default: %(default)s]')
    # Optional argument that sets Sylvania's initial troops
    group.add_argument('--sylvania-troops',action='store',
                     dest='stroops',type=int,default=461432,
                     help='number of Sylvania troops [default: %(default)s]')
    group = parser.add_argument_group('Simulation Options','Control the simulation of the created scenario.')
    # Optional argument that sets the level of explanations when running the simulation
    group.add_argument('-d',action='store',
                     dest='debug',type=int,default=1,
                     help='level of explanation detail [default: %(default)s]')
    # Optional argument that sets the initial offer that Freedonia will make
    group.add_argument('-a',action='store',
                     dest='amount',type=int,default=10,
                     help='Freedonia\'s first offer amount [default: %(default)s]')
    # Optional argument that sets the number of time steps to simulate
    group.add_argument('-t','--time',action='store',
                     dest='time',type=int,default=4,
                     help='number of time steps to simulate [default: %(default)s]')
    args = vars(parser.parse_args())

    world = scenarioCreationUseCase(args['fcost'],args['scost'],territory=args['initial'],
                                    fTroops=args['ftroops'],sTroops=args['stroops'],
                                    maxRounds=args['rounds'],model=args['model'])

    # Create configuration file
    config = SafeConfigParser()
    # Specify game options for web interface
    config.add_section('Game')
    config.set('Game','rounds','%d' % (args['rounds']))
    assert world.agents.has_key('Freedonia')
    config.set('Game','user','Freedonia')
    # Specify which state features are visible in web interface
    config.add_section('Visible')
    for feature in world.features['Freedonia'].keys():
        if feature in ['territory','troops']:
            config.set('Visible',feature,'yes')
        else:
            config.set('Visible',feature,'no')
    # Specify descriptions of actions for web interface
    config.add_section('Actions')
    config.set('Actions','offer','Propose treaty where Sylvania gets amount%% of total disputed territory')
    config.set('Actions','attack','Attack Sylvania')
    config.set('Actions','continue','Continue to next day of negotiation without attacking')
    f = open('default.cfg','w')
    config.write(f)
    f.close()

    # Save scenario to compressed XML file
    world.save(args['output'])

    # Test saved scenario
    world = World(args['output'])
    scenarioSimulationUseCase(world,args['amount'],args['rounds'],args['debug'])
