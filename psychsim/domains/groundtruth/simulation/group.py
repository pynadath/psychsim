import random

from psychsim.pwl import *
from psychsim.action import *
from psychsim.agent import Agent
        
from psychsim.domains.groundtruth.simulation.data import likert
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
            #//GT: node 50; 1 of 1; next 5 lines
            if name in regions:
                actGoodRisk = self.addAction({'verb': 'decreaseRisk','object': name},codePtr=True)
            else:
                actGoodRisk = self.addAction({'verb': 'decreaseRisk'},codePtr=True)
                name ='Region01'
            # TODO: Scale by group size and amplification
            #//GT: edge 68; from 50; to 34; 1 of 1; next 4 lines
            key = stateKey(name,'risk')
            benefit = likert[5][config.getint('Actors','prorisk_benefit')-1]
            tree = makeTree(approachMatrix(key,benefit,self.world.agents[actGoodRisk['object']].risk))
            world.setDynamics(key,actGoodRisk,tree,codePtr=True)
        if config.getboolean('Groups','proresources'):
#            tree = makeTree({'if': thresholdRow(size,1.5),True: True, False: False})
            if name in regions:
                actGoodResources = self.addAction({'verb': 'giveResources','object': name},
                                                  codePtr=True)
        if config.getboolean('Groups','antirisk'):
#            tree = makeTree({'if': thresholdRow(size,1.5),True: True, False: False})
            if name in regions:
                actBadRisk = self.addAction({'verb': 'increaseRisk','object': name},codePtr=True)
            else:
                actBadRisk = self.addAction({'verb': 'increaseRisk'},codePtr=True)
        if config.getboolean('Groups','antiresources'):
#            tree = makeTree({'if': thresholdRow(size,1.5),True: True, False: False})
            if name in regions:
                actBadResources = self.addAction({'verb': 'takeResources','object': name},
                                                 codePtr=True)
            else:
                actBadResources = self.addAction({'verb': 'takeResources'},
                                                 codePtr=True)
        if config.getboolean('Groups','evacuate'):
            # Evacuate city altogether
            tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                             True: False, False: True})
            actEvacuate = self.addAction({'verb': 'evacuate'},tree.desymbolize(world.symbols),
                                         codePtr=True)
#            goHome = self.addAction({'verb': 'returnHome'},codePtr=True)

        self.nop = self.addAction({'verb': 'noDecision'},codePtr=True)
        #//GT: node 51; 1 of 1; next 1 line
        self.setAttribute('horizon',config.getint('Groups','horizon'))
        self.potentials = None
        # Belief aggregation
        #//GT: node 52; 1 of 1; next 16 lines
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
            #//GT: node 47; 1 of 1; next 10 lines
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
            #//GT: node 48; 1 of 1; next 6 lines
            tree = {'if': trueRow(member),True: False, False: True}
            if self.config.getint('Simulation','phase',fallback=1) < 3:
                tree = {'if': trueRow(stateKey(name,'alive')),True: tree,False: False}
            join = agent.addAction({'verb': 'join','object': self.name},
                                   makeTree(tree).desymbolize(self.world.symbols),codePtr=True)
            #//GT: edge 64; from 48; to 47; 1 of 1; next 2 lines
            tree = makeTree(setTrueMatrix(member))
            self.world.setDynamics(member,join,tree,codePtr=True)
#            tree = makeTree(incrementMatrix(size,1))
#            self.world.setDynamics(size,join,tree,codePtr=True)
            # Leave a group
            #//GT: node 49; 1 of 1; next 6 lines
            tree = {'if': trueRow(member),True: True, False: False}
            if self.config.getint('Simulation','phase',fallback=1) < 3:
                tree = {'if': trueRow(stateKey(name,'alive')),True: tree,False: False}
            leave = agent.addAction({'verb': 'leave','object': self.name},
                                    makeTree(tree).desymbolize(self.world.symbols),codePtr=True)
            #//GT: edge 65; from 49; to 47; 1 of 1; next 2 lines
            tree = makeTree(setFalseMatrix(member))
            self.world.setDynamics(member,leave,tree,codePtr=True)
