from psychsim.reward import *
from psychsim.pwl import *
from psychsim.action import *
from psychsim.world import *
from psychsim.agent import *

import random
from random import randint
from time import time, localtime
import sys


class Person(Agent):
	def __init__(self, name, init_location, world, random_horizon=False, random_weight_bases=False, random_costs=False):
		Agent.__init__(self,name)
		world.addAgent(self)

		# set the horizon to 2, so he can see that it should make money to eat
		
		self.horizon_value=randint(1,4) if random_horizon else 2
		print('\n'+name+':')
		print(' Horizon: '+str(self.horizon_value)+'\n')
		self.setAttribute('horizon',self.horizon_value)

		
		# define features of a civilian
		current_x=world.defineState(self.name,'current_x')
		current_y=world.defineState(self.name,'current_y')
		wealth=world.defineState(self.name,'wealth')
		hunger=world.defineState(self.name,'hunger')
		comfort=world.defineState(self.name,'comfort')
		health=world.defineState(self.name,'health')


		# initialize the features
		self.setState('current_x', init_location[0])
		self.setState('current_y', init_location[1])
		self.setState('wealth', 0.)
		self.setState('hunger', 0.)
		self.setState('comfort', 0.)
		self.setState('health', 100.)


		# define rewards
		# here we define mid points for the weights, so we can manipulate the weight ranges. 
		self.wm = randint(2, 9)*1. if random_weight_bases else 2 #wealth  mid point
		self.cm = randint(2, 9)*1. if random_weight_bases else 2 #comfort mid point
		self.hm = randint(2, 9)*1. if random_weight_bases else 9 #health  mid point
		self.um = randint(2, 9)*1. if random_weight_bases else 2 #hunger  mid point

		self.wealth_weight  =randint(self.wm-2, self.wm+2)*1. 
		self.comfort_weight =randint(self.cm-2, self.cm+2)*1. 
		self.health_weight  =randint(self.hm-2, self.hm+2)*1. 
		self.hunger_weight  =randint(self.um-2, self.um+2)*1. 
		print(' Wealth Weight: ' +str(self.wealth_weight ))
		print(' Comfort Weight: '+str(self.comfort_weight))
		print(' Health Weight: ' +str(self.health_weight ))
		print(' Hunger Weight: ' +str(self.hunger_weight )+'\n')
		self.setReward(maximizeFeature(wealth,self.name),  self.wealth_weight)## maximize
		self.setReward(maximizeFeature(comfort,self.name),self.comfort_weight)
		self.setReward(maximizeFeature(health,self.name),  self.health_weight)
		self.setReward(minimizeFeature(hunger,self.name),  self.hunger_weight)## minimize


		# define actions
		time2work=8
		time2home=16
		time_pass = stateKey('env','time_pass') # point to the same variable
		time_of_day = stateKey('env','time_of_day')
		# records[civilian.name]= round(civilian.getState('comfort').domain()[0], 2)
		tree= makeTree({'if': thresholdRow(time_of_day,time2work), # if time_pass is larger than time2work, larger than 8
						True: {'if': thresholdRow(time_of_day,time2home), # if the time_pass is less than time2home, less than 16
								True: False,
								False: True},
						False: False})
		work = self.addAction({'verb':'work'}, tree)

		
		eating_cost =randint(10,50)*.01 if random_costs else .5
		wealth_cost =randint(10,20)*.01 if random_costs else .1 
		hunger_cost =randint(10,20)*.01 if random_costs else .1
		comfort_cost=randint(10,20)*.01 if random_costs else .1
		print(' Eating Cost: ' +str(eating_cost ))
		print(' Wealth Cost: ' +str(wealth_cost ))
		print(' Hunger Cost: ' +str(hunger_cost ))
		print(' Comfort Cost: '+str(comfort_cost))
		print('------------------------------------')


		# see if wealth is larger than the eating cost before eating
		tree= makeTree({'if': thresholdRow(wealth,eating_cost),
						True: True,
						False: False})
		eat = self.addAction({'verb':'eat'}, tree)
		gohome = self.addAction({'verb':'gohome'})

		region_objs= [self.world.agents[name] for name in self.world.agents if isinstance(self.world.agents[name],Region)]
		# set dynamics
		commercial=world.agents['commercial']

		## impacts of work
		tree = makeTree(setToConstantMatrix(current_x,randint(commercial.lower_x, commercial.higher_x)))
		world.setDynamics(current_x,work,tree)
		tree = makeTree(setToConstantMatrix(current_y,randint(commercial.lower_y, commercial.higher_y)))
		world.setDynamics(current_y,work,tree)
		### instead of increments by a constant, we increase by a percentage, so that the changes in one need will be proportionally reflected in the multiplications. That is, instead of weights being multiplied by a certian value each time, they will be multiplied by the amount of change. This way, if one need is not satified, over time, it will get more attention.
		tree = makeTree(approachMatrix(wealth,wealth_cost,100))
		world.setDynamics(wealth,work,tree)

		tree = makeTree(approachMatrix(hunger,hunger_cost,100))
		world.setDynamics(hunger,work,tree)

		tree = makeTree(approachMatrix(comfort,comfort_cost,100))
		world.setDynamics(comfort,work,tree)

		## impacts of eat
		tree = makeTree(approachMatrix(hunger,.9,0))
		world.setDynamics(hunger,eat,tree)

		tree = makeTree(approachMatrix(wealth,eating_cost,0))
		world.setDynamics(wealth,eat,tree)

		tree = makeTree(approachMatrix(health,.9,100))
		world.setDynamics(health,eat,tree)

		risk = stateKey('commercial','risk')
		initialHealth = 100.
		decline_perc = 0.1
		# make future this where we have the value for time T and time T+1, and we are defining the new health value
		# this is basically what it means:
		# future health= current health* (1-decline_perc)+ decline_perc*initialHealth -future risk*(decline_perc/2) -future hunger*(decline_perc/2)
		tree = makeTree(KeyedMatrix({
			makeFuture(health): 
				KeyedVector({
					health: 1.-decline_perc, 
					CONSTANT: decline_perc*initialHealth, 
					# health: 1.,
					#makeFuture(risk): -(decline_perc/2), 
					#makeFuture(risk): -1.*initialHealth,
					makeFuture(hunger): - (decline_perc/2)})}))
		
		# this is the actual effect, has nothing to do with decision making. future risk means 
		world.setDynamics(health,work,tree)


		residential=world.agents['residential']
		## impacts of gohome
		risk = stateKey('residential','risk')
		tree = makeTree(KeyedMatrix({
			makeFuture(health): 
				KeyedVector({
					health: 1.-decline_perc, 
					#CONSTANT: decline_perc*initialHealth, 
					# health: 1.,
					makeFuture(risk): -(decline_perc/2), 
					makeFuture(hunger): - (decline_perc/2)})}))

		world.setDynamics(health,gohome,tree)

		tree = makeTree(setToConstantMatrix(current_x,init_location[0]))
		world.setDynamics(current_x,gohome,tree)
		tree = makeTree(setToConstantMatrix(current_y,init_location[1]))
		world.setDynamics(current_y,gohome,tree)

		tree = makeTree(approachMatrix(comfort,comfort_cost,100))
		world.setDynamics(comfort,gohome,tree)

		tree = makeTree(approachMatrix(hunger,hunger_cost,100))
		world.setDynamics(hunger,gohome,tree)

		

	def attitude_impacts(self):
		# increase the tactical info
		armed_forces_objs= [self.world.agents[name] for name in self.world.agents if isinstance(self.world.agents[name],ArmedForces)]

		provide_info = self.addAction({'verb':'provide_info'})

		for armed_force in armed_forces_objs:
			attitude=binaryKey(self.name, armed_force.name, 'attitude')
			initial_attitude= 0.1 if armed_force.friendly else -0.1
			tactical_info=stateKey(armed_force.name, 'tactical_info')
				
			tree = makeTree({'if': thresholdRow(attitude, initial_attitude), 
				True: approachMatrix(tactical_info, 0.05, 1.0), 
				False: approachMatrix(tactical_info, 0.005, 1.0)})
			world.setDynamics(tactical_info,provide_info,tree)



	# ignore the other people unless they are not civilians
	def init_beliefs(self):
		relevant = {key for key in self.world.state.keys() if (isStateKey(key) and (state2agent(key) == self.name or  state2agent(key)[:8] != 'civilian')) or (isBinaryKey(key) and key2relation(key)['subject']==self.name)}
		return self.resetBelief(include=relevant)


