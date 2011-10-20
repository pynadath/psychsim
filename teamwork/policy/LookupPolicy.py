"""Reactive policies as conditionS{->}action rules"""
import copy
import re
import string

from generic import *

from teamwork.action.PsychActions import *
from teamwork.math.Interval import *
from teamwork.utils.Debugger import *
from teamwork.agent.Agent import Agent
#from teamwork.examples.TactLang.TactLangMessage import TactLangMessage

##def testObservation(act,entry):
##    """Returns true iff the action matches the LHS entry"""
##    for key in act.fields:
##        if entry.has_key(key) and entry[key]:
##            if isinstance(act[key],str):
##                if entry[key] != act[key]:
##                    # Mismatch
##                    break
##            elif isinstance(act[key],Agent):
##                if entry[key] != act[key].name:
##                    # Mismatch
##                    break
##            elif act[key]:
##                # HACK! HACK! HACK!
##                if key == 'amount':
##                    if not act[key] in str2Interval(entry[key]):
##                        break
##                else:
##                    break
##    else:
##        # Successful match
##        return 1
##    return 0

## mei 09/27/05
def testObservation(act,entry):
    """Returns true iff the action matches the LHS entry"""

    for key in entry.keys():

        debug=0
        try:
            if entry['sact_type'] == 'accept':
                pass
##                debug=1
        except:
            pass

##        debug = 1
        if key in ['depth' ,'action','class','value',\
                    'attitude','command','performative','force','_observed','_unobserved']:
            continue

        if entry[key] == 'any':
            continue

        if not act.has_key(key):
            if key in ['lhs','rhs'] and act['factors']:
                pass
            elif key in ['sender','actor'] and (act.has_key('sender') or act.has_key('actor')):
                pass
            elif key in ['receiver','object'] and (act.has_key('receiver') or act.has_key('object')):
                pass
            else:
                if debug ==1:
                    print 'act does not have the key ', key
                break
        
        
        if key == 'lhs':
            res = 0
            for factor in act['factors']:
##                print 'lhs factor ',factor
                try:
                    if isinstance(entry[key],str):
                        tmp = factor['lhs'][1]+'_'+factor['lhs'][3]
                        if string.strip(entry[key]) == string.strip(tmp):
                            res =1
                        else:
                            if debug ==1:
                                print 'lhs not match    '
                                print string.strip(tmp), type(string.strip(tmp))
                                print string.strip(entry[key]), type(string.strip(entry[key]))
##                                print entry[key] == tmp
##
##                                for i in range(len(string.strip(entry[key]))):
##                                    if string.strip(entry[key])[i] == string.strip(tmp)[i]:
##                                        pass
##                                    else:
##                                        print string.strip(entry[key])[i], string.strip(tmp)[i]
                                
                                
                                               
                            pass
                    elif type (entry[key]) == ListType:
                        tmp = factor['lhs']
                        if entry[key] == tmp:
                            res =1
                        else:
                            if debug ==1:
                                print 'lhs not match    '
                                print string.strip(tmp), type(string.strip(tmp))
                                print string.strip(entry[key]), type(string.strip(entry[key]))
                                print entry[key] == tmp
                            pass

                except:
                    pass
            if res == 0:
                break

        elif key == 'rhs':
            res = 0
            for factor in act['factors']:
##                print 'rhs factor ',factor
                try:
                    if isinstance(entry[key],str):
                        if len (factor['rhs']) == 1:
                            tmp = float(factor['rhs'][0])
                        else:
                            tmp = (float(factor['rhs'][0])+float(factor['rhs'][1]))/2
                        if float(entry[key]) == tmp:
                            res =1
##                            print 'rhs matched'
                        else:
                            if debug ==1:
                                print 'rhs not match'
                                print tmp, float(entry[key])
                            pass
                     
                except:
                    pass
            if res == 0:
                break
            
        elif key == 'sender':
            if act.has_key('sender'):
                if entry['sender'] == act['sender']:
                    continue
            elif act.has_key('actor'):
                if entry['sender'] == act['actor']:
                    continue
            if debug ==1:
                print 'sender doe not match '
            break
        
        elif key == 'actor':
            if act.has_key('sender'):
                if entry['actor'] == act['sender']:
                    continue
            elif act.has_key('actor'):
                if entry['actor'] == act['actor']:
                    continue
            if debug ==1:
                print 'sender does not match '
            break
            
        elif key in ['addressee']:
            if type(entry['addressee']) == ListType:
                if act['addressee'] == entry['addressee'] or act['addressee'] in entry['addressee']:
                    continue
                else:
                    if debug ==1:
                        print act['addressee'], entry['addressee']
                    break
            elif type(act['addressee']) == ListType:
                if entry['addressee'] in act['addressee']:
                    continue
                else:
                    break
            else:
                if debug ==1:
                    print 'addressee doe not match '
                break

                
        elif isinstance(act[key],str):
            
            if entry[key] != act[key]:
                if debug ==1:
                    print 'Mismatch ', key, entry[key], act[key]
                # Mismatch
                break
        elif isinstance(act[key],Agent):
            if entry[key] != act[key].name:
                # Mismatch
                break
        else:          
            break


    else:
        # Successful match
        return 1
    return 0

