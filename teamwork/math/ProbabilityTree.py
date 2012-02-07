"""Defines the layer of probabilistic branches over L{KeyedTree}"""
from xml.dom.minidom import Document,parseString
import copy

from matrices import DecisionTree
from Keys import Key,ConstantKey,StateKey,keyConstant
from probability import Distribution
from KeyedVector import KeyedVector,ANDRow,ORRow
from KeyedMatrix import KeyedMatrix,IdentityMatrix
from KeyedTree import KeyedPlane,KeyedTree

class ProbabilityTree(KeyedTree):
    """A decision tree that supports probabilistic branches

    If this node is I{not} a probabilistic branch, then identical to a L{KeyedTree} object.
    @cvar epsilon: minimum threshold to qualify as nonzero
    @type epsilon: float
    """

    epsilon = 1e-8
    def fill(self,keys,value=0.):
        """Fills in any missing slots with a default value
        @param keys: the slots that should be filled
        @type keys: list of L{Key} instances
        @param value: the default value (defaults to 0)
        @note: does not overwrite existing values"""
        if self.isProbabilistic():
            for subtree in self.children():
                try:
                    subtree.fill(keys,value)
                except AttributeError:
                    # Leaf is keyless
                    pass
        else:
            KeyedTree.fill(self,keys,value)

    def freeze(self):
        """Locks in the dimensions and keys of all leaves"""
        if self.isProbabilistic():
            for child in self.children():
                child.freeze()
        else:
            KeyedTree.freeze(self)

    def unfreeze(self):
        """Unocks in the dimensions and keys of all leaves"""
        if self.isProbabilistic():
            for child in self.children():
                child.unfreeze()
        else:
            KeyedTree.unfreeze(self)
            
    def isProbabilistic(self):
        """
        @return: true iff there's a probabilistic branch at this node
        @rtype: boolean"""
        return (not self.isLeaf()) and (self.branchType == 'probabilistic')
    
    def children(self):
        """
        @return: all child nodes of this node
        @rtype: L{ProbabilityTree}[]
        """
        if self.isProbabilistic():
            return self.split.domain()
        else:
            return KeyedTree.children(self)

    def branch(self,plane,falseTree=None,trueTree=None,
               pruneF=True,pruneT=True,prune=True,debug=False):
        """Same as C{L{KeyedTree}.branch}, except that plane can be a L{Distribution}
        @param plane: if a L{Hyperplane}, then the arguments are interpreted as for {L{KeyedTree}.branch} with; if a L{Distribution}, then the tree arguments are ignored
        @param prune: used (iff L{plane} is a L{Distribution}) to determine whether the given subtrees should be pruned
        @type prune: C{boolean}
        @type plane: L{Hyperplane}/L{Distribution}(L{ProbabilityTree})
        """
        if isinstance(plane,Distribution):
            self.branchType = 'probabilistic'
            self.split = plane
            self.falseTree = None
            self.trueTree = None
            for key,subtree in plane._domain.items():
                if isinstance(subtree,DecisionTree):
                    subtree.parent = (self,key)
            if prune:
                for subtree in self.children():
                    if isinstance(subtree,DecisionTree):
                        subtree.prune()
        else:
            KeyedTree.branch(self,plane,falseTree,trueTree,pruneF,pruneT,debug)

    def _merge(self,other,op,comparisons=None,conditions=[]):
        """Helper method that merges the two trees together using the given operator to combine leaf values, without pruning
        @param other: the other tree to merge with
        @type other: L{DecisionTree} instance
        @param op: the operator used to generate the new leaf values, C{lambda x,y:f(x,y)} where C{x} and C{y} are leaf values
        @rtype: a new L{DecisionTree} instance"""
        if comparisons is None:
            comparisons = {}
        if self.isProbabilistic():
            result = self.__class__()
            dist = {}
            for child,prob in self.split.items():
                newChild = child._merge(other,op,comparisons,conditions)
                if newChild.isProbabilistic():
                    # Collapse probabilistic branches together
                    for subchild,subprob in newChild.split.items():
                        try:
                            dist[subchild] += prob*subprob
                        except KeyError:
                            dist[subchild] = prob*subprob
                else:
                    # Probabilistic branch over nonprobabilistic children
                    try:
                        dist[newChild] += prob
                    except KeyError:
                        dist[newChild] = prob
            result.branch(Distribution(dist),prune=False)
            return result
        elif not self.isLeaf():
            return KeyedTree._merge(self,other,op,comparisons,conditions)
        elif other.isProbabilistic():
            result = self.__class__()
            dist = {}
            for child,prob in other.split.items():
                newChild = self._merge(child,op,comparisons,conditions)
                if newChild.isProbabilistic():
                    # Collapse probabilistic branches together
                    for subchild,subprob in newChild.split.items():
                        try:
                            dist[subchild] += prob*subprob
                        except KeyError:
                            dist[subchild] = prob*subprob
                else:
                    # Probabilistic branch over nonprobabilistic children
                    try:
                        dist[newChild] += prob
                    except KeyError:
                        dist[newChild] = prob
            result.branch(Distribution(dist),prune=False)
            return result
        else:
            return KeyedTree._merge(self,other,op,comparisons,conditions)
        
    def prune(self,comparisons=None,debug=False):
        if comparisons is None:
            comparisons = {}
        if self.isProbabilistic():
            for subtree in self.children():
                if isinstance(subtree,DecisionTree):
                    subtree.prune(comparisons,debug)
        else:
            KeyedTree.prune(self,comparisons,debug)

    def marginalize(self,key):
        """Marginalizes any distributions to remove the given key (not in place! returns the new tree)
        @param key: the key to marginalize over
        @return: a new L{ProbabilityTree} object representing the marginal function
        @note: no exception is raised if the key is not present"""
        result = self.__class__()
        if self.isProbabilistic():
            distribution = {}
            for element,prob in self.split.items():
                if isinstance(element,ProbabilityTree):
                    new = element.marginalize(key)
                else:
                    new = copy.deepcopy(element)
                    new.unfreeze()
                    try:
                        del new[key]
                    except KeyError:
                        pass
                try:
                    distribution[new] += prob
                except KeyError:
                    distribution[new] = prob
            result.branch(Distribution(distribution))
        elif self.isLeaf():
            new = copy.deepcopy(self.getValue())
            new.unfreeze()
            try:
                del new[key]
            except KeyError:
                pass
            result.makeLeaf(new)
        else:
            fTree,tTree = self.getValue()
            result.branch(self.split,fTree.marginalize(key),
                          tTree.marginalize(key))
        return result

    def condition(self,observation):
        result = self.__class__()
        if self.isProbabilistic():
            distribution = {}
            for element,prob in self.split.items():
                element = element.condition(observation)
                if element is not None:
                    try:
                        distribution[element] += prob
                    except KeyError:
                        distribution[element] = prob
            if len(distribution) == 0:
                result = None
            else:
                result.branch(Distribution(distribution))
        elif self.isLeaf():
            # Assuming that the leaf is a matrix
            matrix = self.getValue()
            assert(isinstance(matrix,KeyedMatrix))
            for rowKey in observation.keys():
                try:
                    row = matrix[rowKey]
                except KeyError:
                    row = {keyConstant:0.}
                # WARNING: this handles only SetToConstant rows!
                assert(isinstance(row,KeyedVector))
                for colKey,value in row.items():
                    if isinstance(colKey,ConstantKey):
                        if value != observation[rowKey]:
                            # Setting it to a different value
                            return None
                    else:
                        if abs(value) > self.epsilon:
                            # Adding it to something, kind of different
                            return None
            result.makeLeaf(matrix)
        else:
            fTree,tTree = self.getValue()
            fTree = fTree.condition(observation)
            tTree = tTree.condition(observation)
            if fTree is None:
                if tTree is None:
                    result = None
                else:
                    result = tTree
            elif tTree is None:
                result = fTree
            else:
                result.branch(self.split,fTree,tTree)
        return result

    def instantiate(self,table,branch=None):
        if self.isProbabilistic():
            new = self.__class__()
            new.branch(self.split.instantiate(table))
            return new
        else:
            return KeyedTree.instantiate(self,table)
            
    def instantiateKeys(self,values):
        if self.isProbabilistic():
            for subtree in self.children():
                subtree.instantiateKeys(values)
        else:
            return KeyedTree.instantiateKeys(self,values)

    def renameEntity(self,old,new):
        """
        @param old: the current name of the entity
        @param new: the new name of the entity
        @type old: str
        @type new: str
        """
        if self.isProbabilistic():
            for subtree in self.children():
                if isinstance(subtree,KeyedTree):
                    subtree.renameEntity(old,new)
        else:
            return KeyedTree.renameEntity(self,old,new)
        
    def generateAlternatives(self,index,value,test=None):
        if self.isProbabilistic():
            alternatives = []
            for subtree,prob in self.split.items():
                for alt in subtree.generateAlternatives(index,value,test):
                    try:
                        alt['probability'] *= prob
                    except KeyError:
                        alt['probability'] = prob
                    alternatives.append(alt)
            return alternatives
        elif isinstance(index,Distribution):
            alternatives = []
            for subIndex,prob in index.items():
                for alt in KeyedTree.generateAlternatives(self,subIndex,value,
                                                          test):
                    try:
                        alt['probability'] *= prob
                    except KeyError:
                        alt['probability'] = prob
                    alternatives.append(alt)
            return alternatives
        else:
            return KeyedTree.generateAlternatives(self,index,value,test)

    def simpleText(self,printLeaves=True):
        """Returns a more readable string version of this tree
        @param printLeaves: optional flag indicating whether the leaves should also be converted into a user-friendly string
        @type printLeaves: C{boolean}
        @rtype: C{str}
        """
        if self.isProbabilistic():
            content = ''
            for subtree,prob in self.split.items():
                substr = subtree.simpleText(printLeaves)
                content += '%s with probability %5.3f\n' % (substr,prob)
            return content
        else:
            return KeyedTree.simpleText(self,printLeaves)
                
    def updateKeys(self):
        if self.isProbabilistic():
            for subtree in self.children():
                subtree.updateKeys()
        else:
            KeyedTree.updateKeys(self)
        return self.keys

    def __getitem__(self,index):
        """
        @return: the distribution over leaf nodes for this value
        @rtype: L{Distribution}
        """
        if isinstance(index,Distribution):
            result = Distribution()
            for subIndex,prob in index.items():
                value = self[subIndex]
                if isinstance(value,Distribution):
                    for subValue,subProb in value.items():
                        try:
                            result[subValue] += prob*subProb
                        except KeyError:
                            result[subValue] = prob*subProb
                else:
                    # Update return distribution
                    try:
                        result[value] += prob
                    except KeyError:
                        result[value] = prob
        elif self.isProbabilistic():
            result = Distribution()
            for subtree,prob in self.split.items():
                if isinstance(subtree,DecisionTree):
                    value = subtree[index]
                else:
                    value = subtree
                if isinstance(value,Distribution):
                    for subValue,subProb in value.items():
                        try:
                            result[subValue] += subProb*prob
                        except KeyError:
                            result[subValue] = subProb*prob
                else:
                    try:
                        result[value] += prob
                    except KeyError:
                        result[value] = prob
        else:
            result = KeyedTree.__getitem__(self,index)
        # <HACK>
        # By default, matrices use a cruder (but faster) string rep, so there will likely be duplicate matrix entries that need to be consolidated
        if isinstance(result,Distribution) and len(result) > 0 \
               and isinstance(result.domain()[0],KeyedMatrix):
            for value,prob in result.items():
                for other in result.domain():
                    if value is not other:
                        if other.simpleText() == value.simpleText():
                            result[other] += prob
                            del result[value]
                            break
        # </HACK>
        return result

    def _multiply(self,other,comparisons=None,conditions=[]):
        if comparisons is None:
            comparisons = {}
        if self.isProbabilistic():
            if other.isProbabilistic():
                result = self.__class__()
                distribution = {}
                for myChild,myProb in self.split.items():
                    for yrChild,yrProb in other.split.items():
                        new = myChild._multiply(yrChild,comparisons,conditions)
                        try:
                            distribution[new] += myProb*yrProb
                        except KeyError:
                            distribution[new] = myProb*yrProb
                result.branch(Distribution(distribution))
                return result
            else:
                result = self.__class__()
                distribution = {}
                for myChild,myProb in self.split.items():
                    new = myChild._multiply(other,comparisons,conditions)
                    try:
                        distribution[new] += myProb
                    except KeyError:
                        distribution[new] = myProb
                result.branch(Distribution(distribution))
                return result
        elif isinstance(other,Distribution):
            distribution = {}
            for yrChild,yrProb in other.items():
                new = self._multiply(yrChild,comparisons,conditions)
                if isinstance(new,Distribution):
                    for new,myProb in new.items():
                        try:
                            distribution[new] += myProb*yrProb
                        except KeyError:
                            distribution[new] = myProb*yrProb
                else:
                    try:
                        distribution[new] += yrProb
                    except KeyError:
                        distribution[new] = yrProb
            return Distribution(distribution)
        elif isinstance(other,KeyedVector):
            return self[other]*other
        elif other.isProbabilistic():
            result = self.__class__()
            distribution = {}
            for yrChild,yrProb in other.split.items():
                new = self._multiply(yrChild,comparisons,conditions)
                try:
                    distribution[new] += yrProb
                except KeyError:
                    distribution[new] = yrProb
            result.branch(Distribution(distribution))
            return result
        else:
            return KeyedTree._multiply(self,other,comparisons,conditions)

    def __str__(self):
        return self.simpleText(printLeaves=True)
    
    def __xml__(self):
        if self.isProbabilistic():
            doc = Document()
            root = doc.createElement('tree')
            doc.appendChild(root)
            root.setAttribute('type','probabilistic')
            root.appendChild(self.split.__xml__().documentElement)
            return doc
        else:
            return KeyedTree.__xml__(self)

    def parse(self,element,valueClass=None,debug=False):
        """Extracts the tree from the given XML element
        @param element: The XML Element object specifying the plane
        @type element: Element
        @param valueClass: The class used to generate the leaf values
        @return: the L{ProbabilityTree} instance"""
        if not valueClass:
            valueClass = KeyedMatrix
        if element.getAttribute('type') == 'probabilistic':
            # This branch is a distribution over subtrees
            split = Distribution()
            split.parse(element.firstChild,ProbabilityTree)
            self.branch(split,pruneT=False,pruneF=False,prune=False)
        else:
            # This is a leaf or deterministic branch
            KeyedTree.parse(self,element,valueClass,debug)
        return self
            
