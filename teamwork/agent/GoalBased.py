"""Defines the layer for handling reward functions"""
import copy
import os
import sys
import tempfile
from teamwork.math.Keys import StateKey,ObservationKey,ActionKey,keyConstant
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.KeyedTree import KeyedPlane,KeyedTree
from teamwork.math.probability import Distribution
from teamwork.reward.goal import PWLGoal,minGoal,maxGoal
from teamwork.reward.MinMaxGoal import MinMaxGoal
from teamwork.policy.pwlTable import PWLTable
from RecursiveAgent import RecursiveAgent

class GoalBasedAgent(RecursiveAgent):
    """An entity mix-in class that has a reward function based on maximization/minimization of features/actions
    @ivar goals: the goals of this agent
    @type goals: L{MinMaxGoal}S{->}float
    @ivar constraints: the constraints on the goal weights already imposed.
    Each constraint is a dictionary, with the key element being the 'plane'
    expressing the constraint
    @type constraints: dict:str->L{KeyedPlane}
    @ivar reward: cache of reward matrices, indexed by joint actions
    """
    valueTypes = ['cumulative','terminal']
    defaultValueType = 0
    
    def __init__(self,name=''):
        RecursiveAgent.__init__(self,name)
        self.valueType = self.valueTypes[self.defaultValueType]
        self.goals = Distribution()
        self.constraints = {}
        self.goalCache = {}
        self.R = {}
            
    # Goal methods

    def setGoals(self,goals):
        """Sets the goals to the provided list, after normalizing weights
        @type goals: L{MinMaxGoal}[]
        @warning: Replaces any existing goals."""
        # Clear any existing goals
        self.goals.clear()
        if not isinstance(goals,Distribution):
            raise DeprecationWarning,'Use Distribution to set goals, not list'
        for goal in goals.domain():
            self.goals[goal] = goals[goal]
        self.normalizeGoals()
        
    def normalizeGoals(self):
        """Scales all goal weights to sum to 1."""
        self.goals.normalize()
        self.goalCache.clear()
        self.R.clear()
            
    def setGoalWeight(self,goal,value,normalize=True):
        """Assigns the weight of the specified goal
        @type goal: L{MinMaxGoal}
        @type value: float
        @param normalize: if C{True}, renormalizes weights across all goals to sum to 1
        @type normalize: bool
        """
        total = 0.
        delta = 0.
        found = False
        # Adjust selected goal weight, compute normalization factor
        # along the way
        for existing in self.goals.domain():
            weight = self.goals[existing]
            if existing.keys == goal.keys:
                delta = float(value) - weight
                self.goals[existing] = float(value)
                found = True
            else:
                total += weight
        # If we haven't found it, then this is a newly relevant goal
        if not found:
            delta = float(value)
            self.goals[goal] = delta
        # Renormalize
        if normalize:
            for existing in self.goals.domain():
                weight = self.goals[existing]
                if existing.keys != goal.keys:
                    try:
                        self.goals[existing] -= delta*weight/total
                    except ZeroDivisionError:
                        if weight > 0.:
                            self.goals[existing] = 1.-value
        # Set weights on goal objects as well
        for goal in self.getGoals():
            goal.weight = self.getGoalWeight(goal)
        self.goalCache.clear()
        self.R.clear()

    def applyGoals(self,entity=None,world=None,actions={},debug=None):
        """
        @param entity: the entity whose goals are to be evaluated (default is self)
        @type entity: L{GoalBasedAgent}
        @param world: the context for evaluating the goals (default is the beliefs of I{entity})
        @type world: dict
        @return: expected reward of the I{entity} in current I{world}
        @rtype: L{Distribution} over C{float},dict"""
        if not entity:
            entity = self
        if world is None:
            world = self.getAllBeliefs()
        total = Distribution({0.: 1.})
        reward = {}
        for goal in self.getGoals():
            key = goal.toKey()
            if goal.isMeta():
                # Metagoal (would be better to do in PWLGoal)
                try:
                    belief = self.getEntity(key['entity'])
                except KeyError:
                    # Circularity has dropped us past bottom of beliefs
                    continue
                R,subReward = belief.applyGoals(world=world,actions=actions,debug=debug)
                R = goal._sign(R)
            else:
                R = goal.reward(world,actions)
            if isinstance(R,Distribution):
                reward[key] = R.expectation()
            else:
                reward[key] = R
            total += R*self.goals[goal]
        return total,reward
        
    def getGoals(self):
        """
        @rtype: L{PWLGoal}[]"""
        return self.goals.domain()

    def getGoalWeight(self,goal):
        """
        @type goal: L{PWLGoal}
        @return: the weight of the specified goal
        @rtype: float
        """
        try:
            return self.goals[goal]
        except KeyError:
            return 0.0

    def getGoalVector(self):
        """Returns a vector representing the goal weights
        @rtype: L{KeyedVector} instance"""
        stateGoals = KeyedVector()
        actionGoals = KeyedVector()
        totalGoals = KeyedVector()
        for goal in self.getGoals():
            key = goal.toKey()
            weight = self.getGoalWeight(goal)
            if not goal.max:
                weight = -weight
            if isinstance(key,StateKey):
                stateGoals[key] = weight
            elif isinstance(key,ActionKey):
                actionGoals[key] = weight
            else:
                raise NotImplementedError,'Unable to make vector with %s instances' % (key.__class__.__name__)
            totalGoals[key] = weight
        return {'state':Distribution({stateGoals:1.}),
                'action':Distribution({actionGoals:1.}),
                'total':Distribution({totalGoals:1.}),
                }

    def getGoalTree(self,actions={},keyList=None):
        """
        @return: the decision tree representing this entity's goal weights
        @rtype: L{ProbabilityTree}
        """
        key = self.makeActionKey(actions)
        try:
            # We got us a cache
            return self.goalCache[key]
        except KeyError:
            # Combine trees across all goals
            tree = None
            for goal in self.getGoals():
                subtree = goal.getTree(actions)
                if tree is None:
                    tree = subtree
                else:
                    tree += subtree
            # Figure out which state keys to flesh out tree with
            if keyList is None:
                keyList = self.entities.getStateKeys().keys()
                if len(keyList) == 1:
                    # At the bottom of belief hierarchy, so let's pretend we have
                    # a full state vector.  It's fun to pretend.
                    keyList = self.state.domainKeys().keys()
                keyList.sort()
            tree.fill(keyList)
            tree.freeze()
            self.goalCache[key] = tree
            return tree
    
    def getRewardVector(self,actions,worlds={}):
        """
        @return: a vector representing the reward over the given set of possible worlds
        @rtype: L{KeyedVector}
        """
        actionKey = self.makeActionKey(actions)
        try:
            return self.R[actionKey]
        except KeyError:
            vector = KeyedVector()
            for key,world in worlds.items():
                reward,breakdown = self.applyGoals(world={'state':world},actions=actions)
                assert len(reward) == 1,'Uncertain rewards?!'
                vector[key] = reward.expectation()
            vector.freeze()
            self.R[actionKey] = vector
            return vector
        
    def getRewardTable(self,scenario=None):
        """
        @return: a reward function as a function of only my action, given the policies of the other agents in the system
        @rtype: L{PWLTable}
        """
        if scenario is None:
            scenario = self.entities
        R = PWLTable()
        rule = R.rules[0]
        for myAction in self.actions.getOptions():
            value = KeyedVector()
            for key,world in scenario.getWorlds().items():
                nodes = self.actionDistribution(world,myAction)
                value[key] = 0.
                for actions,prob in nodes:
                    reward,breakdown = self.applyGoals(world={'state':world},actions=actions)
                    value[key] += prob*reward.expectation()
            value.freeze()
            rule['values'][self.makeActionKey(myAction)] = value
        return R

    def actionValue(self,actions,horizon=1,state=None,debug=False):
        """Compute the expected value of performing the given action
        @param actions: the actions whose effect we want to evaluate
        @type actions: L{Action}[]
        @param horizon: the length of the forward projection
        @type horizon: int
        @param state: the world state to evaluate the actions in (defaults to current world state)
        @type state: L{teamwork.math.probability.Distribution}
        """
        if debug:
            print 'Computing EV[%s] | %s,%d' % (self.makeActionKey(actions),
                                                self.ancestry(),horizon)
        if state is None:
            state = self.getAllBeliefs()
        start = {self.name:actions}
        value,explanation = self.expectedValue(horizon=horizon,
                                               start=start,
                                               state=state,
                                               goals=[self],
                                               debug=debug)
        value = value[self.name]
        return value,explanation

    def expectedValue(self,horizon=1,start={},goals=None,state=None,
                      debug=False):
        """
        @param horizon: the horizon for the lookahead when computing the expected value
        @type horizon: C{int}
        @param start: a dictionary of actions to be specified in the first time step
        @type start: C{dict:strS{->}L{Action}[]}
        @param goals: the agent(s) whose reward function should be used to compute the expectation (defaults to C{self})
        @type goals: C{L{GoalBasedAgent}[]}
        @param state: the world state to evaluate the actions in (defaults to current world state)
        @type state: L{teamwork.math.probability.Distribution}
        @type debug: L{Debugger}
        @return: the expected reward from the current state

        """
        if goals is None:
            goals = [self]
        if state is None:
            state = self.getAllBeliefs()
        # Lookahead
        sequence = self.multistep(horizon=horizon,start=start,
                                  state=state,debug=debug)
        value = {}
        expectation = {}
        if self.valueType == 'cumulative':
            duration = range(len(sequence))
        elif self.valueType == 'terminal':
            duration = [-1]
        else:
            raise NotImplementedError,\
                  'I do not know how to compute "%s" expected value' \
                  % (self.valueType)
        # Reward averaged over entire time span
        for t in range(len(duration)):
            step = sequence[t]
            for delta in step:
                # Compute expected rewards
                for entity in goals:
                    reward,breakdown = entity.applyGoals(world=delta['result'],actions=delta['action'])
                    reward *= delta['probability']
                    try:
                        value[entity.name] += reward
                    except KeyError:
                        value[entity.name] = reward
                    breakdown = KeyedVector(breakdown)
                    try:
                        expectation[entity.name] += breakdown
                    except KeyError:
                        expectation[entity.name] = breakdown
