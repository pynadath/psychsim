from teamwork.agent.Entities import *
from teamwork.multiagent.sequential import *
from teamwork.multiagent.GenericSociety import *
from teamwork.messages.PsychMessage import *
from teamwork.math.Interval import *
from teamwork.math.rules import applyRules,internalCheck
import copy
import random
import time
import unittest

class TestRecursiveAgentPort(unittest.TestCase):
    debug = None
    
    def setUp(self):
        """Creates the instantiated scenario used for testing"""
        from teamwork.examples.InfoShare import PortClasses
        self.society = GenericSociety()
        self.society.importDict(PortClasses.classHierarchy)
        entities = []
        self.instances = {'World':1,'FederalAuthority':1,'FirstResponder':1,'Shipper':1}
        for cls,num in self.instances.items():
            for index in range(num):
                if num > 1:
                    name = '%s%d' % (cls,index)
                else:
                    name = cls
            entities.append(self.society.instantiateEntity(cls,name))
        self.entities = SequentialAgents(entities)
        self.entities.applyDefaults()
        self.entities.compileDynamics()
        # Set up the spec of the desired test action
        entity = self.entities['FirstResponder']
        options = entity.actions.getOptions()
        for act in options:
            if act[0]['type'] == 'inspect':
                break
        else:
            # No inspection act found!
            self.fail()
        self.actions = {entity.name:act}
        # Set up the spec of the desired test message
        self.danger = Distribution({0.:0.9,
                                    0.7:0.1})
        msg = {'factors': [{'topic':'state',
                            'relation':'=','value':self.danger,
                            'lhs':['entities','Shipper','state',
                                   'containerDanger']}]}
        self.msg = Message(msg)

    def testIncorporateMessage(self):
        """Tests the hypothetical belief update produced by a message"""
        entity = self.entities['FirstResponder']
        delta,exp = entity.incorporateMessage(self.msg)
        self.assert_(isinstance(delta['state'],Distribution))
        keyList = entity.entities.getStateKeys().keys()
        keyList.sort()
        info = Distribution()
        for matrix,prob in delta['state'].items():
            self.assert_(isinstance(matrix,KeyedMatrix))
            self.assertEqual(matrix.rowKeys(),keyList)
            for rowKey in matrix.rowKeys():
                row = matrix[rowKey]
                self.assertEqual(row.keys(),keyList)
                for colKey in row.keys():
                    if isinstance(rowKey,StateKey) and \
                       rowKey['feature'] == 'containerDanger':
                        if colKey == keyConstant:
                            info[matrix[rowKey][colKey]] = prob
                        else:
                            self.assertAlmostEqual(matrix[rowKey][colKey],0.,7)
                    elif rowKey == colKey:
                        self.assertAlmostEqual(matrix[rowKey][colKey],1.,7)
                    else:
                        self.assertAlmostEqual(matrix[rowKey][colKey],0.,7)
        self.assertEqual(info,self.danger)

    def testMessage(self):
        """Tests the real belief update produced by test message"""
        entity = self.entities['FirstResponder']
        self.msg['_unobserved'] = ['Shipper','World']
        self.msg.forceAccept()
        result,delta = entity.stateEstimator(entity,
                                             {'FederalAuthority':[self.msg]})
        while entity.hasBelief('Shipper'):
            self.assertEqual(entity.getBelief('Shipper','containerDanger'),
                             self.danger)
            entity = entity.getEntity(entity.name)
        
