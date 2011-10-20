import copy
import random
import sys

from teamwork.multiagent.sequential import *
from teamwork.agent.Entities import *
from teamwork.agent.AgentClasses import *
from teamwork.dynamics.pwlDynamics import *
from teamwork.math.Interval import *
from teamwork.math.KeyedMatrix import *
from teamwork.math.KeyedTree import *
from teamwork.action.PsychActions import *
from teamwork.policy.StochasticPolicy import *
from teamwork.shell.TerminalShell import *

__GOOD__ = None
__PUNISH__ = 1

population = {'OptOptDonor':0,
              'OptPesDonor':0,
              'PesOptDonor':0,
              'PesPesDonor':0
              }
donations = [.001,.003,.005,.007,.01]
## numDonations = 5
## donations = map(lambda x:float(x)/1000,range(1,11,10/numDonations))
fines = [.01]
namePrefix = 'agent'
neighborSpacing = 1
# Static elements of the class hierarchy

classHierarchy['PublicGood'] = {
    'parent': [],
    'state':{'wealth':0.5},
    'beliefs':{None:{'wealth':None}},
    'dynamics':{'wealth':{}},
    'depth':1
    }

classHierarchy['Donee'] = {
    'parent':['PublicGood'],
    'state':{'wealth':0.,
             'goodExists':0.},
    'goals':[],
    'models':{'normal':{'goals':[]}},
    'model':'normal',
    'beliefs':{'Donor':{'model':'altruistic'}}
    }

classHierarchy['Donor'] = {
    'parent':['PublicGood'],
    'relationships': {'donee':'Donee',
                      'neighbor':'Donor'},
    'actions': [],
    'state':{'wealth':0.9}, # This gets re-set dynamically
    # Label models by Donation style (Altruistic vs. Egoistic) followed by
    # Punishment Style (A vs. E)
    'models':{'AA': {}, 'AE': {}, 'EA':{}, 'EE': {},
              'deliberate':{'policy':['observation depth 1 type disburse -> '\
                                      +'{"type":"lookahead"}']}},
    'beliefs':{'Donee':{'model':'normal'}},
    'model':'deliberate'
    }

classHierarchy['OptOptDonor'] = {
    'parent':['Donor'],
    'beliefs':{'Donor':{'model':'AA'}}
    }

classHierarchy['OptPesDonor'] = {
    'parent':['Donor'],
    'beliefs':{'Donor':{'model':'AE'}}
    }

classHierarchy['PesOptDonor'] = {
    'parent':['Donor'],
    'beliefs':{'Donor':{'model':'EA'}}
    }

classHierarchy['PesPesDonor'] = {
    'parent':['Donor'],
    'beliefs':{'Donor':{'model':'EE'}}
    }

__count__ = -1
def agentCount():
    """Returns the number of agents in the total population"""
    global __count__
    if __count__ < 0:
        __count__ = 0
        for count in population.values():
            __count__ += count
    if __count__ == 0:
        raise UserWarning,'No agents selected!'
    return __count__

class DonateAction(Action):
    """Domain-specific class that includes an 'amount' field."""
    format = ['actor','type','object','amount']

    def __init__(self,arg={}):
        self.fields['amount'] = {'range':donations}
        Action.__init__(self,arg)

    def __eq__(self,other):
        for key in self.fields.keys():
            if not self[key] is None and not other[key] is None \
               and self[key] != other[key]:
                return None
        return 1
        
class PublicGoodAgents(TurnBasedAgents):
    """Domain-specific class that sets up the game stages"""

    fixedNetwork = 1
    
    def mapActions(self,actions):
        if self.fixedNetwork:
            return None
        # Map neighbors to previously randomized agents
        for act in actions:
            if act['object'] and act['object'] != 'Public':
                act['object'] = act['actor'].neighbors[act['object']]
        return 1

    def updateTurn(self,actionList,debug=None):
        TurnBasedAgents.updateTurn(self,actionList,debug)
        if not self.fixedNetwork:
            self.randomizeNeighbors(debug)
        
    def randomizeNeighbors(self,debug=None):
        # Find new random mapping (works if you have only 1 neighbor!)
        remaining = self.keys()
        try:
            remaining.remove('Public')
        except ValueError:
            # Not in the punishment phase
            return None
        for entity in self.members():
            if entity.name == 'Public' or entity.parent:
                continue
            if len(remaining) > 1:
                # Choose out of the list remaining
                index = int(random.random()*len(remaining))
                if remaining[index] == entity.name:
                    index += 1
                    if index == len(remaining):
                        index = 0
            else:
                # Only one agent left to choose
                index = 0
                if remaining[index] == entity.name:
                    # All that's left is myself!
                    flag = 1
                    done = None
                    while not done:
                        # Keep searching for an agent to swap with
                        other = self.members()[int(random.random()*len(self))]
                        if other.name != 'Public' and \
                               other.name != entity.name:
                            # Swap neighbors with this agent
                            neighbor = other.neighbors.keys()[0]
                            remaining[index] = other.neighbors[neighbor]
                            other.neighbors[neighbor] = entity.name
                            done = 1
            # Save random mapping for next call
            try:
                entity.neighbors[entity.neighbors.keys()[0]] = remaining[index]
            except AttributeError,e:
                print entity.ancestry()
                raise AttributeError,e
            del remaining[index]
        if debug:
            for entity in self.members():
                debug.message(8,'New neighbor of %s: %s' % \
                              (entity.name,entity.neighbors.values()[0]))
        return 1
            
    def generateOrder(self):
        """Orders the entities so that there is a first parallel
        donation stage and then a second parallel
        punishment/disbursement stage"""
        # Figure out which agents are donors and which ones not
        donors = []
        donees = []
        for name in self.keys():
            entity = self[name]
            if entity.instanceof('Donor'):
                donors.append(name)
            else:
                donees.append(name)
        self.keyOrder = []
        # Generate turn sequence for game
        round = []
        for agent in donors:
            choices = []
            for act in self[agent].actions:
                # Restrict donors to either donate or wait
                if act['type'] in ['wait','donate']:
                    choices.append(act)
            round.append({'name':agent,'choices':choices})
        self.keyOrder.append(round)
        # Generate turn sequence for disbursement + punishment
        round = []
        for agent in donees:
            for act in self[agent].actions:
                if act['type'] == 'disburse':
                    round.append({'name':agent,'choices':[act]})
        for agent in donors:
            choices = []
            for act in self[agent].actions:
                # Restrict donors to either punish or wait
                if act['type'] in ['wait','punish']:
                    choices.append(act)
            round.append({'name':agent,'choices':choices})
        self.keyOrder.append(round)
        # Prime for first round
        self.order = copy.deepcopy(self.keyOrder)
        # Domain-specific patch time!
        try:
            self['Public'].freezeModels()
        except KeyError:
            pass

        
