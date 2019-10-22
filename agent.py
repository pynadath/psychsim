import copy
import math
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
    @ivar x: X coordinate to be used in UI
    @type x: int
    @ivar y: Y coordinate to be used in UI
    @type y: int
    @ivar color: color name to be used in UI
    @type color: str
    """

    def __init__(self,name):
        self.world = None
        self.actions = set()
        self.legal = {}
        self.omega = set()
        self.O = True
        self.models = {}
        self.modelList = {}
        self.x = None
        self.y = None
        self.color = None
        if isinstance(name,Document):
            self.parse(name.documentElement)
        elif isinstance(name,Node):
            self.parse(name)
        else:
            self.name = name
            # Default model settings
            self.addModel(True,R={},horizon=2,level=2,rationality=1.,discount=1.,selection='consistent',
                          beliefs=True,parent=None,projector=Distribution.expectation)

    """------------------"""
    """Policy methods"""
    """------------------"""

    def decide(self,vector,horizon=None,others=None,model=None,selection='random',actions=None,keys=None):
        """
        Generate an action choice for this agent in the given state
        @param vector: the current state in which the agent is making its decision
        @type vector: L{KeyedVector}
        @param horizon: the value function horizon (default is use horizon specified in model)
        @type horizon: int
        @param others: the optional action choices of other agents in the current time step
        @type others: strS{->}L{ActionSet}
        @param model: the mental model to use (default is model specified in vector)
        @type model: str
        @param selection: how to translate value function into action selection
           - random: choose one of the maximum-value actions at random
           - uniform: return a uniform distribution over the maximum-value actions
           - distribution: return a distribution (a la quantal response or softmax) using rationality of the given model
           - consistent: make a deterministic choice among the maximum-value actions (default setting for a model)
           - C{None}: use the selection method specified by the given model (default)
        @type selection: str
        @param actions: possible action choices (default is all legal actions)
        @param keys: subset of state features to project over (default is all state features)
        """
        selection = 'random'
        if model is None:
            model = self.world.getModel(self.name,vector)
        if selection is None:
            selection = self.getAttribute('selection',model)
        # What are my subjective beliefs for this decision?
        belief = self.getBelief(vector,model)
        # Do I have a policy telling me what to do?
        policy = self.getAttribute('policy',model)
        if policy:
            assert len(belief) == 1,'Unable to apply PWL policies to uncertain beliefs'
            action = policy[belief.domain()[0]]
            if action:
                if isinstance(action,Action):
                    action = ActionSet([action])
                return {'action': action}
        if horizon is None:
            horizon = self.getAttribute('horizon',model)
        if actions is None:
            # Consider all legal actions (legality determined by my belief, circumscribed by real world)
            actions = self.getActions(vector)
            for state in belief.domain():
                actions = actions & self.getActions(state)
        if len(actions) == 0:
            # Someone made a boo-boo because there is no legal action for this agent right now
            buf = StringIO.StringIO()
            print >> buf,'%s has no legal actions in:' % (self.name)
            self.world.printVector(vector,buf)
            print >> buf,'\nwhen believing:'
            self.world.printState(belief,buf)
            msg = buf.getvalue()
            buf.close()
            raise RuntimeError,msg
        elif len(actions) == 1:
            # Only one possible action
            return {'action': iter(actions).next()}
        # Keep track of value function
        V = {}
        best = None
        for action in actions:
            # Compute value across possible worlds
            V[action] = {'__EV__': 0.}
            if isinstance(keys,dict):
                subkeys = keys[action]
            else:
                subkeys = keys
            for state in belief.domain():
                V[action][state] = self.value(state,action,horizon,others,model,subkeys)
                V[action]['__EV__'] += belief[state]*V[action][state]['V']
            if len(V[action]) > 1:
                # Determine whether this action is the best
                if best is None:
                    best = [action]
                elif V[action]['__EV__'] == V[best[0]]['__EV__']:
                    best.append(action)
                elif V[action]['__EV__'] > V[best[0]]['__EV__']:
                    best = [action]
        result = {'V*': V[best[0]]['__EV__'],'V': V}
        # Make an action selection based on the value function
        if selection == 'distribution':
            values = {}
            for key,entry in V.items():
                values[key] = entry['__EV__']
            result['action'] = Distribution(values,self.getAttribute('rationality',model))
        elif len(best) == 1:
            # If there is only one best action, all of the selection mechanisms devolve
            # to the same unique choice
            result['action'] = best[0]
        elif selection == 'random':
            result['action'] = random.sample(best,1)[0]
        elif selection == 'uniform':
            result['action'] = {}
            prob = 1./float(len(best))
            for action in best:
                result['action'][action] = prob
            result['action'] = Distribution(result['action'])
        else:
            assert selection == 'consistent','Unknown action selection method: %s' % (selection)
            best.sort()
            result['action'] = best[0]
        return result

    def value(self,vector,action=None,horizon=None,others=None,model=None,keys=None):
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
        @param keys: subset of state features to project over in computing future value (default is all state features)
        """
        if model is None:
            model = self.world.getModel(self.name,vector)
        # Determine horizon
        if horizon is None:
            horizon = self.getAttribute('horizon',model)
        # Determine discount factor
        discount = self.getAttribute('discount',model)
        # Compute immediate reward
        R = self.reward(vector,model)
        result = {'R': R,
                  'agent': self.name,
                  'state': vector,
                  'horizon': horizon,
                  'projection': []}
        # Check for pre-computed value function
        V = self.getAttribute('V',model).get(self.name,vector,action,horizon,
                                             self.getAttribute('ignore',model))
        if V is not None:
            result['V'] = V
        else:
            result['V'] = R
            if horizon > 0 and not self.world.terminated(vector):
                # Perform action(s)
                if others is None:
                    turn = {}
                else:
                    turn = copy.copy(others)
                if not action is None:
                    turn[self.name] = action
                outcome = self.world.stepFromState(vector,turn,horizon,keys=keys)
                if not outcome.has_key('new'):
                    # No consistent outcome
                    pass
                elif isinstance(outcome['new'],Distribution):
                    # Uncertain outcomes
                    future = Distribution()
                    for newVector in outcome['new'].domain():
                        entry = copy.copy(outcome)
                        entry['probability'] = outcome['new'][newVector]
                        Vrest = self.value(newVector,None,horizon-1,None,model,keys)
                        entry.update(Vrest)
                        try:
                            future[entry['V']] += entry['probability']
                        except KeyError:
                            future[entry['V']] = entry['probability']
                        result['projection'].append(entry)
                    # The following is typically "expectation", but might be "max" or "min", too
                    op = self.getAttribute('projector',model)
                    if discount < -1e-6:
                        # Only final value matters
                        result['V'] = apply(op,(future,))
                    else:
                        # Accumulate value
                        result['V'] += discount*apply(op,(future,))
                else:
                    # Deterministic outcome
                    outcome['probability'] = 1.
                    Vrest = self.value(outcome['new'],None,horizon-1,None,model,keys)
                    outcome.update(Vrest)
                    if discount < -1e-6:
                        # Only final value matters
                        result['V'] = Vrest['V']
                    else:
                        # Accumulate value
                        result['V'] += discount*Vrest['V']
                    result['projection'].append(outcome)
            # Do some caching
            self.getAttribute('V',model).set(self.name,vector,action,horizon,result['V'])
        return result

    def valueIteration(self,horizon=None,ignore=None,model=True,epsilon=1e-6,debug=0,maxIterations=None):
        """
        Compute a value function for the given model
        """
        if horizon is None:
            horizon = self.getAttribute('horizon',model)
        if ignore is None:
            ignore = self.getAttribute('ignore',model)
        # Find transition matrix
        transition = self.world.reachable(horizon=horizon,ignore=ignore,debug=(debug > 1))
        if debug:
            print '|S|=%d' % (len(transition))
        # Initialize value function
        V = self.getAttribute('V',model)
        newChanged = set()
        for start in transition.keys():
            for agent in self.world.agents.values():
                if self.world.terminated(start):
                    if agent.name == self.name:
                        value = agent.reward(start,model)
                    else:
                        value = agent.reward(start)
                    V.set(agent.name,start,None,0,value)
                    if abs(value) > epsilon:
                        newChanged.add(start)
                else:
                    V.set(agent.name,start,None,0,0.)
        # Loop until no change in value function
        iterations = 0
        while len(newChanged) > 0 and (maxIterations is None or iterations < maxIterations):
            iterations += 1
            if debug > 0:
                print 'Iteration %d' % (iterations)
            oldChanged = newChanged.copy()
            newChanged.clear()
            recomputed = set()
            newV = ValueFunction()
            # Consider all possible nodes whose value has changed on the previous iteration
            for node in oldChanged:
                if debug > 1:
                    print
                    self.world.printVector(node)
                for start in transition[node]['__predecessors__'] - recomputed:
                    recomputed.add(start)
                    # This is a state whose value might have changed
                    actor = None
                    for action,distribution in transition[start].items():
                        if action == '__predecessors__':
                            continue
                        if debug > 2:
                            print '\t\t%s' % (action)
                        # Make sure only one actor is acting at a time
                        if actor is None:
                            actor = action['subject']
                        else:
                            assert action['subject'] == actor,'Unable to do value iteration with concurrent actors'
                        # Consider all possible results of this action
                        for agent in self.world.agents.values():
                            # Accumulate expected rewards from possible transitions
                            ER = 0.
                            for end in distribution.domain():
                                # Determine expected value of future
                                future = V.get(agent.name,end,None,0)
                                if future is None:
                                    Vrest = 0.
                                else:
                                    Vrest = distribution[end]*future
                                # Determine discount function
                                # (should use belief about other agent, but doesn't yet)
                                if agent.name == self.name:
                                    discount = agent.getAttribute('discount',model)
                                else:
                                    discount = agent.getAttribute('discount',True)
                                if discount < -epsilon:
                                    # Future reward is all that matters
                                    ER += distribution[end]*Vrest
                                else:
                                    # Current reward + Discounted future reward
                                    if agent.name == self.name:
                                        R = agent.reward(start,model)
                                    else:
                                        R = agent.reward(start)
                                    ER += distribution[end]*(R+discount*Vrest)
                            newV.set(agent.name,start,action,0,ER)
                            if debug > 2:
                                print '\t\t\tV_%s = %5.3f' % (agent.name,ER)
                    # Value of state is the value of the chosen action in this state
                    choice = self.predict(start,actor,newV,0)
                    if debug > 2:
                        print '\tPrediction\n%s' % (choice)
                    delta = 0.
                    for name in self.world.agents.keys():
                        for action in choice.domain():
                            newV.add(name,start,None,0,choice[action]*newV.get(name,start,action,0))
                        old = V.get(name,start,None,0)
                        if old is None:
                            delta += abs(newV.get(name,start,None,0))
                        else:
                            delta += abs(newV.get(name,start,None,0) - old)
                        if debug > 1:
                            print '\tV_%s = %5.3f' % (name,newV.get(name,start,None,0))
                    if delta > epsilon:
                        newChanged.add(start)
            V = newV
            self.setAttribute('V',V,model)
        if debug > 0:
            print 'Completed after %d iterations' % (iterations)
        return self.getAttribute('V',model)

    def setPolicy(self,policy,model=None,level=None):
        self.setAttribute('policy',policy.desymbolize(self.world.symbols),model,level)

    def setHorizon(self,horizon,model=None,level=None):
        """
        @type horizon: int
        @param model: the model to set the horizon for, where C{None} means set it for all (default is C{None})
        @param level: if setting across models, the recursive level of models to do so, where C{None} means all levels (default is C{None})
        """
        self.setAttribute('horizon',horizon,model,level)

    def setParameter(self,name,value,model=None,level=None):
        raise DeprecationWarning,'Use setAttribute instead'

    def setAttribute(self,name,value,model=None,level=None):
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
                    self.setAttribute(name,value,model['name'])
        else:
            self.models[model][name] = value

    def findAttribute(self,name,model=True):
        """
        @return: the name of the nearest ancestor model (include the given model itself) that specifies a value for the named feature
        """
        if self.models[model].has_key(name):
            return model
        elif self.models[model]['parent'] is None:
            return None
        else:
            return self.findAttribute(name,self.models[model]['parent'])

    def getAttribute(self,name,model=True):
        """
        @return: the value for the specified parameter of the specified mental model
        """
        ancestor = self.findAttribute(name,model)
        if ancestor is None:
            return None
        else:
            return self.models[ancestor][name]

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
        if isinstance(action,set) or isinstance(action,frozenset) or isinstance(action,list):
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

    def getActions(self,vector,actions=None):
        """
        @param vector: the world in which to test legality
        @param actions: the set of actions to test legality of (default is all available actions)
        @return: the set of possible actions to choose from in the given state vector
        @rtype: {L{ActionSet}}
        """
        if actions is None:
            actions = self.actions
        if len(self.legal) == 0:
            # No restrictions on legal actions, so take a shortcut
            return actions
        # Otherwise, filter out illegal actions
        result = set()
        for action in actions:
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

    def hasAction(self,atom):
        """
        @type atom: L{Action}
        @return: C{True} iff this agent has the given action (possibly in combination with other actions)
        @rtype: bool
        """
        for action in self.actions:
            for candidate in action:
                if atom.root() == candidate.root():
                    return True
        else:
            return False

    """------------------"""
    """State methods"""
    """------------------"""

    def setState(self,feature,value,state=None):
        return self.world.setState(self.name,feature,value,state)

    def getState(self,feature,state=None):
        return self.world.getState(self.name,feature,state)

    """------------------"""
    """Reward methods"""
    """------------------"""

    def setReward(self,tree,weight=0.,model=True):
        """
        Adds/updates a goal weight within the reward function for the specified model.
        """
        if not self.models[model].has_key('R'):
            self.models[model]['R'] = {}
        if not isinstance(tree,str):
            tree = tree.desymbolize(self.world.symbols)
        self.models[model]['R'][tree] = weight

    def reward(self,vector=None,model=True,recurse=True):
        """
        @param recurse: C{True} iff it is OK to recurse into another agent's reward (default is C{True})
        @type recurse: bool
        @return: the reward I derive in the given state (under the given model, default being the C{True} model)
        @rtype: float
        """
        total = 0.
        if vector is None:
            total = self.reward(self.world.state,model,recurse)
        elif isinstance(vector,VectorDistribution):
            for element in vector.domain():
                total += vector[element]*self.reward(element,model,recurse)
        else:
            R = self.getAttribute('R',model)
            if R is None:
                # No reward components
                return total
            for tree,weight in R.items():
                if isinstance(tree,str):
                    if recurse:
                        # Name of an agent I'm trying to make (un)happy
                        model = self.world.getModel(tree,vector)
                        # Compute agent's reward but don't recurse any further
                        ER = self.world.agents[tree].reward(vector,model,False)
                else:
                    ER = tree[vector]*self.world.scaleState(vector)
                total += ER*weight
        return total

    def printReward(self,model=True,buf=None,prefix=''):
        first = True
        R = self.getAttribute('R',model)
        trees = R.keys()
        trees.sort()
        for tree in trees:
            if first:
                print >> buf,'%s\tR\t\t%3.1f %s' % (prefix,R[tree],str(tree).replace('\n','\n%s\t\t\t' % \
                                                                                         (prefix)))
                first = False
            else:
                print >> buf,'%s\t\t\t%3.1f %s' % (prefix,R[tree],str(tree).replace('\n','\n%s\t\t\t' % \
                                                                                        (prefix)))

    """------------------"""
    """Mental model methods"""
    """------------------"""

    def addModel(self,name,**kwargs):
        """
        Adds a new possible model for this agent (to be used as either true model or else as mental model another agent has of it). Possible arguments are:
         - R: the reward table for the agent under this model (default is C{True}), L{KeyedTree}S{->}float
         - beliefs: the beliefs the agent has under this model (default is C{True}), L{MatrixDistribution}
         - horizon: the horizon of the value function under this model (default is C{True}),int
         - level: the recursive depth of this model (default is C{True}),int
         - rationality: the rationality parameter used in a quantal response function when modeling others (default is 10),float
         - discount: discount factor used in lookahead
         - selection: selection mechanism used in L{decide}
         - parent: another model that this model inherits from (default is C{True})
        @param name: the label for this model
        @type name: sotr
        @return: the model created
        @rtype: dict
        """
        if name is None:
            raise NameError,'"None" is an illegal model name'
        if self.models.has_key(name):
            raise NameError,'Model %s already exists for agent %s' % \
                (name,self.name)
        model = {'name': name,'index': 0,'parent': True,
                 'V': ValueFunction(),'policy': {},'ignore': []}
        model.update(kwargs)
        while self.modelList.has_key(model['index']):
            model['index'] += 1
        self.models[name] = model
        self.modelList[model['index']] = name
        return model

    def deleteModel(self,name):
        """
        Deletes the named model from the space
        @warning: does not check whether there are remaining references to this model
        """
        del self.modelList[self.models[name]['index']]
        del self.models[name]

    def predict(self,vector,name,V,horizon=0):
        """
        Generate a distribution over possible actions based on a table of values for those actions
        @param V: either a L{ValueFunction} instance, or a dictionary of float values indexed by actions
        @param vector: the current state vector
        @param name: the name of the agent whose behavior is to be predicted
        """
        if isinstance(V,ValueFunction):
            V = V.actionTable(name,vector,horizon)
        choices = Distribution()
        if name == self.name:
            # I predict myself to maximize
            best = None
            for action,value in V.items():
                if best is None or value > best:
                    best = value
            best = filter(lambda a: V[a] == best,V.keys())
            for action in best:
                choices[action] = 1./float(len(best))
        else:
            rationality = self.world.agents[name].getAttribute('rationality',
                                                               self.world.getModel(name,vector))
            choices = Distribution(V,rationality)
        return choices

    def model2index(self,model):
        """
        Convert a model name to a numeric representation
        @param model: the model name
        @type model: str
        @rtype: int
        """
        return self.models[model]['index']

    def index2model(self,index,throwException=False):
        """
        Convert a numeric representation of a model to a name
        @param index: the numeric representation of the model
        @type index: int
        @rtype: str
        """
        if isinstance(index,float):
            index = int(index+0.5)
        try:
            return self.modelList[index]
        except KeyError:
            # Unknown model index (hopefully, because of explaining post-GC)
            if throwException:
                raise IndexError,'Unknown model index %s of %s' % (index,self.name)
            else:
                return None

    def belief2model(self,parent,belief):
        # Find "root" model (i.e., one that has more than just beliefs)
        if not isinstance(parent,dict):
            parent = self.models[parent]
        while not parent.has_key('R') and not parent['parent'] is None:
            # Find the model from which we inherit reward
            parent = self.models[parent['parent']]
        # Check whether this is even a new belief (the following loop does badly otherwise)
        if parent.has_key('beliefs') and parent['beliefs'] == belief:
            return parent
        # Find model sharing same parent that has same beliefs
        for model in filter(lambda m: m['parent'] == parent['name'],self.models.values()):
            if model.has_key('beliefs') and not model['beliefs'] is True:
                if model['beliefs'] == belief:
                    return model
        else:
            # Create a new model
            index = 1
            while self.models.has_key('%s%d' % (parent['name'],index)):
                index += 1
            return self.addModel('%s%d' % (parent['name'],index),beliefs=belief,parent=parent['name'])

    def printModel(self,model=True,buf=None,index=None,prefix=''):
        if isinstance(index,int) or isinstance(index,float):
            model = self.index2model(index)
        if model is None:
            print >> buf,'%s\t%-12s\t%-12s' % \
                (prefix,'__model__','__unknown(%s)__' % (index))
            return
        if not isinstance(model,dict):
            model = self.models[model]
        print >> buf,'%s\t%-12s\t%-12s' % \
            (prefix,'__model__',model['name'])
        if model.has_key('R') and not model['R'] is True:
            self.printReward(model['name'],buf,'%s\t\t' % (prefix))
        if model.has_key('beliefs') and not model['beliefs'] is True:
            print >> buf,'%s\t\t\t----beliefs:----' % (prefix)
            self.world.printState(model['beliefs'],buf,prefix+'\t\t\t',beliefs=True)
            print >> buf,'%s\t\t\t----------------' % (prefix)

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
        try:
            beliefs = self.models[model]['beliefs']
        except KeyError:
            beliefs = True
        if beliefs is True:
            beliefs = VectorDistribution({KeyedVector(): 1.})
            self.models[model]['beliefs'] = beliefs
        if isinstance(distribution,MatrixDistribution) or isinstance(distribution,KeyedMatrix):
            raise NotImplementedError,'New implementation of beliefs uses vectors, not matrices. '\
                'Distorted beliefs have not been re-implemented yet.'
        self.world.setFeature(key,distribution,beliefs)

    def getBelief(self,vector,model=None):
        """
        @param model: the model of the agent to use, default is to use model specified in the state vector
        @return: the agent's belief in the given world
        """
        if model is None:
            model = self.world.getModel(self.name,vector)
        world = VectorDistribution({vector: 1.})
        beliefs = self.getAttribute('beliefs',model)
        if not beliefs is True:
            world = world.merge(beliefs)
        return world

    def stateEstimator(self,oldReal,newReal,omega,model=True):
        # Extract belief vector (in minimal diff form)
        try:
            oldBeliefDiff = self.models[model]['beliefs']
        except KeyError:
            # No beliefs on this model, assume they get updated somewhere else
            return self.model2index(model)
        # Look for cached estimator value
        oldBelief = self.getBelief(oldReal,model)
        if not self.models[model].has_key('SE'):
            self.models[model]['SE'] = {oldBelief: {newReal: {}}}
        elif not self.models[model]['SE'].has_key(oldBelief):
            self.models[model]['SE'][oldBelief] = {newReal: {}}
        elif not self.models[model]['SE'][oldBelief].has_key(newReal):
            self.models[model]['SE'][oldBelief][newReal] = {}
        elif self.models[model]['SE'][oldBelief][newReal].has_key(omega):
            return self.models[model]['SE'][oldBelief][newReal][omega]
        # Start computing possible new worlds
        newBeliefs = VectorDistribution()
        for oldWorld in oldBeliefDiff.domain():
            # Compute probability of this observation given this start state
            probOmega = 1.
            # What actions do I think have been performed?
            joint = ActionSet()
            actionDistribution = Distribution({joint: 1.})
            actionMapping = {joint: {}}
            world = self.world.pruneModels(oldReal)
            world.update(oldWorld)
            # Consider each agent (whose turn it is)
            for actor in self.world.next(world):
                actorModel = self.world.getModel(actor,oldWorld)
                # Iterate through each joint action generated for other agents
                for joint in actionDistribution.domain():
                    actions = actionMapping[joint]
                    del actionMapping[joint]
                    probActions = actionDistribution[joint]
                    del actionDistribution[joint]
                    if omega.has_key(actor):
                        # We have observed what this agent did
                        actions[actor] = self.world.float2value(actor,omega[actor])
                        joint = joint | actions[actor]
                        actionMapping[joint] = actions
                        if not actorModel is True:
                            # If we don't have access to True model, then we may not have 100%
                            # confidence that agent would have performed the observed action
                            decision = self.world.agents[actor].decide(world,model=actorModel,
                                                                       selection='distribution')
                            if isinstance(decision['action'],Distribution):
                                probActions *= decision['action'][actions[actor]]
                            elif decision['action'] != actions[actor]:
                                probActions = 0.
                        actionDistribution[joint] = probActions
                    else:
                        # Unobserved action. To ignore action completely, uncomment the following:
#                        continue
                        # Predict what this agent *might* have snuck past our keen observations
                        decision = self.world.agents[actor].decide(world,model=actorModel,
                                                                   selection='distribution')
                        if not isinstance(decision['action'],Distribution):
                            decision['action'] = Distribution({decision['action']: 1.})
                        # Merge each possible action into overall joint action
                        for action in decision['action'].domain():
                            newJoint = joint | action
                            newActions = {actor: action}
                            newActions.update(actions)
                            actionMapping[newJoint] = newActions
                            actionDistribution[newJoint] = probActions*decision['action'][action]
            # What is the effect of those actions?
            for joint in actionDistribution.domain():
                actions = actionMapping[joint]
                if actions:
                    effect = self.world.effect(actions,world)
                else:
                    # If no observed actions, assume world is unchanged (head-in-the-sand strategy)
                    effect = {'new': VectorDistribution({world: 1.})}
                if not effect.has_key('new'):
                    continue
                # Iterate through resulting worlds
                for newWorld in effect['new'].domain():
                    newBelief = KeyedVector()
                    for key in newWorld.keys():
                        if oldWorld.has_key(key):
                            newBelief[key] = newWorld[key]
                        else:
                            if newWorld[key] != newReal[key]:
                                # This resulting state has 0 probability given my original belief
                                break
                    else:
                        # Compute joint probability of old, new, observation, etc.
                        if actions:
                            omegaDist = self.observe(newWorld,actions,model)
                        else:
                            omegaDist = VectorDistribution({KeyedVector(): 1.})
                        # Include the probability of given observation
                        newProb = omegaDist.getProb(omega)*actionDistribution[joint]*effect['new'][newWorld]
                        newBeliefs.addProb(newBelief,oldBeliefDiff[oldWorld]*newProb)
        # Find models corresponding to new beliefs
        if len(newBeliefs) == 0:
            return None
        else:
            newBeliefs.normalize()
            index = self.belief2model(model,newBeliefs)['index']
