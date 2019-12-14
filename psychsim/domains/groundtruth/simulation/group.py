import random

from psychsim.pwl import *
from psychsim.action import *
from psychsim.agent import Agent
        
from psychsim.domains.groundtruth.simulation.data import likert,logNode,logEdge
from psychsim.domains.groundtruth.simulation.region import Region

class Group(Agent):
    def __init__(self,name,world,config):
        Agent.__init__(self,'Group%s' % (name))
        world.addAgent(self)

        self.config = config
        if world.diagram and name == 'Region01':
            world.diagram.setColor(self.name,'yellowgreen')
            
        regions = sorted([name for name in self.world.agents
                          if isinstance(self.world.agents[name],Region)])
        self.setAttribute('static',True)

        # size = world.defineState(self.name,'size',int,codePtr=True)
        # self.setState('size',0)
        
        if config.getboolean('Groups','prorisk'):
            logNode('Group-decreaseRisk','Action choice of performing a prosocial action as a group','Boolean')
            #//GT: node 48; 1 of 1; next 5 lines
            if name in regions:
                actGoodRisk = self.addAction({'verb': 'decreaseRisk','object': name},codePtr=True)
            else:
                actGoodRisk = self.addAction({'verb': 'decreaseRisk'},codePtr=True)
                name ='Region01'

        if config.getboolean('Groups','proresources'):
            logNode('Group-giveResources','Action choice of increasing group resources','Boolean')
            #
#            tree = makeTree({'if': thresholdRow(size,1.5),True: True, False: False})
            if name in regions:
                actGoodResources = self.addAction({'verb': 'giveResources','object': name},
                                                  codePtr=True)

        if config.getboolean('Groups','antirisk'):
            logNode('Group-increaseRisk','Action choice of performing antisocial risk action as a group','Boolean')
            #
#            tree = makeTree({'if': thresholdRow(size,1.5),True: True, False: False})
            if name in regions:
                actBadRisk = self.addAction({'verb': 'increaseRisk','object': name},codePtr=True)
            else:
                actBadRisk = self.addAction({'verb': 'increaseRisk'},codePtr=True)

        if config.getboolean('Groups','antiresources'):
            logNode('Group-takeResources','Action choice of performing antisocial resource action as a group','Boolean')
            #
#            tree = makeTree({'if': thresholdRow(size,1.5),True: True, False: False})
            if name in regions:
                actBadResources = self.addAction({'verb': 'takeResources','object': name},
                                                 codePtr=True)
            else:
                actBadResources = self.addAction({'verb': 'takeResources'},
                                                 codePtr=True)

        if config.getboolean('Groups','evacuate'):
            # Evacuate city altogether
            logNode('Group-evacuate','Action choice of evacuating as a group','Boolean')
            #//GT: node 49; 1 of 1; next 4 lines
            tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                             True: False, False: True})
            actEvacuate = self.addAction({'verb': 'evacuate'},tree.desymbolize(world.symbols),
                                         codePtr=True)

#            goHome = self.addAction({'verb': 'returnHome'},codePtr=True)

        logNode('Group-noDecision','Group chose not to perform any joint action','Boolean')
        #//GT: node 49; 1 of 1; next 1 lines
        self.nop = self.addAction({'verb': 'noDecision'},codePtr=True)

        logNode('Group\'s horizon','Number of steps into future that group uses to evaluate candidate action choices','Positive integer')
        #//GT: node 50; 1 of 1; next 1 lines
        self.setAttribute('horizon',config.getint('Groups','horizon'))

        self.potentials = None
        # Belief aggregation
        logNode('Group\'s beliefAggregation','Degree to which group\'s aggregate beliefs are biased toward those of its more optimistic/pessimistic members',
            'String: "mean" / "max" / "min"')
        #//GT: node 51; 1 of 1; next 16 lines
        aggregators = ['mean']
        weights = [5]
        value = config.getint('Groups','belief_max')
        if value:
            aggregators.append('max')
            weights.append(value)
            weights[0] -= value
        value = config.getint('Groups','belief_min')
        if value:
            aggregators.append('min')
            weights.append(value)
            weights[0] -= value
        if len(aggregators) > 1:
            self.aggregator = random.choices(aggregators,weights)[0]
        else:
            self.aggregator = aggregators[0]

    def potentialMembers(self,agents,weights=None,membership=0):
        assert len(self.models) == 1,'Define potential members before adding multiple models of group %s' % (self.name)
        self.potentials = agents
        model = next(iter(self.models.keys()))
