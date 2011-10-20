from teamwork.math.ProbabilityTree import *
from teamwork.math.KeyedMatrix import *
from teamwork.dynamics.pwlDynamics import *
from teamwork.dynamics.arbitraryDynamics import *


def dummyDyn(feature):
    tree1 = ProbabilityTree(IdentityMatrix(feature))
    
    return {'tree':tree1}

def seflObjectDelta(feature,delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}

def seflDelta(feature,delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree2 = createBranchTree(plane,tree0,tree1)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree2,tree1)

    return {'tree':tree3}


def SetDyn(identity,feature,value):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(SetToConstantMatrix(source=feature,value=value))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':identity,
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}


def thresholdDeltaDyn(identity,thresholdFeature,threshold,pn,deltaFeature,delta):
    if pn == 1:
        tree0 = ProbabilityTree(IdentityMatrix(deltaFeature))
        tree1 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,delta))
    else:
        tree1 = ProbabilityTree(IdentityMatrix(deltaFeature))
        tree0 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,delta))
    
    weights = {makeStateKey(identity,thresholdFeature): 1.}
    plane = KeyedPlane(KeyedVector(weights),threshold)

    tree2 = createBranchTree(plane,tree0,tree1)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree3}


def InitNorm():
    tree1 = ProbabilityTree(IdentityMatrix('init-norm'))

    tree4 = ProbabilityTree(IncrementMatrix('init-norm',keyConstant,-.1))

        
## if I have obligations that haven't been satisfied
    weights = {}
    for feature in [\
                    'being-offered',
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


def RespNorm(varname):
    tree0 = ProbabilityTree(IdentityMatrix('resp-norm'))

    tree4 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,-.1))
    tree3 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,.1))

    #varname = 'being-offered'
        
    weights = {makeStateKey('self',varname):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)
    tree2 = createBranchTree(plane,tree4,tree3)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree1 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree1}


def IntendImposeNorm(varname):

    #varname = 'being-offered'
    tree0 = ProbabilityTree(IdentityMatrix(varname))
    tree3 = ProbabilityTree(SetToConstantMatrix(source=varname,value=1))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)

    tree1 = createBranchTree(plane,tree0,tree3)

    return {'tree':tree1}


def IntendFinishNorm(varname):
    #varname = 'being-offered'
    tree0 = ProbabilityTree(IdentityMatrix(varname))
    tree3 = ProbabilityTree(SetToConstantMatrix(source=varname,value=-1))

    weights = {makeStateKey('self',varname):1.}
    plane = KeyedPlane(KeyedVector(weights),.1)
    tree2 = createBranchTree(plane,tree0,tree3)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree1 = createBranchTree(plane,tree0,tree2)
    return {'tree':tree1}



def acceptNS():
    feature = 'NS'
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,.1))
    tree2 = ProbabilityTree(IncrementMatrix(feature,keyConstant,-.1))
    
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)
    
    
    weights = {makeStateKey('self','negative-force'):1.}
    plane = KeyedPlane(KeyedVector(weights),.5)
    tree4 = createBranchTree(plane,tree0,tree2)
    

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree5 = createBranchTree(plane,tree3,tree4)
    return {'tree':tree5}

        
