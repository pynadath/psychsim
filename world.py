import bz2
import copy
from xml.dom.minidom import Document,Node,parseString

from action import ActionSet,Action
from pwl import *
from probability import Distribution
from agent import Agent

class World:
    def __init__(self,xml=None):
        """
        @param xml: Initialization argument, either an XML Element, or a filename
        @type xml: Node or str
        """
        self.agents = {}
        self.state = VectorDistribution()
        self.features = {}
        self.symbols = {}
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
            outcome = self.stepFromState(stateVector,actions,real)
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
                    try:
                        state[new] += prob*outcome['probability']
                    except KeyError:
                        state[new] = prob*outcome['probability']
            self.history.append(outcomes)
        return outcomes

    def stepFromState(self,vector,actions=None,real=True,horizon=None):
        # Determine the actions taken by the agents in this world
        outcome = {'old': vector,
                   'decisions': {}}
        if actions is None:
            outcome['actions'] = {}
        else:
            outcome['actions'] = copy.copy(actions)
        for name in self.next(vector):
            if not outcome['actions'].has_key(name):
                decision = self.agents[name].decide(vector,horizon,outcome['actions'])
                outcome['decisions'][name] = decision
                outcome['actions'][name] = decision['action']
            elif isinstance(outcome['actions'][name],Action):
                outcome['actions'][name] = ActionSet([outcome['actions'][name]])
        outcome['effect'] = self.effect(outcome['actions'],vector)
        if real:
            outcome['new'] = outcome['effect']*outcome['old']
            outcome['delta'] = outcome['new'] - outcome['old']
        return outcome

    def effect(self,actions,vector):
        result = self.deltaState(actions,vector)
        result.update(self.deltaOrder(actions,vector))
        if vector.has_key(CONSTANT):
            result.update(KeyedMatrix({CONSTANT: KeyedVector({CONSTANT: 1.})}))
        return result

    def deltaState(self,actions,vector):
        result = MatrixDistribution({KeyedMatrix():1.})
        for entity,table in self.features.items():
            for feature,entry in table.items():
                dynamics = self.getDynamics(entry['key'],actions)
                if dynamics:
                    assert len(dynamics) == 1,'Unable to merge multiple effects'
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
        self.dynamics[key][action] = tree

    def getDynamics(self,key,action):
        if not self.dynamics.has_key(key):
            return []
        if isinstance(action,Action):
            action = ActionSet([action])
        elif not isinstance(action,ActionSet):
            # Table of actions by multiple agents
            action = ActionSet(reduce(frozenset.union,action.values(),frozenset()))
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

    def defineState(self,entity,feature,domain=float,lo=-1.,hi=1.):
        if not self.features.has_key(entity):
            self.features[entity] = {}
        self.features[entity][feature] = {'domain': domain}
        if domain is float:
            self.features[entity][feature].update({'lo': lo,'hi': hi})
        elif domain is int:
            self.features[entity][feature].update({'lo': int(lo),'hi': int(hi)})
        elif domain is list:
            assert isinstance(lo,list),'Please provide list of elements for state features of the list type'
            self.features[entity][feature].update({'elements': lo,'lo': None,'hi': None})
            for index in range(len(lo)):
                assert not self.symbols.has_key(lo[index]),'Symbol %s already defined' % (lo[index])
                self.symbols[lo[index]] = index
        else:
            self.features[entity][feature].update({'lo': None,'hi': None})
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
        if entity is None:
            self.state.join(feature,value)
        else:
            self.state.join(stateKey(entity,feature),value)

    def getState(self,entity,feature,state=None):
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
        return result

    def printState(self,buf=None):
        for vector in self.state.domain():
            print >> buf,'%d%%' % (self.state[vector]*100.),
            for entity,table in self.features.items():
                if entity is None:
                    label = 'World'
                else:
                    label = entity
                print >> buf,'\t%12s' % (label),
                first = True
                for feature,entry in table.items():
                    if first:
                        print >> buf,'\t%12s:\t' % (feature),
                        first = False
                    else:
                        print >> buf,'\t\t\t%12s:\t' % (feature),
                    if entity is None:
                        key = feature
                    else:
                        key = stateKey(entity,feature)
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
