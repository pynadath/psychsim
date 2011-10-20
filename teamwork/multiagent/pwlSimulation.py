"""Lightweight multiagent simulation
"""
import bz2
import copy
import sys
import time
from xml.dom.minidom import Document,parseString,parse
from Multiagent import MultiagentSystem
from teamwork.math.Keys import StateKey,LinkKey,ConstantKey
from teamwork.action.PsychActions import Action
from teamwork.agent.lightweight import PWLAgent
from teamwork.math.probability import Distribution
from teamwork.math.KeyedVector import KeyedVector,UnchangedRow,DeltaRow
#from teamwork.math.KeyedMatrix import KeyedMatrix
from teamwork.dynamics.pwlDynamics import PWLDynamics

class PWLSimulation(MultiagentSystem):
    """
    @ivar societyFile: the location of the L{GenericSociety<teamwork.multiagent.GenericSociety.GenericSociety>}
    @type societyFile: str
    """
    
    def __init__(self,agents=None,observable=False):
        """Initializes a collection to contain the given list of agents
        @param agents: the fully-specified agents
        @param observable: iff C{True}, agents always maintain correct beliefs about the world
        @type observable: bool
        @param effects: a table of features that actions affect, indexed by action, with each value being a list of keys
        @type effects: L{Action}S{->}L{StateKey}[]
        """
        self.societyFile = None
        self.observable = observable
        self.effects = {}
        if agents is None:
            MultiagentSystem.__init__(self)
            self.state = Distribution({KeyedVector():1.})
        else:
            members = []
            for agent in agents.members():
                new = PWLAgent(agent)
                if not new.policy.tables:
                    # No policy for this agents; let's check whether
                    # somebody else computed one
                    for other in agents.members():
                        if other.name != agent.name:
                            try:
                                belief = other.getEntity(agent.name)
                                if belief.policy.rules:
                                    new.policy = belief.policy
                                    break
                            except KeyError:
                                pass
                members.append(new)
            MultiagentSystem.__init__(self,members)
            self.state = agents.state
            self.initialize()
        self.time = 0
        self.history = {}

    def initialize(self):
        self.effects.clear()
        for agent in self.members():
            if agent.beliefs is agent.state:
                agent.beliefs = self.state
            agent.state = self.state
            agent.world = self
##             for option in agent.actions.getOptions():
##                 for action in option:
##                     self.effects[action] = []
##                     for other in self.members():
##                         for feature,table in other.dynamics.items():
##                             if table.has_key(action) or \
##                                table.has_key(action['type']):
##                                 key = StateKey({'entity':other.name,
##                                                 'feature':feature})
##                                 self.effects[action].append(key)
        
    def microstep(self,turns,hypothetical=False,explain=False,
                  state=None,suggest=False,debug=False):
        """Step forward by the action of the given entities
        @param turns: the agents to act next, each entry in the list should be a dictionary:
           - I{name}: the name of the agent to act
           - I{choices}: the list of possible options this agent can consider in this turn (defaults to the list of all possible actions if omitted, or if the list is empty)
           - I{history}: a dictionary of actions already performed (defaults to the built-in history of this simulation instance)
        @type turns: C{dict[]}
        @param hypothetical: if C{True}, then this is only a hypothetical microstep; otherwise, it is real (default is C{False})
        @type hypothetical: bool
        @param explain: if C{True}, then add an explanation to the result (default is C{False})
        @type explain: bool
        @return: XML results
        @rtype: Element
        @param suggest: this is ignored
        @type suggest: bool
        """
        start = time.time()
        # Generate XML explanation
        doc = Document()
        root = doc.createElement('step')
        doc.appendChild(root)
        root.setAttribute('time',str(self.time+1))
        root.setAttribute('hypothetical',str(hypothetical))
        # Cache of values
        values = {}
        # Build up the list of selected actions
        actionDict = {}
        raw = {}
        for turn in turns:
            name = turn['name']
            actor = self[name]
            try:
                choices = turn['choices']
            except KeyError:
                choices = []
            if self.history is None:
                history = None
            else:
                try:
                    history = turn['history']
                except KeyError:
                    history = copy.copy(self.history)
            if len(choices) == 0:
                for option in actor.actions.getOptions():
                    choices.append(option)
