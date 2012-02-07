"""Base classes for piecewise linearity
@var __CONSTANT__: flag indicating whether a constant factor should be included in each vector
@type __CONSTANT__: boolean
@var epsilon: margin of error used in comparison
@type epsilon: float
"""
import copy
##try:
##    from numarray.numarrayall import *
##except ImportError:
##    pass
from types import *
from rules import pruneRules
from xml.dom.minidom import *
from id3 import gain
from dtree import create_decision_tree
import time

__CONSTANT__ = 1

epsilon = 0.00001
    
class Hyperplane:
    """A structure to represent linear separations on an I{n}-dimensional space
    @ivar weights: the slope of this plane
    @type weights: L{KeyedVector}
    @ivar threshold: the offset of this plane
    @type threshold: float
    @ivar relation: the relation against this plane.  Default is >, alternatives are: =.
    @type relation: str
    """
    
    def __init__(self,weights,threshold,relation=None):
        """Constructs a hyperplane weights*x == threshold
        @param weights: the slope of the hyperplane
        @type weights: list or array
        @param threshold: the intercept of this hyperplane
        @type threshold: float"""
        self._string = None
        if type(weights) is ListType:
            try:
                self.weights = array(weights)
            except TypeError,e:
                print 'Weights:',weights
                raise TypeError,e
        else:
            self.weights = weights
        self.threshold = threshold
        self.relation = relation

    def getWeights(self):
        """Return the slope of this hyperplane"""
        if __CONSTANT__:
            return self.weights[:len(self.weights)-1]
        else:
            return self.weights
        
    def getConstant(self):
        if __CONSTANT__:
            return self.weights[len(self.weights)-1]
        else:
            return 0.
        
    def test(self,value):
        """Returns true iff the passed in value (in array form) lies
        above this hyperplane (self.weights*value > self.threshold)
        @rtype: boolean"""
        total = dot(self.weights,value)
        if self.relation is None or self.relation == '>':
            return total > self.threshold
        elif self.relation == '=':
            return abs(total - self.threshold) < epsilon
        else:
            raise UserWarning,'Unknown hyperplane test: %s' % (self.relation)

    def always(self):
        """
        @return:
           - True: iff this plane eliminates none of the state space (i.e., for all q, w*q > theta).
           - False: iff this plane eliminates all of the state space (i.e., for all q, w*q <= theta).
           - None: otherwise
        @rtype: boolean
        @warning: This has not yet been implemented for this class"""
        raise NotImplementedError

    def compare(self,other):
        """Modified version of __cmp__ method
        @return:
           - 'less': self < other
           - 'greater': self > other
           - 'equal': self == other
           - 'indeterminate': none of the above
        @rtype: str
        """
        if self == other:
            return 'equal'
        elif self < other:
            return 'less'
        elif self > other:
            return 'greater'
        else:
            return 'indeterminate'

    def __str__(self):
        return '%s ? %5.3f' % (str(self.weights),self.threshold)

##     def __str__(self):
##         if self._string is None:
##             self._string = self.__str__()
##         return self._string
    
    def __neg__(self):
        return self.__class__(self.weights*-1.,self.threshold)

    def inverse(self):
        """
        Creates a plane exactly opposite to this one.  In other words, for all C{x}, C{self.test[x]} implies C{not self.inverse().test[x]}
        @rtype: L{Hyperplane}
        """
        return self.__class__(-self.weights,-self.threshold)
        
##    def __cmp__(self,other):
##        if sum(self.weights != other.weights) > 0:
##            return 0
##        else:
##            return self.threshold.__cmp__(other.threshold)

    def __gt__(self,other):
        if sum(self.getWeights() > other.getWeights()) > 0:
            # One of our weights is greater than the other's
            return 0
        else:
            diff = (self.threshold - self.getConstant()) \
                   - (other.threshold - other.getConstant())
            if sum(self.getWeights() < other.getWeights()) > 0:
                # One weight strictly greater
                return diff > -epsilon
            else:
                # No weights strictly greater, so constant factor must be
                return diff > 0.0

    def __lt__(self,other):
        if sum(self.getWeights() < other.getWeights()) > 0:
            # One of our weights is less than the other's
            return 0
        else:
            diff = (self.threshold - self.getConstant()) \
                   - (other.threshold - other.getConstant())
            if sum(self.getWeights() > other.getWeights()) > 0:
                # One weight strictly greater
                return diff < epsilon
            else:
                # No weights strictly greater, so constant factor must be
                return diff < 0.0
    
    def __eq__(self,other):
        return self.compare(other) == 'equal'
