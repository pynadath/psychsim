import itertools
from xml.dom.minidom import Document,Element,Node,NodeList,parseString

class Action(dict):
    """
    @cvar special: a list of keys that are reserved for system use
    @type special: str[]
    """
    special = ['subject','verb','object']

    def __init__(self,arg={}):
        if isinstance(arg,Node):
            dict.__init__(self)
            self.parse(arg)
        else:
            dict.__init__(self,arg)
        self._string = None
        
    def agentLess(self):
        """
        Utility method that returns a subject-independent version of this action
        @rtype: L{Action}
        """
        args = dict(self)
        try:
            del args['subject']
            return self.__class__(args)
        except KeyError:
            return self.__class__(self)

    def getParameters(self):
        """
        @return: list of special parameters for this action
        @rtype: str[]
        """
        return filter(lambda k: not k in self.special,self.keys())

    def __setitem__(self,key,value):
        self._string = None
        dict.__setitem__(self,key,value)

    def clear(self):
        self._string = None
        dict.clear(self)

    def root(self):
        """
        @return: the base action table, with only special keys "subject", "verb", and "object"
        @rtype: L{Action}
        """
        root = {}
        for key in self.special:
            if self.has_key(key):
                root[key] = self[key]
        return Action(root)

    def __str__(self):
        if self._string is None:
            elements = []
            keys = self.keys()
            for special in self.special:
                if self.has_key(special):
                    elements.append(self[special])
                    keys.remove(special)
            keys.sort()
            elements += map(lambda k: self[k],keys)
            self._string = '-'.join(map(str,elements))
        return self._string

    def __hash__(self):
        return hash(str(self))

    def __xml__(self):
        doc = Document()
        root = doc.createElement('action')
        doc.appendChild(root)
        for key,value in self.items():
            node = doc.createElement('entry')
            node.setAttribute('key',key)
            node.appendChild(doc.createTextNode(str(value)))
            root.appendChild(node)
        return doc

    def parse(self,element):
        assert element.tagName == 'action'
        self.clear()
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                assert child.tagName == 'entry'
                key = str(child.getAttribute('key'))
                subchild = child.firstChild
                while subchild.nodeType != subchild.TEXT_NODE:
                    subchild = subchild.nextSibling
                value = str(subchild.data).strip()
                if not key in self.special:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                self[key] = value
            child = child.nextSibling
    
class ActionSet(frozenset):

    def __new__(cls,elements=[]):
        if isinstance(elements,Element):
            iterable = []
            node = elements.firstChild
            while node:
                if node.nodeType == node.ELEMENT_NODE and node.tagName == 'action':
                    assert node.tagName == 'action','Element has tag %s instead of action' % (node.tagName)
                    atom = Action(node)
                    iterable.append(atom)
                node = node.nextSibling
                
        elif isinstance(elements,NodeList):
            iterable = []
            for node in elements:
                if node.nodeType == node.ELEMENT_NODE and node.tagName == 'action':
                    assert node.tagName == 'action','Element has tag %s instead of action' % (node.tagName)
                    atom = Action(node)
                    iterable.append(atom)
        elif isinstance(elements,Action):
            iterable = [elements]
        elif isinstance(elements,dict):
            iterable = reduce(ActionSet.union,elements.values(),ActionSet())
        else:
            iterable = elements
        return frozenset.__new__(cls,iterable)

    def match(self,pattern):
        """
        @param pattern: a table of key-value patterns that the action must match
        @type pattern: dict
        @return: the first action that matches the given pattern, or C{None} if none
        @rtype: L{Action}
        """
        for action in self:
            for key,value in pattern.items():
                if not action.has_key(key) or action[key] != value:
                    # Mismatch
                    break
            else:
                # Match
                return action
        else:
            # No matching actions
            return None

    def __getitem__(self,key):
        elements = list(self)
        result = elements[0][key]
        for atom in elements[1:]:
            if atom.has_key(key) and atom[key] != result:
                raise ValueError,'Conflicting values for key: %s' % (key)
        return result

    def __str__(self):
        return ','.join(map(str,self))

    def __hash__(self):
        return hash(str(self))

    def __lt__(self,other):
        return str(self) < str(other)

    def agentLess(self):
        """
        Utility method that returns a subject-independent version of this action set
        @rtype: L{ActionSet}
        """
        return self.__class__([a.agentLess() for a in self])

    def __xml__(self):
        doc = Document()
        root = doc.createElement('option')
        doc.appendChild(root)
        for atom in self:
            root.appendChild(atom.__xml__().documentElement)
        return doc

def filterActions(pattern,actions):
    """
    @type pattern: dict
    @return: the subset of given actions that match the given pattern
    """
    return filter(lambda a: a.match(pattern),actions)

def powerset(iterable):
    """
    Utility function, taken from Python doc recipes
    powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)
    """
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))

if __name__ == '__main__':
    act1 = Action({'subject': 'I','verb': 'help','object': 'you'})    
    act2 = Action({'subject': 'you','verb': 'help','object': 'I'})
    old = ActionSet([act1,act2])
    print old
    doc = parseString(old.__xml__().toprettyxml())
    new = ActionSet(doc.documentElement.childNodes)
    print new
    print old == new