##                     if len(option) == 0:
##                         # Doing nothing is always an option?
##                         choices.append(option)
##                     elif not actor.actions.illegal.has_key(str(option)):
##                         # No deactivation of actions, so everything's possible
##                         choices.append(option)
            if len(choices) == 1:
                actionDict[name] = choices[0]
                exp = None
            elif len(choices) > 1:
                action,exp = actor.applyPolicy(actions=choices,history=history,
                                               explain=explain,entities=self,
                                               cache=values,state=state)
                actionDict[name] = action
            else:
                # No actions for this actor
                continue
            node = doc.createElement('turn')
            root.appendChild(node)
            node.setAttribute('agent',name)
            node.setAttribute('time',str(self.time+1))
            node.setAttribute('forced',str(len(choices) == 1))
            subDoc = self.explainAction(actionDict[name])
            node.appendChild(subDoc.documentElement)
            if exp:
                if explain:
                    node.appendChild(exp.documentElement)
                raw[name] = exp
        if debug:
            print 'Decision time:',time.time()-start
        start = time.time()
        # Update state and beliefs
        if state is None:
            current = None
        else:
            current = state[None]
        result = {'decision': actionDict,
                  'delta': self.hypotheticalAct(actionDict,doc,current),
                  'explanation': doc,
                  'raw': raw,
                  }
        if debug:
            print 'Delta time:',time.time()-start
        if not hypothetical and sum(actionDict.values(),[]):
            start = time.time()
            # Update state (both objective and subjective) if real
            # and if there's at least one action being performed
            self.applyChanges(result['delta'])
            # Update simulation clock
            self.time += 1
            if not self.history is None:
                # Update action history
                for option in actionDict.values():
                    for action in option:
                        self.history[str(action)] = True
            if debug:
                print 'Update time:',time.time()-start
        return result
        
    def hypotheticalAct(self,actions,exp=None,state=None):
        """
        Computes the scenario changes that would result from a given action
        @param actions: dictionary of actions, where each entry is a list of L{Action<teamwork.action.PsychActions.Action>} instances, indexed by the name of the actor
        @type actions: C{dict:str->L{Action<teamwork.action.PsychActions.Action>}[]}
        @return: the changes that would result from I{actions}
          - state:   the change to state, in the form of a L{Distribution} over L{KeyedMatrix} (suitable to pass to L{applyChanges})
          - I{agent}: the change to the recursive beliefs of I{agent}, as returned by L{preComStateEstimator<teamwork.agent.RecursiveAgent.RecursiveAgent.preComStateEstimator>}
        @rtype: C{dict}
        @param exp: an optional partial explanation to expand upon
        @type exp: Document
        """
        if state is None:
            state = self.state
        # Eventual return value, storing up all the various belief
        # deltas across the entities
        overallDelta = {}
        overallDelta['state'] = self.getDelta(actions,state,exp)
        if not self.observable:
            # Update members' subjective beliefs
            for entity in self.members():
                overallDelta[entity.name] = self.getDelta(actions,
                                                          entity.beliefs)
        return overallDelta

    def getState(self):
        """
        @return: a dictionary of 'state' and relationships of the current simulation state
        @rtype: dict
        """
        result = {'__state':self.state}
        for entity in self.members():
            result[entity.name] = entity.links
        return result
    
    def getDelta(self,actions,state,exp=None):
        """
        Computes the changes to the given state distribution that would result from a given action
        @param actions: dictionary of actions, where each entry is a list of L{Action<teamwork.action.PsychActions.Action>} instances, indexed by the name of the actor
        @type actions: C{dict:str->L{Action<teamwork.action.PsychActions.Action>}[]}
        @param state: the initial state
        @type state: L{Distribution}(L{KeyedMatrix})
        @param exp: an optional partial explanation to expand upon
        @type exp: Document
        """
        result = Distribution()
        for vector,oProb in state.items():
            delta = self.applyDynamics(actions,vector,exp)
            for matrix,nProb in delta.items():
                # Update probability of result
                try:
                    result[matrix] += oProb*nProb
                except KeyError:
                    result[matrix] = oProb*nProb
        return result

    def applyDynamics(self,actions,state,exp=None):
        """Compute the effect of the given actions on the given state vector
        @param actions: the dictionary of actions
        @type actions: strS{->}L{Action}[]
        @type state: L{KeyedVector}
        @rtype: dict
        """
        if exp:
            # Determine which parts of explanation we are expanding upon
            turns = {}
            child = exp.documentElement.firstChild
            while child:
                if child.nodeType == child.ELEMENT_NODE and \
                        child.tagName == 'turn':
                    turns[str(child.getAttribute('agent'))] = child
                child = child.nextSibling
        result = Distribution()
        matrix = {}
        remaining = {}
        for key in state.keys():
            if isinstance(key,StateKey):
                remaining[key] = True
        if self.effects:
            # We know which state features are affected by each action
            for option in actions.values():
                for action in option:
                    for key in self.effects[action]:
                        dynamics,delta = self.getEffect(action,key,state)
                        if dynamics:
                            if delta:
                                updateDelta(matrix,key,exp,turns,action,
                                            vector=state,delta=delta)
                            else:
                                delta = updateDelta(matrix,key,exp,turns,
                                                    action,dynamics,state)
                        try:
                            del remaining[key]
                        except KeyError:
                            pass
        else:
            # We have to consider all possible features
            for key in remaining.keys():
                for option in actions.values():
                    for action in option:
                        dynamics,delta = self.getEffect(action,key,state)
                        if dynamics:
                            if delta:
                                delta = updateDelta(matrix,key,exp,turns,
                                                    action,vector=state,delta=delta)
                            else:
                                delta = updateDelta(matrix,key,exp,turns,
                                                    action,dynamics,state)
                            if delta:
                                # Update liking for this actor
                                for entity in self.members():
                                    link = entity.getLinkKey(entity._supportFeature,
                                                             action['actor'])
                                    goals = entity.goals.expectation()
                                    if entity.links.has_key(link) and \
                                           goals.has_key(key):
                                        new = {link:KeyedVector(delta[key])}
                                        new[link][key] -= 1.
                                        new[link] *= goals[key]
                                        new[link][link] = 1.
                                        updateDelta(matrix,link,exp,turns,action,
                                                    vector=state,delta=new)
        # Update other dynamic relationships
        for entity in self.members():
            for link in entity.links.keys():
                if link['verb'] != entity._supportFeature and \
                   link['verb'] != entity._trustFeature:
                    try:
                        option = actions[link['object']]
                    except KeyError:
                        option = []
                    for action in option:
                        try:
                            dynamics = entity.linkDynamics[link['verb']][action['type']]
                        except KeyError:
                            dynamics = None
                        if dynamics:
                            change = dynamics.instantiateAndApply(state,entity,
                                                                  action)
                            updateDelta(matrix,link,exp,turns,action,
                                        vector=state,delta=change)
        # Look for default dynamics
        for key in remaining.keys():
            if not matrix.has_key(key):
                entity = self[key['entity']]
                dynamics = entity.getDynamics(Action({'type':None}),
                                              key['feature'])
                if dynamics:
                    updateDelta(matrix,key,exp,turns,None,dynamics,state)
        result[matrix] = 1.
        return result

    def getEffect(self,action,key,vector,instantiate=True,debug=False):
        """Computes the effect of the given action on the given L{StateKey}
        @return: the dynamics object, and possible a computed delta
        """
        entity = self[key['entity']]
        try:
            # Look for instantiated dynamics
            dynamics = entity.dynamics[key['feature']][action]
            if debug:
                print 'Found instantiated dynamics'
            if isinstance(dynamics,dict):
                # Link to other instantiated dynamics
                if debug:
                    print 'Link to other instance'
                entity = self[dynamics['entity']]
                dynamics = entity.dynamics[dynamics['feature']][dynamics['action']]
            return dynamics,None
        except KeyError:
            if not instantiate:
                # Default is no effect
                if debug:
                    print 'No instantiated dynamics'
                return None,None
        # Look for generic dynamics
        try:
            dynamics = entity.dynamics[key['feature']][action['type']]
        except KeyError:
            if debug:
                print 'No generic dynamics'
            return None,None
        if isinstance(dynamics,str):
            # Access link to generic dynamics
            if debug:
                print 'Link to other generic model'
            dynamics = entity.society[dynamics].dynamics[key['feature']][action['type']]
        if isinstance(dynamics,dict):
            dynamics = PWLDynamics(dynamics)
        if dynamics:
            # Do a partial instantiation
            if entity.name == action['actor']:
                effectKey = 'actor'
            elif entity.name == action['object']:
                effectKey = 'object'
            else:
                effectKey = 'other'
            try:
                applicable = dynamics.effects[effectKey]
            except KeyError:
                applicable = True
            if applicable:
                if debug:
                    print 'Instantiating...'
                    print dynamics.getTree()
                delta = dynamics.instantiateAndApply(vector,self[key['entity']]
                                                     ,action)
                if debug:
                    print delta[key]
                return dynamics,delta
        return None,None

    def applyChanges(self,delta,current=None):
        """Applies the differential changes to this set of entities"""
        if current is None:
            state = self.state
        else:
            state = current[None]
        for key,subDelta in delta.items():
            if key == 'state':
                if len(state) == 1 and len(subDelta) == 1:
                    # Update in place
                    vector = state.domain()[0]
                    delta = subDelta.domain()[0]
                    newVector = {}
                    for key,row in delta.items():
                        newValue = 0.
                        for deltaKey,weight in row.items():
                            if isinstance(deltaKey,LinkKey):
                                if current is None:
                                    newValue += weight*self[key['subject']].links[key]
                                else:
                                    newValue += weight*current[key['subject']][key]
                            elif isinstance(deltaKey,ConstantKey):
                                newValue += weight
                            elif isinstance(deltaKey,StateKey):
                                try:
                                    newValue += weight*vector[deltaKey]
                                except KeyError:
                                    sys.stderr.write('Dynamics for %s refers to nonexistent key %s\n' % (key,deltaKey))
                            else:
                                raise UserWarning,'Unknown delta key: %s' % \
                                      (deltaKey)
                        newVector[key] = max(min(newValue,1.),-1.)
                    # Copy new vector over
                    for key,newValue in newVector.items():
                        if isinstance(key,StateKey):
                            try:
                                index = vector._order[key]
                                vector.getArray()[index] = newValue
                            except KeyError:
                                # New value for nonexistent state feature! Bad!
                                pass
                        elif isinstance(key,LinkKey):
                            if current is None:
                                self[key['subject']].links[key] = newValue
                            else:
                                current[key['subject']][key] = newValue
                        else:
                            print 'Unknown delta:',key,newValue
                    state.clear()
                    state[vector] = 1.
                else:
                    state = subDelta*state
            else:
                # Apply changes to subjective beliefs
                entity = self[key]
                entity.beliefs = subDelta*entity.beliefs
        if current is None:
            # Reattach state (need a cleaner way of doing this)
            for agent in self.members():
                agent.state = state
                if self.observable:
                    agent.beliefs = state
        return state

    def explainAction(self,actions):
        doc = Document()
        root = doc.createElement('decision')
        doc.appendChild(root)
        for action in actions:
            root.appendChild(action.__xml__().documentElement)
        return doc

    def __xml__(self,dynamics=False):
        """
        @param dynamcis: if C{True}, instantiated dynamics are stored as well (default is C{False}
        @type dynamics: bool
        """
        doc = Document()
        root = doc.createElement('multiagent')
        root.setAttribute('type',self.__class__.__name__)
        if self.societyFile:
            root.setAttribute('society',self.societyFile)
        doc.appendChild(root)
        for agent in self.members():
            root.appendChild(agent.__xml__(dynamics).documentElement)
        # Save simulation clock
        root = doc.documentElement
        root.setAttribute('time',str(self.time))
        # Save state vector
        node = doc.createElement('state')
        node.appendChild(self.state.__xml__().documentElement)
        root.appendChild(node)
        # Save action history
        node = doc.createElement('history')
        for action,flag in self.history.items():
            # Every action in the keys should have a flag of True,
            # but why take chances?
            if flag:
                child = doc.createElement('action')
                child.setAttribute('label',action)
                node.appendChild(child)
        root.appendChild(node)
        return doc

    def parse(self,element,agentClass=PWLAgent,societyClass=None):
        """
        @return: C{False} iff unable to load a specified society file
        @rtype: bool
        """
        self.history.clear()
        MultiagentSystem.parse(self,element,agentClass)
        filename = str(element.getAttribute('society'))
        if filename:
            self.societyFile = filename
        # Load simulation clock
        self.time = str(element.getAttribute('time'))
        if self.time:
            self.time = int(self.time)
        else:
            # No such attribute
            self.time = 0
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'state':
                    # Load state vector
                    self.state.parse(child.firstChild,KeyedVector)
                elif child.tagName == 'history':
                    # Load action history
                    grandchild = child.firstChild
                    while grandchild:
                        if grandchild.nodeType == grandchild.ELEMENT_NODE:
                            assert grandchild.tagName == 'action'
                            action = str(grandchild.getAttribute('label'))
                            self.history[action] = True
                        grandchild = grandchild.nextSibling
            child = child.nextSibling
        # If completely observable, everyone's beliefs are real state
        if self.observable:
            for entity in self.members():
                entity.beliefs = self.state
        # Load society if available
        if societyClass and self.societyFile:
            society = societyClass()
            try:
                f = bz2.BZ2File(self.societyFile,'r')
                data = f.read()
                f.close()
            except IOError:
                return False
            doc = parseString(data)
            society.parse(doc.documentElement)
            for agent in self.members():
                agent.society = society
        return True

