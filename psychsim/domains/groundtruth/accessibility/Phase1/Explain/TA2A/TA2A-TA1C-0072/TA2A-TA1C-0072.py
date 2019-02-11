"""

Research method Category:
Brief from Expert Observer

Specific question:
We want to send researchers to live with all residents in region06 and region09 (approximately 5% of the overall population) ahead of a future hurricane, and record the actions/attitudes from each resident with whom they reside. We will ask researchers to always remain with the people with whom they live (e.g. If the resident goes to the shelter, our researcher will go to the shelter, too). We want them to live together and record things daily as long as we can afford to do so.
We want them to ask the person they live with the following questions, and record their answers each day.

1. The timestep of this day (e.g. If it’s 1 day after timestep 82 in the known hurricane season, it would be 83)

2. The wealth level of this person(family) on that day.

3. Whether this person has any kind of wealth decrease on that day, if so, list all reasons for the wealth decrease (include decrease not directly caused by the hurricane strike, like money spent on evacuation, giving others money, etc)

4. Whether this person has any kind of wealth increase on that day, if so, list all reasons for the wealth increase
(Please note for 3 and 4, if this person has some type of  wealth decrease and increase on the same day, and the net wealth change is 0, we still need to record both the wealth increase and decrease)
  
5. The net wealth change for that day, increase, decrease or no change (The exact wealth change may not be significant enough to cause a wealth level change, we want to know the exact wealth net change)
  
6. Whether this person’s health suffers minor injury (but not require hospitalization) on that day, if so, how serious is the minor injury.(1 to 5, 5 for the most serious)
  
7. Whether this person gets injured (requiring hospitalization) on that day, if so, how serious is the injury.(On a scale of 1 to 5, 5 being the most serious)
  
8. The number of this individual’s children who get new minor injuries(not requiring hospitalization) on that day.
  
9.  The number of this individual’s children who get new serious injuries(requiring hospitalization) on that day.
  
10. The location of this person (In shelter/ its own region/ evacuation(out of the area)/in hospital) on that given day.
   
11. How many people do they know who get injured (require hospitalization) on that day? Also, describe their relationship. 
	We want the answers to be in the following format:
		Relationship			Number
		Acquaintances		  	  2
		Family			  	  1
		Friend 				  0
       People in the same region	  5
Others (specify the relationship and numbers)
   
12. How many people do they know whose children got injured (require hospitalization) on that day? Describe their relationship. 
   
13. How many people do they know that suffer wealth loss on that day? Describe their relationship. 
   
14. How many people do they know have wealth gain on that day? Describe their relationship. 
  
16. How many people do they know that evacuate on that day? Describe their relationship. 
    
17. How many people do they know that get into a shelter on that day? Describe their relationship. 
       Here are some important notes for questions 11 to 15:
		i) We only record the events that happen on that day. For example, if one hears a friend newly get injured (and require hospitalization) on that day, we will record it as one event, however, if this friend keeps the “injured” state for several days, as long as they do not get a new injury, we don’t count this after the first day when the injury happened.
       
18. The dissatisfaction level for government during all previous hurricanes reported on that day. (On a scale of 1 to 5, 5 is the most dissatisfied) 
       
19. The risk level for government during all previous hurricanes reported on that day. (On a scale of 1 to 5, 5 being the most severe risk) 
       
19. The severity of the current hurricane/incoming hurricane this person thinks is being reported on that day.(On a scale of 1 to 5, 5 for most severe hurricane) 
       
20. All the content this person heard from government broadcast every day.
       
21. Record whether this person receives aid from his/her acquaintances on that day.


Sampling strategy:
All people in region06 and region09.

Other applicable detail:

Research request identifier:
TA2A-TA1C-0072-RR


"""
import os
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
	random.seed(72)
	parser = accessibility.createParser(output='TA2A-TA1C-0072-RR.tsv')
	parser.add_argument('--hurricane',type=int,default=1,help='Hurricane to experience')
	args = accessibility.parseArgs(parser,'%s.log' % (os.path.splitext(__file__)[0]))
	structures = accessibility.loadFromArgs(args,world=True,hurricanes=True)
	hurricane = structures['hurricanes'][args['hurricane']-1]
	world = structures['world']
	data = accessibility.loadRunData(args['instance'],args['run'],hurricane['End']+1)
	regions = {'Region06','Region09'}
	pool = {name for name in world.agents if name[:5] == 'Actor' and world.agents[name].home in regions}
	# Prosocial behavior
	aid = {r: set() for r in regions}
	for name in pool:
		region = world.agents[name].home
		aid[region] |= {day for day in range(hurricane['Start'],hurricane['End']+1)
			if data[name][actionKey(name)][day]['verb'] == 'decreaseRisk'}
	seq = list(pool)
	random.shuffle(seq)
	# Demographics
	survey = []
	fields = ['Participant']+sorted(accessibility.demographics.keys())
	fields.remove('Wealth')
	for participant in range(len(seq)):
		name = seq[participant]
		record = {'Participant': participant+1}
		record.update(accessibility.getDemographics(world.agents[name]))
		del record['Wealth']
		survey.append(record)
	accessibility.writeOutput(args,survey,fields,'TA2A-TA1C-0072-PreSurvey.tsv')
	# Journal
	journal = []
	fields = ['Timestep','Participant','Wealth','Wealth Decrease','Wealth Increase','Wealth Change',
		'Minor Injury','Minor Injury Severity','Serious Injury','Serious Injury Severity',
		'Child Minor Injury','Child Minor Injury Severity','Child Serious Injury','Child Serious Injury Severity',
		'Location']
	groups = ['Acquaintances','Family','Friends','People in Region']
	for field in ['Injured %s','Injured Children of %s','%s Wealth Loss','%s Wealth Gain','%s Evacuated','%s Sheltered']:
		fields += [field % (g) for g in groups]
	fields += ['Dissatisfaction','Risk','Severity','Acquaintance Aid']
	for day in range(hurricane['Start'],hurricane['End']+1):
		for participant in range(len(seq)):
			name = seq[participant]
			agent = world.agents[name]
			record = {'Timestep': day,
				'Participant': participant+1}
			# 2
			value = data[name][stateKey(name,'resources')][day]
			record['Wealth'] = int(value*5.1)
			# 3
			delta = value - data[name][stateKey(name,'resources')][day-1]
			record['Wealth Decrease'] = 'yes' if delta < 0. else 'no'
			# 4
			record['Wealth Increase'] = 'yes' if delta > 0. else 'no'
			# 5
			if record['Wealth Increase'] == 'yes' or record['Wealth Decrease'] == 'yes':
				record['Wealth Change'] = accessibility.toLikert(abs(delta)/0.4)
			else:
				record['Wealth Change'] = 'NA'
			# 6
			value = data[name][stateKey(name,'health')][day]
			old = data[name][stateKey(name,'health')][day-1]
			if value < 0.5 and old >= 0.5:
				record['Minor Injury'] = 'yes'
				record['Minor Injury Severity'] = accessibility.toLikert((value-0.2)/0.3)
			else:
				record['Minor Injury'] = 'no'
				record['Minor Injury Severity'] = 'NA'
			# 7
			if value < 0.2 and old >= 0.2:
				record['Serious Injury'] = 'yes'
				record['Serious Injury Severity'] = accessibility.toLikert(value/0.2)
			else:
				record['Serious Injury'] = 'no'
				record['Serious Injury Severity'] = 'NA'
			# 8
			if agent.kids > 0:
				value = data[name][stateKey(name,'childrenHealth')][day]
				old = data[name][stateKey(name,'childrenHealth')][day-1]
				if value < 0.5 and old >= 0.5:
					record['Child Minor Injury'] = 'yes'
					record['Child Minor Injury Severity'] = accessibility.toLikert((value-0.2)/0.3)
				else:
					record['Child Minor Injury'] = 'no'
					record['Child Minor Injury Severity'] = 'NA'
			# 9
				if value < 0.2 and old >= 0.2:
					record['Child Serious Injury'] = 'yes'
					record['Child Serious Injury Severity'] = accessibility.toLikert(value/0.2)
				else:
					record['Child Serious Injury'] = 'no'
					record['Child Serious Injury Severity'] = 'NA'
			else:
				record['Child Minor Injury'] = 'NA'
				record['Child Minor Injury Severity'] = 'NA'
				record['Child Serious Injury'] = 'NA'
				record['Child Serious Injury Severity'] = 'NA'
			# 10
			record['Location'] = data[name][stateKey(name,'location')][day]
			if record['Location'] == 'shelter11':
				record['Location'] = 'shelter'
			elif record['Location'] == agent.home:
				record['Location'] = 'own region'
			# 11
			for key in data[name]['__beliefs__']:
				if state2agent(key) != name and state2feature(key) == 'health':
					raise NotImplementedError
			record['Injured Acquaintances'] = 0
			record['Injured Family'] = 0
			record['Injured Friends'] = 0
			record['Injured People in Region'] = 0
			# 12
			record['Injured Children of Acquaintances'] = 0
			record['Injured Children of Family'] = 0
			record['Injured Children of Friends'] = 0
			record['Injured Children of People in Region'] = 0
			# 13
			record['Acquaintances Wealth Loss'] = 0
			record['Family Wealth Loss'] = 0
			record['Friends Wealth Loss'] = 0
			record['People in Region Wealth Loss'] = 0
			# 14
			record['Acquaintances Wealth Gain'] = 0
			record['Family Wealth Gain'] = 0
			record['Friends Wealth Gain'] = 0
			record['People in Region Wealth Gain'] = 0
			# 16
			record['Acquaintances Evacuated'] = 0
			record['Family Evacuated'] = 0
			record['Friends Evacuated'] = 0
			record['People in Region Evacuated'] = 0
			# 17
			record['Acquaintances Sheltered'] = 0
			record['Family Sheltered'] = 0
			record['Friends Sheltered'] = 0
			record['People in Region Sheltered'] = 0
			# 18
			record['Dissatisfaction'] = accessibility.toLikert(data[name][stateKey(name,'grievance')][day])
			# 19
			record['Risk'] = accessibility.toLikert(float(data[name]['__beliefs__'][stateKey(name,'risk')][day]))
			# 19
			record['Severity'] = int(round(float(data[name]['__beliefs__'][stateKey('Nature','category')][day])))
			# 20
			record['Government Broadcast'] = 'none'
			# 21
			record['Acquaintance Aid'] = 'yes' if day in aid[agent.home] else 'no'
			journal.append(record)
	accessibility.writeOutput(args,journal,fields)