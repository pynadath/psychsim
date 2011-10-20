 ###########################################################################
 # 11/5/2001: David V. Pynadath, USC Information Sciences Institute
 #            pynadath@isi.edu
 #
 # Domain-specific classes for the helicopter scenario
 #
 ###########################################################################
import math

from teamwork.multiagent.Team import *
from teamwork.multiagent.COMMTDP import *
from teamwork.agent.Agent import *
from teamwork.policy.generic import *

class Escort(Agent):
    def __init__(self):
	Agent.__init__(self,['fly','destroy','wait'],   # A_e
		       {'Transport': 'observable',
			'Escort': 'observable',
			'Enemy': ['present',
				  'destroyed','none']}, # Omega_e
		       ['clear',None],                  # Sigma_e
		       'Escort')

    def legalActions(self,state):
	if state[self.name] == 'Destination':
	    return ['wait']
	elif state[self.name] == 'Destroyed':
	    return ['wait']
	else:
#	elif state[self.name] == state['Enemy']:
	    return self.actions[:]
#	else:
#	    return ['fly','wait']


class Transport(Agent):
    def __init__(self):
	Agent.__init__(self,
		       ['fly-NOE','fly-normal','wait'], # A_t
		       {'Transport': 'observable',
			'Escort': 'observable',
			'Enemy': ['destroyed','none']}, # Omega_t
		       [None],                          # Sigma_t
		       'Transport')

    def legalActions(self,state):
	if state[self.name] == 'Destination':
	    return ['wait']
	elif state[self.name] == 'Destroyed':
	    return ['wait']
	else:
	    return self.actions[:]

class HeloTeam(Team):
    def __init__(self,observability):
	self.escort = Escort()
	self.transport = Transport()
	Team.__init__(self,[self.transport,self.escort])
	self.observability = observability

    def individualObs(self,state,actions,observation,agent):
	# First check the completely observable features
	if self.observableProb(state,actions,observation,agent) < 1.0:
	    return 0.0
	if agent == 'Escort':
	    # If the escort is destroyed, it doesn't see anything
	    if state[agent] == 'Destroyed':
		return float(observation['Enemy'] == 'none')
	    # If the enemy has been destroyed (by the escort), then
	    # the escort observes so; otherwise, it does not.
	    elif state['Enemy'] == 'Destroyed' and \
                 actions[agent] == 'destroy':
		return float(observation['Enemy'] == 'destroyed')
	    elif state['Enemy'] == state[agent]:
		return float(observation['Enemy'] == 'present')
	    else:
		return float(observation['Enemy'] == 'none')
	elif agent == 'Transport':
	    # If the transport is destroyed, it doesn't see anything
	    if state[agent] == 'Destroyed':
		return float(observation['Enemy'] == 'none')
	    # If the escort is at the enemy location,
	    # then the enemy becomes destroyed, and
	    # there's a chance that the transport sees this
	    elif actions.has_key('Escort') and \
		 actions['Escort'] == 'destroy':
		# The probability that the transport observes the
		# enemy's destruction decays with its distance from
		# the event.
		distance = float(state['Escort']) - state[agent]
		prob = self.observability \
		       * math.exp(distance * (self.observability - 1.0))
		if observation['Enemy'] == 'destroyed':
		    return prob
		else:
		    return 1.0 - prob
	    else:
		return float(observation['Enemy'] == 'none')
	else:
	    print 'Unknown agent:',agent
	    return 0.0
	    

