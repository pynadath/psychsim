from teamwork.agent.DefaultBased import * 
from teamwork.agent.Entities import *
from teamwork.multiagent.sequential import *
from teamwork.multiagent.GenericSociety import *
from teamwork.action.PsychActions import *

from teamwork.dynamics.pwlDynamics import *
from teamwork.policy.policyTable import PolicyTable

sceneID = 3

class ThespianAgent(PsychEntity):
##    actionClass = ThespianAction
##    beliefClass = ThespianAgents

    def observe(self,actionDict={}):
        """
        @param actionDict: the performed actions, indexed by actor name
        @type actionDict: C{dict:strS{->}L{Action}[]}
        @return: observations this entity would make of the given actions, in the same format as the provided action dictionary
        @rtype: C{dict}
        """
        observations = {}
        for actor,action in actionDict.items():
            # mei 08/07/15 can't over action that happen at other locations
            #try:
            #    if not self.getBelief(actor,'location').expectation()== self.getState('location').expectation():
            #        continue
            #except:
            #    pass
            if actor == self.name:
                # Always observe our own actions (I assume this is OK)
                observations[actor] = action
            else:
                observation = []
                for subAct in action:
                    if subAct.has_key('_observed'):
                        # Forced to observe
                        if self.name in subAct['_observed']:
                            observation.append(subAct)
                            continue
                    if subAct.has_key('_unobserved'):
                        # Forced to *not* observe
                        if self.name in subAct['_unobserved']:
                            continue
                    if subAct['object'] == self.name:
                        # Always observe actions directed at
                        # ourselves (this is questionable)
                        observation.append(subAct)
                    else:
                        # Check whether we can observe this actor's acts
                        for omega,entries in self.observations.items():
                            if str(subAct) == omega:
                                for entry in entries.keys():
                                    if subAct.matchTemplate(entry):
                                        if entry['_observable']:
                                            # We can definitely observe this
                                            observation.append(subAct)
                                        else:
                                            # We can definitely *not* observe
                                            pass
                                        break
                                else:
                                    # No matching action generates this observation
                                    break
                        else:
                            # By default, assume observable
                            observation.append(subAct)
                if len(observation) > 0:
                    # Only add observations if we have any (questionable?)
                    observations[actor] = observation
        return observations
    
    
    def applyPolicy(self,state=None,actions=[],history=None,debug=None,
                    explain=False):
        """Generates a decision chosen according to the agent's current policy
        @param state: the current state vector
        @type state: L{Distribution}(L{KeyedVector})
        @param actions: the possible actions the agent can consider (defaults to all available actions)
        @type actions: L{Action}[]
        @param history: a dictionary of actions that have already been performed (and which should not be performed again if they are labeled as not repeatable)
        @type history: L{Action}[]:bool
        @param explain: flag indicating whether an explanation should be generated
        @type explain: bool
        @return: a list of actions and an explanation, the latter provided by L{execute<PolicyTable.execute>}
        @rtype: C{(L{Action}[],Element)}
        """
        if state is None:
            state = self.getAllBeliefs()
        
        ##07/10/08 mei added to prevent the agent considering actions that should not happen
        if len(actions) == 1:
            pass
        else:
            actions = self.actions.getOptions()
            actions = self.updateActionChoices(actions,state)
        
        return self.policy.execute(state=state,choices=actions,
                                   history=history,debug=debug,explain=explain)
    
    
    def updateActionChoices(self,choices,state=None,includeLocation = False):
        
        if sceneID == 7:
            return self.updateActionChoices7(choices,state)
        
        if not state:
            state=self.getAllBeliefs()
            
        actions = []
        
        key = StateKey({'entity':self.name,'feature':'power'})
        selfLocation = state['state'].getMarginal(key).expectation()
        if selfLocation == 0:
            actions.append([Action({'actor':self.name,'type':'wait'})])
            return actions
        
        if self.name in ['red','granny']:
            key = StateKey({'entity':self.name,'feature':'eaten'})
            selfEaten = state['state'].getMarginal(key).expectation()
            if selfEaten >= 1:
                try:
                    key = StateKey({'entity':'wolf','feature':'alive'})
                    wolfAlive = state['state'].getMarginal(key).expectation()
                    if wolfAlive <=0:
                        actions.append([Action({'actor':self.name,'type':'escape','object':'wolf'})])
                except:
                    pass
                actions.append([Action({'actor':self.name,'type':'wait'})])
                return actions
        
        
        if self.name in ['wolf','red']:
            key = StateKey({'entity':self.name,'feature':'alive'})
            selfAlive = state['state'].getMarginal(key).expectation()
            if selfAlive <=0:
                actions.append([Action({'actor':self.name,'type':'wait'})])
                return actions
        
        
        for option in choices:
            if option[0]['type'] == 'escape':
                continue
            
            if option[0]['type'] in ['give-cake','eat-cake']:
                key = StateKey({'entity':self.name,'feature':'has-cake'})
                selfHasCake = state['state'].getMarginal(key).expectation()  
                if selfHasCake < 1:
                    continue
            
            #if option[0]['type'] in ['moveto-granny'] and self.name == 'wolf':
            #    key = StateKey({'entity':self.name,'feature':'know-granny'})
            #    selfKnowGranny = state['state'].getMarginal(key).expectation()
            #    if selfKnowGranny <1:
            #        continue
            #
            #if option[0]['type'] == 'moveto-granny':
            #    key = StateKey({'entity':self.name,'feature':'location'})
            #    selfLocation = state['state'].getMarginal(key).expectation()
            #    key = StateKey({'entity':'granny','feature':'location'})
            #    grannyLocation = state['state'].getMarginal(key).expectation()
            #    #print 'selfLocation, grannyLocation: ', selfLocation,grannyLocation
            #    if selfLocation == grannyLocation:
            #        continue
            
            if not option[0].has_key('object'):
                type = option[0]['type']
                if type.find('move')>-1 or type.find('enter')>-1:
                    key = StateKey({'entity':self.name,'feature':'indoor'})
                    selfLocation = state['state'].getMarginal(key).expectation()
                    if selfLocation>.5:
                        continue
                if type.find('exist')>-1:
                    key = StateKey({'entity':self.name,'feature':'indoor'})
                    selfLocation = state['state'].getMarginal(key).expectation()
                    if selfLocation<.5:
                        continue
                actions.append(option)
                
            
            key = StateKey({'entity':self.name,'feature':'location'})
            selfLocation = state['state'].getMarginal(key).expectation()
            key = StateKey({'entity':option[0]['object'],'feature':'location'})
            objectLocation = state['state'].getMarginal(key).expectation()
            if not abs(selfLocation - objectLocation)<0.0001:
                continue
                
            if option[0]['object'] in ['wolf','red']:    
                key = StateKey({'entity':option[0]['object'],'feature':'alive'})
                objectAlive = state['state'].getMarginal(key).expectation()  
                if objectAlive <=0:
                    continue
            
            if option[0]['object'] in ['red','granny']:    
                key = StateKey({'entity':option[0]['object'],'feature':'eaten'})
                objectEaten = state['state'].getMarginal(key).expectation()  
                if objectEaten >0:
                    continue
            
            #if includeLocation == True:
            #    key = StateKey({'entity':self.name,'feature':option[0]['object']+'Location'})
            #    objectLocation = state['state'].getMarginal(key).expectation()
            #    if not abs(selfLocation - objectLocation)<0.001:
            #        continue
                        

   
            if option[0]['type'] == 'inform':
                key = StateKey({'entity':self.name,'feature':'being-enquired'})
                selfEnquired = state['state'].getMarginal(key).expectation()  
                if selfEnquired <1:
                    continue
                obj = option[0]['object']
                key = StateKey({'entity':obj,'feature':'enquired'})
                objEnquired = state['state'].getMarginal(key).expectation()
                if not objEnquired >.5:
                    continue
            
            if option[0]['type'] == 'help' and self.name=='wolf':
                key = StateKey({'entity':self.name,'feature':'helped'})
                selfHelped = state['state'].getMarginal(key).expectation()
                # can only help the woodcutter once
                if selfHelped >.5:
                    continue
        
            if option[0]['type'] in ['eat'] and option[0]['object'] == 'granny':
                key = StateKey({'entity':self.name,'feature':'know-granny'})
                selfKnowGranny = state['state'].getMarginal(key).expectation()
                #if wolf don't know granny, but accidently decide to enter the house, he can eat granny
                if selfKnowGranny < 1:
                    continue
                key = StateKey({'entity':self.name,'feature':'indoor'})
                selfIndoor = state['state'].getMarginal(key).expectation()
                if selfIndoor < 1:
                    continue
            
            if option[0]['type'] in ['talkabout-granny']:
                key = StateKey({'entity':'wolf','feature':'know-granny'})
                wolfKnowGranny = state['state'].getMarginal(key).expectation()
                if wolfKnowGranny >.5:
                    continue
            
                
            actions.append(option)
        
        
        return actions

            
            #actionDict = {}
            #actionDict[actor] = option
            #result = self.entities.hypotheticalAct(actionDict)
            #
            #feasibleAction = True
            #for value,prob in result['state'].items():
            #    for key in value:
            #        try:
            #            if key['entity'] == actor and key['feature']== 'actAliveNorm':
            #                if value[key][keyConstant] < 0:
            #                    feasibleAction = False
            #            elif key['entity'] == actor and key['feature']== 'resp-norm':
            #                if value[key][keyConstant] < 0:
            #                    feasibleAction = False       
            #            elif key['entity'] == actor and key['feature']== 'specialRule':
            #                if value[key][keyConstant] < 0:
            #                    #print option[0], key, value[key][keyConstant]
            #                    feasibleAction = False       
            #        except:
            #            pass
            #
            #if not feasibleAction:
            #    option[0]['active']=0
                    
    def updateActionChoices7(self,choices,state=None,includeLocation = False):
        convert={'unsafesex':1,'safesex':2,'drink':3,'physicaltouch':4}
        
        if not state:
            state=self.getAllBeliefs()    
        actions = []
        
        for option in choices:
            
            if option[0]['type'].find('accept')>-1 or option[0]['type'].find('reject')>-1:
                key = StateKey({'entity':self.name,'feature':'topic'})
                topic = state['state'].getMarginal(key).expectation()
                if topic == 0:
                    continue
            
                offer,thisTopic = string.split(option[0]['type'],'-')
                if not convert[thisTopic] == topic:
                    continue               
            
            actions.append(option)
        
        
        return actions

                    
