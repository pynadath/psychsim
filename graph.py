"""
Class definition for representation of dependency structure among all variables in a PsychSim scenario
"""
import pwl
import world
from action import ActionSet

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

    def __getitem__(self,key):
        if len(self) == 0:
            self.computeGraph()
        return dict.__getitem__(self,key)

    def computeGraph(self):
        # Process the unary state features
        for agent,variables in self.world.locals.items():
            for feature in variables.keys():
                self[world.stateKey(agent,feature)] = {'agent': agent,
                                                       'type': 'state pre',
                                                       'children': set(),
                                                       'parents': set()}
                self[world.stateKey(agent,feature,True)] = {'agent': agent,
                                                            'type': 'state post',
                                                            'children': set(),
                                                            'parents': set()}
        # Process the binary state features
        for relation,table in self.world.relations.items():
            for key,entry in table.items():
                self[key] = {'agent': entry['subject'],
                             'type': 'state pre',
                             'children': set(),
                             'parents': set()}
                self[world.makeFuture(key)] = {'agent': entry['subject'],
                                         'type': 'state post',
                                         'children': set(),
                                         'parents': set()}
        for name,agent in self.world.agents.items():
            # Create the agent reward node
            if agent.getAttribute('R',True):
                self[name] = {'agent': name,
                              'type': 'utility',
                              'parents': set(),
                              'children': set()}
            # Process the agent actions
            for action in agent.actions:
                action = ActionSet([a.root() for a in action])
                if not self.has_key(action):
                    self[action] = {'agent': name,
                                    'type': 'action',
                                    'parents': set(),
                                    'children': set()}
        # Create links from dynamics
        for key,dynamics in self.world.dynamics.items():
            if world.isTurnKey(key):
                continue
            assert self.has_key(key),'Graph has not accounted for key: %s' % (key)
            if isinstance(dynamics,bool):
                continue
            for action,tree in dynamics.items():
                if not action is True:
                    # Link between action to this feature
                    assert self.has_key(action),'Graph has not accounted for action: %s' % (action)
                    dict.__getitem__(self,world.makeFuture(key))['parents'].add(action)
                    dict.__getitem__(self,action)['children'].add(world.makeFuture(key))
                # Link between dynamics variables and this feature
                for parent in tree.getKeysIn() - set([pwl.CONSTANT]):
                    dict.__getitem__(self,world.makeFuture(key))['parents'].add(parent)
                    dict.__getitem__(self,parent)['children'].add(world.makeFuture(key))
        for name,agent in self.world.agents.items():
            # Create links from reward
            if agent.models[True].has_key('R'):
                for R,weight in agent.models[True]['R'].items():
                    for parent in R.getKeysIn() - set([pwl.CONSTANT]):
                        # Link between variable and agent utility
                        dict.__getitem__(self,name)['parents'].add(world.makeFuture(parent))
                        dict.__getitem__(self,world.makeFuture(parent))['children'].add(name)
            # Create links from legality
            for action,tree in agent.legal.items():
                action = ActionSet([a.root() for a in action])
                for parent in tree.getKeysIn() - set([pwl.CONSTANT]):
                    # Link between prerequisite variable and action
                    assert self.has_key(action),'Graph has not accounted for action: %s' % (action)
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
                            if not self[parent].has_key('level') or self[parent]['level'] > level:
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
        for agent,variables in self.world.locals.items():
            for feature in variables.keys():
                key = world.stateKey(agent,feature,True)
                while len(self.evaluation) <= self[key]['level']:
                    self.evaluation.append(set())
                self.evaluation[self[key]['level']].add(world.makePresent(key))
