"""
Class and function definitions for PieceWise Linear (PWL) representations
"""
import copy
from xml.dom.minidom import Document,Node
from probability import Distribution
from action import Action

CONSTANT = ''

class KeyedVector(dict):
    """
    Class for a compact, string-indexable vector
    @cvar epsilon: the margin used for equality of vectors (as well as for testing hyperplanes in L{KeyedPlane})
    @type epsilon: float
    @ivar _string: the C{str} representation of this vector
    @type _string: bool
    """
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

    def desymbolize(self,table):
        result = self.__class__()
        for key,value in self.items():
            if isinstance(value,str):
                try:
                    result[key] = eval(value,table,{})
                except NameError:
                    # Undefined reference: assume it'll get sorted out later
                    result[key] = value
            else:
                result[key] = value
        return result

    def filter(self,ignore):
        """
        @return: a copy of me with the given set of keys dropped out
        @rtype: L{KeyedVector}
        """
        result = self.__class__()
        for key in filter(lambda k: not k in ignore,self.keys()):
            result[key] = self[key]
        return result

    def nearestNeighbor(self,vectors):
        """
        @return: the vector in the given set that is closest to me
        @rtype: L{KeyedVector}
        """
        bestVector = None
        bestValue = None
        for vector in vectors:
            d = self.distance(vector)
            if bestVector is None or d < bestValue:
                bestValue = d
                bestVector = vector
        return bestVector

    def distance(self,vector):
        """
        @return: the distance between the given vector and myself
        @rtype: float
        """
        d = 0.
        for key in self.keys():
            d += pow(self[key]-vector[key],2)
        return d

    def __str__(self):
        if self._string is None:
            self._string = '\n'.join(map(lambda item: '%s: %s' % item,
                                         self.items()))
        return self._string

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__,dict(self))

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
                try:
                    value = float(node.getAttribute('value'))
                except ValueError:
                    value = str(node.getAttribute('value'))
                dict.__setitem__(self,key,value)
            node = node.nextSibling

