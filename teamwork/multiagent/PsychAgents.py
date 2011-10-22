"""PsychSim scenario class"""
import copy
from Queue import Queue
import sys
import threading
import time
from xml.dom.minidom import Document,parseString

from teamwork.utils.Debugger import Debugger
from teamwork.math.Keys import Key,StateKey,ActionKey,ObservationKey,ModelKey,WorldKey,keyConstant
from teamwork.math.matrices import epsilon
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedMatrix import makeIdentityMatrix,KeyedMatrix
from teamwork.math.KeyedTree import KeyedPlane
from teamwork.math.probability import Distribution
from teamwork.math.ProbabilityTree import ProbabilityTree
from teamwork.dynamics.pwlDynamics import PWLDynamics,ConstantDynamics,IdentityDynamics
from Simulation import MultiagentSimulation
from teamwork.policy.pwlTable import PWLTable

lookaheadCount = {}
##import numpy.linalg.linalg

class PsychAgents(MultiagentSimulation):
    """
    A PsychSim scenario

          0. Create a scenario from a list of Agent objects
             - C{scenario = L{PsychAgents}(entityList)}

          1. If the members have been created from elements of a L{GenericSociety}, then the following applies those generic models to the member L{teamwork.agent.Agent} objects:
             - C{scenario.L{applyDefaults}()}

          2. Access a (possibly recursively nested) member agent model
             - C{agent = scenario[name]}

          3. Run the simulation
             - C{result = scenario.L{performMsg}(msg,sender,receivers,hearers)}
             - C{result = scenario.L{performAct}(actions)}
             - C{result = scenario.L{microstep}()}

          4. Access the scenario state distribution
             - C{distribution = scenario.L{getState}()}

          5. Access the system dynamics
             - C{tree = scenario.L{getDynamics}(actions)}

    @cvar observationDecay: the rate at which an observation flag decays on each subsequent epoch (1 means no decay, 0 means instant amnesia)
    @type observationDecay: C{float}
    @cvar threaded: if C{True}, then execution will be multithreaded
    @type threaded: boolean
    @ivar worlds: the possible worlds for this scenario
    @ivar reverseWorlds: the reverse lookup table for possible worlds
    @ivar transition: the transition probability matrix for these possible worlds
    @ivar reward: joint reward vectors over possible worlds
    """
    observationDecay = 0.5
    __VERIFY__ = True
    threaded = False
    
    def __init__(self,entities=[]):
        """
        @param entities: list or dictionary of L{Agent<teamwork.agent.Agent>} instances
        """
        self.society = None
        MultiagentSimulation.__init__(self,entities)
        self.actions = None
        self.actionMatrix = None
        # Sequence of changes over time
        self.log = []
        # Scenario goals
        self.objectives = []
        # Possible worlds
        self.worlds = {}
        self.reverseWorlds = {}
        # Transition matrix among possible worlds
        self.transition = {}
        # Joint reward vectors over possible worlds
        self.reward = {}

    def initialize(self):
        pass
#        self.compileDynamics()

    def addMember(self,agent):
        """Adds the agent to this collection
        @param agent: the agent to add
        @type agent: L{Agent<teamwork.agent.Agent>}
        @warning: will clobber any pre-existing agent with the same name
        """
        MultiagentSimulation.addMember(self,agent)
        # Hook up current agents' beliefs to this new agent
        eList = self.members()
        while len(eList) > 0:
            other = eList.pop()
            if other.name == agent.name:
                other.dynamics.update(agent.dynamics)
            eList += other.entities.members()
        # Hook up all of this new agent's beliefs to this world
        eList = [agent]
        while len(eList) > 0:
            agent = eList.pop()
            agent.entities.dynamics = self.dynamics
            agent.entities.society = self.society
            if self.has_key(agent.name):
                agent.dynamics.update(self[agent.name].dynamics)
            eList += agent.entities.members()
        
    def getActions(self):
        """
        @return: the current observation vector
        @rtype: L{KeyedVector}
        """
        if self.actions is None:
            self.actions = KeyedVector()
            for agent in self.members():
                for option in agent.actions.getOptions():
                    for action in option:
                        key = ActionKey({'type':action['type'],
                                         'entity':action['actor'],
                                         'object':action['object']})
                        self.actions[key] = 0.
            self.actions[keyConstant] = 1.
        return self.actions
    
    def applyDefaults(self,progress=None,total=None,doBeliefs=True):
        """Applies the relevant generic models to the member agent models
        @param progress: optional C{Queue} argument is used to give progress updates, in the form of C{(label,pct)}, where:
           - I{label}: a string label to display for the current task
           - I{pct}: an integer percentage (1-100) representing the amount of progress made since the last call
        @type progress: Queue
        @param total: number of total actions to be progressed through
        @type total: float
        @param doBeliefs: if C{True}, the create recursive beliefs (default is C{True}
        @type doBeliefs: bool
        """
        for entity in self.members():
            assert entity.entities.society is self.society
            # Set up relationships and models
            entity.initRelationships(self.members())
            # Instantiate the observation function with the new entities
            entity.initObservations(self.members())
        for entity in self.members():
            # Add any actions that refer to other entities
            entity.addActions(self.members())
            # Stick the actor in, but we should really do this somewhere else
            for action in entity.actions.getOptions():
                for subAct in action:
                    subAct['actor'] = entity.name
        for entity in self.members():
            # Initialize dynamics
            entity.initDynamics(self)
            # Initialize mental models
            entity.initModels(self.members())
        # Initialize every entity's beliefs about the others
        for entity in self.members():
            if progress:
                msg = 'Initializing beliefs of %s' % (entity.ancestry())
                count = pow(len(self.members()),entity.getDefault('depth'))
                progress.put((msg,0))
            if doBeliefs:
                # Recursive beliefs
                entity.initEntities(self.members())
            else:
                # Don't recurse
                entity.initEntities(self.members(),0)
            if progress:
                try:
                    progress.put((msg,max(1,100.*float(count)/total)))
                except ZeroDivisionError:
                    progress.put((msg,max(1,10.*float(count))))
        # Initialize turn order
        self.initializeOrder()
        self.applyOrder()
        if self.saveHistory:
            self.history.append(self.state.expectation())
                
    def applyOrder(self,entities=None):
        """Applies any generic society's order specification to this scenario"""
        if entities is None and self.society:
            newEntities = self.activeMembers()
            if len(newEntities) == 0:
                # No entities with actions, um, give everybody a turn?
                newEntities = self.members()
            entities = []
            serial = isinstance(self.society._keys[0],str)
            for index in range(len(self.society._keys)):
                if not serial:
                    entities.append([])
                classes = self.society._keys[index]
                if isinstance(classes,str):
                    classes = [classes]
                for agent in newEntities[:]:
                    for generic in classes:
                        if agent.instanceof(generic):
                            if serial:
                                entities.append(agent.name)
                            else:
                                entities[-1].append(agent.name)
                            newEntities.remove(agent)
                            break
            for agent in self.members():
                agent.entities.applyOrder(entities)
        else:
            # Apply order to all subjective beliefs, too
            for agent in self.members():
                if agent.entities:
                    agent.entities.applyOrder(entities)
        self.order = self.generateOrder(entities)
        
    def microstep(self,turns=[],hypothetical=False,explain=False,suggest=False,debug=False):
        """Step forward by the action of the given entities
        @param turns: the agents to act next (defaults to result of L{next}), each entry in the list should be a dictionary:
           - I{name}: the name of the agent to act
           - I{choices}: the list of possible options this agent can consider in this turn (defaults to the list of all possible actions if omitted, or if the list is empty)
        @type turns: C{dict[]}
        @param hypothetical: if C{True}, then this is only a hypothetical microstep; otherwise, it is real
        @type hypothetical: bool
        @param explain: if C{True}, then add an explanation to the result
        @type explain: bool
        @param suggest: if C{True}, then suggest possible belief changes to ensure that the behavior in this step meets whatever objectives have been specifieid (default is C{False})
        @type suggest: bool
        @note: if C{explain} is C{False}, then C{suggest} is treated as C{False}
        @return: a dictionary of results:
           - decision: the dictionary of actions performed in this turn
           - delta: the changes to the state (suitable for passing in to applyChanges)
           - explanation: an XML document explaining what happened in this step and why
        """
        # Build up the list of selected actions
        actionDict = {}
        # If no agents provided, then use default turn-taking order
        if not turns:
            turns = self.next()
        doc = Document()
        root = doc.createElement('step')
        doc.appendChild(root)
        root.setAttribute('time',str(self.time+1))
        root.setAttribute('hypothetical',str(hypothetical))
        for turn in turns:
            if isinstance(turn,dict):
                name = turn['name']
                actor = self[name]
                try:
                    choices = turn['choices']
                except KeyError:
                    choices = []
                try:
                    history = turn['history']
                except KeyError:
                    history = {}
            else:
                raise DeprecationWarning,'Turns should be expressed in dictionary form'
            if len(choices) == 0:
                for option in actor.actions.getOptions():
                    if len(option) == 0:
                        # Doing nothing is always an option?
                        choices.append(option)
                    elif not actor.actions.isIllegal(option):
                        # No deactivation of actions, so everything's possible
                        choices.append(option)
            if len(choices) == 1:
                actionDict[name] = choices[0]
                exp = None
            else:
                # Determine action chosen by this actor
                action,exp = actor.applyPolicy(actions=choices,history=history,
                                               debug=debug,explain=explain)
                actionDict[name] = action
            node = doc.createElement('turn')
            root.appendChild(node)
            node.setAttribute('agent',name)
            node.setAttribute('time',str(self.time+1))
            node.setAttribute('forced',str(len(choices) == 1))
            subDoc = self.explainAction(actionDict[name])
            if exp:
                if isinstance(exp,dict):
                    value = str(exp['value'])
                else:
                    value = exp.documentElement.getAttribute('value')
                subDoc.documentElement.setAttribute('value',value)
            node.appendChild(subDoc.documentElement)
            if explain:
                if exp and not isinstance(exp,dict):
                    # XML explanation
                    node.appendChild(exp.documentElement)
                if suggest:
                    subDoc = self.suggestAll(name,actionDict[name])
                    element = subDoc.documentElement
                    element.appendChild(actor.entities.state.__xml__().documentElement)
                    node.appendChild(element)
        # Update state and beliefs
        result = {'decision': actionDict,
                  'delta': self.hypotheticalAct(actionDict, debug=debug),
                  'explanation': doc,
                  }
        if explain:
            subDoc = self.explainEffect(actionDict,result['delta'])
            root.appendChild(subDoc.documentElement)
        if not hypothetical:
