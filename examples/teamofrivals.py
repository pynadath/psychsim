"""
Scenario for cooperative conquest game

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
--------
Map file
--------
XML file containing regions, specifying their individual parameters and neighbors. If omitted, the "value" attribute defaults to 5, as does the "occupants" attribute". The "owner" attribute indicates which player, 1-N, owns the territory at the start of the game. The default is 0, which indicates that the enemy side owns the territory.

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
--------
Round number
--------
Player: how many resources this player currently owns
        which territories this player currently owns
Enemy: which territories are still currently owned by the enemy (number of defenders in each territory in parens)

Player actions: which territories the player has chosen to invade (number of armies allocated in parens)

Optional Predictions:
        Territory being invaded (how many resources are gained by the owner)
                The player(s) who would be the owner if the invasion is successful
                The probability that the invasion will be successful

Results
Territory being invaded: the result of the invasion

"""
from argparse import ArgumentParser
import os.path
import random
import sys
import lxml.etree as ET

from psychsim.pwl import *
from psychsim.world import *
from psychsim.agent import Agent

class ResourceWorld(World):
    """
    @cvar nullAgent: string label that means none of the ResourceAgent members of this world
    """
    nullAgent = '__none__'
    memory = False

    def __init__(self,xml=None,allocateVerb=None,allocationState=None,winnerState=None):
        self.allocators = set()
        self.objects = set()
        World.__init__(self,xml)
        if xml is None:
            self.allocateVerb = allocateVerb
            self.allocationState = allocationState
            self.winnerState = winnerState

    def addAgent(self,agent):
        World.addAgent(self,agent)
        if isinstance(agent,ResourceAgent):
            self.allocators.add(agent)
            for obj in agent.objects:
                if self.agents.has_key(obj):
                    self.objects.add(self.agents[obj])
        else:
            for other in self.allocators:
                if agent.name in other.objects:
                    self.objects.add(agent)

    def getResources(self,state=None):
        """
        @return: a table of amount of resources owned by each player
        @rtype: strS{->}int
        """
        if state is None:
            state = self.state
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
            state = self.state
        ownership = {}
        # Hacky way to figure out what can be owned
        for agent in self.agents.values():
            if isinstance(agent,ResourceAgent):
                objects = agent.objects
                break
        for obj in objects:
            # Who owns it?
            owner = self.getState(obj,'owner')
            assert len(owner) == 1
            owner = owner.domain()[0]
            # Add to table
            try:
                ownership[owner].add(obj)
            except KeyError:
                ownership[owner] = {obj}
        return ownership

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
            outcomes = self.step(objects[obj]['actions'],real=False)
            assert len(outcomes) == 1
            objects[obj]['leader'] = self.getState(obj,self.winnerState,outcomes[0]['new'])
            objects[obj]['winner'] = self.getState(obj,'owner',outcomes[0]['new'])
        return objects

    def getDynamics(self,key,action,state=None):
        if isTurnKey(key):
            # Caching doesn't work too well with partial prediction
            return []
        elif isinstance(action,ActionSet):
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
                        assert len(self.state) == 1,'Unable to hack dynamics in uncertain states'
                        state = self.state.domain()[0]
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
                        assert len(self.state) == 1,'Unable to hack dynamics in uncertain states'
                        state = self.state.domain()[0]
                    if self.getValue('phase',state) == 'allocate':
                        # No one allocating to this object, so no possible winner
                        tree = makeTree(setToConstantMatrix(key,self.nullAgent))
                        return [tree.desymbolize(self.symbols)]
                    else:
                        return []
        return World.getDynamics(self,key,action)

    def __xml__(self):
        doc = World.__xml__(self)
        doc.documentElement.setAttribute('verb',self.allocateVerb)
        doc.documentElement.setAttribute('allocation',self.allocationState)
        doc.documentElement.setAttribute('winner',self.winnerState)
        return doc

    def parse(self,element):
        World.parse(self,element,ResourceAgent)
        self.allocateVerb = str(element.getAttribute('verb'))
        self.allocationState = str(element.getAttribute('allocation'))
        self.winnerState = str(element.getAttribute('winner'))

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
        resources = vector[stateKey(self.name,self.resourceName)]
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

    def sampleAction(self,vector,numTargets=0,minResources=0):
        """
        @param numTargets: maximum number of targets for allocation. 0 means no limit (default is 0)
        @param minResources: minimum number of resources to leave unallocated (default is 0)
        Generates a random (legal) action for this agent in the given world
        """
        targets = []
        if isinstance(vector,VectorDistribution):
            assert len(vector) == 1,'Unable to sample actions in an uncertain world'
            vector = vector.domain()[0]
        resources = vector[stateKey(self.name,self.resourceName)]
        if resources > minResources:
            resources -= minResources
        else:
            # Less than minimal number, let's not divide them up
            numTargets = 1
        for obj in self.legalObjects(vector):
            targets.append(obj)
        if 0 < numTargets < len(targets):
            targets = random.sample(targets,numTargets)
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

