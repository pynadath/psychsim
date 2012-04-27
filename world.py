import bz2
from xml.dom.minidom import Document,Node,parseString

from probability import VectorDistribution
from agent import Agent
from pwl import KeyedVector

class World:
    def __init__(self,xml=None):
        self.agents = {}
        self.order = []
        self.state = VectorDistribution()
        self.dynamics = {}
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
            self.state[KeyedVector({None: 1.})] = 1.

    def addAgent(self,agent):
        if self.agents.has_key(agent.name):
            raise NameError,'Agent %s already exists in this world' % (agent.name)
        else:
            self.agents[agent.name] = agent
            agent.world = self

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
        for agent in self.agents.values():
            root.appendChild(agent.__xml__().documentElement)
        node = doc.createElement('state')
        node.appendChild(self.state.__xml__().documentElement)
        root.appendChild(node)
        return doc

    def parse(self,element):
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'agent':
                    self.addAgent(Agent(node))
                elif node.tagName == 'state':
                    subnode = node.firstChild
                    while subnode and subnode.nodeType != subnode.ELEMENT_NODE:
                        subnode = subnode.nextSibling
                    self.state.parse(subnode,KeyedVector)
            node = node.nextSibling
        
    def save(self,filename,compressed=True):
        if compressed:
            f = bz2.BZ2File(filename,'w')
        else:
            f = file(filename,'w')
        f.write(self.__xml__().toprettyxml())
        f.close()
