 ###########################################################################
 # 3/1/2002: Ranjit Nair, University of Southern California
 #            nair@usc.edu
 #           David V. Pynadath, USC Information Sciences Institute
 #            pynadath@isi.edu
 #
 # Domain-specific classes for the tiger scenario
 #
 ###########################################################################
import math

from teamwork.multiagent.COMMTDP import *
from teamwork.multiagent.Team import *
from teamwork.policy.JIPolicy import *
from teamwork.state.States import *
from teamwork.agent.Agent import *
from teamwork.policy.generic import *

class PersonA(Agent):
    def __init__(self):
	Agent.__init__(self,['openLeft','openRight','listen'],   # A_e
                       {'Tiger': ['left', 'right']}, # Omega_e
		       [None],                  # Sigma_e
		       'PersonA')

    def legalActions(self,state):
	    return self.actions[:]


    def generateAllObservations(self,time=0):
        if time < 1:
            return [{'Tiger':'left'}]
        else:
            try:
                return self.allObservations
            except AttributeError:
                self.allObservations = [{}]
                for key in self.observations.keys():
                    for omega in self.allObservations[:]:
                        self.allObservations.remove(omega)
                        for value in self.observations[key]:
                            newOmega = copy.copy(omega)
                            newOmega[key] = value
                            self.allObservations.append(newOmega)
                return self.allObservations
	    
    def generateHistories(self,length):
	result = [[]]
	for t in range(length):
	    # Generate possible observations
	    for history in result[:]:
		result.remove(history)
		for omega in self.generateAllObservations(t):
		    newHistory = copy.copy(history)
		    newHistory.append({'type':'observation',
				       'value':omega})
		    result.append(newHistory)
	    # Generate possible actions
	    for history in result[:]:
		result.remove(history)
		for action in self.actions:
		    newHistory = copy.copy(history)
		    newHistory.append({'type':'action',
				       'value':action})
		    result.append(newHistory)
	return result

class PersonB(Agent):
    def __init__(self):
	Agent.__init__(self,['openLeft','openRight','listen'],   # A_e
                       {'Tiger': ['left', 'right']}, # Omega_e
		       [None],                  # Sigma_e
		       'PersonB')

    def legalActions(self,state):
	    return self.actions[:]


    def generateAllObservations(self,time=0):
        if time < 1:
            return [{'Tiger':'left'}]
        else:
            try:
                return self.allObservations
            except AttributeError:
                self.allObservations = [{}]
                for key in self.observations.keys():
                    for omega in self.allObservations[:]:
                        self.allObservations.remove(omega)
                        for value in self.observations[key]:
                            newOmega = copy.copy(omega)
                            newOmega[key] = value
                            self.allObservations.append(newOmega)
                return self.allObservations
	    
    def generateHistories(self,length):
	result = [[]]
	for t in range(length):
	    # Generate possible observations
	    for history in result[:]:
		result.remove(history)
		for omega in self.generateAllObservations(t):
		    newHistory = copy.copy(history)
		    newHistory.append({'type':'observation',
				       'value':omega})
		    result.append(newHistory)
	    # Generate possible actions
	    for history in result[:]:
		result.remove(history)
		for action in self.actions:
		    newHistory = copy.copy(history)
		    newHistory.append({'type':'action',
				       'value':action})
		    result.append(newHistory)
	return result
        
class PersonTeam(Team):
    def __init__(self):
	self.personA = PersonA()
        self.personB = PersonB()
	Team.__init__(self,[self.personA,self.personB])

    def individualObs(self,state,actions,observation,agent):
	# First check the completely observable features
	if self.observableProb(state,actions,observation,agent) < 1.0:
	    return 0.0
        if actions == {}:
            return 0.5
	if agent == 'PersonA' or agent == 'PersonB':
	    # If either agent performed an openLeft or openRight sees left or right with equal probability
	    if actions['PersonA'] == 'openLeft' or actions['PersonA'] == 'openRight' or actions['PersonB'] == 'openLeft' or actions['PersonB'] == 'openRight' :
		return 0.5
            # Else if tiger was behind left door, agent sees left with 0.85 probability
            elif state['Tiger'] == 'left' and actions[agent] == 'listen':
                if observation['Tiger'] == 'left':
                    return 0.85
                else:
                    return 0.15                  
           # Else if tiger was behind right door, agent sees right with 0.85 probability 
            elif state['Tiger'] == 'right' and actions[agent] == 'listen':
                if observation['Tiger'] == 'left':
                    return 0.15
                else:
                    return 0.85
            else:
                print 'Unknown state'
                return 0.0
        else:
	    print 'Unknown agent:',agent
	    return 0.0
	    

