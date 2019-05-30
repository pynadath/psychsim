import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
	random.seed(152)
	logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2BA-TA1C-152.log'))
	args = accessibility.instances[0]
	logging.info('Instance %d, Run %d' % (args['instance'],args['run']))
	data = accessibility.loadRunData(args['instance'],args['run'],args['span'])
	demos = accessibility.readDemographics(data,last=args['span'])
	hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
	population = accessibility.getPopulation(data)
	aid = [{t: data['System'][actionKey('System')][t]['object'] for t in range(h['Start'],h['End']+1)} for h in hurricanes]
	recipients = [set(days.values()) for days in aid]
	allRecipients = set().union(*recipients)
	pool = random.sample([name for name in population if demos[name]['Residence'] in allRecipients],12)+\
		random.sample([name for name in population if demos[name]['Residence'] not in allRecipients],4)
	output = []
	for name in pool:
		print(name)
		record = demos[name]
		record['Timestep'] = args['span']
		output.append(record)
		record['Participant'] = len(output)
		for hurricane in hurricanes:
			# 1
			received = demos[name]['Residence'] in recipients[hurricane['Hurricane']-1]
			record['Received Aid Hurricane %d' % (hurricane['Hurricane'])] = 'yes' if received else 'no'
			if received:
				for t in range(hurricane['End'],hurricane['Start']-1,-1):
					if aid[hurricane['Hurricane']-1][t] == demos[name]['Residence']:
						break
				record['Aid Timestep Hurricane %d' % (hurricane['Hurricane'])] = t
				record['Aid Description Hurricane %d' % (hurricane['Hurricane'])] = 'regional'
				regDelta = data[demos[name]['Residence']][stateKey(demos[name]['Residence'],'risk')][t+1]-data[demos[name]['Residence']][stateKey(demos[name]['Residence'],'risk')][t] 
				myDelta = data[name][stateKey(name,'risk')][t+1]-data[name][stateKey(name,'risk')][t]
				if regDelta < 0:
					if myDelta - regDelta > 1e-8:
						record['Aid Impact Hurricane %d' % (hurricane['Hurricane'])] = 'made region safer'
					else:
						record['Aid Impact Hurricane %d' % (hurricane['Hurricane'])] = 'made me safer'
				elif myDelta < 0:
					record['Aid Impact Hurricane %d' % (hurricane['Hurricane'])] = 'made me safer'
				else:
					record['Aid Impact Hurricane %d' % (hurricane['Hurricane'])] = 'no impact'
				record['Why Aid to Region Hurricane %d' % (hurricane['Hurricane'])] = 'don\'t know'
			# 2
			record['Should Have Been Aided Hurricane %d' % (hurricane['Hurricane'])] = 'yes'
			risks = [(data[name][stateKey(name,'risk')][t],t) for t in range(hurricane['Start'],hurricane['End']+1)]
			level,t = max(risks)
			record['Timestep Should Have Been Aided Hurricane %d' % (hurricane['Hurricane'])] = t
			record['Why Should Have Been Aided Hurricane %d' % (hurricane['Hurricane'])] = 'make me safer'
			record['Aid for Experience Hurricane %d' % (hurricane['Hurricane'])] = 'no'
			record['Timestep Aid for Experience Hurricane %d' % (hurricane['Hurricane'])] = 'N/A'
			delta = data[name][stateKey(name,'grievance')][t+1]-data[name][stateKey(name,'grievance')][t]
			if delta < 0:
				record['Dissatisfaction Change Hurricane %d' % (hurricane['Hurricane'])] = -accessibility.toLikert(-50*delta)
			else:
				record['Dissatisfaction Change Hurricane %d' % (hurricane['Hurricane'])] = accessibility.toLikert(50*delta)
			# 3
			risks = [(data[demos[name]['Residence']][stateKey(demos[name]['Residence'],'risk')][t],t) \
				for t in range(hurricane['Start'],hurricane['End']+1) if aid[hurricane['Hurricane']-1][t] != demos[name]['Residence']]
			level,t = max(risks)
			record['Unfair Aid Hurricane %d' % (hurricane['Hurricane'])] = 'yes'
			record['Unfair Aid Timestep Hurricane %d' % (hurricane['Hurricane'])] = t
			record['Unfair Aid Region Hurricane %d' % (hurricane['Hurricane'])] = aid[hurricane['Hurricane']-1][t]
			record['Unfair Aid Should Have Aided Hurricane %d' % (hurricane['Hurricane'])] = demos[name]['Residence']
			record['Unfair Aid Why Should Have Aided Hurricane %d' % (hurricane['Hurricane'])] = 'make region safer'
	fields = ['Timestep','Participant']+sorted(accessibility.demographics.keys())
	fields += sum([['Received Aid Hurricane %d' % (h['Hurricane']),'Aid Timestep Hurricane %d' % (h['Hurricane']),
		'Aid Description Hurricane %d' % (h['Hurricane']),'Aid Impact Hurricane %d' % (h['Hurricane']),
		'Why Aid to Region Hurricane %d' % (h['Hurricane']),'Should Have Been Aided Hurricane %d' % (h['Hurricane']),
		'Timestep Should Have Been Aided Hurricane %d' % (h['Hurricane']),'Why Should Have Been Aided Hurricane %d' % (h['Hurricane']),
		'Aid for Experience Hurricane %d' % (h['Hurricane']),
		'Dissatisfaction Change Hurricane %d' % (h['Hurricane']),'Unfair Aid Hurricane %d' % (h['Hurricane']),
		'Unfair Aid Timestep Hurricane %d' % (h['Hurricane']),
		'Unfair Aid Region Hurricane %d' % (h['Hurricane']),'Unfair Aid Should Have Aided Hurricane %d' % (h['Hurricane']),
		'Unfair Aid Why Should Have Aided Hurricane %d' % (h['Hurricane'])] \
		for h in hurricanes],[])
	accessibility.writeOutput(args,output,fields,fname='TA2A-TA1C-0152.tsv')
