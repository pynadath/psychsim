"""
Class definition for representation of dependency structure among all variables in a PsychSim scenario
"""
from psychsim.pwl.keys import *
from psychsim.action import ActionSet

class DependencyGraph(dict):
    """
    Representation of dependency structure among PsychSim variables
    """
    def __init__(self,myworld=None):
        self.world = myworld
        self.clear()
        dict.__init__(self)

    def clear(self):
        self.root = None
        self.layers = None
        self.evaluation = None
        dict.clear(self)

    def getLayers(self):
        if self.layers is None:
            self.computeLineage()
        return self.layers

    def getEvaluation(self):
        if self.evaluation is None:
            self.computeEvaluation()
        return self.evaluation

    def getRoot(self):
        if self.root is None:
            self.computeLineage()
        return self.root

    def deleteKeys(self,toDelete):
        self.evaluation = [keySet-toDelete for keySet in self.evaluation if keySet-toDelete]
        
    def __getitem__(self,key):
        if len(self) == 0:
            self.computeGraph()
        return dict.__getitem__(self,key)

    def computeGraph(self,agents=None,state=None,belief=False):
        # Process the unary state features
        if agents is None:
            agents = sorted(self.world.agents.keys())
            agents.append(WORLD)
        if state is None:
            state = self.world.state
        for agent in agents:
            if agent in self.world.locals:
                variables = self.world.locals[agent]
                for feature in variables.keys():
                    key = stateKey(agent,feature)
                    if key in state:
                        self[key] = {'agent': agent,'type': 'state pre',
                                     'children': set(),'parents': set()}
                        self[makeFuture(key)] = {'agent': agent,'type': 'state post',
                                                 'children': set(),'parents': set()}
        # Process the binary state features
        for relation,table in self.world.relations.items():
            for key,entry in table.items():
                if key in state and entry['subject'] in agents and entry['object'] in agents:
                    self[key] = {'agent': entry['subject'],
                                 'type': 'state pre',
                                 'children': set(),
                                 'parents': set()}
                    self[makeFuture(key)] = {'agent': entry['subject'],
                                             'type': 'state post',
                                             'children': set(),
                                             'parents': set()}
        for name in agents:
            if name != WORLD:
                # Create the agent reward node
                agent = self.world.agents[name]
                R = agent.getReward()
                if R:
                    if {reward for reward in R.values()} != {None}:
                        self[name] = {'agent': name,
                                      'type': 'utility',
                                      'parents': set(),
                                      'children': set()}
                # Process the agent actions
                for action in agent.actions:
                    action = ActionSet([a.root() for a in action])
                    if not action in self:
                        self[action] = {'agent': name,
                                        'type': 'action',
                                        'parents': set(),
                                        'children': set()}
        # Create links from dynamics
        for key,dynamics in self.world.dynamics.items():
            if not isinstance(key,str):
                continue
            if isTurnKey(key):
                continue
            if isStateKey(key) and not state2agent(key) in agents:
                continue
            if isBinaryKey(key) and not key2relation(key)['subject'] in agents and \
               not key2relation(key)['object'] in agents:
                continue
            if not key in self:
                continue
#            assert self.has_key(key),'Graph has not accounted for key: %s' % (key)
            if isinstance(dynamics,bool):
                continue
            for action,tree in dynamics.items():
                if not action is True and action['subject'] in agents:
                    # Link between action to this feature
                    if action in self:
                        # assert self.has_key(action),'Graph has not accounted for action: %s' % (action)
                        dict.__getitem__(self,makeFuture(key))['parents'].add(action)
                        dict.__getitem__(self,action)['children'].add(makeFuture(key))
                # Link between dynamics variables and this feature
                for parent in tree.getKeysIn() - set([CONSTANT]):
                    if (state2agent(parent) == WORLD or state2agent(parent) in agents) and \
                       parent in self:
                        dict.__getitem__(self,makeFuture(key))['parents'].add(parent)
                        dict.__getitem__(self,parent)['children'].add(makeFuture(key))
        for name in agents:
            if name in self:
                agent = self.world.agents[name]
                # Create links from reward
                model = '%s0' % (agent.name)
                R = agent.getReward(model)
                for parent in R.getKeysIn() - set([CONSTANT]):
                    if isStateKey(parent) and not state2agent(parent) in agents:
                        continue
                    if parent in self:
                        # Link between variable and agent utility
                        dict.__getitem__(self,name)['parents'].add(makeFuture(parent))
                        dict.__getitem__(self,makeFuture(parent))['children'].add(name)
                # Create links from legality
                for action,tree in agent.legal.items():
                    action = ActionSet([a.root() for a in action])
                    for parent in tree.getKeysIn() - set([CONSTANT]):
                        if isStateKey(parent) and not state2agent(parent) in agents:
                            continue
                        if action in self and parent in self:
                            # Link between prerequisite variable and action
                            dict.__getitem__(self,action)['parents'].add(parent)
                            dict.__getitem__(self,parent)['children'].add(action)

    def items(self):
        if len(self) == 0:
            self.computeGraph()
        return dict.items(self)

    def keys(self):
        if len(self) == 0:
            self.computeGraph()
        return dict.keys(self)

    def values(self):
        if len(self) == 0:
            self.computeGraph()
        return dict.values(self)

    def computeLineage(self):
        """
        Add ancestors to everybody, also computes layers
        """
        self.root = set()
        self.layers = []
        for key,node in self.items():
            node['ancestors'] = set(node['parents'])
            if len(node['parents']) == 0:
                # Root node
                self.root.add(key)
                node['level'] = 0
        self.layers = [self.root]
        level = 0
        while sum(map(len,self.layers)) < len(self):
            layer = set()
            for key in self.layers[level]:
                for child in self[key]['children']:
                    # Update ancestors
                    self[child]['ancestors'] |= self[key]['ancestors']
                    if not child in layer:
                        # Check whether eligible for the new layer
                        for parent in self[child]['parents']:
                            if not 'level' in self[parent] or self[parent]['level'] > level:
                                # Ineligible to be in this layer
                                break
                        else:
                            # All parents are in earlier layers
                            layer.add(child)
                            self[child]['level'] = level + 1
            # Add new layer
            self.layers.append(layer)
            level += 1

    def computeEvaluation(self):
        """
        Determine the order in which to compute new values for state features
        """
        self.getLayers()
        self.evaluation = []
        # for key in self.world.variables:
        #     while len(self.evaluation) <= self[key]['level']:
        #         self.evaluation.append(set())
        #     self.evaluation[self[key]['level']].add(makePresent(key))
            
        for agent,variables in self.world.locals.items():
            for feature in variables.keys():
                key = stateKey(agent,feature,True)
                while len(self.evaluation) <= self[key]['level']:
                    self.evaluation.append(set())
                self.evaluation[self[key]['level']].add(makePresent(key))
        for relation,variables in self.world.relations.items():
            for key,table in variables.items():
                while len(self.evaluation) <= self[key]['level']:
                    self.evaluation.append(set())
                self.evaluation[self[key]['level']].add(makePresent(key))
