import copy
import cStringIO
import fileinput
from xml.dom.minidom import Document
from teamwork.action.PsychActions import Action
from teamwork.math.matrices import epsilon
from teamwork.math.KeyedVector import *
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.KeyedTree import KeyedPlane
from teamwork.math.probability import Distribution

class PWLTable:
    """Tabular representation of a PWL function, as an alternative to L{KeyedTree<teamwork.math.KeyedTree.KeyedTree>}
    @ivar rules: list of rules
    @ivar values: table of value function, in dictionary form, indexed by row number
    @type values: intS{->}dict
    @ivar attributes: the list of LHS conditions
    @type attributes: L{KeyedVector}[]
    @ivar _attributes: mapping from LHS condition to position in C{attributes} list
    @type _attributes: L{KeyedVector}S{->}int
    @ivar _consistency: table of cached consistency checks among attribute values
    @type _consistency: intS{->}intS{->}bool
    @ivar zeroPlanes: C{True} iff all of the attributes are hyperplanes through the origin
    @type zeroPlanes: bool
    """

    def __init__(self):
        self._attributes = {}
        self._consistency = {}
        self.reset()
        self.zeroPlanes = True

    def reset(self):
        """Clears all existing contents (including attributes) of the table"""
        self.attributes = []
        self.initialize(True)

    def initialize(self,resetRules=True):
        """Clears all existing contents (excluding attributes) of the table
        @param resetRules: if C{True} then delete any existing rules (default is C{True})
        @type resetRules: bool
        """
        self._attributes.clear()
        for index in range(len(self.attributes)):
            self._attributes[str(self.attributes[index][0].getArray())] = index
        self._consistency.clear()
        for obj,values in self.attributes:
            if len(values) != 1 or abs(values[0]) > epsilon:
                break
        else:
            self.zeroPlanes = True
        if resetRules:
            self.rules = [{'lhs': map(lambda a: None,self.attributes),
                           'rhs': None, 'values': {}}]

    def expandRules(self):
        """Generates rules for all possible LHS conditions by removing all wildcards
        """
        done = False
        while not done:
            done = True
            for index in range(len(self.rules)):
                rule = self.rules[index]
                for attr in range(len(self.attributes)):
                    if rule['lhs'][attr] is None:
                        # Wildcard to split along possible values
                        obj,values = self.attributes[attr]
                        done = False
                        rule['lhs'][attr] = 0
                        # Figure how many new rules to create
                        if isinstance(obj,KeyedVector):
                            size = len(values) + 1
                        else:
                            size = 2
                        for value in range(1,size):
                            # Create a new rule for other possible values for this attribute
                            newRule = {'lhs': rule['lhs'][:],
                                       'rhs': copy.copy(rule['rhs']),
                                       'values': {}}
                            newRule['lhs'][attr] = value
                            newRule['values'].update(rule['values'])
                            self.rules.append(newRule)
                        break
        self.rules.sort(lambda x,y: cmp(x['lhs'],y['lhs']))

    def addAttribute(self,obj,value):
        """Inserts the new attribute/value into the LHS conditions for this policy
        @param obj: the condition
        @param value: the test value
        @return: the index of the attribute
        @rtype: int
        """
        if abs(value) > epsilon:
            self.zeroPlanes = False
        new = False
        # Look for an existing test
        for index in range(len(self.attributes)):
            other,values = self.attributes[index]
            if obj == other:
                if not value in values:
                    values.append(value)
                    values.sort()
                break
            elif obj == -other:
                # Exact inverse of existing attribute
                if not value in values:
                    values.append(value)
                    values.sort()
                index -= len(self.attributes)
                break
        else:
            # New attribute, insert in order
            new = True
            for index in range(len(self.attributes)):
                if len(obj) == 2:
                    a,b = obj.getArray()
                    less = solveTuple(obj) < solveTuple(self.attributes[index][0])
                else:
                    less = list(obj.getArray()) < \
                               list(self.attributes[index][0].getArray())
                if less:
                    self.attributes.insert(index,(obj,[value]))
                    break
            else:
                self.attributes.append((obj,[value]))
                index = len(self.attributes)-1
        if new:
            # Update LHS to have the right dimension
            for rule in self.rules:
                rule['lhs'].insert(index,None)
        else:
            # Update LHS that already refer to this attribute
            for rule in self.rules[:]:
                if not rule['lhs'][index] is None:
                    if rule['lhs'][index] == values.index(value):
                        # New threshold splits this rule in two
                        newRule = {'lhs': rule['lhs'][:],
                                    'rhs': copy.copy(rule['rhs']),
                                    'values': {}}
                        newRule['lhs'][index] += 1
                        newRule['values'].update(rule['values'])
                        self.rules.append(newRule)
                    elif rule['lhs'][index] > values.index(value):
                        # Now above one more threshold
                        rule['lhs'][index] += 1
                    self.rules.sort(lambda x,y: cmp(x['lhs'],y['lhs']))
        return index

    def delAttribute(self,index):
        """Deletes the attribute in the given position and reorganizes the rules accordingly
        @warning: it does not do any clever aggregation over multiple rules that may be collapsed because of the deletion of this attribute, just deletes all but one of them
        @param index: the position of the attribute to be deleted within the list of attributes
        @type index: int
        """
        vector = self.attributes[index][0]
        del self._attributes[str(vector.getArray())]
        for pos in range(index+1,len(self.attributes)):
            self._attributes[str(self.attributes[pos][0].getArray())] -= 1
        del self.attributes[index]
        for rule in self.rules:
            del rule['lhs'][index]
        # Look for newly redundant rules
        for i in range(len(self.rules)-1):
            j = i+1
            while j < len(self.rules):
                if self.rules[i]['lhs'] == self.rules[j]['lhs']:
                    # Intelligent merging?  Not a chance!
                    del self.rules[j]
                else:
                    j += 1
        
    def index(self,state,observations={}):
        """
        @param state: the beliefs to use in identifying the appropriate rule
        @return: the rule index corresponding to the given beliefs
        @rtype: int
        """
        factors = self.getFactors(state,observations)
        return self.match(factors)

    def getFactors(self,state,observations={}):
        """
        @param state: the beliefs to use in identifying the appropriate rule
        @return: a list of factors indicating the LHS attribute values
        @rtype: int[]
        """
        if observations:
            raise NotImplementedError,'Direct testing of observations not currently supported'
        factors = []
        size = 1
        for index in range(len(self.attributes)):
            obj,values = self.attributes[index]
            if isinstance(obj,KeyedVector):
                # Determine which plane interval this state is in
                value = obj*state
            else:
                # Need to pick out observation
                try:
                    value = observations[obj.name]
                except KeyError:
                    value = None
            factors.append(self.subIndex(index,value))
        return factors
    
    def match(self,factors,multiple=False):
        """
        @param factors: the attribute value assignments, as indices in the domain of the corresponding attribute (C{None} is a wildcard)
        @type factors: int[]
        @param multiple: if C{True}, then return all possible matches; otherwise, return first match found (default is C{False})
        @type multiple: bool
        @return: identifies the rule index that matches the specified attribute values
        @rtype: int or int[]
        """
        if multiple:
            result = []
        for rule in range(len(self.rules)):
            lhs = self.rules[rule]['lhs']
            if not intersection(lhs,factors) is None:
                # Complete match
                if multiple:
                    result.append(rule)
                else:
                    return rule
        if multiple and result:
            # Found at least one match
            return result
        else:
            raise ValueError,'Unable to find rule match for %s' % (str(factors))

    def __getitem__(self,index):
        """Shortcut method, index is either an int (for directly indexing into the table) or a belief vector.  Can't incorporate observations.
        """
        if isinstance(index,int):
            rule = index
        else:
            if isinstance(index,Distribution):
                assert len(index) == 1
                index = index.domain()[0]
            rule = self.index(index,{})
        return self.rules[rule]

    def getRHS(self,state):
        """
        @return: the action specified by this table in the given state
        """
        rule = self.rules[self.index(state)]
        if rule['rhs']:
            return rule['rhs']
        elif isinstance(rule['values'],dict):
            print rule['values']
            raise NotImplementedError
        else:
            best = {}
            for entry in rule['values']:
                V = entry['V']*state
                if not best or V > best['ER']:
                    best.update(entry)
                    best['ER'] = V
            return best['rhs']

    def subIndex(self,attr,value):
        """
        Computes the index corresponding to the given value for the given attribute
        @param attr: the index of the attribute
        @type attr: int
        @param value: the actual value to determine the index of
        @rtype: int
        """
        obj,values = self.attributes[attr]
        if isinstance(obj,KeyedVector):
            for subIndex in range(len(values)):
                if value < values[subIndex]+epsilon:
                    return subIndex
            else:
                return len(values)
        else:
            try:
                return values.index(value)
            except KeyError:
                return 0

    def consistentp(self,assignment,subIndex=None):
        """Tests whether extending a partial LHS assignment with a
        given subIndex is self-consistent.  If C{subIndex} is omitted,
        checks the entire assignment for internal consistency.
        @type assignment: int[]
        @type subIndex: int
        @return: C{True} iff the sub-index is consistent with the current partial assignment
        @rtype: bool
        """
        if subIndex is None:
            for index in range(1,len(assignment)):
                if not assignment[index] is None:
                    if not self.consistentp(assignment[:index],assignment[index]):
                        return False
            else:
                return True
        else:
            newAttr,newVals = self.attributes[len(assignment)]
            for pos in range(len(assignment)):
                oldAttr,oldVals = self.attributes[pos]
                if detectConflict(oldAttr,assignment[pos],newAttr,subIndex):
                    return False
            else:
                return True

    def factored2index(self,factors,check=False):
        """
        Transforms a list of subindices into a list of matching rule indices
        @param check: if C{True}, then check consistency before returning indices (default is C{False})
        @type check: bool
        @note: subindex can be a list of subindices
        @type factors: int[]
        @rtype: int[]
        """
        # Start with a single empty attribute assignment
        old = [[]]
        # Iterate through each attribute
        for position in range(len(self.attributes)):
            obj,values = self.attributes[position]
            if isinstance(obj,KeyedVector):
                size = len(values) + 1
            else:
                size = len(values)
            # Iterate through indices generated so far
            new = []
            for assignment in old:
                if factors[position] is None:
                    # No constraint on this attribute value
                    possible = range(size)
                elif isinstance(factors[position],tuple):
                    # Attribute value is a interval
                    possible = range(factors[position][0],
                                     factors[position][1]+1)
                elif isinstance(factors[position],list):
                    # Attribute value is a set
                    possible = factors[position]
                else:
                    # Assume attribute value is a singleton
                    possible = [factors[position]]
                for subIndex in possible:
                    if not check or self.consistentp(assignment,subIndex):
                        new.append(assignment + [subIndex])
            old = new
        # Convert each assignment into an integer
        indices = []
        for assignment in old:
            index = 0
            for position in range(len(self.attributes)):
                obj,values = self.attributes[position]
                if isinstance(obj,KeyedVector):
                    size = len(values) + 1
                else:
                    size = len(values)
                index *= size
                index += assignment[position]
            indices.append(index)
        return indices
        

    def index2factored(self,index):
        """
        Transforms a rule index into a list of subindices
        @type index: int
        @rtype: int[]
        """
        factors = []
        for pos in range(len(self.attributes)):
            obj,values = self.attributes[-pos-1]
            if isinstance(obj,KeyedVector):
                size = len(values) + 1
            else:
                size = len(values)
            factors.insert(0,index % size)
            index /= size
        return factors
    
    def fromTree(self,tree):
        """Extract a tabular representation of the given PWL tree.  Updates this tree to represent the same PWL function as the given tree.
        @param tree: the tree to import
        @type tree: L{KeyedTree}
        """
        raise NotImplementedError,'Is this a real method?'
        self.reset()
        remaining = [tree]
        while remaining:
            node = remaining.pop()
            if not node.isLeaf():
                if not node.isProbabilistic():
                    for plane in node.split:
                        print plane
                        self.addAttribute(plane.weights,plane.threshold)
                remaining += node.children()
        for obj,values in self.attributes:
            print obj
            print values
        
    def getTable(self):
        """
        @return: the base table (stripped of any subclass extras)
        @rtype: L{PWLTable}
        """
        result = PWLTable()
        return self.copy(result)

    def _consistent(self,attr1,great1,attr2,great2=None,debug=False):
        """Compares an attribute-value pair against another (or others) to determine whether they're potentially consistent
        @type attr1: L{KeyedVector}
        @type attr2: L{KeyedVector} or (L{KeyedVector},bool)[]
        @type great1: bool
        @type great2: bool or None
        @return: C{False} if never consistent, C{True} if always consistent, C{None} otherwise
        """
        if isinstance(attr1,int) and isinstance(attr2,int):
            # Look for cached result
            cache1 = '%d,%d' % (attr1,int(great1))
            cache2 = '%d,%d' % (attr2,int(great2))
            try:
                table = self._consistency[cache1]
                try:
                    result = self._consistency[cache1][cache2]
                    if debug: print '\tCache hit:',result
                    return result
                except KeyError:
                    pass
            except KeyError:
                self._consistency[cache1] = {}
        else:
            cache1,cache2 = None,None
        if isinstance(attr1,int):
            attr1 = self.attributes[attr1][0]
        if isinstance(attr2,list):
            # Multiple attributes to test against each other
            value = None
            for pos in range(len(attr2)):
                # NOTE: switch order
                test = self._consistent(attr2[pos][0],attr2[pos][1],
                                        attr1,great1,debug)
                if debug: print '\t\t',test
                if test is False:
                    # If one is inconsistent, then whole thing is
                    return False
                elif test is True:
                    # Subsumed by another factor
                    value = True
            return value
        elif isinstance(attr2,int):
            attr2 = self.attributes[attr2][0]
        # Solve for first of two variables
        result = None
        if attr1 == attr2:
            # Exact match
            if debug: print '\t\tEqual'
            result = (great1 == great2)
        elif len(attr1) == 2:
            result = self._binaryConsistent(attr1,great1,attr2,great2,debug)
        elif great1 == great2:
            # Both planes in same direction
            if great1:
                # Must be above both planes
                result = True
                for key in attr1.keys():
                    if attr2[key] < attr1[key]:
                        # w1*q > 0 does *not* imply w2*q > 0
                        result = None
                        break
            else:
                # Must be below both planes
                result = True
                for key in attr1.keys():
                    if attr2[key] > attr1[key]:
                        # w1*q < 0 does *not* imply w2*q < 0
                        result = None
                        break
        if cache1:
            self._consistency[cache1][cache2] = result
        return result
            

    def _binaryConsistent(self,attr1,great1,attr2,great2,debug):
        """Version of _consistent for binary attribute vectors
        """
        result = None
        key1,key2 = attr1.keys()
        try:
            weight1 = - attr1[key2] / attr1[key1]
        except:
            raise NotImplementedError,'Unable to handle unary tests: %s' \
                % (str(attr1.getArray()))
        if attr1[key1] < 0.:
            great1 = not great1
        # Solve for first of two variables
        try:
            weight2 = - attr2[key2] / attr2[key1]
        except:
            raise NotImplementedError,'Unable to handle unary tests'
        if attr2[key1] < 0.:
            great2 = not great2
        if debug:
            print '\tComparing:',getProbRep(attr1,great1)
            print '\tvs.:',getProbRep(attr2,great2)
        if great1 != great2:
            # Thresholds in different direction
            if great1:
                # weight1*y < x < weight2*y
                if weight1 > weight2:
                    if debug: print '\t\tInconsistent'
                    result = False
            else:
                # weight1*y > x > weight2*y
                if weight2 > weight1:
                    result = False
        else:
            # Probabilistic comparison
            thresh1 = solveTuple(attr1)
            thresh2 = solveTuple(attr2)
            # Both are thresholds on the same variable
            if great1 and great2:
                # x > theta
                if thresh1 > thresh2:
                    # Subsumed
                    if debug: print '\t\tSubsumed'
                    result = True
            elif not great1 and not great2:
                # x < theta
                if thresh1 < thresh2:
                    # Subsumed
                    if debug: print '\t\tSubsumed'
                    result = True
        return result

    def prune(self,rulesOnly=False,debug=False):
        """Removes rows and attributes that are irrelevant
        @param rulesOnly: if C{True}, only the RHS of the rules need to be distinct, not the value function as well (default is C{False})
        @type rulesOnly: bool
        """
        self.pruneRules(debug)
        self.pruneAttributes(rulesOnly,debug)

    def pruneRules(self,debug=False):
        if debug:
            print 'Starting with %d rules' % (len(self.rules))
        # Prune contradictory LHS combinations'
        rule = 0
        while rule < len(self.rules):
            factors = self.rules[rule]['lhs']
            consistent = True
            for i in range(len(self.attributes)-1):
                attrI,values = self.attributes[i]
                assert values == [0.],'Unable to prune tables with nonzero intercepts in their LHS conditions'
                for j in range(i+1,len(self.attributes)):
                    attrJ,values = self.attributes[j]
                    pairwise = self._consistent(i,bool(factors[i]),j,bool(factors[j]))
                    if pairwise is None:
                        pass
                    elif pairwise:
                        pass
                    else:
                        assert pairwise is False
                        consistent = False
                        if debug:
                            print
                            print attrI.getArray(),factors[i]
                            print 'inconsistent with'
                            print attrJ.getArray(),factors[j]
                        break
                if not consistent:
                    # Already found inconsistency
                    del self.rules[rule]
                    break
            else:
                rule += 1

    def pruneAttributes(self,rulesOnly=False,debug=False):
        """Prune irrelevant attributes
        """
        if debug:
            print 'Starting with %d attributes' % (len(self.attributes))
        delete = []
        attrIndex = 0
        while attrIndex < len(self.attributes):
            distinct = False
            attr,values = self.attributes[attrIndex]
            if debug:
                print 'Testing distinctness of Attribute #%d:' % (attrIndex),
                print ','.join(map(lambda w: '%5.3f' % (w),list(attr.getArray())))
            for index1 in range(len(self.rules)-1):
                rule1 = self.rules[index1]
                factors1 = rule1['lhs'][:]
                factors1[attrIndex] = None
                for index2 in range(index1+1,len(self.rules)):
                    rule2 = self.rules[index2]
                    factors2 = rule2['lhs'][:]
                    if debug: print '\t',factors1,'vs.',factors2
                    factors2[attrIndex] = None
                    if overlap(factors1,factors2):
                        if debug: print '\t\tComparing RHS...'
                        if rule1['rhs'] != rule2['rhs']:
                            if debug: print '\t\t\tRHS Mismatch'
                            distinct = True
                            break
                        elif not rulesOnly and rule1['values'] != rule2['values']:
                            if debug: print '\t\t\tValue Mismatch'
                            distinct = True
                            break
                if distinct:
                    break
            if distinct:
                attrIndex += 1
            else:
                if debug: print '\tDeleting'
                self.delAttribute(attrIndex)
        
    def max(self,debug=False):
        """
        Computes the rules based on maximizing the values in this table
        @return: the table with the newly generated rules
        @rtype: L{PWLTable}
        @warning: assumes that the same option keys exist in every rule in the value function
        """
        # Generate new LHS conditions
        rhs = {} # Store possible conditions that would trigger each RHS
        others = {} # Store conditions for alternatives
