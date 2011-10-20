from Keys import *

class MessageKey(Key):
    keyType = 'message'
    slots = {'sact_type':Key.ACTION,
             'sender':Key.ENTITY,
             'addressee':Key.ENTITIES,
             'lhs':Key.STATE,
             }
    decayRate = 0.5

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{Key}
        """
        keys=[]
        if not self['sact_type'] or self['sact_type'] == 'wait':
            
            for addressee in table['addressee']:
                feature='obs-'+table['actor']+'-'+table['sact_type']+'-to-'+addressee
        
                if table['sact_type'] in  ['enquiry','inform','accept','reject','inform_info']:
                    feature += '-about-'+table['factors'][0]['lhs'][1]+ '-'+table['factors'][0]['lhs'][3]

                key = StateKey({'entity':table['self'].name,
                                          'feature':feature})
##                print key
                keys.append(key)
        else:
            
            for addressee in table['addressee']:
                feature='obs-'+table['actor']+'-'+self['sact_type']+'-to-'+addressee
        
                if table['sact_type'] in  ['enquiry','inform','accept','reject','inform_info']:
                    feature += '-about-'+table['factors'][0]['lhs'][1]+ '-'+table['factors'][0]['lhs'][3]

                key = StateKey({'entity':table['self'].name,
                                          'feature':feature})
##                print key
                keys.append(key)
        if len(keys) > 0:
            return keys
        else:
            return keyDelete
        
    def simpleText(self):
        content = self['sact_type']
        if self['addressee']:
            for add in self['addressee']:
                content += add+' ,'
        if self['sender']:
            content += ' by %s' % (self['sender'])
        if self['lhs']:
            content += ' about %s' % (self['lhs'])
        return content

class GroupStateKey(Key):
    keyType = 'groupstate'
    slots = {'entity':Key.ENTITY,
             'feature':Key.STATE}

    def simpleText(self):
        return '%s\'s %s' % (self['entity'],self['feature'])

class MetaStateKey(Key):
    keyType = 'meta'
    slots = {'entity':Key.ENTITY,
             'metafeature':Key.STATE}

    def simpleText(self):
        return '%s\'s %s' % (self['entity'],self['metafeature'])


class MessageEqualKey(Key):
    keyType = 'equal'
    slots = {'messageAttr':Key.STATE,
             'value':Key.VALUE}

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{Key}
        """
        if table[self['messageAttr']] == table[self['value']]:
            return keyConstant
        else:
            return keyDelete

    def simpleText(self):
        return 'action['+self['messageAttr']+'] equals to '+self['value']

class ObligKey(Key):
    keyType = 'checkApply'
    slots = {'obligation':Key.STATE,
             'role':Key.VALUE} 

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{Key}
        """
        ## obli-inform-to-Hamed-about-student-feature_nationality
        ## obli-bye_resp-to-Xaled
##                print self['obligation']
                
        try:
            dummy1,sact_type,dummy2,toobject,dummy3,entity,feature = string.split(self['obligation'],'-')
        except ValueError:
            try:
                dummy1,sact_type,dummy2,toobject = string.split(self['obligation'],'-')
            except:
                print self
                print table
                raise 'Illegal obligation name: ',self['obligation']

        try:
            actor = table['actor'].name
        except AttributeError:
            actor = table['actor']

        assert(isinstance(actor,str))
                    
        if actor == toobject:
            if table['sact_type']=='greet_init' and sact_type == 'greet_resp':
                return keyConstant
            elif table['sact_type']=='greet2_init' and sact_type == 'greet2_resp':
                return keyConstant
            elif table['sact_type']=='bye_init' and sact_type == 'bye_resp':
                return keyConstant
            elif table['sact_type']=='thank' and sact_type == 'urwelcome':
                return keyConstant
            elif table['sact_type']=='inform_info' and sact_type == 'OK':
                return keyConstant
            elif table['sact_type']=='request' and sact_type == 'accept':
                return keyConstant
##                        topic = table['factors'][0]['lhs'][1]+ '-'+table['factors'][0]['lhs'][3]
##                        try:
##                            entity = entity.name
##                        except AttributeError:
##                            pass
##                        if topic == entity+'-'+feature:
##                            loState[key] = hiState[key] = 1.
##                        else:
##                            pass
##                                print topic, entity+'-'+feature
            elif table['sact_type']=='enquiry' and sact_type == 'inform':
                topic = table['factors'][0]['lhs'][1]+ '-'+table['factors'][0]['lhs'][3]
                try:
                    entity = entity.name
                except AttributeError:
                    pass
                if topic == entity+'-'+feature:
                    return keyConstant
                else:
                    pass
##                                print topic, entity+'-'+feature
        return keyDelete

    def simpleText(self):
        return 'I have the obligation '+self['obligation']+' as an '+self['role']
    
class ExistObligKey(Key):
    keyType = 'checkExistOblig'
    slots = {'entity':Key.ENTITY,}

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{StateKey}
        """
        keys = []
        for addressee in table['addressee']:
            feature = 'obli-'+table['sact_type']+'-to-'+addressee
            if table['sact_type'] in  ['inform','accept','reject']:
                feature += '-about-'+table['factors'][0]['lhs'][1]+ '-'+table['factors'][0]['lhs'][3]
            ##print feature
            keys.append(StateKey({'entity':table['self'].name,
                                  'feature':feature}))
            
        return keys

    def simpleText(self):
        return 'I have the obligation to make this response'

