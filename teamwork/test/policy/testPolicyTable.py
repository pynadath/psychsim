from teamwork.agent.Entities import *
from teamwork.multiagent.sequential import *
from teamwork.multiagent.GenericSociety import *
from teamwork.agent.DefaultBased import createEntity
from teamwork.math.rules import internalCheck,mergeAttributes

import time
import unittest

class TestPWLPolicy(unittest.TestCase):
    """
    @cvar filename: the temporary filename for storing profiling stats
    @cvar granularity: when exploring possible state vectors for testing, the number of points to try for each feature
    @cvar base: the offset for generating the different points for each state feature (i.e., if L{granularity} is I{n}, then the points generated will be C{base}+1/I{n}, C{base}+2/I{n}, ..., C{base}+(I{n}-1)/I{n})
    """
    filename = '/tmp/compile.prof'
    granularity = 2
    base = 0.25

    def setUp(self):
        """Creates the instantiated scenario used for testing"""
        from teamwork.examples.PSYOP import Society
        society = GenericSociety()
        society.importDict(Society.classHierarchy)
        entities = []
        self.instances = {'GeographicArea':1,
                          'US':1,
                          'Turkomen':1,
                          'Kurds':1}
        for cls,num in self.instances.items():
            for index in range(num):
                if num > 1:
                    name = '%s%d' % (cls,index)
                else:
                    name = cls
            entity = createEntity(cls,name,society,PsychEntity)
            entities.append(entity)
            if entity.name in ['Turkomen','Kurds']:
                entity.relationships = {'location':['GeographicArea']}
        self.entities = SequentialAgents(entities)
        self.entities.applyDefaults()
        self.entities.compileDynamics()
        self.keyKeys = self.entities.getStateKeys().keys()
        for key in self.keyKeys[:]:
            if isinstance(key,StateKey):
                if key['feature'] in ['economicPower','population']:
                    self.keyKeys.remove(key)
            else:
                self.keyKeys.remove(key)

    def verifyRuleConsistency(self,rules,attributes,values):
        target = '_value'
        lhs = filter(lambda k:k!=target,attributes)
        comparisons = {}
        # Check for duplicate attributes
        for index1 in range(len(lhs)-1):
            attr1 = lhs[index1]
            for index2 in range(index1+1,len(lhs)):
                attr2 = lhs[index2]
                try:
                    result = comparisons[attr2][attr1]
                except KeyError:
                    result = attributes[attr2].compare(attributes[attr1])
                    try:
                        comparisons[attr2][attr1] = result
                    except KeyError:
                        comparisons[attr2] = {attr1:result}
                self.assertNotEqual(result,'equal')
        for rule1 in rules:
            for attr in rule1.keys():
                self.assert_(attributes.has_key(attr))
        for rule1 in rules:
            for rule2 in rules:
                if rule1 is rule2:
                    continue
                for attr1,value1 in rule1.items():
                    if attr1 != target and value1 is not None:
                        # Check whether rule2 matches on this condition
                        if rule2.has_key(attr1):
                            # Check directly on this attribute
                            if rule2[attr1] != value1 and rule2[attr1] is not None:
                                # Mismatch
                                break
                        for attr2,value2 in rule2.items():
                            if attr2 != target:
                                # Check indirectly related attributes
                                try:
                                    result = comparisons[attr2][attr1]
                                except KeyError:
                                    result = attributes[attr2].compare(attributes[attr1])
                                    try:
                                        comparisons[attr2][attr1] = result
                                    except KeyError:
                                        comparisons[attr2] = {attr1:result}
                                if result == 'equal':
                                    if value1 != value2 and value2 is not None:
                                        # Mismatch
                                        break
                                elif result == 'greater' and value2 == True:
                                    if value1 == False:
                                        break
                                elif result == 'less' and value2 == False:
                                    if value1 == True:
                                        break
                        else:
                            continue
                        break
                else:
                    value1 = values[rule1[target]]
                    value2 = values[rule2[target]]
                    content = '\n'
                    for attr,val in rule1.items():
                        if attr != target and val is not None:
                            content += '%s %s\n' % (val,attr)
                    if isinstance(value1,list):
                        content += '-> %s\n\n' % (str(value1))
                    else:
                        try:
                            content += '-> %s\n\n' % (value1.simpleText())
                        except:
                            content += '-> %s\n\n' % (str(value1))
                    for attr,val in rule2.items():
                        if attr != target and val is not None:
                            content += '%s %s\n' % (val,attr)
                    if isinstance(value2,list):
                        content += '-> %s\n\n' % (str(value2))
                    else:
                        try:
                            content += '-> %s\n\n' % (value2.simpleText())
                        except:
                            content += '-> %s\n\n' % (str(value2))
                    self.assertEqual(len(value1),len(value2),content)
