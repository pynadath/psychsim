import copy
import random
import StringIO
from xml.dom.minidom import Document,Node

from action import Action,ActionSet
from pwl import *
from probability import Distribution

class Agent:
    """
    @ivar name: agent name
    @type name: str
    @ivar world: the environment that this agent inhabits
    @type world: L{World<psychsim.world.World>}
    @ivar actions: the set of possible actions that the agent can choose from
    @type actions: {L{Action}}
    @ivar legal: a set of conditions under which certain action choices are allowed (default is that all actions are allowed at all times)
    @type legal: L{ActionSet}S{->}L{KeyedPlane}
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
            # Default model settings
            self.addModel(True,R={},horizon=2,level=2,rationality=0.9,discount=1.)

    """------------------"""
    """Policy methods"""
    """------------------"""

    def decide(self,vector,horizon=None,others=None,model=True,tiebreak=None):
        """
        Generate an action choice for this agent in the given state
        @param vector: the current state in which the agent is making its decision
        @type vector: L{KeyedVector}
        @param horizon: the value function horizon (default is use horizon specified in model)
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
        # What are my subjective beliefs for this decision?
        belief = self.getBelief(model,vector)
        # Do I have a policy telling me what to do?
        if self.models[model]['policy']:
            assert len(belief) == 1,'Unable to apply PWL policies to uncertain beliefs'
            action = self.models[model]['policy'][belief.domain()[0]]
            if action:
                if isinstance(action,Action):
                    action = ActionSet([action])
                return {'action': action}
        if horizon is None:
            horizon = self.models[model]['horizon']
        # Consider all legal actions (legality determined by *real* world, not my belief)
        actions = self.getActions(vector)
        if len(actions) == 0:
            # Someone made a boo-boo because there is no legal action for this agent right now
            buf = StringIO.StringIO()
            self.world.printVector(vector,buf)
            msg = buf.getvalue()
            buf.close()
            raise RuntimeError,'%s has no legal actions in:\n%s' % (self.name,msg)
        elif len(actions) == 1:
            # Only one possible action
            return {'action': iter(actions).next()}
        # Keep track of value function
        V = {}
        best = None
        for action in actions:
            # Compute value across possible worlds
            V[action] = {'__EV__': 0.}
            for state in belief.domain():
                V[action][state] = self.value(state,action,horizon,others,model)
                V[action]['__EV__'] += belief[state]*V[action][state]['V']
            # Determine whether this action is the best
            if best is None:
                best = [action]
            elif V[action]['__EV__'] == V[best[0]]['__EV__']:
                best.append(action)
            elif V[action]['__EV__'] > V[best[0]]['__EV__']:
                best = [action]
        result = {'V*': V[best[0]]['__EV__'],'V': V}
        if len(best) == 1:
            result['action'] = best[0]
        elif tiebreak == 'random':
            result['action'] = random.sample(best,1)[0]
        elif tiebreak == 'distribution':
            result['action'] = {}
            prob = 1./float(len(best))
            for action in best:
                result['action'][action] = prob
            result['action'] = Distribution(result['action'])
        else:
            assert tiebreak is None,'Unknown tiebreaking method: %s' % (tiebreak)
            best.sort()
            result['action'] = best[0]
        return result
                
    def value(self,vector,action=None,horizon=None,others=None,model=True):
        """
        Computes the expected value of a state vector (and optional action choice) to this agent
        @param vector: the state vector (not distribution) representing the possible world under consideration
        @type vector: L{KeyedVector}
        @param action: prescribed action choice for the agent to evaluate; if C{None}, then use agent's own action choice (default is C{None})
        @type action: L{ActionSet}
        @param horizon: the number of time steps to project into the future (default is agent's horizon)
        @type horizon: int
        @param others: optional table of actions being performed by other agents in this time step (default is no other actions)
        @type others: strS{->}L{ActionSet}
        @param model: the model of this agent to use (default is C{True})
        """
        if horizon is None:
            horizon = self.models[model]['horizon']
        discount = self.models[model]['discount']
        if horizon == self.models[model]['horizon']:
            # Check for pre-computed value function
            V = self.models[model]['V']
            if V:
                substate = vector.filter(self.models[model]['ignore'])
                if V.has_key(substate):
                    value = V[substate][self.name][action]
                else:
                    substate = self.world.nearestVector(substate,V.keys())
                    value = V[substate][self.name][action]
                return {'V': value,'agent': self.name,'horizon': horizon,'projection':[]}
        # Compute immediate reward
        R = self.reward(vector,model)
        result = {'V': R,
                  'R': R,
                  'agent': self.name,
                  'state': vector,
                  'horizon': horizon,
                  'projection': []}
        if horizon > 0 and not self.world.terminated(vector):
            # Perform action(s)
            if others is None:
                turn = {}
            else:
                turn = copy.copy(others)
            if action:
                turn[self.name] = action
            outcome = self.world.stepFromState(vector,turn,horizon)
            if isinstance(outcome['new'],Distribution):
                # Uncertain outcomes
                if discount < 1e-6:
                    # Current reward is irrelevant
                    result['V'] = 0.
                for newVector in outcome['new'].domain():
                    entry = copy.copy(outcome)
                    entry['probability'] = outcome['new'][newVector]
                    Vrest = self.value(newVector,None,horizon-1,None,model)
                    entry.update(Vrest)
                    if discount < -1e-6:
                        # Only final value matters
                        result['V'] += entry['probability']*entry['V']
                    else:
                        # Accumulate value
                        result['V'] += discount*entry['probability']*entry['V']
                    result['projection'].append(entry)
            else:
                # Deterministic outcome
                outcome['probability'] = 1.
                Vrest = self.value(outcome['new'],None,horizon-1,None,model)
                outcome.update(Vrest)
                if discount < -1e-6:
                    # Only final value matters
                    result['V'] = Vrest['V']
                else:
                    # Accumulate value
                    result['V'] += discount*Vrest['V']
                result['projection'].append(outcome)
        return result

    def valueIteration(self,horizon=None,ignore=[],model=True,epsilon=1e-6):
        """
        Compute a value function for the given model
        """
        if horizon is None:
            horizon = self.models[model]['horizon']
        # Find transition matrix
        transition = self.world.reachable(horizon=horizon,ignore=ignore)
        # Initialize value function
        for start in transition.keys():
            self.models[model]['V'][start] = {}
            for agent in self.world.agents.values():
                if self.world.terminated(start):
                    if agent.name == self.name:
                        self.models[model]['V'][start][agent.name] = {'*': agent.reward(start,model)}
                    else:
                        # For now, assume true beliefs, but change later
                        self.models[model]['V'][start][agent.name] = {'*': agent.reward(start)}
                else:
                    self.models[model]['V'][start][agent.name] = {'*': 0.}
        # Loop until no change in value function
        change = 1.
        while change > epsilon:
            print change
            change = 0.
            V = {}
            # Consider all possible start states
            for start in transition.keys():
                if not self.world.terminated(start):
                    # Back-propagate reward from subsequent states
                    V[start] = {}
                    for name in self.world.agents.keys():
                        V[start][name] = {}
                    actor = None
                    best = None
                    for action,distribution in transition[start].items():
                        # Make sure only one actor is acting at a time
                        if actor is None:
                            actor = action['subject']
                        else:
                            assert action['subject'] == actor,'Unable to do value iteration with concurrent actors'
                        # Consider all possible results of this action
                        for agent in self.world.agents.values():
                            for end in transition[start][action].domain():
                                # Determine expected value of future
                                Vrest = transition[start][action][end]*self.models[model]['V'][end][agent.name]['*']
                                # Determine discount function (should use belief about other agent, but doesn't yet)
                                if agent.name == self.name:
                                    discount = agent.models[model]['discount']
                                else:
                                    discount = agent.models[True]['discount']
                                if discount < -epsilon:
                                    # Future reward is all that matters
                                    V[start][agent.name][action] = Vrest
                                else:
                                    # Current reward + Discounted future reward
                                    if agent.name == self.name:
                                        R = agent.reward(start,model)
                                    else:
                                        R = agent.reward(start,model)
                                    V[start][agent.name][action] = R + discount*Vrest
                                try:
                                    change += abs(V[start][agent.name][action]-self.models[model]['V'][start][agent.name][action])
                                except KeyError:
                                    change += abs(V[start][agent.name][action])
                            # Which action is going to be chosen?
                            if agent.name == actor:
                                if best is None or V[start][actor][action] > V[start][actor][best]:
                                    best = action
                    # Value of state is the value of the chosen action in this state
                    assert not best is None,'Unable to determine action choice by %s' % (actor)
                    for name in self.world.agents.keys():
                        V[start][name]['*'] = V[start][name][best]
                        # Update total delta of this iteration
            self.models[model]['V'].update(V)
        return self.models[model]['V']

    def setPolicy(self,policy,model=None,level=None):
        self.setParameter('policy',policy.desymbolize(self.world.symbols),model,level)

    def setHorizon(self,horizon,model=None,level=None):
        """
        @type horizon: int
        @param model: the model to set the horizon for, where C{None} means set it for all (default is C{None})
        @param level: if setting across models, the recursive level of models to do so, where C{None} means all levels (default is C{None})
        """
        self.setParameter('horizon',horizon,model,level)

    def setParameter(self,name,value,model=None,level=None):
        """
        Set a parameter value for the given model(s)
        @param name: the feature of the model to set
        @type name: str
        @param value: the new value for the parameter
        @param model: the model to set the horizon for, where C{None} means set it for all (default is C{None})
        @param level: if setting across models, the recursive level of models to do so, where C{None} means all levels (default is C{None})
        """
        if model is None:
            for model in self.models.values():
                if level is None or model['level'] == level:
                    self.setParameter(name,value,model['name'])
        else:
            self.models[model][name] = value

    """------------------"""
    """Action methods"""
    """------------------"""

    def addAction(self,action,condition=None):
        """
        @param condition: optional legality condition
        @type condition: L{KeyedPlane}
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

    def setLegal(self,action,tree):
        """
        Sets the legality decision tree for a given action
        @param action: the action whose legality we are setting
        @param tree: the decision tree for the legality of the action
        @type tree: L{KeyedTree}
        """
        self.legal[action] = tree.desymbolize(self.world.symbols)

    """------------------"""
    """State methods"""
    """------------------"""

    def setState(self,feature,value):
        self.world.setState(self.name,feature,value)

    """------------------"""
    """Reward methods"""
    """------------------"""

    def setReward(self,tree,weight=0.,model=None):
        if model is None:
            for model in self.models.values():
                model['R'][tree] = weight
        else:
            self.models[model]['R'][tree] = weight

    def reward(self,vector,model=True):
        """
        @return: the reward I derive in the given state (under the given model, default being the C{True} model)
        @rtype: float
        """
        R = self.models[model]['R']
        if R is True:
            # Use true reward function
            R = self.models[True]['R']
        total = 0.
        for tree,weight in R.items():
            ER = tree[vector]*self.world.scaleState(vector)
            total += ER*weight
        return total

    """------------------"""
    """Mental model methods"""
    """------------------"""

    def addModel(self,name,**kwargs):
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
        @param rationality: the rationality parameter used in a quantal response function when modeling others (default is 10)
        @type rationality: float
        @return: the model created
        @rtype: dict
        """
        if self.models.has_key(name):
            raise NameError,'Model %s already exists for agent %s' % \
                (name,self.name)
        model = {'name': name,'index': len(self.models),'R': True,'beliefs': True,
                 'horizon': True,'level': True,'rationality': True,'discount': True,
                 'V': {},'policy': {},'ignore': []}
        model.update(kwargs)
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
        if isinstance(index,float):
            index = int(index+0.5)
        return self.modelList[index]

    """---------------------"""
    """Belief update methods"""
    """---------------------"""

    def setRecursiveLevel(self,level,model=True):
        if model is None:
            for model in self.models.values():
                model['level'] = level
        else:
            self.models[model]['level'] = level

    def setBelief(self,key,distribution,model=True):
        beliefs = self.models[model]['beliefs']
        if beliefs is True:
            beliefs = VectorDistribution({KeyedVector({CONSTANT: 1.}): 1.})
            self.models[model]['beliefs'] = beliefs
        beliefs.join(key,distribution)

    def getBelief(self,model=True,world=None):
        if world is None:
            world = self.world.state
        if isinstance(world,KeyedVector):
            world = VectorDistribution({world: 1.})
        beliefs = self.models[model]['beliefs']
        if beliefs is True:
            beliefs = world
        else:
            beliefs = world.merge(beliefs)
        return beliefs

    def printBeliefs(self,model=True):
        beliefs = self.getBelief(model)
        self.world.printState(beliefs)

    def observe(self,state,actions,model=True):
        """
        @return: the post-observation beliefs of this agent
        """
        return actions

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
        for name in self.modelList:
            model = self.models[name]
            node = doc.createElement('model')
            node.setAttribute('name',str(name))
            for key in filter(lambda k: not k in ['name','index'],model.keys()):
                if key == 'R':
                    # Reward function for this model
                    if model['R'] is True:
                        subnode = doc.createElement(key)
                        subnode.appendChild(doc.createTextNode(str(model[key])))
                        node.appendChild(subnode)
                    else:
                        for tree,weight in model['R'].items():
                            subnode = doc.createElement(key)
                            subnode.setAttribute('weight',str(weight))
                            subnode.appendChild(tree.__xml__().documentElement)
                            node.appendChild(subnode)
                elif key == 'V':
                    pass
                elif key == 'ignore':
                    for key in model['ignore']:
                        subnode = doc.createElement(key)
                        subnode.appendChild(doc.createTextNode(key))
                        node.appendChild(subnode)
                elif key == 'policy':
                    if model['policy']:
                        subnode = doc.createElement(key)
                        subnode.appendChild(model['policy'].__xml__().documentElement)
                        node.appendChild(subnode)
                elif key == 'beliefs':
                    # Beliefs for this model
                    if model['beliefs'] is True:
                        subnode = doc.createElement(key)
                        subnode.appendChild(doc.createTextNode(str(model[key])))
                        node.appendChild(subnode)
                    else:
                        subnode = doc.createElement(key)
                        subnode.appendChild(model['beliefs'].__xml__().documentElement)
                        node.appendChild(subnode)
                else:
                    subnode = doc.createElement(key)
                    subnode.appendChild(doc.createTextNode(str(model[key])))
                    node.appendChild(subnode)
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
                    # Parse children
                    kwargs = {'R': {},'ignore': []}
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            key = subnode.tagName
                            subchild = subnode.firstChild
                            while subchild:
                                if subchild.nodeType == subchild.ELEMENT_NODE:
                                    if key == 'R':
                                        kwargs[key][KeyedTree(subchild)] = float(subnode.getAttribute('weight'))
                                    elif key == 'beliefs':
                                        kwargs[key] = VectorDistribution(subchild)
                                    elif key == 'policy':
                                        kwargs[key] = KeyedTree(subchild)
                                    else:
                                        raise NameError,'Unknown element found when parsing model\'s %s' % (key)
                                elif subchild.nodeType == subchild.TEXT_NODE:
                                    text = subchild.data.strip()
                                    if text:
                                        if key == 'ignore':
                                            kwargs[key].append(text)
                                        elif text == str(True):
                                            kwargs[key] = True
                                        elif key == 'horizon':
                                            kwargs[key] = int(text)
                                        else:
                                            kwargs[key] = float(text)
                                subchild = subchild.nextSibling
                        subnode = subnode.nextSibling
                    # Add new model
                    self.addModel(name,**kwargs)
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
