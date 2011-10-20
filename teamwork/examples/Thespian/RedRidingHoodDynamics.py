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
    tree1 = ProbabilityTree(SetToConstantMatrix(source=fea,value=val))
    weights = {makeStateKey('self',thresholdF): 1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree2 = createBranchTree(plane,tree0,tree1)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree2)

    return {'tree':tree3}
    
    
    
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
    tree1 = ProbabilityTree(SetToConstantMatrix(source=fea,value=val))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}


def ObjectSetDyn(fea, val):
    tree0 = ProbabilityTree(IdentityMatrix(fea))
    tree1 = ProbabilityTree(SetToConstantMatrix(source=fea,value=val))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)

    return {'tree':tree3}

   
##def InitNorm(act):
##    tree1 = ProbabilityTree(IdentityMatrix('norm'))
##
##    tree4 = ProbabilityTree(IncrementMatrix('norm',keyConstant,-.1))
##    tree7 = ProbabilityTree(IncrementMatrix('norm',keyConstant,.1))
##
#### action shouldn't happen after closed conversation, or before conversation opened
##
##    if not act in ['greet-init','bye-resp']:
##        weights = {makeStateKey('self','conversation'): 1.}
##        plane = KeyedPlane(KeyedVector(weights),.001)
##        tree6 = createBranchTree(plane,tree4,tree1)
##    else:
##        weights = {makeStateKey('self','conversation'): 1.}
##        plane = KeyedPlane(KeyedVector(weights),.001)
##        tree6 = createBranchTree(plane,tree7,tree4)
##        
#### if I have obligations that haven't been satisfied
##    weights = {}
##    for feature in [\
##                    'being-greeted',
##                    'being-byed',
##                    'being-enquired',
##                    'being-informed',
##                    'being-enquired-about-granny',
##                    ]:
##        key = makeStateKey('self',feature)
##        weights[key] = 1
##        
##    plane = KeyedPlane(KeyedVector(weights),.001)
##
##    tree5 = createBranchTree(plane,tree6,tree4)
##
##    
#### if I have already did this action
##    if act in ['greet','bye']:
##        if act[len(act)-1] == 'e':
##            varname = act+'d'
##        else:
##            varname = act+'ed'
##            
##        weights = {makeStateKey('self',varname):1.}
##        plane = KeyedPlane(KeyedVector(weights),.001)
##        tree2 = createBranchTree(plane,tree5,tree4)
##    else:
##        tree2 = tree5
##
##    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
##                                          'relationship':'equals'}]),0.5)
##    tree0 = createBranchTree(plane,tree1,tree2)
##
##    return {'tree':tree0}


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
    elif act == 'enquiry-about-granny':
        varname = 'being-enquired-about-granny'
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
    elif act == 'enquiry-about-granny':
        varname = 'being-enquired-about-granny'
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

def conversationDyn(intend):
    tree0 = ProbabilityTree(IdentityMatrix('conversation'))
    if intend == 'greet':
        tree1 = ProbabilityTree(SetToConstantMatrix(source='conversation',value=1))
    elif intend == 'bye':
        tree1 = ProbabilityTree(SetToConstantMatrix(source='conversation',value=0))
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree2 = createBranchTree(plane,tree0,tree1)

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree2,tree1)
    
    return {'tree':tree3}

def aliveDyn():
    tree0 = ProbabilityTree(IdentityMatrix('alive'))
    tree1 = ProbabilityTree(SetToConstantMatrix(source='alive',value=0))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)
    
    return {'tree':tree3}

def aliveProbDyn():
    tree0 = ProbabilityTree(IdentityMatrix('alive'))
    tree1 = ProbabilityTree(SetToConstantMatrix(source='alive',value=0))
    
    tree4 = ProbabilityTree()
    tree4.branch(Distribution({tree0:0.8,tree1:0.2}))

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree4)  
    
    return {'tree':tree3}


##def eatenDyn():
##    tree0 = ProbabilityTree(IdentityMatrix('eaten'))
##    tree1 = ProbabilityTree(SetToConstantMatrix(source='eaten',value=1))
##    
##    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
##                                          'relationship':'equals'}]),0.5)
##    
##    tree3 = createBranchTree(plane,tree0,tree1)
##    
##    return {'tree':tree3}


def escapeDyn():
    tree0 = ProbabilityTree(IdentityMatrix('alive'))
    tree1 = ProbabilityTree(SetToConstantMatrix(source='alive',value=1))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)
    
    return {'tree':tree3}