#         for desired in options:
#             rhs[desired] = []
        for rule in self.rules:
            if debug:
                print 'Rule:',rule['lhs']
            V = rule['values']
            if isinstance(V,dict):
                values = V.items()
            else:
                values = map(lambda e: (e['rhs'],e['V']),V)
            # Identify the LHS conditions that trigger this rule
            lhs = []
            for index in range(len(self.attributes)):
                if not rule['lhs'][index] is None:
                    # Not a wildcard
                    lhs.append((self.attributes[index][0],rule['lhs'][index]))
                    if debug: print '\t',getVectorRep(self.attributes[index][0],rule['lhs'][index])
            # Initialize preconditions
            for i in range(len(values)):
                others[i] = []
            # Do pairwise comparisons between RHS values
            for i in range(len(values)):
                desired = values[i][0]
                Vdesired = values[i][1]
                try:
                    # Add on preconditions found so far
                    path = lhs + others[i]
                except KeyError:
                    # Alternative has been previously eliminated
                    continue
                if debug:
                    print desired,Vdesired.simpleText()
                # Compare against other possible RHS values
                for j in range(i+1,len(values)):
                    alternative = values[j][0]
                    Valternative = values[j][1]
                    if not others.has_key(j):
                        # Alternative has been previous eliminated
                        continue
                    if debug:
                        print '\tvs.',alternative,
                        print Valternative.simpleText()
                    # Find hyperplane border between values of two competing actions
                    weights = Vdesired - Valternative
                    # We want to be "above" plane for desired action to be preferred
                    side = 1
                    try:
                        weights.normalize()
                    except ZeroDivisionError:
                        # Null hyperplane, assume always False
                        if debug: print '\tZero vector'
                        break
                    if len(weights) == 2:
                        # Normalize direction
                        a,b = weights.getArray()
                        if a < b:
                            weights = -weights
                            side = 0
                    if debug: print '\tDifference:',getVectorRep(weights,side)
                    # Check whether this condition can ever be met
                    test = KeyedPlane(weights,0.).always(probability=True)
                    if test is None:
                        pass
                    elif not bool(side) is test:
                        if debug: print '\tNever True'
                        break
                    elif bool(side) is test:
                        if debug: print '\tAlways True'
                        del others[j]
                        continue
                    # Check whether condition consistent with original LHS
                    test = self._consistent(weights,side,lhs)
                    if debug: print '\tConsistent?',test
                    if test is None:
                        # Compare against my pre-conditions
                        test = self._consistent(weights,side,others[i])
                        if test:
                            if debug: print '\t\tSubsumed by pre-condition'
                            continue
                        elif test is False:
                            if debug: print '\t\tInconsistent with pre-condition'
                            break
                        # Add to alternative's pre-conditions
                        if others[j]:
                            test = self._consistent(weights,1-side,lhs+others[j])
                        else:
                            test = None
                        if test is None:
                            if debug: print '\tPrecondition:',getVectorRep(weights,1-side)
                            others[j].append((weights,1-side))
                        elif test is False:
                            if debug: print '\tImpossible'
                            del others[j]
                        else:
                            assert test is True
                            if debug: print '\tSubsumed'
                        if debug: print
                        path.append((weights,side))
                    elif test: # This condition is always met
                        if debug: print '\tDominated'
                        del others[j]
                    else: # This condition is never met
                        if debug: print '\tInconsistent'
                        break
                else: # Conditions are all potentially meetable
                    if debug: 
                        print 'Final for rule',desired
                        for weights,side in path:
                            print side,getVectorRep(weights,side)
                    try:
                        rhs[desired].append({'lhs':path,'values':{desired: Vdesired}})
                    except KeyError:
                        rhs[desired] = [{'lhs':path,'values':{desired: Vdesired}}]
        # Generate new table attributes
        policy = PWLTable()
        for desired,conditions in rhs.items():
            for condition in conditions:
                path = condition['lhs']
                for index in range(len(path)):
                    pos = policy.addAttribute(path[index][0],0.)
        policy.initialize()
        del policy.rules[0]
        if debug:
            print 'New attributes:'
            if policy.attributes:
                for attr in policy.attributes:
                    print '\t',getVectorRep(attr[0])
            else:
                print '\tNone'
        # Translate plane into attribute index
        cache = {}
        for desired,conditions in rhs.items():
            if debug: print 'Processing:',desired
            for condition in conditions:
                path = condition['lhs']
                for index in range(len(path)):
                    try:
                        attr = policy._attributes[str(path[index][0].getArray())]
                        value = path[index][1]
                    except KeyError:
                        attr = policy._attributes[str(-path[index][0].getArray())]
                        assert policy.attributes[attr][1] == [0.]
                        value = 1 - path[index][1]
                    if debug: print '\t%d,%s' % (attr,value)
                    path[index] = (attr,value)
        # Generate new rules for this table
        for desired,conditions in rhs.items():
            if debug: print 'Inserting:',desired
            for condition in conditions:
                # Initialize attribute values
                factors = map(lambda i: None,range(len(policy.attributes)))
                path = []
                # Override defaults with LHS values
                for attr,value in condition['lhs']:
                    assert isinstance(attr,int) and factors[attr] is None
                    factors[attr] = value
                    path.append((attr,value))
                if debug: print 'Original:',policy.factorString(factors)
                for attr in range(len(policy.attributes)):
                    if factors[attr] is None:
                        test = policy._consistent(attr,1,path)
                        if debug: print '\t',getVectorRep(policy.attributes[attr][0],1),test
                        if test is None: # Possibly satisfied
                            pass
                        elif test: # Always satisfied
                            factors[attr] = 1
                            path.append((policy.attributes[attr][0],1))
                        else: # Never satisfied
                            factors[attr] = 0
                            path.append((policy.attributes[attr][0],0))
                if debug: print '\t%s' % (policy.factorString(factors))
                # Insert RHS and value into specified rule
                values = {}
                values.update(condition['values'])
                policy.rules.append({'lhs': factors, 'rhs': desired,
                                     'values': values})
                if debug: print
        return policy
        
    def oldMax(self,debug=False):
        """
        Computes the rules based on maximizing the values in this table
        @return: the table with the newly generated rules
        @rtype: L{PWLTable}
        @warning: assumes that the same option keys exist in every rule in the value function
        """
        # Generate new LHS conditions
        options = self.rules[0]['values'].keys()
        options.sort()
        rhs = {} # Store possible conditions that would trigger each RHS
        for desired in options:
            rhs[desired] = []
        others = {} # Cache defeating conditions of other RHS
        for rule in self.rules:
            if debug:
                print 'Rule:',rule['lhs']
            V = rule['values']
            # Identify the LHS conditions that trigger this rule
            factors = rule['lhs']
            lhs = []
            for index in range(len(self.attributes)):
                if not factors[index] is None:
                    # Not a wildcard
                    lhs.append((self.attributes[index][0],factors[index]))
                    if debug: print '\t',getVectorRep(self.attributes[index][0],factors[index])
            # Initialize preconditions
            for desired in options:
                others[desired] = []
            # Do pairwise comparisons between RHS values
            for i in range(len(options)):
                desired = options[i]
                if not others.has_key(desired):
                    # Alternative has been previously eliminated
                    continue
                if debug:
                    print desired,V[desired].simpleText()
                # Add on preconditions found so far
                path = lhs + others[desired]
                # Compare against other possible RHS values
                for j in range(i+1,len(options)):
                    alternative = options[j]
                    if not others.has_key(alternative):
                        # Alternative has been previous eliminated
                        continue
                    if debug:
                        print '\tvs.',alternative,
                        print V[alternative].simpleText()
                    # Find hyperplane border between values of two competing actions
                    weights = V[desired] - V[alternative]
                    # We want to be "above" plane for desired action to be preferred
                    side = 1
                    try:
                        weights.normalize()
                    except ZeroDivisionError:
                        # Null hyperplane, assume always False
                        if debug: print '\tZero vector'
                        break
                    if len(weights) == 2:
                        # Normalize direction
                        a,b = weights.getArray()
                        if a < b:
                            weights = -weights
                            side = 0
                    if debug: print '\tDifference:',getVectorRep(weights,side)
                    # Check whether this condition can ever be met
                    test = KeyedPlane(weights,0.).always(probability=True)
                    if test is None:
                        pass
                    elif not bool(side) is test:
                        if debug: print '\tNever True'
                        break
                    elif bool(side) is test:
                        if debug: print '\tAlways True'
                        del others[alternative]
                        continue
                    # Check whether condition consistent with original LHS
                    test = self._consistent(weights,side,lhs)
                    if debug: print '\tConsistent?',test
                    if test is None:
                        # Compare against my pre-conditions
                        test = self._consistent(weights,side,others[desired])
                        if test:
                            if debug: print '\t\tSubsumed by pre-condition'
                            continue
                        elif test is False:
                            if debug: print '\t\tInconsistent with pre-condition'
                            break
                        # Add to alternative's pre-conditions
                        if others[alternative]:
                            test = self._consistent(weights,1-side,lhs+others[alternative])
                        else:
                            test = None
                        if test is None:
                            if debug: print '\tPrecondition:',getVectorRep(weights,1-side)
                            others[alternative].append((weights,1-side))
                        elif test is False:
                            if debug: print '\tImpossible'
                            del others[alternative]
                        else:
                            assert test is True
                            if debug: print '\tSubsumed'
                        if debug: print
                        # Check whether any existing conditions are subsumed
