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

likert = {5: [0.2,0.4,0.6,0.8],
          7: [0.14,0.28,0.42,0.56,0.70,0.84],
          }

def toLikert(value,scale=5):
    for index in range(len(likert[scale])):
        if value < likert[scale][index]:
            return index+1
    else:
        return scale

class City:
    def __init__(self,world,config):
        world.defineState(WORLD,'day',int,lo=1)
        world.setState(WORLD,'day',1)
        neighborhoods = [name for name in world.agents
                         if isinstance(world.agents[name],Neighborhood)]
        if config.getboolean('Shelter','exists'):
            # Shelter
            self.shelter = Agent('shelter')
            world.addAgent(self.shelter)

            world.diagram.setColor(self.shelter.name,'skyblue')
            
            self.shelter.setAttribute('static',True)
            
            world.defineState(self.shelter.name,'risk',float)
            self.shelter.setState('risk',config.getfloat('Shelter','risk'))
            if config.getboolean('Shelter','local'):
                world.defineState('shelter','neighborhood',list,neighborhoods)
                self.shelter.setState('neighborhood',config.get('Shelter','neighborhood'))
            world.defineState(self.shelter.name,'allowPets',bool)
            self.shelter.setState('allowPets',config.getboolean('Shelter','pets'))

class Neighborhood(Agent):
    def __init__(self,number,world):
        Agent.__init__(self,'N%02d' % (number))
        world.addAgent(self)

        if number == 1:
            world.diagram.setColor(self.name,'mediumseagreen')

        self.setAttribute('static',True)
        
        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,0.1)

        security = world.defineState(self.name,'security',float)
        world.setFeature(security,0.9)

class Nature(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'Nature')
        world.addAgent(self)

        world.diagram.setColor(self.name,'red')

        evolution = self.addAction({'verb': 'evolve'})

        phase = world.defineState(self.name,'phase',list,['none','increasing','decreasing'])
        world.setFeature(phase,'increasing')
        days = world.defineState(self.name,'days',int)
        world.setFeature(days,0)

        # Phase dynamics
        tree = makeTree({'if': thresholdRow(days,10),
                         True: {'if': equalRow(phase,'increasing'),
                                True: {'distribution': [(setToConstantMatrix(phase,'decreasing'),0.2),
                                                        (noChangeMatrix(phase),0.8)]},
                                False: {'if': equalRow(phase,'decreasing'),
                                        True: {'distribution': [(setToConstantMatrix(phase,'none'),0.2),
                                                                (noChangeMatrix(phase),0.8)]},
                                        False: {'distribution': [(setToConstantMatrix(phase,'increasing'),0.2),
                                                                 (noChangeMatrix(phase),0.8)]}}},
                         False: noChangeMatrix(phase)})
        world.setDynamics(phase,evolution,tree)
        tree = makeTree(noChangeMatrix(days))
        world.setDynamics(days,evolution,tree)
        tree = makeTree({'if': equalFeatureRow(phase,makeFuture(phase)),
                         True: incrementMatrix(days,1),
                         False: setToConstantMatrix(days,0)})
        world.setDynamics(days,True,tree)

        # Effect of disaster on risk
        neighborhoods = sorted([name for name in self.world.agents
                                if isinstance(self.world.agents[name],Neighborhood)])
        if config.getboolean('Disaster','dynamic'):
            for neighborhood in neighborhoods:
                risk = stateKey(neighborhood,'risk')
                tree = makeTree({'if': equalRow(phase,'increasing'),
                                 True: approachMatrix(risk,.1,1.),
                                 False: {'if': equalRow(phase,'decreasing'),
                                         True: approachMatrix(risk,.1,0.),
                                         False: setToConstantMatrix(risk,0.)}})
                world.setDynamics(risk,evolution,tree)
            if config.getboolean('Shelter','exists'):
                risk = stateKey('shelter','risk')
                tree = makeTree({'if': equalRow(phase,'increasing'),
                                 True: approachMatrix(risk,.01,1.),
                                 False: {'if': equalRow(phase,'decreasing'),
                                         True: approachMatrix(risk,.01,0.),
                                         False: setToConstantMatrix(risk,0.)}})
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
    def __init__(self,name,world,config):
        Agent.__init__(self,'Group%s' % (name))
        world.addAgent(self)

        if name == 'N01':
            world.diagram.setColor(self.name,'yellowgreen')
            
        self.setAttribute('static',True)

        size = world.defineState(self.name,'size',int)
        self.setState('size',0)
        
        if config.getboolean('Groups','prosocial') and name in world.agents:
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            actGood = self.addAction({'verb': 'doGood','object': name},
                                     tree.desymbolize(world.symbols))
        if config.getboolean('Groups','antisocial') and name in world.agents:
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            actBad = self.addAction({'verb': 'doBad','object': name},
                                     tree.desymbolize(world.symbols))
        doNothing = self.addAction({'verb': 'doNothing'})

    def potentialMembers(self,agents,weights=None):
        assert len(self.models) == 1,'Define potential members before adding multiple models of group %s' % (self.name)
        model = self.models.keys()[0]
        size = stateKey(self.name,'size')
        for name in agents:
            agent = self.world.agents[name]
            member = self.world.defineRelation(name,self.name,'memberOf',bool)
            # Join a group
            self.world.setFeature(member,False)
            tree = makeTree({'if': trueRow(stateKey(name,'alive')),
                             True: {'if': trueRow(member),
                                    True: False, False: True},
                             False: False})
            join = agent.addAction({'verb': 'join','object': self.name},
                                   tree.desymbolize(self.world.symbols))
            tree = makeTree(setTrueMatrix(member))
            world.setDynamics(member,join,tree)
            tree = makeTree(incrementMatrix(size,1))
            world.setDynamics(size,join,tree)
            # Leave a group
            self.world.setFeature(member,False)
            tree = makeTree({'if': trueRow(stateKey(name,'alive')),
                             True: {'if': trueRow(member),
                                    True: True, False: False},
                             False: False})
            leave = agent.addAction({'verb': 'leave','object': self.name},
                                    tree.desymbolize(self.world.symbols))
            tree = makeTree(setFalseMatrix(member))
            world.setDynamics(member,leave,tree)
            tree = makeTree(incrementMatrix(size,-1))
            world.setDynamics(size,leave,tree)
        # Define reward function for this group as weighted sum of members
        if weights is None:
            weights = {a: 1. for a in agents}
        for name,weight in weights.items():
            self.setReward(name,weight,model)
    