##                    for rowKey,row1 in value1.items():
##                        self.assert_(value2.has_key(rowKey),content)
##                        row2 = value2[rowKey]
##                        self.assertEqual(len(row1),len(row2),content)
##                        for colKey,col1 in row1.items():
##                            self.assertAlmostEqual(col1,row2[colKey],8,content)
                    self.assertEqual(value1,value2,content)
##        # Test attribute minimality
##        for index1 in range(len(lhs)-1):
##            attr1 = lhs[index1]
##            plane1 = attributes[attr1]
##            for index2 in range(index1+1,len(lhs)):
##                attr2 = lhs[index2]
##                plane2 = attributes[attr2]
##                self.assertNotEqual(plane1.compare(plane2),'equal')
##        # Test rule minimality
##        for myIndex in range(len(rules)-1):
##            myRule = rules[myIndex]
##            for yrIndex in range(myIndex+1,len(rules)):
##                yrRule = rules[yrIndex]
##                for attr in lhs:
##                    pass
        
    def verifyRuleEquality(self,rules1,attrs1,vals1,rules2,attrs2,vals2,comparison=None):
        if comparison is None:
            comparison = lambda x,y: x == y
        state = copy.copy(self.entities.getState())
        for index in xrange(pow(self.granularity,len(self.keyKeys))):
            for key in self.keyKeys:
                state.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                index /= self.granularity
            rhs1 = applyRules(state,rules1,attrs1,vals1,'_value',True)
            rhs2 = applyRules(state,rules2,attrs2,vals2,'_value',True)
            self.assertEqual(comparison(rhs1,rhs2),True,
                             'Difference found between %s and %s' % \
                             (str(rhs1),str(rhs2)))

    def testPolicyRules(self):
        for entity in self.entities.activeMembers():
            for other in entity.entities.activeMembers():
                self.verifyValueRules(other)
                self.verifyMergeRules(other)
                self.verifyPolicyRules(other)
##            self.verifyValueRules(entity)
##            self.verifyMergeRules(entity)
##            self.verifyPolicyRules(entity)
            self.verifyProjectedRules(entity)
##            self.verifyMergeRules(entity)
            self.verifyProjectedPolicy(entity)
           
    def verifyValueRules(self,entity):
        entity.horizon = 1
        entity.policy.depth = entity.horizon
        rules = {}
        trees = {}
        attributes = {}
        values = {}
        target = '_value'
        for action in entity.actions.getOptions():
            rules[str(action)],attributes[str(action)],values[str(action)] = entity.policy.getValueRules(action)
            self.verifyRuleConsistency(rules[str(action)],attributes[str(action)],
                                       values[str(action)])
        state = copy.copy(self.entities.getState())
        goals = entity.getGoalVector()['state']
        goals.fill(state.domain()[0].keys())
        for index in xrange(pow(self.granularity,len(self.keyKeys))):
            for key in self.keyKeys:
                state.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                index /= self.granularity
            for action in entity.actions.getOptions():
                dynamics = entity.entities.getDynamics({entity.name:action})
                matrix = dynamics['state'].getTree()[state].domain()[0]
                goals.fill(matrix.rowKeys())
                rawValue = (goals*matrix*state).domain()[0]
                # Test rule-based formulation of value function
                rhs = applyRules(state,rules[str(action)],
                                 attributes[str(action)],
                                 values[str(action)],'_value',True)
                self.assert_(rhs is not None)
                ruleValue = rhs*(state.domain()[0])
                self.assertAlmostEqual(ruleValue,rawValue,8,'%s has wrong value of %s' %\
                                       (entity.ancestry(),str(action)))

    def verifyMergeRules(self,entity):
