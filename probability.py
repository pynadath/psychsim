import math
from xml.dom.minidom import Document,Node

class Distribution(dict):
    """
    A probability distribution over hashable objects
    
    .. warning:: If you make the domain values mutable types, try not to change their values while they are inside the distribution.  If you must change a domain value, it is better to first delete the old value, change it, and then re-insert it.
    """
    epsilon = 1e-8

    def __new__(cls,args=None,rationality=None):
        obj = dict.__new__(cls)
        obj._domain = {}
        return obj
        
    def __init__(self,args=None,rationality=None):
        """
        :param args: the initial elements of the probability distribution
        :type args: dict
        :param rationality: if not ``None``, then use as a rationality parameter in a quantal response over the provided values
        :type rationality: float
        """
        dict.__init__(self)
#        self._domain = {}
        if isinstance(args,Node):
            self.parse(args)
        elif isinstance(args,Distribution):
            # Some other distribution given
            for key in args.domain():
                self[key] = args[key]
        elif isinstance(args,dict):
            if rationality is None:
                # Probability dictionary provided
                for key,value in args.items():
                    self[key] = value
            else:
                # Do quantal response / softmax on table of values
                for key,V in args.items():
                    self[key] = math.exp(rationality*V)
                self.normalize()

    def first(self):
        """
        :returns: the first element in this distribution's domain (most useful if there's only one element)
        """
        return next(iter(self.domain()))

    def get(self,element):
        key = hash(element)
        return dict.get(self,key,0.)
    
    def __getitem__(self,element):
        key = hash(element)
        return dict.__getitem__(self,key)
        
    def __setitem__(self,element,value):
        """
        :param element: the domain element
        :param value: the probability to associate with the given key
        :type value: float
        """
        key = hash(element)
        self._domain[key] = element
        dict.__setitem__(self,key,value)

    def items(self):
        for key,value in dict.items(self):
            yield self._domain[key],value

    def addProb(self,element,value):
        """
        Utility method that increases the probability of the given element by the given value
        """
        key = hash(element)
        if key in self._domain:
            dict.__setitem__(self,key,dict.__getitem__(self,key)+value)
        else:
            self._domain[key] = element
            dict.__setitem__(self,key,value)
