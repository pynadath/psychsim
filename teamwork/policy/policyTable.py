import copy
#import operator
import random
import sys
import time
from xml.dom.minidom import *
from LookaheadPolicy import LookaheadPolicy
from teamwork.action.PsychActions import Action
from teamwork.math.Keys import *
from teamwork.math.KeyedVector import *
from teamwork.math.KeyedMatrix import IdentityMatrix
from teamwork.math.KeyedTree import KeyedPlane
from teamwork.math.probability import Distribution
from teamwork.math.ProbabilityTree import ProbabilityTree
from teamwork.dynamics.pwlDynamics import PWLDynamics
from teamwork.math.matrices import epsilon
from pwlTable import PWLTable
    
class PolicyTable(LookaheadPolicy,PWLTable):
    """Super-nifty class for representing policies as tables and using policy iteration to optimize them.
    @cvar seedMethod: the method to use to generate the initial RHS values to seed policy iteration.  There are currently two types supported:
       - random: the RHS values are randomly generated
       - greedy: the initial RHS value provides the best immediate expected reward (i.e., over a one-step horizon)
    The default is I{greedy}.
    @type seedMethod: str
    @ivar rules: the list of RHS actions
    @type rules: L{Action}[][]
    """
    seedMethod = 'greedy'
    
    def __init__(self,entity,actions=[],horizon=1):
        """Same arguments used by constructor for L{LookaheadPolicy} superclass"""
        LookaheadPolicy.__init__(self,entity=entity,actions=actions,
                                 horizon=horizon)
        self.type = 'Table'
        PWLTable.__init__(self)
        self.transition = None
        self.lookahead = []
        if self.seedMethod == 'random':
            random.seed()
    
    def execute(self,state,observations={},history=None,choices=[],
                index=None,debug=False,explain=False,entities={},cache={}):
        """Applies this policy to the given state and observation history
        @param state: the current state
        @type state: L{KeyedVector}
        @param observations: the current observation history
        @type observations: dict:strS{->}L{Action<teamwork.action.PsychActions.Action>}[]
        @param history: dictionary of actions that have been performed so far
        @type history: dict
        @param entities: a dictionary of entities to be used as a value tree cache
        @param cache: values computed so far
        @return: the corresponding action in the table
        @rtype: L{Action<teamwork.action.PsychActions.Action>}[]
        """
        if history is None:
            history = {}
        if index is None:
            if len(self.rules) <= 1:
                index = 0
            elif isinstance(state,KeyedVector):
                index = self.index(state,observations)
            else:
                index = self.index(state['state'].expectation(),observations)
        if debug is True:
            print '\t\t',index
        if len(choices) == 0:
            choices = self.entity.actions.getOptions()
        try:
            rhs = self.rules[index]
        except KeyError:
            # We have not filled out this table, so use fallback policy
            return LookaheadPolicy.execute(self,state,choices,
                                           explain=explain)
        if rhs is None:
            # This rule has not been seeded yet
            if isinstance(state,KeyedVector):
                self.rules[index] = [self.default(choices,state,observations)]
            else:
                self.rules[index] = [self.default(choices,
                                                  state['state'].expectation(),
                                                  observations)]
            rhs = self.rules[index]
        if not isinstance(rhs,dict) and not isinstance(rhs,list):
            # This is an old-school policy with only one action on the RHS
            rhs = [rhs]
        if explain:
            exp = Document()
            root = exp.createElement('explanation')
            exp.appendChild(root)
            field = exp.createElement('alternatives')
            root.appendChild(field)
        else:
            exp = None
        if isinstance(rhs,list):
            labels = map(str,choices)
            for index in range(len(rhs)):
                option = rhs[index]
                if str(option) in labels:
                    # This option is one of our available choices
                    for action in option:
                        if not action['repeatable']:
                            # Check whether we've already done this action
                            if history.has_key(str(action)):
                                # Already performed, so ignore the rest
                                if explain:
                                    node = exp.createElement('alternative')
                                    node.setAttribute('reason','repeated')
                                    node.setAttribute('rank',str(index))
                                    for action in option:
                                        node.appendChild(action.__xml__().documentElement)
                                    field.appendChild(node)
                                break
                    else:
                        # We have an eligible option
                        break
                else:
                    # This option is not one of our available choices
                    if explain:
                        node = exp.createElement('alternative')
                        node.setAttribute('reason','ineligible')
                        node.setAttribute('rank',str(index))
                        for action in option:
                            node.appendChild(action.__xml__().documentElement)
                        field.appendChild(node)
            else:
                # The policy does not have any of the available choices
                return LookaheadPolicy.execute(self,state,choices,explain=explain)
            if explain:
                # Generate remaining alternatives
                for index in range(index+1,len(rhs)):
                    alternative = rhs[index]
                    node = exp.createElement('alternative')
                    node.setAttribute('reason','worse')
                    node.setAttribute('rank',str(index))
                    for action in alternative:
                        node.appendChild(action.__xml__().documentElement)
                    field.appendChild(node)
                # Generate expected countermoves
                policies = self.getPolicies()
                if len(policies) > 0:
                    node = exp.createElement('expectations')
                    value,sequence = self.evaluate(policies,state,observations,
                                                   history,details=True)
                    for step in sequence:
                        subNode = exp.createElement('turn')
                        node.appendChild(subNode)
                        subNode.setAttribute('agent',step['actor'])
                        for action in step['decision']:
                            subNode.appendChild(action.__xml__().documentElement)
                    root.appendChild(node)
        elif isinstance(rhs,dict):
            # Value function, not explicit rules
            goals = self.entity.goals.expectation()
            eState = state['state'].expectation()
            best = {'option':None,'value':None}
            for option in choices:
                try:
                    value = rhs[option[0]]
                except KeyError:
                    value = None
                if explain:
                    node = exp.createElement('alternative')
                    node.appendChild(option[0].__xml__().documentElement)
                if value:
                    total = 0.
                    for key,dynamics in value.items():
                        delta = None
                        if isinstance(dynamics,dict):
                            # Find referenced value function
                            entry = dynamics['entity']+str(dynamics['action'])+str(dynamics['key'])
                            try:
                                delta = cache[entry]
                            except KeyError:
                                entity = entities[dynamics['entity']]
                                dynamics = entity.policy.rules[index][dynamics['action']][dynamics['key']]
                        else:
                            entry = self.entity.name+str(option[0])+str(key)
                        if delta is None:
                            # Not in cache, so compute new delta
                            matrix = dynamics.apply(state['state']).expectation()
                            delta = goals[key]*(matrix[key]*eState)
                            cache[entry] = delta
                        total += delta
                else:
                    total = 0.
                if best['option'] is None or total > best['value']:
                    best['option'] = option
                    best['value'] = total
            option = best['option']
        return option,exp

    def default(self,choices,state,observations):
        """Generates a default RHS, presumably with minimal effort.  The exact method is determined by the L{seedMethod} class attribute.
        @param state: the current state
        @type state: L{KeyedVector}
        @param observations: the current observation history
        @type observations: dict:strS{->}L{Action<teamwork.action.PsychActions.Action>}[]
        @return: the corresponding action in the table
        @rtype: L{Action<teamwork.action.PsychActions.Action>}[]
        """
        if self.seedMethod == 'greedy':
            return self._defaultGreedy(choices,state,observations)
        elif self.seedMethod == 'random':
            return self._defaultRandom(choices,state,observations)
        else:
            raise NotImplementedError,'Unable to use %s seeding' \
                  % (self.seedMethod)
        
    def _defaultRandom(self,choices,state,observations):
        """Default RHS is a random choice
        """
        return random.choice(choices)

    def _defaultGreedy(self,choices,state,observations):
        """Default RHS is the optimal action over a one-step time horizon
        """
        best = None
        for action in choices:
            value = self.expectedValue(state,action)
            if not best or value > best['value']:
                best = {'action':action,'value':value}
        return best['action']
                        
    def generateObservations(self,remaining=None,result=None):
        if remaining is None:
            remaining = self.getLookahead()[1:]
        if result is None:
            result = [{}]
        try:
            name = remaining[0]
        except IndexError:
            return result
        agent = self.entity.getEntity(name)
        for history in result[:]:
            result.remove(history)
            for action in agent.actions.getOptions():
                newHistory = copy.copy(history)
                newHistory[name] = action
                result.append(newHistory)
        return self.generateObservations(remaining[1:],result)
    
    def getLookahead(self):
        """
        @return: the turn sequence used for the forward projection
        @rtype: str[]
        """
        try:
            others = self.entity.entities.getSequence()
        except AttributeError:
            # lightweight agents
            return []
        if len(others) > 0 and \
               len(self.lookahead) != self.horizon:
            self.lookahead = []
            while len(self.lookahead) < self.horizon:
                self.lookahead += others
            self.lookahead = self.lookahead[:self.horizon]
            while self.lookahead[0] != self.entity.name:
                last = self.lookahead.pop()
                self.lookahead.insert(0,last)
        return self.lookahead

    def getPolicies(self):
        """
        @return: a dictionary of the policies of all of the agents in this entity's lookahed
        @rtype: strS{->}L{PolicyTable}
        """
        policies = {}
        order = self.getLookahead()[:]
        # Seed policies
        while len(order) > 0:
            name = order.pop()
            if name == self.entity.name:
                policies[name] = self
            else:
                agent = self.entity.getEntity(name)
                if not policies.has_key(name):
                    policies[name] = agent.policy
                # Make sure that the next level of entities is covered
                for other in policies[name].getLookahead():
                    if not policies.has_key(other) and not other in order:
                        order.append(other)
        for policy in policies.values():
            policy.initialize()
        return policies
        
    def solve(self,horizon=None,choices=None,debug=False,policies=None,
              interrupt=None,search='exhaustive',progress=None):
        if policies is None:
            policies = self.getPolicies()
        for policy in policies.values():
            assert policy.rules
        if search == 'exhaustive':
            try:
                value = self.iterate(choices,policies,state,
                                     True,False,interrupt)
            except OverflowError:
                return False
            if value is False:
                return value
            else:
                return True
        elif search == 'greedy':
            changes = 1
            candidates = []
            while changes > 0:
                changes = 0
                # Pick a random policy to perturb
                if len(candidates) == 0:
                    candidates = policies.keys()
                name = random.choice(candidates)
                candidates.remove(name)