#         # Compute average reward
#         scale = float(len(sequence))
#         for vector in expectation.values():
#             vector *= 1./scale
#         for key in value.keys():
#             value[key] /= scale
#         elif self.valueType == 'terminal':
#             # Reward for only end state
#             for delta in sequence[-1]
#             for entity in goals:
#                 reward,breakdown = entity.applyGoals(world=sequence[-1],
#                                                      actions=sequence[-1]['action'])
#                 value[entity.name] = reward
#                 expectation[entity.name] = KeyedVector(breakdown)
        if debug:
            for name,reward in value.items():
                print 'R[%s] = %s' % (name,str(reward))
        if len(value) == 0:
            # No projection happened
            for goal in goals:
                value[goal] = goal.applyGoals(None,debug=debug)
        return value,{'value':value,
                      'projection':expectation,
                      'breakdown':sequence,
                      }

    def getCassandra(self,f=None,horizon=None,discount=1.0,debug=False):
        """
        Generates a POMDP representation of this agent's subjective decision
        problem
        @param f: optional file object to write to
        @param discount: the discount factor to use (default is 1.0, as appropriate for finite-horizon solution)
        @type discount: float
        @return: a string containing the POMDP spec
        @rtype: str
        """
        if f is None:
            f = sys.stdout
        if horizon is None:
            horizon = self.policy.getHorizon()
        worlds = self.entities.getWorlds(horizon=horizon,perspective=self.name)
        print 'Worlds:',len(worlds)
        if self.policy.getDepth() == 0:
            # Level 0 so use null policy in beliefs
            self.entities.nullPolicy(False) #,'Player 2-stay,Player 1-stay')
        # Preamble
        print >> f,'discount: %f' % (discount)
        print >> f,'values: reward'
        print >> f,'states: %d' % (len(worlds))
        actions = map(lambda a: self.makeActionKey(a),
                      self.actions.getOptions())
        print >> f,'actions: %s' % (' '.join(map(lambda a: a.replace(' ',''),
                                                 actions)))
        observations = ' '.join(map(lambda o: str(o).replace(' ',''),
                                    self.getOmega()))
        print >> f,'observations: %s' % (observations)
        # Start belief
        belief = self.entities.state2world(self.beliefs)
        print >> f,'start: %s' % (' '.join(map(str,belief.getArray())))
        # Transition
        T = self.getT(False)
        for action in actions:
            matrix = T[action]
            print >> f,'T:',action.replace(' ','')
            for start in range(len(worlds)):
                if debug:
                    print 'Start:',matrix.colKeys()[start]
                    self.printWorld(worlds[matrix.colKeys()[start]])
                    print action
                for end in range(len(worlds)):
                    if debug and matrix.getArray()[end][start] > 1e-8:
                        print '\tEnd:',matrix.rowKeys()[end]
                        self.printWorld(worlds[matrix.rowKeys()[end]])
                        print '\t-->',matrix.getArray()[end][start]
                    print >> f,matrix.getArray()[end][start],
                print >> f
            if debug:
                print action
                print matrix.simpleText()
        # Observation probabilities
        O = self.getO()
        for action in actions:
            matrix = O[action]
            print >> f,'O:',action.replace(' ','')
            if debug:
                print 'O (%s)' % (action)
            for start in range(len(worlds)):
                if debug:
                    key = matrix.keys()[start]
                    self.printWorld(worlds[key])
                    print matrix[key].simpleText()
                print >> f,' '.join(map(str,matrix.getArray()[start]))
        # Reward
        R = self.getRewardTable().rules[0]['values']
        for action in actions:
            vector = R[action]
            if debug:
                print 'R (%s)' % (action)
            for key in vector.keys():
                if debug:
                    self.printWorld(worlds[key])
                    print vector[key]
                print >> f,'R: %s : %d : * : * %5.2f' % \
                    (action.replace(' ',''),key['world'],vector[key])


    def getPOMDP(self,f=None,horizon=None,discount=1.0,tolerance=.001,debug=False):
        """
        Generates a POMDP representation of this agent's subjective decision
        problem
        @param f: optional file object to write to
        @param discount: the discount factor to use (default is 1.0, as appropriate for finite-horizon solution)
        @type discount: float
        @return: a string containing the POMDP spec
        @rtype: str
        """
        if f is None:
            f = sys.stdout
        if horizon is None:
            horizon = self.policy.getHorizon()
        worlds = self.entities.getWorlds(horizon=horizon,perspective=self.name)
        if self.policy.getDepth() == 0:
            # Level 0 so use null policy in beliefs
            self.entities.nullPolicy(False)
        # Generate possible state features and the domain of each
        domains = {}
        for world in worlds:
            vector = self.entities.worlds[world]
            for key in vector.keys():
                if isinstance(key,StateKey):
                    value = int(100.*vector[key])
                    try:
                        domains[key][value] = True
                    except KeyError:
                        domains[key] = {value: True}
        print >> f,'(variables'
        variables = domains.keys()
        variables.sort()
        for key in variables:
            variable = '%s%s' % (key['entity'],key['feature'])
            print >> f,'\t(%s %s)' % (variable,' '.join(map(str,domains[key].keys())))
        print >> f,')'
        # Observations
        print >> f,'(observations (omega %s))' % (' '.join(map(lambda w: str(w).replace(' ',''),self.getOmega())))
        # Actions
        for option in self.actions.getOptions():
            assert len(option) == 1
            action = option[0]['type'].replace(' ','')
            if option[0]['object']:
                action += option[0]['object'].replace(' ','')
            print >> f,'action %s' % (action)
            for key in variables:
                variable = '%s%s' % (key['entity'],key['feature'])
                entity = self.entities[key['entity']]
                try:
                    dynamics = entity.dynamics[key['feature']][option[0]['type']]
                except KeyError:
                    print >> f,'\t%s\t(SAME%s)' % (variable,variable)
                    continue
                print dynamics['condition']
                print dynamics['tree']
            print >> f,'endaction'
        print >> f,'discount %f' % (discount)
        print >> f,'tolerance %f' % (tolerance)
        return
    
    def solvePOMDP(self,solver,depth,horizon,discount=1.,interrupt=None):
        import time
        start = time.time()
        # Set up proper belief depth
        self.setPolicies(depth,horizon)
        print 'setup:',time.time()-start
        # Generate POMDP in temporary directory
        label = self.name.replace(' ','')
        oldDir = os.getcwd()
        dir = tempfile.mkdtemp()
        os.chdir(dir)
        filename = '%s.pomdp' % (label)
        print dir,filename
        f = open(filename,'w')
        self.getPOMDP(f,horizon,discount=discount,debug=False)
        f.close()
        raise UserWarning
        os.system('%s solve -t 120 -o %s.policy %s.pomdp' % (solver,label,label))
        del self.policy.tables[depth][1:]
        table = self.policy.tables[depth][0]
        table.load(self,'%s.policy' % (label),zpomdp=True)
        print 'pomdp:',time.time()-start
