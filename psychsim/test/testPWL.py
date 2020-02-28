import unittest
import random

from psychsim.pwl import *

class TestPWL(unittest.TestCase):

    def makeVector(self,size=8,gap=0.):
        """
        @param size: the maximum length of the returned vector (default is 8)
        @param gap: the probability that there will be gaps in the keys (default is 0)
        @rtype: L{KeyedVector}
        """
        vector = KeyedVector()
        for index in range(size):
            if random.random() > gap:
                key = chr(65+index)
                vector[key] = random.random()
        return vector

    def makeMatrix(self,rows=8,cols=8,rowgap=0.,colgap=0.):
        """
        @param rows: the maximum rows in the returned matrix (default is 1)
        @param cols: the maximum columns in the returned matrix (default is 8)
        @param rowgap: the probability that there will be gaps in the row keys (default is 0)
        @param colgap: the probability that there will be gaps in the column keys (default is 0)
        @rtype: L{KeyedMatrix}
        """
        matrix = KeyedMatrix()
        for index in range(rows):
            if random.random() > rowgap:
                key = chr(65+index)
                matrix[key] = self.makeVector(cols,colgap)
        return matrix

    def makePlane(self,size=8,gap=0.,comparison=1):
        """
        @param size: the maximum length of the plane vector (default is 8)
        @param gap: the probability that there will be gaps in the column keys (default is 0)
        @param comparison: if 1, value must be above hyperplane; if -1, below; if 0, equal (default is 1)
        @rtype: L{KeyedPlane}
        """
        return KeyedPlane(self.makeVector(size,gap),random.random(),comparison)

    def makeTree(self,rows=8,cols=8,planecols=8,depth=3,rowgap=0.,colgap=0.,planegap=0.):
        """
        @param rows: the maximum rows in the leaf matrices (default is 1)
        @param cols: the maximum columns in the leaf matrices (default is 8)
        @param planecols: the maximum columns in the hyperplanes (default is 4)
        @param depth: the depth of the returned tree (default is 3)
        @param rowgap: the probability that there will be gaps in the row keys (default is 0)
        @param colgap: the probability that there will be gaps in the column keys (default is 0)       
        @param colgap: the probability that there will be gaps in the hyperplane keys (default is 0)
        @rtype: L{KeyedTree}
        """
        root = KeyedTree()
        oldEnvelope = [root]
        currentDepth = 0
        # Branch until we reach desired depth
        while currentDepth < depth:
            newEnvelope = []
            for node in oldEnvelope:
                trueTree = KeyedTree()
                falseTree = KeyedTree()
                newEnvelope += [trueTree,falseTree]
                node.makeBranch(self.makePlane(planecols,planegap),trueTree,falseTree)
            oldEnvelope = newEnvelope
            currentDepth += 1
        # Make leaves
        for node in oldEnvelope:
            node.makeLeaf(self.makeMatrix(rows,cols,rowgap,colgap))
        return root

    def testVectorAddition(self):
        for iteration in range(100):
            v1 = self.makeVector(gap=0.1)
            v2 = self.makeVector(gap=0.2)
            total = v1+v2
            for key in v1.keys():
                self.assertTrue(total.has_key(key))
            for key in v2.keys():
                self.assertTrue(total.has_key(key))
            for key in total.keys():
                self.assertTrue(v1.has_key(key) or v2.has_key(key))
                if v1.has_key(key) and v2.has_key(key):
                    self.assertAlmostEqual(v1[key]+v2[key],total[key],8)
                elif v1.has_key(key):
                    self.assertAlmostEqual(v1[key],total[key],8)
                else: # v2.has_key(key)
                    self.assertAlmostEqual(v2[key],total[key],8)

    def testMatrixMultiplication(self):
        # Matrix * Matrix
        for iteration in range(100):
            m1 = self.makeMatrix()
            m2 = self.makeMatrix()
            mProduct = m1*m2
            for testIteration in range(100):
                v0 = self.makeVector()
                v1 = m2*v0
                v2 = m1*v1
                product = mProduct*v0
                self.assertEqual(v2.keys(),product.keys())
                for key in product.keys():
                    self.assertAlmostEqual(product[key],v2[key],8)

    def DONTtestTreeAddition(self):
        for iteration in range(100):
            t1 = self.makeTree(colgap=0.75,planegap=0.75)
            t2 = self.makeTree(colgap=0.75,planegap=0.75)
            tTotal = t1 + t2
            for testIteration in range(100):
                v = self.makeVector()
                total = t1[v]*v + t2[v]*v
                self.assertAlmostEqual(tTotal[v]*v,total,8)

    def testTreeMultiplication(self):
        for iteration in range(100):
            t1 = self.makeTree(rows=2,cols=2,planecols=2,depth=1)
            t2 = self.makeTree(rows=2,cols=2,planecols=2,depth=0)
            tProduct = t1*t2
            for testIteration in range(100):
                v1 = self.makeVector()
                v2 = t2[v1]*v1
                v3 = t1[v2]*v2
                self.assertEqual(t1.branch.evaluate(v2),tProduct.branch.evaluate(v1))
                product1 = tProduct[v1]*v1
                for key in v3.keys():
                    self.assertAlmostEqual(product1[key],v3[key],8)

if __name__ == '__main__':
    unittest.main()