##        entity.horizon = 1
##        entity.policy.depth = entity.horizon
        rules = []
        target = '_value'
        attributes = {target:True}
        values = {}
        choices = entity.actions.getOptions()
        for index in range(len(choices)):
            action = choices[index]
            subRules,subAttributes,subValues = entity.policy.getValueRules(action=action)
            self.verifyRuleConsistency(subRules,subAttributes,subValues)
            subValues = copy.copy(subValues)
            subRules = mapValues(subRules,subValues,
                                 lambda v:{'action':action,'weights':v})
            for rule in subRules:
                self.assertEqual(subValues[rule[target]]['action'], action)
            self.verifyRuleConsistency(subRules,subAttributes,subValues)
            mergeAttributes(attributes,subRules,subAttributes)
            values.update(subValues)
            if len(rules) > 0:
                rules,attributes = mergeRules(rules,action,subRules,attributes,values)
##                rules,attributes = pruneRules(rules,attributes,values)
                self.verifyRuleConsistency(rules,attributes,values)
            else:
                rules = subRules
##            rules,attributes = pruneRules(rules,attributes,values)
                self.verifyRuleConsistency(rules,attributes,values)
##            # Create the final policy
            filteredAttrs = copy.copy(attributes)
            filteredVals = copy.copy(values)
            filteredRules = mapValues(rules,filteredVals,lambda v:v['action'])
            # Verify the value
            state = copy.copy(self.entities.getState())
            for index in xrange(pow(self.granularity,len(self.keyKeys))):
                for key in self.keyKeys:
                    state.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                    index /= self.granularity
                decision1 = applyRules(state,rules,attributes,values,'_value',True)['action']
                decision2 = applyRules(state,filteredRules,filteredAttrs,
                                       filteredVals,'_value',True)
                args = (state,)+entity.policy.getValueRules(decision1)+('_value',True)
                best1 = apply(applyRules,args)*state.domain()[0]
                args = (state,)+entity.policy.getValueRules(decision2)+('_value',True)
                best2 = apply(applyRules,args)*state.domain()[0]
                for choice in choices[:index+1]:
                    # Relies on having passed testValueRules
                    args = (state,)+entity.policy.getValueRules(choice)+('_value',True)
                    value = apply(applyRules,args)*state.domain()[0]
                    self.assert_(best1 >= value,'%s incorrectly prefers %s over %s' % \
                                 (entity.ancestry(),str(decision1),str(choice)))
                    self.assert_(best2 >= value,'%s incorrectly prefers %s over %s' % \
                                 (entity.ancestry(),str(decision2),str(choice)))