##                        index = 0
##                        while index < len(path):
##                            test = self._consistent(path[index][0],path[index][1],weights,side)
##                            if test is True:
##                                if debug: print '\tSubsumes:',getVectorRep(path[index][0],path[index][1])
##                                del path[index]
##                            else:
##                                index += 1
                        path.append((weights,side))
                    elif test: # This condition is always met
                        if debug: print '\tDominated'
                        del others[alternative]
                    else: # This condition is never met
                        if debug: print '\tInconsistent'
                        break
                else: # Conditions are all potentially meetable
                    if debug: 
                        print 'Final for rule',desired
                        for weights,side in path:
                            print side,getVectorRep(weights,side)
                    rhs[desired].append({'lhs':path,'values':rule['values']})
        # Generate new table attributes
        policy = PWLTable()
        for desired,conditions in rhs.items():
            for condition in conditions:
                path = condition['lhs']
                for index in range(len(path)):
                    pos = policy.addAttribute(path[index][0],0.)
        policy.initialize()
        del policy.rules[0]
        if debug:
            print 'New attributes:'
            if policy.attributes:
                for attr in policy.attributes:
                    print '\t',getVectorRep(attr[0])
            else:
                print '\tNone'
        # Translate plane into attribute index
        cache = {}
        for desired,conditions in rhs.items():
            if debug: print 'Processing:',desired
            for condition in conditions:
                path = condition['lhs']
                for index in range(len(path)):
                    try:
                        attr = policy._attributes[str(path[index][0].getArray())]
                        value = path[index][1]
                    except KeyError:
                        attr = policy._attributes[str(-path[index][0].getArray())]
                        assert policy.attributes[attr][1] == [0.]
                        value = 1 - path[index][1]
                    if debug: print '\t%d,%s' % (attr,value)
                    path[index] = (attr,value)
        # Generate new rules for this table
        for desired,conditions in rhs.items():
            if debug: print 'Inserting:',desired
            for condition in conditions:
                # Initialize attribute values
                factors = map(lambda i: None,range(len(policy.attributes)))
                path = []
                # Override defaults with LHS values
                for attr,value in condition['lhs']:
                    assert isinstance(attr,int) and factors[attr] is None
                    factors[attr] = value
                    path.append((attr,value))
                if debug: print 'Original:',policy.factorString(factors)
                for attr in range(len(policy.attributes)):
                    if factors[attr] is None:
                        test = policy._consistent(attr,1,path)
                        if debug: print '\t',getVectorRep(policy.attributes[attr][0],1),test
                        if test is None: # Possibly satisfied
                            pass
                        elif test: # Always satisfied
                            factors[attr] = 1
                            path.append((policy.attributes[attr][0],1))
                        else: # Never satisfied
                            factors[attr] = 0
                            path.append((policy.attributes[attr][0],0))
                if debug: print '\t%s' % (policy.factorString(factors))
                # Insert RHS and value into specified rule
                values = {}
                values.update(condition['values'])
                policy.rules.append({'lhs': factors, 'rhs': desired,
                                     'values': values})
                if debug: print
        return policy

    def star(self):
        """Computes the optimal value function, independent of action
        @return: a table with the optimal value as the rules' RHS, and no values
        @rtype: L{PWLTable}
        """
        result = self.getTable()
        for rule in range(len(self.rules)):
            rhs = result.rules[rule]['rhs']
            if not isinstance(rhs,str):
                rhs = ','.join(map(str,rhs))
            result.rules[rule]['rhs'] = result.rules[rule]['values'][rhs]
            result.rules[rule]['values'].clear()
        return result
    
    def __len__(self):
        return len(self.rules)

    def __add__(self,other,debug=False):
        if self.zeroPlanes and other.zeroPlanes:
            return self.mergeZero(other,lambda x,y: x+y,None,debug)
        result = PWLTable()
        if debug:
            print 'I:',self
            print 'U:',other
        # Start with addend's attributes
        for obj,values in other.attributes:
            result.attributes.append((obj,values[:]))
        # Insert mine in as well
        for obj,values in self.attributes:
            index = result.addAttribute(obj,values[0])
            for value in values[1:]:
                if not value in result.attributes[index][1]:
                    result.attributes[index][1].append(value)
            result.attributes[index][1].sort()
        result.initialize()
        if debug:
            print 'New attributes:'
            for attr in result.attributes:
                print '\t',attr[0].getArray()
        # Transfer RHS 
        for myRule in range(len(self.rules)):
            myFactors = self.rules[myRule]['lhs']
            for yrRule in range(len(other.rules)):
                yrFactors = other.rules[yrRule]['lhs']
                # Compute new rule index
                newFactors = result.mapIndex(other,yrFactors)
                newFactors = result.mapIndex(self,myFactors,newFactors)
                if not newFactors is None:
                    # Consistent mapping found, so insert RHS
                    entry = {'lhs': newFactors,
                             'rhs': None,
                             'values': {},
                             }
                    for option,yrRHS in other.rules[yrRule]['values'].items():
                        # Compute new RHS
                        myRHS = self.rules[myRule]['values'][option]
                        newRHS = myRHS + yrRHS
                        entry['values'][option] = newRHS
                    result.rules.append(entry)
        return result
    
    def __mul__(self,other,combiner=None,debug=False):
        """
        @param combiner: optional binary function for using in combining RHS matrices (default is multiplication, duh)
        @type combiner: lambda
        @warning: like matrix multiplication, not commutative
        """
        if self.zeroPlanes and other.zeroPlanes:
            return self.mergeZero(other,combiner,lambda x,y: x*y,debug)
        result = self.__class__()
        # Start with right multiplicand's LHS
        for obj,values in other.attributes:
            result.attributes.append((obj,values[:]))
        # Project my LHS
        for rule in range(len(other.rules)):
            V = other.rules[rule]['values']
            if V:
                # Access all RHS in value function
                new = V.values()
            else:
                # No value function, take rule RHS
                new = [other.rules[rule]['rhs']]
            for rhs in new:
                for obj,values in self.attributes:
                    new = obj*rhs
                    new.normalize()
                    index = None
                    for value in values:
                        plane = KeyedPlane(new,value)
                        if plane.always(probability=True) is None:
                            if index is None:
                                index = result.addAttribute(new,value)
                            else:
                                result.attributes[index][1].append(value)
                    if not index is None:
                        result.attributes[index][1].sort()
        result.initialize()
        if debug:
            print 'New attributes:'
            for attr in result.attributes:
                print '\t',attr[0].getArray()
        # Transfer RHS 
        for myRule in range(len(self.rules)):
            myFactors = self.rules[myRule]['lhs']
            for yrRule in range(len(other.rules)):
                yrFactors = other.rules[yrRule]['lhs']
                for option,yrRHS in other.rules[yrRule]['values'].items():
                    # Compute new RHS
                    try:
                        myRHS = self.rules[myRule]['values'][option]
                    except KeyError:
                        # No value function... use rules
                        myRHS = self.rules[myRule]['rhs']
                    if combiner:
                        newRHS = combiner(myRHS,yrRHS)
                    else:
                        newRHS = myRHS*yrRHS
                    if debug:
                        print '\nA:'
                        for index in range(len(self.attributes)):
                            print bool(myFactors[index]),self.attributes[index][0].getArray()
                        print 'B:'
                        for index in range(len(other.attributes)):
                            print bool(yrFactors[index]),other.attributes[index][0].getArray()
                        print option
                        print 'Product:',newRHS.getArray()
                    # Compute new rule index
                    newFactors = result.mapIndex(other,yrFactors,debug=debug)
                    newFactors = result.mapIndex(self,myFactors,
                                                 newFactors,yrRHS,debug=debug)
                    if not newFactors is None:
                        # Consistent mapping found, so insert RHS
                        if debug: print newFactors
                        result.mergeValue(newFactors,option,newRHS)
                    elif debug:
                        print 'Rejected'
        result.pruneAttributes()
        return result

    def mergeZero(self,other,combiner=None,projector=None,debug=False):
        """
        Merging when both tables have all of their hyperplanes going through the origin
        @param combiner: optional binary function for using in combining RHS matrices (default is multiplication)
        @type combiner: lambda
        @param projector: optional binary function for using in projecting my LHS attributes based on the RHS of the other
        @type projector: lambda
        @warning: like matrix multiplication, not commutative
        """
        # Build pairwise combinations of all rules
        entries = []
        for yrRule in other.rules:
            # Find non-wildcard LHS conditions for other table's rules
            root = filter(lambda i: not yrRule['lhs'][i] is None,
                          range(len(other.attributes)))
            # Match LHS hyperplane with side we need to be on
            root = map(lambda i: (other.attributes[i][0],
                                  yrRule['lhs'][i]),root)
            for myRule in self.rules:
                for option,yrRHS in yrRule['values'].items():
                    path = root[:]
                    # Extract my RHS
                    try:
                        myRHS = myRule['values'][option]
                    except KeyError:
                        myRHS = myRule['rhs']
                        if myRHS is None:
                            # Incomplete RHS
                            break
                    if debug:
                        print
                        print 'Combining:',myRule['lhs']
