import copy
import string
from teamwork.math.probability import Distribution
from teamwork.math.Keys import StateKey,keyConstant
from teamwork.math.matrices import epsilon
from teamwork.math.KeyedVector import KeyedVector,ThresholdRow
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.KeyedTree import KeyedTree,KeyedPlane
from Multiagent import MultiagentSystem

class MultiagentSimulation(MultiagentSystem):
    """Base multiagent class that provides rudimentary state and turn-taking infrastructure
    @ivar initialOrder: the base turn-taking order, which is the order set at the beginning of the simulation
    @ivar order: the current turn-taking order vector
    @type order: L{KeyedVector}
    @ivar _turnDynamics: the dynamics of turn taking
    @type _turnDynamics: L{teamwork.math.KeyedTree.KeyedTree}
    @cvar turnFeature: the name of the feature labeling the turn status of each agent
    @type turnFeature: C{str}
    @ivar time: the number of epochs passed
    @type time: C{int}
    @cvar threshold: the activation threshold for the agent's L{turnFeature} valueb
    """
    turnFeature = '_turn'
    threshold = 0.5
    
    def __init__(self,agents=[]):
        """Initializes a simulation to contain the given list of agents.  If you would like to create your own turn state and dynamics, override the methods L{generateOrder} and L{createTurnDynamics}.
        @param agents: the initial set of agents (defaults to an empty set)
        @type agents: C{L{teamwork.agent.Agent.Agent}[]}
        """
        # Initialize entity state
        self.state = Distribution({KeyedVector({keyConstant:1.}):1.})
        # World dynamics
        self.dynamics = {}
        self.initialOrder = []
        self.positions = {}
        self.order = KeyedVector()
        MultiagentSystem.__init__(self,agents)
        self.time = 0
        # Initialize turn-taking
        self._turnDynamics = {}
        self.initializeOrder()
        if isinstance(agents,MultiagentSimulation):
            self.order = copy.deepcopy(agents.order)
            self.initialOrder = copy.deepcopy(agents.initialOrder)
        # History
        self.saveHistory = False
        self.history = []
        # Action count
        self.jointActions = None

    def addMember(self,agent):
        """Adds the agent to this collection
        @param agent: the agent to add
        @type agent: L{teamwork.agent.Agent}
        @warning: will clobber any pre-existing agent with the same name
        """
        MultiagentSystem.addMember(self,agent)
        for feature in agent.getStateFeatures():
            value = agent.getState(feature)
            key = StateKey({'entity':agent.name,'feature':feature})
            self.state.join(key,value)
        agent.state = self.state
        if not isinstance(agent.entities,self.__class__):
            agent.entities = self.__class__(agent.entities)

    def getStateKeys(self):
        """
        @return: dictionary containing relevant state keys
        @rtype: C{dict:L{StateKey}S{->}boolean}
        """
        return self.state.domainKeys()
    
    def getState(self):
        """
        @return: the probability over the current states of all member agents
        @rtype: L{Distribution}"""
        return self.state

    def deleteState(self,entity,feature):
        """Removes the given feature from the state vector
        @param entity: the entity on whom the feature currently exists
        @type entity: str
        @param feature: the state feature to remove
        @type feature: str
        """
        key = StateKey({'entity':entity,'feature':feature})
        self.state = self.state.marginalize(key)

    def getSequence(self):
        """
        @return: the sequence of entities who will act in this simulaton
        @rtype: str[]
        """
        keys = filter(lambda k: isinstance(k,StateKey),self.order.keys())
        if len(keys) == 0:
            return []
        entries = map(lambda k: (k,self.order[k]),keys)
        entries.sort(lambda x,y:-cmp(x[1],y[1]))
        order = [[entries[0][0]['entity']]]
        for index in range(1,len(entries)):
            key,value = entries[index]
            if value+epsilon > entries[index-1][1]:
                order[-1].append(key['entity'])
            else:
                order.append([key['entity']])
        return order
        
    def initializeOrder(self):
        """Re-initializes the turn-taking order, in case of any addition/deletion of agents"""
        self.order = self.generateOrder()
        self._turnDynamics.clear()

    def generateOrder(self,entities=None):
        """Creates a new order vector
        @return: the turn state vector suitable for the initial state of the simulation
        @rtype: L{KeyedVector}
        """
        if entities is None:
            entities = [self.activeMembers()]
            entities[0].sort()
        self.initialOrder = entities[:]
        return self.order2vector(entities)

    def pos2float(self,index):
        """Transforms a integer position into float representation in [0,1]
        @type index: int
        @rtype: float
        """
        return 1./pow(2,index) * self.threshold + epsilon
    
    def order2vector(self,entities):
        """Takes a sequence of entities (or lists of entities) and returns a turn vector representing that sequence
        @type entities: str[] or str[][]
        @rtype: KeyedVector
        """
        order = KeyedVector()
        for index in range(len(entities)):
            value = self.pos2float(index)
            if isinstance(entities[index],str):
                # Serial execution
                step = [entities[index]]
            else:
                # Parallel execution
                step = entities[index]
            for agent in step:
                if not isinstance(agent,str):
                    agent = agent.name
                order[StateKey({'entity':agent,
                                'feature':self.turnFeature})] = value
        order[keyConstant] = 1.
        order.freeze()
        return order

    def vector2order(self,vector):
        """Takes a vector representation of turn order and returns a list representation of that same order
        @type vector: L{KeyedVector}
        @rtype: str[][]
        """
        positions = {}
        for key in vector.keys():
            if isinstance(key,StateKey):
                positions[key['entity']] = vector[key]
        if positions:
            for key,value in positions.items():
                for index in range(len(positions)):
                    if abs(value-self.pos2float(index)) < epsilon:
                        positions[key] = index
                        break
                else:
                    raise ValueError,'Unable to find index for %5.3f' % (value)
            ordering = map(lambda i: [],range(max(positions.values())+1))
            for key,value in positions.items():
                ordering[value].append(key)
            return ordering
        else:
            return []
    
    def next(self,order=None):
        """Computes the active agents in the next turn by determining which agents have an activation greater than L{threshold} in the turn state
        @param order: the order vector to use as the basis for computing the turn result (defaults to the current system turn state)
        @type order: L{KeyedVector}
        @return: the names of those agents whose turn it is now.  Each of the agents will thus act in parallel
        @rtype: C{str[]}
        """
        if order is None:
            order = self.order
        active = []
        for key,value in order.items():
            if key.has_key('feature') and key['feature'] == self.turnFeature:
                entry = {'name':key['entity']}
                if value + epsilon > self.threshold:
                    active.append(entry)
        if active:
            return active
        else:
            # No one above threshold?  Shouldn't happen, but let's just pass
            # on the "most" active
            best = {'value':-1.,'agents':[]}
            for key,value in order.items():
                if key.has_key('feature') and key['feature'] == self.turnFeature:
                    entry = {'name':key['entity']}
                    if value > best['value'] + epsilon:
                        # New best
                        best = {'value':value,'agents':[entry]}
                    elif value + epsilon > best['value']:
                        # Tied with best
                        best['agents'].append(entry)
            return best['agents']

    def updateTurn(self,actions,debug=None):
        """Computes the (possibly cached) change in turn due to the specified actions
        @param actions: the actions being performed, indexed by actor name
        @type actions: C{dict:strS{->}L{Action<teamwork.action.PsychActions.Action>}[]}
        @return: the dynamics of change to the standing turn order based on the specified actions, suitable for passing to L{applyTurn} to actually implement the changes
        @rtype: L{KeyedTree<teamwork.math.KeyedTree.KeyedTree>}
        """
        actionKey = string.join(map(str,actions.values()))
        if not self._turnDynamics.has_key(actionKey):
            tree = self.createTurnDynamics(actions)
            tree.fill(self.order.keys())
            tree.freeze()
            self._turnDynamics[actionKey] = tree
        return self._turnDynamics[actionKey]

    def activeMembers(self):
        """
        @return: those agents who are able to take actions
        @rtype: L{Agent<teamwork.agent.Agent.Agent>}[]
        """
        entities = []
        for agent in self.members():
            if len(agent.actions.getOptions()) > 0:
                entities.append(agent)
        return entities

    def actorCount(self,level=0):
        """
        @param level: The belief depth at which all agents will have their policies compiled, where 0 is the belief depth of the real agent.  If the value of this flag is I{n}, then all agents at belief depthS{>=}I{n} will have their policies compiled, while no agents at belief depth<I{n} will.
        @type level: int
        @return: the total number of actors (including recursive beliefs) within this scenario
        @rtype: int
        """
        count = 0
        flag = False
        for agent in self.members():
            if not flag and agent.beliefDepth() >= level:
                flag = True
            count += agent.entities.actorCount()
        if flag:
            count += len(self.activeMembers())
        return count
        
    def actionCount(self,descend=True):
        """
        @param descend: flag, if True, the count includes actions in recursive beliefs; otherwise, not.
        @return: the total number of actions within this scenario
        @rtype: int
        """
        count = 0
        for agent in self.members():
            if descend:
                count += agent.entities.actionCount()
            count += len(agent.actions.getOptions())
        return count

    def generateActions(self,agents=None,result=None):
        """Generates all possible joint actions out of the given agents
        @param agents: the agents eligible for action (defaults to currently eligible agents)
        @type agents: L{Agent<teamwork.agent.Agent.Agent>}[]
        """
        if agents is None:
            agents = self.next()
        if result is None:
            result = [{}]
        if len(agents) == 0:
            return result
        else:
            turn = agents.pop()
            agent = self[turn['name']]
            newResult = []
            try:
                choices = turn['choices']
            except KeyError:
                choices = agent.actions.getOptions()
            for action in choices:
                for set in result:
                    newSet = copy.copy(set)
                    newSet[agent.name] = action
                    newResult.append(newSet)
            return self.generateActions(agents,newResult)
        
    def createTurnDynamics(self,actions):
        """Computes the change in turn due to the specified actions
        @param actions: the actions being performed, indexed by actor name
        @type actions: C{dict:strS{->}L{Action<teamwork.action.PsychActions.Action>}[]}
        @return: the dynamics of change to the standing turn order based on the specified actions, suitable for passing to L{applyTurn} to actually implement the changes
        @rtype: L{KeyedTree<teamwork.math.KeyedTree.KeyedTree>}
        """
        # Unless the actor is taking another turn, then no change
        unchangedMatrix = KeyedMatrix()
        for key in self.order.keys():
            row = KeyedVector()
            row[key] = 1.
            unchangedMatrix[key] = row
        row = KeyedVector()
        row[keyConstant] = 1.
        unchangedMatrix[keyConstant] = row
        # Check whether anyone ever has a turn
        if len(self) == 0:
            tree = KeyedTree()
            tree.makeLeaf(unchangedMatrix)
            return tree
        # If nobody left to act, start the turn order from the beginning
        resetMatrix = KeyedMatrix()
        order = self.order2vector(self.initialOrder)
        for key in order.keys():
            row = KeyedVector()
            row[keyConstant] = order[key]
            resetMatrix[key] = row
        row = KeyedVector()
        row[keyConstant] = 1.
        resetMatrix[keyConstant] = row
        if len(actions) == len(self.order)-1: # Account for constant
            # Everyone is acting in this turn
            tree = KeyedTree()
            tree.makeLeaf(resetMatrix)
            return tree
        # Test whether anybody's left to act after these new actions
        resetWeights = KeyedVector()
        for key in self.order.keys():
            if isinstance(key,StateKey) and not actions.has_key(key['entity']):
                resetWeights[key] = 1.
        resetPlane = KeyedPlane(resetWeights,0.0001)
        # If so, move the leftover actors up in the turn order
        updateMatrix = KeyedMatrix()
        for key in self.order.keys():
            row = KeyedVector()
            if isinstance(key,StateKey):
                if actions.has_key(key['entity']):
                    # Reset activation
                    value = pow(2,len(self.initialOrder)-1)
                    row[keyConstant] = 1./value*self.threshold + epsilon
                else:
                    # Move up in the order
                    row[key] = 2.
            else:
                # Constant
                row[key] = 1.
            updateMatrix[key] = row
        updateTree = unchangedMatrix
        for actor in actions.keys():
            # Test whether actor is sneaking in a second turn
            alreadyActed = ThresholdRow(keys=[{'entity':actor,
                                               'feature':self.turnFeature}])
            updateTree = KeyedTree()
            updateTree.branch(KeyedPlane(alreadyActed,self.threshold-epsilon),
                              falseTree=unchangedMatrix,trueTree=updateMatrix)
            updateMatrix = updateTree
        # Create branch on number of people left to act
        tree = KeyedTree()
        tree.branch(resetPlane,resetMatrix,updateTree)
        return tree
        
    def applyTurn(self,delta,beliefs=None):
        """Applies provided turn changes
        @param delta: changes, as computed by L{updateTurn}
        @type delta: C{L{KeyedTree<teamwork.math.KeyedTree.KeyedTree>}}
        @param beliefs: the belief dictionary to be updated (defaults to this actual L{Simulation})
        @type beliefs: dict
        """
        if beliefs is None:
            self.order = delta[self.order] * self.order
            self.time += 1
            if self.saveHistory:
                self.history.append(self.state.expectation())
        else:
            beliefs['turn'] = delta[beliefs['turn']] * beliefs['turn']
        
    def __xml__(self):
        doc = MultiagentSystem.__xml__(self)
        doc.documentElement.setAttribute('time',str(self.time))
        # State
        node = doc.createElement('state')
        doc.documentElement.appendChild(node)
        node.appendChild(self.state.__xml__().documentElement)
        # Turn sequence
        node = doc.createElement('order')
        doc.documentElement.appendChild(node)
        node.appendChild(self.order.__xml__().documentElement)
        return doc
        
    def parse(self,element,agentClass=None):
        MultiagentSystem.parse(self,element,agentClass)
        try:
            self.time = int(element.getAttribute('time'))
        except ValueError:
            self.time = 0
##        self.initializeOrder()
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'state':
                    subNodes = child.getElementsByTagName('distribution')
                    if len(subNodes) == 1:
                        self.state.parse(subNodes[0],KeyedVector)
                    elif len(subNodes) > 1:
                        raise UserWarning,'Multiple distributions in state'
                elif child.tagName == 'order':
                    subNodes = child.getElementsByTagName('vector')
                    if len(subNodes) == 1:
                        self.order.unfreeze()
                        self.order.parse(subNodes[0],True)
                        self.order.freeze()
                    elif len(subNodes) > 1:
                        raise UserWarning,'Multiple vectors in turn sequence'
                    else:
                        raise UserWarning,'Missing vector in turn sequence'
            child = child.nextSibling
        self.initialOrder = self.vector2order(self.order)
         
    def __copy__(self):
        new = MultiagentSystem.__copy__(self)
        new.time = self.time
        new.initializeOrder()
        new.state = copy.copy(self.state)
        return new

    def __deepcopy__(self,memo):
        memo[id(self.state)] = copy.deepcopy(self.state,memo)
        new = MultiagentSystem.__deepcopy__(self,memo)
        new.time = self.time
        new.initializeOrder()
        new.state = memo[id(self.state)]
        return new