##        # Check that we're matching the actual policy methods
##        altRules,altAttrs,altVals = entity.policy.buildPolicy(debug=False)
##        self.assertEqual(len(rules),len(altRules))
##        for ruleIndex in range(len(rules)):
##            rule1 = rules[ruleIndex]
##            rule2 = altRules[ruleIndex]
##            self.assertEqual(len(rule1),len(rule2))
##            for attr,value1 in rule1.items():
##                if attr != target:
##                    self.assert_(rule2.has_key(attr))
##                    self.assertEqual(rule1[attr],rule2[attr])
##        self.assertEqual(len(attributes),len(altAttrs))
##        self.assertEqual(len(values),len(altVals))
##        # Check that we're matching the actual policy methods on filtering
##        altRules,altAttrs,altVals = entity.policy.compileRules(debug=False)
##        self.assertEqual(len(filteredRules),len(altRules))
##        for ruleIndex in range(len(filteredRules)):
##            rule1 = filteredRules[ruleIndex]
##            rule2 = altRules[ruleIndex]
##            self.assertEqual(len(rule1),len(rule2))
##            for attr,value1 in rule1.items():
##                if attr != target:
##                    self.assert_(rule2.has_key(attr))
##                    self.assertEqual(rule1[attr],rule2[attr])
##        self.assertEqual(len(filteredAttrs),len(altAttrs))
##        self.assertEqual(len(filteredVals),len(altVals))

    def verifyPolicyRules(self,entity):
        entity.horizon = 1
        entity.policy.depth = entity.horizon
        rules,attributes,values = entity.policy.compileRules()
        target = '_value'
        self.verifyRuleConsistency(rules,attributes,values)
        dynRules,dynAttributes,dynValues = entity.policy.getDynamics()
        self.verifyRuleConsistency(dynRules,dynAttributes,dynValues)
        # Test dynamics extension of policy
        dynamicsRules = {}
        rawValues = {}
        rawAttributes = copy.copy(attributes)
        for key,action in values.items():
            actionDict = {entity.name:action}
            tree = entity.entities.getDynamics(actionDict)['state'].getTree()
            subAttributes = {target:True}
            subValues = {}
            dynamicsRules[key] = tree.makeRules(subAttributes,subValues)
            mergeAttributes(rawAttributes,dynamicsRules[key],subAttributes)
            rawValues.update(subValues)
        dynamicsAttributes = copy.copy(rawAttributes)
        dynamicsValues = copy.copy(rawValues)
        for rule in rules:
            for attr,value in rule.items():
                if attr != target:
                    self.assert_(rawAttributes.has_key(attr))
        for ruleSet in dynamicsRules.values():
            for rule in ruleSet:
                for attr,value in rule.items():
                    if attr != target:
                        self.assert_(rawAttributes.has_key(attr))
        rawRules = replaceValues(rules,rawAttributes,values,dynamicsRules,rawValues)
        
        prunedRules,prunedAttributes = pruneRules(rawRules,rawAttributes,rawValues)
        self.verifyRuleEquality(prunedRules,prunedAttributes,rawValues,
                                rawRules,rawAttributes,rawValues)
        self.verifyRuleEquality(prunedRules,prunedAttributes,rawValues,
                                dynRules,dynAttributes,dynValues)
        state = copy.copy(self.entities.getState())
        for index in xrange(pow(self.granularity,len(self.keyKeys))):
            for key in self.keyKeys:
                state.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                index /= self.granularity
            decision = applyRules(state,rules,attributes,values,'_value',True)
            args = (state,)+entity.policy.getValueRules(decision)+('_value',True)
            best = apply(applyRules,args)*state.domain()[0]
            for action in entity.actions.getOptions():
                if str(action) != decision:
                    # Relies on having passed testValueRules
                    args = (state,)+entity.policy.getValueRules(action)+('_value',True)
                    value = apply(applyRules,args)*state.domain()[0]
                    self.assert_(best >= value,'%s incorrectly prefers %s over %s' % \
                                 (entity.ancestry(),str(decision),str(action)))
            # Test policy-dynamics combo rules
            dynamics = entity.entities.getDynamics({entity.name:decision})
            matrix = dynamics['state'].getTree()[state]
            realState = matrix*state
            self.assertEqual(len(realState),1)
            rulesMatrix = applyRules(state,dynamicsRules[str(decision)],
                                     dynamicsAttributes,
                                     dynamicsValues,'_value',True)
            rhs = applyRules(state,dynRules,dynAttributes,dynValues,'_value',True)
            raw = applyRules(state,rawRules,rawAttributes,rawValues,'_value',True)
            pruned = applyRules(state,prunedRules,prunedAttributes,rawValues,'_value',True)
            self.assertEqual(raw,rulesMatrix,'%s differs from actual %s' % \
                             (raw.simpleText(),rulesMatrix.simpleText()))
            self.assertEqual(raw,pruned,'pruned %s differs from original %s' % \
                             (pruned.simpleText(),raw.simpleText()))
            self.assertEqual(raw,rhs)
            for row in matrix.domain()[0].rowKeys():
                realRow = matrix.domain()[0][row]
                self.assert_(rhs.has_key(row))
                ruleRow = rhs[row]
                self.assert_(raw.has_key(row))
                rawRow = raw[row]
                self.assert_(rulesMatrix.has_key(row))
                dynRow = rulesMatrix[row]
                for col in realRow.keys():
                    self.assert_(dynRow.has_key(col))
                    self.assertAlmostEqual(dynRow[col],realRow[col],8)
                    self.assert_(rawRow.has_key(col))
                    self.assertAlmostEqual(dynRow[col],rawRow[col],8)
                    self.assertAlmostEqual(rawRow[col],realRow[col],8)
                    self.assert_(ruleRow.has_key(col))
                    self.assertAlmostEqual(realRow[col],ruleRow[col],8)
            ruleState = rhs*state.domain()[0]
            for key in state.domainKeys():
                self.assertAlmostEqual(realState.domain()[0][key],
                                       ruleState[key],8)

    def DONTtestProjectionGeneration(self):
        entity = self.entities['Turkomen']
        goals = entity.getGoalTree().getValue()
        other = entity.getEntity('US')
        other.horizon = 1
        other.policy.depth = other.horizon
        start = time.time()
        USRules,USAttrs,USVals = other.policy.getDynamics()
        print other.ancestry(),time.time()-start
        self.verifyRuleConsistency(USRules,USAttrs,USVals)
        other = entity.getEntity('Kurds')
        other.horizon = 1
        other.policy.depth = other.horizon
        start = time.time()
        kRules,kAttrs,kVals = other.policy.getDynamics()
        print other.ancestry(),time.time()-start
        self.verifyRuleConsistency(kRules,kAttrs,kVals)
        state0 = copy.copy(self.entities.getState())
        for action in entity.actions.getOptions():
            print action
            # Cumulative storage of attributes and values
            policyAttributes = {'_value':True}
            policyValues = {}
            dynamicsAttributes = {'_value':True}
            dynamicsValues = {}

            # Step 1: Turkomen perform given action
            actionDict = {entity.name:action}
            step1Tree = entity.entities.getDynamics(actionDict)['state'].getTree()
            step1Attrs = {}
            step1Vals = {}
            start = time.time()
            step1Rules = step1Tree.makeRules(step1Attrs,step1Vals)
            print 'Making rules:',time.time()-start

            # Update cumulative dynamics
            mergeAttributes(dynamicsAttributes,step1Rules,step1Attrs)
            dynamicsValues.update(step1Vals)
            dynamicsRules = step1Rules
            self.verifyRuleConsistency(dynamicsRules,dynamicsAttributes,
                                       dynamicsValues)

            # Compute current total reward
            totalVals = copy.copy(dynamicsValues)
            start = time.time()
            totalRules = mapValues(dynamicsRules,totalVals,lambda v:goals*v)
            print 'Evaluating:',time.time()-start
            policyValues.update(totalVals)
            mergeAttributes(policyAttributes,totalRules,dynamicsAttributes)
            policyRules = totalRules

            # Step 2: US follows policy
            mergeAttributes(dynamicsAttributes,USRules,USAttrs)
            dynamicsValues.update(USVals)
            self.verifyRuleConsistency(dynamicsRules,dynamicsAttributes,
                                       dynamicsValues)
            self.verifyRuleConsistency(USRules,dynamicsAttributes,
                                       dynamicsValues)
            start = time.time()
