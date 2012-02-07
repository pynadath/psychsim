from teamwork.math.Keys import *
from teamwork.math.KeyedVector import *
from teamwork.math.KeyedMatrix import *
from teamwork.math.ProbabilityTree import *

def setTo(entity,feature,value):
    setTree = ProbabilityTree(SetToConstantMatrix(source=feature,value=value))
    if entity == 'self':
        return {'tree':setTree}
    else:
        unchangedTree = ProbabilityTree(IdentityMatrix(feature))
        plane = KeyedPlane(IdentityRow(keys=[{'entity':entity,
                                              'relationship':'equals'}]),0.5)
        tree = createBranchTree(plane,unchangedTree,setTree)
        return {'tree':tree}

def setToConstant(feature,value):
	setTree = ProbabilityTree(SetToConstantMatrix(source=feature,value=value))
	return {'tree':setTree}


def add(entity,feature,scale=0.1,sourceFeature=None):
    if not sourceFeature:
        sourceFeature = feature
    objTree = ProbabilityTree(ScaleMatrix(feature,
                                          StateKey({'entity':entity,
                                                    'feature':sourceFeature}),
                                          scale))
    unchangedTree = ProbabilityTree(IdentityMatrix(feature))
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree = createBranchTree(plane,unchangedTree,objTree)
    return {'tree':tree}

def incActor(feature,amount=.01,condition=False):
    trees = {}
    trees['increment'] = ProbabilityTree(IncrementMatrix(feature,keyConstant,amount))
    trees['unchanged'] = ProbabilityTree(IdentityMatrix(feature))
    if condition:
        # Test for the given condition
        plane = KeyedPlane(ThresholdRow(keys=[{'entity':'self',
                                               'feature':condition}]),0.5)
        trees['actor'] = createBranchTree(plane,trees['unchanged'],
                                          trees['increment'])
    else:
        trees['actor'] = trees['increment']
    # Test whether actor
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    trees['top'] = createBranchTree(plane,trees['unchanged'],
                                    trees['actor'])
    return {'tree':trees['top']}
    


def increment(feature,amount=.01):
    trees = {}
    trees['object'] = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                                amount))
    trees['not object'] = ProbabilityTree(IdentityMatrix(feature))
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    trees['top'] = createBranchTree(plane,trees['not object'],
                                    trees['object'])
    return {'tree':trees['top']}

# bad code to handle negotiationstatus - see version 2 below

def negotiationStatus(feature,value,sourceFeature):
    trees = {}
    planes = {}
    planes['selfActor'] = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                                        'relationship':'equals'}]),0.5)
    planes['selfObject'] = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                                         'relationship':'equals'}]),0.5)
    smatrix = SetToFeatureMatrix(feature, StateKey({'entity':'object','feature':sourceFeature}), 1.0)
    
    trees['set'] = ProbabilityTree(KeyedMatrix(smatrix))
    smatrix = SetToFeatureMatrix(feature, StateKey({'entity':'object','feature':sourceFeature}), 1.0)
    trees['set2'] = ProbabilityTree(KeyedMatrix(smatrix))
    trees['selfObj'] =  createBranchTree(planes['selfObject'],ProbabilityTree(IdentityMatrix(feature)), trees['set'])
    trees['selfActor'] =  createBranchTree(planes['selfActor'],trees['selfObj'],trees['set2'])
    return {'tree':trees['selfActor']}


def negotiationStatus2(feature,sourceFeature):
    mat = SetToFeatureMatrix(feature, StateKey({'entity':'object',
						'feature':sourceFeature}), 1.0)
    return {'tree':ProbabilityTree(mat)}

def contractStatus(myfeat,otherfeat):
    trees = {}
    planes = {}
    setObjTree = ProbabilityTree(SetToFeatureMatrix(myfeat, StateKey({'entity':'object','feature':otherfeat}), 1.0))
    setActTree = ProbabilityTree(SetToFeatureMatrix(myfeat, StateKey({'entity':'actor','feature':otherfeat}), 1.0))
    planes['amActor'] = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                                      'relationship':'equals'}]),0.5)
    trees['top'] = createBranchTree(planes['amActor'],setActTree,setObjTree)
    return {'tree':trees['top']}

# scale multiple entries

def negotReject(feature,notsetlst):
    