#            self.models[model]['SE'][oldBelief][newReal][omega] = index
            return index

    def printBeliefs(self,model=True):
        raise DeprecationWarning,'Use the "beliefs=True" argument to printState instead'

    """--------------------"""
    """Observation  methods"""
    """--------------------"""

    def defineObservation(self,omega,tree,actions=None,**kwargs):
        """
        @param omega: The label of this dimension of observations (e.g., an existing feature key, or a new observation dimension)
        @type omega: str
        """
        if not self.world.variables.has_key(omega):
            self.world.defineVariable(omega,**kwargs)
        self.omega.add(omega)
        if self.O is True:
            self.O = {}
        if not self.O.has_key(omega):
            self.O[omega] = {}
        self.O[omega][actions] = tree.desymbolize(self.world.symbols)

    def observe(self,vector,actions,model=True):
        """
        @return: distribution over observations received by this agent in the given world when the given actions are performed
        @rtype: L{Distribution}
        """
        if self.O is True:
            O = {}
        else:
            O = self.O
        if isinstance(actions,ActionSet):
            jointAction = actions
            if actions:
                actions = {actions['subject']: jointAction}
            else:
                actions = {}
        else:
            # Table of actions across multiple agents
            jointAction = reduce(lambda x,y: x|y,actions.values())
        # Generate observations along each dimension
        omega = {}
        for key,table in O.items():
            try:
                # Look up the observation function for the actions performed
                tree = table[jointAction]
            except KeyError:
                # Maybe a tree that applies for all possible actions
                try:
                    tree = table[None]
                except KeyError:
                    if self.world.agents.has_key(key) and not actions.has_key(key):
                        # Observation of an agent's actions, but that agent hasn't acted
                        continue
                    else:
                        # Awkward, someone defined an observation function that doesn't cover the action space
                        raise ValueError,'Observation function for %s does not cover action space' % (key)
            if actions.has_key(key):
                # Observation of action
                omega[key] = tree[vector]
            else:
                # Apply the observation function to any non-action observations
                omega[key] = self.world.float2value(key,tree[vector]*vector)
        # Keep track of potentially unobserved actions
        nulls = set()
        # Translate actions into vectors
        for key,action in actions.items():
            if not self.world.variables.has_key(key):
                self.world.defineVariable(key,ActionSet)
            if omega.has_key(key):
                if omega[key] is None or omega[key] is False:
                    # Action is unobservable
                    del omega[key]
                else:
                    if not isinstance(omega[key],Distribution):
                        omega[key] = Distribution({omega[key]: 1.})
                    for element in omega[key].domain():
                        if element is True:
                            # Action is observable
                            omega[key].replace(element,self.world.value2float(key,action))
                        elif element is False:
                            nulls.add(key)
                            omega[key].replace(element,None)
                        elif element is None:
                            # Action is potentially unobservable
                            nulls.add(key)
                        else:
                            omega[key].replace(element,self.world.value2float(key,element))
            else:
                # Assume action is observable by default
                omega[key] = self.world.value2float(key,action)
        # Generate distribution over joint observations
        jointOmega = VectorDistribution({KeyedVector(): 1.})
        for key,distribution in omega.items():
            jointOmega.join(key,distribution)
        # Prune unobserved actions
        if len(nulls) > 0:
            for observation in jointOmega.domain():
                prob = jointOmega[observation]
                del jointOmega[observation]
                for key in nulls:
                    if observation[key] is None:
                        del observation[key]
                jointOmega[observation] = prob
        return jointOmega

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
        if self.x:
            doc.documentElement.setAttribute('x',str(self.x))
            doc.documentElement.setAttribute('y',str(self.y))
        if self.color:
            doc.documentElement.setAttribute('color',self.color)
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
        if not self.O is True:
            for key,table in self.O.items():
                for actions,tree in table.items():
                    node = doc.createElement('O')
                    node.setAttribute('omega',key)
                    if actions:
                        node.appendChild(actions.__xml__().documentElement)
                    node.appendChild(tree.__xml__().documentElement)
                    root.appendChild(node)
        # Models
        for name,model in self.models.items():
            node = doc.createElement('model')
            node.setAttribute('name',str(name))
            node.setAttribute('parent',str(model['parent']))
            node.setAttribute('index',str(model['index']))
            for key in filter(lambda k: not k in ['name','index','parent'],model.keys()):
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
                            if isinstance(tree,str):
                                # Goal on another agent
                                subnode.setAttribute('name',str(tree))
                            else:
                                # PWL Goal
                                subnode.appendChild(tree.__xml__().documentElement)
                            node.appendChild(subnode)
                elif key == 'V':
                    node.appendChild(model[key].__xml__().documentElement)
                elif key == 'selection':
                    node.setAttribute('selection',str(model[key]))
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
                elif key == 'projector':
                    subnode = doc.createElement(key)
                    subnode.appendChild(doc.createTextNode(model[key].__name__))
                    node.appendChild(subnode)
                elif key == 'static':
                    subnode = doc.createElement(key)
                    subnode.setAttribute('value',str(model[key]))
                    node.appendChild(subnode)
                elif key == 'SE':
                    # We don't serialize state estimator caching right now
                    pass
                else:
                    subnode = doc.createElement(key)
                    subnode.appendChild(doc.createTextNode(str(model[key])))
                    node.appendChild(subnode)
            root.appendChild(node)
        return doc

    def parse(self,element):
        self.name = str(element.getAttribute('name'))
        try:
            self.x = int(element.getAttribute('x'))
            self.y = int(element.getAttribute('y'))
        except ValueError:
            pass
        self.color = str(element.getAttribute('color'))
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'actions':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'option'
                            self.actions.add(ActionSet(subnode))
                        subnode = subnode.nextSibling
                elif node.tagName == 'omega':
                    self.omega.add(str(node.firstChild.data).strip())
                elif node.tagName == 'O':
                    if self.O is True:
                        self.O = {}
                    omega = str(node.getAttribute('omega'))
                    if not self.O.has_key(omega):
                        self.O[omega] = {}
                    action = None
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            if subnode.tagName == 'option':
                                action = ActionSet(subnode)
                            elif subnode.tagName == 'tree':
                                tree = KeyedTree(subnode)
                        subnode = subnode.nextSibling
                    self.O[omega][action] = tree
                elif node.tagName == 'model':
                    # Parse model name
                    name = str(node.getAttribute('name'))
                    if name == 'True':
                        name = True
                    # Parse parent
                    parent = str(node.getAttribute('parent'))
                    if not parent or parent == str(None):
                        parent = None
                    elif parent == 'True':
                        parent = True
                    kwargs = {'parent': parent}
                    # Parse index
                    try:
                        kwargs['index'] = int(node.getAttribute('index'))
                    except ValueError:
                        pass
                    # Parse children
                    text = str(node.getAttribute('selection'))
                    if text == str(True):
                        kwargs['selection'] = True
                    elif text:
                        kwargs['selection'] = text
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            key = str(subnode.tagName)
                            if key == 'V':
                                kwargs[key] = ValueFunction(subnode)
                            elif key == 'static':
                                kwargs[key] = (str(subnode.getAttribute('value')) == str(True))
                            else:
                                if key == 'R' and str(subnode.getAttribute('name')):
                                    if not kwargs.has_key(key):
                                        kwargs[key] = {}
                                    # Goal on another agent's goals
                                    agent = str(subnode.getAttribute('name'))
                                    kwargs[key][agent] = float(subnode.getAttribute('weight'))
                                # Parse component elements
                                subchild = subnode.firstChild
                                while subchild:
                                    if subchild.nodeType == subchild.ELEMENT_NODE:
                                        if key == 'R':
                                            # PWL goal
                                            if not kwargs.has_key(key):
                                                kwargs[key] = {}
                                            kwargs[key][KeyedTree(subchild)] = float(subnode.getAttribute('weight'))
                                        elif key == 'policy':
                                            kwargs[key] = KeyedTree(subchild)
                                        elif key == 'beliefs':
                                            kwargs[key] = VectorDistribution(subchild)
                                        else:
                                            raise NameError,'Unknown element found when parsing model\'s %s' % (key)
                                    elif subchild.nodeType == subchild.TEXT_NODE:
                                        text = subchild.data.strip()
                                        if text:
                                            if key == 'ignore':
                                                try:
                                                    kwargs[key].append(text)
                                                except KeyError:
                                                    kwargs[key] = [text]
                                            elif text == str(True):
                                                kwargs[key] = True
                                            elif key == 'horizon':
                                                kwargs[key] = int(text)
                                            elif key == 'projector':
                                                kwargs[key] = eval('Distribution.%s' % (text))
                                            else:
                                                try:
                                                    kwargs[key] = float(text)
                                                except ValueError:
                                                    raise ValueError,'Unable to parse attribute %s of model %s'  % (key,name)
                                    subchild = subchild.nextSibling
                        subnode = subnode.nextSibling
                    # Add new model
                    self.addModel(name,**kwargs)
                elif node.tagName == 'legal':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            if subnode.tagName == 'option':
                                action = ActionSet(subnode)
                            elif subnode.tagName == 'tree':
                                tree = KeyedTree(subnode)
                        subnode = subnode.nextSibling
                    self.legal[action] = tree
            node = node.nextSibling

    @staticmethod
    def isXML(element):
        return element.tagName == 'agent'

