from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *

from psychsim.domains.groundtruth.simulation.create import loadPickle
from psychsim.domains.groundtruth.simulation.data import *
from psychsim.domains.groundtruth.simulation.execute import demographics

def findMatch(record,population,mismatch,survey):
    for name in sorted(population):
        for field,feature in sorted(demographics.items()):
            key = stateKey(name,feature)
            if world.variables[key]['domain'] is bool:
                value = {True: 'yes',False: 'no'}[world.agents[name].getState(feature).first()]
            elif feature == 'resources':
                # Wealth has changed since beginning
                continue
            else:
                value = str(world.agents[name].getState(feature).first())
            if record[field] != value:
                try:
                    mismatch[field].append(name)
                except KeyError:
                    mismatch[field] = [name]
                break
        else:
            logging.info('%s %s, Participant %s: %s' % (survey,row['Hurricane'],row['Participant'],name))
            return name
    else:
        raise ValueError('No match for %s (mismatches: %s)' % (row['Participant'],mismatch))

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile,filemode='w')
    hurricanes = readHurricanes(args['instance'],args['run'])
    network = readNetwork(args['instance'],args['run'])
    world = loadPickle(args['instance'],args['run'])
    population = {name for name in world.agents if name[:5] == 'Actor'}
    # Verify that actor variable values match pickled scenario
    inFile = os.path.join(os.path.dirname(__file__),'RunDataTable.tsv')
    injured = {}
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['Timestep'] == '1' and row['VariableName'][:6] == 'Actor ':
                agent = world.agents[row['EntityIdx']]
                feature = row['VariableName'][6:]
                if stateKey(agent.name,feature) in world.variables:
                    assert str(agent.getState(feature).first()) == row['Value']
            elif row['VariableName'] == 'Actor health':
                if row['EntityIdx'] not in injured:
                    injured[row['EntityIdx']] = []
                if float(row['Value']) < 0.2:
                    injured[row['EntityIdx']].append(int(row['Timestep']))
    # Identify respondents from pickled scenario
    inFile = os.path.join(os.path.dirname(__file__),'ActorPostTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            mismatch = {}
            actor = findMatch(row,population,mismatch,'PostSurvey')
    inFile = os.path.join(os.path.dirname(__file__),'ActorPreTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            mismatch = {}
            actor = findMatch(row,population,mismatch,'PreSurvey')
