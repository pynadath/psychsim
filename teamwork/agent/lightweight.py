"""A minimal agent implementation that uses only the PWL representations of an agent's beliefs, policy, etc.
"""
from Agent import Agent
from teamwork.dynamics.pwlDynamics import PWLDynamics,IdentityDynamics
from teamwork.action.PsychActions import Action
from teamwork.action.DecisionSpace import parseSpace
from teamwork.math.Keys import StateKey,LinkKey,keyConstant
from teamwork.math.probability import Distribution
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedMatrix import IdentityMatrix
from teamwork.reward.MinMaxGoal import MinMaxGoal
import copy

class PWLAgent(Agent):
    """Lightweight version of a PsychSim agent with only the barest essentials for generating behaviors
    @ivar dynamics: a dictionary of dictionaries of L{PWLDynamics} objects.  The top-level key is the state feature the dynamics affect.  The keys at the level below are L{Action} types.
    @type dynamics: strS{->}(strS{->}L{PWLDynamics})
    @ivar parent: the parent of this agent, included for compatibility with L{RecursiveAgent<teamwork.agent.RecursiveAgent.RecursiveAgent>} instances.  Always C{None}.
    @ivar policy: this agent's policy of behavior
    @type policy: L{PWLTable}
    @ivar goals: this agent's goal weights
    @type goals: L{KeyedVector}
    @ivar liking: the liking this agent has for others
    @type liking: L{KeyedVector}
    @ivar trust: the trust this agent has in others
    @type trust: L{KeyedVector}
    @cvar _supportFeature: the label for the liking relationship
    @cvar _trustFeature: the label for the trust relationship
    @type _supportFeature,_trustFeature: str
    @ivar relationships: an empty dictionary of inter-agent relationships from this agent
    @ivar compiled: if C{True}, the value function is compiled (default is C{False}
    @type compiled: bool
    """
    _supportFeature = 'likes'
    _trustFeature = 'trusts'

    def __init__(self,agent=None):
        """Constructor that creates a lightweight version of a given PsychSim agent
        @param agent: the L{RecursiveAgent<teamwork.agent.RecursiveAgent.RecursiveAgent>} to be distilled (if omitted, an empty agent is created)
        """
        self.dynamics = {}
        self.parent = None
        self.horizon = 0
        self.state = Distribution({KeyedVector({keyConstant:1.}):1.})
        self.goals = Distribution({KeyedVector():1.})
        self.relationships = {}
        self.links = KeyedVector()
        self.linkDynamics = {self._supportFeature:{},
                             self._trustFeature:{}}
        self.linkTypes = [self._supportFeature,self._trustFeature]
        self.classes = []
        self.world = None
        self.society = None
        self.compiled = False
        self.beliefs = self.state
        if agent is None:
            name='Piecewise Linear Agent'
        elif isinstance(agent,str):
            name = agent
        else:
            name = agent.name
        Agent.__init__(self,name)
        if isinstance(agent,Agent):
            self.actions = agent.actions
            if len(agent.entities) > 0:
                self.beliefs = copy.deepcopy(agent.entities.getState())
            # Copy over the policy
            self.horizon = agent.horizon
            try:
                self.policy = agent.policy.getTable()
            except IndexError:
                # No compiled policy
                pass
            # Copy over raw state dynamics
            for feature,dynTable in agent.dynamics.items():
                self.dynamics[feature] = {}
                for action,dynamics in dynTable.items():
                    if isinstance(action,str):
                        self.dynamics[feature][action] = dynamics
            # Copy over goal weights
            self.goals = agent.getGoalVector()['state']
            # Copy over liking, trust, etc.
            self.linkTypes = agent.getLinkTypes()[:]
            for linkType in agent.getLinkTypes():
                for name in agent.getLinkees(linkType):
                    key = agent.getLinkKey(linkType,name)
                    self.links[key] = agent.getLink(linkType,name)
            # Copy over raw relationship dynamics
            for feature,dynTable in agent.linkDynamics.items():
                self.linkDynamics[feature] = {}
                for action,dynamics in dynTable.items():
                    if isinstance(action,str):
                        self.linkDynamics[feature][action] = dynamics
            # Copy over class membership
            self.classes = agent.classes[:]
            # Copy over relationships
            for relation,relatees in agent.relationships.items():
                self.relationships[relation] = relatees[:]

    def setHierarchy(self,classes):
        """We don't need no stinking defaults"""
        pass
    
    def ancestry(self):
        """
        @return: a string representation of this entity's position in the recursive belief tree.
          - If C{self.parent == None}, then returns C{self.name}
          - Otherwise, returns C{self.parent.ancestry()+'->'+self.name}
        @rtype: C{str}
        """
        name = self.name
        parent = self.parent
        while parent:
            name = parent.name + '->' + name
            parent = parent.parent
        return name
            
    def instanceof(self,className):
        """
        @return: True iff this entity is a member of the specified class
        @param className: name of class to test against
        @type className: C{str}
        @rtype: C{boolean}
        """
        return className in self.classes

    def getStateFeatures(self):
        """
        @return: names of the valid state features
        @rtype: C{str[]}
        """
        keyList = []
        for key in self.state.domainKeys():
            if isinstance(key,StateKey) and key['entity'] == self.name:
                keyList.append(key['feature'])
        return keyList

    def getState(self,feature):
        """Returns the current L{Distribution} over the specified feature
        @type feature: string
        @rtype: L{Distribution}"""
        key = StateKey({'entity':self.name,'feature':feature})
        return self.state.getMarginal(key)

    def setState(self,feature,value):
        """Sets this entity's state value for the specified feature
        @type feature: string
        @type value: either a float or a L{Distribution}.  If the value is a float, it is first converted into a point distribution."""
        key = StateKey({'entity':self.name,'feature':feature})
        frozen = self.state.unfreeze()
        self.state.join(key,value)
        if frozen:
            self.state.freeze()

    def getEntities(self):
        entities = {}
        for key in self.beliefs.domain()[0].keys():
            if isinstance(key,StateKey):
                entities[key['entity']] = True
        return entities.keys()

    def getEntity(self,name):
        return self.world[name]

    def getEntityBeliefs(self):
        return map(self.getEntity,self.getEntities())

    def getBeliefKeys(self):
        """
        @return: the state features across all beliefs that this agent has
        @rtype: L{StateKey}[]
        """
        return self.beliefs.expectation().keys()

    def getLinkTypes(self):
        """
        @return: all of the available dynamics relationship types that
        his entity has
        @rtype: str[]
        """
        return self.linkTypes

    def getLinkees(self,relationship):
        """
        @param relationship: the dynamic relationship (e.g., 'likes',
        'trusts') to evaluate
        @type relationship: str
        @return: the others to which this entity has explicit
        relationships of the specified type
        @rtype: str[]
        """
        result = []
        for key in self.links.keys():
            if key['subject'] == self.name and key['verb'] == relationship:
                result.append(key['object'])
        return result

    def getLinkKey(self,relation,entity):
        """
        @return: the vector index for this entity's relation to the given
        entity
        @rtype: L{LinkKey}
        """
        return LinkKey({'subject':self.name,
                        'verb':relation,
                        'object':entity})
    
    def getLink(self,relationship,entity):
        """
        @param relationship: the dynamic relationship (e.g., 'likes',
        'trusts') to evaluate
        @param entity: the entity who is the object of the
        relationship (e.g., the entity being liked or trusted)
        @type relationship: str
        @type entity: str
        @return: the current value of the link
        @rtype: float
        """
        key = self.getLinkKey(relationship,entity)
        try:
            return self.links[key]
        except KeyError:
            return 0.

    def setLink(self,relationship,entity,value):
        """
        @param relationship: the dynamic relationship (e.g., 'likes',
        'trusts') to evaluate
        @param entity: the entity who is the object of the
        relationship (e.g., the entity being liked or trusted)
        @type relationship: str
        @type entity: str
        @param value: the new value for my trust level
        @type value: float
        """
        key = self.getLinkKey(relationship,entity)
        self.links[key] = value
    
    # SE^0_i
    def initialStateEstimator(self):
	"""Generates the initial belief state for the specified agent"""
        return Distribution({KeyedVector():1.})

    def getBelief(self,entity,feature):
        """
        @param entity: the name of the relevant entity
        @type entity: str
        @param feature: the state feature of interest
        @type feature: str
        @return: the agent's current belief about the given entity's value for the given state feature
        @rtype: L{Distribution}
        """
        key = StateKey({'entity':entity,'feature':feature})
        return self.beliefs.getMarginal(key)

    def setBelief(self,entity,feature,value):
        """Sets this entity's belief value for the specified entity's state feature value
        @param entity: the name of the relevant entity
        @type entity: str
        @param feature: the state feature of interest
        @type feature: string
        @type value: either a float or a L{Distribution}.  If the value is a float, it is first converted into a point distribution."""
        key = StateKey({'entity':entity,'feature':feature})
        self.beliefs.unfreeze()
        self.beliefs.join(key,value)
        self.beliefs.freeze()

    def getGoals(self):
        return []

    def getGoalVector(self):
        return {'state': self.goals}
    
    def applyPolicy(self,state=None,actions=[],history=None,debug=None,
                    explain=False,entities={},cache={}):
        """Generates a decision chosen according to the agent's current policy
        @param state: the current state vector
        @type state: L{Distribution}(L{KeyedVector})
        @param actions: the possible actions the agent can consider (defaults to all available actions)
        @type actions: L{Action}[]
        @param history: a dictionary of actions that have already been performed (and which should not be performed again if they are labeled as not repeatable)
        @type history: L{Action}[]:bool
        @param explain: flag indicating whether an explanation should be generated
        @type explain: bool
        @param entities: a dictionary of entities to be used as a value tree cache
        @param cache: values computed so far
        @return: a list of actions and an explanation, the latter provided by L{execute<PolicyTable.execute>}
        @rtype: C{(L{Action}[],Element)}
        """
        if state is None:
            state = {None:self.beliefs}
        return self.policy.execute(state=state,choices=actions,history=history,
                                   debug=debug,explain=explain)
