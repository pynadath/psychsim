"""Linear reward subfunctions
@author: David V. Pynadath <pynadath@ict.usc.edu>
"""

import copy
import string
from types import *
from xml.dom.minidom import *

from teamwork.math.probability import *
from teamwork.math.KeyedMatrix import *
from teamwork.action.PsychActions import *
from teamwork.utils.PsychUtils import *
from teamwork.agent.Agent import Agent

class MinMaxGoal:
    """A reward subfunction that is linear in a single feature/action

    0) Creating a new goal (i.e., __init__()):
    goal = L{MinMaxGoal}(entity,direction,type,key)

    1) Accessing elements of this goal
    goal.L{isMax}()
    """
    def __init__(self,entity=None,direction=None,goalType=None,
                 key=None,value={}):
        """Constructs a goal object with the specified field values

        The named arguments are stored as corresponding attributes:
        @param entity:    list of names (for recursive belief access if a state goal, or for relevant actor/object if action goal)
        @type entity: C{str[]}
        @param direction: either 'min' or 'max'
        @type direction,goalType,key: C{str}
        @param goalType:  either 'state' (value of a state feature), 'act' (number of occurences of action of given type), 'actActor' (number of occurrences of action of given type by given actor), 'actObject' (number of occurences of action of given type to given object)
        @param key: for a 'state' goal, is the state feature to be min/maximized for an 'act', goal, is the act type to be min/maximized"""
        if type(entity) is StringType:
            raise DeprecationWarning,'Entity specification should be list of names'
        self.entity = entity
        if direction:
            self.direction = string.lower(direction)
        else:
            # By default, maximize
            self.direction = None
        if goalType:
            self.type = goalType
        else:
            # By default, state
            self.type = 'state'
        if key:
            self.key = key
        else:
            self.key = ''
        self.name = self.generateName()
        self.value = value
        self.weight = 1.

    def __copy__(self):
        newGoal = self.__class__(self.entity,self.direction,self.type,
                              self.key,copy.deepcopy(self.value))
        newGoal.weight = self.weight
        return newGoal

    def generateName(self):
        """Returns a canonical string representation"""
        if not self.direction:
            # Empty goal
            return ''
        # Start with direction
        name = self.direction+'imize '
        # Generate string rep of key
        if self.key[0] == '_':
            feature = self.key[1:]
        else:
            feature = self.key
        # Generate entity name(s)
        if len(self.entity) == 1:
            entity = self.entity[0]
        elif len(self.entity) == 2:
            entity = '%s to %s' % (self.entity[1],self.entity[0])
        elif len(self.entity) > 2:
            entity = self.entity[0]
            for other in self.entity[1:]:
                entity += '->%s' % (other)
        # Generate type-specific usage of entity
        if self.type == 'state':
            name += '%s of %s' % (feature,entity)
        else:
            name += 'number of %s' % (feature)
            if self.type == 'actActor':
                name += ' by %s' % (entity)
            elif self.type == 'actObject':
                name += ' to %s' % (entity)
        return name

    def isMax(self):
        """
        @return: true if maximization goal, false if minimization
        @rtype: C{boolean}
        """
        if self.direction == 'min':
            return False
        else:
            return True
        
    def toKey(self):
        """
        @return: the vector key corresponding to this goal
        @rtype: L{Key}
        @warning: There is no L{Key} subclass for beliefs
        """
        if self.type == 'state':
            if len(self.entity) == 1:
                return StateKey({'entity':self.entity[0],
                                 'feature':self.key})
            else:
                raise NotImplementedError,'Goals on beliefs cannot yet be converted into keys'
        else:
            # Need to handle action goals as well
            return makeActionKey(Action({'type':self.key}))
        
    def reward(self,context):
        """Applies this goal in the specified context"""
        # Grab the entity relevant to this goal
        entity = None
        if self.entity:
            entity = context
            for name in self.entity:
                try:
                    entity = entity[name]
                except TypeError:
                    # Probably shouldn't have this clunkiness
                    entity = entity.getEntity(name)
                except KeyError:
                    # No info about the relevant entity, so give up
                    value = Distribution({0.0:1.})
                    return value
        if self.type == 'state':
            try:
                value = entity.getState(self.key)
            except KeyError:
                print entity.getGoals()
                raise KeyError,'%s has no %s' % (entity.ancestry(),self.key)
        elif self.type[:3] == 'act':
            if self.key == 'obey':
                # Special action key indicating incentive for
                # obeying commands
                value = 0.
                try:
                    superiors  = entity.relationships['_commander']
                except KeyError:
                    superiors = []
                # Determine what I did last
                myAct,myDepth = context.findObservation({'actor':entity.name})
                if myAct:
                    for superior in superiors:
                        # Look for any commands
                        command = {'type':'command',
                                   'object':entity.name,
                                   'actor':superior}
                        act,depth = context.findObservation(command)
                        if act and depth > myDepth:
                            # There was a command before my last action
                            if myAct == act['command']:
                                try:
                                    value += entity.getSupport(act['actor']).mean()
                                except KeyError:
                                    value += 0.1
            else:
                # Determine target actions to look for
                if self.type == 'actObject':
                    targetList = []
                    for entity in self.entity:
                        targetList.append({'type':self.key,
                                           'object':entity})
                elif self.type == 'actActor':
                    targetList = []
                    for entity in self.entity:
                        targetList.append({'type':self.key,
                                           'actor':entity})
                else:
                    targetList = [{'type':self.key}]
                # Count up time-decayed occurrences of target actions
                value = 0.
                for target in targetList:
                    act,depth = context.findObservation(target)
                    if act:
                        value += pow(ActionKey.decayRate,float(depth))
            # Should be a distribution all the way through eventually
            value = Distribution({value:1.})
        else:
            raise NameError,'unknown goal type '+self.type
        if self.direction == 'max':
            pass
        elif self.direction == 'min':
            value = -value
        else:
            raise NameError,'unknown goal direction '+ self.direction
        return value

    def maxElement(self):
        """Finds the element that has the highest value
        @return: a tuple of the key and value
        @rtype: (C{str},L{Distribution})"""
        maxKey = None
        maxValue = Interval.FLOOR
        for key in self.keys():
            if self[key] > maxValue:
                maxKey = key
                maxValue = self[key]
        return maxKey,maxValue
    
    def __getitem__(self,index):
        """Accessor: supports access in the form `self[index]'"""
        if self.value:
            return self.value[index]
        else:
            return 0.0
    
    def __setitem__(self,index,value):
        """Accessor: supports access in the form `self[index]=x'"""
        self.value[index] = value

    def keys(self):
        """@return: all of the element names in this goal"""
        if self.value:
            return self.value.keys()
        else:
            return []
        
    def evaluate(self,context):
        """Returns a new goal instance in the given context by computing the
        reward and storing it in its value attribute"""
        return self.__class__(self.entity,self.direction,self.type,self.key,
                              {self.name:self.reward(context)})

    def __add__(self,goal):
        if self.value:
            value = copy.deepcopy(self.value)
            if goal.value:
                for key in goal.value.keys():
                    try:
                        value[key] = value[key] + goal.value[key]
                    except KeyError:
                        value[key] = goal.value[key]
            return self.__class__(None,None,None,None,value)
        elif goal.value:
            return goal + self
        else:
            return self.__class__()

    def __neg__(self):
        return self*(-1.0)

    def __sub__(self,goal):
        return self + (-goal)
    
    def __mul__(self,factor):
        if type(factor) is FloatType:
            # Perform dot product
            value = copy.deepcopy(self.value)
            try:
                for key in value.keys():
                    value[key] = value[key] * factor
            except AttributeError,e:
                print value
                raise AttributeError,e
        elif factor.__class__ == self.__class__:
            # Perform dot product
            value = copy.deepcopy(self.value)
            for key in value.keys():
                try:
                    value[key] = value[key] * goal.value[key]
                except KeyError:
                    pass
        elif type(factor) is DictType:
            # Perform dot product
            value = copy.deepcopy(self.value)
            for key in value.keys():
                try:
                    value[key] = value[key] * factor[key]
                except KeyError:
                    # Assume weight is 0
                    del value[key]
        elif self.value:
            # Scale
            value = copy.deepcopy(self.value)
            for key in value.keys():
                value[key] = factor * value[key]
        else:
            value = 0.0
        return self.__class__(None,None,None,None,value)

    def __div__(self,factor):
        if type(factor) is InstanceType and \
               factor.__class__ == self.__class__:
            value = copy.deepcopy(factor.value)
            for key in value.keys():
                value[key] = 1.0 / value[key]
            return self * value
        else:
            return self * (1.0/factor)
        
    def total(self):
        """Returns sum over the individual elements in an instantiated goal"""
        value = Distribution({0.0:1.})
        if self.value:
            for key in self.value.keys():
                value = self.value[key] + value
        return value
        
    def __str__(self):
        if self.value:
            content = '{'
            keyList = self.value.keys()
            keyList.sort()
            first = 1
            for key in keyList:
                if first:
                    first = None
                else:
                    content = content + ','
                content = content + '\n\t' + key + ': '
                try:
                    content = content + '%6.4f' % self.value[key]
                except TypeError:
                    content +=  `self.value[key]`
                except AttributeError:
                    content = content + `self.value[key]`
            return content+'\n}'
        elif self.name:
            content = self.name
            return content
        else:
            return '<null>'

    def __hash__(self):
        return hash(self.name)
    
    def __xml__(self):
        doc = Document()
        root = doc.createElement('goal')
        doc.appendChild(root)
        root.setAttribute('direction',self.direction)
        root.setAttribute('type',self.type)
        root.setAttribute('key',self.key)
        root.setAttribute('weight',self.weight)
        node = doc.createElement('entity')
        root.appendChild(node)
        for name in self.entity:
            subNode = doc.createElement('name')
            node.appendChild(subNode)
            subNode.appendChild(doc.createTextNode(name))
        return doc
    
    def parse(self,element):
        entity = []
        child = element.firstChild
        while child:
            if child.nodeType == Node.ELEMENT_NODE:
                assert child.tagName == 'entity'
                subNodes = child.getElementsByTagName('name')
                for subNode in subNodes:
                    entity.append(string.strip(str(subNode.firstChild.data)))
            child = child.nextSibling
        self.entity = entity
        self.direction = str(element.getAttribute('direction'))
        self.type = str(element.getAttribute('type'))
        self.key = str(element.getAttribute('key'))
        self.weight = float(element.getAttribute('weight'))
        self.name = self.generateName()
        
def avengeGrievance(entity,entities,actions):
    total = 0.0
    for act in actions:
	if type(act) is StringType:
	    act = act2dict(act)
	if type(act['actor']) is StringType:
            try:
                act['actor'] = entities[act['actor']]
            except KeyError:
                # No beliefs about the actor, so don't bother evaluating
                continue
	try:
	    if type(act['object']) is StringType:
		act['object'] = entities[act['object']]
	except KeyError:
	    pass
	if act['type'] == 'violence' and \
	   act['actor'].name == entity.name:
            try:
                grievance = entity.getBelief(act['object'],'blame') * \
                            entity.getSelfBelief('hardship')
            except TypeError:
                # Unknown values show up as strings
                grievance = 0.0
	else:
	    grievance = 0.0
	total = total + grievance
    return total
