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
    @ivar history: accumulated list of outcomes from simulation steps
    @type history: list
    """
    __NORMALIZE__ = False

    def __init__(self,xml=None):
        """
        @param xml: Initialization argument, either an XML Element, or a filename
        @type xml: Node or str
        """
        self.agents = {}
        self.state = VectorDistribution()
        self.features = {}
        self.symbols = {}
        self.ranges = {}
        self.dynamics = {}
        self.history = []
        if isinstance(xml,Node):
            self.parse(xml)
        elif isinstance(xml,str):
            if xml[-3:] == 'xml':
                # Uncompressed
                f = file(xml,'r')
            else:
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
        del self.history[:]

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
                    dist = (outcome['new'],1.)
                for new,prob in dist:
                    self.updateModels(outcome,new)
                    try:
                        state[new] += prob*outcome['probability']
                    except KeyError:
                        state[new] = prob*outcome['probability']
            self.history.append(outcomes)
        return outcomes

    def stepFromState(self,vector,actions=None,horizon=None):
        """
        Compute the resulting states when starting in a given possible world (as opposed to a distribution over possible worlds)
        """
        outcome = {'old': vector,
                   'decisions': {}}
        # Determine the actions taken by the agents in this world
        if actions is None:
            outcome['actions'] = {}
        else:
            outcome['actions'] = copy.copy(actions)
        for name in self.next(vector):
            if not outcome['actions'].has_key(name):
                agent = self.agents[name]
                try:
                    model = agent.index2model(vector[modelKey(name)])
                except KeyError:
                    model = True
                decision = self.agents[name].decide(vector,horizon,outcome['actions'],model)
                outcome['decisions'][name] = decision
                outcome['actions'][name] = decision['action']
            elif isinstance(outcome['actions'][name],Action):
                outcome['actions'][name] = ActionSet([outcome['actions'][name]])
        # Determine the effects of those actions
        outcome['effect'] = self.effect(outcome['actions'],vector)
        outcome['new'] = outcome['effect']*outcome['old']
        outcome['delta'] = outcome['new'] - outcome['old']
        return outcome

    def effect(self,actions,vector):
        # Update world state
        result = self.deltaState(actions,vector)
        # Update turn order
        result.update(self.deltaOrder(actions,vector))
        # Update agent beliefs
        for name,agent in self.agents.items():
            key = modelKey(name)
            if vector.has_key(key):
                result.update(KeyedMatrix({key: KeyedVector({key: 1.})}))
        # Constant factor does not change
        if vector.has_key(CONSTANT):
            result.update(KeyedMatrix({CONSTANT: KeyedVector({CONSTANT: 1.})}))
        return result

    def deltaState(self,actions,vector):
        result = MatrixDistribution({KeyedMatrix():1.})
        for entity,table in self.features.items():
            for feature,entry in table.items():
                dynamics = self.getDynamics(entry['key'],actions)
                if dynamics:
                    assert len(dynamics) == 1,'Unable to merge multiple effects of %s on %s' % \
                        (ActionSet(actions),entry['key'])
                    tree = dynamics[0]
                    matrix = tree[vector]
                else:
                    matrix = KeyedMatrix()
                    delta = KeyedVector()
                    if entry['domain'] is int:
                        delta[entry['key']] = 1
                    else:
                        delta[entry['key']] = 1.
                    matrix[entry['key']] = delta
                result.update(matrix)
        return result

    """-----------------"""
    """Authoring methods"""
    """-----------------"""

    def addAgent(self,agent):
        if self.agents.has_key(agent.name):
            raise NameError,'Agent %s already exists in this world' % (agent.name)
        else:
            self.agents[agent.name] = agent
            agent.world = self

    def setDynamics(self,entity,feature,action,tree):
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
        if isinstance(action,Action):
            action = ActionSet([action])
        if entity is None:
            key = feature
        else:
            key = stateKey(entity,feature)
        if not self.dynamics.has_key(key):
            self.dynamics[key] = {}
        # Translate symbolic names into numeric values
        tree = tree.desymbolize(self.symbols)
        if self.__NORMALIZE__:
            tree = tree.scale(self.ranges)
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
                            for key,value in atom.items():
                                if not key in atom.special:
                                    table[actionKey(key)] = value
                            dynamics.append(tree.desymbolize(table))
            return dynamics

    """------------------"""
    """Turn order methods"""
    """------------------"""

    def setOrder(self,order):
        for index in range(len(order)):
            if isinstance(order[index],list):
                names = order[index]
            else:
                names = [order[index]]
            for name in names:
                self.state.join(turnKey(name),float(index)+0.5)

    def next(self,vector):
        """
        @return: a list of agents (by name) whose turn it is in the current epoch
        @rtype: str[]
        """
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
        delta = KeyedMatrix()
        if len(actions) == len(self.agents):
            # Everybody has acted
            for name in self.agents.keys():
                key = turnKey(name)
                delta[key] = KeyedVector({key: 1.})
        elif len(actions) == 1:
            # Only one agent has acted
            actor = actions.keys()[0]
            position = vector[turnKey(actor)]
            for name in self.agents.keys():
                key = turnKey(name)
                if actions.has_key(name):
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

    """-------------"""
    """State methods"""
    """-------------"""

    def defineState(self,entity,feature,domain=float,lo=0.,hi=1.):
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
        """
        if not self.features.has_key(entity):
            self.features[entity] = {}
        self.features[entity][feature] = {'domain': domain}
        if domain is float:
            self.features[entity][feature].update({'lo': lo,'hi': hi})
            self.ranges[stateKey(entity,feature)] = (lo,hi)
        elif domain is int:
            self.features[entity][feature].update({'lo': int(lo),'hi': int(hi)})
            self.ranges[stateKey(entity,feature)] = (lo,hi)
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
            self.features[entity][feature]['key'] = stateKey(entity,feature)

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
        self.agents[modeler].setBelief(modelKey(modelee),distribution,model)

    def updateModels(self,outcome,vector):
        for name in filter(lambda n: not outcome['actions'].has_key(n),
                           self.agents.keys()):
            # Consider agents who did *not* act
            agent = self.agents[name]
            key = modelKey(name)
            try:
                label = agent.index2model(vector[key])
            except KeyError:
                label = True
            model = agent.models[label]
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
            for name,action in outcome['actions'].items():
                if level > 0: print >> buf,action
                if not outcome['decisions'].has_key(name):
                    # No decision made
                    if level > 1: print >> buf,'\tforced'
                elif level > 1:
                    # Explain decision
                    self.explainDecision(outcome['decisions'][name],buf,level)

    def explainDecision(self,decision,buf=None,level=2,prefix=''):
        """
        Subroutine of L{explain} for explaining agent decisions
        """
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
                            self.printState(node['delta'],buf,prune=True,prefix=tab+prefix)
                        for index in range(len(node['projection'])):
                            nodes.insert(index,node['projection'][index])

    def printState(self,distribution=None,buf=None,prune=False,prefix=''):
        """
        Utility method for displaying a distribution over possible worlds
        @type distribution: L{VectorDistribution}
        @param buf: the string buffer to put the string representation in (default is standard output)
        @param prune: if C{True}, don't print vector entries with 0 values (default is C{False})
        @type prune: bool
        @param prefix: a string prefix (e.g., tabs) to insert at the beginning of each line
        @type prefix: str
        """
        if distribution is None:
            distribution = self.state
        for vector in distribution.domain():
            print >> buf,'%s%d%%' % (prefix,distribution[vector]*100.),
            self.printVector(vector,buf,prune,prefix)

    def printVector(self,vector,buf=None,prune=False,prefix='',first=True):
        """
        Utility method for displaying a single possible world
        @type vector: L{KeyedVector}
        @param buf: the string buffer to put the string representation in (default is standard output)
        @param prune: if C{True}, don't print vector entries with 0 values (default is C{False})
        @type prune: bool
        @param prefix: a string prefix (e.g., tabs) to insert at the beginning of each line
        @type prefix: str
        @param first: if C{True}, then the first line is the continuation of an existing line (default is C{True})
        @type first: bool
        """
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
            if not entity is None:
                # Print model of this entity
                key = modelKey(entity)
                if vector.has_key(key):
                    if not prune or abs(vector[key]) > vector.epsilon:
                        if first:
                            print >> buf,'\t%-12s\t%-12s\t%-12s' % \
                                (label,'__model__',self.agents[entity].index2model(vector[key]))
                            first = False
                        else:
                            print >> buf,'%s\t%-12s\t%-12s\t%-12s' % \
                                (prefix,label,'__model__',self.agents[entity].index2model(vector[key]))
                        newEntity = False
            # Print state features for this entity
            for feature,entry in table.items():
                if entity is None:
                    key = feature
                else:
                    key = stateKey(entity,feature)
                if vector.has_key(key) and \
                        (not prune or abs(vector[key]) > vector.epsilon):
                    if newEntity:
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
                    if entry['domain'] is int:
                        print >> buf,int(vector[key])
                    elif entry['domain'] is bool:
                        if vector[key] > 0.5:
                            print >> buf,True
                        else:
                            print >> buf,False
                    elif entry['domain'] is list:
                        index = int(float(vector[key])+.1)
                        print >> buf,entry['elements'][index]
                    else:
                        print >> buf,vector[key]
        if prune and not change:
            print >> buf,'\tUnchanged'
        
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
        # Event history
        node = doc.createElement('history')
        for entry in self.history:
            subnode = doc.createElement('entry')
            for outcome in entry:
                subsubnode = doc.createElement('outcome')
                for name in self.agents.keys():
                    if outcome['actions'].has_key(name):
                        subsubnode.appendChild(outcome['actions'][name].__xml__().documentElement)
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
                                    subsubnode = subnode.firstChild
                                    while subsubnode:
                                        if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
                                            assert subsubnode.tagName == 'element'
                                            lo.append(str(subsubnode.firstChild.data).strip())
                                        subsubnode = subsubnode.nextSibling
                                else:
                                    raise TypeError,'Unknown feature domain type: %s' % (domain)
                                self.defineState(entity,feature,domain,lo,hi)
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
        if compressed:
            f = bz2.BZ2File(filename,'w')
        else:
            f = file(filename,'w')
        f.write(self.__xml__().toprettyxml())
        f.close()

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
    return stateKey('__action__',feature)

def modelKey(name):
    return stateKey(name,'_model')

def isModelKey(key):
    return key[-9:] == '\'s _model'

def model2name(key):
    return key[:-9]
