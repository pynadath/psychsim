from psychsim.pwl import *
from psychsim.reward import *
from psychsim.agent import Agent

from data import likert
from region import Region
from actor import Actor

class System(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'System')
        world.addAgent(self)

        world.diagram.setColor(self.name,'gray')
        self.setAttribute('static',True)
        
        resources = world.defineState(self.name,'resources',int,lo=0,hi=100)
        self.setState('resources',int(likert[5][config.getint('System','resources')]*100))
        
        regions = [name for name in self.world.agents
                        if isinstance(self.world.agents[name],Region)]
        population = [name for name in self.world.agents
                      if isinstance(self.world.agents[name],Actor)]

        populated = set()
        for actor in population:
            self.setReward(maximizeFeature(stateKey(actor,'health'),self.name),
                           likert[5][config.getint('System','reward_health')])
            self.setReward(minimizeFeature(stateKey(actor,'grievance'),self.name),
                           likert[5][config.getint('System','reward_grievance')])
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
        self.setAttribute('horizon',config.getint('System','horizon'))
