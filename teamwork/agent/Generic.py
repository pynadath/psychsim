"""Class for defining the default parameters of an individual agent"""
import copy

from teamwork.math.Keys import StateKey,ObservationKey
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.probability import Distribution
from teamwork.action.DecisionSpace import extractSpace,ActionCondition
from teamwork.agent.support import Supporter
from teamwork.agent.stereotypes import Stereotyper
from teamwork.math.matrices import DecisionTree

class GenericModel(Supporter,Stereotyper):
    """
    A container of default values for an L{Agent}

          0. Creating a new generic model:
          C{model = L{GenericModel}(name)}
          
          1. Society-specific methods
             - C{model.L{getParents}()}
          
          2. Picking a specific stereotypical mental model
             - C{model.L{setModel}(name)}
          
          3. Manipulating the space of stereotypical mental models:
             - C{model[models]} --- a dictionary of the form C{modelName: modelObj, ...}, where modelObj is a L{GenericModel}.  Currently we read/write only the goals and policy attributes of modelObj.
          
          4. Manipulating the goals
             - C{model.L{getGoals}()}
             - C{model.L{setGoals}(goalList)}
             - C{model.L{getGoalWeight}(goal)}
             - C{model.L{setGoalWeight}(goal,num)}
          
          5. Manipulating the recursive belief structure
             - C{model.L{ancestry}()}
             - C{model.L{getBelief}(entityName,feature)}
             - C{model.L{setBelief}(entityName,feature,num)}
             - C{model.L{getEntities}()}
             - C{model.L{getEntity}(entityName)}
             - C{model.L{setEntity}(entityName,entityObj)}
             - C{model.L{getEntityBeliefs}()}
          
          6. Manipulating the state
             - C{model.L{getState}(feature)}
             - C{model.L{setState}(feature,num)}
          
          7. Manipulating the actions
             - C{model.actions}: a L{DecisionSpace} object
          
          8. Manipulating the dynamics
             - C{model.dynamics}: a L{PWLDynamics} instance
    @ivar depth: maximum depth of nesting of recursive beliefs
    @type depth: int
    """
    
    def __init__(self,name=''):
        """
        @param name: the unique ID for this model
        @type name: string
        """
        Stereotyper.__init__(self,name)
        Supporter.__init__(self,name)
        # Depth of nesting of recursive beliefs
        self.depth = 2
        self.parentModels = []
        self.setHierarchy({})

    def setHierarchy(self,classes):
        """Sets the hierarchy of L{GenericModel} instances that this agent uses for its default values
        @type classes: L{GenericSociety<teamwork.multiagent.GenericSociety.GenericSociety>}
        """
        self.hierarchy = classes
        for agent in self.getEntityBeliefs():
            agent.setHierarchy(classes)

    def initialStateEstimator(self):
        """Initializes beliefs"""
        return Stereotyper.initialStateEstimator(self)
        
    def initializeModel(self,agent):
        """Creates a belief that this agent has of the given one, including a mental model that is accurate
        @type agent: L{GenericModel}
        """
        new = agent.__class__(agent.name)
        new.setHierarchy(self.hierarchy)
        modelT = new.newModel('True')
        self.setEntity(new)
        modelF = new.newModel('Like me')
        try:
            self.getModel(new.name)
        except KeyError:
            # No existing mental model so create accurate one
            self.setModelBeliefs(new.name, Distribution({modelT['name']: 1.,modelF['name']: 0.}))
            
    def merge(self,entity):
        """Merge the contents of another L{GenericModel} into this one
        """
        warnings = []
        # Parents
        for parent in entity.getParents():
            if not self.isSubclass(parent):
                self.parentModels.append(parent)
        # State
        for feature in entity.getStateFeatures():
            if feature in self.getStateFeatures():
                warnings.append('%s of %s' % (feature,self.name))
            else:
                self.setState(feature,entity.getState(feature))
        # Actions
        for action in entity.actions.extras:
            if not action in self.actions.extras:
                self.actions.directAdd(action)
        # Coordinates
        if len(self.getParents()) == 0:
            try:
                # This test takes care of Entity, but it might be unnecessary
                self.attributes['coords'] = copy.copy(entity.attributes['coords'])
            except KeyError:
                pass
        return warnings
    
    def renameEntity(self,old,new):
        """
        @param old: the current name of the member
        @param new: the new name of the member
        @type old,new: str
        """
        # Update name and state
        if self.name == old:
            self.setName(new)
        # Update parents
        try:
            index = self.parentModels.index(old)
            self.parentModels[index] = new
        except ValueError:
            # We don't have this agent as a parent
            pass
        # Update goals
        for goal in self.getGoals():
            prob = self.goals[goal]
            del self.goals[goal]
            goal.renameEntity(old,new)
            self.goals[goal] = prob
        # Update actions
        for option in self.actions.getOptions():
            for action in option:
                if action['object'] == old:
                    action['object'] = new
                if self.name == new:
                    action['actor'] = new
        # Update static relationships
        for fillers in self.relationships.values():
            for name in fillers[:]:
                if name == old:
                    fillers.remove(old)
                    fillers.append(new)
        # Update dynamic relationships
        for key,value in self.links.items():
            remove = False
            if key['subject'] == old:
                remove = True
            if key['object'] == old:
                remove = True
                obj = new
            else:
                obj = key['object']
            if remove:
                del self.links[key]
                self.setLink(key['verb'],obj,value)
        # Update recursive beliefs
        if self.hasBelief(old):
            self.entities.renameMember(old,new)
        # Update class branches in dynamics
        for dynamics in sum(map(lambda d:d.values(),
                                self.dynamics.values()),[]):
            dynamics['tree'].renameEntity(old,new)
            
    def getParents(self):
        """Move up through the generic model hierarchy
        @return: the immediate parent models of this generic model
        @rtype: C{str[]}"""
        return self.parentModels

    def isSubclass(self,cls):
        """
        @return: C{True} iff this class is a subclass (inclusive) of the named class
        @rtype: boolean
        @param cls: The class name to test on
        @type cls: str
        """
        if self.name == cls:
            return True
        else:
            for parent in self.getParents():
                if self.hierarchy[parent].isSubclass(cls):
                    return True
        return False

    def getAllFillers(self,attribute):
        """
        @return: all fillers of a slot (e.g, 'state', 'action', 'goal') on this model I{and} all superclasses
        @rtype: str[]
        """
        values = []
        # Add inherited state features
        for name in self.ancestors():
            entity = self.hierarchy[name]
            if attribute == 'state':
                potential = entity.getStateFeatures()
            elif attribute == 'action':
                potential = entity.actions.getOptions()
            else:
                raise NotImplementedError,\
                      'Unable to get %s slots from superclasses' % (attribute)
            for value in potential:
                if not value in values:
                    values.append(value)
        return values

    def getInheritor(self,attribute,value,includeSelf=True):
        """
        @param attribute: the agent model slot to look for (e.g., 'state', 'action', 'goal')
        @type attribute,value: str
        @param value: the slot filler to look for (e.g., state feature)
        @return: the lowest class (either this one or some ancestory) that defines the given value in the given agent attributes
        @rtype: str
        @param includeSelf: if C{True}, then include self in search (default is C{True})
        @type includeSelf: bool
        """
        if includeSelf:
            classes = [self.name]
        else:
            classes = self.getParents()[:]
        while len(classes) > 0:
            for cls in classes[:]:
                classes.remove(cls)
                classes += self.hierarchy[cls].getParents()
                if attribute == 'state':
                    if value in self.hierarchy[cls].getStateFeatures():
                        return cls
                else:
                    raise NotImplementedError,'Unable to get %s slots from superclasses' % (attribute)
        # Oops, didn't find anything anywhere
        if includeSelf:
            raise KeyError,'No %s value %s for %s' % (attribute,value,
                                                      self.name)
        else:
            return None

    def getCumulativeState(self,feature):
        cls = self.getInheritor('state',feature)
        return self.hierarchy[cls].getState(feature)

    def deleteState(self,feature):
        """Removes the given feature from the state
        @type feature: str
        """
        # Need to actually remove the feature here
        key = StateKey({'entity':self.name,'feature':feature})
        self.state = self.state.marginalize(key)
        # Remove from dynamics
        if self.dynamics.has_key(feature):
            del self.dynamics[feature]

    def ancestors(self,order=False):
        """
        @param order: if C{True}, then order the results from general to specific (default is C{False})
        @type order: bool
        @return: all ancestor classes of this class, including itself
        @rtype: str[]
        """
        result = {}
        next = [self.name]
        while len(next) > 0:
            name = next.pop()
            if not result.has_key(name):
                result[name] = True
                next += self.hierarchy[name].getParents()
        if order:
            remaining = result.keys()
            result = []
            while len(remaining) > 1:
                index = 0
                while True:
                    entity = self.hierarchy[remaining[index]]
                    if len(filter(lambda p: not p in result,
                                  entity.getParents())) == 0:
                        break
                    index += 1
                else:
                    raise UserWarning,'Cycle in hierarchy'
                result.append(entity.name)
                del remaining[index]
            result.append(remaining[0])
            return result
        else:
            return result.keys()
                
    def getRelationships(self):
        """
        @return: all the relationships available to this generic model (including those to its superclasses
        @rtype: str[]
        """
        relationships = {}
        for name in self.ancestors():
            for relationship in self.hierarchy[name].relationships.keys():
                relationships[relationship] = True
        relationships = relationships.keys()
        relationships.sort()
        return relationships
    
    def __xml__(self,doc=None):
        """Returns an XML Document representing this model"""
        if doc is None:
            doc = Stereotyper.__xml__(self)
        root = doc.documentElement
        root.setAttribute('depth',str(self.depth))
        node = doc.createElement('parents')
        root.appendChild(node)
        for name in self.parentModels:
            child = doc.createElement('parent')
            child.appendChild(doc.createTextNode(name))
            node.appendChild(child)
        node = doc.createElement('state')
        node.appendChild(self.state.__xml__().documentElement)
        root.appendChild(node)
        doc = Supporter.__xml__(self,doc)
        return doc

    def parse(self,element):
        """Extracts model elements from the provided XML element
        @type element: Element"""
        Stereotyper.parse(self,element)
        try:
            self.depth = 0 #int(element.getAttribute('depth'))
        except ValueError:
            # Probably means there's no depth attribute at all
            pass
        node = element.firstChild
        while node:
            if node.nodeType != node.ELEMENT_NODE:
                pass
            elif node.tagName == 'parents':
                parent = node.firstChild
                while parent:
                    if parent.nodeType == node.ELEMENT_NODE:
                        name = str(parent.firstChild.data).strip()
                        self.parentModels.append(name)
                    parent = parent.nextSibling
            elif node.tagName == 'state':
                parent = node.firstChild
                while parent:
                    if parent.nodeType == node.ELEMENT_NODE:
                        self.state.parse(parent,KeyedVector)
                    parent = parent.nextSibling
