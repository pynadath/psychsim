from argparse import ArgumentParser
from ConfigParser import SafeConfigParser
from cStringIO import StringIO
import csv
import logging
import os
import os.path
import random
import sys

import psychsim.probability
from psychsim.keys import *
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

class City:
    def __init__(self,world,config):
        world.defineState(WORLD,'day',int,lo=1)
        world.setState(WORLD,'day',1)

        regions = [name for name in world.agents
                         if isinstance(world.agents[name],Region)]

        
class GroundTruth(World):
    def toCDF(self,dirname):
        os.mkdir(dirname)
        os.chdir(dirname)
        os.mkdir('SimulationDefinition')
        os.chdir('SimulationDefinition')

        with open('ActorVariableDefTable.txt','w') as csvfile:
            fields = ['Name','LongName','Values','Observable','Type','Notes']
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',
                                    extrasaction='ignore')
    #        writer.writeheader()
            agent = self.agents['Actor00']
            for name,variable in self.variables.items():
                if keys.isStateKey(name) and keys.state2agent(name) == 'Actor00':
                    if not keys.isTurnKey(name) and not keys.isActionKey(name):
                        feature = keys.state2feature(name)
                        record = {'Name': feature,
                                  'Notes': variable['description'],
                                  'Observable': 1,
                                  }
                        if variable['domain'] is bool:
                            record['Values'] = 'True,False'
                        elif variable['domain'] is list:
                            record['Values'] = ','.join(variable['elements'])
                        elif variable['domain'] is float:
                            record['Values'] = '%4.2f-%4.2f' % (variable['lo'],variable['hi'])
                        else:
                            raise TypeError,'Unable to write values for variables of type %s' \
                                % (variable['domain'])
                        if name in self.dynamics:
                            record['Type'] = 'dynamic'
                        else:
                            record['Type'] = 'fixed'
                        writer.writerow(record)
            for tree,weight in agent.models['%s0' % (agent.name)]['R'].items():
                assert tree.isLeaf(),'Unable to write nonlinear reward components to CDF'
                vector = tree.children[None]
                assert len(vector) == 1,'Unable to write combined reward componetns to CDF'
                feature = keys.state2feature(vector.keys()[0])
                record = {'Name': 'R(%s)' % (feature),
                          'LongName': 'Reward from %s' % (feature),
                          'Values': '-1.0-1.0',
                          'Observable': 0,
                          'Type': 'fixed',
                          }
                writer.writerow(record)
        with open('GroupVariableDefTable.txt','w') as csvfile:
            pass
        with open('SystemVariableDefTable.txt','w') as csvfile:
            pass
        os.mkdir('Instances')
        os.chdir('Instances')
        for instance in range(1):
            os.mkdir('Instance%d' % (instance+1))
            os.chdir('Instance%d' % (instance+1))
            with open('InstanceParameterTable.txt','w') as csvfile:
                pass
            os.mkdir('Runs')
            os.chdir('Runs')
            for run in range(1):
                os.mkdir('run-%d' % (run))
                os.chdir('run-%d' % (run))
                with open('RunDataTable.txt','w') as csvfile:
                    fields = ['Timestep','VariableName','EntityIdx','Name','Value']
                    writer = csv.DictWriter(csvfile,fields,delimiter='\t',
                                            extrasaction='ignore')
                    for name,variable in self.variables.items():
                        if keys.isStateKey(name):
                            if not keys.isTurnKey(name) and not keys.isActionKey(name):
                                value = self.getFeature(name)
                                assert len(value) == 1,'Unable to write uncertain values to CDF'
                                value = value.domain()[0]
                                record = {'Timestep': 0,
                                          'VariableName': name,
                                          'EntityIdx': keys.state2agent(name),
                                          'Name': keys.state2feature(name),
                                          'Value': value}
                                writer.writerow(record)
                os.chdir('..')
            os.chdir('..')
            os.chdir('..')
        
