import copy
import string
import sys
import time
from types import *

from support import *
from stereotypes import *
from consistency import *
from GoalBased import *
from DefaultBased import *
from MemoryAgent import *

from teamwork.math.probability import *
from teamwork.utils.PsychUtils import dict2str
from teamwork.action.PsychActions import *
from teamwork.messages.PsychMessage import *
from teamwork.widgets.images import getAgentImage
from teamwork.utils.Debugger import *

class PsychEntity(GenericEntity,Supporter,ConsistentAgent):
    """
    Entity class

          0. Creating a new agent mode:
             - C{agent = L{PsychEntity}(name)}

          1. Picking a specific stereotypical mental model:
             - C{agent.L{setModel}(name)}

          2. Manipulating the goals:
             - C{agent.L{getGoals}()}
             - C{agent.L{setGoals}(goalList)}
             - C{agent.L{getGoalWeight}(goal)}
             - C{agent.L{setGoalWeight}(goal,num)}

          3. Manipulating the recursive belief structure:
             - C{agent.L{ancestry}()}
             - C{agent.L{getBelief}(entityName,feature)}
             - C{agent.L{setBelief}(entityName,feature,num)}
             - C{agent.L{getEntities}()}
             - C{agent.L{getEntity}(entityName)}
             - C{agent.L{setEntity}(entityName,entityObj)}
             - C{agent.L{getEntityBeliefs}()}

          4. Manipulating the state:
             - C{agent.L{getState}(feature)}
             - C{agent.L{setState}(feature,num)}

          5. Manipulating the actions (see L{teamwork.action.PsychActions.Action}):
             - C{agent.actions}: a list of action objects

          6. Manipulating the dynamics (see L{teamwork.dynamics.pwlDynamics.PWLDynamics}):
             - C{agent.dynamics} --- coming soon
       """

    beliefWeights = {'trust':0.15,
                     'liking':0.075,
                     'self-interest':0.1,
                     'sender-interest':-0.0,
                     'consistency':1.0,
                     'threshold':-0.0001
                     }
    consistencyWeights = {'self-interest':0.1,
                          'sender-interest':-0.1,
                          'consistency':0.9,
                          'threshold':0.0
                          }
    
    def __init__(self,name):
        """Constructor

        Takes a string name, a list of action type strings, and a list
        of message factors.  The final parameters is a flag indicating
        whether Tk variables should be used (default is yes)."""
        GenericEntity.__init__(self,name)
        Supporter.__init__(self,name)
        ConsistentAgent.__init__(self,name)
        # Known susceptibilities (themes or messages) of this entity
        self.susceptibilities = []
        # Initialize themes
        try:
            self.themes = self.getDefault('themes')
        except KeyError:
            self.themes = {}
        self.description = ''

    def initEntities(self,entityList,maxDepth=-1):
        """Sets the entities known to be the list provided, and makes
        the appropriate updates to goals, policy depth, etc.
        @param maxDepth: the maximum depth of this agent's recursive models
        @type maxDepth: int
        """
        GenericEntity.initEntities(self,entityList,maxDepth)
        Supporter.initEntities(self,entityList)
        
    # Belief dynamics
    def stateEstimator(self,beliefs,actions,observation=None,debug=Debugger()):
        """Calls the superclass state estimator, but also handles messages"""
        if beliefs is None:
            beliefs = self.getAllBeliefs()
        msgs = {}
        if isinstance(actions,dict):
            # First, immediate message effects
            for actor,actionList in actions.items():
                msgList = []
                for action in actionList:
                    if action['type'] == '_message':
                        msgList.append(action)
                if len(msgList) > 0:
                    msgs[actor] = msgList
        beliefs,delta = self.postComStateEstimator(beliefs,msgs,debug=debug)
        # The following test is temporary
        if len(msgs) == 0:
            # Then, dynamics
            beliefs,new = GenericEntity.stateEstimator(self,beliefs,
                                                       actions,observation,debug)
            delta.update(new)
        return beliefs,delta
    
    def preComStateEstimator(self,beliefs,observations,action,
                             epoch=-1,debug=Debugger()):
        """
        Computes the hypothetical changes to the given beliefs in response to the given actions
        @param beliefs: the beliefs to be updated (traditionally, the result from L{getAllBeliefs})
        @type beliefs: dict
        @param observations: what was observed by this agent
        @type observations: C{dict:strS{->}L{Action}}
        @param action: what action this agent has taken
        @type action: L{Action}[]
        @param epoch: the current epoch in which these observations occurred (currently ignored, but potentially important)
        @type epoch: C{int}
        @type debug: L{Debugger}
        @return: the belief changes that would result from the specified observed actions, in dictionary form:
           - beliefs: results as returned by L{hypotheticalAct<SequentialAgents.hypotheticalAct>}
           - observations: the given actions
        @rtype: C{dict}
        """
        delta = GenericEntity.preComStateEstimator(self,beliefs,observations,action,epoch,debug)
        Supporter.preComStateEstimator(self,beliefs,observations,action,epoch,debug,delta)
        return delta
    
    def postComStateEstimator(self,beliefs,msgs,epoch=-1,debug=Debugger()):
        """Updates the agent's beliefs based on
        received messages"""
        delta = self.hypotheticalPostCom(beliefs,msgs,epoch,debug)
        for sender,messages in msgs.items():
            effect = delta[sender]['effect']
            if effect is not None:
                if not self.parent:
                    # Kind of annoying necessity; perhaps it will be
                    # smoother in the future
                    try:
                        self.updateLinks(effect['relationships'])
                    except KeyError:
                        pass
                self.entities.applyChanges(effect)
        return beliefs,delta

    def hypotheticalPostCom(self,beliefs,msgs,epoch=-1,debug=Debugger()):
        """
        @return: the potential change in the agent's beliefs based on received messages"""
        explanation = {}
        for sender in msgs.keys():
            explanation[sender] = {'effect':None}
            for msg in msgs[sender]:
                # Iterate through all messages sent by this sender
                acceptance = None
                label = msg.pretty()
                # Create a sub-explanation for this individual message
                subExp = {}
                # Do we want to return the explanation in the delta?
                explanation[label] = subExp
                # Determine whether receiver believes message
                try:
                    entity = self.getEntity(sender)
                except KeyError:
                    # What to do here?
                    continue
                acceptance,accExp = self.acceptMessage(entity,msg,debug)
                subExp['decision'] = acceptance
                subExp['breakdown'] = accExp
                if acceptance:
                    # Update beliefs if accepting message
                    debug.message(4,'%s accepts %s' % (self.ancestry(),
                                                       label))
                    delta,subExp = self.incorporateMessage(msg)
                    if explanation[sender]['effect'] is None:
                        explanation[sender]['effect'] = delta
                    else:
                        raise NotImplementedError,'Currently unable to incorporate multiple messages from the same sender'
                    self.updateTrust(sender,explanation[sender]['effect'],
                                     True)
                    # Update any beliefs about myself
                    try:
                        entity = self.getEntity(self.name)
                    except KeyError:
                        entity = None
                    if entity:
                        previous = copy.deepcopy(msg['force'])
                        msg.forceAccept(self.name)
                        subExp = entity.hypotheticalPostCom(beliefs[sender],
                                                            {sender:[msg]},
                                                            epoch,debug)
                        explanation[sender]['effect'][sender] = {self.name:subExp[sender]['effect']}
                        msg['force'] = previous
                elif entity:
                    debug.message(4,'%s rejects %s' % \
                                  (self.ancestry(),label))
                    explanation[sender]['effect'] = {}
                    self.updateTrust(sender,explanation[sender]['effect'],
                                     False)
                    # Update sender's beliefs about entities' beliefs
                    try:
                        entity = entity.getEntity(self.name)
                    except KeyError:
                        entity = None
                    if entity:
                        # This entity has a belief about me, so I need to
                        # update it
                        entity.postComStateEstimator(entity,{sender:[msg]},
                                                     epoch,debug)
        return explanation
    
    def acceptMessage(self,sender,msg,debug=Debugger()):
        """Boolean test that returns true iff this entity will accept 
        (i.e., believe) the message sent by the specified sender entity"""
        if msg.mustAccept(self.name):
            return True,{'forced':1,'accept':'forced','reject':None}
        elif msg.mustReject(self.name):
            return False,{'forced':1,'accept':'forced','reject':None}
        debug.message(1,'Deciding: does '+self.ancestry()+' accept '+`msg`)
        # Try message in conjunction with current model
        value = {'forced':None,
                 'accept':{},
                 'reject':{},
                 }
        valueAccept = 0.
        valueReject = 0.
