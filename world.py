from __future__ import print_function
import bz2
import copy
import logging
import io
from xml.dom.minidom import Document,Node,parseString

from psychsim.action import ActionSet,Action
import psychsim.probability
from psychsim.pwl import *
from psychsim.agent import Agent
import psychsim.graph

class World:
    """
    @ivar agents: table of agents in this world, indexed by name
    @type agents: strS{->}L{Agent}
    @ivar state: the distribution over states of the world
    @type state: strS{->}L{VectorDistribution}
    @ivar variables: definitions of the domains of possible variables (state features, relationships, observations)
    @type variables: dict
    @ivar symbols: utility storage of symbols used across all enumerated state variables
    @type symbols: strS{->}int
    @ivar dynamics: table of action effect models
    @type dynamics: dict
    @ivar dependency: dependency structure among state features that impose temporal constraints
    @type dependency: L{psychsim.graph.DependencyGraph}
    @ivar history: accumulated list of outcomes from simulation steps
    @type history: list
    @ivar termination: list of conditions under which the simulation terminates (default is none)
    @type termination: L{psychsim.pwl.KeyedTree}[]
    """
    memory = False

    def __init__(self,xml=None):
        """
        @param xml: Initialization argument, either an XML Element, or a filename
        @type xml: Node or str
        """
        self.agents = {}

        # State feature information
        self.state = VectorDistributionSet()
        self.variables = {}
        self.locals = {}
        self.symbols = {}
        self.symbolList = []
        self.termination = []
        self.relations = {}

        # Turn order state info
        self.maxTurn = None
        self.turnSubstate = None
        self.turnKeys = set()

        # Action effect information
        self.dynamics = {}
        self.newDynamics = {True: []}
        self.dependency = psychsim.graph.DependencyGraph(self)

        # Termination state info
        self.defineState(None,TERMINATED,bool)
        self.setFeature(TERMINATED,False)

        self.history = []

        self.diagram = None

        if isinstance(xml,Node):
            self.parse(xml)
        elif isinstance(xml,str):
            if xml[-4:] == '.xml':
                # Uncompressed
                f = open(xml,'r')
            else:
                if xml[-4:] != '.psy':
                    xml = '%s.psy' % (xml)
                f = bz2.BZ2File(xml,'r')
            doc = parseString(f.read())
            f.close()
            self.parse(doc.documentElement)

    def initialize(self):
        self.agents.clear()
        self.variables.clear()
        self.locals.clear()
        self.relations.clear()
        self.symbols.clear()
        del self.symbolList[:]
        self.dynamics.clear()
        self.dependency.clear()
        del self.history[:]
        del self.termination[:]
        self.state.clear()

    """------------------"""
    """Simulation methods"""
    """------------------"""
                
    def step(self,actions=None,state=None,real=True,select=False,keySubset=None,
             horizon=None,tiebreak=None,updateBeliefs=True):
        """
        The simulation method
        @param actions: optional argument setting a subset of actions to be performed in this turn
        @type actions: strS{->}L{ActionSet}
        @param state: optional initial state distribution (default is the current world state distribution)
        @type state: L{VectorDistribution}
        @param real: if C{True}, then modify the given state; otherwise, this is only hypothetical (default is C{True})
        @type real: bool
        """
        if state is None:
            state = self.state
        if real is False:
            state = copy.deepcopy(state)
        assert isinstance(state,VectorDistributionSet)
        outcome = {'old': state,
                   'decisions': {},
                   'effect': {}}
        # Check whether we are already in a terminal state
        if self.terminated(state):
            return state
        # Determine the actions taken by the agents in this world
        outcome['actions'] = self.stepPolicy(state,actions,horizon,tiebreak)
        for actor in outcome['actions']:
            key = stateKey(actor,ACTION)
            values = [e for e in state.domain(makeFuture(key))]
            choices = [self.float2value(key,e) for e in values]
            if len(choices) == 1:
                effect = self.effect(choices[0],state,updateBeliefs,keySubset)
                outcome['effect'].update(effect)
            else:
                print(choices)
                raise ValueError
        # The future becomes the present
        state.rollback()
        if select:
            newState = outcomes[0]['new']
            for dist in newState.distributions.values():
                dist.select()
        if self.memory:
            self.history.append(copy.deepcopy(state))
           # self.modelGC(False)
        return state

    def stepFromVector(self,vector,actions=None,horizon=None,tiebreak=None,updateBeliefs=True,keySubset=None,real=True):
        """
        Compute the resulting states when starting in a given possible world (as opposed to a distribution over possible worlds)
        """
        outcome = {'old': vector,
                   'decisions': {}}
        # Check whether we are already in a terminal state
        if self.terminated(vector):
            outcome['new'] = outcome['old']
            return outcome
        # Determine the actions taken by the agents in this world
        if actions is None:
            outcome['actions'] = {}
        else:
            if isinstance(actions,Action):
                actions = ActionSet([actions])
            outcome['actions'] = copy.copy(actions)
        # Keep track of whether there is uncertainty about the actions to perform
        stochastic = []
        if not isinstance(outcome['actions'],ActionSet) and not isinstance(outcome['actions'],list):
            # ActionSet indicates that we should perform just these actions. 
            # Otherwise, we look at whose turn it is:
            turn = self.next(vector)
            for name in outcome['actions'].keys():
                if not (name in turn):
                    raise NameError('Agent %s must wait for its turn' % (name))
            for name in turn:
                if not name in outcome['actions']:
                    model = self.getModel(name,vector)
                    decision = self.agents[name].decide(vector,None,horizon,outcome['actions'],model,tiebreak)
                    outcome['decisions'][name] = decision
                    outcome['actions'][name] = decision['action']
                elif isinstance(outcome['actions'][name],Action):
                    outcome['actions'][name] = ActionSet([outcome['actions'][name]])
                if isinstance(outcome['actions'][name],psychsim.probability.Distribution):
                    stochastic.append(name)
        if stochastic:
            # Merge effects of multiple possible actions into single effect
            if len(stochastic) > 1:
                raise NotImplementedError('Currently unable to handle stochastic expectations over multiple agents: %s' % (stochastic))
            effects = []
            for action in outcome['actions'][stochastic[0]].domain():
                prob = outcome['actions'][stochastic[0]][action]
                actions = dict(outcome['actions'])
                actions[stochastic[0]] = action 
                effect = self.effect(actions,outcome['old'],prob,updateBeliefs=updateBeliefs,keySubset=keySubset)
                if len(effect) == 0:
                    # No consistent transition for this action (don't blame me, I'm just the messenger)
                    continue
                elif 'new' in outcome:
                    for vector in effect['new'].domain():
                        try:
                            outcome['new'][vector] += effect['new'][vector]
                        except KeyError:
                            outcome['new'][vector] = effect['new'][vector]
                    outcome['effect'] += effect['effect']
                else:
                    outcome['new'] = effect['new']
                    outcome['effect'] = effect['effect']
        else:
            effect = self.effect(outcome['actions'],outcome['old'],1.,updateBeliefs,keySubset,real)
            outcome.update(effect)
        if 'effect' in outcome:
            if not 'new' in outcome:
                # Apply effects
                outcome['new'] = outcome['effect']*outcome['old']
            if not 'delta' in outcome:
                print(outcome['new'].__class__,outcome['old'].__class__)
                outcome['delta'] = outcome['new'] - outcome['old']
        else:
            # No consistent effect
            pass
        return outcome

    def stepPolicy(self,state=None,actions=None,horizon=None,tiebreak=None):
        if state is None:
            state = self.state
        if isinstance(actions,Action):
            actions = {actions['subject']: ActionSet({actions})}
        elif isinstance(actions,ActionSet):
            actions = {actions['subject']: actions}
        if isinstance(actions,dict):
            for name,policy in actions.items():
                if isinstance(policy,ActionSet):
                    # Transfer fixed action into policy
                    key = keys.stateKey(name,keys.ACTION)
                    actions[name] = makeTree({'if': equalRow(turnKey(name),0),
                                              True: setToConstantMatrix(key,policy),
                                              False: noChangeMatrix(key)})
                actions[name] = actions[name].desymbolize(self.symbols)
        else:
            assert actions is None
            actions = {}
        for name in self.agents:
            if not name in actions:
                # No action pre-specified
                key = keys.turnKey(name)
                if key in state.keyMap and 0 in state.domain(key):
                    # This agent might have a turn now
                    decision = self.agents[name].decide(state,horizon,actions,
                                                        None,tiebreak)
                    actions[name] = decision['policy']
        for name,policy in actions.items():
            state *= policy
        return actions

    def deltaTurn(self,state,actions):
        """
        Computes the change in the turn order based on the given actions
        @param start: The original state
        @param end: The final state (which will be modified to reflect the new turn order)
        @type start,end: L{VectorDistributionSet}
        @return: The dynamics functions applied to update the turn order
        """
        turnKeys = {k for k in state.keyMap.keys() if isTurnKey(k)}
        dynamics = {}
        for key in turnKeys:
            dynamics.update(self.getTurnDynamics(key,actions))
        return dynamics

    def deltaObservations(self,state,actions):
        """
        Computes the new observations for each agent in the given state 
        @warning: Does not currently enforce order between observations that have direct dependencies. If you want such a dependency, introduce a state feature to indirectly capture it. 
        """
        Ofuns = {}
        for name in self.agents:
            O = self.agents[name].getO(state,actions)
            if O:
                for key,tree in O.items():
                    Ofuns[key] = [tree]
        return Ofuns
        
    def effect(self,actions,state,updateBeliefs=True,keySubset=None):
        if not isinstance(state,VectorDistributionSet):
            state = psychsim.pwl.VectorDistributionSet(state)
        result = {'new': state}
        # Get effect on state variables
        result['effect'] = self.deltaState(actions,result['new'],keySubset)
        # Update turn order
        result['effect'].append(self.deltaTurn(result['new'],actions))
        # Generate observations
        result['effect'].append(self.deltaObservations(result['new'],actions))
        # Apply all of these update functions
        for stage in result['effect']:
            for key,dynamics in stage.items():
                if dynamics is None:
                    # No dynamics, so status quo
                    substate = result['new'].keyMap[key]
                    newKey = makeFuture(key)
                    result['new'].keyMap[newKey] = substate
                    dist = result['new'].distributions[substate]
                    for vector in dist.domain():
                        prob = dist[vector]
                        del dist[vector]
                        vector[newKey] = vector[key]
                        dist[vector] = prob
                else:
                    for tree in dynamics:
                        result['new'] *= tree
        if updateBeliefs:
            # Update agent models included in the original world
            # (after finding out possible new worlds)
            agentsModeled = [name for name in self.agents.keys()
                             if modelKey(name) in result['new'].keyMap]
            for name in agentsModeled:
                key = modelKey(name)
                agent = self.agents[name]
                Omega = {keys.makeFuture(keys.stateKey(agent.name,omega)) \
                         for omega in agent.omega}
                result['new'].collapse(Omega|{key},False)
                result['effect'].append(agent.updateBeliefs(result['new'],actions))
        return result

    def deltaState(self,actions,state,keySubset=None):
        """
        Computes the change across a subset of state features
        """
        # Figure out the order in which to update vector elements
        keyOrder = []
        for keySet in self.dependency.getEvaluation():
            if not keySubset is None:
                keySet = {k for k in keySet if k in keySubset}
            if len(keySet) > 0:
                keyOrder.append(keySet)
        effects = []
        for keySet in keyOrder:
            dynamics = {}
            for key in keySet:
                dynamics[key] = self.getDynamics(key,actions,state)
                if len(dynamics[key]) == 0:
                    # No dynamics, no change
                    dynamics[key] = None
            effects.append(dynamics)
        return effects

    def multiDeltaVector(self,actions,old,keys):
        new = psychsim.pwl.VectorDistribution({old: 1.})
        for key in keys:
            partial = self.singleDeltaVector(actions,old,key)
            if isinstance(partial,psychsim.pwl.KeyedVector):
                if key in partial:
                    new.join(key,psychsim.probability.Distribution({partial[key]: 1.}))
            else:
                new.join(key,partial.marginal(key))
        return new

    def singleDeltaVector(self,actions,old,key,dynamics=None):
        """
        @type old: L{psychsim.pwl.KeyedVector}
        """
        if dynamics is None:
            dynamics = self.getDynamics(key,actions,old)
        if dynamics:
            if len(dynamics) == 1:
                # Single effect
                matrix = dynamics[0][old]
                if matrix is None:
                    # Null effect
                    return old
                else:
                    newValue = matrix*old
                if isinstance(newValue,psychsim.pwl.KeyedVector):
                    # Deterministic effect
                    new = psychsim.pwl.KeyedVector(old)
                    new.update(newValue)
                else:
                    # Stochastic effect
                    new = psychsim.pwl.VectorDistribution({old: 1.})
                    if not isinstance(newValue,psychsim.pwl.VectorDistribution):
                        # We're going to just go ahead and treat the result as a VectorDistribution,
                        # because we don't play by your rules
                        newValue = psychsim.pwl.VectorDistribution(newValue)
                    new.join(key,newValue.marginal(key))
                return new
            else:
                # Multiply deltas in sequence (expand branches as necessary in the future)
                assert self.variables[key]['combinator'] == '*',\
                    'No valid combinator specified for multiple effects on %s' % (key)
                for tree in dynamics:
                    # Iterate through each tree (possibly ordered)
                    if isinstance(old,psychsim.pwl.KeyedVector):
                        # Certain state
                        old = self.singleDeltaVector(actions,old,key,[tree])
                    else:
                        # Uncertain state
                        new = psychsim.pwl.VectorDistribution()
                        for oldVector in old.domain():
                            partial = self.singleDeltaVector(actions,oldVector,key,[tree])
                            if isinstance(partial,psychsim.pwl.KeyedVector):
                                # Deterministic effect
                                new.addProb(partial,old[oldVector])
                            else:
                                # Stochastic effect
                                for newVector in partial.domain():
                                    new.addProb(newVector,old[oldVector]*partial[newVector])
                        old = new
                return old
        else:
            return old

    def addTermination(self,tree,action=True):
        """
        Adds a possible termination condition to the list
        """
        # Temporary deprecation check (TODO: Remove)
        remaining = [tree]
        while remaining:
            subtree = remaining.pop()
            if subtree.isLeaf():
                if isinstance(subtree.children[None],bool):
                    msg = 'Use set%sMatrix(psychsim.keys.TERMINATED) instead of %s' % \
                          (subtree.children[None],subtree.children[None])
                    raise DeprecationWarning(msg)
            elif subtree.isProbabilistic():
                remaining += subtree.children.domain()
            else:
                remaining += subtree.children.values()
        try:
            dynamics = self.dynamics[TERMINATED]
        except KeyError:
            dynamics = self.dynamics[TERMINATED] = {}
        if action in dynamics and action is True:
            raise DeprecationWarning('Multiple termination conditions no longer supported. Please merge into single boolean PWL tree.')
        self.setDynamics(TERMINATED,action,tree)

    def terminated(self,state=None):
        """
        Evaluates world states with respect to termination conditions
        @param state: the state vector (or distribution thereof) to evaluate (default is the current world state)
        @type state: L{psychsim.pwl.KeyedVector} or L{VectorDistribution}
        @return: C{True} iff the given state (or all possible worlds if a distribution) satisfies at least one termination condition
        @rtype: bool
        """
        if state is None:
            state = self.state
        try:
            termination = self.getValue(TERMINATED,state)
        except KeyError:
            termination = False
        if isinstance(termination,Distribution):
            termination = termination[True] == 1.
        return termination

    """-----------------"""
    """Authoring methods"""
    """-----------------"""

    def addAgent(self,agent):
        if isinstance(agent,str):
            agent = Agent(agent,self)
        if self.has_agent(agent):
            raise NameError('Agent %s already exists in this world' % (agent.name))
        else:
            self.agents[agent.name] = agent
            agent.world = self
            self.turnSubstate = None
            self.turnKeys = set()
        return agent

    def has_agent(self,agent):
        """
        @param agent: The agent (or agent name) to look for
        @type agent: L{Agent} or str
        @return: C{True} iff this C{World} already has an agent with the same name
        @rtype: bool
        """
        if isinstance(agent,str):
            return agent in self.agents
        else:
            return agent.name in self.agents

    def setTurnDynamics(self,name,action,tree):
        """
        Convenience method for setting custom dynamics for the turn order
        @param name: the name of the agent whose turn dynamics are being set
        @type name: str
        @param action: the action affecting the turn order
        @type action: L{Action} or L{ActionSet}
        @param tree: the decision tree defining the effect on this agent's turn order
        @type tree: L{psychsim.pwl.KeyedTree}
        """
        if self.maxTurn is None:
            raise ValueError('Call setOrder before setting turn dynamics')
        key = turnKey(name)
        if not key in self.variables:
            self.defineVariable(key,int,hi=self.maxTurn,evaluate=False)
        self.setDynamics(key,action,tree)

    def addDynamics(self,tree,action=True,enforceMin=False,enforceMax=False):
        if isinstance(action,Action):
            action = ActionSet(action)
        assert action is True or isinstance(action,ActionSet),'Action must be True/ActionSet/Action for addDynamics'
        if not action in self.newDynamics:
            self.newDynamics[action] = []
        tree = tree.desymbolize(self.symbols)
        keysIn = tree.getKeysIn()
        keysOut = tree.getKeysOut()
    
    def setDynamics(self,key,action,tree,enforceMin=False,enforceMax=False):
        """
        Defines the effect of an action on a given state feature
        @param key: the key of the affected state feature
        @type key: str
        @param action: the action affecting the state feature
        @type action: L{Action} or L{ActionSet}
        @param tree: the decision tree defining the effect
        @type tree: L{psychsim.pwl.KeyedTree}
        """
