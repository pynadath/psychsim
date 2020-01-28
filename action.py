import itertools
from xml.dom.minidom import Document,Element,Node,NodeList,parseString

class Action(dict):
    """
    :cvar special: a list of keys that are reserved for system use
    :type special: list(str)
    """
    special = ['subject','verb','object']

    def __init__(self,arg={},description=None):
        if isinstance(arg,Node):
            dict.__init__(self)
            self.parse(arg)
        if isinstance(arg,str):
            values = arg.split('-')
            dict.__init__(self,{self.special[i]: values[i] for i in range(len(values))})
        else:
            dict.__init__(self,arg)
        self._string = None
        self.description = description

    def match(self,pattern):
        for key,value in pattern.items():
            if not key in self or self[key] != value:
                # Mismatch
                return False
        else:
            # Match
            return True
        
    def agentLess(self):
        """
        Utility method that returns a subject-independent version of this action
        :rtype: Action
        """
        args = dict(self)
        try:
            del args['subject']
            return self.__class__(args)
        except KeyError:
            return self.__class__(self)

    def getParameters(self):
        """
        :return: list of special parameters for this action
        :rtype: list(str)
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
        :return: the base action table, with only special keys "subject", "verb", and "object"
        :rtype: Action
        """
        root = {}
        for key in self.special:
            if key in self:
                root[key] = self[key]
        return Action(root)

    def __str__(self):
        if self._string is None:
            elements = []
            keys = list(self.keys())
            for special in self.special:
                if special in self:
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
        node = doc.createElement('description')
        if self.description:
            node.appendChild(doc.createTextNode(self.description))
        root.appendChild(node)
        return doc

    def parse(self,element):
        assert element.tagName == 'action'
        self.clear()
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'entry':
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
                elif child.tagName == 'description':
                    while subchild.nodeType != subchild.TEXT_NODE:
                        subchild = subchild.nextSibling
                    self.description = str(subchild.data).strip()
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
            iterable = set()
            for subset in elements.values():
                iterable |= subset
#            iterable = reduce(ActionSet.union,elements.values(),ActionSet())
        else:
            iterable = elements
        return frozenset.__new__(cls,iterable)

    def match(self,pattern):
        """
        :param pattern: a table of key-value patterns that the action must match
        :type pattern: dict
        :return: the first action that matches the given pattern, or C{None} if none
        :rtype: Action
        """
        for action in self:
            if action.match(pattern):
                return action
        else:
            # No matching actions
            return None

    def __getitem__(self,key):
        elements = list(self)
        result = elements[0].get(key,None)
        for atom in elements[1:]:
            if key in atom and atom[key] != result:
                raise ValueError('Conflicting values for key: %s' % (key))
        return result

    def get(self,key,default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
        
    def __str__(self):
        return ','.join(map(str,self))

    def __hash__(self):
        return hash(str(self))

    def __lt__(self,other):
        return str(self) < str(other)

    def agentLess(self):
        """
        Utility method that returns a subject-independent version of this action set
        :rtype: ActionSet
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
    :type pattern: dict
    :return: the subset of given actions that match the given pattern
    """
    return filter(lambda a: a.match(pattern),actions)

def powerset(iterable):
    """
    Utility function, taken from Python doc recipes
    powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)
    """
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))

def makeActionSet(subject,verb,obj=None):
    if obj is None:
        return ActionSet([Action({'subject': subject,'verb': verb})])
    else:
        return ActionSet([Action({'subject': subject,'verb': verb,'object': obj})])

if __name__ == '__main__':
    act1 = Action({'subject': 'I','verb': 'help','object': 'you'})    
    act2 = Action({'subject': 'you','verb': 'help','object': 'I'})
    old = ActionSet([act1,act2])
    print(old)
    doc = parseString(old.__xml__().toprettyxml())
    new = ActionSet(doc.documentElement.childNodes)
    print(new)
    print(old == new)