#             # before applying changes, update the memory if the agent is a
#             # memory-based agent
#             for agent in self.members():
#                 if isinstance(agent,MemoryAgent):
#                     agent.updateMemory(actionDict,agent.getAllBeliefs())
            self.applyChanges(result['delta'])
        return result
    
    def individualObs(self,state,actions,observation,agent):
        """Probability of the specified observation
        @warning: to be overridden"""
        raise NotImplementedError

    def getMember(self,agent):
        """Access the agent object stored in this scenario
        @param agent: the label for the entity to be returned, either:
           - if a string, the entity object of that name
           - if a list of strings, then the list is treated as a recursive path representing a branch of the belief hierarchy, and the end node is returned
        @type agent: string or list of strings
        @rtype: L{Agent<teamwork.agent.Agent>}"""
        if isinstance(agent,list):
            eList = agent
            entity = MultiagentSimulation.getMember(self,eList[0])
            for other in eList[1:]:
                entity = entity.getEntity(other)
            return entity
        else:
            return MultiagentSimulation.getMember(self,entity)

    def performMsg(self,msg,sender,receivers,hearers=[],debug=Debugger(),
                   explain=False):
        """Updates the scenario in response to the specified message
        @param msg: the message to be sent
        @type msg: L{Message<teamwork.messages.PsychMessage.Message>}
        @param sender: name of the agent sending this message
        @type sender: str
        @param receivers: list of agent names who are the intended receivers
        @type receivers: str[]
        @param hearers: list of agent names who are I{unintended} hearers
        @type hearers: str[]
        @note: hearers is optional, but should not contain any of the receivers
        @param explain: if C{True}, then add an explanation to the result
        @type explain: C{boolean}
        @return: the overall effect of this message
        @rtype: dict
        """
        if explain:
            doc = Document()
            root = doc.createElement('step')
            doc.appendChild(root)
            root.setAttribute('time',str(self.time+1))
            node = doc.createElement('turn')
            node.setAttribute('agent',sender)
            node.setAttribute('time',str(self.time+1))
            node.setAttribute('forced',str(True))
            root.appendChild(node)
            subNode = doc.createElement('decision')
            node.appendChild(subNode)
            subNode.appendChild(msg.__xml__().documentElement)
        else:
            doc = None
        # Agents don't send messages to themselves (could cause problems)
        try:
            receivers.remove(sender)
        except ValueError:
            pass
        # First, every receiver processes the message
        for name in receivers:
            entity = self[name]
            newMsg = copy.deepcopy(msg)
            newMsg['actor'] = newMsg['sender'] = sender
            newMsg['object'] = newMsg['receiver'] = name
            newMsg['_observed'] = receivers
            newMsg['_unobserved'] = []
            for potential in entity.getEntities():
                if not potential in receivers:
                    # Non-receivers are assumed not to have heard
                    newMsg['_unobserved'].append(potential)
            result,exp = entity.stateEstimator(None,{sender:[newMsg]},-1,
                                               debug)
            subExp = exp[newMsg.pretty()]
            if len(subExp) > 0 and explain:
                node.appendChild(self.explainMessage(name,subExp).documentElement)
        try:
            hearers.remove(sender)
        except ValueError:
            pass
        for other in hearers:
            # Each hearer process message as well
            entity = self[other]
            msgList = []
            for name in receivers:
                newMsg = copy.deepcopy(msg)
                newMsg['actor'] = newMsg['sender'] = sender
                newMsg['object'] = newMsg['receiver'] = name
                newMsg['_observed'] = [other]
                newMsg['_unobserved'] = []
                for potential in entity.getEntities():
                    if not potential in receivers+[other]:
                        # Non-receivers (including other overhearers) are
                        # assumed not to have heard
                        newMsg['_unobserved'].append(potential)
                msgList.append(newMsg)
            if len(msgList) > 0:
                result,exp = entity.stateEstimator(None,{sender:msgList},-1,
                                                   debug)
                assert len(msgList) == 1
                subExp = exp[msgList[0].pretty()]
                if len(subExp) > 0 and explain:
                    node.appendChild(self.explainMessage(other,subExp).documentElement)
        # Sender updates its beliefs at the next recursive level
        entity = self[sender]
        newReceivers = []
        for other in receivers:
            if entity.hasBelief(other):
                newReceivers.append(other)
        newHearers = []
        for other in hearers:
            if entity.hasBelief(other):
                newHearers.append(other)
        if len(newReceivers+newHearers) > 0:
            exp = entity.entities.performMsg(msg,sender,
                                             newReceivers,
                                             newHearers,debug)
