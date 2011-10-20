from teamwork.math.ProbabilityTree import *
from teamwork.math.KeyedMatrix import *
from teamwork.dynamics.pwlDynamics import *
from teamwork.dynamics.arbitraryDynamics import *



def dummyDyn(feature):
    tree1 = ProbabilityTree(IdentityMatrix(feature))
    return {'tree':tree1}

def actorClassDeltaDyn(identity, feature, delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    
    plane = KeyedPlane(ClassRow(keys=[{'entity':'actor','value':identity}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}

    
#def setToDyn(feature,entity,efeature,value):
#    key = makeStateKey(entity,efeature)
#    tree = ProbabilityTree (SetToFeatureMatrix(feature,key,value))
#    return {'tree':tree}

def DeltaDyn(identity,feature,delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':identity,
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}


def seflObjectDelta(feature,delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}

def seflActorDelta(feature,delta):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,delta))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
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


def SetDyn2(identity, className, feature,value):
    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(SetToConstantMatrix(source=feature,value=value))
    plane = KeyedPlane(ClassRow(keys=[{'entity':identity,'value':className}]),.5)
    tree3 = createBranchTree(plane,tree0,tree1)
    return {'tree':tree3}


def SetDyn3(feature,value):
    tree1 = ProbabilityTree(SetToConstantMatrix(source=feature,value=value))
    return {'tree':tree1}



def SetToFeature(feature1, character, feature2):
    tree0 = ProbabilityTree(IdentityMatrix(feature2))
    key = makeStateKey(character,feature2)
    tree1 = ProbabilityTree(SetToFeatureMatrix(feature1,key,value=1))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree2 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree2}
    
    
    
    
def InitNorm():
    tree1 = ProbabilityTree(IdentityMatrix('init-norm'))

    tree4 = ProbabilityTree(IncrementMatrix('init-norm',keyConstant,-.1))

        
## if I have obligations that haven't been satisfied
    weights = {}
    for feature in [\
                    #'being-greeted',
                    #'being-byed',
                    'being-enquired',
                    #'being-informed',
                    #'being-enquired-about-granny',
                    ]:
        key = makeStateKey('self',feature)
        weights[key] = 1
        
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree5 = createBranchTree(plane,tree1,tree4)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree0 = createBranchTree(plane,tree1,tree5)

    return {'tree':tree0}


def RespNorm():
    tree0 = ProbabilityTree(IdentityMatrix('resp-norm'))

    #tree4 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,-.1))
    tree3 = ProbabilityTree(IncrementMatrix('resp-norm',keyConstant,.1))
    tree4 = tree0

    varname = 'being-enquired'
        
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
    elif act == 'enquiry-about-granny':
        varname = 'being-enquired-about-granny'
    else:
        varname = 'being-'+act
        if act[len(act)-1] == 'e':
            varname += 'd'
        else:
            varname += 'ed'
    tree0 = ProbabilityTree(IdentityMatrix(varname))
    tree3 = ProbabilityTree(SetToConstantMatrix(source=varname,value=1))
    
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
    elif act == 'enquiry-about-granny':
        varname = 'being-enquired-about-granny'
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


   
def movePosDyn(dis):
    if dis == 1:
        val1=.1
        val2=-.1
    else:
        val1=.2
        val2=-.2

    tree0 = ProbabilityTree(IdentityMatrix('location'))
    tree1 = ProbabilityTree(IncrementMatrix('location',keyConstant,val1))
    tree2 = ProbabilityTree(IncrementMatrix('location',keyConstant,val2))

    weights = {makeStateKey('actor','location'):1.}
    plane = KeyedPlane(KeyedVector(weights),.9)
    tree3 = createBranchTree(plane,tree1,tree2)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)

    tree4 = createBranchTree(plane,tree0,tree3)
    return {'tree':tree4}
    

def moveNegDyn(dis):
    if dis == -1:
        val1=-.1
        val2=.1
    else:
        val1=-.2
        val2=.2

    tree0 = ProbabilityTree(IdentityMatrix('location'))
    tree1 = ProbabilityTree(IncrementMatrix('location',keyConstant,val1))
    tree2 = ProbabilityTree(IncrementMatrix('location',keyConstant,val2))

    weights = {makeStateKey('actor','location'):1.}
    plane = KeyedPlane(KeyedVector(weights),-.9)
    tree3 = createBranchTree(plane,tree2,tree1)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)

    tree4 = createBranchTree(plane,tree0,tree3)
    return {'tree':tree4}