##  07/01/07 mei modified to count fixedActions
##  fixedActions=[{'red-move2':[Action({'actor':'wolf','type':'wait'})]}]
##  fixedActions = []
    #def multistep(self,horizon=1,start={},state=None,debug=Debugger()):
    #    """Steps this entity the specified number of steps into the future (where a step is one entity performing its policy-specified action)
    #    @param state: the world state to evaluate the actions in (defaults to current world state)
    #    @type state: L{Distribution}(L{KeyedVector})
    #    @warning: This method still needs to be handed an updated turn vector
    #    """
    #    if state is None:
    #        state = self.getAllBeliefs()
    #    sequence = []
    #    # Lookahead
    #    for t in range(horizon):
    #        debug.message(9,'Time %d' % (t))
    #        if t == 0:
    #            entityDict = start
    #        else:
    #            entityDict = {}
    #        nextGroup = self.entities.next(state['turn'])
    #        for entity in nextGroup:                 
    #            if isinstance(entity,dict):
    #                try:
    #                    choices = entity['choices']
    #                except KeyError:
    #                    choices = []
    #                entity = entity['name']
    #            else:
    #                raise DeprecationWarning,'Turns should be expressed in dictionary form'
    #
    #            ## give the fixed action specified in $fixedActions$ as the agent's only choice
    #            if len(sequence)>0:
    #                lastAct = max(sequence)['action']
    #                for lastActor in lastAct:
    #                    tmp = lastAct[lastActor][0]
    #                lastAct = `tmp`
    #            else:
    #                lastAct = ''
    #            
    #            for fixedAction in self.fixedActions:
    #                if fixedAction.has_key(lastAct) :
    #                    entityDict[entity] = fixedAction[lastAct]
    #                    break
    #            else:
    #                if len(entityDict) < len(nextGroup) and \
    #                   not entityDict.has_key(entity):
    #                    entityDict[entity] = choices
    #        # Apply these entities' actions
    #        delta = self.step(entityDict,state,debug)
    #        self.updateStateDict(state,delta['effect'])
    #        # Accumulate results
    #        sequence.append(delta)
    #    return sequence


    def forceinitState(self):
        """Instantiates all of the state defaults relevant to this entity"""
        """do not check if the feature has already been set"""
        for cls in self.classes:
            try:
                featureList = self.hierarchy[cls].getStateFeatures()
            except KeyError:
                featureList = []
            for feature in featureList:
                value = self.hierarchy[cls].getState(feature)
                self.setState(feature,value)
        self.setModel(None)


    def fitAllAction(self,horizon=-1,state=None):
        """Computes a set of constraints on possible goal weights for this agent that, if satisfied, will cause the agent to prefer the desired action in the given state.  Each constraint is dictionary with the following elements:
           - delta: the total difference that must be made up
           - slope: dictionary of coefficients for each goal weight in the sum that must make up that difference
           - plane: the vector of weights, such that the product of this vector and the goal weight vector must exceed 0 for the desired action to be preferred
        @param desired: the action that the agent should prefer
        @type desired: L{Action}[]
        @param horizon: the horizon of lookahead to use (if not provided, the agent's default horizon is used)
        @type horizon: int
        @param state: the current state of this agent's beliefs (if not provided, defaults to the result of L{getAllBeliefs}
        @type state: dict
        @return: a list of constraints
        @rtype: dict[]
        """
        if horizon < 0:
            horizon = self.horizon
        if state is None:
            state = self.getAllBeliefs()
        goals = self.getGoalVector()['total']
        if len(goals.domain()) != 1:
            raise NotImplementedError,\
                  'Unable to handle uncertain goals when fitting'
        goals = goals.domain()[0]
        # Compute projections for all actions
        matrices = {}
        for action in self.actions.getOptions():
            sequence = self.multistep(horizon=horizon,
                                      start={self.name:action},
                                      state=copy.deepcopy(state))
            value = None
            if self.valueType == 'average':
                for t in range(len(sequence)):
                    # For now, assume no uncertainty
                    assert len(sequence[t]['state'].domain()) == 1
                    current = copy.deepcopy(sequence[t]['state'].domain()[0])
                    # Add in current state
                    if value is None:
                        value = current
                    else:
                        current.unfreeze()
                        current.fill(value.keys())
                        current.freeze()
                        value += current
                    # Add in relevant actions
                    for key in filter(lambda k:isinstance(k,ObservationKey),
                                      goals.keys()):
                        if not value.has_key(key):
                            value.unfreeze()
                            value[key] = 0.
                            value.freeze()
                        for act in sum(sequence[t]['action'].values(),[]):
                            if act['type'] == key['type']:
                                value[key] += 1.
            elif self.valueType == 'final':
                # Assume no action goals if we care about only the final state
                value = sequence[-1]['state']
            else:
                raise NotImplementedError,\
                      'I do not know how to fit "%s" expected value' \
                      % (self.valueType)
            matrices[str(action)] = value
            
        # Compare against desired action
        # added by mei: generate constraints for each possible action
        allConstraints = {}
        for desired in self.actions.getOptions():
            constraints = []
            for action in self.actions.getOptions():
                if action != desired:
                    projection = matrices[str(desired)] - matrices[str(action)]
                    goals.fill(projection.keys())
                    diff = goals*projection
                    constraint = {'delta':diff,
                                  'value':True,
                                  'slope':{},
                                  }
                    for key in goals.keys():
                        constraint['slope'][key] = projection[key]
                    constraints.append(constraint)
            allConstraints[str(desired)] = constraints
        return allConstraints


    def applyRealGoals(self,entity=None,world=None,debug=Debugger(),fixedgoals=['sameLocation','actAlive','specialRule']):
        """
        @param entity: the entity whose goals are to be evaluated (default is self)
        @type entity: L{GoalBasedAgent}
        @param world: the context for evaluating the goals (default is the beliefs of I{entity})
        @type world: L{teamwork.multiagent.PsychAgents.PsychAgents}
        @return: expected reward of the I{entity} in current I{world}
        @rtype: L{Distribution} over C{float}"""
        if not entity:
            entity = self
        if world is None:
            world = self.entities
        state = world.getState()
        goals = entity.getGoalVector()
        
        ## mei modified
        ## only real goals take effect
        gstate = goals['state']
        for item, prob in gstate.items():
            del gstate[item]
            for goal in fixedgoals:
                key = StateKey({'entity':self.name,'feature':goal})
                try:
                    item.__delitem__(key)
                except:
                    pass
            gstate[item] = prob
            
        goals['state'].fill(state.domain()[0].keys(),0.)

        return goals['state']*state
    
    
    def getDefault(self,feature):
        """Finds the most specific class defaults for the specified
        feature; raises KeyError exception if no default exists"""
        if self.hierarchy is None:
            # Duh, no defaults
            raise KeyError,'%s has no feature %s' % (self.name,feature)
        result = None
        last = None
        for cls in self.classes:
            # Check object attributes
            try:
                result = self.hierarchy[cls].__dict__[feature]
            except KeyError:
                # Check special attributes
                try:
                    result = self.hierarchy[cls].attributes[feature]
                except KeyError:
                    # Nothing here
                    continue
            if feature in ['models','dynamics']:
                # Empty values don't count
                if len(result) > 0:
                    break
            elif feature == 'imageName':
                if result is not None:
                    break
            elif feature == 'actions':
                if result.branchType:
                    # Can't really merge AND/OR decision spaces
                    break
                elif last is None:
                    last = result
                else:
                    # Merge in any extras
                    last = copy.deepcopy(last)
                    for option in result.extras:
                        last.directAdd(option)
                    result = last
            # mei commented out to get depth specified in classHierachy take effect
            #elif feature == 'depth':
            #    # Belief depth is MINIMUM across all default values
            #    if last is None:
            #        last = result
            #    else:
            #        last = min(last,result)
            #        result = last
            else:
                # For everything else, the first thing
                break
        if result is None:
            if feature == 'actions':
                pass
            else:
                raise KeyError,'%s has no feature %s' % (self.name,feature)
        return result

    def initGoals(self,entities=[]):
        """Sets the goal weights of this entity based on class
        defaults.  The resulting goals depend on the group of entities
        passed in as the optional argument."""
