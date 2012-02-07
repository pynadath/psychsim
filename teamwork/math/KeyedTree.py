from ThespianKeys import makeBelongKey
from matrices import Hyperplane,DecisionTree,epsilon
from Keys import IdentityKey,RelationshipKey,ConstantKey,ClassKey,StateKey,keyConstant,makeIdentityKey
from KeyedVector import KeyedVector,TrueRow,IdentityRow
from KeyedMatrix import KeyedMatrix
from probability import Distribution
from teamwork.utils.FriendlyFloat import *

class KeyedPlane(Hyperplane):
    """A L{Hyperplane} alternative that stores the weights as a L{KeyedVector}, rather than as a list/array.  The interface is identical to that of the L{Hyperplane} superclass, except that the array arguments should be in dictionary (not list/array) form
    @ivar weights: the slope of this plane
    @type weights: L{KeyedVector}
    @ivar threshold: the offset of this plane
    @type threshold: float
    @ivar relation: the relation against this plane.  Default is >, alternatives are: =.
    @type relation: str
    """

    def __init__(self,weights,threshold,relation=None):
        """Constructs a hyperplane whose slope is determined by the given weights (in dictionary or L{KeyedVector} form) and whose intercept is defined by threshold (i.e., C{weights*x == threshold})
        @type weights: dict
        @warning: you should start passing in C{weights} in L{KeyedVector} form, because the handling of C{dict} arguments will likely be deprecated
        """
        if isinstance(weights,dict):
            Hyperplane.__init__(self,KeyedVector(weights),threshold,relation)
        else:
            Hyperplane.__init__(self,weights,threshold,relation)
        # No need to have a constant factor on the weights; simply shift intercept
        if self.weights.has_key(keyConstant):
            self.threshold -= self.weights[keyConstant]
            self.weights[keyConstant] = 0.
    
    def simpleThreshold(self,threshold='default'):
        """
        @return: a pretty string representation of the threshold"""
        if threshold == 'default':
            threshold = self.threshold
        return simpleFloat(threshold)

    def test(self,value):
        """
        @return: C{True} iff the passed in value (in dictionary form) lies above this hyperplane (C{self.weights*value > self.threshold})
        @rtype: bool"""
        total = self.weights * value
        if self.relation is None or self.relation == '>':
            return total > self.threshold
        elif self.relation == '=':
            return abs(total - self.threshold) < epsilon
        else:
            raise UserWarning,'Unknown hyperplane test: %s' % (self.relation)

    def testIntervals(self,intervals):
        """
        Computes the 'probability' that a point in this region will satisfy this plane.  In reality, just a coarse measure of volume.
        @param intervals: a list of dictionaries, each with:
           - weights: the slope of the bounding planes (L{KeyedVector})
           - lo: the low value for this interval (int)
           - hi: the high value for this interval (int)
        @return: a dictionary of probability values over C{True} and C{False} (although not a real L{Distribution} object)
        @rtype: boolS{->}float
        """
        result = {True:0.,False:0.}
        for interval in intervals:
            diff = sum(abs(self.weights.getArray()-
                           interval['weights'].getArray()))
            if diff < epsilon:
                # Interval along same slope as this plane
                span = interval['hi'] - interval['lo']
                if span < epsilon:
                    # Point
                    result[self.test(interval['lo'])] = 1.
                else:
                    # Interval of nonzero length
                    if interval['hi'] <= self.threshold:
                        # Never true
                        result[False] = 1.
                    elif interval['lo'] > self.threshold:
                        # Always true
                        result[True] = 1.
                    else:
                        # lo <= threshold < hi
                        result[True] = (interval['hi']-self.threshold)/span
                        result[False] = 1. - result[True]
                break
        else:
            # No interval along same slope as this plane
            # WARNING: the following is simple, but coarse
            result[True] = (1.-self.threshold)/2.
            result[False] = 1. - result[True]
        assert result[True] > -epsilon
        assert result[False] > -epsilon
        assert abs(result[True]+result[False]-1.) < epsilon
        return result
    
    def always(self,negative=True,probability=False):
        """
        @return: C{True} iff this plane eliminates none of the state space (i.e., for all q, w*q > theta).  C{False} iff this plane eliminates all of the state space (i.e., for all q, w*q <= theta).
        @rtype: boolean
        @param probability: if C{True}, then assume that weights are nonnegative and sum to 1 (default is C{False})
        @param negative: if C{True}, then assume that weights may be negative (default is C{True})
        @warning: guaranteed to hold only within unit hypercube"""
        if probability and len(self.weights) == 2 and \
               abs(self.threshold) < epsilon:
            # tuple with nonnegative values that sum to 1
            key1,key2 = self.weights.keys()
            numerator = -self.weights[key2]
            denominator = self.weights[key1] - self.weights[key2]
            if abs(denominator) < epsilon:
                # 0 > -b?
                return 0. > numerator
            else:
                threshold  = numerator/denominator
            if denominator > 0.:
                # x > theta
                if threshold < 0.:
                    # x >= 0 is always true
                    return True
                elif threshold >= 1.:
                    # x > 1 is never true
                    return False
            else:
                # x < theta
                if threshold <= 0.:
                    # x < 0 is never true
                    return False
                elif threshold > 1.:
                    # x <= 1 is always true
                    return True
            return None
        # Compute the biggest and smallest possible value of w*x
        if negative:
            hi = 0.
            for key in self.weights.keys():
                hi += abs(self.weights[key])
            lo = -hi
        else:
            # Assume we're testing a probability
            hi = max([0]+self.weights.getArray())
            lo = min([0]+self.weights.getArray())
        if lo > self.threshold:
            # If smallest possible value exceeds threshold, then always will
            return True
        elif hi <= self.threshold:
            # If largest possible value doesn't exceed threshold, then never
            return False
        else:
            return None

    def isZero(self):
        """
        @return: C{True} iff this plane has zero weights and a zero threshold
        @rtype: bool
        """
        if abs(self.threshold) > epsilon:
            return False
        else:
            for weight in self.weights.getArray():
                if abs(weight) > epsilon:
                    return False
            else:
                return True
            
    def keys(self):
        """
        @return: the keys used by the weight vector of this plane
        @rtype: L{Key}[]"""
        return self.weights.keys()
    
    def __neg__(self):
        return KeyedPlane(-self.weights,self.threshold)
        
    def __eq__(self,other):
        if self.weights == other.weights:
            return abs(self.threshold-other.threshold) < epsilon
        else:
            return None

    def __ge__(self,other):
        return self == other or self > other

    def __le__(self,other):
        return self == other or self < other

    def compare(self,other,negative=True):
        """Modified version of __cmp__ method
        @return:
           - 'less': C{self < other}, i.e., for all C{x}, if C{not self.test(x)}, then C{not other.test(x)}
           - 'greater': C{self > other}, i.e., for all C{x}, if C{self.test(x)}, then C{other.test(x)}
           - 'equal': C{self == other}, i.e., for all C{x}, C{self.test(x) == other.test(x)}
           - 'inverse': C{self == not other}, i.e., for all C{x}, C{self.test(x) != other.test(x)}
           - 'indeterminate': none of the above
        @rtype: str
        @param negative: if C{True}, then assume that weights may be negative (default is C{True})
        """
        if self.weights._frozen and other.weights._frozen:
            # Try to normalize
            myArray = self.weights.getArray()
            yrArray = other.weights.getArray()
            myThresh = self.threshold
            yrThresh = other.threshold
            if negative:
                try:
                    scaling = min(filter(lambda w:w>epsilon,map(abs,myArray)))
                except ValueError:
                    scaling = 1.
                try:
                    myArray = myArray/scaling
                    myThresh /= scaling
                except ZeroDivisionError:
                    pass
                try:
                    scaling = min(filter(lambda w:w>epsilon,map(abs,yrArray)))
                except ValueError:
                    scaling = 1.
                try:
                    yrArray = yrArray/scaling
                    yrThresh /= scaling
                except ZeroDivisionError:
                    pass