##    uplane = KeyedPlane(ThresholdRow(keys=[{'entity':'object',
##					    'feature':'unpaired'}]),0.5)
    aplane = KeyedPlane(ThresholdRow(keys=[{'entity':'object',
					    'feature':'accepted'}]),0.5)
    tplane = KeyedPlane(ThresholdRow(keys=[{'entity':'object',
					    'feature':'terminated'}]),0.5)
 #    fplane = KeyedPlane(ThresholdRow(keys=[{'entity':'object',
#					    'feature':'feature'}]),0.0)

    tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,-0.1))
    utree = ProbabilityTree(IncrementMatrix(feature,keyConstant,-0.2))
    atree = ProbabilityTree(IncrementMatrix(feature,keyConstant,-0.3))
    ttree = ProbabilityTree(IncrementMatrix(feature,keyConstant,-0.4))
#    ftree = ProbabilityTree(IncrementMatrix(feature,keyConstant,0.5))

    if len(notsetlst) > 0:
        uptree = createORTree(map(lambda k:(k,True),notsetlst),tree,utree)
                                      
##    tree = createBranchTree(uplane,utree,tree)
    tree = createBranchTree(aplane,uptree,atree)
    tree = createBranchTree(tplane,tree,ttree)
    plane = makeIdentityPlane('object')
    tree = createBranchTree(plane,ProbabilityTree(IdentityMatrix(feature)),
			      tree)

##    print tree
    return {'tree':tree}



# Increment feature of multiple entities

def modelInc(feature, inclst):
    ltTree = ProbabilityTree(IdentityMatrix(feature))
    for dyn in inclst:
        if dyn['relationship'] == 'self':
            plane = makeIdentityPlane('actor')
	elif dyn['relationship'] == 'object':
            plane = makeIdentityPlane('object')
	elif dyn['relationship'] == 'actor':
            plane = makeIdentityPlane('actor')
        else:
            plane = KeyedPlane(RelationshipRow(keys=[{'feature':dyn['relationship'],
                                                      'relatee':'object'}]),0.5)
        tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                          dyn['value']))
	ltTree = createBranchTree(plane,ltTree,tree)
    return {'tree':ltTree}

# Increment feature of multiple entities but only if key is true

def modelIncK(key, feature, inclst):
    ltTree = ProbabilityTree(IdentityMatrix(feature))
    for dyn in inclst:
        if dyn['relationship'] == 'actor':
            plane = makeIdentityPlane('actor')
	elif dyn['relationship'] == 'self':
            plane = makeIdentityPlane('actor')
	elif dyn['relationship'] == 'object':
            plane = makeIdentityPlane('object')
        else:
            plane = KeyedPlane(RelationshipRow(keys=[{'feature':dyn['relationship'],
                                                      'relatee':'object'}]),0.5)
        tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                          dyn['value']))
	ltTree = createBranchTree(plane,ltTree,tree)

    if key:
        plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
        ltTree = createBranchTree(plane,ProbabilityTree(IdentityMatrix(feature)),
			      ltTree)
    return {'tree':ltTree}

def modelIncDecK(key, feature, inclst, feature2, decval):
    ltTree = ProbabilityTree(IdentityMatrix(feature))
    for dyn in inclst:
        if dyn['relationship'] == 'actor':
            plane = makeIdentityPlane('actor')
	elif dyn['relationship'] == 'self':
            plane = makeIdentityPlane('actor')
	elif dyn['relationship'] == 'object':
            plane = makeIdentityPlane('object')
        else:
            plane = KeyedPlane(RelationshipRow(keys=[{'feature':dyn['relationship'],
                                                      'relatee':'object'}]),0.5)
        tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                          dyn['value']))
	ltTree = createBranchTree(plane,ltTree,tree)

    if key:
        plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
        ltTree = createBranchTree(plane,ProbabilityTree(IncrementMatrix(feature2,keyConstant,
                                          decval)),
				  ltTree)
    return {'tree':ltTree}

# if entity
# if any notsetlst conditions are true, decrement
# if all setlst are true, increment
# else do nothing

def decInc(entity, feature, incval, decval, setlst, notsetlst, incval2=0.0):
    tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  incval))
    decval = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  decval))
    sameval = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  incval2))
##    for key in setlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane,copy.deepcopy(sameval),
##				tree)
##    for key in notsetlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane, tree,
##				copy.deepcopy(decval))
    if len(setlst) > 0:
        tree = createANDTree(map(lambda k:(k,True),setlst),
                             copy.deepcopy(sameval),tree)
    if len(notsetlst) > 0:
	tree = createORTree(map(lambda k:(k,True),notsetlst),tree,decval)
	
    plane =  makeIdentityPlane(entity)
    tree =   createBranchTree(plane,ProbabilityTree(IdentityMatrix(feature)),tree)

    return {'tree':tree}

