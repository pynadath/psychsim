from teamwork.math.ProbabilityTree import *
from teamwork.math.KeyedMatrix import *
from teamwork.dynamics.pwlDynamics import *
from teamwork.dynamics.arbitraryDynamics import *


def thresholdDecrease(feature):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,-.1))
    weights = {makeStateKey('self',feature): 1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree = createBranchTree(plane,tree1,tree0)
    return {'tree':tree}

def thresholdObjectSetDyn(thresholdF,fea,val):
    tree0 = ProbabilityTree(IdentityMatrix(fea))
    tree1 = ProbabilityTree(SetToConstantMatrix(feature=fea,value=val))
    weights = {makeStateKey('self',thresholdF): 1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree = createBranchTree(plane,tree0,tree1)
    return {'tree':tree}
    
    
def deltaDyn(feature,delta):
    tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    return {'tree':tree}

def deltaActorOrObjectDyn(feature,delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)

    tree2 = createBranchTree(plane,tree0,tree1)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree2,tree1)

    return {'tree':tree3}


def deltaActorDyn(feature,delta):
    
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}


def dummyDyn(feature):
    tree1 = ProbabilityTree(IdentityMatrix(feature))
    
    return {'tree':tree1}

def ActorSetDyn(fea, val):
    tree0 = ProbabilityTree(IdentityMatrix(fea))
    tree1 = ProbabilityTree(SetToConstantMatrix(feature=fea,value=val))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}


def ObjectSetDyn(fea, val):
    tree0 = ProbabilityTree(IdentityMatrix(fea))
    tree1 = ProbabilityTree(SetToConstantMatrix(feature=fea,value=val))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}

   

def conversationFlowNorm(act):
    tree1 = ProbabilityTree(IdentityMatrix('conversation-flow-norm'))
    tree4 = ProbabilityTree(IncrementMatrix('conversation-flow-norm',keyConstant,-.1))

## action shouldn't happen after closed conversation, or before conversation opened

    if not act in ['greet-init','bye-resp']:
        weights = {makeStateKey('self','conversation'): 1.}
        plane = KeyedPlane(KeyedVector(weights),.001)
        tree2 = createBranchTree(plane,tree4,tree1)
    else:
        weights = {makeStateKey('self','conversation'): 1.}
        plane = KeyedPlane(KeyedVector(weights),.001)
        tree2 = createBranchTree(plane,tree1,tree4)
        

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree0 = createBranchTree(plane,tree1,tree2)

    return {'tree':tree0}


def InitNorm():
    tree1 = ProbabilityTree(IdentityMatrix('init-norm'))

    tree4 = ProbabilityTree(IncrementMatrix('init-norm',keyConstant,-.1))

        
## if I have obligations that haven't been satisfied
    weights = {}
    for feature in [\
                    'being-greeted',
                    'being-byed',
                    'being-enquired',
                    'being-informed',
                    'being-enquired-about-granny',
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

##    tree3 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,.1))

    if act == 'inform':
        varname = 'being-enquired'
    elif act in ['accept','reject']:
        varname = 'being-requested'
    elif act in ['OK']:
        varname = 'being-informed'
    else:
        varname = 'being-'+act
        if act[len(act)-1] == 'e':
            varname += 'd'
        else:
            varname += 'ed'
        
    weights = {makeStateKey('self',varname):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)
    tree2 = createBranchTree(plane,tree4,tree3)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree1 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree1}

def MakeRespNorm(act):
    tree0 = ProbabilityTree(IdentityMatrix('makeResp-norm'))

    tree4 = ProbabilityTree(IdentityMatrix('makeResp-norm'))
    tree3 = ProbabilityTree(IncrementMatrix('makeResp-norm',keyConstant,.1))

##    tree3 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,.1))

    if act == 'inform':
        varname = 'being-enquired'
    elif act in ['accept','reject']:
        varname = 'being-requested'
    elif act in ['OK']:
        varname = 'being-informed'
    else:
        varname = 'being-'+act
        if act[len(act)-1] == 'e':
            varname += 'd'
        else:
            varname += 'ed'
        
    weights = {makeStateKey('self',varname):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)
    tree2 = createBranchTree(plane,tree4,tree3)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree1 = createBranchTree(plane,tree0,tree2)

    
    return {'tree':tree1}