#         # Fill in policy tables
#         for T in range(0,horizon+1):
#             # System call of POMDP solver
#             out = '%s-%02d' % (label,T)
#             os.system('%s -stdout %s.log -pomdp %s -horizon %d -o %s' % \
#                           (solver,label,filename,T+1,out))
#             # Load resulting value function
#             table = self.policy.tables[depth][T]
#             try:
#                 table.load(self,'%s.alpha' % (out))
#                 print 'Vectors:',len(table.rules[0]['values'])
#             except IOError,msg:
#                 # Restore original working directory before passing it on
#                 os.chdir(oldDir)
#                 raise IOError,msg
#             print T,time.time()-start
        # State estimators
        self.getEstimator()
        print 'total:',time.time()-start
#         # Evaluate
#         f = open(filename,'r')
#         data = f.read()
#         f.close()
#         data = data[data.find('\n'):]
#         f = open(filename,'w')
#         f.write('discount: 1.0\n')
#         f.write(data)
#         f.close()
#         os.system('%s eval --evaluationMaxStepsPerTrial 100 --evaluationTrialsPerEpoch 1000 --policyInputFile %s.policy %s.pomdp' % (solver,label,label))
#         os.rename('scores.plot','/tmp/scores.plot')
#         os.rename('sim.plot','/tmp/sim.plot')
#         os.rename('%s.pomdp' % (label),'/tmp/testing.pomdp')
#         os.rename('%s.policy' % (label),'/tmp/testing.policy')
        os.chdir(oldDir)