##             scaling = 
##             for index in range(len(myArray)):
##                 if abs(myArray[index]) > epsilon and abs(yrArray[index]) > epsilon:
##                     scaling = abs(myArray[index]/yrArray[index])
##                     break
##             else:
##                 # Second array is 0
##                 scaling = 1.
##             yrArray = yrArray * (scaling)
            # Test for inverse first
            diff = sum(abs(myArray+yrArray))
            if diff < epsilon and abs(myThresh+yrThresh) < epsilon:
                return 'inverse'
            # Standard comparison
            diff = sum(abs(myArray-yrArray))
            if diff < epsilon:
                if abs(myThresh-yrThresh) < epsilon:
                    return 'equal'
                elif yrThresh > myThresh:
                    # Harder to satisfy other
                    return 'less'
                else:
                    # Harder to satisfy me
                    return 'greater'
            hi = lo = yrThresh - yrThresh
            if negative:
                hi += diff
            else:
                hi += max([0]+(myArray-yrArray))
            if negative:
                lo -= diff
            else:
                lo += min([0]+(myArray-yrArray))
            if hi > 0.:
                if lo < 0.:
                    return 'indeterminate'
                else:
                    return 'less'
            elif lo < 0.:
                return 'greater'
            else:
                return 'equal'
        else:
            hi = lo = other.threshold - self.threshold
            for key,myValue in self.weights.items():
                try:
                    yrValue = other.weights[key]
                except KeyError:
                    yrValue = 0.
                diff = abs(myValue-yrValue)
                hi += diff
                lo -= diff
                if hi > 0.:
                    if lo < 0.:
                        return 'indeterminate'
            for key,yrValue in other.weights.items():
                try:
                    myValue = self.weights[key]
                except KeyError:
                    myValue = 0.
                diff = abs(myValue-yrValue)
                hi += diff
                lo -= diff
                if hi > 0.:
                    if lo < 0.:
                        return 'indeterminate'
            if hi > 0.:
                return 'less'
            elif lo < 0.:
                return 'greater'
            else:
                return 'equal'

    def __sub__(self,other):
        """Slightly unorthodox subtraction
        @return: a tuple (lo,hi) representing the min/max that the difference between these two planes will be on the unit hypercube"""
        diff = self.weights.getArray() - other.weights.getArray()
        hi = lo = 0.
        for value in diff:
            hi += abs(value)
            lo += -abs(value)
        hi -= self.threshold - other.threshold
        lo -= self.threshold - other.threshold
        return lo,hi

    def instantiate(self,table,weights=None):
        if weights is None:
            weights = self.weights.instantiate(table)
            if isinstance(weights,list):
                results = []
                for entry in weights:
                    results.append({'plane': self.instantiate(entry['table'],entry['row']),
                                    'table': entry['table']})
                return results
        if isinstance(self.threshold,str):
            threshold = float(table[self.threshold])
        else:
            threshold = self.threshold
        if weights is None:
            # Null hyperplane
            if 0. > threshold:
                return 1
            else:
                return -1
        if len(weights.keys()) > 1:
            return self.__class__(weights,threshold,self.relation)
        else:
            try:
                key = weights.keys()[0]
            except IndexError:
                return -1
            if key == keyConstant:
                if weights[key] > threshold:
                    return 1
                else:
                    return -1
            elif sum(map(abs,weights.getArray())) < epsilon:
                if 0. > threshold:
                    return 1
                else:
                    return -1
            else:
                return self.__class__(weights,threshold,self.relation)
        
    def instantiateKeys(self,table):
        self.weights.instantiateKeys(table)
        if isinstance(self.threshold,str):
            self.threshold = float(table[self.threshold])
        if len(self.weights.keys()) > 1:
            return 0
        else:
            try:
                key = self.weights.keys()[0]
            except IndexError:
                return -1
            if key == keyConstant:
                if self.weights[key] > self.threshold:
                    return 1
                else:
                    return -1
            else:
                return 0

    def simpleText(self,numbers=True,all=False):
        """
        @param numbers: if C{True}, floats are used to represent the threshold; otherwise, an automatically generated English representation (defaults to C{False})
        @type numbers: boolean
        @return: a user-friendly string representation of this hyperplane
        @rtype: str
        """
        if isinstance(self.weights,TrueRow):
            # Null row, nothing else to do
            return self.weights.simpleText()
        elif len(self.weights) == 1:
            # aX > theta
            key,weight = self.weights.items()[0]
            if isinstance(key,IdentityKey) or isinstance(key,ClassKey) \
                   or isinstance(key,RelationshipKey):
                if weight > 0:
                    return key.simpleText()
                else:
                    return 'not %s' % (key.simpleText())
            elif isinstance(key,ConstantKey):
                return 'False'
            else:
                try:
                    threshold = self.threshold/weight
                except ZeroDivisionError:
                    if self.threshold > -epsilon:
                        return 'False'
                    else:
                        return 'True'
                row = self.weights.keys()[0]
        else:
            row = self.weights.simpleText()
            threshold = self.threshold
            weight = 1.
        if self.relation is None:
            if numbers:
                condition = '> %5.3f' % (threshold)
            else:
                level = self.simpleThreshold(threshold)
                if weight < 0:
                    # Less than threshold (not greater than)
                    # e.g., convert from "medium or better" to "low or worse"
                    if abs(threshold) < epsilon:
                        condition = 'is negative'
                    else:
                        last = level
                        for index in getLevels():
                            label = levelStrings[index]
                            if level == label:
                                break
                            else:
                                last = label
                        level = last
                        condition = 'is no more than %5.3f' % (threshold)
    ##                     condition = 'is no more than %s' % (level)
                elif abs(threshold) < epsilon:
                    condition = 'is positive'
                else:
                    condition = 'is at least %5.3f' % (threshold)
    ##                 condition = 'is at least %s' % (level)
            content = '%s %s' % (row,condition)
        else:
            # No general representation for arbitrary tests
            content = row
        return content
        
