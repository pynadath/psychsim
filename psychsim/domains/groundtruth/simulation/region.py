import logging
import random
import sys

if (sys.version_info > (3, 0)):
    import configparser
else:
    import ConfigParser as configparser

from psychsim.agent import Agent

from psychsim.domains.groundtruth.simulation.data import likert,toLikert,sampleNormal,logNode

class Region(Agent):
    nameString = 'Region%02d'
    
    def __init__(self,number,world,config,index):
        name = self.nameString % (number)
        Agent.__init__(self,name)
        world.addAgent(self)

        self.number = number
        width = config.getint('Regions','width')
        maxRegion = config.getint('Regions','regions')
        self.x = (number-1) % width + 1
        self.y = int((number-1) / width) + 1
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

        if world.diagram and number == 1:
            world.diagram.setColor(self.name,'mediumseagreen')

        self.setAttribute('static',True)
        
        logNode('Region\'s risk','Risk level of region','Real in [0-1]')
        #//GT: node 1; 1 of 1; next 15 lines
        risk = world.defineState(self.name,'risk',float,description='Level of risk from hurricane',
                                 codePtr=True)
        try:
            self.risk = config.getfloat('Regions','risk_value')
        except configparser.NoOptionError:
            mean = config.getint('Regions','risk_mean')
            if mean == 0:
                self.risk = 0.
            else:
                sigma = config.getint('Regions','risk_sigma')
                if sigma > 0:
                    self.risk = sampleNormal(mean,sigma)
                else:
                    self.risk = likert[5][mean-1]
        world.setFeature(risk,self.risk)

        if config.getint('Simulation','phase',fallback=1) == 1:
            logNode('Region\'s security','Security level of Region','Real in [0-1]')
            #
            security = world.defineState(self.name,'security',float,codePtr=True,
                                         description='Level of law enforcement in region')
            try:
                self.security = config.getfloat('Regions','security_value')
            except configparser.NoOptionError:
                mean = config.getint('Regions','security_mean')
                sigma = config.getint('Regions','security_sigma')
                if sigma > 0:
                    self.security = sampleNormal(mean,sigma)
                else:
                    self.security = likert[5][mean-1]
            world.setFeature(security,self.security)
            
        mean = config.getint('Regions','economy_mean',fallback=0)
        if mean == 0:
            self.economy = None
        else:
            logNode('Region\'s economy','Economic strength of Region','Real in [0-1]')
            #//GT: node 2; 1 of 1; next 8 lines
            sigma = config.getint('Regions','economy_sigma')
            if sigma > 0:
                self.economy = sampleNormal(mean,sigma)
            else:
                self.economy = likert[5][mean-1]
            economy = world.defineState(self.name,'economy',float,codePtr=True,
                                        description='Current economic level of region')
            world.setFeature(economy,self.economy)

        if index is not None:
            # Shelter in this region
            logNode('Region\'s shelterRisk','Risk level of shelter','Real in [0-1]')
            #//GT: node 3; 1 of 1; next 6 lines
            world.defineState(self.name,'shelterRisk',float,codePtr=True)
            riskLevel = int(config.get('Shelter','risk').split(',')[index])
            if riskLevel > 0:
                self.setState('shelterRisk',likert[5][riskLevel-1])
            else:
                self.setState('shelterRisk',0.)

            logNode('Region\'s shelterPets','Whether shelter allows pets','Boolean')
            #//GT: node 4; 1 of 1; next 5 lines
            world.defineState(self.name,'shelterPets',bool,codePtr=True)
            if config.get('Shelter','pets').split(',')[index] == 'yes':
                self.setState('shelterPets',True)
            else:
                self.setState('shelterPets',False)

            self.capacity = int(config.get('Shelter','capacity').split(',')[index])
            if self.capacity > 0:
                logNode('Region\'s shelterCapacity','Maximum number of people that the shelter can accommodate','Positive integer')
                #//GT: node 5; 1 of 1; next 2 lines
                world.defineState(self.name,'shelterCapacity',int,codePtr=True)
                self.setState('shelterCapacity',self.capacity)

                logNode('Region\'s shelterOccupancy','Current number of people in this shelter','Nonnegative integer')
                #//GT: node 6; 1 of 1; next 2 lines
                world.defineState(self.name,'shelterOccupancy',int,codePtr=True)
                self.setState('shelterOccupancy',0)

        else:
            self.capacity = 0

    def distance(self,region):
        if isinstance(region,str):
            return self.distance(self.world.agents[region])
        else:
            return abs(region.x-self.x) + abs(region.y-self.y)
    
    def path(self,region):
        path = [self.name]
        while self.world.agents[path[-1]].x > self.world.agents[region].x:
            path.append(self.world.agents[path[-1]].west)
        while self.world.agents[path[-1]].x < self.world.agents[region].x:
            path.append(self.world.agents[path[-1]].east)
        while self.world.agents[path[-1]].y > self.world.agents[region].y:
            path.append(self.world.agents[path[-1]].north)
        while self.world.agents[path[-1]].y < self.world.agents[region].y:
            path.append(self.world.agents[path[-1]].south)
        return path

    def evacuationPath(self,direction=None):
        """
        :warning: Assumes coastline is on the west (i.e., can't evacuate that way)
        """
        if self.east == 'none' or self.north == 'none' or self.south == 'none':
            return [self.name]
        else:
            if direction is None or direction == 'east':
                path = [self.name]+self.world.agents[self.east].evacuationPath('east')
            else:
                path = None
            if direction is None or direction == 'north':
                newPath = [self.name]+self.world.agents[self.north].evacuationPath('north')
                if path is None or len(newPath) < len(path):
                    path = newPath
            if direction is None or direction == 'south':
                newPath = [self.name]+self.world.agents[self.south].evacuationPath('south')
                if path is None or len(newPath) < len(path):
                    path = newPath
            return path

    def setInhabitants(self,agents):
        self.inhabitants = agents
        total = sum([float(agent.getState('resources')) for agent in agents])
#        if agents:
#            self.setState('economy',total/float(len(agents)))
#        else:
#            self.setState('economy',total)

    def configIndex(self):
        return self.config.get('Shelter','region').split(',').index(self.name[-2:])
