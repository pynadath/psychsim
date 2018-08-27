import logging
import random

from psychsim.agent import Agent

from data import likert,toLikert,sampleNormal

class Region(Agent):
    nameString = 'Region%02d'
    
    def __init__(self,number,world,config,shelter):
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
        
        if number == 1:
            world.diagram.setColor(self.name,'mediumseagreen')

        self.setAttribute('static',True)
        
        risk = world.defineState(self.name,'risk',float)
        mean = config.getint('Regions','risk_mean')
        sigma = config.getint('Regions','risk_sigma')
        if sigma > 0:
            self.risk = sampleNormal(mean,sigma)
        else:
            self.risk = likert[5][mean-1]
        world.setFeature(risk,likert[5][toLikert(self.risk,5)-1])

        security = world.defineState(self.name,'security',float)
        mean = config.getint('Regions','security_mean')
        sigma = config.getint('Regions','security_sigma')
        if sigma > 0:
            self.security = sampleNormal(mean,sigma)
        else:
            self.security = likert[5][mean-1]
        world.setFeature(security,likert[5][toLikert(self.security,5)-1])

        if shelter:
            # Shelter in this region
            world.defineState(self.name,'shelterRisk',float)
            riskLevel = config.getint('Shelter','risk')
            if riskLevel > 0:
                self.setState('shelterRisk',likert[5][riskLevel-1])
            else:
                self.setState('shelterRisk',0.)
            world.defineState(self.name,'shelterPets',bool)
            self.setState('shelterPets',config.getboolean('Shelter','pets'))
            world.defineState(self.name,'shelterCapacity',int)
            self.setState('shelterCapacity',shelter)
            world.defineState(self.name,'shelterOccupancy',int)
            self.setState('shelterOccupancy',0)
