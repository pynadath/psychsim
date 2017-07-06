from xml.dom.minidom import Document,Node

from psychsim.probability import Distribution
import keys

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

    def __rmul__(self,other):
        if isinstance(other,KeyedVector):
            result = {}
            for vector in self.domain():
                product = other*vector
                try:
                    result[product] += self[vector]
                except KeyError:
                    result[product] = self[vector]
            return Distribution(result)
        else:
            return NotImplemented
        
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

class VectorDistributionSet:
    """
    Represents a distribution over independent state vectors, i.e., independent L{VectorDistribution}s
    """
    def __init__(self,node=None,empty=False):
        self.distributions = {}
        self.keyMap = {}
        if node:
            self.parse(node)
        elif not empty:
            self.distributions[0] = VectorDistribution({KeyedVector({keys.CONSTANT: 1.}): 1.})

    def collapse(self,substates):
        """
        @rtype: L{VectorDistribution}
        """
        result = VectorDistribution({KeyedVector({keys.CONSTANT: 1.}): 1.})
        for substate in substates:
            result = result.merge(self.distributions[substate])
        return result
    
    def uncertain(self):
        """
        @return: C{True} iff this distribution has any uncertainty about the vector
        @rtype: bool
        """
        return sum(map(len,self.distributions.values())) > len(self.distributions)

    def vector(self):
        """
        @return: if this distribution contains only a single vector, return that vector; otherwise, throw exception
        @rtype: L{KeyedVector}
        """
        vector = KeyedVector()
        for substate,distribution in self.distributions.items():
            assert len(distribution) == 1,'Cannot return vector from uncertain distribution'
            vector.update(distribution.domain()[0])
        return vector

    def select(self,incremental=False):
        """
        Reduce distribution to a single element, sampled according to the given distribution
        @param incremental: if C{True}, then select each key value in series (rather than picking out a joint vector all at once, default is C{False})
        @return: the probability of the selection made
        """
        if incremental:
            prob = KeyedVector()
        else:
            prob = 1.
        for distribution in self.distributions.values():
            if incremental:
                prob.update(distribution.select(incremental))
            else:
                prob *= distribution.select(incremental)
        return prob

    def substate(self,obj):
        """
        @return: the substate referred to by all of the keys in the given object
        """
        if isinstance(obj,list) or isinstance(obj,set):
            return {self.keyMap[keys.makePresent(k)] for k in obj if k != keys.CONSTANT}
        elif isinstance(obj,bool):
            return set()
        else:
            return self.substate(obj.keys())

    def merge(self,substates):
        """
        @return: a joint distribution across the given substates
        """
        result = self.__class__()
        destination = list(substates)[0]
        for substate,distribution in self.distributions.items():
            if substate == destination:
                result.distributions[substate] = copy.deepcopy(distribution)
            elif substate in substates:
                result.distributions[substate].merge(distribution)
            else:
                result.distributions[substate] = copy.deepcopy(distribution)
        for key,substate in self.keyMap:
            if substate in substates:
                result.keyMap[key] = destination
            else:
                result.keyMap[key] = substate
        return result

    def join(self,key,value,substate=0):
        """
        Modifies the distribution over vectors to have the given value for the given key
        @param key: the key to the column to modify
        @type key: str
        @param value: either a single value to apply to all vectors, or else a L{Distribution} over possible values
        @substate: name of substate vector distribution to join with
        """
        if self.keyMap.has_key(key):
            substate = self.keyMap[key]
        else:
            self.keyMap[key] = substate
        if not self.distributions.has_key(substate):
            self.distributions[substate] = VectorDistribution({KeyedVector({keys.CONSTANT: 1.}): 1.})
        return self.distributions[substate].join(key,value)

    def marginal(self,key):
        return self.distributions[self.keyMap[key]].marginal(key)

    def items(self):
        return self.distributions.items()

    def clear(self):
        self.distributions.clear()
        self.keyMap.clear()

    def applyTree(self,tree,debug=False):
        if tree.isLeaf():
            return tree.children[None],set()
        elif tree.isProbabilistic():
            # Probabilistic branch
            result = psychsim.probability.Distribution()
            substate = set()
            for child in tree.children.domain():
                newTree,newStates = self.applyTree(child)
                if isinstance(newTree,psychsim.probability.Distribution):
                    for subTree in newTree.domain():
                        result.addProb(subTree,tree.children[child]*newTree[subTree])
                else:
                    result.addProb(newTree,tree.children[child])
                substate |= newStates
            return result,substate
        else:
            # Deterministic branch
            substate = self.substate(tree.branch)
            if len(substate) > 1:
                raise UserWarning
            else:
                if debug: print(tree.branch)
                distribution = self.distributions[next(iter(substate))]
                if debug: print(distribution)
                result = psychsim.probability.Distribution()
                for vector in distribution.domain():
                    branch = tree.branch.evaluate(vector)
                    newTree,newStates = self.applyTree(tree.children[branch])
                    if isinstance(newTree,psychsim.probability.Distribution):
                        for subTree in newTree.domain():
                            result.addProb(subTree,distribution[vector]*newTree[subTree])
                    else:
                        result.addProb(newTree,distribution[vector])
                    substate |= newStates
                return result,substate
        
    def __add__(self,other):
        if isinstance(other,self.__class__):
            assert self.keyMap == other.keyMap,'Currently unable to add distributions with mismatched substates'
            result = self.__class__()
            result.keyMap.update(self.keyMap)
            for substate,value in self.distributions.items():
                result[substate] = value + other.distributions[substate]
            return result
        else:
            raise NotImplemented

    def __sub__(self,other):
        if isinstance(other,self.__class__):
            assert self.keyMap == other.keyMap,'Currently unable to subtract distributions with mismatched substates'
            result = self.__class__()
            result.keyMap.update(self.keyMap)
            for substate,value in self.distributions.items():
                result.distributions[substate] = value - other.distributions[substate]
            return result
        else:
            raise NotImplemented

    def __rmul__(self,other):
        if isinstance(other,KeyedVector):
            relevant = self.substate(other)
            subset = self.collapse(relevant)
            return other*subset
        else:
            return NotImplemented
        
    def __xml__(self):
        doc = Document()
        root = doc.createElement('worlds')
        doc.appendChild(root)
        for label,distribution in self.distributions.items():
            node = distribution.__xml__().documentElement
            root.appendChild(node)
            if label:
                node.setAttribute('label',str(label))
        return doc

    def parse(self,element):
        self.keyMap.clear()
        assert element.tagName == 'worlds'
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                label = str(node.getAttribute('label'))
                if not label:
                    label = None
                self.distributions[label] = VectorDistribution(node)
                for key in self.distributions[label].domain()[0].keys():
                    if key != keys.CONSTANT:
                        self.keyMap[key] = label
            node = node.nextSibling
        
    def __deepcopy__(self,memo):
        result = self.__class__()
        for substate,distribution in self.items():
            try:
                new = memo[id(distribution)]
            except KeyError:
                new = copy.deepcopy(distribution)
                memo[id(distribution)] = new
            result.distributions[substate] = distribution
        result.keyMaps.update(self.keyMap)
        return result

    def separate(self,trees,value):
        """
        Identifies which elements in this distribution have the given value across all of the given trees
        """
        good = self.__class__(empty=True)
        good.keyMap.update(self.keyMap)
        bad = self.__class__(empty=True)
        bad.keyMap.update(self.keyMap)
        treeMap = {}
        for substate in self.distributions.keys():
            treeMap[substate] = []
            good.distributions[substate] = VectorDistribution()
            bad.distributions[substate] = VectorDistribution()
        for tree in trees:
            substate = self.substate(tree)
            if len(substate) == 1:
                substate = iter(substate).next()
            elif len(substate) == 0:
                raise UserWarning,'You\'ve made a termination condition that is constant. Why?'
            else:
                raise NotImplementedError,'My creator has given me insufficient wit to handle this termination dependency'
            treeMap[substate].append(tree)
        for substate,distribution in self.distributions.items():
            for vector in distribution.domain():
                for tree in treeMap[substate]:
                    if tree[vector] != value:
                        # Fail
                        bad.distributions[substate][vector] = distribution[vector]
                        break
                else:
                    # Succeed
                    good.distributions[substate][vector] = distribution[vector]
        return good,bad
    
    def __str__(self):
        return '\n'.join(['%s:\n%s' % (sub,dist) for sub,dist in self.items()])
