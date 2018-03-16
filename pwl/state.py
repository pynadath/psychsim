from collections import OrderedDict
import copy
import itertools
import operator
from xml.dom.minidom import Document,Node

from psychsim.probability import Distribution
from . import keys

from psychsim.pwl.vector import KeyedVector,VectorDistribution
from psychsim.pwl.matrix import KeyedMatrix
from psychsim.pwl.tree import KeyedTree

class VectorDistributionSet:
    """
    Represents a distribution over independent state vectors, i.e., independent L{VectorDistribution}s
    """
    def __init__(self,node=None):
        self.distributions = {}
        self.keyMap = {}
        if isinstance(node,KeyedVector):
            node = VectorDistribution({node:1.})
        if isinstance(node,VectorDistribution):
            self.distributions[0] = node
            self.keyMap = {k: 0 for k in node.keys()}
        elif node:
            self.parse(node)
#        elif not empty:
#            self.distributions[0] = VectorDistribution()

    def keys(self):
        return self.keyMap.keys()

    def __contains__(self,key):
        return key in self.keyMap
    
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

    def __getitem__(self,key):
        if key == 0:
            raise DeprecationWarning('step no longer returns a list of outcomes, but rather a single VectorDistributionSet')
        else:
            return self.marginal(key)
        
    def __setitem__(self,key,value):
        """
        Computes a conditional probability of this distribution given the value for this key. To do so, it removes any elements from the distribution that are inconsistent with the given value and then normalizes.
        @warning: If you want to overwrite any existing values for this key use L{join} (which computes a new joint probability)
        """
        dist = self.distributions[self.keyMap[key]]
        for vector in dist.domain():
            if abs(vector[key]-value) > 1e-8:
                del dist[vector]
        dist.normalize()
        
    def __delitem__(self,key):
        """"
        Removes the given column from its corresponding vector (raises KeyError if not present in this distribution)
        """
        substate = self.keyMap[key]
        del self.keyMap[key]
        dist = self.distributions[substate]
        if len(dist.first()) == 2:
            # Assume CONSTANT is the other key, so this whole distribution goes
            del self.distributions[substate]
        else:
            # Go through each vector and remove the key one by one
            for vector in dist.domain():
                prob = dist[vector]
                del dist[vector]
                del vector[key]
                dist.addProb(vector,prob)
            
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
        if key in self.keyMap:
            substate = self.keyMap[key]
        else:
            self.keyMap[key] = substate
        if not substate in self.distributions:
            self.distributions[substate] = VectorDistribution()
        return self.distributions[substate].join(key,value)

    def marginal(self,key):
        return self.distributions[self.keyMap[key]].marginal(key)

    def domain(self,key):
        if isinstance(key,str):
            return {v[key] for v in self.distributions[self.keyMap[key]].domain()}
        elif isinstance(key,list):
            # Identify the relevant subdistributions
            substates = OrderedDict()
            for subkey in key:
                loc = self.keyMap[subkey]
                try:
                    substates[loc].append(subkey)
                    raise RuntimeError('Currently unable to compute domains over interdependent state features')
                except KeyError:
                    substates[loc] = [subkey]
            # Determine the domain of each feature across distributions
            domains = []
            for loc,keys in substates.items():
                dist = self.distributions[loc]
                domains.append([[vector[k] for k in keys] for vector in dist.domain()])
            return [sum(combo,[]) for combo in itertools.product(*domains)]
        else:
            return NotImplemented
    
    def items(self):
        return self.distributions.items()

    def clear(self):
        self.distributions.clear()
        self.keyMap.clear()

    def update(self,other,keySet,scale=1.):
        # Anyone else mixed up in this?
        toMerge = set(keySet)
        for key in keySet:
            # Any new keys in the same joint as this guy?
            for newKey in self.keyMap:
                if (key in self.keyMap and self.keyMap[key] == self.keyMap[newKey]) \
                   or other.keyMap[key] == other.keyMap[newKey]:
                    # This key is in the same joint
                    if len(self.distributions[self.keyMap[newKey]]) == 1 and \
                       len(other.distributions[other.keyMap[newKey]]) == 1:
                        # Maybe this key's value collapses into certainty?
                        if self.marginal(newKey) == other.marginal(newKey):
                            continue
                    toMerge.add(newKey)
        if len(toMerge) > 0: # If 0, no difference between self and other to begin with
            # Prepare myself to merge
            substates = {self.keyMap[k] for k in toMerge if k in self.keyMap}
            self.collapse(substates,False)
            for key in toMerge:
                if key in self.keyMap:
                    destination = self.keyMap[key]
                    break
            else:
                destination = max(self.keyMap.values())+1
                self.distributions[destination] = VectorDistribution()
            # Align and merge the other
            substates = {other.keyMap[k] for k in toMerge}
            other.collapse(substates,False)
            dist = other.distributions[other.keyMap[key]]
            for vector in dist.domain():
                self.distributions[destination].addProb(vector,dist[vector]*scale)
                for key in vector.keys():
                    if key != keys.CONSTANT:
                        self.keyMap[key] = destination
                
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
                if destination is None:
                    # Every value is 100%
                    total = 0.
                    for colKey in vector.keys():
                        if colKey == keys.CONSTANT:
                            # Doesn't really matter
                            total += vector[colKey]
                        else:
                            substate = self.keyMap[colKey]
                            value = self.distributions[substate].first()[colKey]
                            total += vector[colKey]*value
                    destination = max(self.keyMap.values())+1
                    assert not destination in self.distributions,self.distributions[destination]
                    self.join(rowKey,total,destination)
                else:
                    # There is at least one uncertain multiplicand
                    for state in self.distributions[destination].domain():
                        prob = self.distributions[destination][state]
                        del self.distributions[destination][state]
                        total = 0.
                        for colKey in vector.keys():
                            if colKey == keys.CONSTANT:
                                # Doesn't really matter
                                total += vector[colKey]
                            else:
                                substate = self.keyMap[colKey]
                                if substate == destination:
                                    value = state[colKey]
                                else:
                                    # Certainty
                                    value = self.distributions[substate].first()[colKey]
                                total += vector[colKey]*state[colKey]
                        state[rowKey] = total
                        self.distributions[destination][state] = prob
                self.keyMap[rowKey] = destination
        elif isinstance(other,KeyedTree):
            if other.isLeaf():
                self *= other.children[None]
            elif other.isProbabilistic():
                oldKids = list(other.children.domain())
                # Multiply out children, other than first-born
                newKids = []
                for child in oldKids[1:]:
                    assert child.isLeaf(),'Move probabilistic branches to bottom of your trees; otherwise, I haven\'t figured out the easiest math yet.'
                    myChild = copy.deepcopy(self)
                    myChild *= child
                    newKids.append(myChild)
                # Compute first-born child
                self *= oldKids[0]
                # Scale by probability of this child
                prob = other.children[oldKids[0]]
                subkeys = oldKids[0].getKeysOut()
                substates = self.substate(subkeys)
                substate = self.keyMap[iter(subkeys).next()]
                distribution = self.distributions[substate]
                for vector in distribution.domain():
                    distribution[vector] *= prob
                if len(substates) > 1:
                    raise RuntimeError('Somebody got greedy and independent-ified variables that are dependent')
                # Merge products into first-born
                for index in range(len(newKids)):
                    self.update(newKids[index],oldKids[index+1].getKeysOut(),
                                other.children[oldKids[index+1]])
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
                        falseState.collapse(falseState.substate(other.children[False]),
                                            False)
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
                if key != keys.CONSTANT and self.keyMap[key] != destination:
                    # Certain value for this key
                    marginal = self.marginal(key)
                    total += other[key]*iter(marginal.domain()).next()
            self.join(keys.VALUE,total,destination)
            for vector in self.distributions[destination].domain():
                prob = self.distributions[destination][vector]
                del self.distributions[destination][vector]
                for key in other:
                    if key == keys.CONSTANT or self.keyMap[key] == destination:
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
                    distribution.addProb(vector,prob)
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
                        distribution.addProb(vector,prob)
            assert now in self.keyMap
            assert self.keyMap[now] in self.distributions,now
        for s in self.distributions:
            assert s in self.keyMap.values(),self.distributions[s]
            for k in self.distributions[s].keys():
                assert not keys.isFuture(k),'Future key %s persists after rollback' \
                    % (k)
        for k,s in self.keyMap.items():
            if k != keys.CONSTANT:
                assert s in self.distributions,'%s: %s' % (k,s)
            assert not keys.isFuture(k)

    def __eq__(self,other):
        remaining = set(self.keyMap.keys())
        if remaining != set(other.keyMap.keys()):
            # The two do not even contain the same columns
            return False
        else:
            while remaining:
                key = remaining.pop()
                distributionMe = self.distributions[self.keyMap[key]]
                distributionYou = other.distributions[other.keyMap[key]]
                if distributionMe != distributionYou:
                    return False
                remaining -= set(distributionMe.keys())
            return True
        
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
        distributions = {}
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                distribution = VectorDistribution(node)
                try:
                    substate = int(node.getAttribute('label'))
                    for key in distribution.keys():
                        self.keyMap[key] = substate
                except ValueError:
                    substate = str(node.getAttribute('label'))
                    distributions[substate] = distribution
            node = node.nextSibling
        if distributions:
            # For backward compatibility with non-integer substates
            if self.distributions:
                substate = max(self.distributions.keys())+1
            else:
                substate = 0
            for distribution in distributions.values():
                self.distributions[substate] = distribution
                for key in distribution.keys():
                    self.keyMap[key] = substate
                substate += 1
        
    def __deepcopy__(self,memo):
        result = self.__class__()
        for substate,distribution in self.distributions.items():
            new = copy.deepcopy(distribution)
            result.distributions[substate] = new
        result.keyMap.update(self.keyMap)
        return result
    
    def __str__(self):
        return '\n'.join(['%s:\n%s' % (sub,dist) for sub,dist in self.items()])