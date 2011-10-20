"""A class of unique identifiers for symbolic identification of rows and columns in the PWL representations of state, dynamics, reward, etc.
@var keyConstant: a L{ConstantKey} instance to be reused (i.e., so as not to have to create millions of new instances
@var keyDelete: a flag string used internally"""
from xml.dom.minidom import *
import copy
import string
from teamwork.action.PsychActions import Action

keyDelete = '__delete__'

class Key(dict):
    """Superclass for all different keys, used for indexing the various symbolic matrices and hyperplanes"""
    # The label for this Key subclass
    keyType = 'generic'
    # A dictionary of the slot labels expected by this Key subclass
    slots = {}
    # The possible values for the above dictionary
    CLASS = 0
    ENTITY = 1
    STATE = 2
    ACTION = 3
    VALUE = 4
    ENTITIES = 5
    TEST = 6

    def __str__(self):
        try:
            return self._string
        except AttributeError:
            self._string = self.simpleText()
            return self._string

    def __hash__(self):
        """Allows L{Key} objects to be used as dictionary keys
        @return: A hash value for this L{Key}"""
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(str(self))
            return self._hash

    def simpleText(self):
        return dict.__str__(self)

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: Any new L{Key} instances with the appropriate label substitutions
        @rtype: L{Key}[]
        """
        objList = [copy.copy(self)]
        for key in self.slots.keys():
            if self.slots[key] == self.ENTITY and self[key]:
                try:
                    entities = table[self[key]]
                except KeyError:
                    # No filler for this entity
                    return []
                if not isinstance(entities,list):
                    if isinstance(entities,str):
                        entities = [entities]
                    else:
                        # Agent
                        entities = [entities.name]
                for obj in objList[:]:
                    objList.remove(obj)
                    for entity in entities:
                        newObj = copy.copy(obj)
                        newObj[key] = entity
                        objList.append(newObj)
#         for key,value in self.items():
#             try:
#                 entity = table[value]
#             except KeyError:
#                 continue
#             if isinstance(entity,list):
#                 entityList = entity
#             elif isinstance(entity,str):
#                 entityList = [entity]
#             else:
#                 # Assume that it's an Agent
#                 entityList = [entity.name]
#             for obj in objList[:]:
#                 objList.remove(obj)
#                 for entity in entityList:
#                     newObj = copy.copy(obj)
#                     newObj[key] = entity
#                     objList.append(newObj)
        return objList

    def __copy__(self):
        return self.__class__(self)

    def __xml__(self):
        """XML Serialization
        
        The format looks like::

           <key type=\"self.keyType\">
              <tag1>value1</tag1>
              <tag2>value2</tag2>
              ...
              <tagn>valuen</tagn>
           </key>
        
        @return: An XML object representing this L{Key}
        @rtype: Element"""
        doc = Document()
        root = doc.createElement('key')
        doc.appendChild(root)
        root.setAttribute('type',self.keyType)
        for key,value in self.items():
            node = doc.createElement(key)
            root.appendChild(node)
            if isinstance(value,str):
                node.appendChild(doc.createTextNode(value))
            elif isinstance(value,int):
                node.appendChild(doc.createTextNode(str(value)))
            elif value is None:
                pass
            elif isinstance(value,list):
                for action in value:
                    if isinstance(action,Action):
                        node.appendChild(action.__xml__().documentElement)
                    else:
                        raise NotImplementedError,'Unable to serialize key, "%s", with lists of %s' % (key,action.__class__.__name__)
            else:
                raise NotImplementedError,'Unable to serialize key, "%s", with values of type %s' % (key,value.__class__.__name__)
        return doc

    def parse(self,element):
        """Updates the current key with the elements stored in the given XML element
        @type element: Element
        @return: the L{Key} object stored in the given XML element
        """
        assert(element.tagName == 'key')
        keyType = element.getAttribute('type')
        for cls in self.__class__.__subclasses__():
            if cls.keyType == keyType:
                key = cls()
                node = element.firstChild
                while node:
                    if node.nodeType == node.ELEMENT_NODE:
                        # Not sure whether this is robust enough unicode handling
                        label = string.strip(str(node.tagName))
                        value = None
                        if label == 'action':
                            # Special case, how ugly
                            value = []
                            subNode = node.firstChild
                            while subNode:
                                if subNode.nodeType == node.ELEMENT_NODE:
                                    act = Action()
                                    act.parse(subNode)
                                    value.append(act)
                                subNode = subNode.nextSibling
                        elif label == 'depth':
                            # Ouch, another special case
                            value = int(node.childNodes[0].data)
                        else:
                            try:
                                value = string.strip(str(node.childNodes[0].data))
                            except IndexError:
                                # Nothing there, hope that's OK
                                pass
                        key[label] = value
                    node = node.nextSibling
                return key
        else:
            print element.getAttribute('type')
            print map(lambda c:c.keyType,self.__class__.__subclasses__())
            raise NotImplementedError,'Unsupported key type: %s' % (keyType)
    
class ConstantKey(Key):
    """A L{Key} indicating the entry corresponding to a constant factor"""
    keyType = 'constant'

    def simpleText(self):
        return 'constant'
    
keyConstant = ConstantKey()
    
class StateKey(Key):
    """A L{Key} indicating the entry corresponding to a state feature value"""
    keyType = 'state'
    slots = {'entity':Key.ENTITY,
             'feature':Key.STATE}

    def simpleText(self):
        if self['entity'] == 'self':
            return 'my %s' % (self['feature'])
        else:
            return '%s\'s %s' % (self['entity'],self['feature'])

class ModelKey(Key):
    """A L{Key} indicating the mental model corresponding to a given entity
    """
    keyType = 'model'
    slots = {'entity':Key.ENTITY}
    
    def simpleText(self):
        if self['entity'] == 'self':
            return 'mental model of me'
        else:
            return 'mental model of %s' % (self['entity'])
        
class BinaryKey(StateKey):
    """A L{StateKey} whose values will be either 0. or 1.
    @warning: the code does not enforce this restriction; it merely exploits it
    """
    keyType = 'binary'

class ObservationKey(Key):
    """A L{Key} indicating the entry corresponding to an observation flag

    >>> key = ObservationKey({'type':'heard left'})
    """
    keyType = 'observation'
    decayRate = 0.5

    def simpleText(self):
        return self['type']

class ActionKey(ObservationKey,Key):
    """A L{Key} indicating the entry corresponding to an observed action flag

    >>> key = ActionKey({'type':'tax','entity':'manager','object':'market'})

    A minimum of one of the fields must be provided.  Any omitted fields are assumed to be filled by wildcards.
    """
    keyType = 'action'
    slots = {'type':Key.ACTION,
             'entity':Key.ENTITY,
             'object':Key.ENTITY}
        
    def simpleText(self):
        content = self['type']
        if self['object']:
            content += ' %s' % (self['object'])
        if self['entity']:
            content += ' by %s' % (self['entity'])
        return content
        
class IdentityKey(Key):
    """A L{Key} indicating the entry corresponding to a role flag.  The I{relationship} slot can take on the following values:
       - equals: tests that an agent equals the specified I{entity} field
       - in: tests that an agent is in the specified I{entity} list of agents
       """
    keyType = 'identity'
    slots = {'entity':Key.ENTITY,
             'relationship':Key.TEST}

    def __init__(self,args={}):
        Key.__init__(self,args)
        if self.has_key('entity') and 'entity' == 'self':
            raise UserWarning,'Hey nimrod, why are you testing whether the agent is itself?'
        
    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{Key}
        """
        if self['relationship'] == 'equals':
            if table.has_key(self['entity']) and \
                   table[self['entity']] == table['self'].name:
                return keyConstant
            else:
                return keyDelete
        elif self['relationship'] == 'in':
            assert isinstance(self['entity'],list),\
                   'Non-list entity for "in" relationship: %s' \
                   % (str(self['entity']))
            if table['self'].name in table[self['entity']]:
                return keyConstant
            else:
                return keyDelete
        else:
            raise NotImplementedError,'Unknown relationship, "%s", in %s instance' \
                  % (self['relationship'],self.__class__.__name__)

    def simpleText(self):
        return 'I am %s' % (self['entity'])

