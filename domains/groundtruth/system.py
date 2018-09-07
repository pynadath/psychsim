from psychsim.pwl import *
from psychsim.reward import *
from psychsim.agent import Agent

from data import likert
from region import Region
from actor import Actor

class System(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'System')
        self.config = config
        
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
            populated.add(world.getState(actor,'region').first())
#            self.setReward(maximizeFeature(stateKey(actor,'health'),self.name),1.)
#            self.setReward(minimizeFeature(stateKey(actor,'grievance'),self.name),1.)
        allocation = config.getint('System','system_allocation')
        for region in populated:
#            tree = makeTree({'if': thresholdRow(resources,allocation),True: True,False: False})
            allocate = self.addAction({'verb': 'allocate','object': region})
#                                      tree.desymbolize(world.symbols))
            risk = stateKey(region,'risk')
            self.setReward(minimizeFeature(risk,self.name),
                           likert[5][config.getint('System','reward_health')-1])
            tree = makeTree(approachMatrix(risk,likert[5][config.getint('System','system_impact')-1],
                                           0.))
            world.setDynamics(risk,allocate,tree)
#            tree = makeTree(incrementMatrix(resources,-allocation))
#            world.setDynamics(resources,allocate,tree)
            if config.getboolean('Actors','grievance'):
                delta = likert[5][config.getint('Actors','grievance_delta')]
                for actor in population:
                    grievance = stateKey(actor,'grievance')
                    tree = makeTree({'if': equalRow(stateKey(actor,'region'),region),
                                     True: approachMatrix(grievance,delta,0.),
                                     False: approachMatrix(grievance,delta,1.)})
                    world.setDynamics(grievance,allocate,tree)
        self.setAttribute('horizon',config.getint('System','horizon'))

    def reward(self,state=None,model=None,recurse=True):
        if state is None:
            state = self.world.state
        if model is None:
            model = self.world.getModel(self.name,state)
        population = [name for name in self.world.agents
                      if isinstance(self.world.agents[name],Actor)]
        weights = {'health': likert[5][self.config.getint('System','reward_health')],
                   'grievance': -likert[5][self.config.getint('System','reward_grievance')]}
        ER = 0.
        for actor in population:
            for feature in weights:
                key = stateKey(actor,feature)
                dist = state.distributions[state.keyMap[key]]
                for vector in dist.domain():
                    ER += weights[feature]*dist[vector]*vector[key]
        return ER
        
    def decide(self,state=None,horizon=None,others=None,model=None,selection=None,actions=None):
        state = self.world.state
        if actions is None:
            actions = self.getActions(state)
        risks = [(state[stateKey(a['object'],'risk')].expectation(),a) for a in actions]
        tree = makeTree(setToConstantMatrix(stateKey(self.name,ACTION),max(risks)[1]))
        return {'policy': tree.desymbolize(self.world.symbols)}
            
