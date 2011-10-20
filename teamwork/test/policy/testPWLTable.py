from teamwork.policy.pwlTable import PWLTable,overlap,intersection
from teamwork.math.Keys import WorldKey
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedMatrix import KeyedMatrix

import copy
import random
import unittest

class TestPWLTable(unittest.TestCase):
    """
    @cvar dimension: the size of the vector (default is 16)
    @type dimension: int
    @cvar attributes: the number of LHS attributes (default is 8)
    @type attributes: int
    @cvar actions: the number of actions to define value function over (default is 5)
    @type actions: int
    """
    dimension = 4
    attributes = 4
    actions = 2

    def generateVector(self,probability=False):
        """
        @param probability: if C{True}, then make sure vector values are nonnegative and sum to 1. (default is C{False})
        @type probability: bool
        @return: a random vector
        @rtype: L{KeyedVector}
        """
        self.assert_(self.dimension > 0)
        vector = {}
        if probability:
            # Keep track of probability mass
            total = 1.
            # Last value is completely determined by previous n-1
            dimension = self.dimension - 1
        else:
            dimension = self.dimension
        for world in range(dimension):
            key = WorldKey({'world': world})
            if probability:
                # Assign part of remaining mass
                value = random.random()*total
                total -= value
            else:
                # Assign random number from [-1,1]
                value = random.random()*2. - 1.
            vector[key] = value
        if probability:
            # Add remaining probability mass to final world
            key = WorldKey({'world': dimension})
            vector[key] = total
        return KeyedVector(vector)

    def generateMatrix(self,probability=False):
        """
        @param probability: if C{True}, then make sure values are nonnegative and that matrix columns sum to 1. (default is C{False})
        @type probability: bool
        @return: a random matrix
        @rtype: L{KeyedMatrix}
        """
        self.assert_(self.dimension > 0)
        if not probability:
            raise NotImplementedError
        vectors = []
        for world in range(self.dimension):
            vectors.append(self.generateVector(probability))
        matrix = KeyedMatrix()
        for row in range(self.dimension):
            rowKey = WorldKey({'world':row})
            for col in range(self.dimension):
                colKey = WorldKey({'world':col})
                matrix.set(rowKey,colKey,vectors[col][rowKey])
        for colKey in matrix.rowKeys():
            total = 0.
            for rowKey in matrix.rowKeys():
                total += matrix[rowKey][colKey]
            self.assertAlmostEqual(total,1.,8)
        return matrix
    
    def generateAttributes(self):
        """
        Generates an initialized table with random LHS conditions, but no RHS
        @return: a table with random LHS attributes
        @rtype: L{PWLTable}
        """
        table = PWLTable()
        while len(table.attributes) < self.attributes:
            table.addAttribute(self.generateVector(False),0.)
        table.initialize()
        return table

    def generateLHS(self,table):
        """Generates a set of rules with no RHS
        @param table: initialized table
        @type table: L{PWLTable}
        """
        # Start with all wild cards
        for iteration in range(len(table.attributes)):
            # Pick a condition to split
            falsePath = random.choice(table.rules)
            # We assume there is no RHS yet
            assert falsePath['rhs'] is None
            assert falsePath['values'] == {}
            table.rules.remove(falsePath)
            # Find the remaining wild card elements
            candidates = filter(lambda i: falsePath['lhs'][i] is None,
                                range(len(falsePath['lhs'])))
            if len(candidates) == 0:
                continue
            # Randomly choose a wild card to split on
            index = random.choice(candidates)
            # True
            truePath = {'lhs': falsePath['lhs'][:],'values':{},
                        'rhs': None}
            truePath['lhs'][index] = 1
            table.rules.append(truePath)
            # False
            falsePath['lhs'][index] = 0
            table.rules.append(falsePath)
        
    def generateRHS(self,table,matrix=False,probability=False):
        """
        Fills in random RHS value function for the given table
        @param table: initialized table
        @type table: L{PWLTable}
        @param matrix: if C{True}, use matrices in RHS; otherwise, use vectors (default is C{False}, i.e., vectors)
        @type matrix: bool
        @param probability: if C{True}, then make sure vector values are nonneagtive and sum to 1. (default is C{False})
        @type probability: bool
        @warning: the table is modified in place
        """
        for rule in table.rules:
            for action in range(self.actions):
                if matrix:
                    rhs = self.generateMatrix(probability)
                else:
                    rhs = self.generateVector(probability)
                rule['values']['Action %d' % (action)] = rhs

    def generateV(self):
        """
        @return: a suitable value function
        """
        table = self.generateAttributes()
        self.generateLHS(table)
        self.generateRHS(table)
        return table

    def generateT(self):
        """
        @return: a suitable belief mapping
        """
        table = self.generateAttributes()
        self.generateLHS(table)
        self.generateRHS(table,matrix=True,probability=True)
        return table
        
    def testAddAttribute(self):
        for iteration in range(10):
            table = PWLTable()
            cache = {}
            count = self.attributes
            for attr in range(count):
                vector = self.generateVector()
                table.addAttribute(vector,0.)
                if cache.has_key(vector):
                    count -= 1
                else:
                    cache[vector] = True
                table.addAttribute(copy.copy(vector),0.5)
            # Test that uniqueness is preserved
            self.assertEqual(len(table.attributes),count)
            for attr in range(len(table.attributes)-1):
                # Test that attributes are sorted
                self.assert_(list(table.attributes[attr][0].getArray()) < \
                                 list(table.attributes[attr+1][0].getArray()),
                             '%s >= %s' % (table.attributes[attr][0],
                                           table.attributes[attr+1][0]))
                # Test that values are correct
                self.assertEqual(len(table.attributes[attr][1]),2)
                self.assertAlmostEqual(table.attributes[attr][1][0],0.)
                self.assertAlmostEqual(table.attributes[attr][1][1],0.5)
            self.assertEqual(len(table.attributes[-1][1]),2)
            self.assertAlmostEqual(table.attributes[-1][1][0],0.)
            self.assertAlmostEqual(table.attributes[-1][1][1],0.5)
            # Test null table
            table.initialize()
            for state in range(10):
                rhs = table[self.generateVector()]
                self.assertEqual(rhs['rhs'],None)

    def verifyTable(self,table):
        """Verifies that table LHS is a partition (i.e., is exhaustive and mutually exclusive)
        """
        # Check exhaustiveness
        for attempt in range(100):
            state = self.generateVector(probability=True)
            factors = table.getFactors(state)
            indices = table.match(factors,True)
            # Check exclusivity through sampling
            self.assertEqual(len(indices),1)
        # Check exclusivity through LHS comparison
        for index1 in range(len(table.rules)-1):
            rule1 = table.rules[index1]
            for rule2 in table.rules[index1+1:]:
                self.assertFalse(overlap(rule1['lhs'],rule2['lhs']))
            
    def testGeneration(self):
        """
        Test for test case generation
        """
        for iteration in range(100):
            table = self.generateAttributes()
            self.generateLHS(table)
            self.verifyTable(table)
            
    def testMax(self):
        """
        @note: tests C{star} method as well
        """
        for iteration in range(10):
            V = self.generateV()
            original = copy.deepcopy(V.rules)
            Vmax = V.max(debug=False)
            self.verifyTable(Vmax)
            Vstar = Vmax.star()
            for subiteration in range(10):
                state = self.generateVector(probability=True)
                maxRule = Vmax[state]
                self.assert_(isinstance(maxRule['rhs'],str))
                origRule = V[state]
                target = origRule['values'][maxRule['rhs']]*state
                for action,weights in origRule['values'].items():
                    ER = weights*state
                    if action == maxRule['rhs']:
                        self.assertAlmostEqual(target,ER,8)
                    else:
                        self.assert_(target >= ER,target-ER)
                ER = Vstar[state]['rhs']*state
                self.assertAlmostEqual(target,ER,8)

    def testMerge(self):
        for iteration in range(10):
            V1 = self.generateV()
            V2 = self.generateV()
            Vmerge = V1.mergeZero(V2)
            self.verifyTable(Vmerge)

    def verifySum(self,add1,add2,total):
        """Verifies that add1+add2=total
        """
        for subiteration in range(100): 
            state = self.generateVector(probability=True)
            RHS = total[state]
            for action,V in RHS['values'].items():
                ER = V*state
                target = add1[state]['values'][action]*state
                target += add2[state]['values'][action]*state
                self.assertAlmostEqual(target,ER,8)
        
    def testAdd(self):
        for iteration in range(10):
            V1 = self.generateV()
            V2 = self.generateV()
            Vsum = V1 + V2
            self.verifyTable(Vsum)
            self.verifySum(V1,V2,Vsum)

    def testOverlap(self):
        """
        @note: tests intersection, too
        """
        for iteration in range(100):
            factors1 = map(lambda i: random.choice([0,1,None]),
                     range(self.attributes))
            # I must overlap myself
            self.assert_(overlap(factors1,factors1))
            # Try flipping 1-0
            choices = filter(lambda i: not factors1[i] is None,
                             range(self.attributes))
            factors2 = factors1[:]
            while len(choices) > 0:
                index = random.choice(choices)
                choices.remove(index)
                factors2[index] = 1-factors2[index]
                self.assertFalse(overlap(factors1,factors2))
                self.assertFalse(overlap(factors2,factors1))
                self.assert_(intersection(factors1,factors2) is None)
            # Try restricting wild
            choices = filter(lambda i: factors1[i] is None,
                             range(self.attributes))
            factors2 = factors1[:]
            flipped = []
            while len(choices) > 0:
                index = random.choice(choices)
                choices.remove(index)
                factors2[index] = random.choice([0,1])
                # Test overlap
                self.assert_(overlap(factors1,factors2))
                self.assert_(overlap(factors2,factors1))
                # Test intersection
                flipped.append(index)
                flipped.sort()
                restrictions = []
                merge = intersection(factors1,factors2,restrictions)
                self.assert_(isinstance(merge,list))
                self.assertEqual(merge,factors2)
                self.assertEqual(restrictions,flipped)
            # Try adding wilds
            choices = filter(lambda i: not factors1[i] is None,
                             range(self.attributes))
            factors2 = factors1[:]
            flipped = []
            while len(choices) > 0:
                index = random.choice(choices)
                choices.remove(index)
                factors2[index] = None
                self.assert_(overlap(factors1,factors2))
                self.assert_(overlap(factors2,factors1))
                # Test intersection
                flipped.append(index)
                flipped.sort()
                restrictions = []
                merge = intersection(factors1,factors2,restrictions)
                self.assert_(isinstance(merge,list))
                self.assertEqual(merge,factors1)
                self.assertEqual(restrictions,[])
                restrictions = []
                merge = intersection(factors2,factors1,restrictions)
                self.assert_(isinstance(merge,list))
                self.assertEqual(merge,factors1)
                self.assertEqual(restrictions,flipped)

    def verifyProduct(self,mul1,mul2,product):
        """Verifies that mul1*mul2 = product
        """
        for subiteration in range(1000):
            state = self.generateVector(probability=True)
            RHS = product[state]
            for action,V in RHS['values'].items():
                ER = V*state
                newState = mul2[state]['values'][action]*state
                target = mul1[newState]['values'][action]*newState
                self.assertAlmostEqual(target,ER,8)
        
    def testMultiply(self):
        for iteration in range(64):
            V = self.generateV()
            T = self.generateT()
            Vproduct = V*T
##            self.verifyTable(Vproduct)
            self.verifyProduct(V,T,Vproduct)
                
if __name__ == '__main__':
    unittest.main()
