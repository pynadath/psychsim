from teamwork.math.Keys import *
from teamwork.math.KeyedMatrix import *
from teamwork.math.ProbabilityTree import *
from testPWL import TestPWL,makePlane,makeState

import random
import unittest

class TestKeyedPlane(TestPWL):
    """
    @cvar iterations: the number of times to repeat each test
    @type iterations: int
    @cvar maxReps: maximum number of random instances to test ambiguous cases
    @type maxReps: int
    @cvar features: a list of state features to use as test case
    @type features: C{str}
    @cvar agents: a list of entity names to use as test cases
    @type agents: C{str}
    """
    iterations = 100
    maxReps = 1000
    features = [
        'strength',
        'dexterity',
         'constitution',
         'intelligence',
         'charisma',
         'wisdom',
        ]
    agents = [
        'warrior',
        'wizard',
##         'cleric',
##         'thief',
        ]

    def setUp(self):
        self.keys = []
        for agent in self.agents:
            self.keys += map(lambda f:makeStateKey(agent,f),self.features)
        self.keys.sort()

    def testAlways(self):
        # Test some random planes, too
        for index in range(self.iterations):
            plane = makePlane(self.keys)
            if plane.always() == True:
                for iteration in range(100):
                    state = makeState(self.keys)
                    self.assert_(plane.test(state))
            elif plane.always() == False:
                for iteration in range(100):
                    state = makeState(self.keys)
                    self.assert_(not plane.test(state))
            else:
                # First try to test using randomly selected vectors
                last = None
                count = 1
                while count < self.maxReps:
                    state = makeState(self.keys)
                    if plane.test(state):
                        if last == 'false':
                            # Got values on both side
                            break
                        elif not last:
                            last = 'true'
                    else:
                        if last == 'true':
                            # Got values on both side
                            break
                        elif not last:
                            last = 'false'
                    count += 1
                else:
                    # Test using extreme vectors
                    lo = KeyedVector()
                    hi = KeyedVector()
                    for key in self.keys+[keyConstant]:
                        if plane.weights[key] > 0.:
                            lo[key] = -1.
                            hi[key] = 1.
                        else:
                            lo[key] = 1.
                            hi[key] = -1.
                    self.assertEqual(plane.weights.keys(),hi.keys())
                    self.assertEqual(plane.weights.keys(),lo.keys())
                    self.assert_(plane.test(hi),'%s comes up False on %s [%s*%s=%f]' % (plane.simpleText(),hi.simpleText(),str(plane.weights.getArray()),str(hi.getArray()),plane.weights*hi))
                    self.assert_(not plane.test(lo),'%s comes up True on %s' % (plane.simpleText(),lo.simpleText()))
                    
    def testComparison(self):
        for index in range(self.iterations):
            plane1 = makePlane(self.keys)
            plane1.weights.freeze()
            plane2 = copy.deepcopy(plane1)
            comparison = plane1.compare(plane2)
            self.assertEqual(comparison,'equal',
                             '%s relationship between %s and %s?' % \
                             (comparison,plane1.simpleText(),
                              plane2.simpleText()))
            self.assertEqual(plane2.compare(plane1),'equal')
        for index in range(self.iterations):
            plane1 = makePlane(self.keys)
            plane1.weights.freeze()
            plane2 = copy.deepcopy(plane1)
            plane2.weights = plane1.weights * 0.5
            self.assertEqual(plane1.compare(plane2),'less')
            self.assertEqual(plane2.compare(plane1),'greater')
            plane2.threshold = plane1.threshold * 0.25
            self.assertEqual(plane1.compare(plane2),'greater')
            self.assertEqual(plane2.compare(plane1),'less')
            plane2.threshold = plane1.threshold * 0.5
            self.assertEqual(plane1.compare(plane2),'equal')
            self.assertEqual(plane2.compare(plane1),'equal')
            plane2.weights = -plane1.weights
            plane2.threshold = -plane1.threshold
            self.assertEqual(plane1.compare(plane2),'inverse')
            self.assertEqual(plane2.compare(plane1),'inverse') 
        gtCount = 0
        ltCount = 0
        invCount = 0
        eqCount = 0
        for index in range(self.iterations):
            plane1 = makePlane(self.keys)
            plane1.weights.freeze()
            plane2 = makePlane(self.keys)
            plane2.weights.freeze()
            comparison = plane1.compare(plane2)
            if comparison == 'greater':
                gtCount += 1
                for iteration in range(100):
                    state = makeState(self.keys)
                    if plane1.test(state):
                        self.assert_(plane2.test(state))
                    if not plane2.test(state):
                        self.assert_(not plane1.test(state))
            elif comparison == 'less':
                ltCount += 1
                for iteration in range(100):
                    state = makeState(self.keys)
                    if plane2.test(state):
                        self.assert_(plane1.test(state))
                    if not plane1.test(state):
                        self.assert_(not plane2.test(state))
            elif comparison == 'inverse':
                for iteration in range(100):
                    state = makeState(self.keys)
                    self.assertNotEqual(plane1.test(state),plane2.test(state))
            elif comparison == 'equal':
                for iteration in range(100):
                    state = makeState(self.keys)
                    self.assertEqual(plane1.test(state),plane2.test(state),
                                     '%s differs from %s on %s' % \
                                     (plane1.simpleText(),plane2.simpleText(),
                                      state.simpleText()))
            else:
                self.assertEqual(comparison,'indeterminate',
                                 'Unknown comparison: %s' % (comparison))
                # Ignore always true/false planes
                if not plane1.always() is None:
                    continue
                if not plane2.always() is None:
                    continue
                eqCount += 1
                # Test using extreme vectors
                for stateIndex in xrange(pow(3,len(self.keys)+1)):
                    state = KeyedVector()
                    state[keyConstant] = float(stateIndex % 3 - 1)
                    stateIndex /= 3
                    for index in range(len(self.keys)):
                        state[self.keys[index]] = float(stateIndex % 3 - 1)
                        stateIndex /= 3
                    if plane1.test(state) != plane2.test(state):
                        # OK, we've verified that these two planes differ on at least one point
                        break
                else:
                    self.fail('Complete agreement between %s and %s [%s]' % \
                              (plane1.simpleText(),plane2.simpleText(),state.simpleText()))

    def testXML(self):
        for index in range(self.iterations):
            old = makePlane(self.keys)
            doc = old.__xml__()
            new = KeyedPlane({},0.)
            new.parse(doc.documentElement)
            self.assertAlmostEqual(old.threshold,new.threshold,8)
            self.verifyVector(old.weights,new.weights)

    def testInstantiate(self):
        from teamwork.examples.PSYOP.oil import oilPhysical
        from teamwork.agent.Agent import Agent
        tree = oilPhysical()['tree']
        branch = tree.split[0].weights
        table = dict({'actor':'Turkomen',
                      'object':'GeographicArea',
                      'type':'attack',
                      'self':Agent('GeographicArea')
                      })
        branch.instantiateKeys(table)
        ok = False
        for key in branch.keys():
            if key == keyConstant:
                self.assertAlmostEqual(branch[key],1.,8)
                ok = True
            else:
                self.assertAlmostEqual(branch[key],0.,8)
        self.assert_(ok)

    def testRelationshipRow(self):
        from teamwork.agent.RecursiveAgent import RecursiveAgent
        teacher = RecursiveAgent('MrsThompson')
        bully = RecursiveAgent('Bill')
        victim = RecursiveAgent('Victor')
        table = {'actor':bully,
                 'object':victim,
                 'type':'pickOn',
                 'self':teacher}
        row = RelationshipRow(keys=[{'feature':'student',
                                     'relatee':'actor'}])
        plane = KeyedPlane(row,0.5)
        plane = plane.instantiateKeys(table)
        self.assertEqual(plane,-1)
        teacher.relationships['student'] = [bully.name]
        row = RelationshipRow(keys=[{'feature':'student',
                                     'relatee':'actor'}])
        plane = KeyedPlane(row,0.5)
        label = plane.simpleText()
        result = plane.instantiateKeys(table)
        self.assertEqual(result,1,'Plane %s does not evaluate to always True' % (label))

    def testORPlane(self):
        for index in range(self.iterations):
            keys = {}
            for i in range(len(self.keys)/2):
                key = random.choice(self.keys)
                keys[key] = True
            keyList = map(lambda k:(k,random.choice([True,False])),
                          keys.keys())
            trueTree = ProbabilityTree()
            falseTree = ProbabilityTree()
            tree = createORTree(keyList,falseTree,trueTree)
            state = KeyedVector()
            state[keyConstant] = 1.
            for key,truth in keyList:
                if truth:
                    state[key] = 0.
                else:
                    state[key] = 1.
            tree.fill([keyConstant])
            self.assertEqual(tree.split[0].keys(),state.keys())
            self.assert_(not reduce(lambda x,y:x and y,
                                    map(lambda p:p.test(state),tree.split)),
                         '%s comes up True on %s' % \
                         (string.join(map(lambda p:p.simpleText(),tree.split),' and '),str(state)))
            for key,truth in keyList:
                if truth:
                    state[key] = 1.
                    self.assert_(reduce(lambda x,y:x and y,
                                        map(lambda p:p.test(state),tree.split)))
                    state[key] = 0.
                else:
                    state[key] = 0.
                    self.assert_(reduce(lambda x,y:x and y,
                                        map(lambda p:p.test(state),tree.split)))
                    state[key] = 1.

    def testANDPlane(self):
        for index in range(self.iterations):
            keys = {}
            for i in range(len(self.keys)/2):
                key = random.choice(self.keys)
                keys[key] = True
            keyList = map(lambda k:(k,random.choice([True,False])),
                          keys.keys())
            trueTree = ProbabilityTree()
            falseTree = ProbabilityTree()
            tree = createANDTree(keyList,falseTree,trueTree)
            tree.fill([keyConstant])
            new = copy.deepcopy(tree)
            state = KeyedVector()
            state[keyConstant] = 1.
            for key,truth in keyList:
                if truth:
                    state[key] = 1.
                else:
                    state[key] = 0.
            
            self.assert_(reduce(lambda x,y:x and y,
                                map(lambda p:p.test(state),tree.split)),
                         '%s comes up False on %s' % \
                         (string.join(map(lambda p:p.simpleText(),tree.split),' and '),str(state)))
            self.assert_(reduce(lambda x,y:x and y,
                                map(lambda p:p.test(state),new.split)),
                         '%s comes up False on %s' % \
                         (string.join(map(lambda p:p.simpleText(),new.split),' and '),str(state)))
            for key,truth in keyList:
                if truth:
                    state[key] = 0.
                    self.assert_(not reduce(lambda x,y:x and y,
                                            map(lambda p:p.test(state),tree.split)))
                    self.assert_(not reduce(lambda x,y:x and y,
                                            map(lambda p:p.test(state),new.split)))
                    state[key] = 1.
                else:
                    state[key] = 1.
                    self.assert_(not reduce(lambda x,y:x and y,
                                            map(lambda p:p.test(state),tree.split)))
                    self.assert_(not reduce(lambda x,y:x and y,
                                            map(lambda p:p.test(state),new.split)))
                    state[key] = 0.
        
if __name__ == '__main__':
    unittest.main()