def updateDelta(matrix,key,exp,turns,action=None,dynamics=None,vector=None,
                delta=None):
    """Updates the given delta by instantiating the given dynamics
    @param action: the action performed
    @type action: L{Action}
    @param dynamics: the dynamics object to instantiate
    @type dynamics: L{PWLDynamics}
    @param vector: the current state vector
    @type vector: L{KeyedVector}
    @param matrix: the delta matrix so far
    @type matrix: dict
    @param key: the key of the delta entry being generated
    @type key: L{StateKey}
    @param exp: the explanation so far
    @type exp: Document
    @param turns: the dictionary of turn effects
    @type turns: L{Action}S{->}Document
    @return: the delta (untouched if passed in, computed if not)
    @rtype: L{KeyedMatrix}
    """
    if delta is None:
        tree = dynamics.getTree()
        while not tree.isLeaf():
            for plane in tree.split:
                if not plane.test(vector):
                    value = False
                    break
            else:
                value = True
            if value:
                tree = tree.trueTree
            else:
                tree = tree.falseTree
        delta = tree.getValue()
    try:
        if not isinstance(delta[key],UnchangedRow):
            if matrix.has_key(key):
                if isinstance(matrix[key],DeltaRow):
                    # Must generic-ize it
                    new = {}
                    for subKey,weight in matrix[key].items():
                        new[subKey] = weight
                    matrix[key] = new
                for subKey,weight in delta[key].items():
                    try:
                        matrix[key][subKey] += weight
                    except KeyError:
                        matrix[key][subKey] = weight
                matrix[key][key] -= 1.
            else:
                matrix[key] = delta[key]
            if exp and action:
                effect = exp.createElement('effect')
                effect.appendChild(key.__xml__().documentElement)