class PublicGoodAgent(PsychEntity):
    beliefClass = PublicGoodAgents
    actionClass = DonateAction
    # Comment out the following for deterministic policies
##    policyClass = StochasticLookupAhead
    # Comment out the following to eliminate model change
    modelChange = 1
    learningRate = 0.2
    valueType = 'final'
    mentalType = 'aggregate'
    
    def freeze(self):
        """These agents don't really do any backward projection, so
        let's shortcut through the annoying copying that is required
        when freezing the initial version of myself"""
        self.initial = self
        
    def preComStateEstimator(self,beliefs,actions,epoch=-1,debug=Debugger()):
        """Updates beliefs in response to observation
        (Within this model, the agent and its belief state are one and
        the same)"""
        self.saveObservations(actions)
        delta = {}
        if len(self.getEntities()) == 0:
            return beliefs,delta
        # Aggregate actions
	aggActList = []
        pubAct = None
	toDistribute = 0.
	total = 0.
        for act in actions:
            # Get the actor name
            if isinstance(act['actor'],str):
                actor = act['actor']
            else:
                actor = act['actor'].name
            if actor == self.name:
		# Set aside for later
                myAct = act
            elif actor == 'Public':
		# Set aside for later
                pubAct = act
            elif act['type'] == 'punish':
                if act['object'] == self.name:
		    # We care about only those punishments of our ourself
		    if actor in self.relationships['neighbor']:
			aggActList.append(copy.copy(act))
			total += act['amount']
		    else:
			# Store this amount for re-distribution
			toDistribute += act['amount']
		elif actor in self.relationships['neighbor']:
                    aggActList.append(self.actionClass({'type':'wait',
                                                        'actor':actor}))
            elif act['type'] == 'donate':
		if actor in self.relationships['neighbor']:
		    aggActList.append(copy.copy(act))
		    total += act['amount']
		else:
		    # Store this amount for re-distribution
		    toDistribute += act['amount']
            elif actor in self.relationships['neighbor']:
                # For wait actions
		aggActList.append(copy.copy(act))
	    else:
                # Wait (I hope)
                pass
	# Re-distribute actions of non-neighbors among neighbors
	if toDistribute > 0.:
	    for act in aggActList:
		if total > 0.:
		    if act['type'] != 'wait':
			act['amount'] += toDistribute*act['amount']/total
		else:
		    if act['type'] == 'wait':
			if pubAct: # i.e., punish stage
			    act['object'] = self.name
			    act['type'] = 'punish'
			else: # donation stage
			    act['object'] = 'Public'
			    act['type'] = 'donate'
		    elif act['type'] == 'punish':
			act['object'] = self.name
		    act['amount'] = toDistribute/float(len(aggActList))
		if act['amount'] > 1.:
                    print obs
		    raise ValueError,'Illegal amount: %s' % `act`
        aggActList.append(myAct)
        if pubAct:
            aggActList.append(pubAct)
        # Update beliefs
        for act in aggActList:
            delta[`act`] = beliefs.updateBeliefs(act,debug)
        # Update any mental models
        result = Stereotyper.preComStateEstimator(self,beliefs,aggActList,
                                                  epoch,debug)
        for key,value in delta.items():
            try:
                value.update(result[key])
            except KeyError:
                # That's OK...no model change here
                pass
        # Update beliefs about entities' beliefs
        for name in beliefs.getEntities():
            entity = beliefs.getEntity(name)
            entity,changes = entity.preComStateEstimator(entity,aggActList,
                                                         epoch,debug)
            # Merge these nested changes into the overall delta
            for obsType in changes.keys():
                if not delta[obsType].has_key(name):
                    delta[obsType][name] = {}
                for key in changes[obsType].keys():
                    delta[obsType][name][key] = changes[obsType][key]
                if len(delta[obsType][name].keys()) == 0:
                    del delta[obsType][name]
        self.invalidateCache()
        return beliefs,delta
                        
    def initEntities(self,entityList,depth=1):
        """Sets the entities known to be the list provided, and makes
        the appropriate updates to goals, policy depth, etc."""
        # Fill out recursive beliefs
        maxDepth = self.getDefault('depth')
        if depth <= maxDepth:
            newList = []
            # First, generate entity objects for my beliefs
            for entity in entityList:
                # Beliefs for only our neighbors
                if 'Donee' in self.classes or \
                       ('Donor' in entity.classes and \
                        entity.name != self.name and \
                        not entity.name in self.relationships['neighbor']):
                    continue
                # Stick this entity object into my beliefs
                newEntity = copy.copy(entity)
                self.setEntity(newEntity)
                newList.append(newEntity)
                # I am the only neighbor for my Donor models
                if self.mentalType == 'aggregate' and \
		   'Donor' in newEntity.classes and \
		   newEntity.name != self.name:
                    newEntity.relationships = {'donee':newEntity.relationships['donee'],
                                               'neighbor': [self.name]}
                # Assume correct beliefs about states
                for feature in entity.getStateFeatures():
                    try:
                        value = entity.getState(feature)
                        newEntity.setState(feature,value)
                    except KeyError:
                        pass
            # Finally, fill in specific beliefs according to my class
            # defaults, and go to the next recursive level
            for entity in newList:
                entity.models = copyModels(entity.getDefault('models'))
                entity.initModels(newList)
                self.initBeliefs(entity)
		if entity.name != self.name:
		    for entry in entity.policy.entries[:]:
			if not entry['action']['object'] in \
			   ['Public',self.name,None]:
			    entity.policy.entries.remove(entry)
			elif entry.has_key('actor') and \
			     entry['actor'] != self.name:
			    entity.policy.entries.remove(entry)
			elif entry['class'] == 'conjunction':
                            clause = entry['clauses'][0]
                            if clause['label'] == 'ifWait' and \
                                   clause['actor'] != self.name:
                                entity.policy.entries.remove(entry)
                entity.initEntities(newList,depth+1)
        # Add any goals related to the new entities
        self.initGoals(entityList)
        # Set the depth of lookahead
        horizon = self.getDefault('horizon')#*len(entityList)-depth+1
        if not self.policy:
            self.policy = self.policyClass(entity=self.name,
                                           actions=self.actions,
                                           relationships=self.relationships,
                                           size=1,
                                           depth=horizon)
        # Look for a simple model for top-level agents as well
        if not self.parent:
            try:
                self.setModel(self.getDefault('model'))
            except KeyError:
                pass
        # Make sure that we have mental models all the way through
        if not self.model:
            raise UserWarning ,  'No model for %s' % (self.ancestry())
        self.entities.initializeOrder()
        
    def initRelationships(self,entityList):
        """Instantiates the relationships of this entity regarding the
        provided list of entities"""
        GenericEntity.initRelationships(self,entityList)
	if self.mentalType != 'individual':
	    # Reduce our relationships to only a subset of neighbors
	    try:
		myIndex = int(self.name[len(namePrefix):])
	    except ValueError:
		# Public
		return
	    neighbor = myIndex + neighborSpacing
	    while neighbor >= agentCount():
		neighbor -= agentCount()
	    neighbor = '%s%d' % (namePrefix,neighbor)
	    try:
		for name in self.relationships['neighbor'][:]:
		    if name != neighbor:
			self.relationships['neighbor'].remove(name)
	    except KeyError:
		pass
        # initialize neighbor mapping
        self.neighbors = {}
        if self.name != 'Public':
            for neighbor in self.relationships['neighbor']:
                self.neighbors[neighbor] = neighbor
        
    def updateModels(self,actions,debug):
        delta = {}
        stage = 'donate'
        total = 0.
        count = 0
        actDict = {}
        debug.message(8,'Updating mental models held by %s' % self.ancestry())
        for act in actions:
            if act['type'] in ['disburse','punish']:
                stage = 'punish'
            try:
                actDict[act['actor'].name] = act
            except AttributeError:
                actDict[act['actor']] = act
        # Find my last action
        try:
            obsList = self.getObservations()[1]['content']
            myLast = None
        except IndexError:
            myLast = self.actionClass({'type':'wait',
                                       'actor':self.name})
        if not myLast:
            for act in obsList:
                if act['actor'] == self.name:
                    if stage == 'punish' and act['type'] == 'wait':
                        # Waiting is equivalent to a donation of zero
                        myLast = self.actionClass({'type':'donate',
                                                   'amount':0.,
                                                   'object':'Public',
                                                   'actor':self.name})
                    else:
                        myLast = act
                    break
        if stage == 'donate':
            lastDonation = {}
            # Find last donation received
            try:
                obsList = self.getObservations()[2]['content']
            except IndexError:
                obsList = []
                for name in self.neighbors.values():
                    lastDonation[name] = 0.
            for act in obsList:
                if act['actor'] in self.neighbors.values():
                    if act['type'] == 'wait':
                        lastDonation[act['actor'].name] = 0.
                    else:
                        lastDonation[act['actor'].name] = act['amount']
                    break
        models = self.extractModels()
        # Find model to update
        for entity in self.getEntityBeliefs():
            if not entity.name in [self.name,'Public']:
                curModel = models[entity.name]
                debug.message(8,'Examining model of %s' % entity.name)
                debug.message(7,'My current model is %s' % `curModel`)
                debug.message(7,'My last action was %s' % `myLast`)
                debug.message(7,'I observed %s' % `actDict[entity.name]`)
                relevant = []
                # Compare the policy to find the applicable entry
                if stage == 'punish':
                    relevant = entity.policy.entries[:3]
                    interval = str2Interval(relevant[0]['amount'])
                    if myLast['amount'] in interval:
                        size = 'Big'
                    else:
                        size = 'Small'
                else:
                    entry = entity.policy.entries[5]
                    interval = str2Interval(entry['amount'])
                    if lastDonation[self.neighbors[entity.name]] in interval:
                        size = 'Big'
                        relevant = [entity.policy.entries[3]]
                        relevant.append(entity.policy.entries[5])
                    else:
                        size = 'Small'
                        relevant = [entity.policy.entries[4]]
                        relevant.append(entity.policy.entries[6])
                # Policy RHS actions have no actor field, so let's prep
                act = copy.copy(actDict[entity.name])
                act['actor'] = None
                if stage == 'donate':
                    debug.message(7,'The last donation was %s (%6.4f)' %
                                  (size,lastDonation[self.neighbors[entity.name]]))
                    for entry in relevant:
                        debug.message(4,'Examining policy entry: %s' % \
                                      `entry`)
                    # Update our model of donation amounts
                    if myLast['type'] == 'punish':
                        key = 'donateIfPun'+size
                        index = 0
                    else:
                        key = 'donateIfNotPun'+size
                        index = 1
                    debug.message(4,'Modifying entry: %s' \
                                  % `relevant[index]`)
                    # Check whether we must modify the RHS of this entry
                    if act != relevant[index]['action']:
                        if act['amount']:
                            donation = act['amount']
                        else:
                            donation = 0.
                        amt = (1.-self.learningRate)*curModel[key]\
                              +self.learningRate*donation
                        debug.message(7,'New amount = %6.4f' % (amt))
                        relevant[index]['action'] = copy.copy(act)
                        if amt > 0.:
                            relevant[index]['action']['type'] = stage
                            relevant[index]['action']['amount'] = amt
                            relevant[index]['action']['object'] = 'Public'
                        else:
                            relevant[index]['action']['type'] = 'wait'
                            relevant[index]['action']['object'] = None
                            relevant[index]['action']['amount'] = None
                        delta[entity.name] = {key:amt}
                    debug.message(8,"New model: %s" % `relevant`)
                else:
                    # Update our belief about the punishment threshold
                    for entry in relevant:
                        debug.message(4,'Examining policy entry: %s' % \
                                      `entry`)
                    hiInterval = str2Interval(relevant[0]['amount'])
                    loInterval = str2Interval(relevant[1]['amount'])
                    # Find out where my last donation lies
                    if myLast['amount'] in hiInterval:
                        myIndex = 0
                    else:
                        myIndex = 1
                    try:
                        donIndex = donations.index(myLast['amount'])
                    except ValueError:
                        donIndex = -1
                    # Check what kind of update is needed
                    if act['type'] != relevant[myIndex]['action']['type']:
                        if act['type'] == 'punish':
                            # Punished unexpectedly
                            try:
                                threshold = donations[donIndex+1]
                            except IndexError:
                                threshold = 2.*myLast['amount']
                            threshold -= Interval.QUANTUM
                        else:
                            # Got away with it unexpectedly
                            if donIndex > 0:
                                threshold = donations[donIndex-1]
                            else:
                                threshold = -Interval.QUANTUM
                            threshold += Interval.QUANTUM
                    else:
                        if act['type'] == 'wait':
                            # Got away with it unexpectedly
                            if donIndex > 2:
                                threshold = donations[donIndex-2] \
                                            + Interval.QUANTUM
                            else:
                                threshold = -Interval.QUANTUM
                        else:
                            threshold = curModel['punishIfDon<']
                    # Update threshold
                    threshold = (1.-self.learningRate)\
                                *curModel['punishIfDon<']\
                                +self.learningRate*threshold
                    hiInterval['lo'] = threshold
                    loInterval['hi'] = threshold
                    relevant[0]['amount'] = `hiInterval`
                    relevant[1]['amount'] = `loInterval`
                    if 0. in hiInterval:
                        relevant[2]['action'] = self.actionClass({'type':
                                                                  'wait'})
                    else:
                        relevant[2]['action'] = copy.deepcopy(relevant[1]['action'])
                    delta[entity.name] = {'punishIfDon<':threshold}
                    debug.message(8,"New model: %s" % `relevant`)
        return delta

    def extractModels(self):
        models = {}
        for belief in self.getEntityBeliefs():
            if not belief.name in [self.name,'Public']:
                # Analyze agent's mental models
                model = {}
                # Punishment threshold
                entry = belief.policy.entries[1]
                interval = str2Interval(entry['amount'])
                model['punishIfDon<'] = interval['hi']
                # Donation if punished for big donation
                entry = belief.policy.entries[3]
                RHS = entry['action']
                model['donateIfPunBig'] = RHS['amount']
                if not RHS['amount']:
                    model['donateIfPunBig'] = 0.
                # Donation if punished for small donation
                entry = belief.policy.entries[4]
                RHS = entry['action']
                model['donateIfPunSmall'] = RHS['amount']
                if not RHS['amount']:
                    model['donateIfPunSmall'] = 0.
                # Donation if not punished for big donation
                entry = belief.policy.entries[5]
                RHS = entry['action']
                model['donateIfNotPunBig'] = RHS['amount']
                if not RHS['amount']:
                    model['donateIfNotPunBig'] = 0.
                # Donation if not punished for small donation
                entry = belief.policy.entries[6]
                RHS = entry['action']
                model['donateIfNotPunSmall'] = RHS['amount']
                if not RHS['amount']:
                    model['donateIfNotPunSmall'] = 0.
                if len(model.values()) < 5:
                    raise ValueError,'%s has incomplete model' \
                          % (belief.ancestry())
                models[belief.name] = model
        return models

