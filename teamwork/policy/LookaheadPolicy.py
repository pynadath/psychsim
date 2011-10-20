import copy
from xml.dom.minidom import Document

from generic import Policy

class LookaheadPolicy(Policy):
    """Policy subclass that looks a fixed number of turns into the
    future and examines the expected reward received in response to
    the actions of other agents
    @ivar horizon: the lookahead horizon
    @type horizon: C{int}
    @ivar consistentTieBreaking: if C{True}, always breaks ties between equally valued actions in a consistent manner, i.e., it's behavior is deterministic (default is C{True}).
    @type consistentTieBreaking: bool
    """
    
    def __init__(self,entity,actions=[],horizon=1):
        """
        @param entity: the entity whose policy this is (not sure whether this is necessary)
        @type entity: L{teamwork.agent.Agent.Agent}
        @param actions: the options considered by this policy (used by superclass)
        @type actions: L{Action}[]
        @param horizon: the lookahead horizon
        @type horizon: C{int}
        """
        Policy.__init__(self,actions)
        self.entity = entity
        self.horizon = horizon
        self.threshold = 0.5
        self.consistentTieBreaking = True

    def setHorizon(self,horizon=1):
        """Sets the default horizon of lookahead (which can still be overridden by a method call argument
        @param horizon: the desired horizon (default is 1)
        @type horizon: C{int}
        """
        self.horizon = horizon

    def execute(self,state,choices=[],debug=False,horizon=-1,explain=False):
        return self.findBest(state=state,choices=choices,debug=debug,
                             horizon=horizon,explain=explain)

    def evaluateChoices(self,state,choices=[],debug=None,horizon=-1):
        """Evaluates the expected reward of a set of possible actions
        @param state: the agent considering its options
        @type state: L{GoalBasedAgent<teamwork.agent.GoalBased.GoalBasedAgent>}
        @param choices: the actions the agent has to choose from (default is all available actions)
        @type choices: C{L{Action}[]}
        @type debug: L{Debugger}
        @param horizon: the horizon of the lookahead (if omitted, agent's default horizon is used)
        @type horizon: C{int}
        @return: a dictionary, indexed by action, of the projection of the reward of that action (as returned by L{actionValue<teamwork.agent.GoalBased.GoalBasedAgent.actionValue>}) with an additional I{action} field indicating the chosen actions
        @rtype: C{dict}
        """
        values = {}
        if len(choices) == 0:
            choices = self.entity.actions.getOptions()
        for action in choices:
            if debug:
                print '%s considering %s' % (self.entity.ancestry(),
                                             self.entity.makeActionKey(action))
            value,exp = LookaheadPolicy.actionValue(self,
                                                    state=copy.deepcopy(state),
                                                    actStruct=action,
                                                    debug=debug and self.entity.makeActionKey(action)[-10:] != 'do nothing',
                                                    horizon=horizon)
            if debug:
                print 'Value of %s = %s' % \
                    (self.entity.makeActionKey(action),value)
            # Compare value against best so far
            exp['action'] = action
            exp['value'] = value
            values[str(action)] = exp
        return values
        
    def findBest(self,state,choices=[],debug=False,horizon=-1,explain=False):
        """Determines the option with the highest expected reward
        @param state: the current world state
        @type state: L{Distribution<teamwork.math.probability.Distribution>}
        @param choices: the actions the agent has to choose from (default is all available actions)
        @type choices: C{L{Action}[]}
        @type debug: L{Debugger}
        @param horizon: the horizon of the lookahead (if omitted, agent's default horizon is used)
        @type horizon: C{int}
        @return: the optimal action and a log of the lookahead in dictionary form:
           - value: the expected reward of the optimal action
           - decision: the optimal action
           - options: a dictionary, indexed by action, of the projection of the reward of that action (as returned by L{evaluateChoices})
        @rtype: C{dict}
        """
        bestAction = []
        bestValue = None
        explanation = {'options':self.evaluateChoices(state,choices,
                                                      debug,horizon)}
        for result in explanation['options'].values():
            action = result['action']
            value = result['value']
            if not bestAction:
                better = True
            else:
                if float(value) > float(bestValue):
                    better = True
                elif float(value) < float(bestValue):
                    better = False
                elif self.consistentTieBreaking:
                    # Tie, so let's use a consistent tie-breaking mechanism
                    # (i.e, alphabetical order)
                    better = str(action) > str(bestAction)
                else:
                    better = False
            if better:
                bestAction = action
                bestValue = value
        if explain:
            # Generate XML document explaining the policy's output
            exp = Document()
            root = exp.createElement('explanation')
            root.setAttribute('value',str(bestValue.expectation()))
            exp.appendChild(root)
            bestResult = explanation['options'][str(bestAction)]
            if len(explanation['options']) > 1:
                field = exp.createElement('alternatives')
                # Add actions not chosen
                root.appendChild(field)
                # Add agent goals
                node = exp.createElement('goals')
                field.appendChild(node)
                node.appendChild(self.entity.goals.__xml__().documentElement)
                for result in explanation['options'].values():
                    if result['action'] != bestAction:
                        node = exp.createElement('alternative')
                        node.setAttribute('value',str(result['value'].expectation()))
                        field.appendChild(node)
                        if result['projection'][self.entity.name]:
                            delta = result['projection'][self.entity.name] - bestResult['projection'][self.entity.name]
                            node.appendChild(delta.__xml__().documentElement)
                        for action in result['action']:
                            node.appendChild(action.__xml__().documentElement)
                        if result.has_key('breakdown'):
                            subNode = self.addExpectations(exp,result['breakdown'],state)
                            node.appendChild(subNode)
            if bestResult.has_key('breakdown'):
                node = self.addExpectations(exp,bestResult['breakdown'],state)
                root.appendChild(node)
        else:
            exp = explanation
        explanation['value'] = bestValue
        explanation['decision'] = bestAction
        if state is not None:
            try:
                explanation['beliefs'] = state[None]
            except KeyError:
                # Should not really use 'state' as a key
                explanation['beliefs'] = state['state']
        if debug:
            print '%s prefers %s' % (self.entity.name,
                                     self.entity.makeActionKey(bestAction))
        return bestAction,exp

    def addExpectations(self,doc,explanation,state):
        # Add expected actions
        field = doc.createElement('expectations')
        for breakdown in explanation:
            old = state['state']
            for step in breakdown:
                for name,option in step['action'].items():
                    node = doc.createElement('turn')
                    field.appendChild(node)
                    node.setAttribute('agent',name)
                    node.setAttribute('time',str(step['time']))
                    node.setAttribute('probability',str(step['probability']))
                    new = step['effect']['state']*old
                    if step.has_key('models'):
                        try:
                            model = self.entity.getModel(name,step['models'])
                            node.setAttribute('model',model)
                        except KeyError:
                            pass
                    for action in option:
                        node.appendChild(action.__xml__().documentElement)
                    subNode = doc.createElement('state')
                    node.appendChild(subNode)
                    subNode.appendChild((new-old).__xml__().documentElement)
                    old = new
        return field                   

    def __copy__(self):
        return self.__class__(self.entity,horizon=self.horizon)
    
    def actionValue(self,state,actStruct,debug=False,horizon=-1):
        """
        @return: expected value of performing action"""
        if horizon < 0:
            horizon = self.horizon
        return self.entity.actionValue(actStruct,horizon,state,debug)
    
    def __str__(self):
        return 'Lookahead to horizon '+`self.horizon`

    def __contains__(self,value):
        return False

    def __xml__(self):
        doc = Document()
        root = doc.createElement('policy')
        doc.appendChild(root)
        root.setAttribute('horizon',str(self.horizon))
        return doc
        
    def parse(self,element):
        try:
            self.horizon = int(element.getAttribute('horizon'))
        except ValueError:
            try:
                self.horizon = int(element.getAttribute('depth'))
            except ValueError:
                self.horizon = 1
