"""
Example scenario for wartime negotiation.
Provides use cases for both modeling and simulating scenarios.
"""
import sys
from ConfigParser import SafeConfigParser
from argparse import ArgumentParser
import StringIO

from psychsim.pwl import *
from psychsim.reward import *
from psychsim.action import *
from psychsim.world import World,stateKey,actionKey,binaryKey,modelKey
from psychsim.agent import Agent

def scenarioCreationUseCase(enemy='Sylvania',model='powell',web=False,
                            fCollapse=None,sCollapse=None,maxRounds=15):
    """
    An example of how to create a scenario
    @param enemy: the name of the agent-controlled side, i.e., Freedonia's opponent (default: Sylvania)
    @type enemy: str
    @param model: which model do we use (default is "powell")
    @type model: powell or slantchev
    @param web: if C{True}, then create the web-based experiment scenario (default: C{False})
    @type web: bool
    @param fCollapse: the probability that Freedonia collapses (under powell, default: 0.1) or loses battle (under slantchev, default: 0.7)
    @type fCollapse: float
    @param sCollapse: the probability that Sylvania collapses, under powell (default: 0.1)
    @type sCollapse: float
    @param maxRounds: the maximum number of game rounds (default: 15)
    @type maxRounds: int
    @return: the scenario created
    @rtype: L{World}
    """
    # Handle defaults for battle probabilities, under each model
    posLo = 0
    posHi = 10
    if fCollapse is None:
        if model == 'powell':
            fCollapse = 0.1
        elif model == 'slantchev':
            fCollapse = 0.7
    if sCollapse is None:
        sCollapse = 0.1

    # Create scenario
    world = World()

    # Agents
    free = Agent('Freedonia')
    world.addAgent(free)
    sylv = Agent(enemy)
    world.addAgent(sylv)

    # User state
    world.defineState(free.name,'troops',int,lo=0,hi=50000,
                      description='Number of troops you have left')
    free.setState('troops',40000)
    world.defineState(free.name,'territory',int,lo=0,hi=100,
                      description='Percentage of disputed territory owned by you')
    free.setState('territory',15)
    world.defineState(free.name,'cost',int,lo=0,hi=50000,
                      description='Number of troops %s loses in an attack' % (free.name))
    free.setState('cost',2000)
    world.defineState(free.name,'position',int,lo=posLo,hi=posHi,
                      description='Current status of war (%d=%s is winner, %d=you are winner)' % (posLo,sylv.name,posHi))
    free.setState('position',5)
    world.defineState(free.name,'offered',int,lo=0,hi=100,
                      description='Percentage of disputed territory that %s last offered to you' % (sylv.name))
    free.setState('offered',0)
    if model == 'slantchev':
        # Compute new value for territory only *after* computing new value for position
        world.addDependency(stateKey(free.name,'territory'),stateKey(free.name,'position'))

    # Agent state
    world.defineState(sylv.name,'troops',int,lo=0,hi=500000,
                      description='Number of troops %s has left' % (sylv.name))
    sylv.setState('troops',30000)
    world.defineState(sylv.name,'cost',int,lo=0,hi=50000,
                      description='Number of troops %s loses in an attack' % (sylv.name))
    sylv.setState('cost',2000)
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
    # Game model, static descriptor
    world.defineState(None,'model',list,['powell','slantchev'],
                      description='The model underlying the negotiation game')
    world.setState(None,'model',model)
    # Round of negotiation
    world.defineState(None,'round',int,description='The current round of the negotiation')
    world.setState(None,'round',0)

    if not web:
        # Relationship value
        key = world.defineRelation(free.name,sylv.name,'trusts')
        world.setFeature(key,0.)
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
#    world.setOrder([set(world.agents.keys())])
    # Turn order: Uncomment the following if you want agents to act sequentially
    world.setOrder([free.name,sylv.name])

    # User actions
    freeBattle = free.addAction({'verb': 'attack','object': sylv.name})
    for amount in range(20,100,20):
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
        for amount in range(10,100,10):
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
    free.setReward(goalFTerritory,1.)

    # Goals for Sylvania
    goalSTroops = maximizeFeature(stateKey(sylv.name,'troops'))
    sylv.setReward(goalSTroops,1.)
    goalSTerritory = minimizeFeature(stateKey(free.name,'territory'))
    sylv.setReward(goalSTerritory,1.)

    # Possible goals applicable to both
    goalAgreement = maximizeFeature(stateKey(None,'treaty'))

    # Silly goal, provided as an example of an achievement goal
    goalAchieve = achieveFeatureValue(stateKey(None,'phase'),'respond')

    # Horizons
    if model == 'powell':
        free.setAttribute('horizon',4)
        sylv.setAttribute('horizon',4)
    elif model == 'slantchev':
        free.setAttribute('horizon',6)
        sylv.setAttribute('horizon',6)

    # Discount factors
    free.setAttribute('discount',-1)
    sylv.setAttribute('discount',-1)

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
        world.setDynamics(freeTroops,action,tree,enforceMin=not web)
        tree = makeTree(addFeatureMatrix(sylvTroops,stateKey(sylv.name,'cost'),-1.))
        world.setDynamics(sylvTroops,action,tree,enforceMin=not web)
        if model == 'powell':
            # Effect on territory (probability of collapse)
            tree = makeTree({'distribution': [
                        ({'distribution': [(setToConstantMatrix(freeTerr,100),1.-fCollapse), # Sylvania collapses, Freedonia does not
                                           (noChangeMatrix(freeTerr),         fCollapse)]},  # Both collapse
                         sCollapse),
                        ({'distribution': [(setToConstantMatrix(freeTerr,0),fCollapse),      # Freedonia collapses, Sylvania does not
                                           (noChangeMatrix(freeTerr),       1.-fCollapse)]}, # Neither collapses
                         1.-sCollapse)]})
            world.setDynamics(freeTerr,action,tree)
        elif model == 'slantchev':
            # Effect on position
            pos = stateKey(free.name,'position')
            tree = makeTree({'distribution': [(incrementMatrix(pos,1),1.-fCollapse), # Freedonia wins battle
                                              (incrementMatrix(pos,-1),fCollapse)]}) # Freedonia loses battle
            world.setDynamics(pos,action,tree)
            # Effect on territory
            tree = makeTree({'if': thresholdRow(pos,posHi-.5), 
                             True: setToConstantMatrix(freeTerr,100),          # Freedonia won
                             False: {'if': thresholdRow(pos,posLo+.5),
                                     True: noChangeMatrix(freeTerr),
                                     False: setToConstantMatrix(freeTerr,0)}}) # Freedonia lost
            world.setDynamics(freeTerr,action,tree)

    # Dynamics of offers
    for index in range(2):
        atom =  Action({'subject': world.agents.keys()[index],'verb': 'offer',
                        'object': world.agents.keys()[1-index]})
        if atom['subject'] == free.name or model != 'powell':
            offer = stateKey(atom['object'],'offered')
            amount = actionKey('amount')
            tree = makeTree({'if': trueRow(stateKey(None,'treaty')),
                             True: noChangeMatrix(offer),
                             False: setToConstantMatrix(offer,amount)})
            world.setDynamics(offer,atom,tree,enforceMax=not web)

    # Dynamics of treaties
    for action in filterActions({'verb': 'accept offer'},free.actions | sylv.actions):
        # Accepting an offer means that there is now a treaty
        key = stateKey(None,'treaty')
        tree = makeTree(setTrueMatrix(key))
        world.setDynamics(key,action,tree)
        # Accepting offer sets territory
        offer = stateKey(action['subject'],'offered')
        territory = stateKey(free.name,'territory')
        if action['subject'] == free.name:
            # Freedonia accepts sets territory to last offer
            tree = makeTree(setToFeatureMatrix(territory,offer))
            world.setDynamics(freeTerr,action,tree)
        else:
            # Sylvania accepts sets territory to 1-last offer
            tree = makeTree(setToFeatureMatrix(territory,offer,pct=-1.,shift=100.))
            world.setDynamics(freeTerr,action,tree)

    # Dynamics of phase
    phase = stateKey(None,'phase')
    roundKey = stateKey(None,'round')
    # OFFER -> RESPOND
    for index in range(2):
        action = Action({'subject': world.agents.keys()[index],'verb': 'offer',
                         'object': world.agents.keys()[1-index]})
        if action['subject'] == free.name or model != 'powell':
            tree = makeTree(setToConstantMatrix(phase,'respond'))
            world.setDynamics(phase,action,tree)
    # RESPOND -> REJECTION or ENGAGEMENT
    for action in filterActions({'verb': 'reject offer'},free.actions | sylv.actions):
        if model == 'powell':
            tree = makeTree(setToConstantMatrix(phase,'rejection'))
        elif model == 'slantchev':
            tree = makeTree(setToConstantMatrix(phase,'engagement'))
        world.setDynamics(phase,action,tree)
    # accepting -> OFFER
    for action in filterActions({'verb': 'accept offer'},free.actions | sylv.actions):
        tree = makeTree(setToConstantMatrix(phase,'offer'))
        world.setDynamics(phase,action,tree)
    # attacking -> OFFER
    for action in filterActions({'verb': 'attack'},free.actions | sylv.actions):
        tree = makeTree(setToConstantMatrix(phase,'offer'))
        world.setDynamics(phase,action,tree)
        if action['subject'] == sylv.name or model == 'slantchev':
            tree = makeTree(incrementMatrix(roundKey,1))
            world.setDynamics(roundKey,action,tree)
    if model == 'powell':
        # REJECTION -> END
        for atom in [freeNOP,freeBattle]:
            tree = makeTree(setToConstantMatrix(phase,'end'))
            world.setDynamics(phase,atom,tree)
        # END -> OFFER
        atom =  Action({'subject': sylv.name,'verb': 'continue'})
        tree = makeTree(setToConstantMatrix(phase,'offer'))
        world.setDynamics(phase,atom,tree)
        tree = makeTree(incrementMatrix(roundKey,1))
        world.setDynamics(roundKey,atom,tree)


    if not web:
        # Relationship dynamics: attacking is bad for trust
        atom =  Action({'subject': sylv.name,'verb': 'attack','object': free.name})
        key = binaryKey(free.name,sylv.name,'trusts')
        tree = makeTree(approachMatrix(key,0.1,-1.))
        world.setDynamics(key,atom,tree)
    # Handcrafted policy for Freedonia