##             delta[sender] = exp
        # Messages need to be incorporated into turn dynamics
        self.time += 1
        return doc
            
    def updateAll(self,action,debug=Debugger()):
        """Obsolete, still here for backward compatibility"""
        raise DeprecationWarning,'Use performAct instead'

    def compileDynamics(self,progress=None,total=100,profile=False):
        """Pre-compiles all of the dynamics trees for these agents
        @param progress: optional progress argument is invoked to give progress updates, in the form of C{lambda label,pct: ...}, where:
           - I{label}: a string label to display for the current task
           - I{pct}: an integer percentage (1-100) representing the amount of progress made since the last call
        @type progress: lambda
        @param total: the total number of actions to be compiled
        @type total: int
        @param profile: if C{True}, a profiler is run and statistics printed out (default is C{False}
        @type profile: boolean
        @warning: pre-compiles only those trees missing from cache.
        @note: Applies this method to recursive beliefs of member agents as well"""
        # Start compiling
        if profile:
            import hotshot.stats
            filename = '/tmp/stats'
            prof = hotshot.Profile(filename)
            prof.start()
        if self.threaded:
            lock = threading.Lock()
            threads = []
        for step in self.getSequence():
            actionList = self.generateActions(map(lambda n: {'name': n}, step))
            if progress and len(actionList) > 0:
                msg = 'Compiling actions of %s' % (','.join(step))
                progress.put((msg,0.))
            for actionSet in actionList:
                self.updateTurn(actionSet)
                if self.threaded:
                    cmd = lambda : self.getDynamics(actionSet,lock)
                    thread = threading.Thread(target=cmd)
                    thread.start()
                    threads.append(thread)
                else:
                    self.getDynamics(actionSet)
            if self.threaded:
                for thread in threads:
                    if thread.isAlive():
                        thread.join()
            if progress and len(actionList) > 0:
                progress.put((msg,max(1,100.*float(len(actionList))/total)))
            # The following line is unnecessary if dynamics in beliefs are the same as the real dynamics
##            entity.entities.compileDynamics(progress,total)
        if profile:
            prof.stop()
            prof.close()
            print 'loading stats...'
            stats = hotshot.stats.load(filename)
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            stats.print_stats()
            
    def compilePolicy(self,level=0,progress=None,total=100):
        """Pre-compiles policy trees for member agents
        @param level: The belief depth at which all agents will have their policies compiled, where 0 is the belief depth of the real agent.  If the value of this flag is I{n}, then all agents at belief depthS{>=}I{n} will have their policies compiled, while no agents at belief depth<I{n} will.  If C{None}, then no agents will have policies compiled.
        @type level: int
        @warning: pre-compiles only those trees missing from cache.
        @note: Applies this method to recursive beliefs of member agents as well"""
        for entity in self.members():
            entity.entities.compilePolicy(level,progress,total)
            if level is not None and \
                   len(entity.actions.getOptions()) > 0 and \
                   entity.beliefDepth() >= level:
                if entity.parent and entity.name == entity.parent.name:
                    # Do we want to compile here?  I think not.
                    # But ask me again in a week or so.
                    continue
                if progress:
                    msg = 'Compiling policy of %s' % (entity.ancestry())
                    if isinstance(progress,Queue):
                        progress.put((msg,1.))
                    else:
                        progress(msg,1.)
                start = time.time()
                entity.policy.initialize()
                entity.policy.solve()
                if not entity.parent:
                    print entity.name,'policy',time.time()-start
            
    def makeActionKey(self,actions):
        """
        @return: a unique string representation of the table of actions
        @rtype: str
        """
        return ','.join(map(str,sum(actions.values(),[])))

    def getDynamics(self,actionDict,lock=None,debug=False):
        """Returns the overall dynamics function over the provided actions
        @param lock: optional thread lock
        @rtype: L{PWLDynamics}"""
        # Look in cache for dynamics
        actionKey = self.makeActionKey(actionDict)
        if lock:
            lock.acquire()
        if not self.dynamics.has_key(actionKey):
            if debug:
                print 'Unable to find dynamics for:',actionDict
                print 'Looking under:',actionKey
            if lock:
                lock.release()
            # Create dynamics from scratch
            dynamics = {'state':self.getStateDynamics(actionDict),
                        'actions':self.getActionDynamics(actionDict),
                        }
            if lock:
                lock.acquire()
            self.dynamics[actionKey] =  dynamics
        if lock:
            lock.release()
        return self.dynamics[actionKey]

    def getStateDynamics(self,actionDict,errors=None):
        """
        @return: the dynamics of the state vector in response to the given action
        @param actionDict: the actions performed, indexed by actor name
        @type actionDict: C{dict:str->L{Action<teamwork.action.PsychActions.Action>}[]}
        @param errors: a dictionary to hold any dynamics bugs that are corrected (by default, the bugs are corrected but not returned)
        @type errors: dict
        """
        if errors is None:
            errors = {}
        dynamics = None
        keyList = self.getStateKeys().keys()
        keyList.sort()
        remaining = filter(lambda k: isinstance(k,StateKey),keyList)
        matrix = makeIdentityMatrix(keyList)
        identity = PWLDynamics({'tree':ProbabilityTree(matrix)})
        # Go through each possible state feature
        for key in remaining[:]:
            entity = self[key['entity']]
            feature = key['feature']
            toAdd = []
            toCompose = []
            # Extract and categorize dynamics across actions
            subDyn = entity.getDynamics(actionDict,feature)