##         return sum(self.weights != other.weights) == 0 \
##                and abs(self.threshold-other.threshold) < epsilon

    def __getitem__(self,index):
        return self.weights[index]
    
    def __setitem__(self,index,value):
        self.weights[index] = value
    
    def __copy__(self):
        return self.__class__(copy.copy(self.weights),self.threshold,self.relation)

    def __deepcopy__(self,memo):
        weights = copy.deepcopy(self.weights,memo)
        memo[id(self.weights)] = weights
        return self.__class__(weights,self.threshold,self.relation)
    
    def __xml__(self):
        doc = Document()
        root = doc.createElement('plane')
        doc.appendChild(root)
        root.setAttribute('threshold',str(self.threshold))
        if self.relation:
            root.setAttribute('relation',self.relation)
        root.appendChild(self.weights.__xml__().documentElement)
        return doc

    def parse(self,element):
        """Extracts the plane from the given XML element
        @param element: The XML Element object specifying the plane
        @type element: Element
        @return: the L{Hyperplane} instance"""
        self.threshold = float(element.getAttribute('threshold'))
        self.relation = str(element.getAttribute('relation'))
        if not self.relation:
            self.relation = None
        nodes = element.getElementsByTagName('vector')
        self.weights = self.weights.parse(nodes[0])
        # Patch bug in writing EqualRow?
        if self.weights.__class__.__name__ == 'KeyedVector':
            nodes[0].setAttribute('type','Equal')
            self.weights = self.weights.parse(nodes[0])
        return self
    