class HeloScenario(ComMTDP):
    def __init__(self,distance,      # number of steps to reach destination
		 comCost,            # cost of communication (in [0,1])
		 observability,      # observability factor (in [0,1])
		 escortReward,       # reward when escort gets to dest
		 transportReward,    # reward when transport gets to dest
		 relativeSpeed=2):   # relative speed of normal vs. NOE
	# Store parameters
	self.comCost = comCost
	self.relativeSpeed = relativeSpeed
	self.distance = distance
	self.observability = observability
	self.escortReward = escortReward
	self.transportReward = transportReward
	# Initialize state space
	states = StateSpace()
	# Escort can be anywhere from 0 to destination (inclusive)
	locations = range(distance)
	locations.append('Destination')
	locations.append('Destroyed')
	states.addFeature('Escort',locations)
	# Transport can be anywhere from 0 to destination (inclusive),
	# but travels at a different speed than escort
	locations = []
	for index in range(0,distance*relativeSpeed):
	    locations.append(float(index)/float(relativeSpeed))
	locations.append('Destination')
	locations.append('Destroyed')
	states.addFeature('Transport',locations)
	# Enemy can be anywhere between 0 and destination (exclusive),
	# or it might have been destroyed by escort
	locations = range(distance)[1:]
	locations.append('Destroyed')
	states.addFeature('Enemy',locations)
	# Time goes until the maximum number of time steps for
	# transport to reach destination
	# But let's not include time as a state feature...
	# states.addFeature('Time',range(0,distance*relativeSpeed+1))

	# Initialize team
	self.team = HeloTeam(observability)

	actionList = []
	for eAction in self.team.escort.actions:
	    for tAction in self.team.transport.actions:
		actionString = self.team.composeActions({'Escort':eAction,
							 'Transport':tAction})
		actionList.append(actionString)

	self.initialStates = []
	for loc in locations:
	    newState = {'Enemy':loc,'Transport':0.0,'Escort':0.0}
	    states.createIndex(newState)
	    self.initialStates.append(newState)

	substates = EnumeratedSubspace(states,self.generators(),
				       actionList,self.initialStates)

	ComMTDP.__init__(self,substates,self.team,'Helo Scenario')

    def generators(self):
	return {'Escort':self.escortGen,
		'Transport':self.transportGen,
		'Enemy':self.enemyGen,
		'Action':self.actionGen}

    def enemyGen(self,orig,action):
	actions = self.team.decomposeActions(action)
	if orig['Escort'] == orig['Enemy'] and \
	   actions['Escort'] == 'destroy':
	    # If the escort is at the enemy location, it is destroyed
	    return ['Destroyed']
	else:
	    # Otherwise, its state is unchanged
	    return [orig['Enemy']]
	
    def escortGen(self,orig,action):
	actions = self.team.decomposeActions(action)
	if orig['Escort'] == 'Destination':
	    # If at the destination, then stay there
	    return [orig['Escort']]
	elif orig['Escort'] == 'Destroyed':
	    # If destroyed, then stays destroyed
	    return [orig['Escort']]
	elif actions['Escort'] == 'fly' or actions['Escort'] == 'destroy':
	    # If the escort flies, it moves along one spot
	    if orig['Escort'] + 1 < self.distance:
		return [orig['Escort']+1]
	    else:
		return ['Destination']
	else:
	    # If it waits, it does not move
	    return [orig['Escort']]
	
    def transportGen(self,orig,action):
	actions = self.team.decomposeActions(action)
	if orig['Transport'] == 'Destination':
	    # If at the destination, then stay there
	    return [orig['Transport']]
	elif orig['Transport'] == 'Destroyed':
	    # If destroyed, then stays destroyed
	    return [orig['Transport']]
	elif actions['Transport'] == 'fly-NOE':
	    # If the transport flies NOE, it moves along one spot
	    if orig['Transport'] +  1.0/float(self.relativeSpeed) \
	       < float(self.distance):
		return [orig['Transport'] \
			+ 1.0/float(self.relativeSpeed)]
	    else:
		return ['Destination']
	elif actions['Transport'] == 'fly-normal':
	    if orig['Enemy'] != 'Destroyed':
		# If the enemy is alive, then flying at normal
		# altitude results in transport getting destroyed
		return ['Destroyed']
	    # If the transport flies normally,
	    # it moves along multiple spots
	    elif orig['Transport'] +  1.0 < float(self.distance):
		return [orig['Transport']+ 1.0]
	    else:
		return ['Destination']
	else:
	    # If it waits, it does not move
	    return [orig['Transport']]

    def actionGen(self,orig):
	eActions = self.team.escort.legalActions(orig)
	tActions = self.team.transport.legalActions(orig)
	actionList = []
	for eAction in eActions:
	    for tAction in tActions:
		actionString = self.team.composeActions({'Escort':eAction,
							 'Transport':tAction})
		actionList.append(actionString)
	return actionList

    def probability(self,orig,state,actions):
	return 1.0

    def timeGen(self,orig,actions):
	# Time never stops
	return [orig['Time']+1]

    def rewardAct(self,state,actions):
	# The agents get a domain-level reward for being at the
	# destination
	total = 0.0
	if state['Escort'] == 'Destination':
	    total = total + self.escortReward
	if state['Transport'] == 'Destination':
	    total = total + self.transportReward
	# Should there be some reward for destroying the enemy?
	return total

    def rewardCom(self,state,messages):
	total = 0.0
	# Escort incurs a cost for announcing that the area has been
	# cleared of the enemy
	if messages.has_key('Escort'):
	    if messages['Escort'] == 'clear':
		total = total - self.comCost
	# Transport cannot communicate anything
	return total

