import copy
from xml.dom.minidom import Document,Node
from action import Action,ActionSet

class Agent:
    def __init__(self,name):
        self.world = None
        self.subjective = None
        self.actions = set()
        self.reward = set()
        if isinstance(name,Document):
            self.parse(name.documentElement)
        elif isinstance(name,Node):
            self.parse(name)
        else:
            self.name = name

    def setState(self,feature,value):
        self.world.setState(self.name,feature,value)

    def addAction(self,action):
        new = ActionSet()
        if isinstance(action,set):
            for atom in action:
                if isinstance(atom,Action):
                    new.add(Action(atom))
                else:
                    new.add(atom)
        elif isinstance(action,Action):
            new.add(action)
        else:
            assert isinstance(action,dict),'Argument to addAction must be at least a dictionary'
            new.add(Action(action))
        for atom in new:
            if not atom.has_key('subject'):
                # Make me the subject of these actions
                atom['subject'] = self.name
        self.actions.add(new)

    def observe(self,observation,subjective=None):
        """
        @param observation: the observation received by this agent
        @param subjective: the pre-observation beliefs of this agent (default is current beliefs)
        @return: the post-observation beliefs of this agent
        """
        if subjective is None:
            subjective = self.subjective
            
    def __copy__(self):
        new = Agent(self.name)
        new.actions = copy.copy(self.actions)
        new.reward = copy.copy(self.reward)

    def __xml__(self):
        doc = Document()
        root = doc.createElement('agent')
        doc.appendChild(root)
        doc.documentElement.setAttribute('name',self.name)
        # Actions
        node = doc.createElement('actions')
        root.appendChild(node)
        for action in self.actions:
            node.appendChild(action.__xml__().documentElement)
        return doc

    def parse(self,element):
        self.name = str(element.getAttribute('name'))
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'actions':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            self.actions.add(ActionSet(subnode))
                        subnode = subnode.nextSibling
            node = node.nextSibling