#        logging.warning('setDynamics will soon be deprecated. Please migrate to using addDynamics instead.')
        if isinstance(action,str):
            raise TypeError('Incorrect action type in setDynamics call, perhaps due to change in method definition. Please use a key string as the first argument, rather than the more limiting entity/feature combination.')
        if not isinstance(action,ActionSet) and not action is True:
            if not isinstance(action,Action):
                # dict -> Action
                action = Action(action)
            # Action -> ActionSet
            action = ActionSet([action])
        assert key in self.variables,'No state element "%s"' % (key) 
        if not action is True:
            for atom in action:
                assert atom['subject'] in self.agents,\
                    'Unknown actor %s' % (atom['subject'])
                assert self.agents[atom['subject']].hasAction(atom),\
                    'Unknown action %s' % (atom)
        if not key in self.dynamics:
            self.dynamics[key] = {}
        # Translate symbolic names into numeric values
        tree = tree.desymbolize(self.symbols)
        if enforceMin and self.variables[key]['domain'] in [int,float]:
            # Modify tree to enforce floor
            tree.floor(key,self.variables[key]['lo'])
        if enforceMax and self.variables[key]['domain'] in [int,float]:
            # Modify tree to enforce ceiling
            tree.ceil(key,self.variables[key]['hi'])
        self.dynamics[key][action] = tree

    def getDynamics(self,key,action,state=None):
        if not key in self.dynamics:
            return []
        if isinstance(action,Action):
            return self.getDynamics(key,ActionSet([action]),state)
        elif not isinstance(action,ActionSet) and not isinstance(action,list):
            # Table of actions by multiple agents
            return self.getDynamics(key,ActionSet(action),state)
        error = None
        try:
            return [self.dynamics[key][action]]
        except KeyError:
            error = 'key'
        except TypeError:
            error = 'type'
        if error:
            dynamics = []
            for atom in action:
                try:
                    dynamics.append(self.dynamics[key][ActionSet([atom])])
                except KeyError:
                    if len(atom) > len(atom.special):
                        # Extra parameters
                        try:
                            tree = self.dynamics[key][ActionSet([atom.root()])]
                        except KeyError:
                            tree = None
                        if tree:
                            table = {}
                            for field in atom.getParameters():
                                table[actionKey(field)] = atom[field]
                            dynamics.append(tree.desymbolize(table))
            if len(dynamics) == 0:
                # No action-specific dynamics, fall back to default dynamics
                if True in self.dynamics[key]:
                    dynamics.append(self.dynamics[key][True])
            return dynamics

    def getAncestors(self,keySubset,actions):
        """
        @return: a set of keys that potentially influence at least one key in the given set of keys (including this set as well)
        """
        remaining = set(keySubset)
        result = set()
        while remaining:
            key = remaining.pop()
            result.add(key)
            dynamics = self.getDynamics(key,actions)
            if dynamics:
                for tree in dynamics:
                    remaining |= tree.getKeysIn() - result - {CONSTANT}
        return result
        
    def addDependency(self,dependent,independent):
        raise DeprecationWarning('Dependencies are now determined automatically on a case-by-case basis. Simply use "makeFuture(\'%s\')" in the dynamics for %s' % (independent,dependent))

    """------------------"""
    """Turn order methods"""
    """------------------"""

    def setOrder(self,order):
        """
        Initializes the turn order to the given order
        @param order: the turn order, as a list of names (each agent acts in sequence) or a list of sets of names (agents within a set acts in parallel)
        @type order: str[] or {str}[]
        """
        self.maxTurn = len(order) - 1
        for index in range(len(order)):
            if isinstance(order[index],set):
                names = order[index]
            else:
                names = [order[index]]
            for name in names:
                # Insert turn key
                key = turnKey(name)
                self.turnKeys.add(key)
                if not key in self.variables:
                    if self.turnSubstate == None:
                        self.turnSubstate = max(self.state.distributions.keys())+1
                    self.defineVariable(key,int,hi=self.maxTurn,evaluate=False,substate=self.turnSubstate)
                self.state.join(key,index)
                # Insert action key
                key = stateKey(name,keys.ACTION)
                if not key in self.variables:
                    self.defineVariable(key,ActionSet)
                    self.setFeature(key,next(iter(self.variables[key]['elements'])))

    def next(self,vector=None):
        """
        @return: a list of agents (by name) whose turn it is in the current epoch
        @rtype: str[]
        """
        if vector is None:
            vector = self.state
        if isinstance(vector,VectorDistributionSet):
            if len(self.turnKeys) == 0:
                self.turnKeys = {key for key in vector.keyMap.keys() if isTurnKey(key)}
