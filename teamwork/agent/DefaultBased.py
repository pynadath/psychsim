"""Class for applying the defaults in a L{GenericModel<Generic.GenericModel>} instance to an instantiated L{Stereotyper<stereotypes.Stereotyper>}
@author: David V. Pynadath <pynadath@ict.usc.edu>
"""
import copy
from teamwork.math.Keys import StateKey,ModelKey
from teamwork.math.probability import Distribution
from teamwork.action.DecisionSpace import DecisionSpace
from teamwork.agent.stereotypes import Stereotyper
from teamwork.policy.pwlPolicy import PWLPolicy
from teamwork.agent.Generic import GenericModel
from teamwork.action.DecisionSpace import DecisionSpace

classHierarchy = None

class GenericEntity(Stereotyper):
    """Generic entity class with general-purpose methods for
    instantiating an entity, using class-specific defaults"""

    copyCount = 0.0
    # Message factors
    factors = []

    def __init__(self,name):
        Stereotyper.__init__(self,name)
        self.classes = []
        self.relationships = {}
        self.setHierarchy(None)

    def setHierarchy(self,classes):
        """Sets the hierarchy of L{GenericModel} instances that this agent uses for its default values
        @type classes: L{GenericSociety<teamwork.multiagent.GenericSociety.GenericSociety>}
        """
        self.hierarchy = classes
        
    def applyDefaults(self,className=None,hierarchy=classHierarchy):
        """Applies the generic model in the society of the given class name"""
        self.type = className
        self.setHierarchy(hierarchy)
        # Initialize class branch
        self.classes = []
        toExpand = [self.type]
        while len(toExpand) > 0:
            for className in toExpand[:]:
                toExpand.remove(className)
                self.classes.append(className)
                try:
                    toExpand += self.hierarchy[className].getParents()
                except KeyError:
                    pass
        self.valueType = self.getDefault('valueType')
        # Initialize model space
        self.model = None
        self.models = {}
        # Initialize actions
        self.initActions(self.getDefault('actions'))
        # Initialize state
        self.initState()
##        # Initialize goals
##        self.initGoals()
        # Initialize observation function
        self.initObservations()
        try:
            # Initialize image
            self.attributes['imageName'] = self.getDefault('imageName')
        except KeyError:
            # No image, no big deal
            pass
        
    def getDefault(self,feature):
        """Finds the most specific class defaults for the specified
        feature; raises KeyError exception if no default exists"""
        if self.hierarchy is None:
            # Duh, no defaults
            raise KeyError,'%s has no feature %s' % (self.name,feature)
        result = None
        last = None
        for cls in self.classes:
            # Check object attributes
            try:
                result = self.hierarchy[cls].__dict__[feature]
            except KeyError:
                # Check special attributes
                try:
                    result = self.hierarchy[cls].attributes[feature]
                except KeyError:
                    # Nothing here
                    continue
            if feature in ['models','dynamics']:
                # Empty values don't count
                if len(result) > 0:
                    break
            elif feature == 'imageName':
                if result is not None:
                    break
            elif feature == 'actions':
                if result.branchType:
                    # Can't really merge AND/OR decision spaces
                    break
                elif last is None:
                    last = result
                else:
                    # Merge in any extras
                    last = copy.deepcopy(last)
                    for option in result.extras:
                        last.directAdd(option)
                    result = last
            elif feature == 'depth':
                # Belief depth is MINIMUM across all default values
                if last is None:
                    last = result
                else:
                    last = min(last,result)
                    result = last
            else:
                # For everything else, the first thing
                break
        if result is None:
            if feature == 'actions':
                pass
            else:
                raise KeyError,'%s has no feature %s' % (self.name,feature)
        return result

    def initState(self):
        """Instantiates all of the state defaults relevant to this entity"""
        for cls in self.classes:
            try:
                featureList = self.hierarchy[cls].getStateFeatures()
            except KeyError:
                featureList = []
            for feature in featureList:
                if not feature in self.getStateFeatures():
                    value = self.hierarchy[cls].getState(feature)
                    self.setState(feature,value)
        self.setModel(None)
            
    def initActions(self,decisions):
        """Initializes the actions to follow the form of the given L{DecisionSpace<teamwork.action.DecisionSpace.DecisionSpace>}"""
        self.actions = decisions.__class__()
        self.actions.illegal.update(decisions.illegal)
        self._initActions(self.actions,decisions)
        # Add actions that have no objects
        for option in decisions.extras:
            if not self.actions.isIllegal(option):
                for action in option:
                    if action['object'] is not None:
                        break
                else:
                    self.actions.directAdd(copy.deepcopy(option))
        
    def _initActions(self,mySpace,decisions):
        while isinstance(decisions,DecisionSpace):
            mySpace.key = decisions.key
            for value in decisions.values:
                if value['type'] == 'literal':
                    mySpace.append(value['value'])
                elif value['type'] == 'decision':
                    newDecisions = value['value'].__class__()
                    self._initActions(newDecisions,value['value'])
                    mySpace.append(newDecisions)
            if isinstance(decisions.base,DecisionSpace):
                mySpace.base = decisions.base.__class__()
                mySpace = mySpace.base
            else:
                mySpace.base = copy.deepcopy(decisions.base)
            decisions = decisions.base
            
    def initRelationships(self,entityList):
        """Instantiates the relationships of this entity regarding the
        provided list of entities"""
        # Fill out any relationships that this entity may have:
        try:
            relations = self.getDefault('relationships')
        except KeyError:
            relations = {}
        for relation in relations.keys():
            if not self.relationships.has_key(relation):
                # Assume starting with no such relationship
                self.relationships[relation] = []
                # Use defaults if relationships have not already been
                # set (i.e., haven't used wizard)