##    def __copy__(self):
##        newEntity = PsychEntity.__copy__(self)
##        for feature in self.getStateFeatures():
##            value = self.getState(feature)
##            newEntity.setState(feature,value)
##        return newEntity

##    def __deepcopy__(self):
##        newEntity = copy.copy(self)
##        for otherName,other in self.entities.items():
##            if isinstance(other,str):
##                newEntity.entities[otherName] = other
##            else:
##                newOther = copy.copy(other)
##                newEntity.setEntity(newOther)
##        newEntity.entities.initializeOrder()
##        newEntity.entities.order = copy.deepcopy(self.entities.order)
##        return newEntity
            

class PublicGoodShell:
    agentClass = PublicGoodAgent
    multiagentClass = PublicGoodAgents
    actionFormat = [('actor',1),('type',1),('object',None),('amount',None)]

    def createEntities(self):
        """Interactive creation of entities for initial scenario"""
        entityList = []
        count = 0
        for key,value in population.items():
            for i in range(value):
                entity = createEntity(key,'%s%d' % (namePrefix,count),
                                      self.classes,self.agentClass)
                count += 1
                entityList.append(entity)
        # Exactly one Donee instance, named "Public"
        entityList.append(createEntity('Donee','Public',self.classes,
                                       self.agentClass))
        return entityList

    def performAct(self,name,actType,obj,amt,results=[]):
        """Performs the action of the specified type by the named
        entity on the specified object (use 'nil' if no object or
        amount)"""
        actList = [name,actType]
        if obj != 'nil':
            actList.append(obj)
            if amt != 'nil':
                actList.append(amt)
        self.__act__(actList,results)