#            if self.turnSubstate == CONSTANT:
            substate = {vector.keyMap[key] for key in self.turnKeys}
            if len(substate) != 1:
                logging.error('Turns stored in independent substates: %s' % \
                              (', '.join(substate)))
            self.turnSubstate = iter(substate).next()
            distribution = vector.distributions[self.turnSubstate]
            results = {}
            for element in distribution.domain():
                names = self.next(element)
                label = ','.join(names)
                if label in results:
                    results[label]['worlds'][element] = distribution[element]
                else:
                    results[label] = {'agents': names,
                                      'worlds': psychsim.pwl.VectorDistribution({element: distribution[element]})}
            if len(results) > 1:
                logging.error('Unable to handle nondeterministic turns')
            return results.values()[0]['agents']
        else:
            items = filter(lambda i: isTurnKey(i[0]),vector.items())
        if len(items) == 0:
            # No turn information in vector
            return []
        value = min(map(lambda i: int(i[1]),items))
        return map(lambda i: turn2name(i[0]),filter(lambda i: int(i[1]) == value,items))

    def deltaOrder(self,actions,vector):
        """
        @warning: assumes that no one is acting out of turn
        @return: the new turn sequence resulting from the performance of the given actions
        """
        potentials = [name for name in self.agents.keys()
                      if turnKey(name) in vector]
        if len(potentials) == 0:
            return None
        if self.maxTurn is None:
            self.maxTurn = max([vector[turnKey(name)] for name in potentials])
        # Figure out who has acted
        if isinstance(actions,ActionSet):
            table = {}
            for atom in actions:
                try:
                    table[atom['subject']] = ActionSet(list(table[atom['subject']])+[atom])
                except KeyError:
                    table[atom['subject']] = ActionSet(atom)
        elif isinstance(actions,dict):
            table = actions
            actions = ActionSet()
            for atom in table.values():
                actions = actions | atom
        else:
            assert isinstance(actions,list)
            actionList = actions
            table = {}
            actions = set()
            for atom in actionList:
                table[atom['subject']] = True
                actions.add(atom)
            actions = ActionSet(actions)
        # Find dynamics for each turn
        delta = psychsim.pwl.KeyedMatrix()
        for name in potentials:
            key = turnKey(name)
            dynamics = self.getTurnDynamics(key,table)
            # Combine any turn dynamics into single matrix
            matrix = dynamics[0][vector]
            assert isinstance(matrix,psychsim.pwl.KeyedMatrix),'Dynamics must be deterministic'
            delta.update(matrix)
        return delta

    def getTurnDynamics(self,key,actions):
        if not isinstance(actions,ActionSet):
            actions = ActionSet(actions)
        dynamics = self.getDynamics(key,actions)
        if len(dynamics) == 0:
            # Create default dynamics
            agent = turn2name(key)
            for atom in actions:
                if atom['subject'] == agent:
                    tree = psychsim.pwl.makeTree(
                        {'if': psychsim.pwl.thresholdRow(key,0.5),
                         True: psychsim.pwl.incrementMatrix(key,-1),
                         False: psychsim.pwl.setToConstantMatrix(key,self.maxTurn)})
                    break
            else:
                tree = psychsim.pwl.makeTree(psychsim.pwl.incrementMatrix(key,-1))