#        try:
#            self[element] += value
#        except KeyError:
#            self[element] = value

    def getProb(self,element):
        """
        Utility method that is almost identical to __getitem__, except that it returns 0 for missing elements, instead of throwing a C{KeyError}
        """
        try:
            return self[element]
        except KeyError:
            return 0.

    def __delitem__(self,element):
        key = hash(element)
        dict.__delitem__(self,key)
        del self._domain[key]

    def clear(self):
        dict.clear(self)
        self._domain.clear()

    def replace(self,old,new):
        """Replaces on element in the sample space with another.  Raises an exception if the original element does not exist, and an exception if the new element already exists (i.e., does not do a merge)
        """
        prob = self[old]
        del self[old]
        self[new] = prob
        
    def domain(self):
        """
        :returns: the sample space of this probability distribution
        :rtype: list
        """
        return list(self._domain.values())

    def normalize(self):
        """Normalizes the distribution so that the sum of values = 1
        """
        total = sum(self.values())
        if abs(total-1.) > self.epsilon:
            for key in self.domain():
                try:
                    self[key] /= total
                except ZeroDivisionError:
                    self[key] = 1./float(len(self))
    
    def expectation(self):
        """
        :returns: the expected value of this distribution
        :rtype: float
        """
        if len(self) == 1:
            # Shortcut if no uncertainty
            return self.domain()[0]
        else:
            total = None
            for element in self.domain():
                if total is None:
                    total = element*self[element]
                else:
                    total += element*self[element]
            return total

    def __float__(self):
        return self.expectation()
        
    def sample(self,quantify=False):
        """
        :param quantify: if ``True``, also returns the amount of mass by which the sampling crosssed the threshold of the generated sample's range
        :returns: an element from this domain, with a sample probability given by this distribution
        """
        import random
        selection = random.uniform(0.,sum(self.values()))
        original = selection
        for element in self.domain():
            if selection > self[element]:
                selection -= self[element]
            else:
                if quantify:
                    return element,selection
                else:
                    return element
        # We shouldn't get here. But in case of some floating-point weirdness?
        return element

    def set(self,element):
        """
        Reduce distribution to be 100% for the given element
        :param element: the element that will be the only one with nonzero probability
        """
        self.clear()
        self[element] = 1.

    def select(self,maximize=False):
        """
        Reduce distribution to a single element, sampled according to the given distribution
        :returns: the probability of the selection made
        """
        if maximize:
            element = self.max()
        else:
            element = self.sample()
        prob = self[element]
        self.set(element)
        return prob

    def max(self):
        """
        :returns: the most probable element in this distribution (breaking ties by returning the highest-valued element)
        """
        return self._domain[max([(dict.__getitem__(self,element),element) for element in self._domain])[1]]

    def entropy(self):
        """
        :returns: entropy (in bits) of this distribution
        """
        return sum([-p*math.log2(p) for p in dict.values(self)])

    def __add__(self,other):
        if isinstance(other,Distribution):
            result = self.__class__()
            for me in self.domain():
                for you in other.domain():
                    result.addProb(me+you,self[me]*other[you])
            return result
        else:
            result = self.__class__()
            for element in self.domain():
                result.addProb(element+other,self[element])
            return result

    def __sub__(self,other):
        return self + (-other)

    def __neg__(self):
        result = self.__class__()
        for element in self.domain():
            result.addProb(-element,self[element])
        return result

    def __mul__(self,other):
        if isinstance(other,Distribution):
            raise NotImplementedError('Unable to multiply %s by %s.' \
                                      % (self.__class__.__name__,other.__class__.__name__))
        else:
            result = self.__class__()
            for element in self.domain():
                result.addProb(element*other,self[element])
            return result
        
    def prune(self,epsilon=1e-8):
        elements = self.domain()
        i = 0
        while i < len(self)-1:
            el1 = elements[i]
            j = i+1
            while j < len(self):
                el2 = elements[j]
                if abs(el1-el2) < epsilon:
                    self[el1] += self[el2]
                    del self[el2]
                    del elements[j]
                else:
                    j += 1
            i += 1

    def __xml__(self):
        """
        :returns: An XML Document object representing this distribution
        """
        doc = Document()
        root = doc.createElement('distribution')
        doc.appendChild(root)
        for key,value in self._domain.items():
            prob = dict.__getitem__(self,key)
            node = doc.createElement('entry')
            root.appendChild(node)
            node.setAttribute('probability',str(prob))
#            if key != hash(value):
#                node.setAttribute('key',key)
            if isinstance(value,str):
                node.setAttribute('key',key)
            else:
                node.appendChild(self.element2xml(value))
        return doc
        
    def element2xml(self,value):
        raise NotImplementedError('Unable to generate XML for distributions over %s' % (value.__class__.__name__))

    def parse(self,element):
        """Extracts the distribution from the given XML element
        :param element: The XML Element object specifying the distribution
        :type element: Element
        :returns: This L{Distribution} object"""
        assert element.tagName == 'distribution','Unexpected tag %s for %s' \
            % (element.tagName,self.__class__.__name__)
        self.clear()
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                prob = float(node.getAttribute('probability'))
                value = str(node.getAttribute('key'))
                if not value:
                    subNode = node.firstChild
                    while subNode and subNode.nodeType != subNode.ELEMENT_NODE:
                        subNode = subNode.nextSibling
                    value = self.xml2element(None,subNode)
                self[value] = prob
#                if not key:
#                    key = str(value)
#                dict.__setitem__(self,key,prob)
#                self._domain[key] = value
            node = node.nextSibling

    def xml2element(self,key,node):
        return key

    def sortedString(self):
        elements = self.domain()
        elements.sort(lambda x,y: cmp(str(x),str(y)))
        return '\n'.join(['%4.1f%%\t%s' % (100.*self[el],str(el)) for el in elements])

    def __str__(self):
        return '\n'.join(['%d%%\t%s' % (100*self[el],str(el).replace('\n','\n\t'))
                          for el in self._domain.values()])
#        return '\n'.join(map(lambda el: '%d%%\t%s' % (100.*self[el],str(el).replace('\n','\n\t')),self.domain()))

    def __hash__(self):
        return hash(str(self))

    def __copy__(self):
        return self.__class__(self.__xml__().documentElement)

    def __getstate__(self):
        return {el: self[el] for el in self.domain()}
    
    def __setstate__(self,state):
        self.clear()
        for el,prob in state.items():
            self[el] = prob
