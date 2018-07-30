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

likert = {5: [0.2,0.4,0.6,0.8,1.],
          7: [0.14,0.28,0.42,0.56,0.70,0.84,1.],
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
    
    def __init__(self,number,world,config,shelter=0):
        Agent.__init__(self,self.nameString % (number))
        world.addAgent(self)

        self.number = number
        width = config.getint('Regions','width')
        maxRegion = config.getint('Regions','regions')
        self.x = (number-1) % width + 1
        self.y = (number-1) / width + 1
        if self.y > 1:
            self.north = self.nameString % ((self.y-2)*width + self.x)
        else:
            self.north = 'none'
        if self.y*width + self.x <= maxRegion:
            self.south = self.nameString % (self.y*width + self.x)
        else:
            self.south = 'none'
        if self.x > 1:
            self.west = self.nameString % ((self.y-1)*width + self.x - 1)
        else:
            self.west = 'none'
        if self.x < width:
            self.east = self.nameString % ((self.y-1)*width + self.x + 1)
        else:
            self.east = 'none'
        self.config = config
        
        if number == 1:
            world.diagram.setColor(self.name,'mediumseagreen')

        self.setAttribute('static',True)
        
        risk = world.defineState(self.name,'risk',float)
        mean = config.getint('Regions','risk_mean')
        sigma = config.getint('Regions','risk_sigma')
        if sigma > 0:
            self.risk = random.gauss(likert[5][mean-1],likert[5][sigma-1])
        else:
            self.risk = likert[5][mean-1]
        world.setFeature(risk,likert[5][toLikert(self.risk,5)-1])

        security = world.defineState(self.name,'security',float)
        mean = config.getint('Regions','security_mean')
        sigma = config.getint('Regions','security_sigma')
        if sigma > 0:
            self.security = random.gauss(likert[5][mean-1],likert[5][sigma-1])
        else:
            self.security = likert[5][mean-1]
        world.setFeature(security,likert[5][toLikert(self.security,5)-1])

        if shelter:
            # Shelter in this region
            world.defineState(self.name,'shelterRisk',float)
            self.setState('shelterRisk',likert[5][config.getint('Shelter','risk')])
            world.defineState(self.name,'shelterPets',bool)
            self.setState('shelterPets',config.getboolean('Shelter','pets'))
            world.defineState(self.name,'shelterCapacity',int)
            self.setState('shelterCapacity',shelter)
            world.defineState(self.name,'shelterOccupancy',int)
            self.setState('shelterOccupancy',0)

class Nature(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'Nature')
        world.addAgent(self)

        world.diagram.setColor(self.name,'red')

        evolution = self.addAction({'verb': 'evolve'})

        phase = world.defineState(self.name,'phase',list,['none','approaching','active'])
        world.setFeature(phase,'none')
        days = world.defineState(self.name,'days',int)
        world.setFeature(days,0)

        regions = sorted([name for name in self.world.agents
                                if isinstance(self.world.agents[name],Region)])
        location = world.defineState(self.name,'location',list,regions+['none'])
        world.setFeature(location,'none')
        
        # Phase dynamics
        prob = likert[5][config.getint('Disaster','phase_change_prob')-1]
        minDays = config.getint('Disaster','phase_min_days')
        tree = makeTree({'if': equalRow(phase,'none'),
                         # When does a hurricane emerge
                         True: {'if': thresholdRow(days,minDays),
                                True: {'distribution': [(setToConstantMatrix(phase,'approaching'),
                                                         prob),
                                                        (noChangeMatrix(phase),1.-prob)]},
                                False: noChangeMatrix(phase)},
                         False: {'if': equalRow(phase,'approaching'),
                                 # When does hurricane make landfall
                                 True: {'if': thresholdRow(days,minDays),
                                        True: {'distribution': [(setToConstantMatrix(phase,'active'),
                                                                 prob),
                                                                (noChangeMatrix(phase),1.-prob)]},
                                        False: noChangeMatrix(phase)},
                                 # Active hurricane
                                 False: {'if': equalRow(location,'none'),
                                         True: setToConstantMatrix(phase,'none'),
                                         False: noChangeMatrix(phase)}}})
        world.setDynamics(phase,evolution,tree)

        tree = makeTree({'if': equalFeatureRow(phase,makeFuture(phase)),
                         True: incrementMatrix(days,1),
                         False: setToConstantMatrix(days,0)})
        world.setDynamics(days,True,tree)

        category = world.defineState(self.name,'category',int)
        world.setFeature(category,0)

        tree = makeTree({'if': equalRow(makeFuture(phase),'approaching'),
                         True: {'if': equalRow(category,0),
                                # Generate a random cateogry
                                True: {'distribution': [(setToConstantMatrix(category,1),0.2),
                                                        (setToConstantMatrix(category,2),0.2),
                                                        (setToConstantMatrix(category,3),0.2),
                                                        (setToConstantMatrix(category,4),0.2),
                                                        (setToConstantMatrix(category,5),0.2)]},
                                False: noChangeMatrix(category)},
                         False: {'if': equalRow(makeFuture(phase),'active'),
                                 True: noChangeMatrix(category),
                                 False: setToConstantMatrix(category,0)}})
        world.setDynamics(category,evolution,tree)

        # For computing initial locations
        coastline = {r for r in regions if world.agents[r].x == 1}
        prob = 1./float(len(coastline))
        # For computing hurricane movement
        subtree = noChangeMatrix(location)
        for name in regions:
            region = world.agents[name]
            subtree = {'if': equalRow(location,name),
                       True: {'distribution': [(setToConstantMatrix(location,region.north),0.5),
                                               (setToConstantMatrix(location,region.east),0.5)]},
                       False: subtree}
        tree = makeTree({'if': equalRow(makeFuture(phase),'approaching'),
                         True: {'if': equalRow(location,'none'),
                                # Generate initial location estimate
                                True: {'distribution': [(setToConstantMatrix(location,r),prob) \
                                                        for r in coastline]},
                                # No change?
                                False: noChangeMatrix(location)},
                         False: {'if': equalRow(makeFuture(phase),'active'),
                                 # Hurricane moving through regions
                                 True: subtree,
                                 # No hurricane
                                 False: setToConstantMatrix(location,'none')}})
        world.setDynamics(location,evolution,tree)

        # Effect of disaster on risk
        base_increase = likert[5][config.getint('Disaster','risk_impact')-1]
        base_decrease = likert[5][config.getint('Disaster','risk_decay')-1]
        for region in regions:
            risk = stateKey(region,'risk')
            tree = noChangeMatrix(risk)
            for center in regions:
                distance = abs(world.agents[center].x-world.agents[region].x) + \
                           abs(world.agents[center].y-world.agents[region].y)
                subtree = approachMatrix(risk,base_increase*5,1.)
                for cat in range(4):
                    effect = base_increase*float(cat+1)/float(distance+2)
                    subtree = {'if': equalRow(category,cat+1),
                            True: approachMatrix(risk,effect,1.),
                            False: subtree}
                tree = {'if': equalRow(makeFuture(location),center),
                        True: subtree,
                        False: tree}
            tree = makeTree({'if': equalRow(makeFuture(phase),'active'),
                             True: tree, False: approachMatrix(risk,base_decrease,0.)})
            world.setDynamics(risk,evolution,tree)
        if config.getboolean('Shelter','exists'):
            for index in map(int,config.get('Shelter','region').split(',')):
                region = Region.nameString % (index)
                risk = stateKey(region,'shelterRisk')
                subtree = noChangeMatrix(risk)
                for cat in range(5):
                    effect = base_increase*float(cat)
                    subtree = {'if': equalRow(category,cat+1),
                               True: approachMatrix(risk,effect,1.),
                               False: subtree}
                tree = makeTree({'if': equalRow(makeFuture(phase),'active'),
                                 True: {'if': equalRow(makeFuture(location),region),
                                        True: subtree,
                                        False: noChangeMatrix(risk)},
                                 False: approachMatrix(risk,base_decrease,0.)})
                world.setDynamics(risk,evolution,tree)
        self.setAttribute('static',True)

        # Advance calendar after Nature moves
        tree = makeTree(incrementMatrix(stateKey(WORLD,'day'),1))
        world.setDynamics(stateKey(WORLD,'day'),evolution,tree)
        
class System(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'System')
        world.addAgent(self)

        world.diagram.setColor(self.name,'gray')
        
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
        allocation = config.getint('System','system_allocation')
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
                                                    likert[5][config.getint('Actors','attachment_threshold')]),
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
        if random.random() > likert[5][config.getint('Actors','ethnic_majority')]:
            self.ethnicGroup = 'minority'
        else:
            self.ethnicGroup = 'majority'
        world.setFeature(ethnic,self.ethnicGroup)

        religion = world.defineState(self.name,'religion',list,['majority','minority','none'])
        if random.random() < likert[5][config.getint('Actors','religious_majority')]:
            self.religion = 'majority'
        else:
            atheistPct = config.getint('Actors','atheists')
            if atheistPct and random.random() < likert[5][atheistPct]:
                self.religion = 'none'
            else:
                self.religion = 'minority'
        world.setFeature(religion,self.religion)

        gender = world.defineState(self.name,'gender',list,['male','female'])
        if random.random() > 0.5:
            self.gender = 'male'
        else:
            self.gender = 'female'
        world.setFeature(gender,self.gender)
        
        age = world.defineState(self.name,'age',int)
        ageMin = config.getint('Actors','age_min')
        ageMax = config.getint('Actors','age_max')
        self.age = random.randint(ageMin,ageMax)
        ageInterval = toLikert(float(self.age-ageMin)/float(ageMax-ageMin),5)
        world.setFeature(age,self.age)
        
        kids = world.defineState(self.name,'children',int,lo=0,hi=2)
        self.kids = random.randint(0,config.getint('Actors','children_max'))
        world.setFeature(kids,self.kids)

        job = world.defineState(self.name,'employed',bool)
        threshold = likert[5][config.getint('Actors','job_%s' % (self.ethnicGroup))-1]
        self.job = random.random() > threshold
        world.setFeature(job,self.job)
        
        # Psychological
        attachmentStyles = {'secure': likert[5][config.getint('Actors','attachment_secure')],
                            'anxious': likert[5][config.getint('Actors','attachment_anxious')]}
        attachmentStyles['avoidant'] = 1.-attachmentStyles['secure']-attachmentStyles['anxious']
        attachmentStyles = Distribution(attachmentStyles)
        attachment = world.defineState(self.name,'attachment',list,attachmentStyles.domain())
        self.attachment = attachmentStyles.sample()
        world.setFeature(attachment,self.attachment)

        regions = sorted([name for name in self.world.agents
                          if isinstance(self.world.agents[name],Region)])
        region = world.defineState(self.name,'region',list,regions)
        home = regions[(number-1)*config.getint('Regions','regions')/
                       config.getint('Actors','population')]
        world.setFeature(region,home)

        # For display use only
        tooClose = True
        xKey = world.defineState(self.name,'x',float)
        yKey = world.defineState(self.name,'y',float)
        while tooClose:
            x = random.random()
            y = random.random()
            for neighbor in [a for a  in world.agents.values() if isinstance(a,Actor) and \
                             not a.name == self.name and a.getState('location').first() == home]:
                if abs(neighbor.getState('x').first()-x)+abs(neighbor.getState('y').first()-y) < 0.1:
                    break
            else:
                tooClose = False
        world.setFeature(xKey,x)
        world.setFeature(yKey,y)
                             

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
        meanHealth = int(config.get('Actors','health_mean_age').split(',')[ageInterval-1])
        if self.ethnicGroup == 'minority':
            meanHealth += config.getint('Actors','health_mean_ethnic_minority')
        meanHealth = max(1,min(5,meanHealth))
        sigma = config.getint('Actors','health_sigma')
        if sigma > 0:
            self.health = random.gauss(likert[5][meanHealth-1],likert[5][sigma])
            self.health = likert[5][toLikert(self.health,5)-1]
        else:
            self.health = likert[5][meanHealth-1]
        world.setFeature(health,self.health)

        wealth = world.defineState(self.name,'resources',float)
        meanWealth = int(config.get('Actors','wealth_mean_age').split(',')[ageInterval-1])
        if self.ethnicGroup == 'minority':
            meanWealth += config.getint('Actors','wealth_mean_ethnic_minority')
        if self.gender == 'female':
            meanWealth += config.getint('Actors','wealth_mean_female')
        if self.religion == 'minority':
            meanWealth += config.getint('Actors','wealth_mean_religious_minority')
        meanWealth = max(1,min(5,meanWealth))
        sigma = config.getint('Actors','wealth_sigma')
        if sigma > 0:
            self.wealth = random.gauss(likert[5][meanWealth-1],likert[5][sigma])
            self.wealth = likert[5][toLikert(self.wealth,5)-1]
        else:
            self.wealth = likert[5][meanWealth-1]
        world.setFeature(wealth,self.wealth)

        risk = world.defineState(self.name,'risk',float)
        world.setFeature(risk,world.getState(home,'risk').expectation())

        mean = config.getint('Actors','grievance_ethnic_%s' % (self.ethnicGroup))
        mean += config.getint('Actors','grievance_religious_%s' % (self.religion))
        mean += config.getint('Actors','grievance_%s' % (self.gender))
        if self.wealth > 0.75:
            mean += config.getint('Actors','grievance_wealth_yes')
        else:
            mean += config.getint('Actors','grievance_wealth_no')
        mean = min(max(1,mean),5)
        sigma = config.getint('Actors','grievance_sigma')
        grievance = world.defineState(self.name,'grievance',float)
        if sigma > 0:
            self.grievance = random.gauss(likert[5][mean-1],likert[5][sigma])
            self.grievance = likert[5][toLikert(self.grievance,5)-1]
        else:
            self.grievance = likert[5][mean-1]
        world.setFeature(grievance,self.grievance)

        # Actions and Dynamics

        nop = self.addAction({'verb': 'doNothing'})
        goHome = None
        if config.getboolean('Shelter','exists'):
            # Go to shelter
            actShelter = {}
            for index in config.get('Shelter','region').split(','):
                shelter = 'shelter%s' % (index)
                tree = {'if': equalRow(stateKey('Nature','phase'),'none'),
                        True: False,
                        False: {'if': trueRow(alive),
                                True: {'if': equalRow(location,shelter),
                                       True: False, False: True}, False: False}}
                if config.getboolean('Actors','evacuation'):
                    tree = {'if': equalRow(location,'evacuated'),
                            True: False, False: tree}
                if config.getboolean('Actors','movement'):
                    # Actors move from region to region
                    tree = {'if': equalFeatureRow(location,Region.nameString % (int(index))),
                            True: tree, False: False}
                tree = makeTree(tree)
                actShelter[index] = self.addAction({'verb':'moveTo','object': shelter},
                                                   tree.desymbolize(world.symbols))
            # Return from shelter
            if goHome is None:
                pass
        if config.getboolean('Actors','evacuation'):
            # Evacuate city altogether
            tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                             True: False,
                             False: {'if': equalRow(location,'evacuated'),
                                     True: False,
                                     False: {'if': trueRow(alive),
                                             True: True, False: False}}})
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

        if config.getint('Actors','children_max') > 0:
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
        if config.getint('Actors','children_max') > 0:
            self.setReward(maximizeFeature(kids,self.name),1.)
        if config.getboolean('Actors','beliefs'):
            # Observations
            omega = self.defineObservation('phase',domain=list,
                                           lo=self.world.variables['Nature\'s phase']['elements'])
            self.setO('phase',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey('Nature','phase')))))
            self.setState('phase','none')
            omega = self.defineObservation('center',domain=list,
                                           lo=self.world.variables['Nature\'s location']['elements'])
            self.setO('center',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey('Nature','location')))))
            self.setState('center','none')
            omega = self.defineObservation('category',domain=int)
            self.setO('category',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey('Nature','category')))))
            self.setState('category',0)
            omega = self.defineObservation('perceivedHealth')
            self.setO('perceivedHealth',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey(self.name,'health')))))
            self.setState('perceivedHealth',self.health)
            omega = self.defineObservation('perceivedKids',domain=int,lo=0,hi=2)
            self.setO('perceivedKids',None,
                      makeTree(setToFeatureMatrix(omega,makeFuture(stateKey(self.name,'children')))))
            self.setState('perceivedKids',self.kids)
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
            Rneighbors = config.getint('Actors','altruism_neighbors')
            Rfriends = config.getint('Actors','altruism_friends')
            if Rneighbors >= 0 and other in neighbors:
                self.setReward(maximizeFeature(stateKey(other.name,'health'),
                                                self.name),likert[5][Rneighbors])
            elif config.getint('Actors','friends') > 0 and Rfriends >= 0 and \
                 self.world.getFeature(binaryKey(self.name,other.name,'friendOf')).first():
                self.setReward(maximizeFeature(stateKey(other.name,'health'),
                                                self.name),likert[5][Rfriends])
        
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
