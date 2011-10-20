from teamwork.math.Keys import *
from teamwork.math.KeyedMatrix import *
from teamwork.math.KeyedTree import *
from testPWL import TestPWL,makeTree,makeState,makePlane

import copy
import hotshot,hotshot.stats
import time
import unittest
        
class TestKeyedTree(TestPWL):

    """TestCase for L{teamwork.math.KeyedTree} class
    @cvar iterations: the number of times to repeat each test
    @type iterations: int
    @cvar horizon: the number of steps to consider in a projection
    @type horizon: int
    @cvar filename: name of temporary file to store profiling data
    @cvar agents: a list of entity names to use as test cases
    @type agents: str[]
    @cvar features: a list of state features to use as test case
    @type features: str[]
    """
    filename = '/tmp/keyedtree.prof'
    iterations = 10
    horizon = 4
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

    def testXML(self):
        old = makeTree(self.keys,5)
        doc = old.__xml__()
        new = KeyedTree()
        new.parse(doc.documentElement,valueClass=KeyedMatrix)
        self.verifyTree(old,new)

    def testCopy(self):
        old = makeTree(self.keys,4)
        new = copy.copy(old)
        self.verifyTree(old,new)
        self.assert_(not old is new)
        new = copy.deepcopy(old)
        self.verifyTree(old,new)
        self.assert_(not old is new)

    def testTest(self):
        for treeIndex in range(self.iterations):
            tree = makeTree(self.keys,4)
            for stateIndex in range(self.iterations):
                state = makeState(self.keys,1.)
                matrix = tree[state]
                self.assert_(isinstance(matrix,KeyedMatrix))
        
    def testMultiply(self):
        vecLength = 4 # len(self.keys)
        for index in range(self.iterations):
            # Create a sequence of dynamics trees
            trees = []
            for step in range(self.horizon):
                tree = makeTree(self.keys[:vecLength],3)
##                print step,tree.toNumeric()
                trees.append(tree)
            # Accumulate the trees into a single tree
            product = trees[0]
            for step in range(1,self.horizon):
##                prof = hotshot.Profile(self.filename)
##                prof.start()
                product = trees[step] * product
##                prof.stop()
##                prof.close()
##                print 'loading stats...'
##                stats = hotshot.stats.load(self.filename)
##                stats.strip_dirs()
##                stats.sort_stats('time', 'calls')
##                stats.print_stats()
##            print 'product:',product.toNumeric()
            for rep in range(self.iterations):
                # Test on a variety of initial states
                state = makeState(self.keys[:vecLength],1.)
                state.freeze()
##                print 'start:',state.array.transpose()
                # Explicitly iterate through the individual dynamics trees
                iterative = state
                for step in range(0,self.horizon):
                    iterative = trees[step][iterative] * iterative
                # Compare against cumulative state
                cumulative = product[state] * state
                self.verifyVector(iterative,cumulative)

    def DONTtestRebalance(self):
        vecLength = 1
        for index in range(self.iterations):
            # We need a good candidate for rebalancing.  This is our
            # oh-so-clever way of randomly generating one.
            tree1 = makeTree(self.keys[:vecLength],1,1.)
            tree2 = makeTree(self.keys[:vecLength],1,1.)
            subFalse,subTrue = tree2.getValue()
            subFalse.makeLeaf('F')
            subTrue.makeLeaf('T')
            falseTree,trueTree = tree1.getValue()
            falseTree.branch(copy.deepcopy(tree2.split),
                             copy.deepcopy(subFalse),
                             copy.deepcopy(subTrue))
            trueTree.branch(copy.deepcopy(tree2.split),
                            copy.deepcopy(subFalse),
                            copy.deepcopy(subTrue))
            tree4 = copy.deepcopy(tree1)
            tree4.rebalance()
            self.assert_(len(tree4.leaves()) < len(tree1.leaves()),
                        'Rebalancing did not reduce tree size')
        for index in range(self.iterations):
            tree1 = makeTree(self.keys,6,1.)
            tree2 = copy.deepcopy(tree1)
            tree2.rebalance()
            for rep in range(self.iterations):
                state = makeState(self.keys,1.)
                self.assertEqual(tree1[state],tree2[state])
                
if __name__ == '__main__':
    unittest.main()
