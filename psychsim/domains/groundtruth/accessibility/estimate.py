from argparse import ArgumentParser
import csv
import logging
import os
import os.path
import pickle
import random
import sys

from psychsim.domains.groundtruth.simulation.create import loadPickle

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('-p','--phase',type=int,default=1,help='Phase to query')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile,filemode='w')
    world = loadPickle(args['instance'],args['run'])
    population = {name for name in world.agents if name[:5] == 'Actor'}

    runDir = os.path.join(os.path.dirname(__file__),'..','Instances',
    	'Instance%d' % (args['instance']),'Runs','run-%d' % (args['run']))
    files = os.listdir(runDir)
    logfiles = [os.path.join(runDir,f) for f in files if os.path.splitext(f)[1] == '.log']

    for root,dirs,files in os.walk('Phase%d' % (args['phase'])):
    	for f in files:
    		if os.path.splitext(f)[1] == '.log':
    			logfiles.append(os.path.join(root,f))

    actors = {name: [] for name in population}
    for f in logfiles:
    	with open(f,'r') as logfile:
    		for line in logfile:
    			if 'Participant' in line:
    				# Survey
    				name = line.split()[-1]
    				actors[name].append(os.path.split(f)[1])
    total = {}
    initial = {}
    TA2A = {}
    TA2B = {}
    print(len(population))
    for name in sorted(population):
    	count = len(actors[name])
    	total[count] = total.get(count,0) + 1
    	count = len([s for s in actors[name] if s == 'align.log'])
    	initial[count] = initial.get(count,0) + 1
    	count = len([s for s in actors[name] if 'TA2A' in s])
    	TA2A[count] = TA2A.get(count,0) + 1
    	count = len([s for s in actors[name] if 'TA2B' in s])
    	TA2B[count] = TA2B.get(count,0) + 1
    for histogram in [total,initial,TA2A,TA2B]:
    	assert sum(list(histogram.values())) == len(population)
    	print([(i,histogram[i]) for i in range(max(histogram)+1)])
    	print(sum([histogram[i] for i in range(1,max(histogram)+1)]))