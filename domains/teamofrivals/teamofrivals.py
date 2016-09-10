"""
Scenario for cooperative conquest game::

   usage: teamofrivals.py [-h] [-p] [-n NUMBER] [-1] [-f FILE] [-u] [-q]
                          [-m | -a]
                          [--additive | --restorative | --minimal | --none]
                          map

   positional arguments:
     map                   XML file containing world map

   optional arguments:
     -h, --help            show this help message and exit
     -p, --predict         print out predictions before stepping [default: False]
     -n NUMBER, --number NUMBER
                           Number of games to play [default: 1]
     -1, --single          stop execution after one round [default: False]
     -f FILE, --file FILE  name of scenario file [default: <map root>.psy]
     -u, --update          update scenario file [default: False]
     -q, --quiet           suppress all output [default: False]

   Decision Mode:
     -m, --manual          enter actions manually
     -a, --auto            agents choose actions autonomously [default]

   Resource Generation:
     --additive            Resources from all territories, unused ones kept
     --restorative         Resources from all territories, unused ones lost
                        [default]
     --minimal             Resources from initial territories, unused ones lost
     --none                Resources from winning only, unused ones kept

Input:
======
Map file
--------
XML file containing regions, specifying their individual parameters and neighbors. If omitted, the "value" attribute defaults to 5, as does the "occupants" attribute". The "owner" attribute indicates which player, 1-N, owns the territory at the start of the game. The default is 0, which indicates that the enemy side owns the territory::

   <map>
     <region name="Alaska" value="5" occupants="2" owner="0">
       <neighbor name="Northwest Territory"/>
       <neighbor name="Alberta"/>"
       <neighbor name="Kamchatka"/>"
     </region>
     <region>
   .
   .
   .

Output:
=======
Round number
------------
   Player: how many resources this player currently owns
   which territories this player currently owns

   Enemy: which territories are still currently owned by the enemy (number of defenders in each territory in parens)

   Player actions: which territories the player has chosen to invade (number of armies allocated in parens)

   Optional Predictions:
   Territory being invaded (how many resources are gained by the owner)
   The player(s) who would be the owner if the invasion is successful
   The probability that the invasion will be successful

Results (overall probability of outcome)
Territory being invaded: the result of the invasion (spinner result of individual invasion, *not* probability of individual outcome)

"""
from argparse import ArgumentParser
import csv
from datetime import datetime
import os.path
import random
import sys
import lxml.etree as ET
import time

from psychsim.pwl import *
from psychsim.world import *
from psychsim.agent import Agent
from psychsim.reward import *

