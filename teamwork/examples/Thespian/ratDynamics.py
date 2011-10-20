from teamwork.math.ProbabilityTree import *
from teamwork.math.KeyedMatrix import *
from teamwork.dynamics.pwlDynamics import *
from teamwork.dynamics.arbitraryDynamics import *


def dummyDyn(feature):
    tree1 = ProbabilityTree(IdentityMatrix(feature))
    return {'tree':tree1}

def deltaDyn(feature,delta):
    tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    return {'tree':tree}

def setDyn(feature,delta):
    tree = ProbabilityTree(SetToConstantMatrix(feature=feature,value=delta))
    return {'tree':tree}

def objectDeltaDyn(feature,delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    tree = createBranchTree(plane,tree0,tree1)
    return {'tree':tree}


def actorDeltaDyn(feature,delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree3 = createBranchTree(plane,tree0,tree1)
    return {'tree':tree3}


def actorSetDyn(fea, val):
    tree0 = ProbabilityTree(IdentityMatrix(fea))
    tree1 = ProbabilityTree(SetToConstantMatrix(feature=fea,value=val))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}


def objectSetDyn(fea, val):
    tree0 = ProbabilityTree(IdentityMatrix(fea))
    tree1 = ProbabilityTree(SetToConstantMatrix(feature=fea,value=val))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}


def thresholdDeltaDyn(thresholdFeature,threshold,deltaFeature,val):
    tree0 = ProbabilityTree(IdentityMatrix(deltaFeature))
    tree1 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,val))
    weights = {makeStateKey('self',thresholdFeature): 1.}
    plane = KeyedPlane(KeyedVector(weights),threshold)

    tree2 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree2}

def thresholdActorDeltaDyn(thresholdFeature,threshold,deltaFeature,val):
    tree0 = ProbabilityTree(IdentityMatrix(deltaFeature))
    tree1 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,val))
    weights = {makeStateKey('self',thresholdFeature): 1.}
    plane = KeyedPlane(KeyedVector(weights),threshold)

    tree2 = createBranchTree(plane,tree0,tree1)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree3}

def lessThresholdActorDeltaDyn(thresholdFeature,threshold,deltaFeature,val):
    tree0 = ProbabilityTree(IdentityMatrix(deltaFeature))
    tree1 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,val))
    
    weights = {makeStateKey('self',thresholdFeature): 1.}
    plane = KeyedPlane(KeyedVector(weights),threshold)

    tree2 = createBranchTree(plane,tree1,tree0)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree3}

def lessThresholdObjectDeltaDyn(thresholdFeature,threshold,deltaFeature,val):
    tree0 = ProbabilityTree(IdentityMatrix(deltaFeature))
    tree1 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,val))
    
    weights = {makeStateKey('self',thresholdFeature): 1.}
    plane = KeyedPlane(KeyedVector(weights),threshold)

    tree2 = createBranchTree(plane,tree1,tree0)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree3}

def actObjectNotAliveDyn(aliveFeature='ThespianType',deltaFeature='actAlive'):
    tree0 = ProbabilityTree(IdentityMatrix(deltaFeature))
    tree1 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,-.1))

    weights = {makeStateKey('object',aliveFeature):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree2 = createBranchTree(plane,tree0,tree1)                   
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree2)
    
    return {'tree':tree4}


def actActorAliveDyn(aliveFeature='ThespianType',deltaFeature='actAlive'):

    tree0 = ProbabilityTree(IdentityMatrix(deltaFeature))
    tree1 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,-.1))

    weights = {makeStateKey('actor',aliveFeature):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree2 = createBranchTree(plane,tree1,tree0)                   
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree2)
    
    return {'tree':tree4}