##            dynamicsRules,dynamicsAttributes = self.detailedMultiply(USRules,dynamicsRules,
##                                  dynamicsAttributes,dynamicsValues)
            dynamicsRules,dynamicsAttributes = multiplyRules(USRules,dynamicsRules,
                                                             dynamicsAttributes,
                                                             dynamicsValues)
            print 'Multiplying:',time.time()-start
            print len(dynamicsRules)
            self.verifyRuleConsistency(dynamicsRules,dynamicsAttributes,
                                       dynamicsValues)

            # Update running total of reward
            totalVals = copy.copy(dynamicsValues)
            start = time.time()
            totalRules = mapValues(dynamicsRules,totalVals,lambda v:goals*v)
            print 'Evaluating:',time.time()-start
            policyValues.update(totalVals)
            mergeAttributes(policyAttributes,totalRules,dynamicsAttributes)
            policyRules = addRules(policyRules,totalRules,policyAttributes,policyValues)

            # Step 3: Kurds follow Policy
            self.verifyRuleConsistency(dynamicsRules,dynamicsAttributes,
                                       dynamicsValues)
            mergeAttributes(dynamicsAttributes,kRules,kAttrs)
            dynamicsValues.update(kVals)
            self.verifyRuleConsistency(dynamicsRules,dynamicsAttributes,
                                       dynamicsValues)
            self.verifyRuleConsistency(kRules,dynamicsAttributes,
                                       dynamicsValues)
            start = time.time()
##            dynamicsRules,dynamicsAttributes = self.detailedMultiply(kRules,dynamicsRules,
##                                  dynamicsAttributes,dynamicsValues)
            dynamicsRules,dynamicsAttributes = multiplyRules(kRules,dynamicsRules,
                                                             dynamicsAttributes,
                                                             dynamicsValues,debug=True)
            print 'Multiplying:',time.time()-start
            print len(dynamicsRules)
            self.verifyRuleConsistency(dynamicsRules,dynamicsAttributes,
                                       dynamicsValues)

            # Update running total of reward
            totalVals = copy.copy(dynamicsValues)
            start = time.time()
            totalRules = mapValues(dynamicsRules,totalVals,lambda v:goals*v)
            print 'Evaluating:',time.time()-start
            policyValues.update(totalVals)
            mergeAttributes(policyAttributes,totalRules,dynamicsAttributes)
            policyRules = addRules(policyRules,totalRules,policyAttributes,policyValues)
            
            print 'Running %d tests' % (pow(self.granularity,len(self.keyKeys)))
            for index in xrange(pow(self.granularity,len(self.keyKeys))):
                for key in self.keyKeys:
                    state0.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                    index /= self.granularity
