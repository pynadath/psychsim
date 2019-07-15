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
        
        self.resources = None
#        resources = world.defineState(self.name,'resources',int,lo=0,hi=100,codePtr=True)
#        self.setState('resources',int(likert[5][config.getint('System','resources')-1]*100))
        population = [name for name in self.world.agents
                      if isinstance(self.world.agents[name],Actor)]

        populated = self.getPopulated(population)
        for actor in population:
            self.setReward(maximizeFeature(stateKey(actor,'health'),self.name),
                           likert[5][config.getint('System','reward_health')-1])
            self.setReward(minimizeFeature(stateKey(actor,'grievance'),self.name),
                           likert[5][config.getint('System','reward_grievance')-1])
        self.addAction({'verb': 'doNothing'},codePtr=True)
        self.setAidDynamics(population)
        self.setAttribute('horizon',config.getint('System','horizon'))
        self.TA2BTA1C52 = False
        self.TA2BTA1C54 = False
        self.prescription = None

    def getPopulated(self,population):
        populated = set()
        for actor in population:
            populated.add(self.world.agents[actor].demographics['home'])
        return populated

    def setAidDynamics(self,population):
        #//GT: node 37; 1 of 1; next 12 lines        
        regions = self.getPopulated(population)
        allocation = self.config.getint('System','system_allocation')
        try:
            if self.resources is None:
                self.resources = allocation
            resources = self.resources
        except AttributeError:
            self.resources = allocation
            resources = self.resources
        scale = resources/likert[5][max(allocation,1)]
        for region in regions:
            allocate = self.addAction({'verb': 'allocate','object': region},codePtr=True)
            risk = stateKey(region,'risk')
            impact = 1-pow(1-likert[5][self.config.getint('System','system_impact')-1],scale)
            tree = makeTree(approachMatrix(risk,impact,
                                           0. if self.config.getint('Simulation','phase',fallback=1) == 1 else self.world.agents[region].risk))
            self.world.setDynamics(risk,allocate,tree,codePtr=True)
#            tree = makeTree(incrementMatrix(resources,-allocation))
#            self.world.setDynamics(resources,allocate,tree,codePtr=True)
            if self.config.getboolean('Actors','grievance') and \
               self.config.getint('Actors','grievance_delta') > 0:
                delta = likert[5][self.config.getint('Actors','grievance_delta')-1]
                delta /= len(regions)
                delta = 1-pow(1-delta,scale)
                for actor in population:
                    grievance = stateKey(actor,'grievance')
                    if self.world.agents[actor].demographics['home'] == region:
                        tree = makeTree(approachMatrix(grievance,delta,0.))
                    else:
                        tree = makeTree(approachMatrix(grievance,delta,1.))
                    self.world.setDynamics(grievance,allocate,tree,codePtr=True)

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
            if isinstance(self.prescription,dict):
                day = self.world.getState(WORLD,'day',state)
                assert len(day) == 1
                day = day.first()
                if day in self.prescription and 'Region' in self.prescription[day]:
                    for action in actions:
                        if action['object'] == self.prescription[day]['Region']:
                            choice = (None,action)
                            break
                    else:
                        raise RuntimeError('Unable to find allocation action for %s' % (targets[0][0]))
                else:
                    choice = None
            elif isinstance(self.prescription,list) and isinstance(self.prescription[0],str):
                for action in actions:
                    if action['object'] == self.prescription[0]:
                        choice = (None,action)
                        break
                else:
                    choice = None
            else:
                choice = None
        except AttributeError:
            choice = None
        if choice is None:
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
                elif self.TA2BTA1C54:
                    # allocate aid to the region with the most current people sheltering and evacuating.
                    inTrouble = {region: 0 for region in self.world.agents if region[:6] == 'Region'}
                    for actor in [name for name in self.world.agents if name[:5] == 'Actor']:
                        if self.world.getState(actor,'alive',state).first():
                            region = self.world.getState(actor,'region').first()
                            if self.world.getState(actor,'location',state).first() != region:
                                inTrouble[region] = inTrouble[region]+1
                    targets = sorted(list(inTrouble.items()),key=lambda t: t[1],reverse=True)
                    for action in actions:
                        if action['object'] == targets[0][0]:
                            choice = (None,action)
                            break
                    else:
                        raise RuntimeError('Unable to find allocation action for %s' % (targets[0][0]))
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
            