#        size = stateKey(self.name,'size')
        count = 0
        for name in agents:
            logNode('Actor memberOf Group','Group membership relationship','Boolean')
            #//GT: node 52; 1 of 1; next 10 lines
            agent = self.world.agents[name]
            member = self.world.defineRelation(name,self.name,'memberOf',bool,codePtr=True)
            # Join a group
            if membership == 0:
                self.world.setFeature(member,False)
            else:
                inGroup = random.random() < likert[5][membership-1]
                self.world.setFeature(member,inGroup)
                if inGroup:
                    count += 1

            logNode('Actor-join-Group','Action choice of joining a group','Boolean')
            #//GT: node 53; 1 of 1; next 5 lines
            tree = {'if': trueRow(member),True: False, False: True}
            if self.config.getint('Simulation','phase',fallback=1) < 3:
                tree = {'if': trueRow(stateKey(name,'alive')),True: tree,False: False}
            join = agent.addAction({'verb': 'join','object': self.name},
                                   makeTree(tree).desymbolize(self.world.symbols),codePtr=True)

            logEdge('Actor-join-Group','Actor memberOf Group','sometimes','Joining a group makes one a member of it')
            #//GT: edge 61; from 53; to 52; 1 of 1; next 2 lines
            tree = makeTree(setTrueMatrix(member))
            self.world.setDynamics(member,join,tree,codePtr=True)

#            tree = makeTree(incrementMatrix(size,1))
#            self.world.setDynamics(size,join,tree,codePtr=True)

            # Leave a group
            logNode('Actor-leave-Group','Action choice of leaving a group','Boolean')
            #//GT: node 54; 1 of 1; next 5 lines
            tree = {'if': trueRow(member),True: True, False: False}
            if self.config.getint('Simulation','phase',fallback=1) < 3:
                tree = {'if': trueRow(stateKey(name,'alive')),True: tree,False: False}
            leave = agent.addAction({'verb': 'leave','object': self.name},
                                    makeTree(tree).desymbolize(self.world.symbols),codePtr=True)

            logEdge('Actor-leave-Group','Actor memberOf Group','sometimes','Leaving a group makes one no longer a member of it')
            #//GT: edge 62; from 54; to 52; 1 of 1; next 2 lines
            tree = makeTree(setFalseMatrix(member))
            self.world.setDynamics(member,leave,tree,codePtr=True)