#    free.setPolicy(makeTree({'if': equalRow('phase','respond'),
#                             # Accept an offer greater than 50
#                             True: {'if': thresholdRow(stateKey(free.name,'offered'),50),
#                                    True: Action({'subject': free.name,'verb': 'accept offer','object': sylv.name}),
#                                    False: Action({'subject': free.name,'verb': 'reject offer','object': sylv.name})},
#                             False: {'if': equalRow('phase','engagement'),
#                             # Attack during engagement phase
#                                     True: Action({'subject': free.name,'verb': 'attack','object': sylv.name}),
#                             # Agent decides how what to do otherwise
#                                     False: False}}))
        # Mental models of enemy
        # Example of creating a model with incorrect reward all at once (a version of Freedonia who cares about reaching agreement as well)
        # sylv.addModel('false',R={goalSTroops: 10.,goalSTerritory: 1.,goalAgreement: 1.},
        #              rationality=1.,selection='distribution',parent=True)
        # Example of creating a model with incorrect beliefs
        sylv.addModel('false',rationality=10.,selection='distribution',parent=True)
        key = stateKey(free.name,'position')
        # Sylvania believes position to be fixed at 3
        sylv.setBelief(key,3,'false')

        # Freedonia is truly unsure about position (50% chance of being 7, 50% of being 3)
        world.setModel(free.name,True)
        free.setBelief(key,Distribution({7: 0.5,3: 0.5}),True)
        # Observations about military position
        tree = makeTree({'if': thresholdRow(key,1),
                         True: {'if': thresholdRow(key,9),
                                True: {'distribution': [(KeyedVector({key: 1}),0.9),
                                                        (KeyedVector({key: 1,CONSTANT: -1}),0.1)]},
                                False: {'distribution': [(KeyedVector({key: 1}),0.8),
                                                         (KeyedVector({key: 1,CONSTANT: -1}),0.1),
                                                         (KeyedVector({key: 1,CONSTANT: 1}),0.1)]}},
                         False: {'distribution': [(KeyedVector({key: 1}),0.9),
                                                  (KeyedVector({key: 1,CONSTANT: 1}),0.1)]}})
        free.defineObservation(key,tree)

        # Example of setting model parameters separately
        sylv.addModel('true',parent=True)
        sylv.setAttribute('rationality',10.,'true') # Override real agent's rationality with this value
        sylv.setAttribute('selection','distribution','true')
        world.setMentalModel(free.name,sylv.name,{'false': 0.9,'true': 0.1})
        
        # Goal of fooling Sylvania
        goalDeception = achieveFeatureValue(modelKey(sylv.name),sylv.model2index('false'))
    return world