#def locationDyn():
#    tree0 = ProbabilityTree(IdentityMatrix('sameLocation'))
#    tree1 = ProbabilityTree(IncrementMatrix('sameLocation',keyConstant,-.1))
#
#
#    plane = KeyedPlane(DifferenceRow(keys=[makeStateKey('actor','location'),makeStateKey('object','location')]),0.001)
#
#    tree2 = createBranchTree(plane,tree0,tree1)
#
#    plane = KeyedPlane(DifferenceRow(keys=[makeStateKey('object','location'),makeStateKey('actor','location')]),0.001)
#
#    tree3 = createBranchTree(plane,tree2,tree1)
#                       
#        
#    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
#                                          'relationship':'equals'}]),0.5)
#    
#    tree4 = createBranchTree(plane,tree0,tree3)
#    
#    return {'tree':tree4}

#def specialRuleEscapeDyn():
#    tree0 = ProbabilityTree(IdentityMatrix('specialRule'))
#    tree1 = ProbabilityTree(IncrementMatrix('specialRule',keyConstant,-.1))
#
#
#    plane = KeyedPlane(DifferenceRow(keys=[makeStateKey('actor','location'),makeStateKey('object','location')]),0.001)
#
#    tree2 = createBranchTree(plane,tree0,tree1)
#
#    plane = KeyedPlane(DifferenceRow(keys=[makeStateKey('object','location'),makeStateKey('actor','location')]),0.001)
#
#    tree3 = createBranchTree(plane,tree2,tree1)
#                       
#        
#    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
#                                          'relationship':'equals'}]),0.5)
#    
#    tree4 = createBranchTree(plane,tree0,tree3)
#    
#    return {'tree':tree4}    
    
    
def killAliveDyn():
    tree0 = ProbabilityTree(IdentityMatrix('alive'))
    tree1 = ProbabilityTree(SetToConstantMatrix(source='alive',value=0))
    
    key1 = makeStateKey('actor','power')
    key2 = makeStateKey('object','power')
    
    weights = {key1:1.,key2:-1.}
    planeActor = KeyedPlane(KeyedVector(weights),.01)
    
    tree2 = createBranchTree(planeActor,tree1,tree0)
    
    weights = {key1:-1.,key2:1.}
    planeObject = KeyedPlane(KeyedVector(weights),.01)
    
    tree3 = createBranchTree(planeObject,tree1,tree0)
    
    plane2 = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane2,tree0,tree3)
    
    plane1 = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree5 = createBranchTree(plane1,tree4,tree2)
    return {'tree':tree5}


#def AliveDyn(feature):
#    tree0 = ProbabilityTree(IdentityMatrix(feature))
#    tree1 = ProbabilityTree(SetToConstantMatrix(source=feature,value=0))
#    
#    key1 = makeStateKey('actor','power')
#    key2 = makeStateKey('object','power')
#    
#    weights = {key1:-1.,key2:1.}
#    planeObject = KeyedPlane(KeyedVector(weights),.01)
#    
#    tree2 = createBranchTree(planeObject,tree1,tree0)
#    
#    return {'tree':tree2}



def HasCakeDyn():
    tree0 = ProbabilityTree(IdentityMatrix('has-cake'))
    tree1 = ProbabilityTree(SetToConstantMatrix(source='has-cake',value=0))
    tree2 = ProbabilityTree(SetToConstantMatrix(source='has-cake',value=1))

    
    plane2 = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane2,tree0,tree2)
    
    plane1 = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree5 = createBranchTree(plane1,tree4,tree1)
    return {'tree':tree5}



def SDNormDyn():
    tree0 = ProbabilityTree(IdentityMatrix('SD-norm'))
    tree1 = ProbabilityTree(IncrementMatrix('SD-norm',keyConstant,-.5))
    
    weights = {makeStateKey('wolf','SD'):1.}
    plane = KeyedPlane(KeyedVector(weights),.8)
    tree2 = createBranchTree(plane,tree1,tree0)
    
    plane1 = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree5 = createBranchTree(plane1,tree0,tree2)
    return {'tree':tree5}
    
    