def IntendImposeNorm(act):

    if act == 'enquiry':
        varname = 'being-enquired'
    elif act == 'inform-info':
        varname = 'being-informed'
    else:
        varname = 'being-'+act
        if act[len(act)-1] == 'e':
            varname += 'd'
        else:
            varname += 'ed'
    tree0 = ProbabilityTree(IdentityMatrix(varname))
    tree3 = ProbabilityTree(SetToConstantMatrix(feature=varname,value=1))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)

    tree1 = createBranchTree(plane,tree0,tree3)

    return {'tree':tree1}


def IntendFinishNorm(act):

    if act == 'inform':
        varname = 'being-enquired'
    elif act in ['accept','reject']:
        varname = 'being-requested'
    elif act in ['OK']:
        varname = 'being-informed'
    else:
        varname = 'being-'+act
        if act[len(act)-1] == 'e':
            varname += 'd'
        else:
            varname += 'ed'
    tree0 = ProbabilityTree(IdentityMatrix(varname))
    tree3 = ProbabilityTree(IncrementMatrix(varname,keyConstant,-1))

    weights = {makeStateKey('self',varname):1.}
    plane = KeyedPlane(KeyedVector(weights),.1)
    tree2 = createBranchTree(plane,tree0,tree3)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree1 = createBranchTree(plane,tree0,tree2)
    return {'tree':tree1}

def conversationDyn(intend):
    tree0 = ProbabilityTree(IdentityMatrix('conversation'))
    if intend == 'greet':
        tree1 = ProbabilityTree(SetToConstantMatrix(feature='conversation',value=1))
    elif intend == 'bye':
        tree1 = ProbabilityTree(SetToConstantMatrix(feature='conversation',value=0))
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree2 = createBranchTree(plane,tree0,tree1)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree2,tree1)
    
    return {'tree':tree3}


def noRepeatDyn(feature):

    tree0 = ProbabilityTree(IdentityMatrix('noRepeat-norm'))
    tree1 = ProbabilityTree(IncrementMatrix('noRepeat-norm',keyConstant,-.1))
    
    
    weights = {makeStateKey('actor',feature):1.}
    plane = KeyedPlane(KeyedVector(weights),0)
    tree3 = createBranchTree(plane,tree0,tree1)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree3)
    return {'tree':tree4}




def SDDyn(feature):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,.05))
    
    name = feature.strip('SDwith')
    if name == 'Wolf':
        name = 'wolf'
    
    plane = KeyedPlane(ClassRow(keys=[{'entity':'object','value':name}]),0)

    tree3 = createBranchTree(plane,tree0,tree1)

    plane = KeyedPlane(ClassRow(keys=[{'entity':'actor','value':name}]),0)

    tree2 = createBranchTree(plane,tree0,tree1)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)

    tree5 = createBranchTree(plane,tree0,tree2)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree5,tree3)
    return {'tree':tree4}

    
def SDnormDyn(act):
    tree0 = ProbabilityTree(IdentityMatrix('SDnorm'))
    tree1 = ProbabilityTree(IncrementMatrix('SDnorm',keyConstant,-.1))
    
    
    weights = {makeStateKey('object','SDwithWolf'):1.}
    plane = KeyedPlane(KeyedVector(weights),0)
    tree3 = createBranchTree(plane,tree1,tree0)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree3)
    return {'tree':tree4}
    

def likeActDyn(feature):

    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,.01))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)
    
    return {'tree':tree3}