class TestRecursiveAgentIraq(unittest.TestCase):
    debug = False
    profile = False
    
    def setUp(self):
        """Creates the instantiated scenario used for testing"""
        from teamwork.examples.PSYOP import Society
        self.society = GenericSociety()
        self.society.importDict(Society.classHierarchy)
        entities = []
        self.instances = {'GeographicArea':1,
                          'US':1,
                          'Turkomen':1,
                          'Kurds':1,
                          }
        for cls,num in self.instances.items():
            for index in range(num):
                if num > 1:
                    name = '%s%d' % (cls,index)
                else:
                    name = cls
            entity = createEntity(cls,name,self.society,PsychEntity)
            entities.append(entity)
            if entity.name in ['Turkomen','Kurds']:
                entity.relationships = {'location':['GeographicArea']}
        self.entities = SequentialAgents(entities)
        self.entities.applyDefaults()
        self.entities.compileDynamics(profile=self.profile)
        # Set up the spec of the desired test action
        entity = self.entities['Turkomen']
        options = entity.actions.getOptions()
        self.wait = None
        self.attack = None
        for act in options:
            if act[0]['type'] == 'attack':
                self.attack = act
            elif act[0]['type'] == 'wait':
                self.wait = act
        self.assert_(self.wait)
        self.assert_(self.attack)
        self.assertEqual(len(options),2)

    def verifyState(self,entity):
        """Checks whether the state vector is well formed"""
        if entity.name in ['Turkomen','Kurds']:
            allowed = ['population','politicalPower','militaryPower',
                       'economicPower']
        elif entity.name == 'US':
            allowed = ['population','militaryPower','economicPower']
        elif entity.name == 'GeographicArea':
            allowed = ['oilInfrastructure']
        else:
            self.fail()
