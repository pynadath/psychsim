from psychsim.pwl import *
from psychsim.agent import Agent
        
from data import likert

from region import Region

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
                actBadResources = self.addAction({'verb': 'takeResources'},
                                                 tree.desymbolize(world.symbols))
        doNothing = self.addAction({'verb': 'doNothing'})

    def potentialMembers(self,agents,weights=None):
        assert len(self.models) == 1,'Define potential members before adding multiple models of group %s' % (self.name)
        model = self.models.keys()[0]
        size = stateKey(self.name,'size')
        for name in agents:
            agent = self.world.agents[name]
            member = self.world.defineRelation(name,self.name,'memberOf',bool)
            # Join a group
            self.world.setFeature(member,False)
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
            self.world.setFeature(member,False)
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
                agent.setReward(tree,self.config.getfloat('Actors','attachment_r'))
        # Define reward function for this group as weighted sum of members
        if weights is None:
            weights = {a: 1. for a in agents}
        for name,weight in weights.items():
            self.setReward(name,weight,model)