class DecisionTree:
    """Represents a decision tree with hyperplane branches that divide
    an n-dimensional space, and unrestricted values stored at the leaf
    nodes (e.g., matrices for dynamics, actions for policies, etc.)
    @cvar planeClass: the class used to instantiate the branches
    @cvar checkTautology: flag that, if C{True}, activates check for hyperplanes that are either always C{True} or always C{False} in L{branch}.  This can lead to smaller trees, but decreases efficiency
    @type checkTautology: bool
    @cvar checkPrune: flag that, if C{True}, activates the L{prune} method.  This will lead to much smaller trees, but increases the overhead required to check for pruneability
    @type checkPrune: bool
    @ivar additive: if C{True}, then should be combined additively with other decision trees (default is C{True})
    @type additive: bool
    """
    planeClass = Hyperplane
    checkTautology = False
    checkPrune = True
    
    def __init__(self,value=None):
        """Creates a DecisionTree
        @param value: the optional leaf node value"""
        self.additive = True
        self.parent = None
        self.stats = {}
        self.makeLeaf(value)

    def makeLeaf(self,value):
        """Marks this tree as a leaf node
        @param value: the new value of this leaf node"""
        self.branchType = None
        self.split = []
        while isinstance(value,DecisionTree):
            value = value.getValue()
        self.falseTree = value
        self.trueTree = None
    
    def getValue(self):
        """
        @return: the value of this tree
           - If a leaf node, as a single object
           - If a branch, as a tuple (falseTree,trueTree)"""
        if self.isLeaf():
            return self.falseTree
        else:
            return (self.falseTree,self.trueTree)

    def isLeaf(self):
        """
        @return: C{True} iff this tree is a leaf node
        @rtype: boolean"""
        if len(self.split) > 0:
            return False
        else:
            return True

    def children(self):
        """
        @return: all subtrees rooted at this node
        @rtype: list of L{DecisionTree} instances"""
        if self.isLeaf():
            return []
        else:
            falseTree,trueTree = self.getValue()
            return [trueTree,falseTree]

    def leaves(self):
        """
        @return: list of all leaf values (not necessarily unique) from L to R
        @note: the leaf value is the result of calling L{getValue}, not an actual L{DecisionTree} instance
        """
        if self.isLeaf():
            return [self.getValue()]
        else:
            leaves = []
            for child in self.children():
                leaves += child.leaves()
            return leaves

    def leafNodes(self):
        """
        @return: list of all leaf nodes (not necessarily unique) from L to R
        @rtype: L{DecisionTree}[]
        """
        if self.isLeaf():
            return [self]
        else:
            leaves = []
            for child in self.children():
                leaves += child.leafNodes()
            return leaves

    def depth(self):
        """
        @return: the maximum distance between this node and the leaf nodes of the tree rooted at this node (a leaf node has a depth of 0, a branch node with two leaf nodes as children has a depth of 1, etc.)
        @rtype: int
        """
        if self.isLeaf():
            return 0
        else:
            return 1+max(map(lambda c:c.depth(),self.children()))
        
    def branches(self,result=None):
        """
        @return: all branches (not necessarily unique)
        @rtype: intS{->}L{Hyperplane}
        """
        if result is None:
            result = {}
        if not self.isLeaf():
            if isinstance(self.split,list):
                for plane in self.split:
                    result[id(plane)] = plane
            else:
                assert(not isinstance(self.split,Hyperplane))
                result[id(self.split)] = self.split
            for child in self.children():
                result.update(child.branches(result))
        return result
    
    def branch(self,plane,falseTree,trueTree,pruneF=True,pruneT=True,debug=False):
        """Marks this tree as a deterministic branching node
        @param plane: the branchpoint(s) separating the C{False} and C{True} subtrees
        @type plane: L{Hyperplane} or L{Hyperplane}[]
        @param falseTree: the C{False} subtree
        @type falseTree: L{DecisionTree} instance
        @param trueTree: the C{True} subtree
        @type trueTree: L{DecisionTree} instance
        @param pruneF: if true, will L{prune} the C{False} subtree
        @type pruneF: bool
        @param pruneT: if true, will L{prune} the C{True} subtree
        @type pruneT: bool
        @param debug: if C{True}, some debugging statements will be written to stdout (default is C{False})
        @type debug: bool
        @note: setting either prune flag to false will save time (though may lead to more inefficient trees)"""
        self.branchType = 'deterministic'
        if isinstance(plane,list):
            self.split = plane
        else:
            self.split = [plane]
        if self.checkTautology:
            # Check whether these conditions are always true
            always = None
            for plane in self.split[:]:
                value = plane.always()
                if value == False:
                    # A single False value makes the whole condition False
                    always = value
                    break
                elif value == True:
                    # If always True, remove from conjunction
                    self.split.remove(plane)
            if len(self.split) == 0:
                # Always True, so the False subtree is irrelevant
                if isinstance(trueTree,DecisionTree):
                    if trueTree.isLeaf():
                        self.makeLeaf(trueTree.getValue())
                    else:
                        newFalse,newTrue = trueTree.getValue()
                        self.branch(trueTree.split,newFalse,newTrue,
                                    pruneF=False,pruneT=False,debug=debug)
                else:
                    self.makeLeaf(trueTree)
                return
            elif always == False:
                # the True subtree is irrelevant
                if isinstance(falseTree,DecisionTree):
                    if falseTree.isLeaf():
                        self.makeLeaf(falseTree.getValue())
                    else:
                        newFalse,newTrue = falseTree.getValue()
                        self.branch(falseTree.split,newFalse,newTrue,
                                    pruneF=False,pruneT=False,debug=debug)
                else:
                    self.makeLeaf(falseTree)
                return
        # Create False subtree
        if isinstance(falseTree,DecisionTree):
            self.falseTree = falseTree
        else:
            self.falseTree = self.__class__()
            self.falseTree.makeLeaf(falseTree)
        # Create True subtree
        if isinstance(trueTree,DecisionTree):
            self.trueTree = trueTree
        else:
            self.trueTree = self.__class__()
            self.trueTree.makeLeaf(trueTree)
        self.falseTree.parent = (self,False)
        self.trueTree.parent = (self,True)
        if pruneF:
            self.falseTree.prune(debug=debug)
        if pruneT:
            self.trueTree.prune(debug=debug)

    def getPath(self):
        """
        @return: the conditions under which this node will be reached, as a list of C{(plane,True/False)} tuples
        @rtype: (L{Hyperplane},boolean)[]
        """
        if self.parent:
            parent,side = self.parent
            return [(parent.split,side)] + parent.getPath()
        else:
            return []
        
    def createIndex(self,start=0):
        self.stats['index'] = start
        if not self.isLeaf():
            falseTree,trueTree = self.getValue()
            # Initialize statistics, if not already done
            if not falseTree.stats.has_key('leaf'):
                self.count()
            falseTree.createIndex(start)
            trueTree.createIndex(start+falseTree.stats['leaf'])

    def removeTautologies(self,negative=True):
        if not self.isLeaf():
            truth = True # Assume True if no branches
            for plane in self.split:
                truth = plane.always(negative)
                if isinstance(truth,bool):
                    break
            if truth is True:
                # Only need true tree
                fTree,tTree = self.getValue()
                tTree.removeTautologies()
                if tTree.isLeaf():
                    self.makeLeaf(tTree.getValue())
                else:
                    fNew,tNew = tTree.getValue()
                    self.branch(tTree.split,fNew,tNew,
                                pruneF=False,pruneT=False)
            elif truth is False:
                # Only need false tree
                fTree,tTree = self.getValue()
                fTree.removeTautologies()
                if fTree.isLeaf():
                    self.makeLeaf(fTree.getValue())
                else:
                    fNew,tNew = fTree.getValue()
                    self.branch(fTree.split,fNew,tNew,
                                pruneF=False,pruneT=False)
                    
    def prune(self,comparisons=None,debug=False,negative=True):
        if not self.checkPrune:
            return
        if comparisons is None:
            comparisons = {}
        if not self.isLeaf():
            ancestor = self.parent
            split = self.split
            if debug:
                print
                print 'Current:'
                print ' and '.join(map(lambda p:p.simpleText(),split))
                print len(self.leaves())
            while ancestor:
                parent,side = self.parent
                tree,direction = ancestor
                if debug:
                    print 'Ancestor:',len(tree.split)
