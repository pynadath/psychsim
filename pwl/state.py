import copy
import operator
from xml.dom.minidom import Document,Node

from psychsim.probability import Distribution
import keys

from vector import KeyedVector,VectorDistribution
from matrix import KeyedMatrix
from tree import KeyedTree

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
            self.distributions[0] = VectorDistribution()
            self.keyMap[keys.CONSTANT] = 0

    def keys(self):
        return self.keyMap.keys()
    
    def __iter__(self):
        """
        Iterate through elements of this set, with each element being a L{VectorDistributionSet} (with probability not necessarily 1)
        """
        size = 1
        domains = {}
        substates = sorted(self.distributions.keys())
        for substate in substates:
            dist = self.distributions[substate]
            domains[substate] = dist.domain()
            size *= len(dist.domain())
        for i in range(size):
            value = self.__class__()
            value.keyMap.update(self.keyMap)
            for substate in substates:
                element = domains[substate][i % len(domains[substate])]
                prob = self.distributions[substate][element]
                i /= len(domains[substate])
                value.distributions[substate] = VectorDistribution({element: prob})
            yield value

    def __len__(self):
        """
        @return: the number of elements in the implied joint distribution
        @rtype: int
        """
        return reduce(operator.mul,[len(d) for d in self.distributions.values()],1)
    
    def split(self,key):
        """
        @return: partitions this distribution into subsets corresponding to possible values for the given key
        @rtype: strS{->}L{VectorDistributionSet}
        """
        destination = self.keyMap[key]
        original = self.distributions[destination]
        result = {}
        for vector in original.domain():
            value = vector[key]
            if not value in result:
                # Copy everything from me except the distribution of the given key
                result[value] = self.__class__()
                result.keyMap.update(self.keyMap)
                for substate,distribution in self.distributions.items():
                    if substate != destination:
                        result.distributions[substate] = copy.deepcopy(distribution)
            result[value].distributions[destination][vector] = original[vector]
        return result
        
    def collapse(self,substates,preserveCertainty=True):
        """
        Collapses (in place) the given substates into a single joint L{VectorDistribution}
        """
        if len(substates) > 0:
            if isinstance(iter(substates).next(),str):
                # Why not handle keys, too?
                substates = self.substate(substates)
            if preserveCertainty:
                substates = {s for s in substates
                             if len(self.distributions[s]) > 1}
            self.merge(substates,True)
        
    def uncertain(self):
        """
        @return: C{True} iff this distribution has any uncertainty about the vector
        @rtype: bool
        """
        return sum(map(len,self.distributions.values())) > len(self.distributions)

    def findUncertainty(self,substates=None):
        """
        @param substates: Consider only the given substates as candidates
        @return: a substate containing an uncertain distribution if one exists; otherwise, None
        @rtype: int
        """
        if substates is None:
            substates = self.distributions.keys()
        for substate in substates:
            if len(self.distributions[substate]) > 1:
                return substate
        else:
            return None
        
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
            return {self.keyMap[k] for k in obj if k != keys.CONSTANT}
        elif isinstance(obj,bool):
            return set()
        else:
            return self.substate(obj.keys())

    def merge(self,substates,inPlace=False):
        """
        @return: a joint distribution across the given substates
        """
        if inPlace:
            result = self
        else:
            result = self.__class__()
        try:
            destination = iter(substates).next()
        except StopIteration:
            return result
        for substate,distribution in self.distributions.items():
            if substate == destination:
                if not inPlace:
                    result.distributions[substate] = copy.deepcopy(distribution)
            elif substate in substates:
                result.distributions[destination].merge(distribution,True)
                if inPlace:
                    del self.distributions[substate]
            elif not inPlace:
                result.distributions[substate] = copy.deepcopy(distribution)
        for key,substate in self.keyMap.items():
            if substate in substates:
                result.keyMap[key] = destination
            elif not inPlace:
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
        assert not substate is None
        if self.keyMap.has_key(key):
            substate = self.keyMap[key]
        else:
            self.keyMap[key] = substate
        if not self.distributions.has_key(substate):
            self.distributions[substate] = VectorDistribution()
        return self.distributions[substate].join(key,value)

    def marginal(self,key):
        return self.distributions[self.keyMap[key]].marginal(key)

    def items(self):
        return self.distributions.items()

    def clear(self):
        self.distributions.clear()
        self.keyMap.clear()

    def update(self,other,keySet):
        # Anyone else mixed up in this?
        toMerge = set(keySet)
        for key in keySet:
            # Any new keys in the same joint as this guy?
            for newKey in self.keyMap:
                if self.keyMap[key] == self.keyMap[newKey] or \
                   other.keyMap[key] == other.keyMap[newKey]:
                    # This key is in the same joint
                    if len(self.distributions[self.keyMap[newKey]]) == 1 and \
                       len(other.distributions[other.keyMap[newKey]]) == 1:
                        # Maybe this key's value collapses into certainty?
                        if self.marginal(newKey) == other.marginal(newKey):
                            continue
                    toMerge.add(newKey)
        if len(toMerge) > 0: # If 0, no difference between self and other to begin with
            # Prepare myself to merge
            substates = {self.keyMap[k] for k in toMerge}
            self.collapse(substates,False)
            key = iter(toMerge).next()
            destination = self.keyMap[key]
            # Align and merge the other
            substates = {other.keyMap[k] for k in toMerge}
            other.collapse(substates,False)
            dist = other.distributions[other.keyMap[key]]
            for vector in dist.domain():
                self.distributions[destination].addProb(vector,dist[vector])
                
    def __add__(self,other):
        if isinstance(other,self.__class__):
            assert self.keyMap == other.keyMap,'Currently unable to add distributions with mismatched substates'
            result = self.__class__()
            result.keyMap.update(self.keyMap)
            for substate,value in self.distributions.items():
                result[substate] = value + other.distributions[substate]
            return result
        else:
            return NotImplemented

    def __sub__(self,other):
        if isinstance(other,self.__class__):
            assert self.keyMap == other.keyMap,'Currently unable to subtract distributions with mismatched substates'
            result = self.__class__()
            result.keyMap.update(self.keyMap)
            for substate,value in self.distributions.items():
                result.distributions[substate] = value - other.distributions[substate]
            return result
        else:
            return NotImplemented

    def __imul__(self,other):
        if isinstance(other,KeyedMatrix):
            # Focus on subset that this matrix affects
            substates = self.substate(other.getKeysIn())
            self.collapse(substates)
            destination = self.findUncertainty(substates)
            # Go through each key this matrix sets
            for rowKey,vector in other.items():
                result = Distribution()
                # Go through the inputs to the new value
                for colKey in vector.keys():
                    if colKey == keys.CONSTANT:
                        # Doesn't really matter
                        substate = iter(self.distributions.keys()).next()
                    else:
                        substate = self.keyMap[colKey]
                    # Go through the distribution subset containing this key
                    for state in self.distributions[substate].domain():
                        result.addProb(vector[colKey]*state[colKey],
                                       self.distributions[substate][state])
                if len(result) == 1:
                    # We can create a new subset for this value
                    destination = max(self.keyMap.values())+1
                    assert not destination in self.distributions,self.distributions[destination]
                    self.join(rowKey,result,destination)
                elif destination is None:
                    # We can create a new subset for this value, but no more
                    destination = max(self.keyMap.values())+1
                    self.join(rowKey,result,destination)
                else:
                    # We have an uncertain substate to store this value in
                    self.join(rowKey,result,destination)
        elif isinstance(other,KeyedTree):
            if other.isLeaf():
                self *= other.children[None]
            elif other.isProbabilistic():
                raise NotImplementedError,'This is so easy to implement.'
            else:
                # Evaluate the hyperplane and split the state
                branchKeys = set(other.branch.keys())
                substates = self.substate(branchKeys)
                self.collapse(substates)
                self *= other.branch.vector
                valSub = self.keyMap[keys.VALUE]
                falseState = copy.deepcopy(self)
                tPossible = False
                fPossible = False
                del self.keyMap[keys.VALUE]
                del falseState.keyMap[keys.VALUE]
                for vector in self.distributions[valSub].domain():
                    prob = self.distributions[valSub][vector]
                    del self.distributions[valSub][vector]
                    del falseState.distributions[valSub][vector]
                    test = other.branch.evaluate(vector[keys.VALUE])
                    del vector[keys.VALUE]
                    if test:
                        # This vector passes the test
                        if len(vector) > 1:
                            self.distributions[valSub].addProb(vector,prob)
                        tPossible = True
                    else:
                        # This vector fails the test
                        if len(vector) > 1:
                            falseState.distributions[valSub].addProb(vector,prob)
                        fPossible = True
                existingKeys = set(self.keyMap.keys())
                if tPossible:
                    if len(self.distributions[valSub].domain()) == 0:
                        del self.distributions[valSub]
                    self *= other.children[True]
                if fPossible:
                    if tPossible:
                        newKeys = set(other.getKeysOut())
                        assert len(falseState.distributions[valSub].domain()) > 0
                        falseState *= other.children[False]
                        self.update(falseState,newKeys|branchKeys)
                    else:
                        if len(falseState.distributions[valSub].domain()) > 0:
                            self.distributions[valSub] = falseState.distributions[valSub]
                        elif len(self.distributions[valSub].domain()) == 0:
                            del self.distributions[valSub]
                        self *= other.children[False]
        elif isinstance(other,KeyedVector):
            substates = self.substate(other)
            self.collapse(substates)
            destination = self.findUncertainty(substates)
            if destination is None:
                destination = max(self.keyMap.values())+1
            total = 0.
            for key in other:
                if self.keyMap[key] != destination:
                    # Certain value for this key
                    marginal = self.marginal(key)
                    total += other[key]*iter(marginal.domain()).next()
            self.join(keys.VALUE,total,destination)
            for vector in self.distributions[destination].domain():
                prob = self.distributions[destination][vector]
                del self.distributions[destination][vector]
                for key in other:
                    if self.keyMap[key] == destination:
                        # Uncertain value
                        vector[keys.VALUE] += other[key]*vector[key]
                self.distributions[destination][vector] = prob
        else:
            return NotImplemented
        for s in self.distributions:
            assert s in self.keyMap.values(),self.distributions[s]
        for k,s in self.keyMap.items():
            if k != keys.CONSTANT:
                assert s in self.distributions
        return self

    def __rmul__(self,other):
        if isinstance(other,KeyedVector) or isinstance(other,KeyedTree):
            self *= other
            substate = self.keyMap[keys.VALUE]
            distribution = self.distributions[substate]
            del self.keyMap[keys.VALUE]
            total = 0.
            for vector in distribution.domain():
                prob = distribution[vector]
                del distribution[vector]
                total += prob*vector[keys.VALUE]
                del vector[keys.VALUE]
                if len(vector) > 1:
                    distribution[vector] = prob
            if len(distribution) == 0:
                del self.distributions[substate]
            for s in self.distributions:
                assert s in self.keyMap.values(),self.distributions[s]
            for k,s in self.keyMap.items():
                if k != keys.CONSTANT:
                    assert s in self.distributions
            return total
        else:
            return NotImplemented

    def rollback(self):
        """
        Removes any current state values and makes any future state values the current ones
        """
        # What keys have both current and future values?
        # TODO: Should be all of them when we're done with observations and models
        pairs = {k for k in self.keyMap if k != keys.CONSTANT and
                 not keys.isFuture(k) and keys.makeFuture(k) in self.keyMap}
        for now in pairs:
            nowSub = self.keyMap[now]
            future = keys.makeFuture(now)
            futureSub = self.keyMap[future]
            del self.keyMap[future]
            distribution = self.distributions[nowSub]
            for vector in distribution.domain():
                prob = distribution[vector]
                del distribution[vector]
                if nowSub == futureSub:
                    # Kill two birds with one stone
                    vector[now] = vector[future]
                    del vector[future]
                else:
                    del vector[now]
                if len(vector) > 1:
                    distribution[vector] = prob
            if nowSub != futureSub:
                # Kill two birds with two stones
                if len(distribution) == 0:
                    del self.distributions[nowSub]
                self.keyMap[now] = futureSub
                distribution = self.distributions[futureSub]
                for vector in distribution.domain():
                    prob = distribution[vector]
                    del distribution[vector]
                    vector[now] = vector[future]
                    del vector[future]
                    if len(vector) > 1:
                        distribution[vector] = prob
            assert now in self.keyMap
            assert self.keyMap[now] in self.distributions,now
        for s in self.distributions:
            assert s in self.keyMap.values(),self.distributions[s]
        for k,s in self.keyMap.items():
            if k != keys.CONSTANT:
                assert s in self.distributions,'%s: %s' % (k,s)
                
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
        for substate,distribution in self.distributions.items():
            new = copy.deepcopy(distribution)
            result.distributions[substate] = new
        result.keyMap.update(self.keyMap)
        return result
    
    def __str__(self):
        return '\n'.join(['%s:\n%s' % (sub,dist) for sub,dist in self.items()])
