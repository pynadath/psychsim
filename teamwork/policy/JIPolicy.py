 ###########################################################################
 # 11/5/2001: David V. Pynadath, USC Information Sciences Institute
 #            pynadath@isi.edu
 #
 # JIPolicy: generic class for a communication policy, where there is
 #           a single possible message and it refers to the
 #           achievement of some joint goal
 # STEAMPolicy: a subclass of joint intentions policies, but following 
 #           the STEAM algorithm for decision-theoretic selectivity
 # SilentPolicy: a generic policy class that never specifies communication
 # BestAvailablePolicy: a generic communication policy class that
 #           searches a space of candidate policies and finds the best 
 #           one for a given COM-MTDP.
 # GloballyOptimalJIPolicy: a subclass of joint intentions policies
 #           that performs a brute force search to determine the best
 #           policy of communication, in reference to a single JPG
 # SingleMsgPolicy: a subclass of joint intentions policies that
 #           generates all possible communication behaviors for an
 #           agent with a single joint commitment (this class is no
 #           longer very useful)
 # LocallyOptimalJIPolicy: a subclass of joint intentions policies
 #           that generates locally optimal decisions with respect to
 #           a single JPG
 # RepeatMsgs: a policy subclass, useful as a helper to the
 #           LocallyOptimalJIPolicy class
 ###########################################################################

import copy
import string
from types import *
from teamwork.policy.generic import Policy

def generatePolicies(policySpace,actions,observations,horizon,debug=None):
    if horizon == 0:
	return policySpace
    else:
	for policy in policySpace[:]:
	    # Iterate through each policy
	    policySpace.remove(policy)
	    subspace = [policy]
	    policyObj = GenericPolicy(policy)
	    if debug:
		print 'Expanding policy:',policyObj
	    leaves = policyObj.getNodes()
	    while len(leaves) > 0:
		# Iterate through each leaf node
		entry = leaves.pop()
		if debug:
		    print '\tExpanding leaf:',entry
		# Expand table by considering possible observation branches
		table = []
		for omega in observations:
		    tableEntry = {'key':omega}
		    table.append(tableEntry)
		# Expand table by considering possible action selections
		newTables = [[]]
		generateActionCombos(table,actions,newTables)
		if debug:
		    print '\t\tNew actions:'
		# Create partial policies with the current leaf node expanded
		for partialPolicy in subspace[:]:
		    # Iterate through list of previously created partial
		    # policies
		    subspace.remove(partialPolicy)
		    for table in newTables:
			# Iterate through table of possible branchpoints
			if debug:
			    print '\t\t\tTable:',table
			newPolicy = copy.deepcopy(partialPolicy)
			for currentEntry in \
			    GenericPolicy(newPolicy).getNodes():
			    if currentEntry == entry:
				break
			else:
			    # This should never happen
			    print 'Unable to find entry!!!'
			currentEntry['table'] = table
# 			for tableEntry in table:
# 			    newPolicy['leaves'].insert(0,tableEntry)
			subspace.append(newPolicy)
	    # Expansion now complete; partial policies now fully specified so
	    # add to policy space
	    for partialPolicy in subspace:
		policySpace.append(partialPolicy)
		if debug:
		    print '\t\t\tNew Policy:',GenericPolicy(partialPolicy)
		    print
	    del subspace
	    if horizon == 1:
		return policySpace
# 	    policy['leaves'] = policy['newleaves']
# 	    del policy['newleaves']
	return generatePolicies(policySpace,actions,observations,
				horizon-1,debug)

def generateActionCombos(table,actions,result):
    while len(table) > 0:
	entry = table.pop()
	for partialTable in result[:]:
	    result.remove(partialTable)
	    for action in actions:
		entry['action'] = action
		newTable = copy.copy(partialTable)
		newTable.append(copy.copy(entry))
		result.append(newTable)
    return result
	