##                     print ' and '.join(map(lambda p:p.simpleText(),tree.split))
                    print 'Side:',direction
                if isinstance(tree.split,Hyperplane):
                    split = comparePlaneSets(split,tree.split,direction,comparisons,debug,negative)
                    if debug:
                        print 'Result:',
                        if isinstance(split,bool):
                            print split
                        else:
                            print ' and '.join(map(lambda p:p.simpleText(),split))
                    if isinstance(split,bool):
                        oldFalse,oldTrue = parent.getValue()
                        newFalse,newTrue = self.getValue()
                        if split:
                            # The conjunction has degenerated to always be True
                            oldFalse,oldTrue = parent.getValue()
                            newFalse,newTrue = self.getValue()
                            if side:
                                parent.branch(parent.split,oldFalse,newTrue,
                                              pruneF=False,pruneT=True,debug=debug)
                            else:
                                parent.branch(parent.split,newTrue,oldTrue,
                                              pruneF=True,pruneT=False,debug=debug)
                        else:
                            # We're already guaranteed to be False
                            if side:
                                parent.branch(parent.split,oldFalse,newFalse,
                                              pruneF=False,pruneT=True,debug=debug)
                            else:
                                parent.branch(parent.split,newFalse,oldTrue,
                                              pruneF=True,pruneT=False,debug=debug)
                        break
                ancestor = tree.parent
            else:
                self.split = split
                self.falseTree.prune(comparisons,debug)
                self.trueTree.prune(comparisons,debug)
            # Check whether pruning has reduced T/F to be identical
            falseTree,trueTree = self.getValue()
            if falseTree == trueTree:
                if debug:
                    print 'Equal subtrees:',falseTree,trueTree
                if falseTree.isLeaf():
                    self.makeLeaf(falseTree)
                else:
                    newFalse,newTrue = falseTree.getValue()
                    self.branch(falseTree.split,newFalse,newTrue,
                                pruneF=False,pruneT=False,debug=debug)

    def count(self):
        """
        @return: a dictionary of statistics about the decision tree rooted at this node:
           - I{leaf}: # of leaves
           - I{branch}: # of branch nodes
           - I{depth}: depth of tree"""
        if self.isLeaf():
            self.stats['leaf'] = 1
            self.stats['branch'] = 0
            self.stats['depth'] = 0
            return self.stats
        else:
            self.stats['leaf'] = 0
            self.stats['branch'] = 1
            self.stats['depth'] = 1
            depth = 0
            for tree in self.children():
                subCount = tree.count()
                for key in ['leaf','branch']:
                    self.stats[key] += subCount[key]
                if subCount['depth'] > depth:
                    depth = subCount['depth']
            self.stats['depth'] += depth
            return self.stats

    def rebalance(self,debug=False):
        """
        Uses ID3 heuristic to reorder branches
        @return: C{True}, iff a rebalancing was applied at this level
        """
        target = '_value'
        attributes = {target:True}
        values = {}
        data = self.makeRules(attributes,values)
        new = create_decision_tree(data,attributes.keys(),target,gain)
        self._extractTree(new,attributes,values)
        return self

    def _extractTree(self,tree,attributes,values):
        """
        Extracts the rules from the given L{dtree} structure into this tree
        """
        if type(tree) == dict:
            plane = attributes[tree.keys()[0]]
            trueTree = None
            falseTree = None
            for item in tree.values()[0].keys():
                if item == True:
                    trueTree = self.__class__()
                    trueTree._extractTree(tree.values()[0][item],
                                          attributes,values)
                elif item == False:
                    falseTree = self.__class__()
                    falseTree._extractTree(tree.values()[0][item],
                                           attributes,values)
                else:
                    raise UserWarning,'Unknown attribute value: %s' % \
                          (str(item))
            if trueTree is None:
                if falseTree is None:
                    raise UserWarning,'Null decision tree returned'
                else:
                    self.makeLeaf(falseTree)
            elif falseTree is None:
                self.makeLeaf(trueTree)
            else:
                if falseTree == trueTree:
                    raise UserWarning
                self.branch(plane,falseTree,trueTree,
                            pruneF=False,pruneT=False)
        else:
            self.makeLeaf(values[tree])
        return self
        
    def makeRules(self,attributes=None,values=None,conditions=None,
                  debug=False,comparisons=None):
        """Represents this tree as a list of rules
        @return: dict[]
        """
        if comparisons is None:
            comparisons = {}
        rules = []
        if attributes is None:
            attributes = {'_value':True}
        if values is None:
            values = {}
        if conditions is None:
            conditions = []
        if self.isLeaf():
            label = str(self.getValue())
            rule = {'_value':label}
            values[label] = self.getValue()
            for plane,side in conditions:
                rule[plane] = side
            rules.append(rule)
        else:
            falseTree,trueTree = self.getValue()
            newConditions = {}
            for plane in self.split:
                label = plane.simpleText()
                attributes[label] = plane
                newConditions[label] = plane
            # Determine rules when we branch False
            for plane in newConditions.keys():
                split = [newConditions[plane]]
                for oldPlane,side in conditions:
                    split = comparePlaneSets(split,[attributes[oldPlane]],
                                             side,comparisons)
                    if isinstance(split,bool):
                        if split:
                            # Guaranteed to be True, so no need to continue
                            break
                        else:
                            # Guaranteed to be False, so no need to add plane
                            rules += falseTree.makeRules(attributes,values,
                                                         conditions,
                                                         debug,comparisons)
                            break
                else:
                    # Must add this plane as extra condition
                    rules += falseTree.makeRules(attributes,values,
                                                 conditions+[(plane,False)],
                                                 debug,comparisons)
            # Determine rules when we branch True
            split = newConditions.values()
            for oldPlane,side in conditions:
                split = comparePlaneSets(split,[attributes[oldPlane]],
                                         side,comparisons)
                if isinstance(split,bool):
                    if split:
                        # Guaranteed to be True, so no need to add plane
                        rules += trueTree.makeRules(attributes,values,
                                                    conditions,
                                                    debug,comparisons)
                        break
                    else:
                        # Guaranteed to be False, so no need to add plane
                        break
            else:
                # Must add this plane as extra condition
                rules += trueTree.makeRules(attributes,values,
                                            conditions+map(lambda p:(p,True),
                                                           newConditions.keys()),
                                            debug,comparisons)
        # Once we've created all of the rules, fill in any missing
        # conditions on the left-hand sides
        if not self.parent:
            for rule in rules:
                for attr in attributes.keys():
                    if not rule.has_key(attr):
                        # Add a "wildcard"
                        rule[attr] = None
            if debug:
                print '\t\tPruning %s rules' % (len(rules))
            rules,attributes = pruneRules(rules,attributes,values,debug)
        return rules

    def fromRules(self,rules,attributes,values,comparisons=None):
        tree = self
        if comparisons is None:
            comparisons = {}
        for rule in rules[:-1]:
            split = []
            for attr,value in rule.items():
                if attr == '_value':
                    tTree = self.__class__()
                    tTree.makeLeaf(values[value])
                elif value == True:
                    split.append(attributes[attr])
                elif value == False:
                    split.append(attributes[attr].inverse())
            # Minimize branches in conjunction
            value = True
            while value is not None:
                value = None
                for index in range(len(split)):
                    result = comparePlaneSets([split[index]],
                                              split[:index]+split[index+1:],
                                              True,comparisons)
                    if isinstance(result,bool):
                        if result:
                            # This plane is redundant
                            del split[index]
                            value = True
                            break
                        else:
                            # This plane is in conflict with the others
                            value = False
                            break
                if value is False:
                    break
            else:
                fTree = self.__class__()
                fTree.makeLeaf(None)
                tree.branch(split,fTree,tTree)
                tree = fTree
        tree.makeLeaf(values[rules[-1]['_value']])
        return self
    
    def generateAlternatives(self,index,value,test=None):
        if not test:
            test = lambda x,y: x != y
        if self.isLeaf():
            myValue = self.getValue()
            if test(myValue,value):
                return [{'plane':None,'truth':1,'value':myValue}]
            else:
                # No alternative
                return []
        else:
            falseTree,trueTree = self.getValue()
            if reduce(lambda x,y:x and y,
                      map(lambda p:p.test(index),self.split)):
                # We are on the True side
                alternatives = trueTree.generateAlternatives(index,value)
                myValue = falseTree[index]
                for action in myValue:
                    if test(action,value):
                        # Here's a way to get a different value
                        for plane in self.split:
                            if plane.test(index):
                                alternatives.append({'plane':plane,
                                                     'truth':False,
                                                     'value':myValue})
                        break
            else:
                # We are on the False side
                alternatives = falseTree.generateAlternatives(index,value)
                myValue = trueTree[index]
                for action in myValue:
                    if test(action,value):
                        # Here's a way to get a different value
                        for plane in self.split:
                            if not plane.test(index):
                                alternatives.append({'plane':plane,
                                                     'truth':True,
                                                     'value':myValue})
                        break
            return alternatives
        
    def __getitem__(self,index):
        if type(index) is IntType:
            # Direct index into leaf node
            if not self.stats.has_key('index'):
                self.createIndex()
            if self.isLeaf():
                if self.stats['index'] == index:
                    return self
                else:
                    raise IndexError,index
            else:
                falseTree,trueTree = self.getValue()
                if index < falseTree.stats['index'] + falseTree.stats['leaf']:
                    return falseTree[index]
                else:
                    return trueTree[index]
        else:
            # Array type index into decision tree
            if self.isLeaf():
                return self.getValue()
            else:
                # All planes in branch must be true
                if reduce(lambda x,y:x and y,
                          map(lambda p:p.test(index),self.split)):
                    return self.trueTree[index]
                else:
                    return self.falseTree[index]

    def replace(self,orig,new,comparisons=None,conditions=[]):
        """Replaces any leaf nodes that match the given original value
        with the provided new value, followed by a pruning phase
        @param orig: leaf value to be replaced
        @param new: leaf value with which to replace
        @warning: the replacement modifies this tree in place"""
        if not isinstance(new,DecisionTree):
            raise NotImplementedError,'Currently unable to replace leaf nodes with non-tree objects'
        if comparisons is None:
            comparisons = {}
        if self.isLeaf():
            value = self.getValue()
            if isinstance(value,orig.__class__) and value == orig:
                if new.isLeaf():
                    self.makeLeaf(new.getValue())
                else:
                    falseTree,trueTree = new.getValue()
                    # Check whether this branch is relevant
                    split = new.split
                    for plane,truth in conditions:
                        split = comparePlaneSets(split,plane,truth,comparisons)
                        if isinstance(split,bool):
                            if split:
                                # Guaranteed True
                                return self.replace(orig,trueTree,comparisons,conditions)
                            else:
                                # Guaranteed False
                                return self.replace(orig,falseTree,comparisons,conditions)
                    # Merge the subtree branch
                    newFalse = self.__class__()
                    newFalse.makeLeaf(orig)
                    newFalse.replace(orig,falseTree,comparisons,conditions)
                    newTrue = self.__class__()
                    newTrue.makeLeaf(orig)
                    newTrue.replace(orig,trueTree,comparisons,conditions)
                    self.branch(split,newFalse,newTrue,pruneF=False,pruneT=False)
        else:
            # Copy the current tree
            falseTree,trueTree = self.getValue()
            falseTree.replace(orig,new,comparisons,conditions+[(self.split,False)])
            trueTree.replace(orig,new,comparisons,conditions+[(self.split,True)])
            self.branch(self.split,falseTree,trueTree,pruneF=False,pruneT=False)

    def merge(self,other,op):
        """Merges the two trees together using the given operator to combine leaf values
        @param other: the other tree to merge with
        @type other: L{DecisionTree} instance
        @param op: the operator used to generate the new leaf values, C{lambda x,y:f(x,y)} where C{x} and C{y} are leaf values
        @rtype: a new L{DecisionTree} instance"""
        result = self._merge(other,op)
        result.prune()
        return result

    def _merge(self,other,op,comparisons=None,conditions=[]):
        """Helper method that merges the two trees together using the given operator to combine leaf values, without pruning
        @param other: the other tree to merge with
        @type other: L{DecisionTree} instance
        @param op: the operator used to generate the new leaf values, C{lambda x,y:f(x,y)} where C{x} and C{y} are leaf values
        @rtype: a new L{DecisionTree} instance"""
        if comparisons is None:
            comparisons = {}
        result = self.__class__()
        if not self.isLeaf():
            falseTree,trueTree = self.getValue()
            falseTree = falseTree._merge(other,op,comparisons,conditions+[(self.split,False)])
            trueTree = trueTree._merge(other,op,comparisons,conditions+[(self.split,True)])
            result.branch(self.split,falseTree,trueTree,pruneF=False,pruneT=False)
        elif isinstance(other,DecisionTree):
            if other.isLeaf():
                result.makeLeaf(op(self.getValue(),other.getValue()))
            else:
                falseTree,trueTree = other.getValue()
                # Check whether this branch is relevant
                split = other.split
                for plane,truth in conditions:
                    split = comparePlaneSets(split,plane,truth,comparisons)
                    if isinstance(split,bool):
                        if split:
                            # Guaranteed True
                            return self._merge(trueTree,op,comparisons,conditions)
                        else:
                            # Guaranteed False
                            return self._merge(falseTree,op,comparisons,conditions)
                # Merge the subtree branch
                newFalse = self._merge(falseTree,op,comparisons,conditions)
                newTrue = self._merge(trueTree,op,comparisons,conditions)
                result.branch(split,newFalse,newTrue,
                              pruneF=False,pruneT=False)
        else:
            result.makeLeaf(op(self.getValue(),other))
        return result
        
    def __add__(self,other):
        return self.merge(other,lambda x,y:x+y)

    def __mul__(self,other):
        result = self._multiply(other)
        result.prune()
        return result

    def _multiply(self,other,comparisons=None,conditions=[]):
        if comparisons is None:
            comparisons = {}
        result = self.__class__()
        if other.isLeaf():
            if self.isLeaf():
                result.makeLeaf(matrixmultiply(self.getValue(),
                                               other.getValue()))
            else:
                falseTree,trueTree = self.getValue()
                new = []
                for original in self.split:
                    weights = matrixmultiply(original.weights,other.getValue())
                    plane = original.__class__(weights,original.threshold)
                    new.append(plane)
                result.branch(new,falseTree._multiply(other,comparisons,conditions+[(new,False)]),
                              trueTree._multiply(other,comparisons,conditions+[(new,True)]),
                              pruneF=False,pruneT=False)
        else:
            falseTree,trueTree = other.getValue()
            split = other.split
            # Check whether this branch is relevant
            for plane,truth in conditions:
                split = comparePlaneSets(split,plane,truth,comparisons)
                if isinstance(split,bool):
                    if split:
                        # Guaranteed True
                        return self._multiply(trueTree,comparisons,conditions)
                    else:
                        # Guaranteed False
                        return self._multiply(falseTree,comparisons,conditions)
            # Merge the subtree branch
            newFalse = self._multiply(falseTree,comparisons,conditions)
            newTrue = self._multiply(trueTree,comparisons,conditions)
            result.branch(split,newFalse,newTrue,pruneF=False,pruneT=False)
        return result

    def __sub__(self,other):
        return self + (-other)
    
    def __neg__(self):
        result = self.__class__()
        if self.isLeaf():
            result.makeLeaf(-self.getValue())
        else:
            result.branch(self.split,-self.falseTree,-self.trueTree,
                          pruneF=False,pruneT=False)
        return result

    def __eq__(self,other):
        if self.__class__ == other.__class__:
            if self.isLeaf() and other.isLeaf():
                return self.getValue() == other.getValue()
            elif not self.isLeaf() and not other.isLeaf():
                return (self.split == other.split) and \
                       (self.getValue() == other.getValue())
            else:
                return False
        else:
            return False

    def isAdditive(self):
        return self.additive

    def makeAdditive(self):
        self.additive = True
        for tree in self.children():
            tree.makeAdditive()

    def makeNonadditive(self):
        self.additive = False
        for tree in self.children():
            tree.makeNonadditive()

    def __hash__(self):
        return hash(str(self))
        
    def __str__(self):
        return self.simpleText()

    def __copy__(self):
        new = self.__class__()
        if self.isLeaf():
            new.makeLeaf(copy.copy(self.getValue()))
        else:
            falseTree,trueTree = self.getValue()
            new.branch(copy.copy(self.split),copy.copy(falseTree),
                       copy.copy(trueTree),0,0)
        return new

    def __xml__(self):
        doc = Document()
        root = doc.createElement('tree')
        root.setAttribute('additive',str(self.isAdditive()).lower())
        doc.appendChild(root)
        if self.isLeaf():
            root.setAttribute('type','leaf')
            value = self.getValue()
            try:
                root.appendChild(value.__xml__().documentElement)
            except AttributeError:
                # Floats, lists, strings, etc. all get converted into strings
                root.appendChild(doc.createTextNode(str(value)))
        else:
            root.setAttribute('type','branch')
            element = doc.createElement('split')
            root.appendChild(element)
            for plane in self.split:
                element.appendChild(plane.__xml__().documentElement)
            falseTree,trueTree = self.getValue()
            element = doc.createElement('false')
            root.appendChild(element)
            element.appendChild(falseTree.__xml__().documentElement)
            element = doc.createElement('true')
            root.appendChild(element)
            element.appendChild(trueTree.__xml__().documentElement)
        return doc

    def parse(self,element,valueClass=None,debug=False):
        """Extracts the tree from the given XML element
        @param element: The XML Element object specifying the plane
        @type element: Element
        @param valueClass: The class used to generate the leaf values
        @return: the L{KeyedTree} instance"""
        if element.getAttribute('type') == 'leaf':
            # Extract leaf value
            if not valueClass:
                valueClass = float
            node = element.firstChild
            while node:
                if node.nodeType == node.ELEMENT_NODE:
                    value = valueClass()
                    value = value.parse(node)
                    break
                elif node.nodeType == node.TEXT_NODE:
                    value = str(node.data).strip()
                    if len(value) > 0:
                        if value == 'None':
                            # Better hope that this wasn't intended to be a string
                            value = None
                        break
                node = node.nextSibling
            else:
                # Should this be an error?  No, be proud of your emptiness.
                value = None