##                                   entities=entities,cache=cache)
    
    def actionValue(self,actions,horizon=1,state=None,debug=False):
        """Compute the expected value of performing the given action
        @param actions: the actions whose effect we want to evaluate
        @type actions: L{Action}[]
        @param horizon: the length of the forward projection
        @type horizon: int
        @param state: the world state to evaluate the actions in (defaults to current world state)
        @type state: L{Distribution}
        @warning: Computation assumes that dynamics for I{instantiated} actions are already stored.  Missing dynamics are taken to imply no effect.
        """
        if state is None:
            state = {None:self.beliefs}
        eState = state[None].expectation()
        goals = self.goals.expectation()
        projection = {}
        total = 0.
        for key in filter(lambda k: goals[k] > Distribution.epsilon,
                          goals.keys()):
            if key['entity'] == self.name:
                entity = self
            elif self.world:
                entity = self.world[key['entity']]
            else:
                raise UserWarning,'Entity %s has no world' % (self.name)
            dynamics,delta = self.world.getEffect(actions[0],key,eState,
                                                  not self.compiled)
            if dynamics:
                if delta is None:
                    tree = dynamics.getTree()
                    delta = dynamics.apply(state[None]).expectation()
                total += goals[key]*(delta[key]*eState)
                for subKey in delta[key].keys():
                    try:
                        projection[subKey] += goals[key]*delta[key][subKey]
                    except KeyError:
                        projection[subKey] = goals[key]*delta[key][subKey]
        return total,{'value':total,'projection':projection}

    def stateEstimator(self,beliefs=None,actions=[],observation=None):
        """Updates the agent's beliefs in response to the given agents
        @param beliefs: the agent's current beliefs (typically C{self.beliefs})
        @type beliefs: L{Distribution}(L{KeyedVector})
        @param actions: the observed actions
        @type actions: L{Action}[]
        @param observation: if in a partially observable domain, this is the observation received (default is C{None})
        @type observation: str
        @return: the new beliefs (updates the agent's beliefs as a side effect)
        @rtype: L{Distribution}(L{KeyedVector})
        """
        if beliefs is None:
            doForReal = True
            beliefs = self.beliefs
        else:
            doForReal = False
        if observation:
            if isinstance(beliefs,list):
                # Observation history
                beliefs = beliefs + [observation]
            else:
                # Belief state
                SE = self.estimators[observation]
                rule = SE.index(beliefs)
                numerator = SE.values[rule][str(actions)]
                beliefs = numerator*beliefs
                beliefs *= 1./sum(beliefs.getArray())
        else:
            dynamics = self.dynamics[str(actions)]
            beliefs = dynamics[beliefs]*beliefs
        if doForReal:
            self.beliefs = beliefs
        return beliefs

    def getDynamics(self,act,feature,cache=False,debug=False):
        """
        @return: this entity's dynamics model for the given action
        @param act: the action whose effect we are interested in
        @type act: L{Action}
        @param feature: the feature whose effect we want to get the dynamics for
        @type feature: C{str}
        @param cache: if C{True}, then save the instantiated dynamics for future recall (default is C{False})
        @type cache: bool
        @rtype: L{PWLDynamics}
        @param debug: if C{True}, prints out some debugging statements (default is C{False}
        @type debug: bool
        """
        if debug:
            print 'Computing effect of %s on %s\'s %s' % \
                  (str(act),self.name,feature)
        try:
            dynFun = self.dynamics[feature][act]
            if debug:
                print '\tAlready computed'
        except KeyError:
            try:
                dynFun = self.dynamics[feature][act['type']]
                if debug:
                    print '\tFound generic dynamics'
            except KeyError:
                # It's OK for an action to have no dynamics
                # (e.g., the "wait" action)
                if debug:
                    print '\tNo generic dynamics'
                return None 
            if isinstance(dynFun,str):
                # Linked to uninstantiated dynamics in generic society
                if debug:
                    print '\tLink to generic dynamics'
                dynFun = self.society[dynFun].dynamics[feature][act['type']]
            if dynFun:
                if debug:
                    print '\tInstantiating...'
                if isinstance(dynFun,dict):
                    dynFun = PWLDynamics({'tree':dynFun['tree']})
                dynFun = dynFun.instantiate(self,act)
                tree = dynFun.getTree()
                if tree.isLeaf():
                    matrix = tree.getValue()
                    if isinstance(matrix,IdentityMatrix):
                        # Don't bother storing identities as trees
                        dynFun = None
                    else:
                        # Check whether it's an untagged identity
                        key = StateKey({'entity':self.name,'feature':feature})
                        vector = matrix[key]
                        if abs(sum(vector.getArray())-1.) < Distribution.epsilon and \
                           abs(vector[key]-1.) < Distribution.epsilon:
                            dynFun = None
                    if dynFun is None:
                        if debug:
                            print '\tNull effect'
                        return None
            if cache:
                if dynFun and self.world:
                    # Check for identical dynamics somewhere else
                    for other in self.world.members():
                        for key,table in other.dynamics.items():
                            for action,dynamics in table.items():
                                if isinstance(action,Action) and \
                                       isinstance(dynamics,PWLDynamics) and \
                                       dynamics.getTree() == dynFun.getTree():
                                    if debug:
                                        print '\tLink to effect of %s on %s\'s %s' % (str(action),other.name,key)
                                    dynFun = {'entity':other.name,
                                              'feature':key,
                                              'action':action}
                                    break
                            if isinstance(dynFun,dict):
                                break
                        if isinstance(dynFun,dict):
                            break
                try:
                    self.dynamics[feature][act] = dynFun
                except KeyError:
                    self.dynamics[feature] = {act: dynFun}
                if debug:
                    print '\tCached'
                    assert isinstance(act,Action)
                    assert self.dynamics[feature].has_key(act)
        if isinstance(dynFun,dict):
            # Linked to instantiated dynamics somewhere else
            return self.world[dynFun['entity']].dynamics[dynFun['feature']][dynFun['action']]
        else:
            # Actual dynamics objects
            return dynFun


    def compileGoals(self,debug=False):
        """
        Compiles dynamics for goal-relevant features
        """
        savings = 0
        goals = self.goals.expectation()
        keys = filter(lambda k:isinstance(k,StateKey) and goals[k] > 1e-5,
                      goals.keys())
        keys.sort()
        for key in keys:
            entity = self.world[key['entity']]
            if entity.dynamics.has_key(key['feature']):
                if debug:
                    print 'Compiling %s\'s goal of %s' % (self.name,
                                                          str(key))
                for option in self.actions.getOptions():
                    assert len(option) == 1
                    dynamics = entity.getDynamics(option[0],key['feature'],
                                                  cache=True,debug=debug)
        self.compiled = True

    def __xml__(self,dynamics=False):
        """
        @param dynamics: if C{True}, instantiated dynamics are stored as well (default is C{False}
        @type dynamics: bool
        """
        doc = Agent.__xml__(self)
        # Dynamics
        node = doc.createElement('dynamics')
        doc.documentElement.appendChild(node)
        for feature,subDict in self.dynamics.items():
            featureNode = doc.createElement('feature')
            node.appendChild(featureNode)
            featureNode.setAttribute('label',feature)
            for actType,dynamic in subDict.items():
                if isinstance(actType,str):
                    # This test prevents the saving of compiled dynamics
                    actNode = doc.createElement('action')
                    actNode.setAttribute('compiled','0')
                    featureNode.appendChild(actNode)
                    actNode.setAttribute('type',actType)
                    if isinstance(dynamic,str):
                        actNode.setAttribute('link',dynamic)
                    else:
                        actNode.appendChild(dynamic.__xml__().documentElement)
                else:
                    # Store compiled dynamics
                    actNode = actType.__xml__().documentElement
                    actNode.setAttribute('compiled','1')
                    featureNode.appendChild(actNode)
                    if dynamic is None:
                        raise UserWarning
                    elif isinstance(dynamic,dict):
                        link = doc.createElement('link')
                        link.setAttribute('entity',dynamic['entity'])
                        link.setAttribute('feature',dynamic['feature'])
                        link.appendChild(dynamic['action'].__xml__().documentElement)
                        actNode.appendChild(link)
                    else:
                        actNode.appendChild(dynamic.__xml__().documentElement)
        # Relationships
        node = doc.createElement('relationships')
        doc.documentElement.appendChild(node)
        for label,agents in self.relationships.items():
            relationshipNode = doc.createElement('relationship')
            node.appendChild(relationshipNode)
            relationshipNode.setAttribute('label',label)
            for name in agents:
                subNode = doc.createElement('relatee')
                subNode.appendChild(doc.createTextNode(name))
                relationshipNode.appendChild(subNode)
        # Add beliefs
        if not self.beliefs is self.state:
            node = doc.createElement('beliefs')
            doc.documentElement.appendChild(node)
            node.appendChild(self.beliefs.__xml__().documentElement)
        # Add policy
        node = doc.createElement('policy')
        doc.documentElement.appendChild(node)
        node.appendChild(self.policy.__xml__().documentElement)
        # Actions
        node = doc.createElement('actions')
        doc.documentElement.appendChild(node)
        node.appendChild(self.actions.__xml__().documentElement)
        # Goals
        node = doc.createElement('goals')
        doc.documentElement.appendChild(node)
        node.appendChild(self.goals.__xml__().documentElement)
        # Classes
        for cls in self.classes:
            node = doc.createElement('class')
            node.setAttribute('name',cls)
            doc.documentElement.appendChild(node)
        # Dynamic relationships
        node = doc.createElement('links')
        node.appendChild(self.links.__xml__().documentElement)
        doc.documentElement.appendChild(node)
        # Write available link types
        for linkType in self.getLinkTypes():
            node = doc.createElement('linktype')
            node.setAttribute('name',linkType)
            doc.documentElement.appendChild(node)
        # Write link dynamics
        for linkType,table in self.linkDynamics.items():
            for action,dynamics in table.items():
                if isinstance(action,str):
                    node = doc.createElement('linkdynamics')
                    node.setAttribute('feature',linkType)
                    node.setAttribute('action',action)
                    node.appendChild(dynamics.__xml__().documentElement)
                    doc.documentElement.appendChild(node)
        return doc

    def parse(self,element):
        Agent.parse(self,element)
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'dynamics':
                    node = child.firstChild
                    while node:
                        if node.nodeType == node.ELEMENT_NODE:
                            assert(node.tagName=='feature')
                            feature = str(node.getAttribute('label'))
                            self.dynamics[feature] = {}
                            subNode = node.firstChild
                            while subNode:
                                if subNode.nodeType == subNode.ELEMENT_NODE:
                                    assert(subNode.tagName=='action')
                                    flag = subNode.getAttribute('compiled')
                                    if flag == '':
                                        flag = False
                                    else:
                                        flag = int(flag)
                                    if flag:
                                        # Instantiated dynamics
                                        self.compiled = True
                                        link = subNode.firstChild
                                        while link:
                                            if link.nodeType == link.ELEMENT_NODE and (link.tagName == 'link' or link.tagName == 'dynamic'):
                                                break
                                            link = link.nextSibling
                                        else:
                                            raise UserWarning,subNode.toxml()
                                        if link.tagName == 'link':
                                            # Link to other dynamics
                                            dyn = {'entity':str(link.getAttribute('entity')),
                                                   'feature':str(link.getAttribute('feature')),
                                                   'action':Action()}
                                            action = link.firstChild
                                            while action:
                                                if action.nodeType == action.ELEMENT_NODE:
                                                    break
                                                action = action.nextSibling
                                            assert action.tagName == 'action'
                                            dyn['action'] = dyn['action'].parse(action)
                                        else:
                                            # Dynamics stored here
                                            dyn = PWLDynamics()
                                            dyn.parse(link)
                                        # Store dynamics under action
                                        action = Action()
                                        action.parse(subNode)
                                        self.dynamics[feature][action] = dyn
                                    else:
                                        # Uninstantiated dynamics
                                        actionType = str(subNode.getAttribute('type'))
                                        assert(actionType not in self.dynamics[feature].keys())
                                        dyn = str(subNode.getAttribute('link'))
                                        if not dyn:
                                            dyn = PWLDynamics()
                                            subchild = subNode.firstChild
                                            while subchild and subchild.nodeType != child.ELEMENT_NODE:
                                                subchild = subchild.nextSibling
                                            dyn.parse(subchild)
                                        self.dynamics[feature][actionType] = dyn
                                subNode = subNode.nextSibling
                        node = node.nextSibling
                elif child.tagName == 'actions':
                    subNode = child.firstChild
                    while subNode and subNode.nodeType != subNode.ELEMENT_NODE:
                        subNode = subNode.nextSibling
                    if subNode:
                        self.actions = parseSpace(subNode)
                        for action in self.actions.getOptions():
                            for subAct in action:
                                subAct['actor'] = self.name
                elif child.tagName == 'beliefs':
                    subNodes = child.getElementsByTagName('distribution')
                    if len(subNodes) == 1:
                        self.beliefs.parse(subNodes[0],KeyedVector)
                    elif len(subNodes) > 1:
                        raise UserWarning,'Multiple distributions in beliefs'
                    else:
                        raise UserWarning,'Missing distribution in beliefs'
                elif child.tagName == 'policy':
                    subNode = child.firstChild
                    while subNode and subNode.nodeType != subNode.ELEMENT_NODE:
                        subNode = subNode.nextSibling
                    if subNode:
##                        self.policy = PolicyTable(self,self.actions)
                        self.policy.parse(subNode)
                elif child.tagName == 'goals':
                    self.goals.parse(child.firstChild,KeyedVector)
                elif child.tagName == 'class':
                    self.classes.append(str(child.getAttribute('name')))
                elif child.tagName == 'relationships':
                    node = child.firstChild
                    while node:
                        if node.nodeType == node.ELEMENT_NODE:
                            label = str(node.getAttribute('label'))
                            self.relationships[label] = []
                            subNode = node.firstChild
                            while subNode:
                                if subNode.nodeType == subNode.ELEMENT_NODE:
                                    assert(subNode.tagName == 'relatee')
                                    name = subNode.firstChild.data
                                    name = str(name).strip()
                                    self.relationships[label].append(name)
                                subNode = subNode.nextSibling
                        node = node.nextSibling
                elif child.tagName == 'links':
                    node = child.firstChild
                    while node:
                        if node.nodeType == node.ELEMENT_NODE:
                            self.links = self.links.parse(node)
                            break
                        node = node.nextSibling
                elif child.tagName == 'linktype':
                    linkType = str(child.getAttribute('name'))
                    if not self.linkDynamics.has_key(linkType):
                        assert not linkType in self.linkTypes
                        self.linkTypes.append(linkType)
                        self.linkDynamics[linkType] = {}
                elif child.tagName == 'linkdynamics':
                    linkType = str(child.getAttribute('feature'))
                    action = str(child.getAttribute('action'))
                    dyn = PWLDynamics()
                    subChild = child.firstChild
                    while subChild:
                        if subChild.nodeType == child.ELEMENT_NODE:
                            dyn.parse(subChild)
                            break
                        subChild = subChild.nextSibling
                    try:
                        self.linkDynamics[linkType][action] = dyn
                    except KeyError:
                        self.linkDynamics[linkType] = {action: dyn}
                elif child.tagName in ['trust','liking']:
                    # Obsolete, but harmless
                    pass
##                else:
##                    print 'Unhandled tag %s for lightweight agent %s' % \
##                          (child.tagName,self.name)
            child = child.nextSibling