class EscortPolicy(Policy):
    def execute(self,state):
	# Find most recent observations
	for belief in state:
	    if belief['_type'] == 'observation':
		break
	if belief['Enemy'] == 'present':
	    # If at enemy, then destroy it
	    return 'destroy'
	elif belief['Escort'] == 'Destination':
	    # If at destination, then wait
	    return 'wait'
	else:
	    # Otherwise, fly
	    return 'fly'

class TransportPolicy(Policy):
    def execute(self,state):
	clear = None
	for belief in state:
	    if belief['_type'] == 'message':
		# Check messages
		if belief.has_key('Escort') and \
		   belief['Escort'] == 'clear':
		    # Escort told us that enemy is destroyed, so fly
		    # high
		    clear = 1
		    break
	for belief in state:
	    if belief['_type'] == 'observation':
		# Check observations
		if belief['Transport'] == 'Destination':
		    # If at destination, then wait
		    return 'wait'
		elif belief['Transport'] == 'Destroyed':
		    # If destroyed, then wait
		    return 'wait'
		elif belief['Enemy'] == 'destroyed':
		    # If we see that enemy is destroyed, fly high
		    clear = 1
		    break
	if clear:
	    return 'fly-normal'
	else:
	    # We know nothing about enemy, so fly NOE
	    return 'fly-NOE'

class EscortComPolicy(Policy):
    def __init__(self,msg,
                 liveEnemyThreshold,deadEnemyThreshold,deltaThreshold):
        self.liveEnemyThreshold = liveEnemyThreshold
        self.deadEnemyThreshold = deadEnemyThreshold
        self.deltaThreshold = deltaThreshold
        self.msg = msg

    def execute(self,state):
        # If someone has already communicated the message, then don't again
        for belief in state:
            if belief['_type'] == 'message':
                for key in belief.keys():
                    if key[0] != '_' and belief[key] == self.msg:
                        return None
        # If transport is at destination or destroyed, then don't bother
        # communicating to it
        if type(state[0]['Transport']) is StringType:
            return None
        # Determine whether the enemy has been destroyed
        for index in range(len(state)):
            belief = state[index]
            if belief.has_key('Enemy') and belief['Enemy'] == 'destroyed':
                destroyed = index
                break
        else:
            destroyed = -1
        if destroyed >= 0:
            if state[0]['Transport'] < self.deadEnemyThreshold:
                return self.msg
            elif destroyed > 0 and \
                 state[0]['Transport'] - state[2]['Transport'] \
                 < self.deltaThreshold:
                # We destroyed the enemy in the past, but the transport is
                # still travelling NOE
                return self.msg
            else:
                return None
        elif state[0]['Transport'] < self.liveEnemyThreshold:
            return self.msg
        else:
            return None

    def __repr__(self):
        str = 'Communicate\n\tIF trans < ' + `self.liveEnemyThreshold`
        str = str + '\n\tIF enemy dead AND'
        str = str + '\n\t\tIF trans < ' + `self.deadEnemyThreshold`
        str = str + '\n\t\tOR IF delta trans < ' + `self.deltaThreshold`
        return str
                
