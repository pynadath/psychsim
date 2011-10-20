"""Generic class for defining an agent and its capabilities
@author: David V. Pynadath <pynadath@ict.usc.edu>
"""
import copy
from xml.dom.minidom import Document,parse
from teamwork.action.PsychActions import Action,ActionCondition
from teamwork.action.DecisionSpace import DecisionSpace,parseSpace
from teamwork.math.Keys import Key
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.math.probability import Distribution
from teamwork.math.ProbabilityTree import ProbabilityTree
from teamwork.policy.pwlTable import PWLTable
from teamwork.policy.pwlPolicy import PWLPolicy

class Agent:
    """Top-level agent class
    @cvar actionClass: the Python class for this agent's option instances
    @type actionClass: L{Action} subclass (default is L{action})
    @ivar name: the unique label for this agent
    @type name: string
    @ivar actions: the space of possible actions this agent can perform
    @type actions: L{DecisionSpace}
    @ivar omega: set of possible observations
    @ivar observations: trees for observation function
    @ivar O: matrix-based representation of observation function
    @ivar horizon: the horizon of this agent's lookahead
    @type horizon: int
    """
    actionClass = Action
    
    def __init__(self,name='Generic Agent'):
        """
        @param name: a label string
        @type name: str
        """
        self.setName(name)
        self.world = None
        # A_i
        self.actions = DecisionSpace()
        # Omega_i (defaults to null observation and perfect observation of actions)
        self.omega = {None: True, True: True}
        # O_i (defaults to perfect observability)
        self.observations = []
        self.O = {}
        # Sigma_i
        self.messages = []
        # B_i^0
        self.beliefs = self.initialStateEstimator()
        # State Estimators
        self.estimators = {}
        # Subjective transition probability distribution
        self.T = {}
        # Policy
        self.horizon = 1
        self.policy = PWLPolicy(self,self.actions,self.horizon)
        # Extra attributes
        self.attributes = {}

    def setName(self,name):
        """Sets the name of this agent
        @param name: the unique ID for this agent
        @type name: C{str}
        """
        self.name = name

    def legalActions(self,state):
        """Default method for specifying the set (i.e., list) of
	    actions that this agent can choose from in the given state"""
        return self.actions[:]

    def legalMessages(self,state):
        """Default method for specifying the set (i.e., list) of
	    messages that this agent can choose from in the given state"""
        return self.messages[:]
        
    def generateAllObservations(self):
        try:
            return self.allObservations
        except AttributeError:
            self.allObservations = [{}]
            for key in self.omega.keys():
                for omega in self.allObservations[:]:
                    self.allObservations.remove(omega)
                    for value in self.observations[key]:
                        newOmega = copy.copy(omega)
                        newOmega[key] = value
                        self.allObservations.append(newOmega)
            return self.allObservations
   
    def generateHistories(self,length):
        result = [[]]
        for t in range(length):
            # Generate possible observations
            for history in result[:]:
                result.remove(history)
                for omega in self.generateAllObservations():
                    newHistory = copy.copy(history)
                    newHistory.append({'type':'observation',
                                       'value':omega})
                    result.append(newHistory)
            # Generate possible actions
            for history in result[:]:
                result.remove(history)
                for action in self.actions:
                    newHistory = copy.copy(history)
                    newHistory.append({'type':'action',
                                       'value':action})
                    result.append(newHistory)
        return result
        
    # The state estimators.  These default methods implement "perfect
    # recall"

    # SE^0_i
    def initialStateEstimator(self):
        """Generates the initial belief state for the specified agent"""
        return []

    # SE_i\bullet\Sigma
    def preComStateEstimator(self,beliefs,obs,action,epoch=-1):
        """Updates the agent's beliefs based on its observations and action"""
        newBeliefs = beliefs[:]
        newBeliefs.insert(0,obs)
        if epoch >= 0:
            newBeliefs[0]['_epoch'] = epoch
        return newBeliefs

    # SE_i\Sigma\bullet
    def postComStateEstimator(self,beliefs,msgs,epoch=-1):
        """Updates the agent's beliefs based on received messages"""
        newBeliefs = beliefs[:]
        newBeliefs.insert(0,msgs)
        if epoch >= 0:
            newBeliefs[0]['_epoch'] = epoch
        return newBeliefs

    def getOmega(self):
        """
        @return: the set of possible observations (i.e., Omega without special symbols C{True} and C{None}
        @rtype: L{Key}[]
        """
        return filter(lambda o: isinstance(o,Key),self.omega.keys())

    def observable(self):
        """
        @return: C{True} iff this agent has perfect observability of all actions
        @rtype: bool
        @warning: This is a superficial check that the observation function specifies C{True} for all action combinations.  It will return C{False} if there are branches, non-C{True} leaf nodes, I{even} if the end result is equivalent to perfect observability
        """
        if len(self.observations) == 0:
            # Nothing is observable
            return True
        for entry in self.observations:
            if len(entry['actions']) > 0:
                # At least one action required
                return False
            elif not entry['actions'].only:
                # No actions allowed
                return False
            elif not entry['tree'].isLeaf():
                # A branch in the function
                return False
            elif not entry['tree'].getValue() is True:
                # Something other than perfect observability
                return False
        else:
            # Our observation function passed all tests
            return True

    def observe(self,state,actions):
        """
        @param actions: the performed actions, indexed by actor name
        @type actions: C{dict:strS{->}L{Action}[]}
        @return: observations this entity would make of the given actions, in the same format as the provided action dictionary
        @rtype: C{dict}
        """
        key = self.makeActionKey(actions)
        try:
            # We got us a cache
            tree = self.obsCache[key]
        except KeyError:
            # Extract arguments for instantiation of generic observation functions
            table = {}
            for action in sum(actions.values(),[]):
                for key in action.keys():
                    if not table.has_key(key):
                        table[key] = action[key]
                    elif table[key] and action[key] and table[key] != action[key]:
                        table[key] = None
            for key,value in table.items():
                if value is None:
                    del table[key]
            table['self'] = self
            # Look for matching observation function
            for entry in self.observations:
                if entry['actions'].match(actions):
                    tree = entry['tree'].instantiate(table)
                    break
            else:
                # No matching
                tree = None
            self.obsCache[key] = tree
        if tree:
            observations = tree[state]
        else:
            observations = True
        if observations is True:
            # Perfect observation of performed actions
            observations = {}
            for actor,action in actions.items():
                if actor == self.name:
                    # Always observe our own actions (I assume this is OK)
                    observations[actor] = action
                else:
                    observation = []
                    # Placeholder while we modify observation model
                    for subAct in action:
                        # By default, assume observable
                        observation.append(subAct)
                    if len(observation) > 0:
                        # Only add observations if we have any (questionable?)
                        observations[actor] = observation
        if isinstance(observations,str):
            # Not a problem, we just have certainty
            observations = Distribution({observations: 1.})
        return observations

    def getObservationMatrix(self,actions,worlds={}):
        """
        @return: a matrix representation of the observation function over the given possible worlds
        @rtype: L{KeyedMatrix}
        """
        if isinstance(actions,str):
            actionKey = actions
        else:
            actionKey = self.makeActionKey(actions)
        try:
            return self.O[actionKey]
        except KeyError:
            matrix = KeyedMatrix()
            for col,world in worlds.items():
                distribution = self.observe(world,actions)
                for omega in self.getOmega():
                    try:
                        prob = distribution[omega]
                    except KeyError:
                        prob = 0.
                    matrix.set(omega,col,prob)
            matrix.freeze()
            self.O[actionKey] = matrix
            return matrix

    def decideModel(self,world):
        table = self.policy.getTable()
        assert len(table.rules) == 1
        return table.rules[0]['rhs']

    def actionDistribution(self,world,myAction,debug=False):
        """
        @param world: the belief vector of the given world
        @param myAction: the action that I'm doing
        @return: a list of joint actions (with probabilities) over other agents based on expectations in the given world
        """
        nodes = [({self.name: myAction},1.)]
        # Extract actions by others based on mental models
        for agent in filter(lambda a: a.name != self.name,
                            self.entities.activeMembers()):
            rhs = agent.decideModel(world)
            if isinstance(rhs,str):
                for option in agent.actions.getOptions():
                    if agent.makeActionKey(option) == rhs:
                        break
                else:
                    raise NameError,'Unknown RHS action %s' % (rhs)
            else:
                option = rhs
            for actions,prob in nodes:
                actions[agent.name] = option
        return nodes
        
    def getT(self,debug=False):
        """
        @return: a transition function based on only this agent's actions
        """
        self.T.clear()
        trans = self.entities.getDynamicsMatrix(self.name,debug)
        for myAction in self.actions.getOptions():
            # Consider each of my possible actions
            myKey = self.makeActionKey(myAction)
            # Initialize transition matrix
            self.T[myKey] = KeyedMatrix()
            for rowKey,world in self.entities.getWorlds().items():
                self.T[myKey][rowKey] = KeyedVector()
                for colKey in self.entities.getWorlds().keys():
                    self.T[myKey].set(rowKey,colKey,0.)
            for colKey,world in self.entities.getWorlds().items():
                # Generate possible joint actions in this world
                nodes = self.actionDistribution(world,myAction)
                for actions,prob in nodes:
                    actions[self.name] = myAction
                if debug:
                    print 'action:',myKey
                    print 'start:',colKey,world.simpleText()
                    for agent in self.entities.members():
                        try:
                            model = agent.models[agent.identifyModel(world)]
                            print agent.name,model['beliefs'][0].simpleText()
                        except KeyError:
                            pass
                # Fill in matrices
                for actions,prob in nodes:
                    joint = self.makeActionKey(actions)
                    if debug:
                        print 'joint:',joint,prob
                        print trans[joint].simpleText()
                    for rowKey in self.entities.getWorlds().keys():
                        old = self.T[myKey][rowKey][colKey]
                        delta = prob*trans[joint][rowKey][colKey]
                        self.T[myKey].set(rowKey,colKey,old+delta)
                        if debug:
                            print
                            endWorld = self.entities.worlds[rowKey]
                            print 'end:',rowKey,endWorld.simpleText()
                            print '\tT:',trans[joint][rowKey][colKey]
                            for agent in self.entities.members():
                                try:
                                    model = agent.models[agent.identifyModel(endWorld)]
                                    print agent.name,model['beliefs'][0].simpleText()
                                except KeyError:
                                    pass
                            print '\tProbability:',delta
            if debug:
                print myKey
                print self.T[myKey].getArray()
                belief = self.entities.state2world(self.beliefs)
                print 'Current:',belief.getArray()
                belief = self.T[myKey]*belief
                assert sum(belief.getArray()) == 1.
                print 'Projected:',belief.simpleText()
                print
        return self.T

    def getO(self,debug=False):
        """
        @return: an observation function from this agent's individual view
        """
        O = {}
        for myAction in self.actions.getOptions():
            myKey = self.makeActionKey(myAction)
            O[myKey] = KeyedMatrix() 
            for key,world in self.entities.getWorlds().items():
                O[myKey][key] = KeyedVector()
                for omega in self.getOmega():
                    O[myKey].set(key,omega,0.)
                nodes = self.actionDistribution(world,myAction)
                for actions,prob in nodes:
                    distribution = self.getObservationMatrix(actions,self.entities.getWorlds())
                    for omega in self.getOmega():
                        old = O[myKey][key][omega]
                        O[myKey].set(key,omega,old+prob*distribution[omega][key])
        return O
        
    def getEstimator(self,scenario=None,debug=False):
        """Compute state estimator
        """
        if not scenario is None:
            raise NotImplementedError,'Can compute state estimator over only my own beliefs'
        if len(self.estimators) == 0:
            if debug: print '%s computing new state estimator' % (self.name)
            T = self.getT(debug)
            O = self.getO(debug)
            for omega in self.getOmega():
                self.estimators[omega] = PWLTable()
                rule = self.estimators[omega].rules[0]
                for myAction in self.actions.getOptions():
                    myKey = self.makeActionKey(myAction)
                    rule['values'][myKey] = KeyedMatrix()
                    for key,world in self.world.getWorlds().items():
                        rule['values'][myKey][key] = KeyedVector()
                        nodes = [({self.name:myAction},1.)]
                        # Extract actions by others based on mental models
                        for agent in filter(lambda a: a.name != self.name,
                                            scenario.activeMembers()):
                            try:
                                model = agent.models[agent.identifyModel(world)]
                                option = agent.policy.getTable()[model['beliefs'][0]]['rhs']
                                for actions,prob in nodes:
                                    actions[agent.name] = option
                            except KeyError:
                                depth = self.policy.getDepth()
                                if depth > 0:
                                    table = agent.policy.getTable(depth=depth-1)
                                else:
                                    table = agent.policy.getTable()
                                for index in range(len(nodes)):
                                    actions,prob = nodes.pop(0)
                                    for otherRule in table.rules:
                                        subprob = 1.
                                        for attr in range(len(otherRule['lhs'])):
                                            plane,values = table.attributes[attr]
                                            assert len(plane) == 2
                                            a,b = plane.getArray()
                                            threshold = -b/(a-b)
                                            if otherRule['lhs'][attr] == 0:
                                                # Less than threshold
                                                subprob *= threshold
                                            elif otherRule['lhs'][attr] == 1:
                                                # Greater than threshold
                                                subprob *= 1.-threshold
                                        new = copy.deepcopy(actions)
                                        new[agent.name] = otherRule['rhs']
                                        nodes.append((new,prob*subprob))
                        # Fill in matrices
                        for colKey in self.entities.getWorlds().keys():
                            value = T[myKey][rowKey][colKey]
                            value *= O[myKey][colKey][omega]
                            rule['values'][myKey].set(rowKey,colKey,value)
        return self.estimators

    def __cmp__(self,agent):
        """Default comparison function...treats all agents equally"""
        return 0
            
    def makeActionKey(self,actions):
        """
        @type actions: strS{->}L{Action}[] or L{Action}[]
        @return: unique string key to represent given joint action
        @rtype: str
        """
        if len(actions) == 0:
            key = ''
        elif isinstance(actions,dict):
            # Joint action
            if len(actions) == 1:
                key = self.makeActionKey(actions.values()[0])
            else:
                key = ','.join(map(lambda A: self.makeActionKey(A),
                                   actions.values()))
        else:
            # Individual action
            if len(actions) == 1:
                key = str(actions[0])
            else:
                key = ','.join(map(str,actions))
        return key

    def __copy__(self):
        new = self.__class__(name=self.name)
        new.messages = self.messages
        new.actions = self.actions
        new.omega.update(self.omega)
        new.observations = self.observations[:]
        return new

    def __xml__(self):
        doc = Document()
        root = doc.createElement('agent')
        doc.appendChild(root)
        doc.documentElement.setAttribute('name',self.name)
        # Add horizon
        doc.documentElement.setAttribute('horizon',str(self.horizon))
        # Actions
        node = doc.createElement('actions')
        root.appendChild(node)
        node.appendChild(self.actions.__xml__().documentElement)
        # Observation symbols
        element = doc.createElement('observations')
        for key,value in self.omega.items():
            if isinstance(key,Key):
                # Don't bother adding special observations (C{None} and C{True})
                element.appendChild(key.__xml__().documentElement)
        # Observation function
        for entry in self.observations:
            node = doc.createElement('O')
            for key,value in entry.items():
                if key == 'actions':
                    node.appendChild(value.__xml__().documentElement)
                elif key == 'tree':
                    node.appendChild(value.__xml__().documentElement)
                else:
                    node.setAttribute(key,str(value))
            element.appendChild(node)
        root.appendChild(element)
        # Policy
        if self.policy:
            root.appendChild(self.policy.__xml__().documentElement)
        # State estimators
        for omega,table in self.estimators.items():
            node = doc.createElement('estimator')
            node.appendChild(omega.__xml__().documentElement)
            node.appendChild(table.__xml__().documentElement)
            root.appendChild(node)
        # Miscellaneous attributes
        for key,value in self.attributes.items():
            if key == 'image':
                pass
            elif key == 'coords':
                coords = self.attributes['coords']
                doc.documentElement.setAttribute('x0',str(coords[0]))
                doc.documentElement.setAttribute('y0',str(coords[1]))
                doc.documentElement.setAttribute('x1',str(coords[2]))
                doc.documentElement.setAttribute('y1',str(coords[3]))
            elif isinstance(value,str):
                doc.documentElement.setAttribute(key,value)
        return doc

    def parse(self,element):
        assert(element.tagName == 'agent')
        self.setName(str(element.getAttribute('name')))
        arg = str(element.getAttribute('image')).strip()
        if not arg:
            arg = str(element.getAttribute('imageName')).strip()
        if arg:
            self.attributes['imageName'] = arg
        try:
            self.horizon = int(element.getAttribute('horizon'))
        except ValueError:
            pass
        arg = str(element.getAttribute('x0')).strip()
        if arg:
            coords = [float(arg),
                      float(element.getAttribute('y0')),
                      float(element.getAttribute('x1')),
                      float(element.getAttribute('y1')),
                      ]
            self.attributes['coords'] = coords
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'observations':
                    # Parse observations
                    subchild = child.firstChild
                    while subchild:
                        if subchild.nodeType == child.ELEMENT_NODE:
                            if subchild.tagName == 'key':
                                key = Key()
                                key = key.parse(subchild)
                                self.omega[key] = True
                            elif subchild.tagName == 'O':
                                entry = {'actions': ActionCondition(),
                                         'tree': ProbabilityTree()}
                                for key,value in subchild.attributes.items():
                                    entry[str(key)] = bool(value)
                                node = subchild.firstChild
                                while node:
                                    if node.nodeType == node.ELEMENT_NODE and \
                                            node.tagName == 'condition':
                                        entry['actions'].parse(node)
                                    elif node.nodeType == node.ELEMENT_NODE and \
                                            node.tagName == 'tree':
                                        entry['tree'].parse(node,str)
                                    node = node.nextSibling
                                self.observations.append(entry)
                        subchild = subchild.nextSibling
                elif child.tagName == 'actions':
                    subNode = child.firstChild
                    while subNode and subNode.nodeType != subNode.ELEMENT_NODE:
                        subNode = subNode.nextSibling
                    if subNode:
                        self.actions = parseSpace(subNode)
                elif child.tagName == 'policy':
                    self.policy = PWLPolicy(self,self.actions,self.horizon)
                    self.policy.parse(child)
                elif child.tagName == 'estimator':
                    subNode = child.firstChild
                    while subNode and subNode.nodeType != subNode.ELEMENT_NODE:
                        subNode = subNode.nextSibling
                    key = Key()
                    key = key.parse(subNode)
                    subNode = subNode.nextSibling
                    while subNode and subNode.nodeType != subNode.ELEMENT_NODE:
                        subNode = subNode.nextSibling
                    table = PWLTable()
                    table.parse(subNode)
                    self.estimators[key] = table
            child = child.nextSibling
            
if __name__ == '__main__':
    import os.path
    
    agent = Agent()
    name = '/tmp/%s.xml' % (os.path.basename(__file__))
    file = open(name,'w')
    file.write(agent.__xml__().toxml())
    file.close()

    new = Agent()
    new.parse(parse(name))
    print new