class ResourceWorld(World):
    """
    @cvar nullAgent: string label that means none of the ResourceAgent members of this world
    @ivar carryOver: if C{True}, then unallocated resources carry over to next round (default is C{False})
    @type carryOver: bool
    @ivar floor: minimum number of resources that a player can have (default is no minimum)
    @type floor: int
    """
    nullAgent = '__none__'
    memory = False

    def __init__(self,xml=None,allocateVerb=None,allocationState=None,winnerState=None,floor=None):
        self.allocators = set()
        self.objects = []
        self.carryOver = True
        self.resourceName = None
        self.agentOrder = []
        World.__init__(self,xml)
        if xml is None:
            self.allocateVerb = allocateVerb
            self.allocationState = allocationState
            self.winnerState = winnerState

    def addAgent(self,agent):
        World.addAgent(self,agent)
        if isinstance(agent,ResourceAgent):
            if self.resourceName is None:
                self.resourceName = agent.resourceName
            self.allocators.add(agent)
            for obj in agent.objects:
                if self.agents.has_key(obj) and not self.agents[obj] in self.objects:
                    self.objects.append(self.agents[obj])
        else:
            for other in self.allocators:
                if agent.name in other.objects and not agent in self.objects:
                    self.objects.append(agent)

    def getResources(self,state=None):
        """
        @return: a table of amount of resources owned by each player
        @rtype: strS{->}int
        """
        if state is None:
            state = self.state[None]
        resources = {}
        for agent in self.agents.values():
            if isinstance(agent,ResourceAgent):
                resources[agent.name] = self.getState(agent.name,agent.resourceName).expectation()
        return resources

    def getOwnership(self,state=None):
        """
        @return: a table of territories owned by each agent
        @rtype: strS{->}set(str)
        """
        if state is None:
            state = self.state[None]
        ownership = {}
        # Hacky way to figure out what can be owned
        for agent in self.agents.values():
            if isinstance(agent,ResourceAgent):
                objects = agent.objects
                break
        for obj in objects:
            # Who owns it?
            owner = self.getState(obj,'owner',state)
            assert len(owner) == 1
            owner = owner.domain()[0]
            # Add to table
            try:
                ownership[owner].add(obj)
            except KeyError:
                ownership[owner] = {obj}
        return ownership

    def getTotalValue(self,feature,state=None):
        """
        @param feature: the name of the state feature containing the value to be totaled
        @type feature: str
        @return: a table of total value of territories owned by each agent
        @rtype: strS{->}int
        """
        if state is None:
            state = self.state[None]
        result = {}
        # Hacky way to figure out what can be owned
        for agent in self.agents.values():
            if isinstance(agent,ResourceAgent):
                objects = agent.objects
                break
        for agent in self.agents.values():
            if isinstance(agent,ResourceAgent):
                # This is a player, make sure it has an entry
                if not result.has_key(agent.name):
                    result[agent.name] = 0
            elif agent.name in objects:
                # This is something owned, add its value to the owner's entry
                owner = self.getState(agent.name,'owner',state)
                value = self.getState(agent.name,feature,state)
                assert len(owner) == 1
                owner = owner.domain()[0]
                try:
                    result[owner] += value.expectation()
                except KeyError:
                    result[owner] = value.expectation()
        return result
            
    def predictResult(self,actions):
        """
        @param actions: the (sub)set of actions to predict the results of
        @type actions: L{ActionSet}
        @return: a dictionary of predictions in dictionary form for each object included in the action:
           - leader: prediction of which allocator would own the object, if successful
           - winner: prediction of who owns the object, including possibility of being unsuccessful
        @rtype: str{S->}str{S->}L{Distribution}(str)
        """
        # Collect targets
        objects = {}
        for name,action in actions.items():
            for atom in action:
                try:
                    objects[atom['object']].add(atom)
                except KeyError:
                    objects[atom['object']] = set([atom])
        for obj in objects.keys():
            objects[obj] = {'actions': ActionSet(objects[obj])}
            keys = {stateKey(obj,'invader'),stateKey(obj,'owner')}
            outcomes = self.step(objects[obj]['actions'],real=False,keys=keys)
            assert len(outcomes) == 1
            objects[obj]['leader'] = self.getState(obj,self.winnerState,outcomes[0]['new'])
            objects[obj]['winner'] = self.getState(obj,'owner',outcomes[0]['new'])
        return objects

    def deltaOrder(self,actions,vector):
        return None

    def next(self,vector=None):
        if vector is None:
            assert len(self.state[None]) == 1,'Ambiguous state vector'
            vector = self.state[None].domain()[0]
        if self.getValue('phase',vector) == 'generate':
            return [o.name for o in self.objects]
        else:
            return [name for name in self.agents.keys() if isinstance(self.agents[name],ResourceAgent)]

    def getDynamics(self,key,action,state=None):
        if isTurnKey(key):
            # Caching doesn't work too well with partial prediction
            return []
        elif isinstance(action,ActionSet) or isinstance(action,list):
            if key[-len(self.allocationState):] == self.allocationState:
                # Figure out the resulting allocation
                total = 0
                for atom in action:
                    if atom['verb'] == self.allocateVerb and \
                            key[:len(atom['object'])] == atom['object']:
                        # Someone is allocating resources relevant to this state feature
                        total += atom['amount']
                if total > 0:
                    return [makeTree(setToConstantMatrix(key,total))]
                else:
                    return []
            elif key[-len(self.resourceName):] == self.resourceName:
                # Figure out player resources
                if self.getValue('phase',state) == 'generate':
                    player = key[:-(len(self.resourceName)+3)]
                    total = 5 # Minimum value
                    for obj in self.objects:
                        if self.getValue(stateKey(obj,'owner'),state) == player and \
                                self.getValue(stateKey(obj,'invader'),state) == player:
                            # I just won this territory
                            total += self.getValue(stateKey(obj,'value'),state)
                    tree = makeTree(incrementMatrix(key,total))
                    return [tree.desymbolize(self.symbols)]
                else:
                    trees = []
                    for atom in action:
                        if atom['verb'] == self.allocateVerb and \
                                key[:len(atom['subject'])] == atom['subject']:
                            # The relevant player is allocating resources
                            if self.carryOver:
                                trees.append(makeTree(incrementMatrix(key,-atom['amount'])))
                            else:
                                trees.append(makeTree(setToConstantMatrix(key,0)))
                    return trees
            elif key[-5:] == 'owner':
                # Figure out the probability of winning
                total = 0
                for atom in action:
                    if atom['verb'] == self.allocateVerb and \
                            key[:len(atom['object'])] == atom['object']:
                        # Someone is allocating resources relevant to this state feature
                        obj = atom['object']
                        total += atom['amount']
                if total == 0:
                    # No one touching this object
                    return []
                else:
                    # Find ratio of invaders to defenders (hack warning!)
                    if state is None:
                        state = self.state[None].domain()[0]
                    assert len(self.state[None]) == 1,'Unable to hack dynamics in uncertain states'
                    denominator = total + state[stateKey(obj,'occupants')]
                    winning = float(total)/float(denominator)
                    return [makeTree({'distribution': 
                                      [(setToFeatureMatrix(key,stateKey(obj,
                                                                        self.winnerState)),winning),
                                       (noChangeMatrix(key),1.-winning)]})]
            elif self.winnerState and key[-len(self.winnerState):] == self.winnerState:
                # Figure out who's allocating the most
                amounts = {}
                for atom in action:
                    if atom['verb'] == self.allocateVerb and \
                            key[:len(atom['object'])] == atom['object']:
                        # Someone is allocating resources relevant to this state feature
                        try:
                            amounts[atom['amount']].append(atom['subject'])
                        except KeyError:
                            amounts[atom['amount']] = [atom['subject']]
                if len(amounts) > 0:
                    winners = amounts[max(amounts.keys())]
                    if len(winners) == 1:
                        # Phew, unique
                        return [makeTree(setToConstantMatrix(key,winners[0]).desymbolize(self.symbols))]
                    else:
                        # Choose randomly among them
                        tree = makeTree({'distribution': \
                                         [(setToConstantMatrix(key,winner),1./float(len(winners))) \
                                              for winner in winners]})
                        return[tree.desymbolize(self.symbols)]
                else:
                    # Here we go hacking again
                    if state is None:
                        assert len(self.state[None]) == 1,'Unable to hack dynamics in uncertain states'
                        state = self.state[None].domain()[0]
                    if self.getValue('phase',state) == 'allocate':
                        # No one allocating to this object, so no possible winner
                        tree = makeTree(setToConstantMatrix(key,self.nullAgent))
                        return [tree.desymbolize(self.symbols)]
                    else:
                        return []
            elif key == stateKey(None,'phase'):
                for atom in action:
                    if atom['verb'] == self.allocateVerb:
                        # If we allocate, then the phase becomes generate
                        tree = makeTree(setToConstantMatrix(key,'generate'))
                        return [tree.desymbolize(self.symbols)]
                    elif atom['verb'] == 'generate':
                        # If we generate, then the phase becomes allocate
                        tree = makeTree(setToConstantMatrix(key,'allocate'))
                        return [tree.desymbolize(self.symbols)]
                else:
                    # No actions? Must be that no one allocated
                    tree = makeTree(setToConstantMatrix(key,'generate'))
                    return [tree.desymbolize(self.symbols)]
            elif key[-9:] == 'territory':
                if state is None:
                    assert len(self.state[None]) == 1,'Unable to hack dynamics in uncertain states'
                    state = self.state[None].domain()[0]
                if self.getValue('phase',state) == 'generate':#CVM changed world to self
                    player = key[:-12]
                    count = len([atom for atom in action \
                                     if self.getValue(stateKey(atom['subject'],'owner'),state) == player])
                    return [makeTree(setToConstantMatrix(key,count))]
                else:
                    return []
            elif key[-5:] == 'value' and isinstance(self.agents[key[:-8]],ResourceAgent):
                if state is None:
                    assert len(self.state[None]) == 1,'Unable to hack dynamics in uncertain states'
                    state = self.state[None].domain()[0]
                if self.getValue('phase',state) == 'generate':#CVM changed world to self
                    player = key[:-8]
                    count = sum([self.getValue(stateKey(atom['subject'],'value')) for atom in action \
                                     if self.getValue(stateKey(atom['subject'],'owner'),state) == player])
                    return [makeTree(setToConstantMatrix(key,count))]
                else:
                    return []
        dynamics = World.getDynamics(self,key,action,state)
        return dynamics

    def __xml__(self):
        doc = World.__xml__(self)
        doc.documentElement.setAttribute('verb',self.allocateVerb)
        doc.documentElement.setAttribute('allocation',self.allocationState)
        doc.documentElement.setAttribute('winner',self.winnerState)
        for obj in self.objects:
            node = doc.createElement('object')
            node.setAttribute('name',obj.name)
            doc.documentElement.appendChild(node)
        return doc

    def parse(self,element):
        World.parse(self,element,ResourceAgent)
        self.allocateVerb = str(element.getAttribute('verb'))
        self.allocationState = str(element.getAttribute('allocation'))
        self.winnerState = str(element.getAttribute('winner'))
        node = element.firstChild
        self.objects = []
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'object':
                    self.objects.append(self.agents[str(node.getAttribute('name'))])
            node = node.nextSibling

