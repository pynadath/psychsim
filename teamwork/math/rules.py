"""Code for manipulating a rule-based representation of PWL functions"""
import copy

__PROFILE__ = False
if __PROFILE__:
    import hotshot,hotshot.stats
    
class Rule(dict):
    """Representation of a single rule.  The left-hand side of the rule is a dictionary of attribute-value pairs.  The rule fires on inputs that whose value on each attribute matches that of the rule.  A rule with a value of C{None} for a given attribute is indifferent to the input value for the attribute.
    @ivar rhs: the value of the rule if it fires
    """
    def __init__(self,lhs={},rhs=None):
        """
        @param lhs: the initial attribute-value pairs for the left-hand side of this rule
        @type lhs: dict
        @param rhs: the right-hand side of the rule
        """
        dict.__init__(self,lhs)
        self.rhs = rhs

    def test(self,state,attributes):
        """Determines whether this rule fires under the given conditions
        @param attributes: the mapping from attribute labels to actual hyperplane conditions
        @type attributes: dict:strS{->}L{teamwork.math.matrices.Hyperplane}
        @param state: the current point to test this rule's LHS against
        @type state: L{teamwork.math.probability.Distribution}
        @return: C{True} iff this rule matches the given state
        @rtype: bool
        """
        if len(state.domain()) > 1:
            raise NotImplementedError,'Rules currently unable to handle uncertainty'
        else:
            state = state.domain()[0]
        for attr,truth in self.items():
            if truth is not None:
                plane = attributes[attr]
                if plane.test(state) != truth:
                    break
        else:
            return True
        return False
        
    def __copy__(self):
        return self.__class__(self,self.rhs)
        
def applyRules(state,rules,attributes,values,target,checkForDuplicates=False):
    if len(state.domain()) > 1:
        raise NotImplementedError,'Rules currently unable to handle uncertainty'
    else:
        state = state.domain()[0]
    rhs = []
    for rule in rules:
        for attr,truth in rule.items():
            if attr != target and truth is not None:
                plane = attributes[attr]
                if plane.test(state) != truth:
                    break
        else:
            if checkForDuplicates:
                # Accumulate all matches
                rhs.append(values[rule[target]])
            else:
                # Just exit with the first match we find
                return values[rule[target]]
    if checkForDuplicates:
        assert(len(rules) == 0 or len(rhs) > 0)
        for rule in rhs[1:]:
            assert(rule == rhs[0])
    return rhs[0]

def mergeAttributes(original,rules,new):
    for myAttr,myPlane in new.items():
        if original.has_key(myAttr):
            # Already have this attribute, so nothing to do
            pass
        elif myAttr == '_value':
            pass
        else:
            for yrAttr,yrPlane in original.items():
                if yrAttr == '_value':
                    pass
                elif yrPlane.compare(myPlane) == 'equal':
                    # Identical attribute, but with a different label
                    for rule in rules:
                        try:
                            rule[yrAttr] = rule[myAttr]
                            del rule[myAttr]
                        except KeyError:
                            # We may have more than one attribute in original that are equal to myAttr?
                            pass
                    break
            else:
                # New attribute
                original[myAttr] = myPlane

def internalCheck(rules,attributes,values,target,debug=False):
    """Test whether any redundant/inconsistent attribute assignments are present
    """
    lhs = filter(lambda k:k != target,attributes.keys())
    comparisons = {}
    newAttributes = {target:True}
    newRules = []
    for rule in rules:
        if debug:
            print
            for attr,value in rule.items():
                if attr != target: # and value is not None:
                    print value,attr
        rule = copy.copy(rule)
        newRules.append(rule)
        for myIndex in range(len(lhs)):
            myAttr = lhs[myIndex]
            myPlane = attributes[myAttr]
            for yrIndex in range(myIndex+1,len(lhs)):
                yrAttr = lhs[yrIndex]