def decInc2(entity, feature, incval, decval, setlst, notsetlst, notsetlst2):
    tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                           incval))
    decval = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                             decval))
    sameval = ProbabilityTree(IdentityMatrix(feature))
##    for key in setlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane,copy.deepcopy(sameval),
##				tree)
##    for key in notsetlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane, tree,
##				copy.deepcopy(decval))
    if len(setlst) > 0:
        tree = createANDTree(map(lambda k:(k,True),setlst),
                             copy.deepcopy(sameval),tree)
    if len(notsetlst) > 0:
	tree = createORTree(map(lambda k:(k,True),notsetlst),tree,
                            copy.deepcopy(decval))

    if len(notsetlst2) > 0:
	tree = createANDTree(map(lambda k:(k,True),notsetlst2),tree,
                             copy.deepcopy(decval))
	
    plane =  makeIdentityPlane(entity)
    tree =   createBranchTree(plane,ProbabilityTree(IdentityMatrix(feature)),tree)

    return {'tree':tree}


# if entity
# if any notsetlst conditions are false, decrement
# if all setlst are true, increment
# else do nothing

def notdecInc(entity, feature, incval, decval, setlst, notsetlst):
    tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  incval))
    decval = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  decval))
    sameval = ProbabilityTree(IdentityMatrix(feature))
##    for key in setlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane,copy.deepcopy(sameval),
##				tree)

    if len(setlst) > 0:
        tree = createANDTree(map(lambda k:(k,True),setlst),
                             copy.deepcopy(sameval),tree)
        
##    for key in notsetlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane, copy.deepcopy(decval),
##                                tree)


    if len(notsetlst) > 0:
	tree = createORTree(map(lambda k:(k,False),notsetlst),tree,decval)
				
    plane =  makeIdentityPlane(entity)
    tree =   createBranchTree(plane,ProbabilityTree(IdentityMatrix(feature)),tree)

##    print tree
    return {'tree':tree}


# if entity
# if all notsetlst conditions are false and
# if all setlst are true, increment
# else do nothing

def conditionalInc(entity, feature, incval, setlst, notsetlst):
    tree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  incval))
    sameval = ProbabilityTree(IdentityMatrix(feature))
##    for key in setlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane,copy.deepcopy(sameval),
##				tree)

    if len(setlst) > 0:
        tree = createANDTree(map(lambda k:(k,True),setlst),
                             copy.deepcopy(sameval),tree)
        
##    for key in notsetlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane, tree,
##				copy.deepcopy(sameval))

    if len(notsetlst) > 0:
	tree = createANDTree(map(lambda k:(k,False),notsetlst),sameval,tree)
				
				
    plane =  makeIdentityPlane(entity)
    tree =   createBranchTree(plane,ProbabilityTree(IdentityMatrix(feature)),tree)
    return {'tree':tree}


# if entity
# if all notsetlst conditions are false and
# if all setlst are true, increment
# else do nothing

def conditionalSet(entity, feature, value, setlst, notsetlst):
    tree = setTo(entity,feature,value)['tree']
    sameval = ProbabilityTree(IdentityMatrix(feature))
##    for key in setlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane,copy.deepcopy(sameval),
##				tree)

    if len(setlst) > 0:
        tree = createANDTree(map(lambda k:(k,True),setlst),
                             copy.deepcopy(sameval),tree)

##    for key in notsetlst:
##	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
##	tree = createBranchTree(plane, tree,
##				copy.deepcopy(sameval))
    
    if len(notsetlst) > 0:
	tree = createANDTree(map(lambda k:(k,False),notsetlst),
                             copy.deepcopy(sameval),tree)
	
    plane =  makeIdentityPlane(entity)
    tree = createBranchTree(plane,ProbabilityTree(IdentityMatrix(feature)),
                            tree)
    return {'tree':tree}



# if entity
# if any notsetlst conditions are true and
# if all setlst are true, increment
# else do nothing