def actBothAliveDyn(aliveFeature='ThespianType',deltaFeature='actAlive'):
    tree0 = ProbabilityTree(IdentityMatrix(deltaFeature))
    tree1 = ProbabilityTree(IncrementMatrix(deltaFeature,keyConstant,-.1))

    weights = {makeStateKey('actor',aliveFeature):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree2 = createBranchTree(plane,tree1,tree0)

    weights = {makeStateKey('object',aliveFeature):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree3 = createBranchTree(plane,tree1,tree2)
                       
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree3)
    
    return {'tree':tree4}


def InitNorm(feature='request'):
    tree1 = ProbabilityTree(IdentityMatrix('init-norm'))
    tree4 = ProbabilityTree(IncrementMatrix('init-norm',keyConstant,-.1))
        
## if either actor or object has obligations that haven't been satisfied
    weights = {}
    for feature in [\
                    'being-requested-to-exercise',
                    'being-requested-to-match',
                    ]:
        key = makeStateKey('object',feature)
        weights[key] = 1
        key = makeStateKey('actor',feature)
        weights[key] = 1
        
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree5 = createBranchTree(plane,tree1,tree4)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree0 = createBranchTree(plane,tree1,tree5)

    return {'tree':tree0}


def RespNorm(feature='request'):
    tree0 = ProbabilityTree(IdentityMatrix('resp-norm'))
    tree3 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,.001))
    tree4 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,-.1))
    
    weights = {}
    if feature=='request':
        for feature in [\
                        'being-requested-to-exercise',
                        'being-requested-to-match',
                        ]:
            key = makeStateKey('self',feature)
            weights[key] = 1
    elif feature=='match':
        key = makeStateKey('self','being-requested-for-match-result')
        weights[key] = 1
        
    plane = KeyedPlane(KeyedVector(weights),.001)
    tree2 = createBranchTree(plane,tree4,tree3)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree1 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree1}


def CommitImpose(feature = 'exercise'):
    obl = 'being-requested-to-'+feature
    state = 'commit-to-'+feature
    
    tree0 = ProbabilityTree(IdentityMatrix(state))
    tree1 = ProbabilityTree(SetToConstantMatrix(feature=state,value=1))
    
    weights = {}
    weights = {makeStateKey('self',obl): 1.}
    plane = KeyedPlane(KeyedVector(weights),.001)
    
    tree2 = createBranchTree(plane,tree0,tree1)
    
    if feature == 'match':
        weights = {}
        obl1 = 'requested-to-match'
        weights[makeStateKey('self',obl1)]=1.
        plane = KeyedPlane(KeyedVector(weights),.001)
        tree3 = createBranchTree(plane,tree0,tree1)
    else:
        tree3 = tree0
    
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    tree4 = createBranchTree(plane,tree0,tree3)

    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree1 = createBranchTree(plane,tree4,tree2)

    return {'tree':tree1}

def commitNormDyn (punishList=[],rewardList=[]):
    tree0 = ProbabilityTree(IdentityMatrix('commitNorm'))
    tree1 = ProbabilityTree(IncrementMatrix('commitNorm',keyConstant,-.1))
    
    weights = {}
    for obl in  punishList:
        key = makeStateKey('self',obl)
        weights[key] = 1
    plane = KeyedPlane(KeyedVector(weights),.001)
    tree3 = createBranchTree(plane,tree0,tree1)
        
    if len(rewardList)>0:
        weights = {}
        for obl in  rewardList:
            key = makeStateKey('self',obl)
            weights[key] = 1
        plane = KeyedPlane(KeyedVector(weights),.001)
        tree2 = createBranchTree(plane,tree3,tree0)
    else:
        tree2 = tree3
            
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree4 = createBranchTree(plane,tree0,tree2)
    
    return {'tree':tree4}