#            for action in sum(actionDict.values(),[]):
#                subDyn = entity.getDynamics(action,feature)
            if subDyn:
                if key in remaining:
                    remaining.remove(key)
                if self.__VERIFY__:
                    errors.update(self.verifyTree(subDyn.getTree()))
                if subDyn.getTree().isAdditive():
                    toAdd.append(subDyn)
                else:
                    toCompose.append(subDyn)
            # Process additive dynamics first
            stateDynamics = None
            for subDyn in toAdd:
                args = {}
                args.update(subDyn.args)
                args['tree'] = copy.deepcopy(subDyn.getTree())
                subDyn = PWLDynamics(args)
                subDyn.fill(keyList)
                if stateDynamics is None:
                    stateDynamics = subDyn
                else:
                    stateDynamics += subDyn
                    stateDynamics -= identity
            # Now process compositive dynamics
            for subDyn in toCompose:
                args = {}
                args.update(subDyn.args)
                args['tree'] = copy.deepcopy(subDyn.getTree())
                subDyn = PWLDynamics(args)
                subDyn.fill(keyList)
                if stateDynamics is None:
                    stateDynamics = subDyn
                else:
                    stateDynamics *= subDyn
            # Merge into overall dynamics
            if dynamics is None:
                dynamics = stateDynamics
            elif not stateDynamics is None:
                dynamics += stateDynamics
                dynamics -= identity
        # Features which are unaffected by actions
        for key in remaining:
            entity = self[key['entity']]
            try:
                subDyn = entity.dynamics[key['feature']][None]
                if isinstance(subDyn,str):
                    subDyn = entity[subDyn].dynamics[feature][None]
            except KeyError:
                subDyn = IdentityDynamics(key['feature'])
            subDyn = subDyn.instantiate(entity,{})
            subDyn.fill(keyList)
            if dynamics is None:
                dynamics = subDyn
            else:
                dynamics.merge(subDyn)
        # Add dynamics for constant slot
        matrix = ConstantDynamics()
        subDyn = PWLDynamics({'tree':ProbabilityTree(matrix)})
        if dynamics:
            dynamics = dynamics.merge(subDyn)
        else:
            dynamics = subDyn
        dynamics.fill(keyList)
        # Remove any identity trees
        dynamics.getTree().pruneIdentities()
        return dynamics

    def verifyTree(self,tree,validKeys=None,errors=None):
        """Identifies and removes any extraneous keys in the given matrices
        @param tree: the tree to check
        @type tree: C{L{KeyedTree}[]}
        @param errors: the errors found so far (defaults to empty)
        @type errors: C{dict:L{StateKey}[]S{->}True}
        @return: the extraneous keys found (C{L{StateKey}[]S{->}True})
        @rtype: dict
        """
        if errors is None:
            errors = {}
        if validKeys is None:
            validKeys = self.getStateKeys()
        if tree.isLeaf():
            matrix = tree.getValue()
            for rowKey in matrix.rowKeys():
                if isinstance(rowKey,StateKey) and \
                       not validKeys.has_key(rowKey):
                    errors[rowKey] = True
                    del matrix[rowKey]
                else:
                    row = matrix[rowKey]
                    for colKey in row.keys():
                        if isinstance(colKey,StateKey) and \
                               not validKeys.has_key(colKey):
                            errors[colKey] = True
                            del row[colKey]
        else:
            for child in tree.children():
                self.verifyTree(child,validKeys,errors)
            if not tree.isProbabilistic():
                for plane in tree.split:
                    for key in plane.weights.keys():
                        if isinstance(key,StateKey) and \
                               not validKeys.has_key(key):
                            errors[key] = True
                            del plane.weights[key]
        return errors
    
    def getActionDynamics(self,actionDict):
        """
        @return: the dynamics of the action vector in response to the given action
        @param actionDict: the actions performed, indexed by actor name
        @type actionDict: C{dict:str->L{Action<teamwork.action.PsychActions.Action>}[]}
        """
        keyList = self.getActions().keys()
        if self.actionMatrix is None:
            # Create a base dynamics matrix to use a starting point
            self.actionMatrix = KeyedMatrix()
            for rowKey in keyList:
                row = copy.copy(self.getActions())
                for colKey in keyList:
                    if rowKey == colKey:
                        if colKey == keyConstant:
                            row[colKey] = 1.
                        else:
                            row[colKey] = self.observationDecay
                    else:
                        row[colKey] = 0.
                self.actionMatrix[rowKey] = row
        dynamics = copy.deepcopy(self.actionMatrix)
        for actList in actionDict.values():
            for action in actList:
                key = ActionKey({'type':action['type'],
                                 'entity':action['actor'],
                                 'object':action['object']})
                dynamics.set(key,keyConstant,1.)
                dynamics.set(key,key,0.)
        return dynamics

    def verifyDecisions(self,world,actions,decider=None,debug=False):
        """
        @param decider: the name of the agent who is free to choose any action
        @type decider: str
        @param world: the vector including the model specifications
        @type world: L{KeyedVector}
        @param actions: the actions under consideration
        @type actions: strS{->}L{Action}[]
        @return: C{True} iff the non-decider agents could possibly make the given decisions in the given world
        @rtype: bool
        """
        for modelKey in filter(lambda k: isinstance(k,ModelKey) and k['entity'] != decider,
                               world.keys()):
            agent = self[modelKey['entity']]
            if not agent.verifyDecision(world,actions[agent.name],debug):
                # This individual agent's decision is inconsistent with model
                return False
        else:
            # No agent's decision is inconsistent with models
            return True

    def getDynamicsMatrix(self,decider=None,debug=False):
        """Generates matrix representations of probabilistic dynamics, given the space of possible worlds
        @param decider: if given, then it is the name of the agent who can choose any action, while all other agents are following their given policies
        @type deicder: str
        """
        if len(self.transition) != len(self.generateActions()):
            keys = self.getWorlds().keys()
            keys.sort()
            self.transition.clear()
            for actions in self.generateActions():
                if debug:
                    print 'Dynamics of:',
                    print self.makeActionKey(actions)
                dynamics = self.getDynamics(actions)
                # Transform transition probability into matrix representation
                matrix = KeyedMatrix()
                for colKey,world in self.getWorlds().items():
                    if debug:
                        print 'Start world:',colKey
                        print world.simpleText()
                    if decider:
                        if not self.verifyDecisions(world,actions,decider,debug):
                            if debug: print
                            continue
                    # Project world state
                    state = world.getState()
                    if debug:
                        print 'Start state:',state.simpleText()
                    state = dynamics['state'].apply(state)*state
                    if debug:
                        print 'End state:',state.simpleText()
                    if isinstance(state,Distribution):
                        elements = state.items()
                    else:
                        elements = [(state,1.)]
                    # Project beliefs about others
                    for modelKey in filter(lambda k: isinstance(k,ModelKey),
                                           world.keys()):
                        agent = self[modelKey['entity']]
                        action = agent.makeActionKey(actions[agent.name])
                        modelIndex = agent.identifyModel(world)
                        model = agent.models[modelIndex]
                        if debug:
                            print 'Model of %s:' % (agent.name),model['name']
                        for index in range(len(elements)):
                            state,prob = elements.pop(0)
                            if debug:
                                print 'Considering end:',state.simpleText(),prob
                            # Scale by likelihood of this element
                            prob *= 1./float(len(model['beliefs']))
                            for oldBeliefs in model['beliefs']:
                                if debug:
                                    print 'Believes:',oldBeliefs.simpleText()
                                if model['horizon'] is None or model['horizon'] > 0:
                                    # Consider possible observations
                                    obs = agent.observe(state,actions)
                                    for omega,subprob in obs.items():
                                        # Project new belief
                                        SE = agent.getEstimator()[ObservationKey({'type': omega})]
                                        update = SE[state]['values'][action]
                                        newBeliefs = update*oldBeliefs
                                        newBeliefs *= 1./sum(newBeliefs.getArray())
                                        if debug:
                                            print 'Observe:',omega,subprob
                                            print 'Update:',newBeliefs.simpleText()
                                        if model['horizon'] is None:
                                            newModel = agent.findBelief(newBeliefs,model['horizon'],create=False)
                                        else:
                                            newModel = agent.findBelief(newBeliefs,model['horizon']-1,create=False)
                                        if debug:
                                            print 'New model:',newModel['name']
                                        # Insert end model into world vector
                                        new = KeyedVector(state)
                                        new[modelKey] = newModel['value']
                                        if debug:
                                            print 'Adding:',new.simpleText()
                                            print 'with prob:',prob*subprob
                                        elements.append((new,prob*subprob))
                                else:
                                    # Not a real transition, but a loop
                                    if debug:
                                        print 'End of horizon'
                                    # Insert end model into world vector
                                    new = KeyedVector(state)
                                    new[modelKey] = model['value']
                                    if debug:
                                        print 'Adding:',new.simpleText()
                                        print 'with prob:',prob
                                    elements.append((new,prob))
                    else:
                        # Identify worlds corresponding to end states
                        for element,prob in elements:
                            element.freeze()
                            rowKey = self.reverseWorlds[element]
                            if debug:
                                print '%s -> %s: %f' % (colKey,rowKey,prob)
                            try:
                                original = matrix[rowKey][colKey]
                            except KeyError:
                                original = 0.
                            matrix.set(rowKey,colKey,original+prob)
                        if debug:
                            print
                matrix.fill(keys)
                matrix.freeze()
                if debug:
                    print self.makeActionKey(actions)
                    print matrix.getArray()
                    print
                self.transition[self.makeActionKey(actions)] = matrix
        return self.transition
        
    def hypotheticalAct(self,actions,beliefs=None,debug=Debugger()):
        """
        Computes the scenario changes that would result from a given action
        @param actions: dictionary of actions, where each entry is a list of L{Action<teamwork.action.PsychActions.Action>} instances, indexed by the name of the actor
        @type actions: C{dict:str->L{Action<teamwork.action.PsychActions.Action>}[]}
        @return: the changes that would result from I{actions}
          - state:   the change to state, in the form of a L{Distribution} over L{KeyedMatrix} (suitable to pass to L{applyChanges})
          - I{agent}: the change to the recursive beliefs of I{agent}, as returned by L{teamwork.agent.RecursiveAgent.RecursiveAgent.preComStateEstimator}
          - turn: the change in turn in dictionary form (suitable to pass to L{applyTurn}):
        @rtype: C{dict}
        """
        # Eventual return value, storing up all the various belief
        # deltas across the entities
        overallDelta = {}
        if len(self) == 0:
            return overallDelta
        if beliefs is None:
            state = self.getState()
            observations = self.getActions()
        else:
            state = beliefs['state']
            observations = beliefs['observations']
        overallDelta['turn'] = self.updateTurn(actions,debug)
        dynamics = self.getDynamics(actions)
        overallDelta['state'] = dynamics['state'].apply(state)
        overallDelta['observations'] = dynamics['actions']
        # Do observation phase to update any recursive beliefs
        if self.threaded:
            threads = []
        for entity in filter(lambda e: beliefs is None or \
                                 beliefs.has_key(e.name),self.members()):
            if len(entity.entities) == 0:
                continue
            observations = entity.observe(self.getState(),actions)
            if isinstance(observations,Distribution):
                raise NotImplementedError,'Unable to handle partial observability in projection.'
            elif len(observations) > 0:
                name = entity.name
                if beliefs is None:
                    world = None
                elif beliefs.has_key(name):
                    world = beliefs[name]
                else:
                    world = None
                try:
                    action = actions[entity.name]
                except KeyError:
                    action = None
                result = entity.preComStateEstimator(world,observations,
                                                     action,debug=debug)
                overallDelta[name] = result
        if self.threaded:
            # Loop until all threads finish
            for thread in threads:
                if thread.isAlive():
                    thread.join()
        return overallDelta

    def __updateAgent(self,entity,actions,delta,lock,world,debug):
        result = entity.preComStateEstimator(world,actions,
                                             actions[entity.name],debug=debug)
        name = entity.name
        lock.acquire()
        delta[name] = result
        lock.release()
        
    def performAct(self,actions,debug=Debugger()):
        """Updates all of the entities in response to the given actions
        @param actions: a dictionary of actions, indexed by actor name
        @return: a dictionary of the changes, returned by L{hypotheticalAct}
        """
        turns = []
        for actor,actList in actions.items():
            turns.append({'name':actor,
                          'choices':[actList]})
        return self.microstep(turns,hypothetical=False,debug=debug)

    def applyChanges(self,delta,descend=True,rewind=False,beliefs=None):
        """Applies the differential changes to this set of entities"""
        if len(self.members()) == 0:
            # There should be some way to avoid this
            return
        for key,subDelta in delta.items():
            if key == 'turn':
                # Apply new turn info
                self.applyTurn(subDelta,beliefs)
            elif key == 'state':
                if beliefs is None:
                    state = self.getState()
                else:
                    state = beliefs['state']
                state = subDelta*state
                if beliefs is None:
                    # Change the real state
                    self.state.clear()
                    for key,prob in state.items():
                        self.state[key] = prob
                else:
                    beliefs['state'] = state
            elif key == 'observations':
                if beliefs is None:
                    self.actions = subDelta*self.getActions()
                else:
                    beliefs['observations'] = subDelta*beliefs['observations']
            elif key == 'relationships':
                pass
            elif key == 'models':
                pass
            else:
                # Apply changes to recursive beliefs
                entity = self[key]
                if beliefs is None:
                    entity.entities.applyChanges(subDelta,descend,rewind)
                    if subDelta.has_key('relationships'):
                        entity.updateLinks(subDelta['relationships'])
                    if subDelta.has_key('models'):
                        entity.beliefs['models'] = subDelta['models']
                else:
                    entity.entities.applyChanges(subDelta,descend,rewind,
                                                 beliefs[key])

    def reachable(self,horizon,perspective=None,reachable=None,states=None,approximate=True):
        """Generates the possible real-world states (and true belief states) reachable from the current states
        @param horizon: the number of time steps to project into the future
        @type horizon: int
        @param perspective: the agent whose perspective we should use when generating the possible worlds; if C{None}, then use only world states, not beliefs (default is C{None})
        @type perspective: str
        @rtype: L{KeyedVector}[]
        @note: Observations are not tracked, as we assume that they do not affect reachability
        """
        if reachable is None:
            reachable = {}
        if states is None:
            # Extract the possible initial world states
            states = self.getState().domain()
            states = map(lambda vector: {'state':vector,'turn':self.order,
                                         'models':KeyedVector(),
                                         'expanded': False},states)
            # Add possible belief states
            for agent in filter(lambda a: len(a.models) > 0 and \
                                    a.name != perspective,
                                self.activeMembers()):
                beliefs = agent.entities.state2world(agent.beliefs)
                model = agent.findBelief(beliefs,None,create=False)
                key = ModelKey({'entity':agent.name})
                for index in range(len(states)):
                    node = states.pop(0)
                    node['models'][key] = model['value']
                    states.append(node)
            # Create belief vectors including both state and mental models
            for node in states:
                vector = node['state'].merge(node['models'])
                reachable[vector] = True
                vector = vector.merge(node['turn'])
                node['combined'] = vector
        if horizon == 0:
            # End of recursion, return the results
            return reachable.keys()
        else:
            if perspective:
                # Store original models to avoid confusion
                models = {}
                for agent in self.activeMembers():
                    if agent.name != perspective:
                        models[agent.name] = {}
                        for name,model in agent.models.items():
                            models[agent.name][name] = model['beliefs'][:]
            # Expand unexpanded states into next time step
            for node in filter(lambda s: not s['expanded'],states):
                for actionSet in self.generateActions(self.next()):
                    if not self.verifyDecisions(node['models'],actionSet,
                                                perspective):
                        continue
                    newStates = []
                    # Compute new turn order
                    delta = self.updateTurn(actionSet)
                    turn = delta[node['turn']]*node['turn']
                    # Compute new state
                    dynamics = self.getDynamics(actionSet)
                    state = Distribution({node['state']:1.})
                    delta = dynamics['state'].apply(state)
                    state = delta*state
                    # Create envelope of new states based on world
                    for vector in state.domain():
                        newStates.append({'state': vector,
                                          'turn': turn,
                                          'models': KeyedVector(),
                                          'expanded': False})
                    # Expand envelope to consider possible new mental models
                    for agent in self.activeMembers():
                        try:
                            name = agent.identifyModel(node['models'])
                        except KeyError:
                            # No mental model for this agent
                            continue
                        key = ModelKey({'entity':agent.name})
                        for index in range(len(newStates)):
                            old = newStates.pop(0)
                            for omega in agent.getOmega():
                                model = agent.nextModel(name,actionSet[agent.name],omega)
                                new = copy.deepcopy(old)
                                new['models'][key] = model['value']
                                newStates.append(new)
                    # Addd states from envelope which haven't already been expanded
                    for new in newStates:
                        vector = new['state'].merge(new['models'])
                        reachable[vector] = True
                        new['combined'] = vector.merge(new['turn'])
                        for old in states:
                            if old['combined'] == new['combined']:
                                break
                        else:
                            states.append(new)
                node['expanded'] = True
            return self.reachable(horizon-1,perspective,
                                  reachable,states,approximate)

    def getWorlds(self,horizon=None,perspective=None):
        """
        @return: the possible worlds of this scenario
        @rtype: dict
        """
        if not self.worlds:
            self.generateWorlds(horizon,perspective)
        return self.worlds

    def generateWorlds(self,horizon=None,perspective=None,maxSize=100,worlds=None):
        """Generates the space of possible I{n}-level worlds within the current simulation
        @param perspective: the agent whose perspective we should use when generating the possible worlds; if C{None}, then use only world states, not beliefs (default is C{None})
        @type perspective: str
        @param maxSize: the upper limit on the size of the generated space (Default is 100)
        @type maxSize: int
        @warning: clears L{transition} matrix as well
        @return: dictionary of worlds, indexed by L{WorldKey}, and a reverse lookup dictionary as well (i.e., L{WorldKey}S{->}L{KeyedVector},L{KeyedVector}S{->}L{WorldKey}
        @rtype: dict,dict
        """
        if worlds is None:
            # Use my universe by default, but reset first
            worlds = {}
            real = True
        else:
            real = False
        lookup = {}
        if horizon is None:
            if perspective:
                horizon = self[perspective].horizon
            else:
                horizon = len(self.activeMembers()) - 1
        # Start with empty space
        space = []
        newSpace = [None]
        # Expand envelope by one as long as we are within limit
        while len(newSpace) > len(space) and len(newSpace) < maxSize:
#            horizon += 1
            space = newSpace
            newSpace = self.reachable(horizon,perspective)
        # Enforce consistent sorting of worlds
        newSpace.sort(lambda x,y: cmp(list(x.getArray()),list(y.getArray())))
        # Index worlds
        for index in range(len(newSpace)):
            key = WorldKey({'world':index})
            worlds[key] = newSpace[index]
            lookup[worlds[key]] = key
        if real:
            self.transition.clear()
#             for agent in self.members():
#                 agent.O.clear()
#                 agent.estimators.clear()
            self.worlds.clear()
            self.worlds.update(worlds)
            self.reverseWorlds.clear()
            self.reverseWorlds.update(lookup)
            self.reward.clear()
        return worlds,lookup
                
    def state2world(self,state=None,epsilon=1e-10):
        """Maps a given L{Distribution} over state vectors to vector distribution over possible worlds.  Also considers mental models if included.
        @param state: the state distribution to map (default is current state of this scenario)
        @type state: L{Distribution}(L{KeyedVector})
        @rtype: L{KeyedVector}
        """
        if state is None:
            state = self.state
        if isinstance(state,Distribution):
            # Just a state distribution
            models = {}
        else:
            # Dictionary of belief structures
            models = state['models']
            state = state['entities'].state
        vector = KeyedVector()
        for key,world in self.getWorlds().items():
            # Find probability of state part of world
            for element in state.domain():
                if world.getState() == element:
                    prob = state[element]
                    break
            else:
                prob = 0.
            if prob > epsilon and models:
                # Find probability of mental model part of world
                for element in filter(lambda e: models[e] > epsilon,
                                      models.domain()):
                    for subkey in filter(lambda k: isinstance(k,ModelKey),
                                         world.keys()):
                        if world[subkey] != element[subkey]:
                            prob = 0.
                            break
                    else:
                        prob *= models[element]
            vector[key] = prob
        vector.freeze()
        return vector
        
    def jointReward(self):
        """
        @return: a joint reward function, if it exists, in the form of vectors over possible worlds, indexed by joint actions.  Raises C{ValueError} if agents have different reward functions
        @rtype: strS{->}L{KeyedVector}
        """
        if not self.reward:
            rewards = {}
            for entity in filter(lambda e: len(e.goals) > 0,self.members()):
                rewards[entity.name] = entity.R
                for action in self.generateActions():
                    vector = entity.getRewardVector(action,self.getWorlds())
            length = None
            for other in rewards.values():
                if length is None or len(other.values()[0]) > length:
                    length = len(other.values()[0])
                    self.reward = other
                elif len(other.values()[0]) == length:
                    for key,vector in self.reward.items():
                        assert other.has_key(key),'Missing joint action: %s' % (key)
                        if not other[key] == vector:
                            raise ValueError,'Different reward for %s:\n%s' % \
                                (key,vector.getArray()-other[key].getArray())
        return self.reward

    def nullPolicy(self,override=True,joint=None):
        """Sets the policies of all agents in this scenario to be the best joint action in the initial state
        @param override: if C{True}, override any existing policy that may be there (default is C{True})
        @type override: bool
        """
        state = self.state2world()
        reward = self.jointReward()
        best = {'key':joint,'value':None}
        for actions in self.generateActions():
            if best['key'] == self.members()[0].makeActionKey(actions):
                best['action'] = actions
                break
        else:
            best['key'] = None
            for key,vector in reward.items():
                value = vector*state
                if best['key'] is None or value > best['value']:
                    best['key'] = key
                    best['value'] = value
            for actions in self.generateActions():
                if best['key'] == self.members()[0].makeActionKey(actions):
                    best['action'] = actions
                    break
        # Set up null policy
        for name,option in best['action'].items():
            table = PWLTable()
            table.rules[0] = {'lhs': [], 'rhs':option,'values': {}}
            actions = copy.copy(best['action'])
            for alternative in self[name].actions.getOptions():
                actions[name] = alternative
                actionKey = self[name].makeActionKey(actions)
                value = reward[actionKey]
                table.rules[0]['values'][str(alternative)] = value
            if not self[name].policy.tables:
                self[name].policy.tables.append([])
            if len(self[name].policy.tables[0]) > 0:
                # Existing policy here
                if override:
                    self[name].policy.tables[0][0] = table
            else:
                # Create first policy table
                self[name].policy.tables[0].append(table)

    def simulate(self,horizon,interrupt=None,debug=False,epsilon=1e-16):
        """
        @return: the expected joint reward (C{None} iff interrupted)
        @rtype: float
        """
        ER = 0.
        state = self.state2world()
        # Make sure there's at least a null policy (but don't clobber)
        self.nullPolicy(False)
        # Find initial envelope of reachable nodes
        for world in state.keys():
            node = {'_state': world,'_probability': state[world]}
            for agent in self.activeMembers():
                beliefs = agent.entities.state2world(agent.entities.state)
                node[agent.name] = {'beliefs': beliefs,
                                    'observations': []}
            if not self._simulate(node,horizon,interrupt,debug,epsilon):
                # Interrupted
                return None
            ER += node['_probability']*node['_total']
        if debug: print ER
        return ER

    def _simulate(self,start,horizon,interrupt=None,debug=False,epsilon=1e-16):
        """
        @return: C{True} iff run to completion, C{False} iff interrupted
        @rtype: bool
        """
        # Determine what actions each agent will take
        start['_action'] = {}
        for agent in self.activeMembers():
            if interrupt and interrupt.isSet(): return False
            option,exp = agent.applyPolicy(state=start[agent.name]['beliefs'],
                                           horizon=horizon)
            start['_action'][agent.name] = option
        # Compute immediate reward of these actions
        joint = agent.makeActionKey(start['_action'])
        start['_reward'] = self.jointReward()[joint][start['_state']]
        start['_total'] = start['_reward']
        if horizon > 0:
            # Compute transition
            T = self.getDynamicsMatrix()[joint]
            for world in self.getWorlds().keys():
                next = {'_probability': T[world][start['_state']],
                        '_state': world}
                if next['_probability'] < epsilon:
                    continue
                # Project subsequent belief states
                envelope = [{'_probability': next['_probability']}]
                for agent in self.activeMembers():
                    SE = agent.getEstimator()
                    O = agent.getObservationMatrix(start['_action'],
                                                   self.getWorlds())
                    action = agent.makeActionKey(start['_action'][agent.name])
                    # Extend from current belief possibilities envelope
                    for index in range(len(envelope)):
                        partial = envelope.pop(0)
                        # Iterate over possible observations
                        for omega in agent.getOmega():
                            prob = O[omega][next['_state']]
                            if prob < epsilon:
                                continue
                            node = {}
                            for key,value in partial.items():
                                if key == '_probability':
                                    node[key] = value*prob
                                else:
                                    # Another agent's beliefs
                                    node[key] = copy.copy(value)
                            # Project new beliefs
                            if interrupt and interrupt.isSet(): return False
                            node[agent.name] = {'observations': start[agent.name]['observations'][:]}
                            node[agent.name]['observations'].append(omega)
                            belief = start[agent.name]['beliefs']
                            matrix = SE[omega][belief]['values'][action]
                            node[agent.name]['beliefs'] = matrix*belief
                            total = sum(node[agent.name]['beliefs'].getArray())
                            node[agent.name]['beliefs'] *= 1./total
                            envelope.append(node)
                # Project next level
                for node in envelope:
                    node['_state'] = world
                    if not self._simulate(node,horizon-1,interrupt,debug,epsilon):
                        return False
                    start['_total'] += node['_probability']*node['_total']
        if debug:
            # Print results
            line = [str(start['_state'])]
            for agent in self.activeMembers():
                line.append(','.join(map(lambda o: ''.join(map(lambda w: w[0].upper(),
                                                               str(o).split())),
                                         start[agent.name]['observations'])))
            line.append(','.join(map(lambda a: ''.join(map(lambda v: v[0].upper(),
                                                           start['_action'][a.name][0]['type'].split())),
                                     self.activeMembers())))
            line.append('%5.3f' % (start['_reward']))
            line.append('%5.3f' % (start['_total']))
            print '\t'.join(line)
        return True

    ####################
    # Explanation Code #
    ####################
    
    def explainEffect(self,actions,effect={},prefix=None):
        doc = Document()
        root = doc.createElement('effect')
        doc.appendChild(root)
        for key,delta in effect.items():
            if key == 'state':
                if len(delta.expectation()) > 1:
                    node = doc.createElement('state')
                    root.appendChild(node)
                    oldState = self.getState()
                    newState = delta*oldState
                    diff = newState-oldState
                    node.appendChild(diff.__xml__().documentElement)
            elif key == 'turn':
                pass
            elif key == 'explanation':
                pass
            elif key == 'observations':
                pass
            elif key == 'relationships':
                pass
            elif key == 'models':
                pass
            else:
                node = doc.createElement('beliefs')
                node.setAttribute('agent',key)
                beliefs = self[key].entities
                subDoc = beliefs.explainEffect(actions,delta)
                node.appendChild(subDoc.documentElement)
        return doc

    def explainAction(self,actions):
        doc = Document()
        root = doc.createElement('decision')
        doc.appendChild(root)
        for action in actions:
            root.appendChild(action.__xml__().documentElement)
        return doc
        
    def explainDecision(self,actor,explanation):
        """Extracts explanation from explanation structure"""
        doc = Document()
        root = doc.createElement('explanation')
        doc.appendChild(root)
        # Package up the chosen action
        decision = explanation['decision']
        # Extract what actor expects from best decision
        lookahead = explanation['options'][str(decision)]
        subDoc = self.explainExpectation(lookahead['breakdown'])
        root.appendChild(subDoc.documentElement)
        return doc

    def explainMessage(self,name,explanation):
        """Extracts explanation from message acceptance explanation structure"""
        doc = Document()
        root = doc.createElement('hearer')
        doc.appendChild(root)
        root.setAttribute('agent',name)
        root.setAttribute('decision',str(explanation['decision']))
        if explanation['breakdown']['accept'] == 'forced':
            root.setAttribute('forced',str(True))
        elif explanation['breakdown']['reject'] == 'forced':
            root.setAttribute('forced',str(True))
        else:
            root.setAttribute('forced',str(False))
            for key,value in explanation['breakdown']['accept'].items():
                node = doc.createElement('factor')
                root.appendChild(node)
                positive = float(value) > self[name].beliefWeights['threshold']
                node.setAttribute('positive',str(positive))
                node.setAttribute('type',key)
        return doc
                     
    def setModelChange(self,flag=-1):
        """Sets the model change flag value across all entities
        @param flag: if flag argument is positive, activates model changes in the belief updates of these entities; if 0, deactivates them; if negative (default), toggles the activation state
        @type flag: C{int}
        """
        for entity in self.members():
            if flag:
                if flag < 0:
                    entity.modelChange = not entity.modelChange
                else:
                    entity.modelChange = True
            else:
                entity.modelChange = False

    def detectViolations(self,action,objectives=None):
        """Determines which objectives the given action violates
        @param objectives: the objectives to test (default is all)
        @type objectives: (str,str,str)[]
        @type action: L{Action<teamwork.action.PsychActions.Action>}
        @rtype: (str,str,str)[]
        """
        if objectives is None:
            objectives = self.objectives
        actor = self[action['actor']]
        violated = []
        for objective in objectives:
            if objective[0] == actor.name or objective[0] == 'Anybody':
                if not objective[1] in actor.getStateFeatures():
                    if objective[1] == action['type']:
                        if objective[2] == 'Minimize':
                            # Bad action happened
                            violated.append(objective)
                    else:
                        if objective[2] == 'Maximize':
                            # Good action didn't happen
                            violated.append(objective)
        return violated

    def suggestAll(self,actor,option):
        """Generates alternative beliefs that might change the given action into one that satisfies all objectives
        @type actor: str
        @type option: L{Action<teamwork.action.PsychActions.Action>}[]
        @rtype: Document
        """
        doc = Document()
        root = doc.createElement('suggestions')
        doc.appendChild(root)
        root.setAttribute('time',str(self.time+1))
        root.setAttribute('objectives',str(len(self.objectives)))
        # Find any violated objectives
        violated = {}
        for action in option:
            for violation in self.detectViolations(action):
                violated[self.objectives.index(violation)] = True
        root.setAttribute('violations',str(len(violated)))
        # Go through each violated objective and generate suggestions
        for index in violated.keys():
            objective = self.objectives[index]
            node = objective2XML(objective,doc)
            root.appendChild(node)
            suggestions = self.suggest(actor,option,objective)
            node.setAttribute('count',str(len(suggestions)))
            counts = {}
            for suggestion in suggestions[:]:
                if len(suggestion) > 0:
                    try:
                        counts[str(suggestion)] += 1
                        suggestions.remove(suggestion)
                    except KeyError:
                        counts[str(suggestion)] = 1
                else:
                    suggestions.remove(suggestion)
            for suggestion in suggestions:
                child = doc.createElement('suggestion')
                node.appendChild(child)
                for threshold in suggestion.values():
                    key = threshold['key']
                    grandchild = key.__xml__().documentElement
                    grandchild.setAttribute('min',str(threshold['min']))
                    grandchild.setAttribute('max',str(threshold['max']))
                    child.appendChild(grandchild)
        return doc
        
    def suggest(self,actor,action,objective):
        """Suggest alternative beliefs that might change the given action into one that satisfies the given objective
        @type actor: str
        @type action: L{Action<teamwork.action.PsychActions.Action>}[]
        @type objective: (str,str,str)
        @rtype: dict[]
        """
        # Compute the expected sequence of actions
        sequence = self[actor].multistep(horizon=self[actor].horizon,
                                         start={actor:action})
        beliefs = self[actor].entities
        # Compute the dynamics after this first action
        dynamics = None
        for t in range(len(sequence)):
            decision = sequence[t]['action']
            tree = beliefs.getDynamics(decision)['state'].getTree()
            if dynamics is None:
                dynamics = tree
                actual = tree
            else:
                dynamics = tree*dynamics
                actual += dynamics
        alternatives = []
        # Compute the other satisfactory options the actor could've done
        targets = []
        for option in self[actor].actions.getOptions():
            for action in option:
                if self.detectViolations(action,[objective]):
                    break
            else:
                targets.append(option)
        assert not action in targets
        goals = self[actor].getGoalVector()['state']
        goals.fill(self.state.domain()[0].keys())
        for option in targets:
            # Substitute alternative action into the lookahead
            # (we could re-create the whole lookahead,
            # but that might be expensive)
            dynamics = beliefs.getDynamics({actor:option})['state'].getTree()
            desired = dynamics
            for t in range(1,len(sequence)):
                decision = sequence[t]['action']
                tree = beliefs.getDynamics(decision)['state'].getTree()
                dynamics = tree*dynamics
                desired += dynamics
            delta = desired - actual
            # Identify leaves where target action is preferred
            for leaf in delta.leafNodes():
                plane = KeyedPlane((goals*leaf.getValue()).domain()[0],0.)
                result = plane.always()
                if result:
                    # Always true
                    conditions = leaf.getPath()
                elif result is None:
                    # Sometimes true, sometimes false
                    conditions = leaf.getPath()
                    conditions.append(([plane],True))
                else:
                    # Never true
                    conditions = []
                thresholds = {}
                for split,value in conditions:
                    for plane in split:
                        feature = None
                        for key in split[0].weights.keys():
                            if abs(split[0].weights[key]) > epsilon:
                                if isinstance(key,StateKey):
                                    if feature is None:
                                        feature = key
                                        sign = split[0].weights[key]
                                        sign /= abs(sign)
                                    else:
                                        # Two state features in this plane
                                        break
                        else:
                            # Found no more than one relevant state feature
                            if feature is None:
                                # Didn't find any states?  Shouldn't happen
                                pass
                            else:
                                # Merge this threshold with previous
                                try:
                                    threshold = thresholds[feature]
                                except KeyError:
                                    threshold = {'max':1.,'min':-1.,
                                                 'key':feature}
                                    thresholds[feature] = threshold
                                if sign > 0.:
                                    if value:
                                        # Positive weight, test is True
                                        key = 'min'
                                        function = max
                                    else:
                                        # Positive weight, test is False
                                        key = 'max'
                                        function = min
                                else:
                                    if value:
                                        # Negative weight, test is True
                                        key = 'max'
                                        function = min
                                    else:
                                        # Negative weight, test is False
                                        key = 'min'
                                        function = max
                                threshold[key] = function(threshold[key],
                                                          sign*plane.threshold)
                for key,threshold in thresholds.items():
                    if threshold['max'] < threshold['min']:
                        # Contradictory constraints
                        break
                else:
                    # All of the constraints are kosher
                    alternatives.append(thresholds)
        return alternatives

    def evaluate(self,horizon,current=None,debug=False,behaviors=None):
        """
        @param horizon: the number of steps into the future to project
        @type horizon: int
        @param current: list of nodes to expand
        @return: the expected joint reward that the agents in this scenario will receive over the specified horizon
        @rtype: float
        """
        if current is None:
            # Use current state to generate search nodes
            current = []
            worlds = self.getWorlds()
            for vector in self.state.domain():
                state = KeyedVector()
                for key,world in worlds.items():
                    if world == vector:
                        state[key] = 1.
                    else:
                        state[key] = 0.
                node = {'probability': self.state[vector],
                        'state': state}
                for agent in self.activeMembers():
                    node['observations %s' % (agent.name)] = []
                    # Assume everyone has same correct initial beliefs
                    node[agent.name] = copy.deepcopy(state)
                current.append(node)
        if debug:
            print 'Horizon:',horizon
            start = time.time()
            sys.stderr.write('%d to go (%d nodes)\n' % (horizon,len(current)))
        value = 0.
        for node in current:
            if debug:
                print '%s %f' % (node['state'].getArray(),node['probability'])
            # Determine the behavior
            actions = {}
            for agent in self.activeMembers():
                # Assume PWL policy
                actions[agent.name] = agent.policy.execute(node[agent.name],
                                                           horizon=horizon)[0]
                if debug:
                    print ','.join(map(str,node['observations %s' % (agent.name)])),
                    if node.has_key(agent.name):
                        print node[agent.name].getArray(),
                    print '-> %s' % (str(actions[agent.name]))
            node['action'] = actions
            if isinstance(behaviors,dict):
                for agent in behaviors.keys():
                    behaviors[agent].append((node,actions[agent]))
            node['key'] = self.makeActionKey(actions)
            # Compute reward
            r = self.jointReward()[node['key']]*node['state']
            if debug:
                print node['key']
                print node['state'].getArray()
                print 'R =',r
            value += node['probability']*r
        if horizon == 0:
            return value
        # Project next set of nodes
        projection = []
        for node in current:
            # Update state
            dist = self.getDynamicsMatrix()[node['key']]*node['state']
            worlds = dist.keys()
            combinations = []
            for world in range(len(dist)):
                new = copy.copy(node['state'])
                new[worlds[world]] = 1.
                for other in range(len(dist)):
                    if other != world:
                        new[worlds[other]] = 0.
                prob = node['probability']*dist[worlds[world]]
                if prob > 0.:
                    combo = {'probability':prob,'state':new}
                    for agent in self.activeMembers():
                        key = 'observations %s' % (agent.name)
                        combo[key] = node[key][:]
                    combinations.append(combo)
            for agent in self.activeMembers():
                next = []
                for old in combinations:
                    for omega in agent.getOmega():
                        # Generate subsequent belief state possibilities
                        action = node['action'][agent.name]
                        matrix = agent.getObservationMatrix(node['action'],
                                                            self.getWorlds())
                        prob = matrix[omega['type']]*old['state']
                        new = copy.deepcopy(old)
                        new['observations %s' % (agent.name)].append(omega)
                        new['probability'] *= prob
                        if new['probability'] > 0.:
                            agent.getEstimator(self)
                            belief,delta = agent.stateEstimator(beliefs=node[agent.name],
                                                                actions=action,observation=omega)
                            new[agent.name] = belief
                            next.append(new)
                combinations = next
            projection += combinations
        # Merge matching nodes
        index = 1
        while index < len(projection):
            node = projection[index]
            for other in projection[:index]:
                for key in filter(lambda k: k != 'probability',node.keys()):
                    if key[:12] == 'observations':
                        if node[key] != other[key]:
                            # Mismatch
                            break
                    elif sum(map(abs,(node[key] - other[key]).getArray())) > epsilon:
                        # Mismatch
                        break
                else:
                    # Matching node
                    other['probability'] += node['probability']
                    del projection[index]
                    break
            else:
                # Unique node
                index += 1
        total = 0.
        for node in projection:
            total += node['probability']
        assert abs(total-1.) < epsilon, 'Prob = %f' % (total)
        if debug:
            sys.stderr.write('\t%d sec\n%f\n' % (time.time()-start,value))
        return value + self.evaluate(horizon-1,projection,debug,behaviors)
    
    def toHTML(self):
        str = '<TABLE WIDTH="100%">\n'
        str = str + '<TBODY>\n'
        odd = None
        for entity in self.members():
            str = str + '<TR'
            if odd:
                str = str + ' BGCOLOR="#aaaaaa"'
            else:
                str = str + ' BGCOLOR="#ffffff"'
            str = str + '>'
