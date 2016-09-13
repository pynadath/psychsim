from xml.dom.minidom import Document
import psychsim.keys
import psychsim.probability
from psychsim.pwl import *

class MultiVectorDistribution:
    """
    Represents a distribution over independent state vectors, i.e., independent L{VectorDistribution}s
    """
    def __init__(self,node=None,empty=False):
        self.distributions = {}
        self.keyMap = {}
        if node:
            self.parse(node)
        elif not empty:
            self.distributions[0] = VectorDistribution({KeyedVector({psychsim.keys.CONSTANT: 1.}): 1.})

    def collapse(self,substates):
        """
        @rtype: L{VectorDistribution}
        """
        result = VectorDistribution({KeyedVector({psychsim.keys.CONSTANT: 1.}): 1.})
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
        if isinstance(obj,KeyedVector):
            return self.substate(obj.keys())
        elif isinstance(obj,KeyedPlane):
            return self.substate(obj.vector)
        elif isinstance(obj,KeyedMatrix):
            return self.substate(obj.getKeysIn() | obj.getKeysOut())
        elif isinstance(obj,list) or isinstance(obj,set):
            return {self.keyMap[psychsim.keys.makePresent(k)] for k in obj if k != psychsim.keys.CONSTANT}
        elif isinstance(obj,KeyedTree):
            if obj.isLeaf():
                return self.substate(obj.children[None])
            elif obj.isProbabilistic():
                substates = set()
                for child in obj.children.domain():
                    substates |= self.substate(child)
                return substates
            else:
                # Deterministic branch
                substates = self.substate(obj.branch)
                for child in obj.children.values():
                    substates |= self.substate(child)
                return substates
        else:
            raise TypeError("Unable to identify substate of %s:\n%s" % (obj.__class__.__name__,obj))

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
            self.distributions[substate] = VectorDistribution({KeyedVector({psychsim.keys.CONSTANT: 1.}): 1.})
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
        assert isinstance(other,self.__class__),'Currently unable to add %s instances to objects of another class' % (self.__class__.__name__)
        assert self.keyMap == other.keyMap,'Currently unable to add distributions with mismatched substates'
        result = self.__class__()
        result.keyMap.update(self.keyMap)
        for substate,value in self.distributions.items():
            result[substate] = value + other.distributions[substate]
        return result

    def __sub__(self,other):
        assert isinstance(other,self.__class__),'Currently unable to subtract %s instances to objects of another class' % (self.__class__.__name__)
        assert self.keyMap == other.keyMap,'Currently unable to subtract distributions with mismatched substates'
        result = self.__class__()
        result.keyMap.update(self.keyMap)
        for substate,value in self.distributions.items():
            result.distributions[substate] = value - other.distributions[substate]
        return result

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
                    if key != psychsim.keys.CONSTANT:
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
            treeMap[self.substate(tree)].append(tree)
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