class PublicGoodTerminal(PublicGoodShell,TerminalShell):
    pass
        
def genWealthDyn(amountLost=-1.):
    if amountLost < 0.:
        # Donation
        actorGets = '-amount'
        threshold = 'amount'
        objectGets = 'amount'
    else:
        # Punishment
        threshold = amountLost
        actorGets = -amountLost
        objectGets = '-amount'
        
    keyStruct = {'amObject': # Am I object (recipient)?
                 makeIdentityKey('object'),
                 'amActor': # Am I actor (donor)?
                 makeIdentityKey('actor'),
                 'actorValue': # How much does actor have to give ?
                 makeStateKey('actor','wealth'),
                 'myValue': # How much do I have ?
                 makeStateKey('self','wealth')
                 }
    
    # Support unchanged
    unchangedTree = createNodeTree(KeyedMatrix())

    # Increase value
    weights = {keyConstant: objectGets}
    objTree = createDynamicNode(keyStruct['myValue'],weights)
    # Decrease value
    weights = {keyConstant: actorGets}
    actorTree = createDynamicNode(keyStruct['myValue'],weights)

##    # Branch on having enough wealth
##    weights = {`keyStruct['actorValue']`: 1.}
##    enoughDonorTree = createBranchTree(KeyedPlane(KeyedRow(weights),
##                                                  threshold),
##                                       unchangedTree,actorTree)
##    enoughDoneeTree = createBranchTree(KeyedPlane(KeyedRow(weights),
##                                                  threshold),
##                                       unchangedTree,objTree)

    # Branch on being donor
    weights = {`keyStruct['amActor']`: 1.}
    donorTree = createBranchTree(KeyedPlane(KeyedRow(weights),0.5),
                                 unchangedTree,actorTree)