class JIPolicy(Policy):
    """generic class for a communication policy, where there is a
    single possible message and it refers to the achievement of some
    joint goal"""
    
    def __init__(self,jpg,achievedMsg,type='joint intentions'):
	"""jpg: a dictionary of conditions under which the JPG is
	achieved.  The keys are the relevant feature names; the
	values are a list of relevant feature values."""
	Policy.__init__(self,[achievedMsg,None],type)
	self.jpg = jpg
	self.trueMsg = achievedMsg

    def execute(self,state,choices=[],debug=0):
	for feature in self.jpg.keys():
	    if not state[0][feature] in self.jpg[feature]:
		break
	else:
	    # Check whether some agent has already communicated the
	    # achievement of the JPG.
	    for belief in state:
		if belief['_type'] == 'message':
		    for agent in belief.keys():
			if belief[agent] == self.trueMsg:
			    # If so, do not communicate again
			    return None
	    else:
		# No one has communicated achievement, so we must do
		# so now.
		return self.trueMsg
	# We have not achieved the JPG, so do not communicate
	return None

class STEAMPolicy(JIPolicy):
    """subclass of joint intentions policies, but following the STEAM
    algorithm for decision-theoretic selectivity"""
    def __init__(self,jpg,achievedMsg,gamma,costMiscoord,costComm):
	JIPolicy.__init__(self,jpg,achievedMsg,'STEAM')
	# Determine cost of non-communication
	if gamma == 'high':
	    if costMiscoord == 'high':
		costNonComm = 'high'
	    elif costMiscoord == 'medium':
		costNonComm = 'high'
	    else:
		costNonComm = 'medium'
	elif gamma == 'low':
	    if costMiscoord == 'high':
		costNonComm = 'medium'
	    elif costMiscoord == 'medium':
		costNonComm = 'low'
	    else:
		costNonComm = 'low'
	# Weigh cost of non-communication against cost of
	# communication channel
	if costNonComm == 'high':
	    self.communicate = 1
	elif costNonComm == 'medium':
	    if costComm == 'low':
		self.communicate = 1
	    else:
		self.communicate = None
	else:
	    self.communicate = None

    def execute(self,state,choices=[],debug=0):
	if self.communicate:
	    return JIPolicy.execute(self,state,choices,debug)
	else:
	    return None

class SilentPolicy(Policy):
    """generic policy class that never specifies communication"""
    def __init__(self):
	Policy.__init__(self,[None],'silent')

    def execute(self,state,choices=[],debug=0):
	return None

class BestAvailablePolicy(Policy):
    """a generic communication policy class that searches a space of
    candidate policies and finds the best one for a given COM-MTDP.
    It allows one to specify a space of possible policies, and have
    the constructor return the optimal policy from that space."""
    def __init__(self,com_mtdp,states,agent,policySpace,otherAgentsComPolicy,
                 domPolicy,horizon,debug=0):
        self.policy = None
        comPolicy = otherAgentsComPolicy
        for policy in policySpace:
            if debug > 1:
                print '--------'
                print `policy`
            comPolicy[agent] = policy
            value = 0.0
            msgs = 0.0
            for state in states:
                result = com_mtdp.evaluatePolicy(domPolicy,comPolicy,
                                                state,horizon)
                value = value + result['Reward']
                msgs = msgs + result['Messages']
            if debug > 1:
                print 'Value:',value
            if not self.policy or value > bestValue['Reward']:
                self.policy = policy
                bestValue = {'Reward':value,'Messages':msgs}
        if debug:
            print 'Best Policy:'
            print `self.policy`
        self.value = bestValue

    def execute(self,state,choices=[],debug=0):
        return self.policy(state)
    
