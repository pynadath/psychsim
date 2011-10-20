from xml.dom.minidom import *

class MultiagentSystem(dict):
    """Base class for a generic collection of agents
    @ivar extra: dictionary of miscellaneous parameters for this system
    """
    
    def __init__(self,agents=[]):
        """Initializes a collection to contain the given list of agents"""
        if isinstance(agents,dict):
            agents = agents.values()
        for agent in agents:
            self.addMember(agent)
        self.extra = {}

    def initialize(self):
        """Do any necessary preparation before doing whatever
        """
        pass
    
    def members(self):
        """
        @return: a list of the member agents, in decreasing order according to whatever comparison function has been defined on the agent class
        @rtype: C{L{teamwork.agent.Agent}[]}
        """
        return self.values()

    def addMember(self,agent):
        """Adds the agent to this collection
        @param agent: the agent to add
        @type agent: L{teamwork.agent.Agent}
        @warning: will clobber any pre-existing agent with the same name
        """
        self[agent.name] = agent
        agent.world = self
        
    def getMember(self,agent):
        """
        @warning: Deprecated, use C{self[name]} instead
        @return: the member agent contained in this team that corresponds to the specified agent object or string name
        """
        raise DeprecationWarning,\
                  'Use __getitem__ instead (e.g., "entities[%s]")' % \
                  (agent)
            
    def save(self,name):
        """Stores this MAS at the specified file location.  The storage format is based on the file extension:
           - C{xml}: Store in PsychSim's XML format
           - C{scn}: compressed XML (default)
        @param name: the string filename
        @type name: C{str}"""
        doc = self.__xml__()
        if name[-3:] == 'xml':
            f = open(name,'w')
        else:
            import bz2
            f = bz2.BZ2File(name,'w')
        f.write(doc.toxml())
        f.close()

    def __copy__(self):
        dict.__copy__(self)
        
    def __deepcopy__(self,memo):
        dict.__deepcopy__(self,memo)
        
    def __str__(self):
        content = ''
        for agent in self.members():
            content += str(agent)
        return content

    def __xml__(self):
        doc = Document()
        root = doc.createElement('multiagent')
        root.setAttribute('type',self.__class__.__name__)
        for key,value in self.extra.items():
            root.setAttribute(key,value)
        doc.appendChild(root)
        for agent in self.members():
            root.appendChild(agent.__xml__().documentElement)
        return doc

    def parse(self,element,agentClass=None):
        for index in range(element.attributes.length):
            attr = element.attributes.item(index)
            if not attr.name in ['type','time']:
                self.extra[str(attr.name)] = str(attr.nodeValue)
        child = element.firstChild
        while child:
            if child.nodeType == Node.ELEMENT_NODE:
                if child.tagName == 'agent':
                    agent = agentClass(None)
                    agent.parse(child)
                    self.addMember(agent)
            child = child.nextSibling