#                delta = (1.-sum(self.state.values()))/float(len(self.state))
#                for element in self.state.domain():
#                    self.state[element] += delta
            node = node.nextSibling

    def importDict(self,generic):
        """Updates generic model from dictionary-style spec"""
        # Parent models
        try:
            self.parentModels = generic['parent']
        except KeyError:
            pass
        # State
        if generic.has_key('state'):
            for feature,value in generic['state'].items():
                self.setState(feature,value)
        # Actions
        if generic.has_key('actions'):
            self.actions = extractSpace(generic['actions'])
        # Goals
        if generic.has_key('goals'):
            self.setGoals(generic['goals'])
        # Models
        if generic.has_key('models'):
            for name,model in generic['models'].items():
                agent = GenericModel(name)
                agent.setGoals(model['goals'])
                agent.policy = model['policy']
                self.models[name] = agent
        if generic.has_key('model'):
            self.model = generic['model']
        # Relationships
        if generic.has_key('relationships'):
            self.relationships = generic['relationships']
            for label,targets in self.relationships.items():
                if not isinstance(targets,list):
                    raise UserWarning,'For consistency, we require that the target class(es) for a relationship be provided in a list, rather than as a singleton (i.e., %s: [%s])' % (label,targets)
        # Beliefs
        if generic.has_key('beliefs'):
            for other,belief in generic['beliefs'].items():
                if other:
                    if other == 'self':
                        entity = GenericModel(self.name)
                    else:
                        entity = GenericModel(other)
                    self.setEntity(entity)
                    for key,value in belief.items():
                        if key == 'model':
                            entity.model = {'name':value,
                                            'fixed':False}
                        else:
                            entity.setState(key,value)
                else:
                    # What do we do with the "None" values?
                    raise DeprecationWarning,'Do not use "None" keys in generic model hierarchy'
        # Dynamics
        if generic.has_key('dynamics'):
            if isinstance(generic['dynamics'],list):
                dynamicsList = generic['dynamics']
            else:
                dynamicsList = [generic['dynamics']]
            for dynamics in dynamicsList:
                for feature,dynDict in dynamics.items():
                    self.dynamics[feature] = {}
                    for act,dyn in dynDict.items():
                        if isinstance(dyn,dict):
                            tree = apply(dyn['class'],(dyn['args'],))
                            tree = tree.getTree()
                        else:
                            assert isinstance(dyn,DecisionTree)
                            tree = dyn
                        condition = ActionCondition()
                        condition.addCondition(act)
                        self.dynamics[feature][act] = {'condition': condition,
                                                       'tree': tree}
        # Observations
        if generic.has_key('observations'):
            for omega,entries in generic['observations'].items():
                new = copy.deepcopy(entries)
                if isinstance(omega,ObservationKey):
                    key = omega
                else:
                    key = ObservationKey({'type': omega})
                try:
                    self.observations[key].update(new)
                except KeyError:
                    self.observations[key] = new
        # Depth of recursive beliefs
        if generic.has_key('depth'):
            self.depth = generic['depth']
        # Horizon of lookahead
        if generic.has_key('horizon'):
            self.horizon = generic['horizon']