##        added by mei
        if self.getGoals():
            return
        
        goals = []
        # First, figure out the relevant goals and their total weight
        # (for normalization)
        keys = []
        for cls in self.classes:
            for goal in self.hierarchy[cls].getGoals():
                goalList = self.instantiateGoal(goal,entities)
                for subGoal in goalList:
                    key = str(subGoal)
                    try:
                        index = keys.index(key)
                        goals[index].weight += subGoal.weight
                    except ValueError:
                        keys.append(key)
                        goals.append(subGoal)
        if len(goals) > 0:
            # Then, add goal with normalized weight
            self.setGoals(goals)

    def initEntities(self,entityList,depth=1,maxDepth=-1):
        """Sets the entities known to be the list provided, and makes
        the appropriate updates to goals, policy depth, etc."""
##      added maxDepth param by mei
        # Fill out recursive beliefs
        
        if maxDepth == -1:
            ## I am the top level agent, use my beliefs
            maxDepth = self.getDefault('depth')
        
        #print self.ancestry(),depth,maxDepth
        
        if depth <= maxDepth:
            newList = []
            # First, generate entity objects for my beliefs
            for entity in entityList:
                newEntity = copy.copy(entity)
                newEntity.dynamics = copy.deepcopy(entity.dynamics)
                # Stick this entity object into my beliefs
                self.setEntity(newEntity)
                newList.append(newEntity)
                # Assume correct beliefs about states
                for feature in entity.getStateFeatures():
                    try:
                        value = entity.getState(feature)
                        newEntity.setState(feature,value)
                    except KeyError:
                        pass
            # Finally, fill in specific beliefs according to my class
            # defaults, and go to the next recursive level
            for entity in newList:
                self.initBeliefs(entity)
                if maxDepth-depth > entity.getDefault('depth'):
                    ##if the depth needed by the top level agent is more than the entity's max
                    ##level of beliefs allowed
                    newMaxDepth = depth + entity.getDefault('depth')
                else:
                    newMaxDepth = maxDepth

                entity.initEntities(newList,depth+1,newMaxDepth)
        # Add any goals related to the new entities
        self.initGoals(entityList)
        # Set the depth of lookahead
        agents = []
        for agent in entityList:
            if len(agent.actions.getOptions()) > 0:
                agents.append(agent)
        self.horizon = self.getDefault('horizon')*len(agents)
        if not self.policy:
##            print self.name
##            self.policy = PWLPolicy(self,self.actions,
##                                    len(entityList),self.horizon)
            self.policy = PolicyTable(self,self.actions,self.horizon)
        self.entities.initializeOrder()
        self.entities.state.freeze()
        

    def getDynamics(self,act,feature=None):
        """Returns this entity's dynamics model for the given action
        @param act: the action whose effect we are interested in
        @type act: L{Action}
        @param feature: if the optional feature argument is provided, then this method returns the dynamics for only the given feature; otherwise, returns the effect over all state features (but this latter capability is now deprecated)
        @type feature: C{str}
        @rtype: L{PWLDynamics}
        """
        if feature:
            try:
                # Try to find dynamics specific to this particular action
                dynFun = self.dynamics[feature][act]
            except KeyError:
                # If not, find a more general dynamics and then instantiate
                try:
                    ## added by mei
                    dynFun = self.dynamics[feature][`act`]
                except KeyError:
                    try:
                        dynFun = self.dynamics[feature][act['type']]
                    except KeyError:
                        try:
                            dynFun = self.dynamics[feature][None]
                        except KeyError:
                            # It's OK for an action to have no dynamics
                            # (e.g., the "wait" action)
                            if not self.dynamics.has_key(feature):
                                self.dynamics[feature] = {}
                            dynFun = IdentityDynamics(feature)
                    
                dynFun = dynFun.instantiate(self,act)
                # Check whether dynamics is well formed
                vector = self.state.domain()[0]
                for leaf in dynFun.getTree().leaves():
                    for key in leaf.rowKeys():
                        if not vector.has_key(key):
                            pass