if __name__ == '__main__':
    import sys

    candidates = ['GOptimal']
    #candidates = ['Silent','SJI','STEAM']#,'LOptimal','GOptimal']
    distance = 10
    horizon = 22
    initialStates = []
    for enemy in range(1,distance-1):
	newState = {'Enemy':enemy,'Transport':0.0,'Escort':0.0}
	initialStates.append(newState)
    if len(sys.argv) < 2:
	output = sys.stdout
    else:
	output = open(sys.argv[1],'w')
    output.write('#Obs\tCom')
    for candidate in candidates:
	output.write('\t'+candidate+'\t')
    output.write('\n')
    output.flush()
    # Create policies
    domainPolicy = {'Escort':EscortPolicy(['fly','wait']),
		    'Transport':TransportPolicy(['fly-normal','fly-NOE',
						 'wait'])}
    policies = {}
    # Create Silent policy (also needed by Locally Optimal policy)
    if 'Silent' in candidates or 'LOptimal' in candidates:
	policies['Silent'] = {'Escort':SilentPolicy(),
			      'Transport':SilentPolicy()}
    # Create Jennings (aka simple joint intentions) policy
    if 'SJI' in candidates:
	policies['SJI'] = {'Escort':JIPolicy({'Enemy':['destroyed']},
					     'clear'),
			   'Transport':SilentPolicy()}
    policySpace = []
    for deadParam in range(0,distance+2):
        for liveParam in range(0,deadParam):
            for deltaParam in [1.1,0.6,0.0]:
                policySpace.append(EscortComPolicy('clear',
                                                   float(liveParam)/2.0,
                                                   float(deadParam)/2.0,
                                                   deltaParam))
    valueMatrix = []
    for observability in range(11):
	valueArray = []
	for comCost in range(11):
	    output.write(`float(observability)/10.0`)
	    output.write('\t'+`float(comCost)/10.0`)
	    output.flush()
	    tdp = HeloScenario(distance,float(comCost)/10.0,
			       float(observability)/10.0,0.1,0.1)
	    if observability < 5:
		gamma = 'high'
	    else:
		gamma = 'low'
	    if comCost < 5:
		costStr = 'low'
	    else:
		costStr = 'high'
	    # Create STEAM policy
	    if 'STEAM' in candidates:
		policies['STEAM'] = {'Escort':STEAMPolicy({'Enemy':['destroyed']},'clear',gamma,'medium',costStr),'Transport':SilentPolicy()}
	    # Create locally optimal policy
	    if 'LOptimal' in candidates:
		policies['LOptimal'] = {'Escort':
					LocallyOptimalJIPolicy(tdp,initialStates,policies['Silent'],domainPolicy,'Escort',horizon,{'Enemy':['destroyed']},'clear'),'Transport':SilentPolicy()}
	    # Create globally optimal policy
	    if 'GOptimal' in candidates:
		policies['GOptimal'] = BestAvailablePolicy(tdp,initialStates,'Escort',policySpace,{'Transport':SilentPolicy()},domainPolicy,horizon)
		output.write(`policies['GOptimal'].policy`+'\n')
		continue
	    values = {}
	    msgs = {}
	    # Initialize EU and E[#Msgs] results
	    for candidate in candidates:
		if candidate == 'GOptimal':
		    # We can pre-compute the globally optimal policy's
		    # value over all possible enemy positions
		    values[candidate] = policies[candidate].value['Reward']
		    msgs[candidate] = policies[candidate].value['Messages']
		else:
		    values[candidate] = 0.0
		    msgs[candidate] = 0.0
	    # Loop through possible locations of radar
	    for enemy in range(1,distance-1):
		state = {'Escort':0,'Transport':0.0,'Enemy':enemy}
		for candidate in candidates:
		    if candidate != 'GOptimal':
			result = tdp.evaluatePolicy(domainPolicy,
						    policies[candidate],
						    state,horizon)
			values[candidate] = values[candidate] + \
					    result['Reward']
			msgs[candidate] = msgs[candidate] + result['Messages']
            # Normalize values
	    for candidate in candidates:
                values[candidate] = values[candidate]/float(distance-2)
                msgs[candidate] = msgs[candidate]/float(distance-2)
	    for candidate in candidates:
		output.write('\t'+`values[candidate]`)
		output.write('\t'+`msgs[candidate]`)
	    valueArray.append(values)
	    output.write('\n')
	    output.flush()
	valueMatrix.append(valueArray)
	output.write('\n')
	output.flush()
    
    output.close()