##                 effect.appendChild(delta[key].__xml__().documentElement)
                if isinstance(key,StateKey):
                    effect.setAttribute('delta',str(delta[key]*vector-vector[key]))
                else:
                    effect.setAttribute('delta',str(delta[key]*vector))
                turns[action['actor']].appendChild(effect)
            return delta
    except KeyError:
        pass
    return None

def loadScenario(filename):
    """
    Loads a scenario from the given filename
    @return: the scenario
    @rtype: L{PWLSimulation}
    """
    import teamwork.agent.lightweight
    import GenericSociety

    f = bz2.BZ2File(filename,'r')
    data = f.read()
    f.close()
    doc = parseString(data)
    scenario = PWLSimulation()
    scenario.parse(doc.documentElement,teamwork.agent.lightweight.PWLAgent,
                   GenericSociety.GenericSociety)
    scenario.initialize()
    return scenario

if __name__ == '__main__':
    # First argument is name of XML file (as produced by distillation)
#    from teamwork.action.PsychActions import Action
    try:
        doc = parse(sys.argv[1])
    except IndexError:
        print 'Usage: pwlSimulation.py <initial agents XML file> '\
              '[<final agents XML file>]'
        sys.exit(-1)
    # Initialize set of agents
    agents = PWLSimulation()
    agents.parse(doc.documentElement)
    agents.initialize()
    if False:
        # Simulation structure is built on top of a dictionary
        print 'The following agents are present:',', '.join(agents.keys())
        trainee = agents['US']
        # The following finds the relevant character, if I don't already
        # know its name
        for agent in agents.members():
            if agent.name != 'US' and len(agent.actions.getOptions()) > 0:
                # This must be the character (no one else has actions)
                character = agent
        # Want to know what character'll hypothetically do?
        result = agents.microstep([{'name':character.name}],
                                  # Do not update any state/beliefs
                                  hypothetical=True,
                                  # Don't bother with AAR
                                  explain=False,suggest=False)
        decision = result['decision'][character.name][0]
        print '%s wants to %s from %s' % \
              (decision['actor'],decision['type'],decision['object'])
        # Give character an unconstrained turn
        result = agents.microstep([{'name':character.name}],
                                  # This is for real
                                  hypothetical=False,
                                  # Don't bother with AAR
                                  explain=False,suggest=False)
        decision = result['decision'][character.name][0]
        print '%s makes a %s to %s' % \
              (decision['actor'],decision['type'],decision['object'])
        # Input the trainee's externally chosen action
        for option in trainee.actions.getOptions():
            # Just find the first offer for testing purposes
            if option[0]['type'][:5] == 'offer':
                break
        else:
            print '%s has no offers to make!  Using last action as fallback' % \
            (trainee.name)
        print 'Before %s %s to %s, his negotiation satisfaction is %5.3f' % \
              (option[0]['actor'],option[0]['type'],option[0]['object'],
               character.getBelief(character.name,'negSatisfaction'))
        result = agents.microstep([{'name':trainee.name,'choices':[option]}],
                                  # This is for real
                                  hypothetical=False,
                                  # Don't bother with AAR
                                  explain=False,suggest=False)
        print 'After %s %s to %s, his negotiation satisfaction is %5.3f' % \
              (option[0]['actor'],option[0]['type'],option[0]['object'],
               character.getBelief(character.name,'negSatisfaction'))
        # Give character a constrained turn
        accept = [Action({'actor':character.name,'type':'accept',
                          'object':trainee.name})]
        reject = [Action({'actor':character.name,'type':'reject',
                          'object':trainee.name})]
        result = agents.microstep([{'name':character.name,
                                    'choices':[accept,reject]}],
                                  # This is for real
                                  hypothetical=False,
                                  # Don't bother with AAR
                                  explain=False,suggest=False)
        decision = result['decision'][character.name][0]
        print '%s decides to %s %s' % \
              (decision['actor'],decision['type'],decision['object'])
    # If a second command-line argument is present, it is treated as
    # an output filename (for exercising save/load methods)
    if len(sys.argv) > 2:
        name = sys.argv[2]
        # To generate an XML Document representing the state of the
        # trainee-character interaction
        doc = agents.__xml__()
        # To generate a string representation for saving:
        data = doc.toxml()
        f = open(name,'w')
        f.write(data)
        f.close()
        # To reset the negotiation (i.e., erase character's memory about what
        # actions he's already performed), without changing anything else
        # (like his attitude toward trainee)
        agents.history.clear()
        # To re-load
        doc = parse(name)
        agents.parse(doc.documentElement)
        # Verify that history was loaded as well
        assert len(agents.history) == 3
    if True:
        # Profiling
        import hotshot.stats
        filename = '/tmp/stats'
        prof = hotshot.Profile(filename)
        turns = []
        agent = agents['Insurgents']
        turns.append({'name':agent.name})
        prof.start()
        ret = agents.microstep(turns,explain=True)
        prof.stop()
        prof.close()
        stats = hotshot.stats.load(filename)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
##         stats.print_stats()
        dec = ret['decision']
        print ret['explanation'].toprettyxml()
        
##         #REST OF AGENTS
##         turns[:] = []
##         turns.append({'name':'Abdallah'})
##         print 'Turn list being passed into microstep():'
##         print turns
##         t1 = time.clock()
##         ret = agents.microstep(turns)
##         t2 = time.clock()
##         print 'microstep time:' + str(t2 - t1)
##         dec = ret['decision']
##         print dec['Abdallah']