#                        print myRHS.simpleText()
                        print 'with:',yrRule['lhs']
#                        print yrRHS.simpleText()
                        print 'under:',option
                    # Find non-wildcard LHS conditions for my rules
                    myIndices = filter(lambda i:not myRule['lhs'][i] is None,
                                       range(len(self.attributes)))
                    for myIndex in myIndices:
                        myAttr = self.attributes[myIndex][0]
                        if projector:
                            # Project hyperplane against RHS of other
                            if debug:
                                print '\tProjecting:',myAttr.simpleText()
                            newAttr = projector(myAttr,yrRHS)
                            try:
                                newAttr.normalize()
                            except ZeroDivisionError:
                                # all zeros, assume always False
                                if debug: print '\t\tDegenerate'
                                if myRule['lhs'][myIndex]:
                                    # we want it to be True, never will be
                                    break
                                else:
                                    # we want it to be False, always will be
                                    continue
                            # Not zero vector; check for other degeneracy
                            if debug: print '\tInto:',newAttr.simpleText()
                            if len(newAttr) == 2:
                                # Check whether this is a degenerate condition
                                threshold = solveTuple(newAttr)
                                if not isinstance(threshold,float):
                                    if threshold == myRule['lhs'][myIndex]:
                                        # Always satisfied
                                        if debug: print '\t\tRedundant'
                                        continue
                                    else: # Never satisfiable
                                        if debug: print '\t\tInconsistent'
                                        break
                        else:
                            newAttr = myAttr
                        # Check consistency against existing settings