##        if entity.parent and entity.parent.name != entity.name \
##               and entity.name != 'GeographicArea':
##            allowed.append(entity._supportFeature)
##            allowed.append(entity._trustFeature)
        # Make sure that the state contains only state for this agent
        for row in entity.state.domain():
            count = 0
            for key in row.keys():
                if isinstance(key,StateKey) and key['entity'] == entity.name:
                    count += 1
            self.assertEqual(count,len(allowed),
                             '%s has state vector of length %d, instead of %d'\
                             %(entity.ancestry(),len(row.getArray()),
                               len(allowed)))
            for key,value in row.items():
                if isinstance(key,StateKey):
                    if key['entity'] == entity.name:
                        self.assert_(key['feature'] in allowed)
                else:
                    self.assert_(isinstance(key,ConstantKey))
        # Make sure all features are covered
        keyList = entity.getStateFeatures()
        for row in entity.state.domain():
            for feature in allowed:
                key = StateKey({'entity':entity.name,'feature':feature})
                self.assert_(row.has_key(key))
                self.assert_(key['feature'] in keyList)
                keyList.remove(key['feature'])
        self.assertEqual(keyList,[])
        # Descend recursively
        for other in entity.getEntityBeliefs():
            self.verifyState(other)

    def verifyGlobalState(self,entities):
        """Checks whether the scenario state is well formed
        @param entities: the scenario to verify
        @type entities: L{PsychAgents}
        """
        state = entities.getState()
        for vector in state.domain():
            keyList = vector.keys()
            for entity in entities.members():
                self.assertEqual(id(entity.state),id(state))
                for feature in entity.getStateFeatures():
                    key = StateKey({'entity':entity.name,
                                    'feature':feature})
                    self.assert_(key in keyList)
                    keyList.remove(key)
            self.assertEqual(keyList,[keyConstant])
        
    def testLocalState(self):
        for entity in self.entities.members():
            self.verifyState(entity)
            if len(entity.entities) > 0:
                state = entity.entities.getState()
                for vector in state.domain():
                    self.assertEqual(len(vector),13)
                self.verifyGlobalState(entity.entities)
            if entity.name == 'Turkomen':
                state = entity.state.expectation()
                count = 0
                for key,value in state.items():
                    if isinstance(key,StateKey) and \
                       key['entity'] == entity.name:
                        self.assertAlmostEqual(value,.1,10)
                        count += 1
                self.assertEqual(count,4)
            elif entity.name == 'Kurds':
                state = entity.state.expectation()
                count = 0
                for key,value in state.items():
                    if isinstance(key,StateKey) and \
                       key['entity'] == entity.name:
                        if key['feature'] == 'politicalPower':
                            self.assertAlmostEqual(value,.4,10)
                        else:
                            self.assertAlmostEqual(value,.2,10)
                        count += 1
                self.assertEqual(count,4)
            elif entity.name == 'GeographicArea':
                state = entity.state.expectation()
                count = 0
                for key,value in state.items():
                    if isinstance(key,StateKey) and \
                           key['entity'] == entity.name:
                        count += 1
                        if key['feature'] == 'oilInfrastructure':
                            self.assertAlmostEqual(value,.8,10)
                        else:
                            self.fail()
                self.assertEqual(count,1)
            elif entity.name == 'US':
                state = entity.state.expectation()
                count = 0
                for key,value in state.items():
                    if isinstance(key,StateKey) and \
                       key['entity'] == entity.name:
                        self.assertAlmostEqual(value,.1,10)
                        count += 1
                self.assertEqual(count,3)
            else:
                self.fail()

    def testState(self):
        state = self.entities.getState()
        for vector in state.domain():
            self.assertEqual(len(vector),13)
        self.verifyGlobalState(self.entities)

    def testDynamics(self):
        entity = self.entities['Turkomen']
        action = self.wait[0]
        tree = self.entities.getDynamics({entity.name:self.wait})['state'].getTree()
        for matrix in tree.leaves():
            for feature in entity.getStateFeatures():
                rowKey = StateKey({'feature':feature,'entity':entity.name})
                self.assert_(matrix.has_key(rowKey))
                row = matrix[rowKey]
                if feature in ['politicalPower','population']:
                    for colKey,value in row.items():
                        if colKey == rowKey:
                            self.assertAlmostEqual(value,1.,8)
                        else:
                            self.assertAlmostEqual(value,0.,8)
        dynamics = self.entities['GeographicArea'].getDynamics(self.attack[0],'oilInfrastructure')
        tree = dynamics.getTree()
        flag = False
        for matrix in tree.leaves():
            for rowKey in matrix.rowKeys():
                if isinstance(rowKey,StateKey) and \
                       rowKey['entity'] == 'GeographicArea' and \
                       rowKey['feature'] == 'oilInfrastructure':
                    for colKey in matrix.colKeys():
                        value = matrix[rowKey][colKey]
                        if isinstance(colKey,StateKey):
                            if colKey == rowKey:
                                self.assertAlmostEqual(value,1.,8)
                            elif colKey['entity'] == 'Turkomen' and \
                                     colKey['feature'] == 'militaryPower':
                                if value < -0.05:
                                    flag = True
                            else:
                                self.assertAlmostEqual(value,0.,8)
                    break
            else:
                self.fail()
        self.assert_(flag)
        tree = self.entities.getDynamics({entity.name:self.attack})['state'].getTree()
        flag = False
        for matrix in tree.leaves():
            for rowKey in self.entities.getStateKeys().keys():
                if isinstance(rowKey,StateKey) and \
                       rowKey['entity'] == 'GeographicArea' and \
                       rowKey['feature'] == 'oilInfrastructure':
                    for colKey in self.entities.getStateKeys().keys():
                        value = matrix[rowKey][colKey]
                        if colKey == rowKey:
                            self.assertAlmostEqual(value,1.,8)
                        elif isinstance(colKey,StateKey) and \
                                 colKey['entity'] == entity.name and \
                                 colKey['feature'] == 'militaryPower':
                            if value < -.05:
                                flag = True
                        else:
                            self.assertAlmostEqual(value,0.,8)
                else:
                    for colKey in self.entities.getStateKeys().keys():
                        value = matrix[rowKey][colKey]
                        if colKey == rowKey:
                            self.assertAlmostEqual(value,1.,8)
                        else:
                            self.assertAlmostEqual(value,0.,8)
        self.assert_(flag)
        
    def verifyEffect(self,entities,action):
        """Check the result of the given action
        @param entities: the scenario to which the action has been applied
        @type entities: L{PsychAgents}
        @param action: the action performed
        @type action: L{Action}
        """
        for entity in entities.members():
            for feature in entity.getStateFeatures():
                for cls in entity.classes:
                    generic = entity.hierarchy[cls]
                    if feature in generic.getStateFeatures():
                        if feature == 'oilInfrastructure':
                            new = entity.getState(feature).domain()[0]
                            old = generic.getState(feature).domain()[0]
                            attacker = entities[action['actor']]
                            power = attacker.getState('militaryPower')
                            power = power.domain()[0]
                            diff = -.1*power
                            self.assertAlmostEqual(old+diff,new,10)
                        else:
                            new = entity.getState(feature).domain()[0]
                            old = generic.getState(feature).domain()[0]
                            self.assertAlmostEqual(new,old,10)
                        break
                else:
                    # Should be able to check belief features, too, but not right now
                    self.assertEqual(feature[0],'_')

    def testAction(self):
        name = 'Turkomen'
        entity = self.entities[name]
        key = StateKey({'entity':name,
                        'feature':self.entities.turnFeature})
        self.assertAlmostEqual(self.entities.order[key],0.25,3)
        # Check initial observation flags
        observations = self.entities.getActions()
        for obsKey,value in observations.items():
            if isinstance(obsKey,ActionKey):
                self.assertAlmostEqual(value,0.,8)
            else:
                self.assert_(isinstance(obsKey,ConstantKey))
                self.assertAlmostEqual(value,1.,8)
        # Perform action
        dynamics = self.entities.getDynamics({name:self.attack})['state'].getTree()[self.entities.getState()]
        self.assert_(self.entities['GeographicArea'].state is self.entities.state)
        result = self.entities.microstep([{'name':name,
                                           'choices':[self.attack]}])
        # Check final observation flags
        observations = self.entities.getActions()
        for obsKey,value in observations.items():
            if isinstance(obsKey,ActionKey):
                if obsKey['entity'] == name and \
                   obsKey['type'] == self.attack[0]['type'] and \
                   obsKey['object'] == self.attack[0]['object']:
                    self.assertAlmostEqual(value,1.,8)
                else:
                    self.assertAlmostEqual(value,0.,8)
            else:
                self.assert_(isinstance(obsKey,ConstantKey))
                self.assertAlmostEqual(value,1.,8)
        # Check effects on states
        for other in self.entities.members():
            self.verifyState(other)
        self.assert_(self.entities['GeographicArea'].state is self.entities.state)
        self.verifyEffect(self.entities,self.attack[0])
        for entity in self.entities.members():
            self.verifyEffect(entity.entities,self.attack[0])
            if len(entity.entities) > 0:
                self.assertAlmostEqual(entity.entities.order[key],0.,8)
            for other in entity.entities.members():
                self.verifyEffect(other.entities,self.attack[0])
        self.assertAlmostEqual(self.entities.order[key],0.,8)
        key = StateKey({'entity':'US','feature':self.entities.turnFeature})
        self.assertAlmostEqual(self.entities.order[key],0.25,3)

    def testValueAttack(self):
        self.entities.compileDynamics()
        entity = self.entities['Turkomen']
        action = {entity.name:self.attack}
        horizon = 3
        # Compute the projected value of the action over different horizons
        expected = []
        for t in range(1,horizon+1):
            value,explanation = entity.actionValue(self.attack,horizon=t)
            expected.append(value)
        # Compute the actual value of the action over different horizons
        actual = []
        self.entities.performAct(action)
        value = entity.applyGoals()
        actual.append(value)
        for t in range(horizon-1):
            next = entity.entities.next()[0]['name'] # Assume only one entity
            other = entity.getEntity(next)
            action,explanation = other.applyPolicy()
            self.entities.performAct({next:action})
            value = entity.applyGoals()
            actual.append(actual[t]+value)
        for t in range(horizon):
            self.assertEqual(expected[t],actual[t])

    def testValueWait(self):
        self.entities.compileDynamics()
        entity = self.entities['Turkomen']
        action = {entity.name:self.wait}
        horizon = 3
        # Compute the projected value of the action over different horizons
        expected = []
        for t in range(1,horizon+1):
            value,explanation = entity.actionValue(self.wait,t)
            expected.append(value)
        # Compute the actual value of the action over different horizons
        actual = []
        self.entities.performAct(action)
        value = entity.applyGoals()
        actual.append(value)
        for t in range(horizon-1):
            next = entity.entities.next()[0]['name'] # Assume only one entity
            other = entity.getEntity(next)
            action,explanation = other.applyPolicy()
            self.entities.performAct({next:action})
            value = entity.applyGoals()
            actual.append(actual[t]+value)
        for t in range(horizon):
            self.assertEqual(expected[t],actual[t])

    def testPolicy(self):
        # Verify the entity attribute on everyone's policy
        entityList = self.entities.activeMembers()
        while len(entityList) > 0:
            entity = entityList.pop()
            self.assert_(entity.policy.entity is entity)
            entityList += entity.entities.activeMembers()
        # Verify the result of applying one agent's policy
        entity = self.entities['Turkomen']
        self.entities.compileDynamics()
        values = {}
        for action in entity.actions.getOptions():
            values[action[0]],explanation = entity.actionValue(action,3)
        action,explanation = entity.applyPolicy()
        for option,value in values.items():
            if action[0] != option:
                self.assert_(float(values[action[0]]) > float(value),
                             '%s is preferred over %s, although value %s does not exceed %s' % (action[0],option,values[action[0]],value))
        # Test turn order
        order = []
        for key,value in self.entities.order.items():
            if isinstance(key,StateKey):
                order.append((value,key['entity']))
        order.sort()
        order.reverse()
        order = map(lambda t:t[1],order)
        breakdown = explanation['options'][str(action)]['breakdown']
        topOrder = order[:]
        topOrder.remove(entity.name)
        topOrder.insert(0,entity.name)
        for t0 in range(len(breakdown)):
            step = breakdown[t0]
            self.assertEqual(len(step['action']),1)
            actor = step['action'].keys()[0]
            self.assertEqual(actor,topOrder[0])
            topOrder.remove(actor)
            if len(topOrder) == 0:
                topOrder = order[:]
            decision = step['action'][actor]
            subBreakdown = step['breakdown'][actor]
            if t0 == 0:
                self.assert_(subBreakdown.has_key('forced'))
                self.assert_(subBreakdown['forced'])
            else:
                botOrder = topOrder[:]+order
                botOrder.insert(0,actor)
                subBreakdown = subBreakdown['options'][str(decision)]
                self.assert_(subBreakdown.has_key('breakdown'))
                subBreakdown = subBreakdown['breakdown']
                for t1 in range(len(subBreakdown)):
                    subStep = subBreakdown[t1]
                    self.assertEqual(len(subStep['action']),1)
                    subActor = subStep['action'].keys()[0]
                    self.assertEqual(subActor,botOrder[t1])

    def DONTtestPolicyCompilation(self):
        parent = self.entities['Turkomen'].getEntity('Kurds')
        entity = parent.getEntity('Turkomen')
        tree = entity.policy.compileTree()
        state = copy.copy(parent.entities.getState())
        for index in xrange(pow(self.granularity,len(self.keyKeys))):
            for key in self.keyKeys:
                state.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                index /= self.granularity
            decision = tree[state].domain()[0]
            best = entity.policy.getValueTree(decision)*state
            for action in entity.actions.getOptions():
                if str(action) != decision:
                    # Relies on having passed testValueFunction
                    value = entity.policy.getValueTree(action)*state
                    self.assert_(float(best) >= float(value))

    def DONTtestRuleReplacement(self):
        entity = self.entities['Turkomen']
        entity.horizon = 1
        entity.policy.depth = entity.horizon
        rules,attributes,values = entity.policy.compileRules()
        # Test dynamics extension of policy
        dynamicsRules = {}
        dynamicsAttrs = {}
        dynamicsValues = {}
        rawValues = {}
        rawAttributes = copy.copy(attributes)
        for key,action in values.items():
            actionDict = {entity.name:action}
            tree = entity.entities.getDynamics(actionDict)['state'].getTree()
            dynamicsAttrs[key] = {}
            dynamicsValues[key] = {}
            dynamicsRules[key] = tree.makeRules(dynamicsAttrs[key],
                                                dynamicsValues[key])
            rawAttributes.update(dynamicsAttrs[key])
            rawValues.update(dynamicsValues[key])
        self.assertEqual(dynamicsRules.keys(),values.keys())
        for rule in rules:
            for attr,value in rule.items():
                if attr != '_value':
                    self.assert_(rawAttributes.has_key(attr))
        for ruleSet in dynamicsRules.values():
            for rule in ruleSet:
                for attr,value in rule.items():
                    if attr != '_value':
                        self.assert_(rawAttributes.has_key(attr))
        rawRules = replaceValues(rules,rawAttributes,values,dynamicsRules,rawValues)
        state = copy.copy(self.entities.getState())
        for index in xrange(pow(self.granularity,len(self.keyKeys))):
            for key in self.keyKeys:
                state.domain()[0][key] = float(index % self.granularity)/float(self.granularity) + self.base
                index /= self.granularity
            decision = applyRules(state,rules,attributes,values,'_value',True)
            rulesMatrix = applyRules(state,dynamicsRules[str(decision)],
                                     dynamicsAttrs[str(decision)],
                                     dynamicsValues[str(decision)],'_value',True)
            raw = applyRules(state,rawRules,rawAttributes,rawValues,'_value',True)
            self.assertEqual(raw.getArray(),rulesMatrix.getArray())
            self.assertEqual(len(raw),len(rulesMatrix))
            self.assertEqual(len(raw),len(state.domainKeys()))
            self.assertEqual(len(raw.colKeys()),len(rulesMatrix.colKeys()))
            self.assertEqual(len(raw.colKeys()),len(state.domainKeys()))
            for row in rulesMatrix.keys():
                self.assert_(raw.has_key(row))
                rawRow = raw[row]
                dynRow = rulesMatrix[row]
                for col in dynRow.keys():
                    self.assert_(dynRow.has_key(col))
                    self.assert_(rawRow.has_key(col))
                    self.assertAlmostEqual(dynRow[col],rawRow[col],8)

    def DONTtestCompilationDeterminism(self):
        entity = self.entities['Turkomen']
        entity.horizon = 1
        entity.policy.depth = entity.horizon
        orig = entity.policy.compileRules()
        for index in range(1000):
            new = entity.policy.compileRules()
            self.assertEqual(orig,new)
                    
    def DONTtestPolicyPruning(self):
        target = '_value'
        entity = self.entities['Turkomen'].getEntity('Kurds')
        entity.horizon = 1
        entity.policy.depth = entity.horizon
        oldRules,oldAttrs,oldVals = entity.policy.getDynamics()
        self.verifyRuleConsistency(oldRules,oldAttrs,oldVals)
        print len(oldRules)
        newRules,newAttrs = internalCheck(oldRules[:],oldAttrs,oldVals,target)
        print len(newRules)
        self.verifyRuleEquality(oldRules,oldAttrs,oldVals,newRules,newAttrs,oldVals)

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
            dynamicsAttributes.update(step1Attrs)
            dynamicsValues.update(step1Vals)
            dynamicsRules = step1Rules

            # Compute current total reward
            totalVals = copy.copy(dynamicsValues)
            start = time.time()
            totalRules = mapValues(dynamicsRules,totalVals,lambda v:goals*v)
            print 'Evaluating:',time.time()-start
            policyValues.update(totalVals)
            policyAttributes.update(dynamicsAttributes)
            policyRules = totalRules

            # Step 2: US follows policy
            dynamicsAttributes.update(USAttrs)
            dynamicsValues.update(USVals)
            start = time.time()
