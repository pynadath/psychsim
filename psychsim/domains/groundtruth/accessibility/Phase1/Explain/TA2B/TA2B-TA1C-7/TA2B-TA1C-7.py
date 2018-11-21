"""
Research method category: Survey

Specific questions to be answered by the sampled households:
This survey is meant to be deployed to households. A single custodial adult should respond to the questions for the household. 

0. Ask the post hurricane demographics questions (age, children, ethnicity, fulltime job, gender, pets, region, religion)
For each hurricane "N" :
1. How many children do you have? (integer 0+; if 0, no need to answer questions 2-4)
2. If you evacuated for hurricane N, did you bring all of your children with you? (Yes / No / Did not evacuate)
3. If you went to a shelter for hurricane N, did you bring all of your children with you? (Yes / No / Did not go to shelter)
4. How many of your children suffered from casualties in hurricane N? (integer 0+)

Sampling strategy:
50% random sample of all households.

Other applicable detail:
Hypothesis: Our general hypothesis about this scenario right now is: The decision to evacuate is a cost benefit calculation conducted by the individual household. Benefits are reduced risk of injury. Costs are lost wages, logistical cost, lost property, and inability to shelter/transport pets. We hypothesize that families with children bear more logistical costs and are more risk averse to lost wages as well as injury. Sheltering is an alternate option to evacuation that has lower logistical cost. However, inadequate capacity or distance may be limiting the use of shelters. The outcome of interest is: casualties. This research request helps us test the part of the hypothesis related to children.

Research request identifier: 7children_survey
"""
from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random


from psychsim.domains.groundtruth.simulation.create import loadPickle
from psychsim.domains.groundtruth.simulation.data import readHurricanes,toLikert
from psychsim.domains.groundtruth.simulation.execute import demographics

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('--sampling',type=float,default=0.1,help='% of actors to sample')
    parser.add_argument('--seed',type=int,default=1,help='Random number generator seed')
    parser.add_argument('-o','--output',default='TA2B-TA1C-7.tsv',help='Output filename')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile)
    random.seed(args['seed'])
    root = os.path.join(os.path.dirname(__file__),'..','..','..','..','..')
    hurricanes = readHurricanes(args['instance'],args['run'])

    population = set()
    dead = set()

    data = {}
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RunDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
        	if row['VariableName'][:5] == 'Actor' and row['VariableName'][6:] in demographics.values():
        		if row['EntityIdx'] not in population:
	        		population.add(row['EntityIdx'])
	        		data[row['EntityIdx']] = {'evacuate': set(), 'moveTo': set(), 'casualties': set()}
	        	data[row['EntityIdx']][row['VariableName'][6:]] = row['Value']
        	if row['VariableName'] == 'Actor alive' and row['Value'] == 'False' and row['EntityIdx'] not in dead:
        		dead.add(row['EntityIdx'])
        	elif row['VariableName'] == 'Actor action' and row['EntityIdx'] not in dead:
        		for index in range(len(hurricanes)):
        			if hurricanes[index]['Start'] < int(row['Timestep']) < hurricanes[index]['End']:
        				action = row['Value'].split('-')
        				if action[1] == 'evacuate':
        					data[row['EntityIdx']][action[1]].add(index+1)
        				elif action[1] == 'moveTo' and action[2][:7] == 'shelter':
        					data[row['EntityIdx']][action[1]].add(index+1)
        				break
        	elif row['VariableName'] == 'Actor childrenHealth' and row['EntityIdx'] not in dead and float(row['Value']) < 0.2:
        		for index in range(len(hurricanes)):
        			if hurricanes[index]['Start'] < int(row['Timestep']) < hurricanes[index]['End']:
        				data[row['EntityIdx']]['casualties'].add(index+1)
        				break
    pool = population - dead
    samples = []
    numSamples = args['sampling']*len(pool)
    fieldSet = False

    while len(samples) < numSamples:
    	actor = random.choice(list(pool))
    	print(data[actor])
    	pool.remove(actor)
    	record = {'Participant ID': len(samples)+1}
    	logging.info('Participant %d: %s' %(record['Participant ID'],actor))
    	if not fieldSet and data[actor]['children'] != '0':
	    	fields = list(record.keys())+sorted(demographics.keys())
    	for label,feature in demographics.items():
    		if feature in {'employed','pet'}:
	    		record[label] = {'False': 'no','True': 'yes'}[data[actor][feature]]
	    	elif feature == 'resources':
	    		record[label] = toLikert(float(data[actor][feature]))
	    	else:
	    		record[label] = data[actor][feature]
    	for hurricane in hurricanes:
    		key = 'Hurricane %d, # Children' % (hurricane['Hurricane'])
    		record[key] = data[actor]['children']
	    	if not fieldSet and data[actor]['children'] != '0':
	    		fields.append(key)
    		if int(data[actor]['children']) > 0:
    			if hurricane['Hurricane'] in data[actor]['evacuate']:
    				record['Hurricane %d, Evacuate Children' % (hurricane['Hurricane'])] = 'Yes'
    			else:
    				record['Hurricane %d, Evacuate Children' % (hurricane['Hurricane'])] = 'Did not evacuate'
    			if hurricane['Hurricane'] in data[actor]['moveTo']:
    				record['Hurricane %d, Shelter Children' % (hurricane['Hurricane'])] = 'Yes'
    			else:
    				record['Hurricane %d, Shelter Children' % (hurricane['Hurricane'])] = 'Did not shelter'
    			if hurricane['Hurricane'] in data[actor]['casualties']:
    				record['Hurricane %d, Casualties Children' % (hurricane['Hurricane'])] = data[actor]['children']
    			else:
    				record['Hurricane %d, Casualties Children' % (hurricane['Hurricane'])] = 0
		    	if not fieldSet and data[actor]['children'] != '0':
    				fields.append('Hurricane %d, Evacuate Children' % (hurricane['Hurricane']))
    				fields.append('Hurricane %d, Shelter Children' % (hurricane['Hurricane']))
    				fields.append('Hurricane %d, Casualties Children' % (hurricane['Hurricane']))
    	if not fieldSet and data[actor]['children'] != '0':
    		fieldSet = True
    	samples.append(record)
    with open(args['output'],'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in samples:
        	writer.writerow(record)