def eatFullDyn():
    tree0 = ProbabilityTree(IdentityMatrix('full'))
    tree1 = ProbabilityTree(IncrementMatrix('full',keyConstant,.5))

    weights = {makeStateKey('actor','full'):1.}
    plane = KeyedPlane(KeyedVector(weights),.9)
    tree2 = createBranchTree(plane,tree1,tree0)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree2)
    
    return {'tree':tree3}

def eatCakeFullDyn():
    tree0 = ProbabilityTree(IdentityMatrix('full'))
    tree1 = ProbabilityTree(IncrementMatrix('full',keyConstant,.2))

    weights = {makeStateKey('object','full'):1.}
    plane = KeyedPlane(KeyedVector(weights),.9)
    tree2 = createBranchTree(plane,tree1,tree0)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree2)
    
    return {'tree':tree3}


def cakeDyn():
    tree0 = ProbabilityTree(IdentityMatrix('has-cake'))
    tree1 = ProbabilityTree(SetToConstantMatrix(source='has-cake',value=1))
    tree2 = ProbabilityTree(SetToConstantMatrix(source='has-cake',value=0))

    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree3,tree2)
    
    return {'tree':tree4}


def knowPersonDyn(name):
    tree0 = ProbabilityTree(IdentityMatrix(name))
    tree1 = ProbabilityTree(SetToConstantMatrix(source=name,value=1))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)
    
    return {'tree':tree3}

   
def moveDyn(dis):
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


def likeActDyn(feature):

    tree0 = ProbabilityTree(IdentityMatrix(feature))
    tree1 = ProbabilityTree(IncrementMatrix(feature,keyConstant,.1))
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree3 = createBranchTree(plane,tree0,tree1)
    
    return {'tree':tree3}


def locationDyn():

    tree0 = ProbabilityTree(IdentityMatrix('sameLocation'))
    tree1 = ProbabilityTree(IncrementMatrix('sameLocation',keyConstant,-.1))


    plane = KeyedPlane(DifferenceRow(keys=[makeStateKey('actor','location'),makeStateKey('object','location')]),0.001)

    tree2 = createBranchTree(plane,tree0,tree1)

    plane = KeyedPlane(DifferenceRow(keys=[makeStateKey('object','location'),makeStateKey('actor','location')]),0.001)

    tree3 = createBranchTree(plane,tree2,tree1)
                       
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree3)
    
    return {'tree':tree4}
    
def actBothAliveDyn():

    tree0 = ProbabilityTree(IdentityMatrix('actAlive'))
    tree1 = ProbabilityTree(IncrementMatrix('actAlive',keyConstant,-.1))

    weights = {makeStateKey('actor','alive'):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree2 = createBranchTree(plane,tree1,tree0)

    weights = {makeStateKey('object','alive'):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree3 = createBranchTree(plane,tree1,tree2)
                       
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree3)
    
    return {'tree':tree4}
    

def actActorAliveDyn():

    tree0 = ProbabilityTree(IdentityMatrix('actAlive'))
    tree1 = ProbabilityTree(IncrementMatrix('actAlive',keyConstant,-.1))

    weights = {makeStateKey('actor','alive'):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree2 = createBranchTree(plane,tree1,tree0)                   
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree2)
    
    return {'tree':tree4}

def actActorAliveOnlyDyn():

    tree0 = ProbabilityTree(IdentityMatrix('actAlive'))
    tree1 = ProbabilityTree(IncrementMatrix('actAlive',keyConstant,-.1))

    weights = {makeStateKey('actor','alive'):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree2 = createBranchTree(plane,tree1,tree0)

    weights = {makeStateKey('object','alive'):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree3 = createBranchTree(plane,tree2,tree1)
                       
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree3)
    
    return {'tree':tree4}


def actBothNotAliveDyn():

    tree0 = ProbabilityTree(IdentityMatrix('actAlive'))
    tree1 = ProbabilityTree(IncrementMatrix('actAlive',keyConstant,-.1))

    weights = {makeStateKey('actor','alive'):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree2 = createBranchTree(plane,tree0,tree1)

    weights = {makeStateKey('object','alive'):1.}
    plane = KeyedPlane(KeyedVector(weights),.001)

    tree3 = createBranchTree(plane,tree2,tree1)
                       
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree3)
    
    return {'tree':tree4}

def specialRuleEatDyn():
    tree0 = ProbabilityTree(IdentityMatrix('specialRule'))
    tree1 = ProbabilityTree(IncrementMatrix('specialRule',keyConstant,-.1))
    
    ## if want to eat granny, must know granny
    weights = {makeStateKey('actor','know-granny'):1.}
    plane = KeyedPlane(KeyedVector(weights),0)

    tree5 = createBranchTree(plane,tree1,tree0)

    plane = KeyedPlane(ClassRow(keys=[{'entity':'object','value':'granny'}]),0)

    tree6 = createBranchTree(plane,tree0,tree5)


    ## can not eat at the location when wolf first meet red
    weights = {makeStateKey('actor','location'):1.}
    plane = KeyedPlane(KeyedVector(weights),0)

    tree2 = createBranchTree(plane,tree1,tree6)

    weights = {makeStateKey('actor','location'):1.}
    plane = KeyedPlane(KeyedVector(weights),-.9)

    tree3 = createBranchTree(plane,tree0,tree2)


    ## the actor's identity must be wolf
    weights = {makeStateKey('actor','identity'):1.}
    plane = KeyedPlane(KeyedVector(weights),0)

    tree7 = createBranchTree(plane,tree3,tree1)


    ## the actor can not eat if it is already full
    weights = {makeStateKey('actor','full'):1.}
    plane = KeyedPlane(KeyedVector(weights),0.9)

    tree8 = createBranchTree(plane,tree7,tree1)
    
        
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree8)
    
    return {'tree':tree4}


def preferWaitWolfDyn():
    tree0 = ProbabilityTree(IdentityMatrix('preferWait'))
    tree2 = ProbabilityTree(IncrementMatrix('preferWait',keyConstant,.1))

    weights = {makeStateKey('self','full'):1.}
    plane = KeyedPlane(KeyedVector(weights),.8)

    tree4 = createBranchTree(plane,tree0,tree2)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)

    tree3 = createBranchTree(plane,tree0,tree4)
    
    return {'tree':tree3}

