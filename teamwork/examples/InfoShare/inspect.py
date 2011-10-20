from teamwork.math.KeyedMatrix import *
from teamwork.math.KeyedTree import *
from teamwork.math.ProbabilityTree import *

def scale(feature,scale):
    return {'tree':ProbabilityTree(IncrementMatrix(feature,value=scale))}

def waitTime(scale):
    # This handles only the feature named "waitTime"
    feature = 'waitTime'
    unchangedTree = ProbabilityTree(IdentityMatrix(feature))
    smallTree = ProbabilityTree(IncrementMatrix(feature,value=scale))
    bigTree = ProbabilityTree(IncrementMatrix(feature,value=2.*scale))
    keys = [{'entity':'self','feature':feature}]
    plane = KeyedPlane(ThresholdRow(keys=keys),0.3)
    tree = createBranchTree(plane,smallTree,bigTree)
    return {'tree': tree}
    
def welfareDynamics():
    feature = 'socialWelfare'
    key = {'entity':'object','feature':'containerDanger'}
    unchangedTree = ProbabilityTree(IdentityMatrix(feature))
    changeTree = ProbabilityTree(ScaleMatrix(feature,StateKey(key),-1.))
    plane = KeyedPlane(ThresholdRow(keys=[key]),0.)
    tree = createBranchTree(plane,unchangedTree,changeTree)
    return {'tree': tree}
               
def bustDynamics(amount=.01):
    goodTree = ProbabilityTree(IncrementMatrix('reputation',value=amount))
    badTree = ProbabilityTree(IncrementMatrix('reputation',value=-amount))
    plane = KeyedPlane(ThresholdRow(keys=[{'entity':'object',
                                           'feature':'containerDanger'}]),0.)
    tree = createBranchTree(plane,badTree,goodTree)
    return {'tree':tree}

def zero(feature):
    tree = ProbabilityTree(ScaleMatrix(feature,value=-1.,
                                 key=StateKey({'entity':'object',
                                               'feature':feature})))
    return {'tree':tree}
                     
if __name__ == '__main__':
    dyn = welfareDynamics()
    print dyn['tree'].simpleText()
    print
    
    dyn = bustDynamics()
    print dyn['tree'].simpleText()

