from argparse import ArgumentParser
import csv
import logging
import os
import pickle
import random
import sys

from psychsim.pwl.keys import *

from psychsim.world import World

from .environmental import readHurricanes
from ..simulation.data import likert
from ..simulation.create import getConfig
from ..simulation.execute import nextDay
from ..simulation.actor import Actor

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestTrial.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=20,help='Number of people')
    parser.add_argument('--seed',type=int,default=None,help='Random number generator seed')
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    args = vars(parser.parse_args())
    
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.getLogger().setLevel(level)

    random.seed(args['seed'])
    logging.info('Loading PsychSim scenario')
    dirName = os.path.join(os.path.dirname(__file__),'..','Instances',
                           'Instance%d' % (args['instance']),'Runs','run-%d' % (args['run']))
    inFile = os.path.join(dirName,'scenario.pkl')
    with open(inFile,'rb') as f:
        world = pickle.load(f)

    living = [agent for agent in world.agents.values() if isinstance(agent,Actor) and
              world.getFeature('%s\'s alive' % (agent.name)).first()]
    pool = living[:]
    control = set()
    while len(control) < int(args['samples']/2):
        actor = random.choice(pool)
        control.add(actor.name)
        pool.remove(actor)
    manipulation = set()
    while len(manipulation) < int(args['samples']/2):
        actor = random.choice(pool)
        manipulation.add(actor.name)
        pool.remove(actor)
    
    logging.info('Loading hurricane table')
    hurricanes = readHurricanes(args['instance'],args['run'])
    hurricane = hurricanes[-1]
    if hurricane[-1]['Location'] == 'approaching':
        # Extraneous next hurricane at the end
        hurricane = hurricanes[-2]
    firstDay = hurricane[0]['Timestep']
    lastDay = hurricane[-1]['Timestep']
    lastHurricane = int(hurricanes[-1][0]['Name'])
    state = {'hurricanes': lastHurricane,
             'phase': world.getState('Nature','phase').first()}
    config = getConfig(args['instance'])

    evacuated = set()
    manipulated = False
    while state['hurricanes'] == lastHurricane:
        if state['phase'] == 'approaching' and not manipulated:
            # It's manipulatin' time!
            myScale = likert[5][config.getint('Actors','self_trust')-1]
            optScale = likert[5][config.getint('Actors','friend_opt_trust')-1]
            pessScale = likert[5][config.getint('Actors','friend_pess_trust')-1]
            key = stateKey('Nature','category')
            msg = world.getFeature(key)
            for actor in manipulation:
                world.agents[actor].recvMessage(key,msg,myScale,optScale,pessScale)
            manipulated = True
        nextDay(world,living,[],state,config,dirName)
        for actor in control|manipulation:
            if world.getFeature(stateKey(actor,'location')).first() == 'evacuated':
                evacuated.add(actor)
    outFile = os.path.join(dirName,args['output'])
    fields = ['ParticipantId','Manipulation','Evacuated']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        pool = list(control|manipulation)
        for i in range(len(pool)):
            record = {'ParticipantId': i+1}
            if pool[i] in manipulation:
                record['Manipulation'] = 'yes'
            else:
                record['Manipulation'] = 'no'
            if pool[i] in evacuated:
                record['Evacuated'] = 'yes'
            else:
                record['Evacuated'] = 'no'
            writer.writerow(record)
