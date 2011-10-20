__author__ = 'David V. Pynadath <pynadath@isi.edu>'
"""Class definition of messages"""

import string
from types import *
from teamwork.math.Interval import Interval
from teamwork.action.PsychActions import *

from teamwork.messages.PsychMessage import *


class ThespianMessage(Message):
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
    acceptString = 'accept'
    rejectString = 'reject'
    
    def __init__(self,arg='',theme=None):
        if isinstance(arg,str):
            Message.__init__(self)
##            self['type'] = '_message'

            try:

                if string.find(arg,',')>-1:
                    try:
                        sender,addressee, sact_type, formality,politeness,detail,emphasis, factors = string.split(arg,',')
                        self['attitude'] = {'formality':float(formality),'politeness':float(politeness),\
                                            'detail':float(detail),'emphasis':float(emphasis)}
                    except:
                        try:
                            sender,addressee, sact_type, formality, politeness,factors = string.split(arg,',')
                            self['attitude'] = {'formality':float(formality),'politeness':float(politeness)}
                        except:
                            try:
                                sender,addressee, sact_type, mtype, factors = string.split(arg,',')
                                self['type'] = string.strip(mtype)
                            except:
                                try:
                                    sender,addressee, sact_type, factors = string.split(arg,',')
                                except:
    ##                                print here
                                    raise arg
                    
                    self['actor'] = self['sender'] = string.strip(sender)

                    if string.find(addressee,'+')>-1:
                        addrs = string.split(string.strip(addressee),'+')
                        addressee = []
                        for addr in addrs:
                            addressee.append(addr)
                        self['addressee'] = addressee
                    else:
                        self['addressee'] = [string.strip(addressee)]

                    self['object']=None
                                
                    self['sact_type'] = string.strip(sact_type)

                    self.extractFromString(string.strip(factors))
                elif not arg == '':
                    self.extractFromString(arg)
            except:
##                print arg
                raise arg
            
        else:
            dict.__init__(self,arg)


        if not self['type'] or self['type'] == 'wait':
            if self['sact_type']:
                if not self['sact_type'] in ['inform','request','accept','reject','message']:
                    self['type'] = self['sact_type']
                else:
                    self['type'] = '_message'
            else:
                self['type'] = '_message'

        if self.has_key('sender') and not self.has_key('actor'):
            self['actor'] = self['sender']
        elif not self.has_key('sender') and self.has_key('actor'):
            self['sender'] = self['actor']

##        if self.has_key('addressee'):
##            print self['addressee']
##            print
##        else:
##            print 'no filed addressee'

        if not self.has_key('addressee') or self['addressee'] == None or self['addressee'] == []:
            if self.has_key('object'):
                self['addressee'] = [self['object']]
            else:
##                print 'no field object'
                self['addressee'] = None
        

#        self['object'] = self['addressee']
        self['object'] = None

        # Flag (used by internal Entity methods) to force the
        # acceptance of this message...useful for what-if reasoning
        if not self.has_key('force'):
            self['force'] = {}
##        self['theme'] = theme
        if not self.has_key('performative'):
            self['performative'] = 'tell'

        if not self.has_key('attitude'):
            self['attitude'] = {'formality':0.0,'politeness':0.0,'detail':0.0,'emphasis':0.0}

        for key in ['formality','politeness','detail','emphasis']:
            if not self['attitude'].has_key(key):
                self['attitude'][key]=0.0
            

        if not self.has_key('sact_type'):
            self['sact_type'] = 'wait'

        
        
        
    def extractFromString(self,str):
        """The string representation of a non-command message is:
        <key11>:<key12>:...:<key1n>=<value1>;<key21>:<key22>:...:<key2m>=<value2>;...
        e.g., entities:Psyops:state:power=0.7;entities:Paramilitary:entities:Psyops:state:power=0.7
        e.g., message Psyops Paramilitary entities:Psyops:policy:observation depth 3 actor Paramilitary type violence object UrbanPoor  violence-to-Paramilitary
        For commands, the syntax is
        'command;<key1>=<val1>;<key2>=<val2>;...', where the usual keys
        are 'object' (e.g., 'opponent') and 'type' (e.g., 'violence').
        This same format is expected by the constructor and returned by
        the string converter."""
