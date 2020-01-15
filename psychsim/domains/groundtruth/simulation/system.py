import logging

from psychsim.pwl import *
from psychsim.agent import Agent

from psychsim.domains.groundtruth.simulation.data import likert,logNode,logEdge
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
        population = [name for name in self.world.agents
                      if isinstance(self.world.agents[name],Actor)]

        populated = self.getPopulated(population)
        self.nop = self.addAction({'verb': 'doNothing'},codePtr=True)
        self.setAidDynamics(population)
        self.setAttribute('horizon',config.getint('System','horizon',fallback=1))
        self.TA2BTA1C52 = False
        self.TA2BTA1C54 = False
        self.prescription = None

        value = config.getint('System','ethnic_bias',fallback=0)
        if value < 0:
            self.ethnicBias = -likert[5][-value-1]
        elif value > 0:
            self.ethnicBias = likert[5][value-1]
        else:
            self.ethnicBias = 0
        if self.ethnicBias != 0:
            logNode('System\'s ethnicBias','Degree to which System favors actors of the ethnic majority (negative numbers mean favoring the ethnic minority)',
                'Real in [-1-1]')
            #//GT: node 44; 1 of 1; next 2 lines
            world.defineState(self.name,'ethnicBias',float,description='Degree to which System favors actors of the ethnic majority',codePtr=True)
            self.setState('ethnicBias',self.ethnicBias)

        value = config.getint('System','religious_bias',fallback=0)
        if value < 0:
            self.religiousBias = -likert[5][-value-1]
        elif value > 0:
            self.religiousBias = likert[5][value-1]
        else:
            self.religiousBias = 0
        if self.religiousBias != 0:
            logNode('System\'s religiousBias','Degree to which System favors actors of the religious majority (negative numbers mean favoring the religious minority)',
                'Real in [-1-1]')
            #//GT: node 45; 1 of 1; next 2 lines
            world.defineState(self.name,'religiousBias',float,description='Degree to which System favors actors of the religious majority',codePtr=True)
            self.setState('religiousBias',self.religiousBias)

    def getPopulated(self,population):
        populated = set()
        for actor in population:
            populated.add(self.world.agents[actor].demographics['home'])
        return populated

    def grievanceDelta(self,regions):
        allocation = self.config.getint('System','system_allocation')
        try:
            if self.resources is None:
                self.resources = allocation
            resources = self.resources
        except AttributeError:
            self.resources = allocation
            resources = self.resources
        scale = resources/likert[5][max(allocation,1)]
        if self.config.getboolean('Actors','grievance') and \
           self.config.getint('Actors','grievance_delta') > 0:
            delta = likert[5][self.config.getint('Actors','grievance_delta')-1]
            delta /= len(regions)
            if self.config.getint('Simulation','phase',fallback=1) > 1:
                delta = 1-pow(1-delta,scale)
        else:
            delta = 0
        return delta,scale

    def setAidDynamics(self,population,multiplier=1.):
        regions = self.getPopulated(population)
        delta,scale = self.grievanceDelta(regions)
        if self.config.getboolean('System','aid',fallback=True):
            logNode('System-allocate-Region','Allocation of aid to a given region','Region[01-16]')
            #//GT: node 43; 1 of 1; next 5 lines
            for region in regions:
                try:
                    allocate = self.addAction({'verb': 'allocate','object': region},codePtr=True)
                except AssertionError:
                    allocate = ActionSet([Action({'subject': self.name,'verb': 'allocate','object': region})])

                logEdge('System-allocate-Region','Region\'s risk','often','Allocating resources reduces the risk in a given region')
                #//GT: edge 60; from 43; to 1; 1 of 1; next 5 lines
                risk = stateKey(region,'risk')
                impact = (1-pow(1-likert[5][self.config.getint('System','system_impact')-1],scale))*multiplier
                tree = makeTree(approachMatrix(risk,impact,
                                               0. if self.config.getint('Simulation','phase',fallback=1) == 1 else self.world.agents[region].risk))
                self.world.setDynamics(risk,allocate,tree,codePtr=True)

                if self.config.getboolean('Actors','grievance') and \
                   self.config.getint('Actors','grievance_delta') > 0:
                    logEdge('Actor\'s home','Actor\'s grievance','often','An actor\'s grievance will decrease (increase) if aid goes (does not go) to his/her home region')
                    #//GT: edge 61; from 19; to 26; 1 of 1; next 9 lines
                    logEdge('System-allocate-Region','Actor\'s grievance','often','An actor\'s grievance will decrease (increase) if aid goes (does not go) to his/her home region')
                    #//GT: edge 62; from 43; to 26; 1 of 1; next 7 lines
                    for actor in population:
                        grievance = stateKey(actor,'grievance')
                        if self.world.agents[actor].demographics['home'] == region:
                            tree = makeTree(approachMatrix(grievance,delta,0.))
                        else:
                            tree = makeTree(approachMatrix(grievance,delta,1.))
                        self.world.setDynamics(grievance,allocate,tree,codePtr=True)

        self.setNullGrievance(population)

    def setNullGrievance(self,population):
        """
        Used in hypothetical situations when TA2 wants to test what happens when the System does nothing
        """
        regions = self.getPopulated(population)
        delta,scale = self.grievanceDelta(regions)
        # Null
        if self.config.getboolean('Actors','grievance') and \
           self.config.getint('Actors','grievance_delta') > 0:
           # Not doing anything same as giving aid to region other than mine
           for actor in population:
                grievance = stateKey(actor,'grievance')
                tree = makeTree(approachMatrix(grievance,delta,1.))
                try:
                    action = self.nop
                except AttributeError:
                    for action in self.actions:
                        if action['verb'] == 'doNothing':
                            self.nop = action
                            break
                    else:
                        raise ValueError('Unable to find nop for System')
                self.world.setDynamics(grievance,self.nop,tree,codePtr=True)
        
    def decide(self,state=None,horizon=None,others=None,model=None,selection=None,actions=None,
               debug={}):
        if state is None:
            state = self.world.state
        if actions is None:
            actions = self.getActions(state)
        if len(actions) == 1:
            tree = makeTree(setToConstantMatrix(stateKey(self.name,ACTION),next(iter(actions))))
            return {'policy': tree.desymbolize(self.world.symbols)}
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
            logEdge('Region\'s risk','System-allocate-Region','often','Aid target determined by allocating resources to region with highest risk level')
            #//GT: edge 86; from 1; to 43; 1 of 1; next 26 lines
            logEdge('System\'s ethnicBias','System-allocate-Region','often','System\'s bias affects region chosen to receive aid')
            #//GT: edge 87; from 44; to 43; 1 of 1; next 24 lines
            logEdge('System\'s religiousBias','System-allocate-Region','often','System\'s bias affects region chosen to receive aid')
            #//GT: edge 88; from 45; to 43; 1 of 1; next 22 lines
            logEdge('Actor\'s ethnicGroup','System-allocate-Region','often','Ethnic demographics affect region chosen to receive aid')
            #//GT: edge 89; from 15; to 43; 1 of 1; next 20 lines
            logEdge('Actor\'s religion','System-allocate-Region','often','Religious demographics affect region chosen to receive aid')
            #//GT: edge 90; from 16; to 43; 1 of 1; next 18 lines
            population = {name: [a.name for a in self.world.agents.values() if isinstance(a,Actor) and a.demographics['home'] == name]
                          for name in self.world.agents if isinstance(self.world.agents[name],Region)}
            weights = {}
            for region,actors in population.items():
                if self.config.getint('Simulation','phase',fallback=1) < 3:
                    weights[region] = 1
                else:
                    weights[region] = len(actors)
                    for name in actors:
                        demos = self.world.agents[name].demographics
                        key = stateKey(self.name,'ethnicBias')
                        if key in state and demos['ethnicGroup'] == 'majority':
                            weights[region] += float(self.world.getFeature(key,state))
                        if key in state and demos['religion'] == 'majority':
                            weights[region] += float(self.world.getFeature(key,state))
            risks = [(float(state[stateKey(a['object'],'risk')])*weights[a['object']],a)
                     for a in actions if a['object'] is not None and stateKey(a['object'],'risk') in state]
            choice = max(risks)

        tree = makeTree(setToConstantMatrix(stateKey(self.name,ACTION),choice[1]))
        return {'policy': tree.desymbolize(self.world.symbols)}
            
    def election(self,voters):
        logEdge('Actor\'s grievance','System\'s ethnicBias','sometimes','A new government is chosen during an offseason "election"')
        #//GT: edge 86; from 27; to 46; 1 of 1; next 30 lines
        logEdge('Actor\'s grievance','System\'s religiousBias','sometimes','A new government is chosen during an offseason "election"')
        #//GT: edge 87; from 27; to 47; 1 of 1; next 28 lines
        logEdge('Actor\'s religion','System\'s ethnicBias','sometimes','A new government is chosen during an offseason "election"')
        #//GT: edge 88; from 16; to 46; 1 of 1; next 26 lines
        logEdge('Actor\'s ethnicGroup','System\'s ethnicBias','sometimes','A new government is chosen during an offseason "election"')
        #//GT: edge 89; from 15; to 46; 1 of 1; next 24 lines
        ethnicWeight = 0
        religiousWeight = 0
        for agent in voters:
            if agent.demographics['ethnicGroup'] == 'majority':
                ethnicWeight += agent.getState('grievance').expectation()
            else:
                ethnicWeight -= agent.getState('grievance').expectation()
            if agent.demographics['religion'] == 'majority':
                religiousWeight += agent.getState('grievance').expectation()
            elif agent.demographics['religion'] == 'minority':
                religiousWeight -= agent.getState('grievance').expectation()
        ethnicWeight /= len(voters)
        religiousWeight /= len(voters)
        self.ethnicBias += ethnicWeight / len(voters)
        self.religiousBias += religiousWeight / len(voters)
        logging.info('Election')
        logging.info('New ethnic bias: %f' % (self.ethnicBias))
        logging.info('New religious bias: %f' % (self.religiousBias))
        self.setState('ethnicBias',self.ethnicBias)
        self.setState('religiousBias',self.religiousBias)
        for actor in voters:
            for beliefs in actor.getBelief().values():
                self.setState('ethnicBias',self.ethnicBias,beliefs)
                self.setState('religiousBias',self.religiousBias,beliefs)