def addState2tables(world,day,tables,population,regions):
    # Grab all of the relevant fields, but only once
    values = {agent.name: {} for agent in population}
    for agent in population:
        for table in tables.values():
            for feature,label,function in table['fields']:
                if not feature in values[agent.name]:
                    value = world.getState(agent.name,feature)
                    assert len(value) == 1
                    values[agent.name][feature] = value.first()
    # Create tables
    for table in tables.values():
        if table['population'] is City:
            entry = {'day': day}
            for feature,label,function in table['fields']:
                if world.variables[stateKey(population[0].name,feature)]['domain'] is bool:
                    entry[label] = len([a for a in population if values[a.name][feature]])
                if function == 'invert':
                    entry[label] = len(population) - entry[label]
                elif function and function[0] == '#':
                    entry[label] = len([a for a in population if values[a.name][feature] == function[1:]])
            table['log'].append(entry)
        elif table['population'] is Region:
            for region in sorted(regions):
                inhabitants = regions[region]['inhabitants']
                entry = {'day': day,
                         'region': region}
                for feature,label,function in table['fields']:
                    if world.variables[stateKey(population[0].name,feature)]['domain'] is bool:
                        entry[label] = len([a for a in inhabitants if values[a.name][feature]])
                        hi = len(inhabitants)
                    elif function and function[0] == '#':
                        target = function[1:]
                        entry[label] = len([a for a in inhabitants if values[a.name][feature][:len(target)] == target])
                        hi = len(inhabitants)
                    elif function and function[0] == '%':
                        target = function[1:]
                        count = len([a for a in inhabitants if values[a.name][feature][:len(target)] == target])
                        try:
                            entry[label] = float(count)/float(len(inhabitants))
                        except ZeroDivisionError:
                            pass
                        hi = 1.
                    elif function and function[0] == '/':
                        value = [values[a.name][feature] for a in inhabitants]
                        entry[label] = sum(value)/float(len(value))
                        hi = 1.
                    else:
                        value = world.getState(region,feature)
                        assert len(value) == 1
                        entry[label] = value.first()
                        hi = 1.
                    if function == 'invert':
                        entry[label] = hi - entry[label]
                    elif function == 'likert':
                        entry[label] = toLikert(entry[label])
                table['log'].append(entry)
        elif table['population'] is Actor:
            for actor in population:
                belief = actor.getBelief().values()[0]
                entry = {'day': day,'participant': actor.name[-4:]}
                for feature,label,function in table['fields']:
                    key = stateKey(actor.name,feature)
                    if world.variables[key]['domain'] is bool:
                        if function == 'invert':
                            entry[label] = not values[actor.name][feature]
                        else:
                            entry[label] = values[actor.name][feature]
                    else:
                        if function == 'likert':
                            entry[label] = toLikert(values[actor.name][feature])
                        elif function and function[0] == '=':
                            entry[label] = values[actor.name][feature] == function[1:]
                        elif function == 'invert':
                            entry[label] = 1.-values[actor.name][feature]
                        else:
                            entry[label] = values[actor.name][feature]
                table['log'].append(entry)
    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('-n','--number',default=1,type=int,help='Number of days to run')
    parser.add_argument('-r','--runs',default=1,type=int,help='Number of runs to run')
    parser.add_argument('-i','--instance',default=1,type=int,help='Instance number')
    args = vars(parser.parse_args())
    # Extract configuration
    config = SafeConfigParser()
    config.read(os.path.join('config','%06d.ini' % (args['instance'])))
    try:
        random.seed(config.getint('Simulation','seed'))
    except ValueError:
        # Non int, so assume None
        random.seed()
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])

    for run in range(args['runs']):
        # Verify directory structure
        dirName = os.path.join('Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (run))
        logfile = os.path.join(dirName,'psychsim.log')
        try:
            os.stat(dirName)
            os.remove(logfile)
        except OSError:
            os.mkdir(dirName)
        logging.basicConfig(level=level,filename=logfile)
        world = World()
        world.diagram = Diagram()
        world.diagram.setColor(None,'deepskyblue')

        regions = {}
        for region in range(config.getint('Regions','regions')):
            capacity = 0
            if config.getboolean('Shelter','exists'):
                try:
                    index = config.get('Shelter','region').split(',').index(str(region+1))
                    capacity = int(config.get('Shelter','capacity').split(',')[index])
                except ValueError:
                    pass
            
            n = Region(region+1,world,config,capacity)
            regions[n.name] = {'agent': n, 'inhabitants': [], 'number': region+1}

        city = City(world,config)
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

        if system:
            if config.getboolean('Actors','beliefs'):
                system.resetBelief()
            else:
                system.setAttribute('static',True)
                
        world.dependency.computeEvaluation()

        #        for agent in population:
        #            agent.compileV(state=world.state)
        #            sys.exit(0)
        if population:
            allTables = {'Population': {'fields': [('alive','casualties','invert'),
                                                   ('location','evacuated','#evacuated'),
                                                   ('location','shelter','#shelter')],
                                        'population': City,
                                        'series': True,
                                        'log': []},
                         'Region': {'fields': [('alive','casualties','invert'),
                                               ('location','evacuated','#evacuated'),
                                               ('location','shelter','#shelter'),
                                               ('risk','safety','invert')],
                                    'population': Region,
                                    'series': True,
                                    'log': []},
                         'Actors': {'fields': [('gender','gender',None),
                                               ('age','age',None),
                                               ('ethnicGroup','ethnicity',None),
                                               ('children','#children',None),
                                               ('region','region',None),
                                               ('alive','alive',None),
                                               ('location','shelter','=shelter'),
                                               ('location','evacuated','=evacuated'),
                                               ('risk','risk','likert'),
                                               ('health','health','likert'),
                                               ('grievance','grievance','likert'),
                         ],
                                    'population': Actor,
                                    'series': True,
                                    'log': []},
                         'Census': {'fields': [('ethnicGroup','ethnicMajority','%majority'),
                                               ('religion','religiousMajority','%majority')],
                                    'population': Region,
                                    'series': False,
                                    'log': []},
                         'Display': {'fields': [('x','x',None),
                                                ('y','y',None)],
                                     'population': Actor,
                                     'series': False,
                                     'log': []}
            }
            tables = {name: allTables[name] for name in allTables
                      if config.getboolean('Data',name.lower())}
            addState2tables(world,0,tables,population,regions)
            hurricanes = 0
            oldPhase = world.getState('Nature','phase').first()
            while hurricanes < args['number']:
                today = int(world.getState(WORLD,'day').expectation())
                logging.info('Day %d' % (today))
                day = today
                while day == today:
                    agents = world.next()
                    print ','.join(sorted(agents))
                    newState = world.step(select=True)
                    buf = StringIO()
                    world.explainAction(newState,level=1,buf=buf)
                    logging.debug('\n'+buf.getvalue())
                    buf.close()
                    buf = StringIO()
                    world.printState(newState,buf)
                    logging.debug(buf.getvalue())
                    buf.close()
                    day = int(world.getState(WORLD,'day').expectation())
                    phase = world.getState('Nature','phase').first()
                    if phase == 'none':
                        if oldPhase == 'active':
                            hurricanes += 1
                            logging.info('Completed Hurricane #%d' % (hurricanes))
                    if config.getboolean('Actors','beliefs'):
                        for actor in population:
                            model = world.getModel(actor.name)
                            assert len(model) == 1
                            belief = actor.getBelief(world.state,model.first())
                            if len(belief) > 1:
                                world.printState(belief)
                            assert len(belief) == 1
                            for omega in actor.omega:
                                true = actor.getState(omega)
                                believed = actor.getState(omega,belief)
                                print actor.name,omega,believed
                    oldPhase = phase
                addState2tables(world,today,{name: table for name,table in tables.items()
                                             if table['series']},population,regions)

            for name,table in tables.items():
                fields = ['day']+[field[1] for field in table['fields']]
                if table['population'] is Region:
                    fields.insert(1,'region')
                elif table['population'] is Actor:
                    fields.insert(1,'participant')
                with open(os.path.join(dirName,'%sTable' % (name)),'w') as csvfile:
                    writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
                    writer.writeheader()
                    for entry in table['log']:
                        writer.writerow(entry)
    world.save('scenario.psy')