##        print 'WARNING: You should migrate to dictionary spec of messages'
        self['factors'] = []
        factors = string.split(str,';')
        if factors[0] == 'command':
            self['command'] = {}
            for factor in factors[1:]:
                key,value = string.split(factor,'=')
                self['command'][key] = value
        else:
            self['command'] = None
            for factor in factors:
                factor = string.strip(factor)
                if factor == self.acceptString:
                    self.forceAccept()
                elif factor == self.rejectString:
                    self.forceReject()
                else:
                    relation = '='
                    pair = string.split(factor,relation)
                    if len(pair) == 1:
                        relation = '>>'
                        pair = string.split(factor,relation)
                    lhs = string.split(string.strip(pair[0]),':')
                    rhs = string.split(string.strip(pair[1]),':')
                    factor = {'lhs':lhs,'rhs':rhs,'relation':relation,
                              'topic':'state'}
                    if len(rhs) == 1:
                        try:
                            value = float(pair[1])
                        except ValueError:
                            value = pair[1]
                        factor['value'] = value
                    elif len(rhs) == 2:
                        try:
                            lo = float(rhs[0])
                            hi = float(rhs[1])
                            factor['value'] = Interval(lo,hi)
                        except ValueError:
                            pass
                    self['factors'].append(factor)
                    
        
        
    def __copy__(self):
        return TactLangMessage(self)
    
    def __repr__(self):
	rep = ''

	if self['actor']:
##            rep += 'sender'
            if type(self['actor']) is ListType:
                for actor in self['actor']:
                    if not type(actor) is StringType and actor != None:
                        actor = actor.name
                    rep += '; %s' % (actor)
            else:
                if not type(self['actor']) is StringType and self['actor']:
                    actor = self['actor'].name
                    rep += '; %s' % (actor)
                elif type(self['actor']) is StringType:
                    actor = self['actor']
                    rep += '; %s' % (actor)
                

##        if self['receiver']:
####            rep += ';receiver'
##            if type(self['receiver']) is ListType:
##                for actor in self['receiver']:
##                    if not type(actor) is StringType and actor != None:
##                        actor = actor.name
##                    rep += '; %s' % (actor)
##            else:
##                if not type(self['receiver']) is StringType and self['receiver']:
##                    receiver = self['receiver'].name
##                    rep += '; %s' % (receiver)
##                elif type(self['receiver']) is StringType:
##                    receiver = self['receiver']
##                    rep += '; %s' % (receiver)

        if self['addressee']:
##            rep += ';addressee'
            if type(self['addressee']) is ListType:
                for actor in self['addressee']:
                    if not type(actor) is StringType and actor != None:
                        actor = actor.name
                    rep += '; %s' % (actor)
            else:
                if not type(self['addressee']) is StringType and self['addressee']:
                    addressee = self['addressee'].name
                    rep += '; %s' % (addressee)
                elif type(self['addressee']) is StringType:
                    addressee = self['addressee']
                    rep += '; %s' % (addressee)

##        rep += ';sact_type'
        rep += '; %s' % (self['sact_type'])

        rep += '; %s' % (self['type'])
         
##        rep += ';factors'
##        rep += '; %s' % (self['attitude']['formality'] )
##        rep += '; %s' % (self['attitude']['politeness'] )
##        rep += '; %s' % (self['attitude']['detail'] )
##        rep += '; %s' % (self['attitude']['emphasis'] )

        if self['factors']:
            for factor in self['factors']:
                # Default rep of messages we can't yet pretty print
                if factor['topic'] == 'state':
                    substr = string.join(factor['lhs'],':')
                    try:
                        value = string.join(factor['rhs'],':')
                    except KeyError:
                        value = str(factor['value'])
                    rep += '; %s%s%s' % (substr,factor['relation'],value)
                elif factor['topic'] == 'observation':
                    rep += '; %s %s' % (factor['actor'],str(factor['action']))

      
	return rep[1:]

    def pretty(self):
        """Returns a more user-friendly string rep of this  message"""
	rep = ''
	for factor in self['factors']:
            if factor['topic'] == 'state':
                substr = ''
                if factor['lhs'][0] == 'entities':
                    entity = factor['lhs'][1]
                    if factor['lhs'][2] == 'state':
                        feature = factor['lhs'][3]
                        substr = 'the %s of %s' % (feature,entity)
                        try:
                            value = '%4.2f' % (float(factor['rhs'][0]))
                        except KeyError:
                            value = '%4.2f' % (factor['value'])
                if len(substr) == 0:
                    # Default rep of messages we can't yet pretty print
                    substr = string.join(factor['lhs'],':')
                    value = string.join(factor['rhs'],':')
                rep += '; %s %s %s' % (substr,factor['relation'],value)
            elif factor['topic'] == 'observation':
                rep += '; %s chose %s' % (factor['actor'],
                                          str(factor['action']))
        if self.mustAccept():
            rep += ' (force to accept)'
        elif self.mustReject():
            rep += ' (force to reject)'
	return rep[2:]