DynFun = {
    'noneDyn': {},
    'basicDyn': {
 
        'init-norm':{\
                    'enquiry':{'class':PWLDynamics,
                                    'args':InitNorm()}, 
                     'move1':{'class':PWLDynamics,
                                    'args':InitNorm()},
                     'move2':{'class':PWLDynamics,
                                    'args':InitNorm()},
                     'wait':{'class':PWLDynamics,
                                    'args':InitNorm()},
                    'kill':{'class':PWLDynamics,
                                    'args':InitNorm()},
                    'eat':{'class':PWLDynamics,
                                    'args':InitNorm()},
                    'give-cake':{'class':PWLDynamics,
                                    'args':InitNorm()},
                    'moveto-granny':{'class':PWLDynamics,
                                    'args':InitNorm()},
                    'help':{'class':PWLDynamics,
                                    'args':InitNorm()}, 
                    
                    },
        
        'resp-norm':{\
                     'inform':{'class':PWLDynamics,
                                'args':RespNorm()},
                     'talkabout-granny':{'class':PWLDynamics,
                                'args':RespNorm()},  
                                },
            
        'being-enquired':{'enquiry':{'class':PWLDynamics,
                            'args':IntendImposeNorm('enquiry')},
                        'inform':{'class':PWLDynamics,
                            'args':IntendFinishNorm('inform')},
                        'talkabout-granny':{'class':PWLDynamics,
                            'args':IntendFinishNorm('inform')},
                        },
        'enquired':{'enquiry':{'class':PWLDynamics,
                            'args':SetDyn('actor','enquired',1.0)},
                    'inform':{'class':PWLDynamics,
                            'args':SetDyn('object','enquired',0.0)},
                    'talkabout-granny':{'class':PWLDynamics,
                            'args':SetDyn('object','enquired',0.0)},
                        },
                        },
        'RedSelfDyn': {
            'eaten':{'eat':{'class':PWLDynamics,
                        'args':SetDyn('object','eaten',1.0)},
                    'escape':{'class':PWLDynamics,
                         'args':SetDyn('actor','eaten',0.0)},
                    'kill':{'class':PWLDynamics,
                         'args':dummyDyn('eaten')},
                        
            },
            
        },
            
        'grannySelfDyn': {
            'eaten':{'eat':{'class':PWLDynamics,
                        'args':SetDyn('object','eaten',1.0)},
                    'escape':{'class':PWLDynamics,
                         'args':SetDyn('actor','eaten',0.0)},
                    'kill':{'class':PWLDynamics,
                         'args':dummyDyn('eaten')},
            },
        },
        
        'woodcutterSelfDyn': {
            
        },
        
        'RedDyn': {
            'preferWait':{'wait':{'class':PWLDynamics,
                            'args':seflActorDelta('preferWait',.1)},
            },
            
            
            
            #'redEaten':{'eat':{'class':PWLDynamics,
            #            'args':SetDyn2('object','red','redEaten',1.0)},
            #           'escape':{'class':PWLDynamics,
            #             'args':SetDyn2('actor','red','redEaten',0.0)},
            #             'kill':{'class':PWLDynamics,
            #             'args':SetDyn3('redEaten',0.0)},
            #},
            #    
            #'grannyEaten':{'eat':{'class':PWLDynamics,
            #            'args':SetDyn2('object','granny','grannyEaten',1.0)},
            #           'escape':{'class':PWLDynamics,
            #             'args':SetDyn2('actor','granny','grannyEaten',0.0)},
            #             'kill':{'class':PWLDynamics,
            #             'args':SetDyn3('grannyEaten',0.0)},
            #},
                    
            'SD':{'enquiry':{'class':PWLDynamics,
                            'args':seflDelta('SD',.05)},
                  'inform':{'class':PWLDynamics,
                            'args':seflDelta('SD',.05)},
                  'help':{'class':PWLDynamics,
                            'args':seflActorDelta('SD',.5)},
                  'give-cake':{'class':PWLDynamics,
                            'args':seflActorDelta('SD',.5)},
                  'eat':{'class':PWLDynamics,
                        'args':SetDyn('actor','SD',-1.0)},
            },
            
            'helped':{'help':{'class':PWLDynamics,
                            'args':SetDyn('actor','helped',1.0)},
            },
            
            'SD-norm':{'talkabout-granny':{'class':PWLDynamics,
                            'args':SDNormDyn()},
                        },
            'eaten':{'eat':{'class':PWLDynamics,
                        'args':SetDyn('object','eaten',1.0)},
                    'escape':{'class':PWLDynamics,
                         'args':SetDyn('actor','eaten',0.0)},
                    'kill':{'class':PWLDynamics,
                         'args':SetDyn3('eaten',0.0)},
            },
            'power':{\
                     'give-gun':{'class':PWLDynamics,
                            'args':DeltaDyn('object','power',1.0)},
                },
                
                
            'full':{'eat':{'class':PWLDynamics,
                            'args':DeltaDyn('actor','full',0.5)},
                    'eat-cake':{'class':PWLDynamics,
                            'args':DeltaDyn('actor','full',0.1)},
                },

            'has-cake':{'give-cake':{'class':PWLDynamics,
                            'args':HasCakeDyn()},
                        'eat-cake':{'class':PWLDynamics,
                            'args':SetDyn('actor','has-cake',0.0)},
                },
            'alive':{'kill':{'class':PWLDynamics,
                            'args':killAliveDyn()},
                             },
            
            #'wolfAlive':{\
            #                'kill':{'class':PWLDynamics,
            #                        'args':AliveDyn('wolfAlive')},
            #                 },
            #'redAlive':{\
            #                'kill':{'class':PWLDynamics,
            #                        'args':AliveDyn('redAlive')},
            #                 },
            
            #'sameLocation':{'wait':{'class':PWLDynamics,
            #                'args':dummyDyn('sameLocation')},
            #                'move1':{'class':PWLDynamics,
            #                'args':dummyDyn('sameLocation')},
            #                'move2':{'class':PWLDynamics,
            #                'args':dummyDyn('sameLocation')},
            #                'moveto-granny':{'class':PWLDynamics,
            #                'args':dummyDyn('sameLocation')},
            #                #'changeIdentity':{'class':PWLDynamics,
            #                #'args':dummyDyn('sameLocation')},
            #                None:{'class':PWLDynamics,
            #                'args':locationDyn()},
            #    },
            #    
            'location':{\
                     'move1':{'class':PWLDynamics,
                            'args':movePosDyn(1)},
                     'move2':{'class':PWLDynamics,
                            'args':movePosDyn(2)},
                    'move-1':{'class':PWLDynamics,
                            'args':moveNegDyn(-1)},
                     'move-2':{'class':PWLDynamics,
                            'args':moveNegDyn(-2)},
                     'escape':{'class':PWLDynamics,
                            'args':SetToFeature('location','wolf','location')},
                     'moveto-granny':{'class':PWLDynamics,
                            'args':SetToFeature('location','granny','location')},
                },

            'likeMove':{'move1':{'class':PWLDynamics,
                                'args':DeltaDyn('actor','likeMove',0.1)},
                        'move2':{'class':PWLDynamics,
                                'args':DeltaDyn('actor','likeMove',0.1)},
                        'move-1':{'class':PWLDynamics,
                                'args':DeltaDyn('actor','likeMove',0.1)},
                        'move-2':{'class':PWLDynamics,
                                'args':DeltaDyn('actor','likeMove',0.1)},
                        #'moveto-granny':{'class':PWLDynamics,
                        #        'args':DeltaDyn('actor','likeMove',0.1)},
                        
                },
            'likeTalk':{
                        'inform':{'class':PWLDynamics,
                                'args':DeltaDyn('actor','likeTalk',0.1)},
                        'enquiry':{'class':PWLDynamics,
                                'args':DeltaDyn('actor','likeTalk',0.1)},
                        'talkabout-granny':{'class':PWLDynamics,
                                'args':DeltaDyn('actor','likeTalk',0.1)},
                },
                
            'know-granny':{
                        'talkabout-granny':{'class':PWLDynamics,
                                            'args':SetDyn('object','know-granny',1.0)},
                },
                
            'indoor':{
                        'enter-house':{'class':PWLDynamics,
                                            'args':SetDyn('actor','indoor',1.0)},
                        'exist-house':{'class':PWLDynamics,
                                            'args':SetDyn('actor','indoor',0.0)},
                },
            #'specialRule':{
            #    'escape':{'class':PWLDynamics,
            #                'args':specialRuleDyn('escape')},
            #}
            
            }
        }