##                 raise UserWarning,'Empty leaf node: %s' % (element.toxml())
            self.makeLeaf(value)
        else:
            # Extract plane, False, and True
            planes = []
            falseTree = self.__class__()
            trueTree = self.__class__()
            node = element.firstChild
            while node:
                if node.nodeType == node.ELEMENT_NODE:
                    if node.tagName == 'split':
                        subNode = node.firstChild
                        while subNode:
                            if subNode.nodeType == subNode.ELEMENT_NODE:
                                plane = self.planeClass({},0.)
                                planes.append(plane.parse(subNode))
                            subNode = subNode.nextSibling
                    elif node.tagName in ['false','left']:
                        subNode = node.firstChild
                        while subNode and subNode.nodeType != node.ELEMENT_NODE:
                            subNode = subNode.nextSibling
                        falseTree = falseTree.parse(subNode,valueClass,debug)
                    elif node.tagName in ['true','right']:
                        subNode = node.firstChild
                        while subNode and subNode.nodeType != node.ELEMENT_NODE:
                            subNode = subNode.nextSibling
                        trueTree = trueTree.parse(subNode,valueClass,debug)
                node = node.nextSibling
            self.branch(planes,falseTree,trueTree,
                        pruneF=False,pruneT=False,prune=False)
        if element.getAttribute('additive') == 'false':
            self.makeNonadditive()
        else:
            self.makeAdditive()
        return self

