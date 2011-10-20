import copy
import string
from types import *

from teamwork.agent.Agent import Agent
from teamwork.action.PsychActions import *

class ThespianAction(Action):
    nop = 'wait'
    fields = {
    # Redundant fields between actions and messages
    'actor':{},'sender':{},
    'object':{},'receiver':{},
    # Same as in actions
    'type':{},'command':{},
    # Unique to messages
    'factors':{},'performative':{},'force':{},
    '_observed':{},'_unobserved':{},

    'sact_type':{},
    'attitude':{'pos_face':0.0,'neg_face':0.0},
    'addressee':{},
    }
##    format = ['actor','type','object','command','item','property','sact_type','attitude']
    
    def __init__(self,arg={}):
        """Translates an action in string form into a structured
        representation of that same action (e.g.,
        'CLF-violence-to-UrbanPoor' becomes a PsychAction object
        {'actor':CLF,'type':'violence','object':UrbanPoor}"""
##        self.command = None
        if len(arg) == 0:
            dict.__init__(self,{'type': self.nop})
        if type(arg) is StringType:
            components = string.split(arg,'-')
##            print '[PS] ', components
            if len(components) < 2:
                # <type>
##                self.type = components[0]
                dict.__init__(self,{'type': components[0]})
            elif len(components) < 3:
                # <actor>-<type>
##                self.actor = components[0]
##                self.type = components[1]
                dict.__init__(self,{'actor': components[0],'type': components[1]})
            elif len(components) < 4:
                if components[1]=='to':
                    # <type>-to-<object>
##                    self.type = components[0]
##                    self.object = components[2]
                    dict.__init__(self,{'type': components[0],'object': components[2]})
                elif components[1]=='about':
                    # <type>-about-<item>
##                    self.type = components[0]
##                    self.item = components[2]
                    dict.__init__(self,{'type': components[0],'item': components[2]})
            elif len(components) < 5:
                # <actor>-<type>-to-<object>
                if components[2]=='to':
##                    self.object = components[3]
##                    self.actor = components[0]
##                    self.type = components[1]
                    dict.__init__(self,{'actor': components[0],'type': components[1],'object': components[3]})
                else:
                #mei 03/16/04
                #<type>-<object>-<item>-<property>
##                    self.type = components[0]
##                    self.object = components[1]
##                    self.item = components[2]
##                    self.property = components[3]
                    dict.__init__(self,{'type': components[0],'object': components[1],'item': components[2],'property': components[3]})
##            elif components[2] == 'to':
##                # <actor>-<command>-to-<object>-<action>
##                self.object = components[3]
##                substr = string.join(components[4:],'-')
##                self.command = PsychAction(substr)
##                self.actor = components[0]
##                self.type = components[1]
##            elif:
##                # <command>-to-<object>-<action>
##                self.object = components[2]
##                substr = string.join(components[3:],'-')
##                self.command = PsychAction(substr)
##                self.type = components[0]
            elif len(components) < 6:
                # <actor>-<type>-<object>-<item>-<property>
                # mei added 03/16/04
                #print 'coming here'
                if components[1] == 'to':
                    #<type>-to-<object>-about-<item>
##                    self.type = components[0]
##                    self.object = components[2]
##                    self.item = components[4]
                    dict.__init__(self,{'type': components[0],'object': components[2],'item': components[4]})
                else:
##                    self.actor = components[0]
##                    self.type = components[1]
##                    self.object = components[2]
##                    self.item = components[3]
##                    self.property = components[4]
                    dict.__init__(self,{'actor': components[0],'type': components[1],'object': components[2],'item': components[3],'property': components[4]})
            elif len(components) < 7:
                #<actor>-<type>-to-<object>-about-<item>
                 if components[2] == 'to':
##                    self.actor = components[0]
##                    self.type = components[1]
##                    self.object = components[3]
##                    self.item = components[5]
                      dict.__init__(self,{'actor': components[0],'type': components[1],'object': components[3],'item': components[5]})
            elif len(components) < 8:
                #<type>-to-<object>-about-<property>-of-<item>
##                self.type = components[0]
##                self.object = components[2]
##                self.item = components[6]
##                self.property = components[4]
                dict.__init__(self,{'type': components[0],'object': components[2],'item': components[6],'property': components[4]})
                #student-request-to-oldman-about-name-of-town
            elif len(components) < 9:
##                self.actor = components[0]
##                self.type = components[1]
##                self.object = components[3]
##                self.item = components[7]
##                self.property = components[5]
                dict.__init__(self,{'actor': components[0],'type': components[1],'object': components[3],'item': components[7],'property': components[5]})
##                print 'psychaction: ',self

            if (not self.has_key('addressee')) and self.has_key('object'):
                self['addressee'] = [self['object']]
                self['object'] = None
            
        elif type(arg) is ListType:
            dict.__init__(self,arg[0])
        else:
##            for key in self.fields:
##                try:
##                    self[key] = arg[key]
##                except KeyError:
##                    self[key] = None
                dict.__init__(self,arg)
##            if self.command:
##                self.command = PsychAction(self.command)
                
        self.name = ''

        if not self.has_key('sact_type'):
            self['sact_type'] = self['type']

        if not self.has_key('addressee'):
            self['addressee'] = []
        

        ## quick to make it compatibale with current code
##        self.type = self['type']
##        self.actor = self['actor']
##        self.object = self['object']
##        self.item = self['item']
##        self.property = self['property']
        

##        for key in self.fields:
##            if not self.__dict__.has_key(key):
##                self.__dict__[key] = None

        
##    def instantiate(self,entities=[]):
##        if type(entities) is DictType:
##            for key in self.fields:
##                if entities.has_key(key):
##                    self.__dict__[key] = entities[key]
##        elif type(entities) is ListType:
##            for key in self.fields:
##                for entity in entities:
##                    try:
##                        if entity.name == self.__dict__[key]:
##                            self.__dict__[key] = entity
##                            break
##                    except AttributeError:
##                        pass
##        else:
##            raise TypeError,`type(entities)`+' not supported by '+\
##                  'PsychAgents instantiate method'
##        if self.command:
##            self.command.instantiate(entities)
### Mei
##    def toString (self):
##        res=self.type
##        if self.actor:
##            tmp=self.actor
##            if not type(tmp) is StringType:
##                tmp = tmp.name
##            res=tmp+'-'+res
##        
##        if self.object:
##            tmp=self.object
##            if not type(tmp) is StringType:
##                tmp = tmp.name
##            res=res+'-'+tmp
##        if self.item:
##            res=res+'-'+self.item
##        if self.property:
##            res=res+'-'+self.property
##    
##
##        return res
##    
##    def __getitem__(self,index):
##        if index in self.fields:
##            return self.__dict__[index]
##        else:
##            return KeyError,index
##
##    def __setitem__(self,index,value):
##        if index in self.fields:
##            self.__dict__[index] = value
##        else:
##            return KeyError,index
##            
##    def __delitem__(self,index):
##        if index in self.fields:
##            self.__dict__[index] = None
##        else:
##            return KeyError,index

##    def keys(self):
##        list = []
##        for key in self.fields:
##            if self.__dict__[key]:
##                list.append(key)
##        return list
    
    def __repr__(self):
        """Translates a structured dictionary representation of an action
        into a standardized string format (e.g.,
        {'actor':CLF,'type':'violence','object':UrbanPoor} becomes
        'CLF-violence-to-UrbanPoor'"""
        str = ''
        try:
            str = self['type']
            if self['object']:
                obj = self['object']
                if not type(obj) is StringType:
                    obj = obj.name
                str = str+'-to-'+obj
            if self['actor']:
                actor = self['actor']
                if not type(actor) is StringType:
                    actor = actor.name
                str = actor+'-'+str
    ##        if self['command']:
    ##            str = str + '-' + `self.command`

        except AttributeError:
            pass
##            print obj

        self.name = str
        return self.name


if __name__ == '__main__':
##    from teamwork.examples.PsychSim.EntityFactory import *

    #act = PsychAction('CortinaGov-wait')
    #print act.keys()
#<type>-to-<object>-about-<item>-of-<property>
    act = ThespianAction('request-to-oldman-about-name-of-town')
    act['actor']='stu'
    print act
    
##    actor = createEntity('ProGovPsyops','Coalition')
##    for actType in actor.getDefault('actions'):
##        act = PsychAction({'actor':actor.name,
##                           'type':actType,
##                           'object':'Poor'})
##        print act
##    act = PsychAction('CortinaGov-command-to-UrbanPoor-violence-to-CLF')
##    copy = PsychAction(act)
##    if act == copy:
##        print 'yay!'
