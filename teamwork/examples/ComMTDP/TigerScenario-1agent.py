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


#class PersonB(Agent):
#def __init__(self):
#Agent.__init__(self,['openLeft','openRight','listen'],   # A_e
#{'Tiger': ['left', 'right']}, # Omega_e
#       [None],                  # Sigma_e
#      'PersonB')

    def legalActions(self,state):
	    return self.actions[:]

        
class PersonTeam(Team):
    def __init__(self):
	self.personA = PersonA()
        #self.personB = PersonB()
	#Team.__init__(self,[self.personA,self.personB])
        Team.__init__(self,[self.personA])


    def individualObs(self,state,actions,observation,agent,debug=0):
        if debug > 0:
            print 'DEBUG'
            print `actions`
        if self.observableProb(state,actions,observation,agent) < 1.0:
	    return 0.0
        if actions == {}:
            return 0.5
	    # If either agent performed an openLeft or openRight sees left or right with equal probability
        if actions[agent] == 'openLeft' or actions[agent] == 'openRight':
            return 0.5
            # Else if tiger was behind left door, agent sees left with 0.85 probability
        elif state['Tiger'] == 'left':
            if observation['Tiger'] == 'left':
                return 0.85
            else:
                return 0.15   
           # Else if tiger was behind right door, agent sees right with 0.85 probability 
        elif state['Tiger'] == 'right':
            if observation['Tiger'] == 'left':
                return 0.15
            else:
                return 0.85
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
            actionString = self.team.composeActions({'PersonA':aAction})
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
        if actions['PersonA'] == 'listen':
            #feature Tiger is unchanged
	    return [orig['Tiger']]
        else:
            return ['left','right']

    #specify transition function here i.e. Pr(state|orig,actions)
    def probability(self,orig,state,actions):
        if actions['PersonA'] == 'listen':
            if orig['Tiger'] == state['Tiger']:
                return 1.0
            else:
                return 0.0
        else:
            return 0.5

    def rewardAct(self,state,actions):
        total = 0.0
        if actions['PersonA'] == 'listen':
            total = -1.0
        elif actions['PersonA'] == 'openLeft' and state['Tiger'] == 'left':
            total = -100
        elif actions['PersonA'] == 'openLeft' and state['Tiger'] == 'right':
            total = 10
        elif actions['PersonA'] == 'openRight' and state['Tiger'] == 'left':
            total = 10
        elif actions['PersonA'] == 'openRight' and state['Tiger'] == 'right':
            total = -100
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
    communicationPolicy = {'PersonA':SilentPolicy()}
    policySpace = []
    #for deadParam in range(0,distance+2):
    #for liveParam in range(0,deadParam):
    #for deltaParam in [1.1,0.6,0.0]:
    policySpace.append(PersonADomPolicy(['openLeft','openRight']))            
    #output.flush()
    tdp = TigerScenario()
    nashEqbm = NashDomainPolicy(tdp,initialStates,
                                 'PersonA',policySpace,
                                 {},
                                 communicationPolicy,horizon)
    values['Nash'] = nashEqbm.value['Reward']
    msgs['Nash'] = nashEqbm.value['Messages']
    output.write('\t'+`values['Nash']`)
    output.write('\t'+`msgs['Nash']`)
    output.write('\n')
    output.flush()
    
    output.close()