#            self.setTurnDynamics(name,actions,tree)
            dynamics = [tree]
        return {key: dynamics}
        
    def getActions(self,vector,agents=None,actions=None):
        """
        @return: the set of all possible action combinations that could happen in the given state
        @rtype: set(L{ActionSet})
        """
        if agents is None:
            agents = self.next(vector)
        if actions is None:
            actions = set([ActionSet()])
        if len(agents) > 0:
            newActions = set()
            name = agents.pop()
            for subset in actions:
                for action in self.agents[name].getActions(vector):
                    newActions.add(subset | action)
            return self.getActions(vector,agents,newActions)
        else:
            return actions
                    
    """-------------"""
    """State methods"""
    """-------------"""

    def defineVariable(self,key,domain=float,lo=-1.,hi=1.,description=None,
                       combinator=None,substate=None,evaluate=True):
        """
        Define the type and domain of a given element of the state vector
        @param key: string label for the column being defined
        @type key: str
        @param domain: the domain of values for this feature. Acceptable values are:
           - float: continuous range
           - int: discrete numeric range
           - bool: True/False value
           - list: enumerated set of discrete values
           - ActionSet: enumerated set of actions, of the named agent (as key)
        @type domain: class
        @param lo: for float/int features, the lowest possible value. for list features, a list of possible values.
        @type lo: float/int/list
        @param hi: for float/int features, the highest possible value
        @type hi: float/int
        @param description: optional text description explaining what this state feature means
        @type description: str
        @param combinator: how should multiple dynamics for this variable be combined
        @param substate: name of independent state subvector this variable belongs to
        """
        for agent in self.agents.values():
            for model in agent.models.values():
                if 'beliefs' in model and not model['beliefs'] is True:
                    raise RuntimeError('Define all variables before setting beliefs')
        if key in self.variables:
            raise NameError('Variable %s already defined' % (key))
        if key[-1] == "'":
            raise ValueError('Ending single-quote reserved for indicating future state')
        if substate is None:
            substate = max(self.state.distributions.keys())+1
        self.variables[key] = {'domain': domain,
                               'description': description,
                               'substate': substate,
                               'combinator': combinator}