class LookupPolicy(Policy):
    """Class for representing a strictly reactive policy

    Each entry is represented as a dictionary:
    >>> {'class':<cls>, 'action':<action>, ... }
    The action can be passed in as a dictionary, which is then
    converted into the appropriate Action subclass.  The remaining
    structure of the entry depends on the value of <cls>, as follows:
    
       - I{default}: no other entries.  Rules of this class always fire
    """
    def __init__(self,entity,actions=[],span=1):
	Policy.__init__(self,actions)
	self.entries = []
        self.entity = entity
        self.span = span

    def matchAnswer(self,state,action):
        obsList = state.getObservations()
        for index in range(len(obsList)):
            lastObs = obsList[index]
            for actor,actList in lastObs.items():
                for act in actList:
                    if act['sact_type']=='enquiry':
                        action['factors']=[]
                        action['factors'].append(act['factors'][0])

                        try:
                            action['factors'][0]['value']=state.getBelief(act['factors'][0]['lhs'][1],act['factors'][0]['lhs'][3])
                        except:
                            action['factors'][0]['value'][0]=-1
                            action['factors'][0]['value'][1]=1
                        try:
                            action['factors'][0]['rhs'][0]=str(action['factors'][0]['value']['lo'])
                            action['factors'][0]['rhs'][1]=str(action['factors'][0]['value']['hi'])
                        except:
##                                            print type(msg['factors'][0]['value'])
                            action['factors'][0]['rhs']=str(action['factors'][0]['value'])

                        return 

    
    def execute(self,state,choices=[],history=None,debug=Debugger(),explain=None):
        # The basic explanation structure for a lookup-specified
        # action is always the following
        explanation = {'value':None,
                       'decision':None,
                       'actor':self.entity.name,
                       'effect':{},
                       'breakdown':[],
                       }
        # Test against each of the entries in the lookup table
        for entry in self.entries:
            debug.message(1,'\tConsidering entry: '+`entry`)
            result = self.testCondition(state,entry,debug)
            if result:
                # We match the trigger of this particular entry
##                if len(entry['action']) == 0 or \
##                       isinstance(entry['action'][0], TactLangMessage) or \
##                       len(choices) == 0 or entry['action'] in choices:
                    # The RHS is one of our available options
                    debug.message(5,'Matched.')
                    decision = copy.deepcopy(entry['action'])