##                for entity in entityList:
##                    # match the desired class against each and every class
##                    # that this entity is a member of (string compare)
##                    for target in targetList:
##                        if entity.name != self.name and \
##                               target in entity.classes:
##                            self.relationships[relation].append(entity.name)
##            if len(self.relationships[relation]) == 0:
##                del self.relationships[relation]

    def initModels(self,entityList):
        """Instantiate all of the relevant models"""
        # Prune any agents who don't have actions
        agents = []
        for agent in entityList:
            if len(agent.actions.getOptions()) > 0:
                agents.append(agent)
        self.horizon = self.getDefault('horizon')*len(agents)
        for model in self.models.values():
            # If we've already instantiated the goals and policy,
            # then the only thing left to do is set the lookahead
            # depth 
            model.policy.depth = self.horizon
            model.policy.entity = self
                        
    def initEntities(self,entityList,maxDepth=-1):
        """Sets the entities known to be the list provided, and makes
        the appropriate updates to goals, policy depth, etc.
        @param maxDepth: the maximum depth of this agent's recursive models
        @type maxDepth: int
        """
        # Fill out recursive beliefs
        if maxDepth < 0:
            maxDepth = self.getDefault('depth')
        else:
            maxDepth = min(self.getDefault('depth'),maxDepth)
        newList = []
        if maxDepth > 0:
            # First, generate entity objects for my beliefs
            for entity in entityList:
                newEntity = copy.copy(entity)
                newEntity.dynamics = copy.deepcopy(entity.dynamics)
                # Stick this entity object into my beliefs
                self.setEntity(newEntity)
                newList.append(newEntity)
                # Assume correct beliefs about states
                for feature in entity.getStateFeatures():
                    try:
                        value = entity.getState(feature)
                        newEntity.setState(feature,value)
                    except KeyError:
                        pass
            # Finally, fill in specific beliefs according to my class
            # defaults, and go to the next recursive level
            for entity in newList:
                self.initBeliefs(entity)
                entity.initEntities(newList,maxDepth-1)
        # Add any goals related to the new entities
        self.initGoals(entityList)
        for entity in self.getEntityBeliefs():
            self.initMental(entity)
        # Set the depth of lookahead
        agents = []
        for agent in entityList:
            if len(agent.actions.getOptions()) > 0:
                agents.append(agent)
        self.horizon = self.getDefault('horizon')*len(agents)
        if not self.policy:
            self.policy = PWLPolicy(self,self.actions,self.horizon)
        self.entities.initializeOrder()
        self.entities.state.freeze()

    def initBeliefs(self,entity):
        """Sets the beliefs that this entity has about the given entity,
        following the various defaults"""
        # Find the relationships I have with this entity
        relations = []
        for relation in self.relationships.keys():
            if entity.name in self.relationships[relation]:
                relations.append(relation)
        # Consider each class that this entity belongs to
        myClassList = self.classes[:]