#        self.state.keyMap[key] = substate
        if domain is float:
            self.variables[key].update({'lo': lo,'hi': hi})
        elif domain is int:
            self.variables[key].update({'lo': int(lo),'hi': int(hi)})
        elif domain is list or domain is set:
            assert isinstance(lo,list) or isinstance(lo,set),\
                'Please provide set/list of elements for features of the set/list type'
            self.variables[key].update({'elements': lo,'lo': None,'hi': None})
            for element in lo:
                if not element in self.symbols:
                    self.symbols[element] = len(self.symbols)
                    self.symbolList.append(element)
        elif domain is bool:
            self.variables[key].update({'lo': None,'hi': None})
        elif domain is ActionSet:
            # The actions of an agent
            if isinstance(lo,float):
                if key in self.agents:
                    lo = self.agents[key].actions
                else:
                    lo = self.agents[keys.state2agent(key)].actions
            self.variables[key].update({'elements': lo,'lo': None,'hi': None})
            for action in lo:
                self.symbols[action] = len(self.symbols)
                self.symbolList.append(action)
        else:
            raise ValueError('Unknown domain type %s for %s' % (domain,key))
        self.variables[key]['key'] = key
        self.dependency.clear()

    def setFeature(self,key,value,state=None):
        """
        Set the value of an individual element of the state vector
        @param key: the label of the element to set
        @type key: str
        @type value: float or L{psychsim.probability.Distribution}
        @param state: the state distribution to modify (default is the current world state)
        @type state: L{VectorDistribution}
        """
        if state is None or state is self.state:
            for agent in self.agents.values():
                for model in agent.models.values():
                    if 'beliefs' in model and not model['beliefs'] is True and \
                       not key in model['beliefs']:
                        raise RuntimeError('Set all variable values before setting beliefs')
        assert key in self.variables,'Unknown element "%s"' % (key)
        if state is None:
            state = self.state
        state.join(key,self.value2float(key,value),self.variables[key]['substate'])

    def encodeVariable(self,key,value):
        raise DeprecationWarning('Use value2float method instead')

    def float2value(self,key,flt):
        if isinstance(flt,psychsim.probability.Distribution):
            # Decode each element
            value = flt.__class__()
            for element in flt.domain():
                newElement = self.float2value(key,element)
                try:
                    value[newElement] += flt[element]
                except KeyError:
                    value[newElement] = flt[element]
            return value
        elif isinstance(flt,set):
            return {self.float2value(key,element) for element in flt}
        elif self.variables[key]['domain'] is bool:
            if flt > 0.5:
                return True
            else:
                return False
        elif self.variables[key]['domain'] is list or \
             self.variables[key]['domain'] is set or \
             self.variables[key]['domain'] is ActionSet:
            index = int(float(flt)+0.1)
            return self.symbolList[index]
        elif self.variables[key]['domain'] is int:
            return int(flt)
        elif isModelKey(key):
            return self.agents[model2name(key)].index2model(flt)
        else:
            return flt

    def value2float(self,key,value):
        """
        @return: the float value (appropriate for storing in a L{psychsim.pwl.KeyedVector}) corresponding to the given (possibly symbolic, bool, etc.) value
        """
        if isinstance(value,psychsim.probability.Distribution):
            # Encode each element
            newValue = value.__class__()
            for element in value.domain():
                newElement = self.value2float(key,element)
                try:
                    newValue[newElement] += value[element]
                except KeyError:
                    newValue[newElement] = value[element]
            return newValue
        elif self.variables[key]['domain'] is bool:
            if value:
                return 1.
            else:
                return 0.
        elif self.variables[key]['domain'] is list or self.variables[key]['domain'] is set or \
                self.variables[key]['domain'] is ActionSet:
            return self.symbols[value]
        else:
            return value

    def getFeature(self,key,state=None):
        """
        @param key: the label of the state element of interest
        @type key: str
        @param state: the distribution over possible worlds (default is the current world state)
        @type state: L{VectorDistribution}
        @return: a distribution over values for the given feature
        @rtype: L{psychsim.probability.Distribution}
        """
        if state is None:
            state = self.state
        assert key in self.variables,'Unknown element "%s"' % (key)
        marginal = state.marginal(key)
        assert isinstance(marginal,psychsim.probability.Distribution)
        return self.float2value(key,marginal)

    def getValue(self,key,state=None):
        """
        Helper method that returns a single value from a vector or a singleton distribution
        @param key: the label of the state element of interest
        @type key: str
        @param state: the distribution over possible worlds (default is the current world state)
        @type state: L{VectorDistribution} or L{psychsim.pwl.KeyedVector}
        @return: a single value for the given feature
        """
        if isinstance(state,psychsim.pwl.KeyedVector):
            return self.float2value(key,state[key])
        else:
            marginal = self.getFeature(key,state)
            assert len(marginal) == 1,'getValue operates on only singleton distributions'
            return marginal.domain()[0]

    def decodeVariable(self,key,distribution):
        raise DeprecationWarning('Use float2value method instead')

    def defineState(self,entity,feature,domain=float,lo=0.,hi=1.,description=None,combinator=None,
                    substate=None):
        """
        Defines a state feature associated with a single agent, or with the global world state.
        @param entity: if C{None}, the given feature is on the global world state; otherwise, it is local to the named agent
        @type entity: str
        """
        if isinstance(entity,Agent):
            entity = entity.name
        key = stateKey(entity,feature)
        if substate is None:
            substate = len(self.state.keyMap)
        try:
            self.locals[entity][feature] = key
        except KeyError:
            self.locals[entity] = {feature: key}
        if not domain is None:
            # Haven't defined this feature yet
            self.defineVariable(key,domain,lo,hi,description,combinator,substate)
        return key

    def setState(self,entity,feature,value,state=None):
        """
        For backward compatibility
        @param entity: the name of the entity whose state feature we're setting (does not have to be an agent)
        @type entity: str
        @type feature: str
        """
        self.setFeature(stateKey(entity,feature),value,state)

    def getState(self,entity,feature,state=None):
        """
        For backward compatibility
        @param entity: the name of the entity of interest (C{None} if the feature of interest is of the world itself)
        @type entity: str
        @param feature: the state feature of interest
        @type feature: str
        """
        return self.getFeature(stateKey(entity,feature),state)

    def defineRelation(self,subj,obj,name,domain=float,lo=0.,hi=1.,description=None):
        """
        Defines a binary relationship between two agents
        @param subj: one of the agents in the relation (if a directed link, it is the "origin" of the edge)
        @type subj: str
        @param obj: one of the agents in the relation (if a directed link, it is the "destination" of the edge)
        @type obj: str
        @param name: the name of the relation (e.g., the verb to use between the subject and object)
        @type name: str
        """
        key = binaryKey(subj,obj,name)
        try:
            self.relations[name][key] = {'subject': subj,'object': obj}
        except KeyError:
            self.relations[name] = {key: {'subject': subj,'object': obj}}
        if not domain is None:
            # Haven't defined this feature yet
            self.defineVariable(key,domain,lo,hi,description)
        return key

    """------------------"""
    """Mental model methods"""
    """------------------"""

    def getModel(self,modelee,vector=None):
        """
        @return: the name of the model of the given agent indicated by the given state vector
        @type modelee: str
        @type vector: L{psychsim.pwl.KeyedVector}
        @rtype: str
        """
        if vector is None:
            vector = self.state
        agent = self.agents[modelee]
        if isinstance(vector,VectorDistributionSet):
            key = modelKey(modelee)
            if key in self.variables:
                model = self.getFeature(key,vector)
            else:
                assert len(agent.models) == 1,'Ambiguous model of %s' % (modelee)
                model = agent.models.keys()[0]
        else:
            try:
                model = agent.index2model(vector[modelKey(modelee)])
            except KeyError:
                model = True
        return model

    def getMentalModel(self,modelee,vector):
        raise DeprecationWarning('Substitute getModel instead (sorry for pedanticism, but a "model" may be real, not "mental")')

    def setModel(self,modelee,distribution,state=None,model=None):
        # Make sure distribution is probability distribution over floats
        if not isinstance(distribution,dict):
            distribution = {distribution: 1.}
        if not isinstance(distribution,psychsim.probability.Distribution):
            distribution = psychsim.probability.Distribution(distribution)
        for element in distribution.domain():
            if not isinstance(element,float):
                distribution.replace(element,float(self.agents[modelee].model2index(element)))
        distribution.normalize()
        key = modelKey(modelee)
        if not key in self.variables:
            self.defineVariable(key)
        if isinstance(state,str):
            # This is the name of the modeling agent (*cough* hack *cough*)
            self.agents[state].setBelief(key,distribution,model)
        else:
            # Otherwise, assume we're changing the model in the current state
            self.setFeature(key,distribution,state)
        
    def setMentalModel(self,modeler,modelee,distribution,model=True):
        """
        Sets the distribution over mental models one agent has of another entity
        @note: Normalizes the distribution given
        """
        self.setModel(modelee,distribution,modeler,model)

    def pruneModels(self,vector):
        """
        Do you want a version of a possible world *without* all the fuss of agent models?
        Then *this* is the method for you!
        """
        return psychsim.pwl.KeyedVector({key: vector[key] for key in vector.keys() if not isModelKey(key)})

    def modelGC(self,check=False):
        """
        Garbage collect orphaned models.
        """
        if check:
            # Record initial indices for verification purposes
            indices = {}
            for name,agent in self.agents.items():
                indices[name] = {}
                for label,model in agent.models.items():
                    indices[name][label] = agent.model2index(label)
                    assert agent.index2model(indices[name][label]) == label
        # Keep track of which models are active for each agent and who their parent models are
        parents = {}
        children = {}
        for name in self.agents.keys():
            parents[name] = {}
            children[name] = set()
        # Start with the worlds in the current state
        remaining = self.state[None].domain()
        realWorld = True
        while len(remaining) > 0:
            newRemaining = []
            for vector in remaining:
                # Look for models of each agent
                for name,agent in self.agents.items():
                    key = modelKey(name)
                    if key in vector:
                        # This world specifies an active model
                        model = agent.index2model(vector[key])
                    elif realWorld:
                        # No explicit specification, so assume True
                        model = True
                    else:
                        model = None
                    if model:
                        children[name].add(model)
                        try:
                            parents[name][agent.models[model]['parent']].append(model)
                        except KeyError:
                            parents[name][agent.models[model]['parent']] = [model]
                        if 'beliefs' in agent.models[model]:
                            while not isinstance(agent.models[model]['beliefs'],psychsim.pwl.VectorDistribution):
                                # Beliefs are symbolic link to another model
                                model = agent.models[model]['beliefs']
                                if model in children[name]:
                                    # Already processed this model
                                    break
                                else:
                                    children[name].add(model)
                            else:
                                # Recurse into the worlds within this agent's subjective view
                                newRemaining += agent.models[model]['beliefs'].domain()
            realWorld = False
            remaining = newRemaining
        # Remove inactive models
