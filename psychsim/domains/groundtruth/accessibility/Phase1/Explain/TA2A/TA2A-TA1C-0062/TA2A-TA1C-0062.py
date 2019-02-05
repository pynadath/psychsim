"""
Research method category:
Survey

Specific question:
	We are asking people at their workplace about their social networks and their communication/interactions during the hurricane.
1. The total number of acquaintances you have(within or outside your region).
2. What information do you get from your friends from time 1 to 82, does that include:
a. Personal injury, whether they(and their family members) are seriously injured(Requiring hospitalization)
b. Personal injury, whether they(and their family members) have minor injures?(Not requiring hospitalization)
c. Personal wealth loss, whether their family have wealth loss?
d. Hurricane information (e.g. predicted category, predicted path, current location), if so, write down a description of such information.
e. Personal experience receiving government aid: Does the government provide aid to their family?
f. Regional damage: Information regarding the damage caused by the hurricane in their region(e.g. Injury caused, damage caused, etc) If so, describe at most 5 messages you heard in this area.
g. Regional government aid: GovernmentÕs aid to one particular region
h. Others, please describe.
If true for any of these, describe the content and how many times they get it.
3. We want to ask whether they get this information (a-h) from acquaintances (exclude ÔfriendsÕ). If so, describe the content and how many times they get it.
4. We want to ask whether they get this information (a-h) from any public sources (media, government broadcast, TV, etc)
5. We want to inquire whether they get any kind of support from their friends (e.g. financial aid) If so, describe the content and times.
6. We want to inquire whether they get any kind of support from their acquaintances(excluding friends (e.g. financial aid) If so, describe the content and times.
7. Do they have any other relationship with others in the world (except for ÔfamilyÕ, ÔfriendsÕ, ÔacquaintancesÕ) If so, please describe the relationship and tell us how many people they know with that specific relationship.

Sampling strategy:
	All people from region06, 09, 02, if we cannot afford so many, we want all people from region06 and 09.

Other applicable detail:
Research request identifier: 
TA2A-TA1C-0062-RR-R1
"""
import logging
import os.path
from psychsim.pwl.keys import stateKey,actionKey
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
	parser = accessibility.createParser(output='TA2A-TA1C-0062-RR-R1.tsv',day=True)
	args = accessibility.parseArgs(parser,'%s.log' % (os.path.splitext(__file__)[0]))
	structures = accessibility.loadFromArgs(args,world=True,network=True)
	data = accessibility.loadRunData(args['instance'],args['run'],args['day'])
	world = structures['world']
	network = structures['network']
	pool = {name for name in world.agents if name[:5] == 'Actor' and world.agents[name].home in {'Region06','Region09','Region02'}}
	survey = []
	questions = ['Serious Injury','Minor Injury','Wealth Loss','Hurricane','Aid','Damage','Regional Aid']
	for name in sorted(pool):
		record = accessibility.getDemographics(world.agents[name])
		record['Wealth'] = int(data[name][stateKey(name,'resources')][82]*5.1)
		survey.append(record)
		record['Participant'] = len(survey)
		logging.info('Participant %03d: %s' % (record['Participant'],name))
		# 1
		record['Acquaintances'] = len(network['friendOf'][name])+len(network['neighbor'][name])
		# 2
		for question in questions:
			if question == 'Hurricane':
				record['Friend %s' % (question)] = 'none'
			else:
				record['Friend %s' % (question)] = 'No'
		if len(network['friendOf'][name]) > 0:
			record['Friend Hurricane'] = 'category'
			record['Friend Frequency'] = 'daily'
		# 3
		for question in questions:
			if question == 'Hurricane':
				record['Acquaintance %s' % (question)] = 'none'
			else:
				record['Acquaintance %s' % (question)] = 'No'
		# 4
		for question in questions:
			if question == 'Hurricane':
				record['Public %s' % (question)] = 'category,location'
			elif question in {'Regional Aid','Damage'}:
				record['Public %s' % (question)] = 'Yes'
			else:
				record['Public %s' % (question)] = 'No'
		record['Public Frequency'] = 'daily'
		# 5
		record['Friend Support'] = 'No'
		# 6
		days = set()
		for neighbor in network['neighbor'][name]:
			for day,action in data[neighbor][actionKey(neighbor)].items():
				if action['verb'] == 'decreaseRisk' and action['object'] == world.agents[name].home:
					days.add(day)
		if len(days) == 0:
			record['Acquaintance Support'] = 'No'
		else:
			record['Acquaintance Support'] = 'Yes'
			if len(days) < 4:
				record['Acquaintance Support Frequency'] = 'monthly'
			elif len(days) < 40:
				record['Acquaintance Support Frequency'] = 'weekly'
			else:
				record['Acquaintance Support Frequency'] = 'daily'
		# 7
	fields = ['Participant']+sorted(accessibility.demographics.keys())+['Acquaintances']\
		+['Friend %s' % (q) for q in questions+['Frequency']]\
		+['Acquaintance %s' % (q) for q in questions+['Frequency']]+['Public %s' % (q) for q in questions+['Frequency']]\
		+['Friend Support','Friend Support Frequency','Acquaintance Support','Acquaintance Support Frequency','Other Relationships']
	accessibility.writeOutput(args,survey,fields)