def printData(data,values=None):
    for datum in data:
        print '\n\t',
        for attr,val in datum.items():
            if attr != '_value':
                print '%5s' % (val),
        if values:
            print values.index(datum['_value']),pow(2,datum.values().count(None)),
    print


def comparePlaneSets(set1,set2,side,comparisons=None,
                     debug=False,negative=True):
    """
    Compares a conjunction of planes against a second conjunction of planes that has already been tested against.  It prunes the current conjunction based on any redundancy or inconsistency with the test
    @param set1: the plane set to be pruned
    @param set2: the plane set already tested
    @type set1: L{Hyperplane}[]
    @type set2: L{Hyperplane}[]
    @param side: the side of the second set that we're already guaranteed to be on
    @type side: boolean
    @return: The minimal set of planes in the first set that are not redundant given these a priori conditions (if guaranteed to be C{True} or C{False}, then the boolean value is returned)
    @rtype: L{Hyperplane}[]
    @param negative: if C{True}, then assume that weights may be negative (default is C{True}
    """
    hasher = id
    # Relevant planes so far
    planes = []
    mustBe = map(lambda p:None,set2)
    trueCount = 0
    # Compare this branch against parent branch
    for myPlane in set1:
        for yrIndex in range(len(set2)):
            yrPlane = set2[yrIndex]
            if isinstance(comparisons,dict):
                try:
                    result = comparisons[hasher(yrPlane)][hasher(myPlane)]
                except KeyError:
                    result = yrPlane.compare(myPlane,negative)
                    try:
                        comparisons[hasher(yrPlane)][hasher(myPlane)] = result
                    except KeyError:
                        comparisons[hasher(yrPlane)] = {hasher(myPlane):result}
            else:
                result = yrPlane.compare(myPlane,negative)
            if result == 'equal':
                # We need yrPlane to be True
                if side:
                    # All of set2 is True, so myPlane already guaranteed to be True
                    break
                else:
                    # At least one in set2 is False
                    if mustBe[yrIndex] is False:
                        # Oops, already asked yrPlane to be False
                        return False
                    elif not mustBe[yrIndex]:
                        mustBe[yrIndex] = True
                        trueCount += 1
                        if trueCount == len(set2):
                            # We require all of set2 to be True, but at least one's False
                            return False
            elif result == 'inverse':
                # We need yrPlane to be False
                if side:
                    # all of set2 is True
                    return False
                else:
                    # At least one in set2 is False
                    if mustBe[yrIndex]:
                        # Oops, already asked yrPlane to be True
                        return False
                    else:
                        mustBe[yrIndex] = False
            elif result == 'greater':
                if side:
                    # This plane is already guaranteed to be True
                    break
                else:
                    # We can't conclude anything about this plane
                    pass
            elif result == 'less':
                if side:
                    # We can't conclude anything about this plane
                    pass
                else:
                    # myPlane is False if yrPlane is False
                    if mustBe[yrIndex] is False:
                        # Oops, already asked yrPlane to be False
                        return False
                    elif not mustBe[yrIndex]:
                        mustBe[yrIndex] = True
                        trueCount += 1
                        if trueCount == len(set2):
                            # We require all of set2 to be True, but at least one's False
                            return False
            else:
                # No conclusive comparison
                pass
        else:
            # We didn't draw any conclusions about this plane
            planes.append(myPlane)
    if len(planes) == 0:
        return True
    else:
        return planes