class TigerScenario(ComMTDP):
    def __init__(self):   
	# Initialize state space
	states = StateSpace()
	# Tiger can be either behind left door or right door
	locations = ['left', 'right']
	states.addFeature('Tiger',locations)

	# Initialize team
	self.team = PersonTeam()
	actionList = []
	for aAction in self.team.personA.actions:
	    for bAction in self.team.personB.actions:
		actionString = self.team.composeActions({'PersonA':aAction,
							 'PersonB':bAction})
		actionList.append(actionString)

	self.initialStates = []
	for loc in locations:
	    newState = {'Tiger':loc}
	    states.createIndex(newState)
	    self.initialStates.append(newState)

	substates = EnumeratedSubspace(states,self.generators(),
				       actionList,self.initialStates)
        
	ComMTDP.__init__(self,substates,self.team,'Tiger Scenario')

    def generators(self):
	return {'Tiger':self.tigerGen}
   
    def tigerGen(self,orig,action):
	actions = self.team.decomposeActions(action)
	if actions['PersonA'] == 'listen' and actions['PersonB'] == 'listen':  
	    return [orig['Tiger']]
        else:
            return ['left','right']


    def probability(self,orig,state,actions):
        if actions['PersonA'] == 'listen' or actions['PersonB'] == 'listen':
            if orig['Tiger'] == state['Tiger']:
                return 1.0
            else:
                return 0.0
        else:
            return 0.5
        

    def rewardAct(self,state,actions):
        total = 0.0
        if actions['PersonA'] == 'listen' and actions['PersonB'] == 'listen':
            total = -2.0
        elif actions['PersonA'] == 'openLeft' and actions['PersonB'] == 'openRight':
            total = -100.0
        elif actions['PersonA'] == 'openRight' and actions['PersonB'] == 'openLeft':
            total = -100.0
	elif state['Tiger'] == 'left':
            if actions['PersonA'] == 'openRight' and actions['PersonB'] == 'openRight':
                total = 20
            elif actions['PersonA'] == 'openLeft' and actions['PersonB'] == 'openLeft': 
                total = -50
            elif actions['PersonA'] == 'listen' and actions['PersonB'] == 'openLeft': 
                total = -101
            elif actions['PersonA'] == 'listen' and actions['PersonB'] == 'openRight':
                total = 9
            elif actions['PersonA'] == 'openLeft' and actions['PersonB'] == 'listen': 
                total = -101
            elif actions['PersonA'] == 'openRight' and actions['PersonB'] == 'listen':
                total = 9
        elif state['Tiger'] == 'right':
            if actions['PersonA'] == 'openRight' and actions['PersonB'] == 'openRight':
                total = -50
            elif actions['PersonA'] == 'openLeft' and actions['PersonB'] == 'openLeft': 
                total = 20
            elif actions['PersonA'] == 'listen' and actions['PersonB'] == 'openLeft': 
                total = 9
            elif actions['PersonA'] == 'listen' and actions['PersonB'] == 'openRight':
                total = -101
            elif actions['PersonA'] == 'openLeft' and actions['PersonB'] == 'listen': 
                total = 9
            elif actions['PersonA'] == 'openRight' and actions['PersonB'] == 'listen':
                total = -101
        return total

    def rewardCom(self,state,messages):
	total = 0.0
	return total

class PersonADomPolicy(Policy):
    def execute(self,state):
	# Find most recent observations
	for belief in state:
	    if belief['_type'] == 'observation':
		break
	if belief['Tiger'] == 'left':	    
	    return 'openRight'
	elif belief['Tiger'] == 'right':
            return 'openLeft'
	else:
	    return 'listen'

class PersonBDomPolicy(Policy):
    def execute(self,state):
	# Find most recent observations
	for belief in state:
	    if belief['_type'] == 'observation':
		break
	if belief['Tiger'] == 'left':	    
	    return 'openRight'
	elif belief['Tiger'] == 'right':
            return 'openLeft'
	else:
	    return 'listen'

class PersonDomPolicy(Policy):
    def __init__(self,threshold):
	self.threshold = threshold
	Policy.__init__(self)

    def execute(self,state):
	numLefts = 0
	numRights = 0
	for belief in state:
	    if belief['_type'] == 'observation':
		if belief['Tiger'] == 'right':
		    numRights = numRights + 1
		elif belief['Tiger'] == 'left':
		    numLefts = numLefts + 1
		else:
		    break
	# Compute prob of left given numRights and numLefts
	###
	if prob > self.threshold:
	    return 'openRight'
	elif prob < 1.0 - self.threshold:
	    return 'openLeft'
	else:
	    return 'listen'

        
if __name__ == '__main__':
    import sys

    horizon = 10
    initialStates = []
    for tiger in ['left','right']:
	newState = {'Tiger':tiger}
	initialStates.append(newState)
    #print 'Initial States',`initialStates`
    if len(sys.argv) < 2:
	output = sys.stdout
    else:
	output = open(sys.argv[1],'w')   
    output.write('\t\tGOptimal\n')
    output.flush()
    # Create policies
    values={}
    communicationPolicy = {'PersonA':SilentPolicy(),'PersonB':SilentPolicy()}
   
    tdp = TigerScenario()
    prevDomPolicy = {'PersonA':PersonADomPolicy,'PersonB':PersonBDomPolicy}

    convCount = 0
    prevVal = 0.0
    e = 0.000001
    while convCount < 2:
      for agent in ['PersonA','PersonB']:
          if convCount < 2:
              #specify policy space for agent with other agent fixed
              NashEqbm = NashDomainPolicy(tdp,initialStates,
                                          agent,policySpace,
                                          prevDomainPolicy,
                                          communicationPolicy,horizon)
              if (NashEqbm.value[Reward] - bestVal < e):
                  convCount = convCount + 1
              else:
                  convCount = 0
                  prevVal = NashEqbm.value['Reward']
                  prevDomainPolicy = NashEqbm
          else:
              break

    values['Nash'] = nashEqbm.value['Reward']
    msgs['Nash'] = nashEqbm.value['Messages']
    output.write('\t'+`values['Nash']`)
    output.write('\t'+`msgs['Nash']`)
    output.write('\n')
    output.flush()
    
    output.close()