##                                 unchangedTree,enoughDonorTree)

    # Branch on being donee
    weights = {`keyStruct['amObject']`: 1.}
    doneeTree = createBranchTree(KeyedPlane(KeyedRow(weights),0.5),
                                 donorTree,objTree)
##                                 donorTree,enoughDoneeTree)
    
    return {'tree':doneeTree}

def genDisburseDyn(scale):
    """Generates the wealth dynamics for the disbursement of the
    public pool of wealth"""
    key = makeStateKey('actor','wealth')
    # Donor receives a portion of the total pool
    donorTree = createDynamicNode(key,{key: scale/float(agentCount())})
    # Donee loses all wealth
    doneeTree = createDynamicNode(key,{key:-1.})
    tree = createBranchTree(KeyedPlane({makeIdentityKey('actor'):1.},0.5),
                            donorTree,doneeTree)
    return {'tree':tree}

def genGoodDyn():
    weights = {keyConstant: 1.}
    return {'tree':createDynamicNode({'entity':'self',
                                      'feature':'goodExists'},weights)}
                                                           
def createGoals(uWealth):
    if not __GOOD__:
        uWealth = 1.
    goalList = [{'entity':'self',
                 'direction':'max',
                 'type':'state',
                 'feature':'wealth',
                 'weight':uWealth}]
    if __GOOD__:
        goalList.append({'entity':'Donee',
                         'direction':'max',
                         'type':'state',
                         'feature':'goodExists',
                         'weight':1.-uWealth})
    return goalList

def makeDonateEntry(lo,hi,label='',depth=1):
    entry = 'observation depth %d actor neighbor type donate amount [%f,%f]'\
            % (depth,lo,hi)
    if len(label) > 0:
        entry += ' label %s' % label
    return entry