def createBranchTree(plane,falseTree,trueTree):
    """Shorthand for constructing a decision tree with a single branch in it
    @param plane: the plane to branch on
    @type plane: L{Hyperplane}
    @param falseTree: the tree that will be followed if the plane tests C{False}
    @param trueTree: the tree that will be followed if the plane tests C{True}
    @type falseTree: L{ProbabilityTree}
    @type trueTree: L{ProbabilityTree}
    @note: Will not prune tree
    """
    tree = ProbabilityTree()
    tree.branch(plane,falseTree,trueTree,pruneF=False,pruneT=False)
    return tree

def createNodeTree(node=None):
    """Shorthand for constructing a leaf node with the given value"""
    tree = ProbabilityTree()
    tree.makeLeaf(node)
    return tree
    
def createEqualTree(plane,equalTree,unequalTree):
    """Shorthand for constructing a decision tree that branches on
    whether the value lies on the plane or not, with the former/latter
    cases leading down to the given equalTree/unequalTree"""
    subPlane = copy.copy(plane)
    subPlane.threshold -= 2.*ProbabilityTree.epsilon
    subTree = createBranchTree(subPlane,unequalTree,equalTree)
    tree = createBranchTree(plane,subTree,unequalTree)
    return tree

def createDynamicNode(feature,weights):
    """Shorthand for constructing a leaf node with a dynamics matrix
    for the given key with the specified weights (either KeyedVector, or
    just plain old dictionary, for the lazy)"""
    if isinstance(feature,Key):
        key = feature
    else:
        key = StateKey({'entity':'self','feature':feature})
    if isinstance(weights,KeyedVector):
        matrix = KeyedMatrix({key:weights})
    else:
        matrix = KeyedMatrix({key:KeyedVector(weights)})
    return createNodeTree(matrix)