class ResourceAgent(Agent):
    """
    @ivar allocateAll: if C{True}, then agent cannot leave resources unallocated (default is C{False})
    """
    def __init__(self,name,resource=None,verb=None,objects=None):
        Agent.__init__(self,name)
        if not resource is None:
            self.resourceName = resource
            self.verbName = verb
            self.objects = objects
            self.objectLegality = {}
            for obj in objects:
                self.objectLegality[obj] = makeTree(True)
        self.allocateAll = False

    def getActions(self,vector):
        targets = []
        resources = self.world.getValue(stateKey(self.name,self.resourceName),vector)
        for obj in self.legalObjects(vector):
            targets.append(obj)
        actions = self.getCombos(targets,resources)
        return Agent.getActions(self,vector,actions).union(Agent.getActions(self,vector))

    def hasAction(self,atom):
        if atom['subject'] == self.name and atom['verb'] == self.verbName and \
                atom['object'] in self.objects:
            return True
        else:
            return Agent.hasAction(self,atom)

    def getCombos(self,targets,resources):
        if len(targets) == 0:
            return set([ActionSet()])
        elif len(targets) == 1 and self.allocateAll:
            if resources > 0:
                # Have to allocate remaining resources
                return set([ActionSet([Action({'subject': self.name,
                                               'verb': self.verbName,
                                               'object': targets[0],
                                               'amount': resources})])])
            else:
                # Nothing left to allocate
                return set([ActionSet()])
        else:
            target = targets[0]
            # If we don't consider this target, what other actions can we do?
            actions = self.getCombos(targets[1:],resources)
            # If we do consider this target, what other actions can we do?
            for amount in range(resources):
                action = Action({'subject': self.name,
                                 'verb': self.verbName,
                                 'object': target,
                                 'amount': amount+1})
                remaining = self.getCombos(targets[1:],resources-amount-1)
                actions = actions.union({partial.union({action}) for partial in remaining})
            return actions

    def sampleAction(self,vector,numTargets=0,minResources=0,joint={}):
        """
        @param numTargets: maximum number of targets for allocation. 0 means no limit (default is 0)
        @param minResources: minimum number of resources to leave unallocated (default is 0)
        @param joint: current joint action with which to coordinate
        Generates a random (legal) action for this agent in the given world
        """
        if isinstance(vector,VectorDistribution):
            assert len(vector) == 1,'Unable to sample actions in an uncertain world'
            vector = vector.domain()[0]
        # How many resources do I have to allocate?
        resources = vector[stateKey(self.name,self.resourceName)]
        if resources > minResources:
            resources -= minResources
        else:
            # Less than minimal number, let's not divide them up
            numTargets = 1
        # All legal objects are possible targets
        targets = Distribution()
        for obj in self.legalObjects(vector):
            targets[obj] = float(vector[stateKey(obj,'occupants')])
        # All targets chosen by teammates are more likely targets
        for action in joint.values():
            for atom in action:
                targets[atom['object']] /= 2.
        targets.normalize()
        while len(targets) > numTargets:
            element = targets.sample()
            del targets[element]
            targets.normalize()
        targets = targets.domain()
        actions = set()
        for target in targets:
            if target == targets[-1]:
                # Last target gets all remaining resources
                if isinstance(resources,float):
                    amount = int(resources+0.5)
                else:
                    amount = resources
            else:
                amount = random.randint(0,resources)
            if amount > 0:
                action = Action({'subject': self.name,
                                 'verb': self.verbName,
                                 'object': target,
                                 'amount': amount})
                actions.add(action)
                resources -= amount
        return ActionSet(actions)

    def legalObjects(self,vector):
        if isinstance(vector,VectorDistribution):
            assert len(vector.domain()) == 1,'Unable to determine legal objects in an uncertain world'
            vector = vector.domain()[0]
        return [obj for obj in self.objects if self.objectLegality[obj][vector]]

    def singletonActions(self,vector):
        """
        Generates all possible single-country invasions I can do in the given world
        """
        resources = self.world.getValue(stateKey(self.name,self.resourceName),vector)
        return [ActionSet([Action({'subject': self.name,
                                   'verb': self.verbName,
                                   'object': target,
                                   'amount': resources})]) for target in self.legalObjects(vector)]

    def __xml__(self):
        doc = Agent.__xml__(self)
        doc.documentElement.setAttribute('resource',self.resourceName)
        doc.documentElement.setAttribute('verb',self.verbName)
        for obj in self.objects:
            node = doc.createElement('object')
            node.appendChild(doc.createTextNode(obj))
            doc.documentElement.appendChild(node)
        for obj,tree in self.objectLegality.items():
            node = doc.createElement('objectlegal')
            node.setAttribute('object',obj)
            node.appendChild(tree.__xml__().documentElement)
            doc.documentElement.appendChild(node)
        return doc

    def parse(self,element):
        Agent.parse(self,element)
        self.resourceName = str(element.getAttribute('resource'))
        self.verbName = str(element.getAttribute('verb'))
        self.objects = []
        self.objectLegality = {}
        node = element.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                if node.tagName == 'object':
                    self.objects.append(str(node.firstChild.data).strip())
                elif node.tagName == 'objectlegal':
                    obj = str(node.getAttribute('object'))
                    subnode = node.firstChild
                    while subnode:
                        if subnode.nodeType == subnode.ELEMENT_NODE:
                            tree = KeyedTree(subnode)
                            self.objectLegality[obj] = tree
                            break
                        subnode = subnode.nextSibling
            node = node.nextSibling

    @staticmethod
    def isXML(element):
        if not Agent.isXML(element):
            return False
        return len(element.getAttribute('resource')) > 0

def closeRegions(regions):
    """
    Makes the links symmetric in the given region map
    @type regions: strS{->}set(str)
    """
    for orig,table in regions.items():
        for dest in table['neighbors']:
            if not regions.has_key(dest):
                regions[dest] = {'neighbors': set(),
                                 'value': 4}
            regions[dest]['neighbors'].add(orig)
    return regions

def powerSet(limit):
    """
    @return: a list of all possible combinations of numbers in the range of 1 to the given limit
    @rtype: set
    """
    old = [[]]
    for i in range(limit):
        new = []
        for partial in old:
            new.append(partial+[i+1])
            new.append(partial)
        old = new
    return old