##                 size = reduce(operator.mul,map(len,policies[name].rules))
                # Try to find a best-response strategy for the chosen agent
                for index in range(1000):
                    if interrupt and interrupt.isSet():
                        return False
                    if progress: progress()
                    if policies[name].perturb(policies,interrupt,debug):
                        changes += 1
            return True
        elif search == 'abstract':
            return self.abstractSolve(policies,interrupt,progress)
        else:
            raise NameError,'Unknown search type "%s"' % (search)
    
    def iterate(self,choices,policies,state,recurse=False,debug=False,
                interrupt=None):
        """Exhaustive policy search"""
        if choices is None:
            choices = self.entity.actions.getOptions()
        assert policies[self.entity.name] is self
        best = None
        # Consider each possible policy
        for rule in xrange(pow(len(choices),len(self.rules))):
            if interrupt and interrupt.isSet():
                if best is None:
                    # Haven't made any progress; nothing to report
                    return None
                else:
                    # Go ahead and return results so far
                    break
            self.fromIndex(rule,choices)
            assert self.toIndex(choices) == rule
            if debug:
                print self.entity.name,map(lambda a:a[0]['type'],self.rules)
            current = {'policy':rule}
            if recurse:
                # Work our way backward from our turn
                order = self.getLookahead()[:]
                order.reverse()
                for name in order:
                    if name != self.entity.name:
                        index = policies[name].iterate(None,policies,state,
                                                       False,debug,interrupt)
                        current[name] = index
                        if debug:
                            # very domain-specific info
                            print '\t',policies[name].rules[0]
            # Evaluate the policy currently under consideration
            if recurse:
                current['value'] = self.evaluate(policies,state,{},start=1)
            else:
                current['value'] = self.evaluate(policies,state,{},start=0)
            if best is None or current['value'] > best['value']:
                best = current
            if debug:
                print 'ER =',current['value']
                sys.stdout.flush()
        # Set rule to best found
        self.fromIndex(best['policy'],choices)
        if recurse:
            # Set everyone else's policy to best responses
            for name in self.getLookahead():
                if name != self.entity.name:
                    actions = self.entity.getEntity(name).actions.getOptions()
                    policies[name].fromIndex(best[name])
        return best['policy']
        
    def perturb(self,policies,interrupt=None,debug=False):
        """Consider a random perturbation of this policy
        @return: C{True} iff a better variation was found
        @rtype: bool
        """
        # Select random rule to perturb
        state,observations,index = self.chooseRule()
        # Compute expected reward of original RHS
        old = self.evaluate(policies,state,observations)
        # Swap randomly selected actions on RHS
        size = len(self.rules[index])
        i = random.randint(0,size-1)
        j = random.randint(0,size-2)
        if j >= i: j += 1
        if debug:
            print 'Perturbing %s Rule #%d, %s<->%s' % \
                  (self.entity.name,index,self.rules[index][i],
                   self.rules[index][j])
        original = self.rules[index][i]
        self.rules[index][i] = self.rules[index][j]
        self.rules[index][j] = original
        new = self.evaluate(policies,state,observations)
        if debug:
            print old,'->',new
        if old >= new:
            # Original ordering was better
            original = self.rules[index][i]
            self.rules[index][i] = self.rules[index][j]
            self.rules[index][j] = original
            return False
        else:
            # We've made a change
            return True
        
    def abstractSolve(self,policies,interrupt=None,progress=None):
        """
        Generates an abstract state space (defined by the LHS attributes) and does value iteration to generate a policy
        @warning: assumes that all of the agents have the same LHS attribute breakdown! (not hard to overcome this assumption, but annoying to code)
        @rtype: bool
        """
        assert self.rules
        # Compute abstract transition probability
        if self.transition is None:
            if not self.abstractTransition(policies,interrupt):
                # Interrupted
                self.transition = None
                return None
            for name in policies.keys():
                if name != self.entity.name:
                    policies[name].transition = self.transition
        # Initialize abstract value function
        for name in policies.keys():
            policies[name].values = {}
            for current in self.rules.keys():
                policies[name].values[current] = {}
                for other in policies.keys():
                    if other == name:
                        policies[name].values[current][other] = {}
                        for option in policies[name].rules[current]:
                            policies[name].values[current][other][str(option)] = 0.
                    else:
                        policies[name].values[current][other] = 0.
        # Compute immediate (abstract) reward and cache it
        rewards = {}
        goals = self.entity.getGoalVector()['state'].expectation()
        for name in policies.keys():
            rewards[name] = {}
            for current in self.rules.keys():
                intervals = self.abstract(current)
                table = {}
                rewards[name][current] = table
                for other in policies.keys():
                    for option in policies[other].rules[current]:
                        value = self.abstractReward(intervals,goals,option,
                                                    interrupt)
                        if value is None:
                            # Interrupted
                            return None
                        table[str(option)] = value
        # Value iteration
        change = 1.
        iterations = 0
        while iterations < self.horizon:
            print iterations
            iterations += 1
            change = 0.
            for name in policies.keys():
                if interrupt and interrupt.isSet(): return None
                # Iterate through one whole policy at a time
                change += policies[name].abstractIterate(policies,rewards,
                                                         interrupt)
                if progress: progress()
            if change > epsilon:
                iterations = 0
        print 'Result:',self.rules
        return True

    def abstractTransition(self,policies,interrupt=None,progress=None):
        """
        Generates a transition probability function over the abstract state state space (defined by the LHS attributes)
        """
        self.transition = {}
        for current in self.rules.keys():
            self.transition[current] = {}
            for name in policies.keys():
                # Determine what ranges we fall in
                intervals = self.abstract(current)
                if policies[name].rules[current] is None:
                    entity = self.entity.getEntity(name)
                    policies[name].rules[current] = entity.actions.getOptions()
                # WARNING: the following assumes that all of the agents' policies have the same LHS breakdown!!!
                for option in policies[name].rules[current]:
                    # Compute dynamics for this action
                    event = {name:option}
                    dynamics = self.entity.entities.getDynamics(event)
                    tree = dynamics['state'].getTree()
                    # Compute possible transitions over intervals
                    table = Distribution()
                    self.transition[current][str(option)] = table
                    for matrix,prob in tree[intervals].items():
                        new = []
                        for index in range(len(self.attributes)):
                            if interrupt and interrupt.isSet(): return None
                            if progress: progress()
                            # Determine effect on individual attribute
                            obj,values = self.attributes[index]
                            assert isinstance(obj,KeyedVector)
                            if isinstance(obj,ThresholdRow):
                                key = obj.specialKeys[0]
                                print option
                                print key
                                print matrix[key].simpleText()
                                new.append(adjustInterval(intervals,index,
                                                          key,matrix[key]))
                            elif isinstance(obj,DifferenceRow):
                                key = obj.specialKeys[0]
                                hi = adjustInterval(intervals,index,
                                                    key,matrix[key])
                                key = obj.specialKeys[1]
                                lo = adjustInterval(intervals,index,
                                                    key,matrix[key])
                                new.append({'lo':hi['lo']-lo['hi'],
                                            'hi':hi['hi']-lo['lo']})
                            else:
                                raise NotImplementedError,'Unable to compute abstract transitions of %s attributes' % (obj.__class__.__name__)
                        # Compute the possible rules applicable in the new interval
                        destinations = [{'prob':prob,'factors':[]}]
                        for index in range(len(self.attributes)):
                            obj,values = self.attributes[index]
                            interval = new[index]
                            span = interval['hi'] - interval['lo']
                            loIndex = self.subIndex(index,interval['lo'])
                            hiIndex = self.subIndex(index,interval['hi'])
                            # Compute probability of individual destinations
                            subProbs = {}
                            if hiIndex > loIndex:
                                # Multiple destinations
                                subProbs[loIndex] = (values[loIndex]-interval['lo'])/span
                                subProbs[hiIndex] = (interval['hi']-values[hiIndex-1])/span
                                for subIndex in range(loIndex+1,hiIndex):
                                    subProbs[subIndex] = (values[subIndex]-values[subIndex-1])/span
                            else:
                                # Only one destination
                                subProbs[loIndex] = 1.
                            # Generate possible destinations
                            for dest in destinations[:]:
                                destinations.remove(dest)
                                for subIndex in range(loIndex,hiIndex+1):
                                    newDest = copy.deepcopy(dest)
                                    newDest['prob'] *= subProbs[subIndex]
                                    newDest['factors'].append(subIndex)
                                    destinations.append(newDest)
                        for dest in destinations:
                            index = self.factored2index(dest['factors'])
                            try:
                                table[index] += dest['prob']
                            except KeyError:
                                table[index] = dest['prob']
                    for dest,prob in table.items():
                        assert prob > -epsilon
                        if prob < epsilon:
                            del table[dest]
                    assert abs(sum(table.values())-1.) < epsilon
        return True
        
    def abstractIterate(self,policies,rewards,interrupt):
        """
        One pass of value iteration over abstract state space.
        @warning: Currently works for only two agents (easy, but messy, to generalize)
        @param rewards: C{rewards[name][state][action]} = the reward that agent C{name} gets in state C{state} (index form) derived from the performance of C{action}
        @type rewards: strS{->}(strS{->}float)[]
        @return: the total change to the value function
        @rtype: float
        """
        values = []
        # Proceed backward from end of lookahead
        sequence = self.getLookahead()[:] # entity.entities.getSequence()[:]
        sequence.reverse()
        delta = 0.
        for index in range(len(sequence)):
            name = sequence[index]
            for current in self.rules.keys():
                if name != self.entity.name:
                    # Determine what action this agent will do
                    best = {'value':None}
                    for option in policies[name].rules[current]:
                        value = policies[name].values[current][name][str(option)]
                        if best['value'] is None or value > best['value']:
                            best['value'] = value
                            best['option'] = option
                    # Compute new value
                    value = rewards[self.entity.name][current][str(best['option'])]
                    table = self.transition[current][str(best['option'])]
                    next = sequence[index-1]
                    for dest,prob in table.items():
                        if next != self.entity.name:
                            value += prob*self.values[dest][next]
                        else:
                            value += prob*max(self.values[dest][next].values())
                    self.values[current][name] = value
                else:
                    # Evaluate all of my possible actions
                    for option in self.rules[current]:
                        value = rewards[self.entity.name][current][str(option)]
                        table = self.transition[current][str(option)]
                        next = sequence[index-1]
                        for dest,prob in table.items():
                            value += prob*self.values[dest][next]
                        self.values[current][name][str(option)] = value
                    order = self.rules[current][:]
                    order.sort(lambda o1,o2:cmp(-self.values[current][name][str(o1)],-self.values[current][name][str(o2)]))
                    if order != self.rules[current]:
                        delta += 1.
                        self.rules[current] = order
        return delta

    def abstractReward(self,intervals,goals,tree,interrupt=None):
        reward = 0.
        # Apply state-dependent factors of reward
        for index in range(len(self.attributes)):
            if interrupt and interrupt.isSet(): return None
            obj,values = self.attributes[index]
            interval = intervals[index]
            if isinstance(obj,ThresholdRow):
                key = obj.specialKeys[0]
                if goals.has_key(key):
                    # We have a non-zero reward weight for a feature
                    # where we know the interval of possible values
                    mean = (interval['hi']+interval['lo'])/2.
                    reward += goals[key]*mean
            else:
                raise NotImplementedError,'Unable to compute abstract reward for %s attributes' % (obj.__class__.__name__)
        return reward

    def oldReachable(self,choices,policies,state,observations,debug=False):
        # Determine what policy entries are reachable from here
        reachable = {}
        current = [(state,observations)]
        # Move myself to end of lookahead
        sequence = self.getLookahead()[:]
        sequence.append(sequence.pop(0))
        horizon = len(sequence)
        for t in range(horizon):
            name = sequence[t]
            if name == self.entity.name:
                for state,observations in current:
                    reachable[self.index(state,observations)] = True
                actions = choices
            else:
                agent = self.entity.getEntity(name)
                actions = agent.actions.getOptions()
            for oldState,oldHistory in current[:]:
                current.remove((oldState,oldHistory))
                for action in actions:
                    newHistory = copy.copy(oldHistory)
                    newHistory[name] = action
                    assert name == action[0]['actor']                        
                    event = {name:action}
                    dynamics = self.entity.entities.getDynamics(event)
                    delta = dynamics['state'].apply(oldState)
                    newState = delta*oldState
                    current.append((newState,newHistory))
        # Iterate over joint RHS entries for reachable rules
        rules = reachable.keys()
        rules.sort()
        return rules
    
    def evaluate(self,policies,state,observations,history=None,debug=False,
                 fixed=True,start=0,details=False):
        """Computes the expected value of this policy in response to the given
        policies for the other agents
        @param policies: the policies that the other agents are expected to follow
        @type policies: dict:strS{->}L{PolicyTable}
        @param state: the current state
        @type state: L{KeyedVector}
        @param observations: the current observation history
        @type observations: dict:strS{->}L{Action<teamwork.action.PsychActions.Action>}[]
        @param history: dictionary of actions that have been performed so far (not changed by this method)
        @type history: dict
        @param fixed: flag, if C{True}, then the other agents follow their given policies; otherwise, they can optimize
        @type fixed: bool
        @param start: the time offset to use in the lookahead (0 starts with this agent, and is the default)
        @type start: int
        @param details: flag, if C{True}, then the details of this evaluation are returned in addition to the expected value
        @return: expected value of this policy (and sequence of actions if details is C{True})
        @rtype: float
        """
        total = 0.
        observations = copy.copy(observations)
        if isinstance(state,KeyedVector):
            stateVector = state
        else:
            stateVector = state['state'].expectation()
        goals = self.entity.getGoalVector()
        goals['state'].fill(stateVector.keys(),0.)
        sequence = self.getLookahead()[:]
        for t in range(start):
            sequence.append(sequence.pop(0))
        if history is None:
            history = {}
        else:
            history = copy.copy(history)
        actions = []
        for name in sequence:
            if fixed or name == self.entity.name:
                action,exp = policies[name].execute(stateVector,observations,
                                                    history)
            else:
                action = policies[name].localSolve(policies,stateVector,
                                                   observations,
                                                   update=False,debug=debug)
            actions.append({'actor':name,'decision':action})
            if debug:
                print '\texpects',name,'to',action
            # Update observation history
            observations[name] = action
            for act in action:
                history[str(act)] = True
            # Update state
            dynamics = self.entity.entities.getDynamics({name:action})
            stateVector = dynamics['state'].apply(stateVector)*stateVector
            # Compute expected value
            total += self.expectedValue(stateVector,action,goals)
        if debug:
            print 'EV =',total
        if details:
            return total,actions
        else:
            return total

    def localSolve(self,policies,state,observations,update=False,debug=False):
        """Determines the best action out of the available options, given the current state and observation history, and while holding fixed the expected policies of the other agents.
        @param update: if C{True}, as a side effect, this policy is modified to have this best action be the RHS of the applicable rule.
        @type update: bool
        @return: the best action
        @rtype: L{Action<teamwork.action.PsychActions.Action>}[]
        """
        index = self.index(state,observations)
        best = None
        original = self.execute(state,observations)
        for action in self.entity.actions.getOptions():
            self.rules[index] = action
            value = self.evaluate(policies,state,observations,debug=debug)
            if debug:
                print '\t\tEV of',action,'=',value
            if best is None or value > best['value']:
                best = {'action':action,'value':value}
        if update:
            self.rules[index] = best['action']
        else:
            self.rules[index] = original
        return best['action']
        
    def expectedValue(self,state,action,goals=None,debug=False):
        if goals is None:
            goals = self.entity.getGoalVector()
            goals['state'].fill(state.keys(),0.)
        total = (goals['state']*state).expectation()
        for goal in self.entity.getGoals():
            if goal.type == 'state':
                # Already covered by vector
                pass
            elif goal.type == 'act':
                # Action goals not yet handled by vector
                for subAct in action:
                    if subAct['type'] == goal.key:
                        total += goal.weight
            else:
                raise NotImplementedError,\
                      'Unable to handle goals of type %s' % (goal.type)
        return total
    
    def chooseRule(self):
        """Generates a random state and observation history and finds the rule
        corresponding to them
        @return: a tuple of the state, observation history, and rule index
        @rtype: (L{KeyedVector},dict:strS{->}L{Action<teamwork.action.PsychActions.Action>}[],int)
        """        
        state = self.entity.entities.getState().expectation()
        observations = {}
        for obj,values in self.attributes:
            if isinstance(obj,KeyedVector):
                # Randomly generated state vector
                if isinstance(obj,ThresholdRow):
                    key = obj.specialKeys[0]
                    index = random.choice(range(len(values)+1))
                    if index == 0:
                        lo = -1.
                    else:
                        lo = values[index-1]
                    if index == len(values):
                        hi = 1.
                    else:
                        hi = values[index]
                    state[key] = (lo+hi)/2.
                else:
                    raise NotImplementedError,'Unable to generate random choices for attributes of type %s' % (obj.__class__.__name__)
            else:
                # Randomly generated observation history
                name = obj.name
                agent = self.entity.getEntity(name)
                observations[name] = random.choice(agent.actions.getOptions())
        return state,observations,self.index(state,observations)

    def abstract(self,index):
        """
        @param index: the rule index of interest
        @type index: int
        @return: the abstract state subspace where the given rule is applicable, in the form of a list of intervals, one for each attribute, where each interval is a dictionary with keys C{weights}, C{index}, C{lo}, and C{hi}
        @rtype: dict[]
        """
        abstract = []
        for attrIndex in range(len(self.attributes)):
            obj,values = self.attributes[-attrIndex-1]
            if isinstance(obj,KeyedVector):
                subIndex = index % (len(values)+1)
                index /= (len(values)+1)
                if subIndex > 0:
                    lo = values[subIndex-1]
                else:
                    lo = -1.
                try:
                    hi = values[subIndex]
                except IndexError:
                    hi = 1.
                abstract.append({'weights':obj,'index':subIndex,
                                 'lo':lo,'hi':hi})
            else:
                raise NotImplementedError,'Not yet able to abstract over rules on observations.'
        abstract.reverse()
        return abstract
    
    def fromIndex(self,index,choices=None):
        """Fills in the rules using the given number as an I{n}-ary representation of the RHS values (where I{n} is the number of possible RHS values)
        """
        if choices is None:
            choices = self.entity.actions.getOptions()
        for rule in range(len(self.rules)):
            self.rules[rule] = choices[index % len(choices)]
            index /= len(choices)

    def toIndex(self,choices=None):
        """
        @return: the I{n}-ary representation of the RHS values (where I{n} is the number of possible RHS values)
        @rtype: int
        """
        if choices is None:
            choices = self.entity.actions.getOptions()
        index = 0
        for rule in range(len(self.rules)):
            index *= len(choices)
            index += choices.index(self.rules[-rule-1])
        return index
                
    def updateAttributes(self,actor,attributes,diffs,leaves):
        """
        @param actor: the name of the agent whose turn it is
        @type actor: str
        @param attributes: the attributes already found
        @type attributes: KeyedPlane[]
        """
        options = self.entity.getEntity(actor).actions.getOptions()
        newDiffs = {}
        newLeaves = {}
        values = {}
        for action in options:
            actionDict = {self.entity.name:action}
            dynamics = self.entity.entities.getDynamics(actionDict)
            tree = dynamics['state'].getTree()
            try:
                myLeaves = values[str(action)]
            except KeyError:
                myLeaves = values[str(action)] = tree.leaves()
            myBranches = tree.branches().values()
            for branch in myBranches:
                if len(leaves) > 0:
                    # Project this branch over the actions that have
                    # occurred so far
                    for leaf in leaves.values():
                        newBranch = KeyedPlane(branch.weights*leaf,
                                               branch.threshold)
                        insertBranch(newBranch,attributes)
                else:
                    # No previous actions, so this branch is directly
                    # relevant
                    insertBranch(branch,attributes)
            if len(diffs) == 0:
                for myLeaf in myLeaves:
                    newLeaves[myLeaf.simpleText()] = myLeaf
                for other in options:
                    if action != other:
                        try:
                            yrLeaves = values[str(other)]
                        except KeyError:
                            actionDict = {self.entity.name:other}
                            dynamics = self.entity.entities.getDynamics(actionDict)
                            tree = dynamics['state'].getTree()
                            yrLeaves = values[str(other)] = tree.leaves()
                        for myLeaf in myLeaves:
                            for yrLeaf in yrLeaves:
                                diff = myLeaf - yrLeaf
                                newDiffs[diff.simpleText()] = diff
            else:
                for diff in diffs.values():
                    for myLeaf in myLeaves:
                        newDiff = myLeaf*diff
                        newDiffs[newDiff.simpleText()] = newDiff
                for leaf in leaves.values():
                    for myLeaf in myLeaves:
                        newLeaf = myLeaf*leaf
                        newLeaves[newLeaf.simpleText()] = newLeaf
        diffs.clear()
        for key,value in newDiffs.items():
            diffs[key] = value
        leaves.clear()
        for key,value in newLeaves.items():
            leaves[key] = value
        
    def importTable(self,table):
        """Takes the given table and uses it to set the LHS and RHS of this policy (making sure that the RHS refers to my entity instead)
        @param table: the PWL table that contains the relevant LHS and RHS
        @type table: L{PWLTable}
        @warning: Does not import value function, just policy itself
        """
        self.reset()
        self.attributes = table.attributes[:]
        for rule,rhs in table.rules.items():
            for option in self.entity.actions.getOptions():
                if len(rhs) == len(option):
                    # Might be equal
                    for action in option:
                        for other in rhs:
                            if other['type'] == action['type'] and \
                                    other['object'] == action['object']:
                                break
                        else:
                            # Didn't find a matching action
                            break
                    else:
                        # Match
                        self.rules[rule] = option
                        break
            else:
                raise UserWarning,'Unable to find %s\'s equivalent for %s' % \
                    (self.entity.name,str(rhs))
            
    def generateLHS(self,horizon=None,choices=None,debug=False):
        if horizon is None:
            horizon = self.horizon
        if choices is None:
            choices = self.entity.actions.getOptions()
        attributes = {}
        vectors = {}
        keyList = filter(lambda k:isinstance(k,StateKey),
                         self.entity.entities.getStateKeys().keys())
        order = self.getLookahead()
        for agent in order:
            if agent == self.entity.name:
                optionList = choices
            else:
                optionList = self.entity.getEntity(agent).actions.getOptions()
            actions = {}
            # Look for state features affected by this action
            # (we could get dynamics off of PsychAgents object itself,
            # but we sometimes want to use uncompiled dynamics)
            for option in optionList:
                for action in option:
                    actions[action] = True
            for action in actions.keys():
                for key in keyList:
                    entity = self.entity.getEntity(key['entity'])
                    dynamics = entity.getDynamics(action,key['feature'])
                    tree = dynamics.getTree()
                    for plane in tree.branches().values():
                        if isinstance(plane.weights,ThresholdRow):
                            # Needs to be a bit more permissive, but...
                            label = plane.weights.simpleText()
                            try:
                                attributes[label][plane.threshold] = True
                            except KeyError:
                                attributes[label] = {plane.threshold: True}
                                vectors[label] = plane.weights
        self.attributes = []
        for key,values in attributes.items():
            values = values.keys()
            values.sort()
            self.attributes.append((vectors[key],values))
            
    def OLDgenerateLHS(self,horizon=None,choices=None,debug=False):
        if horizon is None:
            horizon = self.horizon
        if choices is None:
            choices = self.entity.actions.getOptions()
        goals = self.entity.getGoalTree().leaves()[0]
        attributes = []
        diffs = {}
        leaves = {}
        order = self.getLookahead()
        for agent in order:
            if debug:
                print agent
            self.updateAttributes(agent,attributes,diffs,leaves)
            if debug:
                for plane in attributes:
                    print '\t',plane.weights.getArray(),plane.threshold
                print
            valuePlanes = {}
            for matrix in diffs.values():
                weights = goals*matrix
                plane = KeyedPlane(copy.deepcopy(weights),0.)
                if plane.always() is None:
                    for other in valuePlanes.values():
                        result = plane.compare(other)
                        if result in ['equal','inverse']:
                            del diffs[matrix.simpleText()]
                            break
                    else:
                        if debug:
                            print '\t',weights.getArray()
                        valuePlanes[plane.simpleText()] = plane
                else:
                    del diffs[matrix.simpleText()]
            if debug:
                print
        for matrix in diffs.values():
            weights = goals*matrix
            plane = KeyedPlane(weights,0.)
            insertBranch(plane,attributes)
        if debug:
            print 'FINAL:'
        newAttributes = {}
        for plane in attributes:
            weights = plane.weights.getArray()
            if abs(weights[1]-1.) < epsilon:
                scaling = 1./weights[1]
            else:
                scaling = 1.
            plane.weights *= scaling
            threshold = plane.threshold * scaling
            plane.threshold = 0.
            for other in newAttributes.keys():
                result = plane.compare(KeyedPlane(newAttributes[other][0],0.))
                if result == 'equal':
                    newAttributes[other][1].append(threshold)
                    break
                elif result == 'inverse':
                    newAttributes[other][1].append(-threshold)
                    break
            else:
                newAttributes[plane.weights.simpleText()] = (plane.weights,[threshold])
        for name in order[1:]:
            agent = self.entity.getEntity(name)
            newAttributes[name] = (agent,agent.actions.getOptions())
        for weights,tList in newAttributes.values():
            tList.sort()
            if debug:
                print self.attrString(weights)
                print tList
        self.attributes = newAttributes.values()
        
    def __copy__(self):
        result = LookaheadPolicy.__copy__(self)
        return PWLTable.copy(self,result)

    def __xml__(self):
        doc = LookaheadPolicy.__xml__(self)
        # Save attributes
        root = doc.createElement('attributes')
        doc.documentElement.appendChild(root)
        for obj,values in self.attributes:
            node = doc.createElement('attribute')
            root.appendChild(node)
            node.appendChild(obj.__xml__().documentElement)
            for value in values:
                child = doc.createElement('value')
                child.setAttribute('threshold',str(value))
                node.appendChild(child)
        if len(self.rules) > 0:
            # Save RHS
            root = doc.createElement('rules')
            flag = False # Set type attribute only once
            doc.documentElement.appendChild(root)
            for rhs in self.rules:
                if rhs is None:
                    rhs = self.entity.actions.getOptions()
                node = doc.createElement('rhs')
                if isinstance(rhs,list):
                    # RHS is an ordered list of actions
                    node.setAttribute('type','list')
                    for option in rhs:
                        subNode = doc.createElement('option')
                        node.appendChild(subNode)
                        for action in option:
                            subNode.appendChild(action.__xml__().documentElement)
                elif isinstance(rhs,dict):
                    # RHS is a table of action-value tree pairs
                    node.setAttribute('type','dict')
                    for action,value in rhs.items():
                        print action,value
                        if value is None:
                            continue
                        for key,dynamics in value.items():
                            subNode = doc.createElement('entry')
                            subNode.appendChild(action.__xml__().documentElement)
                            subNode.appendChild(key.__xml__().documentElement)
                            if isinstance(dynamics,dict):
                                link = doc.createElement('link')
                                link.setAttribute('entity',dynamics['entity'])
                                link.appendChild(dynamics['key'].__xml__().documentElement)
                                link.appendChild(dynamics['action'].__xml__().documentElement)
                                subNode.appendChild(link)
                            else:
                                subNode.appendChild(dynamics.__xml__().documentElement)
                            node.appendChild(subNode)
                else:
                    raise UserWarning,'Unknown RHS type: %s' % \
                          (rhs.__class__.__name__)
                root.appendChild(node)
        return doc

    def parse(self,element):
        LookaheadPolicy.parse(self,element)
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'attributes':
                    vector = KeyedVector()
                    child = node.firstChild
                    while child:
                        if child.nodeType == child.ELEMENT_NODE:
                            if child.tagName == 'attribute':
                                values = []
                                obj = None
                                grandchild = child.firstChild
                                while grandchild:
                                    if grandchild.nodeType == child.ELEMENT_NODE:
                                        if grandchild.tagName == 'value':
                                            values.append(float(grandchild.getAttribute('threshold')))
                                        else:
                                            obj = vector.parse(grandchild)
                                    grandchild = grandchild.nextSibling
                                values.sort()
                                if obj is not None:
                                    self.attributes.append((obj,values))
                        child = child.nextSibling
                elif node.tagName == 'rules':
                    child = node.firstChild
                    while child:
                        if child.nodeType == child.ELEMENT_NODE:
                            assert child.tagName == 'rhs'
                            rhsType = str(child.getAttribute('type'))
                            if rhsType == 'dict':
                                rhs = {}
                                entry = child.firstChild
                                while entry:
                                    if entry.nodeType == child.ELEMENT_NODE:
                                        assert entry.tagName == 'entry'
                                        action = None
                                        dynamics = None
                                        key = None
                                        grandChild = entry.firstChild
                                        while grandChild:
                                            if grandChild.nodeType == grandChild.ELEMENT_NODE:
                                                if grandChild.tagName == 'action':
                                                    action = Action()
                                                    action.parse(grandChild)
                                                elif grandChild.tagName == 'dynamic':
                                                    dynamics = PWLDynamics()
                                                    dynamics.parse(grandChild)
                                                elif grandChild.tagName == 'link':
                                                    dynamics = {'entity':str(grandChild.getAttribute('entity')),'action':Action(),'key':Key()}
                                                    greatChild = grandChild.firstChild
                                                    while greatChild:
                                                        if greatChild.nodeType == greatChild.ELEMENT_NODE:
                                                            if greatChild.tagName == 'action':
                                                                dynamics['action'].parse(greatChild)
                                                            elif greatChild.tagName == 'key':
                                                                dynamics['key'] = dynamics['key'].parse(greatChild)
                                                        greatChild = greatChild.nextSibling
                                                else:
                                                    key = Key()
                                                    key = key.parse(grandChild)
                                            grandChild = grandChild.nextSibling
                                        assert not action is None
                                        assert not dynamics is None
                                        assert not key is None
                                        try:
                                            rhs[action][key] = dynamics
                                        except KeyError:
                                            rhs[action] = {key: dynamics}
                                    entry = entry.nextSibling
                                self.rules.append(rhs)
                            else:
                                rhs = []
                                grandChild = child.firstChild
                                while grandChild:
                                    if grandChild.nodeType == child.ELEMENT_NODE:
                                        assert grandChild.tagName == 'option'
                                        option = []
                                        elements = grandChild.getElementsByTagName('action')
                                        for element in elements:
                                            action = Action()
                                            action.parse(element)
                                            option.append(action)
                                        rhs.append(option)
                                    grandChild = grandChild.nextSibling
                            self.rules.append(rhs)
                        child = child.nextSibling
            node = node.nextSibling
        if self.entity.name == 'Police' and self.entity.__class__.__name__ == 'PWLAgent':
            if len(self.rules) == 0:
                raise UserWarning,'%s has no rules' % (self.entity.name)

