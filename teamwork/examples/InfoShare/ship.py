from teamwork.math.KeyedMatrix import *
from teamwork.math.KeyedTree import *
from teamwork.math.ProbabilityTree import *

def shipThrough(feature,modifier='',entity=''):
    if len(modifier) == 0:
        modifier = feature
    if len(entity) == '':
        entity = 'actor'
    # Feature change for chosen shipper
    shipperTree = ProbabilityTree(ScaleMatrix(feature,
                                              StateKey({'entity':entity,
                                                        'feature':modifier}),
                                              1.))
    # Feature unchanged for anyone else
    unchangedTree = KeyedTree(IdentityMatrix(feature))
    # Branch on whether I'm chosen shipper
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    tree = createBranchTree(plane,unchangedTree,shipperTree)
    return {'tree': tree}

def shippingFees():
    pass
