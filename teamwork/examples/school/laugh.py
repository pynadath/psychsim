from teamwork.math.KeyedMatrix import *
from teamwork.math.KeyedTree import *
from teamwork.math.ProbabilityTree import *

def genLaughDyn(feature,increment=0.05):
    # Power unchanged
    unchangedTree = ProbabilityTree(IdentityMatrix(feature))
    # Object dynamics if object is stronger
    objWeaker = ProbabilityTree(IncrementMatrix(feature,keyConstant,-increment))
    # Branch on whether I'm object
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    tree = createBranchTree(plane,unchangedTree,objWeaker)
    return {'tree':tree}