class Region(Agent):
	def __init__(self, name, lower_points, higher_points, max_occupancy, category, world):
		Agent.__init__(self,name)
		world.addAgent(self)
		self.lower_x, self.lower_y = lower_points
		self.higher_x, self.higher_y= higher_points
		self.max_occupancy=max_occupancy

		current_occupancy = world.defineState(self.name,'current_occupancy')
		self.setState('current_occupancy', 0)

		#risk/danger level of being in this region for a civilian health
		risk = world.defineState(self.name,'risk')
		self.setState('risk', 0)

class Environment(Agent):
	def __init__(self, name, world):
		Agent.__init__(self,name)
		world.addAgent(self)
		time_pass=world.defineState(self.name,'time_pass')

		time_of_day=world.defineState(self.name,'time_of_day',lo=0,hi=23)

		time_increase = self.addAction({'verb':'time_increase'})
		self.setState('time_pass', 0)
		self.setState('time_of_day', 0)

		# impact of time_increase
		tree = makeTree(incrementMatrix(time_pass,1))
		world.setDynamics(time_pass,time_increase,tree)

		tree = makeTree({'if': equalRow(time_of_day,23),
			True: setToConstantMatrix(time_of_day,0),
			False: incrementMatrix(time_of_day,1)})
		world.setDynamics(time_of_day,time_increase,tree)