def andOrInc(entity, feature, incval, nandval, norval, setlst, notsetlst):
    inctree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  incval))
    nandtree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  nandval))
    nortree = ProbabilityTree(IncrementMatrix(feature,keyConstant,
					  norval))
    sametree = ProbabilityTree(IdentityMatrix(feature))
    if len(notsetlst) > 0:
        tree = createORTree(map(lambda k:(k,True),notsetlst),
                             nortree,inctree)
    else:
        tree = sametree
    if len(setlst) > 0:
        tree = createANDTree(map(lambda k:(k,True),setlst),
                             nandtree,tree)
##     for key in notsetlst:
## 	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
## 	tree = createBranchTree(plane, tree,
## 				copy.deepcopy(inctree))
##     for key in setlst:
## 	plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
## 	tree = createBranchTree(plane,copy.deepcopy(sametree),
## 				tree)
    plane =  makeIdentityPlane(entity)
    tree =   createBranchTree(plane,copy.deepcopy(sametree),tree)
    return {'tree':tree}



def symmetricSet(feature,value,entities,setlst,notsetlst):
    """For a given entity, set the feature to a given value only if a set of conditions apply to all of the other relevant entities
    @param feature: the feature to set (on C{self})
    @type feature: str
    @param value: the value to set the feature to
    @type value: float
    @param entities: the list of entities among whom this symmetric dependency applies
    @type entities: str[]
    @param setlst: the features on those other entities which have to all be C{True} for the value to be set
    @type setlst: str[]
    @param notsetlst: the features on those other entities which have to all be C{False} for the value to be set
    @type notsetlst: str[]
    """
    newval = ProbabilityTree(SetToConstantMatrix(source=feature,value=value))
    sameval = ProbabilityTree(IdentityMatrix(feature))
    total = copy.deepcopy(sameval)
    for entity in entities:
        tree = copy.deepcopy(newval)
        for other in entities:
            if entity != other:
                for feature in setlst:
                    key = StateKey({'entity':other,'feature':feature})
                    plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
                    tree = createBranchTree(plane,copy.deepcopy(sameval),tree)
                for feature in notsetlst:
                    key = StateKey({'entity':other,'feature':feature})
                    plane = KeyedPlane(ThresholdRow(keys=[key]),0.5)
                    tree = createBranchTree(plane, tree,copy.deepcopy(sameval))
        plane =  makeIdentityPlane(entity)
        total = createBranchTree(plane,total,tree)
    return {'tree':total}				
	
def economics(feature,target,badFeature=None):
    unchangedTree = ProbabilityTree(IdentityMatrix(feature))
    row = KeyedVector({StateKey({'entity':'object','feature':target}):0.1})
    if badFeature:
        row[StateKey({'entity':'object','feature':badFeature})] = -1.
    loChangeTree = ProbabilityTree(KeyedMatrix({StateKey({'entity':'self',
                                                    'feature':feature}):row}))
    row = KeyedVector({StateKey({'entity':'object','feature':target}):0.4})
    if badFeature:
        row[StateKey({'entity':'object','feature':badFeature})] = -1.
    hiChangeTree = ProbabilityTree(KeyedMatrix({StateKey({'entity':'self',
                                                    'feature':feature}):row}))
    plane = KeyedPlane(ThresholdRow(keys=[{'entity':'object',
                                           'feature':target}]),0.2)
    subtree = createBranchTree(plane,loChangeTree,hiChangeTree)
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree = createBranchTree(plane,unchangedTree,subtree)
    return {'tree':tree}
    
def market(featureList):
    unchangedTree = ProbabilityTree(IdentityMatrix(feature))
    row = KeyedVector()
    for feature in featureList:
        row[StateKey({'entity':'object','feature':feature})] = .1
    changeTree = ProbabilityTree(KeyedMatrix({StateKey({'entity':'self',
                                                  'feature':'money'}):row}))
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    tree = createBranchTree(plane,unchangedTree,changeTree)
    return {'tree':tree}