def createWorld(numPlayers,regionTable,starts,generation='additive',maxResources=32,incentive='value'):
    """
    @param numPlayers: number of players in the game
    @type numPlayers: int
    @param regionTable: a table of regions, indexed by name
    @param starts: a list of starting regions, one for each player
    @param maxResources: the maximum number of resources a player may have
    @type maxResources: int
    @param incentive: the type of reward for the agents (default is "value" for all)
       - B{value}: reward for cumulative value of individually owned territories
       - B{territory}: reward for number of individually owned territories
       - B{team}: reward for number of team owned territories
    @type: str (applied to all) or str[] (individually specified reward)
    """
    if isinstance(incentive,str):
        incentive = [incentive for player in range(numPlayers)]
    world = ResourceWorld(allocateVerb='allocate',allocationState='invaders',winnerState='invader')

    # Create regions
    regions = set()
    for name,table in regionTable.items():
        region = Agent(name)
        world.addAgent(region)
        regions.add(region)

        world.defineState(name,'occupants',int,lo=0,hi=maxResources,
                          description='Number of resources in %s' % (region))
        region.setState('occupants',table['occupants'] if table.has_key('occupants') else table['value'])

        world.defineState(name,'value',int,lo=0,hi=maxResources,
                          description='Number of resources generated by %s' % (region))
        region.setState('value',table['value'])

        world.defineState(name,'invaders',int,lo=0,hi=numPlayers*maxResources,
                         description='Number of resources invading %s' % (region))
        region.setState('invaders',0)
        world.dynamics[stateKey(region.name,'invaders')] = True

    # Create agents for human players
    players = []
    for player in range(numPlayers):
        players.append(ResourceAgent('Player%d' % (player+1),'resources','allocate',
                                     [region.name for region in regions]))
        world.addAgent(players[player])
        players[player].allocateAll = True

        world.defineState(players[player].name,'resources',int,lo=0,hi=maxResources,
                          description='Number of total resources owned by %s' % (players[player].name),
                          combinator='*')
        players[player].setState('resources',0)

        world.defineState(players[player].name,'territory',int,lo=0,hi=len(regionTable),
                          combinator='*',
                          description='Number of territories owned by %s' % (players[player].name))
        players[player].setState('territory',0)
        world.dynamics[stateKey(players[player].name,'territory')] = True
        world.defineState(players[player].name,'value',int,lo=0,
                          hi=sum([region['value'] for region in regionTable.values()]),
                          combinator='*',
                          description='Total vaue of territories owned by %s' % (players[player].name))
        players[player].setState('value',0)
        world.dynamics[stateKey(players[player].name,'value')] = True
    # Reward functions
    for player in range(numPlayers):
        if incentive[player] == 'team':
            for other in range(numPlayers):
                players[player].setReward(maximizeFeature(stateKey(players[other].name,'territory')),1.)
        elif incentive[player] == 'territory':
            players[player].setReward(maximizeFeature(stateKey(players[player].name,'territory')),1.)
        else:
            # Assume "value"
            players[player].setReward(maximizeFeature(stateKey(players[player].name,'value')),1.)
        players[player].setAttribute('rationality',10.)
        players[player].setAttribute('discount',-10.)

    # Create agent for "enemy"
    enemy = Agent('Enemy')
    world.addAgent(enemy)

    owners = world.agents.keys()

    for region in regions:
        world.defineState(region.name,'owner',set,set(owners),
                          description='Name of owner of %s' % (region))
        region.setState('owner',enemy.name)

        world.defineState(region.name,'invader',set,set(owners)-{enemy.name}|{world.nullAgent},
                          description='Name of invader who will own %s if successful' % (region))
        # try:
        #     index = starts.index(region.name)
        #     region.setState('invader','Player%d' % (index+1))
        # except ValueError:
        region.setState('invader',world.nullAgent)
        world.dynamics[stateKey(region.name,'invader')] = True

    # Set players' initial territories
    world.objects.sort(lambda x,y: cmp(x.name,y.name))
    for index in range(numPlayers):
        region = world.agents[starts[index]]
        region.setState('owner',players[index].name)
        world.objects.remove(region)
        world.objects.append(region)
        # Players can invade only if enemy owns it and they (or teammate) own a neighboring country
        for region in regions:
            tree = False
            for neighbor in regionTable[region.name]['neighbors']:
                tree = {'if': equalRow(stateKey(neighbor,'owner'),enemy.name),
                        True: tree,
                        False: True}
            tree = makeTree({'if': equalRow(stateKey(region.name,'owner'),enemy.name),
                             True: tree,
                             False: False})
            players[index].objectLegality[region.name] = tree.desymbolize(world.symbols)

    # Create region "action"
    for region in regions:
        region.addAction({'verb': 'generate'})
    
    # Set order of play
    world.setOrder([set([region.name for region in world.objects]),set([player.name for player in players])])

    # Winner determination
    for region in regions:
        # Determine the owner after determining who's invading
        world.addDependency(stateKey(region.name,'owner'),stateKey(region.name,'invader'))
        # Determine the winner of the invasion
        owner = stateKey(region.name,'owner')
        world.dynamics[owner] = True
        invader = stateKey(region.name,'invader')
        defenders = stateKey(region.name,'occupants')
        invaders = stateKey(region.name,'invaders')
        value = stateKey(region.name,'value')
        for player in players:
            resources = stateKey(player.name,'resources')
            world.dynamics[resources] = True
#             # Determine how many resources lost
#             action = Action({'subject': player.name,'verb': 'allocate','object': region.name})
# #            world.addDependency(resources,invader)
#             if generation == 'additive': # or generation == 'none':
#                 # Lose only those resources allocated
#                 tree = makeTree(incrementMatrix(resources,'-%s' % (actionKey('amount'))))
#             else:
#                 # Lose all resources
#                 tree = makeTree(setToConstantMatrix(resources,0))
# #            world.setDynamics(resources,action,tree)
#             # Regain resources from owned territories
#             action = Action({'subject': region.name,'verb': 'generate'})
#             if generation == 'additive' or generation == 'restorative':
#                 tree = makeTree({'if': equalRow(owner,player.name),
#                                  True: addFeatureMatrix(resources,value),
#                                  False: None})
#             elif generation == 'minimal':
#                 if region is world.agents[starts[int(player.name[-1])-1]]:
#                     # Get resources from home base (repeated)
#                     tree = makeTree({'if': equalRow(owner,player.name),
#                                      True: addFeatureMatrix(resources,value),
#                                      False: None})
#                 else:
#                     # And any new winnings (one-time)
#                     tree = makeTree({'if': equalRow(owner,player.name),
#                                      True: {'if': equalFeatureRow(owner,invader),
#                                             True: addFeatureMatrix(resources,value),
#                                             False: None},
#                                      False: None})
#             elif generation is 'none':
#                 if region is world.agents[starts[int(player.name[-1])-1]]:
#                     # Get resources from home base if below threshold
#                     tree = makeTree(addFeatureMatrix(resources,value))
# #                    tree = makeTree({'if': greaterThanRow(resources,value),
# #                                     True: None,
# #                                     False: setToFeatureMatrix(resources,value)})
#                 else:
#                     tree = makeTree({'if': equalRow(owner,player.name),
#                                      True: {'if': equalFeatureRow(owner,invader),
#                                             True: addFeatureMatrix(resources,value),
#                                             False: None},
#                                      False: None})
#             world.setDynamics(resources,action,tree)
    # The game has two phases: generating resources and allocating resources
    world.defineState(None,'phase',list,['generate','allocate'],combinator='*',
                      description='The current phase of the game')
    world.setState(None,'phase','generate')
    key = stateKey(None,'phase')
    world.dynamics[key] = True

    # Game ends when territory is all won
    tree = {'if': equalRow(key,'allocate'),
            True: True,
            False: False}
    for region in regions:
        tree = {'if': equalRow(stateKey(region.name,'owner'),enemy.name),
                True: False,
                False: tree}
    world.addTermination(makeTree(tree))
    # Or if nobody has any resources
    vector = KeyedVector()
    for player in players:
        vector[stateKey(player.name,'resources')] = 1.
    tree = {'if': equalRow(stateKey(None,'phase'),'allocate'),
            True: {'if': KeyedPlane(vector,0.5),
                   True: False, False: True},
            False: False}
    world.addTermination(makeTree(tree))

    # Keep track of which round it is
    world.defineState(None,'round',int,description='The current round of the game')
    world.setState(None,'round',0)
    action = Action({'subject': list(regions)[0].name,
                     'verb': 'generate'})
    key = stateKey(None,'round')
    world.setDynamics(key,action,makeTree(incrementMatrix(key,1)))
    return world

