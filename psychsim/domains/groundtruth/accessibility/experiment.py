from argparse import ArgumentParser
import csv
import logging
import os
import pickle
import random
import sys

from psychsim.pwl.keys import *

from psychsim.world import World

from ..simulation.data import toLikert
from .environmental import readHurricanes
from ..simulation.create import getConfig
from ..simulation.execute import nextDay
from ..simulation.actor import Actor

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestExperiment.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=1,help='Number of regions to change')
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
    groups = []
    regions = [region for region in world.agents if region[:6] == 'Region']
    deaths = {region: len([actor for actor in world.agents if actor[:5] == 'Actor' and
                           world.agents[actor].home == region and
                           world.agents[actor] not in living]) for region in regions}
    target = random.choice(regions)
    while len([agent.name for agent in living if agent.home == target]) == 0:
        regions.remove(target)
        if len(regions) == 0:
            raise RuntimeError('Unable to find populated region!')
        target = random.choice(regions)
    
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

    while state['hurricanes'] == lastHurricane:
        agents = world.next()
        turn = world.agents[next(iter(agents))].__class__.__name__
        if turn == 'Actor' and state['phase'] != 'none':
            residents = [actor.name for actor in living if actor.home == target]
            nonPro = []
            actions = {actor.name: actor.decide()
                       for actor in living if actor.home == target}
            count = 0
            for actor,decision in actions.items():
                for key in decision:
                    if key != 'policy':
                        actions[actor] = decision[key]['action']
                        break
                else:
                    raise ValueError('No viable model for agent %s' % (actor))
                if actions[actor]['verb'] == 'decreaseRisk':
                    count += 1
                else:
                    nonPro.append(actor)
            if count == 0:
                count = 1
            delta = int(round(count*1.25))
            if delta == count:
                delta += 1
            poolSize = len(nonPro)
            while nonPro and len(nonPro) > poolSize-delta:
                # More people to turn
                actor = random.choice(nonPro)
                nonPro.remove(actor)
                for action in world.agents[actor].actions:
                    if action['verb'] == 'decreaseRisk':
                        actions[actor] = action
                        break
                else:
                    raise ValueError('No prosocial actions for %s' % (actor))
        else:
            actions = None
        nextDay(world,living,[],state,config,dirName,actions={'Actor': actions})
    start = world.getState(WORLD,'day').first()
    risk = {region: 0. for region in deaths}
    while state['today'] < start+7:
        for region in deaths:
            risk[region] += world.getFeature(stateKey(region,'risk')).expectation()/7.
        nextDay(world,living,[],state,config,dirName)

    outFile = os.path.join(dirName,args['output'])
    fields = ['Region','Manipulation','Risk','Deaths']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for region in deaths:
            deaths[region] -= len([actor for actor in world.agents if actor[:5] == 'Actor' and
                                   world.agents[actor].home == region and
                                   world.agents[actor] not in living])
            record = {'Region': region,
                      'Deaths': deaths[region],
                      'Risk': toLikert(risk[region])}
            if region == target:
                record['Manipulation'] = 'yes'
            else:
                record['Manipulation'] = 'no'
            writer.writerow(record)
