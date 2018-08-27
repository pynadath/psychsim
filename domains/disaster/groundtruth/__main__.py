from argparse import ArgumentParser
import cProfile
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import csv
import logging
import os
import os.path
import pstats
import random
import sys
import time


if (sys.version_info > (3, 0)):
    from configparser import ConfigParser
else:
    from ConfigParser import SafeConfigParser as ConfigParser

import psychsim.probability
from psychsim.pwl import *
from psychsim.action import powerset
from psychsim.reward import *
from psychsim.world import *
from psychsim.agent import Agent
from psychsim.ui.diagram import Diagram

from data import likert,toLikert
from region import Region
from nature import Nature
from system import System
from group import Group
from actor import Actor
from cdf import *

def writeHurricane(world,hurricane,dirName):
    fields = ['Timestep','Name','Category','Location']
    today = world.getState(WORLD,'day').first()
    if hurricane == 0:
        mode = 'w'
    else:
        mode = 'a'
    with open(os.path.join(dirName,'HurricaneTable'),mode) as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        if hurricane == 0:
            writer.writeheader()
        else:
            phase = world.getState('Nature','phase').first()
            if phase != 'none':
                record = {}
                for field in fields:
                    if field == 'Timestep':
                        record[field] = today
                    elif field == 'Name':
                        record[field] = hurricane
                    else:
                        record[field] = world.getState('Nature',field.lower()).first()
                    if field == 'Location':
                        if phase == 'approaching':
                            record[field] = phase
                        elif record[field] == 'none':
                            record[field] = 'leaving'
                writer.writerow(record)
                