def transfer(feature,amount=0.01):
    trees = {}
    trees['actor'] = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                               -amount))
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'actor',
                                          'relationship':'equals'}]),0.5)
    trees['actor?'] = createBranchTree(plane,
                                       identityTree(feature),
                                       trees['actor'])
    trees['object'] = ProbabilityTree(IncrementMatrix(feature,keyConstant,
                                                amount))
    plane = KeyedPlane(IdentityRow(keys=[{'entity':'object',
                                          'relationship':'equals'}]),0.5)
    trees['sufficient'] = createBranchTree(plane,trees['actor?'],
                                           trees['object'])
    plane = KeyedPlane(ThresholdRow(keys=[{'entity':'actor',
                                           'feature':feature}]),amount)
    trees['sufficient?'] = createBranchTree(plane,
                                            identityTree(feature),
                                            trees['sufficient'])
    plane = KeyedPlane(ThresholdRow(keys=[{'entity':'object',
                                           'feature':feature}]),1.-amount)
    trees['maxedout?'] = createBranchTree(plane,trees['sufficient?'],
                                          identityTree(feature))
    plane = KeyedPlane(ThresholdRow(keys=[{'entity':'self',
                                           'feature':'terminated'}]),0.5)
    trees['terminated'] = createBranchTree(plane, identityTree(feature), 
					  trees['maxedout?'])
    return {'tree':trees['terminated']}

##def transfer(feature,amount=.01,floor=0.):
##    trees = {}
##    # If not actor or object, then do nothing
##    trees['unchanged'] = createNodeTree(KeyedMatrix())
##    # If actor doesn't have enough to give, then give as much as it can
##    weights = {makeStateKey('actor',feature):1.}
##    trees['insufficient object'] = createDynamicNode(feature,weights)
##    weights = {makeStateKey('actor',feature):-1.}
##    trees['insufficient actor'] = createDynamicNode(feature,weights)
##    # If object has too much, then give as much as it can take
##    weights = {makeStateKey('object',feature):-1.,
##               keyConstant:1.}
##    trees['maxed-out object'] = createDynamicNode(feature,weights)
##    weights = {makeStateKey('object',feature):1.,
##               keyConstant:-1.}
##    trees['maxed-out actor'] = createDynamicNode(feature,weights)
##    # Otherwise, give the specified amount
##    weights = {keyConstant:amount}
##    trees['normal object'] = createDynamicNode(feature,weights)
##    weights = {keyConstant:-amount}
##    trees['normal actor'] = createDynamicNode(feature,weights)

##    # Create object side of the tree
    
##    # Need to handle more cases, but for now:
##    trees['object'] = trees['normal object']
##    # Branch on being object
##    trees['object?'] = createBranchTree(makeIdentityPlane('object'),
##                                        trees['unchanged'],trees['object'])

##    # Create actor side of the tree

##    # Branch on being maxed out [actor version]
##    weights = {makeStateKey('object',feature):1.}
##    tree = createBranchTree(KeyedPlane(KeyedVector(weights),1.-amount),
##                            trees['normal actor'],trees['maxed-out actor'])
##    trees['sufficient maxed-out? actor'] = tree

##    # Branch on whether more maxed out or more insufficient [actor version]
##    weights = {makeStateKey('actor',feature):.5,
##               makeStateKey('object',feature):.5}
##    tree = createBranchTree(KeyedPlane(KeyedVector(weights),(1.+floor)/2.),
##                            trees['insufficient actor'],
##                            trees['maxed-out actor'])
##    trees['insufficient maxed-out actor'] = tree

##    # Branch on being maxed out when also insufficient [actor version]
##    weights = {makeStateKey('object',feature):1.}
##    tree = createBranchTree(KeyedPlane(KeyedVector(weights),1.-amount),
##                            trees['insufficient actor'],
##                            trees['insufficient maxed-out actor'])
##    trees['insufficient maxed-out? actor'] = tree

##    # Branch on being too poor to give full amount [actor version]
##    weights = {makeStateKey('actor',feature):1.}
##    tree = createBranchTree(KeyedPlane(KeyedVector(weights),floor+amount),
##                            trees['insufficient maxed-out? actor'],
##                            trees['sufficient maxed-out? actor'])
##    trees['sufficient? actor'] = tree
##    # Branch on being too poor to do anything [actor version]
##    tree = createBranchTree(KeyedPlane(KeyedVector(weights),floor),
##                            trees['unchanged'],trees['sufficient? actor'])
##    trees['actor'] = tree

##    # Branch on being actor
##    trees['actor?'] = createBranchTree(makeIdentityPlane('actor'),
##                                       trees['object?'],trees['actor'])
    
##    return {'tree': tree}


notsetlst = [StateKey({'entity':'object','feature':'f1'}),
             StateKey({'entity':'object','feature':'f2'}),
             StateKey({'entity':'object','feature':'f3'})]

decval = ProbabilityTree(IncrementMatrix('dummy',keyConstant,
					  .1))
tree = createORTree(map(lambda k:(k,False),notsetlst),ProbabilityTree(IdentityMatrix('dummy')),decval)


