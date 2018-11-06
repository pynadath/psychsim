"""
Research method category: Environmental data

Specific question:
We would like the number of shelters in each region of the original data and each of their capacities.

Sampling strategy:
Collect data from government databases and records

Other applicable detail:
Hypothesis: Our general hypothesis about this scenario right now is: The decision to evacuate is a cost benefit calculation conducted by the individual household. Benefits are reduced risk of injury. Costs are lost wages, logistical cost, lost property, and inability to shelter/transport pets. We hypothesize that families with children bear more logistical costs and are more risk averse to lost wages as well as injury. Sheltering is an alternate option to evacuation that has lower logistical cost. However, inadequate capacity or distance may be limiting the use of shelters. The outcome of interest is: casualties. This research request helps us test the part of the hypothesis related to shelters.

Research request identifier: 6shelters
"""
from argparse import ArgumentParser
import csv
import logging
import os
import os.path
import pickle

from psychsim.pwl.keys import stateKey
from psychsim.domains.groundtruth.simulation.data import toLikert
from psychsim.domains.groundtruth.simulation.create import *
from psychsim.domains.groundtruth.simulation.execute import getDemographics

reasonMapping = {'resources': 'financial',
                 }
    

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    try:
    	os.remove(logfile)
    except FileNotFoundError:
    	pass
    logging.basicConfig(level=level,filename=logfile)
    world = loadPickle(args['instance'],args['run'])

    data = []
    population = [name for name in world.agents if name[:5] == 'Actor']
    fields = ['Region','Shelter','Capacity']
    for region in sorted([name for name in world.agents if name[:6] == 'Region']):
    	key = stateKey(region,'shelterRisk')
    	if key in world.variables:
    		data.append({'Region': region,
    			'Shelter': 1,
    			'Capacity': len(population)})

    with open('TA2B-TA1C-6.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in data:
            writer.writerow(record)