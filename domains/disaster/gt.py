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

class City:
    def __init__(self,world,config):
        world.defineState(WORLD,'day',int,lo=1)
        world.setState(WORLD,'day',1)
        if config.get('Shelter','neighborhood') != 'none':
            # Shelter
            self.shelter = Agent('shelter')
            world.addAgent(self.shelter)
            self.shelter.setAttribute('static',True)
            
            world.defineState(self.shelter.name,'risk',float)
            self.shelter.setState('risk',config.getfloat('Shelter','risk'))
            world.defineState('shelter','neighborhood',list,neighborhoods.keys())
            self.shelter.setState('neighborhood',config.get('Shelter','neighborhood'))
            world.defineState(self.shelter.name,'allowPets',bool)
            self.shelter.setstate('allowPets',config.getboolean('Shelter','pets'))

class Neighborhood(Agent):
    def __init__(self,name,world):
        Agent.__init__(self,name)
        world.addAgent(self)

        self.setAttribute('static',True)
        
        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,random.random()/2.+0.25)

        security = world.defineState(self.name,'security',float)
        world.setFeature(security,random.random()/2+0.25)

class Nature(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'Nature')
        world.addAgent(self)
        evolution = self.addAction({'verb': 'evolve'})

#        phase = world.defineState(self.name,'phase',int)
#        world.setFeature(phase,3)

#        neighborhoods = [name for name in self.world.agents
#                        if isinstance(self.world.agents[name],Neighborhood)]

        # Phase dynamics
#        tree = makeTree({'if': equalRow(phase,20),
#                         True: setToConstantMatrix(phase,1),
#                         False: incrementMatrix(phase,1)})
#        world.setDynamics(phase,evolution,tree)

        # Effect of disaster on risk
        if config.getboolean('Disaster','dynamic'):
            for neighborhood in neighborhoods:
                risk = stateKey(neighborhood,'risk')
                tree = makeTree({'if': thresholdRow(phase,10),
                                 True: {'if': thresholdRow(phase,15),
                                        True: approachMatrix(risk,.1,0.),
                                        False: approachMatrix(risk,.05,0.)},
                                 False: {'if': thresholdRow(phase,5),
                                         True: approachMatrix(risk,.05,1.),
                                         False: approachMatrix(risk,.1,1.)}})
                world.setDynamics(risk,evolution,tree)
            if config.get('Shelter','neighborhood') != 'none':
                risk = stateKey(keys.WORLD,'shelterRisk')
                tree = makeTree({'if': thresholdRow(phase,10),
                                 True: {'if': thresholdRow(phase,15),
                                        True: approachMatrix(risk,.1,0.),
                                        False: approachMatrix(risk,.05,0.)},
                                 False: {'if': thresholdRow(phase,5),
                                         True: approachMatrix(risk,.05,1.),
                                         False: approachMatrix(risk,.1,1.)}})
                world.setDynamics(risk,evolution,tree)
        self.setAttribute('static',True)

        # Advance calendar after Nature moves
        tree = makeTree(incrementMatrix(stateKey(WORLD,'day'),1))
        world.setDynamics(stateKey(WORLD,'day'),evolution,tree)
        
class System(Agent):
    def __init__(self,world):
        Agent.__init__(self,'System')
        world.addAgent(self)

        world.defineState(self.name,'resources',int,lo=0,hi=100)
        self.setState('resources',int(random.random()*25.)+75)
        
        neighborhoods = [name for name in self.world.agents
                        if isinstance(self.world.agents[name],Neighborhood)]

        for neighborhood in neighborhoods:
            self.addAction({'verb': 'allocate','object': neighborhood})
        
class Group(Agent):
    def __init__(self,name,world):
        Agent.__init__(self,'Group%s' % (name))
        world.addAgent(self)
        actGood = self.addAction({'verb': 'doGood'})
        actBad = self.addAction({'verb': 'doBad'})

    def potentialMembers(self,agents,weights=None):
        assert len(self.models) == 1,'Define potential members before adding multiple models of group %s' % (self.name)
        model = self.models.keys()[0]
        for agent in agents:
            self.world.defineRelation(agent,self.name,'memberOf',bool)
        # Define reward function for this group as weighted sum of members
        if weights is None:
            weights = {a: 1. for a in agents}
        for name,weight in weights.items():
            self.setReward(name,weight,model)
    