##                assert(myAttr != yrAttr)
                yrPlane = attributes[yrAttr]
                try:
                    result = comparisons[yrAttr][myAttr]
                except KeyError:
                    result = yrPlane.compare(myPlane)
                    try:
                        comparisons[yrAttr][myAttr] = result
                    except KeyError:
                        comparisons[yrAttr] = {myAttr:result}
                if result == 'equal':
                    if isinstance(rule[myAttr],bool) and isinstance(rule[yrAttr],bool):
                        if debug:
                            print 'Attribute:',myAttr,rule[myAttr]
                            print 'Redundant given:',yrAttr,rule[yrAttr]
                        if rule[myAttr] != rule[yrAttr]:
                            # Inconsistent (unlikely to ever happen)
                            if debug:
                                print '\tRule inconsistency'
                            newRules.pop()
                    break
                elif result == 'greater' and rule.has_key(yrAttr) and rule[yrAttr] == True:
                    if debug:
                        print 'Attribute:',myAttr,rule[myAttr]
                        print 'Eliminated by greater:',yrAttr,rule[yrAttr]
                    if rule.has_key(myAttr) and rule[myAttr] == False:
                        # Inconsistent
                        if debug:
                            print '\tRule inconsistency'
                        newRules.pop()
                        break
                    else:
                        # Redundant
                        rule[myAttr] = None
                        break
                elif result == 'less' and rule.has_key(yrAttr) and rule[yrAttr] == False:
                    if debug:
                        print 'Attribute:',myAttr,rule[myAttr]
                        print 'Eliminated by lesser:',yrAttr,rule[yrAttr]
                    if rule.has_key(myAttr) and rule[myAttr] == True:
                        # Inconsistent
                        if debug:
                            print '\tRule inconsistency'
                        newRules.pop()
                        break
                    else:
                        # Redundant
                        rule[myAttr] = None
                        break
            else:
##                for yrAttr,yrPlane in newAttributes.items():
##                    assert(isinstance(yrPlane,bool) or yrPlane.compare(myPlane) != 'equal' \
##                           or (myAttr == yrAttr))
                newAttributes[myAttr] = attributes[myAttr]
            if len(newRules) == 0 or rule is not newRules[-1]:
                break
        if debug:
            print
            for attr in newAttributes.keys():
                value = rule[attr]
                if attr != target and value is not None:
                    print value,attr
            from Keys import StateKey
            try:
                print values[rule[target]][StateKey({'entity':'GeographicArea','feature':'oilInfrastructure'})]
            except KeyError:
                pass
            print '-------------------------------------------------------------------'
    for rule in newRules:
        for attr in rule.keys():
            if not newAttributes.has_key(attr):
                del rule[attr]
    if debug:
        print 'Internal inconsistencies eliminated:',
        print len(rules)-len(newRules),'rules',
        print len(attributes)-len(newAttributes),'attributes'
    return newRules,newAttributes

def clusterRules(rules,values):
    print len(rules)
    newRules = []
    lhsKeys = filter(lambda k:k!='_value',rules[0].keys())
    for value in values.keys():
        onesToRules = map(lambda i: [],range(pow(2,len(lhsKeys))))
        rulesToOnes = []
        for ruleIndex in range(len(rules)):
            rule = rules[ruleIndex]
            if rule['_value'] == value:
                ones = [0]
                for attrIndex in range(len(lhsKeys)):
                    attr = lhsKeys[attrIndex]
                    if rule[attr] == True:
                        ones = map(lambda v:v+pow(2,attrIndex),ones)
                    elif rule[attr] is None:
                        ones = sum(map(lambda v:[v,v+pow(2,attrIndex)],ones),[])
                for one in ones:
                    onesToRules[one].append(ruleIndex)
            else:
                ones = []
            rulesToOnes.append(ones)
        missing = True
        essential = {}
        for one in onesToRules:
            if len(one) == 1:
                essential[one[0]] = True
        while missing:
            missing = False
            for one in onesToRules:
                if len(one) > 0:
                    for rule in one:
                        if essential.has_key(rule):
                            # Already covered
                            break
                    else:
                        missing = True
                        essential[one[0]] = True
        for rule in essential.keys():
            newRules.append(rules[rule])
    print len(newRules)
                