def readLogs(world,root):
    ignore = {'getPlayerRegionOwnershipInfo','getPrediction','getCommitCount',
              'updateCommitFlagToMinusOne','getCompletedSurveyCount','inGameSurvey',
              'getActionsForCurrentTurn','logMessage','updateCommitFlagToNull'}
    game = {'users': [],'states': [], 'moves': []}
    timeline = []
    game['timeline'] = timeline
    for player in range(1,5):
        with open('%s_%d_logs.csv' % (root,player),'r') as csvfile:
            turn = 0
            reader = csv.DictReader(csvfile)
            for row in reader:
                msg = row['spl_message']
                elements = msg.split('|')
                assert len(elements) > 1
                now = datetime.strptime(elements[0],'%Y-%m-%d %H:%M:%S.%f')
                if elements[1] in ignore:
                    continue
                elif elements[1] == 'joinGame':
                    entry = int(elements[2].split()[2])
                    game['users'].append(entry)
                elif elements[1] == 'preGameSurvey':
                    entry = None
                elif elements[1] == 'pollStatus':
                    if not 'PlayerRegionOwnershipInfo' in elements[2]:
                        continue
                    if player == 1:
                        game['states'].append({})
                        game['moves'].append({i: {} for i in range(1,5)})
                    if not elements[2].split()[-1] in ['wait','=']:
                        state = {'resources': {}, 'territories': {},'ownership': {}}
                        for element in elements[3:7]:
                            field = element.split(':')
                            try:
                                state['resources'][int(field[0][-1])] = int(field[1])
                            except ValueError:
                                state['resources'][int(field[0][-1])] = int(field[1].split()[0])
                        for element in elements[7:49]:
                            field = element.split(',')
                            territory = field[0]
                            if field[3][:5] == 'Enemy':
                                owner = 0
                            else:
                                owner = int(field[3][6])
                            state['territories'][territory] = owner
                            if not state['ownership'].has_key(owner):
                                state['ownership'][owner] = []
                            state['ownership'][owner].append(territory)
                        if turn >= len(game['states']):
                            print 'Extra turn %d for player %d' % (turn,player)
                        else:
                            if game['states'][turn]:
                                if game['states'][turn] != state:
                                    print 'Discrepancy for player %d on turn %d' % (player,turn)
                            else:
                                game['states'][turn].update(state)
                    turn += 1
                    entry = turn
                elif elements[1] == 'actionTaken':
                    subelements = elements[2].split()
                    if subelements[-1] == 'armies':
                        territory = ' '.join(subelements[3:-3])
                        resources = int(subelements[-2])
                        entry = '%s,%d' % (territory,resources)
                        try:
                            game['moves'][turn-1][player][territory] = resources
                        except IndexError:
                            print 'Illegal move %d for player %d' % (turn,player)
                    else:
                        continue
                elif elements[1] == 'commitTurn':
                    entry = None
                else:
                    raise ValueError,'Unknown message type: %s' % (elements[1])
                timeline.append((now,player,elements[1],entry))
    timeline.sort()
    return game

def analyzeGame(world,game,gameID):
    regions = sorted(game['states'][0]['territories'].keys())
    fields = ['gameID','turn','content']+regions
    flow = []
    collaborations = 0
    solos = 0
    moves = 0
    outcomes = {'wins': 0, 'losses': 0}
    favorables = {'wins': 0,'losses': 0}
    coinflips = {'wins': 0,'losses': 0}
    unfavorables = {'wins': 0,'losses': 0}
    for index in range(len(game['moves'])):
        state = game['states'][index]
        record = {'gameID': gameID,
                  'turn': index,
                  'content': 'ownership',
                  }
        for region in regions:
            record[region] = state['territories'][region]
        if index > 0:
            # Check what the outcome of previous moves was
            for region,prob in flow[-1]['win'].items():
                pct = round(100.*prob)
                if record[region] == 0:
                    # Loss
                    outcomes['losses'] += 1
                    if pct > 50:
                        favorables['losses'] += 1
                    elif pct == 50:
                        coinflips['losses'] += 1
                    else:
                        unfavorables['losses'] += 1
                else:
                    # Win
                    outcomes['wins'] += 1
                    if pct > 50:
                        favorables['wins'] += 1
                    elif pct == 50:
                        coinflips['wins'] += 1
                    else:
                        unfavorables['wins'] += 1
        flow.append(record)
        record = {'gameID': gameID,
                  'turn': index+1,
                  'content': 'allocation',
                  'win': {}}
        for region in regions:
            record[region] = []
            invaders = 0
            leader = 0
            for player,allocation in game['moves'][index].items():
                try:
                    record[region].append('%d' % (allocation[region]))
                    if allocation[region] > 0:
                        invaders += allocation[region]
                        leader = max(leader,allocation[region])
                        moves += 1
                except KeyError:
                    record[region].append('0')
            assert len(record[region]) == 4
            if record[region].count('0') == 3:
                solos += 1
            else:
                collaborations += 4-record[region].count('0')
            record[region] = '|'.join(record[region])
            if invaders > 0:
                # Compute win probability
                defenders = world.state[None].domain()[0][stateKey(region,'occupants')]
                record['win'][region] = float(invaders)/float(invaders+defenders)
        flow.append(record)
    print '%2d Turns' % (len(game['moves'])-1)
    print '%2d/42 Territories Won' % (len([region for region in regions if game['states'][-1]['territories'][region] != 0]))
    print '%2d/%2d Moves are Collaborative' % (collaborations,moves)
    print '%2d/%2d Invasions Won' % (outcomes['wins'],sum(outcomes.values()))
    print '%2d/%2d Favorable invasions won' % (favorables['wins'],sum(favorables.values()))
    print '%2d/%2d 50-50 invasions won' % (coinflips['wins'],sum(coinflips.values()))
    print '%2d/%2d Unfavorable invasions won' % (unfavorables['wins'],sum(unfavorables.values()))
    return fields,flow[:-1]

