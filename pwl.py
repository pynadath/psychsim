"""
Class and function definitions for PieceWise Linear (PWL) representations
"""
from xml.dom.minidom import Document,Node

CONSTANT = ''

class KeyedVector(dict):
    epsilon = 1e-8

    def __init__(self,arg={}):
        if isinstance(arg,Node):
            dict.__init__(self)
            self.parse(arg)
        else:
            dict.__init__(self,arg)
        self._string = None
        
    def __eq__(self,other):
        delta = 0.
        tested = {}
        for key,value in self.items():
            try:
                delta += abs(value-other[key])
            except KeyError:
                delta += abs(value)
            tested[key] = True
        for key,value in other.items():
            if not tested.has_key(key):
                delta += abs(value)
        return delta < self.epsilon

    def __ne__(self,other):
        return not self == other

    def __add__(self,other):
        result = KeyedVector(self)
        for key,value in other.items():
            try:
                result[key] += value
            except KeyError:
                result[key] = value
        return result

    def __neg__(self):
        result = KeyedVector()
        for key,value in self.items():
            result[key] = -value
        return result

    def __sub__(self,other):
        return self + (-other)

    def __mul__(self,other):
        if isinstance(other,KeyedVector):
            # Dot product
            total = 0.
            for key,value in self.items():
                if other.has_key(key):
                    total += value*other[key]
            return total
        elif isinstance(other,float):
            result = KeyedVector()
            for key,value in result.items():
                result[key] = value*scalar
            return result
        else:
            raise TypeError,'Unable to multiply %s by %s' % \
                (self.__class__.__name__,other.__class__.__name__)

    def __setitem__(self,key,value):
        self._string = None
        dict.__setitem__(self,key,value)

    def __str__(self):
        if self._string is None:
            self._string = ', '.join(map(lambda item: '%s=%s' % item,
                                         self.items()))
        return self._string

    def __hash__(self):
        return hash(str(self))

    def __xml__(self):
        doc = Document()
        root = doc.createElement('vector')
        for key,value in self.items():
            node = doc.createElement('entry')
            node.setAttribute('key',key)
            node.setAttribute('value',str(value))
            root.appendChild(node)
        doc.appendChild(root)
        return doc

    def parse(self,element):
        self._string = None
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert node.tagName == 'entry'
                key = str(node.getAttribute('key'))
                value = float(node.getAttribute('value'))
                dict.__setitem__(self,key,value)
            node = node.nextSibling

class KeyedMatrix(dict):
    def __init__(self,arg={}):
        dict.__init__(self,arg)
        self._string = None

    def __eq__(self,other):
        for key,vector in self.items():
            try:
                if vector != other[key]:
                    return False
            except KeyError:
                if vector != {}:
                    return False
        else:
            return True

    def __ne__(self,other):
        return not self == other

    def __neg__(self):
        result = KeyedMatrix()
        for key,vector in self.items():
            result[key] = -vector
        return result

    def __add__(self,other):
        result = KeyedMatrix()
        for key,vector in self.items():
            try:
                result[key] = vector + other[key]
            except KeyError:
                result[key] = KeyedVector(vector)
        for key,vector in other.items():
            if not result.has_key(key):
                result[key] = KeyedVector(vector)
        return result

    def __sub__(self,other):
        return self + (-other)

    def __mul__(self,other):
        if isinstance(other,KeyedMatrix):
            result = KeyedMatrix()
            for r1,v1 in self.items():
                result[r1] = KeyedVector()
                for c1,value1 in v1.items():
                    for r2,v2 in other.items():
                        for c2,value2 in v2.items():
                            try:
                                result[r1][c2] += value1*value2
                            except KeyError:
                                result[r1][c2] = value1*value2
        elif isinstance(other,KeyedVector):
            result = KeyedVector()
            for r1,v1 in self.items():
                result[r1] = KeyedVector()
                for c1,value1 in v1.items():
                    for c2,value2 in other.items():
                        try:
                            result[r1] += value1*value2
                        except KeyError:
                            result[r1] = value1*value2
        else:
            raise TypError,'Unable to multiply %s by %s' % \
                (self.__class__.__name__,other.__class__.__name__)
        return result

    def __setitem__(self,key,value):
        assert isinstance(value,KeyedVector),'Illegal row type: %s' % \
            (value.__class__.__name__)
        self._string = None
        dict.__setitem__(self,key,value)


    def __str__(self):
        if self._string is None:
            joiner = lambda item: '%s*%s' % (item[1],item[0])
            self._string = '\n'.join(map(lambda item: '%s) %s' % \
                                             (item[0],' + '.join(map(joiner,
                                                                    item[1].items()))),
                                         self.items()))
        return self._string

    def __hash__(self):
        return hash(str(self))

class KeyedPlane:
    def __init__(self,vector,threshold):
        self.vector = vector
        self.threshold = threshold

class KeyedTree:
    def __init__(self,leaf=None):
        self.leaf = True
        self.children = [leaf]
        self.branch = None
            
    def isLeaf(self):
        return self.leaf

    def makeLeaf(self,leaf):
        self.children = [leaf]
        self.leaf = True
