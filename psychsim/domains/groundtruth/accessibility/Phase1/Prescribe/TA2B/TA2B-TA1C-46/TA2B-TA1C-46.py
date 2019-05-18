import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
	random.seed(46)
	logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2B-TA1C-46.log'))
	fields = ['Timestep','Participant']+sorted(accessibility.demographics)+['Tax Frequency','Personal Assistance','Regional Assistance']
	for instance in range(2,14):
		args = accessibility.instances[instance]
		logging.info('Instance %d, Run %d' % (args['instance'],args['run']))
		data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'])
		size = len([name for name in data if name[:5] == 'Actor'])
		demos = accessibility.readDemographics(data,last=args['span'])
		hurricanes = accessibility.readHurricanes(args['instance'],args['run'],'Input')
		population = accessibility.getPopulation(data)
		sample = random.sample(population,size//10)
		output = []
		for name in sample:
			record = demos[name]
			record['Timestep'] = args['span']
			output.append(record)
			record['Participant'] = len(output)
			logging.info('Participant %d: %s' % (record['Participant'],name))
			record['Tax Frequency'] = 'never'
			record['Personal Assistance'] = 'no'
			for day in range(hurricanes[-1]['Start'],hurricanes[-1]['End']+1):
				if data['System'][actionKey('System')][day]['object'] == demos[name]['Residence']:
					record['Regional Assistance'] = 'yes'
					break
			else:
				record['Regional Assistance'] = 'no'
		accessibility.writeOutput(args,output,fields,'TA2B-TA1C-46.tsv',
			os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0'))