class Person(Agent):
    def __init__(self,name,world,config):
        Agent.__init__(self,'Person%s' % (name))
        world.addAgent(self)

        # States

        # Demographic info
        ethnic = world.defineState(self.name,'ethnicGroup',list,['majority','minority'])
        if random.random() > 0.75:
            world.setFeature(ethnic,'minority')
        else:
            world.setFeature(ethnic,'majority')
        gender = world.defineState(self.name,'gender',list,['male','female'])
        if random.random() > 0.5:
            world.setFeature(gender,'male')
        else:
            world.setFeature(gender,'female')
        kids = world.defineState(self.name,'children',float)
        world.setFeature(kids,random.random()/2.+0.25)

        # Psychological
        attachmentStyles = ['secure','insecure']
        attachment = world.defineState(self.name,'attachment',list,attachmentStyles)
        world.setFeature(attachment,random.choice(attachmentStyles))

        neighborhoods = [name for name in self.world.agents
                         if isinstance(self.world.agents[name],Neighborhood)]
        neighborhood = world.defineState(self.name,'neighborhood',list,neighborhoods)
        home = random.choice(neighborhoods)
        world.setFeature(neighborhood,home)

        # For display use only
        x = world.defineState(self.name,'x',float)
        world.setFeature(x,random.random())
        y = world.defineState(self.name,'y',float)
        world.setFeature(y,random.random())

        # Dynamic states
        locationSet = neighborhoods[:]
        locationSet.append('evacuated')
        locationSet.append('shelter')
        location = world.defineState(self.name,'location',list,locationSet)
        world.setFeature(location,home)
        alive = world.defineState(self.name,'alive',bool)
        world.setFeature(alive,True)
        health = world.defineState(self.name,'health',float)
        world.setFeature(health,random.random()/2.+.5)
        wealth = world.defineState(self.name,'wealth',float)
        world.setFeature(wealth,random.random()/2.+0.25)

        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,world.getState(home,'risk').expectation())

        grievance = world.defineState(self.name,'grievance',float)
        world.setFeature(grievance,random.random()/2.)

        # Actions and Dynamics

        nop = self.addAction({'verb': 'doNothing'})
        if config.get('Shelter','neighborhood') != 'none':
            # Go to shelter
            tree = makeTree({'if': equalFeatureRow(location,stateKey(keys.WORLD,
                                                                     'shelterNeighborhood')),
                             True: {'if': trueRow(alive), True: True, False: False},
                             False: False})
            actShelter = self.addAction({'verb':'gotoShelter'},tree.desymbolize(world.symbols))
        if config.getboolean('Actors','evacuation'):
            # Evacuate city altogether
            tree = makeTree({'if': equalRow(location,['Neighborhood00','evacuated']),
                             True: {'if': trueRow(alive),
                                    True: True, False: False}, False: False})
            actEvacuate = self.addAction({'verb': 'evacuate'},tree.desymbolize(world.symbols))
        if config.getboolean('Actors','prosocial'):
            # Prosocial behavior
            tree = makeTree({'if': equalRow(location,['shelter','evacuated']),
                             True: False, False: {'if': trueRow(alive),
                                                  True: True, False: False}})
            actGood = self.addAction({'verb': 'doGood'},tree.desymbolize(world.symbols))
        if config.getboolean('Actors','antisocial'):
            # Antisocial behavior
            tree = makeTree({'if': equalRow(location,['shelter','evacuated']),
                             True: False, False: {'if': trueRow(alive),
                                                  True: True, False: False}})
            actBad = self.addAction({'verb': 'doBad'},tree.desymbolize(world.symbols))
        neighborhoods = [n for n in self.world.agents.values()
                         if isinstance(n,Neighborhood)]
        if config.getboolean('Actors','movement'):
            actMove = {}
            for neighborhood in neighborhoods:
                tree = makeTree({'if': equalRow(location,'evacuated'),
                                 True: False, False: {'if': trueRow(alive),
                                                      True: True, False: False}})
                actMove[neighborhood.name] = self.addAction({'verb': 'moveTo',
                                                            'object': neighborhood.name},
                                                            tree.desymbolize(world.symbols))

        # Effect on location
        if config.get('Shelter','neighborhood') != 'none':
            tree = makeTree(setToConstantMatrix(location,'shelter'))
            world.setDynamics(location,actShelter,tree)
        if config.getboolean('Actors','evacuation'):
            tree = makeTree(setToConstantMatrix(location,'evacuated'))
            world.setDynamics(location,actEvacuate,tree)
        if config.getboolean('Actors','movement'):
            for neighborhood in neighborhoods:
                tree = makeTree(setToConstantMatrix(location,neighborhood.name))
                world.setDynamics(location,actMove[neighborhood.name],tree)

        # Effect on my risk
        tree = {'if': equalRow(makeFuture(location),'evacuated'),
                True: {'if': trueRow(alive),
                       True: approachMatrix(risk,0.9,0.),
                       False: noChangeMatrix(risk)},
                False:  noChangeMatrix(risk)}
        if config.get('Shelter','neighborhood') != 'none':
            tree = {'if': equalRow(makeFuture(location),'shelter'),
                    True: setToFeatureMatrix(risk,stateKey(keys.WORLD,'shelterRisk')),
                    False: tree}
        for neighborhood in neighborhoods:
            tree = {'if': equalRow(makeFuture(location),neighborhood.name),
                    True: setToFeatureMatrix(risk,stateKey(neighborhood.name,'risk')),
                    False: tree}
        world.setDynamics(risk,True,makeTree(tree))
        
        # Effect on my health
        tree = makeTree({'if': trueRow(alive),
                         True: {'if': thresholdRow(makeFuture(risk),0.75),
                                True: {'distribution': [(approachMatrix(health,0.75,0.),0.75),
                                                        (noChangeMatrix(health),0.25)]},
                                False: {'if': thresholdRow(makeFuture(risk),0.5),
                                        True: {'distribution': [(approachMatrix(health,0.8,0.),0.5),
                                                                (noChangeMatrix(health),0.5)]},
                                        False: {'if': thresholdRow(makeFuture(risk),0.25),
                                                True: {'distribution':  [(approachMatrix(health,0.85,0),0.25),
                                                                         (noChangeMatrix(health),0.75)]},
                                                False: noChangeMatrix(health)}}},
                         False: noChangeMatrix(health)})
        world.setDynamics(health,True,tree)

        # Effect on kids' health
        tree = makeTree({'if': thresholdRow(makeFuture(risk),0.75),
                         True: {'distribution': [(approachMatrix(kids,0.6,0.),0.75),
                                                 (noChangeMatrix(kids),0.25)]},
                         False: {'if': thresholdRow(makeFuture(risk),0.5),
                                 True: {'distribution': [(approachMatrix(kids,0.7,0.),0.5),
                                                         (noChangeMatrix(kids),0.5)]},
                                 False: {'if': thresholdRow(makeFuture(risk),0.25),
                                         True: {'distribution':  [(approachMatrix(kids,0.8,0),0.25),
                                                                  (noChangeMatrix(kids),0.75)]},
                                         False: noChangeMatrix(kids)}}})
        world.setDynamics(kids,True,tree)

        # Effect on life
        tree = makeTree({'if': trueRow(alive),
                         True: {'if': thresholdRow(makeFuture(health),0.01),
                                True: setTrueMatrix(alive),
                                False: setFalseMatrix(alive)},
                         False: noChangeMatrix(alive)})
        world.setDynamics(alive,True,tree)
        
        # Effect on wealth
        if config.getboolean('Actors','evacuation'):
            tree = makeTree({'if': thresholdRow(wealth,0.1),
                             True: incrementMatrix(wealth,-0.1),
                             False: setToConstantMatrix(wealth,0.)})
            world.setDynamics(wealth,actEvacuate,tree)

        if config.getboolean('Actors','prosocial'):
            # Effect of doing good
            for neighborhood in neighborhoods:
                key = stateKey(neighborhood.name,'risk')
                tree = makeTree({'if': equalRow(location,neighborhood.name),
                                 True: approachMatrix(key,.1,0.),
                                 False: noChangeMatrix(key)})
                world.setDynamics(key,actGood,tree)
        # Reward
        self.setReward(maximizeFeature(health,self.name),1.)
        self.setReward(maximizeFeature(wealth,self.name),1.)
        self.setReward(maximizeFeature(kids,self.name),1.)
        # Decision-making parameters
        self.setAttribute('horizon',1)
        #self.setAttribute('selection','distribution')
        #self.setAttribute('rationality',1.)

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
            agent = self.agents['Person00']
            for name,variable in self.variables.items():
                if keys.isStateKey(name) and keys.state2agent(name) == 'Person00':
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
        
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('-n','--number',default=1,type=int,help='Number of days to run')
    parser.add_argument('-r','--runs',default=1,type=int,help='Number of runs to run')
    parser.add_argument('-i','--instance',default=1,type=int,help='Instance number')
    args = vars(parser.parse_args())
    # Extract configuration
    config = SafeConfigParser()
    config.read(os.path.join('config','%06d.ini' % (args['instance'])))
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.getLogger().setLevel(level)

    for run in range(args['runs']):
        world = World()
        world.diagram = Diagram()

        city = City(world,config)

        neighborhoods = {}
        for neighborhood in range(config.getint('City','neighborhoods')):
            n = Neighborhood('N%02d' % (neighborhood+1),world)
            neighborhoods[n.name] = {'agent': n, 'inhabitants': []}

        nature = Nature(world,config)

        population = []
        for i in range(config.getint('Actors','population')):
            agent = Person('%02d' % (i+1),world,config)
            population.append(agent)
            neighborhood = agent.getState('neighborhood').first()
            neighborhoods[neighborhood]['inhabitants'].append(agent)

        groups = []
            #    for neighborhood,info in neighborhoods.items():
            #        group = Group('Group%s' % (neighborhood[-2:]),world)
            #        group.potentialMembers([a.name for a in info['inhabitants']])

        if config.get('Actors','altruism') == 'neighbors':
            for agent in population:
                myHome = world.getState(agent.name,'neighborhood').first()
                for other in population:
                    if other.name != agent.name:
                        if world.getState(other.name,'neighborhood').first() == myHome:
                            agent.setReward(maximizeFeature(stateKey(other.name,'health'),agent.name),1.)

        order = [{agent.name for agent in population}]
        order.append({'Nature'})
        world.setOrder(order)

        if config.get('Actors','theory_of_mind') == 'none':
            for agent in population:
                beliefs = agent.resetBelief()
                for other in population:
                    if other.name != agent.name:
                            agent.ignore(other.name,'%s0' % (agent.name))

        allTables = {'Population': {'fields': [('alive','casualties','invert')],
                                    'population': City,
                                    'log': []},
                     'Neighborhood': {'fields': [('alive','casualties','invert')],
                                      'population': Neighborhood,
                                      'log': []},
        }
        tables = {name: allTables[name] for name in allTables
                  if config.getboolean('Data',name.lower())}
        while int(world.getState(WORLD,'day').expectation()) <= args['number']:
            day = int(world.getState(WORLD,'day').expectation())
            oldState = world.state
            newState = world.step(select=True)
            logging.info('Day %d' % (day))
            buf = StringIO()
            world.explainAction(newState,level=1,buf=buf)
            logging.debug(buf.getvalue())
            buf.close()
            newState = world.step(select=True)
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
                    table['log'].append(entry)
                elif table['population'] is Neighborhood:
                    for neighborhood in neighborhoods:
                        inhabitants = neighborhoods[neighborhood]['inhabitants']
                        if inhabitants:
                            entry = {'day': day,
                                     'neighborhood': neighborhood}
                            for feature,label,function in table['fields']:
                                if world.variables[stateKey(population[0].name,feature)]['domain'] is bool:
                                    entry[label] = len([a for a in inhabitants if values[a.name][feature]])
                                if function == 'invert':
                                    entry[label] = len(inhabitants) - entry[label]
                            table['log'].append(entry)
        # Verify directory structure
        dirName = os.path.join('Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (run))
        try:
            os.stat(dirName)
        except OSError:
            os.mkdir(dirName)
        for name,table in tables.items():
            fields = ['day']+[field[1] for field in table['fields']]
            if table['population'] is Neighborhood:
                fields.insert(1,'neighborhood')
            with open(os.path.join(dirName,'%sTable' % (name)),'w') as csvfile:
                writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
                writer.writeheader()
                for entry in table['log']:
                    writer.writerow(entry)

        world.save('scenario.psy')