class ArmedForces(Agent):
	def __init__(self, name, world, init_location, friendly):
		Agent.__init__(self,name)
		world.addAgent(self)

		self.friendly=friendly

		current_x=world.defineState(self.name,'current_x')
		current_y=world.defineState(self.name,'current_y')
		self.setState('current_x', init_location[0])
		self.setState('current_y', init_location[1])

		# friendly forces have less tactical info than hostile forces to start with
		tactical_info=world.defineState(self.name,'tactical_info')
		if self.friendly:
			self.setState('tactical_info', 0.05)
		else:
			self.setState('tactical_info', 0.40)

		# the resources that they need to take action, which could be weapons, money, etc
		resources =world.defineState(self.name,'resources') 
		self.setState('resources', 1)
		gather_resources = self.addAction({'verb':'gather_resources'})
		tree = makeTree(incrementMatrix(resources,1))
		world.setDynamics(resources,gather_resources,tree)

		do_good_amount=.10
		do_bad_amount=.10
		# region_names = [name for name in self.world.agents if isinstance(self.world.agents[name],Region)]
		region_objs= [self.world.agents[name] for name in self.world.agents if isinstance(self.world.agents[name],Region)]
		civilian_objs= [self.world.agents[name] for name in self.world.agents if isinstance(self.world.agents[name],Person)]
		
		for civilian in civilian_objs:
			# since the attitudes of civilians towards armed forces change based on the actions of armed forces, we define the attitudes in the armed forces instead of civilians. 
			attitude = self.world.defineRelation(civilian.name, self.name,'attitude', float)
			if self.friendly:
				self.world.setFeature(attitude, 0.1)
			else:
				self.world.setFeature(attitude, -0.1)

		# do_nothing = self.addAction({'verb':'do_nothing'})
		# tree = makeTree(incrementMatrix(current_x,0.)) # it does nothing
		# world.setDynamics(current_x,do_nothing,tree)

		# here we have to write it declaratively because it is not executed now. so we define the actions over all of the regions and their risks but here in the Armed_Forced class where the actions impact the risks
		for region in region_objs:

			# each armed_force can only take action in the region it is in. the tree below checks for that
			tree= makeTree({'if': thresholdRow(current_x, region.lower_x), # if armed_force's current_x is larger than lower end of x_range for this region
				True: {'if': thresholdRow(current_x, region.higher_x), # if the armed_force's x is less than upper end of x_range
					True: False,
					False: {'if': thresholdRow(current_y, region.lower_y), # if armed_force's y is larger than lower end of y_range
						True: {'if': thresholdRow(current_y, region.higher_y), # if the armed_force's y is less than upper end of y_range
							True: False,
							False: {'if': thresholdRow(resources, 30), # if the armed_force's y is less than upper end of y_range
								True: True,
								False: False}},
						False: False}},
				False: False})
			# print(tree[world.state])
			do_good = self.addAction({'verb':'do_good', 'object':region.name}, tree)
			do_bad = self.addAction({'verb':'do_bad', 'object':region.name}, tree)
			
			risk=stateKey(region.name,'risk')

			if friendly:
				self.setReward(minimizeFeature(risk,self.name), 5.)
			else:
				self.setReward(maximizeFeature(risk,self.name), 5.)

			# here if there is more tactical info, aka over 0.3, then the risk is reduced more than otherwise.
			tree = makeTree({'if': thresholdRow(tactical_info, 0.3), 
				True: approachMatrix(risk, do_good_amount + 0.2, 0.0), 
				False: approachMatrix(risk, do_good_amount, 0.0)})
			world.setDynamics(risk,do_good,tree)


			tree = makeTree(incrementMatrix(risk,do_bad_amount))
			#tree = makeTree(approachMatrix(risk,do_bad_amount,1.))
			world.setDynamics(risk,do_bad,tree)
			
			# go through all of the civilians and change their attitudes based on the action that is being taken
			for civilian in civilian_objs:
				attitude=binaryKey(civilian.name, self.name, 'attitude')

				civilian_x=stateKey(civilian.name, 'current_x')
				civilian_y=stateKey(civilian.name, 'current_y')
				
				# below, we have the impact of armed forces' actions on the civilians' attitudes. it approcaches 1 for doing good and -1 for doing bad.
				# here if the civilian is in the same region, the impact on attitude is higher: 0.2, otherwise, for all other cases, it is lower: 0.1
				tree= makeTree({'if': thresholdRow(civilian_x, region.lower_x), 
					True: {'if': thresholdRow(civilian_x, region.higher_x), 
						True: approachMatrix(attitude,0.1,1.0), # when civilian is  NOT in the same region, the impact is lower: .1 
						False: {'if': thresholdRow(civilian_y, region.lower_y), 
							True: {'if': thresholdRow(civilian_y, region.higher_y), 
								True: approachMatrix(attitude,0.1,1.0), # when civilian is  NOT in the same region, the impact is lower: .1 
								False: approachMatrix(attitude,0.2,1.0)}, # when civilian is in the same region, the impact is higher: .2 
							False: approachMatrix(attitude,0.1,1.0)}}, # when civilian is  NOT in the same region, the impact is lower: .1 
					False: approachMatrix(attitude,0.1,1.0)}) # when civilian is  NOT in the same region, the impact is lower: .1 
				world.setDynamics(attitude,do_good,tree)

				tree= makeTree({'if': thresholdRow(civilian_x, region.lower_x), 
					True: {'if': thresholdRow(civilian_x, region.higher_x), 
						True: approachMatrix(attitude,0.1,-1.0), # when civilian is  NOT in the same region, the impact is lower: .1 
						False: {'if': thresholdRow(civilian_y, region.lower_y), 
							True: {'if': thresholdRow(civilian_y, region.higher_y), 
								True: approachMatrix(attitude,0.1,-1.0), # when civilian is  NOT in the same region, the impact is lower: .1 
								False: approachMatrix(attitude,0.2,-1.0)}, # when civilian is in the same region, the impact is higher: .2 
							False: approachMatrix(attitude,0.1,-1.0)}}, # when civilian is  NOT in the same region, the impact is lower: .1 
					False: approachMatrix(attitude,0.1,-1.0)}) # when civilian is  NOT in the same region, the impact is lower: .1
				world.setDynamics(attitude,do_bad,tree)
			
	def init_beliefs(self):
		relevant = {key for key in self.world.state.keys() if (isStateKey(key) and (state2agent(key) == self.name or  state2agent(key)[:8] != 'civilian'))}
		return self.resetBelief(include=relevant)
			# print(world.dynamics[risk][do_bad])
			# print(world.dynamics.keys())
			# print(world.dynamics[do_bad][risk])