def compileWorld(world):
    # First, let's set the start state
    world.setState(None,'phase','offer')
    # Um, not sure about this one
    world.agents[args['enemy']].setAttribute('rationality',10.)
    # Then, do value iteration to pre-compute Freedonia's policy
    world.agents['Freedonia'].valueIteration(horizon=-1,debug=1)

def fitWorld(world):
    """
    Piecewise linear compilation of Freedonia's policy
    """
    for agent in world.agents.values():
        if agent.name == 'Freedonia':
            free = agent
        else:
            sylv = agent
    world.setState(None,'phase','offer')
    state = world.state.domain()[0]
    freeModel = world.getModel(free.name,state)
    beliefs = free.getBelief(state,freeModel)
    # Compute transition trees
    T = {}
    for agent in world.agents.values():
        for action in agent.actions:
            T[action] = None
            for keys in world.evaluationOrder:
                result = None
                for key in keys:
                    dynamics = world.getDynamics(key,action)
                    if dynamics:
                        # Use existing tree
                        assert len(dynamics) == 1
                        dynamics = dynamics[0]
                    else:
                        # Create identity tree
                        dynamics = KeyedTree(noChangeMatrix(key))
                    if result is None:
                        result = dynamics
                    else:
                        result += dynamics
                result += KeyedTree(noChangeMatrix(CONSTANT))
                if T[action] is None:
                    T[action] = result
                else:
                    T[action] = result*T[action]
    # Compute policy trees for the other agent
    models = {}
    for agent in world.agents.values():
        models[agent.name] = set()
    for agent in world.agents.values():
        for vector in beliefs.domain():
            model = world.getModel(agent.name,vector)
            ancestor = agent.findAttribute('R',model)
            models[agent.name].add(ancestor)
        if len(models[agent.name]) == 0:
            # No beliefs about models found, assume True model
            models[agent.name].add(True)
    for agent in world.agents.values():
        for model in models[agent.name]:
            R = sum(agent.getAttribute('R',model),KeyedTree(KeyedVector()))
            agent.models[model]['policy'] = []
            policy = agent.models[model]['policy']
            for horizon in range(1,agent.getAttribute('horizon',model)+1):
                # Dynamic programming of policies
                if len(policy) < horizon:
                    # Policy tree for this horizon is missing
                    legal = {}
                    actions = []
                    # Process legality conditions
                    for action in agent.actions:
                        try:
                            legal[action] = agent.legal[action]
                        except KeyError:
                            legal[action] = KeyedTree(True)
                    # Compute value functions for each action
                    if horizon > 1:
                        raise NotImplementedError,'Backup step is missing'
                    V = {}
                    for action in agent.actions:
                        V[action] = R*T[action]
                        V[action] = legal[action].replace(True,V[action])
                        V[action] = V[action].expectation()
                        V[action] = V[action].map(lambda leaf: {'vector': leaf,'action': action} if isinstance(leaf,KeyedVector) else leaf)
                    # Build up a policy
                    policy.append(None)
                    for action in agent.actions:
                        if policy[horizon-1] is None:
                            policy[horizon-1] = V[action]
                        else:
                            policy[horizon-1] = policy[horizon-1].max(V[action])
                    Vstar = policy[horizon-1].map(lambda leaf: leaf['vector'] if isinstance(leaf,dict) else leaf)
                    policy[horizon-1] = policy[horizon-1].map(lambda leaf: leaf['action'] 
                                                              if isinstance(leaf,dict) else leaf)
    #                print 'Unpruned:'
                    policy[horizon-1].minimizePlanes()
    #                print policy[horizon-1]
                    pruned = policy[horizon-1].prune()
    #                print 'Pruned:'
                    print pruned
                    # # Verify pruning
                    # world.setFeature('phase','respond',beliefs)
                    # world.setState('Freedonia','territory',72,beliefs)
                    # for offer in range(50,100,3):
                    #     world.setState(agent.name,'offered',offer,beliefs)
                    #     vector = beliefs.domain()[0]
                    #     print offer
                    #     print policy[horizon-1][vector],pruned[vector]
                    #     assert policy[horizon-1][vector] == pruned[vector]
                    print free.models[freeModel]['beliefs']
                break
    sys.exit(0)
                                 

