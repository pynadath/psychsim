import bz2
import copy
from xml.dom.minidom import Document,Node,parseString

from probability import VectorDistribution
from pwl import KeyedVector,KeyedMatrix,CONSTANT
from action import ActionSet
from agent import Agent

class World:
    def __init__(self,xml=None):
        self.agents = {}
        self.state = VectorDistribution()
        self.features = {}
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
        self.dynamics.clear()
        del self.history[:]

    def addAgent(self,agent):
        if self.agents.has_key(agent.name):
            raise NameError,'Agent %s already exists in this world' % (agent.name)
        else:
            self.agents[agent.name] = agent
            agent.world = self

    def step(self,actions={},state=None,hypothetical=True):
        if state is None:
            state = self.state
        outcomes = []
        # Iterate through each possible world
        for stateVector in state.domain():
            prob = state[stateVector]
            # Determine the actions taken by the agents in this world
            turn = copy.copy(actions)
            for name in self.next(stateVector):
                if not actions.has_key(name):
                    decision = self.agents[name].decide(stateVector)
                    turn[name] = decision['action']
            outcomes.append({'original': stateVector,
                             'actions': turn,
                             'probability': prob,
                             'effect': self.effect(turn,stateVector)
                             })
        if not hypothetical:
            # Apply effects
            self.history.append(outcomes)
        return outcomes

    def effect(self,actions,vector):
        result = self.deltaState(actions,vector)
        result.update(self.deltaOrder(actions,vector))
        return result

    def deltaState(self,actions,vector):
        result = KeyedMatrix()
        for entity,table in self.features.items():
            for feature,domain in table.items():
                if self.dynamics.has_key(entity) and self.dynamics[entity].has_key(feature):
                    key = stateKey(entity,feature)
                    table = self.dynamics[entity][feature]
                    vector = KeyedVector()
                    if domain is float:
                        vector[key] = 1.
                    elif domain is int:
                        vector[key] = 1
                    result[key] = vector
        return result

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
            raise NotImplementedError,'Currently unable to process serial execution.'
        else:
            raise NotImplementedError,'Currently unable to process mixed turn orders.'
        return delta

    def defineState(self,entity,feature,domain=float,lo=-1.,hi=1.):
        if not self.features.has_key(entity):
            self.features[entity] = {}
        self.features[entity][feature] = {'domain': domain,'lo': lo,'hi': hi}

    def setState(self,entity,feature,value):
        """
        @param entity: the name of the entity whose state feature we're setting (does not have to be an agent)
        @type entity: str
        @type feature: str
        @type value: float or L{Distribution}
        """
        self.state.join("%s's %s" % (entity,feature),value)

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
                subnode.setAttribute('entity',entity)
                if entry['domain'] is int:
                    subnode.setAttribute('domain','int')
                elif entry['domain'] is float:
                    subnode.setAttribute('domain','float')
                else:
                    raise TypeError,'Unable to serialize state features with domain of type %s' % (entry['domain'].__name__)
                if not entry['lo'] is None:
                    subnode.setAttribute('lo',str(entry['lo']))
                if not entry['hi'] is None:
                    subnode.setAttribute('hi',str(entry['hi']))
                node.appendChild(subnode)
        root.appendChild(node)
        node = doc.createElement('history')
        for entry in self.history:
            subnode = doc.createElement('entry')
            for outcome in entry:
                subsubnode = doc.createElement('outcome')
                for name in self.agents.keys():
                    if outcome['actions'].has_key(name):
                        subsubnode.appendChild(outcome['actions'][name].__xml__().documentElement)
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
                                self.state.parse(subnode,KeyedVector)
                            elif subnode.tagName == 'feature':
                                entity = str(subnode.getAttribute('entity'))
                                feature = str(subnode.firstChild.data).strip()
                                domain = str(subnode.getAttribute('domain'))
                                lo = str(subnode.getAttribute('lo'))
                                if not lo:
                                    lo = None
                                hi = str(subnode.getAttribute('hi'))
                                if not hi:
                                    hi = None
                                if domain == 'int':
                                    domain = int
                                    if lo:
                                        lo = int(lo)
                                    if hi:
                                        hi = int(hi)
                                elif subnode.getAttribute('domain') == 'float':
                                    domain = float
                                    if lo:
                                        lo = float(lo)
                                    if hi:
                                        hi = float(hi)
                                else:
                                    raise TypeError,'Unknown feature domain type: %s' % (domain)
                                self.defineState(entity,feature,domain,lo,hi)
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
                                                option = ActionSet(element)
                                                for action in option:
                                                    outcome['actions'][action['subject']] = option
                                                    break
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
    return '%s\'s %s' % (name,feature)
    
def turnKey(name):
    return stateKey(name,'_turn')

def isTurnKey(key):
    return key[-8:] == '\'s _turn'

def turn2name(key):
    return key[:-8]