class GloballyOptimalJIPolicy(JIPolicy):
    """subclass of joint intentions policies that performs a brute
    force search to determine the best policy of communication, in
    reference to a single JPG"""
    def __init__(self,com_mtdp,states,domPolicy,agent,horizon,
                 jpg,achievedMsg,debug=0):
        JIPolicy.__init__(self,jpg,achievedMsg,'globally optimal')
        self.agent = agent
        self.domPolicy = domPolicy
        self.mtdp = com_mtdp
        comPolicy = {self.agent:SingleMsgPolicy(self)}
        for agent in self.mtdp.agents:
            if agent.name != self.agent:
                comPolicy[agent.name] = SilentPolicy()
	# Create state of execution, which includes state of the
	# world, as well as belief states of individual agents
	stateList = []
        for state in states:
            stateList.append({'_world': state,'_parent':None,
                              '_prob':1.0/float(len(states)),'_epoch':0,
                              '_value':0.0,'_actions':{},'_messages':{}})
	for s in stateList:
	    for agent in self.mtdp.agents:
		s[agent.name] = agent.initialStateEstimator()
	for epoch in range(horizon):
	    if debug:
		print '========='
            print 'Epoch',epoch
            if debug:
		print '========='
                print '# States:',len(stateList)

            self.mtdp.ProjectObservations(stateList,None,[],epoch,debug)
            self.mtdp.ExecuteCommunication(stateList,comPolicy,debug)
            self.mtdp.ExecuteActions(stateList,domPolicy,debug)
            self.mtdp.ProjectWorldDynamics(stateList)

	# Construct optimal policy
	if debug:
	    print
	    print '-------'
	    print 'Policy selection phase'
	if debug:
	    print '-------'
	    print 'Examining Leaf Nodes:',len(stateList)
	values = []
	leafNodes = stateList
	stateList = []
	for index in range(len(leafNodes)):
	    print index
	    s = leafNodes[index]
	    value = s['_value'] * s['_prob']
	    # Determine whether a message was sent to arrive
	    # at the current state
	    key = 'Communicate'
	    if not s['_parent']['_messages'].has_key(self.agent):
		key = 'No ' + key
	    if debug:
		print '-------'
		print 'Examining state:',strip(s['_world'])
		print 'Epoch:',s['_epoch']
		print 'Latest belief update:',s[self.agent][0]
		print 'Message choice:',key
		print 'Value:',value
	    # The grandparent state has the pre-communication
	    # belief state.
	    parent = s['_parent']['_parent']
	    belief = parent[self.agent]
	    if not parent.has_key('_msgValues'):
		parent['_msgValues'] = {'Communicate':0.0,
					'No Communicate':0.0}
	    parent['_msgValues'][key] = parent['_msgValues'][key] \
					+ value
	    if debug:
		print 'Parent:',strip(s['_world'])
	    # Update values for this particular belief state
	    for entry in values:
		if entry['Beliefs'] == belief:
		    if debug:
			print 'Updating value...'
		    break
	    else:
		if debug:
		    print 'Creating value...'
		entry = {'Beliefs':belief,
			 'Communicate':0.0,
			 'No Communicate':0.0}
		values.append(entry)
	    entry[key] = entry[key] + value
	    if debug:
		print 'New total value:',entry[key]
	    # Move back to pre-observation state
	    if not parent in leafNodes:
		leafNodes.append(parent)
	    del s
	self.policy = values
	for index in range(length(values)):
	    entry = {'Beliefs':values[index]['Beliefs']}
	    entry['Policy'] = values[index]['Communicate'] \
			      > values[index]['No Communicate']
	    del values[index]
	    self.policy.append(entry)
	debug = 1
	while len(stateList) > 0:
            if debug:
                print '-------'
                print 'Starting a new ply...'
            # Store final policy
	    for s in stateList[:]:
		if debug:
		    print '-------'
		    print 'Examining state:',strip(s['_world'])
		    print 'Epoch:',s['_epoch']
		    print 'Latest belief update:',s[self.agent][0]
		    print 'Values:',s['_msgValues']
                # Compute local value of the current state
                value = s['_value'] 
		# Compute future value of execution from the
		# current state
		key = self.policy[`s[self.agent]`]
		if debug:
		    print 'Preference:',key
		value = value + s['_msgValues'][key]
                value = value * s['_prob']
		stateList.remove(s)
		# Move back to pre-observation state
		s = s['_parent']
                if s['_parent']:
                    # Determine whether a message was sent to arrive
                    # at the current state
                    key = 'Communicate'
                    if not s['_parent']['_messages'].has_key(self.agent):
                        key = 'No ' + key
		    if debug:
			print 'Message choice:',key
			print 'Value:',value
                    # The grandparent state has the pre-communication
                    # belief state.
                    parent = s['_parent']['_parent']
                    belief = parent[self.agent]
                    if not parent.has_key('_msgValues'):
                        parent['_msgValues'] = {'Communicate':0.0,
                                                'No Communicate':0.0}
                    parent['_msgValues'][key] = parent['_msgValues'][key] \
                                                + value
		    if debug:
			print 'Parent:',strip(s['_world'])
                    # Update values for this particular belief state
		    for entry in values:
			if entry['Beliefs'] == belief:
			    if debug:
				print 'Updating value...'
			    break
		    else:
			if debug:
			    print 'Creating value...'
			entry = {'Beliefs':belief,
				 'Communicate':0.0,
				 'No Communicate':0.0}
			values.append(entry)
		    entry[key] = entry[key] + value
		    if debug:
			print 'New total value:',entry[key]
                    # Update values for this pre-observation parent state
		    if not parent in stateList[:]:
			stateList.append(parent)
		del s
	    for index in range(length(values)):
		entry = {'Beliefs':values[index]['Beliefs']}
		entry['Policy'] = values[index]['Communicate'] \
				  > values[index]['No Communicate']
		del values[index]
		self.policy.append(entry)
	if debug:
	    print
	    print '-------'
	    print 'Final Policy:'
            print 'Communicate in the following belief states:'
            for key in policy.keys():
                if policy[key]:
                    print '-------'
                    print key
        print hello

    def execute(self,state,choices=[],debug=0):
        return policy[`state`]
    
