import copy
import random
from xml.dom.minidom import Document,Node

from action import Action,ActionSet
from pwl import *
from probability import Distribution

class Agent:
    """
    @ivar name: agent name
    @type name: str
    @ivar world: the environment that this agent inhabits
    @type world: L{<psychsim.world.World>World}
    @ivar actions: the set of possible actions that the agent can choose from
    @type actions: {L{Action}}
    @ivar legal: a set of conditions under which certain action choices are allowed (default is that all actions are allowed at all times)
    @type legal: L{ActionSet}S{->}L{<psychsim.pwl.KeyedPlane>KeyedPlane}
    @ivar omega: the set of possible observations this agent may receive
    @type ivar omega: {str}
    @ivar O: the observation function; default is C{True}, which means perfect observations of actions
    @type O: L{KeyedTree}
    """
    def __init__(self,name):
        self.world = None
        self.actions = set()
        self.legal = {}
        self.omega = set()
        self.O = True
        self.models = {}
        self.modelList = []
        if isinstance(name,Document):
            self.parse(name.documentElement)
        elif isinstance(name,Node):
            self.parse(name)
        else:
            self.name = name
            self.addModel(True,{},True,1,0)

    """------------------"""
    """Policy methods"""
    """------------------"""
                
    def value(self,vector,action=None,horizon=None,others=None,model=True):
        """
        Computes the expected value of a state vector (and optional action choice) to this agent
        @param vector: the state vector (not distribution) representing the possible world under consideration
        @type vector: L{KeyedVector}
        @param action: the action choice for the agent to evalue; if C{None}, then use agent's own action choice (default)
        @type action: L{ActionSet}
        @param horizon: the number of time steps to project into the future (default is agent's horizon)
        @type horizon: int
        @param others: optional table of actions being performed by other agents in this time step
        @type others: strS{->}L{ActionSet}
        @param model: the model of this agent to use (default is C{True})
        """
        if horizon is None:
            horizon = self.models[model]['horizon']
        # Compute immediate reward
        R = self.reward(vector,model)
        result = {'V': R,
                  'R': R,
                  'old': vector,
                  'horizon': horizon,
                  'projection': []}
        if horizon > 0:
            # Perform action(s)
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
        return result

    def decide(self,vector,horizon=None,others=None,model=True,tiebreak=None):
        """
        Generate an action choice for this agent in the given state
        @param vector: the current state in which the agent is making its decision
        @type vector: L{KeyedVector}
        @param horizon: the value function horizon (default is use horizon specified in model}
        @type horizon: int
        @param others: the optional action choices of other agents in the current time step
        @type others: strS{->}L{ActionSet}
        @param model: the mental model to use (default is C{True})
        @type model: str
        @param tiebreak: what to do in case multiple actions have the same expected value
           - random: choose one of the actions at random
           - distribution: return a uniform distribution over the actions
           - None: make a deterministic choice among the actions (default)
        @type tiebreak: str
        """
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

    def setHorizon(self,horizon,model=None,level=None):
        """
        @type horizon: int
        @param model: the model to set the horizon for, where C{None} means set it for all (default is C{None})
        @param level: if setting across models, the recursive level of models to do so, where C{None} means all levels (default is C{None})
        """
        if model is None:
            for model in self.models.values():
                if level is None or model['level'] == level:
                    model['horizon'] = horizon
        else:
            self.models[model]['horizon'] = horizon

    """------------------"""
    """Action methods"""
    """------------------"""

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

    """------------------"""
    """State methods"""
    """------------------"""

    def setState(self,feature,value):
        self.world.setState(self.name,feature,value)

    """------------------"""
    """Reward methods"""
    """------------------"""

    def addReward(self,tree):
        raise DeprecationWarning,'Use setReward(tree) instead'

    def setReward(self,tree,weight=0.,model=None):
        if model is None:
            for model in self.models.values():
                model['R'][tree] = weight
        else:
            self.models[model]['R'][tree] = weight

    def setRewardWeight(self,tree,weight,model=True):
        raise DeprecationWarning,'Use setReward(tree,weight,model) instead'

    def reward(self,vector,model=True):
        total = 0.
        for tree,weight in self.models[model]['R'].items():
            R = tree[vector]*vector
            total += R*weight
        return total

    """------------------"""
    """Mental model methods"""
    """------------------"""

    def addModel(self,name,R=True,beliefs=True,horizon=True,level=True):
        """
        Adds a new possible model for this agent (to be used as either true model or else as mental model another agent has of it)
        @param name: the label for this model
        @type name: str
        @param R: the reward table for the agent under this model (default is C{True})
        @type R: L{KeyedTree}S{->}float
        @param beliefs: the beliefs the agent has under this model (default is C{True})
        @type beliefs: L{VectorDistribution}
        @param horizon: the horizon of the value function under this model (default is C{True})
        @type horizon: int
        @param level: the recursive depth of this model (default is C{True})
        @type level: int
        @return: the model created
        @rtype: dict
        """
        if self.models.has_key(name):
            raise NameError,'Model %s already exists for agent %s' % \
                (name,self.name)
        model = {'R': R,'beliefs': beliefs,
                 'horizon': horizon,'level': level,
                 'index': len(self.models),'V': []}
        self.models[name] = model
        self.modelList.append(name)
        return model

    def model2index(self,model):
        """
        Convert a model name to a numeric representation
        @param model: the model name
        @type model: str
        @rtype: int
        """
        return self.models[model]['index']

    def index2model(self,index):
        """
        Convert a numeric representation of a model to a name
        @param index: the numeric representation of the model
        @type index: int
        @rtype: str
        """
        return self.modelList[index]

    """---------------------"""
    """Belief update methods"""
    """---------------------"""

    def setBelief(self,key,distribution,model=True):
        beliefs = self.models[model]['beliefs']
        if beliefs is True:
            beliefs = copy.deepcopy(self.world.state)
            self.models[model]['beliefs'] = beliefs
        beliefs.join(key,distribution)

    def printBeliefs(self,model=True):
        beliefs = self.models[model]['beliefs']
        if beliefs is True:
            beliefs = self.world.state
        self.world.printState(beliefs)

    def observe(self,observation,real=True,model=True):
        """
        @param observation: the observation received by this agent
        @return: the post-observation beliefs of this agent
        """
        if not self.models[model]['beliefs'] is True:
            # Beliefs are not necessarily true state
            pass
        if real:
            pass

    """------------------"""
    """Serialization methods"""
    """------------------"""
            
    def __copy__(self):
        return self.__class__(self.self.__xml__())

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
        # Observations
        for omega in self.omega:
            node = doc.createElement('omega')
            node.appendChild(doc.createTextNode(omega))
            root.appendChild(node)
        # Models
        for name,model in self.models.items():
            node = doc.createElement('model')
            if model['R'] is True:
                node.setAttribute('R','True')
            else:
                for tree,weight in model['R'].items():
                    subnode = doc.createElement('reward')
                    subnode.setAttribute('weight',str(weight))
                    subnode.appendChild(tree.__xml__().documentElement)
                    node.appendChild(subnode)
            node.setAttribute('name',str(name))
            node.setAttribute('horizon',str(model['horizon']))
            node.setAttribute('level',str(model['level']))
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
                elif node.tagName == 'omega':
                    self.omega.add(str(node.firstChild.data).strip())
                elif node.tagName == 'model':
                    # Parse model name
                    name = str(node.getAttribute('name'))
                    if name == 'True':
                        name = True
                    # Parse model reward weights
                    weights = str(node.getAttribute('R'))
                    if weights == str(True):
                        weights = True
                    else:
                        weights = {}
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'reward'
                            subchild = subnode.firstChild
                            while subchild and subchild.nodeType != subchild.ELEMENT_NODE:
                                subchild = subchild.nextSibling
                            weights[KeyedTree(subchild)] = float(subnode.getAttribute('weight'))
                        subnode = subnode.nextSibling
                    beliefs = True
                    # Parse horizon
                    horizon = str(node.getAttribute('horizon'))
                    try:
                        horizon = int(horizon)
                    except ValueError:
                        assert horizon == str(True)
                        horizon = True
                    # Parse recursive level
                    level = str(node.getAttribute('level'))
                    try:
                        level = int(level)
                    except ValueError:
                        assert level == str(True)
                        level = True
                    # Add new model
                    self.addModel(name,weights,beliefs,horizon,level)
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
