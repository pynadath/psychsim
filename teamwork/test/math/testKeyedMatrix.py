from teamwork.math.Keys import *
from teamwork.math.KeyedMatrix import *
from testPWL import TestPWL,makeDynamics,makeVector
import copy
import random
import time
import unittest

class TestKeyedVector(TestPWL):
    """
    @cvar iterations: the number of times to repeat each test
    @type iterations: int
    @cvar horizon: the number of steps to consider in a projection
    @type horizon: int
    @cvar features: a list of state features to use as test case
    @type features: C{str}[]
    @cvar agents: a list of entity names to use as test cases
    @type agents: C{str}[]
    @cvar step: the granularity of the iteration through vector space
    @type step: C{float}
    """
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
        'cleric',
        'thief',
        ]
    step = 0.5
    iterations = 10
    horizon = 10

    def setUp(self):
        self.keys = []
        for agent in self.agents:
            self.keys += map(lambda f:makeStateKey(agent,f),self.features)
        self.keys.sort()

    def firstVector(self):
        """Generate the first state vector in an exhaustive sequence
        @rtype: L{KeyedVector} instance"""
        vec = KeyedVector()
        vec.setArray()
        return vec

    def nextVector(self,vec):
        """Return the next state vector in sequence following the given one
        @param vec: the current vector from the sequence
        @type vec: L{KeyedVector} instance
        @rtype: L{KeyedVector} instance"""
        for key in self.keys + [keyConstant]:
            if vec.has_key(key):
                vec[key] += self.step
                if vec[key] > 1.:
                    del vec[key]
                else:
                    break
            else:
                vec[key] = -1.
                break
        else:
            return None
        vec.setArray()
        return vec
        
    def verifyAdd(self,row1,row2):
        """Checks a single addition between two vectors
        @type row1: L{KeyedVector}
        @type row2: L{KeyedVector}
        """
        row3 = row1 + row2
        self.assertEqual(row1.keys(),row3.keys())
        self.assertEqual(row2.keys(),row3.keys())
        for key in row1.keys():
            self.assert_(key in row3.keys())
        for key in row2.keys():
            self.assert_(key in row3.keys())
        for key in row3.keys():
            if key in row1.keys():
                if key in row2.keys():
                    self.assertAlmostEqual(row1[key]+row2[key],row3[key],8)
                else:
                    self.assertAlmostEqual(row1[key],row3[key],8)
            elif key in row2.keys():
                self.assertAlmostEqual(row2[key],row3[key],8)
            else:
                self.fail()
        
    def verifyScale(self,vec1,scale):
        """Checks a single product between vector and float scaling factor
        @param vec1: the vector to scale
        @type vec1: L{KeyedVector}
        @param scale: the factor to scale vector by
        @type scale: C{float}"""
        vec2 = vec1 * scale
        for key in vec2.keys():
            self.assert_(key in vec1.keys())
        for key in vec1.keys():
            self.assertAlmostEqual(vec2[key],vec1[key]*scale,8)
        self.assertEqual(len(vec2),len(vec1.keys()))
        
    def verifyMultiply(self,row1,row2):
        """Checks a single product between two vectors
        @type row1: L{KeyedVector}
        @type row2: L{KeyedVector}
        """
        total = 0.
        for key in row1.keys():
            try:
                total += row1[key]*row2[key]
            except KeyError:
                # Assume row2[key] == 0
                pass
        keyList = self.keys+[keyConstant]
        keyList.sort()
        row1.fill(keyList,0.)
        row1.freeze()
        row2.fill(keyList,0.)
        row2.freeze()
        result = row1 * row2
        self.assertAlmostEqual(result,total,8)

    def testMatrix(self):
        keyList = self.keys+[keyConstant]
        keyList.sort()
        size = len(keyList)
        for index in range(self.iterations):
            matrix = makeDynamics(self.keys)
            self.assertEqual(len(matrix),size)
            self.assertEqual(matrix.rowKeys(),keyList)
            colCopy = matrix.colKeys()[:]
            colCopy.sort()
            self.assertEqual(colCopy,matrix.colKeys())
            for row in matrix.values():
                self.assertEqual(row.keys(),matrix.colKeys())
            self.assertEqual(matrix.colKeys(),keyList)
            for index in range(size):
                key = keyList[index]
                self.assertEqual(matrix._rowOrder[key],index)
                other = matrix.colKeys()[index]
                self.assertEqual(other,key)
                self.assertEqual(matrix.colOrder(key),index)

    def testSet(self):
        for index in range(self.iterations):
            matrix = makeDynamics(self.keys)
            row = random.choice(self.keys)
            col = random.choice(self.keys)
            value = random.random()
            matrix.set(row,col,value)
            self.assertAlmostEqual(matrix[row][col],value,8)
            a = matrix.getArray()
            self.assertAlmostEqual(a[matrix._rowOrder[row]][matrix.colOrder(col)],value,8)
            
    def testVector(self):
        # Test filling and key ordering
        keyList = self.keys+[keyConstant]
        keyList.sort()
        size = len(keyList)
        for index in range(self.iterations):
            vector = makeVector(self.keys)
            vector.fill(keyList)
            self.assertEqual(len(vector),len(keyList))
            self.assertEqual(vector.keys(),keyList)
            for index in range(size):
                key = keyList[index]
                self.assert_(vector.has_key(key))
                self.assertEqual(vector._order[key],index)
            self.assertEqual(vector.keys(),keyList)
        # Test that setting existing keys works, too
        key = random.choice(keyList)
        vector[key] = random.random()
        self.assertEqual(len(vector),len(keyList))
        self.assertEqual(len(vector.keys()),len(keyList))
        self.assertEqual(len(vector.getArray()),len(keyList))
        # Test deletion
        del vector[key]
        self.assertEqual(len(vector),len(keyList)-1)
        self.assertEqual(len(vector.keys()),len(keyList)-1)
        self.assertEqual(len(vector.getArray()),len(keyList)-1)
        self.assert_(not vector.has_key(key))
        
    def testMatrixEdit(self):
        keyList = self.keys+[keyConstant]
        keyList.sort()
        for index in range(self.iterations):
            matrix = KeyedMatrix()
            for key in self.keys:
                if random.random() <= 0.5:
                    row = makeVector(self.keys)
                    matrix[key] = row
            matrix[keyConstant] = KeyedVector({keyConstant:1.})
            matrix.fill(keyList)
            
    def testVectorAddition(self):
        keyList = self.keys+[keyConstant]
        keyList.sort()
        for index in range(self.iterations):
            vec1 = makeVector(self.keys)
            vec1.fill(keyList)
            vec1.freeze()
            vec2 = makeVector(self.keys)
            vec2.fill(keyList)
            vec2.freeze()
            self.verifyAdd(vec1,vec2)

    def testVectorScaling(self):
        for index in range(self.iterations):
            vec1 = makeVector(self.keys)
            vec1.freeze()
            scale = random.uniform(-1.,1.)
            self.verifyScale(vec1,scale)
            
    def testVectorDotProduct(self):
        for index in range(self.iterations):
            vec1 = makeVector(self.keys)
            vec2 = makeVector(self.keys)
            self.verifyMultiply(vec1,vec2)

    def testMatrixTimesVector(self):
        for index in range(self.iterations):
            mat1 = makeDynamics(self.keys)
            self.assertEqual(mat1.colOrder(keyConstant),0.)
            self.assertEqual(mat1._rowOrder[keyConstant],0.)
            vec2 = makeVector(self.keys)
            vec2[keyConstant] = 1.
            self.verifyMatrixVector(mat1,vec2)

    def verifyMatrixVector(self,mat,vec):
        """Checks a single product between 2D and 1D matrices
        @type mat: L{KeyedMatrix}
        @type vec: L{KeyedVector}"""
        vec.fill(self.keys,0.)
        result = mat*vec
        for key in self.keys:
            self.assertAlmostEqual(result[key],mat[key]*vec,8)
        self.assertAlmostEqual(result[keyConstant],1.,8)

    def DONTtestVectorTimesMatrix(self):
        for index in range(self.iterations):
            vec1 = makeVector(self.keys)
            vec1[keyConstant] = 0.