##                    if decision[0]['sact_type'] == 'inform' :
##                        self.matchAnswer (state, decision[0])
                        
                    explanation['breakdown'].append({'entry':entry,
                                                     'actor':self.entity.name,
                                                     'decision':decision,
                                                     'result':result})
                    explanation['decision'] = decision
                    break
        debug.message(8,'Lookup table match on: %s' \
                      % (`explanation['decision']`))
        return explanation['decision'],explanation

    def actionValue(self,state,actStruct,debug=Debugger()):
        """Return some quantified value of performing action"""
        actStr = str(actStruct)
        myAction,explanation = LookupPolicy.execute(self,state=state,
                                                    debug=debug)
        if `myAction` == actStr:
            # This is the exact action generated by the policy
            debug.message(3,'Exact match')
            return 1.0,explanation
        # Otherwise, identify how many entries generate this action
        value = 0.0
        explanation['breakdown'] = []
        for entry in self.entries:
            if `entry['action']` == actStr:
                explanation['breakdown'].append(entry)
                value = value + 1.0
        debug.message(3,'Number of entries with action '+actStr+': '+`int(value)`)
        try:
            value = value / float(len(self.entries))
        except ZeroDivisionError:
            value = 0.0
        return value,explanation
                    
    def testCondition(self,state,entry,debug=Debugger):
        if entry['class'] == 'observation':
            # This entry pertains to a specific observation, so
            # identify most recent observations and check whether
            # they match the specified condition (LHS)
            debug.message(3,'\t\tTesting condition: %s' % `entry`)
            try:
                depth = entry['depth']
            except KeyError:
                depth = 1
            obsList = state.getObservations()
            for index in range(len(obsList)):
                lastObs = obsList[index]
                for actor,actList in lastObs.items():
                    for act in actList:
                        debug.message(3,'\t\t\tObservation: %s' % `act`)
                        if testObservation(act,entry):
                            return 1
                        
                        if depth == -1:
                            if entry['sender'] == act ['sender'] or entry['sender'] == act ['actor'] :
                                if act['sact_type'] != 'wait':
                                    depth = 0
                                    break
                            
                            
                    if depth >= 1:
                        depth = depth - 1
                else:
                    # A received message
                    pass
                if depth == 0:
                    # We have now examined the maximum number of
                    # observations specified
                    debug.message(1,'\t\tNo such observation')
                    break
        elif entry['class'] == 'belief':
            # This entry pertains to some (possibly nested)
            # belief, so we dig down into the beliefs until we
            # find the specified belief and then verify whether
            # its value matches to the specified condition (LHS)
            try:
                currentBelief = state.getNestedBelief(entry['keys'])
            except KeyError:
                # No such belief
                debug.message(1,'\t\tNo relevant belief value')
                return None
            # OK, we've found the specified belief, so let's check 
            # its value
            debug.message(1,'\t\tRelevant belief value: '+`currentBelief`)
            return currentBelief in entry['range']
        elif entry['class'] == 'combine':
            try:
                lBelief = state.getNestedBelief(entry['left keys'])
                rBelief = state.getNestedBelief(entry['right keys'])
            except KeyError:
                # No matching beliefs
                return None
            cmd = 'Interval('+`lBelief['lo']`+','+`lBelief['hi']`+')' + \
                  entry['operator'] + \
                  'Interval('+`rBelief['lo']`+','+`rBelief['hi']`+')'
            try:
                value = eval(cmd,{'Interval':Interval},{})
            except:
                raise TypeError,"Unable to perform combination: %s" % cmd
            debug.message(1,'\t\tRelevant belief value: '+`value`)
            return value in entry['range']
        elif entry['class'] == 'conjunction':
            # For a conjunction, each and every clause must hold for the
            # overall rule to hold
            for clause in entry['clauses']:
                if not self.testCondition(state,clause,debug):
                    debug.message(1,'\t\tClause failure: '+`clause`)
                    return None
            else:
                debug.message(1,'\t\tSuccessful match')
                return 1
        elif entry['class'] == 'negation':
            # For a negation, return the opposite of the contained clause
            if self.testCondition(state,entry['clause'],debug):
                debug.message(1,'\t\tNegation of successful match')
                return None
            else:
                debug.message(1,'\t\tNegation of failed match')
                return 1
        elif entry['class'] == 'default':
            # Default rules always match
            return 1
        else:
            raise TypeError,'illegal entry class: '+entry['class']
	return None

    def extend(self,entry,actionClass=None,entity=None):
        """Extends the current policy table to include the given entry

        The entry can be either a string or a list of policy entry
        dictionaries or a single policy entry dictionary.  The
        optional actionClass argument (default: Action) specifies the
        base class for the RHS"""
        if isinstance(entry,list):
            newEntries = entry
        elif isinstance(entry,dict):
            newEntries = [entry]
        else:
            # Assume to be string
##            print 'WARNING: Use dictionary specification of policies'
            newEntries = self.parseEntry(entry,actionClass)
        # Convert RHS entries to the given actionClass
        for entry in newEntries[:]:
            if not isinstance(entry['action'],list):
                entry['action'] = [entry['action']]
            for index in range(len(entry['action'])):
                action = entry['action'][index]

                if not isinstance (action, Action):
                    action = actionClass(action)
                    
                action['actor'] = entity.name
                obj = action['object']
                if entity:
                    objList = entity.instantiateName(obj)
                    if len(objList) > 0:
                        action['object'] = objList[0]
                entry['action'][index] = action
        # Add new entries to end of table
        self.entries += newEntries
        return newEntries

    def parseEntry(self,entry,actionClass=None):
        """Takes a string representation of a lookup entry and returns
        the corresponding policy entry structure"""
        try:
            lhs,rhs = string.split(entry,'->')
        except ValueError:
            print entry
            return
        lhs = string.strip(lhs)
        if not actionClass:
            actionClass = Action