#        self.dumpPolicy(horizon)

    def dumpPolicy(self,horizon=None):
        """
        Generate a description of my current behavior in observation-history form
        """
        if horizon is None:
            horizon = self.policy.getHorizon()
        initial = self.entities.state2world(self.beliefs)
        for t in range(len(self.policy.tables[-1])):
            table = self.policy.tables[-1][t]
            Vstar = max(map(lambda V: V['V']*initial,
                            table[initial]['values']))
            print '%d\t%f\t%f' % (t,Vstar,Vstar/float(t+1))
#         nodes = [{'observations': [],'horizon': horizon,'belief': initial}]
#         while len(nodes) > 0:
#             node = nodes.pop()
#             decision,explanation = self.policy.execute(node['belief'],horizon=node['horizon'])
#             action = self.makeActionKey(decision)
#             print '%s\t%s' % (action,'\t'.join(map(str,node['observations'])))
#             if node['horizon'] > 0:
#                 for omega in self.getOmega():
#                     update = self.getEstimator()[omega][node['belief']]
#                     new = update['values'][action]
#                     new = new*node['belief']
#                     new *= 1./sum(new.getArray())
#                     nodes.append({'observations': node['observations']+[omega],
#                                   'horizon': node['horizon']-1,'belief': new})

    def getNormalization(self,constant=False):
        """
        @param constant: if C{True}, include a column for the constant factor (which will be 1)
        @type constant: bool
        @return: the vector expressing the constraint that the goal weights sum to 1
        @rtype: L{KeyedVector}
        """
        weights = KeyedVector()
        for goal in self.getGoals():
            key = goal.toKey()
            if goal.isMax(): 
                weights[key] = 1.
            else:
                weights[key] = -1.
        if constant:
            weights[keyConstant] = 1.
        weights.freeze()
        return weights
    
    def generateConstraints(self,desired,horizon=-1,state=None):
        """Computes a set of constraints on possible goal weights for this agent that, if satisfied, will cause the agent to prefer the desired action in the given state.  Each constraint is dictionary with the following elements:
           - delta: the total difference that must be made up
           - slope: dictionary of coefficients for each goal weight in the sum that must make up that difference
           - plane: the vector of weights, such that the product of this vector and the goal weight vector must exceed 0 for the desired action to be preferred
        @param desired: the action that the agent should prefer
        @type desired: L{Action}[]
        @param horizon: the horizon of lookahead to use (if not provided, the agent's default horizon is used)
        @type horizon: int
        @param state: the current state of this agent's beliefs (if not provided, defaults to the result of L{getAllBeliefs}
        @type state: dict
        @return: a list of constraints
        @rtype: dict[]
        """
        if horizon < 0:
            horizon = self.horizon
        if state is None:
            state = self.getAllBeliefs()
        goals = self.getGoalVector()['total']
        if len(goals.domain()) != 1:
            raise NotImplementedError,\
                  'Unable to handle uncertain goals when fitting'
        goals = goals.expectation()
        # Compute projections for all actions
        matrices = {}
        for action in self.actions.getOptions():
            sequence = self.multistep(horizon=horizon,
                                      start={self.name:action},
                                      state=copy.deepcopy(state))
            value = None
            if self.valueType == 'cumulative':
                duration = range(len(sequence))
            elif self.valueType == 'terminal':
                # Assume no action goals if we care about only the final state
                duration = [-1]
            else:
                raise NotImplementedError,\
                      'I do not know how to fit "%s" expected value' \
                      % (self.valueType)
            for t in duration:
                for delta in sequence[t]:
                    current = copy.deepcopy(delta['result']['state'])
                    # Add in current state
                    if value is None:
                        value = current.expectation()*delta['probability']
                    else:
                        current.unfreeze()
                        current.fill(value.keys())
                        current.freeze()
                        value += current.expectation()*delta['probability']
                    # Add in relevant actions
                    for key in filter(lambda k:isinstance(k,ObservationKey),
                                      goals.keys()):
                        if not value.has_key(key):
                            value.unfreeze()
                            value[key] = 0.
                            value.freeze()
                        for act in sum(sequence[t]['action'].values(),[]):
                            if act['type'] == key['type']:
                                value[key] += 1.
            matrices[str(action)] = value
        # Compare against desired action
        constraints = []
        goals.fill(matrices[str(desired)].keys())
        for action in self.actions.getOptions():
            if action != desired:
                projection = matrices[str(desired)] - matrices[str(action)]
                diff = goals*projection
                constraint = {'delta':diff,
                              'value':True,
                              'slope':KeyedVector(),
                              'option':action,
                              }
                for goal in self.getGoals():
                    key = goal.toKey()
                    if goal.isMeta():
                        entity = self.getEntity(key['entity'])
                        total = 0.
                        for subgoal in entity.getGoals():
                            subkey = subgoal.toKey()
                            if subgoal.isMeta():
                                # Ignore next level of recursion?
                                pass
                            else:
                                total += projection[subkey]
                        constraint['slope'][key] = total
                    else:
                        constraint['slope'][key] = projection[key]
                constraint['plane'] = KeyedPlane(constraint['slope'],0.)
                constraint['plane'].weights.freeze()
                constraints.append(constraint)
        return constraints

    def fit(self,desired,horizon=-1,state=None,granularity=0.01,label=None):
        """Computes a new set of goal weights for this agent that will cause the agent to prefer the desired action in the given state.
        @param desired: the action that the agent should prefer
        @type desired: L{Action}[]
        @param horizon: the horizon of lookahead to use (if not provided, the agent's default horizon is used)
        @type horizon: int
        @param state: the current state of this agent's beliefs (if not provided, defaults to the result of L{getAllBeliefs}
        @type state: dict
        @param granularity: the minimum movement of a goal weight (default is 0.01)
        @type granularity: float
        @param label: the label to store the generated constraints under,
        overwriting any previous constraints using the same label (by default,
        C{None})
        @type label: str
        @return: a goal vector (error message if no such vector exists)
        @rtype: L{KeyedVector} (str)
        """
        constraints = self.generateConstraints(desired,horizon,state)
        # Remove redundant constraints
        remove = {}
        for index in range(len(constraints)):
            constraint = constraints[index]
            for other in constraints[:index]:
                result = other['plane'].compare(constraint['plane'])
                if result == 'equal':
                    remove[index] = True
                    break
        remove = remove.keys()
        remove.sort()
        remove.reverse()
        for index in remove:
            del constraints[index]
        # Add earlier constraints that do not refer to current state
        cumulative = constraints[:]
        for key,values in self.constraints.items():
            if key != label:
                cumulative += values
        # Find the current goal weights
        vectors = self.getGoalVector()
        goals = vectors['state'].domain()[0]
        vector = vectors['action'].domain()[0]
        for key in vector.keys():
            goals[key] = vector[key]
        # Find the surface of the combined constraints
        surface = None
        for index in range(len(cumulative)):
            constraint = cumulative[index]
            if constraint['plane'].isZero():
                # There is no difference between this action and another
                return 'The selected action is equivalent to %s' % \
                       (', '.join(map(str,constraint['option'])))
            elif surface is None:
                surface = KeyedTree(constraint['plane'])
            else:
                split = []
                for other in cumulative[:index]:
                    result = other['plane'].compare(constraint['plane'])
                    if result == 'indeterminate':
                        # The planes intersect
                        weights = constraint['plane'].weights - \
                                  other['plane'].weights
                        threshold = constraint['plane'].threshold - \
                                  other['plane'].threshold
                        # Check whether this new plane can be satisfied
                        total = 0.
                        for key in weights.keys():
                            if weights[key] > 0.:
                                total += weights[key]
                            else:
                                total -= weights[key]
                        if total > threshold:
                            split.append(KeyedPlane(weights,threshold))
                        else:
                            # Not even at all +/-1 can this work
                            break
                    elif result == 'equal':
                        # This plane is redundant
                        break
                    elif result == 'less':
                        # This plane dominates another one
                        # (we could also remove the other one, but tricky)
                        pass
                    elif result == 'greater':
                        # This plane is dominated
                        break
                    elif result == 'inverse':
                        # These planes are contradictory
                        return 'There are contradictory constraints on the goals.'
                else:
                    subtree = KeyedTree(constraint['plane'])
                    if len(split) > 0:
                        # This plane is maximal only under some conditions
                        new = KeyedTree()
                        new.branch(split,subtree,surface)
                        surface = new
                    else:
                        # This plane dominates all previous ones
                        surface = subtree
        # Check whether we can move toward surface
        if surface[goals].test(goals):
            # We already satisfy our constraints
            return goals
        # Check whether we can move toward the surface
        plane = surface[goals]
        increase = {}
        decrease = {}
        for key in goals.keys():
            if goals[key]*plane.weights[key] > 0.:
                increase[key] = True
            elif goals[key]*plane.weights[key] < 0.:
                decrease[key] = True
        if len(increase) == 0 or len(decrease) == 0:
            # All the weights must move in the same direction!
            return 'No goals motivate the desired action!'
        # Move into the surface (with some maximum # of moves)
        for index in range(100):
            plane = surface[goals]
            if plane.test(goals):
                # Hooray!  Now, it's safe to save these constraints
                self.constraints[label] = constraints
                return goals
            # Find out how many goals have large enough weights to change
            for key in increase.keys():
                if abs(goals[key]) > 1.- granularity:
                    del increase[key]
            for key in decrease.keys():
                if abs(goals[key]) < granularity:
                    del decrease[key]
            # For the side that must change by more than
            # "granularity", test whether  there are enough to change
            change = True
            while change:
                if len(increase) == 0 or len(decrease) == 0:
                    # We have lost all of the goals on one side
                    break
                change = False
                ratio = float(len(increase)/len(decrease))
                if ratio > 1.:
                    for key in decrease.keys():
                        if abs(goals[key]) < granularity*ratio:
                            del decrease[key]
                            change = True
                            break
                elif ratio < 1.:
                    for key in increase.keys():
                        if abs(goals[key]) < granularity/ratio:
                            del increase[key]
                            change = True
                            break
            if change:
                # We exited on a failure
                break
            else:
                # OK, let's try moving the goal weights
                for key in increase.keys():
                    if plane.weights[key] > 0.:
                        delta = granularity
                    elif plane.weights[key] < 0.:
                        delta = -granularity
                    if ratio < 1.:
                        delta /= ratio
                    goals[key] += delta
                for key in decrease.keys():
                    if plane.weights[key] > 0.:
                        delta = granularity
                    elif plane.weights[key] < 0.:
                        delta = -granularity
                    if ratio > 1.:
                        delta *= ratio
                    goals[key] += delta
        # Failure
        return 'Unable to find a satisfying set of goal weights.'

    def __str__(self):
        rep = RecursiveAgent.__str__(self)
        rep = rep + '\n\tGoals:\n'
        rep = rep + '\t\t' + `map(lambda g,s=self:(g,s.getGoalWeight(g)),
                                  self.goals.keys())`+'\n'
        return rep

    def __copy__(self,new=None):
        if not new:
            new = RecursiveAgent.__copy__(self)
        for goal in self.getGoals():
            new.setGoalWeight(goal,self.getGoalWeight(goal),None)
        return new

    def __xml__(self):
        doc = RecursiveAgent.__xml__(self)
        # Add goals
        root = doc.createElement('goals')
        doc.documentElement.setAttribute('valueType',self.valueType)
        doc.documentElement.appendChild(root)
        for goal,weight in self.goals.items():
            node = goal.__xml__().documentElement
            node.setAttribute('weight',str(weight))
            root.appendChild(node)
        return doc

    def parse(self,element):
        RecursiveAgent.parse(self,element)
        self.valueType = str(element.getAttribute('valueType'))
        if self.valueType == '':
            self.valueType = self.valueTypes[self.defaultValueType]
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE and \
                   child.tagName == 'goals':
                node = child.firstChild
                while node:
                    if node.nodeType == node.ELEMENT_NODE:
                        if str(node.getAttribute('type')):
                            goal = MinMaxGoal()
                        else:
                            goal = PWLGoal()
                        goal.parse(node)
                        if str(node.getAttribute('type')):
                            # Backward compatibility
                            if goal.direction == 'min':
                                goal = minGoal(goal.toKey())
                            else:
                                goal = maxGoal(goal.toKey())
                        weight = float(node.getAttribute('weight'))
                        self.goals[goal] = weight
                    node = node.nextSibling
            child = child.nextSibling
            
if __name__ == '__main__':
    from teamwork.test.agent.testRecursiveAgent import TestRecursiveAgentIraq
    from unittest import TestResult
    case = TestRecursiveAgentIraq('testValueAttack')
    result = TestResult()
    case(result)
    for failure in result.errors+result.failures:
        print failure[1]