#                        if debug: print '\t\tChecking:',newAttr.getArray()
                        consistent = True
                        for yrAttr,yrSide in path:
                            if detectConflict(newAttr,myRule['lhs'][myIndex],
                                              yrAttr,yrSide):
                                # Conflict with other rule
                                consistent = False
                                break
                        if consistent:
                            path.append((newAttr,myRule['lhs'][myIndex]))
                        else:
                            break
                    else:
                        # Consistent path found
                        entry = {'LHS': path,'option': option}
                        if combiner:
                            entry['RHS'] = combiner(myRHS,yrRHS)
                        else:
                            entry['RHS'] = myRHS*yrRHS
                        if debug:
                            print 'Path found:'
                            if entry['LHS']:
                                print '\t%s' % (map(lambda (v,s): s,entry['LHS']))
 #                               for vector,side in entry['LHS']:
 #                                   print '\t',getVectorRep(vector,side)
                            else:
                                print '\t[]'
                            print '\tRHS:',entry['RHS'].simpleText()
                        entries.append(entry)
        # Extract entries found
        result = self.__class__()
        # Copy over attributes from other
        attributes = {}
        # Add new attributes from each new rule
        for entry in entries:
            for attr,side in entry['LHS']:
                key = str(attr.getArray())
                if not attributes.has_key(key):
                    # Keep track of which side of plane we've found
                    attributes[key] = side
                elif attributes[key] is None:
                    # Already added
                    pass
                elif attributes[key] != side:
                    # Both sides of plane are represented
                    result.addAttribute(attr,0.)
                    attributes[key] = None
        attributes.clear()
        # Find indices for new set of attributes
        for index in range(len(result.attributes)):
            attributes[str(result.attributes[index][0].getArray())] = index
            if debug:
                print 'Attribute:',result.attributes[index][0].simpleText()
        result.initialize(False)
        if projector is None:
            result.rules = []
        # Convert entries into value function entries
        for entry in entries:
            if debug:
                print 'New Entry:',entry['option']
                print '\tValue:',entry['RHS'].simpleText()
            # Start with all wildcards
            factors = map(lambda a: None,result.attributes)
            # Set new factors
            for plane,side in entry['LHS']:
                if debug:
                    print '\t',getVectorRep(plane,side)
                key = str(plane.getArray())
                try:
                    attr = attributes[key]
                except KeyError:
                    # Probably a float problem
                    for attr in range(len(result.attributes)):
                        if sum(abs(plane.getArray()-result.attributes[attr][0].getArray())) < 1e-8:
                            break
                    else:
                        raise ValueError,'Unable to find attribute!'
                if factors[attr] is None:
                    factors[attr] = side
                elif factors[attr] != side:
                    # Conflict!  Should we have caught this before?
                    break
                if debug:
                    print '\t\t',attr,side
            else:
                # Insert new value entry
                if projector:
                    # Possibly overlapping due to new attributes
                    result.mergeValue(factors,entry['option'],entry['RHS'],debug=debug)
                    if debug:
                        print 'Ending LHS:'
                        for rule in result.rules:
                            print rule['lhs'],','.join(rule['values'].keys())
                else:
                    # Impossible to overlap
                    for newRule in result.rules:
                        if newRule['lhs'] == factors:
                            assert not newRule['values'].has_key(entry['option'])
                            newRule['values'][entry['option']] = entry['RHS']
                            break
                    else:
                        # No rule for these factors yet
                        result.rules.append({'lhs': factors,
                                             'values':{entry['option']:entry['RHS']},
                                             'rhs': None})
        index = 0
        while index < len(result.rules):
            rule = result.rules[index]
            if len(rule['values']) < len(other.rules[0]['values']):
                if rule['direct']:
                    raise ValueError,'Actions missing from RHS'
                else:
                    del result.rules[index]
            else:
                index += 1
        return result

    def mergeValue(self,factors,option,value,debug=False):
        """
        Merges the single V entry, using the given LHS and action key, into the current value function
        @param factors: the attribute values for the LHS of this rule
        @type factors: int[]
        """
        if debug: print 'Merging:',factors,option
        for rule in self.rules[:]:
            if debug: print 'w/',rule['lhs'],','.join(rule['values'].keys())
            restrictions = []
            newLHS = intersection(rule['lhs'],factors,restrictions)
            if not newLHS is None:
                # Merge into this rule
                if debug: 
                    print '\tIntersection =',newLHS
                    print '\tRestrictions =',restrictions
                if restrictions:
                    # Add rules when this does *not* apply
                    for index in range(len(restrictions)):
                        lhs = newLHS[:]
                        lhs[restrictions[index]] = 1 - lhs[restrictions[index]]
                        for other in restrictions[index+1:]:
                            lhs[other] = None
                        if self.consistentp(lhs):
                            entry = {'lhs': lhs,'values': {},
                                     'rhs': rule['rhs'],
                                     'direct': False}
                            entry['values'].update(rule['values'])
                            if debug: print '\tadding:',entry['lhs'],','.join(entry['values'].keys())
                            entry['direct'] = False
                            self.rules.append(entry)
                # Update existing rule
                rule['lhs'] = newLHS
                assert not rule['values'].has_key(option)
                rule['values'][option] = value
                if rule['lhs'] == factors: rule['direct'] = True

    def mapIndex(self,other,factors,result=None,multiplicand=None,debug=False):
        """Translates an index in another table into one for this table
        @param other: the other table
        @type other: L{PWLTable}
        @param factors: the index or factors of the rule to map
        @type factors: int or int[]
        @param result: previously determined factors that should be merged (default is C{None})
        @type result: int[]
        @param multiplicand: matrix used to scale any attributes (default is identity)
        @type multiplicand: L{KeyedMatrix<teamwork.math.KeyedMatrix.KeyedMatrix>}
        @return: a list of attributes subindices, C{None} if no consistent index exists
        @rtype: int[]
        """
        if result is None:
            result = map(lambda attr: None,self.attributes)
        if isinstance(factors,int):
            factors = other.index2factored(factors)
            raise NotImplementedError
        for pos in range(len(factors)):
            obj,values = other.attributes[pos]
            assert values == [0.],'Unable to handle non-zero thresholds'
            if multiplicand:
                # Apply projection to LHS condition
                obj = obj*multiplicand
                obj.normalize()
            # Figure out interval of acceptable values for this attribute
            side = factor[pos]
            if debug:
                print '\tMapping:',obj.getArray()
            # Map interval into new range of possible values
            try:
                index = self._attributes[str(obj.getArray())]
            except KeyError:
                try:
                    index = self._attributes[str(-obj.getArray())]
                    if not side is None:
                        side = 1 - side
                except KeyError:
                    # Check whether we've generated a degenerate condition
                    assert values == [0.]
                    plane = KeyedPlane(obj,0.)
                    always = plane.always(probability=True)
                    if always is None:
                        raise UserWarning,str(plane)
                    elif always:
                        # This condition is always true
                        if side == 0:
                            # But we need it to be false
                            if debug:
                                print '\t',always
                            return None
                        else:
                            continue
                    else:
                        # This condition will never be met
                        if side == 1:
                            # But we need it to be true
                            if debug:
                                print '\t',always
                            return None
                        else:
                            continue
            obj,values = self.attributes[index]
            assert values == [0.],'Unable to handle non-zero thresholds'
            if result[index] is None:
                if not side is None:
                    # Check consistency
                    if index < 0:
                        always = self._consistent(index+len(self.attributes),side,
                                                  map(lambda i: (i,result[i]),
                                                      range(len(self.attributes))))
                    else:
                        always = self._consistent(index,side,
                                                  map(lambda i: (i,result[i]),
                                                      range(len(self.attributes))))
                    if always is False:
                        return None
                    # Setting attribute value fresh
                    result[index] = side
            else:
                # Merge with existing attribute
                if side == 1 and result[index] == 0:
                    # Mismatch
                    return None
                elif side == 0 and result[index] == 1:
                    # Mismatch
                    return None
        return result

    ## Abstract value iteration methods

    def abstract(self,factors):
        """
        @param factors: the rule LHS indices
        @type factors: int[]
        @return: the abstract state subspace where the given rule is applicable, in the form of a list of intervals, one for each attribute, where each interval is a dictionary with keys C{weights}, C{index}, C{lo}, and C{hi}
        @rtype: dict[]
        """
        abstract = []
        for attrIndex in range(len(self.attributes)):
            obj,values = self.attributes[attrIndex]
            if isinstance(obj,KeyedVector):
                if factors[attrIndex] is None:
                    lo = -1.
                    hi = 1.
                else:
                    if factors[attrIndex] > 0:
                        lo = values[factors[attrIndex]-1]
                    else:
                        lo = -1.
                    try:
                        hi = values[factors[attrIndex]]
                    except IndexError:
                        hi = 1.
                abstract.append({'weights':obj,'index':factors[attrIndex],
                                 'lo':lo,'hi':hi})
            else:
                raise NotImplementedError,'Not yet able to abstract over rules on observations.'
        return abstract
        
    def abstractSolve(self,entity,horizon,options=None,interrupt=None):
        """
        Generates an abstract state space (defined by the LHS attributes) and does value iteration to generate a policy
        @warning: assumes that all of the agents have the same LHS attribute breakdown! (not hard to overcome this assumption, but annoying to code)
        @rtype: bool
        """
        policies = {entity.name: self}
        policies = entity.getPolicies(policies)
        if len(self.rules) == 1:
            # If no pre-existing rules, expand reachable LHS combinations
            self.abstractReachable(entity,policies)
        # Initialize RHS possibilities
        if options is None:
            options = entity.actions.getOptions()
        for name,policy in policies.items():
            for rule in policy.rules:
                if not rule['values']:
                    if name == entity.name:
                        rhs = options
                    else:
                        rhs = entity.getEntity(name).actions.getOptions()
                    for option in rhs:
                        rule['values'][entity.makeActionKey(option)] = 0.
        # Initialize abstract value function
        for name,policy in policies.items():
            for rule in policy.rules:
                for key in rule['values'].keys():
                    assert key[:len(name)] == name
                    rule['values'][key] = 0.
        # Compute immediate (abstract) reward and cache it
        for name in policies.keys():
            policy = policies[name]
            if name == entity.name:
                goals = entity.getGoalVector()['state'].expectation()
            else:
                goals = entity.getEntity(name).getGoalVector()['state'].expectation()
            for rule in policy.rules:
                intervals = policy.abstract(rule['lhs'])
                # R(a,b)
                rule['R'] = policy.abstractReward(intervals,goals,interrupt)
                # V(b)
                rule['V'] = {}
                for other in policies.keys():
                    rule['V'][other] = 0.
        # Compute abstract transition probability
        for rule in self.rules:
            if not rule.has_key('transition'):
                if self.abstractTransition(entity,policies,interrupt):
                    break
                else:
                    # Interrupted
                    return None
        # Value iteration
        change = 1.
        iterations = 0
        while iterations < horizon:
            iterations += 1
            change = 0.
            for name in policies.keys():
                if interrupt and interrupt.isSet(): return None
                # Iterate through one whole policy at a time
                if name == entity.name:
                    change += policies[name].abstractIterate(entity,policies,interrupt)
                else:
                    change += policies[name].abstractIterate(entity.getEntity(name),policies,interrupt)
            if change < epsilon:
                break
        # Extract RHS actions from value function
        for name,policy in policies.items():
            if name == entity.name:
                agent = entity
            else:
                agent = entity.getEntity(name)
            for rule in policy.rules:
                best = None
                for option in agent.actions.getOptions():
                    actionKey = agent.makeActionKey(option)
                    if rule['values'].has_key(actionKey):
                        if best is None or rule['values'][actionKey] > best:
                            best = rule['values'][actionKey]
                            rule['rhs'] = option