def adjustInterval(intervals,index,key,row):
    """Adjust a specific interval by the effect of the given row
    @param intervals: the intervals the state currently lies in
    @param index: the index of the current interval of relevance
    @param key: the state feature key being adjusted
    @param row: the effect row on the state feature
    @return: the adjusted interval
    """
    interval = intervals[index]
    if isinstance(row,UnchangedRow):
        # No change to current interval
        return interval
    elif isinstance(row,SetToFeatureRow):
        # Interval set by % of other interval
        for other in intervals:
            otherRow = other['weights']
            if isinstance(otherRow,ThresholdRow) and \
               other is not interval and \
               otherRow.specialKeys[0] == row.deltaKey:
                if row[row.deltaKey] > 0.:
                    lo = row[row.deltaKey]*other['lo']
                    hi = row[row.deltaKey]*other['hi']
                else:
                    lo = row[row.deltaKey]*other['hi']
                    hi = row[row.deltaKey]*other['lo']
                return {'lo':lo,'hi':hi}
        else:
            lo = max(-1.,interval['lo']-abs(row[row.deltaKey]))
            hi = min(1.,interval['hi']+abs(row[row.deltaKey]))
            return {'lo':lo,'hi':hi}
    elif isinstance(row,SetToConstantRow):
        # Interval set to fixed point
        lo = hi = row[row.deltaKey]
        return {'lo':lo,'hi':hi}
    elif isinstance(row,IncrementRow):
        # Interval offset by fixed amount
        lo = max(-1.,interval['lo']+row[row.deltaKey])
        hi = min(1.,interval['hi']+row[row.deltaKey])
        return {'lo':lo,'hi':hi}
    elif isinstance(row,ScaleRow):
        # Interval offset by % of other
        if row.deltaKey == key:
            lo = max(-1.,interval['lo']*row[key])
            hi = min(1.,interval['hi']*row[key])
            return {'lo':lo,'hi':hi}
        else:
            for other in intervals:
                otherRow = other['weights']
                if isinstance(otherRow,ThresholdRow) and \
                       other is not interval and \
                       otherRow.specialKeys[0] == row.deltaKey:
                    if row[row.deltaKey] > 0.:
                        delta = {'lo':row[row.deltaKey]*other['lo'],
                                 'hi':row[row.deltaKey]*other['hi']}
                    else:
                        delta = {'lo':row[row.deltaKey]*other['hi'],
                                 'hi':row[row.deltaKey]*other['lo']}
                    break
            else:
                # No constraint on this state featureb
                delta = {'lo':-abs(row[row.deltaKey]),
                         'hi': abs(row[row.deltaKey])}
            lo = max(-1.,interval['lo']+delta['lo'])
            hi = min( 1.,interval['hi']+delta['hi'])
            return {'lo':lo,'hi':hi}
    else:
        raise NotImplementedError,'Unable to compute abstract effect for %s\n'\
            % (row.__class__.__name__)