def makePunishPolicy(punishmentThreshold):
    punish = '{"type":"punish","object":"neighbor",'\
             + '"amount":%f}' % (fines[len(fines)-1])
    wait = '{"type":"wait"}'
    policy = []
    # If neighbor donated enough, then do nothing
    entry = makeDonateEntry(punishmentThreshold-Interval.QUANTUM,
                            Interval.CEILING,'ifBig')
    entry += '-> %s' % wait
    policy.append(entry)
    # If neighbor donated too small an amount, then punish
    # by an appropriate amount
    entry = makeDonateEntry(Interval.FLOOR,
                            punishmentThreshold-Interval.QUANTUM,'ifSmall')
    entry += ' -> %s' % punish
    policy.append(entry)
    if punishmentThreshold > 0.:
        # If neighbor did nothing before, then punish the max amount
        act = punish
    else:
        # We're not ever punishing
        act =  wait
    policy.append('conjunction observation depth 1 actor neighbor type wait '\
                  +'label ifWait & negation observation depth 1 type disburse'\
                  +' -> %s' % act)
    return policy

def makeDonatePolicy(actions,threshold=0.):
    policy = []
    punishEntry = 'observation depth 1 type punish object self label ifPun'
    if len(actions) == 2:
        # This is how I play the game if I've just been punished
        policy.append('%s -> %s' % (punishEntry,actions['ifPun']))
        # This is how I play the game if I have not been punished
        policy.append('default -> %s' % (actions['default']))
    else:
        ifBig = makeDonateEntry(threshold-Interval.QUANTUM,
                                Interval.CEILING,'ifBig',2)
        ifSmall = makeDonateEntry(Interval.FLOOR,
                                  threshold-Interval.QUANTUM,'ifBig',2)
        # This is how I play the game if I've been punished after donating
        policy.append('conjunction %s & %s -> %s' % \
                      (punishEntry,ifBig,actions['ifPunBig']))
        # This is how I play the game if I've been punished after not
        # donating 
        policy.append('%s -> %s' % (punishEntry,actions['ifPunSmall']))
        # This is how I play the game if I've not been punished after
        # donating 
        policy.append('%s -> %s' % (ifBig,actions['ifNotPunBig']))
        # This is how I play the game if I've not been punished after
        # not  donating
        policy.append('default -> %s' % (actions['ifNotPunSmall']))
        
    return policy

def createPolicy(threshold):
    """Creates a policy for the pooler/disburser, with the threshold the cost
    of the public good (ignored if there is no explicit public good"""
    policy = []
    if __GOOD__:
        # Don't buy the good if already bought        
        policy.append('belief entities self state goodExists 0.5 1. -> '\
                      +'{"type":"wait"}')
        # Always buy the good if have more than the threshold
        policy.append('belief entities self state wealth %4.2f 1.0 -> '\
                      +'{"type":"buyGood"}' % (threshold-0.01))
        # Otherwise, do nothing
        policy.append('default -> {"type":"wait"}')
    else:
        # Give wealth away
        policy.append('default -> {"type":"disburse"}')
    return policy


def initialize(args={}):
    """Set the dynamic parameters of the class hierarchy."""
    default = classHierarchy['PublicGood']
    donor = classHierarchy['Donor']
    donee = classHierarchy['Donee']
    default['horizon'] = args['horizon']
    # Set the initial wealth
    donor['state']['wealth'] = args['wealth']/float(agentCount())
    # Set the utility function
    donor['goals'] = createGoals(0.2)
    # Set the space of actions to match the space of possible donation sizes
    actList = [{'type':'donate','object':['Donee']}]
    donor['actions'] += actList
    # Set the dynamics for each of these donation sizes
    dynamics = default['dynamics']['wealth']
    dynamics['donate'] = {'class':PWLDynamics,'args':genWealthDyn()}
    if __PUNISH__:
        # Add actions and dynamics for fines
        actList = [{'type':'punish','object':['neighbor'],
                    'amount':fines}]
        donor['actions'] += actList
        # Don't need to charge for punishment if using a fixed policy
        if args['punish'] != 'lookahead':
            args['cost'] = 0.
        dynFun = {'class':PWLDynamics,'args':genWealthDyn(args['cost'])}
        dynamics['punish'] = dynFun

    if __GOOD__:
        # Parameters required for a separate, fixed-price public good
        default['dynamics']['goodExists'] = {'buyGood':{'class':PWLDynamics,
                                                        'args':genGoodDyn()}}
        default['beliefs'][None]['goodExists'] = None
        donee['actions'] = [{'type':'buyGood','object':[]}]
    else:
        # Parameters required for a general pool division
        donee['actions'] = [{'type':'disburse','object':[],'amount':[]}]
        dynamics['disburse'] = {'class':PWLDynamics,
                                'args':genDisburseDyn(args['scale'])}

    if args['aggregate']:
	ideal = {'type':'donate','object':'donee',
		 'amount':args['ideal']*(agentCount()-1)}
    else:
	ideal = {'type':'donate','object':'donee',
		 'amount':args['ideal']}
    wait = {'type':'wait'}
    for name,model in donor['models'].items():
        if name == 'deliberate':
            model['goals'] = createGoals(1.)
            if args['punish'] == 'lookahead':