##                            print 'Dynamics of %s\'s %s in response to %s has extraneous key, %s' % (self.ancestry(),feature,str(act),str(key))
                    for key in leaf.colKeys():
                        if not vector.has_key(key):
                            pass
##                            print 'Dynamics of %s\'s %s in response to %s has extraneous key, %s' % (self.ancestry(),feature,str(act),str(key))
                for branch in dynFun.getTree().branches().values():
                    if not isinstance(branch,Distribution):
                        for key in branch.weights.keys():
                            if not vector.has_key(key):
                                pass
##                                print 'Dynamics of %s\'s %s in response to %s has extraneous key, %s' % (self.ancestry(),feature,str(act),str(key))
                self.dynamics[feature][act] = dynFun
        else:
            raise DeprecationWarning,'Do not compute dynamics over an entire action at the individual agent level'
        return dynFun
    

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
                # mei editted for testing, exception in acceptMessage
                #acceptance,accExp = self.acceptMessage(entity,msg,debug)
                acceptance = True
                subExp['decision'] = acceptance
                subExp['breakdown'] = {}
                #subExp['breakdown'] = accExp
                if acceptance:
                    # Update beliefs if accepting message
                    debug.message(4,'%s accepts %s' % (self.ancestry(),
                                                       label))
                    delta,subExp = self.incorporateMessage(msg)
                    if explanation[sender]['effect'] is None:
                        explanation[sender]['effect'] = delta
                    else:
                        raise NotImplementedError,'Currently unable to incorporate multiple messages from the same sender'


                    ## mei added
                    ## update all my beliefs recursively
                    for entity in self.entities:
                        previous = copy.copy(msg['force'])
                        msg.forceAccept()
                        self.entities[entity].postComStateEstimator(beliefs[entity],{sender:[msg]},
                                                     epoch,debug)
                        msg['force'] = previous



                    self.updateTrust(sender,explanation[sender]['effect'],
                                     True)
                    # Update any beliefs about myself
                    try:
                        entity = self.getEntity(self.name)
                    except KeyError:
                        entity = None
                    if entity:
                        previous = copy.copy(msg['force'])
                        msg.forceAccept()
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



        
##    def applyDefaults(self,className=None,hierarchy=None):
##        """Applies the generic model in the society of the given class name"""
##
##        PsychEntity.applyDefaults(self,className,hierarchy)
##        if self.option_messages:
##            for msg in self.getDefault('option_messages'):
##                msg1 = ThespianMessage (msg)
##    ##            self.option_messages.append(msg1)
##                ## directly add messages as options
##                self.actions.directAdd([msg1])
##    ##        print self.name
##    ##        print self.actions.getOptions()
##    ##        print
##
##
##
##    def __repr__(self):
##        """Returns a string representation of this entity"""
##        content = PsychEntity.__repr__(self)
##        if self.option_messages:
##            content += '\n\tOption_messages:\n'
##            content += '\t\t'+`self.option_messages`
##        return content