##        mei to comply with using messages as actions
        if rhs.find('{')>-1:
            rhs = actionClass(eval(string.strip(rhs),{}))
        else:
            rhs = TactLangMessage(string.strip(rhs))
                                  
	keys = string.split(lhs)
        lhs = self.parseLHS(keys[1:],keys[0])
        entries = []
        for (entry,substitution) in lhs:
            entry['action'] = copy.deepcopy(rhs)
            for key in rhs.keys():
                if type (rhs[key]) == ListType:
                    rhs[key] =rhs[key][0]
                if key == 'command':
                    for subkey in rhs[key].keys():
                        if isinstance(rhs[key][subkey],str):
                            if substitution.has_key(rhs[key][subkey]):
                                value = substitution[rhs[key][subkey]]
                                entry['action'][key][subkey] = value
                            elif self.entity.relationships.has_key(rhs[key][subkey]):
                                value = self.entity.relationships[rhs[key][subkey]][0]
                                entry['action'][key][subkey] = value
                            elif rhs[key][subkey] == 'self':
                                entry['action'][key][subkey] = self.entity.name
                elif isinstance(rhs[key],str):
                    if substitution.has_key(rhs[key]):
                        value = substitution[rhs[key]]
                        entry['action'][key] = value
                    elif self.entity.relationships.has_key(rhs[key]):
                        value = self.entity.relationships[rhs[key]][0]
                        entry['action'][key] = value
                    elif rhs[key] == 'self':
                        entry['action'][key] = self.entity.name
            entries.append(entry)
        return entries
    
    def parseLHS(self,keys,entryType):
        entries = [({'class':entryType},{})]
	if entryType == 'observation':
	    # Sample observation policy string:
	    # "observation depth 3 actor Paramilitary type violence
	    #    object UrbanPoor -> violence-against-Paramilitary"
	    # (i.e., triggered if, within past 3 steps, the
	    # paramilitary have committed violence against UrbanPoor)
	    for index in range(0,len(keys),2):
		key = keys[index]
		value = keys[index+1]
                for entry,sub in entries[:]:
                    entries.remove((entry,sub))
                    try:
                        entry[key] = int(value)
                        if key == 'depth':
                            entry[key] = entry[key] * self.span
                        entries.append((entry,sub))
                    except ValueError:
                        if value == 'self':
                            entry[key] = self.entity.name
                            entries.append((entry,sub))
                        elif self.entity.relationships.has_key(value):
                            for other in self.entity.relationships[value]:
                                newSub = copy.copy(sub)
                                newSub[value] = other
                                newEntry = copy.deepcopy(entry)
                                newEntry[key] = other
                                entries.append((newEntry,newSub))
                        elif key == 'command':
                            command = self.choices[0].__class__(value)
                            if self.entity.relationships.has_key(command.object):
                                for other in self.entity.relationships[command.object]:
                                    newSub = copy.copy(sub)
                                    newSub[command.object] = other
                                    newEntry = copy.deepcopy(entry)
                                    newEntry[key] = copy.copy(command)
                                    newEntry[key].object = other
                                    entries.append((newEntry,newSub))
                        else:
                            entry[key] = value
                            entries.append((entry,sub))
	elif entryType == 'message':
	    # Sample message policy string:
	    # "message depth 3 sender CortinaGov content command;...
            # -> violence-against-Paramilitary"
	    # (i.e., triggered if, within past 3 steps, the CortinaGov
	    # have issued a command)
	    for index in range(0,len(keys),2):
		key = keys[index]
		value = keys[index+1]
                for entry in entries[:]:
                    entries.remove(entry)
                    try:
                        entry[key] = int(value)
                        entries.append(entry)
                    except ValueError:
                        if self.entity.relationships.has_key(value):
                            for other in self.entity.relationships[value]:
                                entry[key] = other
                                entries.append(copy.copy(entry))
                        else:
                            entry[key] = value
                            entries.append(entry)
	elif entryType == 'belief':
	    # Sample belief policy string:
	    # "belief entities Psyops state power 0.0 0.4
            #  -> violence-against-Psyops"
	    # (i.e., triggered if beliefs about Psyops' power in [0.0,0.4])
            keyList = []
            for key in keys[:len(keys)-2]:
                if key == 'self':
                    keyList.append(self.entity.name)
                else:
                    keyList.append(key)
            entries[0][0]['keys'] = keyList
                    
            entries[0][0]['range'] = Interval(float(keys[len(keys)-2]),
                                      float(keys[len(keys)-1]))
            entry,sub = entries.pop()
            for other,keySub in self.instantiateKeys(entry['keys']):
                newSub = copy.copy(sub)
                for key in keySub.keys():
                    newSub[key] = keySub[key]
                entry['keys'] = other
                entries.append((copy.copy(entry),newSub))
	elif entryType == 'combine':
	    # Sample combination policy string:
	    # "combine entities Psyops state power - entities
            #    Paramilitary state power 0.0 0.4 ->
            #    violence-against-Psyops"
	    # (i.e., triggered if beliefs about Psyops' power -
            # paramilitary's power in [0.0,0.4])
            try:
                index = keys.index('-')
                entries[0][0]['operator'] = '-'
            except ValueError:
                index = keys.index('+')
                entries[0][0]['operator'] = '+'
	    entries[0][0]['left keys'] = keys[:index]
            entries[0][0]['range'] = Interval(float(keys[len(keys)-2]),
                                      float(keys[len(keys)-1]))
            for entry,sub in entries[:]:
                entries.remove((entry,sub))
                for keySet,sub in \
                        self.instantiateKeys(entry['left keys']):
                    entry['left keys'] = keySet
                    entries.append((copy.deepcopy(entry),sub))
            for entry,oldsub in entries[:]:
                entries.remove((entry,oldsub))
                entry['right keys'] = keys[index+1:len(keys)-2]
                for keySet,sub in \
                        self.instantiateKeys(entry['right keys']):
                    # Check for conflict with left key substitution
                    for key,val in oldsub.items():
                        if sub.has_key(key) and sub[key] != val:
                            break
                        else:
                            sub[key] = val
                    else:
                        entry['right keys'] = keySet
                        entries.append((copy.deepcopy(entry),sub))
        elif entryType == 'conjunction':
            # Sample conjunction policy string:
            # "conjunction observation depth 3 actor Paramilitary
            #   type violence object UrbanPoor & belief entities Psyops
            #   state power 0.0 0.4 -> violence-against-Psyops"
            clauses = string.split(string.join(keys[:]),'&')
            entries[0][0]['clauses'] = []
            for str in clauses:
                keys = string.split(str)
                for entry,sub in entries[:]:
                    entries.remove((entry,sub))
                    for clause,clauseSub in \
                            self.parseLHS(keys[1:],keys[0]):
                        newSub = copy.copy(sub)
                        # First, check whether this clause's
                        # substitution is consistent with substitution
                        # so far
                        for key in clauseSub.keys():
                            if sub.has_key(key) and \
                               sub[key] != clauseSub[key]:
                                break
                            else:
                                newSub[key] = clauseSub[key]
                        else:
                            # Consistent substitution
                            newEntry = copy.deepcopy(entry)
                            newEntry['clauses'].append(clause)
                            entries.append((newEntry,newSub))
        elif entryType == 'negation':
            # Sample negation policy string:
            # "negation observation depth 3 actor Paramilitary
            #   type violence object UrbanPoor -> violence-against-Psyops"
            for entry,sub in entries[:]:
                entries.remove((entry,sub))
                for clause,clauseSub in self.parseLHS(keys[1:],keys[0]):
                    newSub = copy.copy(sub)
                    # First, check whether this clause's
                    # substitution is consistent with substitution
                    # so far
                    for key in clauseSub.keys():
                        if sub.has_key(key) and sub[key] != clauseSub[key]:
                            break
                        else:
                            newSub[key] = clauseSub[key]
                    else:
                        # Consistent substitution
                        newEntry = copy.deepcopy(entry)
                        newEntry['clause'] = clause
                        entries.append((newEntry,newSub))
        elif entryType == 'default':
            # Sample default string:
            # "default -> wait"
            pass
        else:
            raise TypeError,'illegal entry class: '+entryType
        return entries
                    
    def instantiateKeys(self,keys):
        """Takes a list of strings and substitutes any specific
        entities into generic relation labels"""
        keyList = [([],{})]
        for key in keys:
            if self.entity.relationships.has_key(key):
                for keySet,sub in keyList[:]:
                    keyList.remove((keySet,sub))
                    for entity in self.entity.relationships[key]:
                        newKeys = copy.copy(keySet)
                        newSub = copy.copy(sub)
                        newKeys.append(entity)
                        newSub[key] = entity
                        keyList.append((newKeys,newSub))
            else:
                for keySet,sub in keyList:
                    keySet.append(key)
        return keyList
        
    def __str__(self):
 	return str(self.entries)

    def __contains__(self,value):
        """Returns true if the specified value matches an entry in
        this policy"""
        entries = self.parseEntry(value)
        for entry in entries:
            if not entry in self.entries:
                return False
        return True