def writeCensus(world,regions,dirName):
    census = {'Population': None,
              'Gender': 'gender',
              'Ethnicity': 'ethnicGroup',
              'Religion': 'religion',
              'Age': 'age',
              'Employment': 'employed',
    }
    fields = ['Region','Field','Value','Count']
    with open(os.path.join(dirName,'CensusTable'),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        ages = [a.age for a in world.agents.values() if isinstance(a,Actor)]
        limits = [18]+[i for i in range(25,max(ages),5)]
        labels = ['<%d' % (limits[0])]
        labels += ['%d-%d' % (limits[i],limits[i+1]-1) for i in range(len(limits)-1)]
        labels.append('>%d' % (limits[-1]-1))
        for field,feature in census.items():
            if field == 'Population':
                total = 0
            else:
                total = {}
            for name,table in regions.items():
                if field == 'Population':
                    record = {'Region': name,
                              'Field': field,
                              'Count': len(table['inhabitants']) + \
                              sum([a.kids for a in table['inhabitants']])}
                    writer.writerow(record)
                    total += record['Count']
                elif field == 'Age':
                    histogram = [0 for limit in limits]
                    histogram.append(0)
                    for agent in table['inhabitants']:
                        histogram[0] += agent.kids
                        for i in range(len(limits)):
                            if agent.age < limits[i]:
                                histogram[i] += 1
                                break
                    else:
                        histogram[-1] += 1
                    for i in range(len(histogram)):
                        record = {'Region': name,
                                  'Field': field,
                                  'Value': labels[i],
                                  'Count': histogram[i]}
                        writer.writerow(record)
                        total[record['Value']] = total.get(record['Value'],0)+record['Count']
                else:
                    histogram = {}
                    for agent in table['inhabitants']:
                        value = agent.getState(feature).first()
                        histogram[value] = histogram.get(value,0) + 1
                    for value,count in histogram.items():
                        total[value] = total.get(value,0) + count
                        record = {'Region': name,
                                  'Field': field,
                                  'Value': value,
                                  'Count': count}
                        writer.writerow(record)
            if field == 'Population':
                record = {'Region': 'All',
                          'Field': field,
                          'Count': total}
                writer.writerow(record)
            else:
                for value,count in sorted(total.items()):
                    record = {'Region': 'All',
                              'Field': field,
                              'Value': value,
                              'Count': count}
                    writer.writerow(record)

def createWorld(config):
    try:
        random.seed(config.getint('Simulation','seedGen'))
    except ValueError:
        # Non int, so assume None
        random.seed()
    world = World()
    world.diagram = Diagram()
    world.diagram.setColor(None,'deepskyblue')

    regions = {}
    shelters = [int(region) for region in config.get('Shelter','region').split(',')]
    for region in range(config.getint('Regions','regions')):
        capacity = None
        if config.getboolean('Shelter','exists'):
            try:
                index = shelters.index(region+1)
                capacity = int(config.get('Shelter','capacity').split(',')[index])
            except ValueError:
                pass

        n = Region(region+1,world,config,capacity)
        regions[n.name] = {'agent': n, 'inhabitants': [], 'number': region+1}

    world.defineState(WORLD,'day',int,lo=1)
    world.setState(WORLD,'day',1)

    nature = Nature(world,config)

    population = []
    for i in range(config.getint('Actors','population')):
        agent = Actor(i+1,world,config)
        population.append(agent)
        region = agent.getState('region').first()
        regions[region]['inhabitants'].append(agent)

    if config.getboolean('System','system'):
        system = System(world,config)
    else:
        system = None

    groups = []
    if config.getboolean('Groups','region'):
        for region,info in regions.items():
            group = Group(info['agent'].name,world,config)
            group.potentialMembers([a.name for a in info['inhabitants']])
            groups.append(group)
    if config.getboolean('Groups','ethnic'):
        group = Group('EthnicMinority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('ethnicGroup').first() == 'minority'])
        world.diagram.setColor(group.name,'mediumpurple')
        groups.append(group)
        group = Group('EthnicMajority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('ethnicGroup').first() == 'majority'])
        world.diagram.setColor(group.name,'blueviolet')
        groups.append(group)
    if config.getboolean('Groups','religion'):
        group = Group('ReligiousMinority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('religion').first() == 'minority'])
        world.diagram.setColor(group.name,'rosybrown')
        groups.append(group)
        group = Group('ReligiousMajority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('religion').first() == 'majority'])
        world.diagram.setColor(group.name,'darkorange')
        groups.append(group)
    if config.getboolean('Groups','generic'):
        group = Group('',world,config)
        group.potentialMembers([a.name for a in population])
        world.diagram.setColor(group.name,'mediumpurple')
        groups.append(group)

    for agent in population:
        agent._initializeRelations(config)

    order = []
    if groups:
        order.append({g.name for g in groups})
    if population:
        order.append({agent.name for agent in population})
    if system:
        order.append({system.name})
    order.append({'Nature'})

    world.setOrder(order)

    for agent in population:
        agent._initializeBeliefs(config)
        if not config.getboolean('Actors','beliefs'):
            agent.setAttribute('static',True)

    if system and config.getboolean('System','beliefs'):
        system.resetBelief()


    world.dependency.computeEvaluation()
    return world

def getConfig(instance):
    """
    @type instance: int
    """
    # Extract configuration
    config = ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__),'config','%06d.ini' % (instance)))
    return config
    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('-n','--number',default=1,type=int,help='Number of days to run')
    parser.add_argument('-r','--runs',default=1,type=int,help='Number of runs to run')
    parser.add_argument('-i','--instance',default=1,type=int,help='Instance number')
    parser.add_argument('-p','--profile',action='store_true',help='Profile simulation step')
    parser.add_argument('-c','--compile',action='store_true',help='Pre-compile agent policies')
    parser.add_argument('-w','--write',action='store_true',help='Write simulation definition tables')
    
    args = vars(parser.parse_args())
    config = getConfig(args['instance'])
    os.environ['PYTHONHASHSEED'] = config.get('Simulation','seedEnv')
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])

    for run in range(args['runs']):
        # Verify directory structure
        dirName = os.path.join(os.path.dirname(__file__),'Instances',
                               'Instance%d' % (args['instance']),'Runs','run-%d' % (run))
        if not os.path.exists(dirName):
            os.makedirs(dirName)
        logfile = os.path.join(dirName,'psychsim.log')
        try:
            os.stat(dirName)
        except OSError:
            os.makedirs(dirName)
        try:
            os.remove(logfile)
        except OSError:
            pass
        logging.basicConfig(level=level,filename=logfile)

        world = createWorld(config)
        population = [agent for agent in world.agents.values() if isinstance(agent,Actor)]
        regions = {agent.name: {'agent': agent,
                                'inhabitants': [a for a in population if a.home == agent.name]}
                   for agent in world.agents.values() if isinstance(agent,Region)}
        
        if args['write']:
            defDir = os.path.join(os.path.dirname(__file__),'SimulationDefinition')
            if not os.path.exists(defDir):
                os.makedirs(defDir)
            writeDefinition(world,defDir)
        cdfTables = {'InstanceVariable': [],
                     'RunData': [],
                     'SummaryStatisticsData':
                     [(population,'alive','count=False'),
                      (population,'health','count<0.2'),
                      (population,'location','count=evacuated'),
                      ([world.agents[r] for r in regions],'shelterOccupancy','sum'),
                      (population,'health','mean'),
                      (population,'resources','mean'),
                      ([world.agents[r] for r in regions],'risk','invert,mean'),
                      (population,ACTION,'count=decreaseRisk'),
                      (population,ACTION,'count=takeResources'),
                     ],
                     'QualitativeData': [],
                     'RelationshipData': [],
                     'Population': {'Deaths': (population,'alive','count=False'),
                                    'Casualties': (population,'health','count<0.2'),
                                    'Evacuees': (population,'location','count=evacuated'),
                                    'Sheltered': (population,'shelterOccupancy','count=shelter'),
                     },
                     'Regional': {'Deaths': (regions,'alive','count=False'),
                                  'Casualties': (regions,'health','count<0.2'),
                                  'Sheltered': ([world.agents[r] for r in regions],'shelterOccupancy',
                                                None)
                     },
        }
        writeCensus(world,regions,dirName)
        writeHurricane(world,0,dirName)
        toCDF(world,dirName,cdfTables)
        if args['compile']:
            for agent in population:
                agent.compileV()
        try:
            random.seed(config.getint('Simulation','seedRun'))
        except ValueError:
            # Non int, so assume None
            random.seed()
        hurricanes = 0
        oldPhase = world.getState('Nature','phase').first()
        start = time.time()
        while hurricanes < args['number']:
            today = world.getState(WORLD,'day').first()
            logging.info('Day %d' % (today))
            day = today
            updateCDF(world,dirName,cdfTables)
            while day == today:
                print(today,time.time()-start)
                agents = world.next()
                if args['profile']:
                    prof = cProfile.Profile()
                    prof.enable()
                newState = world.step(select=True)
                if args['profile']:
                    prof.disable()
                    buf = StringIO()
                    profile = pstats.Stats(prof, stream=buf)
                    profile.sort_stats('time').print_stats()
                    logging.critical(buf.getvalue())
                    buf.close()
                buf = StringIO()
                world.explainAction(newState,level=1,buf=buf)
                logging.debug('\n'+buf.getvalue())
                buf.close()
                buf = StringIO()
                world.printState(newState,buf)
                logging.debug(buf.getvalue())
                buf.close()
                day = world.getState(WORLD,'day').first()
                phase = world.getState('Nature','phase').first()
                if phase == 'none':
                    if oldPhase == 'active':
                        hurricanes += 1
                        logging.info('Completed Hurricane #%d' % (hurricanes))
                oldPhase = phase
            writeHurricane(world,hurricanes+1,dirName)
        world.save(os.path.join(dirName,'scenario.psy'))