def mapSave(regions,filename):
    """
    Saves a region map to an XML file
    """
    root = ET.Element('map')
    for name,table in regions.items():
        node = ET.SubElement(root,'region')
        node.set('name',name)
        if table.has_key('value'): node.set('value',str(table['value']))
        if table.has_key('occupants'): node.set('occupants',str(table['occupants']))
        node.set('owner',str(table['owner']))
        for neighbor in table['neighbors']:
            subnode = ET.SubElement(node,'neighbor')
            subnode.set('name',neighbor)
    tree = ET.ElementTree(root)
    tree.write(filename,pretty_print=True)
    return tree

def mapLoad(filename,close=False):
    """
    Parses an XML file representing a region map
    @param close: if C{True}, then fill in missing links and regions (default is False)
    @type close: bool
    """
    tree = ET.parse(filename)
    regions = {}
    starts = []
    for node in tree.getroot().getchildren():
        assert node.tag == 'region'
        name = str(node.get('name'))
        assert not regions.has_key(name),'Duplicate region name: %s' % (name)
        regions[name] = {'value': int(node.get('value','5')),
                         'owner': int(node.get('owner','0')),
                         'occupants': int(node.get('occupants','5')),
                         'neighbors': set()}
        for subnode in node.getchildren():
            assert subnode.tag == 'neighbor'
            regions[name]['neighbors'].add(str(subnode.get('name')))
        if regions[name]['owner'] > 0:
            starts.append((regions[name]['owner'],name))
    starts = [entry[1] for entry in sorted(starts)]
    if close:
        closeRegions(regions)
    return regions,starts

def createAsia():
    # Set of borders in Asia in Risk (only one direction included)
    asia = {'Afghanistan': {'neighbors': {'Ural','China','India','Middle East'},
                            'value': 4,'occupants': 6},
            'China': {'neighbors': {'India','Ural','Siberia','Mongolia','Siam'},
                      'value': 8,'occupants': 16},
            'India': {'neighbors': {'Middle East','Siam'},
                      'value': 6,'occupants': 12},
            'Irkutsk': {'neighbors': {'Siberia','Yakutsk','Kamchatka','Mongolia'},
                        'value': 4},
            'Japan': {'neighbors': {'Kamchatka','Mongolia'},
                      'value': 4, 'occupants': 10},
            'Kamchatka': {'neighbors': {'Yakutsk','Mongolia'},
                          'value': 4},
            'Mongolia': {'neighbors': {'Siberia'},
                         'value': 4},
            'Siberia': {'neighbors': {'Ural','Yakutsk'},
                        'value': 4}
            }
    # Fills out the transitive closure so that all neighbor links are bi-directional
    closeRegions(asia)
    starts = ['Ural','Middle East','Kamchatka','Siam']
    for region,table in asia.items():
        try:
            table['owner'] = starts.index(region)+1
        except ValueError:
            table['owner'] = 0
    mapSave(asia,'asia.xml')
    return asia

def counts2incentives(counts):
    """
    @return: a list of incentive specs that matches the given counts
    """
    return ['value' for i in range(counts['value'])] + \
        ['territory' for i in range(counts['individual'])] + \
        ['team' for i in range(counts['team'])]

if __name__ == '__main__':
    ######
    # Parse command-line arguments
    ######

    parser = ArgumentParser()
    # Positional argument that loads a map file
    parser.add_argument('map',help='XML file containing world map')

    # Optional argument that prints out predictions as well
    parser.add_argument('-p','--predict',action='store_true',
                      help='print out predictions before stepping [default: %(default)s]')
    # Optional argument that sets the initial number of games to play 
    parser.add_argument('-n','--number',action='store',
                        type=int,default=1,
                        help='Number of games to play [default: %(default)s]')
    # Optional argument that stops execution after 1 round
    parser.add_argument('-1','--single',action='store_true',
                      help='stop execution after one round [default: %(default)s]')
    # Optional argument that specifies the name of the scenario file
    parser.add_argument('-f','--file',help='name of scenario file [default: <map root>.psy]')
    # Optional argument that specifies the root of the log file to replay
    parser.add_argument('-r','--replay',help='root of log files')
    # Optional argument that specifies the name of the log file
    parser.add_argument('-l','--log',help='name of log file [default: <map root>.csv]')
    # Optional argument that indicates game execution should lead to update of scenario file
    parser.add_argument('-u','--update',action='store_true',default=False,
                        help='update scenario file [default: %(default)s]')

    # Optional argument that suppresses all output
    parser.add_argument('-q','--quiet',action='store_true',
                        help='suppress all output [default: %(default)s]')

    # Optional arguments that determine the agent selection mode
    label = parser.add_argument_group('Decision Mode')
    group = label.add_mutually_exclusive_group()
    group.add_argument('-m','--manual',action='store_true',
                        help='enter actions manually')
    group.add_argument('-a','--auto',action='store_false',
                        dest='manual',
                        help='agents choose actions autonomously [default]')

    # Optional arguments that determine the agent selection mode
    label = parser.add_argument_group('Agent Rewards')
    label.add_argument('-v','--value',type=int,default=0,
                       help='Value of individually owned territories')
    label.add_argument('-i','--individual',type=int,default=0,
                       help='Number of individually owned territories')
    label.add_argument('-t','--team',type=int,default=0,
                       help='Number of team owned territories')

    # Optional arguments that select the resource generation model
    label = parser.add_argument_group('Resource Generation')
    group = label.add_mutually_exclusive_group()
    group.add_argument('--additive',action='store_const',const='additive',dest='generation',
                       help='Resources from all territories, unused ones kept')
    group.add_argument('--restorative',action='store_const',const='restorative',dest='generation',
                       help='Resources from all territories, unused ones lost')
    group.add_argument('--minimal',action='store_const',const='minimal',dest='generation',
                       help='Resources from initial territories, unused ones lost')
    group.add_argument('--none',action='store_const',const='none',dest='generation',
                       help='Resources from winning only, unused ones kept [default]')
    
    parser.set_defaults(generation='none',manual=False)
    args = vars(parser.parse_args())
    if args['update']:
        assert args['number'] == 1,'Unable to update scenario file based on multiple games'
    if args['single']:
        assert args['number'] == 1,'Unable to perform single rounds based on multiple games'
    assert args['value'] + args['individual'] + args['team'] <= 4,\
        'Number of agent rewards exceeds number of players'
    args['value'] = 4 - args['individual'] - args['team']
    incentives = counts2incentives(args)
    print incentives
    
    ######
    # Set up map and world
    ######
    regions,starts = mapLoad(args['map'])