def scenarioSimulationUseCase(world,offer=0,rounds=1,debug=1,model='powell'):
    """
    @param offer: the initial offer for Freedonia to give (default is none)
    @type offer: int
    @param rounds: the number of complete rounds, where a round is two turns each, following Powell (default is 1)
    @type rounds: int
    @param debug: the debug level to use in explanation (default is 1)
    @type debug: int
    """
    testMode = isinstance(debug,dict)
    if testMode:
        buf = StringIO.StringIO()
        debug[offer] = buf
        debug = 0
    for agent in world.agents.values():
        if agent.name == 'Freedonia':
            free = agent
        else:
            sylv = agent
    world.setState(None,'phase','offer')

    if model == 'powell':
        steps = 4
    else:
        assert model == 'slantchev'
        steps = 3

    if debug > 0:
        world.printState(beliefs=True)

    for t in range(rounds):
        for step in range(steps):
            assert len(world.state) == 1
            phase = world.getState(None,'phase').expectation()
            state = world.state.domain()[0]
            if not world.terminated(state):
                if t == 0 and phase == 'offer' and offer > 0:
                    # Force Freedonia to make low offer in first step
                    outcome = world.step({free.name: Action({'subject':free.name,'verb':'offer','object': sylv.name,'amount': offer})})
                    world.explain(outcome,debug)
                else:
                    # Free to choose
                    outcome = world.step()
                    world.explain(outcome,debug)
                    if testMode:
                        if (t == 0 and step == 1) or (t == 1 and step == 0):
                            for entry in outcome:
                                world.explainAction(entry,buf,1)
                world.state.select()
                if not testMode and debug > 0:
                    world.printState(beliefs=True)
                for agent in world.agents.values():
                    print agent.name,len(agent.models)
            assert len(world.state) == 1
            phase = world.getState(None,'phase').expectation()
            if phase == 'offer':
                # Looped around
                break

