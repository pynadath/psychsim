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

        regions = [name for name in world.agents
                         if isinstance(world.agents[name],Region)]


class Region(Agent):
    nameString = 'Region%02d'
    
    def __init__(self,number,world):
        Agent.__init__(self,self.nameString % (number))
        world.addAgent(self)

        if number == 1:
            world.diagram.setColor(self.name,'mediumseagreen')

        self.setAttribute('static',True)
        
        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,0.1)

        security = world.defineState(self.name,'security',float)
        world.setFeature(security,0.9)

        if config.getboolean('Shelter','exists') and \
           str(number) in config.get('Shelter','region').split(','):
            # Shelter in this region
            
            world.defineState(self.name,'shelterRisk',float)
            self.setState('shelterRisk',likert[5][config.getint('Shelter','risk')])
            world.defineState(self.name,'shelterPets',bool)
            self.setState('shelterPets',config.getboolean('Shelter','pets'))

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
        regions = sorted([name for name in self.world.agents
                                if isinstance(self.world.agents[name],Region)])
        if config.getboolean('Disaster','dynamic'):
            for region in regions:
                risk = stateKey(region,'risk')
                tree = makeTree({'if': equalRow(phase,'increasing'),
                                 True: approachMatrix(risk,.1,1.),
                                 False: {'if': equalRow(phase,'decreasing'),
                                         True: approachMatrix(risk,.1,0.),
                                         False: setToConstantMatrix(risk,0.)}})
                world.setDynamics(risk,evolution,tree)
            if config.getboolean('Shelter','exists'):
                for index in map(int,config.get('Shelter','region').split(',')):
                    region = Region.nameString % (index)
                    risk = stateKey(region,'shelterRisk')
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
    def __init__(self,world,config):
        Agent.__init__(self,'System')
        world.addAgent(self)

        world.diagram.setColor(self.name,'darkgoldenrod')
        
#        self.setAttribute('static',True)
        
        resources = world.defineState(self.name,'resources',int,lo=0,hi=100)
        self.setState('resources',int(random.random()*25.)+75)
        
        regions = [name for name in self.world.agents
                        if isinstance(self.world.agents[name],Region)]
        population = [name for name in self.world.agents
                      if isinstance(self.world.agents[name],Actor)]

        populated = set()
        for actor in population:
            self.setReward(maximizeFeature(stateKey(actor,'health'),self.name),1.)
            populated.add(world.getState(actor,'region').first())
        allocation = config.getint('City','system_allocation')
        for region in populated:
            tree = makeTree({'if': thresholdRow(resources,allocation),True: True,False: False})
            allocate = self.addAction({'verb': 'allocate','object': region},
                                      tree.desymbolize(world.symbols))
            risk = stateKey(region,'risk')
            tree = makeTree(approachMatrix(risk,0.1,0.))
            world.setDynamics(risk,allocate,tree)
            tree = makeTree(incrementMatrix(resources,-allocation))
            world.setDynamics(resources,allocate,tree)
            if config.getboolean('Actors','grievance'):
                delta = likert[5][config.getint('Actors','grievance_delta')]
                for actor in population:
                    grievance = stateKey(actor,'grievance')
                    tree = makeTree({'if': equalRow(stateKey(actor,'region'),region),
                                     True: approachMatrix(grievance,delta,0.),
                                     False: approachMatrix(grievance,delta,1.)})
                    world.setDynamics(grievance,allocate,tree)
        
