import bz2
import copy

import StringIO
from xml.dom.minidom import Document,Node,parseString

from action import ActionSet,Action
from pwl import *
from probability import Distribution
from agent import Agent

class World:
    """
    @ivar agents: table of agents in this world, indexed by name
    @type agents: strS{->}L{Agent}
    @ivar state: the distribution over states of the world
    @type state: strS{->}L{VectorDistribution}
    @ivar variables: definitions of the domains of possible variables (state features, relationships, observations)
    @type variables: dict
    @ivar symbols: utility storage of symbols used across all enumerated state variables
    @type symbols: strS{->}int
    @ivar dynamics: table of action effect models
    @type dynamics: dict
    @ivar dependency: table of dependencies among state features that impose temporal constraints
    @type dependency: dict
    @ivar history: accumulated list of outcomes from simulation steps
    @type history: list
    @ivar termination: list of conditions under which the simulation terminates (default is none)
    @type termination: L{KeyedTree}[]
    """
    memory = True

    def __init__(self,xml=None):
        """
        @param xml: Initialization argument, either an XML Element, or a filename
        @type xml: Node or str
        """
        self.agents = {}

        # State feature information
        self.state = {None: VectorDistribution()}
        self.variables = {}
        self.locals = {}
        self.symbols = {}
        self.symbolList = []
        self.termination = []
        self.relations = {}

        self.maxTurn = None

        # Action effect information
        self.dynamics = {}
        self.dependency = {}
        self.graph = {}
        self.evaluationOrder = [set()]

        self.history = []

        self.diagram = None

        if isinstance(xml,Node):
            self.parse(xml)
        elif isinstance(xml,str) or isinstance(xml,unicode):
            if xml[-4:] == '.xml':
                # Uncompressed
                f = open(xml,'r')
            else:
                if xml[-4:] != '.psy':
                    xml = '%s.psy' % (xml)
                f = bz2.BZ2File(xml,'r')
            doc = parseString(f.read())
            f.close()
            self.parse(doc.documentElement)
        else:
            self.state[None][KeyedVector({CONSTANT: 1.})] = 1.

    def initialize(self):
        self.agents.clear()
        self.variables.clear()
        self.locals.clear()
        self.relations.clear()
        self.symbols.clear()
        del self.symbolList[:]
        self.dynamics.clear()
        self.dependency.clear()
        del self.evaluationOrder[:]
        self.evaluationOrder.append(set())
        del self.history[:]
        del self.termination[:]
        self.state.clear()

    """------------------"""
    """Simulation methods"""
    """------------------"""
    
    def step(self,actions=None,state=None,real=True,select=True,keys=None):
        """
        The simulation method
        @param actions: optional argument setting a subset of actions to be performed in this turn
        @type actions: strS{->}L{ActionSet}
        @param state: optional initial state distribution (default is the current world state distribution)
        @type state: L{VectorDistribution}
        @param real: if C{True}, then modify the given state; otherwise, this is only hypothetical (default is C{True})
        @type real: bool
        """
        if state is None:
            state = self.state[None]
        outcomes = []
        # Iterate through each possible world
        oldStates = state.domain()
        for stateVector in oldStates:
            prob = state[stateVector]
            outcome = self.stepFromState(stateVector,actions,keys=keys)
            outcome['probability'] = prob
            outcomes.append(outcome)
        if real:
            # Apply effects
            assert keys is None,'Cannot perform real step over a subset of keys'
            state.clear()
            for outcome in outcomes:
                if not outcome.has_key('new'):
                    # No effect. Just keep moving
                    continue
                elif isinstance(outcome['new'],Distribution):
                    if select:
                        new = outcome['new'].sample()
                        dist = [(new,1.)]
                    else:
                        dist = map(lambda el: (el,outcome['new'][el]),outcome['new'].domain())
                else:
                    dist = [(outcome['new'],1.)]
                for new,prob in dist:
                    try:
                        state[new] += prob*outcome['probability']
                    except KeyError:
                        state[new] = prob*outcome['probability']
            if len(state) == 0:
                # This is the safest place to detect an inconsistency
                buf = StringIO.StringIO()
                print >> buf,'Unable to find consistent transition when actions:'
                print >> buf,' and '.join([str(ActionSet(outcome['actions'])) for outcome in outcomes])
                print >> buf,'are performed in states:'
                for stateVector in oldStates:
                    self.printVector(stateVector,buf)
                msg = buf.getvalue()
                buf.close()
                raise RuntimeError,msg
            if self.memory:
                self.history.append(outcomes)
            self.modelGC(False)
        return outcomes

    def stepFromState(self,vector,actions=None,horizon=None,tiebreak=None,updateBeliefs=True,keys=None):
        """
        Compute the resulting states when starting in a given possible world (as opposed to a distribution over possible worlds)
        """
        outcome = {'old': vector,
                   'decisions': {}}
        # Check whether we are already in a terminal state
        if self.terminated(vector):
            outcome['new'] = outcome['old']
            return outcome
        # Determine the actions taken by the agents in this world
        if actions is None:
            outcome['actions'] = {}
        else:
            if isinstance(actions,Action):
                actions = ActionSet([actions])
            outcome['actions'] = copy.copy(actions)
        # Keep track of whether there is uncertainty about the actions to perform
        stochastic = []
        if not isinstance(outcome['actions'],ActionSet) and not isinstance(outcome['actions'],list):
            # ActionSet indicates that we should perform just these actions. 
            # Otherwise, we look at whose turn it is:
            turn = self.next(vector)
            for name in outcome['actions'].keys():
                if not (name in turn):
                    raise NameError,'Agent %s must wait for its turn' % (name)
            for name in turn:
                if not outcome['actions'].has_key(name):
                    model = self.getModel(name,vector)
                    decision = self.agents[name].decide(vector,horizon,outcome['actions'],model,tiebreak)
                    outcome['decisions'][name] = decision
                    outcome['actions'][name] = decision['action']
                elif isinstance(outcome['actions'][name],Action):
                    outcome['actions'][name] = ActionSet([outcome['actions'][name]])
                if isinstance(outcome['actions'][name],Distribution):
                    stochastic.append(name)
        if stochastic:
            # Merge effects of multiple possible actions into single effect
            if len(stochastic) > 1:
                raise NotImplementedError,'Currently unable to handle stochastic expectations over multiple agents: %s' % (stochastic)
            effects = []
            for action in outcome['actions'][stochastic[0]].domain():
                prob = outcome['actions'][stochastic[0]][action]
                actions = dict(outcome['actions'])
                actions[stochastic[0]] = action 
                effect = self.effect(actions,outcome['old'],prob,updateBeliefs=updateBeliefs,keys=keys)
                if len(effect) == 0:
                    # No consistent transition for this action (don't blame me, I'm just the messenger)
                    continue
                elif outcome.has_key('new'):
                    for vector in effect['new'].domain():
                        try:
                            outcome['new'][vector] += effect['new'][vector]
                        except KeyError:
                            outcome['new'][vector] = effect['new'][vector]
                    outcome['effect'] += effect['effect']
                else:
                    outcome['new'] = effect['new']
                    outcome['effect'] = effect['effect']
        else:
            effect = self.effect(outcome['actions'],outcome['old'],1.,updateBeliefs,keys)
            outcome.update(effect)
        if outcome.has_key('effect'):
            if not outcome.has_key('new'):
                # Apply effects
                outcome['new'] = outcome['effect']*outcome['old']
            if not outcome.has_key('delta'):
                outcome['delta'] = outcome['new'] - outcome['old']
        else:
            # No consistent effect
            pass
        return outcome

    def effect(self,actions,vector,probability=1.,updateBeliefs=True,keys=None):
        """
        @param probability: the likelihood of this particular action set (default is 100%)
        @type probability: float
        """
        result = {'effect': [],
                  'new': VectorDistribution({vector: probability})}
        result['new'] = self.deltaState(actions,result['new'],result['effect'],keys)
        # Update turn order
        delta = self.deltaOrder(actions,vector)
        if delta:
            result['effect'].append(delta)
            new = VectorDistribution()
            for old in result['new'].domain():
                newVector = KeyedVector(old)
                newVector.update(delta*old)
                new.addProb(newVector,result['new'][old])
            result['new'] = new
        # Update agent models included in the original world (after finding out possible new worlds)
        agentsModeled = [name for name in self.agents.keys() if vector.has_key(modelKey(name)) and \
                             (keys is None or modelKey(name) in keys)]
        for name in agentsModeled:
            result['SE %s' % (name)] = {}
        if agentsModeled:
            delta = MatrixDistribution({KeyedMatrix(): 1.})
            for newVector in result['new'].domain():
                # Update the agent model under each possible outcome
                for name in agentsModeled:
                    key = modelKey(name)
                    agent = self.agents[name]
                    oldModel = self.getModel(name,vector)
                    if not agent.models[oldModel].has_key('beliefs') or \
                            agent.models[oldModel]['beliefs'] is True or \
                            agent.getAttribute('static',oldModel):
                        # No need to update the model
                        modelDistribution = KeyedMatrix({key: KeyedVector({key: 1})})
                    else:
                        # Imperfect beliefs need to be updated
                        omegaDistribution = agent.observe(newVector,actions)
                        modelDistribution = MatrixDistribution()
                        if result['SE %s' % (name)].has_key(oldModel):
                            raise NotImplementedError,'Unable to re-merge beliefs'
                        else:
                            result['SE %s' % (name)][oldModel] = {}
                        for omega in omegaDistribution.domain():
                            newModel = agent.stateEstimator(vector,newVector,omega,oldModel)
                            result['SE %s' % (name)][oldModel][omega] = newModel
                            if newModel is None:
                                pass
                            else:
                                matrix = KeyedMatrix({key: KeyedVector({CONSTANT: newModel})})
                                modelDistribution.addProb(matrix,omegaDistribution[omega])
                    if len(modelDistribution) > 0:
                        delta.update(modelDistribution)
            for matrix in delta.domain():
                errors = [name for name in agentsModeled if not matrix.has_key(modelKey(name))]
                if errors:
                    # Some agents have no consistent belief update
                    del delta[matrix]
            if delta:
                delta.normalize()
                result['effect'].append(delta)
                new = VectorDistribution()
                for old in result['new'].domain():
                    newVector = KeyedVector(old)
                    for matrix in delta.domain():
                        newVector.update(matrix*old)
                        new.addProb(newVector,result['new'][old]*delta[matrix])
                result['new'] = new
            else:
                # No possible transition at all!
                result.clear()
        return result

    def multiDeltaVector(self,actions,old,keys):
        new = VectorDistribution({old: 1.})
        for key in keys:
            partial = self.singleDeltaVector(actions,old,key)
            if isinstance(partial,KeyedVector):
                if partial.has_key(key):
                    new.join(key,Distribution({partial[key]: 1.}))
            else:
                new.join(key,partial.marginal(key))
        return new

    def singleDeltaVector(self,actions,old,key,dynamics=None):
        """
        @type old: L{KeyedVector}
        """
        assert isinstance(old,KeyedVector)
        if dynamics is None:
            dynamics = self.getDynamics(key,actions,old)
        if dynamics:
            if len(dynamics) == 1:
                # Single effect
                matrix = dynamics[0][old]
                if matrix is None:
                    # Null effect
                    return old
                else:
                    newValue = matrix*old
                if isinstance(newValue,KeyedVector):
                    # Deterministic effect
                    new = KeyedVector(old)
                    new.update(newValue)
                else:
                    # Stochastic effect
                    new = VectorDistribution({old: 1.})
                    if not isinstance(newValue,VectorDistribution):
                        # We're going to just go ahead and treat the result as a VectorDistribution,
                        # because we don't play by your rules
                        newValue = VectorDistribution(newValue)
                    new.join(key,newValue.marginal(key))
                return new
            else:
                # Multiply deltas in sequence (expand branches as necessary in the future)
                assert self.variables[key]['combinator'] == '*',\
                    'No valid combinator specified for multiple effects on %s' % (key)
                for tree in dynamics:
                    # Iterate through each tree (possibly ordered)
                    if isinstance(old,KeyedVector):
                        # Certain state
                        old = self.singleDeltaVector(actions,old,key,[tree])
                    else:
                        # Uncertain state
                        new = VectorDistribution()
                        for oldVector in old.domain():
                            partial = self.singleDeltaVector(actions,oldVector,key,[tree])
                            if isinstance(partial,KeyedVector):
                                # Deterministic effect
                                new.addProb(partial,old[oldVector])
                            else:
                                # Stochastic effect
                                for newVector in partial.domain():
                                    new.addProb(newVector,old[oldVector]*partial[newVector])
                        old = new
                return old
        else:
            return old
        
    def deltaState(self,actions,old,effects,keys=None):
        """
        Computes the change across a subset of state features
        """
        for keySet in self.evaluationOrder:
            if not keys is None:
                keySet = {k for k in keySet if k in keys}
            new = VectorDistribution()
            for oldVector in old.domain():
                partial = self.multiDeltaVector(actions,oldVector,keySet)
                for newVector in partial.domain():
                    new.addProb(newVector,old[oldVector]*partial[newVector])
            old = new
            effects.append(MatrixDistribution({KeyedMatrix(): 1.}))
        return new

    def addTermination(self,tree):
        """
        Adds a possible termination condition to the list
        """
        self.termination.append(tree.desymbolize(self.symbols))

    def terminated(self,state=None):
        """
        Evaluates world states with respect to termination conditions
        @param state: the state vector (or distribution thereof) to evaluate (default is the current world state)
        @type state: L{KeyedVector} or L{VectorDistribution}
        @return: C{True} iff the given state (or all possible worlds if a distribution) satisfies at least one termination condition
        @rtype: bool
        """
        if state is None:
            for state in self.state.values():
                if self.terminated(state):
                    # If any local state is terminated, the whole system is terminated
                    return True
            else:
                # No local states satisfy a termination condition
                return False
        if isinstance(state,VectorDistribution):
            # All possible worlds must be terminal states
            for vector in state.domain():
                if not self.terminated(vector):
                    return False
            else:
                return True
        else:
            assert isinstance(state,KeyedVector)
            for condition in self.termination:
                if condition[state]:
                    return True
            else:
                return False

    """-----------------"""
    """Authoring methods"""
    """-----------------"""

    def addAgent(self,agent):
        if self.has_agent(agent):
            raise NameError,'Agent %s already exists in this world' % (agent.name)
        if isinstance(agent,str):
            agent = Agent(agent)
        self.agents[agent.name] = agent
        agent.world = self
        return agent

    def has_agent(self,agent):
        """
        @param agent: The agent (or agent name) to look for
        @type agent: L{Agent} or str
        @return: C{True} iff this C{World} already has an agent with the same name
        @rtype: bool
        """
        if isinstance(agent,str):
            return self.agents.has_key(agent)
        else:
            return self.agents.has_key(agent.name)

    def setTurnDynamics(self,name,action,tree):
        """
        Convenience method for setting custom dynamics for the turn order
        @param name: the name of the agent whose turn dynamics are being set
        @type name: str
        @param action: the action affecting the turn order
        @type action: L{Action} or L{ActionSet}
        @param tree: the decision tree defining the effect on this agent's turn order
        @type tree: L{KeyedTree}
        """
        if self.maxTurn is None:
            raise ValueError,'Call setOrder before setting turn dynamics'
        key = turnKey(name)
        if not self.variables.has_key(key):
            self.defineVariable(key,int,hi=self.maxTurn,evaluate=False)
        self.setDynamics(key,action,tree)

    def setDynamics(self,key,action,tree,enforceMin=False,enforceMax=False):
        """
        Defines the effect of an action on a given state feature
        @param key: the key of the affected state feature
        @type key: str
        @param action: the action affecting the state feature
        @type action: L{Action} or L{ActionSet}
        @param tree: the decision tree defining the effect
        @type tree: L{KeyedTree}
        """
        if isinstance(action,str):
            raise TypeError,'Incorrect action type in setDynamics call, perhaps due to change in method definition. Please use a key string as the first argument, rather than the more limiting entity/feature combination.'
        if not isinstance(action,ActionSet) and not action is True:
            if not isinstance(action,Action):
                # dict -> Action
                action = Action(action)
            # Action -> ActionSet
            action = ActionSet([action])
        assert self.variables.has_key(key),'No state element "%s"' % (key) 
        if not action is True:
            for atom in action:
                assert self.agents.has_key(atom['subject']),'Unknown actor %s' % (atom['subject'])
                assert self.agents[atom['subject']].hasAction(atom),'Unknown action %s' % (atom)
        if not self.dynamics.has_key(key):
            self.dynamics[key] = {}
        # Translate symbolic names into numeric values
        tree = tree.desymbolize(self.symbols)
        if enforceMin and self.variables[key]['domain'] in [int,float]:
            # Modify tree to enforce floor
            tree.floor(key,self.variables[key]['lo'])
        if enforceMax and self.variables[key]['domain'] in [int,float]:
            # Modify tree to enforce ceiling
            tree.ceil(key,self.variables[key]['hi'])
        self.dynamics[key][action] = tree

    def getDynamics(self,key,action,state=None):
        if not self.dynamics.has_key(key):
            return []
        if isinstance(action,Action):
            return self.getDynamics(key,ActionSet([action]),state)
        elif not isinstance(action,ActionSet) and not isinstance(action,list):
            # Table of actions by multiple agents
            return self.getDynamics(key,ActionSet(action),state)
        error = None
        try:
            return [self.dynamics[key][action]]
        except KeyError:
            error = 'key'
        except TypeError:
            error = 'type'
        if error:
            dynamics = []
            for atom in action:
                try:
                    dynamics.append(self.dynamics[key][ActionSet([atom])])
                except KeyError:
                    if len(atom) > len(atom.special):
                        # Extra parameters
                        try:
                            tree = self.dynamics[key][ActionSet([atom.root()])]
                        except KeyError:
                            tree = None
                        if tree:
                            table = {}
                            for field in atom.getParameters():
                                table[actionKey(field)] = atom[field]
                            dynamics.append(tree.desymbolize(table))
            if len(dynamics) == 0:
                # No action-specific dynamics, fall back to default dynamics
                if self.dynamics[key].has_key(True):
                    dynamics.append(self.dynamics[key][True])
            return dynamics

    def addDependency(self,dependent,independent):
        """
        Adds a dependency between the dependent key and the independent key, indicating that the new value for the independent key should be determined first
        @type dependent: str
        @type independent: str
        """
        try:
            self.dependency[dependent][independent] = True
        except KeyError:
            self.dependency[dependent] = {independent: True}
        foundDep = False
        foundInd = False
        for entry in self.evaluationOrder:
            if foundDep:
                if foundInd:
                    # Independent was earlier, so we can stick dependent variable here and exit
                    entry.add(dependent)
                    break
                elif independent in entry:
                    # We have now found independent variable
                    foundInd = True
            else:
                if dependent in entry:
                    if not foundInd:
                    # Dependent is in the same or earlier time frame
                        entry.remove(dependent)
                    foundDep = True
                if independent in entry:
                    # Here is the independent variable
                    foundInd = True
                    if not foundDep:
                        # Dependent is somewhere later, so we're ok
                        break
        else:
            # Need to add another entry
            self.evaluationOrder.append(set([dependent]))

    """------------------"""
    """Turn order methods"""
    """------------------"""

    def setOrder(self,order):
        """
        Initializes the turn order to the given order
        @param order: the turn order, as a list of names (each agent acts in sequence) or a list of sets of names (agents within a set acts in parallel)
        @type order: str[] or {str}[]
        """
        for index in range(len(order)):
            if isinstance(order[index],set):
                names = order[index]
            else:
                names = [order[index]]
            for name in names:
                self.state[None].join(turnKey(name),index)
        self.maxTurn = len(order) - 1

    def next(self,vector=None):
        """
        @return: a list of agents (by name) whose turn it is in the current epoch
        @rtype: str[]
        """
        if vector is None:
            assert len(self.state[None]) == 1,'Ambiguous state vector'
            vector = self.state[None].domain()[0]
        items = filter(lambda i: isTurnKey(i[0]),vector.items())
        if len(items) == 0:
            # No turn information in vector
            return []
        value = min(map(lambda i: int(i[1]),items))
        return map(lambda i: turn2name(i[0]),filter(lambda i: int(i[1]) == value,items))

    def deltaOrder(self,actions,vector):
        """
        @warning: assumes that no one is acting out of turn
        @return: the new turn sequence resulting from the performance of the given actions
        """
        potentials = [name for name in self.agents.keys() if vector.has_key(turnKey(name))]
        if self.maxTurn is None:
            self.maxTurn = max([vector[turnKey(name)] for name in potentials])
        # Figure out who has acted
        if isinstance(actions,ActionSet):
            table = {}
            for atom in actions:
                try:
                    table[atom['subject']].add(atom)
                except KeyError:
                    table[atom['subject']] = ActionSet(atom)
        elif isinstance(actions,dict):
            table = actions
            actions = ActionSet()
            for atom in table.values():
                actions = actions | atom
        else:
            assert isinstance(actions,list)
            actionList = actions
            table = {}
            actions = set()
            for atom in actionList:
                table[atom['subject']] = True
                actions.add(atom)
            actions = ActionSet(actions)
        # Find dynamics for each turn
        delta = KeyedMatrix()
        for name in potentials:
            key = turnKey(name)
            dynamics = self.getDynamics(key,actions,vector)
            if len(dynamics) == 0:
                # Create default dynamics
                if table.has_key(name):
                    tree = makeTree({'if': thresholdRow(key,0.5),
                                     True: incrementMatrix(key,-1),
                                     False: setToConstantMatrix(key,self.maxTurn)})
                else:
                    tree = makeTree(incrementMatrix(key,-1))
                self.setTurnDynamics(name,actions,tree)
                dynamics = [tree]
            # Combine any turn dynamics into single matrix
            matrix = dynamics[0][vector]
            assert isinstance(matrix,KeyedMatrix),'Dynamics must be deterministic'
            delta.update(matrix)
        return delta

    def getActions(self,vector,agents=None,actions=None):
        """
        @return: the set of all possible action combinations that could happen in the given state
        @rtype: set(L{ActionSet})
        """
        if agents is None:
            agents = self.next(vector)
        if actions is None:
            actions = set([ActionSet()])
        if len(agents) > 0:
            newActions = set()
            name = agents.pop()
            for subset in actions:
                for action in self.agents[name].getActions(vector):
                    newActions.add(subset | action)
            return self.getActions(vector,agents,newActions)
        else:
            return actions
                    
    """-------------"""
    """State methods"""
    """-------------"""

    def defineVariable(self,key,domain=float,lo=-1.,hi=1.,description=None,combinator=None,evaluate=True):
        """
        Define the type and domain of a given element of the state vector
        @param key: string label for the column being defined
        @type key: str
        @param domain: the domain of values for this feature. Acceptable values are:
           - float: continuous range
           - int: discrete numeric range
           - bool: True/False value
           - list: enumerated set of discrete values
           - ActionSet: enumerated set of actions, of the named agent (as key)
        @type domain: class
        @param lo: for float/int features, the lowest possible value. for list features, a list of possible values.
        @type lo: float/int/list
        @param hi: for float/int features, the highest possible value
        @type hi: float/int
        @param description: optional text description explaining what this state feature means
        @type description: str
        @param combinator: how should multiple dynamics for this variable be combined
        """
        if self.variables.has_key(key):
            raise NameError,'Variable %s already defined' % (key)
        if key[-1] == "'":
            raise ValueError,'Ending single-quote reserved for indicating future state'
        self.variables[key] = {'domain': domain,
                               'description': description,
                               'combinator': combinator}
        if domain is float:
            self.variables[key].update({'lo': lo,'hi': hi})
        elif domain is int:
            self.variables[key].update({'lo': int(lo),'hi': int(hi)})
        elif domain is list or domain is set:
            assert isinstance(lo,list) or isinstance(lo,set),\
                'Please provide set/list of elements for features of the set/list type'
            self.variables[key].update({'elements': lo,'lo': None,'hi': None})
            for element in lo:
                if not self.symbols.has_key(element):
                    self.symbols[element] = len(self.symbols)
                    self.symbolList.append(element)
        elif domain is bool:
            self.variables[key].update({'lo': None,'hi': None})
        elif domain is ActionSet:
            # The actions of an agent
            if isinstance(lo,float):
                assert self.agents.has_key(key)
                lo = self.agents[key].actions
            self.variables[key].update({'elements': lo,'lo': None,'hi': None})
            for action in lo:
                self.symbols[action] = len(self.symbols)
                self.symbolList.append(action)
                assert self.symbolList[self.symbols[action]] == action
        else:
            raise ValueError,'Unknown domain type %s for %s' % (domain,key)
        self.variables[key]['key'] = key
        if evaluate:
            self.evaluationOrder[0].add(key)

    def setFeature(self,key,value,state=None):
        """
        Set the value of an individual element of the state vector
        @param key: the label of the element to set
        @type key: str
        @type value: float or L{Distribution}
        @param state: the state distribution to modify (default is the current world state)
        @type state: L{VectorDistribution}
        """
        assert self.variables.has_key(key),'Unknown element "%s"' % (key)
        if state is None:
            state = self.state[None]
        state.join(key,self.value2float(key,value))

    def encodeVariable(self,key,value):
        raise DeprecationWarning,'Use value2float method instead'

    def float2value(self,key,flt):
        if isinstance(flt,Distribution):
            # Decode each element
            value = flt.__class__()
            for element in flt.domain():
                newElement = self.float2value(key,element)
                try:
                    value[newElement] += flt[element]
                except KeyError:
                    value[newElement] = flt[element]
            return value
        elif self.variables[key]['domain'] is bool:
            if flt > 0.5:
                return True
            else:
                return False
        elif self.variables[key]['domain'] is list or self.variables[key]['domain'] is set or \
                self.variables[key]['domain'] is ActionSet:
            index = int(float(flt)+0.1)
            return self.symbolList[index]
        elif self.variables[key]['domain'] is int:
            return int(flt)
        else:
            return flt

    def value2float(self,key,value):
        """
        @return: the float value (appropriate for storing in a L{KeyedVector}) corresponding to the given (possibly symbolic, bool, etc.) value
        """
        if isinstance(value,Distribution):
            # Encode each element
            newValue = value.__class__()
            for element in value.domain():
                newElement = self.value2float(key,element)
                try:
                    newValue[newElement] += value[element]
                except KeyError:
                    newValue[newElement] = value[element]
            return newValue
        elif self.variables[key]['domain'] is bool:
            if value:
                return 1.
            else:
                return 0.
        elif self.variables[key]['domain'] is list or self.variables[key]['domain'] is set or \
                self.variables[key]['domain'] is ActionSet:
            return self.symbols[value]
        else:
            return value

    def getFeature(self,key,state=None):
        """
        @param key: the label of the state element of interest
        @type key: str
        @param state: the distribution over possible worlds (default is the current world state)
        @type state: L{VectorDistribution}
        @return: a distribution over values for the given feature
        @rtype: L{Distribution}
        """
        if state is None:
            state = self.state[None]
        assert self.variables.has_key(key),'Unknown element "%s"' % (key)
        return self.float2value(key,state.marginal(key))

    def getValue(self,key,state=None):
        """
        Helper method that returns a single value from a vector or a singleton distribution
        @param key: the label of the state element of interest
        @type key: str
        @param state: the distribution over possible worlds (default is the current world state)
        @type state: L{VectorDistribution} or L{KeyedVector}
        @return: a single value for the given feature
        """
        if state is None:
            state = self.state[None]
        assert self.variables.has_key(key),'Unknown element "%s"' % (key)
        if isinstance(state,KeyedVector):
            return self.float2value(key,state[key])
        else:
            assert len(state.domain()) == 1,'getValue operates on only singleton distributions'
            return self.float2value(key,state.domain()[0][key])

    def decodeVariable(self,key,distribution):
        raise DeprecationWarning,'Use float2value method instead'

    def defineState(self,entity,feature,domain=float,lo=0.,hi=1.,description=None,combinator=None):
        """
        Defines a state feature associated with a single agent, or with the global world state.
        @param entity: if C{None}, the given feature is on the global world state; otherwise, it is local to the named agent
        @type entity: str
        """
        key = stateKey(entity,feature)
        try:
            self.locals[entity][feature] = key
        except KeyError:
            self.locals[entity] = {feature: key}
        if not domain is None:
            # Haven't defined this feature yet
            self.defineVariable(key,domain,lo,hi,description,combinator)
        return key

    def setState(self,entity,feature,value,state=None):
        """
        For backward compatibility
        @param entity: the name of the entity whose state feature we're setting (does not have to be an agent)
        @type entity: str
        @type feature: str
        """
        self.setFeature(stateKey(entity,feature),value,state)

    def getState(self,entity,feature,state=None):
        """
        For backward compatibility
        @param entity: the name of the entity of interest (C{None} if the feature of interest is of the world itself)
        @type entity: str
        @param feature: the state feature of interest
        @type feature: str
        """
        return self.getFeature(stateKey(entity,feature),state)

    def defineRelation(self,subj,obj,name,domain=float,lo=0.,hi=1.,description=None):
        """
        Defines a binary relationship between two agents
        @param subj: one of the agents in the relation (if a directed link, it is the "origin" of the edge)
        @type subj: str
        @param obj: one of the agents in the relation (if a directed link, it is the "destination" of the edge)
        @type obj: str
        @param name: the name of the relation (e.g., the verb to use between the subject and object)
        @type name: str
        """
        key = binaryKey(subj,obj,name)
        try:
            self.relations[name][key] = {'subject': subj,'object': obj}
        except KeyError:
            self.relations[name] = {key: {'subject': subj,'object': obj}}
        if not domain is None:
            # Haven't defined this feature yet
            self.defineVariable(key,domain,lo,hi,description)
        return key

    """------------------"""
    """Mental model methods"""
    """------------------"""

    def getModel(self,modelee,vector):
        """
        @return: the name of the model of the given agent indicated by the given state vector
        @type modelee: str
        @type vector: L{KeyedVector}
        @rtype: str
        """
        agent = self.agents[modelee]
        try:
            model = agent.index2model(vector[modelKey(modelee)])
        except KeyError:
            model = True
        return model

    def getMentalModel(self,modelee,vector):
        raise DeprecationWarning,'Substitute getModel instead (sorry for pedanticism, but a "model" may be real, not "mental")'

    def setModel(self,modelee,distribution,state=None,model=True):
        # Make sure distribution is probability distribution over floats
        if not isinstance(distribution,dict):
            distribution = {distribution: 1.}
        if not isinstance(distribution,Distribution):
            distribution = Distribution(distribution)
        for element in distribution.domain():
            if not isinstance(element,float):
                distribution.replace(element,float(self.agents[modelee].model2index(element)))
        distribution.normalize()
        key = modelKey(modelee)
        if not self.variables.has_key(key):
            self.defineVariable(key)
        if isinstance(state,str):
            # This is the name of the modeling agent (*cough* hack *cough*)
            self.agents[state].setBelief(key,distribution,model)
        else:
            # Otherwise, assume we're changing the model in the current state
            self.setFeature(key,distribution,state)
        
    def setMentalModel(self,modeler,modelee,distribution,model=True):
        """
        Sets the distribution over mental models one agent has of another entity
        @note: Normalizes the distribution given
        """
        self.setModel(modelee,distribution,modeler,model)

    def pruneModels(self,vector):
        """
        Do you want a version of a possible world *without* all the fuss of agent models?
        Then *this* is the method for you!
        """
        return KeyedVector({key: vector[key] for key in vector.keys() if not isModelKey(key)})

    def modelGC(self,check=False):
        """
        Garbage collect orphaned models.
        """
        if check:
            # Record initial indices for verification purposes
            indices = {}
            for name,agent in self.agents.items():
                indices[name] = {}
                for label,model in agent.models.items():
                    indices[name][label] = agent.model2index(label)
                    assert agent.index2model(indices[name][label]) == label
        # Keep track of which models are active for each agent and who their parent models are
        parents = {}
        children = {}
        for name in self.agents.keys():
            parents[name] = {}
            children[name] = set()
        # Start with the worlds in the current state
        remaining = self.state[None].domain()
        realWorld = True
        while len(remaining) > 0:
            newRemaining = []
            for vector in remaining:
                # Look for models of each agent
                for name,agent in self.agents.items():
                    key = modelKey(name)
                    if vector.has_key(key):
                        # This world specifies an active model
                        model = agent.index2model(vector[key])
                    elif realWorld:
                        # No explicit specification, so assume True
                        model = True
                    else:
                        model = None
                    if model:
                        children[name].add(model)
                        try:
                            parents[name][agent.models[model]['parent']].append(model)
                        except KeyError:
                            parents[name][agent.models[model]['parent']] = [model]
                        if agent.models[model].has_key('beliefs'):
                            while not isinstance(agent.models[model]['beliefs'],VectorDistribution):
                                # Beliefs are symbolic link to another model
                                model = agent.models[model]['beliefs']
                                if model in children[name]:
                                    # Already processed this model
                                    break
                                else:
                                    children[name].add(model)
                            else:
                                # Recurse into the worlds within this agent's subjective view
                                newRemaining += agent.models[model]['beliefs'].domain()
            realWorld = False
            remaining = newRemaining
        # Remove inactive models
