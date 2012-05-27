"""
Class and function definitions for PieceWise Linear (PWL) representations
"""
import copy
from xml.dom.minidom import Document,Node
from probability import Distribution

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
            self._string = '\n'.join(map(lambda item: '%s: %s' % item,
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

class VectorDistribution(Distribution):
    """
    A class representing a L{Distribution} over L{KeyedVector} instances
    """

    def join(self,key,value):
        if isinstance(value,Distribution):
            raise NotImplementedError,'Wait for it'
        else:
            for row in self.domain():
                prob = self[row]
                del self[row]
                row[key] = value
                self[row] = prob

    def element2xml(self,value):
        return value.__xml__().documentElement

    def xml2element(self,key,node):
        return KeyedVector(node)

    def marginal(self,key):
        result = {}
        for row in self.domain():
            result[row[key]] = self[row]
        return Distribution(result)

    def select(self):
        """
        Reduce distribution to a single element, sampled according to the given distribution
        """
        vector = self.sample()
        self.clear()
        self[vector] = 1.
        return vector

class KeyedMatrix(dict):
    def __init__(self,arg={}):
        if isinstance(arg,Node):
            dict.__init__(self)
            self.parse(arg)
        else:
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
                for c1,value1 in v1.items():
                    if other.has_key(c1):
                        try:
                            result[r1] += value1*other[c1]
                        except KeyError:
                            result[r1] = value1*other[c1]
        else:
            raise TypError,'Unable to multiply %s by %s' % \
                (self.__class__.__name__,other.__class__.__name__)
        return result

    def __setitem__(self,key,value):
        assert isinstance(value,KeyedVector),'Illegal row type: %s' % \
            (value.__class__.__name__)
        self._string = None
        dict.__setitem__(self,key,value)

    def update(self,other):
        self._string = None
        dict.update(self,other)
    
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

    def __xml__(self):
        doc = Document()
        root = doc.createElement('matrix')
        for key,value in self.items():
            element = value.__xml__().documentElement
            element.setAttribute('key',key)
            root.appendChild(element)
        doc.appendChild(root)
        return doc

    def parse(self,element):
        self._string = None
        assert element.tagName == 'matrix'
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                key = str(node.getAttribute('key'))
                value = KeyedVector(node)
                dict.__setitem__(self,key,value)
            node = node.nextSibling

def scaleMatrix(key,weight):
    """
    @return: a dynamics matrix modifying the given keyed value by scaling it by the given weight
    @rtype: L{KeyedMatrix}
    """
    return KeyedMatrix({key: KeyedVector({key: weight})})
def noChangeMatrix(key):
    """
    @return: a dynamics matrix indicating no change to the given keyed value
    @rtype: L{KeyedMatrix}
    """
    return scaleMatrix(key,1.)
def approachMatrix(key,weight,limit):
    """
    @type weight: float
    @type limit: float
    @return: a dynamics matrix modifying the given keyed value by approaching the given limit by the given weighted percentage of distance
    @rtype: L{KeyedMatrix}
    """
    return KeyedMatrix({key: KeyedVector({key: 1.-weight,CONSTANT: weight*limit})})
def incrementMatrix(key,delta):
    """
    @type delta: float
    @return: a dynamics matrix incrementing the given keyed value by the constant delta
    @rtype: L{KeyedMatrix}
    """
    return KeyedMatrix({key: KeyedVector({key: 1.,CONSTANT: delta})})
def setToConstantMatrix(key,value):
    """
    @type value: float
    @return: a dynamics matrix setting the given keyed value to the constant value
    @rtype: L{KeyedMatrix}
    """
    return KeyedMatrix({key: KeyedVector({CONSTANT: value})})
def setToFeatureMatrix(key,otherKey,pct=1.,shift=0.):
    """
    @type otherKey: str
    @return: a dynamics matrix setting the given keyed value to a percentage of another keyed value plus a constant shift (default is 100% with shift of 0)
    @rtype: L{KeyedMatrix}
    """
    return KeyedMatrix({key: KeyedVector({otherKey: pct,CONSTANT: shift})})
def setTrueMatrix(key):
    return setToConstantMatrix(key,1.)
def setFalseMatrix(key):
    return setToConstantMatrix(key,0.)

class MatrixDistribution(Distribution):
    def update(self,matrix):
        for old in self.domain():
            prob = self[old]
            del self[old]
            if isinstance(matrix,Distribution):
                # Merge distributions
                for submatrix in matrix.domain():
                    new = copy.copy(old)
                    new.update(submatrix)
                    try:
                        self[new] += prob*matrix[submatrix]
                    except KeyError:
                        self[new] = prob*matrix[submatrix]
            else:
                old.update(matrix)
                self[old] = prob

    def __mul__(self,other):
        if isinstance(other,Distribution):
            raise NotImplementedError,'Unable to multiply two distributions.'
        else:
            result = {}
            for element in self.domain():
                try:
                    result[element*other] += self[element]
                except KeyError:
                    result[element*other] = self[element]
            if isinstance(other,KeyedVector):
                return VectorDistribution(result)
            elif isinstance(other,KeyedMatrix):
                return self.__class__(result)
            else:
                raise TypeError,'Unable to process multiplication by %s' % (other.__class__.__name__)

    def element2xml(self,value):
        return value.__xml__().documentElement

    def xml2element(self,key,node):
        return KeyedMatrix(node)
        
class KeyedPlane:
    epsilon = 1e-8

    def __init__(self,vector,threshold=None):
        self._string = None
        if isinstance(vector,Node):
            self.parse(vector)
        else:
            self.vector = vector
            self.threshold = threshold

    def evaluate(self,vector):
        return self.vector*vector+self.epsilon > self.threshold

    def __str__(self):
        if self._string is None:
            self._string = '%s > %f' % (' + '.join(map(lambda (k,v): '%5.3f*%s' % (v,k),self.vector.items())),
                                        self.threshold)
        return self._string

    def __xml__(self):
        doc = self.vector.__xml__()
        doc.documentElement.setAttribute('threshold',str(self.threshold))
        return doc

    def parse(self,element):
        self.threshold = float(element.getAttribute('threshold'))
        self.vector = KeyedVector(element)

def thresholdRow(key,threshold):
    """
    @return: a plane testing whether the given keyed value exceeds the given threshold
    @rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key: 1.}),threshold)
def greaterThanRow(key1,key2):
    """
    @return: a plane testing whether the first keyed value is greater than the second
    @rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key1: 1.,key2: -1.}),0.)
