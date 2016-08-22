"""
Class and function definitions for PieceWise Linear (PWL) representations
"""
import copy
import operator
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
            # Scaling
            result = KeyedVector()
            for key,value in self.items():
                result[key] = value*other
            return result
        elif isinstance(other,KeyedMatrix):
            # Transform vector
            result = KeyedVector()
            for key in self.keys():
                if other.has_key(key):
                    for col in other[key].keys():
                        try:
                            result[col] += self[key]*other[key][col]
                        except KeyError:
                            result[col] = self[key]*other[key][col]
            return result
        else:
            raise TypeError,'Unable to multiply %s by %s' % \
                (self.__class__.__name__,other.__class__.__name__)

    def __setitem__(self,key,value):
        self._string = None
        dict.__setitem__(self,key,value)

    def __delitem__(self,key):
        self._string = None
        dict.__delitem__(self,key)

    def desymbolize(self,table,debug=False):
        result = self.__class__()
        for key,value in self.items():
            if isinstance(value,str):
                try:
                    result[key] = eval(value,globals(),table)
                except NameError:
                    # Undefined reference: assume it'll get sorted out later
                    result[key] = value
            else:
                result[key] = value
        return result

    def filter(self,ignore):
        """
        @return: a copy of me applying the given lambda expression to the keys (if a list is provided, then any keys in that list are dropped out)
        @rtype: L{KeyedVector}
        """
        if isinstance(ignore,list):
            test = lambda k: not k in ignore
        else:
            test = ignore
        result = self.__class__()
        for key in filter(test,self.keys()):
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
            keys = self.keys()
            keys.sort()
            self._string = '\n'.join(map(lambda k: '%s: %s' % (k,self[k]),keys))
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
        original = dict(self)
        domain = self.domain()
        self.clear()
        for row in domain:
            prob = original[str(row)]
            if isinstance(value,Distribution):
                for element in value.domain():
                    new = row.__class__(row)
                    new[key] = element
                    self.addProb(new,prob*value[element])
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
            try:
                result[row[key]] += self[row]
            except KeyError:
                result[row[key]] = self[row]
        return Distribution(result)

    def select(self,incremental=False):
        """
        @param incremental: if C{True}, then select each key value in series (rather than picking out a joint vector all at once, default is C{False})
        """
        if incremental:
            # Sample each key and keep track how likely each individual choice was
            sample = KeyedVector()
            keys = self.domain()[0].keys()
            index = 0
            while len(self) > 1:
                key = keys[index]
                dist = self.marginal(key)
                if len(dist) > 1:
                    # Have to make a choice here
                    element,sample[key] = dist.sample(True)
                    # Figure out where the "spinner" ended up across entire pie chart
                    for other in dist.domain():
                        if other == element:
                            break
                        else:
                            sample[key] += dist[other]
                    for vector in self.domain():
                        if vector[key] != element:
                            del self[vector]
                    self.normalize()
                index += 1
            return sample
        else:
            Distribution.select(self)
            
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
        self._keysIn = None
        self._keysOut = None
        if isinstance(arg,Node):
            dict.__init__(self)
            self.parse(arg)
        else:
            dict.__init__(self,arg)
            self._string = None
        
    def __eq__(self,other):
        return str(self) == str(other)
         # for key,vector in self.items():
         #     try:
         #         if vector != other[key]:
         #             return False
         #     except KeyError:
         #         if vector != {}:
         #             return False
         # else:
         #     return True

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
                    if other.has_key(c1):
                        for c2,value2 in other[c1].items():
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
        elif isinstance(other,VectorDistribution):
            result = VectorDistribution()
            for vector in other.domain():
                product = self*vector
                try:
                    result[product] += other[vector]
                except KeyError:
                    result[product] = other[vector]
        else:
            raise TypeError,'Unable to multiply %s by %s' % \
                (self.__class__.__name__,other.__class__.__name__)
        return result

    def getKeysIn(self):
        """
        @return: a set of keys which affect the result of multiplying by this matrix
        """
        if self._keysIn is None:
            self._keysIn = set()
            self._keysOut = set()
            for col,row in self.items():
                self._keysIn |= set(row.keys())
                self._keysOut.add(col)
        return self._keysIn

    def getKeysOut(self):
        """
        @return: a set of keys which are changed as a result of multiplying by this matrix
        """
        if self._keysOut is None:
            self.getKeysIn()
        return self._keysOut

    # def getKeys(self):
    #     result = set()
    #     for row in self.values():
    #         result |= set(row.keys())
    #     return result

    def desymbolize(self,table,debug=False):
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
        original = dict(self)
        domain = self.domain()
        self.clear()
        for old in domain:
            prob = original[old]
            if isinstance(matrix,Distribution):
                # Merge distributions
                for submatrix in matrix.domain():
                    new = copy.copy(old)
                    new.update(submatrix)
                    self.addProb(new,prob*matrix[submatrix])
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
        elif self.comparison == 0:
            if isinstance(self.threshold,list):
                return reduce(operator.or_,[abs(total-t) < self.vector.epsilon for t in self.threshold])
            else:
                return abs(total-self.threshold) < self.vector.epsilon
        else:
            raise ValueError,'Unknown comparison for %s: %s' % (self.__class__.__name__,self.comparison)

    def desymbolize(self,table,debug=False):
        threshold = self.desymbolizeThreshold(self.threshold,table)
        return self.__class__(self.vector.desymbolize(table),threshold,self.comparison)

    def desymbolizeThreshold(self,threshold,table):
        if isinstance(threshold,str):
            try:
                return eval(threshold,globals(),table)
            except NameError:
                # Undefined reference: assume it'll get sorted out later
                return threshold
        elif isinstance(threshold,list):
            return [self.desymbolizeThreshold(t,table) for t in threshold]
        else:
            return threshold

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

    def __eq__(self,other):
        if not isinstance(other,KeyedVector):
            return False
        elif self.vector == other.vector and \
                self.threshold == other.threshold and \
                self.comparison == other.comparison:
            return True
        else:
            return False

    def compare(self,other,value):
        """
        Identifies any potential conflicts between two hyperplanes
        @return: C{None} if no conflict was detected, C{True} if the tests are redundant, C{False} if the tests are conflicting
        @warning: correct, but not complete
        """
        if self.vector == other.vector:
            if self.comparison == 0:
                if other.comparison == 0:
                    # Both are equality tests
                    if abs(self.threshold - other.threshold) < self.vector.epsilon:
                        # Values are the same, so test results must be the same
                        return value
                    elif value:
                        # Values are different, but we are equal to the other value
                        return False
                    else:
                        # Values are different, but not equal to other, so no information
                        return None
                elif cmp(self.threshold,other.threshold) == other.comparison:
                    # Our value satisfies other's inequality
                    if value:
                        # So no information in this case
                        return None
                    else:
                        # But we know we are invalid in this one
                        return False
                else:
                    # Our value does not satisfy other's inequality
                    if value:
                        # We know we are invalid
                        return False
                    else:
                        # And no information
                        return None
            elif other.comparison == 0:
                # Other specifies equality, we are inequality
                if value:
                    # Determine whether equality condition satisfies our inequality
                    return cmp(other.threshold,self.threshold) == self.comparison
                else:
                    # No information about inequality
                    return None
            else:
                # Both inequalities, we should do something here
                return None
        return None

    def minimize(self):
        """
        @return: an equivalent plane with no constant element in the weights
        """
        weights = self.vector.__class__(self.vector)
        if self.vector.has_key(CONSTANT):
            threshold = self.threshold - self.vector[CONSTANT]
            del weights[CONSTANT]
        else:
            threshold = self.threshold
        return self.__class__(weights,threshold,self.comparison)

    def __str__(self):
        if self._string is None:
            operator = ['==','>','<'][self.comparison]
            self._string = '%s %s %s' % (' + '.join(map(lambda (k,v): '%5.3f*%s' % (v,k),self.vector.items())),
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
            self.threshold = eval(str(element.getAttribute('threshold')))
        try:
            self.comparison = int(element.getAttribute('comparison'))
        except ValueError:
            self.comparison = str(element.getAttribute('comparison'))
        self.vector = KeyedVector(element)

def thresholdRow(key,threshold):
    """
    @return: a plane testing whether the given keyed value exceeds the given threshold
    @rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key: 1.}),threshold)
def differenceRow(key1,key2,threshold):
    """
    @return: a plane testing whether the difference between the first and second keyed values exceeds the given threshold
    @rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key1: 1.,key2: -1.}),threshold)