##                print 0,state0.domain()[0].simpleText()
                real0 = state0
                rhs1 = applyRules(state0,step1Rules,step1Attrs,step1Vals,'_value',True)
                product = rhs1
                total = goals * rhs1
                state1 = Distribution({rhs1*state0.domain()[0]:1.})
                real1 = step1Tree*real0
                self.assertEqual(state1,real1)
                reward = goals*real1.domain()[0]
                self.assertAlmostEqual(reward,total*real0.domain()[0],8)
##                print 1,state1.domain()[0].simpleText()
                rhsUS = applyRules(state1,USRules,USAttrs,USVals,'_value',True)
                product = rhsUS*product
                total += goals*product
                decision,exp = entity.getEntity('US').policy.execute({'state':real1})
                step2Tree = self.entities.getDynamics({'US':decision})['state'].getTree()
                real2 = step2Tree*real1
                state2 = Distribution({rhsUS*state1.domain()[0]:1.})
                self.assertEqual(state2,real2)
                reward += goals*real2.domain()[0]
                self.assertAlmostEqual(reward,total*real0.domain()[0],8)
##                print 2,state2.domain()[0].simpleText()
                rhsKurds = applyRules(state2,kRules,kAttrs,kVals,'_value',True)
                product = rhsKurds*product
                total += goals*product
##                print result[0]
                state3 = Distribution({rhsKurds*state2.domain()[0]:1.})
                decision,exp = entity.getEntity('Kurds').policy.execute({'state':real1})
                step3Tree = self.entities.getDynamics({'Kurds':decision})['state'].getTree()
                real3 = step3Tree*real2
                self.assertEqual(state3,real3)
                reward += goals*real3.domain()[0]
                self.assertAlmostEqual(reward,total*real0.domain()[0],8)
##                print 3,state3.domain()[0].simpleText()
                projection = applyRules(state0,dynamicsRules,dynamicsAttributes,
                                        dynamicsValues,'_value',True)
##                print 'Alleged:',(projection*state0.domain()[0]).simpleText()
                self.assertEqual(product,projection,
                                 'Difference found between %s and %s' % \
                                 (product.simpleText(),projection.simpleText()))

                rhsTotal = applyRules(state0,policyRules,policyAttributes,
                                      policyValues,'_value',True)
                self.assertEqual(total,rhsTotal,'Difference found between %s and %s' % \
                                 (total.simpleText(),rhsTotal.simpleText()))

    def verifyProjectedRules(self,entity):
        sequence = entity.policy.getSequence(entity,len(self.entities.activeMembers()))
        entity.horizon = len(sequence)
        entity.policy.depth = entity.horizon
        # Pre-compile mental models
        for other in entity.getEntityBeliefs():
            if other.name != entity.name:
                other.horizon = 1
                other.policy.depth = other.horizon
                # We assume this is correct based on testPolicyRules
                other.policy.compileRules()
        state = copy.copy(entity.entities.getState())
        goals = entity.getGoalVector()['state']
        goals.fill(state.domain()[0].keys())
        target = '_value'
        for action in entity.actions.getOptions():
            actionDict = {entity.name:action}
            actionKey = string.join(map(str,actionDict.values()))
            self.assert_(self.entities.dynamics.has_key(actionKey))
            dynamics = self.entities.getDynamics(actionDict)
            tree = dynamics['state'].getTree()
            # Compile a "long-range" policy
            rules,attributes,values = entity.policy.getValueRules(action,debug=False)
            self.verifyRuleConsistency(rules,attributes,values)
