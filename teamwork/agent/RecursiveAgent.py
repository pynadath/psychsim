"""Defines the agent layer that handles beliefs about other agents"""
#from xml.dom.minidom import *
import copy
import math
from Agent import Agent

from teamwork.math.Keys import Key,StateKey,ObservationKey,keyConstant
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.probability import Distribution
from teamwork.math.ProbabilityTree import ProbabilityTree
from teamwork.action.PsychActions import Action
from teamwork.action.DecisionSpace import ActionCondition
from teamwork.multiagent.sequential import SequentialAgents
from teamwork.dynamics.pwlDynamics import PWLDynamics
from teamwork.policy.pwlPolicy import PWLPolicy

class RecursiveAgent(Agent):
    """Base class for an agent that keeps recursive models of the other agents in its world.
    @ivar state: the probability distribution over the state of this agent's world
    @type state: L{Distribution}
    @ivar parent: the agent whose subjective view this agent represents (C{None}, if this is an objective view)
    @type parent: L{RecursiveAgent}
    @ivar dynamics: the dynamics by which this agent's state evolves
    @type dynamics: dict
    @ivar relationships: inter-agent relationships from this agent.  In dictionary form:
       - I{relationship name}: list of agent names
    """
    
    def __init__(self,name=''):
        """
        @param name: label for this instance
        @type name: string
        """
        # Initialize entity state
        self.state = Distribution({KeyedVector():1.})
        # Create agent
        Agent.__init__(self,name)
        # Start with an empty policy
        self.policy = None
        # Fixed links to other agents
        self.relationships = {}
        # Effects of actions on state features of this agent
        self.dynamics = {}
        # The state of this agent at time 0
        self.initial = None
        # The agent (if any) in whose subjective view this agent exists
        self.parent = None
        # Cache of any instantiated observation functions
        self.obsCache = {}

    def setName(self,name):
        """Sets the name of this agent
        @param name: the unique ID for this agent
        @type name: C{str}
        """
        Agent.setName(self,name)
        # Update state
        frozen = self.state.unfreeze()
        for vector,prob in self.state.items():
            del self.state[vector]
            for oldKey,value in vector.items():
                del vector[oldKey]
                newKey = StateKey({'entity':self.name,
                                   'feature':oldKey['feature']})
                vector[newKey] = value
                vector._updateString()
            self.state[vector] = prob
        if frozen:
            self.state.freeze()

    # State accessor methods

    def getState(self,feature):
        """Returns the current L{Distribution} over the specified feature
        @type feature: string
        @rtype: L{Distribution}"""
        key = StateKey({'entity':self.name,'feature':feature})
        return self.state.getMarginal(key)

    def setState(self,feature,value):
        """Sets this entity's state value for the specified feature
        @type feature: string
        @type value: either a float or a L{Distribution}.  If the value is a float, it is first converted into a point distribution."""
        key = StateKey({'entity':self.name,'feature':feature})
        frozen = self.state.unfreeze()
        self.state.join(key,value)
        if frozen:
            self.state.freeze()

    def getObservation(self,name):
        """Returns the current L{Distribution} over the specified observation flag
        @type name: string
        @rtype: L{Distribution}"""
        key = ObservationKey({'type':name})
        return self.state.getMarginal(key)
        
    def setObservation(self,name,value):
        """Sets this entity's observation flag for the observation type
        @type name: string
        @type value: either a float or a L{Distribution}.  If the value is a float, it is first converted into a point distribution."""
        key = ObservationKey({'type':name})
        self.state.unfreeze()
        self.state.join(key,value)
        self.state.freeze()

    def getStateFeatures(self):
        """
        @return: names of the valid state features
        @rtype: C{str[]}
        """
        keyList = []
        for key in self.state.domainKeys():
            if isinstance(key,StateKey) and key['entity'] == self.name:
                keyList.append(key['feature'])
        return keyList
    
    # Methods for accessing subjective beliefs about entities

    def getEntity(self,name):
        """
        @return: the agent representing the beliefs about the given entity
        @type name: string
        @rtype: L{RecursiveAgent}
        """
        if not isinstance(name,str):
            raise DeprecationWarning,'getEntity requires string argument'
        try:
            return self.entities[name]
        except KeyError:
            raise KeyError,'Entity %s has no belief about %s' \
                  % (self.ancestry(),name)

    def __getitem__(self,index):
        """Allows indexing into entity beliefs (i.e., C{entity['Bill']})"""
        return self.getEntity(index)

    def hasBelief(self,entity):
        """
        @param entity: the name of the entity being queried about
        @type entity: C{str}
        @return: C{True} iff I have a belief about the named entity
        @rtype: C{boolean}
        """
        return self.entities.has_key(entity)

    def getEntities(self):
        """
        @return: the names of entities that I have beliefs about
        @rtype: C{str[]}
        """
        return self.entities.keys()

    def getEntityBeliefs(self):
        """
        @return: the subjective entity views that I have
        @rtype: L{Agent}[]
        """
        return self.entities.values()

    def getBeliefKeys(self):
        """
        @return: the state features across all beliefs that this agent has
        @rtype: L{StateKey}[]
        """
        return self.entities.getStateKeys().keys()
    
    def getBelief(self,entity,feature):
        """Shortcut for C{self.L{getEntity}(entity).L{getState}(feature)}"""
        subjectiveEntity = self.getEntity(entity)
        return subjectiveEntity.getState(feature)
    
    def getNestedBelief(self,keys):
        """Accesses a nested belief by following the branches specified by keys (a list of strings).
        @warning: may not actually work anymore!
        """
        currentBelief = self
        for key in keys:
            if isinstance(currentBelief,Agent):
                if key == 'state':
                    currentBelief = currentBelief.state
                    continue
                elif key == 'entities':
                    continue
            # Translate special key "self" into my name
            if key == 'self':
                key = self.name
            try:
                currentBelief = currentBelief[key]
            except KeyError:
                try:
                    currentBelief = currentBelief.getEntity(key)
                except AttributeError:
                    raise AttributeError,'Illegal belief spec: %s' % (`keys`)
            except AttributeError:
                raise AttributeError,'Illegal belief spec: %s' % (`keys`)
        return currentBelief

    def getSelfBelief(self,feature):
        """Shortcut for C{self.L{getEntity}(self.name).L{getState}(feature)}"""
        selfImage = self.getEntity(self.name)
        return selfImage.getState(feature)

    # Methods for manipulating subjective beliefs about entities
    
    def setBelief(self,name,feature,value):
        """Shortcut for C{self.L{getEntity}(entity).{setState}(feature,value)}"""
        subjectiveEntity = self.getEntity(name)
        subjectiveEntity.setState(feature,value)

    def setSelfBelief(self,feature,value):
        """Shortcut for C{self.setBelief(self,feature,value)}"""
        self.setBelief(self.name,feature,value)

    def setEntity(self,entity):
        """Sets my belief about the given entity to be the provided entity object.  Basically equivalent to C{self.entities[entity.name] = entity}.
        @type entity: L{RecursiveAgent}
        """
        self.entities.addMember(entity)
        entity.parent = self

    def setRecursiveBelief(self,name,feature,value):
        """Helper method for setting the beliefs of a feature
        @param name: the name of the other entity about whom our belief is is subject to change.
        @type name: C{str}
        @param feature: the state feature to change
        @type feature: C{str}
        @param value: the new value for the named state feature

        @note: this will change all of the subjective beliefs that this entityd holds.  Thus, not only will my beliefs about C{name}, but also my beliefs about I{X}'s beliefs about C{name}."""
        if self.hasBelief(name):
            self.setBelief(name,feature,value)
        for entity in self.getEntityBeliefs():
            entity.setRecursiveBelief(name,feature,value)

    def getAllBeliefs(self,recurse=True):
        """Packages up all of this agent's beliefs into a handy dictionary
        @param recurse: if C{True}, it's OK to borrow parents' beliefs if no beliefs of our own (you shouldn't use this)
        @type recurse: bool
        @return: the dictionary has the following indices:
           - state: what this agent believes about the state of the world
           - I{name}: what this agent think agent, I{name}, believes (i.e., a recursive call to L{getAllBeliefs})
        @rtype: dict
        """
        if len(self.entities.members()) > 0:
            believer = self
        elif recurse and self.parent:
            believer = self.parent
        else:
            believer = self
        result = {'state':believer.entities.getState(),
                  'turn':believer.entities.order,
                  'observations':believer.entities.getActions()
                  }
        for agent in believer.getEntityBeliefs():
            result[agent.name] = agent.getAllBeliefs(recurse=False)
        return result
    
    # Policy methods

    def applyPolicy(self,state=None,actions=[],horizon=None,history=None,
                    debug=None,explain=False):
        """Generates a decision chosen according to the agent's current policy
        @param state: the current state vector
        @type state: L{Distribution}(L{KeyedVector})
        @param actions: the possible actions the agent can consider (defaults to all available actions)
        @type actions: L{Action}[]
        @param horizon: the horizon to consider (by default, use the entity's given horizon)
        @type horizon: int
        @param history: a dictionary of actions that have already been performed (and which should not be performed again if they are labeled as not repeatable)
        @type history: L{Action}[]:bool
        @param explain: flag indicating whether an explanation should be generated
        @type explain: bool
        @return: a list of actions and an explanation, the latter provided by L{execute<PWLPolicy.execute>}
        @rtype: C{(L{Action}[],Element)}
        """
        if state is None:
            state = self.getAllBeliefs()
        return self.policy.execute(state=state,choices=actions,horizon=horizon,
                                   history=history,debug=debug,explain=explain)
    
    def invalidateCache(self):
        """Removes any cached policy value, as well as any cached policy values of my parents"""
        if self.policy:
            self.policy.reset()
        if self.parent:
            self.parent.invalidateCache()

    def getLookahead(self):
        """
        @return: Extract a sequence of agents for lookahead, where I am first
        @rtype: str[]
        """
        if self.policy.horizon == 0:
            return [self.name]
        world = self
        while True:
            others = world.entities.getSequence()
            if len(others) > 0:
                break
            # Use parents' belief?
            world = world.parent
        if isinstance(others[0],list):
            others = sum(others,[])
        order = []
        while len(order) < self.policy.horizon:
            order += others
        order = order[:self.policy.horizon]
        while order[0] != self.name:
            last = order.pop()
            order.insert(0,last)
        return order
    
    def getPolicies(self,policies=None):
        """
        @return: a dictionary of the policies of all of the agents in this entity's lookahed
        @rtype: strS{->}L{PWLTable}
        """
        order = self.getLookahead()
        # Seed policies
        if policies is None:
            policies = {}
        while len(order) > 0:
            name = order.pop()
            if name == self.name:
                agent = self
            else:
                agent = self.getEntity(name)
            if not policies.has_key(name):
                try:
                    policies[name] = agent.policy.tables[-1][-1]
                except IndexError:
                    agent.policy.getTable(0,0,True)
                    policies[name] = agent.policy.tables[-1][-1]
        return policies

    def setPolicies(self,depth,horizon):
        """
        Gives this agent correct beliefs about all other agents' policies and state estimators
        @param depth: the resulting belief depth for this agent, as it will take the policies of the other agents at level depth-1
        @type depth: int
        @param horizon: the horizon to use for the policies
        """
        for belief in filter(lambda e: e.name != self.name,
                             self.entities.activeMembers()):
            belief.policy.tables = []
            real = self.world[belief.name]
            # Find corresponding agent in real world
            while not real.parent is None:
                real = real.parent.world[belief.name]
            if len(real.policy.tables) == 0:
                # No policies at all.  A tragedy.
                continue
            for level in range(depth):
                try:
                    real.policy.tables[level]
                except IndexError:
                    # No more policies
                    break
                # Update policy tables
                belief.policy.tables.append([])
                for t in range(horizon+1):
                    try:
                        table = real.policy.getTable(level,t)
                    except IndexError:
                        break
                    belief.policy.tables[level].append(table.getTable())
            # Update state estimator
            for omega,table in real.estimators.items():
                belief.estimators[omega] = table.getTable()
            # Update possible worlds
            belief.entities.worlds.clear()
            belief.entities.reverseWorlds.clear()
            belief.entities.worlds.update(real.entities.worlds)
            belief.entities.reverseWorlds.update(real.entities.reverseWorlds)
                
    # Update methods

    def initialStateEstimator(self):
        """Initializes beliefs"""
        beliefs = {}
        beliefs['entities'] = self.entities = SequentialAgents()
        self.resetHistory(beliefs)
        return beliefs

    def stateEstimator(self,beliefs,actions,observation=None,debug=None):
        """Trying to unify L{preComStateEstimator} and L{postComStateEstimator}"""
        if observation:
            if isinstance(beliefs,list):
                # Observation history
                beliefs = beliefs + [observation]
                return beliefs,[observation]
            else:
                # Belief state
                SE = self.getEstimator()[observation]
                rule = SE.index(beliefs)
                numerator = SE.values[rule][str(actions)]
                beliefs = numerator*beliefs
                beliefs *= 1./sum(beliefs.getArray())
                return beliefs,numerator
        else:
            return self.preComStateEstimator(beliefs,actions,debug=debug)
        
    def preComStateEstimator(self,beliefs,observations,action,epoch=-1,debug=None):
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
           - beliefs: results as returned by L{SequentialAgents.hypotheticalAct}
           - observations: the given actions
        @rtype: C{dict}
        """
        # Compute the effect of these actions in the given belief state
        if isinstance(observations,str):
            observations = ObservationKey({'type': observations})
        if isinstance(observations,Key):
            # Distribution over possible observations
            state = beliefs['entities'].state
            vector = self.world.state2world(state)
            SE = self.getEstimator()[observations]
            rule = SE[vector]
            numerator = rule['values'][self.makeActionKey(action)]
            vector = numerator*vector
            vector *= 1./sum(vector.getArray())
            for world in vector.keys():
                state[self.world.worlds[world]] = vector[world]
            return beliefs,numerator
        # Action by someone else that should cause update in probability
        if len(self.entities.state) > 1 and self.parent is None:
            for actor in observations.keys():
                if actor != self.name:
                    entity = self.getEntity(actor)
                    values = {}
                    for vector in self.entities.state.domain():
                        state = entity.getAllBeliefs()
                        nodes = [state]
                        while len(nodes) > 0:
                            node = nodes.pop()
                            for key in node.keys():
                                if key == 'state':
                                    node['state'] = Distribution({vector:1.})
                                elif self.entities.has_key(key):
                                    nodes.append(node[key])
                        EV,explanation = entity.actionValue(observations[actor],
                                                            horizon=entity.policy.horizon,state=state)
                        values[vector] = math.exp(0.8*(EV.expectation() + 1.*float(entity.policy.horizon)))
                    for vector in self.entities.state.domain():
                        self.entities.state[vector] = self.entities.state[vector] * values[vector]
                    self.entities.state.normalize()
#        if len(self.entities) == 0 and self.parent and max(map(len,beliefs['state'].domain())) > 1:
#            delta = self.parent.entities.hypotheticalAct(actions,beliefs)
#        else:
        delta = self.entities.hypotheticalAct(observations,beliefs)
#         if beliefs is not None:
#             # Update the belief state
#             self.applyChanges(beliefs,delta,descend=False)
        return delta
    
    def incorporateMessage(self,msg,log=None):
        """Update an entity's beliefs in response to set of messages
        @param msg: the message whose dynamics we wish to compute
        @type msg: L{Message<teamwork.messages.PsychMessage.Message>}
        @param log: not sure what this is for, probably auditing at some point, but nothing happens to it right now, so it's not very useful
        @return: the dynamics matrix corresponding to the desired change of beliefs implied by the given message
        @rtype: L{KeyedMatrix}
        """
        delta = None
        explanation = []
        for factor in msg['factors']:
            try:
                result = factor['matrix']
            except KeyError:
                result = self.__incorporateMessage(factor)
            if delta is None:
                delta = result
            else:
                delta *= result
            explanation.append(factor)
        return {'state':delta},explanation

    def __incorporateMessage(self,factor):
        """Update an entity's beliefs in response to a received message
        @param factor: the individual message factor
        @type factor: dict
        @return: the dynamics corresponding to an individual factor
        @rtype: L{KeyedMatrix}
        """
        # Start with an identity matrix
        matrix = KeyedMatrix()
        keyList = self.entities.state.expectation().keys()
        matrix.fill(keyList)
        for key in keyList:
            matrix.set(key,key,1.)
        delta = Distribution({matrix:1.})
        # Incorporate the given message factor into this distribution
        if factor['topic'] == 'state':
            currentBelief = self
            path = []
            for key in factor['lhs'][:len(factor['lhs'])-1]:
                if key == 'entities':
                    currentBelief = currentBelief.entities
                elif isinstance(currentBelief,Agent):
                    if key == 'state':
                        continue
                    elif key == 'policy':
                        currentBelief = currentBelief.policy
                    else:
                        currentBelief = currentBelief.beliefs
                        currentBelief = currentBelief[key]
                else:
                    try:
                        currentBelief = currentBelief[key]
                        path.append(key)
                    except KeyError:
                        # Belief is too far deep for this entity
                        break
            else:
                if len(path) != 1:
                    raise NotImplementedError,'My apologies, I am unable to handle such rich messages right now'
                else:
                    feature = factor['lhs'][len(factor['lhs'])-1]
                    key = StateKey({'entity':path[0],
                                    'feature':feature})
                    if factor['relation'] == '=':
                        # This message is trying to directly set a specific belief
                        if isinstance(factor['value'],float):
                            for element,prob in delta.items():
                                del delta[element]
                                element.set(key,key,0.)
                                element.set(key,keyConstant,factor['value'])
                                delta[element] = prob
                        elif isinstance(factor['value'],Distribution):
                            if len(factor['value']) == 1:
                                for element,prob in delta.items():
                                    del delta[element]
                                    element.set(key,key,0.)
                                    element.set(key,keyConstant,
                                                factor['value'].expectation())
                                    delta[element] = prob
                            else:
                                for matrix,oldProb in delta.items():
                                    del delta[matrix]
                                    for value,newProb in factor['value'].items():
                                        newMatrix = copy.deepcopy(matrix)
                                        newMatrix.set(key,key,0.)
                                        newMatrix.set(key,keyConstant,value)
                                        delta[newMatrix] = oldProb*newProb
                    else:
                        # This message is trying to make a comparative statement
                        raise NotImplementedError,'Unable to handle messages with relationship, "%s"' % (factor['relation'])
        elif factor['topic'] == 'observation':
            raise NotImplementedError,'Currently unable to handle messages about actions'
##            actions = {factor['actor']: factor['action']}
##            result = self.stateEstimator(actions=actions)
##            print result.keys()
##            delta.update(result)
        elif factor['topic'] == 'model':
            raise NotImplementedError,'Currently unable to handle messages about mental models'
##            try:
##                entity = self.getEntity(factor['entity'])
##            except KeyError:
##                entity = None
##            if entity:
##                diff = delta
##                for name in factor['entity']:
##                    if not diff.has_key(name):
##                        diff['beliefs'] = {name: {}}
##                    diff = diff['beliefs'][name]
##                diff['model'] = {'previous model':entity.model,
##                                 'model':factor['value']}
        delta.freeze()
        return delta

    # Handle observation history
                
    def getObservations(self):
        """
        @return: the sequence of events that this entity has witnessed
        @rtype: C{list}
        """
        return self.beliefs['observations']
    
    def saveObservations(self,obs):
        """Adds the given observation to the history
        """
        self.beliefs['observations'].insert(0,obs)

    def findObservation(self,action,depth=0):
        """Returns true iff the agent has observed the given action
        @param action: the observation to look for
        @type action: L{Action}
        @param depth: the maximum number of steps to look into the past (by default, look arbitrarily far)
        @type depth: int
        @rtype: a tuple (boolean,int)
        @return: the first return value is true iff the agent has observed the given action within the past depth time steps.  The second return value is the number of steps in the past that the observation occurs.  This value is negative if no such observation is found within the specified depth."""
        obsList = self.getObservations()
        if depth and depth < len(obsList):
            limit = depth
        else:
            limit = len(obsList)
        for index in range(limit):
            for actions in obsList[index].values():
                for obs in actions:
                    if obs.matchTemplate(action):
                        return obs,index
        return None,-1

    def resetHistory(self,beliefs=None):
        """Resets the observation history of the specified beliefs (defaults to this entity's beliefs if none provided)"""
        if not beliefs:
            beliefs = self.beliefs
        beliefs['observations'] = []

    def getActionKeys(self):
        """
        @return: the minimal set of observations relevant to this agent
        @rtype: C{L{teamwork.math.Keys.ActionKey}[]}"""
        actionKeys = []
        # Find any observations that I have goals for
        for key in self.getGoalVector()['action'].keys():
            actionKeys.append(key)
        # Find any observations that are on the LHS of my policy rules
        for key in self.policy.tree.getKeys():
            if key['class'] == 'observation':
                if not key in actionKeys:
                    actionKeys.append(key)
        return actionKeys
    
    # Handle the effects of actions on state

    def multistep(self,horizon=1,start={},state=None,window=True,debug=None,explain=False):
        """Steps this entity the specified number of steps into the future (where a step is one entity performing its policy-specified action)
        @param state: the world state to evaluate the actions in (defaults to current world state)
        @type state: L{Distribution}(L{KeyedVector})
        @param window: if C{True}, do not let any agents look beyond the edge of this horizon
        @type window: bool
        @warning: This method still needs to be handed an updated turn vector
        """
        if state is None:
            state = self.getAllBeliefs()
        sequence = []
        # Lookahead
        for t in range(horizon):
            if debug:
                print 'Time',t
            if t == 0:
                entityDict = start
            else:
                entityDict = {}
            try:
                previous = sequence[-1]
            except IndexError:
                previous = [{'result': state}]
            next = []
            for node in previous:
                current = node['result']
                nextGroup = self.entities.next(current['turn'])
                for entity in nextGroup:
                    try:
                        choices = entity['choices']
                    except KeyError:
                        choices = []
                    entity = entity['name']
                    if len(entityDict) < len(nextGroup) and \
                           not entityDict.has_key(entity):
                        entityDict[entity] = choices
                # Apply these entities' actions
                if window:
                    result = self.step(actDict=entityDict,state=current,
                                       horizon=horizon-t,debug=debug,explain=explain)
                else:
                    result = self.step(actDict=entityDict,state=current,debug=debug,explain=explain)
                for delta in result:
                    if delta['probability'] > 1e-8:
                        delta['result'] = copy.deepcopy(current)
                        self.applyChanges(delta['result'],delta['effect'],True,False)
                        delta['time'] = t
                        next.append(delta)
            # Accumulate end points across all possible starting points
            sequence.append(next)
        return sequence

    def updateStateDict(self,original,delta):
        for key,diff in delta.items():
            if key == 'turn':
                original[key] = diff[original[key]] * original[key]
            elif self.hasBelief(key):
                self.updateStateDict(original[key],diff)
            else:
                pass
        
    def step(self,actDict,state=None,horizon=None,debug=False,explain=False):
        """Modifies the current entity in response to the
        policy-driven actions selected by the provided dictionary of
        entities.
        @param state: the world state to evaluate the actions in (defaults to current world state)
        @type state: L{Distribution}(L{KeyedVector})
        @rtype: dict[]
        @param horizon: window of projection to use for any lookahead
        @type horizon: int
        """
        # By default, use my beliefs as the world
        if state is None:
            state = self.getAllBeliefs()
        # Construct the set of actions performed by these entities
        branch = {'breakdown': {},'action':actDict}
        for name,options in actDict.items():
            if debug:
                print self.name,'predicting',name
            action,exp = self.predict(name,options,state,horizon,debug,explain)
            if action:
                if debug:
                    print '\t%s expects %s to %s' % \
                        (self.name,name,self.makeActionKey(action))
                actDict[name] = action
                branch['breakdown'][name] = exp
            else:
                del actDict[name]
        if len(actDict) > 0:
            obs = self.observe(state['state'],actDict)
            try:
                myAct = actDict[self.name]
            except KeyError:
                myAct = None
            branch['effect'] = self.preComStateEstimator(state,obs,myAct,debug=debug)
            branch['state'] = state['state']
            branch['turn'] = state['turn']
            branch['probability'] = 1.
            return [branch]
        else:
            return []

    def predict(self,actor,options,state=None,horizon=None,debug=False,explain=False):
        """Generates an expected action for the specified actor, considering the given options, in the given state of belief
        """
        try:
            entity = self.getEntity(actor)
        except KeyError:
            # Don't do anything if we have no belief about this entity
            entity = None
        if isinstance(options,list) and len(options) > 0:
            # Pre-specified action
            if isinstance(options[0],list):
                # Set of possible actions to choose from
                return entity.applyPolicy(state=state[actor],actions=options,
                                          horizon=horizon,debug=debug,explain=explain)
            else:
                # A single action for you to do
                return options,{'forced':True,'decision':options}
        elif entity:
            # Unconstrained set of possible actions
            beliefs = state[actor]
            return entity.applyPolicy(state=beliefs,horizon=horizon,debug=debug,explain=explain)
        else:
            return None,{}

    def getDynamics(self,actions,feature):
        """
        @return: this entity's dynamics model for the given action (C{None} if no effect)
        @param actions: the action(s) whose effect we are interested in
        @type actions: L{Action} or strS{->}L{Action}[]
        @param feature:  the state feature whose dynamics we want
        @type feature: C{str}
        @rtype: L{PWLDynamics}
        """
        if not self.dynamics.has_key(feature):
            # This state feature is constant
            return None
        actionKey = self.makeActionKey(actions)
        try:
            # Try to find dynamics specific to this particular action
            dynFun = self.dynamics[feature][actionKey]
            if isinstance(dynFun,dict):
                dynFun = dynFun['tree']
        except KeyError:
            # Test matching conditions
            dynFun = None
            for cls in self.dynamics[feature].values():
                if not isinstance(cls,str):
                    # Already instantiated dynamics, not relevant
                    continue
                for conditional in self.hierarchy[cls].dynamics[feature].values():
                    if isinstance(actions,Action):
                        actions = [actions]
                    if conditional['condition'].match(actions):
                        dynFun = PWLDynamics({'tree':conditional['tree']})
                        break
                if dynFun:
                    break
            else:
                # It's OK for an action to have no dynamics
                # (e.g., the "wait" action)
                try:
                    self.dynamics[feature][actionKey] = None
                except KeyError:
                    self.dynamics[feature] = {actionKey: None}
                return None
            dynFun = dynFun.instantiate(self,actions)
            # Check whether dynamics is well formed
            vector = self.state.domain()[0]
            for leaf in dynFun.getTree().leaves():
                for key in leaf.rowKeys():
                    if not vector.has_key(key):
                        print 'Dynamics of %s\'s %s in response to %s has extraneous key, %s' % (self.ancestry(),feature,actionKey,str(key))
                for key in leaf.colKeys():
                    if not vector.has_key(key):
                        print 'Dynamics of %s\'s %s in response to %s has extraneous key, %s' % (self.ancestry(),feature,actionKey,str(key))
            for branch in dynFun.getTree().branches().values():
                if not isinstance(branch,Distribution):
                    for key in branch.weights.keys():
                        if not vector.has_key(key):
                            print 'Dynamics of %s\'s %s in response to %s has extraneous key, %s' % (self.ancestry(),feature,actionKey,str(key))
            self.dynamics[feature][actionKey] = dynFun
        return dynFun

    def applyChanges(self,beliefs,delta,descend=True,rewind=False):
        """Takes changes and modifies the given beliefs accordingly
        @param descend: If the descend flag is set, then the recursive changes in the delta will also be applied.
        @type descend: C{boolean}
        @param rewind: If the rewind flag is set, then the changes will be undone, instead of applied.
        @type rewind: C{boolean}"""
        for feature,diff in delta.items():
            if feature == 'state':
                beliefs['state'] = diff*beliefs['state']
            elif feature == 'turn':
                beliefs['turn'] = diff[beliefs['turn']]*beliefs['turn']
            elif feature == 'observations':
                beliefs['observations'] = diff*beliefs['observations']
            elif feature == 'relationships':
                pass
            else:
                if descend and self.hasBelief(feature):
                    self.applyChanges(beliefs[feature],diff,descend,rewind)
            
    def freeze(self):
        """Takes the current state of beliefs and marks it as the initial, beginning-of-the-world state of beliefs.
        @note: as a side effect, it resets the observation history"""
        self.initial = None
##        self.initial = copy.deepcopy(self)
##        for entity in self.initial.getEntities():
##            self.initial.getEntity(entity).freeze()
##            self.getEntity(entity).freeze()
##        self.initial.initial = None
##        self.initial.resetHistory()
        self.resetHistory()

    # Utility methods
    
    def ancestry(self):
        """
        @return: a string representation of this entity's position in the recursive belief tree.
          - If C{self.parent == None}, then returns C{self.name}
          - Otherwise, returns C{self.parent.ancestry()+'->'+self.name}
        @rtype: C{str}"""
        name = self.name
        parent = self.parent
        while parent:
            name = parent.name + '->' + name
            parent = parent.parent
        return name

    def beliefDepth(self):
        """
        Inverse of L{beliefHeight}
        @return: the recursive depth of the current entity (0 is the depth of a root entity)
        @rtype: C{int}"""
        if self.parent:
            return 1 + self.parent.beliefDepth()
        else:
            return 0

    def beliefHeight(self):
        """
        Inverse of L{beliefDepth}
        @return: the recursive height of the current entity from bottom of depth tree (0 is the depth of a leaf entity)
        @rtype: C{int}"""
        children = self.getEntityBeliefs()
        if children:
            return 1 + max(map(lambda e: e.beliefHeight(),children))
        else:
            return 0

    def __copy__(self):
        """
        @warning: the dynamics are not copied, but simply linked
        """
        new = Agent.__copy__(self)
##        new.beliefs['observations'] = self.beliefs['observations']
        new.parent = self.parent
        new.dynamics = self.dynamics
##        for feature in self.getStateFeatures():
##            value = self.getState(feature)
##            new.setState(feature,value)
        return new
    
    def __deepcopy__(self,memo):
        new = copy.copy(self)
        new.dynamics = copy.deepcopy(self.dynamics,memo)
        memo[id(self)] = new
        new.beliefs['observations'] = self.beliefs['observations'][:]
        new.entities = copy.deepcopy(self.entities,memo)
        return new

    def __str__(self):
        """Returns a string representation of this entity"""
        content = '\n'+self.name+':'
        content += ' ('+self.ancestry() + ')\n'
        content += '\tState:\n'
        for feature in self.getStateFeatures():
            resAct = self.getState(feature)
            for value, prob in resAct.items():
                content += '\t\t'+feature+' '+str(value)+'  prob  '+`prob`+'\n'
        if len(self.getEntities()) > 0:
            content += '\tBeliefs:'
        for otherName in self.getEntities():
            other = self.getEntity(otherName)
            content += str(other).replace('\n','\n\t\t')
        content += '\n\tPolicy:\n'
        substr = `self.policy`
        content += '\t\t' + substr.replace('\n','\n\t\t')
        content += '\n\tDynamics:\n'
        content += '\t\t'+`self.dynamics.keys()`
        return content
    
    def toHTML(self):
        content = '<TABLE RULES="rows" BORDER="3">\n'
        substr = self.name
        entity = self
        while entity.parent:
            entity = entity.parent
            substr = entity.name + "'s beliefs about " + substr
        content += '<FONT SIZE="+2">%s</FONT>' % (substr)
        content += '<CAPTION>'
        content += '</CAPTION>\n'
        content += '<TBODY>\n'
        # Add my state
        content += '<TR>'
        content += '<TH BGCOLOR="#ffff00"><FONT SIZE="+1">State</FONT></TH>'
##        content += '<TD>' + self.state.toHTML() + '</TD>\n'
        content += '<TD><TABLE BORDER="3" WIDTH="100%%" CELLPADDING="0">\n'
        content += '<TBODY>\n'
        for feature in self.getStateFeatures():
            content += '<TR>'
            content += '<TH>' + feature + '</TH>\n'
            content += '<TD WIDTH="200" HEIGHT="50">'
            value = float(self.getState(feature))
            content += float2bar(value,False)
            content += '</TD>'
##            content += '<TD><OL><FONT SIZE="-1">'
##            history = self.getHistory(feature)
##            for index in range(len(history)):
##                content += '<LI VALUE="%d">%s</LI>\n' % (len(history)-index,
##                                                     history[index])
##            content += '</FONT></OL></TD>\n'
            content += '</TR>\n'
        content += '</TBODY>\n'
        content += '</TABLE></TD>\n'
        content += '</TR>\n'
        # Add my goals
        content += '<TR>'
        content += '<TH BGCOLOR="#ffff00"><FONT SIZE="+1">Goals</FONT></TH>'
        content += '<TD>'
        content += '<TABLE BORDER="3" WIDTH="100%%">\n'
        content += '<TBODY>\n'
##        content += '<THEAD><TH>Goal</TH><TH>Weight</TH><TH>History</TH></THEAD>\n'
        for goal in self.getGoals():
            
            content += '<TR><TD>%s</TD><TD WIDTH="100" HEIGHT="50">' % (goal)
            content += float2bar(self.getGoalWeight(goal))
            content += '</TD>'
##            content += '<TD><OL><FONT SIZE="-1">'
##            history = self.getHistory(goal)
##            for index in range(len(history)):
##                content += '<LI VALUE="%d">%s</LI>\n' % (len(history)-index,
##                                                     history[index])
##            content += '</FONT></OL></TD>\n'
            content += '</TR>\n'
        content += '</TBODY>\n'
        content += '</TABLE>\n'
        content += '</TD>\n'
        content += '</TR>\n'
        # Add my beliefs about other entities
        content += '<TH BGCOLOR="#ffff00"><FONT SIZE="+1">Beliefs</FONT></TH>'
        content += '<TD>'
        content += '<TABLE BORDER="3" WIDTH="100%%">\n'
        content += '<TBODY>\n'
        odd = None
        for entity in self.getEntityBeliefs():
            content += '<TR'
            if odd:
                content += ' BGCOLOR="#aaaaaa"'
            else:
                content += ' BGCOLOR="#ffffff"'
            content += '>'
            content += '<TD>' + entity.toHTML() + '</TD>'
            content += '</TR>\n'
            odd = not odd
        content += '</TBODY>\n'
        content += '</TABLE>\n'
        # Close
        content += '</TBODY>\n'
        content += '</TABLE>\n'
        return content
    
    def __ne__(self,entity):
        return not (self == entity)
    
    def __eq__(self,entity):
        """Equality test between agents
        @warning: only partially implemented
        @param entity: the entity to be compared against
        @type entity: L{RecursiveAgent}
        @rtype: C{boolean}"""
        if isinstance(entity,str):
            return self.name == entity
        if self.name != entity.name:
            return False
        if self.parent != entity.parent:
            return False
        if self.state != entity.state:
            return False
        return True

    def __xml__(self):
        doc = Agent.__xml__(self)
        root = doc.documentElement
        # Beliefs
        node = doc.createElement('beliefs')
        root.appendChild(node)
        node.appendChild(self.entities.__xml__().documentElement)
        # Relationships
        node = doc.createElement('relationships')
        root.appendChild(node)
        for label,agents in self.relationships.items():
            relationshipNode = doc.createElement('relationship')
            node.appendChild(relationshipNode)
            relationshipNode.setAttribute('label',label)
            for name in agents:
                subNode = doc.createElement('relatee')
                subNode.appendChild(doc.createTextNode(name))
                relationshipNode.appendChild(subNode)
        if not self.parent:
            # Dynamics
            node = doc.createElement('dynamics')
            root.appendChild(node)
            for feature,subDict in self.dynamics.items():
                featureNode = doc.createElement('feature')
                node.appendChild(featureNode)
                featureNode.setAttribute('label',feature)
                for actType,dynamic in subDict.items():
                    if isinstance(actType,str) or actType is None:
                        # This test prevents the saving of compiled dynamics
                        actNode = doc.createElement('action')
                        featureNode.appendChild(actNode)
                        if actType:
                            # Not specified for default dynamics
                            actNode.setAttribute('type',actType)
                        if isinstance(dynamic,str):
                            dynamic = self.hierarchy[dynamic].dynamics[feature][actType]
                        if isinstance(dynamic,dict):
                            if dynamic['tree']:
                                actNode.appendChild(dynamic['condition'].__xml__().documentElement)
                                actNode.appendChild(dynamic['tree'].__xml__().documentElement)
                        elif not dynamic is None:
                            actNode.appendChild(dynamic.__xml__().documentElement)
        return doc

    def parse(self,element):
        """Extracts this agent's recursive belief structure from the given XML Element
        @type element: Element
        """
        Agent.parse(self,element)
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'beliefs':
                    node = child.firstChild
                    while node:
                        if node.nodeType == node.ELEMENT_NODE:
                            self.entities.parse(node,self.__class__)
                        node = node.nextSibling
                    for entity in self.entities.members():
                        entity.parent = self
                elif child.tagName == 'state':
                    self.state = Distribution()
                    subNodes = child.getElementsByTagName('distribution')
                    if len(subNodes) == 1:
                        self.state.parse(subNodes[0],KeyedVector)
                    elif len(subNodes) > 1:
                        raise UserWarning,'Multiple distributions in state of %s' % (self.ancestry())
                elif child.tagName == 'relationships':
                    node = child.firstChild
                    while node:
                        if node.nodeType == node.ELEMENT_NODE:
                            label = str(node.getAttribute('label'))
                            self.relationships[label] = []
                            subNode = node.firstChild
                            while subNode:
                                if subNode.nodeType == subNode.ELEMENT_NODE:
                                    assert(subNode.tagName == 'relatee')
                                    name = subNode.firstChild.data
                                    name = str(name).strip()
                                    self.relationships[label].append(name)
                                subNode = subNode.nextSibling
                        node = node.nextSibling
                elif child.tagName == 'dynamics':
                    node = child.firstChild
                    while node:
                        if node.nodeType == node.ELEMENT_NODE:
                            assert(node.tagName=='feature')
                            feature = str(node.getAttribute('label'))
                            self.dynamics[feature] = {}
                            subNode = node.firstChild
                            while subNode:
                                if subNode.nodeType == subNode.ELEMENT_NODE:
                                    assert(subNode.tagName=='action')
                                    actionType = str(subNode.getAttribute('type'))
                                    if not actionType:
                                        actionType = None
                                    condition = None
                                    assert(actionType not in self.dynamics[feature].keys())
                                    dyn = str(subNode.getAttribute('link'))
                                    if not dyn:
                                        subchild = subNode.firstChild
                                        while subchild:
                                            if subchild.nodeType == child.ELEMENT_NODE:
                                                if subchild.tagName == 'condition':
                                                    condition = ActionCondition()
                                                    condition.parse(subchild)
                                                elif subchild.tagName == 'tree':
                                                    dyn = ProbabilityTree()
                                                    dyn.parse(subchild)
                                                else:
                                                    # Backward compatibility
                                                    dyn = PWLDynamics()
                                                    dyn.parse(subchild)
                                            subchild = subchild.nextSibling
                                    if condition is None:
                                        # Backward compatibility
                                        condition = ActionCondition()
                                        if actionType:
                                            condition.addCondition(actionType)
                                    if isinstance(dyn,PWLDynamics):
                                        self.dynamics[feature][actionType] = dyn
                                    else:
                                        self.dynamics[feature][actionType] = {'condition': condition,'tree':dyn}
                                subNode = subNode.nextSibling
                        node = node.nextSibling
            child = child.nextSibling
        # Some post-processing
        for action in self.actions.getOptions():
            for subAct in action:
                subAct['actor'] = self.name
        if not self.policy:
            self.policy = PWLPolicy(self,self.actions,self.horizon)

def float2bar(value,positive=True):
    str = '<TABLE WIDTH="100%%" HEIGHT="100%%"><TR>'
    if positive:
        str += '<TD WIDTH="%d%%" BGCOLOR="#000000"></TD><TD></TD>' % (value*100.)
    else:
        if value > 0.:
            str += '<TD WIDTH="50%%"></TD>\n'
            str += '<TD WIDTH="%d%%" BGCOLOR="#000000"></TD><TD></TD>' % (value*50.)
        else:
            str += '<TD WIDTH="%d%%"></TD>\n' % ((value+1.)*50.)
            str += '<TD WIDTH="%d%%" BGCOLOR="#ff0000"></TD>' % (-value*50.)
            str += '<TD WIDTH="50%%"></TD>\n'
    str += '</TR></TABLE>'
    return str

def dictionaryDepth(beliefs,name):
    """
    @type beliefs: dict
    @type name: str
    @return: the depth to which the named agent's beliefs are stored in the given belief dictionary
    @rtype: int
    """
    try:
        beliefs = beliefs[name]
    except KeyError:
        return 0
    return dictionaryDepth(beliefs,name)+1

if __name__ == '__main__':
    import sys
    from unittest import TestResult
    from teamwork.test.agent.testRecursiveAgent import TestRecursiveAgentIraq

    if len(sys.argv) > 1:
        method = sys.argv[1]
    else:
        method = 'testLocalState'
    case = TestRecursiveAgentIraq(method)
    result = TestResult()
    case(result)
    for failure in result.errors+result.failures:
        print failure[1]