def pruneRules(original,attributes,values,debug=False):
    if debug:
        print 'Starting with:',len(original)
    target = '_value'
    rules,newAttributes = internalCheck(original,attributes,values,target,debug=False)
    lhs = filter(lambda k:k != target,newAttributes.keys())
    # Cluster rules based on RHS values
    values = {}
    for rule in rules:
        try:
            values[rule[target]].append(rule)
        except KeyError:
            values[rule[target]] = [rule]
    for value,ruleSet in values.items():
        change = True
        while change:
            change = False
            newRules = []
            for myIndex in range(len(ruleSet)):
                # Loop through each rule
                myRule = ruleSet[myIndex]
                merged = []
                for yrIndex in range(myIndex+1,len(ruleSet)):
                    # Loop through any candidates for merging
                    yrRule = ruleSet[yrIndex]
                    difference = None
                    for attr in lhs:
                        try:
                            myValue = myRule[attr]
                        except KeyError:
                            myValue = None
                        try:
                            yrValue = yrRule[attr]
                        except KeyError:
                            yrValue = None
                        if isinstance(myValue,bool) and \
                               isinstance(yrValue,bool):
                            if myValue != yrValue:
                                # These rules have opposite conditions
                                if difference is None:
                                    # First difference found
                                    difference = attr
                                else:
                                    # More than one difference is useless
                                    break
                        elif myValue != yrValue:
                            # None is treated as not matching T/F
                            break
                    else:
##                        if debug:
##                            print 'Merging:'
##                            print map(lambda k:myRule[k],lhs)
##                            print map(lambda k:yrRule[k],lhs)
                        rule = copy.copy(myRule)
                        if difference is None:
                            # These two rules are identical
                            if myRule[target] != yrRule[target]:
                                raise UserWarning,'Mismatched identitical rules found'
                        else:
                            # These two rules differ in only one condition
                            rule[difference] = None
                        merged.append(rule)
                if len(merged) > 0:
                    # We merged this rule with others
                    newRules += merged
                    change = True
                else:
                    newRules.append(myRule)
            if change:
                # Find any redundant rules
                myIndex = 0
                while myIndex < len(newRules):
                    myRule = newRules[myIndex]
                    yrIndex = myIndex + 1
                    while yrIndex < len(newRules):
                        yrRule = newRules[yrIndex]
                        subsumes = True
                        isSubsumed = True
                        for attr in newAttributes.keys():
                            if attr != target:
                                try:
                                    myValue = myRule[attr]
                                except KeyError:
                                    myValue = None
                                try:
                                    yrValue = yrRule[attr]
                                except KeyError:
                                    yrValue = None
                                if isinstance(myValue,bool):
                                    if isinstance(yrValue,bool):
                                        if myValue != yrValue:
                                            # Mismatch
                                            subsumes = False
                                            isSubsumed = False
                                            break
                                    else:
                                        # yrRule is more general
                                        subsumes = False
                                elif isinstance(yrValue,bool):
                                    # yrRule is more specific
                                    isSubsumed = False
                                else:
                                    # Both are indifferent
                                    pass
                        else:
                            if subsumes:
                                # yrRule is redundant
##                                if debug:
##                                    print 'Redundancy:'
##                                    print map(lambda k:myRule[k],lhs),'subsumes'
##                                    print map(lambda k:yrRule[k],lhs)
                                if myRule[target] != yrRule[target]:
                                    raise UserWarning,'Identical conditions lead to different RHS values!'
                                else:
                                    del newRules[yrIndex]
                                    # Go on to next rule
                                    continue
                            elif isSubsumed:
                                # myRule is redundant
##                                if debug:
##                                    print 'Redundancy:'
##                                    print map(lambda k:yrRule[k],lhs),'subsumes'
##                                    print map(lambda k:myRule[k],lhs)
                                del newRules[myIndex]
                                break
                        yrIndex += 1
                    else:
                        myIndex += 1
            if debug:
                if len(ruleSet) != len(newRules):
                    print 'Reducing rule set by:',len(ruleSet)-len(newRules)
            ruleSet = newRules
            if len(ruleSet) == 1:
                # No need to continue if we're already down to one rule
                change = False
        values[value] = ruleSet
    # Check whether any conditions have been made irrelevant
    ruleSet = sum(values.values(),[])
    unused = {}
    for attr in ruleSet[0].keys():
        if attr != target and ruleSet[0][attr] is None:
            # This attribute is unused by the first rule
            unused[attr] = True
    for rule in ruleSet[1:]:
        for attr in unused.keys():
            if rule.has_key(attr) and rule[attr] is not None:
                # This attribute is used by this rule
                del unused[attr]
    # Delete any unused attributes
    for attr in unused.keys():
        del newAttributes[attr]
        for rule in ruleSet:
            if rule.has_key(attr):
                del rule[attr]
    if debug:
        print 'Overall reduction:',len(rules)-len(ruleSet)
    return ruleSet,newAttributes

