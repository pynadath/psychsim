from teamwork.math.ProbabilityTree import *
from teamwork.math.KeyedMatrix import *
from teamwork.dynamics.pwlDynamics import *
from teamwork.dynamics.arbitraryDynamics import *


def dummyDyn(feature):
    tree1 = ProbabilityTree(IdentityMatrix(feature))
    
    return {'tree':tree1}



def InitNorm():
    tree1 = ProbabilityTree(IdentityMatrix('init-norm'))

    tree4 = ProbabilityTree(IncrementMatrix('init-norm',keyConstant,-.1))

        
## if I have obligations that haven't been satisfied
    weights = {}
    for feature in [\
                    'being-enquired',
                    ]:
        key = makeStateKey('self',feature)
        weights[key] = 1
        
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree5 = createBranchTree(plane,tree1,tree4)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree0 = createBranchTree(plane,tree1,tree5)

    return {'tree':tree0}


def RespNorm(act):
    tree0 = ProbabilityTree(IdentityMatrix('resp-norm'))

    tree4 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,-.1))
    tree3 = ProbabilityTree(IdentityMatrix('resp-norm'))

    varname = 'being-enquired'
        
    weights = {makeStateKey('self',varname):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)
    tree2 = createBranchTree(plane,tree4,tree3)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree1 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree1}


def IntendImposeNorm(act):

    varname = 'being-enquired'
    tree0 = ProbabilityTree(IdentityMatrix(varname))
    tree3 = ProbabilityTree(SetToConstantMatrix(feature=varname,value=1))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)

    tree1 = createBranchTree(plane,tree0,tree3)

    return {'tree':tree1}


def IntendFinishNorm(act):
    varname = 'being-enquired'
    tree0 = ProbabilityTree(IdentityMatrix(varname))
    tree3 = ProbabilityTree(IncrementMatrix(varname,keyConstant,-1))

    weights = {makeStateKey('self',varname):1.}
    plane = KeyedPlane(KeyedVector(weights),.1)
    tree2 = createBranchTree(plane,tree0,tree3)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree1 = createBranchTree(plane,tree0,tree2)
    return {'tree':tree1}


DynFun = {
    'noneDyn': {},
    'basicDyn': {
        'init-norm':{\
                    'enquiry':{'class':PWLDynamics,
                                'args':InitNorm()},        
                                    },
        'resp-norm':{\
                     'pos-inform':{'class':PWLDynamics,
                                'args':RespNorm('inform')},
                     'neu-inform':{'class':PWLDynamics,
                                'args':RespNorm('inform')},
                     'neg-inform':{'class':PWLDynamics,
                                'args':RespNorm('inform')},
                    
                                },
        
        'being-enquired':{'enquiry':{'class':PWLDynamics,
                            'args':IntendImposeNorm('enquiry')},
                        'pos-inform':{'class':PWLDynamics,
                            'args':IntendFinishNorm('inform')},
                        'neu-inform':{'class':PWLDynamics,
                            'args':IntendFinishNorm('inform')},
                        'neg-inform':{'class':PWLDynamics,
                            'args':IntendFinishNorm('inform')},
                        },

        }
}