##            original=copy.deepcopy((rules,attributes,values))
##            internRules,internAttrs = internalCheck(rules,attributes,values,target)
##            prunedRules,prunedAttrs = pruneRules(internRules,internAttrs,values)
##            print 'Pruning saved:',len(rules)-len(prunedRules)
##            self.assertEqual(original,(rules,attributes,values))
##            self.verifyRuleEquality(rules,attributes,values,
##                                    prunedRules,prunedAttrs,values)
            for index in xrange(pow(self.granularity,len(self.keyKeys))):
                for key in self.keyKeys:
                    state.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                    index /= self.granularity
                # Project chosen action
                current = copy.copy(state)
                stateSequence = [current]
                dynAttrs = {target:True}
                dynVals = {}
                dynRules = tree.makeRules(dynAttrs,dynVals)
                self.verifyRuleConsistency(dynRules,dynAttrs,dynVals)
                ruleMatrix = applyRules(current,dynRules,dynAttrs,dynVals,target,True)
                totalRules = copy.deepcopy(dynRules)
                totalAttrs = copy.copy(dynAttrs)
                totalVals = copy.copy(dynVals)
                matrix = tree[current]
                self.assertEqual(ruleMatrix,matrix.domain()[0],'%s differs from %s' % \
                                 (ruleMatrix.simpleText(),
                                  matrix.domain()[0].simpleText()))
                rawValue = 0.
                current = matrix*current
                stateSequence.append(current)
                rawValue += (goals*current).domain()[0]
                for t in range(1,entity.horizon):
                    other = entity.getEntity(sequence[t][0])
                    decision,exp = other.policy.execute({'state':current})
                    dynamics = self.entities.getDynamics({other.name:decision})
                    matrix = dynamics['state'].getTree()[current]
                    newRules,newAttrs,newVals = other.policy.compileRules()
                    self.verifyRuleConsistency(newRules,newAttrs,newVals)
                    newRules,newAttrs,newVals = other.policy.getDynamics()
                    newRules = copy.deepcopy(newRules)
                    self.verifyRuleConsistency(newRules,newAttrs,newVals)
                    ruleMatrix = applyRules(current,newRules,newAttrs,newVals,'_value',True)
                    mergeAttributes(dynAttrs,newRules,newAttrs)
                    dynVals.update(newVals)
                    dynRules,dynAttrs = multiplyRules(newRules,dynRules,dynAttrs,dynVals)
                    self.verifyRuleConsistency(dynRules,dynAttrs,dynVals)
                    ruleState = ruleMatrix*current.domain()[0]
                    current = matrix*current
                    stateSequence.append(current)
                    for key,value in ruleState.items():
                        self.assertAlmostEqual(value,current.domain()[0][key],8)
                    rawValue += (goals*current).domain()[0]
                # Test rule-based formulation of value function
                rhs = applyRules(state,rules,attributes,values,'_value',True)
                ruleValue = rhs*(state.domain()[0])
                if abs(ruleValue-rawValue) > .000001:
                    for index in range(len(stateSequence)):
                        print index,stateSequence[index].domain()[0]
                self.assertAlmostEqual(ruleValue,rawValue,8,
                                       'Incorrect value (%f!=%f) on %s' % \
                                       (ruleValue,rawValue,action))

    def verifyProjectedPolicy(self,entity):
        target = '_value'
        policyRules,policyAttrs,policyVals = entity.policy.compileRules()
        self.verifyRuleConsistency(policyRules,policyAttrs,policyVals)
##        internRules,internAttrs = internalCheck(policyRules,policyAttrs,policyVals,target)
##        prunedRules,prunedAttrs = pruneRules(internRules,internAttrs,policyVals)
##        print 'Pruning saved:',len(policyRules)-len(prunedRules)
##        self.verifyRuleEquality(policyRules,policyAttrs,policyVals,
##                                prunedRules,prunedAttrs,policyVals)
        state = copy.copy(entity.entities.getState())
        for index in xrange(pow(self.granularity,len(self.keyKeys))):
            for key in self.keyKeys:
                state.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                index /= self.granularity
            decision = applyRules(state,policyRules,policyAttrs,policyVals,target,True)
            valRules,valAttrs,valVals = entity.policy.getValueRules(decision)
            best = applyRules(state,valRules,valAttrs,valVals,target,True)*state.domain()[0]
            # The right thing?
            for action in entity.actions.getOptions():
                if action != decision:
                    valRules,valAttrs,valVals = entity.policy.getValueRules(action)
                    value = applyRules(state,valRules,valAttrs,valVals,'_value',True)*state.domain()[0]
                    self.assert_(best >= value,'Nope, %s not better than %s' % (best,value))
            
if __name__ == '__main__':
    unittest.main()
