import operator
from xml.dom.minidom import Node

from vector import KeyedVector

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
        if not isinstance(other,KeyedPlane):
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