#        for name,active in children.items():
#            agent = self.agents[name]
#            for model in agent.models.keys():
#                if not model in active and not model in parents[name]:
#                    # Inactive model with no dependencies
#                    agent.deleteModel(model)
        if check:
            # Verify final indices
            for name,agent in self.agents.items():
                for label,model in agent.models.items():
                    assert indices[name][label] == agent.model2index(label)
                    assert agent.index2model(indices[name][label]) == label

    def updateModels(self,outcome,vector):
        for agent in self.agents.values():
            label = self.getModel(agent.name,vector)
            model = agent.models[label]
            if not model['beliefs'] is True:
                omega = agent.observe(vector,outcome['actions'])
                beliefs = model['beliefs']
                if not omega is True:
                    raise NotImplementedError('Unable to update mental models under partial observability')
                for actor,actions in outcome['actions'].items():
                    # Consider each agent who *did* act
                    actorKey = modelKey(actor)
                    if beliefs.hasColumn(actorKey):
                        # Agent has uncertain beliefs about this actor
                        belief = beliefs.marginal(actorKey)
                        prob = {}
                        for index in belief.domain():
                            # Consider the hypothesis mental models of this actor
                            hypothesis = self.agents[actor].models[self.agents[actor].index2model(index)]
                            denominator = 0.
                            V = {}
                            state = psychsim.pwl.KeyedVector(outcome['old'])
                            state[actorKey] = index
                            for alternative in self.agents[actor].getActions(outcome['old']):
                                # Evaluate all available actions with respect to the hypothesized mental model
                                V[alternative] = self.agents[actor].value(state,alternative,model=hypothesis['name'])['V']
                            if not actions in V:
                                # Agent performed a non-prescribed action
                                V[actions] = self.agents[actor].value(state,alternative,model=hypothesis['name'])['V']
                            # Convert into probability distribution of observed action given hypothesized mental model
                            behavior = psychsim.probability.Distribution(V,hypothesis['rationality'])
                            prob[index] = behavior[actions]
                            # Bayes' rule
                            prob[index] *= belief[index]
                        # Update posterior beliefs over mental models
                        prob = psychsim.probability.Distribution(prob)
                        prob.normalize()
                        belief = MatrixDistribution()
                        for element in prob.domain():
                            belief[setToConstantMatrix(actorKey,element)] = prob[element]
                        model['beliefs'].update(belief)

    def scaleState(self,vector):
        """
        Normalizes the given state vector so that all elements occur in [0,1]
        @param vector: the vector to normalize
        @type vector: L{psychsim.pwl.KeyedVector}
        @return: the normalized vector
        @rtype: L{psychsim.pwl.KeyedVector}
        """
        result = vector.__class__()
        remaining = dict(vector)
        # Handle defined state features
        for key,entry in self.variables.items():
            if key in remaining:
                new = scaleValue(remaining[key],entry)
                result[key] = new
                del remaining[key]
        for name in self.agents.keys():
            # Handle turns
            key = turnKey(name)
            if key in remaining:
                result[key] = remaining[key] / len(self.agents)
                del remaining[key]
            # Handle models
            key = modelKey(name)
            if key in remaining:
                result[key] = remaining[key] / len(self.agents[name].models)
                del remaining[key]
        # Handle constant term
        if CONSTANT in remaining:
            result[CONSTANT] = remaining[CONSTANT]
            del remaining[CONSTANT]
        if remaining:
            raise NameError('Unprocessed keys: %s' % (remaining.keys()))
        return result

    def reachable(self,state=None,transition=None,horizon=-1,ignore=[],debug=False):
        """
        @note: The C{__predecessors__} entry for each reachable vector is a set of possible preceding states (i.e., those whose value must be updated if the value of this vector changes
        @return: transition matrix among states reachable from the given state (default is current state)
        @rtype: psychsim.pwl.KeyedVectorS{->}ActionSetS{->}VectorDistribution
        """
        envelope = set()
        transition = {}
        if state is None:
            # Initialize with current state
            state = self.state[None]
        if isinstance(state,psychsim.pwl.VectorDistribution):
            for vector in state.domain():
                envelope.add((vector,horizon))
        else:
            # Initialize with given state
            envelope.add((state,horizon))
        while len(envelope) > 0:
            vector,horizon = envelope.pop()
            assert len(vector) == len(state.domain()[0])
            if debug:
                print('Expanding...')
                self.printVector(vector)
            node = vector.filter(ignore)
            # If no entry yet, then this is a start node
            if not node in transition:
                transition[node] = {'__predecessors__': set()}
            # Process next steps from this state
            if not self.terminated(vector) and horizon != 0:
                for actions in self.getActions(vector):
                    if debug: print('Performing:', actions)
                    future = self.stepFromState(vector,actions)['new']
                    if isinstance(future,psychsim.pwl.KeyedVector):
                        future = psychsim.pwl.VectorDistribution({future: 1.})
                    transition[node][actions] = psychsim.pwl.VectorDistribution()
                    for newVector in future.domain():
                        if debug:
                            print('Result (P=%f)' % (future[newVector]))
                            self.printVector(newVector)
                        newNode = newVector.filter(ignore)
                        transition[node][actions][newNode] = future[newVector]
                        if newNode in transition:
                            transition[newNode]['__predecessors__'].add(node)
                        else:
                            envelope.add((newNode,horizon-1))
                            transition[newNode] = {'__predecessors__': set([node])}
        return transition
            
    def nearestVector(self,vector,vectors):
        mapping = {}
        for candidate in vectors:
            mapping[self.scaleState(candidate)] = candidate
        return mapping[self.scaleState(vector).nearestNeighbor(mapping.keys())]

    def getDescription(self,key,feature=None):
        if not feature is None:
            raise DeprecationWarning('Use key when calling getDescription, not entity/feature combination.')
        return self.variables[key]['description']

    """---------------------"""
    """Visualization methods"""
    """---------------------"""

    def explain(self,outcomes,level=1,buf=None):
        """
        Generate a more readable interpretation of outcomes generated by L{step}
        @param outcomes: the return value from L{step}
        @type outcomes: dict[]
        @param level: the level of explanation detail:
           0. No explanation
           1. Agent decisions
           2. Agent value functions
           3. Agent expectations
           4. Effects of expected actions
           5. World state (possibly subjective) at each step
        @type level: int
        @param buf: the string buffer to put the explanation into (default is standard out)
        """
        for outcome in outcomes:
            if level > 0: print('%d%%' % (outcome['probability']*100.),file=buf)
            if 'actions' in outcome:
                self.explainAction(outcome,buf,level)
                for name,action in outcome['actions'].items():
                    if not name in outcome['decisions']:
                        # No decision made
                        if level > 1: print(buf,'\tforced',file=buf)
                    elif level > 1:
                        # Explain decision
                        self.explainDecision(outcome['decisions'][name],buf,level)

    def explainAction(self,outcome,buf=None,level=0):
        if level > 0:
            for name,action in outcome['actions'].items():
                print(action,file=buf)
        return set(outcome['actions'].values())
        

    def explainDecision(self,decision,buf=None,level=2,prefix=''):
        """
        Subroutine of L{explain} for explaining agent decisions
        """
        if not 'V' in decision:
            # No value function
            return
        actions = decision['V'].keys()
        actions.sort(lambda x,y: cmp(str(x),str(y)))
        for alt in actions:
            V = decision['V'][alt]
            print('%s\tV(%s) = %6.3f' % (prefix,alt,V['__EV__']),file=buf)
            if level > 2:
                # Explain lookahead
                beliefs = filter(lambda k: not isinstance(k,str),V.keys())
                for state in beliefs:
                    nodes = V[state]['projection'][:]
                    while len(nodes) > 0:
                        node = nodes.pop(0)
                        tab = ''
                        t = V[state]['horizon']-node['horizon']
                        for index in range(t):
                            tab = prefix+tab+'\t'
                        if level > 4: 
                            print('%sState:' % (tab),file=buf)
                            self.printVector(node['old'],buf,prefix=tab,first=False)
                        print('%s%s (V_%s=%6.3f) [P=%d%%]' % (tab,ActionSet(node['actions']),V[state]['agent'],node['R'],node['probability']*100.),file=buf)
                        for other in node['decisions'].keys():
                            self.explainDecision(node['decisions'][other],buf,level,prefix+'\t\t')
                        if level > 3: 
                            print('%sEffect:' % (tab+prefix),file=buf)
                            self.printDelta(node['old'],node['new'],buf,prefix=tab+prefix)
                        for index in range(len(node['projection'])):
                            nodes.insert(index,node['projection'][index])

    def printState(self,distribution=None,buf=None,prefix='',beliefs=True):
        """
        Utility method for displaying a distribution over possible worlds
        @type distribution: L{VectorDistribution}
        @param buf: the string buffer to put the string representation in (default is standard output)
        @param prefix: a string prefix (e.g., tabs) to insert at the beginning of each line
        @type prefix: str
        @param beliefs: if C{True}, print out inaccurate beliefs, too
        @type beliefs: bool
        """
        if distribution is None:
            distribution = self.state
        if isinstance(distribution,VectorDistributionSet):
            minKeys = {s: None for s in distribution.distributions}
            certain = KeyedVector()
            for key,substate in distribution.keyMap.items():
                if key != keys.CONSTANT:
                    entity = keys.state2agent(key)
                    if entity is None:
                        feature = keys.state2feature(key)
                        key = stateKey(keys.WORLD,feature)
                    if minKeys[substate] is None or key < minKeys[substate]:
                        minKeys[substate] = key
            minKeys = [(k,s) for s,k in minKeys.items()]
            minKeys = [item[1] for item in sorted(minKeys)]

            remaining = []
            for substate in minKeys:
                if len(distribution.distributions[substate]) == 1:
                    certain.update(distribution.distributions[substate].first())
                else:
                    remaining.append(substate)
            self.printVector(certain,buf,prefix,beliefs)
            for label in remaining:
                subdistribution = distribution.distributions[label]
                if not label is None:
                    print('-------------------',file=buf)
                self.printState(subdistribution,buf,prefix,beliefs)
        else:
            for vector in distribution.domain():
                print('%s%d%%' % (prefix,distribution[vector]*100.),file=buf)
                self.printVector(vector,buf,prefix,beliefs=beliefs)

    def printVector(self,vector,buf=None,prefix='',first=True,beliefs=False,csv=False):
        """
        Utility method for displaying a single possible world
        @type vector: L{psychsim.pwl.KeyedVector}
        @param buf: the string buffer to put the string representation in (default is standard output)
        @param prefix: a string prefix (e.g., tabs) to insert at the beginning of each line
        @type prefix: str
        @param first: if C{True}, then the first line is the continuation of an existing line (default is C{True})
        @type first: bool
        @param csv: if C{True}, then print the vector as comma-separated values (default is C{False})
        @type csv: bool
        @param beliefs: if C{True}, then print any agent beliefs that might deviate from this vector as well (default is C{False})
        @type beliefs: bool
        """
        if csv:
            if prefix:
                elements = [prefix]
            else:
                elements = []
        entities = sorted(self.agents.keys())
        entities.insert(0,None)
        change = False
        # Sort relations
        relations = {}
        for link,table in self.relations.items():
            for key in table.keys():
                subj = table[key]['subject']
                obj = table[key]['object']
                try:
                    relations[subj].append((link,obj,key))
                except KeyError:
                    relations[subj] = [(link,obj,key)]
        for entity in entities:
            try:
                table = {state2feature(k): k for k in vector.keys() \
                         if keys.isStateKey(k) and keys.state2agent(k) == entity \
                         and not keys.isFuture(k)}
            except KeyError:
                table = {}
            if entity is None:
                label = keys.WORLD
            else:
                if entity in vector:
                    # Action performed in this vector
                    table['__action__'] = entity
                label = entity
            newEntity = True
            # Print state features for this entity
            for feature,key in sorted(table.items()):
                if key in vector:
                    if isFuture(key):
                        value = self.float2value(makePresent(key),vector[key])
                    else:
                        value = self.float2value(key,vector[key])
                    if csv:
                        elements.append(label)
                        elements.append(feature)
                        elements.append(value)
                    else:
                        future = makeFuture(key)
                        if future in vector:
                            fValue = self.float2value(key,vector[future])
                            if fValue != value:
                                value = '%s->%s' % (value,fValue)
                            else:
                                value = '%s.' % (value)
                        if newEntity:
                            newEntity = False
                            change = True
                        else:
                            label = ''
                        if first:
                            first = False
                            start = ''
                        else:
                            start = prefix
                        print('%s\t%-12s\t%-12s\t%s' % (start,label,feature+':',
                                                        value),file=buf)
            # Print relationships
            if entity in relations:
                for link,obj,key in relations[entity]:
                    if key in vector:
                        if newEntity:
                            print('\t%-12s' % (label),file=buf)
                            newEntity = False
                        print('\t\t%s\t%s:\t%s' % (link,obj,self.float2value(key,vector[key])),file=buf)
            # Print models (and beliefs associated with those models)
            if not entity is None:
                # Print model of this entity
                key = modelKey(entity)
                if key in vector:
                    if csv:
                        elements.append(label)
                        elements.append('__model__')
                        elements.append(self.agents[entity].index2model(vector[key]))
                    elif not beliefs:
                        if first:
                            print('\t%-12s:\t%s' % (label,self.agents[entity].index2model(vector[key])),file=buf)
                            first = False
                        else:
                            print('%s\t%-12s\t%s' % (prefix,label,self.agents[entity].index2model(vector[key])),file=buf)
                        change = True
                        newEntity = False
                    elif newEntity:
                        if first:
                            print('\t%-12s' % (label),file=buf)
                            first = False
                        else:
                            print('%s\t%-12s' % (prefix,label),file=buf)
                        self.agents[entity].printModel(index=vector[key],prefix=prefix)
                        change = True
                        newEntity = False
                    else:
                        print('\t%12s' % (''),file=buf)
                        self.agents[entity].printModel(index=vector[key],prefix=prefix)
                    newEntity = False