#            tree = makeTree(incrementMatrix(size,-1))
#            self.world.setDynamics(size,leave,tree,codePtr=True)
            if self.config.getboolean('Actors','attachment'):
                # Reward associated with being a member
                logEdge('Actor\'s attachment','Actor\'s Expected Reward','sometimes','Attachment style can make person happier/sadder to be in a group')
                #
                logEdge('Actor memberOf Group','Actor\'s Expected Reward','sometimes','Attachment style can make person happier/sadder to be in a group')
                #
                attachment = stateKey(name,'attachment')
                R = rewardKey(name)
                tree = makeTree({'if': thresholdRow(stateKey(name,'risk'),
                                                    likert[5][self.config.getint('Actors','attachment_threshold')]),
                                 True: {'if': equalRow(attachment,'anxious'),
                                        True: setToFeatureMatrix(R,member,1.),
                                        False: {'if': equalRow(attachment,'avoidant'),
                                                True: setToFeatureMatrix(R,member,-1.),
                                                False: setToConstantMatrix(R,0.)}},
                                 False: setToConstantMatrix(R,0.)})
                agent.setReward(tree,likert[5][self.config.getint('Actors','attachment_r')-1])

            logNode('Group\'s magnification','Magnification of effect of joint action by Group (as a function of size of the group)','Real in [0-1]')
            #//GT: node 55; 1 of 1; next 1 lines
            magnify = self.config.getint('Groups','magnification')

            if self.config.getboolean('Groups','prorisk') and magnify > 0:
                for action in self.actions:
                    if action['verb'] == 'decreaseRisk':
                        for lonely in agent.actions:
                            if lonely['verb'] == action['verb'] and \
                               (action.get('object') is None or \
                                lonely['object'] == action['object']):
                                # Magnify effect of prosocial behavior
                                logEdge('Group-decreaseRisk-Region','Region\'s risk','sometimes','Performing prosocial behavior reduces the risk in the target region')
                                #//GT: edge 63; from 56; to 1; 1 of 1; next 15 lines
                                logEdge('Actor memberOf Group','Region\'s risk','sometimes','Performing prosocial behavior as a group reduces the risk in the target region more')
                                #//GT: edge 64; from 52; to 1; 1 of 1; next 13 lines
                                logEdge('Group\'s magnification','Region\'s risk','sometimes','Performing prosocial behavior as a group reduces the risk in the target region more')
                                #//GT: edge 65; from 55; to 1; 1 of 1; next 11 lines
                                risk = stateKey(lonely['object'],'risk')
                                tree = self.world.dynamics[risk][lonely]
                                assert tree.isLeaf(),'Unable to magnify branching trees'
                                weight = tree.getLeaf()[makeFuture(risk)][risk]
                                newWeight = (1.-weight)*(1.+likert[5][magnify-1])
                                newTree = {'if': trueRow(binaryKey(name,self.name,'memberOf')),
                                            True: {'if': equalRow(stateKey(self.name,ACTION),action),
                                                True: approachMatrix(risk,newWeight,self.world.agents[lonely['object']].risk),
                                                False: copy.deepcopy(tree)},
                                            False: tree}
                                self.world.setDynamics(risk,lonely,makeTree(newTree))

                                # Minimize cost of prosocial behavior
                                risk = stateKey(name,'risk')
                                try:
                                    tree = self.world.dynamics[risk][lonely]
                                    assert tree.isLeaf(),'Unable to magnify branching trees'
                                    weight = tree.getLeaf()[makeFuture(risk)][risk]
                                    newWeight = (1.-weight)*(1.-likert[5][magnify-1])
                                    newTree = {'if': trueRow(binaryKey(name,self.name,'memberOf')),
                                               True: {'if': equalRow(stateKey(self.name,ACTION),
                                                                     action),
                                                      True: approachMatrix(risk,newWeight,1.),
                                                      False: copy.deepcopy(tree)},
                                               False: tree}
                                    self.world.setDynamics(risk,lonely,makeTree(newTree))
                                except KeyError:
                                    pass
                                break
                        else:
                            raise ValueError('Member %s of %s has no equivalent of %s' %
                                             (name,self.name,action))
                        break
                else:
                    raise ValueError('Group %s has no prosocial action' % (self.name))

        # Define reward function for this group as weighted sum of members
        if weights is None:
            weights = {a: 1. for a in agents}