class GroupExistObligKey(Key):
    keyType = 'checkGroupExistOblig'
    slots = {'entity':Key.ENTITY,}

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{StateKey}
        """
        keys = []
        for addressee in table['addressee']:
            feature = 'obli-'+table['sact_type']+'-to-'+addressee
                    
            if table['sact_type'] in  ['inform','accept','reject']:
                feature += '-about-'+table['factors'][0]['lhs'][1]+ '-'+table['factors'][0]['lhs'][3]
                    
            for entity1 in table['self'].getEntityBeliefs():
                if entity1.getState('group') == table['self'].getState('group'):
                    keys.append(StateKey({'entity':entity1.name,
                                          'feature':feature}))
        if len(keys) > 0:
            return keys
        else:
            return keyDelete

    def simpleText(self):
        return 'Somebody in the group have the obligation to make this response'
    
class ExistUnFinOligKey(Key):
    keyType = 'checkExistUnFinOblig'
    slots = {'entity':Key.ENTITY,}

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{Key}
        """
        keys = []
        for feature in table['self'].getStateFeatures():
            if string.find(feature,'obli')==0 and feature != 'obligNorm':
                keys.append(StateKey({'entity':table['self'].name,
                                     'feature':feature}))
        if len(keys) > 0:
            return keys
        else:
            return keyDelete
        
    def simpleText(self):
        return 'I have unfinished obligation'

class GroupExistUnFinOligKey(Key):
    keyType = 'checkGroupExistUnFinOblig'
    slots = {'entity':Key.ENTITY,}

    def instantiate(self,table):
        """Utility method that takes a mapping from entity references (e.g., 'self', 'actor') to actual entity names (e.g., 'Bill', 'agent0').  It returns a new key string with the substitution applied.  It also reduces any 'identity' keys to be either constant or null depending on whether the key matches the identity of the entity represented in the dictionary provided.  Subclasses should override this method for more instantiation of more specialized fields.
        @param table: A dictionary of label-value pairs.  Any slot in the key whose filler matches a label in the given table will be replaced by the associated value.
        @type table: C{dict}
        @return: A new L{Key} instance with the appropriate label substitutions
        @rtype: L{Key}
        """
        keys = []
        for entity1 in table['self'].getEntityBeliefs():
            for feature in entity1.getStateFeatures():
                if string.find(feature,'obli')==0 and not feature == 'obligNorm':
                    key = StateKey({'entity':entity1.name,
                                    'feature':feature})
                    keys.append(key)
        if len(keys) > 0:
            return keys
        else:
            return keyDelete

    def simpleText(self):
        return 'Somebody in the group still have unfinished obligation'

def makeGroupStateKey(entity,feature):
    """Helper function for creating GroupStateKey objects
    @param entity: The group of entity to be pointed to by this key
    @type entity: string
    @param feature: The state feature to be pointed to by this key
    @type feature: string
    @return: the corresponding GroupStateKey object"""
    return GroupStateKey({'entity':entity,'feature':feature})
    

def makeMessageKey(action):
    """Returns a key correspond to the value of the given action"""
    try:
        return MessageKey({'sact_type':action['sact_type'],
                          'sender':action['sender'],
                          'addressee':action['addressee'],
                          'lhs':action['factors'][0]['lhs'],})
    except:
        return MessageKey({'sact_type':action['sact_type'],
                          'sender':action['sender'],
                          'addressee':action['addressee'],
                          'lhs':'dummy',})

def makeBelongKey(entity):
    return IdentityKey({'relationship':'in',
                        'entity':entity})

def makeMessageEqualKey(attr,value):
    return EqualKey({'messageAttr':'attr',
                        'value':value})

## if this state feature is the obligation related to the current action
def makeObligKey(feature,role):
    return ObligKey({'obligation':feature,
                        'role':role})

def makeMetaStateKey(entity,feature):
    """Returns a key correspond to the value of the given feature of the
    given entity"""
    return MetaStateKey({'entity':entity,'metafeature':feature})

## if the current action is satisfying an existing obligation of the entity
def makeExistObligKey(entity):
    return ExistObligKey({'entity':entity})

## if the current action is satisfying an existing obligation of somebody in the group
def makeGroupExistObligKey(entity):
    return GroupExistObligKey({'entity':entity})

## if the agent has unsatisfied obligations
def makeExistUnFinOligKey(entity):
    return ExistUnFinOligKey({'entity':entity})

## if any agent in the conversation has unsatisfied obligations
def makeGroupExistUnFinOligKey(entity):
    return GroupExistUnFinOligKey({'entity':entity})