def createANDTree(keyWeights,falseTree,trueTree):
    """
    To create a tree that follows the C{True} branch iff both the actor has accepted and the negotiation is not terminated:

    >>> tree = createANDTree([(StateKey({'entity':'actor','feature':'accepted'}),True), (StateKey({'entity':'self','feature':'terminated'}),False)], falseTree, trueTree)
    
    @note: the default truth value of the plane is C{True} (i.e., if no keys are provided, then C{trueTree} is returned
    @param keyWeights: a list of tuples, C{(key,True/False)}, of the preconditions for the test to be true
    @type keyWeights: (L{Key},boolean)[]
    @param falseTree: the tree to invoke if the conjunction evaluates to C{False}
    @param trueTree: the tree to invoke if the conjunction evaluates to C{True}
    @type falseTree: L{DecisionTree}
    @type trueTree: L{DecisionTree}
    @return: the new tree with the conjunction test at the root
    @rtype: L{ProbabilityTree}
    """
    if len(keyWeights) == 0:
        return trueTree
    weights = {} 
    length = float(len(keyWeights))
    for key,truth in keyWeights:
        if truth:
            weights[key] = 1./length
        else:
            weights[key] = -1./length
            try:
                weights[keyConstant] += 1./length
            except KeyError:
                weights[keyConstant] = 1./length
    weights = ANDRow(args=weights,keys=map(lambda t:t[0],keyWeights))
    plane = KeyedPlane(weights,1.-1/(2.*length))
    return createBranchTree(plane,falseTree,trueTree)

