from xml.dom.minidom import Document,Node

from psychsim.probability import Distribution

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
        else:
            return NotImplemented

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
