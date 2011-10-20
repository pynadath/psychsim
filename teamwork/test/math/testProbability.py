from teamwork.math.Keys import *
from teamwork.math.KeyedMatrix import *
from teamwork.math.probability import *
from teamwork.math.ProbabilityTree import *
from testPWL import makeVector,makePlane
import random

import unittest

class TestProbability(unittest.TestCase):

    def setUp(self):
        distribution = Distribution()
        self.key = StateKey({'entity':'Bill',
                             'feature':'power'})
        row1 = KeyedVector({self.key:0.2})
        row2 = KeyedVector({self.key:0.4})
        self.rows = [row1,row2]
        distribution[row1] = 1.
        distribution[row2] = distribution[row1]
        self.distribution = distribution
        self.distribution.normalize()

    def testNormalize(self):
        self.assertAlmostEqual(sum(self.distribution.values()),1.,5)
        self.assertAlmostEqual(self.distribution[self.rows[0]],
                               self.distribution[self.rows[1]],5)

    def testSample(self):
        total = 10000
        counts = {}
        for element in self.distribution.domain():
            counts[element] = 0
        self.assertEqual(counts.keys(),self.distribution.domain())
        for index in range(total):
            counts[self.distribution.sample()] += 1
        for element,prob in self.distribution.items():
            self.assertAlmostEqual(float(counts[element])/float(total),prob,1)
            
    def testExpectation(self):
        eValue = self.distribution.expectation()
        self.assertEqual(eValue.keys(),[self.key])
        self.assertAlmostEqual(eValue[self.key],0.3,5)
        eValue = float(self.distribution.getMarginal(self.key))
        self.assertAlmostEqual(eValue,0.3,5)

    def testNegation(self):
        value = -self.distribution
        self.assertAlmostEqual(value.expectation()[self.key],-0.3,5)

    def testAddition(self):
        result = self.distribution + self.distribution
        self.assertEqual(len(result),3)
        for row,prob in result.items():
            if row[self.key] < 0.5:
                self.assertAlmostEqual(row[self.key],0.4,5)
                self.assertAlmostEqual(prob,0.25,5)
            elif row[self.key] < 0.7:
                self.assertAlmostEqual(row[self.key],0.6,5)
                self.assertAlmostEqual(prob,0.5,5)
            else:
                self.assertAlmostEqual(row[self.key],0.8,5)
                self.assertAlmostEqual(prob,0.25,5)

    def testSubtraction(self):
        result = self.distribution - self.distribution
        self.assertEqual(len(result),3)
        for row,prob in result.items():
            if row[self.key] < 0.:
                self.assertAlmostEqual(row[self.key],-.2,5)
                self.assertAlmostEqual(prob,0.25,5)
            elif row[self.key] < 0.1:
                self.assertAlmostEqual(row[self.key],0.,5)
                self.assertAlmostEqual(prob,0.5,5)
            else:
                self.assertAlmostEqual(row[self.key],0.2,5)
                self.assertAlmostEqual(prob,0.25,5)

    def testMultiplication(self):
        result = self.distribution * self.distribution
        self.assertEqual(len(result),3)
        for row,prob in result.items():
            if row < 0.05:
                self.assertAlmostEqual(row,0.04,5)
                self.assertAlmostEqual(prob,0.25,5)
            elif row < 0.1:
                self.assertAlmostEqual(row,0.08,5)
                self.assertAlmostEqual(prob,0.5,5)
            else:
                self.assertAlmostEqual(row,.16,5)
                self.assertAlmostEqual(prob,0.25,5)

    def testGetMarginal(self):
        distribution = Distribution()
        key = StateKey({'entity':'Bill','feature':'_trustworthiness'})
        row = KeyedVector({key:-.3})
        distribution[row] = 0.6
        row = KeyedVector({key:.3})
        distribution[row] = 0.4
        value =  self.distribution + distribution
        marginal = value.getMarginal(self.key)
        self.assertEqual(len(marginal),len(value))
        for row in value.domain():
            for val,prob in marginal.items():
                if abs(val-row[self.key]) < 0.001:
                    self.assertAlmostEqual(prob,value[row])
                    break
            else:
                self.fail()

    def testJoint(self):
        initial = len(self.distribution)
        key = StateKey({'entity':'Bill','feature':'_trustworthiness'})
        self.assertEqual(self.distribution.keys(),
                         self.distribution._domain.keys())
        self.distribution.join(key,0.3)
        self.assertEqual(self.distribution.keys(),
                         self.distribution._domain.keys())
        self.assertEqual(len(self.distribution),initial)
        marginal = self.distribution.getMarginal(key)
        self.assertEqual(marginal.keys(),marginal._domain.keys())
        self.assertAlmostEqual(marginal.domain()[0],0.3,5)
        self.assertAlmostEqual(float(marginal),0.3,5)
        distribution = Distribution({0.3:0.7,-0.3:0.3})
        self.assertEqual(distribution.keys(),distribution._domain.keys())
        self.distribution.join(key,distribution)
        self.assertEqual(len(self.distribution),2*initial)

    def testXML(self):
        doc = self.distribution.__xml__()
        new = Distribution()
        new.parse(doc.documentElement,KeyedVector)
        self.assertEqual(self.distribution,new)