#        if not csv and not change:
#            print('%s\tUnchanged' % (prefix),file=buf)
        if csv:
            print(','.join(elements),file=buf)

    def printDelta(self,old,new,buf=None,prefix=''):
        """
        Prints a kind of diff patch for one state vector with respect to another
        @param old: the "original" state vector
        @type old: L{psychsim.pwl.KeyedVector}
        @param new: the state vector we want to see the diff of
        @type new: L{VectorDistribution}
        """
        deltaDist = psychsim.pwl.VectorDistribution()
        for vector in new.domain():
            delta = psychsim.pwl.KeyedVector()
            deltakeys = []
            for key,entry in self.variables.items():
                # Look for change in feature value
                deltakeys.append(key)
            for name in self.agents.keys():
                # Look for change in mental model of this agent
                key = modelKey(name)
                if key in vector:
                    deltakeys.append(key)
                    if not key in old:
                        old = psychsim.pwl.KeyedVector(vector)
                        old[key] = self.agents[name].model2index(True)
            for key in deltakeys:
                try:
                    diff = abs(vector[key]-old[key])
                except KeyError:
                    diff = 0.
                if diff > 1e-3:
                    # Notable change
                    delta[key] = vector[key]
            if self.terminated(vector):
                delta['__END__'] = 1.
            else:
                delta['__END__'] = -1.
            try:
                deltaDist[delta] += new[vector]
            except KeyError:
                deltaDist[delta] = new[vector]
        self.printState(deltaDist,buf,prefix=prefix,beliefs=False)
        
    """---------------------"""
    """Serialization methods"""
    """---------------------"""

    def __xml__(self):
        doc = Document()
        root = doc.createElement('world')
        if not self.maxTurn is None:
            root.setAttribute('maxTurn','%d' % (self.maxTurn))
        doc.appendChild(root)
        # Agents
        for agent in self.agents.values():
            root.appendChild(agent.__xml__().documentElement)
        # State vector definitions
        node = doc.createElement('state')
        node.appendChild(self.state.__xml__().documentElement)
        root.appendChild(node)
        for key,entry in self.variables.items():
            subnode = doc.createElement('feature')
            subnode.setAttribute('name',key)
            subnode.setAttribute('domain',entry['domain'].__name__)
            for coord in ['xpre','ypre','xpost','ypost']:
                if coord in entry:
                    subnode.setAttribute(coord,str(entry[coord]))
            if not entry['lo'] is None:
                subnode.setAttribute('lo',str(entry['lo']))
            if not entry['hi'] is None:
                subnode.setAttribute('hi',str(entry['hi']))
            if entry['domain'] is list or entry['domain'] is set:
                for element in entry['elements']:
                    subsubnode = doc.createElement('element')
                    subsubnode.appendChild(doc.createTextNode(element))
                    subnode.appendChild(subsubnode)
            elif entry['domain'] is ActionSet:
                for element in entry['elements']:
                    subsubnode = doc.createElement('element')
                    subsubnode.appendChild(element.__xml__().documentElement)
                    subnode.appendChild(subsubnode)
            if entry['description']:
                subsubnode = doc.createElement('description')
                subsubnode.appendChild(doc.createTextNode(entry['description']))
                subnode.appendChild(subsubnode)
            if entry['combinator']:
                subnode.setAttribute('combinator',str(entry['combinator']))
            node.appendChild(subnode)
        # Local/global state
        for entity,table in self.locals.items():
            for feature,entry in table.items():
                subnode = doc.createElement('local')
                subnode.appendChild(doc.createTextNode(feature))
                if entity:
                    subnode.setAttribute('entity',entity)
                node.appendChild(subnode)
        # Relationships
        for link,table in self.relations.items():
            node = doc.createElement('relation')
            node.setAttribute('name',link)
            for key,entry in table.items():
                subnode = doc.createElement('link')
                subnode.setAttribute('subject',entry['subject'])
                subnode.setAttribute('object',entry['object'])
                node.appendChild(subnode)
            root.appendChild(node)
        # Dynamics
        node = doc.createElement('dynamics')
        for key,table in self.dynamics.items():
            subnode = doc.createElement('table')
            subnode.setAttribute('key',key)
            if isinstance(table,dict):
                for action,tree, in table.items():
                    if not action is True:
                        subnode.appendChild(action.__xml__().documentElement)
                    subnode.appendChild(tree.__xml__().documentElement)
            node.appendChild(subnode)
        root.appendChild(node)
        # Termination conditions
        for termination in self.termination:
            node = doc.createElement('termination')
            node.appendChild(termination.__xml__().documentElement)
            root.appendChild(node)
        # Global symbol table
        for symbol in self.symbolList:
            node = doc.createElement('symbol')
            if isinstance(symbol,str):
                node.appendChild(doc.createTextNode(symbol))
            elif isinstance(symbol,ActionSet):
                node.appendChild(symbol.__xml__().documentElement)
            else:
                raise TypeError('Unknown symbol of type: %s' % (symbol.__class__.__name__))
            root.appendChild(node)
        # Event history
        node = doc.createElement('history')
        for entry in self.history:
            node.appendChild(entry.__xml__().documentElement)
        #     subnode = doc.createElement('entry')
        #     for outcome in entry:
        #         subsubnode = doc.createElement('outcome')
        #         for name in self.agents.keys():
        #             if 'actions' in outcome and name in outcome['actions']:
        #                 subsubnode.appendChild(outcome['actions'][name].__xml__().documentElement)
        # #        if 'delta' in outcome:
        # #            subsubnode.appendChild(outcome['delta'].__xml__().documentElement)
        #         subsubnode.appendChild(outcome['old'].__xml__().documentElement)
        #         subnode.appendChild(subsubnode)
        #     node.appendChild(subnode)
        root.appendChild(node)
        # UI Diagram
        if self.diagram:
            if isinstance(self.diagram,Node):
                # We never bothered parsing this, so easy
                root.appendChild(self.diagram)
            else:
                root.appendChild(self.diagram.__xml__().documentElement)
        # UI Diagram
        if self.diagram:
            if isinstance(self.diagram,Node):
                # We never bothered parsing this, so easy
                root.appendChild(self.diagram)
            else:
                root.appendChild(self.diagram.__xml__().documentElement)
        return doc

    def parse(self,element,agentClass=Agent):
        self.initialize()
        try:
            self.maxTurn = int(element.getAttribute('maxTurn'))
        except ValueError:
            self.maxTurn = None
        node = element.firstChild
        order = {}
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'agent':
                    if agentClass.isXML(node):
                        self.addAgent(agentClass(node))
                    else:
                        assert Agent.isXML(node)
                        self.addAgent(Agent(node))
                elif node.tagName == 'state':
                    label = str(node.getAttribute('label'))
                    if label:
                        if label == 'None':
                            label = None
                    else:
                        label = None
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            if subnode.tagName == 'worlds':
                                self.state = VectorDistributionSet(subnode)
                            elif subnode.tagName == 'distribution':
                                distribution = psychsim.pwl.VectorDistribution(subnode)
                                for key in distribution.domain()[0].keys():
                                    if key != CONSTANT:
                                        print(key,label)
                                        self.state.keyMap[key] = label
                                self.state.distributions[label] = distribution
                            elif subnode.tagName == 'feature':
                                key = str(subnode.getAttribute('name'))
                                domain,lo,hi,description,combinator = parseDomain(subnode)
                                try:
                                    substate = self.state.keyMap[key]
                                except KeyError:
                                    substate = None
                                self.defineVariable(key,domain,lo,hi,description,combinator,substate)
                                try:
                                    for coord in ['xpre','ypre','xpost','ypost']:
                                        self.variables[key][coord] = int(subnode.getAttribute(coord))
                                except ValueError:
                                    pass
                            elif subnode.tagName == 'local':
                                entity = str(subnode.getAttribute('entity'))
                                if not entity:
                                    entity = None
                                feature = str(subnode.firstChild.data).strip()
                                self.defineState(entity,feature,None)
                        subnode = subnode.nextSibling
                elif node.tagName == 'relation':
                    name = str(node.getAttribute('name'))
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'link'
                            subj = str(subnode.getAttribute('subject'))
                            obj = str(subnode.getAttribute('object'))
                            self.defineRelation(subj,obj,name,None)
                        subnode = subnode.nextSibling
                elif node.tagName == 'dynamics':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'table'
                            key = str(subnode.getAttribute('key'))
                            self.dynamics[key] = {}
                            subsubnode = subnode.firstChild
                            action = True
                            while subsubnode:
                                if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
                                    if subsubnode.tagName == 'action':
                                        assert action is True
                                        action = Action(subsubnode)
                                    elif subsubnode.tagName == 'option':
                                        assert action is True
                                        action = ActionSet(subsubnode)
                                    elif subsubnode.tagName == 'tree':
                                        self.dynamics[key][action] = psychsim.pwl.KeyedTree(subsubnode)
                                        action = True
                                    else:
                                        raise NameError('Unknown dynamics element: %s' % (subsubnode.tagName))
                                subsubnode = subsubnode.nextSibling
                            if len(self.dynamics[key]) == 0:
                                # Empty table
                                self.dynamics[key] = True
                        subnode = subnode.nextSibling
                elif node.tagName == 'termination':
                    subnode = node.firstChild
                    while subnode and subnode.nodeType != subnode.ELEMENT_NODE:
                        subnode = subnode.nextSibling
                    if subnode:
                        self.termination.append(psychsim.pwl.KeyedTree(subnode))
                elif node.tagName == 'symbol':
                    symbol = str(node.firstChild.data)
                    if not symbol.strip():
                        subnode = node.firstChild
                        while subnode and subnode.nodeType != subnode.ELEMENT_NODE:
                            subnode = subnode.nextSibling
                        if subnode:
                            if subnode.tagName == 'option':
                                symbol = ActionSet(subnode)
                            else:
                                raise ValueError('Unknown symbol tag: %s' % (subnode.tagName))
                    self.symbolList.append(symbol)
                elif node.tagName == 'history':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'entry'
                            entry = []
                            subsubnode = subnode.firstChild
                            while subsubnode:
                                if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
                                    assert subsubnode.tagName == 'outcome'
                                    outcome = {'actions': {}}
                                    element = subsubnode.firstChild
                                    while element:
                                        if element.nodeType == element.ELEMENT_NODE:
                                            if element.tagName == 'option':
                                                option = ActionSet(element)
                                                for action in option:
                                                    outcome['actions'][action['subject']] = option
                                                    break
                                            elif element.tagName == 'vector':
                                                outcome['old'] = psychsim.pwl.KeyedVector(element)
                                            elif element.tagName == 'distribution':
                                                outcome['delta'] = psychsim.pwl.VectorDistribution(element)
                                        element = element.nextSibling
                                    entry.append(outcome)
                                subsubnode = subsubnode.nextSibling
                            self.history.append(entry)
                        subnode = subnode.nextSibling
                elif node.tagName == 'diagram':
                    # UI information. Parse later
                    self.diagram = node
            node = node.nextSibling
        self.symbolList = self.symbolList[len(self.symbolList)/2:]
        for index in range(len(self.symbolList)):
            self.symbols[self.symbolList[index]] = index
        
    def save(self,filename,compressed=True):
        """
        @param compressed: if C{True}, then save in compressed XML; otherwise, save in XML (default is C{True})
        @type compressed: bool
        @return: the filename used (possibly with a .psy extension added)
        @rtype: str
        """
        if compressed:
            if filename[-4:] != '.psy':
                filename = '%s.psy' % (filename)
        elif filename[-4:] != '.xml':
            filename = '%s.xml' % (filename)
        if compressed:
            f = bz2.BZ2File(filename,'w')
        else:
            f = open(filename,'w')
        f.write(self.__xml__().toprettyxml())
        f.close()
        return filename