#    closeRegions(regions)
#    mapSave(regions,args['map'])
    if args['file'] is None:
        args['file'] = '%s.psy' % (os.path.splitext(args['map'])[0])
    if args['log'] is None:
        args['log'] = '%s.csv' % (os.path.splitext(args['map'])[0])

    if os.path.isfile(args['file']):
        # Existing scenario file
        startTime = time.time()
        world = ResourceWorld(args['file'])
        if not args['quiet']:
            print >> sys.stderr,'Load:\t\t%3dms' % (1000.*(time.time()-startTime))
        if world.terminated():
            raise RuntimeError,'Game already over in scenario file %s' % (args['file'])
    else:
        world = createWorld(len(starts),regions,starts,args['generation'],incentive=incentives)
        world.save(args['file'])
#        world.printState()
    if args['replay']:
        if args['replay'] == 'all':
            files = set(os.listdir('.'))
            possibles = [fname[:4] for fname in files if fname[4:] == '_1_logs.csv']
            games = []
            for game in possibles:
                if not '%s.csv' % (game) in files:
                    # No pre-existing merged log file
                    for player in range(2,5):
                        if not '%s_%d_logs.csv' % (game,player) in files:
                            # Missing a player log
                            break
                    else:
                        games.append(game)
            games.sort()
        else:
            games = [args['replay']]
        gameLogs = {}
        for gameID in games:
            print 'Game: %s' % (gameID)
            game = readLogs(world,gameID)
            if game['states']:
                fields,flow = analyzeGame(world,game,args['replay'])
                with open('%s.csv' % (args['replay']),'w') as csvfile:
                    writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
                    writer.writeheader()
                    for record in flow:
                        writer.writerow(record)
        sys.exit(0)
    # Set up end-of-game stat storage
    stats = {'rounds': Distribution(),                       # How many rounds did it take to win?
             'win': Distribution({True: 0.,False: 0.})}      # How often did the team win?
    for player in world.allocators:
        stats[player.name] = {'resources': Distribution(),   # How many resources does the player end with?
                              'territory': Distribution(),   # How many regions does the player end with?
                              'value': Distribution()}       # What is the total value of those regions?
        for region in world.objects:
            stats[player.name][region.name] = Distribution() # Does the player end with this region?
    totalProb = 0.
    prediction = {}

    for iteration in range(args['number']):
        world = ResourceWorld(args['file'])
        if world.getValue('phase') == 'allocate':
            start = world.getValue('round') - 1
        else:
            start = world.getValue('round')

        ######
        # Game loop
        ######
 
        # The probability of this current run
        probability = 1.

        while True:
            phase = world.getValue('phase')
            rnd = world.getValue('round')
            if phase == 'allocate':
                if not args['quiet']:
                    # Print current game state
                    print '--------'
                    print 'Round %2d' % (rnd)
                    print '--------'
                    resources = world.getResources()
                    regions = world.getOwnership()
                    values = world.getTotalValue('value')
                    for player in range(4):
                        playerName = 'Player%d' % (player+1)
                        print 'Player %d: %d resources' % (player+1,resources[playerName])
                        print '\t%2d territories (value: %3d): %s' % \
                            (world.getValue(stateKey(playerName,'territory')),
                             world.getValue(stateKey(playerName,'value')),
                             ', '.join(sorted(regions[playerName])))
                        total = 0
                        for region in regions['Player%d' % (player+1)]:
                            total += world.getValue(stateKey(region,'value'))
                    if regions.has_key('Enemy'):
                        print 'Enemy: %s' % (', '.join(['%s (%d)' % (o,world.getValue(stateKey(o,'occupants'))) for o in sorted(regions['Enemy'])]))
                    print
                # Check whether game is over
                if world.terminated():
                    break
            # Who's doing what
            turns = world.next()
            if phase == 'generate':
                actions = []
            else:
                actions = {}
                # Initialize other players to be doing nothing
                others = {}
                for name in turns:
                    actions[name] = ActionSet()
                    others[name] = ActionSet()
            if args['manual']:
                turns.sort()
            for name in turns:
                if phase  == 'generate':
                    # Time for re-generation of resources
                    assert not isinstance(world.agents[name],ResourceAgent)
                    if name in starts:
                        actions.append(Action({'subject': name,'verb': 'generate'}))
                    else:
                        actions.insert(0,Action({'subject': name,'verb': 'generate'}))
                else:
                    assert phase == 'allocate'
                    # Time for players to allocate resources
                    agent = world.agents[name]
                    if args['manual']:
                        # Manual selection of actions
                        objects = agent.legalObjects(world.state[None])
                        objects.sort()
                        resources = world.getValue(stateKey(agent.name,agent.resourceName))
                        choices = set()
                        while True:
                            # Pick a target
                            print
                            for i in range(len(objects)):
                                print '%2d) %s\t(value: %2d, defenders: %2d)' % \
                                    (i+1,objects[i],world.getValue(stateKey(objects[i],'value')),
                                     world.getValue(stateKey(objects[i],'occupants')))
                            print ' 0) End %s\'s turn' % (name)
                            print '-1) End game'
                            print
                            print 'Choose target for %s: ' % (name),
                            try:
                                index = int(sys.stdin.readline().strip())
                            except:
                                continue
                            if index == 0:
                                # Chosen done
                                break
                            elif index == -1:
                                sys.exit()
                            if index > len(objects) or index < 0:
                                # Illegal value
                                continue
                            # Pick an amount
                            print '\nChoose resources for %s to allocate to %s (1-%d): ' \
                                % (agent.name,objects[index-1],resources),
                            try:
                                amount = int(sys.stdin.readline().strip())
                            except:
                                continue
                            if amount < 1 or amount > resources:
                                # Illegal value
                                continue
                            print
                            action = Action({'subject': agent.name,
                                             'verb': agent.verbName,
                                             'object': objects[index-1],
                                             'amount': amount})
                            # Update available targets and resources
                            del objects[index-1]
                            resources -= amount
                            choices.add(action)
                            if resources == 0:
                                # Nothing  left to allocate
                                break
                        actions[name] = ActionSet(choices)
                    else:
                        startTime = time.time()
                        currentWorld = world.state[None].domain()[0]
                        choices = agent.singletonActions(currentWorld)
                        choices.sort(lambda x,y: cmp(str(x),str(y)))
                        keys = {}
                        for action in choices:
                            keys[action] = {stateKey(None,'phase'),
                                            stateKey(agent.name,'resources'),
                                            stateKey(agent.name,'territory'),
                                            stateKey(agent.name,'value'),
                                            stateKey(action['object'],'invader'),
                                            stateKey(action['object'],'owner')}
                        decision = agent.decide(currentWorld,horizon=2,others=actions,
                                                selection='uniform',actions=choices,keys=keys)
                        if len(choices) > 1:
                            if not args['quiet']:
                                print agent.name,', '.join(['%s %d (%5.3f)' % (a['object'],a['amount'],decision['V'][a]['__EV__']) for a in sorted(choices,lambda x,y: -cmp(decision['V'][x]['__EV__'],decision['V'][y]['__EV__']))])
                        if isinstance(decision['action'],Distribution):
                            actions[name] = decision['action'].sample()
                        else:
                            actions[name] = decision['action']
                        if not args['quiet']:
                            print >> sys.stderr,'Decision:\t%3dms (%s)' % \
                            (1000*(time.time()-startTime),actions[name])
