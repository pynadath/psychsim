"""Various utility methods for use by other PsychSim classes"""

import copy
import string
import time
import sys
from types import *

from teamwork.math.Interval import Interval
from Debugger import *
from teamwork.action.PsychActions import *

def goalDiff(goalList1,goalList2):
    """Returns the difference in goal weights between two lists of
    goals of the form [(goal,weight),(goal,weight),...], where
    goal is either a PsychGoal object or a dictionary that is a
    suitable input to the PsychGoal constructor, and weight is a
    (possibly unnormalized) float"""
    goalDict = {}
    # First, figure out total weight (for appropriate scaling)
    normalization1 = 0.0
    for goal,weight in goalList1:
        if type(goal) is DictType:
            goal = PsychGoal(goal)
        normalization1 = normalization1 + weight
        goalDict[`goal`] = (weight,0.0)
    normalization2 = 0.0
    for goal,weight in goalList2:
        if type(goal) is DictType:
            goal = PsychGoal(goal)
        if goalDict.has_key(`goal`):
            goalDict[`goal`] = (goalDict[`goal`][0],weight)
        else:
            goalDict[`goal`] = (0.0,weight)
        normalization2 = normalization2 + weight
    # Add up normalized differences
    total = 0.0
    for weight1,weight2 in goalDict.values():
        total = total + pow(weight1/normalization1-weight2/normalization2,2)
    return total

def generateMessages(factorList):
    """Takes a list of factors and generates all possible messages
    (i.e., all possible combinations of those factors"""
    msgList = [{}]
    for factor in factorList:
	for msg in msgList[:]:
	    newMsg = copy.copy(msg)
	    newMsg[factor] = 1
	    msgList.append(newMsg)
    msgList.remove({})
    msgList.append(None)
    return msgList

def noisyOR(probabilities):
    """Takes a list of probability values and computes a noisy OR"""
    result = -1
    for prob in probabilities:
	result = result * (1.0-prob)
    return result

def act2dict(action,entities=[]):
    """Translates an action in string form into a structured
    dictionary representation of that same action (e.g.,
    'CLF-violence-to-UrbanPoor' becomes
    {'actor':CLF,'type':'violence','object':UrbanPoor}"""
    if not action:
        action = 'wait'
    if not isinstance(action,str):
        action = `str`
    components = string.split(action,'-')
    if len(components) < 2:
	# ???
	return {'type':action}
    elif len(components) < 3:
        # <actor>-<type>
        return {'actor':components[0],'type':components[1]}
    elif len(components) < 4:
	# <type>-to-<object>
	for obj in entities:
            try:
                if obj.name == components[2]:
                    break
            except AttributeError:
                pass
	else:
	    obj = components[2]
	return {'type':components[0],'object':obj}
    elif len(components) < 5:
	# <actor>-<type>-to-<object>
	for obj in entities:
	    if obj.name == components[3]:
		break
	else:
	    obj = components[3]
	return {'actor':components[0],'type':components[1],
		'object':obj}
    else:
        # <actor>-<command>-to-<object>-<action>
	for obj in entities:
	    if obj.name == components[3]:
		break
	else:
	    obj = components[3]
        actionStr = string.join(components[4:],'-')
        subAction = act2dict(actionStr,entities)
        subAction['string'] = actionStr
	return {'actor':components[0],'type':components[1],
                'object':obj,'action':subAction}

def dict2act(action):
    """Translates a structured dictionary representation of an action
    into a standardized string format (e.g.,
    {'actor':CLF,'type':'violence','object':UrbanPoor} becomes
    'CLF-violence-to-UrbanPoor'"""
    str = action['type']
    if action.has_key('object'):
	obj = action['object']
	if not type(obj) is StringType:
	    obj = obj.name
	str = str+'-to-'+obj
    if action.has_key('actor'):
	actor = action['actor']
	if not type(actor) is StringType:
	    actor = actor.name
	str = actor+'-'+str
    if action.has_key('action'):
        if action['action'].has_key('string'):
            str = str + '-' + action['action']['string']
        else:
            str = str + '-' + dict2act(action['action'])
    return str

def normalize(value):
    """Performs a floor and ceiling to keep the provided value within
    the range specified by the Interval class"""
    if value < Interval.FLOOR:
	return Interval.FLOOR
    elif value > Interval.CEILING:
	return Interval.CEILING
    else:
	return value

def forceFloat(value):
    """Tries to convert the specified value into a float; if unable,
    returns 0.0 (avoids nasty exceptions)"""
    try:
        return float(value)
    except ValueError:
        return 0.0