def greaterThanRow(key1,key2):
    """
    @return: a plane testing whether the first keyed value is greater than the second
    @rtype: L{KeyedPlane}
    """
    return differenceRow(key1,key2,0.)
def trueRow(key):
    """
    @return: a plane testing whether a boolean keyed value is True
    @rtype: L{KeyedPlane}
    """
    return thresholdRow(key,0.5)
def andRow(trueKeys=[],falseKeys=[]):
    """
    @param trueKeys: list of keys which must be C{True} (default is empty list)
    @type trueKeys: str[]
    @param falseKeys: list of keys which must be C{False} (default is empty list)
    @type falseKeys: str[]
    @return: a plane testing whether all boolean keyed values are set as desired
    @rtype: L{KeyedPlane}
    """
    weights = {}
    for key in trueKeys:
        weights[key] = 1.
    for key in falseKeys:
        weights[key] = -1.
    return KeyedPlane(KeyedVector(weights),float(len(trueKeys))-0.5)
def equalRow(key,value):
    """
    @return: a plane testing whether the given keyed value equals the given target value
    @rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key: 1.}),value,0)
def equalFeatureRow(key1,key2):
    """
    @return: a plane testing whether the values of the two given features are equal
    @rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key1: 1.,key2: -1.}),0,0)

class KeyedBranch:
    """
    Disjuction/conjunction of individual planes
    """
    pass

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
        self._keysIn = None
        self._keysOut = None
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

    def isProbabilistic(self):
        """
        @return: C{True} if there is a probabilistic branch at this node
        @rtype: bool
        """
        return self.branch is None and not self.isLeaf()

    def getKeysIn(self):
        """
        @return: a set of all keys that affect the output of this PWL function
        """
        if self._keysIn is None:
            self._keysIn = set()
            self._keysOut = set()
            if self.isProbabilistic():
                # Keys are taken from each child
                children = self.children.domain()
            else:
                children = self.children.values()
                if not self.isLeaf():
                    # Keys also include those in the branch
                    self._keysIn |= set(self.branch.vector.keys())
            # Accumulate keys across children
            for child in children:
                if isinstance(child,KeyedVector):
                    self._keysIn |= set(child.keys())
                elif not child is None and not isinstance(child,bool):
                    self._keysIn |= child.getKeysIn()
                    self._keysOut |= child.getKeysOut()
        return self._keysIn

    def getKeysOut(self):
        """
        @return: a set of all keys that are affected by this PWL function
        """
        if self._keysOut is None:
            self.getKeysIn()
        return self._keysOut

    # def getKeys(self):
    #     """
    #     @return: a set of all keys references in this PWL function
    #     """
    #     if self.isProbabilistic():
    #         # Keys are taken from each child
    #         result = set()
    #         children = self.children.domain()
    #     else:
    #         children = self.children.values()
    #         if self.isLeaf():
    #             result = set()
    #         else:
    #             # Keys also include those in the branch
    #             result = set(self.branch.vector.keys())
    #     # Accumulate keys across children
    #     for child in children:
    #         if isinstance(child,KeyedVector):
    #             result |= set(child.keys())
    #         elif not child is None and not isinstance(child,bool):
    #             result |= child.getKeys()
    #     return result

    def collapseProbabilistic(self):
        """
        Utility method that combines any consecutive probabilistic branches at this node into a single distribution
        """
        if self.isProbabilistic():
            collapse = False
            distribution = Distribution(self.children)
            for child in self.children.domain():
                if child.isProbabilistic():
                    # Probabilistic branch to merge
                    collapse = True
                    child.collapseProbabilistic()
                    del distribution[child]
                    for grandchild in child.children.domain():
                        try:
                            distribution[grandchild] += self.children[child]*child.children[grandchild]
                        except KeyError:
                            distribution[grandchild] = self.children[child]*child.children[grandchild]
            if collapse:
                assert sum(distribution.values()) == 1.
                self.makeProbabilistic(distribution)
            
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

    def desymbolize(self,table,debug=False):
        """
        @return: a new tree with any symbolic references replaced with numeric values according to the table of element lists
        @rtype: L{KeyedTree}
        """
        tree = self.__class__()
        if self.isLeaf():
            leaf = self.children[None]
            if isinstance(leaf,KeyedVector) or isinstance(leaf,KeyedMatrix):
                tree.makeLeaf(leaf.desymbolize(table,debug))
            else:
                tree.makeLeaf(leaf)
        elif self.branch:
            tree.makeBranch(self.branch.desymbolize(table),self.children[True].desymbolize(table),
                            self.children[False].desymbolize(table))
        else:
            new = TreeDistribution()
            for child in self.children.domain():
                new.addProb(child.desymbolize(table),self.children[child])
            tree.makeProbabilistic(new)
        return tree

    def floor(self,key,lo):
        """
        Modify this tree to make sure the new computed value never goes lower than the given floor
        @warning: may introduce redundant checks
        """
        if self.isLeaf():
            tMatrix = self.children[None]
            assert len(tMatrix) == 1,'Unable to handle dynamics of more than one feature'
            assert tMatrix.has_key(key),'Are you sure you should be flooring me on a key I don\'t have?'
            del self.children[None]
            fMatrix = setToConstantMatrix(key,lo)
            branch = KeyedPlane(KeyedVector(tMatrix[key]),lo)
            self.makeBranch(branch,KeyedTree(tMatrix),KeyedTree(fMatrix))
        elif self.branch:
            self.children[True].floor(key,lo)
            self.children[False].floor(key,lo)
        else:
            for child in self.children.domain():
                prob = self.children[child]
                del self.children[child]
                self[child.floor(key,lo)] = prob
        return self

    def ceil(self,key,hi):
        """
        Modify this tree to make sure the new computed value never goes higher than the given ceiling
        @warning: may introduce redundant checks
        """
        if self.isLeaf():
            fMatrix = self.children[None]
            assert len(fMatrix) == 1,'Unable to handle dynamics of more than one feature'
            assert fMatrix.has_key(key),'Are you sure you should be ceiling me on a key I don\'t have?'
            del self.children[None]
            tMatrix = setToConstantMatrix(key,hi)
            branch = KeyedPlane(KeyedVector(fMatrix[key]),hi)
            self.makeBranch(branch,KeyedTree(tMatrix),KeyedTree(fMatrix))
        elif self.branch:
            self.children[True].ceil(key,hi)
            self.children[False].ceil(key,hi)
        else:
            for child in self.children.domain():
                prob = self.children[child]
                del self.children[child]
                self[child.ceil(key,hi)] = prob
        return self

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

    def __eq__(self,other):
        if self.isLeaf():
            if other.isLeaf():
                return self.children[None] == other.children[None]
            else:
                return False
        elif isinstance(self.children,Distribution):
            if isinstance(other.children,Distribution):
                return self.children == other.children
            else:
                return false
        else:
            if self.branch == other.branch:
                return self.children == other.children
            else:
                return False
            
    def __add__(self,other):
        if isinstance(other,KeyedTree):
            return self.compose(other,lambda x,y: x+y)
        else:
            return self+KeyedTree(other)
            
    def __mul__(self,other):
        if isinstance(other,KeyedTree):
            return self.compose(other,lambda x,y: x*y,lambda x,y: x*y)
        else:
            return self*KeyedTree(other)

    def max(self,other):
        return self.compose(other,self.__max)

    def __max(self,leaf1,leaf2):
        """
        Helper method for computing max
        @return: a tree returing the maximum of the two vectors
        @rtype: L{KeyedTree}
        """
        result = self.__class__()
        if leaf1 is False:
            result.graft(leaf2)
        elif leaf2 is False:
            result.graft(leaf1)
        else:
            if isinstance(leaf1,dict):
                weights = leaf1['vector'] - leaf2['vector']
            else:
                # Assume vectors
                weights = leaf1 - leaf2
            result.makeBranch(KeyedPlane(weights,0.),KeyedTree(leaf1),KeyedTree(leaf2))
        return result

    def compose(self,other,leafOp=None,planeOp=None):
        """
        Compose two trees into a single tree
        @param other: the other tree to be composed with
        @type other: L{KeyedTree}
        @param leafOp: the binary operator to apply to leaves of each tree to generate a new leaf
        @param planeOp: the binary operator to apply to the plane
        @rtype: L{KeyedTree}
        """
        result = KeyedTree()
        if other.isLeaf():
            if self.isLeaf():
                result.graft(leafOp(self.children[None],other.children[None]))
            elif self.branch is None:
                # Probabilistic branch
                distribution = self.children.__class__()
                for old in self.children.domain():
                    new = old.compose(other,leafOp,planeOp)
                    if isinstance(new,Distribution):
                        for tree in new.domain():
                            distribution.addProb(tree,self.children[old]*new[tree])
                    else:
                        distribution.addProb(new,self.children[old])
                if len(distribution) > 1:
                    result.makeProbabilistic(distribution)
                    result.collapseProbabilistic()
                else:
                    result.graft(new)
            else:
                # Deterministic branch
                trueTree = self.children[True].compose(other,leafOp,planeOp)
                falseTree = self.children[False].compose(other,leafOp,planeOp)
                if trueTree == falseTree:
                    result.graft(trueTree)
                else:
                    if planeOp is None or not isinstance(other.children[None],KeyedMatrix):
                        plane = self.branch
                    else:
                        plane = KeyedPlane(planeOp(self.branch.vector,other.children[None]),
                                           self.branch.threshold,self.branch.comparison)
                    result.makeBranch(plane,trueTree,falseTree)
        elif other.branch is None:
            # Probabilistic branch
            distribution = other.children.__class__()
            for old in other.children.domain():
                new = self.compose(old,leafOp,planeOp)
                if isinstance(new,Distribution):
                    for tree in new.domain():
                        distribution.addProb(tree,other.children[old]*new[tree])
                else:
                    distribution.addProb(new,other.children[old])
            if len(distribution) > 1:
                result.makeProbabilistic(distribution)
                result.collapseProbabilistic()
            else:
                result.graft(new)
        else:
            # Deterministic branch
            trueTree = self.compose(other.children[True],leafOp,planeOp)
            falseTree = self.compose(other.children[False],leafOp,planeOp)
            if trueTree == falseTree:
                result.graft(trueTree)
            else:
                result.makeBranch(other.branch,trueTree,falseTree)
        return result
            
    def replace(self,old,new):
        """
        @return: a new tree with the given substitution applied to all leaf nodes
        """
        return self.map(lambda leaf: new if leaf == old else leaf)

    def expectation(self):
        """
        @return: a new tree representing an expectation over any probabilistic branches
        """
        return self.map(distOp=lambda branch: branch.expectation())

    def map(self,leafOp=None,planeOp=None,distOp= None):
        """
        Generates a new tree applying a function to all planes and leaves
        @param leafOp: functional transformation of leaf nodes
        @type leafOp: lambda XS{->}X
        @param planeOp: functional transformation of hyperplanes
        @type planeOp: lambda XS{->}X
        @param distOp: functional transformation of probabilistic branches
        @type distOp: lambda L{TreeDistribution}S{->}X
        @rtype: L{KeyedTree}
        """
        result = self.__class__()
        if self.isLeaf():
            if leafOp:
                leaf = leafOp(self.children[None])
            else:
                leaf = self.children[None]
            result.graft(leaf)
        elif self.isProbabilistic():
            if distOp:
                result.graft(distOp(self.children))
            else:
                distribution = self.children.__class__()
                for old in self.children.domain():
                    new = old.map(leafOp,planeOp,distOp)
                    try:
                        distribution[new] += self.children[old]
                    except KeyError:
                        distribution[new] = self.children[old]
                result.makeProbabilistic(distribution)
        else:
            # Deterministic branch
            if planeOp:
                branch = planeOp(self.branch)
            else:
                branch = self.branch
            result.makeBranch(branch,self.children[True].map(leafOp,planeOp,distOp),
                              self.children[False].map(leafOp,planeOp,distOp))
        return result

    def graft(self,root):
        """
        Grafts a tree at the current node
        @warning: clobbers anything currently at (or rooted at) this node
        """
        if isinstance(root,TreeDistribution):
            self.makeProbabilistic(root)
        elif isinstance(root,KeyedTree):
            if root.isLeaf():
                self.makeLeaf(root.children[None])
            elif root.isProbabilistic():
                self.makeProbabilistic(root.children)
            else:
                self.makeBranch(root.branch,root.children[True],root.children[False])
        else:
            # Leaf node (not a very smart use of graft, but who are we to judge)
            self.makeLeaf(root)

    def prune(self,path=[]):
        """
        Removes redundant branches
        @warning: correct, but not necessarily complete
        """
        result = self.__class__()
        if self.isLeaf():
            # Leaves are unchanged
            result.makeLeaf(self.children[None])
        elif self.isProbabilistic():
            # Distributions are passed through
            distribution = self.children.__class__() 
            for tree in self.children.domain():
                prob = self.children[tree]
                tree.prune(path)
                try:
                    distribution[tree] += prob
                except KeyError:
                    distribution[tree] = prob
            if len(distribution) == 1:
                result.graft(tree)
            else:
                result.makeProbabilistic(distribution)
        else:
            # Deterministic branch
            for branch,value in path:
                conflict = self.branch.compare(branch,value)
                if not conflict is None:
                    result.graft(self.children[conflict].prune(path))
                    break
            else:
                # No matches
                result.makeBranch(self.branch,self.children[True].prune(path+[(self.branch,True)]),
                                  self.children[False].prune(path+[(self.branch,False)]))
        return result

    def minimizePlanes(self):
        """
        Modifies tree in place so that there are no constant factors in branch weights
        """
        if self.isProbabilistic():
            for child in self.children.domain():
                child.minimizePlanes()
        elif not self.isLeaf():
            self.branch = self.branch.minimize()
            self.children[True].minimizePlanes()
            self.children[False].minimizePlanes()
            
    def __hash__(self):
        return hash(str(self))

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
                elif value is None:
                    node = doc.createElement('none')
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
                elif node.tagName == 'none':
                    key = eval(node.getAttribute('key'))
                    children[key] = None
            node = node.nextSibling
        if plane:
            self.makeBranch(plane,children[True],children[False])
        elif isinstance(children,Distribution):
            self.makeProbabilistic(children)
        else:
            self.makeLeaf(children[None])

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
    elif table is None:
        # Null leaf
        return KeyedTree(table)
    elif isinstance(table,str):
        # String leaf
        return KeyedTree(table)
    elif isinstance(table,frozenset):
        # Set leaf (e.g., ActionSet for a policy)
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
