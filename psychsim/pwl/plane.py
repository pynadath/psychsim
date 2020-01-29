import operator
from xml.dom.minidom import Node,Document

from psychsim.pwl.keys import CONSTANT
from psychsim.pwl.vector import KeyedVector
from psychsim.probability import Distribution
from psychsim.action import ActionSet

class KeyedPlane:
    """
    String indexable hyperplane class
    :ivar vector: the weights for the hyperplane
    :type vector: L{KeyedVector}
    :ivar threshold: the threshold for the hyperplane
    :type threshold: float
    :ivar comparison: if 1, value must be above hyperplane; if -1, below; if 0, equal (default is 1)
    :type comparison: int
    """
    DEFAULT_THRESHOLD = 0.
    DEFAULT_COMPARISON = 1
    COMPARISON_MAP = ['==','>','<']

    def __init__(self,planes,threshold=None,comparison=None):
        """
        :warning: if S{planes} is a list, then S{threshold} and S{comparison} are ignored
        """
        if isinstance(planes,Node):
            self.parse(planes)
        elif isinstance(planes,KeyedVector):
            # Only a single branch passed
            if threshold is None:
                threshold = self.DEFAULT_THRESHOLD
            if comparison is None:
                comparison = self.DEFAULT_COMPARISON
            self.planes = [(planes,threshold,comparison)]
        else:
            self.planes = []
            for plane in planes:
                if len(plane) == 3:
                    self.planes.append(plane)
                elif len(plane) == 2:
                    self.planes.append((plane[0],plane[1],self.DEFAULT_COMPARISON))
                elif len(plane) == 1:
                    self.planes.append((plane[0],self.DEFAULT_THRESHOLD,self.DEFAULT_COMPARISON))
                else:
                    raise ValueError('Empty plane passed into constructor')
        self._string = None
        self._keys = None
        self.isConjunction = True

    def __add__(self,other):
        """
        :warning: Does not check for duplicate planes
        """
        assert self.isConjunction == other.isConjunction,'Planes must be both disjunctive or both conjunctive to be combined'
        result = self.__class__(self.planes+other.planes)
        result.isConjunction = self.isConjunction
        return result
    
    def keys(self):
        if self._keys is None:
            self._keys = set()
            for vector,threshold,comparison in self.planes:
                self._keys |= set(vector.keys())
        return self._keys
    
    def possible(self,variables):
        for plane,threshold,comparison in self.planes:
            lo = 0.
            hi = 0.
            for key in plane.keys():
                if key not in variables:
                    # Ambiguous
                    return None
                elif variables[key]['domain'] is set or variables[key]['domain'] is list:
                    # Symbolic
                    return None
                if plane[key] > 0.:
                    lo += plane[key]*variables[key]['lo']
                    hi += plane[key]*variables[key]['hi']
                else:
                    lo -= plane[key]*variables[key]['hi']
                    hi -= plane[key]*variables[key]['lo']
            values = []
            if self.COMPARISON_MAP[comparison] == '>':
                print(plane)
                print(lo,hi)
                print(threshold)
                if isinstance(threshold,list):
                    for i in range(len(threshold)):
                        if hi <= threshold[i]:
                            break
                        elif i > 0 and lo < threshold[i]:
                            values.append(i-1)
                elif lo > threshold:
                    print('Always true')
                    return [True]
                elif hi <= threshold:
                    print('Always false')
                    return [False]
                else:
                    print('Who knows?')
                    return [True,False]
            else:
                raise NotImplementedError('Not yet handling comparisons other than >, but it is really easy to do')

    def evaluate(self,vector):
        """
        Tests whether the given vector passes or fails this test.
        Also accepts a numeric value, in lieu of doing a dot product.
        :rtype: bool
        :warning: If multiple planes are present, an AND over their results is assumed
        """
        result = None
        for plane,threshold,comparison in self.planes:
            if isinstance(vector,float):
                total = vector
            else:
                total = plane * vector
            if isinstance(total,Distribution):
                assert len(total) == 1,'Unable to handle uncertain test results'
                total = total.first()
            if comparison > 0:
                value = total+plane.epsilon
                if isinstance(threshold,list):
                    for index in range(len(threshold)):
                        if value <= threshold[index]:
                            return index
                    else:
                        return len(threshold)
                elif value > threshold:
                    if not self.isConjunction:
                        # Disjunction, so any positive result is sufficient
                        return True
                elif self.isConjunction:
                    # Conjunction, so any negative result is sufficient
                    return False
            elif comparison < 0:
                value = total-plane.epsilon
                if isinstance(threshold,list):
                    for index in range(len(threshold)):
                        if value < threshold[index]:
                            return index
                    else:
                        return len(threshold)
                elif value  < threshold:
                    if not self.isConjunction:
                        # Disjunction, so any positive result is sufficient
                        return True
                elif self.isConjunction:
                    # Conjunction, so any negative result is sufficient
                    return False
            elif comparison == 0:
                if isinstance(threshold,list):
                    for index in range(len(threshold)):
                        if abs(total-threshold[index]) < plane.epsilon:
                            # Disjunction, so any positive result is sufficient
                            return index
                    else:
                        return None
                elif isinstance(threshold,set):
                    for t in threshold:
                        if abs(total-t) < plane.epsilon:
                            # Disjunction, so any positive result is sufficient
                            return True
                    else:
                        if self.isConjunction:
                            # Conjunction, so any negative result is sufficient
                            return False
                else:
                    if abs(total-threshold) < plane.epsilon:
                        if not self.isConjunction:
                            # Disjunction, so any positive result is sufficient
                            return True
                    elif self.isConjunction:
                        # Conjunction, so any negative result is sufficient
                        return False
            else:
                # Return raw value, to be used in unspeakable ways
                raise ValueError('Invalid comparison %s' % (comparison))
        else:
            # No planes matched
            if self.isConjunction:
                return True
            else:
                return False

    def desymbolize(self,table,debug=False):
        planes = [(p[0].desymbolize(table),self.desymbolizeThreshold(p[1],table),p[2])
                  for p in self.planes]
        return self.__class__(planes)

    def desymbolizeThreshold(self,threshold,table):
        if isinstance(threshold,str):
            try:
                return eval(threshold,globals(),table)
            except NameError:
                # Undefined reference: assume it'll get sorted out later
                return threshold
        elif isinstance(threshold,list):
            return [self.desymbolizeThreshold(t,table) for t in threshold]
        elif isinstance(threshold,set):
            return {self.desymbolizeThreshold(t,table) for t in threshold}
        elif isinstance(threshold,ActionSet):
            return table[threshold]
        else:
            return threshold

    def makeFuture(self,keyList=None):
        """
        Transforms this plane to refer to only future versions of its columns
        :param keyList: If present, only references to these keys are made future
        """
        self.changeTense(True,keyList)

    def makePresent(self,keyList=None):
        """
        Transforms this plane to refer to only current versions of its columns
        :param keyList: If present, only references to these keys are made present
        """
        self.changeTense(False,keyList)

    def changeTense(self,future=True,keyList=None):
        if keyList is None:
            keyList = self.keys()
        planes = []
        for plane,threshold,comparison in self.planes:
            plane.changeTense(future,keyList)
        self._keys = None
        self._string = None