#         self.compact()
        return True

    def clearTransition(self):
        """Erases any abstract transition probability in the rules
        """
        for rule in self.rules:
            if rule.has_key('transition'):
                del rule['transition']
            else:
                break

    def abstractReachable(self,entity,policies):
        state = entity.entities.getState()
        index = self.index(state.expectation(),{})
        del self.rules[:index-1]
        del self.rules[index+1:]
        rule = self.rules[0]
        rule['lhs'] = self.getFactors(state.expectation(),{})
        index = self.factored2index(rule['lhs'])
        assert len(index) == 1,'Ambiguous LHS from initial state'
        reachable = {index[0]: True}
        remaining = [rule]
        while len(remaining) > 0:
            # Examine an unexpanded LHS combination
            rule = remaining.pop()
            intervals = self.abstract(rule['lhs'])
            # Cycle through all possible actions
            for actor in entity.getEntityBeliefs():
                for option in actor.actions.getOptions():
                    # Consider all possible destinations
                    destinations = self._abstractTransition(entity,intervals,{actor.name: option})
                    for index in filter(lambda i: not reachable.has_key(i),
                                        destinations.domain()):
                        # Newly reachable LHS combinations
                        factors = self.index2factored(index)
                        new = copy.deepcopy(rule)
                        new['lhs'] = factors
                        self.rules.append(new)
                        remaining.append(new)
                        reachable[index] = True
        self.rules.sort(lambda r1,r2: cmp(r1['lhs'],r2['lhs']))
        # Copy LHS combinations over to other policies as well
        for table in policies.values():
            if not table is self:
                assert len(table.rules) == 1
                original = table.rules[0]
                table.rules = copy.deepcopy(self.rules)
                # Restore RHS values from original table
                for rule in table.rules:
                    for key,value in original.items():
                        if key != 'lhs':
                            rule[key] = copy.copy(value)
        # Uncomment the following to test that the LHS combinations are mutually exclusive
##        reachable.clear()
##        for rule in self.rules:
##            index = self.factored2index(rule['lhs'])
##            assert len(index) == 1
##            assert not reachable.has_key(index[0])
##            reachable[index[0]] = True
        
    def abstractTransition(self,entity,policies,interrupt=None,debug=False):
        """
        Generates a transition probability function over the abstract state state space (defined by the LHS attributes)
        """
        self.clearTransition()
        for name in policies.keys():
            if debug:
                print 'Agent:',name
            for rule in policies[name].rules:
                if name == entity.name:
                    agent = entity
                else:
                    agent = entity.getEntity(name)
                rule['transition'] = {}
                if debug:
                    print 'Start:',policies[name].factored2str(rule['lhs'])
                # Determine what ranges we fall in
                intervals = policies[name].abstract(rule['lhs'])
                # WARNING: the following assumes that all of the agents' policies have the same LHS breakdown!!!
                for option in agent.actions.getOptions(): 
                    if interrupt and interrupt.isSet():
                        self.clearTransition()
                        return None
                    event = {name:option}
                    actionKey = entity.makeActionKey(event)
##                    if not rule['values'].has_key(actionKey):
##                        # Not an eligible action in this LHS
##                        continue
                    if debug:
                        print '\t%s' % (actionKey)
                    rule['transition'][actionKey] = policies[name]._abstractTransition(entity,intervals,event)
                    if debug:
                        for dest in rule['transition'][actionKey].domain():
                            print '\t\t%s: %5.3f' % (policies[name].factored2str(policies[name].index2factored(dest)),
                                                     rule['transition'][actionKey][dest])
        return True

    def _abstractTransition(self,entity,intervals,event):
        """Computes a specific transition probability from a given start set in response to a specific action
        """
        # Compute dynamics for this action
        dynamics = entity.entities.getDynamics(event)
        tree = dynamics['state'].getTree()
        # Compute possible transitions over intervals
        table = Distribution()
        for matrix,prob in tree[intervals].items():
            new = []
            for index in range(len(self.attributes)):
                # Determine effect on individual attribute
                obj,values = self.attributes[index]
                assert isinstance(obj,KeyedVector)
                if isinstance(obj,ThresholdRow):
                    key = obj.specialKeys[0]
                    new.append(adjustInterval(intervals,index,key,matrix[key]))
                elif isinstance(obj,DifferenceRow):
                    key = obj.specialKeys[0]
                    hi = adjustInterval(intervals,index,key,matrix[key])
                    key = obj.specialKeys[1]
                    lo = adjustInterval(intervals,index,key,matrix[key])
                    new.append({'lo':hi['lo']-lo['hi'],
                                'hi':hi['hi']-lo['lo']})
                else:
                    msg = 'Unable to compute abstract transitions of %s attributes' % \
                          (obj.__class__.__name__)
                    raise NotImplementedError,msg
            # Compute the possible rules applicable in the new interval
            destinations = [{'prob':prob,'factors':[]}]
            for index in range(len(self.attributes)):
                obj,values = self.attributes[index]
                interval = new[index]
                span = interval['hi'] - interval['lo']
                loIndex = self.subIndex(index,interval['lo'])
                hiIndex = self.subIndex(index,interval['hi'])
                # Compute probability of individual destinations
                subProbs = {}
                if hiIndex > loIndex:
                    # Multiple destinations
                    subProbs[loIndex] = (values[loIndex]-interval['lo'])/span
                    subProbs[hiIndex] = (interval['hi']-values[hiIndex-1])/span
                    for subIndex in range(loIndex+1,hiIndex):
                        subProbs[subIndex] = (values[subIndex]-values[subIndex-1])/span
                else:
                    # Only one destination
                    subProbs[loIndex] = 1.
                # Generate possible destinations
                for dest in destinations[:]:
                    destinations.remove(dest)
                    for subIndex in range(loIndex,hiIndex+1):
                        newDest = copy.deepcopy(dest)
                        newDest['prob'] *= subProbs[subIndex]
                        newDest['factors'].append(subIndex)
                        destinations.append(newDest)
            for dest in destinations:
                index = self.factored2index(dest['factors'])
                assert len(index) == 1
                try:
                    table[index[0]] += dest['prob']
                except KeyError:
                    table[index[0]] = dest['prob']
        for dest,prob in table.items():
            assert prob > -epsilon
            if prob < epsilon:
                del table[dest]
        assert abs(sum(table.values())-1.) < epsilon
        return table
        
    def abstractIterate(self,entity,policies,interrupt):
        """
        One pass of value iteration over abstract state space.
        @warning: Currently works for only two agents (easy, but messy, to generalize)
        @param rewards: C{rewards[name][state][action]} = the reward that agent C{name} gets in state C{state} (index form) derived from the performance of C{action}
        @type rewards: strS{->}(strS{->}float)[]
        @return: the total change to the value function
        @rtype: float
        """
        values = []
        # Proceed backward from end of lookahead
        sequence = entity.getLookahead()
        sequence.reverse()
        delta = 0.
        for index in range(len(sequence)):
            name = sequence[index]
            for rule in policies[name].rules:
                current = self.match(rule['lhs'])
                if name == entity.name:
                    # Evaluate all of my possible actions
                    for option in rule['values'].keys():
                        assert option[:len(name)] == name
                        value = self.rules[current]['R']
                        table = rule['transition'][option]
                        next = sequence[index-1]
                        for dest,prob in table.items():
                            rule = self.rules[self.match(self.index2factored(dest))]
                            value += prob*rule['V'][next]
                        rule['values'][option] = value
                # Determine what action this agent will do
                best = {'value':None}
                for option,value in rule['values'].items():
                    assert option[:len(name)] == name
                    if best['value'] is None or value > best['value']:
                        best['value'] = value
                        best['option'] = option
                # Compute new value
                value = self.rules[current]['R']
                table = rule['transition'][best['option']]
                next = sequence[index-1]
                for dest,prob in table.items():
                    rule = self.rules[self.match(self.index2factored(dest))]
                    value += prob*rule['V'][next]
                delta += abs(self.rules[current]['V'][name]-value)
                self.rules[current]['V'][name] = value
        return delta

    def abstractReward(self,intervals,goals,interrupt=None):
        reward = 0.
        # Apply state-dependent factors of reward
        for index in range(len(self.attributes)):
            if interrupt and interrupt.isSet(): return None
            obj,values = self.attributes[index]
            interval = intervals[index]
            if isinstance(obj,ThresholdRow):
                key = obj.specialKeys[0]
                if goals.has_key(key):
                    # We have a non-zero reward weight for a feature
                    # where we know the interval of possible values
                    mean = (interval['hi']+interval['lo'])/2.
                    reward += goals[key]*mean
            else:
                raise NotImplementedError,'Unable to compute abstract reward for %s attributes' % (obj.__class__.__name__)
        return reward

    def compact(self):
        """Use wildcards to merge rules that have the same RHS and value function
        """
        change = True
        while change:
            # Iterate until we make a complete pass without any compacting happening
            change = False
            i = 0
            while i < len(self.rules)-1:
                rule = self.rules[i]
                for index in range(len(self.attributes)):
                    if not rule['lhs'] is None:
                        # Not a wildcard.  Should it be?
                        obj,values = self.attributes[index]
                        myLHS = rule['lhs'][:index]+rule['lhs'][index+1:]
                        matches = []
                        for j in range(i+1,len(self.rules)):
                            yrLHS = self.rules[j]['lhs'][:index]+self.rules[j]['lhs'][index+1:]
                            if myLHS == yrLHS:
                                # We match on all other attributes
                                assert not self.rules[j]['lhs'][index] is None
                                assert self.rules[j]['lhs'][index] != rule['lhs'][index]
                                if rule['values'] == self.rules[j]['values']:
                                    matches.append(j)
                                    if len(matches) == len(values):
                                        # We have covered all other possible values for this attribute
                                        self.rules[i]['lhs'][index] = None
                                        for k in matches:
                                            del self.rules[k]
                                        change = True
                                        break
                                else:
                                    # Different RHS so this attribute is important
                                    break
                i += 1

    def load(self,entity,filename,zpomdp=False):
        """
        Loads a value function from a file
        @param zpomdp: if C{True}, then expects ZPOMDP file format; otherwise, Cassandra format (default is C{False})
        @type zpomdp: bool
        """
        # Clear all rules except for 1
        del self.rules[1:]
        rule = self.rules[0]
        rule['rhs'] = None
        rule['values'] = []
        if zpomdp:
            self.loadZPOMDP(entity,filename)
        else:
            self.loadCassandra(entity,filename)

    def loadZPOMDP(self,entity,filename):
        """
        Loads a value function from file generated by pomdp-solve
        """
        # Parse file
        f = open(filename,'r')
        data = f.read()
        f.close()
        data = data.replace('=>',':')
        policyType = 'policyType'
        numPlanes = 'numPlanes'
        planes = 'planes'
        action = 'action'
        numEntries = 'numEntries'
        entries = 'entries'
        table = eval(data)
        # Extract value
        rule = self.rules[0]
        options = entity.actions.getOptions()
        worlds = entity.entities.getWorlds()
        for plane in table[planes]:
            option = options[int(plane[action])]
            # Extract vector
            vector = KeyedVector()
            for key in worlds.keys():
                vector[key] = 0.
            index = 0
            for entry in range(int(plane[numEntries])):
                key = WorldKey({'world': plane[entries][index]})
                index += 1
                vector[key] = plane[entries][index]
                index += 1
            vector.freeze()
            rule['values'].append({'rhs': entity.makeActionKey(option),
                                   'V': vector})

    def loadCassandra(self,entity,filename):
        """
        Loads a value function from file generated by pomdp-solve
        """
        # Parse value function
        rule = self.rules[0]
        worlds = entity.entities.getWorlds()
        phase = 'action'
        for line in fileinput.input(filename):
            if phase == 'action':
                # Parse action
                option = entity.actions.getOptions()[int(line)]
                optionString = entity.makeActionKey(option)
                phase = 'hyperplane'
            elif phase == 'hyperplane':
                # Parse V hyperplane
                values = map(float,line.split())
                assert len(values) == len(worlds)
                vector = KeyedVector()
                for index in range(len(values)):
                    vector[WorldKey({'world': index})] = values[index]
                rule['values'].append({'rhs': optionString,'V': vector})
                phase = 'whitespace'
                vector.freeze()
            elif line.strip() == '':
                phase = 'action'
        
    ## Utility methods
    
    def __str__(self,values=False):
        """Helper method that returns a string representation of the rules
        @param values: if C{True}, then print value function, not just RHS (default is C{False})
        @type values: bool
        @rtype: str
        """
        buf = cStringIO.StringIO()
        print >> buf,self._attributeHeader()
        for rule in range(len(self.rules)):
            index = self.rules[rule]['lhs']
            lhs = '\t'.join(map(lambda attr: self.attrIndex2str(attr,index[attr]),
                                range(len(self.attributes))))
            rhs = self.rules[rule]['rhs']
            if values or rhs is None:
                keys = self.rules[rule]['values'].keys()
                keys.sort()
                for key in keys:
                    value = self.rules[rule]['values'][key]
                    print >> buf,'%s\t%s\t%s' % (lhs,key,value.simpleText())
            elif isinstance(rhs,KeyedVector):
                print >> buf,'%s\t%s' % (lhs,rhs.simpleText())
            elif isinstance(rhs,str):
                print >> buf,'%s\t%s' % (lhs,rhs)
            else:
                print >> buf,'%s\t%s' % (lhs,','.join(map(str,rhs)))
        content = buf.getvalue()
        buf.close()
        return content

    def _attributeHeader(self,rhsLabel='Action'):
        """Helper method that returns column headings for the attributes
        @param rhsLabel: column heading to use for RHS (default is 'Action')
        @type rhsLabel: str
        @rtype: str
        """
        row = '\t'.join(map(lambda attr: attrString(attr[0]),
                            self.attributes))