##def preferWaitDyn():
##    tree0 = ProbabilityTree(IdentityMatrix('preferWait'))
##    tree1 = ProbabilityTree(IncrementMatrix('preferWait',keyConstant,-.01))
##    tree2 = ProbabilityTree(IncrementMatrix('preferWait',keyConstant,-.1))
##
##    weights = {}
##    for feature in [\
##                    'being-greeted',
##                    'being-byed',
##                    'being-enquired',
##                    'being-informed',                 
##                    ]:
##        key = makeStateKey('self',feature)
##        weights[key] = 1
##        
##    plane = KeyedPlane(KeyedVector(weights),.001)
##
##    tree4 = createBranchTree(plane,tree1,tree2)
##    
##    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
##                                          'relationship':'equals'}]),0.5)
##
##    tree3 = createBranchTree(plane,tree0,tree4)
##    
##    return {'tree':tree3}

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


def specialRuleEnquiryDyn():
    
    tree0 = ProbabilityTree(IdentityMatrix('specialRule'))
    tree1 = ProbabilityTree(IncrementMatrix('specialRule',keyConstant,-.1))
    
    
    weights = {makeStateKey('actor','know-granny'):1.}
    plane = KeyedPlane(KeyedVector(weights),0)
    tree3 = createBranchTree(plane,tree0,tree1)
    
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    
    tree4 = createBranchTree(plane,tree0,tree3)
    return {'tree':tree4}