##        projection = copy.deepcopy(self)
####        delta,exp = projection.incorporateMessage(msg)
##        msg = copy.copy(msg)
##        msg.forceAccept()
##        delta,exp = projection.postComStateEstimator(projection,
##                                                     {sender.name:[msg]},
##                                                     None,debug-1)
####        delta,exp = projection.initial.incorporateMessage(msg)
##        if not delta:
##            # There is no way for me to modify my beliefs to accept this
##            # message
##            debug.message(5,'Cannot accept message: '+`exp`)
##            return None,exp
##        # Add a filter to determine which entities to check
##        filter = None
##        valueAccept,value['accept'] = projection.acceptability(sender,0.0,filter,debug)
        # Compute relevant trust totals
##            entityList = self.trustees(debug)
        entityList = [sender]
        key = 'trust'
        try:
            belief = self.getTrust(sender.name)
        except KeyError:
            belief = 0.
        debug.message(1,'Trust in %s = %s' % (sender.name,`belief`))
        value['accept'][key] = belief
        valueAccept += float(value['accept'][key])*self.beliefWeights[key]
        # Compute relevant support totals
        key = 'liking'
        try:
            belief = self.getSupport(sender.name)
        except KeyError:
            belief = 0.
        debug.message(1,'Liking of %s = %s '% (sender.name,`belief`))
        value['accept'][key] = belief
        valueAccept += float(value['accept'][key])*self.beliefWeights[key]