class SingleMsgPolicy(JIPolicy):
    """subclass of joint intentions policies that generates all
    possible communication behaviors for an agent with a single joint
    commitment (this class is no longer very useful)"""
    def __init__(self,policy):
        JIPolicy.__init__(self,policy.jpg,policy.trueMsg)
        self.agent = policy.agent

    def execute(self,state,choices=[],debug=0):
        """Generates possible messages for this agent"""
        for belief in state:
            if belief['_type'] == 'message':
                if belief.has_key(self.agent):
                    return [None]
        else:
            return [None,self.trueMsg]
        
        
class LocallyOptimalJIPolicy(JIPolicy):
    """subclass of joint intentions policies that generates locally
    optimal decisions with respect to a single JPG"""
    def __init__(self,com_mtdp,states,comPolicy,domPolicy,agent,horizon,
                 jpg,achievedMsg,debug=0):
        JIPolicy.__init__(self,jpg,achievedMsg,'locally optimal')
        self.horizon = horizon
        self.agent = agent
        self.comPolicy = comPolicy
        self.domPolicy = domPolicy
        self.mtdp = com_mtdp
        self.initial = states
        self.debug = debug

    def execute(self,state,choices=[],debug=-1):
        if debug < 0:
            debug = self.debug
        if not JIPolicy.execute(self,state,choices):
            # If we haven't achieved JPG, then don't communicate
            return None
        # Determine what epoch we're in
        currentEpoch = state[0]['_epoch']
        if debug:
            print 'Executing at time:',currentEpoch
            print 'Beliefs:',state
	# Create state of execution, which includes state of the
	# world, as well as belief states of individual agents
	stateList = []
        for s in self.initial:
            stateList.append({'_world': s,'_epoch':0,
			      '_prob':1.0/float(len(self.initial)),
			      '_value':0.0,'_actions':{}})
	for s in stateList:
	    for agent in self.mtdp.agents:
		s[agent.name] = agent.initialStateEstimator()
        self.__generateConsistentStates(state,stateList,currentEpoch,debug)
        if debug:
            print 'Consistent states:',len(stateList)
        # Communication phase
        if debug:
            print
            print '--------'
            print 'Communication phase:'
        value = {'Communicate': 0.0, 'No Communicate':0.0}
        states = {'Communicate':[],'No Communicate':[]}
        for s in stateList[:]:
            if debug:
                print '--------'
                print 'Examining state:',strip(s['_world'])
                print 'Beliefs:',strip(s[self.agent])
            # Generate all possible messages
            messages = self.mtdp.__generateTeamMessages(s,self.mtdp.agents[:],
                                                       [{}])
            for msg in messages:
                newState = copy.copy(s)
                msg['_type'] = 'message'
                if debug:
                    print 'Messages:',msg
                # Update agents' beliefs based on messages exchanged
                for agent in self.mtdp.agents:
                    newState[agent.name] = agent.postComStateEstimator(s[agent.name],msg)
                # Update value based on communication cost
                newState['_value'] = self.mtdp.rewardCom(s['_world'],msg)
                newState['_parent'] = s
                if msg.has_key(self.agent):
                    if msg[self.agent] == self.trueMsg:
                        states['Communicate'].append(newState)
                else:                        
                    states['No Communicate'].append(newState)
            stateList.remove(s)

        for choice in ['Communicate','No Communicate']:
            stateList = states[choice]
            if debug:
                print '+++++++'
                print 'Evaluating Policy:',choice
                print '# States:',len(stateList)
                print '+++++++'
            # Action phase
            value[choice] = value[choice] + \
                            self.mtdp.ExecuteActions(stateList,self.domPolicy,
                                                     debug)
            self.mtdp.ProjectWorldDynamics(stateList)
            result = self.mtdp._evaluatePolicy(stateList,self.domPolicy,
                                               self.comPolicy,
                                               self.horizon,debug)
            value[choice] = value[choice] + result['Reward']
        
	# Construct optimal policy
	if debug:
	    print
	    print '-------'
	    print 'Policy selection phase'
            print '-------'
            for key in value.keys():
                print key+':',value[key]
        if value['Communicate'] > value['No Communicate']:
            #print strip(state[0]),'-> Communicate'
            return JIPolicy.execute(self,state,choices)
        else:
            #print strip(state[0]),'-> No Communicate'
            return None

    def __generateConsistentStates(self,beliefs,stateList,currentTime,debug=0):
        for epoch in range(currentTime+1):
	    if debug:
		print '========='
                print 'Epoch',epoch
		print '========='
            self.mtdp.ProjectObservations(stateList,self.agent,beliefs,
                                          epoch,debug)
            if epoch == currentTime:
                break
            comPolicy = {}
            for agent in self.mtdp.agents:
                comPolicy[agent.name] = RepeatMsgs(agent.name,beliefs,epoch)
            self.mtdp.ExecuteCommunication(stateList,comPolicy,debug)
            self.mtdp.ExecuteActions(stateList,self.domPolicy,debug)
            self.mtdp.ProjectWorldDynamics(stateList)

class RepeatMsgs(Policy):
    """policy subclass, useful as a helper to the
    LocallyOptimalJIPolicy class"""
    def __init__(self,agent,beliefs,epoch):
        self.msg = None
        # Find messages sent in past
        for msg in beliefs:
            if msg['_type'] == 'message' and \
               msg['_epoch'] == epoch:
                if msg.has_key(agent):
                    self.msg = msg[agent]
                break

    def execute(self,state,choices=[],debug=0):
        return self.msg
            

if __name__=='__main__':
    initialSpace = [{}]
    #     for policy in initialSpace:
    # 	policy['leaves'] = [policy]

    space = generatePolicies(initialSpace,['left','right'],
			     [{'Tiger':'l'}],1)
    space = generatePolicies(space,['left','right'],
			     [{'Tiger':'l'},{'Tiger':'r'}],2)
    for policy in space:
 	policy = GenericPolicy(policy)
	print policy
 	print '--------------------------'
    print '# Policies:',len(space)