#        return self.__class__(planes)

    def scale(self,table):
        vector = self.vector.__class__(self.vector)
        threshold = self.threshold
        symbolic = False
        span = None
        assert CONSTANT not in vector,'Unable to scale hyperplanes with constant factors. Move constant factor into threshold.'
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
        if len(self.planes) != len(other.planes):
            return False
        for plane in other.planes:
            if plane not in self.planes:
                return False
        else:
            return True

    def compare(self,other,value):
        """
        Identifies any potential conflicts between two hyperplanes
        :return: C{None} if no conflict was detected, C{True} if the tests are redundant, C{False} if the tests are conflicting
        :warning: correct, but not complete
        """
        assert len(self.planes) == 1,'Unable to compare branches with multiple tests'
        assert len(other.planes) == 1,'Unable to compare branches with multiple tests'
        myVec,myThresh,myComp = self.planes[0]
        yrVec,yrThresh,yrComp = other.planes[0]
        if myVec == yrVec:
            if myComp == 0:
                if yrComp == 0:
                    # Both are equality tests
                    if isinstance(myThresh,set):
                        if isinstance(yrThresh,set):
                            if myThresh == yrThresh and value is True:
                                return True
                            # TODO: There are more cases here
                            return None
                        elif isinstance(yrThresh,list):
                            raise NotImplementedError
                        else:
                            if yrThresh in myThresh:
                                # This equality test is one of my acceptable values
                                if value is True:
                                    return True
                            return None
                    elif isinstance(yrThresh,set):
                        if myThresh in yrThresh:
                            # Not in a set that includes my acceptable value
                            if value is False:
                                return False
                        return None
                    elif isinstance(yrThresh,list):
                        try:
                            return yrThresh.index(myThresh)
                        except ValueError:
                            return None
                    elif isinstance(myThresh,list):
                        try:
                            return myThresh.index(yrThresh)
                        except ValueError:
                            return None
                    elif abs(myThresh - yrThresh) < myVec.epsilon:
                        # Values are the same, so test results must be the same
                        return value
                    elif value:
                        # Values are different, but we are equal to the other value
                        return False
                    else:
                        # Values are different, but not equal to other, so no information
                        return None
                elif cmp(myThresh,yrThresh) == yrComp:
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
            elif yrComp == 0:
                # Other specifies equality, we are inequality
                if value:
                    # Determine whether equality condition satisfies our inequality
                    return cmp(yrThresh,myThresh) == myComp
                else:
                    # No information about inequality
                    return None
            elif myThresh == yrThresh and myComp == yrComp:
                # Identical planes
                return value
            else:
                # Both inequalities, we should do something here
                return None
        return None

    def minimize(self):
        """
        """
        for i in range(len(self.planes)):
            vector,threshold,comparison = self.planes[i]
            if CONSTANT in vector:
                if isinstance(threshold,list):
                    threshold = [value-vector[CONSTANT] for value in threshold]
                elif isinstance(threshold,set):
                    threshold = {value-vector[CONSTANT] for value in threshold}
                else:
                    threshold -= vector[CONSTANT]
                vector[CONSTANT] = 0.
                self.planes[i] = (vector,threshold,comparison)
                self._string = None

    def __str__(self):
        if self._string is None:
            if self.isConjunction:
                operator = '\nAND '
            else:
                operator = '\nOR '
            self._string = operator.join(['%s %s %s' % (' + '.join(['%5.3f*%s' % (v,k)
                                                                    for k,v in vector.items()]),
                                                        self.COMPARISON_MAP[comparison],threshold)
                                          for vector,threshold,comparison in self.planes])
        return self._string

    def __xml__(self):
        doc = Document()
        root = doc.createElement('plane')
        for vector,threshold,comparison in self.planes:
            node = vector.__xml__().documentElement
            node.setAttribute('threshold',str(threshold))
            node.setAttribute('comparison',str(comparison))
            root.appendChild(node)
        doc.appendChild(root)
        return doc

    def parse(self,element):
        assert element.tagName == 'plane'
        node = element.firstChild
        self.planes = []
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert node.tagName == 'vector'
                vector = KeyedVector(node)
                text = node.getAttribute('threshold')
                if text[0] == '[':
                    if '.' in text:
                        threshold = [float(t) for t in text[1:-1].split(',')]
                    else:
                        threshold = [int(t) for t in text[1:-1].split(',')]
                elif text[0] == '{':
                    if '.' in text:
                        threshold = {float(t) for t in text[1:-1].split(',')}
                    else:
                        threshold = {int(t) for t in text[1:-1].split(',')}
                elif '.' in text:
                    threshold = float(text)
                else:
                    threshold = int(text)
                try:
                    comparison = int(node.getAttribute('comparison'))
                except ValueError:
                    comparison = str(node.getAttribute('comparison'))
                self.planes.append((vector,threshold,comparison))
            node = node.nextSibling