#        for name,weight in weights.items():
#            agent = self.world.agents[name]
#            R = agent.getReward(self.world.getModel(name,self.world.state).first())
#            assert isinstance(R,KeyedTree)
#            self.setReward(R,weights[name],model)
#        self.setState('size',count)

    def members(self,state=None):
        if state is None:
            state = self.world.state
        return [agent for agent in self.potentials \
                if self.world.getFeature(binaryKey(agent,self.name,'memberOf')).first()]

    def reward(self,state=None,model=None,recurse=False):
        if state is None:
            state = self.world.state
        if model is None:
            model = self.world.getModel(self.name,state)
        total = 0.
        for name in self.members(state):
            agent = self.world.agents[name]
            ER = agent.reward(state)  
            total += ER
        return total
    
    def getBelief(self,state=None,model=None):
        logNode('GroupBeliefOfRegion\'s risk','Belief about risk level of home region','Probability Distribution over reals in [0-1]')
        #//GT: node 58; 1 of 1; next 85 lines
        logEdge('Actor memberOf Group','GroupBeliefOfRegion\'s risk','often','Group\'s belief is a function of its members\' beliefs')
        #//GT: edge 66; from 52; to 58; 1 of 1; next 83 lines
        logEdge('ActorBeliefOfRegion\'s risk','GroupBeliefOfRegion\'s risk','often','Group\'s belief is a function of its members\' beliefs')
        #//GT: edge 67; from 12; to 58; 1 of 1; next 81 lines
        logEdge('Group\'s beliefAggregation','GroupBeliefOfRegion\'s risk','often','Group\'s belief is a function of its members\' beliefs')
        #//GT: edge 68; from 51; to 58; 1 of 1; next 79 lines
        if state is None:
            state = self.world.state
        if model is None:
            model = self.world.getModel(self.name,state)
        members = self.members(state)
        # Extract member beliefs
        models = {}
        for name in members:
            if modelKey(name) in state:
                models[name] = self.world.getModel(name,state)
            else:
                models[name] = self.world.getModel(name,self.world.state)
            assert len(models[name]) == 1
            models[name] = models[name].first()
        beliefs = {name: self.world.agents[name].getBelief(state,models[name])
                   for name in members}
        belief = VectorDistributionSet()
        for key in [turnKey(name) for name in [self.name,'Nature','System']]+[turnKey(name) for name in members]+\
            [actionKey(name) for name in [self.name,'Nature','System']]+[actionKey(name) for name in members]+\
            [binaryKey(name,self.name,'memberOf') for name in members]+[modelKey(name) for name in members]:
            self.world.setFeature(key,self.world.getFeature(key,state),belief)
        uncertain = {stateKey('Nature','category'): None,
            stateKey(self.name[5:],'risk'): None}
        for subbelief in beliefs.values():
            for key in subbelief.keys():
                if isStateKey(key) and state2feature(key) == 'shelterRisk':
                    uncertain[key] = None
        for name in members:
            for key in {stateKey(name,'risk'),stateKey(name,'location'),stateKey(name,'employed')}|\
                self.world.agents[name].getReward(models[name]).getKeysIn()-{CONSTANT}:
                self.world.setFeature(key,self.world.getFeature(key,beliefs[name]),belief)
            for feature in ['phase','days','location']:
                subbelief = self.world.getState('Nature',feature,beliefs[name])
                if stateKey('Nature',feature) in belief:
                    # Everyone should agree on this feature
                    if self.world.getState('Nature',feature,belief) != subbelief:
                        print(feature)
                        print(subbelief)
                        print(self.world.getState('Nature',feature,belief))
                else:
                    self.world.setState('Nature',feature,subbelief,belief)

            for key in uncertain:
                subbelief = self.world.getFeature(key,beliefs[name])
                if uncertain[key] is None:
                    uncertain[key] = {value: subbelief[value] for value in subbelief.domain()}
                elif self.aggregator == 'max':
                    if subbelief.expectation() > belief.expectation():
                        uncertain[key] = subbelief
                elif self.aggregator == 'min':
                    if subbelief.expectation() < belief.expectation():
                        uncertain[key] = subbelief
                else:
                    assert self.aggregator == 'mean'
                    uncertain[key].update({value: subbelief[value]+uncertain[key].get(value,0.) for value in subbelief.domain()})
        if self.aggregator == 'mean':
            for key in uncertain:
                uncertain[key] = Distribution({value: prob / len(members) for value,prob in uncertain[key].items()})
        for key,dist in uncertain.items():
            self.world.setFeature(key,dist,belief)
        return belief

    def decide(self,state=None,horizon=None,others=None,model=None,selection=None,actions=None,
               debug={}):
        if state is None:
            state = self.world.state
        if actions is None:
            actions = self.getActions(state)
        members = self.members(state)
        if len(members) < 2:
            for action in actions:
                if action['verb'] == 'noDecision':
                    return{'action': action}
        if model is None:
            model = self.world.getModel(self.name,state)
            assert len(model) == 1,'Currently unable to decide under uncertain models'
            model = model.first()
        horizon = self.getAttribute('horizon',model)
        V = {}
        risk = {}
        risks = {}
        health = {}
        belief = self.getBelief(state,model)
        order = [{k for k in keySet if k in belief} for keySet in self.world.dependency.getEvaluation()]
        order = [keySet for keySet in order if keySet]
        for action in actions:
            # Project effect of this action
            assert len(action) == 1
            verb = 'stayInLocation' if action['verb'] == 'noDecision' else action['verb']
            V[action] = 0.
            # Determine what each member is doing
            evolve = ActionSet(Action({'subject': 'Nature','verb': 'evolve'}))
            joint = {}
            for name in members:
                actor = self.world.agents[name]
                if action['verb'] == 'noDecision':
                    joint[name] = actor.nop
                else:
                    for joint[name] in actor.getActions(state):
                        if joint[name]['verb'] == verb:
                            break
                    else:
                        # Must be somewhere where the group action is illegal
                        joint[name] = actor.nop
            current = copy.deepcopy(belief)
            for t in range(horizon):
                self.world.step({self.name: action},current,keySubset=belief.keys(),updateBeliefs=False)
                self.world.step(joint,current,keySubset=belief.keys(),updateBeliefs=False)
                self.world.step({'System': self.world.agents['System'].nop},current,keySubset=belief.keys(),updateBeliefs=False)
                self.world.step({'Nature': evolve},current,keySubset=belief.keys(),updateBeliefs=False)
            assert model is not None
            V[action] = self.reward(current,model)
        best = None
        for action,value in V.items():
            if best is None or value > best[1]:
                best = action,value
        actions = sorted(risks.keys())
        return {'action': best[0],'V': V}