#        myClassList.reverse()
        yourClassList = entity.classes[:]
#        yourClassList.reverse()
        for default in myClassList:
            beliefs = {}
            # For others, use class-based defaults
            for cls in yourClassList:
                # Consider all of the default beliefs I have
                try:
                    beliefs = self.hierarchy[default].getEntity(cls)
                except KeyError:
                    # If no generic beliefs either, then go on to
                    # next class
                    continue
                # Copy default belief values from this class
                entity.applyBeliefs(beliefs)
            # Relations take precedence over class defaults
            for relation in relations:
                try:
                    beliefs = self.hierarchy[default].getEntity(relation)
                except KeyError:
                    continue
                # Copy default belief values from this class
                entity.applyBeliefs(beliefs)
            if entity.name == self.name:
                try:
                    beliefs = self.hierarchy[default].getEntity('self')
                    # Copy default belief values from this class
                    entity.applyBeliefs(beliefs)
                except KeyError:
                    pass
                
    def initMental(self,entity):
        """Initialize beliefs over mental models
        """
        newBelief = {}
        models = self.getDefault('beliefs')['models']
        cls = entity.classes[0]
        belief = self.getDefault('entities')[cls]
        key = ModelKey({'entity':cls})
        try:
            dist = models.getMarginal(key)
        except KeyError:
            dist = Distribution()
        for value in dist.domain():
            name = belief.float2model(value)
            model = belief.models[name]
            prob = dist[value]
            if name == 'True':
                # Not 100% accurate
                if abs(prob-1.)>1e-8:
                    model = entity.newModel(name)
                    model['goals'] = entity.initGoals(entity.getEntityBeliefs(),entity)
                    newBelief[name] = prob
            elif name == 'Like me':
                # Nonzero belief in being just like me
                if prob>1e-8:
                    model = entity.newModel(name)
                    model['goals'] = entity.initGoals(entity.getEntityBeliefs(),self)
                    newBelief[name] = prob
            elif prob > 1e-8:
                # Arbitrary model
                goalList = map(lambda g: (g,model['goals'][g]),model['goals'].domain())
                model = entity.newModel(name)
                model['goals'] = entity.initGoals(self.getEntityBeliefs(),None,goalList,debug=False)
                newBelief[name] = prob
                print model
        if newBelief:
            self.setModelBeliefs(entity.name,Distribution(newBelief))
        if entity.model:
            self.setModel(entity.model['name'])
        return entity

    def applyBeliefs(self,beliefs):
        for feature in beliefs.getStateFeatures():
            self.setState(feature,beliefs.getState(feature))
        
    def initDynamics(self,entities={}):
        """Sets world dynamics of this entity in response to all of the possible actions in the given multiagent system
        @param entities: the agents whose actions are relevant
        @type entities: strS{->}Agent
        """
        for cls in self.classes:
            for feature,actDict in self.hierarchy[cls].dynamics.items():
                if not self.dynamics.has_key(feature):
                    self.dynamics[feature] = {}
                for actType,dynamics in actDict.items():
                    if not self.dynamics[feature].has_key(actType):
                        # No prior dynamics for this specific type of action
                        found = False
                        for agent in entities.values():
                            for option in agent.actions.getOptions():
                                if dynamics['condition'].match(option):
                                    # This condition could potentially match
                                    self.dynamics[feature][actType] = cls
                                    found = True
                                    break
                                else:
                                    # Use old-school matching, although should become deprecated
                                    for action in option:
                                        if action['type'] == actType:
                                            self.dynamics[feature][actType] = cls
                                            found = True
                                            break
                                if found:
                                    break
                            if found:
                                break

    def initGoals(self,entities=[],default=None,goalList=None,debug=False):
        """Sets the goal weights of this entity based on class
        defaults.  The resulting goals depend on the group of entities
        passed in as the optional argument.
        @param default: the instance whose generic classes should be used (default is C{self})
        @param goalList: list of tuples of goals and weights (default is taken from class inheritance)
        @return: the resulting goal vector
        """
        if default is None:
            classList = self.classes
        else:
            classList = default.classes
        if goalList is None:
            goalList = []
            for generic in map(lambda c: self.hierarchy[c],classList):
                for goal in generic.getGoals():
                    goalList.append((goal,generic.getGoalWeight(goal)))
        goals = Distribution()
        for goal,weight in goalList:
            key = goal.toKey()
            selfs = []
            if debug: print key
            if debug: print self.relationships[key['entity']]
            if debug: print entities
            if isinstance(key,StateKey):
                if key['entity'] == 'self':
                    selfs.append(self)
                elif self.relationships.has_key(key['entity']):
                    # Find instances who I have the specified relationship with
                    for entity in entities:
                        if entity.name in self.relationships[key['entity']]:
                            selfs.append(entity)
                else:
                    # Find all applicable instances
                    for entity in entities:
                        if entity.instanceof(key['entity']):
                            selfs.append(entity)
            else:
                raise NotImplementedError,'Tell David to implement instantiation of %s goals' % (key.__class__.__name__)
            for goalSelf in selfs:
                args = {}
                for entity in entities:
                    for cls in entity.classes:
                        try:
                            args[cls].append(entity.name)
                        except KeyError:
                            args[cls] = [entity.name]
                if self.relationships.has_key(key['entity']):
                    args['self'] = self
                    args.update(self.relationships)
                    args[key['entity']] = goalSelf
                else:
                    args['self'] = goalSelf
                    args.update(goalSelf.relationships)
                    if key['entity'] != 'self':
                        args[key['entity']] = goalSelf
                for subGoal in goal.instantiate(args):
                    try:
                        goals[subGoal] += weight
                    except KeyError:
                        goals[subGoal] = weight
        if debug: print self.ancestry(),map(str,goals.domain())
        if not default is None:
            # Normalize goals to return
            goals.normalize()
        elif len(goals) > 0:
            # Don't try to set empty goals
            self.setGoals(goals)
        return goals

    def initObservations(self,entries=[]):
        """Instantiates generic observation function with given entity list"""
        for cls in self.classes:
            if not self.hierarchy[cls].observable():
                # Perfect observability is recessive
                self.omega.update(self.hierarchy[cls].omega)
                for default in self.hierarchy[cls].observations:
                    # Look to see whether there's an existing function to override
                    for entry in self.observations:
                        if entry['actions'] == default['actions']:
                            # Override previous default
                            entry['tree'] = copy.deepcopy(default['tree'])
                            break
                    else:
                        # Nope, just copy it over
                        self.observations.append(copy.deepcopy(default))

    def instantiateGoal(self,goal,entities=[]):
        """Specializes the given goal to the given scenario context.
        @return: a list of goals created by instantiating the given
        goal template (i.e., it refers to classes or relationships)
        with respect to the provided list of entities and current
        relationships
        @rtype: L{PWLGoal}[]
        """
        raise DeprecationWarning,'Use instantiate method on goals themselves'

    def instantiateList(self,nameList,refList,entities=[]):
        """
        @param nameList: list of names to be instantiated
        @type nameList: C{str[]}
        @param refList: partial results of name lists instantiation so far
        @type refList: C{str[][]}
        @param entities: the entities from which to draw instances from
        @type entities: C{L{Agent}[]}
        @return: a list of entity lists appropriate for recursive beliefs with all name references replaced by the appropriate entities"""
        try:
            name = nameList[0]
        except IndexError:
            return refList
        newNames = self.instantiateName(name,entities)
        newList = []
        for ref in refList:
            for name in newNames:
                newList.append(ref[:]+[name])
        return self.instantiateList(nameList[1:],newList,entities)
        
    def instantiateName(self,name,entities=[]):
        """Returns a list of instance names that match the given abstract entity reference (either 'self', relationship, or class name).
        @param name: the reference(s) to be instantiated
        @type name: C{str} or C{str[]}
        @param entities: the entities to search for the given reference.  If no entities are provided, defaults to the list of entities that this entity has beliefs about
        @type entities: L{Agent}[]
        @rtype: C{str[]}
        """
        if len(entities) == 0:
            entities = self.entities.values()
        if isinstance(name,list):
            return map(lambda n,s=self,e=entities:s.instantiateName(n,e))
        if name == 'self':
            return [self.name]
        elif self.relationships.has_key(name):
            matches = []
            for entity in entities:
                if entity.name in self.relationships[name]:
                    matches.append(entity.name)
            return matches
        else:
            matches = []
            for entity in entities:
                if entity.instanceof(name):
                    matches.append(entity.name)
            return matches
            
    def addActions(self,entities):
        """Adds any actions that I can perform with respect to the given entities
        @type entities: L{Agent}[]
        """
        default = self.getDefault('actions')
        self._addActions(entities,default,self.actions)
        for option in default.extras:
            if self.actions.isIllegal(option):
                continue
            newOptions = [[]]
            for action in option:
                if not action['object'] is None:
                    names = self.instantiateName(action['object'],entities)
                    if self.name in names:
                        try:
                            selfEligible = action['self']
                        except KeyError:
                            # By default, assume self is ineligible
                            selfEligible = False
                        if not selfEligible:
                            names.remove(self.name)
                    for new in newOptions[:]:
                        newOptions.remove(new)
                        for name in names:
                            newAction = copy.deepcopy(action)
                            newAction['object'] = name
                            newOption = copy.deepcopy(new)
                            newOption.append(newAction)
                            newOptions.append(newOption)
                else:
                    # No object, always applicable
                    for new in newOptions:
                        new.append(copy.deepcopy(action))
                if len(newOptions) == 0:
                    break
            else:
                for newOption in newOptions:
                    self.actions.directAdd(newOption)
            
    def _addActions(self,entities,baseActions,realActions):
        while isinstance(baseActions,DecisionSpace):
            for value in baseActions.values:
                if value['type'] == 'generic':
                    for entity in entities:
                        if value['value'] in entity.classes:
                            if entity.name != realActions:
                                realActions.append(entity.name)
                elif value['type'] == 'relationship':
                    for entity in entities:
                        if value['value'] in self.relationships.keys() and \
                               entity.name in \
                               self.relationships[value['value']]:
                            if entity.name != realActions:
                                realActions.append(entity.name)
                elif value['type'] == 'decision':
                    space = value['value'].__class__()
                    self._initActions(space,value['value'])
                    self._addActions(entities,value['value'],space)
                    realActions.append(space)
            baseActions = baseActions.base
            realActions = realActions.base
            
    def instanceof(self,className):
        """
        @return: True iff this entity is a member of the specified class
        @param className: name of class to test against
        @type className: C{str}
        @rtype: C{boolean}
        """
        return className in self.classes

    def __copy__(self):
        new = Stereotyper.__copy__(self)
        new.setHierarchy(self.hierarchy)
        new.initial = self.initial
        if self.policy:
            new.policy = copy.copy(self.policy)
            new.policy.entity = new
        new.actions = self.actions
        new.messages = self.messages
        new.relationships = self.relationships
        new.classes = self.classes
        return new

    def __xml__(self):
        doc = Stereotyper.__xml__(self)
        for cls in self.classes:
            node = doc.createElement('class')
            node.setAttribute('name',cls)
            doc.documentElement.appendChild(node)
        return doc
    
    def parse(self,element):
        """Extracts this agent's recursive belief structure from the given XML Element
        @type element: Element
        """
        Stereotyper.parse(self,element)
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE and \
               child.tagName == 'class':
                self.classes.append(str(child.getAttribute('name')))
            child = child.nextSibling

def packageHierarchy(linkList,result):
    """Packages up the tree branch containing L{GenericEntity} into a neat
    little dictionary, indexed by class name, with the values being
    lists of classes that represent the branch up to the root (we
    don't include L{GenericEntity}, which is the root)"""
    for entry in linkList:
        if isinstance(entry,tuple):
            child = entry[0].__name__
            parent = entry[1][0].__name__
            if not result.has_key(child):
                result[child] = []
            if parent != 'GenericEntity':
                if not result.has_key(parent):
                    result[parent] = []
                result[child].append(parent)
                result[child] = result[child] + result[parent]
        else:
            packageHierarchy(entry,result)
    return result

def copyModels(models):
    newModels = {}
    for key in models.keys():
        newModels[key] = copyModel(models[key])
    return newModels

def copyModel(model):
    newModel = GenericModel(model.name)
    newModel.setGoals(model.getGoals())
    newModel.policy = copy.deepcopy(model.policy)
##    for key in model.keys():
##        newModel[key] = copy.copy(model[key])
    return newModel