class ValueFunction:
    """
    Representation of an agent's value function, either from caching or explicit solution
    """
    def __init__(self,xml=None):
        self.table = []
        if xml:
            self.parse(xml)

    def get(self,name,state,action,horizon,ignore=None):
        try:
            V = self.table[horizon]
        except IndexError:
            return None
        if V:
            if ignore:
                substate = state.filter(ignore)
                if V.has_key(substate):
                    value = V[substate][name][action]
                else:
                    substate = self.world.nearestVector(substate,V.keys())
                    value = V[substate][name][action]
                return value
            else:
                try:
                    value = V[state][name][action]
                    return value
                except KeyError:
                    pass
        return None

    def set(self,name,state,action,horizon,value):
        while True:
            try:
                V = self.table[horizon]
                break
            except IndexError:
                self.table.append({})
        if not V.has_key(state):
            V[state] = {}
        if not V[state].has_key(name):
            V[state][name] = {}
        V[state][name][action] = value

    def add(self,name,state,action,horizon,value):
        """
        Adds the given value to the current value function
        """
        previous = self.get(name,state,action,horizon)
        if previous is None:
            # No previous value, take it to be 0
            self.set(name,state,action,horizon,value)
        else:
            # Add given value to previous value
            self.set(name,state,action,horizon,previous+value)

    def actionTable(self,name,state,horizon):
        """
        @return: a table of values for actions for the given agent in the given state
        """
        V = self.table[horizon]
        table = dict(V[state][name])
        if table.has_key(None):
            del table[None]
        return table

    def printV(self,agent,horizon):
        V = self.table[horizon]
        for state in V.keys():
            print
            agent.world.printVector(state)
            print self.get(agent.name,state,None,horizon)

    def __lt__(self,other):
        return self.name < other.name

    def __xml__(self):
        doc = Document()
        root = doc.createElement('V')
        doc.appendChild(root)
        for horizon in range(len(self.table)):
            subnode = doc.createElement('table')
            subnode.setAttribute('horizon',str(horizon))
            for state,V_s in self.table[horizon].items():
                subnode.appendChild(state.__xml__().documentElement)
                for name,V_s_a in V_s.items():
                    for action,V in V_s_a.items():
                        subsubnode = doc.createElement('value')
                        subsubnode.setAttribute('agent',name)
                        if action:
                            subsubnode.appendChild(action.__xml__().documentElement)
                        subsubnode.appendChild(doc.createTextNode(str(V)))
                        subnode.appendChild(subsubnode)
            root.appendChild(subnode)
        return doc

    def parse(self,element):
        assert element.tagName == 'V',element.tagName
        del self.table[:]
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert node.tagName == 'table',node.tagName
                horizon = int(node.getAttribute('horizon'))
                subnode = node.firstChild
                while subnode:
                    if subnode.nodeType == subnode.ELEMENT_NODE:
                        if subnode.tagName == 'vector':
                            state = KeyedVector(subnode)
                        elif subnode.tagName == 'value':
                            action = None
                            agent = str(subnode.getAttribute('agent'))
                            subsubnode = subnode.firstChild
                            while subsubnode:
                                if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
                                    if subsubnode.tagName == 'option':
                                        actions = []
                                        bottomNode = subsubnode.firstChild
                                        while bottomNode:
                                            if bottomNode.nodeType == bottomNode.ELEMENT_NODE:
                                                actions.append(Action(bottomNode))
                                            bottomNode = bottomNode.nextSibling
                                        action = ActionSet(actions)
                                elif subsubnode.nodeType == subsubnode.TEXT_NODE:
                                    text = subsubnode.data.strip()
                                    if text:
                                        value = float(text)
                                subsubnode = subsubnode.nextSibling
                            self.set(agent,state,action,horizon,value)
                    subnode = subnode.nextSibling
            node = node.nextSibling
