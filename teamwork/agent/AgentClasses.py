from teamwork.math.probability import Distribution

classHierarchy = {}

classHierarchy['Entity'] = {
    # Default goal weights
    'goals': Distribution(),
    # Default horizon on lookahead
    'horizon': 1,
    # Default depth on belief recursion
    'depth': 2,
    # Default set of possible models
    'models': {},
    # Current model used as basis for this entity
    'model': None,
    # Default relationships
    'relationships': {},
    # Default initially public persona
    'persona': {},
    # Default set of actions
    'actions': {'type':None},
    # For UI purposes...
    'full-name': "Generic Entity",
    'subtype-name': None,
    # this class should be considered abstract
    'abstract': 1,
    # default count for scenerio creation
    'defaultCount': 0
    }

def getClassAttrib( classId, attribId ):
    classObj = classHierarchy[ classId ]
    if( classObj.has_key( attribId ) ):
        return classObj[ attribId ]
#    if( classId == None ):
#        throw new KeyError   #or however Python does it
    else:
        for parent in classObj['parent']:
            try:
                return getClassAttrib(parent, attribId )
            except KeyError:
                pass
        else:
            raise KeyError,'%s has no feature %s' % (classId,attribId)


def isSubclassOf( class1, class2 ):
    #print "isSubclassOf( ", class1, ", ", class2, " )"
    assert classHierarchy.has_key( class1 )
    assert classHierarchy.has_key( class2 )

    # dp: Modified to handle new multiple-inheritance taxonomy
    classList = [class1]
    while len(classList) > 0:
        curClass = classList.pop()
        if class2 == curClass:
            return 1
        else:
            try:
                classList += classHierarchy[curClass]['parent']
            except KeyError:
                pass
    return None
##    if( class1 == class2 ):
##        return 1
##    curClass = class1
##    while( curClass != None ):
##        curClass = classHierarchy[curClass]['parent']
##        if( curClass == class2 ):
##            return 1
##    return None

def createEntityClass( className, parentClass ):
    try:
        assert classHierarchy.has_key( parentClass )
        if not classHierarchy.has_key( className ):

            newClass = { 'parent': parentClass }
            classHierarchy[ className ] = newClass
    except AssertionError:
        return
        
    return classHierarchy[ className ]
    


#  Return an alphabetical list of Entity class name
def getEntityClassList( classHierarchy ):
    # The class names
    names = classHierarchy.keys()
    names.remove(None)
    names.sort()

    return names

#  Returns a new dict: class Id -> dict sub-class Id, etc...
def buildHierarchicalEntityDict( classHierarchy ):
    names = getEntityClassList( classHierarchy )
    
    #remove None (the hierarchy root)
    names.pop(0)
    # init dicts
    root = {}
    dicts = { None: root }

    for name in names:
        if( dicts.has_key( name ) ):
            dict = dicts[name]
        else:
            dict = {}
            dicts[name] = dict

        # dp: rewritten to handle multiple parents...not sure if it's
        # doing the intended thing anymore
        classList = classHierarchy[name]['parent']
        if len(classList) == 0:
            classList = [None]
        for parent in classList:
            if( dicts.has_key( parent ) ):
                pDict = dicts[parent]
            else:
                pDict = {}
                dicts[parent] = pDict

            pDict[name] = dict
    return dicts  #  The generic entity and it's sub-classes
    
#  Returns a new dict: class Id -> dict sub-class Id, etc...
##def buildUserHierarchicalEntityDict( classHierarchy ):
##    names = getEntityClassList()
    
##    #remove None (the hierarchy root)
##    names.pop(0)
##    # init dicts
##    root = {}
##    dicts = { None: root }

##    for name in names:
##        dict = {}
##        if( dicts.has_key( name ) ):
##            dict = dicts[name]
##        else:
##            dicts[name] = dict
            
##        parent = classHierarchy[name]['parent']
##        pDict = {}
##        if( dicts.has_key( parent ) ):
##            pDict = dicts[parent]
##        else:
##            dicts[parent] = pDict

##        pDict[name] = dict

##    return { None: root }  #  The generic entity and it's sub-classes


    
#def printEntityHierarchy( classhierarchy=defaultClassHierarchy ):
def printEntityHierarchy():
    printEntityHierarchyImpl( buildHierarchicalEntityDict(classHierarchy), '' )
    
def printEntityHierarchyImpl( dict, indent ):
    children = dict.keys()
    children.sort()
    for childId in children:
        child = classHierarchy[childId]
        try:
            name = child['full-name']
            if( child.has_key( 'subtype-name' ) and
                child['subtype-name'] != None ):
                name = child['subtype-name']
            print( indent+name+" ("+repr(childId)+")" )
            printEntityHierarchyImpl( dict[childId], '  '+indent )
        except KeyError:
            pass





if __name__=='__main__':
#    print( repr( getEntityHierarchy() ) )
    printEntityHierarchy()