def thresholdRow(key,threshold):
    """
    :return: a plane testing whether the given keyed value exceeds the given threshold
    :rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key: 1.}),threshold)
def differenceRow(key1,key2,threshold):
    """
    :return: a plane testing whether the difference between the first and second keyed values exceeds the given threshold
    :rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key1: 1.,key2: -1.}),threshold)
def greaterThanRow(key1,key2):
    """
    :return: a plane testing whether the first keyed value is greater than the second
    :rtype: L{KeyedPlane}
    """
    return differenceRow(key1,key2,0.)
def trueRow(key):
    """
    :return: a plane testing whether a boolean keyed value is True
    :rtype: L{KeyedPlane}
    """
    return thresholdRow(key,0.5)
def andRow(trueKeys=[],falseKeys=[]):
    """
    :param trueKeys: list of keys which must be C{True} (default is empty list)
    :type trueKeys: str[]
    :param falseKeys: list of keys which must be C{False} (default is empty list)
    :type falseKeys: str[]
    :return: a plane testing whether all boolean keyed values are set as desired
    :rtype: L{KeyedPlane}
    """
    weights = {}
    for key in trueKeys:
        weights[key] = 1.
    for key in falseKeys:
        weights[key] = -1.
    return KeyedPlane(KeyedVector(weights),float(len(trueKeys))-0.5)
def equalRow(key,value):
    """
    :return: a plane testing whether the given keyed value equals the given target value
    :rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key: 1.}),value,0)
def equalFeatureRow(key1,key2):
    """
    :return: a plane testing whether the values of the two given features are equal
    :rtype: L{KeyedPlane}
    """
    return KeyedPlane(KeyedVector({key1: 1.,key2: -1.}),0,0)
