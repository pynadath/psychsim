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
        health = world.defineState(self.name,'health',bool)
        world.setFeature(health,True)
        resources = world.defineState(self.name,'resources',float)
        world.setFeature(resources,random.random()/2.+0.25)

        # Demographic info
        ethnic = world.defineState(self.name,'ethnicGroup',list,['majority','minority'])
        if random.random() > 0.75:
            world.setFeature(ethnic,'minority')
        else:
            world.setFeature(ethnic,'majority')
        wealthy = world.defineState(self.name,'wealthy',bool)
        world.setFeature(wealthy,random.random()>0.75)
        gender = world.defineState(self.name,'gender',list,['male','female'])
        if random.random() > 0.5:
            world.setFeature(gender,'male')
        else:
            world.setFeature(gender,'female')
        kids = world.defineState(self.name,'children',bool)
        world.setFeature(kids,random.random()>0.75)

        neighborhoods = [name for name in self.world.agents
                         if isinstance(self.world.agents[name],Neighborhood)]
        neighborhood = world.defineState(self.name,'neighborhood',list,neighborhoods)
        home = random.choice(neighborhoods)
        world.setFeature(neighborhood,home)
        location = world.defineState(self.name,'location',list,neighborhoods+
                                     ['shelter','gone','home'])
        world.setFeature(location,'home')

        x = world.defineState(self.name,'x',float)
        world.setFeature(x,random.random())
        y = world.defineState(self.name,'y',float)
        world.setFeature(y,random.random())

        attachmentStyles = ['secure','insecure']
        attachment = world.defineState(self.name,'attachment',list,attachmentStyles)
        world.setFeature(attachment,random.choice(attachmentStyles))

        grievance = world.defineState(self.name,'grievance',bool)
        world.setFeature(grievance,random.random()>0.85)

        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,random.random()/2.+0.25)

        # Actions and Dynamics

        # A: Go home
        actHome = self.addAction({'verb':'goHome'})
        # Effect on location
        tree = makeTree(setToConstantMatrix(location,'home'))
        world.setDynamics(location,actHome,tree)
        # Effect on my health
        tree = makeTree(noChangeMatrix(health))
        world.setDynamics(health,actHome,tree)
        # Effect on kids' health
        tree = makeTree(noChangeMatrix(kids))
        world.setDynamics(kids,actHome,tree)
        # Effect on risk
        tree = makeTree(setToFeatureMatrix(risk,stateKey(home,'risk')))
        world.setDynamics(risk,actHome,tree)

        # A: Go to a shelter
        actShelter = self.addAction({'verb':'gotoShelter'})
        # Effect on location
        tree = makeTree(setToConstantMatrix(location,'shelter'))
        world.setDynamics(location,actShelter,tree)
        # Effect on my health
        tree = makeTree(noChangeMatrix(health))
        world.setDynamics(health,actShelter,tree)
        # Effect on kids' health
        tree = makeTree(noChangeMatrix(kids))
        world.setDynamics(kids,actShelter,tree)
        # Effect on wealth
        tree = makeTree({'if': thresholdRow(wealthy,0.5),
                         True: noChangeMatrix(wealthy),
                         False: scaleMatrix(wealthy,0.5)})
        world.setDynamics(wealthy,actShelter,tree)
        # Effect on risk
        tree = makeTree(setFalseMatrix(risk))
        world.setDynamics(risk,actShelter,tree)

        # A: Leave city
        actEvacuate = self.addAction({'verb': 'evacuate'})
        # Effect on location
        tree = makeTree(setToConstantMatrix(location,'gone'))
        world.setDynamics(location,actEvacuate,tree)
        # Effect on my health
        tree = makeTree(noChangeMatrix(health))
        world.setDynamics(health,actEvacuate,tree)
        # Effect on kids' health
        tree = makeTree(noChangeMatrix(kids))
        world.setDynamics(kids,actEvacuate,tree)

        # A: Shelter in place
        actStay = self.addAction({'verb': 'noMove'})
        # Effect on location
        tree = makeTree(noChangeMatrix(location))
        world.setDynamics(location,actStay,tree)
        # Effect on my health
        tree = makeTree({'if': trueRow(risk),
                          True: {'if': trueRow(wealthy),
                                 True: {'distribution': [(setTrueMatrix(health),0.75),
                                                         (setFalseMatrix(health),0.25)]},
                                 False: {'distribution': [(setTrueMatrix(health),0.25),
                                                          (setFalseMatrix(health),0.75)]}},
                          False: setTrueMatrix(health)})
        world.setDynamics(health,actStay,tree)
        # Effect on kids' health
        tree = makeTree({'if': trueRow(kids),
                         True: {'if': trueRow(risk),
                                True: {'if': trueRow(wealthy),
                                       True: {'distribution': [(setTrueMatrix(kids),0.75),
                                                               (setFalseMatrix(kids),0.25)]},
                                       False: {'distribution': [(setTrueMatrix(kids),0.25),
                                                                (setFalseMatrix(kids),0.75)]}},
                                False: setTrueMatrix(kids)},
                         False: setFalseMatrix(kids)})
        world.setDynamics(kids,actStay,tree)

        # A: Do good/bad
        for neighborhood in self.world.agents.values():
            if isinstance(neighborhood,Neighborhood):
                # Doing good brings the risk in the neighborhood closer to False
                good = self.addAction({'verb': 'doGood','object': neighborhood.name})
                tree = makeTree({approachMatrix(stateKey(neighborhood.name,'risk'),.1,0.)})
                # Doing good brings the risk in the neighborhood closer to 0
                bad = self.addAction({'verb': 'doBad','object': neighborhood.name})
                tree = makeTree({approachMatrix(stateKey(neighborhood.name,'risk'),.1,1.)})
                
        # Reward
        self.setReward(maximizeFeature(health),1.)
#        self.setReward(maximizeFeature(pet),1.)
        self.setReward(maximizeFeature(wealthy),1.)
        self.setReward(maximizeFeature(kids),1.)
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
    parser.add_argument('-n','--number',default=100,type=int,help='Number of actors')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.getLogger().setLevel(level)

    world = World()
    world.diagram = Diagram()

    neighborhoods = {}
    for neighborhood in ['sw','nw','ne','se']:
        n = Neighborhood(neighborhood,world)
    neighborhoods.update(world.agents)

    # Shelter
    shelter = world.addAgent('shelter')
    world.diagram.setColor(shelter.name,'cornflowerblue')
    shelter.setAttribute('static',True)
#    allowPets = world.defineState(shelter.name,'allowPets',bool)
#    world.setFeature(allowPets,False)

    population = []
    for i in range(args['number']):
        agent = Person('%02d' % (i),world)
        population.append(agent)

    world.setOrder([{agent.name for agent in population}])
    for agent in population:
        beliefs = agent.resetBelief()
        for other in population:
            if other.name != agent.name:
                    agent.ignore(other.name,'%s0' % (agent.name))
    print shelter.models['shelter0']['beliefs']

#    world.printState()
#    world.toCDF(world,'/tmp/testing')
#    data = []
    result = world.step(select=False)
    world.explainAction(level=1)

#    print float(shelter)/float(len(data))

#    world.save('scenario.psy')