def trueRow(key):
    """
    @return: a plane testing whether a boolean keyed value is True
    @rtype: L{KeyedPlane}
    """
    return thresholdRow(key,0.5)

class KeyedTree:
    def __init__(self,leaf=None):
        self._string = None
        self.leaf = True
        self.children = {}
        self.branch = None
        if isinstance(leaf,Node):
            self.parse(leaf)
        else:
            self.children[None] = leaf
            
    def isLeaf(self):
        return self.leaf

    def makeLeaf(self,leaf):
        self.children = {None: leaf}
        self.leaf = True

    def makeBranch(self,plane,trueTree,falseTree):
        self.children = {True: trueTree,False: falseTree}
        self.branch = plane
        self.leaf = False

    def makeProbabilistic(self,distribution):
        assert isinstance(distribution,Distribution)
        self.children = distribution
        self.branch = None
        self.leaf = False

    def __getitem__(self,index):
        if self.isLeaf():
            return self.children[None]
        elif self.branch is None:
            # Probabilistic branch
            result = {}
            for element in self.children.domain():
                prob = self.children[element]
                subtree = element[index]
                if isinstance(subtree,Distribution):
                    for subelement in subtree.domain():
                        try:
                            result[subelement] += prob*subtree[subelement]
                        except KeyError:
                            result[subelement] = prob*subtree[subelement]
                else:
                    try:
                        result[subtree] += prob
                    except KeyError:
                        result[subtree] = prob
            return Distribution(result)
        else:
            # Deterministic branch
            return self.children[self.branch.evaluate(index)][index]

    def __str__(self):
        if self._string is None:
            if self.isLeaf():
                self._string = str(self.children[None])
            elif self.children.has_key(True):
                # Deterministic branch
                self._string = 'if %s\nThen\t%s\nElse\t%s' % (str(self.branch),str(self.children[True]).replace('\n','\n\t'),
                                                      str(self.children[False]).replace('\n','\n\t'))
            else:
                # Probabilistic branch
                self._string = '\n'.join(map(lambda el: '%d%%: %s' % (100.*self.children[el],str(el)),self.children.domain()))
        return self._string

    def __xml__(self):
        doc = Document()
        root = doc.createElement('tree')
        if not self.isLeaf():
            if self.branch:
                root.appendChild(self.branch.__xml__().documentElement)
        if isinstance(self.children,Distribution):
            root.appendChild(self.children.__xml__().documentElement)
        else:
            for key,value in self.children.items():
                if isinstance(value,bool):
                    node = doc.createElement('bool')
                    node.setAttribute('value',str(value))
                else:
                    node = value.__xml__().documentElement
                node.setAttribute('key',str(key))
                root.appendChild(node)
        doc.appendChild(root)
        return doc

    def parse(self,element):
        assert element.tagName == 'tree'
        node = element.firstChild
        plane = None
        children = {}
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'vector':
                    if node.getAttribute('key'):
                        # Vector leaf
                        key = eval(node.getAttribute('key'))
                        children[key] = KeyedVector(node)
                    else:
                        # Branch
                        plane = KeyedPlane(node)
                elif node.tagName == 'matrix':
                    key = eval(node.getAttribute('key'))
                    children[key] = KeyedMatrix(node)
                elif node.tagName == 'tree':
                    key = eval(node.getAttribute('key'))
                    children[key] = KeyedTree(node)
                elif node.tagName == 'distribution':
                    children = TreeDistribution(node)
                elif node.tagName == 'bool':
                    key = eval(node.getAttribute('key'))
                    children[key] = eval(node.getAttribute('value'))
            node = node.nextSibling
        if plane:
            self.makeBranch(plane,children[True],children[False])
        elif isinstance(children,Distribution):
            self.makeProbabilistic(children)
        else:
            self.makeLeaf(children[None])
        
def maximizeFeature(key):
    return KeyedTree(KeyedVector({key: 1.}))
        
def minimizeFeature(key):
    return KeyedTree(KeyedVector({key: -1.}))

class TreeDistribution(Distribution):
    """
    A class representing a L{Distribution} over L{KeyedTree} instances
    """
    def element2xml(self,value):
        return value.__xml__().documentElement

    def xml2element(self,key,node):
        return KeyedTree(node)

def makeTree(table):
    if isinstance(table,bool):
        # Boolean leaf
        return KeyedTree(table)
    elif table.has_key('if'):
        # Deterministic branch
        tree = KeyedTree()
        tree.makeBranch(table['if'],makeTree(table[True]),makeTree(table[False]))
        return tree
    elif table.has_key('distribution'):
        # Probabilistic branch
        tree = KeyedTree()
        branch = {}
        for subtable,prob in table['distribution']:
            branch[makeTree(subtable)] = prob
        tree.makeProbabilistic(TreeDistribution(branch))
        return tree
    else:
        # Leaf
        return KeyedTree(table)