def specialRuleCakeDyn():
    
    tree0 = ProbabilityTree(IdentityMatrix('specialRule'))
    tree1 = ProbabilityTree(IncrementMatrix('specialRule',keyConstant,-.1))
    
    
    weights = {makeStateKey('actor','has-cake'):1.}
    plane = KeyedPlane(KeyedVector(weights),.5)
    tree3 = createBranchTree(plane,tree1,tree0)
    
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
    
    
DynFun = {
    'noneDyn': {},
    'basicDyn': {
##        'norm':{'greet-init':{'class':PWLDynamics,
##                                'args':InitNorm('greet-init')}, 
##                     'greet-resp':{'class':PWLDynamics,
##                                  'args':RespNorm('greet')},
##                     'bye-init':{'class':PWLDynamics,
##                                    'args':InitNorm('bye')}, 
##                     'bye-resp':{'class':PWLDynamics,
##                                'args':RespNorm('bye')},
##                    'enquiry':{'class':PWLDynamics,
##                                    'args':InitNorm('enquiry')}, 
##                     'inform':{'class':PWLDynamics,
##                                'args':RespNorm('inform')},
##                    'inform-info':{'class':PWLDynamics,
##                                'args':InitNorm('inform-info')},
##                    'OK':{'class':PWLDynamics,
##                            'args':RespNorm('OK')},
##                    'enquiry-about-granny':{'class':PWLDynamics,
##                                    'args':InitNorm('enquiry-about-granny')},
##                    'inform-about-granny':{'class':PWLDynamics,
##                                    'args':RespNorm('enquiry-about-granny')},
##                
##                                },
        'resp-norm':{\
                     'greet-resp':{'class':PWLDynamics,
                                  'args':RespNorm('greet')},
                     
                     'bye-resp':{'class':PWLDynamics,
                                'args':RespNorm('bye')},
                    
                     'inform':{'class':PWLDynamics,
                                'args':RespNorm('inform')},
                    
                     'inform-about-granny':{'class':PWLDynamics,
                                    'args':RespNorm('enquiry-about-granny')},
                
                                },
        'makeResp-norm':{\
                     'greet-resp':{'class':PWLDynamics,
                                  'args':MakeRespNorm('greet')},
                     
                     'bye-resp':{'class':PWLDynamics,
                                'args':MakeRespNorm('bye')},
                    
                     'inform':{'class':PWLDynamics,
                                'args':MakeRespNorm('inform')},
                    
                     'inform-about-granny':{'class':PWLDynamics,
                                    'args':MakeRespNorm('enquiry-about-granny')},
                
                                },
        'init-norm':{'greet-init':{'class':PWLDynamics,
                                'args':InitNorm()}, 
                    
                     'bye-init':{'class':PWLDynamics,
                                    'args':InitNorm()}, 
                    
                    'enquiry':{'class':PWLDynamics,
                                    'args':InitNorm()}, 
                    
                    'enquiry-about-granny':{'class':PWLDynamics,
                                    'args':InitNorm()}, 

                    'tell-about-granny':{'class':PWLDynamics,
                                    'args':InitNorm()},
                     'move1':{'class':PWLDynamics,
                                    'args':InitNorm()},
                     'move2':{'class':PWLDynamics,
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
                                  'enquiry-about-granny':{'class':PWLDynamics,
                                                    'args':conversationFlowNorm('enquiry-about-granny')},
                                  'inform-about-granny':{'class':PWLDynamics,
                                                    'args':conversationFlowNorm('enquiry-about-granny')},
                                  'tell-about-granny':{'class':PWLDynamics,
                                                    'args':conversationFlowNorm('enquiry-about-granny')},
                
                                },

            'noRepeat-norm':{\
##                        'enquiry':{'class':PWLDynamics,
##                         'args':noRepeatDyn('enquired')},
                        'tell-about-granny':{'class':PWLDynamics,
                         'args':noRepeatDyn('told-about-granny')},
                        'give-cake':{'class':PWLDynamics,
                         'args':noRepeatDyn('given-cake')},
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
                   'enquiry-about-granny':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('greeted', 1)},
                 'inform-about-granny':{'class':PWLDynamics,
                            'args':deltaActorOrObjectDyn('greeted', 1)},
                   'tell-about-granny':{'class':PWLDynamics,
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

        'given-cake':{'give-cake':{'class':PWLDynamics,
                                'args':deltaActorDyn('given-cake', 1)},
                        },
        'told-about-granny':{'tell-about-granny':{'class':PWLDynamics,
                                'args':deltaActorDyn('told-about-granny', 1)},
                             'inform-about-granny':{'class':PWLDynamics,
                                'args':deltaActorDyn('told-about-granny', 1)},
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
                        'eat':{'class':PWLDynamics,
                            'args':conversationDyn('bye')},
                        
                        'kill':{'class':PWLDynamics,
                            'args':conversationDyn('bye')},
                        
                        'escape':{'class':PWLDynamics,
                            'args':dummyDyn('conversation')},
                        
                        'resurrect':{'class':PWLDynamics,
                            'args':dummyDyn('conversation')},
    
                        'wait':{'class':PWLDynamics,
                            'args':dummyDyn('conversation')},
                        'move1':{'class':PWLDynamics,
                            'args':conversationDyn('bye')},
                        'move2':{'class':PWLDynamics,
                            'args':conversationDyn('bye')},
    
                        'bye-resp':{'class':PWLDynamics,
                            'args':dummyDyn('conversation')},
                        'give-cake':{'class':PWLDynamics,
                            'args':dummyDyn('conversation')},
                        
                        None:{'class':PWLDynamics,
                                'args':conversationDyn('greet')},
                        'bye-init':{'class':PWLDynamics,
                                'args':conversationDyn('bye')},
                        },
                           
                        },
        'RedDyn': {
            'alive':{\
                     'hunter-kill-wolf':{'class':PWLDynamics,
                            'args':aliveDyn()},
                     'fairy-kill-wolf':{'class':PWLDynamics,
                            'args':aliveDyn()},
                     'red-kill-wolf':{'class':PWLDynamics,
                            'args':aliveProbDyn()},
                     'eat':{'class':PWLDynamics,
                            'args':aliveDyn()},
                     'escape':{'class':PWLDynamics,
                            'args':escapeDyn()},
                     'resurrect':{'class':PWLDynamics,
                            'args':ObjectSetDyn('alive',1.0)},
                },
            'full':{'eat':{'class':PWLDynamics,
                            'args':eatFullDyn()},
                    'give-cake':{'class':PWLDynamics,
                            'args':eatCakeFullDyn()},   
                },
##            'eaten':{'eat':{'class':PWLDynamics,
##                            'args':eatenDyn()},
##                },
            'has-cake':{'give-cake':{'class':PWLDynamics,
                            'args':cakeDyn()},
                },
            'location':{\
                     'move1':{'class':PWLDynamics,
                            'args':moveDyn(1)},
                     'move2':{'class':PWLDynamics,
                            'args':moveDyn(2)},
                },
            'know-granny':{\
                     'tell-about-granny':{'class':PWLDynamics,
                                          'args':knowPersonDyn('know-granny')},
                     'inform-about-granny':{'class':PWLDynamics,
                                          'args':knowPersonDyn('know-granny')},
                },
            'likeMove':{'move1':{'class':PWLDynamics,
                                'args':likeActDyn('likeMove')},
                        'move2':{'class':PWLDynamics,
                                'args':likeActDyn('likeMove')},
                        
                },
            'likeTalk':{'greet-init':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'greet-resp':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'bye-init':{'class':PWLDynamics,
                               'args':likeActDyn('likeTalk')},
                        'bye-resp':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'tell-about-granny':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'inform-about-granny':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'inform':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'enquiry':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'inform-about-granny':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                        'enquiry-about-granny':{'class':PWLDynamics,
                                'args':likeActDyn('likeTalk')},
                },
            'sameLocation':{'wait':{'class':PWLDynamics,
                            'args':dummyDyn('sameLocation')},
                            'move1':{'class':PWLDynamics,
                            'args':dummyDyn('sameLocation')},
                            'move2':{'class':PWLDynamics,
                            'args':dummyDyn('sameLocation')},
                            'changeIdentity':{'class':PWLDynamics,
                            'args':dummyDyn('sameLocation')},
                            None:{'class':PWLDynamics,
                            'args':locationDyn()},
                },
            'actAlive':{'wait':{'class':PWLDynamics,
                        'args':dummyDyn('actAlive')},
                        'move1':{'class':PWLDynamics,
                        'args':actActorAliveDyn()},
                        'move2':{'class':PWLDynamics,
                        'args':actActorAliveDyn()},
                        'changeIdentity':{'class':PWLDynamics,
                        'args':actActorAliveDyn()},
                        'escape':{'class':PWLDynamics,
                        'args':actBothNotAliveDyn()},
                        None:{'class':PWLDynamics,
                        'args':actBothAliveDyn()},
                },
            'specialRule':{'eat':{'class':PWLDynamics,
                            'args':specialRuleEatDyn(),},
                            'enquiry-about-granny':{'class':PWLDynamics,
                            'args':specialRuleEnquiryDyn()},
                           'enquiry':{'class':PWLDynamics,
                            'args':specialRuleEnquiryDyn()},
                           'give-cake':{'class':PWLDynamics,
                            'args':specialRuleCakeDyn()},
                },

            'preferWait':{'wait':{'class':PWLDynamics,
                         'args':preferWaitWolfDyn()},
                },
            'being-enquired-about-granny':{\
                'enquiry-about-granny':{'class':PWLDynamics,
                         'args':thresholdObjectSetDyn('SDwithWolf','being-enquired-about-granny',1)},
                'inform-about-granny':{'class':PWLDynamics,
                         'args':ActorSetDyn('being-enquired-about-granny',0)},
                },
            'SDwithWolf':{None:{'class':PWLDynamics,
                        'args':SDDyn('SDwithWolf')},
                          'wait':{'class':PWLDynamics,
                            'args':dummyDyn('SDwithWolf')},
                            'move1':{'class':PWLDynamics,
                            'args':dummyDyn('SDwithWolf')},
                            'move2':{'class':PWLDynamics,
                            'args':dummyDyn('SDwithWolf')},
                          'escape':{'class':PWLDynamics,
                            'args':dummyDyn('SDwithWolf')},
                          'enquiry-about-granny':{'class':PWLDynamics,
                            'args':thresholdDecrease('SDwithWolf')},
                          },
            'SDnorm':{'enquiry-about-granny':{'class':PWLDynamics,
                            'args':SDnormDyn('enquiry-about-granny')},
                          },
            'identity':{'changeIdentity':{'class':PWLDynamics,
                            'args':deltaActorDyn('identity',2.0)},
                          },
        
            }
        }