def record_results(world, init_weights_str, step_str, date_time):
	
	output_file = open("output/output_%s.txt" % date_time, "a")
	output_file.write(step_str)
	hour_str = step_str.split('\n')[2]
	day_str = step_str.split('\n')[3]

	background_states=['__MODEL__', 'current_occupancy', 'time_pass', 'time_of_day', 'current_x', 'current_y', '__TURN__', '__REWARD__']
	background_agents=['env']

	csv_output = open("output/output_%s.csv" % date_time, "a")
	aggregate_output = open("output/aggregate_%s.csv" % date_time, "a")
	
	if hour_str == ' Step(hr) 1 ' and day_str == ' Day 1 ':
		csv_output.write(init_weights_str)
		output_file.write(init_weights_str)
		# aggregate_output.write(init_weights_str)
	
	
	civilian_count = float(init_weights_str.split(' ')[3])
	# print ('civilian_count : '+str(civilian_count))

	## adding list of the civilian actions as keys to the dict
	step_agg_dict = {}
	aggregate_dict = {}
	for action_set in civilian.actions:
		new_key = 'avg civilian\'s ' + action_set['verb']
		aggregate_dict[new_key]=0
	
	for key in world.state.keys():
		state_value = str(world.getFeature(key, unique=True))

		# remove agent name from action value
		state_value= state_value.split('-')[1] if '-' in state_value else state_value 

		data_pair = key + ' : ' + str(state_value) + '\n'
		output_file.write(data_pair)

		if isStateKey(key):
			agent_str, state_str = state2tuple(key)
			agent_str= agent_str.split(' ')[0] if 'civilian' in agent_str else agent_str
		else:
			agent1_str, agent2_str, state_str = key2relation(key)['subject'], key2relation(key)['object'], key2relation(key)['relation']
			agent1_str= agent1_str.split(' ')[0] if 'civilian' in agent1_str else agent1_str
			agent_str = agent1_str + ' and ' + agent2_str
		
		if state_str not in background_states and agent_str not in background_agents:
			state_str= state_str.replace(agent_str,'') # remove agent name from state_str
			csv_str = hour_str + ', ' + day_str + ', ' + agent_str + ', ' + state_str+ ', ' +state_value + '\n'
			csv_output.write(csv_str)

			# aggregating civilian states
			if 'civilian' in agent_str:
				if state_str == '__ACTION__':
					new_key = 'avg civilian\'s ' + state_value
					#here we are adding each possible action (state_value) as a key for aggregate_dict and keeping the count for each action
					# aggregate_dict[new_key] = 1.0 if new_key not in aggregate_dict.keys() else aggregate_dict[new_key]+ 1
					aggregate_dict[new_key]+= 1
				else:
					new_key = 'avg civilian\'s ' + state_str
					aggregate_dict[new_key] = float(state_value) if new_key not in aggregate_dict.keys() else aggregate_dict[new_key] + float(state_value)
				# print(key)
				# print('key: '+ new_key)
				# print('value: '+ str(aggregate_dict[new_key]))
				# print('state value: '+str(state_value)+'\n')
			else:
				# adding none-civilian rows to the aggregate
				# aggregate_output.write(csv_str)
				step_agg_dict[key]=state_value
	
	aggregate_dict = {key : aggregate_dict[key]/civilian_count for key in aggregate_dict.keys()}
	
	for key in aggregate_dict.keys():
		# aggregate_str = hour_str + ', ' + day_str + ', civilians\' avg, ' + str(key) + ', ' + str(aggregate_dict[key]) + '\n'
		# aggregate_output.write(aggregate_str)
		step_agg_dict[key]=aggregate_dict[key]
	
	# print ('\n hr %s day %s: aggregate dict keys: %s \n\n' %( hour_str, day_str, str(aggregate_dict.keys())))
	step_values_str = hour_str + 'in' + day_str
	if hour_str == ' Step(hr) 1 ' and day_str == ' Day 1 ':
		label_str ='Step'
		for key in step_agg_dict.keys():
			label_str += ', ' + key
			step_values_str += ', '+ str(step_agg_dict[key])
		aggregate_output.write(label_str+'\n')
	else:
		for key in step_agg_dict.keys():
			step_values_str += ', '+ str(step_agg_dict[key])
	aggregate_output.write(step_values_str+'\n')

	aggregate_output.close()
	csv_output.close()
	output_file.close()


