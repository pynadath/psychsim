import copy
import random
from xml.dom.minidom import Document,Node

from action import Action,ActionSet
from pwl import *
from probability import Distribution

class Agent:
    """
    @ivar world: the environment that this agent inhabits
    @type world: L{<psychsim.world.World>World}
    @ivar actions: the set of possible actions that the agent can choose from
    @type actions: {L{Action}}
    @ivar legal: a set of conditions under which certain action choices are allowed (default is that all actions are allowed at all times)
    @type legal: L{ActionSet}S{->}L{<psychsim.pwl.KeyedPlane>KeyedPlane}
    @ivar name: agent name
    @type name: str
    """
    def __init__(self,name):
        self.world = None
        self.subjective = None
        self.actions = set()
        self.legal = {}
        self.rewards = []
        self.models = {True: {'weights': [],'V': [], 'horizon': 1}}
        if isinstance(name,Document):
            self.parse(name.documentElement)
        elif isinstance(name,Node):
            self.parse(name)
        else:
            self.name = name

    def decide(self,vector,horizon=None,others=None,model=True,tiebreak=None):
        if horizon is None:
            horizon = self.models[model]['horizon']
        V = {}
        best = None
        for action in self.getActions(vector):
            V[action] = self.value(vector,action,horizon,others,model)
            if best is None:
                best = [action]
            elif V[action]['V'] == V[best[0]]['V']:
                best.append(action)
            elif V[action]['V'] > V[best[0]]['V']:
                best = [action]
        result = {'V*': V[best[0]]['V'],'V': V}
        if len(best) == 1:
            result['action'] = best[0]
        elif tiebreak == 'random':
            result['action'] = random.sample(best,1)[0]
        elif tiebreak == 'distribution':
            raise NotImplementedError,'Currently unable to return distribution over actions.'
        else:
            best.sort()
            result['action'] = best[0]
        return result

    def getActions(self,vector):
        """
        @return: the set of possible actions to choose from in the given state vector
        @rtype: {L{ActionSet}}
        """
        if len(self.legal) == 0:
            # No restrictions on legal actions, so take a shortcut
            return self.actions
        # Otherwise, filter out illegal actions
        result = set()
        for action in self.actions:
            try:
                tree = self.legal[action]
            except KeyError:
                # No condition on this action's legality => legal
                result.add(action)
                continue
            # Must satisfy all conditions
            if tree[vector]:
                result.add(action)
        return result
                
    def value(self,vector,action=None,horizon=None,others=None,model=True):
        if horizon is None:
            horizon = self.models[model]['horizon']
        R = self.reward(vector,model)
        result = {'V': R,
                  'old': vector,
                  'horizon': horizon,
                  'projection': []}
        if horizon > 0:
            # Perform action
            turn = copy.copy(others)
            if action:
                turn[self.name] = action
            outcome = self.world.stepFromState(vector,turn,True,horizon)
            if isinstance(outcome['new'],Distribution):
                # Uncertain outcomes
                for newVector in outcome['new'].domain():
                    entry = copy.copy(outcome)
                    entry['probability'] = outcome['new'][newVector]
                    Vrest = self.value(newVector,None,horizon-1,{},model)
                    entry.update(Vrest)
                    result['V'] += entry['probability']*entry['V']
                    result['projection'].append(entry)
            else:
                # Deterministic outcome
                Vrest = self.value(outcome['new'],None,horizon-1,{},model)
                outcome.update(Vrest)
                result['V'] += Vrest['V']
                result['projection'].append(outcome)
                turn = ActionSet(reduce(frozenset.union,outcome['actions'].values(),frozenset()))
        return result

    def setState(self,feature,value):
        self.world.setState(self.name,feature,value)

    def addReward(self,tree):
        """
        @return: the index of the added reward tree
        @rtype: int
        """
        try:
            return self.rewards.index(tree)
        except ValueError:
            self.rewards.append(tree)
            for model in self.models.values():
                model['weights'].append(0.)
            return len(self.rewards)-1

    def setRewardWeight(self,tree,weight,model=True):
        index = self.rewards.index(tree)
        self.models[model]['weights'][index] = weight

    def reward(self,vector,model=True):
        total = 0.
        for index in range(len(self.rewards)):
            tree = self.rewards[index]
            R = tree[vector]*vector
            total += self.models[model]['weights'][index]*R
        return total

    def setHorizon(self,horizon,model=True):
        self.models[model]['horizon'] = horizon

    def addAction(self,action,condition=None):
        """
        @param condition: optional legality condition
        @type condition: L{<psychsim.pwl.KeyedPlane>KeyedPlane}
        @return: the action added
        @rtype: L{ActionSet}
        """
        actions = []
        if isinstance(action,set):
            for atom in action:
                if isinstance(atom,Action):
                    actions.append(Action(atom))
                else:
                    actions.append(atom)
        elif isinstance(action,Action):
            actions.append(action)
        else:
            assert isinstance(action,dict),'Argument to addAction must be at least a dictionary'
            actions.append(Action(action))
        for atom in actions:
            if not atom.has_key('subject'):
                # Make me the subject of these actions
                atom['subject'] = self.name
        new = ActionSet(actions)
        self.actions.add(new)
        if condition:
            self.legal[new] = condition
        return new

    def observe(self,observation,subjective=None):
        """
        @param observation: the observation received by this agent
        @param subjective: the pre-observation beliefs of this agent (default is current beliefs)
        @return: the post-observation beliefs of this agent
        """
        if subjective is None:
            subjective = self.subjective
            
    def __copy__(self):
        new = Agent(self.name)
        new.actions = copy.copy(self.actions)
        new.rewards = copy.copy(self.rewards)

    def __xml__(self):
        doc = Document()
        root = doc.createElement('agent')
        doc.appendChild(root)
        doc.documentElement.setAttribute('name',self.name)
        # Actions
        node = doc.createElement('actions')
        root.appendChild(node)
        for action in self.actions:
            node.appendChild(action.__xml__().documentElement)
        # Conditions for legality of actions
        for action,tree in self.legal.items():
            node = doc.createElement('legal')
            node.appendChild(action.__xml__().documentElement)
            node.appendChild(tree.__xml__().documentElement)
            root.appendChild(node)
        # Reward components
        node = doc.createElement('reward')
        for tree in self.rewards:
            node.appendChild(tree.__xml__().documentElement)
        root.appendChild(node)
        # Models
        for name,model in self.models.items():
            node = doc.createElement('model')
            for weight in model['weights']:
                subnode = doc.createElement('weight')
                subnode.appendChild(doc.createTextNode(str(weight)))
                node.appendChild(subnode)
            node.setAttribute('name',str(name))
            node.setAttribute('horizon',str(model['horizon']))
            root.appendChild(node)
        return doc

    def parse(self,element):
        self.name = str(element.getAttribute('name'))
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'actions':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            self.actions.add(ActionSet(subnode.childNodes))
                        subnode = subnode.nextSibling
                elif node.tagName == 'reward':
                    self.rewards = []
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            self.rewards.append(KeyedTree(subnode))
                        subnode = subnode.nextSibling
                elif node.tagName == 'model':
                    name = str(node.getAttribute('name'))
                    if name == 'True':
                        name = True
                    subnode = node.firstChild
                    model = {'weights': [],'V': [], 'horizon': int(node.getAttribute('horizon'))}
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'weight'
                            model['weights'].append(float(subnode.firstChild.data))
                        subnode = subnode.nextSibling
                    self.models[name] = model
                elif node.tagName == 'legal':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            if subnode.tagName == 'option':
                                action = ActionSet(subnode.childNodes)
                            elif subnode.tagName == 'tree':
                                tree = KeyedTree(subnode)
                        subnode = subnode.nextSibling
                    self.legal[action] = tree
            node = node.nextSibling