#         row = ''
#         for obj,values in self.attributes:
#             row += '%s' % (attrString(obj))
        row += '\t%s' % (rhsLabel)
        return row

    def attrIndex2str(self,attr,index):
        """Helper method that returns a string representation of a given index into a specific attribute
        @type attr: int
        @type index: int
        @rtype: str
        """
        if index is None:
            return 'Any'
        else:
            values = self.attributes[attr][1]
            if len(values) == 1:
                if index == 0:
                    return 'F'
                else:
                    return 'T'
            else:
                if index == 0:
                    return '<%5.3f' % (values[0])
                elif index == len(values):
                    return '>%5.3f' % (values[-1])
                else:
                    return '%5.3f<x<%5.3f' % (values[index-1],values[index])

    def factorString(self,factors):
        """Helper method that returns string representation of factor tuple
        @param factors: factors (or rule index)
        @type factors: int or int[]
        """
        lhs = ''
        if not isinstance(factors,list):
            factors = self.index2factored(factors)
        for attr in range(len(self.attributes)):
            values = self.attributes[attr][1]
            if len(self.attributes[attr][0]) == 2 and values == [0.]:
                if factors[attr] == 0:
                    return (getProbRep(self.attributes[attr][0],
                                          factors[attr]))
                elif attr == len(self.attributes)-1:
                    return (getProbRep(self.attributes[attr][0],
                                          factors[attr]))
            elif factors[attr] is None:
                # All values possible
                lhs += '\tAny'
            else:
                if isinstance(factors[attr],list):
                    assert factors[attr] == range(len(values)+1)
                    # All values possible
                    lhs += '\tAny'
                else:
                    index = factors[attr]
                    if index == 0:
                        lhs += '\t<=%8.3f' % (values[index])
                    elif index == len(values):
                        lhs += '\t >%8.3f' % (values[-1])
                    else:
                        lhs += '\t<=%5.3f,>%5.3f' % (values[index-1],values[index])
        return lhs

    def factored2str(self,factors):
        """
        @return: string representation of which attributes are true
        @rtype: str
        @warning: Assumes all attributes are thresholds on 0.5
        """
        trues = []
        for index in range(len(self.attributes)):
            if factors[index]:
                trues.append(self.attributes[index][0].simpleText())
        if trues:
            return ','.join(trues)
        else:
            return 'null'
        
    def __copy__(self):
        return self.copy(self.__class__())

    def copy(self,result):
        result.attributes = self.attributes[:]
        result._attributes.clear()
        result._attributes.update(self._attributes)
        result.rules = []
        for rule in self.rules:
            new = {'lhs': rule['lhs'][:], 'rhs': rule['rhs'],'values': {}}
            if isinstance(rule['values'],dict):
                # Table form, indexed by action
                for key,value in rule['values'].items():
                    new['values'][key] = value
            else:
                # List form, series of vectors tied to actions
                assert isinstance(rule['values'],list)
                new['values'] = rule['values'][:]
            result.rules.append(new)
        return result
          
    def __xml__(self):
        doc = Document()
        root = doc.createElement('table')
        doc.appendChild(root)
        # Store attributes
        for obj,values in self.attributes:
            node = doc.createElement('attribute')
            root.appendChild(node)
            node.appendChild(obj.__xml__().documentElement)
            for value in values:
                subnode = doc.createElement('value')
                subnode.appendChild(doc.createTextNode(str(value)))
                node.appendChild(subnode)
        # Store rules
        for rule in self.rules:
            node = doc.createElement('rule')
            root.appendChild(node)
            # Store LHS
            for value in rule['lhs']:
                subnode = doc.createElement('factor')
                subnode.setAttribute('value',str(value))
                node.appendChild(subnode)
            # Store RHS
            if isinstance(rule['rhs'],list):
                # List of actions
                node.setAttribute('type','action')
                for action in rule['rhs']:
                    node.appendChild(action.__xml__().documentElement)
            elif rule['rhs'] is None:
                node.setAttribute('type','null')
            else:
                raise NotImplementedError,'Unable to store %s rules' % \
                    (rule['rhs'].__class__.__name__)
            # Store V
            node.setAttribute('format',rule['values'].__class__.__name__)
            if isinstance(rule['values'],dict):
                for key,vector in rule['values'].items():
                    if isinstance(vector,float):
                        subnode = doc.createElement('value')
                        subnode.setAttribute('value',str(vector))
                    else:
                        subnode = vector.__xml__().documentElement
                    subnode.setAttribute('action',key)
                    node.appendChild(subnode)
            else:
                assert isinstance(rule['values'],list)
                for entry in rule['values']:
                    subnode = entry['V'].__xml__().documentElement
                    subnode.setAttribute('action',entry['rhs'])
                    node.appendChild(subnode)
        return doc

    def parse(self,element):
        self.reset()
        del self.rules[0]
        assert element.tagName == 'table'
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'attribute':
                    values = []
                    subchild = node.firstChild
                    while subchild:
                        if subchild.nodeType == subchild.ELEMENT_NODE:
                            if subchild.tagName == 'value':
                                values.append(float(subchild.firstChild.data))
                            elif subchild.tagName == 'vector':
                                obj = KeyedVector()
                                obj = obj.parse(subchild)
                        subchild = subchild.nextSibling
                    self.attributes.append((obj,values))
                elif node.tagName == 'rule':
                    rule = {'lhs': [],'rhs': None}
                    if str(node.getAttribute('format')) == 'dict':
                        rule['values'] = {}
                    else:
                        assert str(node.getAttribute('format')) == 'list'
                        rule['values'] = []
                    ruleType = str(node.getAttribute('type'))
                    if ruleType == 'action':
                        rule['rhs'] = []
                    elif ruleType == 'null':
                        rule['rhs'] = None
                    else:
                        raise NameError,'Unknown rule type: %s' % (ruleType)
                    subchild = node.firstChild
                    while subchild:
                        if subchild.nodeType == node.ELEMENT_NODE:
                            if subchild.tagName == 'factor':
                                try:
                                    rule['lhs'].append(int(subchild.getAttribute('value')))
                                except ValueError:
                                    rule['lhs'].append(None)
                            elif subchild.tagName == 'action':
                                action = Action()
                                action.parse(subchild)
                                rule['rhs'].append(action)
                            elif subchild.tagName == 'vector':
                                vector = KeyedVector()
                                vector = vector.parse(subchild)
                                key = str(subchild.getAttribute('action'))
                                if str(node.getAttribute('format')) == 'dict':
                                    rule['values'][key] = vector
                                else:
                                    rule['values'].append({'rhs': key,
                                                           'V': vector})
                            elif subchild.tagName == 'value':
                                key = str(subchild.getAttribute('action'))
                                rule['values'][key] = float(subchild.getAttribute('value'))
                            elif subchild.tagName == 'matrix':
                                key = str(subchild.getAttribute('action'))
                                assert str(node.getAttribute('format')) == 'dict'
                                rule['values'][key] = KeyedMatrix()
                                rule['values'][key].parse(subchild)
                            else:
                                raise NameError,'Unknown rule node: %s' % (subchild.tagName)
                        subchild = subchild.nextSibling
                    self.rules.append(rule)
            node = node.nextSibling
        self.initialize(False)