class ClassKey(Key):
    """A L{Key} indicating the entry corresponding to a class membership flag"""
    keyType = 'class'
    slots = {'value':Key.CLASS,
             'entity':Key.ENTITY}

    def simpleText(self):
        if self['entity'] == 'self':
            return 'I am %s' % (self['value'])
        else:
            return '%s is %s' % (self['entity'],self['value'])

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{Key}
        """
        if self['entity'] == 'self':
            entity = table['self']
        else:
            try:
                entity = table['self'].getEntity(table[self['entity']])
            except KeyError:
                # Assume false
                return keyDelete
        if entity.instanceof(self['value']):
            return keyConstant
        else:
            return keyDelete

class RelationshipKey(Key):
    """A L{Key} indicating the entry corresponding to the slot for the corresponding inter-agent relationship
    """
    keyType = 'relationship'
    slots = {'feature':Key.STATE,
             'relatee':Key.ENTITY,
             }

    def simpleText(self):
        if self['relatee'] == 'self':
            content = 'I am my own %s' % (self['feature'])
        else:
            content = '%s is my %s' % (self['relatee'],self['feature'])
        return content

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{Key}
        """
        try:
            eligible = table['self'].relationships[self['feature']]
        except KeyError:
            return keyDelete
        if self['relatee'] == 'self':
            name = table[self['relatee']].name
        else:
            name = table[self['relatee']]
        if name in eligible:
            return keyConstant
        else:
            return keyDelete