class KeyedTree(DecisionTree):
    """A L{DecisionTree} that requires L{KeyedPlane} branches.
    @cvar planeClass: the L{Hyperplane} subclass used for the L{split} attribute
    @ivar keys: the cumulative list of keys used by all of the branches below"""
    planeClass = KeyedPlane

    def fill(self,keys,value=0.):
        """Fills in any missing slots with a default value
        @param keys: the slots that should be filled
        @type keys: list of L{Key} instances
        @param value: the default value (defaults to 0)
        @note: does not overwrite existing values"""
        if self.isLeaf():
            try:
                self.getValue().fill(keys,value)
            except AttributeError:
                # Leaf is keyless
                pass
        else:
            for plane in self.split:
                plane.weights.fill(keys,value)
            falseTree,trueTree = self.getValue()
            falseTree.fill(keys,value)
            trueTree.fill(keys,value)

    def keys(self):
        """
        @return: all keys used in this tree and all subtrees and leaves
        @rtype: C{L{Key}[]}
        """
        return self._keys().keys()

    def _keys(self):
        """Helper method for L{keys}
        @return: all keys used in this tree and all subtrees and leaves
        @rtype: C{dict:L{Key}S{->}boolean}
        """
        result = {}
        if self.isLeaf():
            value = self.getValue()
            if isinstance(value,KeyedVector):
                keyList = value.keys()
            elif isinstance(value,KeyedMatrix):
                keyList = value.rowKeys()+value.colKeys()
            else:
                keyList = []
            for key in keyList:
                result[key] = True
        else:
            for plane in self.split:
                if isinstance(plane,KeyedPlane):
                    for key in plane.weights.keys():
                        result[key] = True
            for child in self.children():
                result.update(child._keys())
        return result

    def freeze(self):
        """Locks in the dimensions and keys of all leaves"""
        if self.isLeaf():
            try:
                self.getValue().freeze()
            except AttributeError:
                # Not a keyed entity
                pass
        else:
            for plane in self.split:
                plane.weights.freeze()
            for child in self.children():
                child.freeze()

    def unfreeze(self):
        """Unlocks the dimensions and keys of all leaves"""
        if self.isLeaf():
            self.getValue().unfreeze()
        else:
            for plane in self.split:
                plane.weights.unfreeze()
            for child in self.children():
                child.unfreeze()
                
    def simpleText(self,printLeaves=True):
        """Returns a more readable string version of this tree
        @param printLeaves: optional flag indicating whether the leaves should also be converted into a user-friendly string
        @type printLeaves: C{boolean}
        @param numbers: if C{True}, floats are used to represent the threshold; otherwise, an automatically generated English representation (defaults to C{False})
        @type numbers: boolean
        @rtype: C{str}
        """
        if self.isLeaf():
            if printLeaves:
                value = self.getValue()
                if printLeaves is True:
                    try:
                        content = value.simpleText()
                    except AttributeError:
                        content = str(value)
                else:
                    content = printLeaves(value)
            else:
                content = '...'
        else:
            falseTree,trueTree = self.getValue()
            falseTree = falseTree.simpleText(printLeaves).replace('\n','\n\t')
            trueTree = trueTree.simpleText(printLeaves).replace('\n','\n\t')
            plane = ' and '.join(map(lambda p:p.simpleText(),self.split))
            content = 'if %s\n\tthen %s\n\telse %s' \
                       % (plane,trueTree,falseTree)
        return content

    def updateKeys(self):
        """Updates the record of contained keys in C{self.keys}"""
        self.keys = {}
        if self.isLeaf():
            node = self.getValue()
            if isinstance(node,KeyedVector):
                for key in node.keys():
                    self.keys[key] = 1
            elif isinstance(node,KeyedMatrix):
                for key1,value in node.items():
                    self.keys[key1] = 1
                    for key2 in value.keys():
                        self.keys[key2] = 1
        else:
            for plane in self.split:
                for key in plane.weights.keys():
                    try:
                        self.keys[key] += 1
                    except KeyError:
                        self.keys[key] = 1
            falseTree,trueTree = self.getValue()
            for key,count in falseTree.updateKeys().items():
                try:
                    self.keys[key] += count
                except KeyError:
                    self.keys[key] = count
            for key,count in trueTree.updateKeys().items():
                try:
                    self.keys[key] += count
                except KeyError:
                    self.keys[key] = count
        return self.keys

    def instantiate(self,table,branch=None):
        if self.isLeaf():
            if isinstance(self.getValue(),str) or \
                   isinstance(self.getValue(),bool):
                new = self.__class__(self.getValue())
            else:
                new = self.__class__(self.getValue().instantiate(table))
        else:
            if len(self.split) > 1:
                raise NotImplementedError,'Currently unable to instantiate trees with conjunction branches'
            if branch is None:
                branch = self.split[0].instantiate(table)
            falseTree,trueTree = self.getValue()
            if not isinstance(branch,list):
                branch = [{'plane': branch, 'table': table}]
            assert len(branch) > 0
            first = True
            for entry in branch:
                falseTree = self.instantiateBranch(entry['table'],entry['plane'],falseTree,trueTree,first)
                first = False
            new = falseTree
        new.additive = self.additive
        return new
                
    def instantiateBranch(self,table,branch,falseTree,trueTree,instantiateFalse=True):
        """
        @param instantiateFalse: if C{True}, then instantiate C{falseTree}; otherwise, assume it is already instantiated
        @type instantiateFalse: bool
        """
        if not isinstance(branch,int):
            new = self.__class__()
            if instantiateFalse:
                falseTree = falseTree.instantiate(table)
            new.branch(branch,falseTree,trueTree.instantiate(table))
            return new
        elif branch > 0:
            # Ignore the False branch
            trueTree = trueTree.instantiate(table)
            if trueTree.isLeaf():
                new = self.__class__(trueTree.getValue())
            else:
                new = self.__class__()
                plane = trueTree.split
                falseTree,trueTree = trueTree.getValue()
                new.branch(plane,falseTree,trueTree)
        elif branch < 0:
            # Ignore the True branch
            if instantiateFalse:
                falseTree = falseTree.instantiate(table)
            if falseTree.isLeaf():
                new = self.__class__(falseTree.getValue())
            else:
                new = self.__class__()
                plane = falseTree.split
                falseTree,trueTree = falseTree.getValue()
                new.branch(plane,falseTree,trueTree)
        return new
        
    def instantiateKeys(self,table):
        """Replaces any key references by the values in the table"""
        self._instantiate(table)
        self.updateKeys()

    def _instantiate(self,table):
        if self.isLeaf():
            self.getValue().instantiateKeys(table)
        else:
            if len(self.split) > 1:
                raise NotImplementedError,'Currently unable to instantiate trees with conjunction branches'
            result = self.split[0].instantiateKeys(table)
            falseTree,trueTree = self.getValue()
            if result > 0:
                # Ignore the False branch
                trueTree.instantiateKeys(table)
                if trueTree.isLeaf():
                    self.makeLeaf(trueTree.getValue())
                else:
                    plane = trueTree.split
                    falseTree,trueTree = trueTree.getValue()
                    self.branch(plane,falseTree,trueTree)
            elif result < 0:
                # Ignore the True branch
                falseTree.instantiateKeys(table)
                if falseTree.isLeaf():
                    self.makeLeaf(falseTree.getValue())
                else:
                    plane = falseTree.split
                    falseTree,trueTree = falseTree.getValue()
                    self.branch(plane,falseTree,trueTree)
            else:
                falseTree.instantiateKeys(table)
                trueTree.instantiateKeys(table)