#        for name,active in children.items():
#            agent = self.agents[name]
#            for model in agent.models.keys():
#                if not model in active and not parents[name].has_key(model):
#                    # Inactive model with no dependencies
#                    agent.deleteModel(model)
        if check:
            # Verify final indices
            for name,agent in self.agents.items():
                for label,model in agent.models.items():
                    assert indices[name][label] == agent.model2index(label)
                    assert agent.index2model(indices[name][label]) == label

    def updateModels(self,outcome,vector):
        for agent in self.agents.values():
            label = self.getModel(agent.name,vector)
            model = agent.models[label]
            if not model['beliefs'] is True:
                omega = agent.observe(vector,outcome['actions'])
                beliefs = model['beliefs']
                if not omega is True:
                    raise NotImplementedError,'Unable to update mental models under partial observability'
                for actor,actions in outcome['actions'].items():
                    # Consider each agent who *did* act
                    actorKey = modelKey(actor)
                    if beliefs.hasColumn(actorKey):
                        # Agent has uncertain beliefs about this actor
                        belief = beliefs.marginal(actorKey)
                        prob = {}
                        for index in belief.domain():
                            # Consider the hypothesis mental models of this actor
                            hypothesis = self.agents[actor].models[self.agents[actor].index2model(index)]
                            denominator = 0.
                            V = {}
                            state = KeyedVector(outcome['old'])
                            state[actorKey] = index
                            for alternative in self.agents[actor].getActions(outcome['old']):
                                # Evaluate all available actions with respect to the hypothesized mental model
                                V[alternative] = self.agents[actor].value(state,alternative,model=hypothesis['name'])['V']
                            if not V.has_key(actions):
                                # Agent performed a non-prescribed action
                                V[actions] = self.agents[actor].value(state,alternative,model=hypothesis['name'])['V']
                            # Convert into probability distribution of observed action given hypothesized mental model
                            behavior = Distribution(V,hypothesis['rationality'])
                            prob[index] = behavior[actions]
                            # Bayes' rule
                            prob[index] *= belief[index]
                        # Update posterior beliefs over mental models
                        prob = Distribution(prob)
                        prob.normalize()
                        belief = MatrixDistribution()
                        for element in prob.domain():
                            belief[setToConstantMatrix(actorKey,element)] = prob[element]
                        model['beliefs'].update(belief)

    def scaleState(self,vector):
        """
        Normalizes the given state vector so that all elements occur in [0,1]
        @param vector: the vector to normalize
        @type vector: L{KeyedVector}
        @return: the normalized vector
        @rtype: L{KeyedVector}
        """
        result = vector.__class__()
        remaining = dict(vector)
        # Handle defined state features
        for key,entry in self.variables.items():
            if remaining.has_key(key):
                new = scaleValue(remaining[key],entry)
                result[key] = new
                del remaining[key]
        for name in self.agents.keys():
            # Handle turns
            key = turnKey(name)
            if remaining.has_key(key):
                result[key] = remaining[key] / len(self.agents)
                del remaining[key]
            # Handle models
            key = modelKey(name)
            if remaining.has_key(key):
                result[key] = remaining[key] / len(self.agents[name].models)
                del remaining[key]
        # Handle constant term
        if remaining.has_key(CONSTANT):
            result[CONSTANT] = remaining[CONSTANT]
            del remaining[CONSTANT]
        if remaining:
            raise NameError,'Unprocessed keys: %s' % (remaining.keys())
        return result

    def reachable(self,state=None,transition=None,horizon=-1,ignore=[],debug=False):
        """
        @note: The C{__predecessors__} entry for each reachable vector is a set of possible preceding states (i.e., those whose value must be updated if the value of this vector changes
        @return: transition matrix among states reachable from the given state (default is current state)
        @rtype: KeyedVectorS{->}ActionSetS{->}VectorDistribution
        """
        envelope = set()
        transition = {}
        if state is None:
            # Initialize with current state
            state = self.state[None]
        if isinstance(state,VectorDistribution):
            for vector in state.domain():
                envelope.add((vector,horizon))
        else:
            # Initialize with given state
            envelope.add((state,horizon))
        while len(envelope) > 0:
            vector,horizon = envelope.pop()
            assert len(vector) == len(state.domain()[0])
            if debug:
                print 'Expanding...'
                self.printVector(vector)
            node = vector.filter(ignore)
            # If no entry yet, then this is a start node
            if not transition.has_key(node):
                transition[node] = {'__predecessors__': set()}
            # Process next steps from this state
            if not self.terminated(vector) and horizon != 0:
                for actions in self.getActions(vector):
                    if debug: print 'Performing:', actions
                    future = self.stepFromState(vector,actions)['new']
                    if isinstance(future,KeyedVector):
                        future = VectorDistribution({future: 1.})
                    transition[node][actions] = VectorDistribution()
                    for newVector in future.domain():
                        if debug:
                            print 'Result (P=%f)' % (future[newVector])
                            self.printVector(newVector)
                        newNode = newVector.filter(ignore)
                        transition[node][actions][newNode] = future[newVector]
                        if transition.has_key(newNode):
                            transition[newNode]['__predecessors__'].add(node)
                        else:
                            envelope.add((newNode,horizon-1))
                            transition[newNode] = {'__predecessors__': set([node])}
        return transition
            
    def nearestVector(self,vector,vectors):
        mapping = {}
        for candidate in vectors:
            mapping[self.scaleState(candidate)] = candidate
        return mapping[self.scaleState(vector).nearestNeighbor(mapping.keys())]

    def getDescription(self,key,feature=None):
        if not feature is None:
            raise DeprecationWarning,'Use key when calling getDescription, not entity/feature combination.'
        return self.variables[key]['description']

    """---------------------"""
    """Visualization methods"""
    """---------------------"""

    def getGraph(self):
        if not self.graph:
            self.graph = {}
            # Process the unary state features
            for agent,variables in self.locals.items():
                for feature in variables.keys():
                    self.graph[stateKey(agent,feature)] = {'agent': agent,
                                                      'type': 'state pre',
                                                      'children': set(),
                                                      'parents': set()}
                    self.graph[stateKey(agent,feature,True)] = {'agent': agent,
                                                           'type': 'state post',
                                                           'children': set(),
                                                           'parents': set()}
            # Process the binary state features
            for relation,table in self.relations.items():
                for key,entry in table.items():
                    self.graph[key] = {'agent': entry['subject'],
                                  'type': 'state pre',
                                  'children': set(),
                                  'parents': set()}
                    self.graph[makeFuture(key)] = {'agent': entry['subject'],
                                              'type': 'state post',
                                              'children': set(),
                                              'parents': set()}
            for name,agent in self.agents.items():
                # Create the agent reward node
                self.graph[name] = {'agent': name,
                               'type': 'utility',
                               'parents': set(),
                               'children': set()}
                # Process the agent actions
                for action in agent.actions:
                    action = ActionSet([a.root() for a in action])
                    if not self.graph.has_key(action):
                        self.graph[action] = {'agent': name,
                                         'type': 'action',
                                         'parents': set(),
                                         'children': set()}
            # Create links from dynamics
            for key,dynamics in self.dynamics.items():
                assert self.graph.has_key(key),'Graph has not accounted for key: %s' % (key)
                if isinstance(dynamics,bool):
                    continue
                for action,tree in dynamics.items():
                    if not action is True:
                        # Link between action to this feature
                        assert self.graph.has_key(action),'Graph has not accounted for action: %s' % (action)
                        self.graph[makeFuture(key)]['parents'].add(action)
                        self.graph[action]['children'].add(makeFuture(key))
                    # Link between dynamics variables and this feature
                    for parent in tree.getKeys() - set([CONSTANT]):
                        self.graph[makeFuture(key)]['parents'].add(parent)
                        self.graph[parent]['children'].add(makeFuture(key))
            # Create links from dependencies
            for key,table in self.dependency.items():
                for parent in table.keys():
                    self.graph[makeFuture(key)]['parents'].add(makeFuture(parent))
                    self.graph[makeFuture(parent)]['children'].add(makeFuture(key))
            for name,agent in self.agents.items():
                # Create links from reward
                if agent.models[True].has_key('R'):
                    for R,weight in agent.models[True]['R'].items():
                        for parent in R.getKeys() - set([CONSTANT]):
                            # Link between variable and agent utility
                            self.graph[name]['parents'].add(makeFuture(parent))
                            self.graph[makeFuture(parent)]['children'].add(name)
                # Create links from legality
                for action,tree in agent.legal.items():
                    action = ActionSet([a.root() for a in action])
                    for parent in tree.getKeys() - set([CONSTANT]):
                        # Link between prerequisite variable and action
                        assert self.graph.has_key(action),'Graph has not accounted for action: %s' % (action)
                        self.graph[action]['parents'].add(parent)
                        self.graph[parent]['children'].add(action)
        return self.graph

    def explain(self,outcomes,level=1,buf=None):
        """
        Generate a more readable interpretation of outcomes generated by L{step}
        @param outcomes: the return value from L{step}
        @type outcomes: dict[]
        @param level: the level of explanation detail:
           0. No explanation
           1. Agent decisions
           2. Agent value functions
           3. Agent expectations
           4. Effects of expected actions
           5. World state (possibly subjective) at each step
        @type level: int
        @param buf: the string buffer to put the explanation into (default is standard out)
        """
        for outcome in outcomes:
            if level > 0: print >> buf,'%d%%' % (outcome['probability']*100.)
            if outcome.has_key('actions'):
                self.explainAction(outcome,buf,level)
                for name,action in outcome['actions'].items():
                    if not outcome['decisions'].has_key(name):
                        # No decision made
                        if level > 1: print >> buf,'\tforced'
                    elif level > 1:
                        # Explain decision
                        self.explainDecision(outcome['decisions'][name],buf,level)

    def explainAction(self,outcome,buf=None,level=0):
        if level > 0:
            for name,action in outcome['actions'].items():
                print >> buf,action
        return set(outcome['actions'].values())
        

    def explainDecision(self,decision,buf=None,level=2,prefix=''):
        """
        Subroutine of L{explain} for explaining agent decisions
        """
        if not decision.has_key('V'):
            # No value function
            return
        actions = decision['V'].keys()
        actions.sort(lambda x,y: cmp(str(x),str(y)))
        for alt in actions:
            V = decision['V'][alt]
            print >> buf,'%s\tV(%s) = %6.3f' % (prefix,alt,V['__EV__'])
            if level > 2:
                # Explain lookahead
                beliefs = filter(lambda k: not isinstance(k,str),V.keys())
                for state in beliefs:
                    nodes = V[state]['projection'][:]
                    while len(nodes) > 0:
                        node = nodes.pop(0)
                        tab = ''
                        t = V[state]['horizon']-node['horizon']
                        for index in range(t):
                            tab = prefix+tab+'\t'
                        if level > 4: 
                            print >> buf,'%sState:' % (tab)
                            self.printVector(node['old'],buf,prefix=tab,first=False)
                        print >> buf,'%s%s (V_%s=%6.3f) [P=%d%%]' % (tab,ActionSet(node['actions']),V[state]['agent'],node['R'],node['probability']*100.)
                        for other in node['decisions'].keys():
                            self.explainDecision(node['decisions'][other],buf,level,prefix+'\t\t')
                        if level > 3: 
                            print >> buf,'%sEffect:' % (tab+prefix)
                            self.printDelta(node['old'],node['new'],buf,prefix=tab+prefix)
                        for index in range(len(node['projection'])):
                            nodes.insert(index,node['projection'][index])

    def printState(self,distribution=None,buf=None,prefix='',beliefs=True):
        """
        Utility method for displaying a distribution over possible worlds
        @type distribution: L{VectorDistribution}
        @param buf: the string buffer to put the string representation in (default is standard output)
        @param prefix: a string prefix (e.g., tabs) to insert at the beginning of each line
        @type prefix: str
        @param beliefs: if C{True}, print out inaccurate beliefs, too
        @type beliefs: bool
        """
        if distribution is None:
            for distribution in self.state.values():
                self.printState(distribution,buf,prefix,beliefs)
        else:
            for vector in distribution.domain():
                print >> buf,'%s%d%%' % (prefix,distribution[vector]*100.),
                self.printVector(vector,buf,prefix,beliefs=beliefs)

    def printVector(self,vector,buf=None,prefix='',first=True,beliefs=False,csv=False):
        """
        Utility method for displaying a single possible world
        @type vector: L{KeyedVector}
        @param buf: the string buffer to put the string representation in (default is standard output)
        @param prefix: a string prefix (e.g., tabs) to insert at the beginning of each line
        @type prefix: str
        @param first: if C{True}, then the first line is the continuation of an existing line (default is C{True})
        @type first: bool
        @param csv: if C{True}, then print the vector as comma-separated values (default is C{False})
        @type csv: bool
        @param beliefs: if C{True}, then print any agent beliefs that might deviate from this vector as well (default is C{False})
        @type beliefs: bool
        """
        if csv:
            if prefix:
                elements = [prefix]
            else:
                elements = []
        entities = self.agents.keys()
        entities.sort()
        entities.insert(0,None)
        change = False
        # Sort relations
        relations = {}
        for link,table in self.relations.items():
            for key in table.keys():
                subj = table[key]['subject']
                obj = table[key]['object']
                try:
                    relations[subj].append((link,obj,key))
                except KeyError:
                    relations[subj] = [(link,obj,key)]
        for entity in entities:
            try:
                table = self.locals[entity]
            except KeyError:
                table = {}
            if entity is None:
                label = 'World'
            else:
                if vector.has_key(entity):
                    # Action performed in this vector
                    table['__action__'] = entity
                label = entity
            newEntity = True
            # Print state features for this entity
            for feature,key in table.items():
                if vector.has_key(key):
                    if csv:
                        elements.append(label)
                        elements.append(feature)
                    elif newEntity:
                        if first:
                            print >> buf,'\t%-12s' % (label),
                            first = False
                        else:
                            print >> buf,'%s\t%-12s' % (prefix,label),
                        print >> buf,'\t%-12s\t' % (feature+':'),
                        newEntity = False
                        change = True
                    else:
                        print >> buf,'%s\t\t\t%-12s\t' % (prefix,feature+':'),
                    # Generate string representation of feature value
                    value = self.float2value(key,vector[key])
                    if csv:
                        elements.append(value)
                    else:
                        print >> buf,value
            # Print relationships
            if relations.has_key(entity):
                for link,obj,key in relations[entity]:
                    if vector.has_key(key):
                        if newEntity:
                            print >> buf,'\t%-12s' % (label),
                            newEntity = False
                        print >> buf,'\t\t%s\t%s:\t%s' % (link,obj,self.float2value(key,vector[key]))
            # Print models (and beliefs associated with those models)
            if not entity is None:
                # Print model of this entity
                key = modelKey(entity)
                if vector.has_key(key):
                    if csv:
                        elements.append(label)
                        elements.append('__model__')
                        elements.append(self.agents[entity].index2model(vector[key]))
                    elif newEntity:
                        if first:
                            print >> buf,'\t%-12s' % (label),
                            first = False
                        else:
                            print >> buf,'%s\t%-12s' % (prefix,label),
                        self.agents[entity].printModel(index=vector[key],prefix=prefix)
                        change = True
                        newEntity = False
                    else:
                        print >> buf,'\t%12s' % (''),
                        self.agents[entity].printModel(index=vector[key],prefix=prefix)
                    newEntity = False
        if not csv and not change:
            print >> buf,'%s\tUnchanged' % (prefix)
        if len([key for key in vector.keys() if not isTurnKey(key) and not isModelKey(key) and not self.agents.has_key(key)]) == len([key for key in self.variables.keys() if not isTurnKey(key) and not isModelKey(key) and not self.agents.has_key(key)]):
            # Check for termination only if we have all state features
            if (not vector.has_key('__END__') and self.terminated(vector)) or \
                    (vector.has_key('__END__') and vector['__END__'] > 0.):
                if csv:
                    elements.append('World')
                    elements.append('__END__')
                    elements.append(str(True))
                else:
                    print >> buf,'%s\t__END__' % (prefix)
            elif csv:
                elements.append('World')
                elements.append('__END__')
                elements.append(str(False))
        if csv:
            print >> buf,','.join(elements)

    def printDelta(self,old,new,buf=None,prefix=''):
        """
        Prints a kind of diff patch for one state vector with respect to another
        @param old: the "original" state vector
        @type old: L{KeyedVector}
        @param new: the state vector we want to see the diff of
        @type new: L{VectorDistribution}
        """
        deltaDist = VectorDistribution()
        for vector in new.domain():
            delta = KeyedVector()
            keys = []
            for key,entry in self.variables.items():
                # Look for change in feature value
                keys.append(key)
            for name in self.agents.keys():
                # Look for change in mental model of this agent
                key = modelKey(name)
                if vector.has_key(key):
                    keys.append(key)
                    if not old.has_key(key):
                        old = KeyedVector(vector)
                        old[key] = self.agents[name].model2index(True)
            for key in keys:
                try:
                    diff = abs(vector[key]-old[key])
                except KeyError:
                    diff = 0.
                if diff > 1e-3:
                    # Notable change
                    delta[key] = vector[key]
            if self.terminated(vector):
                delta['__END__'] = 1.
            else:
                delta['__END__'] = -1.
            try:
                deltaDist[delta] += new[vector]
            except KeyError:
                deltaDist[delta] = new[vector]
        self.printState(deltaDist,buf,prefix=prefix,beliefs=False)
        
    """---------------------"""
    """Serialization methods"""
    """---------------------"""

    def __xml__(self):
        doc = Document()
        root = doc.createElement('world')
        doc.appendChild(root)
        # Agents
        for agent in self.agents.values():
            root.appendChild(agent.__xml__().documentElement)
        # State vector definitions
        for label,state in self.state.items():
            node = doc.createElement('state')
            node.setAttribute('label',label)
            node.appendChild(state.__xml__().documentElement)
        for key,entry in self.variables.items():
            subnode = doc.createElement('feature')
            subnode.setAttribute('name',key)
            subnode.setAttribute('domain',entry['domain'].__name__)
            for coord in ['xpre','ypre','xpost','ypost']:
                if entry.has_key(coord):
                    subnode.setAttribute(coord,str(entry[coord]))
            if not entry['lo'] is None:
                subnode.setAttribute('lo',str(entry['lo']))
            if not entry['hi'] is None:
                subnode.setAttribute('hi',str(entry['hi']))
            if entry['domain'] is list or entry['domain'] is set:
                for element in entry['elements']:
                    subsubnode = doc.createElement('element')
                    subsubnode.appendChild(doc.createTextNode(element))
                    subnode.appendChild(subsubnode)
            elif entry['domain'] is ActionSet:
                for element in entry['elements']:
                    subsubnode = doc.createElement('element')
                    subsubnode.appendChild(element.__xml__().documentElement)
                    subnode.appendChild(subsubnode)
            if entry['description']:
                subsubnode = doc.createElement('description')
                subsubnode.appendChild(doc.createTextNode(entry['description']))
                subnode.appendChild(subsubnode)
            if entry['combinator']:
                subnode.setAttribute('combinator',str(entry['combinator']))
            node.appendChild(subnode)
        # Local/global state
        for entity,table in self.locals.items():
            for feature,entry in table.items():
                subnode = doc.createElement('local')
                subnode.appendChild(doc.createTextNode(feature))
                if entity:
                    subnode.setAttribute('entity',entity)
                node.appendChild(subnode)
        root.appendChild(node)
        # Relationships
        for link,table in self.relations.items():
            node = doc.createElement('relation')
            node.setAttribute('name',link)
            for key,entry in table.items():
                subnode = doc.createElement('link')
                subnode.setAttribute('subject',entry['subject'])
                subnode.setAttribute('object',entry['object'])
                node.appendChild(subnode)
            root.appendChild(node)
        # Dynamics
        node = doc.createElement('dynamics')
        for key,table in self.dynamics.items():
            subnode = doc.createElement('table')
            subnode.setAttribute('key',key)
            if isinstance(table,dict):
                for action,tree, in table.items():
                    if not action is True:
                        subnode.appendChild(action.__xml__().documentElement)
                    subnode.appendChild(tree.__xml__().documentElement)
            node.appendChild(subnode)
        root.appendChild(node)
        # Inter-state dependency
        node = doc.createElement('dependency')
        for key,table in self.dependency.items():
            subnode = doc.createElement('dependent')
            subnode.setAttribute('key',key)
            for ind in table.keys():
                subsubnode = doc.createElement('independent')
                subsubnode.appendChild(doc.createTextNode(ind))
                subnode.appendChild(subsubnode)
            node.appendChild(subnode)
        root.appendChild(node)
        # Termination conditions
        for termination in self.termination:
            node = doc.createElement('termination')
            node.appendChild(termination.__xml__().documentElement)
            root.appendChild(node)
        # Global symbol table
        for symbol in self.symbolList:
            node = doc.createElement('symbol')
            if isinstance(symbol,str):
                node.appendChild(doc.createTextNode(symbol))
            elif isinstance(symbol,ActionSet):
                node.appendChild(symbol.__xml__().documentElement)
            else:
                raise TypeError,'Unknown symbol of type: %s' % (symbol.__class__.__name__)
            root.appendChild(node)
        # Event history
        #node = doc.createElement('history')
        #for entry in self.history:
        #    subnode = doc.createElement('entry')
        #    for outcome in entry:
        #        subsubnode = doc.createElement('outcome')
        #        for name in self.agents.keys():
        #            if outcome.has_key('actions') and outcome['actions'].has_key(name):
        #                subsubnode.appendChild(outcome['actions'][name].__xml__().documentElement)
        #        if outcome.has_key('delta'):
        #            subsubnode.appendChild(outcome['delta'].__xml__().documentElement)
        #        subsubnode.appendChild(outcome['old'].__xml__().documentElement)
        #        subnode.appendChild(subsubnode)
        #    node.appendChild(subnode)
        #root.appendChild(node)
        # UI Diagram
        if self.diagram:
            if isinstance(self.diagram,Node):
                # We never bothered parsing this, so easy
                root.appendChild(self.diagram)
            else:
                root.appendChild(self.diagram.__xml__().documentElement)
        return doc

    def parse(self,element,agentClass=Agent):
        self.initialize()
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'agent':
                    if agentClass.isXML(node):
                        self.addAgent(agentClass(node))
                    else:
                        assert Agent.isXML(node)
                        self.addAgent(Agent(node))
                elif node.tagName == 'state':
                    label = str(node.getAttribute('label'))
                    if label:
                        if label == 'None':
                            label = None
                    else:
                        label = None
                    self.state[label] = VectorDistribution()
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            if subnode.tagName == 'distribution':
                                self.state[label].parse(subnode)
                            elif subnode.tagName == 'feature':
                                key = str(subnode.getAttribute('name'))
                                domain,lo,hi,description,combinator = parseDomain(subnode)
                                self.defineVariable(key,domain,lo,hi,description,combinator)
                                try:
                                    for coord in ['xpre','ypre','xpost','ypost']:
                                        self.variables[key][coord] = int(subnode.getAttribute(coord))
                                except ValueError:
                                    pass
                            elif subnode.tagName == 'local':
                                entity = str(subnode.getAttribute('entity'))
                                if not entity:
                                    entity = None
                                feature = str(subnode.firstChild.data).strip()
                                self.defineState(entity,feature,None)
                        subnode = subnode.nextSibling
                elif node.tagName == 'relation':
                    name = str(node.getAttribute('name'))
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'link'
                            subj = str(subnode.getAttribute('subject'))
                            obj = str(subnode.getAttribute('object'))
                            self.defineRelation(subj,obj,name,None)
                        subnode = subnode.nextSibling
                elif node.tagName == 'dynamics':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'table'
                            key = str(subnode.getAttribute('key'))
                            self.dynamics[key] = {}
                            subsubnode = subnode.firstChild
                            action = True
                            while subsubnode:
                                if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
                                    if subsubnode.tagName == 'action':
                                        assert action is True
                                        action = Action(subsubnode)
                                    elif subsubnode.tagName == 'option':
                                        assert action is True
                                        action = ActionSet(subsubnode)
                                    elif subsubnode.tagName == 'tree':
                                        self.dynamics[key][action] = KeyedTree(subsubnode)
                                        action = True
                                    else:
                                        raise NameError,'Unknown dynamics element: %s' % (subsubnode.tagName)
                                subsubnode = subsubnode.nextSibling
                            if len(self.dynamics[key]) == 0:
                                # Empty table
                                self.dynamics[key] = True
                        subnode = subnode.nextSibling
                elif node.tagName == 'dependency':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'dependent'
                            dep = str(subnode.getAttribute('key'))
                            subsubnode = subnode.firstChild
                            while subsubnode:
                                if subsubnode.nodeType == subnode.ELEMENT_NODE:
                                    assert subsubnode.tagName == 'independent'
                                    self.addDependency(dep,str(subsubnode.firstChild.data).strip())
                                subsubnode = subsubnode.nextSibling
                        subnode = subnode.nextSibling
                elif node.tagName == 'termination':
                    subnode = node.firstChild
                    while subnode and subnode.nodeType != subnode.ELEMENT_NODE:
                        subnode = subnode.nextSibling
                    if subnode:
                        self.termination.append(KeyedTree(subnode))
                elif node.tagName == 'symbol':
                    symbol = str(node.firstChild.data)
                    if not symbol.strip():
                        subnode = node.firstChild
                        while subnode and subnode.nodeType != subnode.ELEMENT_NODE:
                            subnode = subnode.nextSibling
                        if subnode:
                            if subnode.tagName == 'option':
                                symbol = ActionSet(subnode)
                            else:
                                raise ValueError,'Unknown symbol tag: %s' % (subnode.tagName)
                    self.symbolList.append(symbol)
                elif node.tagName == 'history':
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            assert subnode.tagName == 'entry'
                            entry = []
                            subsubnode = subnode.firstChild
                            while subsubnode:
                                if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
                                    assert subsubnode.tagName == 'outcome'
                                    outcome = {'actions': {}}
                                    element = subsubnode.firstChild
                                    while element:
                                        if element.nodeType == element.ELEMENT_NODE:
                                            if element.tagName == 'option':
                                                option = ActionSet(element)
                                                for action in option:
                                                    outcome['actions'][action['subject']] = option
                                                    break
                                            elif element.tagName == 'vector':
                                                outcome['old'] = KeyedVector(element)
                                            elif element.tagName == 'distribution':
                                                outcome['delta'] = VectorDistribution(element)
                                        element = element.nextSibling
                                    entry.append(outcome)
                                subsubnode = subsubnode.nextSibling
                            self.history.append(entry)
                        subnode = subnode.nextSibling
                elif node.tagName == 'diagram':
                    # UI information. Parse later
                    self.diagram = node
            node = node.nextSibling
        self.symbolList = self.symbolList[len(self.symbolList)/2:]
        for index in range(len(self.symbolList)):
            self.symbols[self.symbolList[index]] = index
        
    def save(self,filename,compressed=True):
        """
        @param compressed: if C{True}, then save in compressed XML; otherwise, save in XML (default is C{True})
        @type compressed: bool
        @return: the filename used (possibly with a .psy extension added)
        @rtype: str
        """
        if compressed:
            if filename[-4:] != '.psy':
                filename = '%s.psy' % (filename)
        elif filename[-4:] != '.xml':
            filename = '%s.xml' % (filename)

        if compressed:
            f = bz2.BZ2File(filename,'w')
        else:
            f = file(filename,'w')

        f.write(self.__xml__().toprettyxml())
        f.close()
        return filename