#                        actions[name] = agent.sampleAction(world.state[None],1,joint=actions)
            if phase == 'allocate' and not args['quiet']:
                for player in range(4):
                    print 'Player %d invades: %s' % (player+1,', '.join(['%s (%d)' % (a['object'],a['amount']) for a in actions['Player%d' % (player+1)]]))
            # Predict at possible outcomes
            if args['predict'] and phase == 'allocate' and not args['quiet']:
                startTime = time.time()
                prediction = world.predictResult(actions)
                if not args['quiet']:
                    print >> sys.stderr,'Prediction:\t%3dms' % (1000.*(time.time()-startTime))
                objects = prediction.keys()
                objects.sort()
                print
                print 'Predictions:'
                for obj in objects:
                    print '\t%s (worth %d)' % (obj,world.getValue(stateKey(obj,'value')))
                    print '\t\tLeader:',','.join(prediction[obj]['leader'].domain())
                    print '\t\tWin: %d%%' % (100-int(100*prediction[obj]['winner']['Enemy']))
            # Perform actions
            startTime = time.time()
            outcomes = world.step(actions,select=False)
            if not args['quiet']:
                print >> sys.stderr,'Step:\t\t%3dms' % (1000.*(time.time()-startTime))
            if len(world.state[None]) > 1:
                original = VectorDistribution(world.state[None])
                sample = world.state[None].select(True)
                sampleProb = original[world.state[None].domain()[0]]
                probability *= sampleProb
                if not args['quiet']:
                    if not args['predict']:
                        # Haven't figured out the objects yet
                        objects = set()
                        for name,action in actions.items():
                            for atom in action:
                                objects.add(atom['object'])
                        objects = list(objects)
                        objects.sort()
                    print
                    print 'Results (prob %d%%):' % (int(100*sampleProb))
                    for obj in objects:
                        key = stateKey(obj,'owner')
                        owner = world.getValue(key)
                        if owner == 'Enemy':
                            print '%-10s:\tLost\t\t\tSpinner =%3d%%' % (obj,int(100.*sample[key]))
                        else:
                            print '%-10s:\tWon by %s\t+%d\tSpinner =%3d%%' % \
                                (obj,owner,world.getValue(stateKey(obj,'value')),int(100.*sample[key]))
            if phase == 'generate':
                if args['single'] and rnd == start+1:
                    # Finished one round
                    break
        # Accumulate end-of-game stats
        resources = world.getResources()
        regions = world.getOwnership()
        entry = {'probability': probability,'valueRewards': args['value'],
                 'territoryRewards': args['individual'],'teamRewards': args['team']}
        if regions.has_key('Enemy'):
            # Team lost
            stats['win'][False] += probability
            entry['win'] = 'no'
        else:
            # Team won
            stats['win'][True] += probability
            stats['rounds'].addProb(world.getValue('round'),probability)
            entry['win'] = 'yes'
        entry['rounds'] = world.getValue('round')
        for player in world.allocators:
            stats[player.name]['resources'].addProb(resources[player.name],probability)
            entry['resources%s' % (player.name)] = resources[player.name]
            territory = len(regions[player.name])
            assert world.getValue(stateKey(player.name,'territory')) == territory
            stats[player.name]['territory'].addProb(territory,probability)
            entry['territory%s' % (player.name)] = territory
            value = sum([world.getValue(stateKey(region,'value')) for region in regions[player.name]])
            assert world.getValue(stateKey(player.name,'value')) == value
            stats[player.name]['value'].addProb(value,probability)
            entry['value%s' % (player.name)] = value
            for region in world.objects:
                owned = world.getValue(stateKey(region.name,'owner')) == player.name
                stats[player.name][region.name].addProb(owned,probability)
        totalProb += probability
        with open(args['log'],'a') as csvfile:
            fieldnames = ['probability','win','rounds']+\
                         ['resources%s' % (p.name) for p in world.allocators]+\
                         ['territory%s' % (p.name) for p in world.allocators]+\
                         ['value%s' % (p.name) for p in world.allocators]+\
                         ['valueRewards','territoryRewards','teamRewards']
            writer = csv.DictWriter(csvfile,fieldnames=fieldnames)
            writer.writerow(entry)

    if args['number'] > 1:
        # Normalize end-of-game stats
        stats['win'].normalize()
        stats['rounds'].normalize()
        for player in world.allocators:
            stats[player.name]['resources'].normalize()
            stats[player.name]['territory'].normalize()
            stats[player.name]['value'].normalize()
            for region in world.objects:
                stats[player.name][region.name].normalize()
        # Print end-of-game stats
        print 'Games:',args['number']
        print 'Win: %3d%%' % (int(100.*stats['win'][True]))
        if stats['rounds']:
            print 'Rounds until win:'
            rounds = stats['rounds'].domain()
            rounds.sort()
            for r in range(rounds[0],rounds[-1]+1):
                print '\t%2d rounds: %2d%%' % (r,int(100.*stats['rounds'].getProb(r)))
        print
        world.allocators = sorted(world.allocators,key=lambda a: a.name)
        print 'Player\t\t%s' % ('\t'.join([player.name[-1] for player in world.allocators]))
        print 'E[resources]\t%s' % ('\t'.join(['%3d' % (stats[player.name]['resources'].expectation()) \
                                                   for player in world.allocators]))
        print 'E[regions]\t%s' % ('\t'.join(['%3d' % (stats[player.name]['territory'].expectation()) \
                                                 for player in world.allocators]))
        print 'E[value]\t%s' % ('\t'.join(['%3d' % (stats[player.name]['value'].expectation()) \
                                                 for player in world.allocators]))
        for region in sorted(world.objects,key=lambda a: a.name):
            if not region.name in starts:
                print '%-12s\t%s' % (region.name,'\t'.join(['%3d%%' % (int(100.*stats[player.name][region.name].getProb(True))) for player in world.allocators]))
                

    if args['update']:
        world.save(args['file'])
