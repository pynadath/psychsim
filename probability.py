from xml.dom.minidom import Document,Node

class Distribution(dict):
    """
    A probability distribution

       - C{dist.L{domain}()}:   Returns the domain of possible values
       - C{dist.L{items}()}:  Returns the list of all (value,prob) pairs
       - C{dist[value]}:     Returns the probability of the given value
       - C{dist[value] = x}: Sets the probability of the given value to x

    The possible domain values are any objects
    @warning: If you make the domain values mutable types, try not to change the values while they are inside the distribution.  If you must change a domain value, it is better to first delete the old value, change it, and then re-insert it.
    """
    epsilon = 1e-8

    def __init__(self,args=None):
        self._domain = {}
        dict.__init__(self)
        if not args is None:
            if isinstance(args,Node):
                self.parse(args)
            else:
                for key,value in args.items():
                    self[key] = value

    def __getitem__(self,element):
        key = str(element)
        return dict.__getitem__(self,key)
        
    def __setitem__(self,element,value):
        """
        @param element: the domain element
        @param value: the probability to associate with the given key
        @type value: float
        """
        key = str(element)
        self._domain[key] = element
        dict.__setitem__(self,key,value)

    def __delitem__(self,element):
        key = str(element)
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
        @return: the sample space of this probability distribution
        @rtype: C{list}
        """
        return self._domain.values()

    def normalize(self):
        """Normalizes the distribution so that the sum of values = 1
        @note: Not sure if this is really necessary"""
        total = sum(self.values())
        if abs(total-1.) > self.epsilon:
            for key in self.domain():
                try:
                    self[key] /= total
                except ZeroDivisionError:
                    self[key] = 1./float(len(self))
    
    def expectation(self):
        """
        @return: the expected value of this distribution
        @rtype: float
        @warning: As a side effect, the distribution will be normalized
        """
        if len(self) == 1:
            # Shortcut if no uncertainty
            return self.domain()[0]
        else:
            # I suppose we could just assume that the distribution is already
            # normalized
            self.normalize()
            total = None
            for element in self.domain():
                if total is None:
                    total = element*self[element]
                else:
                    total += element*self[element]
            return total

    def sample(self):
        """
        @return: an element from this domain, with a sample probability given by this distribution
        """
        import random
        selection = random.random()
        for element in self.domain():
            if selection > self[element]:
                selection -= self[element]
            else:
                return element
        else:
            raise ValueError,'Random number exceeded total probability in distribution.'

    def set(self,element):
        """
        Reduce distribution to be 100% for the given element
        @param element: the element that will be the only one with nonzero probability
        """
        self.clear()
        self[element] = 1.

    def select(self):
        """
        Reduce distribution to a single element, sampled according to the given distribution
        @return: the selected element
        """
        element = self.sample()
        self.set(element)
        return element

    def __add__(self,other):
        if isinstance(other,Distribution):
            raise NotImplementedError,'Unable to add two distributions.'
        else:
            result = {}
            for element in self.domain():
                result[element+other] = self[element]
            return self.__class__(result)

    def __sub__(self,other):
        return self + (-other)

    def __xml__(self):
        """
        @return: An XML Document object representing this distribution
        """
        doc = Document()
        root = doc.createElement('distribution')
        doc.appendChild(root)
        for key,value in self._domain.items():
            prob = dict.__getitem__(self,key)
            node = doc.createElement('entry')
            root.appendChild(node)
            node.setAttribute('probability',str(prob))
            if key != str(value):
                node.setAttribute('key',key)
            if isinstance(value,str):
                node.setAttribute('key',key)
            else:
                node.appendChild(self.element2xml(value))
        return doc
        
    def element2xml(self,value):
        raise NotImplementedError,'Unable to generate XML for distributions over %s' % (value.__class__.__name__)

    def parse(self,element):
        """Extracts the distribution from the given XML element
        @param element: The XML Element object specifying the distribution
        @type element: Element
        @return: This L{Distribution} object"""
        assert element.tagName == 'distribution'
        self.clear()
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                prob = float(node.getAttribute('probability'))
                key = str(node.getAttribute('key'))
                subNode = node.firstChild
                while subNode and subNode.nodeType != subNode.ELEMENT_NODE:
                    subNode = subNode.nextSibling
                value = self.xml2element(key,subNode)
                if not key:
                    key = str(value)
                dict.__setitem__(self,key,prob)
                self._domain[key] = value
            node = node.nextSibling

    def xml2element(self,key,node):
        return key

    def __str__(self):
        return '\n'.join(map(lambda el: '%d%%\t%s' % (100.*self[el],str(el).replace('\n','\n\t')),self.domain()))

    def __hash__(self):
        return hash(str(self))

    def __copy__(self):
        return self.__class__(self.__xml__().documentElement)
