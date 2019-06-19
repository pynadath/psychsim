from psychsim.pwl import *
from psychsim.reward import *
from psychsim.agent import Agent

from psychsim.domains.groundtruth.simulation.data import likert
from psychsim.domains.groundtruth.simulation.region import Region
from psychsim.domains.groundtruth.simulation.actor import Actor

class System(Agent):
    def __init__(self,world,config):
        Agent.__init__(self,'System')
        self.config = config
        
        world.addAgent(self)

        if world.diagram:
            world.diagram.setColor(self.name,'gray')
        self.setAttribute('static',True)
        
        resources = world.defineState(self.name,'resources',int,lo=0,hi=100,codePtr=True)
        self.setState('resources',int(likert[5][config.getint('System','resources')-1]*100))
        
        regions = [name for name in self.world.agents
                        if isinstance(self.world.agents[name],Region)]
        population = [name for name in self.world.agents
                      if isinstance(self.world.agents[name],Actor)]

        populated = set()
        for actor in population:
            populated.add(world.agents[actor].demographics['home'])
            self.setReward(maximizeFeature(stateKey(actor,'health'),self.name),
                           likert[5][config.getint('System','reward_health')-1])
            self.setReward(minimizeFeature(stateKey(actor,'grievance'),self.name),
                           likert[5][config.getint('System','reward_grievance')-1])
        self.addAction({'verb': 'doNothing'},codePtr=True)
        allocation = config.getint('System','system_allocation')
        for region in populated:
            allocate = self.addAction({'verb': 'allocate','object': region},codePtr=True)
            risk = stateKey(region,'risk')
            tree = makeTree(approachMatrix(risk,likert[5][config.getint('System','system_impact')-1],
                                           0. if config.getint('Simulation','phase',fallback=1) == 1 else world.agents[region].risk))
            world.setDynamics(risk,allocate,tree,codePtr=True)
            tree = makeTree(incrementMatrix(resources,-allocation))
            world.setDynamics(resources,allocate,tree,codePtr=True)
            if config.getboolean('Actors','grievance') and \
               config.getint('Actors','grievance_delta') > 0:
                delta = likert[5][config.getint('Actors','grievance_delta')-1]
                delta /= len(regions)
                for actor in population:
                    grievance = stateKey(actor,'grievance')
                    if world.agents[actor].demographics['home'] == region:
                        tree = makeTree(approachMatrix(grievance,delta,0.))
                    else:
                        tree = makeTree(approachMatrix(grievance,delta,1.))
                    world.setDynamics(grievance,allocate,tree,codePtr=True)
        self.setAttribute('horizon',config.getint('System','horizon'))
        self.TA2BTA1C52 = False

    def reward(self,state=None,model=None,recurse=True):
        if state is None:
            state = self.world.state
        if model is None:
            model = self.world.getModel(self.name,state)
        population = [name for name in self.world.agents
                      if isinstance(self.world.agents[name],Actor)]
        weights = {'health': likert[5][self.config.getint('System','reward_health')-1],
                   'grievance': -likert[5][self.config.getint('System','reward_grievance')-1]}
        ER = 0.
        for actor in population:
            for feature in weights:
                key = stateKey(actor,feature)
                dist = state.distributions[state.keyMap[key]]
                for vector in dist.domain():
                    ER += weights[feature]*dist[vector]*vector[key]
        return ER
        
    def decide(self,state=None,horizon=None,others=None,model=None,selection=None,actions=None,
               debug={}):
        state = self.world.state
        if actions is None:
            actions = self.getActions(state)
        try:
            if self.TA2BTA1C52:
                location = self.world.getState('Nature','location',state)
                assert len(location) == 1
                for action in actions:
                    if action['object'] == location.first():
                        choice = (None,action)
                        break
                else:
                    choice = None
            else:
                choice = None
        except AttributeError:
            choice = None
        if choice is None:
            population = {name: [a for a in self.world.agents.values() if isinstance(a,Actor) and a.demographics['home'] == name]
                          for name in self.world.agents if isinstance(self.world.agents[name],Region)}
            risks = [(state[stateKey(a['object'],'risk')].expectation()*len(population[a['object']]),a)
                     for a in actions if a['object'] is not None]
            choice = max(risks)
        tree = makeTree(setToConstantMatrix(stateKey(self.name,ACTION),choice[1]))
        return {'policy': tree.desymbolize(self.world.symbols)}
            
