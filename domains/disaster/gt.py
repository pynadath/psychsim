from argparse import ArgumentParser
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

class Neighborhood(Agent):
    def __init__(self,name,world):
        Agent.__init__(self,name)
        world.addAgent(self)

        self.setAttribute('static',True)
        
        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,random.random()/2.+0.25)

        security = world.defineState(self.name,'security',float)
        world.setFeature(security,random.random()/2+0.25)

class System(Agent):
    def __init__(self,world):
        Agent.__init__(self,'System')
        world.addAgent(self)
        
class Group(Agent):
    def __init__(self,name,world):
        Agent.__init__(self,'Group%s' % (name))
        world.addAgent(self)

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
    def __init__(self,name,world):
        Agent.__init__(self,'Person%s' % (name))
        world.addAgent(self)

        # States

        # Demographic info
        ethnic = world.defineState(self.name,'ethnicGroup',list,['majority','minority'])
        if random.random() > 0.75:
            world.setFeature(ethnic,'minority')
        else:
            world.setFeature(ethnic,'majority')
        wealthy = world.defineState(self.name,'wealthy',float)
        world.setFeature(wealthy,random.random()/2.+0.25)
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
        location = world.defineState(self.name,'location',list,neighborhoods+
                                     ['shelter','gone'])
        world.setFeature(location,home)
        health = world.defineState(self.name,'health',float)
        world.setFeature(health,random.random()/2.+.5)
        resources = world.defineState(self.name,'resources',float)
        world.setFeature(resources,random.random()/2.+0.25)

        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,world.getState(home,'risk').expectation())

        grievance = world.defineState(self.name,'grievance',bool)
        world.setFeature(grievance,random.random()>0.85)

        # Actions and Dynamics

        actHome = self.addAction({'verb':'goHome'})
        actShelter = self.addAction({'verb':'gotoShelter'})
        actEvacuate = self.addAction({'verb': 'evacuate'})
        actGood = self.addAction({'verb': 'doGood'})
        actBad = self.addAction({'verb': 'doBad'})
        actMove = {}
        neighborhoods = [n for n in self.world.agents.values()
                         if isinstance(neighborhood,Neighborhood)]
        for neighborhood in neighborhoods:
            actMove[neighborhood] = self.addAction({'verb': 'moveTo','object': neighborhood.name})

        # Effect on location
        tree = makeTree(setToConstantMatrix(location,home))
        world.setDynamics(location,actHome,tree)
        tree = makeTree(setToConstantMatrix(location,'shelter'))
        world.setDynamics(location,actShelter,tree)
        tree = makeTree(setToConstantMatrix(location,'gone'))
        world.setDynamics(location,actEvacuate,tree)
        tree = makeTree(noChangeMatrix(location))
        world.setDynamics(location,actGood,tree)
        tree = makeTree(noChangeMatrix(location))
        world.setDynamics(location,actBad,tree)
        for neighborhood in neighborhoods:
            tree = makeTree(setToConstantMatrix(location,neighborhood))
            world.setDynamics(location,actMove[neighborhood],tree)

        # Effect on my risk
        tree = noChangeMatrix(risk)
        for neighborhood in neighborhoods:
            tree = {'if': equalRow(makeFuture(location),neighborhood),
                    True: setToFeatureRow(risk,stateKey(neighborhood,'risk')),
                    False: tree}
        world.setDynamics(risk,True,makeTree(tree))
        
        # Effect on my health
        tree = makeTree({'if': thresholdRow(makeFuture(risk),0.75),
                         True: {'distribution': [(approachMatrix(health,0.75,0.),0.75),
                                                 (noChangeMatrix(health),0.25)]},
                         False: {'if': thresholdRow(makeFuture(risk),0.5),
                                 True: {'distribution': [(approachMatrix(health,0.8,0),0.5),
                                                         (noChangeMatrix(health),0.25)]},
                                 False: {'if': thresholdRow(makeFuture(risk),0.25),
                                         True: {'distribution':  [(approachMatrix(health,0.85,0),0.25),
                                                                  (noChangeMatrix(health),0.75)]},
                                         False: noChangeMatrix(health)}}})
        world.setDynamics(health,True,tree)

        # Effect on kids' health
        tree = makeTree({'if': thresholdRow(makeFuture(risk),0.75),
                         True: {'distribution': [(approachMatrix(kids,0.6,0.),0.75),
                                                 (noChangeMatrix(kids),0.25)]},
                         False: {'if': thresholdRow(makeFuture(risk),0.5),
                                 True: {'distribution': [(approachMatrix(kids,0.7,0),0.5),
                                                         (noChangeMatrix(kids),0.25)]},
                                 False: {'if': thresholdRow(makeFuture(risk),0.25),
                                         True: {'distribution':  [(approachMatrix(kids,0.8,0),0.25),
                                                                  (noChangeMatrix(kids),0.75)]},
                                         False: noChangeMatrix(kids)}}})
        world.setDynamics(kids,True,tree)
        
        # Reward
        self.setReward(maximizeFeature(health,self.name),1.)
        self.setReward(maximizeFeature(wealthy,self.name),1.)
        self.setReward(maximizeFeature(kids,self.name),1.)
        # Decision-making parameters
        self.setAttribute('horizon',2)
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
    parser.add_argument('-p','--population',default=2,type=int,help='Number of actors')
    parser.add_argument('-a','--area',default=4,type=int,help='Number of neighborhoods')
    parser.add_argument('-n','--number',default=1,type=int,help='Number of days to run')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.getLogger().setLevel(level)

    world = World()
    world.diagram = Diagram()

    
    # Shelter
    world.defineState(None,'shelterRisk',float)
    world.setFeature('shelterRisk',random.random()/5.)
    
#    allowPets = world.defineState(shelter.name,'allowPets',bool)
#    world.setFeature(allowPets,False)

    neighborhoods = {}
    for neighborhood in range(args['area']):
        n = Neighborhood('Neighborhood%02d' % (neighborhood),world)
        neighborhoods[n.name] = n

    population = []
    for i in range(args['population']):
        agent = Person('%02d' % (i),world)
        population.append(agent)

    world.setOrder([{agent.name for agent in population}])
    for agent in population:
        beliefs = agent.resetBelief()
        for other in population:
            if other.name != agent.name:
                    agent.ignore(other.name,'%s0' % (agent.name))


    world.printState()
    for day in range(args['number']):
        oldState = world.state
        newState = world.step(select=False)
        print 'Day %d' % (day+1)
        world.explainAction(newState,level=1)
        world.printState(newState)

#    print float(shelter)/float(len(data))

#    world.save('scenario.psy')

#    world.printState()
#    world.toCDF(world,'/tmp/testing')
#    data = []

