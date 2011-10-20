import copy
import random
from xml.dom.minidom import Document

from Keys import ConstantKey

def setitemAndReturn(table,key,value):
    """Helper method used by L{Distribution.join} method
    @param table: the dictionary to modify
    @type table: dictionary
    @param key: the entry to set in that dictionary
    @type key: hashable instance
    @param value: the value to stick into the dictionary
    @return: a I{copy} of the original dictionary with the specified key-value association inserted
    """
    new = copy.copy(table)
    new[key] = value
    return new

class Distribution(dict):
    """
    A probability distribution

       - C{dist.L{domain}()}:   Returns the domain of possible values
       - C{dist.L{items}()}:  Returns the list of all (value,prob) pairs
       - C{dist[value]}:     Returns the probability of the given value
       - C{dist[value] = x}: Sets the probability of the given value to x

    The possible domain values are any objects
    @warning: If you make the domain values mutable types, try not to change the values while they are inside the distribution.  If you must change a domain value, it is better to first delete the old value, change it, and then re-insert it.
    @cvar epsilon: the granularity for float comparisons
    @type epsilon: float
    """
    epsilon = 0.0001

    def __init__(self,args=None):
        self._domain = {}
        dict.__init__(self)
        if not args is None:
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
        @warning: raises an C{AssertionError} if setting to an invalid prob value"""
        value = max(0.,value)
##        assert value > -self.epsilon,\
##               "Negative probability value: %f" % (value)
        # It's ok to be temporarily un-normalized
##        assert value < 1.+self.epsilon,\
##               "Probability value exceeds 1: %f" % (value)
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

    def items(self):
        """
        @return: a list of tuples of value,probability pairs
        @rtype: (value,float)[]
        """
        return map(lambda k:(self._domain[k],dict.__getitem__(self,k)),
                   self.keys())
    
    def domainKeys(self):
        """
        @return: all keys contained in the domain values
        @rtype: C{dict:L{teamwork.math.Keys.Key}S{->}boolean}
        """
        keys = {}
        for value in self.domain():
            for key in value.keys():
                keys[key] = True
        return keys
    
    def normalize(self):
        """Normalizes the distribution so that the sum of values = 1
        @note: Not sure if this is really necessary"""
        total = sum(self.values())
        if abs(total-1.) > self.epsilon:
            for key,value in self.items():
                try:
                    self[key] /= total
                except ZeroDivisionError:
                    self[key] = 1./float(len(self))

    def marginalize(self,key):
        """Marginalizes the distribution to remove the given key (not in place! returns the new distribution)
        @param key: the key to marginalize over
        @return: a new L{Distribution} object representing the marginal distribution
        @note: no exception is raised if the key is not present"""
        result = self.__class__()
        for row,prob in self.items():
            new = copy.copy(row)
            new.unfreeze()
            try:
                del new[key]
            except KeyError:
                pass
            try:
                result[new] += prob
            except KeyError:
                result[new] = prob
        return result

    def getMarginal(self,key):
        """Marginalizes the distribution over all but the given key
        @param key: the key to compute the marginal distribution over
        @return: a new L{Distribution} object representing the marginal"""
        result = self.__class__()
        for row,prob in self.items():
##            try:
            value = row[key]
##            except KeyError:
##                # If no entry, then assume 0 value
##                # (maybe there are domains where this is incorrect?)
##                value = 0.
            try:
                result[value] += prob
            except KeyError:
                result[value] = prob
        return result

    def join(self,key,value,debug=False):
        """Returns the joint distribution that includes the given key
        @param key: any hashable instance
        @param value: if a L{Distribution}, the marginal distribution for the given key; otherwise, the marginal distribution is assumed to be I{P(key=value)=1} 
        @return: the joint distribution combining the current distribution with the specified marginal over the given key
        @warning: this method assumes that this L{Distribution} has domain values that are C{dict} instances (i.e., for each domain element C{e}, it can set C{e[key]=value})...in other words, there should probably be a subclass."""
        if isinstance(value,Distribution):
            self.compose(value,lambda x,y,k=key:setitemAndReturn(x,k,y),
                         replace=True,debug=debug)
        else:
            for row,prob in self.items():
                del self[row]
                row[key] = value
                self[row] = prob
        return self
    
    def expectation(self):
        """Returns the expected value of this distribution

        @warning: As a side effect, the distribution will be normalized"""
        if len(self) == 1:
            # Shortcut if no uncertainty
            return self.domain()[0]
        else:
            # I suppose we could just assume that the distribution is already
            # normalized
            self.normalize()
            total = None
            for key,value in self.items():
                if total is None:
                    total = key*value
                else:
                    total += key*value
            return total

    def prune(self):
        """Removes any zero-probability entries from this distribution
        @return: the pruned distribution (not a copy)"""
        for key,value in self.items():
            if abs(value) < self.epsilon:
                del self[key]
        return self

    def fill(self,keys,value=0.):
        """Fills in any missing rows/columns in the domain matrices with a default value
        @param keys: the new slots that should be filled
        @type keys: C{L{teamwork.math.Keys.Key}[]}
        @param value: the default value (default is 0.)
        @note: essentially calls appropriate C{fill} method for any domain objects
        """
        for element,prob in self.items():
            del self[element]
            element.fill(keys,value)
            self[element] = prob
            

    def freeze(self):
        """Locks in the dimensions and keys of all domain values"""
        for element in self.domain():
            element.freeze()

    def unfreeze(self):
        """Unlocks in the dimensions and keys of all domain values"""
        for element in self.domain():
            element.unfreeze()

    def instantiate(self,table):
        """Substitutes values for any abstract references, using the
        given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{teamwork.math.Keys.Key} object
        @type table: dictionary"""
        result = self.__class__()
        for key,element in self._domain.items():
            prob = dict.__getitem__(self,key)
            new = element.instantiate(table)
            if key == str(element):
                # Make sure new key matches new element
                key = str(new)
            result._domain[key] = new
            try:
                prob += dict.__getitem__(result,key)
            except KeyError:
                pass
            dict.__setitem__(result,key,prob)
        return result

    def instantiateKeys(self,table):
        """Substitutes values for any abstract references, using the
        given substitution table
        @param table: dictionary of key-value pairs, where the value will be substituted for any appearance of the given key in a field of this L{teamwork.math.Keys.Key} object
        @type table: dictionary"""
        for key,element in self._domain.items():
            prob = dict.__getitem__(self,key)
            # Check whether we need to synch key with new value
            update = key == str(element)
            element.instantiateKeys(table)
            if update:
                dict.__delitem__(self,key)
                del self._domain[key]
                key = str(element)
            self._domain[key] = element
            dict.__setitem__(self,key,prob)
            
    def compose(self,other,operator,replace=False,debug=False):
        """Composes this distribution with the other given, using the given op
        @param other: a L{Distribution} object, or an object of the same class as the keys in this Distribution object
        @param operator: a binary operator applicable to the class of keys in this L{Distribution} object
        @param replace:  if this flag is true, the result modifies this distribution itself
        @return: the composed distribution"""
        if replace:
            result = self
        else:
            result = self.__class__()
        original = self.items()
        if replace:
            self.clear()
        for key1,value1 in original:
            if isinstance(other,Distribution):
                for key2,value2 in other.items():
                    if debug:
                        print key1,key2
                    key = apply(operator,(key1,key2))
                    if debug:
                        print '\t->',key
                    prob = value1*value2
                    try:
                        result[key] += prob
                    except KeyError:
                        result[key] = prob
                    if debug:
                        print '\t=',result[key]
            else:
                key = apply(operator,(key1,other) )
                try:
                    result[key] += value1
                except KeyError:
                    result[key] = value1
        return result 
        
    def __add__(self,other):
        """
        @note: Also supports + operator between Distribution object and objects of the same class as its keys"""
        return self.compose(other,lambda x,y:x+y)
    
    def __neg__(self):
        result = self.__class__()
        for key,value in self._domain.items():
            prob = dict.__getitem__(self,key)
            result[-value] = prob
        return result

    def __sub__(self,other):
        """@note: Also supports - operator between L{Distribution} object and objects of the same class as its keys"""
        return self + (-other)

    def __mul__(self,other):
        """@note: Also supports * operator between L{Distribution} object and objects of the same class as its keys"""
        return self.compose(other,lambda x,y:x*y)


    def __div__(self,other):
        if isinstance(other,Distribution):
            return self.conditional(other,{})
        else:
            return self * (1./other)

    def conditional(self,other,value={}):
        """Computes a conditional probability, given this joint probability I{P(AB)}, the marginal probability I{P(B)}, and the value of I{B} being conditioned on
        @param other: the marginal probability, I{P(B)}
        @type other: L{Distribution}
        @param value: the value of I{B}
        @type value: L{KeyedVector} (if omitted, it's assumed that both I{P(AB)} and I{P(B)} have already been conditioned on the desired value)
        @return: I{P(A|B=C{value})} where C{self} is I{P(AB)}
        @rtype: L{Distribution}
        """
        result = {}
        for myValue,myProb in self.items():
            for yrValue,yrProb in other.items():
                for key in value.keys():
                    if not yrValue.has_key(key) \
                           or yrValue[key] != value[key]:
                        break
                else:
                    for key in yrValue.keys():
                        if not myValue.has_key(key) \
                               or myValue[key] != yrValue[key]:
                            break
                    else:
                        new = copy.copy(myValue)
                        frozen = new.unfreeze()
                        for key in yrValue.keys():
                            if not isinstance(key,ConstantKey):
                                del new[key]
                        if frozen:
                            new.freeze()
                        try:
                            result[new] += myProb/yrProb
                        except KeyError:
                            result[new] = myProb/yrProb
        return Distribution(result)


    def reachable(self,estimators,observations,horizon):
        """Computes any reachable distributions from this one
        @param estimators: any possible conditional probability distributions, expressed as dictionaries, each containing C{numerator} and C{denominator} fields
        @type estimators: dict[]
        @param observations: any possible observations
        @type observations: L{KeyedVector}[]
        @param horizon: the maximum length of observation sequences to consider (if less than 1, then only the current distribution is reachable)
        @return: all the reachable distributions
        @rtype: L{Distribution}[]
        """
        if horizon <= 0:
            return [self]
        reachable = {str(self):self}
        for estimator in estimators:
            numerator = estimator['numerator']*self
            denominator = estimator['denominator']*self
            for obs in observations:
                posterior = numerator.conditional(denominator,obs)
                for beliefState in posterior.reachable(estimators,observations,
                                                       horizon-1):
                    key= str(beliefState)
                    if not reachable.has_key(key):
                        reachable[key] = beliefState
        return reachable.values()

    def sample(self):
        """
        @return: a single element from the sample space, chosen randomly according to this distribution.
        """
        elements = self.domain()
        elements.sort()
        total = random.random()
        index = 0
        while total > self[elements[index]]:
            total -= self[elements[index]]
            index += 1
        return elements[index]
        
    def __float__(self):
        """Supports float conversion of distributions by returning EV.
        Invoked by calling C{float(self)}"""
        return float(self.expectation())

    def __str__(self):
        """Returns a pretty string representation of this distribution"""
        return self.simpleText()
##         content = ''
##         for value,prob in self.items():
##             content += '%s with probability %5.3f, ' % (str(value),prob)
##         return content[:-2]

    def simpleText(self,numbers=True,all=False):
        """
        @param numbers: if C{True}, returns a number-free representation of this distribution
        """
        if not numbers:
            raise DeprecationWarning,'Do not be afraid.  Numbers are your friends.'
        return ',\n'.join(map(lambda (key,value): '%s with probability %5.3f' % \
                                 (str(value),dict.__getitem__(self,key)),
                             self._domain.items()))

    def __copy__(self):
        result = self.__class__()
        result._domain.update(self._domain)
        for element in result._domain.keys():
            dict.__setitem__(result,element,dict.__getitem__(self,element))
        return result
        
    def __deepcopy__(self,memo):
        result = self.__class__()
        memo[id(self)] = result
        result._domain = copy.deepcopy(self._domain,memo)
        for element in result._domain.keys():
            dict.__setitem__(result,element,dict.__getitem__(self,element))
        return result
        
    def __xml__(self):
        """@return: An XML Document object representing this distribution"""
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
                node.appendChild(value.__xml__().documentElement)
        return doc
        
    def parse(self,element,valueClass=None):
        """Extracts the distribution from the given XML element
        @param element: The XML Element object specifying the distribution
        @type element: Element
        @param valueClass: The class used to generate the domain values for this distribution
        @return: This L{Distribution} object"""
        assert(element.tagName == 'distribution')
        self.clear()
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                prob = float(node.getAttribute('probability'))
                key = str(node.getAttribute('key'))
                subNode = node.firstChild
                while subNode and subNode.nodeType != subNode.ELEMENT_NODE:
                    subNode = subNode.nextSibling
                if subNode:
                    value = valueClass()
                    value = value.parse(subNode)
                else:
                    value = key
                if value is None:
                    raise UserWarning,'XML parsing method for %s has null return value' % (valueClass.__name__)
                if not key:
                    key = str(value)
                self[key] = prob
                self._domain[key] = value
            node = node.nextSibling
        return self
