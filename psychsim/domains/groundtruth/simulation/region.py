import logging
import random
import sys

if (sys.version_info > (3, 0)):
    import configparser
else:
    import ConfigParser as configparser

from psychsim.agent import Agent

from psychsim.domains.groundtruth.simulation.data import likert,toLikert,sampleNormal

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
        
        #//GT: node 34; 1 of 1; next 15 lines
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
            #//GT: node 46; 1 of 1; next 8 lines
            sigma = config.getint('Regions','economy_sigma')
            if sigma > 0:
                self.economy = sampleNormal(mean,sigma)
            else:
                self.economy = likert[5][mean-1]
            economy = world.defineState(self.name,'economy',float,codePtr=True,
                                        description='Current economic level of region')
            world.setFeature(economy,self.economy)

        #//GT: node 35; 1 of 1; next 8 lines
        if index is not None:
            # Shelter in this region
            world.defineState(self.name,'shelterRisk',float,codePtr=True)
            riskLevel = int(config.get('Shelter','risk').split(',')[index])
            if riskLevel > 0:
                self.setState('shelterRisk',likert[5][riskLevel-1])
            else:
                self.setState('shelterRisk',0.)
            world.defineState(self.name,'shelterPets',bool,codePtr=True)
        #//GT: node 36; 1 of 1; next 4 lines
            if config.get('Shelter','pets').split(',')[index] == 'yes':
                self.setState('shelterPets',True)
            else:
                self.setState('shelterPets',False)
            self.capacity = int(config.get('Shelter','capacity').split(',')[index])
            if self.capacity > 0:
                #//GT: node 44; 1 of 1; next 2 lines
                world.defineState(self.name,'shelterCapacity',int,codePtr=True)
                self.setState('shelterCapacity',self.capacity)
                #//GT: node 45; 1 of 1; next 2 lines
                world.defineState(self.name,'shelterOccupancy',int,codePtr=True)
                self.setState('shelterOccupancy',0)
        else:
            self.capacity = 0

    def distance(self,region):
        if isinstance(region,str):
            return self.distance(self.world.agents[region])
        else:
            return abs(region.x-self.x) + abs(region.y-self.y)
    

    def setInhabitants(self,agents):
        self.inhabitants = agents
        total = sum([agent.getState('resources').expectation() for agent in agents])
#        if agents:
#            self.setState('economy',total/float(len(agents)))
#        else:
#            self.setState('economy',total)

    def configIndex(self):
        return self.config.get('Shelter','region').split(',').index(self.name[-2:])