def addRules(set1,set2,attributes,values):
    result = []
    target = '_value'
    lhsKeys = filter(lambda k:k!=target,attributes.keys())
    for new in set2:
        newValue = values[new[target]]
        for old in set1:
            rule = {}
            for attr in lhsKeys:
                if not old.has_key(attr):
                    old[attr] = None
                if not new.has_key(attr):
                    new[attr] = None
                if old[attr] is None:
                    # Old rule is indifferent, so use new rule
                    rule[attr] = new[attr]
                elif new[attr] is None:
                    # Old rule has restriction, but new rule is indifferent
                    rule[attr] = old[attr]
                elif old[attr] == new[attr]:
                    # Both rules have the same restriction
                    rule[attr] = old[attr]
                else:
                    # Mismatch
                    break
            else:
                oldValue = values[old[target]]
                newValue = values[new[target]]
                total = oldValue + newValue
                label = str(total)
                rule[target] = label
                if not values.has_key(label):
                    values[label] = total
                result.append(rule)
    for rule in result:
        for attr in lhsKeys:
            if not rule.has_key(attr):
                rule[attr] = None
    return result

def multiplyRules(set1,set2,attributes,values,interrupt=None):
    if __PROFILE__:
        filename = '/tmp/stats'
        prof = hotshot.Profile(filename)
        prof.start()
    comparisons = {}
    cache = {}
    newRules = []
    target = '_value'
    lhsKeys = filter(lambda k:k!=target,attributes.keys())
    newAttributes = {}
    newPlanes = {}
    for new in set1:
        for old in set2:
            # Examine every pairwise combination of rules
            matrix = values[old[target]]
            inconsistent = False
            projectedNew = {}
            for newAttr,newValue in new.items():
                if newAttr != target and newValue is not None:
                    # Transform each hyperplane in the new rule by the RHS of the old
                    try:
                        label = cache[newAttr][old[target]]
                        newPlane = newPlanes[label]
                    except KeyError:
                        newPlane = attributes[newAttr]
                        weights = newPlane.weights * matrix
                        newPlane = newPlane.__class__(weights,
                                                      newPlane.threshold)
                        label = newPlane.simpleText()
                        newPlanes[label] = newPlane
                        try:
                            cache[newAttr][old[target]] = label
                        except KeyError:
                            cache[newAttr] = {old[target]:label}
                    # Identify any conflicts/redundancies with the conditions of old rule
                    for oldAttr,oldValue in old.items():
                        if interrupt and interrupt.isSet():
                            return None
                        if oldAttr != target and oldValue is not None:
                            oldPlane = attributes[oldAttr]
                            try:
                                result = comparisons[oldAttr][label]
                            except KeyError:
                                result = oldPlane.compare(newPlane)
                                try:
                                    comparisons[oldAttr][label] = result
                                except KeyError:
                                    comparisons[oldAttr] = {label:result}
                            if result == 'equal':
                                label = oldAttr
                                for attr,plane in newAttributes.items():
                                    if attr != target and attr != label:
                                        try:
                                            result = comparisons[label][attr]
                                        except KeyError:
                                            result = newPlane.compare(plane)
                                            try:
                                                comparisons[label][attr] = result
                                            except KeyError:
                                                comparisons[label] = {attr:result}
                                        if result == 'equal':
                                            label = attr
                                            break
                                else:
                                    newAttributes[label] = attributes[label]
                                if projectedNew.has_key(label):
                                    if projectedNew[label] is None:
                                        projectedNew[label] = newValue
                                    elif newValue is not None and \
                                             projectedNew[label] != newValue:
                                        inconsistent = True
                                else:
                                    projectedNew[label] = newValue
                                if projectedNew[label] is None:
                                    # Old rule takes precedence
                                    projectedNew[label] = oldValue
                                elif projectedNew[label] != oldValue:
                                    # Mismatch
                                    inconsistent = True
                                break
                            elif result == 'greater' and oldValue == True:
                                # newAttr is guaranteed to be True
                                if newValue == False:
                                    inconsistent = True
                                break
                            elif result == 'less' and oldValue == False:
                                # newAttr is guaranteed to be False
                                if newValue == True:
                                    inconsistent = True
                                break
                    else:
                        for attr,plane in newAttributes.items():
                            if attr != target and attr != label:
                                try:
                                    result = comparisons[label][attr]
                                except KeyError:
                                    result = newPlane.compare(plane)
                                try:
                                    comparisons[label][attr] = result
                                except KeyError:
                                    comparisons[label] = {attr:result}
                                if result == 'equal':
                                    label = attr
                                    break
                        if newAttributes.has_key(label):
                            projectedNew[label] = newValue
                        elif attributes.has_key(label):
                            if old.has_key(label) and old[label] is not None and old[label] != newValue:
                                # Mismatch
                                inconsistent = True
                                break
                            projectedNew[label] = newValue
                            newAttributes[label] = attributes[label]
                            cache[newAttr][old[target]] = label
                        else:
                            # No matching plane found
                            newAttributes[label] = newPlane
                            cache[newAttr][old[target]] = label
                            lhsKeys.append(label)
                            projectedNew[label] = newValue
                if inconsistent:
                    # Once we've found an inconsistency, no need to examine rest of this rule
                    break
            if inconsistent:
                # These two rules are incompatible
                continue
            for oldAttr,oldValue in old.items():
                if oldAttr == target or oldValue is None:
                    pass
                else:
                    oldPlane = attributes[oldAttr]
                    for newAttr,newPlane in newAttributes.items():
                        if oldPlane.compare(newPlane) == 'equal':
                            break
                    else:
                        newAttributes[oldAttr] = attributes[oldAttr]
                        newAttr = oldAttr
                    if projectedNew.has_key(newAttr):
                        pass
                    else:
                        projectedNew[newAttr] = oldValue
            # Compute new RHS
            try:
                label = cache[old[target]][new[target]]
            except KeyError:
                oldValue = values[old[target]]
                newValue = values[new[target]]
                product = newValue * oldValue
                label = product.simpleText()
                if not values.has_key(label):
                    values[label] = product
                try:
                    cache[old[target]][new[target]] = label
                except KeyError:
                    cache[old[target]] = {new[target]:label}
            projectedNew[target] = label
            newRules.append(projectedNew)
    newAttributes[target] = True
    if __PROFILE__:
        prof.stop()
        prof.close()
        print 'loading stats...',len(set1), len(set2)
        stats = hotshot.stats.load(filename)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats()
        raise UserWarning
    return newRules,newAttributes