DynFun = {
    'noneDyn': {},
    'basicDyn': {
        'resp-norm':{\
                     'greet-resp':{'class':PWLDynamics,
                                  'args':RespNorm('greet')},
                     
                     'bye-resp':{'class':PWLDynamics,
                                'args':RespNorm('bye')},
                    
                     'inform':{'class':PWLDynamics,
                                'args':RespNorm('inform')},
                    
                                },
        'makeResp-norm':{\
                     'greet-resp':{'class':PWLDynamics,
                                  'args':MakeRespNorm('greet')},
                     
                     'bye-resp':{'class':PWLDynamics,
                                'args':MakeRespNorm('bye')},
                    
                     'inform':{'class':PWLDynamics,
                                'args':MakeRespNorm('inform')},
                    
                
                                },
        'init-norm':{'greet-init':{'class':PWLDynamics,
                                'args':InitNorm()}, 
                    
                     'bye-init':{'class':PWLDynamics,
                                    'args':InitNorm()}, 
                    
                    'enquiry':{'class':PWLDynamics,
                                    'args':InitNorm()}, 
                    
                     'wait':{'class':PWLDynamics,
                                    'args':InitNorm()}, 
                    
                                    },

        'conversation-flow-norm':{'greet-init':{'class':PWLDynamics,
                                        'args':conversationFlowNorm('greet-init')}, 
                                  'greet-resp':{'class':PWLDynamics,
                                        'args':conversationFlowNorm('greet')},
                                  'bye-init':{'class':PWLDynamics,
                                        'args':conversationFlowNorm('bye-init')}, 
                                  'bye-resp':{'class':PWLDynamics,
                                        'args':conversationFlowNorm('bye-resp')},
                                  'enquiry':{'class':PWLDynamics,
                                        'args':conversationFlowNorm('enquiry')}, 
                                  'inform':{'class':PWLDynamics,
                                        'args':conversationFlowNorm('inform')},
                                  'inform-info':{'class':PWLDynamics,
                                        'args':conversationFlowNorm('inform-info')},
                                  'OK':{'class':PWLDynamics,
                                         'args':conversationFlowNorm('OK')},
 
                                },

        'noRepeat-norm':{\
##                        'enquiry':{'class':PWLDynamics,
##                         'args':noRepeatDyn('enquired')},
                        'greet-init':{'class':PWLDynamics,
                         'args':noRepeatDyn('greeted')},
                        'bye-init':{'class':PWLDynamics,
                         'args':noRepeatDyn('byed')},
                },

        

        'greeted':{'greet-init':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('greeted', 1)},
                 'greet-resp':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('greeted', 1)},
                   'bye-init':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('greeted', 1)},
                 'bye-resp':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('greeted', 1)},
                   'enquiry':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('greeted', 1)},
                 'inform':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('greeted', 1)},

                        },

        'byed':{'bye-init':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('byed', 1)},
                 'bye-resp':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('byed', 1)},
                        },

        'enquired':{'enquiry':{'class':PWLDynamics,
                            'args':deltaActorDyn('enquired', 1)},
                        },

        'being-greeted':{'greet-init':{'class':PWLDynamics,
                            'args':IntendImposeNorm('greet')},
                        'greet-resp':{'class':PWLDynamics,
                            'args':IntendFinishNorm('greet')},
                        },
        'being-byed':{'bye-init':{'class':PWLDynamics,
                            'args':IntendImposeNorm('bye')},
                        'bye-resp':{'class':PWLDynamics,
                            'args':IntendFinishNorm('bye')},
                        },
        
        'being-enquired':{'enquiry':{'class':PWLDynamics,
                            'args':IntendImposeNorm('enquiry')},
                        'inform':{'class':PWLDynamics,
                            'args':IntendFinishNorm('inform')},
                        },
        'being-informed':{'inform-info':{'class':PWLDynamics,
                            'args':IntendImposeNorm('inform-info')},
                        'OK':{'class':PWLDynamics,
                            'args':IntendFinishNorm('OK')},
                        },
                
        'conversation':{\
    
                        'wait':{'class':PWLDynamics,
                            'args':dummyDyn('conversation')},
                        'bye-resp':{'class':PWLDynamics,
                            'args':dummyDyn('conversation')},

                        None:{'class':PWLDynamics,
                                'args':conversationDyn('greet')},
                        'bye-init':{'class':PWLDynamics,
                                'args':conversationDyn('bye')},
                        },
        
        'likeTalk':{\
                        None:{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'wait':{'class':PWLDynamics,
                            'args':dummyDyn('likeTalk')},
                },
                           
                        },
 
        }
