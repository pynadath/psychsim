 ###########################################################################
 # 11/5/2001: David V. Pynadath (pynadath@isi.edu)
 #
 # StateSpace: generic state space class for representing a set of states,
 #      where each state is a combination of feature-value pairs.  Useful
 #      mainly as a skeleton class, since by itself, it enumerates all
 #      possible combinations of feature-value pairs, regardless of actual
 #      reachability.
 #
 # EnumeratedSubspace: more practical state space class that generates only 
 #      reachable subset of the overall state space.
 # 
 ###########################################################################

import copy
from types import *
#
# Very general, but very weak state space class, defines some basic
# methods, and is useful for state spaces where all combinations of
# attribute values are possible and reachable
#
class StateSpace:
    version = 1.0
    # Takes an optional list of features, where each feature is a tuple (name, 
    # values), with "name" being a string giving the name of the feature, and
    # "values" is a list of strings, with each string being the name of a
    # possible value for this feature.
    def __init__(self,featureList=[]):
	self.features = {}
	self.size = 1
	for feature in featureList:
	    self.features[feature[0]] = feature[1]
	    self.size = self.size * len(feature[1])

    # Adds an additional feature to the space, named after the string
    # "featureName" and with possible values taken from the list
    # "featureSpace"
    def addFeature(self,featureName,featureSpace):
	self.features[featureName] = featureSpace
	self.size = self.size*len(featureSpace)

    # Useful for iterating through state space, since it (along with
    # getNextState) provides a java Enumeration-type functionality
    def getFirstState(self):
	state = {'_index':{}}
	for feature in self.features.keys():
	    state['_index'][feature] = 0
	    state[feature] = self.features[feature][0]
	return state

    # Useful for iterating through state space, since it (along with
    # getFirstState) provides a java Enumeration-type functionality.  Returns
    # None when there are no more states left.
    def getNextState(self,oldState,parent=None):
	keys = self.features.keys()
	state = copy.deepcopy(oldState)
	changedFlag = None
	for feature in keys:
	    state['_index'][feature] = state['_index'][feature] + 1
	    if state['_index'][feature] >= len(self.features[feature]):
		state['_index'][feature] = 0
	    state[feature] = \
			   self.features[feature][state['_index'][feature]]
	    if state['_index'][feature] > 0:
		changedFlag = 1
		break
	if changedFlag:
	    return state
	else:
	    return None

    # Returns a unique integer ID corresponding to a state
    def state2index(self,state):
	index = 0
	keys = copy.deepcopy(self.features.keys())
	keys.reverse()
	for feature in keys:
	    index = (index*len(self.features[feature])) + \
		    state['_index'][feature]
	return index

    # Returns the unique state corresponding to an integer ID
    def index2state(self,index):
	total = index
	state = {'_index':{}}
	for feature in self.features.keys():
	    value = total - (total/len(self.features[feature])*\
			     len(self.features[feature]))
	    state['_index'][feature] = value
	    state[feature] = self.features[feature][value]
	    total = (total/len(self.features[feature])*\
		     len(self.features[feature]))
	return state

    # Generates a unique ID for the state, returns nothing
    def createIndex(self,state):
	state['_index'] = {}
	for feature in self.features.keys():
	    try:
		state['_index'][feature] = self.features[feature].\
					   index(state[feature])
	    except ValueError:
		print 'Feature:',feature,'does not contain:',state[feature]

    # Returns a dictionary version of the provided state with various
    # bookkeeping fields removed.  Useful for pretty printing of states.
    def state2dict(self,state):
	dict = copy.copy(state)
	for key in dict.keys()[:]:
	    if key[0] == '_':
		del dict[key]
	return dict

    # Utility method for taking a dictionary of state feature values and
    # returning the specific state object stored in the state space.
    def dict2state(self,state):
	return self.index2state(self.state2index(state))

    def printStates(self):
	state = self.getFirstState()
	while state:
	    print self.state2dict(state)
	    state = self.getNextState(state)

