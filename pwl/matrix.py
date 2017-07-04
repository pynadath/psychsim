import copy
from xml.dom.minidom import Document,Node

from psychsim.probability import Distribution

from vector import *
from . import CONSTANT

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
            return NotImplemented
        return result

    def __rmul__(self,other):
        if isinstance(other,KeyedVector):
            # Transform vector
            result = KeyedVector()
            for key in other.keys():
                if self.has_key(key):
                    for col in self[key].keys():
                        try:
                            result[col] += other[key]*self[key][col]
                        except KeyError:
                            result[col] = other[key]*self[key][col]
        else:
            return NotImplemented
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
                for col,value in items():
                    if col == row:
                        # Same value
                        result[row][col] = value
                        constant += value*lo
                    elif col != CONSTANT:
                        # Scale weight for another feature
                        if abs(value) > epsilon:
                            assert table.has_key(col),'Unable to mix symbolic and numeric values in single vector'
                            colLo,colHi = table[col]
                            result[row][col] = value*(colHi-colLo)*(hi-lo)
                            constant += value*colLo
                result[row][CONSTANT] = constant - lo
                if has_key(CONSTANT):
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