class LinkKey(Key):
    """A L{Key} corresponding to a slot for a pairwise link between two entities
    """
    keyType = 'link'
    slots = {
        'subject':Key.ENTITY,
        'verb':Key.STATE,
        'object':Key.ENTITY,
        }

    def simpleText(self):
        if self['subject'] == 'self':
            content = 'I %s ' % (self['verb'])
            if self['object'] == 'self':
                content += 'myself'
            else:
                content += self['object']
        else:
            content = '%s %s ' % (self['subject'],self['verb'])
            if self['object'] == 'self':
                content += 'me'
            else:
                content += self['object']
        return content
    
class WorldKey(Key):
    """A L{Key} indexing into a sample space of possible worlds
    """
    keyType = 'world'
    slots = {'world': Key.VALUE}

    def __setitem__(self,index,value):
        Key.__setitem__(self,index,value)
        if not isinstance(self['world'],int):
            self['world'] = int(self['world'])

    def simpleText(self):
        return 'Q=%d' % (self['world'])
    
def makeStateKey(entity,feature):
    """Helper function for creating StateKey objects
    @param entity: The entity to be pointed to by this key
    @type entity: string
    @param feature: The state feature to be pointed to by this key
    @type feature: string
    @return: the corresponding StateKey object"""
    return StateKey({'entity':entity,'feature':feature})

def makeActionKey(action):
    """Helper function for creating ActionKey objects
    @param action: The action to be flagged by this Key
    @type action: Action instance (though a generic dictionary will work, too)
    @return: an ActionKey instance corresponding to the given action"""
    return ActionKey({'type':action['type'],
                      'entity':action['actor'],
                      'object':action['object']})

def makeIdentityKey(entity):
    """Helper funtion for creating IdentityKey objects
    @param entity: the relationship that should be matched on
    @type entity: string (e.g., 'actor','object')
    @return: an IdentityInstance testing for the given relationship"""
    return IdentityKey({'entity':entity,
                        'relationship':'equals'})

def makeClassKey(entity,className):
    """Helper function for creating ClassKey objects
    @param entity: the entity to be tested
    @type entity: string (e.g., 'actor','object','self')
    @param className: the class name to test membership for
    @type className: string
    @return: a ClassKey instance with the appropriate class test
    @warning: may not actually work
    """
    return ClassKey({'value':className,
                     'entity':entity})

def temporaryTest(original):
    """Debugging code"""
    used = {}
    for root in original:
        trees = [root]
        while len(trees) > 0:
            tree = trees.pop()
            trees += tree.children()
            assert not used.has_key(id(tree))
            used[id(tree)] = True
            if tree.isLeaf():
                matrix = tree.getValue()
                assert not used.has_key(id(matrix))
                used[id(matrix)] = True
                for row in matrix.values():
                    assert not used.has_key(id(row))
                    used[id(row)] = True
            else:
                for plane in tree.split:
                    assert not plane.weights._frozen
                    assert not used.has_key(id(plane.weights))
                    assert not used.has_key(id(plane.weights._order))
                    used[id(plane.weights)] = True
                    used[id(plane.weights._order)] = True
    for root in original:
        trees = [root]
        while len(trees) > 0:
            tree = trees.pop()
            trees += tree.children()
            if tree.isLeaf():
                for row in tree.getValue().values():
                    for key in row.keys():
                        if not row._order.has_key(key):
                            print 'leaf'
                            return root,key
            else:
                for plane in tree.split:
                    for key in plane.weights.keys():
                        if not plane.weights._order.has_key(key):
                            print 'branch'
                            return root,key
    else:
        return None
