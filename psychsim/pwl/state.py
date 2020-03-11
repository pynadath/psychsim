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
        if isinstance(node,dict):
            substate = 0
            for key,value in node.items():
                self.join(key,value,substate)
                substate += 1
        elif isinstance(node,VectorDistribution):
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
                i //= len(domains[substate])
                value.distributions[substate] = VectorDistribution({element: prob})
            yield value

    def __len__(self):
        """
        :return: the number of elements in the implied joint distribution
        :rtype: int
        """
        prod = 1
        for dist in self.distributions.values():
            prod *= len(dist)
        return prod

    def __getitem__(self,key):
        return self.marginal(key)
        
    def __setitem__(self,key,value):
        """
        Computes a conditional probability of this distribution given the value for this key. To do so, it removes any elements from the distribution that are inconsistent with the given value and then normalizes.
        .. warning:: If you want to overwrite any existing values for this key use L{join} (which computes a new joint probability)
        """
        dist = self.distributions[self.keyMap[key]]
        for vector in dist.domain():
            if abs(vector[key]-value) > 1e-8:
                del dist[vector]
        dist.normalize()
        
    def subDistribution(self,key):
        """
        :return: the minimal joint distribution containing this key
        """
        return self.distributions[self.keyMap[key]]

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
            # Go through each vector and remove the key
            for vector in dist.domain():
                prob = dist[vector]
                del dist[vector]
                del vector[key]
                dist.addProb(vector,prob)

    def deleteKeys(self,toDelete):
        """
        Removes multiple columns at once
        """
        distributions = {}
        for key in toDelete:
            substate = self.keyMap[key]
            del self.keyMap[key]
            if substate in distributions:
                old = distributions[substate]
                distributions[substate] = []
                for vector,prob in old:
                    del vector[key]
                    distributions[substate].append((vector,prob))
            else:
                dist = self.distributions[substate]
                distributions[substate] = []
                for vector in dist.domain():
                    prob = dist[vector]
                    del vector[key]
                    distributions[substate].append((vector,prob))
        for substate,dist in distributions.items():
            if len(dist[0][0]) == 1:
                assert next(iter(dist[0][0].keys())) == keys.CONSTANT
                del self.distributions[substate]
            else:
                self.distributions[substate].clear()
                for vector,prob in distributions[substate]:
                    self.distributions[substate].addProb(vector,prob)
            
    def split(self,key):
        """
        :return: partitions this distribution into subsets corresponding to possible values for the given key
        :rtype: dict(str,VectorDistributionSet)
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
            if isinstance(next(iter(substates)),str):
                # Why not handle keys, too?
                substates = self.substate(substates)
            if preserveCertainty:
                substates = {s for s in substates
                             if len(self.distributions[s]) > 1}
            result = self.merge(substates)
            return result
        else:
            raise ValueError('No substates to collapse')
        
    def uncertain(self):
        """
        :return: C{True} iff this distribution has any uncertainty about the vector
        :rtype: bool
        """
        return sum(map(len,self.distributions.values())) > len(self.distributions)

    def findUncertainty(self,substates=None):
        """
        :param substates: Consider only the given substates as candidates
        :return: a substate containing an uncertain distribution if one exists; otherwise, None
        :rtype: int
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
        :return: if this distribution contains only a single vector, return that vector; otherwise, throw exception
        :rtype: KeyedVector
        """
        vector = KeyedVector()
        for substate,distribution in self.distributions.items():
            assert len(distribution) == 1,'Cannot return vector from uncertain distribution'
            vector.update(distribution.domain()[0])
        return vector

    def worlds(self):
        """
        :return: iterator through all possible joint vectors (i.e., possible worlds) and their probabilities
        :rtype: KeyedVector,float
        """
        # Convert to lists now to ensure same ordering throughout
        substates = list(self.distributions.keys())
        domains = {substate: self.distributions[substate].domain() for substate in substates}
        for index in range(len(self)):
            vector = {}
            prob = 1.
            for substate in substates:
                subindex = index % len(self.distributions[substate])
                subvector = domains[substate][subindex % len(domains[substate])]
                vector.update(subvector)
                prob *= self.distributions[substate][subvector]
                index = index // len(self.distributions[substate])
            yield KeyedVector(vector),prob

    def select(self,maximize=False,incremental=False):
        """
        Reduce distribution to a single element, sampled according to the given distribution
        :param incremental: if C{True}, then select each key value in series (rather than picking out a joint vector all at once, default is C{False})
        :return: the probability of the selection made
        """
        if incremental:
            prob = KeyedVector()
        else:
            prob = 1.
        for distribution in self.distributions.values():
            if incremental:
                prob.update(distribution.select(maximize,incremental))
            else:
                prob *= distribution.select(maximize,incremental)
        return prob

    def substate(self,obj,ignoreCertain=False):
        """
        :return: the substate referred to by all of the keys in the given object
        """
        if isinstance(obj,bool):
            raise DeprecationWarning('If you really need this, please inform management.')
            return set()
        elif ignoreCertain:
            return {self.keyMap[k] for k in obj if k != keys.CONSTANT and len(self.distributions[self.keyMap[k]]) > 1}
        else:
            return {self.keyMap[k] for k in obj if k != keys.CONSTANT}

    def merge(self,substates):
        """
        :return: the substate into which they've all been merged
        """
        destination = None
        for substate in substates:
            if destination is None:
                destination = substate
            else:
                dist = self.distributions[substate]
                self.distributions[destination].merge(dist,True)
                del self.distributions[substate]
                for key in dist.keys():
                    if key != keys.CONSTANT:
                        self.keyMap[key] = destination
        return destination

    def join(self,key,value,substate=0):
        """
        Modifies the distribution over vectors to have the given value for the given key
        :param key: the key to the column to modify
        :type key: str
        :param value: either a single value to apply to all vectors, or else a L{Distribution} over possible values
        :substate: name of substate vector distribution to join with, ignored if the key already exists in this state. By default, find a new substate
        """
        if key in self.keyMap:
            substate = self.keyMap[key]
        else:
            if substate is None:
                substate = 0
                while substate in self.distributions:
                    substate += 1
            self.keyMap[key] = substate
        if not substate in self.distributions:
            self.distributions[substate] = VectorDistribution({KeyedVector({keys.CONSTANT:1.}):1.})
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
            for loc,subkeys in substates.items():
                dist = self.distributions[loc]
                domains.append([[vector[k] for k in subkeys] for vector in dist.domain()])
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
                    if len(self.distributions[self.keyMap[newKey]]) > 1 or \
                       len(other.distributions[other.keyMap[newKey]]) > 1 or \
                        self.marginal(newKey) != other.marginal(newKey):
                        # If there's uncertainty
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
            return destination
        else:
            return None
                
    def __add__(self,other):
        if isinstance(other,self.__class__):
            assert self.keyMap == other.keyMap,'Currently unable to add distributions with mismatched substates'
            result = self.__class__()
            result.keyMap.update(self.keyMap)
            for substate,value in self.distributions.items():
                result.distributions[substate] = value + other.distributions[substate]
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

    def __imul__(self,other,select=False):
        if isinstance(other,KeyedMatrix):
            # Focus on subset that this matrix affects
            substates = self.substate(other.getKeysIn(),True)
            if substates:
                destination = self.collapse(substates)
            else:
                destination = None
            #     if destination:
            #         print self.distributions[destination]
            #         print len(self.distributions[destination])
            # destination = self.findUncertainty(substates)
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
                    assert not rowKey in self.keyMap,'%s already exists' % (rowKey)
                    destination = len(self.distributions)
                    while destination in self.distributions:
                        destination -= 1
#                    destination = max(self.keyMap.values())+1
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
                                total += vector[colKey]*value
                        state[rowKey] = total
                        self.distributions[destination][state] = prob
                self.keyMap[rowKey] = destination
        elif isinstance(other,KeyedTree):
            if other.isLeaf():
                self *= other.children[None]
            elif other.isProbabilistic():
                if select:
                    oldKid = other.children.sample(select=='max')
                    self *= oldKid
                else:
                    oldKids = list(other.children.domain())
                    # Multiply out children, other than first-born
                    newKids = []
                    for child in oldKids[1:]:
                        assert child.getKeysOut() == oldKids[0].getKeysOut()
                        myChild = copy.deepcopy(self)
                        myChild *= child
                        newKids.append(myChild)
                    self *= oldKids[0]
                    subkeys = oldKids[0].getKeysOut()
                    # Compute first-born child
                    newKids.insert(0,self)
                    for index in range(len(oldKids)):
                        prob = other.children[oldKids[index]]
                        substates = newKids[index].substate(subkeys)
                        if len(substates) > 1:
                            substate = newKids[index].collapse(substates)
                        else:
                            substate = next(iter(substates))
                        if index == 0:
                            for vector in self.distributions[substate].domain():
                                self.distributions[substate][vector] *= prob
                            mySubstate = substate
                        else:
                            toCollapse = (subkeys,set())
                            while len(toCollapse[0]) + len(toCollapse[1]) > 0:
                                mySubstates = self.substate(toCollapse[1]|\
                                                            set(self.distributions[mySubstate].keys()))
                                if len(mySubstates) > 1:
                                    mySubstate = self.collapse(mySubstates,False)
                                else:
                                    mySubstate = next(iter(mySubstates))
                                substates = newKids[index].substate(toCollapse[0]|set(newKids[index].distributions[substate].keys()))
                                if len(substates) > 1:
                                    substate = newKids[index].collapse(substates,False)
                                else:
                                    substate = next(iter(substates))
                                toCollapse = ({k for k in self.distributions[mySubstate].keys() \
                                               if k != keys.CONSTANT and \
                                               not k in newKids[index].distributions[substate].keys()},
                                              {k for k in newKids[index].distributions[substate].keys() \
                                               if k != keys.CONSTANT and \
                                               not k in self.distributions[mySubstate].keys()})
                            distribution = newKids[index].distributions[substate]
                            for vector in distribution.domain():
                                self.distributions[mySubstate].addProb(vector,distribution[vector]*prob)
            else:
                # Evaluate the hyperplane and split the state
                branchKeys = set(other.branch.keys())-{keys.CONSTANT}
                substates = self.substate(branchKeys)
                if substates:
                    valSub = self.collapse(substates,False)
                else:
                    valSub = None
                assert len(other.branch.planes) == 1,'Currently unable to process conjunctive branches'
                if valSub is None:
                    vector = KeyedVector({k: self.distributions[self.keyMap[k]].first()[k] \
                                          for k in branchKeys})
                    vector[keys.CONSTANT] = 1.
                    self *= other.children[other.branch.evaluate(vector)]
                else:
                    assert len(other.branch.planes) == 1,'Unable to multiply by joint planes'
                    # Apply the test to this tree
                    self *= other.branch.planes[0][0]
                    valSub = self.keyMap[keys.VALUE]
                    states = {}
                    del self.keyMap[keys.VALUE]
                    # Iterate through possible test results
                    for vector in self.distributions[valSub].domain():
                        prob = self.distributions[valSub][vector]
                        del self.distributions[valSub][vector]
                        test = other.branch.evaluate(vector[keys.VALUE])
                        del vector[keys.VALUE]
                        if test not in states:
                            if states:
                                states[test] = copy.deepcopy(self)
                                states[test].distributions[valSub].clear()
                            else:
                                states[test] = self
                                first = test
                        if len(vector) > 1:
                            states[test].distributions[valSub].addProb(vector,prob)
                    assert states,'Empty result of multiplication'
                    if len(self.distributions[valSub].domain()) == 0:
                        del self.distributions[valSub]
                    self *= other.children[first]
                    for key in other.getKeysOut():
                        assert key in self.keyMap
                    for test,state in states.items():
                        if state is not self:
                            newKeys = set(other.getKeysOut())
                            assert len(state.distributions[valSub].domain()) > 0
                            state *= other.children[test]
                            substates = state.substate(other.children[test].keys(),True)
                            if substates:
                                newSub = state.collapse(substates,False)
                            newSub = self.update(state,newKeys|branchKeys)
        elif isinstance(other,KeyedVector):
            substates = self.substate(other)
            self.collapse(substates)
            destination = self.findUncertainty(substates)
            if destination is None:
                destination = len(self.distributions)
                while destination in self.distributions:
                    destination -= 1
#                destination = max(self.keyMap.values())+1
            total = 0.
            for key in other:
                if key != keys.CONSTANT and self.keyMap[key] != destination:
                    # Certain value for this key
                    marginal = self.marginal(key)
                    total += other[key]*next(iter(marginal.domain()))
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
#        for s in self.distributions:
#            assert s in self.keyMap.values(),'%d: %s' % (s,';'.join(['%s: %d' % (k,self.keyMap[k]) for k in self.distributions[s].keys() if k != keys.CONSTANT]))
#        for k,s in self.keyMap.items():
#            if k != keys.CONSTANT:
#                assert s in self.distributions,'Substate %s of %s is missing' % (s,k)
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
#            for s in self.distributions:
#                assert s in self.keyMap.values(),self.distributions[s]
#            for k,s in self.keyMap.items():
#                if k != keys.CONSTANT:
#                    assert s in self.distributions
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
                elif len(vector) == 1:
                    assert next(iter(vector.keys())) == keys.CONSTANT
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
                    elif len(vector) == 1:
                        assert next(iter(vector.keys())) == keys.CONSTANT
            assert now in self.keyMap
            assert self.keyMap[now] in self.distributions,now
        for s in self.distributions:
            assert s in self.keyMap.values(),'Distribution %s is missing\n%s' % (s,self.distributions[s])
            for k in self.distributions[s].keys():
                assert not keys.isFuture(k),'Future key %s persists after rollback' \
                    % (k)
        for k,s in self.keyMap.items():
            if k != keys.CONSTANT:
                assert s in self.distributions,'%s: %s' % (k,s)
            assert not keys.isFuture(k)

    def simpleRollback(self,futures):
        # Make the future the present
        for key in futures:
            future = keys.makeFuture(key)
            oldstate = self.keyMap[key]
            newstate = self.keyMap[future]
            dist = self.distributions[newstate]
            if oldstate == newstate:
                for vector in dist.domain():
                    prob = dist[vector]
                    del dist[vector]
                    vector[key] = vector[future]
                    del vector[future]
                    dist.addProb(vector,prob)
            elif len(dist) > 1:
                # New value is probabilistic, not a single value, so update old value across possible worlds
                for vector in dist.domain():
                    prob = dist[vector]
                    del dist[vector]
                    vector[key] = vector[future]
                    del vector[future]
                    dist[vector] = prob
                self.keyMap[key] = newstate
                # Remove old state values
                dist = self.distributions[oldstate]
                if len(dist.first()) > 2:
                    # Other variables still remain
                    for vector in dist.domain():
                        prob = dist[vector]
                        del dist[vector]
                        del vector[key]
                        dist.addProb(vector,prob)
                else:
                    del self.distributions[oldstate]
            else:
                vector = dist.first()
                value = vector[future]
                del dist[vector]
                del vector[future]
                if len(vector) > 1:
                    dist[vector] = 1.
                else:
                    del self.distributions[newstate]
                dist = self.distributions[oldstate]
                for vector in dist.domain():
                    prob = dist[vector]
                    del dist[vector]
                    vector[key] = value
                    dist.addProb(vector,prob)
            del self.keyMap[future]

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
            if not label is None:
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
                    self.distributions[substate] = distribution
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

    def copySubset(self,ignore=None,include=None):
        result = self.__class__()
        if include is None:
            if ignore is None:
                return self.__deepcopy__({})
            else:
                keySubset = {k for k in self.keys() if not k in ignore}
        elif ignore is None:
            keySubset = include
        else:
            raise RuntimeError('Use either ignore or include sets, but not both')
        for key in keySubset:
            if not key in result:
                distribution = self.distributions[self.keyMap[key]]
                substate = len(result.distributions)
                result.distributions[substate] = distribution.__class__()
                intersection = [k for k in distribution.keys() if k in keySubset]
                for subkey in intersection:
                    result.keyMap[subkey] = substate
                newDist = {}
                for vector in distribution.domain():
                    newValues = {subkey: vector[subkey] for subkey in intersection}
                    newValues[keys.CONSTANT] = 1.
                    newVector = vector.__class__(newValues)
                    newDist[newVector] = distribution[vector]+newDist.get(newVector,0.)
                result.distributions[substate] = VectorDistribution(newDist)
        return result
                    
    def verifyIntegrity(self,sumToOne=False):
        for key in self.keys():
            assert self.keyMap[key] in self.distributions,'Distribution %s missing for key %s' % \
                (self.keyMap[key],key)
            distribution = self.distributions[self.keyMap[key]]
            for vector in distribution.domain():
                assert key in vector,'Key %s is missing from vector\n%s\nProb: %d%%' % \
                    (key,vector,distribution[vector]*100)
                for other in vector:
                    assert other == keys.CONSTANT or self.keyMap[other] == self.keyMap[key] ,\
                        'Unmapped key %s is in vector\n\%s' % (other,vector)
            if sumToOne:
                assert (sum(distribution.values())-1.)<.000001,'Distribution sums to %4.2f' % \
                    (sum(distribution.values()))
            else:
                assert sum(distribution.values())<1.000001,'Distribution sums to %4.2f' % \
                    (sum(distribution.values()))