def createWorld(numPlayers,regionTable,starts,generation='additive',maxResources=32):
    """
    @param numPlayers: number of players in the game
    @type numPlayers: int
    @param regionTable: a table of regions, indexed by name
    @param starts: a list of starting regions, one for each player
    @param maxResources: the maximum number of resources a player may have
    @type maxResources: int
    """
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
        try:
            index = starts.index(region.name)
            region.setState('invader','Player%d' % (index+1))
        except ValueError:
            region.setState('invader',world.nullAgent)
        world.dynamics[stateKey(region.name,'invader')] = True

    # Set players' initial territories
    for index in range(numPlayers):
        region = world.agents[starts[index]]
        region.setState('owner',players[index].name)
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
    world.setOrder([set([region.name for region in regions]),set([player.name for player in players])])

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

        for player in players:
            resources = stateKey(player.name,'resources')
            # tree = makeTree({'if': equalFeatureRow(owner,invader),
            #                  True: None, # No one's invading, so owner is unchanged
            #                  False: 
            #                  {'if': equalRow(invader,player.name),
            #                   True: # I'm invading
            #                   {'if': differenceRow(invaders,defenders,4), # Significantly more invaders
            #                    True: setToFeatureMatrix(owner,invader), # Invader wins
            #                    False: 
            #                    {'if': differenceRow(invaders,defenders,0), # More invaders
            #                     True: setToFeatureMatrix(owner,invader), # Invader wins
            #                     False: 
            #                     {'if': differenceRow(invaders,defenders,-4), # More defenders
            #                      True: noChangeMatrix(owner), # Invader lose
            #                      False: noChangeMatrix(owner)}}}, # Invader loses
            #                   False: None}}) # I'm not invading
            # Determine how many resources lost
            action = Action({'subject': player.name,'verb': 'allocate','object': region.name})
            world.addDependency(resources,invader)
            if generation == 'additive' or generation == 'none':
                # Lose only those resources allocated
                tree = makeTree(incrementMatrix(resources,'-%s' % (actionKey('amount'))))
            else:
                # Lose all resources
                tree = makeTree(setToConstantMatrix(resources,0))
            world.setDynamics(resources,action,tree)
            # Regain resources from owned territories
            action = Action({'subject': region.name,'verb': 'generate'})
            if generation == 'additive' or generation == 'restorative':
                tree = makeTree({'if': equalRow(owner,player.name),
                                 True: addFeatureMatrix(resources,stateKey(region.name,'value')),
                                 False: None})
            elif generation == 'minimal':
                if region is world.agents[starts[int(player.name[-1])-1]]:
                    tree = makeTree({'if': equalRow(owner,player.name),
                                     True: setToFeatureMatrix(resources,stateKey(region.name,'value')),
                                     False: None})
                else:
                    tree = makeTree(noChangeMatrix(resources))
            elif generation is 'none':
                tree = makeTree({'if': equalRow(owner,player.name),
                                 True: {'if': equalFeatureRow(owner,invader),
                                        True: addFeatureMatrix(resources,stateKey(region.name,'value')),
                                        False: None},
                                 False: None})
#                tree = makeTree(noChangeMatrix(resources))
            world.setDynamics(resources,action,tree)

    # The game has two phases: generating resources and allocating resources
    world.defineState(None,'phase',list,['generate','allocate'],combinator='*',
                      description='The current phase of the game')
    world.setState(None,'phase','generate')
    key = stateKey(None,'phase')
    # If we generate, then the phase becomes allocate
    action = Action({'subject': list(regions)[0].name,'verb': 'generate'})
    tree = makeTree(setToConstantMatrix(key,'allocate'))
    world.setDynamics(key,action,tree)
    # If we allocate, then the phase becomes generate
    tree = makeTree(setToConstantMatrix(key,'generate'))
    for region in regions:
        for player in players:
            action = Action({'subject': player.name,'verb': 'allocate','object': region.name})
            world.setDynamics(key,action,tree)

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

    # Optional arguments that select the resource generation model
    label = parser.add_argument_group('Resource Generation')
    group = label.add_mutually_exclusive_group()
    group.add_argument('--additive',action='store_const',const='additive',dest='generation',
                       help='Resources from all territories, unused ones kept')
    group.add_argument('--restorative',action='store_const',const='restorative',dest='generation',
                       help='Resources from all territories, unused ones lost [default]')
    group.add_argument('--minimal',action='store_const',const='minimal',dest='generation',
                       help='Resources from initial territories, unused ones lost')
    group.add_argument('--none',action='store_const',const='none',dest='generation',
                       help='Resources from winning only, unused ones kept')
    
    parser.set_defaults(generation='restorative',manual=False)
    args = vars(parser.parse_args())
    if args['update']:
        assert args['number'] == 1,'Unable to update scenario file based on multiple games'
    if args['single']:
        assert args['number'] == 1,'Unable to perform single rounds based on multiple games'

    ######
    # Set up map and world
    ######
    regions,starts = mapLoad(args['map'])
