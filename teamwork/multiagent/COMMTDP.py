 ###########################################################################
 # 11/5/2001: David V. Pynadath (pynadath@isi.edu)
 #
 # Agent: generic class for defining an agent and its capabilities
 #
 # Team: generic class for defining a team of agents
 #
 # ComMTDP: the COM-MTDP class
 # 
 ###########################################################################
import copy
import string
from types import *

##from teamwork.state.States import StateSpace
##from teamwork.state.States import EnumeratedSubspace

def strip(state):
    s = {}
    for key in state.keys():
        if key[0] != '_':
            s[key] = state[key]
    return s
    
class ComMTDP:
    version = 1.0
    def __init__(self,states,team,name='Generic COM-MTDP'):
	self.states = states
	self.team = team
	self.agents = []
	for agent in self.team.agents.keys():
	    self.agents.append(self.team.agents[agent])
	self.name = name

    # R
    def reward(self,state,actions,messages):
	return self.rewardAct(state,actions) + \
	       self.rewardCom(state,messages)

    # R_A
    def rewardAct(self,state,actions):
        raise NotImplementedError

    # R_Sigma
    def rewardCom(self,state,messages):
        raise NotImplementedError

    # P
    def probability(self,orig,dest,actions):
        raise NotImplementedError

    def evaluatePolicy(self,domPolicy,comPolicy,state,horizon=100,debug=0):
	"""Computes expected reward of following the domain- and
	communication-level policies over the finite horizon
	specified, from the initial state specified"""
	# Create state of execution, which includes state of the
	# world, as well as belief states of individual agents
	stateList = [{'_world': state,'_prob':1.0,'_value':0.0,
                      '_actions':{},'_epoch':0}]
	for s in stateList:
	    for agent in self.agents:
		s[agent.name] = agent.initialStateEstimator()
	return self.__evaluatePolicy(stateList,domPolicy,comPolicy,
                                    horizon,debug)
        
    def __evaluatePolicy(self,stateList,domPolicy,comPolicy,horizon,debug):
        results = {'Reward':0.0,
                   'Messages':0.0}
        if len(stateList) == 0:
            return results
	for epoch in range(stateList[0]['_epoch'],horizon):
	    if debug:
		print '========='
		print 'Epoch',epoch
		print '========='
            self.ProjectObservations(stateList,None,[],epoch,debug)
            results['Messages'] = results['Messages'] + \
                                  self.ExecuteCommunication(stateList,
                                                            comPolicy,debug)
            results['Reward'] = results['Reward'] \
                                + self.ExecuteActions(stateList,domPolicy,
                                                      debug)
            self.ProjectWorldDynamics(stateList)
	if debug:
	    print 'EValue:',results['Reward']
            print '# Msgs:',results['Messages']
	return results

    def __generateTeamMessages(self,state,agents,msgList):
        """Generates all possible messages over all agents"""
        if len(agents) == 0:
            return msgList
        else:
            # Generate set of possible messages for the current agent
            agent = agents[0]
            for teamMsg in msgList[:]:
                for msg in agent.legalMessages(state[agent.name]):
                    newMsg = copy.copy(teamMsg)
                    if msg:
                        newMsg[agent.name] = msg
                    msgList.append(newMsg)
                msgList.remove(teamMsg)
            agents.remove(agent)
            return self.__generateTeamMessages(state,agents,msgList)
        
    def __generateTeamObservations(self,state,actions,agents,obsList,debug=0):
	"""Generates all possible observations over all agents"""
	if len(agents) == 0:
	    return obsList
	else:
	    # Find the current agent's observations
	    agent = agents[0]
	    agentObsList = [{'_type':'observation'}]
	    self.__generateAgentObservations(state,actions,agent,self.states.features.keys()[:],agentObsList,debug)
	    # Compose this list with current list of possible observations
	    for obs in obsList[:]:
		obsList.remove(obs)
		for agentObs in agentObsList:
		    newObs = copy.copy(obs)
		    newObs[agent.name] = agentObs
		    newObs['_prob'] = newObs['_prob'] * \
				      self.team.individualObs(state,actions,agentObs,agent.name)
		    if newObs['_prob'] > 0.0:
			obsList.append(newObs)
	    agents.remove(agent)
	    return self.__generateTeamObservations(state,actions,agents,obsList)

    def __generateAgentObservations(self,state,actions,agent,
				   features,observations,debug=0):
	"""Generates all possible observations for an individual agent"""
	if len(features) == 0:
	    if debug:
		print 'Agent',agent.name,'observes:',observations
	    return observations
	else:
	    feature = features[0]
	    if agent.observations.has_key(feature):
		if agent.observations[feature] == 'observable':
		    # For observable features, there is only one
		    # possible observation
		    for obs in observations:
			obs[feature] = state[feature]
		else:
		    # For partially observable features, we must
		    # consider all of the possible observations and
		    # their probabilities.
		    for obs in observations[:]:
			observations.remove(obs)
			for value in agent.observations[feature]:
			    newObs = copy.copy(obs)
			    newObs[feature] = value
			    observations.append(newObs)
	    else:
		# Feature is unobservable
		pass
	    features.remove(feature)
	    return self.__generateAgentObservations(state,actions,
						   agent,features,
						   observations)			
    def computeBeliefState(self,states,agent,policy,history):
	"""Partially implemented"""
	stateList = []
	for state in states:
	    stateList.append({'_world': state,'_prob':1.0,'_value':0.0,
			      '_actions':{},'_epoch':0})
	self.ProjectObservations(states,agent,history,0,1)

    def bestAction(self,agent,history,horizon,policyOthers):
	choice = self.team.agents[agent].actions[0]
	best = self.valueHistory(agent,history,horizon,choice)
	for action in self.team.agents[agent].actions[1:]:
	    value = self.valueHistory(agent,history,horizon,action)
	    if value > best:
		best = value
		choice = action
	return choice

    def valueHistory(self,agent,history,horizon,action,policyOthers):
	value = 0.0
	# Iterate through each state
	state = self.states.getFirstState()
	while state:
	    # Compute conditional probability of state given specified history 
	    # and policy of other agents
	    belief = self.computeBelief(state,agent,history,policyOthers)
	    # Consider all possible team actions consistent with the specified 
	    # action choice
	    for actionStr in self.team.generateAllActions({agent:action}):
		actionTeam = self.team.decomposeActions(actionStr)
		# Compute the probability of this state-action pair
		prob = belief * self.probAction(actionOthers,agent,history,
						state)
		# Increase value by expected reward
		value = value + prob * self.reward(state,actionTeam)
		# If looking into future, consider possible state transitions
		if horizon > 1:
		    pass
	    state = self.states.getNextState(state)
	return value
	
    def ProjectObservations(self,states,agent=None,beliefs=[],
                            epoch=-1,debug=0):
        # Observation phase
        if debug:
            print
            print '--------'
            print 'Observation phase:'
        for s in states[:]:
            if debug:
                print '--------'
                print 'Examining state:',strip(s['_world'])
            # Draw observations of initial world state (under no actions)
            observations = [{'_prob':1.0}]
            self.__generateTeamObservations(s['_world'],s['_actions'],
                                           self.agents[:],observations,
                                           debug)
            if debug:
                print 'Possible observations:'
                for obs in observations:
                    print '\t',strip(obs)
            # Eliminate observations inconsistent with state
            for belief in beliefs:
                if belief['_type'] == 'observation' and \
                   belief['_epoch'] == epoch:
                    totalProb = 0.0
                    break
            else:
                totalProb = 1.0
                belief = None
            if belief:
                for obs in observations[:]:
                    for feature in obs[agent].keys():
                        if feature[0] != '_' and \
                           obs[agent][feature] != belief[feature]:
                            break
                    else:
                        feature = None
                    if feature:
                        # Observation is inconsistent
                        observations.remove(obs)
                    else:
                        # Observation is consistent
                        totalProb = totalProb + obs['_prob']
            if len(observations) == 0:
                # The state itself is inconsistent with observations
                for state in states:
                    if not state is s:
                        state['_prob'] = state['_prob'] / (1.0 - s['_prob'])
            else:
                # Update belief state based on new observations
                if s.has_key('_parent'):
                    s['_children'] = []
                for obs in observations:
                    newState = copy.copy(s)
                    for a in self.agents:
                        newState[a.name] = a.preComStateEstimator(s[a.name],obs[a.name],epoch)
                    # Use normalized probability
                    newState['_prob'] = newState['_prob'] \
                                        * obs['_prob'] / totalProb
                    if s.has_key('_parent'):
                        newState['_parent'] = s
                        s['_children'].append(newState)
                    states.append(newState)
            states.remove(s)

    def ExecuteCommunication(self,states,comPolicy,debug=0):
        # Communication phase
        if debug:
            print
            print '--------'
            print 'Communication phase:'
        msgCount = 0.0
        for s in states[:]:
            if debug:
                print '--------'
                print 'Examining state:',strip(s)
            if comPolicy:
                # Execute each agent's communication policy to
                # generate set of messages
                messages = [{'_type':'message'}]
                for agent in self.agents:
                    contents = comPolicy[agent.name].execute(s[agent.name])
                    if not contents or type(contents) is StringType:
                        contents = [contents]
                    for msg in messages[:]:
                        for content in contents:
                            newMsg = copy.copy(msg)
                            if content:
                                newMsg[agent.name] = content
                                msgCount = msgCount + s['_prob']
                            messages.append(newMsg)
                        messages.remove(msg)
            else:
                # Generate all possible messages
		messages = self.__generateTeamMessages(s,self.agents[:],[{}])
            if s.has_key('_parent'):
                s['_children'] = {}
            for msg in messages:
                newState = copy.copy(s)
                msg['_type'] = 'message'
                if debug:
                    print 'Messages:',strip(msg)
                # Update agents' beliefs based on messages exchanged
                for agent in self.agents:
                    newState[agent.name] = agent.postComStateEstimator(s[agent.name],msg,s['_epoch'])
                # Update value based on communication cost
                newState['_value'] = self.rewardCom(s['_world'],msg)
                newState['_messages'] = msg
                if s.has_key('_parent'):
                    newState['_parent'] = s
                    s['_children'][`msg`] = newState
                states.append(newState)
            states.remove(s)
        return msgCount

    def ExecuteActions(self,states,domPolicy,debug=0):
        # Action phase
        if debug:
            print
            print '--------'
            print 'Action phase:'
        value = 0.0
        for s in states[:]:
            if debug:
                print '--------'
                print 'Examining state:',strip(s['_world'])
                print 'Beliefs:',strip(s)
            # Execute each agent's domain-level policy to
            # generate set of actions
            s['_actions'] = {}
            for agent in self.agents:
                act = domPolicy[agent.name].execute(s[agent.name])
                if act:
                    s['_actions'][agent.name] = act
            if debug:
                print 'Actions:',s['_actions']
            # Update value based on action cost
            s['_value'] = s['_value'] \
                          + self.rewardAct(s['_world'],s['_actions'])
            # Update overall value
            value = value + s['_prob'] * s['_value']
            if debug:
                print 'Reward:',s['_value']
        return value

    def ProjectWorldDynamics(self,states,debug=0):
        # World Dynamics phase
        if debug:
            print
            print '--------'
            print 'World dynamics phase:'
        for s in states[:]:
            if debug:
                print '--------'
                print 'Examining state:',strip(s['_world'])
                print 'Beliefs:',strip(s)
            orig = self.states.state2index(s['_world'])
            action = self.team.composeActions(s['_actions'])
            if s.has_key('_parent'):
                s['_children'] = {}
            for dest in self.states.children[orig][action]:
                destState = self.states.index2state(dest)
                newState = copy.copy(s)
                newState['_world'] = destState
                newState['_epoch'] = newState['_epoch'] + 1
                newState['_prob'] = s['_prob'] \
                                    * self.probability(s['_world'],
                                                       destState,action)
                if s.has_key('_parent'):
                    newState['_parent'] = s
                    s['_children'][action] = newState
                try:
                    del newState['_messages']
                except KeyError:
                    pass
                states.append(newState)
            states.remove(s)
	
    def updateBeliefs(self,world,beliefs,agent):
	"""Generates all possible new belief states for an agent"""
	raise NotImplementedError