def findThreshold(scenario,t,model='powell',position=0):
    """
    Finds the threshold at which the agent will accept the offer"""
    if model == 'slantchev':
        # Find counteroffer in this state
        actions = []
        while len(actions) < 2:
            world = World(scenario)
            world.setState(None,'round',t)
            world.setState('Freedonia','position',position)
            entry = {}
            scenarioSimulationUseCase(world,20,2,entry,model)
            actions = entry[20].getvalue().split('\n')[:-1]
            entry[20].close()
        amount = int(actions[1].split('-')[-1])
        print 'Time: %d, Position %d -> Offer %d%%' % (t,position,amount)
    # Compute acceptance threshold
    offers = [50]
    index = 0
    entry = {}
    while True:
        world = World(scenario)
        world.setState(None,'round',t)
        if model == 'slantchev':
            world.setState('Freedonia','position',position)
        scenarioSimulationUseCase(world,offers[index],1,entry,model)
        actions = entry[offers[index]].getvalue().split('\n')[:-1]
        entry[offers[index]].close()
        entry[offers[index]] = actions[0].split('-')[1].split()[0]
        if entry[offers[index]] == 'accept':
            # Try a lower offer
            if index > 0:
                down = offers[index-1]
                assert entry[down] != 'accept'
            else:
                down = 0
            new = (offers[index]+down) / 2
            if entry.has_key(new):
                if entry[new] != 'accept':
                    new += 1
                break
            else:
                offers.insert(index,new)
        else:
            assert entry[offers[index]] in ['reject','attack']
            # Try a higher offer
            try:
                up = offers[index+1]
                assert entry[up] == 'accept'
            except IndexError:
                up = 100
            new = (offers[index]+up) / 2
            if entry.has_key(new):
                break
            else:
                offers.insert(index+1,new)
                index += 1
    return new