##            dynamicsRules,dynamicsAttributes = self.detailedMultiply(USRules,dynamicsRules,
##                                  dynamicsAttributes,dynamicsValues)
            dynamicsRules,dynamicsAttributes = multiplyRules(USRules,dynamicsRules,
                                                             dynamicsAttributes,
                                                             dynamicsValues)
            print 'Multiplying:',time.time()-start
            print len(dynamicsRules)

            # Update running total of reward
            totalVals = copy.copy(dynamicsValues)
            start = time.time()
            totalRules = mapValues(dynamicsRules,totalVals,lambda v:goals*v)
            print 'Evaluating:',time.time()-start
            policyValues.update(totalVals)
            policyAttributes.update(dynamicsAttributes)
            policyRules = addRules(policyRules,totalRules,policyAttributes,policyValues)

            # Step 3: Kurds follow Policy
            dynamicsAttributes.update(kAttrs)
            dynamicsValues.update(kVals)
            start = time.time()
##            dynamicsRules,dynamicsAttributes = self.detailedMultiply(kRules,dynamicsRules,
##                                  dynamicsAttributes,dynamicsValues)
            dynamicsRules,dynamicsAttributes = multiplyRules(kRules,dynamicsRules,
                                                             dynamicsAttributes,
                                                             dynamicsValues)
            print 'Multiplying:',time.time()-start
            print len(dynamicsRules)

            # Update running total of reward
            totalVals = copy.copy(dynamicsValues)
            start = time.time()
            totalRules = mapValues(dynamicsRules,totalVals,lambda v:goals*v)
            print 'Evaluating:',time.time()-start
            policyValues.update(totalVals)
            policyAttributes.update(dynamicsAttributes)
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
        
    def detailedMultiply(self,set1,set2,attributes,values):
        newRules = []
        target = '_value'
        lhsKeys = filter(lambda k:k!=target,attributes.keys())
        self.assertEqual(len(lhsKeys),len(attributes)-1)
        newAttributes = {}
        for new in set1:
            for old in set2:
                matrix = values[old[target]]
                inconsistent = False
