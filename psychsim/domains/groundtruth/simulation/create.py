import csv
import os
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.world import World
try:
    from psychsim.ui.diagram import Diagram
    __ui__ = True
except:
    __ui__ = False

from psychsim.domains.groundtruth.simulation.region import Region
from psychsim.domains.groundtruth.simulation.nature import Nature
from psychsim.domains.groundtruth.simulation.actor import Actor
from psychsim.domains.groundtruth.simulation.system import System
from psychsim.domains.groundtruth.simulation.group import Group
    
if (sys.version_info > (3, 0)):
    from configparser import ConfigParser
else:
    from ConfigParser import SafeConfigParser as ConfigParser

def createWorld(config):
    random.seed(config.getint('Simulation','seedGen'))
    world = World()
#    world.history = {}
    if __ui__:
        world.diagram = Diagram()
        world.diagram.setColor(None,'deepskyblue')

    regions = {}
    shelters = [int(region) for region in config.get('Shelter','region').split(',')]
    for region in range(config.getint('Regions','regions')):
        index = None
        if config.getboolean('Shelter','exists'):
            try:
                index = shelters.index(region+1)
            except ValueError:
                pass

        n = Region(region+1,world,config,index)
        regions[n.name] = {'agent': n, 'inhabitants': [], 'number': region+1}

    if not config.getboolean('Simulation','graph',fallback=False):
        world.defineState(WORLD,'day',int,lo=1,codePtr=True)
        world.setState(WORLD,'day',1)

    nature = Nature(world,config)

    population = []
    for i in range(config.getint('Actors','population')):
        agent = Actor(i+1,world,config)
        agent.epsilon = config.getfloat('Actors','likelihood_threshold')
        population.append(agent)
        region = agent.demographics['home']
        regions[region]['inhabitants'].append(agent)

    for region,entry in regions.items():
        entry['agent'].setInhabitants(regions[region]['inhabitants'])

    if config.getboolean('System','system'):
        system = System(world,config)
    else:
        system = None

    groups = []
    if config.getboolean('Groups','region'):
        for region,info in regions.items():
            if len(info['inhabitants']) > 1:
                group = Group(info['agent'].name,world,config)
                group.potentialMembers([a.name for a in info['inhabitants']],
                                       membership=config.getint('Groups','region_membership'))
                groups.append(group)
    if config.getboolean('Groups','ethnic'):
        group = Group('EthnicMinority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('ethnicGroup').first() == 'minority'])
        if world.diagram:
            world.diagram.setColor(group.name,'mediumpurple')
        groups.append(group)
        group = Group('EthnicMajority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('ethnicGroup').first() == 'majority'])
        if world.diagram:
            world.diagram.setColor(group.name,'blueviolet')
        groups.append(group)
    if config.getboolean('Groups','religion'):
        group = Group('ReligiousMinority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('religion').first() == 'minority'])
        if world.diagram:
            world.diagram.setColor(group.name,'rosybrown')
        groups.append(group)
        group = Group('ReligiousMajority',world,config)
        group.potentialMembers([a.name for a in population \
                                if a.getState('religion').first() == 'majority'])
        if world.diagram:
            world.diagram.setColor(group.name,'darkorange')
        groups.append(group)
    if config.getboolean('Groups','generic'):
        group = Group('',world,config)
        group.potentialMembers([a.name for a in population])
        if world.diagram:
            world.diagram.setColor(group.name,'mediumpurple')
        groups.append(group)

        
    toInit = [agent.name for agent in population]
    random.shuffle(toInit)
    for name in toInit:
        world.agents[name]._initializeRelations(config)

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
    config.read(os.path.join(os.path.dirname(__file__),'..','config','%06d.ini' % (instance)))
    return config

def loadPickle(instance,run=0,day=None,sub=None):
    """
    Loads a PsychSim simulation object from the specified instance/run that has executed until the specified day and then been saved to a file
    """
    if day is None:
        dayStr = ''
    else:
        dayStr = '%d' % (day)
    fname = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                           'Runs','run-%d' % (run))
    if sub:
        fname = os.path.join(fname,sub)
    fname = os.path.join(fname,'scenario%s.pkl' % (dayStr))
    with open(fname,'rb') as f:
        world = pickle.load(f)
    return world
    
def loadHurricanes(instance,run):
    hurricanes = []
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'HurricaneTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            hurricane = int(row['Name'])
            if len(hurricanes) < hurricane:
                hurricanes.append({'Hurricane': hurricane,
                                   'Predicted Location': row['Location'],
                                   'Media Coverage': 'yes',
                                   'Actual Track': [],
                                   'Official Announcements': 'none',
                                   'Start': int(row['Timestep']),
                                   })
            elif row['Landed'] == 'yes':
                if 'Landfall' not in hurricanes[-1]:
                    hurricanes[-1]['Landfall'] = int(row['Timestep'])
                if row['Location'] == 'leaving':
                    hurricanes[-1]['End'] = int(row['Timestep'])
                else:
                    if not 'Actual Severity' in hurricanes[-1]:
                        hurricanes[-1]['Actual Severity'] = row['Category']
                    if len(hurricanes[-1]['Actual Track']) == 0 or \
                       hurricanes[-1]['Actual Track'][-1] != row['Location']:
                        hurricanes[-1]['Actual Track'].append(row['Location'])
    if 'End' not in hurricanes[-1]:
        # Incomplete hurricane (probably just showed up on the last day)
        hurricanes.pop()
    return hurricanes
    
def loadRunData(instance,run):
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RunDataTable.tsv')
    data = {}
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if not row['EntityIdx'] in data:
                data[row['EntityIdx']] = [{}]
            t = int(row['Timestep'])
            if len(data[row['EntityIdx']]) < t:
                data[row['EntityIdx']].append({})
            data[row['EntityIdx']][t-1][row['VariableName']] = {'Value': row['Value'],
                                                                'Notes': row['Notes']}
    return data
    