##        valueReject,value['reject'] = self.acceptability(sender,0.0,filter,debug)
        value['differential'] = valueAccept - valueReject
        
        #evaluate consistency
        if consistencyCalculationAvailable:
            key = 'consistency'
            consistencyCalc = self.calculateMessageConsistency(msg)
            value['accept'][key] = consistencyCalc['proposedConsistency'] - consistencyCalc['currentConsistency']
            debug.message(1,'Consistency of msg = %f'% value['accept'][key])
            valueAccept += float(value['accept'][key])*self.beliefWeights[key]


##        # Evaluate susceptibility
##        if msg.theme:
##            try:
##                item = self.susceptibilities
##            except AttributeError:
##                self.susceptibilities = []
##            for item in self.susceptibilities:
##                if item[0] == msg.theme:
##                    debug.message(1,'Susceptibility: '+item[2])
##                    value['susceptibility'] = float(item[2])
##                    value['differential'] += value['susceptibility']
##                    break
        debug.message(1,'Overall evaluation of message = '+\
                      `valueAccept`)
        # Try message with sender's models
        
        # Try message with other models

        return (float(valueAccept) > \
                self.beliefWeights['threshold']),value
    
    def acceptability(self,sender=None,distance=0.0,filter=None,
                      debug=Debugger()):
        """Quantitative assessment of the acceptability of my current beliefs"""
        value = {}
        # Compute the value to myself
        debug.message(1,'Computing my expected reward...')
        projection = copy.deepcopy(self)
        entityList = [self]
        if sender:
            entityList.append(sender)
        horizon = projection.policy.depth
        eValues,exp = projection.expectedValue(horizon=horizon,
                                               goals=entityList,
                                               debug=debug-1)
        key = 'self-interest'
        value[key] = eValues[self.name]
        debug.message(4,'Value of beliefs to myself = '+`value[key]`)
        if sender:
            # Compute the value to sender
            debug.message(1,'Computing sender''s expected reward...')
            key = 'sender-interest'
            value[key] = eValues[sender.name]
            debug.message(4,'Value of beliefs to sender = '+`value[key]`)
        # Compute consistency of message with my observations
        observations = self.getObservations()[:]
        observations.reverse()