class TestProbabilityTree(unittest.TestCase):

    def setUp(self):
        # Set up distribution over radar position
        self.keys = {'enemy': StateKey({'entity':'Radar',
                                        'feature':'position'}),
                     }
        self.state = Distribution()
        for position in range(2,10,2):
            row = KeyedVector({self.keys['enemy']:float(position)/10.})
            row[keyConstant] = 1.
            self.state[row] = 1.
        self.state.normalize()
        # Set up escort state
        self.keys['escort'] = StateKey({'entity':'Escort',
                                        'feature':'position'})
        marginal = Distribution({0:1.})
        self.state.join(self.keys['escort'],marginal)
        # Set up transport state
        self.keys['transport'] = StateKey({'entity':'Transport',
                                           'feature':'position'})
        marginal = Distribution({0.:1.})
        self.state.join(self.keys['transport'],marginal)
        
        for row in self.state.domain():
            row.fill(self.keys.values())
        # Set up action dynamics
        self.dynamics = {}
        tree = ProbabilityTree()
        row = KeyedVector({self.keys['escort']:1.,
                           self.keys['enemy']:-1.})
        plane = KeyedPlane(row,-.1)
        left = ProbabilityTree(IdentityMatrix('position'))
        key = StateKey({'entity':'self','feature':'position'})
        right = ProbabilityTree(ScaleMatrix('position',key,-1.))
        tree.branch(plane,left,right)
        self.dynamics['enemy'] = tree
        tree = ProbabilityTree()
        tree.makeLeaf(IncrementMatrix('position',value=0.2))
        self.dynamics['escort'] = tree
        self.dynamics['fly-normal'] = tree
        tree = ProbabilityTree()
        tree.makeLeaf(IncrementMatrix('position',value=0.1))
        self.dynamics['fly-noe'] = tree
        # Add constant factor
        tree = ProbabilityTree()
        tree.makeLeaf(KeyedMatrix({keyConstant:KeyedVector({keyConstant:1.})}))
        self.dynamics['constant'] = tree

    def testTiger(self):
        key = StateKey({'entity': 'tiger','feature':'position'})
        left = KeyedVector({key: 0.,keyConstant:1.})
        right = KeyedVector({key: 1.,keyConstant:1.})
        state = Distribution({left: 0.5,right: 0.5})
        oLeft = Distribution({'heard left': 0.85,'heard right': 0.15})
        lTree = ProbabilityTree()
        lTree.branch(oLeft)
        oRight = Distribution({'heard left': 0.15,'heard right': 0.85})
        rTree = ProbabilityTree()
        rTree.branch(oRight)
        branch = ThresholdRow(keys=[key])
        plane = KeyedPlane(branch,0.5)
        tree = ProbabilityTree()
        tree.branch(plane,falseTree=lTree,trueTree=rTree)
        result = tree[state]
        self.assertEqual(len(result),2)
        self.assertAlmostEqual(result['heard left'],0.5,10)
        self.assertAlmostEqual(result['heard right'],0.5,10)

    def testClear(self):
        self.state.clear()
        self.assertEqual(len(self.state),0)
        self.assertEqual(len(self.state.domain()),0)
        
    def testGetItem(self):
        keyList = self.keys.values()+[keyConstant]
        keyList.sort()
        # Test escort dynamics
        dynamics = self.dynamics['escort']
        table = {'self':'Escort'}
        dynamics.instantiateKeys(table)
        for row in dynamics.leaves()[0].values():
            key = StateKey({'entity':'self','feature':'position'})
            self.assert_(not row.has_key(key))
        dynamics.fill(keyList)
        self.assertEqual(len(dynamics.getValue()),len(self.keys)+1)
        self.assert_(dynamics.isLeaf())
        dynamics = dynamics[self.state]
        self.assertEqual(len(dynamics),1)
        for vector in dynamics.domain():
            self.assertEqual(len(vector),len(self.keys)+1)
        self.assertEqual(len(self.state),4)
        for vector in self.state.domain():
            self.assertEqual(len(vector),len(self.keys)+1)
        matrix = dynamics.domain()[0]
        self.assertEqual(len(matrix),len(self.keys)+1)
        for key in self.keys.values():
            row = matrix[key]
            self.assertEqual(len(row),len(self.keys)+1)
            if key['entity'] == 'Escort':
                self.assertAlmostEqual(row[keyConstant],0.2,5)
                for subKey in self.keys.values():
                    if subKey['entity'] == 'Escort':
                        self.assertAlmostEqual(row[subKey],1.,5)
                    else:
                        self.assertAlmostEqual(row[subKey],0.,5)
            else:
                for subKey in self.keys.values():
                    self.assertAlmostEqual(row[subKey],0.,5)
        self.assertAlmostEqual(matrix[keyConstant][keyConstant],0.,5)
        for key in self.keys.values():
            self.assertAlmostEqual(matrix[keyConstant][key],0.,5)

    def testDynamics(self):
        self.assertEqual(len(self.state),len(self.state.domain()))
        tables = {'escort':{'self':'Escort'},
                  'enemy':{'self':'Radar'},
                  'fly-noe':{'self':'Transport'},
                  'constant':{},
                  }
        total = None
        keyList = self.keys.values()+[keyConstant]
        keyList.sort()
        for key,table in tables.items():
            dynamics = self.dynamics[key]
            dynamics.instantiateKeys(table)
            dynamics.fill(keyList)
            if total is None:
                total = dynamics
            else:
                total += dynamics
        total.freeze()
        state = total[self.state]*self.state
        valid = map(lambda row:row[StateKey({'entity':'Radar',
                                             'feature':'position'})],
                    self.state.domain())
        self.assertEqual(len(state),len(valid))
        for vector in state.domain():
            self.assertEqual(len(vector),len(self.keys)+1)
            self.assertAlmostEqual(vector[self.keys['escort']],.2,5)
            self.assertAlmostEqual(vector[self.keys['transport']],.1,5)
            self.assertAlmostEqual(vector[keyConstant],1.,5)
            self.assert_(vector[self.keys['enemy']] in valid)

    def testXML(self):
        doc = self.dynamics['escort'].__xml__()
        new = ProbabilityTree()
        new.parse(doc.documentElement)
        self.assertEqual(self.dynamics['escort'].split,new.split)
        self.assertEqual(self.dynamics['escort'].getValue(),new.getValue())
        self.assertEqual(self.dynamics['escort'],new)

    def testMerge(self):
        # Make a 1-row matrix
        vector1 = makeVector(self.keys.values())
        key1 = random.choice(self.keys.values())
        matrix1 = KeyedMatrix({key1:vector1})
        # Make a 1-row matrix with a different row key
        key2 = key1
        while key2 == key1:
            key2 = random.choice(self.keys.values())
        vector2 = makeVector(self.keys.values())
        matrix2 = KeyedMatrix({key2:vector2})
        # Make another 1-row matrix with a different row key
        key3 = key1
        while key3 == key1 or key3 == key2:
            key3 = random.choice(self.keys.values())
        vector3 = makeVector(self.keys.values())
        matrix3 = KeyedMatrix({key3:vector3})
        # Make trees out of these matrices
        tree1 = ProbabilityTree(matrix1)
        tree2 = ProbabilityTree()
        plane2 = makePlane(self.keys.values())
        tree2.branch(plane2,
                     ProbabilityTree(matrix2),
                     ProbabilityTree(matrix3))
        # Merge them
        tree = tree1.merge(tree2,KeyedMatrix.merge)
        self.assert_(not tree.isLeaf())
        self.assertEqual(tree.split[0],plane2)
        for matrix in tree.leaves():
            self.assert_(matrix.has_key(key1))
            self.assertEqual(len(matrix),2)
            self.assertEqual(matrix[key1],vector1)
            if matrix.has_key(key2):
                self.assertEqual(matrix[key2],vector2)
            else:
                self.assert_(matrix.has_key(key3))
                self.assertEqual(matrix[key3],vector3)
        
if __name__ == '__main__':
    unittest.main()
        
