from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random

from ..simulation.create import loadPickle,getConfig
from ..simulation.data import *

def createParser(output=None,day=None,seed=False):
	"""
	:return: dictionary of arguments
	"""
	parser = ArgumentParser()
	parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
	parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
	if output:
		parser.add_argument('-o','--output',default=output,help='Output filename')
	if day:
		parser.add_argument('--day',type=int,default=0,help='Day to start from (default is beginning)')
	if seed:
	    parser.add_argument('--seed',type=int,default=1,help='Random number generator seed')
	parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
	return parser

def parseArgs(parser):
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile)
    if 'seed' in args:
	    random.seed(args['seed'])
    return args

def loadFromArgs(args,world=False,hurricanes=False,participants=False,actions=False,deaths=False,network=False,runData=False):
	values = {'directory': os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (args['run']))}
	if world:
		values['world'] = loadPickle(args['instance'],args['run'],args['day'])
	if participants:
		values['participants'] = readParticipants(args['instance'],args['run'])
	if actions:
		values['actions'] = readActions(args['instance'],args['run'])
	if hurricanes:
		values['hurricanes'] = readHurricanes(args['instance'],args['run'])
	if deaths:
		values['deaths'] = readDeaths(args['instance'],args['run'])
	if network:
		values['network'] = readNetwork(args['instance'],args['run'])
	if runData:
		values['run'] = readRunData(args['instance'],args['run'])
	return values

def writeOutput(args,data,fields=None):
	if fields is None:
		fields = sorted(list(data[0].keys()))
	with open(os.path.join(os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (args['run'])),args['output']),'w') as csvfile:
		writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
		writer.writeheader()
		for record in data:
			writer.writerow(record)