##            vec1.fill(self.keys)
            mat2 = makeDynamics(self.keys)
            self.verifyVectorMatrix(vec1,mat2)

    def verifyVectorMatrix(self,vector,matrix):
        """Checks a single product between 1D and 2D matrices
        @type vector: L{KeyedVector}
        @type matrix: L{KeyedMatrix}
        """
        vector.fill(self.keys)
        self.assertEqual(vector.keys(),matrix.rowKeys())
        self.assertEqual(vector._order,matrix._rowOrder)
        self.assertEqual(vector.keys(),matrix.colKeys())
        self.assertEqual(vector._order,matrix.values()[0]._order)
        result = vector * matrix
        self.assertEqual(vector.keys(),result.keys())
        for col in self.keys+[keyConstant]:
            total = 0.
            for row in self.keys+[keyConstant]:
                total += vector[row]*matrix[row][col]
            self.assertAlmostEqual(result[col],total,8)
        self.assertEqual(result.getArray().shape,vector.getArray().shape)
            
    def testMatrixTimesMatrix(self):
        for index in range(self.iterations):
            state = makeVector(self.keys)
            state[keyConstant] = 1.
            state.fill(self.keys,0.)
            dynamics = makeDynamics(self.keys)
            iterative = dynamics * state
            for t in range(self.horizon):
                matrix = makeDynamics(self.keys)
                iterative = matrix * iterative
                dynamics = matrix * dynamics
            new = dynamics * state
            for key in self.keys:
                self.assertAlmostEqual(new[key],iterative[key],8)
            self.assertAlmostEqual(new[keyConstant],1.,8)
            self.assertAlmostEqual(iterative[keyConstant],1.,8)

    def testMatrixPlusMatrix(self):
        for index in range(self.iterations):
            state = makeVector(self.keys)
            state[keyConstant] = 1.
            state.fill(self.keys,0.)
            state.freeze()
            cumulative = makeDynamics(self.keys)
            cumulative.freeze()
            total = cumulative * state
            for t in range(self.horizon-1):
                matrix = makeDynamics(self.keys)
                matrix.freeze()
                total += matrix * state
                cumulative += matrix
            new = cumulative * state
            for key in self.keys:
                self.assertAlmostEqual(new[key],total[key],8)
            self.assertAlmostEqual(new[keyConstant],float(self.horizon),8)
            self.assertAlmostEqual(total[keyConstant],float(self.horizon),8)
        
    def DONTtestVectorMathExhaustive(self):
        """Verifies exhaustive space of generated math problems"""
        # Test addition
        vec1 = self.firstVector()
        while not vec1 is None:
            vec2 = self.firstVector()
            while not vec2 is None:
                self.verifyAdd(vec1,vec2)
                vec2 = self.nextVector(vec2)
            vec1 = self.nextVector(vec1)
        # Test scaling
        vec1 = self.firstVector()
        while not vec1 is None:
            scale = random.uniform(-1.,1.)
            self.verifyScale(vec1,scale)
        # Test multiplication
        vec1 = self.firstVector()
        while not vec1 is None:
            vec2 = self.firstVector()
            while not vec2 is None:
                self.verifyMultiply(vec1,vec2)
                vec2 = self.nextVector(vec2)
            vec1 = self.nextVector(vec1)

    def testDelta(self):
        typeList = getDeltaTypes()
        for cls1 in typeList.values():
            if cls1.keyClass is StateKey:
                key = random.choice(self.keys)
            elif cls1.keyClass is ConstantKey:
                key = keyConstant
            elif cls1.keyClass is ActionKey:
                continue
            else:
                self.fail()
            row1 = cls1(sourceKey=StateKey({'entity':'self',
                                            'feature':self.features[0]}),
                        deltaKey=key,value=random.uniform(-1.,1.))
            for cls2 in typeList.values():
                if cls2.keyClass is StateKey:
                    key = random.choice(self.keys)
                elif cls2.keyClass is ConstantKey:
                    key = keyConstant
                elif cls2.keyClass is ActionKey:
                    continue
                else:
                    self.fail(cls2.keyClass)
                row2 = cls2(sourceKey=StateKey({'entity':'self',
                                                'feature':self.features[1]}),
                            deltaKey=key,value=random.uniform(-1.,1.))
                row3 = row1 + row2
                if isinstance(row3,row1.__class__):
                    self.assert_(isinstance(row2,row1.__class__))
                else:
                    self.assert_(not isinstance(row3,DeltaRow))

    def testVectorCopy(self):
        for index in range(self.iterations):
            old = makeVector(self.keys)
            new = copy.copy(old)
            self.verifyVector(old,new)
            self.assert_(not old is new)

        for index in range(self.iterations):
            old = ScaleRow(sourceKey=StateKey({'entity':self.agents[0],
                                               'feature':self.features[0]}),
                           deltaKey=StateKey({'entity':self.agents[1],
                                              'feature':self.features[1]}),
                           value=0.1)
            new = copy.deepcopy(old)
            self.verifyVector(old,new)
            self.assert_(not old is new)
            
    def testVectorXML(self):
        for index in range(self.iterations):
            old = makeVector(self.keys)
            doc = old.__xml__()
            new = KeyedVector()
            new = new.parse(doc.documentElement)
            self.verifyVector(old,new)

    def testMatrixCopy(self):
        for index in range(self.iterations):
            old = makeDynamics(self.keys)
            new = copy.copy(old)
            self.verifyMatrix(old,new)
            self.assert_(not old is new)
            for key,row in old.items():
                self.assert_(new[key] is row)
        # What the heck, let's test a dynamics subclass
        feature = random.choice(self.keys)['feature']
        key = None # random.choice(self.keys)
        delta = random.random()
        old = IncrementMatrix(feature,key,delta)
        new = copy.deepcopy(old)
        self.verifyMatrix(old,new)

    def testMatrixXML(self):
        for index in range(self.iterations):
            old = makeDynamics(self.keys)
            doc = old.__xml__()
            new = KeyedMatrix()
            new.parse(doc.documentElement)
            self.verifyMatrix(old,new)

    def testFill(self):
        size = len(self.keys)+1
        keyList = self.keys+[keyConstant]
        keyList.sort()
        for index in range(self.iterations):
            matrix = KeyedMatrix()
            squares = []
            for entry in range(len(self.keys)):
                row = random.randint(0,len(keyList)-1)
                col = random.randint(0,len(keyList)-1)
                matrix.set(keyList[row],keyList[col],1.)
                squares.append((row,col))
            matrix.fill(keyList)
            # Test matrix properties
            self.assertEqual(len(matrix),size)
            self.assertEqual(matrix.getArray().shape,(size,size))
            self.assertEqual(keyList,matrix.rowKeys())
            self.assertEqual(keyList,matrix.colKeys())
            # Test individual row properties
            for vector in matrix.values():
                self.assertEqual(len(vector),size)
                self.assertEqual(vector.getArray().shape,(size,))
                self.assertEqual(keyList,vector.keys())
            # Test matrix values
            for row in range(len(keyList)):
                for col in range(len(keyList)):
                    if (row,col) in squares:
                        self.assertAlmostEqual(matrix.getArray()[row][col],1.)
                    else:
                        self.assertAlmostEqual(matrix.getArray()[row][col],0.)


    def testSetToMatrix(self):
        from teamwork.agent.Agent import Agent
        keyList = self.keys+[keyConstant]
        keyList.sort()
        table = {'self':Agent(self.agents[0])}
        for agent in self.agents:
            table[agent] = agent
        for index in range(self.iterations):
            value = random.random()
            matrix = SetToConstantMatrix(source=self.features[0],
                                         value=value)
            matrix.instantiateKeys(table)
            matrix.fill(keyList)
            old = makeVector(self.keys)
            old[keyConstant] = 1.
            old.fill(self.keys)
            key = StateKey({'entity':self.agents[0],
                            'feature':self.features[0]})
            new = matrix*old
            self.assertAlmostEqual(new[key],value,8)
        for index in range(self.iterations):
            value = random.random()
            deltaKey = StateKey({'entity':self.agents[1],
                                 'feature':self.features[1]})
            matrix = SetToFeatureMatrix(source=self.features[0],
                                        key=deltaKey,
                                        value=value)
            matrix.instantiateKeys(table)
            matrix.fill(keyList)
            old = makeVector(self.keys)
            old[keyConstant] = 1.
            old[deltaKey] = random.random()
            old.fill(self.keys)
            key = StateKey({'entity':self.agents[0],
                            'feature':self.features[0]})
            new = matrix*old
            self.assertAlmostEqual(new[key],value*old[deltaKey],8)

    def testInvert(self):
        from numpy.linalg.linalg import LinAlgError
        for index in range(self.iterations):
            done = False
            while not done:
                matrix = makeDynamics(self.keys,1.)
                try:
                    inverse = matrix.inverse()
                    done = True
                except LinAlgError:
                    pass
            result1 = matrix*inverse
            result2 = inverse*matrix
            for rowKey in matrix.rowKeys():
                for colKey in matrix.colKeys():
                    if colKey == rowKey:
                        self.assertAlmostEqual(result1[rowKey][colKey],1.,8)
                        self.assertAlmostEqual(result2[rowKey][colKey],1.,8)
                    else:
                        self.assertAlmostEqual(result1[rowKey][colKey],0.,8)
                        self.assertAlmostEqual(result2[rowKey][colKey],0.,8)
                        
if __name__ == '__main__':
    unittest.main()