def generateComparisons(set1,set2):
    """Pre-computes a comparison matrix between two sets of planes
    @param set1,set2: the two sets of planes
    @type set1: L{Hyperplane}[]
    @type set2: L{Hyperplane}[]
    @return: a pairwise matrix of comparisons, indexed by the C{id} of each plane, so that C{result[id(p1)][id(p2)] = p1.compare(p2)}
    @rtype: str{}{}
    """
    comparisons = {}
    for plane1 in set1:
        comparisons[id(plane1)] = {}
        for plane2 in set2:
            comparisons[id(plane1)][id(plane2)] = plane1.compare(plane2)
    return comparisons

if __name__ == '__main__':
    from ProbabilityTree import *
    import pickle
    f = open('/tmp/tree.pickle','r')
    tree = pickle.load(f)
    print len(tree.leaves()),'leaves'
    f.close()

    planes = {}
    nodes = [tree]
    while len(nodes) > 0:
        node = nodes.pop()
        if not node.isLeaf():
            for plane in node.split:
                planes[id(plane)] = plane
            nodes += node.children()
    print len(planes)

    comparisons = generateComparisons(planes.values(),planes.values())
    for plane1 in planes.values():
        assert(comparisons.has_key(id(plane1)))
        for plane2 in planes.values():
            assert(comparisons[id(plane1)].has_key(id(plane2)))
    from teamwork.utils.Debugger import quickProfile
    quickProfile(tree.prune,(comparisons,False))
    print len(tree.leaves())
