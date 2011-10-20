from teamwork.math.Interval import Interval
from teamwork.utils.PsychUtils import *

DYNAMICS = 'object'
#DYNAMICS = 'function'

class BaseDynamics:
    """Class of objects that represent the dynamics of a specific
    state/belief feature in the simulation"""

    def __init__(self,args=None):
        if args is None:
            args = {}
        self.args = args
		
    def apply(self,entity,value,action,world,debug=0):
        """Takes an entity with the specified initial value for the
        feature of interest and returns a new value in response to the
        specified action being taken within the specified world
        context (in the form of a dictionary of entity objects,
        indexed by entity name)"""
        return value

    def instantiate(self,entity,action):
        return self
    
    def invert(self,entity,value,action,world,debug=0):
        return value

    def getIncrement(self):
        """Returns the incremental delta by which this dynamics
        function adjusts values; this delta is stored in the
        'increment' field of the 'args' attribute of this object; if
        none is specified, defaults to 0.1"""
        try:
            return self.args['increment']
        except KeyError:
            return 0.1

    def reset(self):
        """Deletes any stored information (e.g., partial results)
        before beginning dynamics computation (should be
        overridden by subclass)"""
        pass
    
def genericDynamics(entity,actor,object,oldValue,actParam,objParam):
	if entity.name == object.name:
            return normalize(oldValue-objParam)
	elif entity.name == actor.name:
	    return normalize(oldValue+actParam)
	else:
	    return oldValue

class FunDynamics(BaseDynamics):
    def apply(self,entity,value,action,world,debug=Debugger()):
        actor = action['actor']
        if type(actor) is InstanceType:
            actor = actor.name
        if action['type'][:6] == 'moveTo':
            destination = action['type'][6:]
            origin = world[actor].getState('floor')
            if entity == actor:
                pass
            elif entity.getState('floor') == origin:
                pass
            elif entity.getState('floor') == destination:
                pass
            else:
                return value
        else:
            return value
        
class SupportDynamics(BaseDynamics):
    def __init__(self,args={}):
        BaseDynamics.__init__(self,args)
        self.results = {}
    
    def apply(self,entity,value,action,world,debug=Debugger()):
        try:
            # move up a level to get supporter ?
            supporter = world[entity].parent
        except KeyError:
            return value
        actor = action['actor']
        if type(actor) is InstanceType:
            actor = actor.name
##        if entity != actor or actor == self.args['entity']:
        if actor == self.args['entity']:
            return value
        debug.message(8,'Computing support of %s for %s...' \
                      % (supporter.ancestry(),actor))
        if not self.results.has_key(actor):
            self.results[actor] = supporter.actionSupport(action,debug)
        delta = self.results[actor]
        if entity != actor:
            try:
                scale = supporter.getEntity(actor).getSupport(entity).mean()
            except KeyError:
                scale = 0.0
##                # A bit of a hack, to use parent's beliefs about the
##                # support if I don't have any of my own
##                try:
##                    scale = supporter.parent.getEntity(actor).getSupport(entity).mean()
##                    scale = scale / 1.5
##                except KeyError:
##                    scale = 0.0
##                except AttributeError:
##                    scale = 0.0
            delta = delta * scale
        if type(value) is FloatType:
            value = normalize(value+delta)
        else:
            value += delta
        debug.message(8,'New support value = %s' % (`value`))
        return value

    def reset(self):
        for key in self.results.keys():
            del self.results[key]
            
# Dynamics functions
def violence2power(entity,actor,victim,oldPower,invert=None):
    """Dynamics function for change in power due to act of violence"""
    if invert:
        if entity.name == victim.name:
            return normalize(oldPower+0.1)
        elif entity.name == actor.name:
            return normalize(oldPower-0.1)
        else:
            return oldPower
    else:
        if entity.name == victim.name:
            return normalize(oldPower-0.1)
        elif entity.name == actor.name:
            return normalize(oldPower+0.1)
        else:
            return oldPower

def violence2hardship(entity,actor,victim,oldHardship,invert=None):
    """Dynamics function for change in hardship due to act of violence"""
    if entity.name == victim.name:
        if invert:
            # Do something clever
            pass
        else:
            return delta(actor,oldHardship,'power') + decay(oldHardship)
    else:
        return decay(oldHardship,invert)

decayRate = 0.9

def decay(value,invert=None):
    if invert:
	return value / decayRate
    else:
	return value * decayRate

def delta(actor,oldValue,feature):
    try:
	return ((1.0-decayRate)*actor.getState(feature))/oldValue
    except ZeroDivisionError:
	return ((1.0-decayRate)*actor.getState(feature))/0.1

def nullDynamics(entity,actor,object,oldValue):
    return oldValue
