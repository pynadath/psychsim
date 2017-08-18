import unittest
import random

from psychsim.probability import *
from psychsim.pwl import *

class TestTree(unittest.TestCase):
    def setUp(self):
        self.state = VectorDistributionSet()
        self.state.join('x',Distribution({0: 0.5, 1: 0.2, 2: 0.3}))


    def testMatrix(self):
        matrix = incrementMatrix('x',1.)
        self.state *= matrix
        dist = self.state.marginal(makeFuture('x'))
        for x in dist.domain():
            if abs(x-1.)<1e-8:
                self.assertAlmostEqual(dist[x],0.5)
            elif abs(x-2.)<1e-8:
                self.assertAlmostEqual(dist[x],0.2)
            elif abs(x-3.)<1e-8:
                self.assertAlmostEqual(dist[x],0.3)
            else:
                self.fail('Illegal element %4.2f' % (x))
        self.state.rollback()
        dist = self.state.marginal('x')
        for x in dist.domain():
            if abs(x-1.)<1e-8:
                self.assertAlmostEqual(dist[x],0.5)
            elif abs(x-2.)<1e-8:
                self.assertAlmostEqual(dist[x],0.2)
            elif abs(x-3.)<1e-8:
                self.assertAlmostEqual(dist[x],0.3)
            else:
                self.fail('Illegal element %4.2f' % (x))

    def DONTtestIf(self):
        print self.state
        tree = makeTree({'if': thresholdRow('x',0.5),
                         True: noChangeMatrix('x'),
                         False: incrementMatrix('x',1)})
        self.state *= tree
        print self.state
        
    def DONTtestCase(self):
        print self.state
        tree = makeTree({'case': 'x',
                         0: incrementMatrix('x',1),
                         1: incrementMatrix('x',-1),
                         2: noChangeMatrix('x')})
        self.state *= tree
        self.state.rollback()
        print self.state

if __name__ == '__main__':
    unittest.main()
    