#            tree = makeTree(incrementMatrix(size,-1))
#            self.world.setDynamics(size,leave,tree,codePtr=True)
            if self.config.getboolean('Actors','attachment'):
                # Reward associated with being a member
                #//GT: edge 66; from 40; to 11; 1 of 1; next 11 lines
                #//GT: edge 67; from 47; to 11; 1 of 1; next 11 lines
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
            magnify = self.config.getint('Groups','magnification')
            if self.config.getboolean('Groups','prorisk') and magnify > 0:
                for action in self.actions:
                    if action['verb'] == 'decreaseRisk':
                        for lonely in agent.actions:
                            if lonely['verb'] == action['verb'] and \
                               (action.get('object') is None or \
                                lonely['object'] == action['object']):
                                # Magnify effect of prosocial behavior
                                risk = stateKey(lonely['object'],'risk')
                                tree = self.world.dynamics[risk][lonely]
                                assert tree.isLeaf(),'Unable to magnify branching trees'
                                weight = tree.getLeaf()[makeFuture(risk)][risk]
                                newWeight = (1.-weight)*(1.+likert[5][magnify-1])
                                newTree = {'if': equalRow(stateKey(self.name,ACTION),action),
                                           True: approachMatrix(risk,newWeight,self.world.agents[lonely['object']].risk),
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
            total += agent.reward(state)
        return total
    
    def getBelief(self,state=None,model=None):
        #//GT: node 53; 1 of 1; next 88 lines
        #//GT: edge 69; from 47; to 53; 1 of 1; next 88 lines
        #//GT: edge 70; from 28; to 53; 1 of 1; next 88 lines
        #//GT: edge 71; from 52; to 53; 1 of 1; next 88 lines
        if state is None:
            state = self.world.state
        if model is None:
            model = self.world.getModel(self.name,state)
        members = self.members(state)
        models = {}
        for name in members:
            if modelKey(name) in state:
                models[name] = self.world.getModel(name,state)
            else:
                models[name] = self.world.getModel(name,self.world.state)
        beliefs = {name: self.world.agents[name].getBelief(state,models[name])
                   for name in members}
        belief = None
        if self.aggregator == 'max':
            pass
        elif self.aggregator == 'min':
            pass
        elif self.aggregator == 'mean':
            for name in members:
                assert len(beliefs[name]) == 1
                subbelief = next(iter(beliefs[name].values()))
                if belief is None:
                    belief = copy.deepcopy(subbelief)
                else:
                    for dist in subbelief.distributions.values():
                        existing = [key for key in dist.keys() if key in belief and key != CONSTANT]
                        if existing:
                            substates = belief.substate(existing)
                            if len(substates) == 1:
                                substate = next(iter(substates))
                            else:
                                if len(substates) == 0:
                                    print(existing)
                                    self.world.printState(belief)
                                    raise RuntimeError
                                substate = belief.collapse(substates,False)
                                if substate is None:
                                    print(substates)
                                    raise RuntimeError
                            if dist != belief.distributions[substate]:
                                newDist = belief.distributions[substate].__class__()
                                for oldVec in belief.distributions[substate].domain():
                                    prob = belief.distributions[substate][oldVec]
                                    del belief.distributions[substate][oldVec]
                                    found = False
                                    for newVec in dist.domain():
                                        for key in existing:
                                            if oldVec[key] != newVec[key]:
                                                if key == stateKey(self.name,'size'):
                                                    oldVec[key] = len(members)
                                                elif state2feature(key) == 'risk':
                                                    oldVec[key] = (oldVec[key]+newVec[key])/2.
                                                elif key == 'Nature\'s category':
                                                    oldVec[key] = (oldVec[key]+newVec[key])/2.
                                                else:
                                                    break
                                        else:
                                            found = True
                                            result = oldVec.__class__(oldVec)
                                            for key in newVec:
                                                if not key in existing:
                                                    result[key] = newVec[key]
                                                    belief.keyMap[key] = substate
                                            newDist.addProb(result,prob*dist[newVec])
                                    if not found:
                                        print(existing)
                                        print(sorted(list(belief.keys())))
                                        print('Old')
                                        print(belief.distributions[substate])
                                        print('New')
                                        print(dist)
                                        raise RuntimeError
                                belief.distributions[substate] = newDist
                        else:
                            substate = max(belief.keyMap.values())+1
                            belief.distributions[substate] = copy.deepcopy(dist)
                            for key in dist.keys():
                                if key != CONSTANT:
                                    belief.keyMap[key] = substate
        if belief is None:
            belief = state.__class__()
        for name in self.potentials:
            # Insert true models of members into group beliefs
            key = modelKey(name)
            submodel = self.world.state[key]
            assert len(submodel) == 1
            belief.join(key,submodel)
            # Insert true membership into group beliefs
            key = binaryKey(name,self.name,'memberOf')
            belief.join(key,self.world.state[key])
        assert turnKey(self.name) in belief.keys(),'%s\n%s' % (self.name,members)
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
        belief = self.getBelief(state,model)
        V = {}
        risk = {}
        risks = {}
        health = {}
        for action in actions:
            assert len(action) == 1
            joint = {self.name: action}
            current = copy.deepcopy(belief)
            dist = None
            for name in members:
                if action['verb'] == 'noDecision':
                    joint[name] = self.world.agents[name].nop
                else:
                    act = Action(next(iter(action)))
                    act['subject'] = name
                    joint[name] = ActionSet([act])
            # Use final value
            EV = self.value(current,action,model,horizon,joint,belief.keys(),
                            updateBeliefs=False,debug=debug)
            risk[action] = EV['__S__'][-1]['%s\'s risk' % (self.name[5:])].expectation()
            health[action] = {}
            risks[action] = {}
            for name in members:
                health[action][name] = EV['__S__'][-1]['%s\'s health' % (name)].expectation()
                risks[action][name] = EV['__S__'][-1]['%s\'s risk' % (name)].expectation()
            V[action] = EV['__ER__'][-1]
        best = None
        for action,value in V.items():
            if best is None or value > best[1]:
                best = action,value
        actions = sorted(risks.keys())
        return {'action': best[0],'V': V}