##                if args['aggregate']:
##                    model['policy'].insert(0,'observation depth 1 type donate actor neighbor amount [%f,1.] -> {"type":"wait"}' % (donations[len(donations)-1]-Interval.QUANTUM))
##                else:
##                    raise TypeError,'Unable to avoid punishing max donators under individual model'
                model['policy'].append('default -> {"type":"lookahead",'\
                                       +'"amount":3}')
            else:
                model['policy'] += makePunishPolicy(args['punishmentThreshold'])
        else:
            if name[1] == 'A':
                # Altruistic punisher
                policy = makePunishPolicy(args['punishmentThreshold'])
            else:
                # Egoistic punisher
                policy = makePunishPolicy(0.)
            if name[0] == 'A':
                # Altruistic donor
                punished = copy.copy(ideal)
                punished['amount'] /= 2.
                punished['amount'] = min(punished['amount'],Interval.CEILING)
                policy += makeDonatePolicy({'ifPunBig':wait,
                                            'ifPunSmall':ideal,
                                            'ifNotPunSmall':punished,
                                            'ifNotPunBig':ideal},
                                           args['ideal'])
            else:
                # Egoistic donor
                policy += makeDonatePolicy({'ifPunBig':wait,
                                            'ifPunSmall':ideal,
                                            'ifNotPunSmall':wait,
                                            'ifNotPunBig':ideal},
                                           args['ideal'])
            model['policy'] = policy
            # Goals are always the same for now
            model['goals'] = createGoals(1.)
        
    donee['models']['normal']['policy'] = createPolicy(0.8)
    # Set the type of policy
    if args['beta'] != 'deterministic':
        StochasticLookupAhead.beta = float(args['beta'])
        PublicGoodAgent.policyClass = StochasticLookupAhead
    # Set the type of network
    if args['network'] == 'random':
        PublicGoodAgents.fixedNetwork = None
    # Set type of mental models
    if args['aggregate']:
	PublicGoodAgent.mentalType = 'aggregate'
    else:
	PublicGoodAgent.mentalType = 'individual'

def usage(value=-1):
    sys.stderr.write('Supported arguments:\n')
    sys.stderr.write('-c|--cost <amt>\t\tPunishing another agent costs <amt>\n')
    sys.stderr.write('--horizon <T>\t\tAgents compute expected values over <T> games\n')
    sys.stderr.write('-l|--length <n>\t\tThe agents play <n> iterations of the game\n')
    sys.stderr.write('-p|--punish <policy>\tPunishment policy is either "fixed" or "lookahead"\n')
    sys.stderr.write('-s|--scale <num>\tDonations are scaled by <num> before disbursement\n')
    sys.stderr.write('-w|--wealth <amt>\tThe total wealth among agents is <amt> at start\n')
    sys.stderr.write('\n')
    sys.stderr.write('--beta <b>\t\tAgents use a stochastic lokahead policy with beta=<b>\n')
    sys.stderr.write('--beta deterministic\tAgents use a deterministic lokahead policy\n')
    sys.stderr.write('\n')
    sys.stderr.write('--network fixed\t\tUse a static assignment of neighbors\n')
    sys.stderr.write('--network random\tUse a dynamic, random assignment of neighbors\n')
    sys.stderr.write('\n')
    sys.stderr.write('--directory <name>\tSaves the data files in the directory <name>\n')
    sys.stderr.write('--save <name>\t\tSaves the *initial* game in file <name>\n')
    sys.stderr.write('\n')
    sys.stderr.write('-d|--debug <level>\tSets the output level of detail\n')
    sys.stderr.write('-h|--help\t\tPrints this message\n')
    sys.exit(value)
    
