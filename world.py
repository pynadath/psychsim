import bz2
import copy
import math
from xml.dom.minidom import Document,Node,parseString

from action import ActionSet,Action
from pwl import *
from probability import Distribution
from agent import Agent

class World:
    """
    @ivar agents: table of agents in this world, indexed by name
    @type agents: strS{->}L{Agent}
    @ivar state: the distribution over states of the world
    @type state: L{VectorDistribution}
    @ivar features: definitions of state features, over agents and the world itself
    @type features: dict
    @ivar symbols: utility storage of symbols used across all enumerated state features
    @type symbols: strS{->}int
    @ivar dynamics: table of action effect models
    @type dynamics: dict
    @ivar dependency: table of dependencies among state features that impose temporal constraints
    @type dependency: dict
    @ivar history: accumulated list of outcomes from simulation steps
    @type history: list
    @ivar termination: list of conditions under which the simulation terminates (default is none)
    @type termination: L{KeyedTree}[]
    """
    __NORMALIZE__ = False

    def __init__(self,xml=None):
        """
        @param xml: Initialization argument, either an XML Element, or a filename
        @type xml: Node or str
        """
        self.agents = {}

        # State feature information
        self.state = VectorDistribution()
        self.features = {}
        self.symbols = {}
        self.ranges = {}
        self.termination = []

        # Action effect information
        self.dynamics = {}
        self.dependency = {}
        self.evaluationOrder = [set()]

        self.history = []

        if isinstance(xml,Node):
            self.parse(xml)
        elif isinstance(xml,str):
            if xml[-4:] == '.xml':
                # Uncompressed
                f = file(xml,'r')
            else:
                if xml[-4:] != '.psy':
                    xml = '%s.psy' % (xml)
                f = bz2.BZ2File(xml,'r')
            doc = parseString(f.read())
            f.close()
            self.parse(doc.documentElement)
        else:
            self.state[KeyedVector({CONSTANT: 1.})] = 1.

    def initialize(self):
        self.agents.clear()
        self.features.clear()
        self.symbols.clear()
        self.ranges.clear()
        self.dynamics.clear()
        self.dependency.clear()
        del self.evaluationOrder[:]
        self.evaluationOrder.append(set())
        del self.history[:]
        del self.termination[:]

    """------------------"""
    """Simulation methods"""
    """------------------"""
    
    def step(self,actions=None,state=None,real=True):
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
        outcomes = []
        # Iterate through each possible world
        for stateVector in state.domain():
            prob = state[stateVector]
            outcome = self.stepFromState(stateVector,actions)
            outcome['probability'] = prob
            outcomes.append(outcome)
        if real:
            # Apply effects
            state.clear()
            for outcome in outcomes:
                if isinstance(outcome['new'],Distribution):
                    dist = map(lambda el: (el,outcome['new'][el]),outcome['new'].domain())
                else:
                    dist = [(outcome['new'],1.)]
                for new,prob in dist:
                    if outcome.has_key('actions'):
                        self.updateModels(outcome,new)
                    try:
                        state[new] += prob*outcome['probability']
                    except KeyError:
                        state[new] = prob*outcome['probability']
            self.history.append(outcomes)
        return outcomes

    def stepFromState(self,vector,actions=None,horizon=None,tiebreak=None):
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
            outcome['actions'] = copy.copy(actions)
        # Keep track of whether there is uncertainty about the actions to perform
        stochastic = []
        if not isinstance(outcome['actions'],ActionSet):
            # ActionSet indicates that we should perform just these actions. Otherwise, we look at whose turn it is:
            for name in self.next(vector):
                if not outcome['actions'].has_key(name):
                    model = self.getMentalModel(name,vector)
                    decision = self.agents[name].decide(vector,horizon,outcome['actions'],model,tiebreak)
                    outcome['decisions'][name] = decision
                    outcome['actions'][name] = decision['action']
                elif isinstance(outcome['actions'][name],Action):
                    outcome['actions'][name] = ActionSet([outcome['actions'][name]])
                if isinstance(outcome['actions'][name],Distribution):
                    stochastic.append(name)
        if stochastic:
            # Merge effects of multiple possible actions into single effect
            if len(stochastic) > 1:
                raise NotImplementedError,'Currently unable to handle stochastic expectations over multiple agents: %s' % (stochastic)
            effects = []
            for action in outcome['actions'][stochastic[0]].domain():
                prob = outcome['actions'][stochastic[0]][action]
                actions = dict(outcome['actions'])
                actions[stochastic[0]] = action
                outcome.update(self.effect(actions,outcome['old'],prob))
        else:
            outcome.update(self.effect(outcome['actions'],outcome['old']))
        if not outcome.has_key('new'):
            # Apply effects
            outcome['new'] = outcome['effect']*outcome['old']
        if not outcome.has_key('delta'):
            outcome['delta'] = outcome['new'] - outcome['old']
        return outcome

    def effect(self,actions,vector,probability=1.):
        """
        @param probability: the likelihood of this particular action set (default is 100%)
        @type probability: float
        """
        result = {'effect': [],
                  'new': VectorDistribution({vector: probability})}
        for keys in self.evaluationOrder:
            new = VectorDistribution()
            effect = MatrixDistribution()
            for old in result['new'].domain():
                # Update world state
                delta = self.deltaState(actions,old,keys)
                for matrix in delta.domain():
                    try:
                        effect[matrix] += result['new'][old]
                    except KeyError:
                        effect[matrix] = result['new'][old]
                    vector = KeyedVector(old)
                    vector.update(matrix*old)
                    prob = result['new'][old]*delta[matrix]
                    try:
                        new[vector] += prob
                    except KeyError:
                        new[vector] = prob
            result['new'] = new
            result['effect'].append(effect)
        # Update turn order
        delta = self.deltaOrder(actions,vector)
        # Update agent beliefs
        for name,agent in self.agents.items():
            key = modelKey(name)
            if vector.has_key(key):
                delta[key] = KeyedVector({key: 1.})
        result['effect'].append(delta)
        new = VectorDistribution()
        for old in result['new'].domain():
            vector = KeyedVector(old)
            vector.update(delta*old)
            try:
                new[vector] += result['new'][old]
            except KeyError:
                new[vector] = result['new'][old]
        result['new'] = new
        return result

    def deltaState(self,actions,vector,keys=None):
        """
        Computes the change across a subset of state features
        """
        if keys is None:
            keys = sum(self.evaluationOrder,[])
        result = MatrixDistribution({KeyedMatrix(): 1.})
        for key in keys:
            dynamics = self.getDynamics(key,actions)
            if dynamics:
                assert len(dynamics) == 1,'Unable to merge multiple effects of %s on %s' % \
                    (ActionSet(actions),key)
                result.update(dynamics[0][vector])
        return result

    def addTermination(self,tree):
        """
        Adds a possible termination condition to the list
        """
        self.termination.append(tree.desymbolize(self.symbols))

    def terminated(self,state=None):
        """
        Evaluates world states with respect to termination conditions
        @param state: the state vector (or distribution thereof) to evaluate (default is the current world state)
        @type state: L{KeyedVector} or L{VectorDistribution}
        @return: C{True} iff the given state (or all possible worlds if a distribution) satisfies at least one termination condition
        @rtype: bool
        """
        if state is None:
            state = self.state
        if isinstance(state,VectorDistribution):
            # All possible worlds must be terminal states
            for vector in state.domain():
                if not self.terminated(vector):
                    return False
            else:
                return True
        else:
            assert isinstance(state,KeyedVector)
            for condition in self.termination:
                if condition[state]:
                    return True
            else:
                return False

    """-----------------"""
    """Authoring methods"""
    """-----------------"""

    def addAgent(self,agent):
        if self.agents.has_key(agent.name):
            raise NameError,'Agent %s already exists in this world' % (agent.name)
        else:
            self.agents[agent.name] = agent
            agent.world = self

    def setDynamics(self,entity,feature,action,tree,enforceMin=False,enforceMax=False):
        """
        Defines the effect of an action on a given state feature
        @param entity: the entity whose state feature is affected (C{None} if on the world itself)
        @type entity: str
        @param feature: the name of the affected state feature
        @type feature: str
        @param action: the action affecting the state feature
        @type action: L{Action} or L{ActionSet}
        @param tree: the decision tree defining the effect
        @type tree: L{KeyedTree}
        """
        assert self.features.has_key(entity),'No state features defined for entity "%s"' % (entity)
        assert self.features[entity].has_key(feature),'No feature "%s" defined for entity "%s"' % (feature,entity)
        if isinstance(action,Action):
            action = ActionSet([action])
        if entity is None:
            key = feature
        else:
            key = stateKey(entity,feature)
        for atom in action:
            assert self.agents.has_key(atom['subject']),'Unknown actor %s' % (atom['subject'])
            assert self.agents[atom['subject']].hasAction(atom),'Unknown action %s' % (atom)
        if not self.dynamics.has_key(key):
            self.dynamics[key] = {}
        # Translate symbolic names into numeric values
        tree = tree.desymbolize(self.symbols)
        if self.__NORMALIZE__:
            tree = tree.scale(self.ranges)
        if enforceMin and self.features[entity][feature]['domain'] in [int,float]:
            # Modify tree to enforce floor
            tree.floor(key,self.features[entity][feature]['lo'])
        if enforceMax and self.features[entity][feature]['domain'] in [int,float]:
            # Modify tree to enforce ceiling
            tree.ceil(key,self.features[entity][feature]['hi'])
        self.dynamics[key][action] = tree

    def getDynamics(self,key,action):
        if not self.dynamics.has_key(key):
            return []
        if isinstance(action,Action):
            action = ActionSet([action])
        elif not isinstance(action,ActionSet):
            # Table of actions by multiple agents
            action = ActionSet(action)
        try:
            return [self.dynamics[key][action]]
        except KeyError:
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
                            for key in atom.getParameters():
                                table[actionKey(key)] = atom[key]
                            dynamics.append(tree.desymbolize(table))
            return dynamics

    def addDependency(self,dependent,independent):
        """
        Adds a dependency between the dependent key and the independent key, indicating that the new value for the independent key should be determined first
        @type dependent: str
        @type independent: str
        """
        try:
            self.dependency[dependent][independent] = True
        except KeyError:
            self.dependency[dependent] = {independent: True}
        foundDep = False
        foundInd = False
        for entry in self.evaluationOrder:
            if foundDep:
                if foundInd:
                    # Independent was earlier, so we can stick dependent variable here and exit
                    entry.add(dependent)
                    break
                elif independent in entry:
                    # We have now found independent variable
                    foundInd = True
            else:
                if dependent in entry:
                    # Dependent is in the same time frame
                    entry.remove(dependent)
                    foundDep = True
                if independent in entry:
                    # Here is the independent variable
                    foundInd = True
                    if not foundDep:
                        # Dependent is somewhere later, so we're ok
                        break
        else:
            # Need to add another entry
            self.evaluationOrder.append(set([dependent]))

    """------------------"""
    """Turn order methods"""
    """------------------"""

    def setOrder(self,order):
        """
        Initializes the turn order to the given order
        @param order: the turn order, as a list of names (each agent acts in sequence) or a list of sets of names (agents within a set acts in parallel)
        @type order: str[] or {str}[]
        """
        for index in range(len(order)):
            if isinstance(order[index],set):
                names = order[index]
            else:
                names = [order[index]]
            for name in names:
                self.state.join(turnKey(name),float(index)+0.5)

    def next(self,vector=None):
        """
        @return: a list of agents (by name) whose turn it is in the current epoch
        @rtype: str[]
        """
        if vector is None:
            assert len(self.state) == 1,'Ambiguous state vector'
            vector = self.state.domain()[0]
        items = filter(lambda i: isTurnKey(i[0]),vector.items())
        if len(items) == 0:
            # No turn information in vector
            return []
        value = min(map(lambda i: int(i[1]),items))
        return map(lambda i: turn2name(i[0]),filter(lambda i: int(i[1]) == value,items))

    def deltaOrder(self,actions,vector):
        """
        @return: the new turn sequence resulting from the performance of the given actions
        """
        potentials = filter(lambda n: vector.has_key(turnKey(n)),self.agents.keys())
        for name in self.agents.keys():
            key = turnKey(name)
            if vector.has_key(key):
                dynamics = self.getDynamics(key,actions)
        # Figure out who has acted
        if isinstance(actions,dict):
            actors = actions.keys()
        elif isinstance(actions,ActionSet):
            actors = set()
            for atom in actions:
                actors.add(atom['subject'])
        # Create turn order matrix
        delta = KeyedMatrix()
        if len(actors) == len(potentials):
            # Everybody has acted (NOTE: Need to make this more sensitive to whose turn it is)
            for name in potentials:
                key = turnKey(name)
                delta[key] = KeyedVector({key: 1.})
        elif len(actors) == 1:
            # Only one agent has acted
            actor = actors.pop()
            position = vector[turnKey(actor)]
            for name in potentials:
                key = turnKey(name)
                if name == actor:
                    # Acted, move to end of line
                    delta[key] = KeyedVector({CONSTANT: float(len(self.agents))-0.5})
                elif vector[key] > position:
                    # Not acted, move ahead of actor
                    delta[key] = KeyedVector({key: 1.,CONSTANT: -1.})
                else:
                    # Not acted, but already ahead of actor
                    delta[key] = KeyedVector({key: 1.})
        else:
            raise NotImplementedError,'Currently unable to process mixed turn orders.'
        return delta

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

    def defineState(self,entity,feature,domain=float,lo=0.,hi=1.,description=None):
        """
        Define a state feature in this world
        @param entity: the name of the entity this feature pertains to (C{None} if feature is on the world itself)
        @type entity: str
        @param feature: the name of this new state feature
        @type feature: str
        @param domain: the domain of values for this feature. Acceptable values are:
           - float: continuous range
           - int: discrete numeric range
           - bool: True/False value
           - list: enumerated set of discrete values
        @type domain: class
        @param lo: for float/int features, the lowest possible value. for list features, a list of possible values.
        @type lo: float/int/list
        @param hi: for float/int features, the highest possible value
        @type hi: float/int
        @param description: optional text description explaining what this state feature means
        @type description: str
        """
        key = stateKey(entity,feature)
        if not self.features.has_key(entity):
            self.features[entity] = {}
        self.features[entity][feature] = {'domain': domain,'description': description}
        if domain is float:
            self.features[entity][feature].update({'lo': lo,'hi': hi})
            self.ranges[key] = (lo,hi)
        elif domain is int:
            self.features[entity][feature].update({'lo': int(lo),'hi': int(hi)})
            self.ranges[key] = (lo,hi)
        elif domain is list:
            assert isinstance(lo,list),'Please provide list of elements for state features of the list type'
            self.features[entity][feature].update({'elements': lo,'lo': None,'hi': None})
            for index in range(len(lo)):
                assert not self.symbols.has_key(lo[index]),'Symbol %s already defined' % (lo[index])
                self.symbols[lo[index]] = index
        elif domain is bool:
            self.features[entity][feature].update({'lo': None,'hi': None})
        else:
            raise ValueError,'Unknown domain type %s for state feature' % (domain)
        if entity is None:
            self.features[entity][feature]['key'] = feature
        else:
            self.features[entity][feature]['key'] = key
        self.evaluationOrder[0].add(key)

    def setState(self,entity,feature,value):
        """
        @param entity: the name of the entity whose state feature we're setting (does not have to be an agent)
        @type entity: str
        @type feature: str
        @type value: float or L{Distribution}
        """
        assert self.features.has_key(entity) and self.features[entity].has_key(feature)
        if self.features[entity][feature]['domain'] is bool:
            if value:
                value = 1.
            else:
                value = 0.
        elif self.features[entity][feature]['domain'] is list:
            value = self.features[entity][feature]['elements'].index(value)
        else:
            if self.__NORMALIZE__:
                lo = self.features[entity][feature]['lo']
                hi = self.features[entity][feature]['hi']
                value = float(value-lo)/float(hi-lo)
        if entity is None:
            self.state.join(feature,value)
        else:
            self.state.join(stateKey(entity,feature),value)

    def getState(self,entity,feature,state=None):
        """
        @param entity: the name of the entity of interest (C{None} if the feature of interest is of the world itself)
        @type entity: str
        @param feature: the state feature of interest
        @type feature: str
        @param state: the distribution over possible worlds (default is the current world state)
        @type state: L{VectorDistribution}
        @return: a distribution over values for the given feature
        @rtype: L{Distribution}
        """
        if state is None:
            state = self.state
        assert self.features.has_key(entity) and self.features[entity].has_key(feature)
        if entity is None:
            result = state.marginal(feature)
        else:
            result = state.marginal(stateKey(entity,feature))
        if self.features[entity][feature]['domain'] is bool:
            abstract = {True: 0.,False: 0.}
            for value in result.domain():
                if value > 0.5:
                    abstract[True] += result[value]
                else:
                    abstract[False] += result[value]
            result = Distribution(abstract)
        elif self.features[entity][feature]['domain'] is list:
            abstract = {}
            for value in result.domain():
                index = int(float(value)+0.1)
                abstract[self.features[entity][feature]['elements'][index]] = result[value]
            result = Distribution(abstract)
        elif self.__NORMALIZE__:
            abstract = {}
            lo = self.features[entity][feature]['lo']
            hi = self.features[entity][feature]['hi']
            for value in result.domain():
                new = value*(hi-lo) + lo
                if self.features[entity][feature]['domain'] is int:
                    new = int(new+0.5)
                abstract[new] = result[value]
            result = Distribution(abstract)
        return result

    def getMentalModel(self,modelee,vector):
        agent = self.agents[modelee]
        try:
            model = agent.index2model(vector[modelKey(modelee)])
        except KeyError:
            model = True
        return model

    def setMentalModel(self,modeler,modelee,distribution,model=True):
        """
        Sets the distribution over mental models one agent has of another entity
        """
        # Make sure distribution is probability distribution over floats
        if not isinstance(distribution,dict):
            distribution = {distribution: 1.}
        if not isinstance(distribution,Distribution):
            distribution = Distribution(distribution)
        for element in distribution.domain():
            if not isinstance(element,float):
                distribution.replace(element,float(self.agents[modelee].model2index(element)))
        # Make sure recursive levels match up
        modelerLevel = self.agents[modeler].models[model]['level']
        for element in distribution.domain():
            name = self.agents[modelee].index2model(element)
            assert self.agents[modelee].models[name]['level'] == modelerLevel - 1,\
                'Agent %s\'s %s model has belief level of %d, so its model %s for agent %s must have belief level of %d' % \
                (modeler,model,modelerLevel,name,modelee,modelerLevel-1)
        distribution.normalize()
        self.agents[modeler].setBelief(modelKey(modelee),distribution,model)

    def updateModels(self,outcome,vector):
        for name in filter(lambda n: not outcome['actions'].has_key(n),
                           self.agents.keys()):
            # Consider agents who did *not* act
            label = self.getMentalModel(name,vector)
            model = self.agents[name].models[label]
            if not model['beliefs'] is True:
                for actor,actions in outcome['actions'].items():
                    # Consider each agent who *did* act
                    actorKey = modelKey(actor)
                    if model['beliefs'].hasColumn(actorKey):
                        # Agent has uncertain beliefs about this actor
                        belief = model['beliefs'].marginal(actorKey)
                        prob = {}
                        for index in belief.domain():
                            # Consider the hypothesis mental models of this actor
                            hypothesis = self.agents[actor].models[self.agents[actor].index2model(index)]
                            denominator = 0.
                            V = {}
                            for alternative in self.agents[actor].getActions(outcome['old']):
                                # Evaluate all available actions with respect to the hypothesized mental model
                                V[alternative] = self.agents[actor].value(outcome['old'],alternative,model=hypothesis['name'])['V']
                                denominator += math.exp(hypothesis['rationality']*V[alternative])
                            # Convert into probability distribution of observed action given hypothesized mental model
                            prob[index] = math.exp(hypothesis['rationality']*V[actions])/denominator
                            # Bayes' rule
                            prob[index] *= belief[index]
                        # Update posterior beliefs over mental models
                        prob = Distribution(prob)
                        prob.normalize()
                        model['beliefs'].join(actorKey,prob)

    def scaleState(self,vector):
        """
        Normalizes the given state vector so that all elements occur in [0,1]
        @param vector: the vector to normalize
        @type vector: L{KeyedVector}
        @return: the normalized vector
        @rtype: L{KeyedVector}
        """
        result = vector.__class__()
        remaining = dict(vector)
        # Handle defined state features
        for entity,table in self.features.items():
            for feature,entry in table.items():
                key = stateKey(entity,feature)
                if remaining.has_key(key):
                    if entry['domain'] is float or entry['domain'] is int:
                        # Scale by range of possible values
                        new = remaining[key]-entry['lo']
                        new /= entry['hi']-entry['lo']
                    elif entry['domain'] is list:
                        # Scale by size of set of values
                        new = remaining[key]/len(entry['elements'])
                    else:
                        new = remaining[key]
                    result[key] = new
                    del remaining[key]
        for name in self.agents.keys():
            # Handle turns
            key = turnKey(name)
            if remaining.has_key(key):
                result[key] = remaining[key] / len(self.agents)
                del remaining[key]
            # Handle models
            key = modelKey(name)
            if remaining.has_key(key):
                result[key] = remaining[key] / len(self.agents[name].models)
                del remaining[key]
        # Handle constant term
        if remaining.has_key(CONSTANT):
            result[CONSTANT] = remaining[CONSTANT]
            del remaining[CONSTANT]
        if remaining:
            raise NameError,'Unprocessed keys: %s' % (remaining.keys())
        return result

    def reachable(self,vector=None,transition=None,horizon=-1,ignore=[]):
        """
        @return: transition matrix among states reachable from the given state (default is current state)
        @rtype: KeyedVectorS{->}ActionSetS{->}VectorDistribution
        """
        envelope = set()
        transition = {}
        if vector is None:
            # Initialize with current state
            for vector in self.state.domain():
                envelope.add((vector,horizon))
        else:
            # Initialize with given state
            envelope.add((vector,horizon))
        while len(envelope) > 0:
            vector,horizon = envelope.pop()
            node = vector.filter(ignore)
            # Process next steps from this state
            transition[node] = {}
            if not self.terminated(vector) and horizon != 0:
                for actions in self.getActions(vector):
                    future = self.stepFromState(vector,actions)['new']
                    if isinstance(future,KeyedVector):
                        future = VectorDistribution({future: 1.})
                    transition[node][actions] = VectorDistribution()
                    for newVector in future.domain():
                        newNode = newVector.filter(ignore)
                        transition[node][actions][newNode] = future[newVector]
                        if not transition.has_key(newNode):
                            envelope.add((newNode,horizon-1))
        return transition
            
    def nearestVector(self,vector,vectors):
        mapping = {}
        for candidate in vectors:
            mapping[self.scaleState(candidate)] = candidate
        return mapping[self.scaleState(vector).nearestNeighbor(mapping.keys())]

    def getDescription(self,entity,feature):
        return self.features[entity][feature]['description']

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
            if level > 0: print >> buf,'%d%%' % (outcome['probability']*100.)
            if outcome.has_key('actions'):
                self.explainAction(outcome,buf,level)
                for name,action in outcome['actions'].items():
                    if not outcome['decisions'].has_key(name):
                        # No decision made
                        if level > 1: print >> buf,'\tforced'
                    elif level > 1:
                        # Explain decision
                        self.explainDecision(outcome['decisions'][name],buf,level)

    def explainAction(self,outcome,buf=None,level=0):
        if level > 0:
            for name,action in outcome['actions'].items():
                print >> buf,action
        return set(outcome['actions'].values())
        

    def explainDecision(self,decision,buf=None,level=2,prefix=''):
        """
        Subroutine of L{explain} for explaining agent decisions
        """
        if not decision.has_key('V'):
            # No value function
            return
        actions = decision['V'].keys()
        actions.sort(lambda x,y: cmp(str(x),str(y)))
        for alt in actions:
            V = decision['V'][alt]
            print >> buf,'%s\tV(%s) = %6.3f' % (prefix,alt,V['__EV__'])
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
                            print >> buf,'%sState:' % (tab)
                            self.printVector(node['old'],buf,prefix=tab,first=False)
                        print >> buf,'%s%s (V_%s=%6.3f)' % (tab,ActionSet(node['actions']),V[state]['agent'],node['R'])
                        for other in node['decisions'].keys():
                            self.explainDecision(node['decisions'][other],buf,level,prefix+'\t\t')
                        if level > 3: 
                            print >> buf,'%sEffect:' % (tab+prefix)
                            self.printDelta(node['old'],node['new'],buf,prefix=tab+prefix)
                        for index in range(len(node['projection'])):
                            nodes.insert(index,node['projection'][index])

    def printState(self,distribution=None,buf=None,prefix='',beliefs=False):
        """
        Utility method for displaying a distribution over possible worlds
        @type distribution: L{VectorDistribution}
        @param buf: the string buffer to put the string representation in (default is standard output)
        @param prefix: a string prefix (e.g., tabs) to insert at the beginning of each line
        @type prefix: str
        @param beliefs: if C{True}, print out inaccurate beliefs, too
        @type beliefs: True
        """
        if distribution is None:
            distribution = self.state
        for vector in distribution.domain():
            print >> buf,'%s%d%%' % (prefix,distribution[vector]*100.),
            self.printVector(vector,buf,prefix,beliefs=beliefs)

    def printVector(self,vector,buf=None,prefix='',first=True,beliefs=False,csv=False):
        """
        Utility method for displaying a single possible world
        @type vector: L{KeyedVector}
        @param buf: the string buffer to put the string representation in (default is standard output)
        @param prefix: a string prefix (e.g., tabs) to insert at the beginning of each line
        @type prefix: str
        @param first: if C{True}, then the first line is the continuation of an existing line (default is C{True})
        @type first: bool
        @param csv: if C{True}, then print the vector as comma-separated values (default is C{False})
        @type csv: bool
        """
        if csv:
            if prefix:
                elements = [prefix]
            else:
                elements = []
        entities = self.features.keys()
        entities.sort()
        change = False
        for entity in entities:
            table = self.features[entity]
            if entity is None:
                label = 'World'
            else:
                label = entity
            newEntity = True
            # Print state features for this entity
            for feature,entry in table.items():
                if entity is None:
                    key = feature
                else:
                    key = stateKey(entity,feature)
                if vector.has_key(key):
                    if csv:
                        elements.append(label)
                        elements.append(feature)
                    elif newEntity:
                        if first:
                            print >> buf,'\t%-12s' % (label),
                            first = False
                        else:
                            print >> buf,'%s\t%-12s' % (prefix,label),
                        print >> buf,'\t%-12s\t' % (feature+':'),
                        newEntity = False
                        change = True
                    else:
                        print >> buf,'%s\t\t\t%-12s\t' % (prefix,feature+':'),
                    # Generate string representation of feature value
                    if entry['domain'] is int:
                        value = '%d' % (int(vector[key]))
                    elif entry['domain'] is bool:
                        if vector[key] > 0.5:
                            value = str(True)
                        else:
                            value = str(False)
                    elif entry['domain'] is list:
                        index = int(float(vector[key])+.1)
                        value = entry['elements'][index]
                    else:
                        value = vector[key]
                    if csv:
                        elements.append(value)
                    else:
                        print >> buf,value
            if not entity is None:
                # Print model of this entity
                key = modelKey(entity)
                if vector.has_key(key):
                    if csv:
                        elements.append(label)
                        elements.append('__model__')
                        elements.append(self.agents[entity].index2model(vector[key]))
                    elif first:
                        print >> buf,'\t%-12s\t%-12s\t%-12s' % \
                            (label,'__model__',self.agents[entity].index2model(vector[key]))
                        change = True
                        first = False
                    else:
                        print >> buf,'%s\t%-12s\t%-12s\t%-12s' % \
                            (prefix,label,'__model__',self.agents[entity].index2model(vector[key]))
                    newEntity = False
                elif beliefs:
                    model = self.agents[entity].models[True]
                    if not model['beliefs'] is True:
                        print >> buf,'\t\t\t----beliefs:----'
                        self.printDelta(vector,self.agents[entity].getBelief(model['name'],vector),buf,'\t\t\t')
                        print >> buf,'\t\t\t----------------'
        if not csv and not change:
            print >> buf,'%s\tUnchanged' % (prefix)
        if (not vector.has_key('__END__') and self.terminated(vector)) or \
                (vector.has_key('__END__') and vector['__END__'] > 0.):
            if csv:
                elements.append('World')
                elements.append('__END__')
                elements.append(str(True))
            else:
                print >> buf,'%s\t__END__' % (prefix)
        elif csv:
            elements.append('World')
            elements.append('__END__')
            elements.append(str(False))
        if csv:
            print >> buf,','.join(elements)

    def printDelta(self,old,new,buf=None,prefix=''):
        deltaDist = VectorDistribution()
        for vector in new.domain():
            delta = KeyedVector()
            keys = []
            for name,table in self.features.items():
                for feature,entry in self.features[name].items():
                    # Look for change in feature value
                    keys.append(stateKey(name,feature))
                # Look for change in mental model of this agent
                key = modelKey(name)
                if vector.has_key(key):
                    keys.append(key)
                    if not old.has_key(key):
                        old = KeyedVector(vector)
                        old[key] = self.agents[name].model2index(True)
            for key in keys:
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
        doc.appendChild(root)
        # Agents
        for agent in self.agents.values():
            root.appendChild(agent.__xml__().documentElement)
        # State distribution
        node = doc.createElement('state')
        node.appendChild(self.state.__xml__().documentElement)
        for entity,table in self.features.items():
            for feature,entry in table.items():
                subnode = doc.createElement('feature')
                subnode.appendChild(doc.createTextNode(feature))
                if entity:
                    subnode.setAttribute('entity',entity)
                subnode.setAttribute('domain',entry['domain'].__name__)
                if not entry['lo'] is None:
                    subnode.setAttribute('lo',str(entry['lo']))
                if not entry['hi'] is None:
                    subnode.setAttribute('hi',str(entry['hi']))
                if entry['domain'] is list:
                    for element in entry['elements']:
                        subsubnode = doc.createElement('element')
                        subsubnode.appendChild(doc.createTextNode(element))
                        subnode.appendChild(subsubnode)
                if entry['description']:
                    subsubnode = doc.createElement('description')
                    subsubnode.appendChild(doc.createTextNode(entry['description']))
                    subnode.appendChild(subsubnode)
                node.appendChild(subnode)
        root.appendChild(node)
        # Dynamics
        node = doc.createElement('dynamics')
        for key,table in self.dynamics.items():
            subnode = doc.createElement('table')
            subnode.setAttribute('key',key)
            for action,tree, in table.items():
                subnode.appendChild(action.__xml__().documentElement)
                subnode.appendChild(tree.__xml__().documentElement)
            node.appendChild(subnode)
        root.appendChild(node)
        # Inter-state dependency
        node = doc.createElement('dependency')
        for key,table in self.dependency.items():
            subnode = doc.createElement('dependent')
            subnode.setAttribute('key',key)
            for ind in table.keys():
                subsubnode = doc.createElement('independent')
                subsubnode.appendChild(doc.createTextNode(ind))
                subnode.appendChild(subsubnode)
            node.appendChild(subnode)
        root.appendChild(node)
        # Termination conditions
        for termination in self.termination:
            node = doc.createElement('termination')
            node.appendChild(termination.__xml__().documentElement)
            root.appendChild(node)
        # Event history
        node = doc.createElement('history')
        for entry in self.history:
            subnode = doc.createElement('entry')
            for outcome in entry:
                subsubnode = doc.createElement('outcome')
                for name in self.agents.keys():
                    if outcome.has_key('actions') and outcome['actions'].has_key(name):
                        subsubnode.appendChild(outcome['actions'][name].__xml__().documentElement)
                if outcome.has_key('delta'):
                    subsubnode.appendChild(outcome['delta'].__xml__().documentElement)
                subsubnode.appendChild(outcome['old'].__xml__().documentElement)
                subnode.appendChild(subsubnode)
            node.appendChild(subnode)
        root.appendChild(node)
        return doc

    def parse(self,element):
        self.initialize()
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'agent':
                    self.addAgent(Agent(node))
                elif node.tagName == 'state':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            if subnode.tagName == 'distribution':
                                self.state.parse(subnode)
                            elif subnode.tagName == 'feature':
                                entity = str(subnode.getAttribute('entity'))
                                if not entity:
                                    entity = None
                                feature = str(subnode.firstChild.data).strip()
                                domain = eval(str(subnode.getAttribute('domain')))
                                description = None
                                lo = str(subnode.getAttribute('lo'))
                                if not lo: lo = None
                                hi = str(subnode.getAttribute('hi'))
                                if not hi: hi = None
                                if domain is int:
                                    if lo: lo = int(lo)
                                    if hi: hi = int(hi)
                                elif domain is float:
                                    if lo: lo = float(lo)
                                    if hi: hi = float(hi)
                                elif domain is bool:
                                    pass
                                elif domain is list:
                                    lo = []
                                else:
                                    raise TypeError,'Unknown feature domain type: %s' % (domain)
                                subsubnode = subnode.firstChild
                                while subsubnode:
                                    if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
                                        if subsubnode.tagName == 'element':
                                            assert domain is list
                                            lo.append(str(subsubnode.firstChild.data).strip())
                                        else:
                                            assert subsubnode.tagName == 'description'
                                            description = str(subsubnode.firstChild.data).strip()
                                    subsubnode = subsubnode.nextSibling
                                self.defineState(entity,feature,domain,lo,hi,description)
                        subnode = subnode.nextSibling
                elif node.tagName == 'dynamics':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'table'
                            key = str(subnode.getAttribute('key'))
                            self.dynamics[key] = {}
                            subsubnode = subnode.firstChild
                            action = None
                            while subsubnode:
                                if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
                                    if subsubnode.tagName == 'action':
                                        assert action is None
                                        action = Action(subsubnode)
                                    elif subsubnode.tagName == 'option':
                                        assert action is None
                                        action = ActionSet(subsubnode.childNodes)
                                    elif subsubnode.tagName == 'tree':
                                        assert not action is None
                                        self.dynamics[key][action] = KeyedTree(subsubnode)
                                        action = None
                                    else:
                                        raise NameError,'Unknown dynamics element: %s' % (subsubnode.tagName)
                                subsubnode = subsubnode.nextSibling
                        subnode = subnode.nextSibling
                elif node.tagName == 'dependency':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'dependent'
                            dep = str(subnode.getAttribute('key'))
                            subsubnode = subnode.firstChild
                            while subsubnode:
                                if subsubnode.nodeType == subnode.ELEMENT_NODE:
                                    assert subsubnode.tagName == 'independent'
                                    self.addDependency(dep,str(subsubnode.firstChild.data).strip())
                                subsubnode = subsubnode.nextSibling
                        subnode = subnode.nextSibling
                elif node.tagName == 'termination':
                    subnode = node.firstChild
                    while subnode and subnode.nodeType != subnode.ELEMENT_NODE:
                        subnode = subnode.nextSibling
                    if subnode:
                        self.termination.append(KeyedTree(subnode))
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
                                                option = ActionSet(element.childNodes)
                                                for action in option:
                                                    outcome['actions'][action['subject']] = option
                                                    break
                                            elif element.tagName == 'vector':
                                                outcome['old'] = KeyedVector(element)
                                            elif element.tagName == 'distribution':
                                                outcome['delta'] = VectorDistribution(element)
                                        element = element.nextSibling
                                    entry.append(outcome)
                                subsubnode = subsubnode.nextSibling
                            self.history.append(entry)
                        subnode = subnode.nextSibling
            node = node.nextSibling
        
    def save(self,filename,compressed=True):
        """
        @param compressed: if C{True}, then save in compressed XML; otherwise, save in XML (default is C{True})
        @type compressed: bool
        @return: the filename used (possibly with a .psy extension added)
        @rtype: str
        """
        if filename[-4:] != '.psy':
            filename = '%s.psy' % (filename)
        if compressed:
            f = bz2.BZ2File(filename,'w')
        else:
            f = file(filename,'w')
        f.write(self.__xml__().toprettyxml())
        f.close()
        return filename

def stateKey(name,feature):
    """
    @return: a key representation of a given entity's state feature
    @rtype: str
    """
    if name is None:
        return feature
    else:
        return '%s\'s %s' % (name,feature)
    
def turnKey(name):
    return stateKey(name,'_turn')

def isTurnKey(key):
    return key[-8:] == '\'s _turn'

def turn2name(key):
    return key[:-8]

def actionKey(feature):    
    return '__action__%s__' % (feature)

def modelKey(name):
    return stateKey(name,'_model')

def isModelKey(key):
    return key[-9:] == '\'s _model'

def model2name(key):
    return key[:-9]