def attrString(attr):
    """
    @return: a happy string representation of the given attribute
    @rtype: str
    """
    if isinstance(attr,KeyedVector):
        if len(attr) == 2:
            return getProbRep(attr,True)
        else:
            keys = filter(lambda k: abs(attr[k]) > epsilon,attr.keys())
            if len(attr) == 2:
                return getArrayRep(attr[keys[0]],attr[keys[1]],True)
            elif len(keys) == 1:
                return '%s>0.' % (keys[0])
            else:
                return '\t'+','.join(map(lambda x: '%6.4f' % (x),attr.getArray()))
    else:
        return ' %s action' % (attr.name)

def getVectorRep(vector,side=True):
    """
    @return: for general vector attributes
    @rtype: str
    """
    if len(vector) == 2:
        return getProbRep(vector,side)
    else:
        result = attrString(vector)
        if side:
            return result
        else:
            return result.replace('>','<')

def getProbRep(vector,side=True):
    """
    @return: for probabilistic tuples, returns a unary constraint representation of this vector
    @rtype: str
    """
    # Probabilistic tuple: ax + by > 0.
    label = getArrayRep(vector.getArray()[0],vector.getArray()[1],side)
    return label

def getArrayRep(a,b,side=True):
    """
    @return: for binary array, returns a unary constraint representation of this vector
    @rtype: str
    """
    # Probabilistic tuple: ax + by > 0.
    threshold,var = solveTuple(a,b),'L'
    if a-b < 0.:
        side = not side
    if side is None:
        sign = '??'
    elif side:
        sign = '> '
    else:
        sign = '<='
    return ' %s%s%5.3f' % (var,sign,threshold)

def solveTuple(a,b=None):
    """Solves a 2-dimensional vector for one of the variables
    @param vector: ax + by
    @type vector: L{KeyedVector}
    @return: -b/(a-b) if a!=b; otherwise, C{True} iff b>0
    @rtype: float or bool
    """
    # Solve one for the other
    if b is None:
        a,b = a.getArray()
    if abs(a-b) > epsilon:
        return -b/(a-b)
    else:
        return b > 0.
    
def detectConflict(vector1,side1,vector2,side2):
    """Detects whether there is a conflict between two attribute-value pairs, where each attribute is a binary, 2-dimensional vector
    @type side1,side2: bool
    @type vector1,vector2: L{KeyedVector}
    @return: C{True} if there is a conflict
    """
    if len(vector1) == 2 and len(vector2) == 2:
        weight1 = solveTuple(vector1)
        weight2 = solveTuple(vector2)
        # compare a > w*b attributes
        if side1 != side2:
            if side1:
                # > w1, < w2
                if weight1 > weight2-epsilon:
                    return True
            else:
                # < w1, > w2
                if weight2 > weight1-epsilon:
                    return True
#     elif len(vector1) == 1 and len(vector2) == 1:
#         raise NotImplementedError,'I should be able to do this, but my creator is lazy'
#     else:
#         raise NotImplementedError,'Your %d-dimensional vectors frighten and confuse me' % (max(len(vector1),len(vector2)))
    return False

def intersection(factors1,factors2,restrictions=None):
    """
    Does an intersection across the attribute value assignments
    @param restrictions: if provided, then a side effect appends any positions in which wildcards in C{factors1} are restricted by values in C{factors2}
    @type restrictions: int[]
    @return: the intersection, or C{None} if intersection is null
    @rtype: bool or int[]
    """
    assert len(factors1) == len(factors2)
    result = []
    for index in range(len(factors1)):
        if factors1[index] is None:
            result.append(factors2[index])
            if not restrictions is None and not factors2[index] is None:
                restrictions.append(index)
        elif factors2[index] is None:
            result.append(factors1[index])
        elif factors1[index] == factors2[index]:
            result.append(factors1[index])
        else:
            return None
    return result

def overlap(factors1,factors2):
    """
    @return: C{True} iff there are states where both LHS conditions would match
    @rtype: bool
    """
    for index in range(len(factors1)):
        if factors1[index] is not None and \
           factors2[index] is not None and \
           factors1[index] != factors2[index]:
            return False
    return True

def adjustInterval(intervals,index,key,row,debug=False):
    """Adjust a specific interval by the effect of the given row
    @param intervals: the intervals the state currently lies in
    @param index: the index of the current interval of relevance
    @param key: the state feature key being adjusted
    @param row: the effect row on the state feature
    @return: the adjusted interval
    """
    interval = intervals[index]
    if isinstance(row,UnchangedRow):
        # No change to current interval
        return interval
    elif isinstance(row,SetToFeatureRow):
        # Interval set by % of other interval
        for other in intervals:
            otherRow = other['weights']
            if isinstance(otherRow,ThresholdRow) and \
               other is not interval and \
               otherRow.specialKeys[0] == row.deltaKey:
                if row[row.deltaKey] > 0.:
                    lo = row[row.deltaKey]*other['lo']
                    hi = row[row.deltaKey]*other['hi']
                else:
                    lo = row[row.deltaKey]*other['hi']
                    hi = row[row.deltaKey]*other['lo']
                return {'lo':lo,'hi':hi}
        else:
            lo = max(-1.,interval['lo']-abs(row[row.deltaKey]))
            hi = min(1.,interval['hi']+abs(row[row.deltaKey]))
            return {'lo':lo,'hi':hi}
    elif isinstance(row,SetToConstantRow):
        # Interval set to fixed point
        lo = hi = row[row.deltaKey]
        return {'lo':lo,'hi':hi}
    elif isinstance(row,IncrementRow):
        # Interval offset by fixed amount
        lo = max(-1.,interval['lo']+row[row.deltaKey])
        hi = min(1.,interval['hi']+row[row.deltaKey])
        return {'lo':lo,'hi':hi}
    elif isinstance(row,ScaleRow):
        # Interval offset by % of other
        if row.deltaKey == key:
            lo = max(-1.,interval['lo']*row[key])
            hi = min(1.,interval['hi']*row[key])
            return {'lo':lo,'hi':hi}
        else:
            for other in intervals:
                otherRow = other['weights']
                if isinstance(otherRow,ThresholdRow) and \
                       other is not interval and \
                       otherRow.specialKeys[0] == row.deltaKey:
                    if row[row.deltaKey] > 0.:
                        delta = {'lo':row[row.deltaKey]*other['lo'],
                                 'hi':row[row.deltaKey]*other['hi']}
                    else:
                        delta = {'lo':row[row.deltaKey]*other['hi'],
                                 'hi':row[row.deltaKey]*other['lo']}
                    break
            else:
                # No constraint on this state feature
                delta = {'lo':-abs(row[row.deltaKey]),
                         'hi': abs(row[row.deltaKey])}
            lo = max(-1.,interval['lo']+delta['lo'])
            hi = min( 1.,interval['hi']+delta['hi'])
            return {'lo':lo,'hi':hi}
    else:
        # Process non-typed vector (I dream of a day when this case no longer occurs)
        assert isinstance(row,KeyedVector)
        new = {'lo':0.,'hi':0.}
        for otherKey in filter(lambda k: abs(row[k]) > 0.,row.keys()):
            if isinstance(otherKey,ConstantKey):
                new['lo'] += row[otherKey]
                new['hi'] += row[otherKey]
            else:
                for other in intervals:
                    # Process keys that are in our known intervals
                    if otherKey == other['weights'].specialKeys[0]:
                        if row[otherKey] > 0.:
                            new['lo'] += row[otherKey]*other['lo']
                            new['hi'] += row[otherKey]*other['hi']
                        else:
                            new['lo'] += row[otherKey]*other['hi']
                            new['hi'] += row[otherKey]*other['lo']
                        break
                else:
                    # Process unconstrained keys
                    new['lo'] += -abs(row[otherKey])
                    new['hi'] += abs(row[otherKey])
        if debug:
            print intervals[index]
            print row.simpleText()
            print new
        return new
##        raise NotImplementedError,'Unable to compute abstract effect for %s\n'\
##            % (row.__class__.__name__)