if __name__ == '__main__':
    import getopt
    import os
    import profile
    
    args = {'cost': 0.001,
            'debug': 1,
            'filename': '',
            'horizon':2,
            'punishmentThreshold':  .003,
            'ideal':.005,
            'scale' : 2.,
            'steps': 1,
            'punish':'lookahead',
            'wealth':.5,
            'beta':'deterministic',
            'network':'fixed',
	    'aggregate':1,
            'profile':None,
            'directory':os.environ['HOME']+'/python/teamwork/examples/games/'
            }

    try:
        optlist,cmdargs = getopt.getopt(sys.argv[1:],'gd:l:s:w:h:p:c:ai',
                                        ['debug=','OO=','PP=','OP=','PO=',
                                         'steps=','length=','wealth=',
                                         'horizon=','help','save=',
                                         'punish=','scale=','directory=',
                                         'beta=','network=','cost=',
					 'aggregate','individual','profile'])
    except getopt.error:
        usage()
    for option in optlist:
        if option[0] == '-g':
            __GOOD__ = 1
        elif option[0] == '-c' or option[0] == '--cost':
            args['cost'] = float(option[1])
        elif option[0] == '-d' or option[0] == '--debug':
            args['debug'] = int(option[1])
        elif option[0] == '-p' or option[0] == '--punish':
            args['punish'] = int(option[1])
        elif option[0] == '--OO':
            population['OptOptDonor'] = int(option[1])
        elif option[0] == '--OP':
            population['OptPesDonor'] = int(option[1])
        elif option[0] == '--PO':
            population['PesOptDonor'] = int(option[1])
        elif option[0] == '--PP':
            population['PesPesDonor'] = int(option[1])
        elif option[0] == '-l' or option[0] == '--length':
            args['steps'] = int(option[1])
        elif option[0] == '-s' or option[0] == '--scale':
            args['scale'] = float(option[1])
        elif option[0] == '-h' or option[0] == '--help':
            usage(0)
        elif option[0] == '--horizon':
            args['horizon'] = int(option[1])
        elif option[0] == '--save':
            args['filename'] = option[1]
        elif option[0] == '--directory':
            args['directory'] = option[1]
        elif option[0] == '-w' or option[0] == '--wealth':
            args['wealth'] = float(option[1])
        elif option[0] == '--beta':
            args['beta'] = option[1]
        elif option[0] == '--network':
            args['network'] = option[1]
        elif option[0] == '-a' or option[0] == '--aggregate':
            args['aggregate'] = 1
        elif option[0] == '-i' or option[0] == '--individual':
            args['aggregate'] = None
        elif option[0] == '--profile':
            args['profile'] = 1
        else:
            usage()
    initialize(args)
    dynamics = classHierarchy['PublicGood']['dynamics']
    if args['profile']:
        import hotshot
        prof = hotshot.Profile('intialization.prof')
        prof.runcall(PublicGoodTerminal,entities=None,
                     classes=classHierarchy,dynamics=dynamics,
                     file=None,debug=args['debug'])
        prof.close()
    else:
        shell = PublicGoodTerminal(None,classHierarchy,dynamics,
                                   None,args['debug'])
    sys.stderr.write('Initialization complete.\n')
    script = []
    results = []
    if len(args['filename']) > 0:
        shell.save(args['filename'])
    # Set up log file
    fileroot = args['directory']+'/OO%dOP%dPO%dPP%d' \
               % (population['OptOptDonor'],population['OptPesDonor'],
                  population['PesOptDonor'],population['PesPesDonor'])
    fields = ['amount','amount','mean','wealth','punishIfDon<',
              'donateIfPunBig','donateIfNotPunBig',
              'donateIfPunSmall','donateIfNotPunSmall',
              'donateIfSmallDiff','donateIfBigDiff']
    # Iterate game
    output = []
    for t in range(2*args['steps']+1):
        results = []
        if t > 0:
            sys.stderr.write('Iteration %d' % ((t+1)/2))
            if t%2 == 1:
                sys.stderr.write(': Donate\n')
            else:
                sys.stderr.write(': Punish\n')
            if args['profile']:
                prof = hotshot.Profile('step.prof')
                prof.run('data  = shell.step(1,results)[0]')
                prof.close()
            else:
                data  = shell.step(1,results)[0]
            del data['delta']
            for result in data.values():
                for key in result.keys():
                    if key == 'decision':
                        if result[key]['type'] == 'wait':
                            result[key] = 0.
                        else:
                            result[key] = result[key]['amount']
                    else:
                        del result[key]
        else:
            data = {}
        # Let's save some interesting results
        for agent in shell.entities.members():
            if agent.name != 'Public':
                if not data.has_key(agent.name):
                    data[agent.name] = {}
                data[agent.name]['wealth'] = agent.getState('wealth').mean()
                models = agent.extractModels().values()
                data[agent.name].update(models[0])
        output.append(data)
##        shell.displayResult('step',string.join(results,'\n'))
    shell.executeCommand('quit')
##    script = [
####        'save %s/python/teamwork/examples/games/publicgood.scn' \
####        % (os.environ['HOME']),
##        'step %d' % (2*steps),
##        'quit'
##        ]
##    for cmd in script:
##        shell.executeCommand(cmd)
    sys.stderr.write('Saving data...')
    shell.mainloop()
    for field in fields:
        if field == 'amount':
            donFile = open(fileroot+'D','w')
            punFile = open(fileroot+'P','w')
            for index in range(agentCount()):
                name = '%s%d' % (namePrefix,index)
                stage = None
                for step in output[1:]:
                    content = '\t%6.4f' % (step[name]['decision'])
                    if stage:
                        punFile.write(content)
                    else:
                        donFile.write(content)
                    stage = not stage
                donFile.write('\n')
                punFile.write('\n')
            donFile.close()
            punFile.close()
        elif field == 'mean':
            donFile = open(fileroot+'DMean','w')
            punFile = open(fileroot+'PMean','w')
            stage = None
            for step in output[1:]:
                totalP = 0.
                totalD = 0.
                for index in range(agentCount()):
                    if stage:
                        totalP += step[name]['decision']
                    else:
                        totalD += step[name]['decision']
                if stage:
                    punFile.write('%6.4f\n' % (totalP/float(agentCount())))
                else:
                    donFile.write('%6.4f\n' % (totalD/float(agentCount())))
                stage = not stage
            donFile.close()
            punFile.close()
        else:
            donFile = open(fileroot+field,'w')
            for index in range(agentCount()):
                name = '%s%d' % (namePrefix,index)
                for step in output:
                    if field[-4:] == 'Diff':
                        root = field[:-4]
                        if root[-3:] == 'Big':
                            donation = root[-3:]
                            root = root[:-3]
                        else:
                            donation = root[-5:]
                            root = root[:-5]
                        value = step[name][root+'Pun'+donation]\
                                -step[name][root+'NotPun'+donation]
                    else:
                        value = step[name][field]
                    try:
                        content = '\t%6.4f' % (value)
                    except TypeError:
                        raise TypeError,'%s = %s' % (value)
                    donFile.write(content)
                donFile.write('\n')
            donFile.close()
    
    sys.stderr.write('Done.\n')
    if args['profile']:
        stats = hotshot.stats.load('step.prof')
        stats.print_stats()