def stateKey(name,feature,future=False):
    """
    @param future: if C{True}, then this refers to the projected value of this feature (default is C{False})
    @type future: bool
    @return: a key representation of a given entity's state feature
    @rtype: str
    """
    if isinstance(name,Agent):
        return stateKey(name.name,feature,future)
    elif future:
        return stateKey(name,feature)+"'"
    elif name is None:
        return feature
    else:
        return '%s\'s %s' % (name,feature)

def state2feature(key):
    """
    @return: the feature string from the given key
    @rtype: str
    """
    index = key.find("'")
    if index < 0:
        return key
    else:
        return key[index+3:]
    
def makePresent(key):
    """
    @return: a reference to the given state features' current value
    @rtype: str
    """
    if key[-1] == "'":
        return key[:-1]
    else:
        raise ValueError,'%s is already a present key' % (key)
def makeFuture(key):
    """
    @return: a reference to the given state features' projected future value
    @rtype: str
    """
    if key[-1] == "'":
        raise ValueError,'%s is already a future key' % (key)
    else:
        return key+"'"

def isFuture(key):
    return key[-1] == "'"

def turnKey(name):
    return stateKey(name,'_turn')

def isTurnKey(key):
    return key[-8:] == '\'s _turn'

def turn2name(key):
    return key[:-8]