DynFun = {
    'noneDyn': {},
    'basicDyn': {
        'init-norm':{\
                    'request-exercise':{'class':PWLDynamics,
                                'args':InitNorm('request')},
                    'request-match':{'class':PWLDynamics,
                                'args':InitNorm('request')},        
                                    },
        
        'resp-norm':{\
                     'accept':{'class':PWLDynamics,
                                'args':RespNorm('request')},
                    #'exercise':{'class':PWLDynamics,
                    #            'args':RespNorm('request')},
                    #'match':{'class':PWLDynamics,
                    #            'args':RespNorm('request')},
                     'reject':{'class':PWLDynamics,
                                'args':RespNorm('request')},
                    'win':{'class':PWLDynamics,
                                'args':RespNorm('match')},
                     'lose':{'class':PWLDynamics,
                                'args':RespNorm('match')},      
                    },
        
        'being-requested-for-match-result':{\
                     'match':{'class':PWLDynamics,
                                'args':setDyn('being-requested-for-match-result',1.0)},
                     'lose':{'class':PWLDynamics,
                                'args':setDyn('being-requested-for-match-result',0.0)},
                    'win':{'class':PWLDynamics,
                                'args':setDyn('being-requested-for-match-result',0.0)},         
                    },
            
        'preferWait':{'wait':{'class':PWLDynamics,
                            'args':actorDeltaDyn('preferWait',.001)},
                     },
        'winChance':{'increasewinChance':{'class':PWLDynamics,
                            'args':actorDeltaDyn('winChance',.001)},
                    'decreasewinChance':{'class':PWLDynamics,
                            'args':actorDeltaDyn('winChance',-0.001)},
                    },
            
        'actAliveNorm':{\
                'buyV':{'class':PWLDynamics,
                    'args':dummyDyn('actAliveNorm')},
                'buyLR':{'class':PWLDynamics,
                    'args':actObjectNotAliveDyn('ThespianType','actAliveNorm')},
                'catchSR':{'class':PWLDynamics,
                    'args':actObjectNotAliveDyn('ThespianType','actAliveNorm')},
                'wait':{'class':PWLDynamics,
                    'args':dummyDyn('actAliveNorm')},
                'exercise':{'class':PWLDynamics,
                    'args':actActorAliveDyn(aliveFeature='ThespianType',deltaFeature='actAliveNorm')},
                'match':{'class':PWLDynamics,
                    'args':actActorAliveDyn(aliveFeature='ThespianType',deltaFeature='actAliveNorm')},
                None:{'class':PWLDynamics,
                    'args':actBothAliveDyn(aliveFeature='ThespianType',deltaFeature='actAliveNorm')},
                },
        },
    'usrDyn':{'specialRule':{\
                     'buyLR':{'class':PWLDynamics,
                                'args':lessThresholdActorDeltaDyn('money',.99,'specialRule',-.1)},
                    'feedV':{'class':PWLDynamics,
                                'args':lessThresholdActorDeltaDyn('money',.04,'specialRule',-.1)},
                    },
        'money':{\
                    'buyLR':{'class':PWLDynamics,
                                'args':deltaDyn('money',-1)},
                    'feedV':{'class':PWLDynamics,
                                'args':deltaDyn('money',-.05)},
                    'win':{'class':PWLDynamics,
                                'args':deltaDyn('money',.1)},
                    },
        
        'being-requested-to-match':{\
                                        'request-match':{'class':PWLDynamics,
                                                            'args':objectSetDyn('being-requested-to-match',1)},
                                       'accept':{'class':PWLDynamics,
                                                            'args':actorSetDyn('being-requested-to-match',0)},
                                       'reject':{'class':PWLDynamics,
                                                            'args':actorSetDyn('being-requested-to-match',0)},
                        },
        
        },

    'ratDyn': {
        'being-requested-to-exercise':{'request-exercise':{'class':PWLDynamics,
                                                            'args':objectSetDyn('being-requested-to-exercise',1)},
                                        'request-match':{'class':PWLDynamics,
                                                            'args':objectSetDyn('being-requested-to-exercise',0)},
                                       'accept':{'class':PWLDynamics,
                                                            'args':actorSetDyn('being-requested-to-exercise',0)},
                                        'exercise':{'class':PWLDynamics,
                                                            'args':actorSetDyn('being-requested-to-exercise',0)},
                                       'reject':{'class':PWLDynamics,
                                                            'args':actorSetDyn('being-requested-to-exercise',0)},
                        },
        
        'being-requested-to-match':{'request-exercise':{'class':PWLDynamics,
                                                            'args':objectSetDyn('being-requested-to-match',0)},
                                        'request-match':{'class':PWLDynamics,
                                                            'args':objectSetDyn('being-requested-to-match',1)},
                                       'accept':{'class':PWLDynamics,
                                                            'args':actorSetDyn('being-requested-to-match',0)},
                                        'match':{'class':PWLDynamics,
                                                            'args':actorSetDyn('being-requested-to-match',0)},
                                       'reject':{'class':PWLDynamics,
                                                            'args':actorSetDyn('being-requested-to-match',0)},
                        },
        
        'requested-to-match':{\
                                        'request-match':{'class':PWLDynamics,
                                                            'args':actorSetDyn('requested-to-match',1)},
                                       'accept':{'class':PWLDynamics,
                                                            'args':objectSetDyn('requested-to-match',0)},
                                       'reject':{'class':PWLDynamics,
                                                            'args':objectSetDyn('requested-to-match',0)},
                        },
        
        'commit-to-exercise':{'accept':{'class':PWLDynamics,
                                        'args':CommitImpose('exercise')},
                            None:{'class':PWLDynamics,
                                        'args':actorSetDyn('commit-to-exercise',0)},
                        },
        'commit-to-match':{'accept':{'class':PWLDynamics,
                                        'args':CommitImpose('match')},
                            None:{'class':PWLDynamics,
                                        'args':actorSetDyn('commit-to-match',0)},
                        },
        'force-to-commit':{'eshock':{'class':PWLDynamics,
                                        'args':objectSetDyn('force-to-commit',1)},
                            'accept':{'class':PWLDynamics,
                                        'args':actorSetDyn('force-to-commit',0)},
                          },
        'avoidShock':{'reject':{'class':PWLDynamics,
                                'args':thresholdActorDeltaDyn('force-to-commit',0.001,'avoidShock',-.1)},
                          },
        'SD':{'feedV':{'class':PWLDynamics,
                        'args':lessThresholdObjectDeltaDyn('SD',.9,'health',.1)},
              'eshock':{'class':PWLDynamics,
                        'args':objectDeltaDyn('SD',-.5)},
            'bad-mouth':{'class':PWLDynamics,
                        'args':objectDeltaDyn('SD',-.3)},
                        },
        'commitNorm':{\
                    'exercise':{'class':PWLDynamics,
                                 'args':commitNormDyn(['commit-to-match'],['commit-to-exercise'])},
                    'match':{'class':PWLDynamics,
                                'args':commitNormDyn(['commit-to-exercise'],['commit-to-match'])},
                    None:{'class':PWLDynamics,
                                'args':commitNormDyn(['commit-to-match','commit-to-exercise'],[])},
                    
                        },
        
        'like-to-exercise':{'exercise':{'class':PWLDynamics,
                                 'args':actorDeltaDyn('like-to-exercise',.01)},
                        },
        
        'like-to-match':{'request-match':{'class':PWLDynamics,
                                 'args':actorDeltaDyn('like-to-match',.01)},
                        },
        
        'just-matched':{'match':{'class':PWLDynamics,
                                 'args':actorSetDyn('just-matched',1)},
                        'win':{'class':PWLDynamics,
                                 'args':setDyn('just-matched',0)},
                        'lose':{'class':PWLDynamics,
                                 'args':setDyn('just-matched',0)},
                        },
        
        },
    'labratDyn': {
        'ThespianType':{'buyLR':{'class':PWLDynamics,
                        'args':objectSetDyn('ThespianType',1)}, 
                },
        'health':{'feedV':{'class':PWLDynamics,
                        'args':lessThresholdObjectDeltaDyn('health',.9,'health',.1)},
                'eshock':{'class':PWLDynamics,
                        'args':objectDeltaDyn('health',-.5)},
                'lose':{'class':PWLDynamics,
                        'args':thresholdDeltaDyn('just-matched',.5,'health',-.5)},
                'exercise':{'class':PWLDynamics,
                        'args':lessThresholdActorDeltaDyn('health',.9,'health',.1)},
                'daypass':{'class':PWLDynamics,
                        'args':thresholdDeltaDyn('ThespianType',0.5,'health',-.1)},
                },
    },
    'streetratDyn': {
        'ThespianType':{'catchSR':{'class':PWLDynamics,
                        'args':objectSetDyn('ThespianType',1)},
                'escape':{'class':PWLDynamics,
                        'args':actorSetDyn('ThespianType',0)}, 
                },
        'health':{'feedV':{'class':PWLDynamics,
                        'args':lessThresholdObjectDeltaDyn('health',.9,'health',.1)},
                'eshock':{'class':PWLDynamics,
                        'args':objectDeltaDyn('health',-.5)},
                'lose':{'class':PWLDynamics,
                        'args':thresholdDeltaDyn('just-matched',.5,'health',-.5)},
                'exercise':{'class':PWLDynamics,
                        'args':lessThresholdActorDeltaDyn('health',.9,'health',.1)},
                },
        
                },
    
    'timerDyn': {
        'specialRule':{'wait':{'class':PWLDynamics,
                        'args':thresholdActorDeltaDyn('time',.9,'specialRule',.02)},
                       'daypass':{'class':PWLDynamics,
                        'args':thresholdActorDeltaDyn('time',-3,'specialRule',.01)},
                },
        'time':{\
                'catchSR':{'class':PWLDynamics,
                    'args':deltaDyn('time',-4)},
                'request-exercise':{'class':PWLDynamics,
                    'args':deltaDyn('time',-1)},
                'request-match':{'class':PWLDynamics,
                    'args':deltaDyn('time',-1)},
                'daypass':{'class':PWLDynamics,
                    'args':setDyn('time',4)},
                },
        'day':{'daypass':{'class':PWLDynamics,
                'args':deltaDyn('day',1)},
                },
    },
    }