def insertBranch(new,oldList):
    """Adds the new branch to the old list if neither it (nor its inverse) is
    already present
    @param new: branch to be added
    @type new: KeyedPlane
    @param oldList: the branches already found (modified directly)
    @type oldList: KeyedPlane[]
    """
    for branch in oldList:
        result = new.compare(branch)
        if result in ['equal','inverse']:
            break
    else:
        oldList.append(new)
    
if __name__ == '__main__':
    import sys
    from xml.dom.minidom import parse
    from teamwork.multiagent.sequential import SequentialAgents
    from teamwork.agent.Entities import PsychEntity
    from optparse import OptionParser

    # Parse command-line options
    parser = OptionParser('usage: %prog [options] SCENARIO')
    parser.add_option('-b','--bully-resolution',
                      dest='bullyResolution',
                      metavar='BRES',
                      help='resolution of goal space for bully',
                      default=5)
    parser.add_option('-t','--teacher-resolution',
                      dest='teacherResolution',
                      metavar='TRES',
                      help='resolution of goal space for teacher',
                      default=5)
    parser.add_option('-o','--output-file',
                      dest='output',
                      metavar='FILE',
                      help='file in which to store data [default is standard out]',
                      default=None)
    parser.add_option('-c','--collapse',
                      dest='collapse',
                      action='store_true',
                      help='collapse common rows into a single entry',
                      default=False)

    (options,args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments")
    doc = parse(args[0])
    scenario = SequentialAgents()
    scenario.parse(doc.documentElement,PsychEntity)
    policies = {}
    name = 'Teacher'
    for agent in scenario.activeMembers():
        print agent.name
        for goal in agent.getGoals():
            print '\t',goal,agent.getGoalWeight(goal)
        table = PolicyTable(agent,agent.actions.getOptions(),
                            len(scenario),agent.horizon)
        if agent.name != name:
            table.rules = [None]
        policies[agent.name] = table

##    # Temporary output generation of policies from indices
##    for index in [0,6,687,1030,2059,1,36,43]:
##        policies[name].rules = range(4)
##        policies[name].fromIndex(index)
##        print index
##        print policies[name].rules
##    # End of temporary code
    agent = scenario[name]
    state = scenario.getState().domain()[0]
    granularity = int(options.teacherResolution)
    tSpace = agent.generateSpace(granularity)
    granularity = int(options.bullyResolution)
    bSpace = scenario['Bully'].generateSpace(granularity)
    # Print column headings
    columns = ['B Type','B Goals','T Type','T Goals','T Policy','T Count',
               'B Policy','O Policy','T Action','B ER']
##    errors = ['B MisAction','O MisAction','T MisAction','Error']
    errors = ['Error']
    if options.collapse:
        try: columns.remove('T Type')
        except ValueError: pass
        try: columns.remove('T Goals')
        except ValueError: pass
    else:
        try: columns.remove('T Count')
        except ValueError: pass
    header = ''
    for column in columns:
        if column == 'T Goals':
            goals = agent.getGoals()
            goals.sort()
            for goal in goals:
                header += '%s %s,' % (goal.direction,goal.entity[0])
        elif column == 'B Goals':
            goals = scenario['Bully'].getGoals()
            goals.sort()
            for goal in goals:
                header += '%s %s,' % (goal.direction,goal.entity[0])
        else:
            header += '%s,' % (column)
    if options.output:
        f = open(options.output,'w')
    else:
        f = sys.stdout
    f.write(header[:-1]+'\n')
    for bully in range(len(bSpace)):
        # Try each possible set of goals for the bully
        feasible = {}
        bWeights = bSpace[bully]
        for goal,weight in bWeights.items():
            scenario['Bully'].setGoalWeight(goal,weight,normalize=False)
            agent.getEntity('Bully').setGoalWeight(goal,weight,normalize=False)
        for teacher in range(len(tSpace)):
            # Try each possible set of goals for the teacher
            tWeights = tSpace[teacher]
            for goal,weight in tWeights.items():
                agent.setGoalWeight(goal,weight,normalize=False)
            policies[name].solve(choices=agent.actions.getOptions(),
                                 policies=policies)
            index = policies[name].toIndex()
            entry = {'Teacher goals':tWeights,
                     'Teacher policy':index,
                     'Bully goals':bWeights,
                     'Bully RHS':policies['Bully'].rules[0],
                     'Onlooker RHS':policies['Onlooker'].rules[0],
                     'Bully ER':policies['Bully'].evaluate(policies,state,{})
                     }
            # Output data
            line = ''
            for column in columns:
                if column == 'B Goals':
                    goals = bWeights.keys()
                    goals.sort()
                    for goal in goals:
                        line += '%f,' % (scenario['Bully'].getGoalWeight(goal))
                elif column == 'B Type':
                    line += '%d,' % (bully)
                elif column == 'T Goals':
                    goals = tWeights.keys()
                    goals.sort()
                    for goal in goals:
                        line += '%f,' % (agent.getGoalWeight(goal))
                elif column == 'T Type':
                    line += '%d,' % (teacher)
                elif column == 'T Policy':
                    line += '%d,' % (index)
                elif column == 'O Policy':
                    line += '%s,' % (policies['Onlooker'].rules[0][0]['type'])
                elif column == 'B Policy':
                    line += '%s,' % (policies['Bully'].rules[0][0]['type'])
                elif column == 'B ER':
                    line += '%f,' % (entry['Bully ER'])
                elif column == 'T Action':
                    observations = {'Bully':policies['Bully'].execute(state,None),
                                    'Onlooker':policies['Onlooker'].execute(state,None),
                                    }
                    action = policies['Teacher'].execute(state,observations)
                    line += '%s,' % (action[0]['type'])
                else:
                    line += '%s,' % (column)
            entry['data'] = line
            try:
                feasible[index].append(entry)
            except KeyError:
                feasible[index] = [entry]
            if not options.collapse:
                f.write(line[:-1]+'\n')
                f.flush()
        if options.collapse:
            modelSpace = feasible.keys()
            modelSpace.sort()
            for model in modelSpace:
                # Loop through possible mental models to use
                entryList = feasible[model]
                entry = entryList[0]
                line = entry['data']
                # Count number of teacher models that reduce to this policy
                line = line.replace('T Count','%d' % (len(entryList)))
                # Analyze lost ER when using this model
                policies['Bully'].rules[0] = entry['Bully RHS']
                for real in modelSpace:
                    realEntry = feasible[real][0]
                    policies['Teacher'].fromIndex(real)
                    policies['Onlooker'].rules[0] = realEntry['Onlooker RHS']
                    if model == real:
                        error = 0.
                    else:
                        # Measure lost ER
                        value = policies['Bully'].evaluate(policies,state,{})
                        error = entry['Bully ER']-value
                    for column in errors:
                        if column == 'Error':
                            line += '%f,' % (error)
                        elif column == 'B MisAction':
                            line += '%s,' % (policies['Bully'].rules[0][0]['type'])
                        elif column == 'O MisAction':
                            line += '%s,' % (policies['Onlooker'].rules[0][0]['type'])
                        elif column == 'T MisAction':
                            observations = {'Bully':policies['Bully'].execute(state,None),
                                            'Onlooker':policies['Onlooker'].execute(state,None),
                                            }
                            action = policies['Teacher'].execute(state,observations)
                            line += '%s,' % (action[0]['type'])
                        else:
                            raise NotImplementedError,column
                f.write(line[:-1]+'\n')
            f.flush()
            
    f.close()