##        projection = copy.deepcopy(self.initial)
##        projection.freezeModels()
##        debug.message(1,'Computing consistency...')
##        key = 'consistency'
##        value[key] = projection._consistency(observations,filter,debug-1)
##        debug.message(4,'Belief consistency = '+`value[key]`)
        # Compute weighted sum of values
        total = Distribution({0.:1.})
        for key in value.keys():
            try:
                weight = self.beliefWeights[key]
                try:
                    total = total + value[key].total()*weight
                except AttributeError:
                    total = total + value[key]*weight
            except KeyError:
                # We don't have a weight for this subtotal
                pass
        debug.message(4,'Overall evaluation of beliefs = '+`total`)
        return total,value
        
    def extendPolicy(self,subpolicy):
        """Extends the lookup policy I{within} the overall composite policy"""
        for policy in self.policy.subpolicies:
            if policy.type == 'lookup':
                policy.extend(subpolicy,entity=self)
                break

    def setPolicyDepth(self,depth):
        """Sets the lookahead policy depth I{within} the overall composite policy (creates a lookahead subpolicy if none pre-existing)
        @param depth: the desired horizon
        @type depth: int"""
##        self.invalidateCache()
        if self.policy.type == 'composite':
            for policy in self.policy.subpolicies:
                if policy.type == 'lookahead':
                    policy.depth = depth
                    break
            else:
                # No pre-existing lookahead policy
                self.policy.extend(LookaheadPolicy(self,self.entities,depth))
        elif self.policy.type == 'lookupahead':
            self.policy.depth = depth

    def getPolicyDepth(self):
        """@return: the lookahead policy depth I{within} the overall composite policy (returns 0 if no such subpolicy)
        @rtype: int"""
        if self.policy.type == 'composite':
            for policy in self.policy.subpolicies:
                if policy.type == 'lookahead':
                    return policy.depth
            else:
                # No pre-existing lookahead policy
                return 0
        elif self.policy.type == 'lookupahead':
            return self.policy.depth
        
    # Utility methods

    def __cmp__(self,agent):
        """@note: This is just a string compare on names.  Feel free to override with a more domain-specific comparison"""
        return cmp(self.name.lower(),agent.name.lower())
    
    def __copy__(self):
        new = GenericEntity.__copy__(self)
        new = Stereotyper.__copy__(self,new)
        new.themes = self.themes
        new.factors = self.factors
##        if self.attributes.has_key('imageName'):
##            new.attributes['image'] = self.attributes['image']
##            new.attributes['imageName'] = self.attributes['imageName']
        new.description = copy.copy(self.description)
        return new

    def __getstate__(self):
        """Remove any image info before pickling"""
        new = copy.copy(self.__dict__)
        new['image'] = None
        return new

    def __setstate__(self,newDict):
        """Restore image info after unpickling"""
        for key,value in newDict.items():
            self.__dict__[key] = value
        if self.attributes.has_key('window'):
            name = self.attributes['imageName']
            self.attributes['image'] = getAgentImage(name)
        return self

    def __xml__(self):
        doc = GenericEntity.__xml__(self)
        return Supporter.__xml__(self,doc)

    def parse(self,element):
        GenericEntity.parse(self,element)
        Supporter.parse(self,element)