DynFun = {
    'noneDyn': {},
    'basicDyn': {
        'init-norm':{\
                    'offer-unsafesex':{'class':PWLDynamics,
                                'args':InitNorm()},        
                                    
                    'offer-safesex':{'class':PWLDynamics,
                                'args':InitNorm()},
                        
                    'offer-drink':{'class':PWLDynamics,
                                'args':InitNorm()},        
                                    
                    'offer-physicaltouch':{'class':PWLDynamics,
                                'args':InitNorm()},
                    
                    'enquiry':{'class':PWLDynamics,
                                'args':InitNorm()},        
                    },


        'resp-norm':{\
                     'accept-unsafesex':{'class':PWLDynamics,
                                'args':RespNorm('being-offered')},
                     'reject-unsafesex':{'class':PWLDynamics,
                                'args':RespNorm('being-offered')},
                    'accept-safesex':{'class':PWLDynamics,
                                'args':RespNorm('being-offered')},
                     'reject-safesex':{'class':PWLDynamics,
                                'args':RespNorm('being-offered')},
                        
                    'accept-drink':{'class':PWLDynamics,
                                'args':RespNorm('being-offered')},
                     'reject-drink':{'class':PWLDynamics,
                                'args':RespNorm('being-offered')},
                    'accept-physicaltouch':{'class':PWLDynamics,
                                'args':RespNorm('being-offered')},
                     'reject-physicaltouch':{'class':PWLDynamics,
                                'args':RespNorm('being-offered')},
                    
                     'inform':{'class':PWLDynamics,
                                'args':RespNorm('being-enquired')},
                    'inform-negHistory':{'class':PWLDynamics,
                                'args':RespNorm('being-enquired')},    
                                },
        
        'being-enquired':{'enquiry':{'class':PWLDynamics,
                            'args':IntendImposeNorm('being-enquired')},
                        'inform':{'class':PWLDynamics,
                            'args':IntendFinishNorm('being-enquired')},
                        'inform-negHistory':{'class':PWLDynamics,
                            'args':IntendFinishNorm('being-enquired')},
                        },
        
        'being-offered':{'offer-unsafesex':{'class':PWLDynamics,
                            'args':IntendImposeNorm('being-offered')},
                        'offer-safesex':{'class':PWLDynamics,
                            'args':IntendImposeNorm('being-offered')},
                        'accept-unsafesex':{'class':PWLDynamics,
                            'args':IntendFinishNorm('being-offered')},
                        'reject-unsafesex':{'class':PWLDynamics,
                            'args':IntendFinishNorm('being-offered')},
                        'accept-safesex':{'class':PWLDynamics,
                                'args':IntendFinishNorm('being-offered')},
                        'reject-safesex':{'class':PWLDynamics,
                                'args':IntendFinishNorm('being-offered')},
                        
                        'offer-drink':{'class':PWLDynamics,
                            'args':IntendImposeNorm('being-offered')},
                        'offer-physicaltouch':{'class':PWLDynamics,
                            'args':IntendImposeNorm('being-offered')},
                        'accept-drink':{'class':PWLDynamics,
                            'args':IntendFinishNorm('being-offered')},
                        'reject-drink':{'class':PWLDynamics,
                            'args':IntendFinishNorm('being-offered')},
                        'accept-physicaltouch':{'class':PWLDynamics,
                                'args':IntendFinishNorm('being-offered')},
                        'reject-physicaltouch':{'class':PWLDynamics,
                                'args':IntendFinishNorm('being-offered')},
                        },
            
        'NS':{          'accept-unsafesex':{'class':PWLDynamics,
                              'args':seflObjectDelta('NS',.1)},
                        'reject-unsafesex':{'class':PWLDynamics,
                            'args':seflObjectDelta('NS',-.1)},
                        'accept-safesex':{'class':PWLDynamics,
                                'args':seflObjectDelta('NS',.1)},
                        'reject-safesex':{'class':PWLDynamics,
                                'args':seflObjectDelta('NS',-.1)},
                            
                            
                        'accept-drink':{'class':PWLDynamics,
                              #'args':seflObjectDelta('NS',.1)},
                              'args':acceptNS()},
                        'reject-drink':{'class':PWLDynamics,
                            'args':seflObjectDelta('NS',-.1)},
                        'accept-physicaltouch':{'class':PWLDynamics,
                                #'args':seflObjectDelta('NS',.1)},
                                'args':acceptNS()},
                        'reject-physicaltouch':{'class':PWLDynamics,
                                'args':seflObjectDelta('NS',-.1)},
                        },
            
        'health':{'accept-unsafesex':{'class':PWLDynamics,
                        'args':seflDelta('health',-.1)},
                #'accept-safesex':{'class':PWLDynamics,
                #        'args':seflDelta('health',.0)},                      
                        },
            
        'pleasure':{'accept-unsafesex':{'class':PWLDynamics,
                        'args':seflDelta('pleasure',.2)},
                    'accept-safesex':{'class':PWLDynamics,
                        'args':seflDelta('pleasure',.1)},
                        
                        },
        
        'positive-force':{'accept-drink':{'class':PWLDynamics,
                                'args':seflDelta('positive-force',.1)},
                        'accept-physicaltouch':{'class':PWLDynamics,
                                'args':seflDelta('positive-force',.1)},
                        'inform':{'class':PWLDynamics,
                                'args':seflDelta('positive-force',.1)},        
                        },
            
        'negative-force':{'offer-drink':{'class':PWLDynamics,
                            'args':thresholdDeltaDyn('actor','offered-drink',.5,1,'negative-force',.1)},
                        'offer-physicaltouch':{'class':PWLDynamics,
                            'args':thresholdDeltaDyn('self','negative-force',.5,1,'negative-force',.1)},
                        'inform-negHistory':{'class':PWLDynamics,
                            'args':seflObjectDelta('negative-force',.1)},
                        },
        
        'offered-drink':{'offer-drink':{'class':PWLDynamics,
                            'args':SetDyn('actor','offered-drink',1.0)},
                        },
            
        
        'topic':{'offer-unsafesex':{'class':PWLDynamics,
                            'args':SetDyn('object','topic',1)},
                'offer-safesex':{'class':PWLDynamics,
                            'args':SetDyn('object','topic',2)},
                'accept-unsafesex':{'class':PWLDynamics,
                            'args':SetDyn('actor','topic',0)},
                'reject-unsafesex':{'class':PWLDynamics,
                            'args':SetDyn('actor','topic',0)},
                'accept-safesex':{'class':PWLDynamics,
                            'args':SetDyn('actor','topic',0)},
                'reject-safesex':{'class':PWLDynamics,
                            'args':SetDyn('actor','topic',0)},
                
                'offer-drink':{'class':PWLDynamics,
                            'args':SetDyn('object','topic',3)},
                'offer-physicaltouch':{'class':PWLDynamics,
                            'args':SetDyn('object','topic',4)},
                'accept-drink':{'class':PWLDynamics,
                            'args':SetDyn('actor','topic',0)},
                'reject-drink':{'class':PWLDynamics,
                            'args':SetDyn('actor','topic',0)},
                'accept-physicaltouch':{'class':PWLDynamics,
                            'args':SetDyn('actor','topic',0)},
                'reject-physicaltouch':{'class':PWLDynamics,
                            'args':SetDyn('actor','topic',0)},
                        },


        }
}
