from teamwork.math.KeyedMatrix import *
from teamwork.math.KeyedTree import *
from teamwork.math.ProbabilityTree import *

def genAttackDyn(fromFeature,feature=None,scale=1.):
    if not feature:
        feature = fromFeature
    # Object dynamics if object is stronger
    weights = {StateKey({'entity':'self','feature':feature}):1.,
               StateKey({'entity':'actor','feature':fromFeature}): -.1,
               StateKey({'entity':'object','feature':fromFeature}): .1,
               keyConstant: -.05*scale}
    objWeaker = createDynamicNode(feature,weights)
    # Object dynamics if object is weaker
    objStronger = ProbabilityTree(IncrementMatrix(feature,value=-.01*scale))
    # Branch on whether actor is stronger than object
    plane = KeyedPlane(DifferenceRow(keys=[{'entity':'object','feature':fromFeature},
                                           {'entity':'actor','feature':fromFeature}]),0.)
    # Object dynamics
    objectTree = createBranchTree(plane,objWeaker,objStronger)
    # Power unchanged
    unchangedTree = ProbabilityTree(IdentityMatrix(feature))
    # Branch on whether I'm object
    weights = {makeIdentityKey('object'): 1.}
    notActorTree = createBranchTree(KeyedPlane(IdentityRow(keys=[{'entity':'object','relationship':'equals'}]),0.5),
                                    unchangedTree,objectTree)
    # Actor much weaker
    weights = {StateKey({'entity':'self','feature':feature}):1.,
               StateKey({'entity':'actor','feature':fromFeature}): .1,
               StateKey({'entity':'object','feature':fromFeature}): -.1,
               keyConstant: .02*scale}
    actorMuchWeakerTree = createDynamicNode(feature,weights)
    # Actor weaker
    actorWeakerTree = ProbabilityTree(IncrementMatrix(feature,value=-.01*scale))

    # Branch on whether actor is *much* weaker than object
    weights = {makeStateKey('actor',fromFeature): -1.,
               makeStateKey('object',fromFeature): 1.}
    plane = KeyedPlane(DifferenceRow(keys=[{'entity':'object','feature':fromFeature},
                                           {'entity':'actor','feature':fromFeature}]),0.2)
    actorTree = createBranchTree(plane,actorWeakerTree,actorMuchWeakerTree)
    # Branch on whether I'm actor
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree = createBranchTree(plane,notActorTree,actorTree)
    return {'tree':tree}

def genPunishClass(target,feature=None,scale=1.):
    # Power unchanged
    unchangedTree = ProbabilityTree(IdentityMatrix(feature))
    # Object dynamics if object is stronger
    objWeaker = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                                -.05*scale))
    # Branch on whether I'm object
    weights = {makeClassKey('self',target): 1.}
    tree = createBranchTree(KeyedPlane(KeyedVector(weights),0.5),
                            unchangedTree,objWeaker)
    return {'tree':tree}

if __name__ == '__main__':
    tree = genAttackDyn('power','power')['tree']
    print tree.simpleText()
