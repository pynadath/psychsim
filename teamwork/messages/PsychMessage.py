"""Class definition of messages
@author: David V. Pynadath <pynadath@isi.edu>
"""

import string
from types import *
from xml.dom.minidom import *

from teamwork.math.Interval import Interval
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.probability import Distribution
from teamwork.action.PsychActions import *

class Message(Action):
    """Subclass of L{Action} corresponding to messages, which are realized as attempts to modify the beliefs of others
    @cvar acceptString: the flag indicating that a hearer should be forced to believe this message
    @cvar rejectString: the flag indicating that a hearer should be forced to disbelieve this message
    @type acceptString,rejectString: C{str}
    @cvar fields: the available keys for messages of this class (unless otherwise noted, the value under each key is a string)
       - I{sender}: the agent sending the message (i.e., the I{actor})
       - I{receiver}: the I{sender}'s intended hearer (i.e., the I{object})
       - I{type}: the action type (default is C{_message})
       - I{performative}: as defined by ACL conventions (default is C{tell})
       - I{command}: the action that the I{sender} is commanding the I{receiver} to perform (probably doesn't work)
       - I{force}: dictionary (over receivers) of flags indicating whether acceptance/rejection of the message should be forced.  For each name key, if the value is C{None}, then the agent decides for itself; if L{acceptString}, then theagent must believe the message; if L{rejectString}, then the agent must reject the message.  You should not set this field's value directly; rather, use the L{forceAccept}, L{forceReject}, L{mustAccept}, and L{mustReject} methods as appropriate
       - I{factors}: the content of the message, in the form of a list of dictionaries, specifying the intended change to individual beliefs
    """
    fields = {
        # Redundant fields between actions and messages
        'actor':{},'sender':{},
        'object':{},'receiver':{},
        # Same as in actions
        'type':{},'command':{},
        # Unique to messages
        'factors':{},'performative':{},'force':{},
        '_observed':{},'_unobserved':{},
        # The implied belief change of this message content
        'matrix':{},
        # Flags indicating whether acceptance/rejection is forced
        }
    acceptString = 'accept'
    rejectString = 'reject'
    
    def __init__(self,arg={}):
        if isinstance(arg,str):
            Action.__init__(self)
            self.extractFromString(arg)
        else:
            Action.__init__(self,arg)
        if not self['type']:
            self['type'] = '_message'
        # Flag (used by internal Entity methods) to force the
        # acceptance of this message...useful for what-if reasoning
        if not self.has_key('force'):
            self['force'] = {}
        if not self.has_key('performative'):
            self['performative'] = 'tell'

    def __setitem__(self,index,value):
        Action.__setitem__(self,index,value)
        if index == 'actor':
            Action.__setitem__(self,'sender',value)
        elif index == 'sender':
            Action.__setitem__(self,'actor',value)
        elif index == 'object':
            Action.__setitem__(self,'receiver',value)
        elif index == 'receiver':
            Action.__setitem__(self,'object',value)
            
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
        print 'WARNING: You should migrate to dictionary spec of messages'
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
        
    def force(self,agent='',value=None):
        """
        @param value: if a positive number or equals the 'acceptString'
        attribute, then sets the message to force acceptance; if value
        is a negative number of equals the 'rejectString' attribute,
        then sets the message to force rejection; otherwise, the
        acceptance of this message is left up to the receiver
        @param agent: the agent whose acceptance is being forced.  If the empty string, then all agents are forced (the default)
        @type agent: str
        """
        if value:
            if type(value) is StringType:
                if value == self.acceptString:
                    self['force'][agent] = self.acceptString
                elif value == self.rejectString:
                    self['force'][agent] = self.rejectString
                else:
                    raise TypeError,'Unknown forced value: '+`value`
            elif value > 0:
                    self['force'][agent] = self.acceptString
            else:
                self['force'][agent] = self.rejectString
        else:
            self['force'][agent] = None

    def forceAccept(self,agent=''):
        """Sets the message to force acceptance by the receiver
        @param agent: the agent whose acceptance is being forced.  If the empty string, then all agents are forced (the default)
        @type agent: str
        """
        self.force(agent,self.acceptString)

    def forceReject(self,agent=''):
        """Sets the message to force rejection by the receiver
        @param agent: the agent whose acceptance is being forced.  If the empty string, then all agents are forced (the default)
        @type agent: str
        """
        self.force(agent,self.rejectString)

    def mustAccept(self,agent=''):
        """
        @param agent: the agent whose forcing is being tested.  If the empty string, then the test is over all agents (the default)
        @type agent: str
        @return: true iff this message has been set to force
        acceptance by the specified receiver
        @rtype: boolean
        """
        try:
            return self['force'][agent] == self.acceptString
        except KeyError:
            try:
                return self['force'][''] == self.acceptString
            except KeyError:
                return False

    def mustReject(self,agent=''):
        """
        @param agent: the agent whose forcing is being tested.  If the empty string, then the test is over all agents (the default)
        @type agent: str
        @return: true iff this message has been set to force
        rejection by the receiver
        @rtype: boolean"""
        try:
            return self['force'][agent] == self.rejectString
        except KeyError:
            try:
                return self['force'][''] == self.rejectString
            except KeyError:
                return False

    def __cmp__(self,other):
        if len(self['factors']) == len(other['factors']):
            for factor in self['factors']:
                if not factor in other['factors']:
                    return -1
            else:
                return 0
        else:
            return -1
        
    def __copy__(self):
        return Message(self)

    def __xml__(self):
        doc = Action.__xml__(self)
        # Record who is forced to do what
        node = doc.createElement('force')
        doc.documentElement.appendChild(node)
        for name in self['force'].keys():
            if self.mustAccept(name):
                child = doc.createElement(self.acceptString)
                node.appendChild(child)
                child.setAttribute('agent',name)
            elif self.mustReject(name):
                child = doc.createElement(self.rejectString)
                node.appendChild(child)
                child.setAttribute('agent',name)
        # Record factors
        for factor in self['factors']:
            node = doc.createElement('factor')
            doc.documentElement.appendChild(node)
            node.setAttribute('topic',factor['topic'])
            if factor.has_key('matrix'):
                node.appendChild(factor['matrix'].__xml__().documentElement)
        return doc

    def parse(self,doc):
        Action.parse(self,doc)
        if doc.nodeType == doc.DOCUMENT_NODE:
            element = doc.documentElement
        else:
            element = doc
        self['factors'] = []
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'factor':
                    factor = {'topic':str(child.getAttribute('topic'))}
                    if child.firstChild:
                        distribution = Distribution()
                        distribution.parse(child.firstChild,KeyedMatrix)
                        factor['matrix'] = distribution
                    self['factors'].append(factor)
            child = child.nextSibling
        return self
    
    def __str__(self):
        return self.pretty()

    def pretty(self,query=None):
        """
        @return: a more user-friendly string rep of this  message"""
        rep = ''
        for factor in self['factors']:
            if factor['topic'] == 'state':
                substr = ''
                if factor['lhs'][0] == 'entities':
                    entity = factor['lhs'][1]
                    if factor['lhs'][2] == 'state':
                        feature = factor['lhs'][3]
                        if query:
                            substr = 'What is the'
                        else:
                            substr = 'The'
                        substr += ' %s of %s' % (feature,entity)
                        if isinstance(factor['value'],Distribution):
                            if len(factor['value']) == 1:
                                value = str(factor['value'].domain()[0])
                            else:
                                value = str(factor['value'])
                        else:
                            try:
                                value = '%4.2f' % (float(factor['rhs'][0]))
                            except KeyError:
                                value = str(factor['value'])
                if len(substr) == 0:
                    # Default rep of messages we can't yet pretty print
                    substr = string.join(factor['lhs'],':')
                    value = string.join(factor['rhs'],':')
                if query:
                    substr += '?'
                rep += '; %s' % (substr)
                if not query:
                    rep += ' %s %s' % (factor['relation'],value)
            elif factor['topic'] == 'observation':
                factors = map(lambda a:'%s to %s' % (a['type'],a['object']),
                              factor['action'])
                actType = string.join(factors,', ')
                if query:
                    rep += '; Who did %s?' % (actType)
                else:
                    rep += '; %s chose to %s' % (factor['actor'],actType)
            elif factor['topic'] == 'model':
                substr = ' is %s' % (factor['value'])
                entity = string.join(factor['entity'],' believes ')
                rep += '; %s %s' % (entity,substr)
            else:
                raise NotImplementedError,'No pretty printing for messages of type %s' % (factor['topic'])
        if self.mustAccept():
            rep += ' (force to accept)'
        elif self.mustReject():
            rep += ' (force to reject)'
        return rep[2:]
