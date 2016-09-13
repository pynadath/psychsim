from __future__ import print_function
from psychsim.action import *
from psychsim.keys import *
from psychsim.probability import Distribution
from psychsim.pwl import *

import logging
import io

class Timeline:
    def __init__(self,world,state=None,actions=None,horizon=None):
        self.world = world
        if state is None:
            state = world.state
        self.state = state
        self.root = SimulationNode(world,state,actions=actions)
        self.root.probability = 1.
        self.root.conditional = 1.
        self.nodes = [[self.root]]
        self.reward = {}
        self.horizon = horizon

    def walk(self):
        self.root.walk()
        
    def ER(self,agent):
        if isinstance(agent,str):
            agent = self.world.agents[agent]
        if not self.reward.has_key(agent.name):
            self.reward[agent.name] = 0.
            for layer in self.nodes:
                for node in layer:
                    R = agent.reward(node.state)
                    self.reward[agent.name] += node.probability*R
        return self.reward[agent.name]
    
    def expand(self):
        """
        @return: C{True} iff another time step was added
        @rtype: bool
        """
        if self.horizon is None or len(self.nodes) < self.horizon:
            layer = []
            for node in self.nodes[-1]:
                node.expand()
                layer += node.children
            self.nodes.append(layer)
            return True
        else:
            return False

    def __len__(self):
        """
        @return: the number of steps into the future that this timeline extends
        @rtype: int
        """
        return len(self.nodes) - 1
    
class SimulationNode:
    def __init__(self,world,state=None,parent=None,actions=None,t=0):
        self.world = world
        if state is None:
            state = self.world.state
        self.state = state
        self.parents = []
        if parent:
            self.parents.append(parent)
        self.effects = {}
        self.children = None
        self.expanded = False
        self.actions = actions
        self.time = t
        self.decisions = {}
        self.reward = {}
        self.probability = None
        self.conditional = None

    def walk(self):
        print('Time: %d' % (self.time))
#        self.world.printState(self.state)
        if self.actions:
            print('\nActions:')
            print(self.actions)
            for decision in self.decisions.values():
                decision.explain()
        if self.children:
            for child in self.children:
                child.walk()
            
    def reward(self,agent,model=True):
        if not self.reward.has_key(agent):
            self.reward[agent] = self.world.agents[agent].reward(self.state)
        return self.reward[agent]
    
    def expand(self):
        if not self.expanded:
            # What's everybody doing?
            for name in self.world.next(self.state):
                agent = self.world.agents[name]
                if not self.actions is None and self.actions.has_key(name):
                    # We already know what you're doing
                    self.decisions[name] = Decision(agent,choice=self.actions[name])
                else:
                    # You need to figure out what you're doing
                    key = modelKey(name)
                    model = self.world.getModel(name,self.state)
                    beliefs = agent.getBelief(self.state,model)
                    horizon = agent.getAttribute('horizon',model) - self.time
                    horizon = max(0,horizon)
                    self.decisions[name] = agent.newDecide(belief=beliefs,horizon=horizon,model=model)
            # Generate distribution over possible joint actions across all agents
            self.actions = jointProb({name: self.decisions[name].getDecision() \
                                             for name in self.decisions.keys()})
            # Generate children
            assert self.children is None
            self.children = []
            for joint in self.actions.domain():
                effect = Effect(self.world,self.state,joint,self.actions[joint])
                after = effect.expand()
                self.effects[joint] = effect
                node = self.__class__(self.world,after,effect,None,self.time+1)
                node.conditional = self.actions[joint]
                node.probability = self.probability*node.conditional
                self.children.append(node)
                node.parents.append(self)
            self.expanded = True

class Effect:
    def __init__(self,world,state,actions,prob):
        self.world = world
        self.before = state
        self.actions = actions
        self.probability = prob
        self.after = None
        self.dynamics = {}
        self.sequence = []

    def expand(self):
        if self.after is None:
            self.after = self.before.__class__(empty=True)
            key2key = {key: set() for key in self.before.keyMap.keys()}
            key2sub = {key: set() for key in self.before.keyMap.keys()}
            sub2key = {substate: set() for substate in self.before.distributions.keys()}
            for layer in self.world.dependency.getEvaluation():
                for key in layer:
                    assert self.before.keyMap.has_key(key)
                    assert sub2key.has_key(self.before.keyMap[key])
                    if isTurnKey(key):
                        self.dynamics[key] = self.world.getTurnDynamics(key,self.actions)
                    else:
                        self.dynamics[key] = self.world.getDynamics(key,self.actions)
                    if self.dynamics[key]:
                        if len(self.dynamics[key]) > 1:
                            raise UserWarning
                        # What keys does this effect depend on?
                        for tree in self.dynamics[key]:
                            key2key[key] |= makePresent(tree.getKeysIn())
                            tree.makePresent()