class Actor(Agent):
    def __init__(self,number,world,config):
        Agent.__init__(self,'Actor%04d' % (number))
        world.addAgent(self)

        if number == 1:
            world.diagram.setColor(self.name,'gold')
        elif number == 2:
            world.diagram.setColor(self.name,'yellow')

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
        age = world.defineState(self.name,'age',int)
        world.setFeature(age,int(random.random()*50.)+20)
        if config.getboolean('Actors','children'):
            kids = world.defineState(self.name,'children',int,lo=0,hi=2)
            world.setFeature(kids,int(random.random()*3.))

        # Psychological
        attachmentStyles = ['secure','anxious','avoidant']
        attachment = world.defineState(self.name,'attachment',list,attachmentStyles)
        world.setFeature(attachment,random.choice(attachmentStyles))

        neighborhoods = sorted([name for name in self.world.agents
                                if isinstance(self.world.agents[name],Neighborhood)])
        neighborhood = world.defineState(self.name,'neighborhood',list,neighborhoods)
        home = neighborhoods[(number-1)/config.getint('City','density')]
        world.setFeature(neighborhood,home)

        # For display use only
#        x = world.defineState(self.name,'x',float)
#        world.setFeature(x,random.random())
#        y = world.defineState(self.name,'y',float)
#        world.setFeature(y,random.random())

        # Dynamic states
        locationSet = neighborhoods[:]
        locationSet.append('evacuated')
        if config.getboolean('Shelter','exists'):
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
        if config.getboolean('Shelter','exists'):
            # Go to shelter
            tree = {'if': trueRow(alive),
                    True: {'if': equalRow(location,'shelter'),
                           True: False, False: True}, False: False}
            if config.getboolean('Actors','evacuation'):
                tree = {'if': equalRow(location,'evacuated'),
                        True: False, False: tree}
            if config.getboolean('Shelter','local'):
                tree = {'if': equalFeatureRow(location,stateKey('shelter','neighborhood')),
                        True: tree, False: False}
            tree = makeTree(tree)
            actShelter = self.addAction({'verb':'moveTo','object': 'shelter'},
                                        tree.desymbolize(world.symbols))
        if config.getboolean('Actors','evacuation'):
            # Evacuate city altogether
            tree = makeTree({'if': equalRow(location,[neighborhoods[0],'evacuated']),
                             True: {'if': trueRow(alive),
                                    True: True, False: False}, False: False})
            actEvacuate = self.addAction({'verb': 'evacuate'},tree.desymbolize(world.symbols))
        if config.getboolean('Actors','prosocial'):
            # Prosocial behavior
            actGood = {}
            for neighborhood in neighborhoods:
                if config.getboolean('Actors','movement') or neighborhood == home:
                    tree = makeTree({'if': equalRow(location,neighborhood),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actGood[neighborhood] = self.addAction({'verb': 'doGood','object': neighborhood},
                                                           tree.desymbolize(world.symbols))
        if config.getboolean('Actors','antisocial'):
            # Antisocial behavior
            actBad = {}
            for neighborhood in neighborhoods:
                if config.getboolean('Actors','movement') or neighborhood == home:
                    tree = makeTree({'if': equalRow(location,neighborhood),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actBad[neighborhood] = self.addAction({'verb': 'doBad','object': neighborhood},
                                                          tree.desymbolize(world.symbols))
        neighborhoods = [n for n in self.world.agents.values()
                         if isinstance(n,Neighborhood)]
        if config.getboolean('Actors','movement'):
            actMove = {}
            for neighborhood in neighborhoods:
                cell = int(neighborhood.name[-2:])
                row = (cell-1) / 5
                col = (cell-1) % 5
                neighbors = []
                if row > 0:
                    neighbors.append('N%02d' % ((row-1)*5+col+1))
                if row < len(neighborhoods)/5-1:
                    neighbors.append('N%02d' % ((row+1)*5+col+1))
                if col > 0:
                    neighbors.append('N%02d' % (cell-1))
                if col < 4:
                    neighbors.append('N%02d' % (cell+1))
                tree = makeTree({'if': equalRow(location,neighbors),
                                 True: {'if': trueRow(alive),
                                        True: True, False: False}, False: False})
                actMove[neighborhood.name] = self.addAction({'verb': 'moveTo',
                                                            'object': neighborhood.name},
                                                            tree.desymbolize(world.symbols))

        # Effect on location
        if config.getboolean('Shelter','exists'):
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
        if config.getboolean('Actors','movement'):
            tree = noChangeMatrix(risk)
        else:
            tree = setToFeatureMatrix(risk,stateKey(home,'risk'))
        if config.getboolean('Actors','evacuation'):
            tree = {'if': equalRow(makeFuture(location),'evacuated'),
                    True: approachMatrix(risk,0.9,0.),
                    False:  tree}
        if config.getboolean('Shelter','exists'):
            tree = {'if': equalRow(makeFuture(location),'shelter'),
                    True: setToFeatureMatrix(risk,stateKey('shelter','risk')),
                    False: tree}
        if config.getboolean('Actors','movement'):
            for neighborhood in neighborhoods:
                tree = {'if': equalRow(makeFuture(location),neighborhood.name),
                        True: setToFeatureMatrix(risk,stateKey(neighborhood.name,'risk')),
                        False: tree}
        tree = {'if': trueRow(alive),True: tree, False: setToConstantMatrix(risk,0.)}
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
                         False: setToConstantMatrix(health,0.)})
        world.setDynamics(health,True,tree)

        if config.getboolean('Actors','children'):
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
            benefit = config.getfloat('Actors','prosocial_benefit')
            for neighborhood,action in actGood.items():
                key = stateKey(neighborhood,'risk')
                tree = makeTree(approachMatrix(key,benefit,0.))
                world.setDynamics(key,action,tree)
            proRisk = config.getfloat('Actors','prosocial_risk')
            if proRisk > 0.:
                for neighborhood,action in actGood.items():
                    tree = makeTree(approachMatrix(risk,proRisk,1.))
                    world.setDynamics(risk,action,tree)
                
        # Reward
        self.setReward(maximizeFeature(health,self.name),1.)
        self.setReward(maximizeFeature(wealth,self.name),1.)
        if config.getboolean('Actors','children'):
            self.setReward(maximizeFeature(kids,self.name),1.)
        # Decision-making parameters
        self.setAttribute('horizon',config.getint('Actors','horizon'))
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
        
def addState2tables(world,day,tables,population,neighborhoods):
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
                        elif feature == 'risk':
                            value = world.getState(neighborhood,feature)
                            assert len(value)
                            entry[label] = value.first()
                        else:
                            value = [values[a.name][feature] for a in inhabitants]
                            entry[label] = sum(value)/float(len(value))
                        if function == 'invert':
                            entry[label] = len(inhabitants) - entry[label]
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
                        else:
                            entry[label] = values[actor.name][feature]
                table['log'].append(entry)
    
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
        world.diagram.setColor(None,'deepskyblue')

        neighborhoods = {}
        for neighborhood in range(config.getint('City','neighborhoods')):
            n = Neighborhood(neighborhood+1,world)
            neighborhoods[n.name] = {'agent': n, 'inhabitants': [], 'number': neighborhood+1}

        city = City(world,config)

        nature = Nature(world,config)

        population = []
        for i in range(config.getint('Actors','population')):
            agent = Actor(i+1,world,config)
            population.append(agent)
            neighborhood = agent.getState('neighborhood').first()
            neighborhoods[neighborhood]['inhabitants'].append(agent)

        groups = []
        if config.getboolean('Groups','neighborhood'):
            for neighborhood,info in neighborhoods.items():
                group = Group(info['agent'].name,world,config)
                group.potentialMembers([a.name for a in info['inhabitants']])
                groups.append(group)

        neighbors = {}
        friends = {}
        for agent in population:
            myHome = world.getState(agent.name,'neighborhood').first()
            neighbors[agent.name] = {a.name for a in population if a.name != agent.name and \
                                     world.getState(a.name,'neighborhood').first() == myHome}

            # Social network
            friends[agent.name] = set()
            for other in population:
                if other.name != agent.name:
                    friendship = world.defineRelation(agent.name,other.name,'friendOf',bool)
                    world.setFeature(friendship,False)
        friendCount = {agent.name: 0 for agent in population}
        friendMax = config.getint('Actors','friends')
        while friendCount:
            friend1 = random.choice(friendCount.keys())
            friend2 = random.choice(list(set(friendCount.keys())-{friend1}))
            world.setFeature(binaryKey(friend1,friend2,'friendOf'),True)
            if friendCount[friend1] == friendMax - 1:
                del friendCount[friend1]
            else:
                friendCount[friend1] += 1
            world.setFeature(binaryKey(friend2,friend1,'friendOf'),True)
            if friendCount[friend2] == friendMax - 1:
                del friendCount[friend2]
            else:
                friendCount[friend2] += 1

        if config.get('Actors','altruism') == 'neighbors':
            for agent in population:
                for other in neighbors[agent.name]:
                    agent.setReward(maximizeFeature(stateKey(other,'health'),agent.name),1.)

        order = [{agent.name for agent in population}]
        order.append({'Nature'})
        world.setOrder(order)

        for agent in population:
            beliefs = agent.resetBelief()
            for other in population:
                if other.name != agent.name:
                    if config.get('Actors','altruism') == 'neighbors' and \
                       other.name in neighbors[agent.name]:
                        # I care about my neighbors, so I can't ignore them
                        continue
                    agent.ignore(other.name,'%s0' % (agent.name))

        world.dependency.computeEvaluation()

#        for agent in population:
#            agent.compileV(state=world.state)
#            sys.exit(0)

        allTables = {'Population': {'fields': [('alive','casualties','invert')],
                                    'population': City,
                                    'log': []},
                     'Neighborhood': {'fields': [('alive','casualties','invert'),
                                                 ('risk','risk','likert')],
                                      'population': Neighborhood,
                                      'log': []},
                     'Actors': {'fields': [('neighborhood','neighborhood',None),
                                           ('alive','alive',None),
                                           ('risk','risk','likert'),
                                           ('health','health','likert'),
                                           ('grievance','grievance','likert'),
                                           ('location','shelter','=shelter'),
                                           ('location','evacuated','=evacuated'),
                     ],
                                'population': Actor,
                                'log': []},
        }
        tables = {name: allTables[name] for name in allTables
                  if config.getboolean('Data',name.lower())}
        addState2tables(world,0,tables,population,neighborhoods)
        while int(world.getState(WORLD,'day').expectation()) <= args['number']:
            day = int(world.getState(WORLD,'day').expectation())
            logging.info('Day %d' % (day))
            # People's turn
            newState = world.step(select=True)
            buf = StringIO()
            world.explainAction(newState,level=1,buf=buf)
            logging.info('\n'+buf.getvalue())
            buf.close()
            buf = StringIO()
            world.printState(newState,buf)
            logging.debug(buf.getvalue())
            buf.close()
            addState2tables(world,day,tables,population,neighborhoods)
            # Nature's turn
            newState = world.step(select=True)
            buf = StringIO()
            world.printState(newState,buf)
            logging.debug(buf.getvalue())
            buf.close()
                                    
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
            elif table['population'] is Actor:
                fields.insert(1,'participant')
            with open(os.path.join(dirName,'%sTable' % (name)),'w') as csvfile:
                writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
                writer.writeheader()
                for entry in table['log']:
                    writer.writerow(entry)

    world.save('scenario.psy')