def play(world,debug=1):
    """
    Modify Freedonia to play autonomously and simulate
    """
    for agent in world.agents.values():
        if agent.name == 'Freedonia':
            free = agent
        else:
            sylv = agent
    for amount in range(10,100,20):
        action = Action({'verb': 'offer','object': sylv.name,'amount': amount})
        free.addAction(action)
        action = Action({'verb': 'offer','object': free.name,'amount': amount})
        sylv.addAction(action)
    for action in filterActions({'verb': 'offer'},free.actions | sylv.actions):
        actor = world.agents[action['subject']]
        if not actor.legal.has_key(action):
            actor.setLegal(action,makeTree({'if': equalRow(stateKey(None,'phase'),'offer'),
                                           True: True,     # Offers are legal in the offer phase
                                           False: False})) # Offers are illegal in all other phases
    model = world.getState(None,'model').domain()[0]
    start = world.getState(free.name,'territory').expectation()
    print model,start
    scenarioSimulationUseCase(world,offer=0,rounds=15,debug=debug,model=model)

def findPolicies(args):
    """
    Wrapper for finding agent offers and acceptance thresholds
    """
    results = []
    search = (30,40,1)
    for t in range(args['rounds']):
        entry = {}
        if args['model'] == 'slantchev':
            for position in range(1,10):
                subresult = []
                results.append(subresult)
                subresult.append(entry)
                thresh = findThreshold(args['output'],t,args['model'],position)
                print 'Time %d, Position %d -> Accept if > %d%%' % (t,position,thresh)
        else:
            results.append(entry)
            print 'Time %d -> Accept if > %d%%' %(t,findThreshold(args['output'],t))

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
                     dest='fcost',type=int,default=2000,
                     help='cost of battle to Freedonia [default: %(default)s]')
    # Optional argument that sets the cost of battle to Sylvania
    group.add_argument('-s',action='store',
                     dest='scost',type=int,default=1000,
                     help='cost of battle to enemy [default: %(default)s]')
    # Optional argument that sets the initial amount of territory owned by Freedonia
    group.add_argument('-i','--initial',action='store',
                     dest='initial',type=int,default=13,
                     help='Freedonia\'s initial territory percentage [default: %(default)s]')
    # Optional argument that sets Freedonia's initial military positional advantage
    group.add_argument('-p','--position',action='store',
                     dest='position',type=int,default=3,
                     help='Freedonia\'s initial positional advantage [default: %(default)s]')
    # Optional argument that sets the name of the enemy country
    group.add_argument('-e',action='store',
                     dest='enemy',default='Sylvania',
                     help='Name of the enemy country [default: %(default)s]')
    # Optional argument that sets the name of the disputed region
    group.add_argument('--region',action='store',
                     dest='region',default='Trentino',
                     help='Name of the region under dispute [default: %(default)s]')
    # Optional argument that sets the maximum number of rounds to play
    group.add_argument('-r',action='store',
                     dest='rounds',type=int,default=15,
                     help='Maximum number of rounds to play [default: %(default)s]')
    # Optional argument that sets Freedonia's initial troops
    group.add_argument('--freedonia-troops',action='store',
                     dest='ftroops',type=int,default=40000,
                     help='number of Freedonia troops [default: %(default)s]')
    # Optional argument that sets Sylvania's initial troops
    group.add_argument('--enemy-troops',action='store',
                     dest='stroops',type=int,default=30000,
                     help='number of enemy troops [default: %(default)s]')
    # Optional argument that determines whether to generate models for Web platform
    group.add_argument('-w','--web',action='store_true',
                      dest='web',default=False,
                      help='generate Web version if set [default: %(default)s]')

    group = parser.add_argument_group('Algorithm Options','Control the algorithms to apply to the agents.')
    # Optional argument that determines whether to use value iteration to create Freedonia's policy
    group.add_argument('-c','--compiled',action='store_true',
                      dest='compiled',default=False,
                      help='use value iteration for Freedonia [default: %(default)s]')
    # Optional argument that determines whether to use PWL compilation of Freedonia's policy
    group.add_argument('--fitting',action='store_true',
                      dest='fitting',default=False,
                      help='use PWL compilation and fitting for Freedonia [default: %(default)s]')

    group = parser.add_argument_group('Simulation Options','Control the simulation of the created scenario.')
    # Optional argument that sets the level of explanations when running the simulation
    group.add_argument('-d',action='store',
                     dest='debug',type=int,default=1,
                     help='level of explanation detail [default: %(default)s]')
    # Optional argument that sets the initial offer that Freedonia will make
    group.add_argument('-a',action='store',
                     dest='amount',type=int,default=0,
                     help='Freedonia\'s first offer amount')
    # Optional argument that sets the number of time steps to simulate
    group.add_argument('-t','--time',action='store',
                     dest='time',type=int,default=1,
                     help='number of time steps to simulate [default: %(default)s]')
    group = parser.add_argument_group('Creation Options','Control the parameters of the created scenario.')
    args = vars(parser.parse_args())

    world = scenarioCreationUseCase(args['enemy'],maxRounds=args['rounds'],model=args['model'],
                                    web=args['web'])

    # Initialize state values based on command-line arguments
    world.agents['Freedonia'].setState('troops',args['ftroops'])
    world.agents['Freedonia'].setState('territory',args['initial'])
    world.agents['Freedonia'].setState('position',args['position'])
    world.agents['Freedonia'].setState('cost',args['fcost'])
    world.agents[args['enemy']].setState('troops',args['stroops'])
    world.agents[args['enemy']].setState('cost',args['scost'])

    if args['compiled']:
        compileWorld(world)
    if args['fitting']:
        fitWorld(world)

    # Create configuration file
    config = SafeConfigParser()
    # Specify game options for web interface
    config.add_section('Game')
    config.set('Game','rounds','%d' % (args['rounds']))
    config.set('Game','user','Freedonia')
    config.set('Game','agent',args['enemy'])
    config.set('Game','region',args['region'])
    if args['model'] == 'powell':
        # Battle is optional under Powell
        config.set('Game','battle','optional')
    elif args['model'] == 'slantchev':
        # Battle is mandatory under Slantchev
        config.set('Game','battle','mandatory')
    # Specify which state features are visible in web interface
    config.add_section('Visible')
    features = ['territory','troops']
    if args['model'] == 'slantchev':
        features.append('position')
    for feature in features:
        config.set('Visible',feature,'yes')
    # Specify descriptions of actions for web interface
    config.add_section('Actions')
    config.set('Actions','offer','Propose treaty where %s gets <action:amount>%%%% of total disputed territory' % (args['enemy']))
    config.set('Actions','attack','Attack %s' % (args['enemy']))
    config.set('Actions','accept offer','Accept offer of <Freedonia:offered>%% of total disputed territory')
    config.set('Actions','reject offer','Reject offer of <Freedonia:offered>%% of total disputed territory')
    config.set('Actions','continue','Continue to next round of negotiation without attacking')
    config.set('Actions','%s offer' % (args['enemy']),'offer <action:amount>%%')
    config.set('Actions','%s accept offer' % (args['enemy']),
               'Accept offer of <%s:offered>%%%% of total disputed territory' % (args['enemy']))
    config.set('Actions','%s reject offer' % (args['enemy']),
               'Reject offer of <%s:offered>%%%% of total disputed territory' % (args['enemy']))
    # Specify what changes are displayed
    config.add_section('Change')
    config.set('Change','troops','yes')
    if args['model'] == 'slantchev':
        config.set('Change','position','yes')
    # Specify links
    config.add_section('Links')
    config.set('Links','survey','http://www.curiouslab.com/clsurvey/index.php?sid=39345&lang=en')
    config.set('Links','scenarios','8839,1308,2266,5538')
    f = open('%s.cfg' % (args['output']),'w')
    config.write(f)
    f.close()

    # Save scenario to compressed XML file
    world.save(args['output'])

    # Test saved scenario
    world = World(args['output'])
    scenarioSimulationUseCase(world,args['amount'],args['time'],args['debug'],args['model'])
#    findPolicies(args)
#    world.printState(world.agents[args['enemy']].getBelief(world.state.domain()[0],'false'))