##                print 'projecting by:',matrix.simpleText()
                projectedNew = {}
                for newAttr,newValue in new.items():
                    self.assert_(attributes.has_key(newAttr))
                    if newAttr != target and newValue is not None:
##                        print '\t',newAttr,newValue
                        newPlane = attributes[newAttr]
                        weights = newPlane.weights * matrix
                        newPlane = newPlane.__class__(weights,
                                                      newPlane.threshold)
                        label = newPlane.simpleText()
                        for oldAttr,oldValue in old.items():
                            if oldAttr != target and oldValue is not None:
                                oldPlane = attributes[oldAttr]
                                result = oldPlane.compare(newPlane)
                                if result == 'equal':
                                    label = oldAttr
                                    newAttributes[oldAttr] = attributes[oldAttr]
                                    if projectedNew.has_key(oldAttr):
                                        if projectedNew[oldAttr] is None:
                                            projectedNew[oldAttr] = newValue
                                        elif newValue is not None and \
                                                 projectedNew[oldAttr] != newValue:
                                            inconsistent = True
                                    else:
                                        projectedNew[oldAttr] = newValue
                                    if projectedNew[oldAttr] is None:
                                        # Old rule takes precedence
                                        projectedNew[oldAttr] = oldValue
                                    elif projectedNew[oldAttr] != oldValue:
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
                            if newAttributes.has_key(label):
                                self.assert_(not projectedNew.has_key(label))
                                projectedNew[label] = newValue