#
# Compact, dynamically generated version of the state space class
#
class EnumeratedSubspace(StateSpace):
    version = 1.0
    # states: instance of StateSpace, used to specify the features of
    #         interest, as well as all possible values for those features
    # generators: a dictionary, with keys corresponding to the names of
    #         features in the state space, and the entry for each key being a
    #         function that takes, as input, an original state and an action
    #         and returns, as output, a list of possible values for the given
    #         feature over all possible destination states
    # actions: a list of strings, with each string being the name of a
    #         possible action (corresponding to the action argument to the
    #         generator functions)
    # initialStates: an optional list of start states
    # RETURNS: a subset of the overall StateSpace instance.  This subset
    #         contains only those states reachable from the specified
    #         initial states, according to the generator functions and set of
    #         all possible actions
    def __init__(self,states,generators,actions,initialStates=None,
		 debug=0):
	self.features = states.features
	self.featureKeys = self.features.keys()
	if initialStates:
	    self.states = initialStates[:]
	else:
	    self.states = [states.getFirstState()]
	self.children = []
	self.parents = []
	self.indices = {}
	self.__initializeIndex(self.indices,0)
	for curState in range(len(self.states)):
	    realState = states.state2dict(self.states[curState])
	    self.__addIndex(realState,curState)

	curState = 0
	maxChildren = 0
	while curState < len(self.states):
	    if debug > 1:
		print self.state2dict(self.index2state(curState))
	    self.children.append({})
	    while len(self.parents) <= curState:
		self.parents.append({})
	    # Determine set of applicable actions in this state
	    if generators.has_key('Action'):
		actionSet = generators['Action'](self.states[curState])
	    else:
		actionSet = actions
	    for action in actionSet:
		self.children[curState][action] = []
		successors = {}
		# Determine all possible successor states, given the
		# particular action to be taken
		for feature in self.featureKeys:
                    successors[feature] = []
                    possibleSuccessors = generators[feature]\
                                         (self.states[curState],action)
                    for successor in possibleSuccessors:
                        if not successor in successors[feature]:
                            successors[feature].append(successor)
		# Create set of possible states out of combinations of
		# possible successor feature values
		successorStates = [{}]
                for feature in self.features.keys():
                    self.__generateStates(generators,curState,action,
                                         feature,successorStates)
		# Add successors to state space (unless already present)
		for nextState in successorStates:
		    # Create state index for quick access
		    nextIndex = self.state2index(nextState)
		    if nextIndex < 0:
			# State doesn't exist yet, so add it to state space
			# now.
			nextIndex = len(self.states)
			self.__addIndex(nextState,nextIndex)
			self.states.append(nextState)
		    # Enumerate state as possible successor
		    self.children[curState][action].append(nextIndex)
		    # Enumerate current state as possible parent of successor
		    while len(self.parents) <= nextIndex:
			self.parents.append({})
		    if not self.parents[nextIndex].has_key(action):
			self.parents[nextIndex][action] = []
		    self.parents[nextIndex][action].append(curState)
		# Update record of maximum branching factor
		if len(self.children[curState][action]) > maxChildren:
		    maxChildren = len(self.children[curState][action])
	    curState = curState + 1
	# Create position index within each state
	for curState in range(len(self.states)):
	    self.states[curState]['_position'] = curState
	self.size = len(self.states)
	if debug:
	    print 'State space:',self.size,'states'
	    print 'Max successors:',maxChildren

    def __initializeIndex(self,indices,position):
	if position < len(self.featureKeys):
	    for value in self.features[self.featureKeys[position]]:
		if position + 1 < len(self.featureKeys):
		    indices[value] = {}
		else:
		    indices[value] = -1
		self.__initializeIndex(indices[value],position+1)

    def __generateStates(self,generators,state,action,feature,stateList):
            # Determine whether we've already processed this feature
            try:
                if stateList[0].has_key(feature):
                    # This feature has already been processed
                    done = 1
                else:
                    done = None
            except IndexError:
                done = None
            if not done:
                # Process this feature
		successors = {}
		# Determine all possible successor states, given the
		# particular action to be taken
                successors = []
                possibleSuccessors = generators[feature]\
                                     (self.states[state],action)
                try:
                    substate = possibleSuccessors[0]
                    if type(substate) is DictType:
                        #  Joint generator for multiple features
                        successors = possibleSuccessors
                    else:
                        # Independent generator for this feature only
                        for successor in possibleSuccessors:
                            substate = {feature:successor}
                            if not substate in successors:
                                successors.append(substate)
                except IndexError:
                    pass
                # Compose new successors with current list of partial
                # states
                originalStates = stateList[:]
                for orig in originalStates:
                    stateList.remove(orig)
                    for substate in successors:
                        for key in substate.keys():
                            orig[key] = substate[key]
                        stateList.append(copy.copy(orig))

    def ___generateStatesOld(self,featureVals,features,index,stateList):
	if index < len(features):
	    originalStates = stateList[:]
	    for state in originalStates:
		stateList.remove(state)
		for value in featureVals[features[index]]:
		    state[features[index]] = value
		    stateList.append(copy.copy(state))
	    self.___generateStatesOld(featureVals,features,index+1,stateList)

    # Returns a first state from the state space.  This is useful for
    # iterating through the state space.  If the optional parent argument is
    # provided, it returns the first destination state immediately reachable
    # from the parent.  The return value is consistent across multiple calls
    # with the same argument.
    def getFirstState(self,parent=None):
	if parent:
	    children = self.children[parent['_position']]
	    state = self.states[children[0]]
	    if not state.has_key('_'+`parent['_position']`):
		state['_'+`parent['_position']`] = 0
	    return state
	else:
	    return self.states[0]

    # Returns the next state in a sequence throughout the state space.  This
    # is useful for iterating through the state space.  oldState is the
    # previous state in this sequence.  The sequence is consistent across
    # multiple calls.
    def getNextState(self,oldState,parent=None):
	if parent:
	    children = self.children[parent['_position']]
	    key = '_'+`parent['_position']`
	    if oldState[key] < len(children)-1:
		state = self.states[children[oldState[key]+1]]
		if not state.has_key(key):
		    state[key] = oldState[key]+1
		return state
	    else:
		return None
	elif oldState['_position'] < len(self.states)-1:
	    return self.states[oldState['_position']+1]
	else:
	    return None

    # Remove any children that have a zero probability with respect to the
    # given distribution.
    def pruneChildren(self,probFun,threshold=0.000001):
	maxChildren = 0
	for origState in self.states:
	    orig = self.state2index(origState)
	    for action in self.children[orig].keys():
		for dest in self.children[orig][action][:]:
		    destState = self.index2state(dest)
		    self.state2dict(destState)
		    if probFun(origState,destState,action) < threshold:
			self.parents[dest][action].remove(orig)
			self.children[orig][action].remove(dest)
		if len(self.children[orig][action]) > maxChildren:
		    maxChildren = len(self.children[orig][action])

    def __addIndex(self,state,position):
	index = self.indices
	for feature in self.featureKeys:
	    if type(index[state[feature]]) is IntType:
		index[state[feature]] = position
	    else:
		index = index[state[feature]]

    # Utility method for taking a symbolic state representation and returning
    # a unique numeric ID for the state
    def state2index(self,state):
	if state.has_key('_position'):
	    return state['_position']
	else:
	    index = self.indices
	    for feature in self.featureKeys:
		if index.has_key(state[feature]):
		    index = index[state[feature]]
		else:
		    print 'Unable to find index for state:',state
		    print 'Failed on feature value:',state[feature]
		    print 'Valid feature values:',index.keys()
		    return -1
	    state['_position'] = index
	    return index

    # Utility method for taking a numeric state ID and returning a symbolic
    # state representation
    def index2state(self,index):
	try:
	    return self.states[index]
	except IndexError:
	    print 'Illegal index:',index
	    return None

    def dict2state(self,state):
	try:
	    del state['_position']
	except KeyError:
	    pass
	return StateSpace.dict2state(self,state)