def mapValues(rules,values,op):
    """Applies a fixed transformation to the RHS of a set of rules
    @param rules: the set of rules to transform (left unchanged)
    @type rules: dict[]
    @param values: the dictionary of current RHS values
    @type values: dict
    @param op: the transformation, a function that takes a single RHS value as input and returns the new RHS value (assumed to be a 1-1 mapping)
    """
    target = '_value'
    cache = {}
    used = {}
    result = []
    for rule in rules:
        rule = copy.copy(rule)
        try:
            label = cache[rule[target]]
        except KeyError:
            newRHS = op(values[rule[target]])
            label = str(newRHS)
            cache[rule[target]] = label
            if not values.has_key(label):
                values[label] = newRHS
                used[label] = True
        rule[target] = label
        result.append(rule)
    for label in values.keys():
        if not used.has_key(label):
            del values[label]
    return result

def replaceValues(rules,attributes,oldValues,mapping,newValues):
    """Use RHS values to trigger a second set of rules, and return a merged set of the two
    @param rules: the original rule set
    @type rules: dict[]
    @param attributes: the attribute set for both sets of rules
    @type attributes: dict
    @param oldValues: the set of values for only the original set of rules
    @type oldValues: dict
    @param mapping: a dictionary of rule sets, indexed by value labels from the original set of rules
    @type mapping: dict:strS{->}dict[]
    @param newValues: the set of values for only the new set of rules
    @type newValues: dict
    @return: the new rules merging the two sets
    @rtype: dict[]
    """
    result = []
    target = '_value'
    lhsKeys = filter(lambda k:k!=target,attributes.keys())
    for old in rules:
        for new in mapping[old[target]]:
            rule = {}
            for attr in lhsKeys:
                if not old.has_key(attr) or old[attr] is None:
                    # Old rule is indifferent, so use new rule
                    try:
                        rule[attr] = new[attr]
                    except KeyError:
                        # New rule is indifferent, too
                        rule[attr] = None
                elif not new.has_key(attr) or new[attr] is None:
                    # Old rule has restriction, but new rule is indifferent
                    rule[attr] = old[attr]
                elif old[attr] == new[attr]:
                    # Both rules have the same restriction
                    rule[attr] = old[attr]
                else:
                    # Mismatch
                    break
            else:
                rule[target] = new[target]
                result.append(rule)
    return result