class Group(Agent):
    def __init__(self,name,world,config):
        Agent.__init__(self,'Group%s' % (name))
        world.addAgent(self)

        if name == 'Region01':
            world.diagram.setColor(self.name,'yellowgreen')
            
        self.setAttribute('static',True)

        size = world.defineState(self.name,'size',int)
        self.setState('size',0)
        
        if config.getboolean('Groups','prorisk') and name in world.agents:
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            actGood = self.addAction({'verb': 'doGoodRisk','object': name},
                                     tree.desymbolize(world.symbols))
        if config.getboolean('Groups','proresources') and name in world.agents:
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            actGood = self.addAction({'verb': 'doGoodResources','object': name},
                                     tree.desymbolize(world.symbols))
        if config.getboolean('Groups','antirisk') and name in world.agents:
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            actBad = self.addAction({'verb': 'doBadRisk','object': name},
                                     tree.desymbolize(world.symbols))
        if config.getboolean('Groups','antiresources') and name in world.agents:
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            actBad = self.addAction({'verb': 'doBadResources','object': name},
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
            if config.getboolean('Actors','attachment'):
                # Reward associated with being a member
                attachment = stateKey(name,'attachment')
                R = rewardKey(name)
                tree = makeTree({'if': thresholdRow(stateKey(name,'risk'),
                                                    config.getfloat('Actors','attachment_threshold')),
                                 True: {'if': equalRow(attachment,'anxious'),
                                        True: setToFeatureMatrix(R,member,1.),
                                        False: {'if': equalRow(attachment,'avoidant'),
                                                True: setToFeatureMatrix(R,member,-1.),
                                                False: setToConstantMatrix(R,0.)}},
                                 False: setToConstantMatrix(R,0.)})
                agent.setReward(tree,config.getfloat('Actors','attachment_r'))
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
        religion = world.defineState(self.name,'religion',list,['majority','minority','none'])
        if random.random() > 0.8:
            world.setFeature(ethnic,'minority')
        elif random.random() > 0.5:
            world.setFeature(ethnic,'none')
        else:
            world.setFeature(ethnic,'majority')
        gender = world.defineState(self.name,'gender',list,['male','female'])
        if random.random() > 0.5:
            world.setFeature(gender,'male')
        else:
            world.setFeature(gender,'female')
        age = world.defineState(self.name,'age',int)
        world.setFeature(age,int(random.random()*50.)+20)
        kids = world.defineState(self.name,'children',int,lo=0,hi=2)
        if config.getboolean('Actors','children'):
            world.setFeature(kids,int(random.random()*3.))
        else:
            world.setFeature(kids,0)

        # Psychological
        attachmentStyles = ['secure','anxious','avoidant']
        attachment = world.defineState(self.name,'attachment',list,attachmentStyles)
        attachmentValue = random.choice(attachmentStyles)
        world.setFeature(attachment,attachmentValue)

        regions = sorted([name for name in self.world.agents
                                if isinstance(self.world.agents[name],Region)])
        region = world.defineState(self.name,'region',list,regions)
        home = regions[(number-1)/config.getint('City','density')]
        world.setFeature(region,home)

        # For display use only
#        x = world.defineState(self.name,'x',float)
#        world.setFeature(x,random.random())
#        y = world.defineState(self.name,'y',float)
#        world.setFeature(y,random.random())

        # Dynamic states
        locationSet = regions[:]
        locationSet.append('evacuated')
        if config.getboolean('Shelter','exists'):
            for index in config.get('Shelter','region').split(','):
                locationSet.append('shelter%s' % (index))
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
            actShelter = {}
            for index in config.get('Shelter','region').split(','):
                shelter = 'shelter%s' % (index)
                tree = {'if': trueRow(alive),
                        True: {'if': equalRow(location,shelter),
                               True: False, False: True}, False: False}
                if config.getboolean('Actors','evacuation'):
                    tree = {'if': equalRow(location,'evacuated'),
                            True: False, False: tree}
                if config.getboolean('Shelter','local'):
                    tree = {'if': equalFeatureRow(location,Region.nameString % (int(index))),
                            True: tree, False: False}
                tree = makeTree(tree)
                actShelter[index] = self.addAction({'verb':'moveTo','object': shelter},
                                                   tree.desymbolize(world.symbols))
        if config.getboolean('Actors','evacuation'):
            # Evacuate city altogether
            tree = makeTree({'if': equalRow(location,[regions[0],'evacuated']),
                             True: {'if': trueRow(alive),
                                    True: True, False: False}, False: False})
            actEvacuate = self.addAction({'verb': 'evacuate'},tree.desymbolize(world.symbols))
        if config.getboolean('Actors','prorisk'):
            # Prosocial behavior
            actGoodRisk = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == home:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actGoodRisk[region] = self.addAction({'verb': 'doGoodRisk','object': region},
                                                         tree.desymbolize(world.symbols))
        if config.getboolean('Actors','proresources'):
            # Prosocial behavior
            actGoodResources = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == home:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actGoodResources[region] = self.addAction({'verb': 'doGoodResources',
                                                               'object': region},
                                                              tree.desymbolize(world.symbols))
        if config.getboolean('Actors','antirisk'):
            # Antisocial behavior
            actBadRisk = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == home:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actBadRisk[region] = self.addAction({'verb': 'doBadRisk','object': region},
                                                        tree.desymbolize(world.symbols))
        if config.getboolean('Actors','antiresources'):
            # Antisocial behavior
            actBadResources = {}
            for region in regions:
                if config.getboolean('Actors','movement') or region == home:
                    tree = makeTree({'if': equalRow(location,region),
                                     True: {'if': trueRow(alive),True: True, False: False},
                                     False: False})
                    actBadResources[region] = self.addAction({'verb': 'doBadResources',
                                                              'object': region},
                                                        tree.desymbolize(world.symbols))
        regions = [n for n in self.world.agents.values()
                         if isinstance(n,Region)]
        if config.getboolean('Actors','movement'):
            actMove = {}
            for region in regions:
                cell = int(region.name[-2:])
                row = (cell-1) / 5
                col = (cell-1) % 5
                neighbors = []
                if row > 0:
                    neighbors.append('Region%02d' % ((row-1)*5+col+1))
                if row < len(regions)/5-1:
                    neighbors.append('Region%02d' % ((row+1)*5+col+1))
                if col > 0:
                    neighbors.append('Region%02d' % (cell-1))
                if col < 4:
                    neighbors.append('Region%02d' % (cell+1))
                tree = makeTree({'if': equalRow(location,neighbors),
                                 True: {'if': trueRow(alive),
                                        True: True, False: False}, False: False})
                actMove[region.name] = self.addAction({'verb': 'moveTo',
                                                            'object': region.name},
                                                            tree.desymbolize(world.symbols))

        # Information-seeking actions
        if config.getboolean('Actors','infoseek'):
            tree = makeTree({'if': trueRow(alive), True: True, False: False})
            self.addAction({'verb': 'infoSeek','object': home},tree.desymbolize(world.symbols))
                
        # Effect on location
        if config.getboolean('Shelter','exists'):
            for index,action in actShelter.items():
                tree = makeTree(setToConstantMatrix(location,'shelter%s' % (index)))
            world.setDynamics(location,action,tree)
        if config.getboolean('Actors','evacuation'):
            tree = makeTree(setToConstantMatrix(location,'evacuated'))
            world.setDynamics(location,actEvacuate,tree)
        if config.getboolean('Actors','movement'):
            for region in regions:
                tree = makeTree(setToConstantMatrix(location,region.name))
                world.setDynamics(location,actMove[region.name],tree)

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
            for index in config.get('Shelter','region').split(','):
                tree = {'if': equalRow(makeFuture(location),'shelter%s' % (index)),
                    True: setToFeatureMatrix(risk,stateKey(Region.nameString % (int(index)),'risk')),
                    False: tree}
        if config.getboolean('Actors','movement'):
            for region in regions:
                tree = {'if': equalRow(makeFuture(location),region.name),
                        True: setToFeatureMatrix(risk,stateKey(region.name,'risk')),
                        False: tree}
        tree = {'if': trueRow(alive),True: tree, False: setToConstantMatrix(risk,0.)}
        world.setDynamics(risk,True,makeTree(tree))
        
        # Effect on my health
        tree = makeTree({'if': trueRow(alive),
                         True: {'if': thresholdRow(makeFuture(risk),0.75),
                                True: {'distribution': [(approachMatrix(health,0.75,0.),0.75),
                                                        (noChangeMatrix(health),0.25)]},
                                False: {'if': thresholdRow(makeFuture(risk),0.5),
                                        True: {'distribution': [(approachMatrix(health,0.75,0.),0.5),
                                                                (noChangeMatrix(health),0.5)]},
                                        False: {'if': thresholdRow(makeFuture(risk),0.25),
                                                True: {'distribution':  [(approachMatrix(health,0.75,0),0.25),
                                                                         (noChangeMatrix(health),0.75)]},
                                                False: noChangeMatrix(health)}}},
                         False: setToConstantMatrix(health,0.)})
        world.setDynamics(health,True,tree)

        if config.getboolean('Actors','children'):
            # Effect on kids' health
            tree = makeTree({'if': thresholdRow(makeFuture(risk),0.75),
                             True: {'distribution': [(approachMatrix(kids,0.75,0.),0.75),
                                                     (noChangeMatrix(kids),0.25)]},
                             False: {'if': thresholdRow(makeFuture(risk),0.5),
                                     True: {'distribution': [(approachMatrix(kids,0.75,0.),0.5),
                                                             (noChangeMatrix(kids),0.5)]},
                                     False: {'if': thresholdRow(makeFuture(risk),0.25),
                                             True: {'distribution':  [(approachMatrix(kids,0.75,0),0.25),
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

        if config.getboolean('Actors','prorisk'):
            # Effect of doing good
            benefit = likert[5][config.getint('Actors','prorisk_benefit')]
            for region,action in actGoodRisk.items():
                key = stateKey(region,'risk')
                tree = makeTree(approachMatrix(key,benefit,0.))
                world.setDynamics(key,action,tree)
            proRisk = likert[5][config.getint('Actors','prorisk_cost_risk')]
            if proRisk > 0.:
                for region,action in actGoodRisk.items():
                    tree = makeTree(approachMatrix(risk,proRisk,1.))
                    world.setDynamics(risk,action,tree)
        if config.getboolean('Actors','proresources'):
            # Effect of doing good
            benefit = likert[5][config.getint('Actors','proresources_benefit')]
            for region,action in actGoodResources.items():
                key = stateKey(region,'resources')
                tree = makeTree(approachMatrix(key,benefit,0.))
                world.setDynamics(key,action,tree)
            proRisk = likert[5][config.getint('Actors','proresources_cost_risk')]
            if proRisk > 0.:
                for region,action in actGoodResources.items():
                    tree = makeTree(approachMatrix(risk,proRisk,1.))
                    world.setDynamics(risk,action,tree)
        if config.getboolean('Actors','antiresources'):
            # Effect of doing bad
            benefit = likert[5][config.getint('Actors','antiresources_benefit')]
            for region,action in actBadResources.items():
                tree = makeTree(incrementMatrix(wealth,benefit))
                world.setDynamics(wealth,action,tree)
            antiRisk = likert[5][config.getint('Actors','antiresources_cost_risk')]
            if antiRisk > 0.:
                for region,action in actBadResources.items():
                    tree = makeTree(approachMatrix(risk,antiRisk,1.))
                    world.setDynamics(risk,action,tree)
        if config.getboolean('Actors','antirisk'):
            # Effect of doing bad
            benefit = likert[5][config.getint('Actors','antirisk_benefit')]
            for region,action in actBadResources.items():
                key = stateKey(region,'risk')
                tree = makeTree(approachMatrix(key,benefit,1.))
                world.setDynamics(key,action,tree)
            antiRisk = likert[5][config.getint('Actors','antirisk_cost_risk')]
            if antiRisk > 0.:
                for region,action in actBadResources.items():
                    tree = makeTree(approachMatrix(risk,antiRisk,1.))
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

    def makeFriend(self,friend,config):
        key = binaryKey(self.name,friend.name,'friendOf')
        if not key in self.world.variables:
            self.world.defineRelation(self.name,friend.name,'friendOf',bool)
        self.world.setFeature(key,True)
        if config.getboolean('Actors','messages'):
            tree = makeTree({'if': trueRow(stateKey(self.name,'alive')),
                             True: True, False: False})
            msg = self.addAction({'verb': 'message','object': friend.name},
                                 tree.desymbolize(self.world.symbols))

    def _initializeRelations(self,config):
        friends = set()
        population = {a for a in self.world.agents.values() if isinstance(a,self.__class__)}
        friendMax = config.getint('Actors','friends')
        myHome = self.world.getState(self.name,'region').first()
        neighbors = {a.name for a in population if a.name != self.name and \
                     self.world.getState(a.name,'region').first() == myHome}
        if friendMax > 0:
            # Social network
            friendCount = {}
            for other in population:
                if other.name != self.name:
                    friendship = binaryKey(self.name,other.name,'friendOf')
                    if not friendship in self.world.variables:
                        self.world.defineRelation(self.name,other.name,'friendOf',bool)
                    self.world.setFeature(friendship,False)
                    friendCount[other.name] = 0
                    if other.name in self.world.relations:
                        for key in self.world.relations[other.name]:
                            relation = key2relation(key)
                            if relation['relation'] == 'friendOf':
                                if self.world.getFeature(key).first():
                                    # This person has a friend
                                    friendCount[other.name] += 1
                                    if friendCount[other.name] == friendMax:
                                        del friendCount[other.name]
                                        break
            for count in range(friendMax):
                friend = random.choice(list(set(friendCount.keys())))
                self.makeFriend(self.world.agents[friend],config)
                self.world.agents[friend].makeFriend(self,config)
                if friendCount[friend] == friendMax - 1:
                    del friendCount[friend]
                else:
                    friendCount[friend] += 1

        for other in population:
            if self.name == other.name:
                continue
            Rneighbors = config.getfloat('Actors','altruism_neighbors')
            Rfriends = config.getfloat('Actors','altruism_friends')
            if Rneighbors > 0. and other in neighbors:
                self.setReward(maximizeFeature(stateKey(other.name,'health'),
                                                self.name),Rneighbors)
            elif Rfriends > 0. and \
                 self.world.getFeature(binaryKey(self.name,other.name,'friendOf')).first():
                self.setReward(maximizeFeature(stateKey(other.name,'health'),
                                                self.name),Rfriends)
        
    def _initializeBeliefs(self,config):
        # Beliefs
        friends = set()
        population = {a for a in self.world.agents.values() if isinstance(a,self.__class__)}
        myHome = self.world.getState(self.name,'region').first()
        neighbors = {a.name for a in population if a.name != self.name and \
                     self.world.getState(a.name,'region').first() == myHome}

        beliefs = agent.resetBelief()
        for other in population:
            if other.name != agent.name:
                if config.getfloat('Actors','altruism_neighbors') > 0. and \
                   other.name in neighbors:
                    # I care about my neighbors, so I can't ignore them
                    continue
#                 if world.getFeature(binaryKey(agent.name,other.name,'friendOf')).first():
#                     continue
                agent.ignore(other.name,'%s0' % (agent.name))
        if config.getboolean('Actors','misperception_risk'):
            home = self.world.getState(self.name,'region').first()
            dist = Distribution({'over': config.getfloat('Actors','misperception_risk_over'),
                                 'under': config.getfloat('Actors','misperception_risk_under')})
            dist['none'] = 1.-dist['over']-dist['under']
            mis = dist.sample()
            prob = config.getfloat('Actors','misperception_risk_prob')
            err = config.getfloat('Actors','misperception_risk_error')
            true = self.world.getState(home,'risk').expectation()
            if mis == 'over':
                dist = Distribution({true: 1.-prob,
                                     (1.-err)*true+err: prob})
            elif mis == 'under':
                dist = Distribution({true: 1.-prob,
                                     (1.-err)*true: prob})
            else:
                dist = true
            self.setBelief(stateKey(home,'risk'),dist)
        
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
                elif function and function[0] == '=':
                    entry[label] = len([a for a in population if values[a.name][feature] == function[1:]])
            table['log'].append(entry)
        elif table['population'] is Region:
            for region in regions:
                inhabitants = regions[region]['inhabitants']
                if inhabitants:
                    entry = {'day': day,
                             'region': region}
                    for feature,label,function in table['fields']:
                        if world.variables[stateKey(population[0].name,feature)]['domain'] is bool:
                            entry[label] = len([a for a in inhabitants if values[a.name][feature]])
                        elif feature == 'risk':
                            value = world.getState(region,feature)
                            assert len(value)
                            entry[label] = value.first()
                        elif function and function[0] == '=':
                            target = function[1:]
                            entry[label] = len([a for a in inhabitants if values[a.name][feature][:len(target)] == target])
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
    try:
        random.seed(config.getint('Simulation','seed'))
    except ValueError:
        # Non int, so assume None
        random.seed()
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.getLogger().setLevel(level)

    for run in range(args['runs']):
        world = World()
        world.diagram = Diagram()
        world.diagram.setColor(None,'deepskyblue')

        regions = {}
        for region in range(config.getint('City','regions')):
            n = Region(region+1,world)
            regions[n.name] = {'agent': n, 'inhabitants': [], 'number': region+1}

        city = City(world,config)
        nature = Nature(world,config)

        population = []
        for i in range(config.getint('Actors','population')):
            agent = Actor(i+1,world,config)
            population.append(agent)
            region = agent.getState('region').first()
            regions[region]['inhabitants'].append(agent)

        if config.getboolean('City','system'):
            system = System(world,config)
        else:
            system = None

        groups = []
        if config.getboolean('Groups','region'):
            for region,info in regions.items():
                group = Group(info['agent'].name,world,config)
                group.potentialMembers([a.name for a in info['inhabitants']])
                groups.append(group)

        for agent in population:
            agent._initializeRelations(config)
        
        order = [{agent.name for agent in population}]
#        order.insert(0,system.name)
        order.append({'Nature'})
        world.setOrder(order)

        for agent in population:
            agent._initializeBeliefs(config)

        if system:
            system.resetBelief()
        
        world.dependency.computeEvaluation()

#        for agent in population:
#            agent.compileV(state=world.state)
#            sys.exit(0)

        allTables = {'Population': {'fields': [('alive','casualties','invert'),
                                               ('location','evacuated','=evacuated'),
                                               ('location','shelter','=shelter')],
                                    'population': City,
                                    'log': []},
                     'Region': {'fields': [('alive','casualties','invert'),
                                                 ('location','evacuated','=evacuated'),
                                                 ('location','shelter','=shelter'),
                                                 ('risk','risk','likert')],
                                      'population': Region,
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
                                'log': []},
        }
        tables = {name: allTables[name] for name in allTables
                  if config.getboolean('Data',name.lower())}
        addState2tables(world,0,tables,population,regions)
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
            addState2tables(world,day,tables,population,regions)
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