#    closeRegions(regions)
#    mapSave(regions,args['map'])
    if args['file'] is None:
        args['file'] = '%s.psy' % (os.path.splitext(args['map'])[0])

    if os.path.isfile(args['file']):
        world = ResourceWorld(args['file'])
        if world.terminated():
            raise RuntimeError,'Game already over in scenario file %s' % (args['file'])
    else:
        world = createWorld(len(starts),regions,starts,args['generation'])
        world.save(args['file'])

    # Set up end-of-game stat storage
    stats = {'rounds': Distribution(),                       # How many rounds did it take to win?
             'win': Distribution({True: 0.,False: 0.})}      # How often did the team win?
    for player in world.allocators:
        stats[player.name] = {'resources': Distribution(),   # How many resources does the player end with?
                              'territory': Distribution()}   # How many regions does the player end with?
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
                    for player in range(4):
                        print 'Player %d: %d resources' % (player+1,resources['Player%d' % (player+1)])
                        print '\tTerritories owned: %s' % (', '.join(sorted(regions['Player%d' % (player+1)])))
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
            actions = {}
            turns = world.next()
            if args['manual']:
                turns.sort()
            for name in turns:
                if phase  == 'generate':
                    # Time for re-generation of resources
                    assert not isinstance(world.agents[name],ResourceAgent)
                    actions[name] = Action({'subject': name,'verb': 'generate'})
                else:
                    assert phase == 'allocate'
                    # Time for players to allocate resources
                    agent = world.agents[name]
                    if args['manual']:
                        # Manual selection of actions
                        objects = agent.legalObjects(world.state)
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
                    elif args['generation'] == 'none':
                        actions[name] = agent.sampleAction(world.state,2,2)
                    else:
                        actions[name] = agent.sampleAction(world.state,2)
            if phase == 'allocate' and not args['quiet']:
                for player in range(4):
                    print 'Player %d invades: %s' % (player+1,', '.join(['%s (%d)' % (a['object'],a['amount']) for a in actions['Player%d' % (player+1)]]))
            # Predict at possible outcomes
            if args['predict'] and phase == 'allocate' and not args['quiet']:
                prediction = world.predictResult(actions)
                objects = prediction.keys()
                objects.sort()
                print
                print 'Predictions:'
                for obj in objects:
                    print '\t%s (worth %d)' % (obj,world.getValue(stateKey(obj,'value')))
                    print '\t\tLeader:',','.join(prediction[obj]['leader'].domain())
                    print '\t\tWin: %d%%' % (100-int(100*prediction[obj]['winner']['Enemy']))
            # Perform actions
            outcomes = world.step(actions,select=False)
            if len(world.state) > 1:
                sample = world.state.select()
                probability *= sample
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
                    print 'Results (prob %d%%):' % (int(100*sample))
                    for obj in objects:
                        owner = world.getValue(stateKey(obj,'owner'))
                        if owner == 'Enemy':
                            print '%s: Lost' % (obj)
                        else:
                            print '%s: Won by %s' % (obj,owner)
            if phase == 'generate':
                if args['single'] and rnd == start+1:
                    # Finished one round
                    break
        # Accumulate end-of-game stats
        resources = world.getResources()
        regions = world.getOwnership()
        if regions.has_key('Enemy'):
            # Team lost
            stats['win'][False] += probability
        else:
            # Team won
            stats['win'][True] += probability
            stats['rounds'].addProb(world.getValue('round'),probability)
        for player in world.allocators:
            stats[player.name]['resources'].addProb(resources[player.name],probability)
            stats[player.name]['territory'].addProb(len(regions[player.name]),probability)
            for region in world.objects:
                owned = world.getValue(stateKey(region.name,'owner')) == player.name
                stats[player.name][region.name].addProb(owned,probability)
        totalProb += probability
                                
    if args['number'] > 1:
        # Normalize end-of-game stats
        stats['win'].normalize()
        stats['rounds'].normalize()
        for player in world.allocators:
            stats[player.name]['resources'].normalize()
            stats[player.name]['territory'].normalize()
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
        for region in sorted(world.objects,key=lambda a: a.name):
            if not region.name in starts:
                print '%-12s\t%s' % (region.name,'\t'.join(['%3d%%' % (int(100.*stats[player.name][region.name].getProb(True))) for player in world.allocators]))
                

    if args['update']:
        world.save(args['file'])