def createObservation(act):
    """Translates an action (in either string or dictionary form) into
    a properly formatted observation dictionary for use by COM-MTDP
    code"""
    obs = {'type':'observation','content':{}}
    if type(act) is StringType:
        obs['content'][act] = 'yes'
    else:
        obs['content'][`act`] = 'yes'
    return obs

def dict2str(dict,depth=-1):
    content = '{'
    for key in dict.keys():
        obj = dict[key]
        if type(obj) is FloatType:
            content += '\n\t%s: %5.3f' % (str(key),obj)
        elif type(obj) is StringType:
            content += '\n\t%s: %s' % (str(key),obj)
        elif type(obj) is InstanceType:
            content += '\n\t%s: %s' % (str(key),str(obj))
        elif isinstance(obj,Action):
            content += '\n\t%s: %s' % (str(key),str(obj))
        elif not type(obj) in [DictType,ListType,TupleType]:
            try:
                content += '\n\t%s: %s' % (str(key),str(obj.keys()))
            except AttributeError:
                content += '\n\t%s: %s' % (str(key),str(obj))
    if depth:
        substr = ''
        for key in dict.keys():
            obj = dict[key]
            if type(obj) is DictType:
                substr = substr + '\n' + key + ': ' + dict2str(obj,depth-1)
            elif type(obj) is ListType:
                substr = substr + '\n' + key + ': '
                for index in range(len(obj)):
                    entry = obj[index]
                    if type(entry) is DictType:
                        substr = substr + '\n\t' + `index` + '. ' + \
                                 dict2str(entry,depth-1)
                    else:
                        substr = substr + '\n\t' + `index` + '. ' + `entry`
        content += substr.replace('\n','\n\t')
    content += '}'
    return content
                
def debugger(level,str,debug):
    """Generic debugging statement that can handle three types of
    debug parameters: (1) Integer - prints string if debug >= level,
    (2) Tuple (debug,result) - appends string to result if debug >=
    level, and (3) List [debug,result,time] - if debug >= level, adds
    string to result along with time difference between now and
    provided time (side efffect: sets time to now)"""
    if type(debug) is TupleType:
        if debug[0] >= level:
            debug[1].append(str)
    elif type(debug) is ListType:
        if debug[0] >= level:
            try:
                lastTime = debug[2]
                newTime = time.time()
                if lastTime:
                    diff = int((newTime-lastTime)*1000.0)
                    if diff > 0:
                        str = str + ' ('+`diff`+' ms)'
                debug[2] = newTime
            except IndexError:
                pass
            debug[1].append(str)
    else:
        if debug >= level:
            print str

def load(name):
    """Takes a file name (string) and reads a pickled Python object
    from the file and returns it"""
    import pickle
        
    file = open(name,'rb')
    try:
        obj = pickle.load(file)
    except AttributeError,e:
        # This is an incredibly bad way of doing this
        items = string.split(str(e))
        module = items[len(items)-1]
        module = module[1:len(module)-1]
        raise NameError,'Unknown module: %s' % (module)
    file.close()
    return obj

def extractEntity(name,entities):
    try:
        entity = entities[name]
        return entity
    except KeyError:
        print 'Unknown entity:',name
        return None

def extractAction(cmd,entities,format,debug=Debugger(),actClass=None):
    action = {}
    for item in format:
        # Check whether next item is required
        if item[1]:
            # If nothing left to parse then fail
            if len(cmd) == 0:
                return None
        # If nothing left to parse, end
        if len(cmd) == 0:
            break
        # We have an item to parse
        if item[0] in ['actor','object']:
            entity = extractEntity(cmd[0],entities)
            if not entity:
                # Unable to find the specified entity
                if item[1]:
                    # If this was a required item, then fail
                    return None
                else:
                    # Otherwise, end
                    break
            # Stick the found entity into the action slot
            action[item[0]] = entity.name
        elif item[0] == 'type':
            # Check for special "policy" symbol
            if cmd[0] == 'policy':
                act,explanation = action['actor'].applyPolicy(debug=debug)
                debug.message(1,'Policy: '+`action`)
                return act
            else:
                action[item[0]] = cmd[0]
                if cmd[0] == 'command':
                    format += [('type',1),('object',None)]
        else:
            action[item[0]] = cmd[0]
        # Go on to next item in format list
        cmd = cmd[1:]
    actClass = entities.members()[0].actionClass
    return actClass(action)
