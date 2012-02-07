"""Utility functions and base testing class for verifying PWL code
@author: David V. Pynadath <pynadath@isi.edu>
"""
from teamwork.math.Keys import *
from teamwork.math.KeyedMatrix import *
from teamwork.math.KeyedTree import *

from random import random,uniform
import unittest

def makeVector(keys,fillProb=0.5):
    """Generate a random vector, with random constant field
    @param keys: the keys to consider using in the vector
    @type keys: L{Key}[]
    @param fillProb: the probability that each key will be present in the vector (default is 0.5)
    @type fillProb: float
    @rtype: L{KeyedVector}"""
    row = KeyedVector()
    for key in keys:
        if random() <= fillProb:
            # e.g., 50% chance of this key actually existing
            row[key] = uniform(-1.,1.)
    if random() <= fillProb:
        row[keyConstant] = uniform(-1.,1.)
    return row
    
def makeDynamics(keys,fillProb=0.5):
    """Constructs a random dynamics matrix
    @param keys: the keys to consider using in the matrix and component vectors
    @type keys: L{Key}[]
    @rtype: L{KeyedMatrix} instance"""
    keyList = keys+[keyConstant]
    keyList.sort()
    matrix = KeyedMatrix()
    for key in keys:
        if random() <= fillProb:
            row = makeVector(keys,fillProb)
            matrix[key] = row
    matrix[keyConstant] = KeyedVector({keyConstant:1.})
    matrix.fill(keyList)
    return matrix

def makeState(keys,fillProb=0.5):
    """Generate a random vector, with constant field of 1
    @param keys: the keys to consider using in the vector
    @type keys: L{Key}[]
    @param fillProb: the probability that each key will be present in the vector (default is 0.5)
    @type fillProb: float
    @rtype: L{KeyedVector}"""
    vector = makeVector(keys,fillProb)
    vector[keyConstant] = 1.
    vector.fill(keys)
    return vector
    
def makePlane(keys,fillProb=0.5):
    """Generate a random hyperplane
    @param keys: the keys to consider using in the vector
    @type keys: L{Key}[]
    @param fillProb: the probability that a given key will be present in the weights vector (default is 0.5)
    @type fillProb: float
    @rtype: L{KeyedPlane}"""
    weights = makeVector(keys,fillProb)
    weights[keyConstant] = 0.
    weights.fill(keys)
    threshold = random()
    return KeyedPlane(weights,threshold)

def makeTree(keys,depth=0,fillProb=0.5):
    """Constructs a random dynamics tree
    @param keys: the keys to consider using in the vector
    @type keys: L{Key}[]
    @param depth: the depth of the tree to return
    @type depth: int
    @rtype: L{KeyedTree} instance"""
    tree = _makeTree(keys,depth,fillProb)
    tree.freeze()
    return tree

def _makeTree(keys,depth=0,fillProb=0.5):
    """Constructs a random dynamics tree
    @param keys: the keys to consider using in the vector
    @type keys: L{Key}[]
    @param depth: the depth of the tree to return
    @type depth: int
    @rtype: L{KeyedTree} instance"""
    tree = KeyedTree()
    if depth > 0:
        plane = makePlane(keys,fillProb)
        falseTree = makeTree(keys,depth-1,fillProb)
        trueTree = makeTree(keys,depth-1,fillProb)
        tree.branch(plane,falseTree,trueTree,pruneT=False,pruneF=False)
    else:
        dynamics = makeDynamics(keys,fillProb)
        tree.makeLeaf(dynamics)
    return tree

class TestPWL(unittest.TestCase):
    """Base class for testing PWL code.  Intended to be abstract class
    @cvar precision: number of significant digits to check for equality
    @type precision: int
    @cvar agents: a list of entity names to use as test cases
    @type agents: str[]
    @cvar features: a list of state features to use as test case
    @type features: str[]
    """
    features = []
    agents = []
    precision = 8

    def setUp(self):
        self.keys = []
        for agent in self.agents:
            self.keys += map(lambda f:makeStateKey(agent,f),self.features)

    def verifyVector(self,old,new):
        """Tests equality of given vectors
        @type old: L{KeyedVector}
        @type new: L{KeyedVector}
        """
        self.assert_(isinstance(old,KeyedVector))
        self.assert_(isinstance(new,KeyedVector))
        for key in old.keys():
            self.assert_(new.has_key(key))
            self.assertAlmostEqual(old[key],new[key],self.precision)
        for key in new.keys():
            self.assert_(old.has_key(key))

    def verifyMatrix(self,old,new):
        """Tests equality of given matrices
        @type old: L{KeyedMatrix}
        @type new: L{KeyedMatrix}
        """
        self.assert_(isinstance(old,KeyedMatrix))
        self.assert_(isinstance(new,KeyedMatrix))
        for key in old.keys():
            self.assert_(new.has_key(key))
            self.verifyVector(old[key],new[key])
        for key in new.keys():
            self.assert_(old.has_key(key))
            
    def verifyPlane(self,old,new):
        """Tests equality of given planes
        @type old: L{KeyedPlane}
        @type new: L{KeyedPlane}
        """
        self.assert_(isinstance(old,KeyedPlane))
        self.assert_(isinstance(new,KeyedPlane))
        self.assertAlmostEqual(old.threshold,new.threshold,self.precision)
        self.verifyVector(old.weights,new.weights)
            
    def verifyTree(self,old,new): 
        """Tests equality of given trees
        @type old: L{KeyedTree}
        @type new: L{KeyedTree}
        """
        self.assert_(isinstance(old,KeyedTree))
        self.assert_(isinstance(new,KeyedTree))
        if old.isLeaf():
            self.assert_(new.isLeaf())
            if isinstance(old.getValue(),KeyedMatrix):
                matrix1 = old.getValue()
                matrix2 = new.getValue()
                self.verifyMatrix(matrix1,matrix2)
            else:
                self.assertEqual(old.getValue(),new.getValue())
        else:
            self.assert_(not new.isLeaf())
            self.assertEqual(len(old.split),len(new.split))
            for index in range(len(old.split)):
                self.verifyPlane(old.split[index],new.split[index])
            self.verifyTree(old.falseTree,new.falseTree)
            self.verifyTree(old.trueTree,new.trueTree)
