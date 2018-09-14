import random

from psychsim.pwl import *
from psychsim.action import *
from psychsim.agent import Agent
        
from psychsim.domains.groundtruth.data import likert

from psychsim.domains.groundtruth.region import Region

class Group(Agent):
    def __init__(self,name,world,config):
        Agent.__init__(self,'Group%s' % (name))
        world.addAgent(self)

        self.config = config
        if name == 'Region01':
            world.diagram.setColor(self.name,'yellowgreen')
            
        regions = sorted([name for name in self.world.agents
                          if isinstance(self.world.agents[name],Region)])
        self.setAttribute('static',True)

        size = world.defineState(self.name,'size',int)
        self.setState('size',0)
        
        if config.getboolean('Groups','prorisk'):
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            if name in regions:
                actGoodRisk = self.addAction({'verb': 'decreaseRisk','object': name},
                                             tree.desymbolize(world.symbols))
            else:
                actGoodRisk = self.addAction({'verb': 'decreaseRisk'},
                                             tree.desymbolize(world.symbols))
        if config.getboolean('Groups','proresources'):
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            if name in regions:
                actGoodResources = self.addAction({'verb': 'giveResources','object': name},
                                         tree.desymbolize(world.symbols))
                actGoodResources = self.addAction({'verb': 'giveResources'},
                                                  tree.desymbolize(world.symbols))
        if config.getboolean('Groups','antirisk'):
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            if name in regions:
                actBadRisk = self.addAction({'verb': 'increaseRisk','object': name},
                                            tree.desymbolize(world.symbols))
            else:
                actBadRisk = self.addAction({'verb': 'increaseRisk'},
                                            tree.desymbolize(world.symbols))
        if config.getboolean('Groups','antiresources'):
            tree = makeTree({'if': thresholdRow(size,0.5),True: True, False: False})
            if name in regions:
                actBadResources = self.addAction({'verb': 'takeResources','object': name},
                                                 tree.desymbolize(world.symbols))
            else:
                actBadResources = self.addAction({'verb': 'takeResources'},
                                                 tree.desymbolize(world.symbols))
        if config.getboolean('Groups','evacuate'):
            # Evacuate city altogether
            tree = makeTree({'if': equalRow(stateKey('Nature','phase'),'none'),
                             True: False, False: True})
            actEvacuate = self.addAction({'verb': 'evacuate'},tree.desymbolize(world.symbols))
            goHome = self.addAction({'verb': 'returnHome'})

        self.nop = self.addAction({'verb': 'noDecision'})
        self.setAttribute('horizon',config.getint('Groups','horizon'))
        self.potentials = None

    def potentialMembers(self,agents,weights=None,membership=0):
        assert len(self.models) == 1,'Define potential members before adding multiple models of group %s' % (self.name)
        self.potentials = agents
        model = next(iter(self.models.keys()))
        size = stateKey(self.name,'size')
        count = 0
        for name in agents:
            agent = self.world.agents[name]
            member = self.world.defineRelation(name,self.name,'memberOf',bool)
            # Join a group
            if membership == 0:
                self.world.setFeature(member,False)
            else:
                inGroup = random.random() < likert[5][membership-1]
                self.world.setFeature(member,inGroup)
                if inGroup:
                    count += 1
                
            tree = makeTree({'if': trueRow(stateKey(name,'alive')),
                             True: {'if': trueRow(member),
                                    True: False, False: True},
                             False: False})
            join = agent.addAction({'verb': 'join','object': self.name},
                                   tree.desymbolize(self.world.symbols))
            tree = makeTree(setTrueMatrix(member))
            self.world.setDynamics(member,join,tree)
            tree = makeTree(incrementMatrix(size,1))
            self.world.setDynamics(size,join,tree)
            # Leave a group
            tree = makeTree({'if': trueRow(stateKey(name,'alive')),
                             True: {'if': trueRow(member),
                                    True: True, False: False},
                             False: False})
            leave = agent.addAction({'verb': 'leave','object': self.name},
                                    tree.desymbolize(self.world.symbols))
            tree = makeTree(setFalseMatrix(member))
            self.world.setDynamics(member,leave,tree)
            tree = makeTree(incrementMatrix(size,-1))
            self.world.setDynamics(size,leave,tree)
            if self.config.getboolean('Actors','attachment'):
                # Reward associated with being a member
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
        # Define reward function for this group as weighted sum of members
        if weights is None:
            weights = {a: 1. for a in agents}
        for name,weight in weights.items():
            self.setReward(name,weight,model)
        self.setState('size',count)

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
        if state is None:
            state = self.world.state
        if model is None:
            model = self.world.getModel(self.name,state)
        belief = None
        members = self.members(state)
        for name in members:
            agent = self.world.agents[name]
            subbelief = agent.getBelief(state)
            assert len(subbelief) == 1
            subbelief = next(iter(subbelief.values()))
            if belief is None:
                belief = copy.deepcopy(subbelief)
            else:
                for dist in subbelief.distributions.values():
                    existing = [key for key in dist.keys() if key in belief]
                    if existing:
                        substates = belief.substate(existing)
                        if len(substates) == 1:
                            substate = next(iter(substates))
                        else:
                            substate = belief.collapse(substates)
                        if dist != belief.distributions[substate]:
                            newDist = belief.distributions[substate].__class__()
                            for oldVec in belief.distributions[substate].domain():
                                prob = belief.distributions[substate][oldVec]
                                del belief.distributions[substate][oldVec]
                                for newVec in dist.domain():
                                    for key in existing:
                                        if oldVec[key] != newVec[key]:
                                            break
                                    else:
                                        result = oldVec.__class__(oldVec)
                                        for key in newVec:
                                            if not key in existing:
                                                result[key] = newVec[key]
                                        newDist.addProb(result,prob*dist[newVec])
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
            submodel = state[key]
            assert len(submodel) == 1,'Unable to form uncertain beliefs about members'
            belief.join(key,submodel)
        return belief

    def decide(self,state=None,horizon=None,others=None,model=None,selection=None,actions=None):
        if state is None:
            state = self.world.state
        if actions is None:
            actions = self.getActions(state)
        print(self.name)
        print(self.getState('size',state))
        if len(actions) == 1:
            # Probably nop because no one's joined
            result = {'action': next(iter(actions))}
            result['policy'] = makeTree(setToConstantMatrix(stateKey(self.name,ACTION),
                                                            result['action']))
            return result
        belief = self.getBelief(state,model)
        members = self.members(state)
        V = {}
        for action in actions:
            print(action)
            assert len(action) == 1
            joint = {}
            current = copy.deepcopy(belief)
            if action['verb'] == 'noDecision':
                print(self.reward(current))
            else:
                for name in members:
                    act = Action(next(iter(action)))
                    act['subject'] = name
                    joint[name] = ActionSet([act])
                self.world.step(joint,current,keySubset=belief.keys(),updateBeliefs=False)
            print(self.reward(current,model))
        raise RuntimeError