##            str = str + '<TH>' + entity.ancestry() + '</TH>\n'
            str = str + '<TD>' + entity.toHTML() + '</TD>\n'
            str = str + '</TR>\n'
            odd = not odd
        str = str + '</TBODY>\n'
        str = str + '</TABLE>\n'
        return str

    def __xml__(self):
        doc = MultiagentSimulation.__xml__(self)
        for objective in self.objectives:
            doc.documentElement.appendChild(objective2XML(objective,doc))
        node = doc.createElement('possible')
        doc.documentElement.appendChild(node)
        for key,world in self.worlds.items():
            node.appendChild(key.__xml__().documentElement)
            node.appendChild(world.__xml__().documentElement)
#         if self.society:
#             node = doc.createElement('society')
#             node.appendChild(self.society.__xml__().documentElement)
#             doc.documentElement.appendChild(node)
        return doc

    def parse(self,element,agentClass=None,societyClass=None):
        """
        @param agentClass: the Python class for the individual entity members
        @type agentClass: class
        @param societyClass: the optional Python class for any generic society associated with this scenario
        @type societyClass: class
        """
        MultiagentSimulation.parse(self,element,agentClass)
        if societyClass:
            self.society = societyClass()
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'objective':
                    objective = (str(child.getAttribute('who')),
                                 str(child.getAttribute('what')),
                                 str(child.getAttribute('how')),
                                 )
                    self.objectives.append(objective)
                elif child.tagName == 'society' and societyClass:
                    grandchild = child.firstChild
                    while grandchild:
                        if grandchild.nodeType == child.ELEMENT_NODE:
                            break
                        grandchild = grandchild.nextSibling
                    if grandchild:
                        self.society.parse(grandchild)
                elif child.tagName == 'possible':
                    # Load possible worlds
                    grandchild = child.firstChild
                    while grandchild:
                        while grandchild.nodeType != grandchild.ELEMENT_NODE:
                            grandchild = grandchild.nextSibling
                        key = Key()
                        key = key.parse(grandchild)
                        grandchild = grandchild.nextSibling
                        while grandchild.nodeType != grandchild.ELEMENT_NODE:
                            grandchild = grandchild.nextSibling
                        vector = KeyedVector()
                        vector = vector.parse(grandchild)
                        self.worlds[key] = vector
                        self.reverseWorlds[vector] = key
                        grandchild = grandchild.nextSibling
            child = child.nextSibling
        return self
        
    def __copy__(self):
        entities = self.__class__(self.members())
        entities.objectives = self.objectives[:]
        return entities

    def __deepcopy__(self,memo):
        result = self.__class__()
        memo[id(self)] = result
        result.__init__(copy.deepcopy(self.members(),memo))
        result.objectives = copy.deepcopy(self.objectives,memo)
        return result

def objective2XML(objective,doc):
    node = doc.createElement('objective')
    node.setAttribute('who',str(objective[0]))
    node.setAttribute('what',str(objective[1]))
    node.setAttribute('how',str(objective[2]))
    return node
    
def loadScenario(filename):
    """
    Loads a scenario from the given filename
    @return: the scenario
    @rtype: L{PsychAgents}
    """
    import bz2
    import teamwork.agent.Entities
    import GenericSociety

    f = bz2.BZ2File(filename,'r')
    data = f.read()
    f.close()
    doc = parseString(data)
    scenario = PsychAgents()
    scenario.parse(doc.documentElement,teamwork.agent.Entities.PsychEntity,
                   GenericSociety.GenericSociety)
    scenario.initialize()
    return scenario

if __name__ == '__main__':
    import os
    from teamwork.utils.PsychUtils import load

    entities = load('%s/python/teamwork/examples/Scenarios/school.scn' \
                    % (os.environ['HOME']))
    doc = entities.__xml__()
    print doc.toxml()