class VectorDistribution(Distribution):
    """
    A class representing a L{Distribution} over L{KeyedVector} instances
    """

    def join(self,key,value):
        """
        Modifies the distribution over vectors to have the given value for the given key
        @param key: the key to the column to modify
        @type key: str
        @param value: either a single value to apply to all vectors, or else a L{Distribution} over possible values
        """
        for row in self.domain():
            prob = self[row]
            del self[row]
            if isinstance(value,Distribution):
                for element in value.domain():
                    new = row.__class__(row)
                    new[key] = element
                    try:
                        self[new] += prob*value[element]
                    except KeyError:
                        self[new] = prob*value[element]
            else:
                row[key] = value
                self[row] = prob

    def merge(self,other):
        """
        Merge two distributions (the passed-in distribution takes precedence over this one in case of conflict)
        @type other: L{VectorDistribution}
        @return: the merged distribution
        @rtype: L{VectorDistribution}
        """
        result = {}
        for diff in other.domain():
            for old in self.domain():
                new = old.__class__(old)
                new.update(diff)
                result[new] = self[old]*other[diff]
        return self.__class__(result)
        
    def element2xml(self,value):
        return value.__xml__().documentElement

    def xml2element(self,key,node):
        return KeyedVector(node)

    def marginal(self,key):
        result = {}
        for row in self.domain():
            result[row[key]] = self[row]
        return Distribution(result)

    def hasColumn(self,key):
        """
        @return: C{True} iff the given key appears in all of the vectors of this distribution
        @rtype: bool
        """
        for vector in self.domain():
            if not vector.has_key(key):
                return False
        return True

    def __deepcopy__(self,memo):
        result = self.__class__()
        for vector in self.domain():
            try:
                new = memo[id(vector)]
            except KeyError:
                new = KeyedVector(vector)
                memo[id(vector)] = new
            result[new] = self[vector]
        return result

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

    def desymbolize(self,table):
        result = self.__class__()
        for key,row in self.items():
            result[key] = row.desymbolize(table)
        return result

    def scale(self,table):
        result = self.__class__()
        for row,vector in self.items():
            if table.has_key(row):
                result[row] = KeyedVector()
                lo,hi = table[row]
                constant = 0.
                for col,value in vector.items():
                    if col == row:
                        # Same value
                        result[row][col] = value
                        constant += value*lo
                    elif col != CONSTANT:
                        # Scale weight for another feature
                        if abs(value) > vector.epsilon:
                            assert table.has_key(col),'Unable to mix symbolic and numeric values in single vector'
                            colLo,colHi = table[col]
                            result[row][col] = value*(colHi-colLo)*(hi-lo)
                            constant += value*colLo
                result[row][CONSTANT] = constant - lo
                if vector.has_key(CONSTANT):
                    result[row][CONSTANT] += vector[CONSTANT]
                result[row][CONSTANT] /- (hi-lo)
            else:
                result[row] = KeyedVector(vector)
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
    @param weight: the percentage by which you want the feature to approach the limit
    @type weight: float
    @param limit: the value you want the feature to approach
    @type limit: float
    @return: a dynamics matrix modifying the given keyed value by approaching the given limit by the given weighted percentage of distance
    @rtype: L{KeyedMatrix}
    """
    return KeyedMatrix({key: KeyedVector({key: 1.-weight,CONSTANT: weight*limit})})
def incrementMatrix(key,delta):
    """
    @param delta: the constant value to add to the state feature
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
def addFeatureMatrix(key,otherKey,pct=1.):
    """
    @type otherKey: str
    @return: a dynamics matrix adding a percentage of another feature value to the given feature value (default percentage is 100%)
    @rtype: L{KeyedMatrix}
    """
    return KeyedMatrix({key: KeyedVector({key: 1.,otherKey: pct})})
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
    """
    String indexable hyperplane class
    @ivar vector: the weights for the hyperplane
    @type vector: L{KeyedVector}
    @ivar threshold: the threshold for the hyperplane
    @type threshold: float
    @ivar comparison: if 1, value must be above hyperplane; if -1, below; if 0, equal (default is 1)
    @type comparison: int
    """

    def __init__(self,vector,threshold=None,comparison=1):
        self._string = None
        if isinstance(vector,Node):
            self.parse(vector)
        else:
            self.vector = vector
            self.threshold = threshold
            self.comparison = comparison

    def evaluate(self,vector):
        total = self.vector * vector
        if self.comparison > 0:
            return total+self.vector.epsilon > self.threshold
        elif self.comparison < 0:
            return total-self.vector.epsilon < self.threshold
        else:
            return abs(total-self.threshold) < self.vector.epsilon

    def desymbolize(self,table):
        if isinstance(self.threshold,str):
            try:
                threshold = eval(self.threshold,table,{})
            except NameError:
                # Undefined reference: assume it'll get sorted out later
                threshold = self.threshold
        else:
            threshold = self.threshold
        return self.__class__(self.vector.desymbolize(table),threshold,self.comparison)

    def scale(self,table):
        vector = self.vector.__class__(self.vector)
        threshold = self.threshold
        symbolic = False
        span = None
        assert not vector.has_key(CONSTANT),'Unable to scale hyperplanes with constant factors. Move constant factor into threshold.'
        for key in vector.keys():
            if table.has_key(key):
                assert not symbolic,'Unable to scale hyperplanes with both numeric and symbolic variables'
                if span is None:
                    span = table[key]
                    threshold /= float(span[1]-span[0])
                else:
                    assert table[key] == span,'Unable to scale hyperplanes when the variables have different ranges (%s != %s)' % (span,table[key])
                threshold -= vector[key]*span[0]/(span[1]-span[0])
            else:
                assert span is None,'Unable to scale hyperplanes with both numeric and symbolic variables'
                symbolic = True
        return self.__class__(vector,threshold)
            
    def __str__(self):
        if self._string is None:
            operator = ['==','>','<'][self.comparison]
            self._string = '%s %s %f' % (' + '.join(map(lambda (k,v): '%5.3f*%s' % (v,k),self.vector.items())),
                                        operator,self.threshold)
        return self._string

    def __xml__(self):
        doc = self.vector.__xml__()
        doc.documentElement.setAttribute('threshold',str(self.threshold))
        doc.documentElement.setAttribute('comparison',str(self.comparison))
        return doc

    def parse(self,element):
        try:
            self.threshold = float(element.getAttribute('threshold'))
        except ValueError:
            self.threshold = str(element.getAttribute('threshold'))
        self.comparison = int(element.getAttribute('comparison'))
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
def equalRow(key,value):
    """
    @return: a plane testing whether the given keyed value equals the given target value
    @rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key: 1.}),value,0)

class KeyedTree:
    """
    Decision tree node using symbolic PWL structures
    @ivar leaf: C{True} iff this node is a leaf
    @type leaf: bool
    @ivar children: table of children of this node
    @type children: dict
    @ivar branch: the hyperplane branch at this node (if applicable)
    @type branch: L{KeyedPlane}
    """
    def __init__(self,leaf=None):
        self._string = None
        if isinstance(leaf,Node):
            self.parse(leaf)
        else:
            self.makeLeaf(leaf)
            
    def isLeaf(self):
        return self.leaf

    def makeLeaf(self,leaf):
        self.children = {None: leaf}
        self.leaf = True
        self.branch = None

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

    def desymbolize(self,table):
        """
        @return: a new tree with any symbolic references replaced with numeric values according to the table of element lists
        @rtype: L{KeyedTree}
        """
        tree = self.__class__()
        if self.isLeaf():
            leaf = self.children[None]
            if isinstance(leaf,KeyedVector) or isinstance(leaf,KeyedMatrix):
                tree.makeLeaf(leaf.desymbolize(table))
            else:
                tree.makeLeaf(leaf)
        elif self.branch:
            tree.makeBranch(self.branch.desymbolize(table),self.children[True].desymbolize(table),
                            self.children[False].desymbolize(table))
        else:
            new = {}
            for child in self.children.domain():
                new[child.desymbolize(table)] = self.children[child]
            tree.makeProbabilistic(TreeDistribution(new))
        return tree

    def scale(self,table):
        tree = self.__class__()
        if self.isLeaf():
            tree.makeLeaf(self.children[None].scale(table))
        elif self.branch:
            tree.makeBranch(self.branch.scale(table),self.children[True].scale(table),
                            self.children[False].scale(table))
        else:
            new = {}
            for child in self.children.domain():
                new[child.scale(table)] = self.children[child]
            tree.makeProbabilistic(TreeDistribution(new))
        return tree

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
                elif isinstance(value,str):
                    node = doc.createElement('str')
                    node.appendChild(doc.createTextNode(value))
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
                elif node.tagName == 'action': 
                    key = eval(node.getAttribute('key'))
                    children[key] = Action(node)
                elif node.tagName == 'str':
                    key = eval(node.getAttribute('key'))
                    children[key] = str(node.firstChild.data).strip()
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
    elif isinstance(table,str):
        # String leaf
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