def parseDomain(subnode):
    varType = str(subnode.getAttribute('type'))
    domain = str(subnode.getAttribute('domain'))
    if not varType:
        varType = domain
    description = None
    lo = str(subnode.getAttribute('lo'))
    if not lo: lo = None
    hi = str(subnode.getAttribute('hi'))
    if not hi: hi = None
    if varType == 'int':
        varType = int
        if lo: lo = int(lo)
        if hi: hi = int(hi)
    elif varType == 'float':
        varType = float
        if lo: lo = float(lo)
        if hi: hi = float(hi)
    elif varType == 'bool':
        varType = bool
    elif varType == 'list':
        varType = list
        lo = []
    elif varType == 'set':
        varType = set
        lo = []
    elif varType == 'ActionSet':
        varType = ActionSet
        lo = []
    else:
        raise TypeError('Unknown feature domain type: %s' % (varType))
    combinator = str(subnode.getAttribute('combinator'))
    if len(combinator) == 0:
        combinator = None
    subsubnode = subnode.firstChild
    while subsubnode:
        if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
            if subsubnode.tagName == 'element':
                if varType is list or varType is set:
                    lo.append(str(subsubnode.firstChild.data).strip())
                else:
                    assert varType is ActionSet
                    lo.append(ActionSet(subsubnode.getElementsByTagName('action')))
            else:
                assert subsubnode.tagName == 'description'
                description = str(subsubnode.firstChild.data).strip()
        subsubnode = subsubnode.nextSibling
    return varType,lo,hi,description,combinator

def scaleValue(value,entry):
    """
    @return: a new float value that has been normalized according to the feature's domain
    """
    if entry['domain'] is float or entry['domain'] is int:
        # Scale by range of possible values
        return float(value-entry['lo']) / float(entry['hi']-entry['lo'])
    elif entry['domain'] is list:
        # Scale by size of set of values
        return float(value)/float(len(entry['elements']))
    else:
        return value
