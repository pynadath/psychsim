import unittest
import random

from psychsim.probability import *
from psychsim.pwl import *

class TestTree(unittest.TestCase):
    def setUp(self):
        self.state = VectorDistributionSet()
        self.state.join('x',Distribution({0: 0.5, 1: 0.2, 2: 0.3}))


    def verifyDistribution(self,key,correct):
        actual = self.state.marginal(key)
        self.assertEqual(len(actual),len(correct))
        for value in actual.domain():
            for match in correct:
                if abs(value-match)<1e-8:
                    self.assertAlmostEqual(actual[value],correct[match])
                    break
            else:
                self.fail('Illegal element %4.2f' % (value))
            
    def testMatrix(self):
        matrix = incrementMatrix('x',1.)
        self.state *= matrix
        self.verifyDistribution(makeFuture('x'),{1: 0.5,2: 0.2, 3: 0.3})
        self.state.rollback()
        self.verifyDistribution('x',{1: 0.5,2: 0.2, 3: 0.3})

    def testIf(self):
        tree = makeTree({'if': thresholdRow('x',0.5),
                         True: noChangeMatrix('x'),
                         False: incrementMatrix('x',1)})
        self.state *= tree
        self.verifyDistribution(makeFuture('x'),{1: 0.7, 2: 0.3})
        self.state.rollback()
        self.verifyDistribution('x',{1: 0.7, 2: 0.3})
        
    def testCase(self):
        tree = makeTree({'case': 'x',
                         0: incrementMatrix('x',1),
                         1: incrementMatrix('x',-1),
                         2: noChangeMatrix('x')})
        self.state *= tree
        self.verifyDistribution(makeFuture('x'),{0: 0.2, 1: 0.5, 2: 0.3})
        self.state.rollback()
        self.verifyDistribution('x',{0: 0.2, 1: 0.5, 2: 0.3})
        tree = makeTree({'case': 'x',
                         0: incrementMatrix('x',1),
                         1: incrementMatrix('x',-1),
                         'otherwise': noChangeMatrix('x')})
        self.state *= tree
        self.verifyDistribution(makeFuture('x'),{0: 0.5, 1: 0.2, 2: 0.3})
        self.state.rollback()
        self.verifyDistribution('x',{0: 0.5, 1: 0.2, 2: 0.3})

if __name__ == '__main__':
    unittest.main()
    