def actionKey(feature):    
    return '__action__%s__' % (feature)

def modelKey(name):
    return stateKey(name,'_model')

def isModelKey(key):
    return key[-9:] == '\'s _model'

def model2name(key):
    return key[:-9]

def binaryKey(subj,obj,relation):
    return '%s %s -> %s' % (subj,relation,obj)

def isBinaryKey(key):
    return ' -> ' in key

def key2relation(key):
    sides = key.split(' -> ')
    first = sides[0].split()
    return {'subject': ' '.join(first[:-1]),
            'object': sides[1],
            'relation': first[-1]}

def likesKey(subj,obj):
    return binaryKey(subj,obj,'likes')

def isLikesKey(key):
    return ' likes -> ' in key

def parseDomain(subnode):
    domain = str(subnode.getAttribute('domain'))
    description = None
    lo = str(subnode.getAttribute('lo'))
    if not lo: lo = None
    hi = str(subnode.getAttribute('hi'))
    if not hi: hi = None
    if domain == 'int':
        domain = int
        if lo: lo = int(lo)
        if hi: hi = int(hi)
    elif domain == 'float':
        domain = float
        if lo: lo = float(lo)
        if hi: hi = float(hi)
    elif domain == 'bool':
        domain = bool
    elif domain == 'list':
        domain = list
        lo = []
    elif domain == 'set':
        domain = set
        lo = []
    elif domain == 'ActionSet':
        domain = ActionSet
        lo = []
    else:
        raise TypeError,'Unknown feature domain type: %s' % (domain)
    combinator = str(subnode.getAttribute('combinator'))
    if len(combinator) == 0:
        combinator = None
    subsubnode = subnode.firstChild
    while subsubnode:
        if subsubnode.nodeType == subsubnode.ELEMENT_NODE:
            if subsubnode.tagName == 'element':
                if domain is list or domain is set:
                    lo.append(str(subsubnode.firstChild.data).strip())
                else:
                    assert domain is ActionSet
                    lo.append(ActionSet(subsubnode.getElementsByTagName('action')))
            else:
                assert subsubnode.tagName == 'description'
                description = str(subsubnode.firstChild.data).strip()
        subsubnode = subsubnode.nextSibling
    return domain,lo,hi,description,combinator

def scaleValue(value,entry):
    """
    @return: a new float value that has been normalized according to the feature's domain
    """
    if entry['domain'] is float or entry['domain'] is int:
        # Scale by range of possible values
        return float(value-entry['lo']) / float(entry['hi']-entry['lo'])
    elif entry['domain'] is list:
        # Scale by size of set of values
        return float(value)/float(len(entry['elements']))
    else:
        return value