if __name__ == '__main__':
	start_time=time()	
	world = World()
	# below, the first tuple is (lower_x, lower_y) and the second one is (higher_x, higher_y)
	# housing_west = Region('housing_west', (0,80), (60,140), 150,'residential', world) 
	# housing_east = Region('housing_east', (180,80), (250,110), 100, 'residential', world)
	# housing_north_east = Region('housing_north_east', (175,120), (185,160), 30, 'residential', world)
	# hotel = Region('hotel', (140,45), (190,70), 80, 'residential', world)
	# business = Region('business', (85,10), (135,40), 100, 'commercial', world)
	# embassy = Region('embassy', (60,45), (85,70), 50, 'commercial', world)
	# food_retail = Region('food_retail', (90,80), (150,120), 100, 'commercial', world)
	#hospital = Region('hospital', (175,170), (200,190), 50, 'commercial', world)
	#jail = Region('jail', (5,20), (30,30), 40, 'commercial', world)

	residential = Region('residential', (30,30), (50,50), 100, 'residential', world)

	commercial = Region('commercial', (75,35), (85,45), 25, 'commercial', world)

	env =Environment('env', world)

	civilians = []
	
	print('\n' + (('|'*86)+'\n'+('-'*86)+'\n')*32) #separating lines

	civilian_count = int(input("Number of civilians: "))
	random_horizon, random_weight_bases, random_costs = False, False, False
	day_count= int(input("Number of days: "))

	for j in range(civilian_count):
		starting_location=(randint(residential.lower_x,residential.higher_x), randint(residential.lower_y,residential.higher_y))
		civilian = Person('civilian_%d' %(j+1), starting_location, world, random_horizon, random_weight_bases, random_costs)
		civilians.append(civilian.name)


	init_weights_str= '# Civilian count, %d \n# Day count, %d \n# Horizon, %d \n# Randomized Weights, %r \n# Wealth Weight, %d \n# Comfort Weight, %d \n# Health Weight, %d \n# Hunger Weight, %d \n' %(civilian_count, day_count, civilian.horizon_value, random_weight_bases,  civilian.wealth_weight, civilian.comfort_weight, civilian.health_weight, civilian.hunger_weight)


	friendly_force_location=(randint(commercial.lower_x, commercial.higher_x), randint(commercial.lower_y, commercial.higher_y))
	
	hostile_force_location=friendly_force_location #both in the same region

	friendly_force=ArmedForces('friendly_force', world, friendly_force_location, True)
	hostile_force=ArmedForces('hostile_force', world, hostile_force_location, False) 
	# print(hostile_force.getLegalActions())
	#exit()
	
	world.setOrder([set(civilians) | {hostile_force.name,friendly_force.name} | {env.name}])

	# for name in civilians:
	# 	world.agents[name].attitude_impacts()
	for name in civilians:
		world.agents[name].init_beliefs()

	world.agents['friendly_force'].init_beliefs()
	world.agents['hostile_force'].init_beliefs()

	date_time = str(localtime()[0])+'_'+str(localtime()[1])+'_'+str(localtime()[2])+'__'+str(localtime()[3])+'_'+str(localtime()[4])+'_'+str(localtime()[5])
	for i in range(24*day_count):
		start_round=time()
		hour=(i%24)+1
		day =int(i/24)+1
		step_str='\n' + '_'*70 + '\n Step(hr) %d \n Day %d \n\n' %(hour, day)
		print(step_str)
		newWorldState = world.step()
		# print(env.getState('time_pass',unique=True))
		# print(env.getState('time_of_day',unique=True))
		# world.explainAction(newState)
		# world.printState(newWorldState)

		## writing the results to the file
		record_results(world, init_weights_str, step_str, date_time)
		end_round = time()
		time_elapsed = round(end_round - start_round)
		step_time= 'Step time: %02d:%02d:%02d \n ' %(int(time_elapsed/3600), int((time_elapsed%3600)/60), time_elapsed%60) + '_'*70 +'\n'
		print(step_time)

		
		# for action,tree in world.dynamics['residential\'s risk'].items():
		# 	print(action)
		#	print(tree)

	end_time=time()
	time_overall = end_time - start_time
	print('Overall time for %d civilians, during %d days: %02d:%02d:%02d' %(civilian_count, day_count, int(time_overall/3600), int(time_overall%3600/60), time_overall%60))