##                                print 'new ->',label,newValue
                            elif attributes.has_key(label):
                                self.assert_(isinstance(newValue,bool))
                                if old.has_key(label) and old[label] is not None and old[label] != newValue:
                                    # Mismatch
                                    inconsistent = True
                                    break
                                self.assert_(not projectedNew.has_key(label))
                                projectedNew[label] = newValue
                                newAttributes[label] = attributes[label]
##                                print 'old ->',label,newValue
                            else:
                                # No matching plane found
##                                print 'New attribute:',label
                                newAttributes[label] = newPlane
                                lhsKeys.append(label)
                                projectedNew[label] = newValue
                    if inconsistent:
                        break
                if inconsistent:
                    # These two rules are incompatible
                    continue
                for oldAttr,oldValue in old.items():
                    if oldAttr == target or oldValue is None:
                        pass
                    elif projectedNew.has_key(oldAttr):
                        self.assertEqual(oldValue,projectedNew[oldAttr])
                    else:
                        newAttributes[oldAttr] = attributes[oldAttr]
                        projectedNew[oldAttr] = oldValue
                for key in projectedNew.keys():
                    self.assert_(newAttributes.has_key(key) or attributes.has_key(key),'Key %s is missing' % (str(key)))
                # Verify projection
                for attr,value in new.items():
                    if attr == target or value is None:
                        continue
                    oldPlane = attributes[attr]
                    plane = oldPlane.__class__(oldPlane.weights*matrix,
                                               oldPlane.threshold)
                    for key in projectedNew.keys():
                        if key != target:
                            result = newAttributes[key].compare(plane)
                            if result == 'equal':
                                break
                            elif result == 'less' and projectedNew[key] == False and new[attr] == False:
                                break
                            elif result == 'greater' and projectedNew[key] == True and new[attr] == True:
                                break
                    else:
                        self.fail()
                    self.assert_(newAttributes.has_key(key))
                    self.assert_(key in lhsKeys)
                    self.assertEqual(projectedNew[key],value,
                                     'Deviation (%s vs. %s) on %s (to %s)' % \
                                     (projectedNew[key],value,attr,key))
                # Compute new RHS
                oldValue = values[old[target]]
                newValue = values[new[target]]
                product = newValue * oldValue
                label = str(product)
                projectedNew[target] = label
                if not values.has_key(label):
                    values[label] = product
                newRules.append(projectedNew)
        for rule in newRules:
            for attr in newAttributes.keys():
                if not rule.has_key(attr):
                    rule[attr] = None
        newAttributes[target] = True
        return newRules,newAttributes
                    
    def DONTtestValueFunction(self):
        for entity in self.entities.activeMembers():
            self.verifyValueFunction(entity)

    def verifyValueFunction(self,entity):
        entity.horizon = 1
        entity.policy.depth = entity.horizon
        rules = {}
        trees = {}
        target = '_value'
        for action in entity.actions.getOptions():
            tree = entity.policy.getValueTree(action)
            attributes = {target:True}
            values = {}
            rules[str(action)] = tree.makeRules(attributes,values)
            tree = tree.__class__()
            tree = tree.fromRules(rules[str(action)],attributes,values)
            trees[str(action)] = tree
            # Verify that all values are mutually exclusive
            key = StateKey({'entity':'GeographicArea','feature':'oilInfrastructure'})
            for index1 in range(len(values)-1):
                key1,vector1 = values.items()[index1]
                for index2 in range(index1+1,len(values)):
                    key2,vector2 = values.items()[index2]
                    self.assertNotEqual(key1,key2)
                    self.assertNotEqual(vector1[key],vector2[key])
        state = copy.copy(self.entities.getState())
        goals = entity.getGoalVector()['state']
        goals.fill(state.domain()[0].keys())
        for index in xrange(pow(self.granularity,len(self.keyKeys))):
            for key in self.keyKeys:
                state.domain()[0][key] = float(index % self.granularity)/float(self.granularity)
                index /= self.granularity
            for action in entity.actions.getOptions():
                dynamics = self.entities.getDynamics({entity.name:action})
                matrix = dynamics['state'].getTree()[state].domain()[0]
                rawValue = (goals*matrix*state).domain()[0]
                tree = entity.policy.getValueTree(action)
                value = (tree*state).domain()[0]
                self.assertAlmostEqual(rawValue,value,8)
                # Test rule-based formulation of value function
                rhs = None
                for rule in rules[str(action)]:
                    for attr,truth in rule.items():
                        if attr != target and truth is not None:
                            plane = attributes[attr]
                            if plane.test(state.domain()[0]) != truth:
                                break
                    else:
                        rhs = values[rule[target]]
                self.assert_(rhs is not None)
                ruleValue = rhs*(state.domain()[0])
                self.assertAlmostEqual(ruleValue,value,8)
                ruleValue = (trees[str(action)]*state).domain()[0]
                self.assertAlmostEqual(ruleValue,value,8)
    
    def DONTtestCompile(self):
        entity = self.entities['Turkomen']
        goals = entity.getGoalTree()
        goalKeys = {}
        first = True
        for leaf in goals.leaves():
            for key in leaf.keys():
                if first:
                    goalKeys[key] = True
                else:
                    self.assert_(goalKeys.has_key(key))
                self.assert_(entity.entities.getStateKeys().has_key(key),
                             'Extraneous goal key: %s' % (str(key)))
            for key in entity.state.domainKeys():
                self.assert_(leaf.has_key(key),
                             'Missing goal key: %s' % (str(key)))
            if first:
                first = False
            else:
                self.assertEqual(len(leaf),len(goalKeys))
        goalKeys = goalKeys.keys()
        goalKeys.sort()
        uncompiled,exp = entity.applyPolicy()
        if self.profile:
            import hotshot,hotshot.stats
            filename = '/tmp/stats'
            prof = hotshot.Profile(filename)
            prof.start()
        tree = entity.policy.getActionTree(self.attack)
        for leaf in tree.leaves():
            for key in leaf.rowKeys():
                if not key in goalKeys:
                    print 'extra key:',key
            self.assertEqual(len(leaf.rowKeys()),len(goalKeys))
            self.assertEqual(len(leaf.colKeys()),len(goalKeys))
            for key in leaf.rowKeys():
                self.assert_(key in goalKeys)
            for key in leaf.colKeys():
                self.assert_(key in goalKeys)
        entity.policy.compile()
        if self.profile:
            prof.stop()
            prof.close()
            print 'loading stats...'
            stats = hotshot.stats.load(filename)
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            stats.print_stats()
        compiled,exp = entity.applyPolicy()
        self.assertEqual(uncompiled,compiled)
##        tree2 = entity.policy.getActionTree(entity,self.wait)
##        tree = tree1-tree2
##        print tree.simpleText()
##        self.entities.compile()
        
if __name__ == '__main__':
    unittest.main()