##     def __mul__(self,other):
##         result = self._multiply(other)
##         result.prune()
##         return result

    def _multiply(self,other,comparisons=None,conditions=[]):
        if comparisons is None:
            comparisons = {}
        result = self.__class__()
        if other.isLeaf():
            if self.isLeaf():
                try:
                    result.makeLeaf(self.getValue()*other.getValue())
                except TypeError:
                    # This is odd, but I think it works
                    result.makeLeaf(other.getValue()*self.getValue())
            else:
                falseTree,trueTree = self.getValue()
                new = []
                for plane in self.split:
                    vector = plane.weights * other.getValue()
                    new.append(plane.__class__(vector,plane.threshold,plane.test))
                    newF = falseTree._multiply(other,comparisons,
                                               conditions+[(new,False)])
                    newT = trueTree._multiply(other,comparisons,
                                              conditions+[(new,True)])
                result.branch(new,newF,newT,pruneF=False,pruneT=False)
        else:
            result = DecisionTree._multiply(self,other,comparisons,conditions)
        return result

    def scale(self,factor):
        """Scales all of the leaf nodes by the given float factor"""
        if self.isLeaf():
            self.makeLeaf(self.getValue()*factor)
        else:
            for subtree in self.children():
                subtree.scale(factor)
        return self
            
    def getKeys(self):
        """
        @return: a list of any keys used by at least one branch in this tree"""
        try:
            keyList = self.keys.keys()
        except AttributeError:
            keyList = self.updateKeys().keys()
        keyList.sort()
        return keyList

    def toNumeric(self):
        """
        @return: a string representation of the internal array representation
        @rtype: str
        """
        if self.isLeaf():
            return str(self.getValue().getArray())
        else:
            falseTree,trueTree = self.getValue()
            prefix = 'if '
            content = ''
            for plane in self.split:
                content += '%s %s*x > %f:\n' % \
                           (prefix,
                            str(plane.weights.getArray().transpose()),
                            plane.threshold)
                prefix = 'and '
            substring = trueTree.toNumeric()
            substring = substring.replace('\n','\n\t\t')
            content += '\tthen:\t%s\n' % (substring) 
            substring = falseTree.toNumeric()
            substring = substring.replace('\n','\n\t\t')
            content += '\telse:\t%s\n' % (substring)
            return content

    def pruneIdentities(self):
        """Replaces any identity matrices at the leaves of this tree with the number 1.
        @return: the number of identity matrices found
        @rtype: int
        """
        if self.isLeaf():
            if self.getValue().isIdentity():
                self.makeLeaf(1.)
                return 1
            else:
                return 0
        else:
            return sum(map(self.__class__.pruneIdentities,self.children()))

    def renameEntity(self,old,new):
        """
        @param old: the current name of the entity
        @param new: the new name of the entity
        @type old,new: str
        """
        if self.isLeaf():
            # Is there anything to do?  Right now, assume no
            pass
        else:
            for index in range(len(self.split)):
                # Update any refs to the old name in branches
                plane = self.split[index]
                newKeys = []
                for key in plane.weights.specialKeys:
                    newKey = {}
                    newKey.update(key)
                    if isinstance(key,StateKey) and key['entity'] == old:
                        newKey['entity'] = new
                    elif isinstance(key,ClassKey) and key['value'] == old:
                        newKey['value'] = new
                    newKeys.append(newKey)
                newPlane = plane.weights.__class__(keys=newKeys)
                self.split[index] = KeyedPlane(newPlane,plane.threshold)
            # Recurse
            for child in self.children():
                child.renameEntity(old,new)

    def __getitem__(self,index):
        if isinstance(index,list):
            # Intervals
            if self.isLeaf():
                return Distribution({self.getValue():1.})
            else:
                prob = 1.
                for plane in self.split:
                    prob *= plane.testIntervals(index)[True]
                falseTree,trueTree = self.getValue()
                # True
                result = trueTree[index]
                for key,value in result.items():
                    result[key] *= prob
                # False
                for key,value in falseTree[index].items():
                    try:
                        result[key] += value*(1.-prob)
                    except KeyError:
                        result[key] = value*(1.-prob)
                for key,value in result.items():
                    if value < epsilon:
                        del result[key]
                return result
        else:
            return DecisionTree.__getitem__(self,index)
        
def makeIdentityPlane(key):
    return KeyedPlane(IdentityRow(keys=[makeIdentityKey(key)]),0.5)

def makeBelongPlane(key):
    return KeyedPlane(KeyedVector({makeBelongKey(key):1.}),0.5)

if __name__ == '__main__':
    from KeyedVector import EqualRow
    plane1 = KeyedPlane(EqualRow(keys=[{'entity':'object','feature':'x'},
                                       {'entity':'actor','feature':'x'}]),0.)
    print plane1