def createORTree(keyWeights,falseTree,trueTree):
    """
    To create a tree that follows the C{True} branch iff either the actor has accepted or the negotiation is not terminated:

    >>> tree = createORTree([(StateKey({'entity':'actor','feature':'accepted'}),True), (StateKey({'entity':'self','feature':'terminated'}),False)], falseTree, trueTree)
    
    @note: the default truth value of the plane is C{False} (i.e., if no keys are provided, then C{falseTree} is returned
    @param keyWeights: a list of tuples, C{(key,True/False)}, of the preconditions for the test to be true
    @type keyWeights: (L{Key},boolean)[]
    @param falseTree: the tree to invoke if the conjunction evaluates to C{False}
    @param trueTree: the tree to invoke if the conjunction evaluates to C{True}
    @type falseTree: L{DecisionTree}
    @type trueTree: L{DecisionTree}
    @return: the new tree with the conjunction test at the root
    @rtype: L{ProbabilityTree}
    """
    if len(keyWeights) == 0:
        return falseTree
    weights = ORRow(keys=map(lambda t:t[0],keyWeights))
    length = float(len(keyWeights))
    for key,truth in keyWeights:
        if truth:
            weights[key] = 1./length
        else:
            weights[key] = -1./length
            try:
                weights[keyConstant] += 1./length
            except KeyError:
                weights[keyConstant] = 1./length
    plane = KeyedPlane(weights,1/(2.*length))
    return createBranchTree(plane,falseTree,trueTree)

def identityTree(feature):
    """Creates a decision tree that will leave the given feature unchanged
    @param feature: the state feature whose dynamics we are creating
    @type feature: C{str}/L{Key}
    @rtype: L{ProbabilityTree}
    """
    return ProbabilityTree(IdentityMatrix(feature))

if __name__ == '__main__':
    f = open('/tmp/pynadath/tree.xml')
    data = f.read()
    f.close()
    doc = parseString(data)
    tree = ProbabilityTree()
    tree.parse(doc.documentElement)
    print tree.simpleText()

##     from unittest import TestResult
##     import sys
##     from teamwork.test.math.testKeyedPlane import TestKeyedPlane
##     if len(sys.argv) > 1:
##         method = sys.argv[1]
##     else:
##         method = 'testANDPlane'
##     case = TestKeyedPlane(method)
##     result = TestResult()
##     case(result)
##     for failure in result.errors+result.failures:
##         print failure[1]