#                        assert all([not isFuture(k) for k in key2key[key]])
                        # What subdistributions does this effect depend on?
                        for substate in self.before.substate([k for k in key2key[key]]):
                            key2sub[key].add(substate)
                            sub2key[substate].add(key)
                    else:
                        # No effect on this feature
                        key2key[key].add(key)
                        key2sub[key].add(self.before.keyMap[key])
                        sub2key[self.before.keyMap[key]].add(key)
            self.sequence.append(self.before)
            # Compute the resulting state
            for layer in self.world.dependency.getEvaluation():
                for key in layer:
                    if not self.after.keyMap.has_key(key):
                        # Haven't found a place for this feature yet
                        subs2add = set()
                        newSubs = set()
                        keys2add = set()
                        newKeys = {key}
                        # Add any other keys that are dependent (through common substates)
                        while len(newKeys) > 0 or len(newSubs) > 0:
                            subs2add |= newSubs
                            keys2add |= newKeys
                            newList = [key2sub[k] for k in newKeys]
                            newSubs = newSubs.union(*newList) - subs2add
                            newList = [sub2key[s] for s in newSubs]
                            newKeys = newKeys.union(*newList) - keys2add
                        # Compute new values for the interdependent keys
                        before = self.sequence[-1].collapse(subs2add)
                        after = before.__class__()
                        for oldVector in before.domain():
                            # For each joint world (across substates)
                            newDist = VectorDistribution({KeyedVector({CONSTANT: 1.}):1.})
                            for key in keys2add:
                                if self.dynamics[key]:
                                    newValue = None
                                    for tree in self.dynamics[key]:
                                        # Apply dynamics (serially if multiple)
                                        if newValue is None:
                                            newValue = tree[oldVector]*oldVector
                                        else:
                                            newValue = tree[newValue]*newValue
                                    if isinstance(newValue,KeyedVector):
                                        newDist.join(key,newValue[key])
                                    else:
                                        # Distribution over vectors
                                        newDist = newDist.merge(newValue)
                                else:
                                    # No dynamics, so value does not change
                                    newDist.join(key,oldVector[key])
                            # Add effects to cumulative distribution
                            for newVector in newDist.domain():
                                after.addProb(newVector,before[oldVector]*newDist[newVector])
                        # Add cumulative distribution to posterior state
                        substate = len(self.after.distributions)
                        self.after.distributions[substate] = after
                        for key in keys2add:
                            self.after.keyMap[key] = substate
        return self.after
            
class Decision:
    def __init__(self,agent,beliefs=None,model=True,choice=None,selection=None,horizon=None):
        self.agent = agent
        self.model = model
        self.beliefs = beliefs
        self.V = {}
        self.decision = choice
        self.policy = self.agent.getAttribute('policy',self.model)
        if selection is None:
            selection = self.agent.getAttribute('selection',self.model)
        self.selection = selection
        if horizon is None:
            horizon = self.agent.getAttribute('horizon',self.model)
        self.horizon = horizon

    def getDecision(self):
        """
        @return: a L{Distribution} over possible L{ActionSet} choices
        """
        if self.decision is None and self.policy:
            # Do we have a policy specified?
            choice = self.policy[belief.domain()[0]]
            if isinstance(choice,Action):
                choice = ActionSet([choice])
            if isinstance(choice,ActionSet):
                self.decision = choice
        if self.decision is None:
            actions = self.agent.getActions(self.beliefs)
            if len(actions) == 0:
                # Someone made a boo-boo because there is no legal action for this agent right now
                buf = io.StringIO()
                print('%s has no legal actions when believing:' % (self.agent.name),file=buf)
                self.agent.world.printState(self.beliefs,buf)
                msg = buf.getvalue()
                buf.close()
                logging.error(msg)
                self.decision = ActionSet()
            elif len(actions) == 1:
                # Only one action to choose from, so this isn't hard
                self.decision = iter(actions).next()
            else:
                best = None
                for choice in actions:
                    # Evaluate candidate action
                    self.V[choice] = Timeline(self.agent.world,self.beliefs,
                                              {self.agent.name: choice})
                    while len(self.V[choice]) < self.horizon:
                        # Expand projection up to horizon
                        self.V[choice].expand()
                    # Compare against best action(s) found so far
                    if best is None:
                        best = [choice]
                    elif self.V[choice].ER(self.agent) == self.V[best[0]].ER(self.agent):
                        best.append(choice)
                    elif self.V[choice].ER(self.agent) > self.V[best[0]].ER(self.agent):
                        best = [choice]
                # Make selection
                if self.selection == 'distribution':
                    # Softmax over value function
                    dist = {a: self.V[a].ER(self.agent) for a in self.V.keys()}
                    rationality = self.agent.getAttribute('rationality',self.model)
                    self.decision = Distribution(dist,rationality)
                elif len(best) == 1:
                    # There can be only one
                    self.decision = best[0]
                elif self.selection == 'consistent':
                    # Consistent tiebreaking
                    self.decision = sorted(best)[0]
                elif self.selection == 'random':
                    # Random tie-breaking
                    self.decision = random.sample(best,1)
                elif self.selection == 'uniform':
                    # Distribution over best choices
                    prob = 1./float(len(best))
                    self.decision = Distribution({a: prob for a in best})
                else:
                    logging.error('Unknown selection method: %s' % (self.selection))
                    # Fallback to 'consistent'
                    self.decision = sorted(best)[0]
        if isinstance(self.decision,ActionSet):
            self.decision = Distribution({self.decision: 1.})
        return self.decision

    def explain(self):
        if self.V:
            for action,timeline in self.V.items():
                print('\nConsidering:',action)
                timeline.walk()
                print('V_%s(%s) = %5.2f' % (self.agent.name,action,timeline.ER(self.agent)))
