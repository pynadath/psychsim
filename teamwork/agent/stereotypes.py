"""Mental models for stereotyping agents
@author: David V. Pynadath <pynadath@isi.edu>
"""
import math
import string
import copy

from teamwork.reward.goal import PWLGoal
from GoalBased import GoalBasedAgent
from teamwork.utils.Debugger import Debugger
from teamwork.math.Keys import ModelKey
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.probability import Distribution

class Stereotyper(GoalBasedAgent):
    """Mix-in class that supports stereotypical mental models
    @cvar defaultModelChange: Class-wide default for L{modelChange} attribute
    @type defaultModelChange: boolean
    @ivar modelChange: Flag that specifies whether this agent will change its mental models or not
    @type modelChange: boolean
    @ivar model: the current stereotype that this agent is following
          - I{name}: the name of the current stereotype
          - I{fixed}: a flag indicating whether this model is subject to change
    @type model: dictionary
    @ivar decay: the parameter of the exponential distribution governing the decay of probability with suboptimality of actions (when evaluating the likelihood of an action given a candidate mental model)
    @type decay: float
    """
    defaultModelChange = True
    
    def __init__(self,name):
        GoalBasedAgent.__init__(self,name)
        self.decay = 1.
        self.modelChange = self.defaultModelChange
        self.model = None
        self.models = {}

    def newModel(self,name=None):
        """Creates a new mental model (defaulting to current agent values) under the given label
        @type name: str
        @return: the mental model created
        @rtype: dict
        """
        if name is None:
            index = 0
            while self.models.has_key(str(index)):
                index += 1
            name = str(index)
        if self.models.has_key(name):
            raise NameError,'Model %s already exists' % (name)
        else:
            model = {'goals': copy.copy(self.goals),
                     'name': name,
                     'horizon': None,
                     }
            value = hash(name)
            if value < 0:
                model['value'] = -float('.%d' % (-value))
            else:
                model['value'] = float('.%d' % (value))
            self.models[name] = model
            return model
            
    def initialStateEstimator(self):
        beliefs = GoalBasedAgent.initialStateEstimator(self)
        beliefs['models'] = Distribution({KeyedVector():1.})
        return beliefs
    
    def preComStateEstimator(self,beliefs,observations,action,epoch=-1,debug=None):
        """
        @return: the hypothetical model changes (plus any other effects)
        """
        delta = GoalBasedAgent.preComStateEstimator(self,beliefs,observations,action,epoch,debug)
        if beliefs is None:
            models = self.beliefs['models']
        else:
            models = beliefs['models']
        delta['models'] = Distribution({KeyedVector(): 1.})
        for key in filter(lambda k: isinstance(k,ModelKey),models.domain()[0].keys()):
            # Extract prior probability over possible mental models
            prob = models.getMarginal(key)
            if observations.has_key(key['entity']):
                # Update model based on new observation
                option = observations[key['entity']]
                values = {}
                entity = self.getEntity(key['entity'])
                for name,model in entity.models.items():
                    if prob[model['value']] > 1e-8:
                        # Here's a possible mental model with nonzero likelihood
                        entity.setModel(name)
                        best = None
                        values.clear()
                        # Compute values of possible actions given candidate model
                        for alternative in entity.actions.getOptions():
                            if beliefs:
                                state = copy.deepcopy(beliefs[key['entity']])
                            else:
                                state = entity.getAllBeliefs()
                            value = entity.policy.actionValue(state,alternative)[0]
                            value = value.expectation()
                            values[entity.makeActionKey(alternative)] = value
                            if best is None or value > best:
                                best = value
                        # Convert values into distribution over possible actions
                        for alternative,value in values.items():
                            values[alternative] = self.decay*math.exp(-self.decay*(best-value))
                        # Normalize
                        normalization = sum(values.values())
                        # Probability of observed action
                        prob[model['value']] *= values[entity.makeActionKey(option)]/normalization
                prob.normalize()
            delta['models'].join(key,prob)
        return delta

    def applyChanges(self,beliefs,delta,descend=1,rewind=0):
        """Takes changes and modifies the given beliefs accordingly
        @param descend: If the descend flag is set, then the recursive changes in the delta will also be applied.
        @type descend: C{boolean}
        @param rewind: If the rewind flag is set, then the changes will be undone, instead of applied.
        @type rewind: C{boolean}"""
        GoalBasedAgent.applyChanges(self,beliefs,delta,descend,rewind)
        if delta.has_key('models'):
            beliefs['models'] = delta['models']

    def getAllBeliefs(self,recurse=True):
        beliefs = GoalBasedAgent.getAllBeliefs(self,recurse)
        beliefs['models'] = self.beliefs['models']
        return beliefs

    def setModelBeliefs(self,entity,value):
        """Updates my uncertain beliefs about possible mental models of others
        @type entity: str
        @type value: L{Distribution}
        """
        key = ModelKey({'entity':entity})
        mapping = Distribution()
        for name in value.domain():
            mapping[self.getEntity(entity).models[name]['value']] = value[name]
        frozen = self.beliefs['models'].unfreeze()
        self.beliefs['models'].join(key,mapping)
        if frozen:
            self.beliefs['models'].freeze()
        
    def updateModels(self,actions,debug):
        """Updates the mental models in response to the given dictionary of actions"""
        delta = {}
        for act in actions.values():
            newModel = self.updateModel(act,debug)
            if newModel:
                actor = self.getEntity(act['actor'])
                if delta.has_key(actor.name):
                    delta[actor.name]['model'] = newModel
                else:
                    delta[actor.name] = {'model':newModel}
        return delta

    def updateModel(self,actual,debug=Debugger()):
        """Updates the mental model in response to the single action"""
        try:
            actor = self.getEntity(actual[0]['actor'])
        except KeyError:
            return None
        if (not actor.model) or actor.model['fixed']:
            return None
        # Check for expectation violation
        predicted = actor.applyPolicy(debug=debug-1)[0]
        if `actual` == `predicted`:
            return None
        filter = lambda e,a=actor:e.name==a.name
        debug.message(6,self.ancestry()+' observed "'+`actual`+\
                      '" instead of "'+`predicted`)
        # Expectation violation, so re-evaluate model choice
        projection = copy.deepcopy(self)
        projection.freezeModels()
        value,explanation = projection.acceptability(actor,0.0,filter,debug)
        best = {'model':actor.model['name'],'value':value,
                'explanation':explanation}
        best['previous model'] = best['model']
        best['previous value'] = best['value']
        debug.message(5,'Current model: '+actor.model['name']+' = '+`value`)
        for model in actor.models:
            if model != best['model']:
                projection.getEntity(actor).setModel(model,1)
                value,explanation = projection.acceptability(actor,0.0,
                                                             filter,debug)
                debug.message(5,'Alternate model: '+model+' = '+`value`)
                if value > best['value']:
                    best['model'] = model
                    best['value'] = value
                    best['explanation'] = explanation
        if best['model'] == actor.model['name']:
            debug.message(5,'No model change')
            return None
        else:
            # Model change!
##            actor.setModel(best['model'])
            debug.message(7,'Model change: '+best['model'])
            return best

    def step(self,actDict,state=None,horizon=None,debug=False):
        """Projects a single step, considering uncertainty over mental models of any agents who are acting in this step
        """
        result = []
        cache = {}
        # Generate necessary mental models to execute
        for belief in state['models'].domain():
            actions = copy.copy(actDict)
            cached = []
            uncached = []
            for name in actions.keys():
                # Extract entity's state from current beliefs
                try:
                    entity = self.getEntity(name)
                except KeyError:
                    if debug:
                        print 'No belief about',name
                    continue
                try:
                    entity.setModel(belief[ModelKey({'entity':name})])
                    model = entity.model['name']
                    if debug:
                        print name,'is modeled as',model
                except KeyError:
                    # No mental model to apply
                    model = None
                try:
                    # Have we already determined what this agent will do in this model?
                    exp = cache[name][model]
                    actions[name] = exp['decision']
                    cached.append((name,exp))
                except KeyError:
                    uncached.append((name,model))
            step = GoalBasedAgent.step(self,actDict=actions,state=state,
                                       horizon=horizon,debug=debug)
            if step:
                branch = step[0]
                # Cache expected decisions
                for name,model in uncached:
                    exp = branch['breakdown'][name]
                    try:
                        cache[name][model] = exp
                    except KeyError:
                        cache[name] = {model: exp}
                # Fill in explanations of cached decisions
                for name,exp in cached:
                    branch['breakdown'][name] = exp
                branch['models'] = belief
                branch['probability'] = state['models'][belief]
                result.append(branch)
        return result

    # Belief model methods

    def getModel(self,entity,vector=None):
        """
        @type entity: str
        @type vector: L{KeyedVector}
        @return: a model string corresponding to the value of the mental model of the given entity in the given vector
        @rtype: str
        """
        if vector is None:
            vector = self.beliefs['models']
        return self.getEntity(entity).identifyModel(vector)

    def printWorld(self,vector):
        """
        Outputs a string representation of the given vector (including models of others)
        """
        print vector.getState().simpleText()
        for agent in self.entities.members():
            try:
                model = agent.models[agent.identifyModel(vector)]
            except KeyError:
                continue
            assert len(model['beliefs']) == 1
            print '%s (%s): %s' % (agent.name,model['horizon'],
                                   model['beliefs'][0].simpleText())

    def identifyModel(self,vector):
        value = vector[ModelKey({'entity':self.name})]
        return self.float2model(value)

    def float2model(self,value):
        """Identifies the model indexed by the given float
        """
        for name,model in self.models.items():
            if model['value'] == value:
                return name
        else:
            raise ValueError,'Unknown model symbol %f not found.' % (value)

        
    def findBelief(self,vector,horizon=None,name=None,create=True):
        """
        @param vector: the belief vector to find
        @type vector: L{KeyedVector}
        @param name: the name of the model to examine (by default, C{None} to indicate that all models should be searched)
        @type name: str
        @param create: if C{True}, then create a new model if no matching one is found (default is C{True})
        @type create: bool
        @return: the found/created mental model
        @rtype: dict
        """
        if name:
            # We're given a name, gotta go with it
            try:
                model = self.models[name]
            except KeyError:
                # No existing model of that name, so create one
                if create:
                    model = self.newModel(name)
                    model['beliefs'] = []
                    model['horizon'] = horizon
                else:
                    raise ValueError,'Unable to find mental model matching beliefs %s' % (vector.simpleText())
            if not vector in model['beliefs']:
                model['beliefs'].append(model)
        else:
            # No name given, so search
            for model in self.models.values():
                if vector in model['beliefs'] and model['horizon'] == horizon:
                    break
            else:
                if create:
                    # Create new model with auto-generated name
                    model = self.newModel()
                    model['beliefs'] = [vector]
                    model['horizon'] = horizon
                else:
                    raise ValueError,'Unable to find model with beliefs %s, horizon %s' % \
                        (vector.simpleText(),horizon)
        return model

    def setModel(self,model,fixed=False):
        """Applies the named mental model to this entity"""
        if model:
            try:
                myModel = self.models[model]
            except KeyError:
                # Maybe this is float value of model
                for name in self.models.keys():
                    if self.models[name]['value'] == model:
                        myModel = self.models[name]
                        break
                else:
                    raise NameError,'%s has no model "%s"' % (self.ancestry(),model)
                model = name
            self.model = {'name':model,'fixed':fixed}
        else:
            myModel = None
        if myModel:
            self.goals = myModel['goals']

    def generateModels(self,horizon=None,useHorizon=False):
        """
        Generates a mental model state space for this agent based on all
        the possible beliefs it may have during the given horizon
        @type horizon: int
        @warning: does not identify observations that have 0 probability
        """
        if horizon is None:
            horizon = self.policy.getHorizon()
        self.models.clear()
        # Identify current beliefs
        if not self.entities.worlds:
            self.entities.generateWorlds(horizon,self.name)
        belief = self.entities.state2world(self.beliefs)
        if useHorizon:
            nextHorizon = horizon
        else:
            nextHorizon = None
        self.findBelief(belief,nextHorizon,create=True)
        nodes = [belief]
        # Find reachable beliefs
        for t in range(horizon):
            envelope = nodes
            nodes = []
            for node in envelope:
                option = self.policy.execute(node)[0]
                for omega in self.getOmega():
                    action = self.makeActionKey(option)
                    O = self.estimators[omega][node]['values'][action]
                    new = O*node
                    new *= 1./sum(new.getArray())
                    if useHorizon:
                        nextHorizon = horizon-1-t
                    else:
                        nextHorizon = None
                    try:
                        self.findBelief(new,nextHorizon,create=False)
                    except ValueError:
                        # No matching belief.  Create new one
                        self.findBelief(new,nextHorizon,create=True)
                        nodes.append(new)

    def nextModel(self,current,action,omega):
        """
        @return: the model resulting from taking the given action from the given model (or vector) and making the given observation
        @rtype: dict
        """
        if isinstance(current,str):
            current = self.models[current]
        elif isinstance(current,KeyedVector):
            current = self.identifyModel(current)
        assert len(current['beliefs']) == 1
        beliefs = current['beliefs'][0]
        SE = self.getEstimator()[omega]
        numerator = SE[beliefs]['values'][self.makeActionKey(action)]
        vector = numerator*beliefs
        vector *= 1./sum(vector.getArray())
        if current['horizon'] is None:
            model = self.findBelief(vector,current['horizon'],create=False)
        else:
            model = self.findBelief(vector,current['horizon']-1,create=False)
        return model

    def setPolicies(self,depth,horizon):
        GoalBasedAgent.setPolicies(self,depth,horizon)
        if depth > 0:
            # Generate possible mental models for others
            for belief in filter(lambda e: e.name != self.name,
                                 self.entities.activeMembers()):
                real = self.world[belief.name]
                while not real.parent is None:
                    real = real.parent.world[belief.name]
                belief.beliefs['models'] = real.beliefs['models']
                belief.generateModels(horizon,False)
                # Compute my belief about mental models
                vector = belief.entities.state2world(belief.beliefs)
                model = belief.findBelief(vector,None,create=False)
                distribution = Distribution()
                for other in belief.models.values():
                    if other['value'] == model['value']:
                        distribution[other['value']] = 1.
                    else:
                        distribution[other['value']] = 0.
                self.beliefs['models'].join(ModelKey({'entity': belief.name}),
                                            distribution)

    def decideModel(self,world):
        """
        @return: the decision by the agent under the model specified in the given world
        """
        try:
            model = self.models[self.identifyModel(world)]
        except KeyError:
            return GoalBasedAgent.decideModel(self,world)
        if model['horizon'] is None:
            table = self.policy.getTable()
        else:
            try:
                table = self.policy.getTable(horizon=model['horizon'])
            except IndexError:
                table = self.policy.getTable()
        assert len(model['beliefs']) == 1
        return table.getRHS(model['beliefs'][0])

    def verifyDecision(self,world,decision,debug=False):
        """
        @param world: the vector including the model specification
        @type world: L{KeyedVector}
        @param decision: the action under consideration
        @type decision: L{Action}[] or str
        @return: C{True} iff this agent could possibly make the given decision in the given world
        @rtype: bool
        """
        if not isinstance(decision,str):
            decision = self.makeActionKey(decision)
        modelIndex = self.identifyModel(world)
        model = self.models[modelIndex]
        # Check whether action matches policy specification
        for oldBeliefs in model['beliefs']:
            if model['horizon'] is None:
                table = self.policy.getTable()
            else:
                try:
                    table = self.policy.getTable(horizon=model['horizon'])
                except IndexError:
                    table = self.policy.getTable()
            rhs = table.getRHS(oldBeliefs)
            if rhs == decision:
                # Possible to generate this action
                if debug:
                    print self.name,'would',decision
                    print 'under model:',model['name']
                    print 'horizon:',model['horizon']
                    print 'beliefs:',oldBeliefs.simpleText()
                return True
        if debug:
            print self.name,'would not',decision
            print 'under model:',model['name']
            print 'horizon:',model['horizon']
            print 'beliefs:',','.join(map(lambda v: v.simpleText(),
                                          model['beliefs']))
        return False
        
    def freezeModels(self):
        """Lock the model of this agent and all mental models it may have"""
        self.modelChange = None
##        if self.model:
##            self.model['fixed'] = True
        for entity in self.getEntityBeliefs():
            try:
                entity.freezeModels()
            except AttributeError:
                pass

    def __copy__(self,new=None):
        if not new:
            new = GoalBasedAgent.__copy__(self)
        new.models.update(self.models)
        new.model = None
        new.modelChange = self.modelChange
        if self.model:
            new.setModel(self.model['name'],self.model['fixed'])
        return new

    def __str__(self):
        rep = GoalBasedAgent.__str__(self)
        if self.model and self.model['name']:
            rep = rep + '\tModel: '+self.model['name']+'\n'
        return rep
            
    def __xml__(self):
        doc = GoalBasedAgent.__xml__(self)
        root = doc.createElement('models')
        doc.documentElement.appendChild(root)
        if self.modelChange:
            doc.documentElement.setAttribute('modelChange','true')
        else:
            doc.documentElement.setAttribute('modelChange','false')
        if self.model:
            if isinstance(self.model,dict):
                if self.model['name']:
                    doc.documentElement.setAttribute('modelName',
                                                     self.model['name'])
                if self.model['fixed']:
                    doc.documentElement.setAttribute('modelFixed','True')
                else:
                    doc.documentElement.setAttribute('modelFixed','False')
            else:
                doc.documentElement.setAttribute('modelName',self.model)
        node = doc.createElement('beliefs')
        if self.beliefs.has_key('models'):
            node.appendChild(self.beliefs['models'].__xml__().documentElement)
        root.appendChild(node)
        for name,model in self.models.items():
            node = doc.createElement('model')
            node.setAttribute('name',name)
            node.setAttribute('value',str(model['value']))
            node.appendChild(model['goals'].__xml__().documentElement)
            if model.has_key('beliefs'):
                for vector in model['beliefs']:
                    node.appendChild(vector.__xml__().documentElement)
            if not model['horizon'] is None:
                node.setAttribute('horizon',str(model['horizon']))
            root.appendChild(node)
        return doc

    def parse(self,element):
        GoalBasedAgent.parse(self,element)
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE \
                   and child.tagName == 'models':
                node = child.firstChild
                while node:
                    if node.nodeType == node.ELEMENT_NODE and \
                           node.tagName == 'model':
                        name = str(node.getAttribute('name'))
                        model = {'goals': Distribution(),
                                 'value': float(node.getAttribute('value')),
                                 'beliefs': []}
                        try:
                            model['horizon'] = int(node.getAttribute('horizon'))
                        except ValueError:
                            model['horizon'] = None
                        subNode = node.firstChild
                        while subNode:
                            if subNode.nodeType == subNode.ELEMENT_NODE:
                                if subNode.tagName == 'distribution':
                                    model['goals'].parse(subNode,PWLGoal)
                                else:
                                    assert subNode.tagName == 'vector'
                                    vector = KeyedVector()
                                    vector = vector.parse(subNode)
                                    model['beliefs'].append(vector)
                            subNode = subNode.nextSibling
                        self.models[name] = model
                    elif node.nodeType == node.ELEMENT_NODE and \
                           node.tagName == 'beliefs':
                        subNode = node.firstChild
                        while subNode and \
                                  subNode.nodeType != subNode.ELEMENT_NODE:
                            subNode = subNode.nextSibling
                        if subNode:
                            self.beliefs['models'].parse(subNode,KeyedVector)
                    node = node.nextSibling
            child = child.nextSibling
        if string.lower(str(element.getAttribute('modelChange'))) == 'true':
            self.modelChange = True
        else:
            self.modelChange = False
        name = str(element.getAttribute('modelName'))
        if len(name) > 0:
            if string.lower(str(element.getAttribute('modelFixed'))) == 'true':
                self.setModel(name,True)
            else:
                self.setModel(name,False)
            
    def generateSpace(self,granularity=10,goals=None,weightList=None,availableWeight=1.):
        """Generates a space of possible goal weights for this agent
        @param granularity: the number of positive goal weights to consider for each goal (i.e., a granularity of I{n} will generate values of [0,1/I{n},2/I{n}, ..., 1].  This is a dictionary of numbers, indexed by individual goals.
        @type granularity: dict
        @param goals: the list of goals left to consider (typically omitted, the default is the current set of goals for this agent)
        @type goals: L{teamwork.reward.MinMaxGoal.MinMaxGoal}[]
        @param weightList: the initial list of possible goal weightings, to be extended in combination with the newly generated goal weightings (typically omitted)
        @type weightList: dict
        @param availableWeight: the weight to be distributed across the possible goals (typically omitted, the default is 1)
        @type availableWeight: float
        @return: all possible combinations of goal weights that sum to the C{availableWeight}
        @rtype: (dict:L{teamwork.reward.MinMaxGoal.MinMaxGoal}S{->}float)[]
        """
        if goals is None:
            goals = self.getGoals()
            if len(goals) == 0:
                return [{}]
            goals.sort()
        if weightList is None:
            weightList = [{}]
        if len(goals) == 1:
            # Only one goal left, so it must have whatever leftover weight is available
            for weighting in weightList:
                weighting[goals[0]] = availableWeight
            return weightList
        result = []
        weight = 0.
        while weight < availableWeight+.0001:
            newList = []
            for weighting in weightList:
                weighting = copy.copy(weighting)
                weighting[goals[0]] = weight
                newList.append(weighting)
            result += self.generateSpace(granularity,goals[1:],newList,
                                         availableWeight-weight)
            weight += 1./float(granularity-1)
        return result

    def reachable(self,weightList,granularity,neighbors=None):
        if neighbors is None:
            neighbors = {}
        reachable = {0:True}
        toExplore = [0]
        while len(toExplore) > 0:
            index1 = toExplore.pop()
            try:
                neighbors[index1]
            except KeyError:
                neighbors[index1] = []
                weight1 = weightList[index1]
                weight2 = copy.copy(weight1)
                for goal1 in self.getGoals():
                    delta = 1./float(granularity-1)
                    if weight1[goal1] > delta/2.:
                        weight2[goal1] -= delta
                        for goal2 in self.getGoals():
                            if goal1 != goal2 and weight2[goal2] < 1.-delta/2.:
                                weight2[goal2] += delta
                                for index2 in range(len(weightList)):
                                    if self.weightEqual(weight2,
                                                        weightList[index2]):
                                        neighbors[index1].append(index2)
                                        break
                                weight2[goal2] -= delta
                        weight2[goal1] += delta
                neighbors[index1].sort()
            for index2 in neighbors[index1]:
                if not reachable.has_key(index2):
                    reachable[index2] = True
                    toExplore.append(index2)
        return len(reachable) == len(weightList)
    
    def weightEqual(self,weight1,weight2):
        for goal in self.getGoals():
            if abs(weight1[goal]-weight2[goal]) > 0.0001:
                return False
        return True
    
    def clusterSpace(self,granularity,weightList=None,debug=None,
                     finish=None,interrupt=None):
        if debug is None:
            debug = lambda msg: None
        # Generate all candidate points in goal space
        if weightList is None:
            weightList = self.generateSpace(granularity)
        goals = self.getGoals()
        goals.sort()
        weightDict = {}
        for index in range(len(weightList)):
            weighting = weightList[index]
            key = string.join(map(lambda k:'%6.4f' % \
                                  (abs(weighting[k])),goals))
            weightDict[key] = index
        # Generate the policies for all candidate points, as well as fill in
        # adjacency matrix
        ruleSets = []
        neighbors = {}
        if not self.reachable(weightList,granularity,neighbors):
            raise UserWarning
##         delta = 1./float(granularity-1)
        for index in range(len(weightList)):
            weighting = weightList[index]
            debug((index,'Generating'))
##             # Find neighboring points in goal space
##             for goal,value in weighting.items():
##                 if value > delta/2.:
##                     for other in weighting.keys():
##                         if other != goal:
##                             newWeighting = copy.copy(weighting)
##                             newWeighting[goal] -= delta
##                             newWeighting[other] += delta
##                             key = string.join(map(lambda k:'%6.4f' % \
##                                                   (abs(newWeighting[k])),
##                                                   goals))
##                             try:
##                                 newIndex = weightDict[key]
##                             except KeyError:
##                                 print weightDict.keys()
##                                 raise UserWarning,key
##                             if newIndex >= 0:
##                                 try:
##                                     neighbors[index][newIndex] = True
##                                 except KeyError:
##                                     neighbors[index] = {newIndex: True}
##                                 try:
##                                     neighbors[newIndex][index] = True
##                                 except KeyError:
##                                     neighbors[newIndex] = {index: True}
            # Compute the policy at this point
            self.setGoals(weighting)
            self.policy.reset()
            rules = self.policy.compileRules(horizon=1,interrupt=interrupt)
##             print rules[1].values()
##             attr1,attr2 = filter(lambda v:not isinstance(v,bool),
##                                  rules[1].values())
##             print attr1.weights.getArray()
##             print attr2.weights.getArray()
##             print sum(abs(attr1.weights.getArray()-attr2.weights.getArray()))
##             print attr1.compare(attr2)
##             if index >= 0:
##                 raise UserWarning
            if rules:
                debug((index,'%d Rules' % (len(rules[0]))))
                ruleSets.append(rules)
            if interrupt and interrupt.isSet():
                return
##         for index in range(len(weightList)):
##             try:
##                 neighbors[index] = neighbors[index].keys()
##             except KeyError:
##                 neighbors[index] = []
##             neighbors[index].sort()
        # Cluster points goal space that have equivalent policies
        distinct = {}
        equivalence = {}
        for myIndex in range(len(weightList)):
            if interrupt and interrupt.isSet():
                return
            # Keep track of comparisons already made
            distinct[myIndex] = {}
            # Consider only those neighbors we haven't already covered
            myNeighbors = filter(lambda i: i>myIndex,neighbors[myIndex])
            # Find the base equivalent for this rule set
            original = myIndex
            while equivalence.has_key(myIndex):
                myIndex = equivalence[myIndex]
            if original != myIndex:
                debug((original,'= %d' % (myIndex)))
            else:
                debug((original,'Unique'))
            myRules = ruleSets[myIndex][0]
            for yrIndex in myNeighbors:
                # Find the base equivalent for the rule set to compare against
                while yrIndex > myIndex and equivalence.has_key(yrIndex):
                    yrIndex = equivalence[yrIndex]
                if distinct[myIndex].has_key(yrIndex):
                    # Already shown that they are not equal
                    continue
                elif yrIndex <= myIndex:
                    # We've already done this comparison
                    continue
                yrRules = ruleSets[yrIndex][0]
                if rulesEqual(myRules,yrRules):
                    # All the rules have equivalents
                    equivalence[yrIndex] = myIndex
                else:
                    # The rule sets differed in at least one way
                    distinct[myIndex][yrIndex] = True

        # Extract partition on goal space, as well as abstract adjacency
        # matrix
        adjacency = {}
        for myIndex in range(len(weightList)):
            myNeighbors = neighbors[myIndex]
            while equivalence.has_key(myIndex):
                myIndex = equivalence[myIndex]
            if not adjacency.has_key(myIndex):
                adjacency[myIndex] = {}
            for yrIndex in myNeighbors:
                while equivalence.has_key(yrIndex):
                    yrIndex = equivalence[yrIndex]
                if myIndex != yrIndex:
                    adjacency[myIndex][yrIndex] = True
        unique = adjacency.keys()
        unique.sort()
        for myIndex in unique:
            myNeighbors = adjacency[myIndex].keys()
            myNeighbors.sort()
            print myIndex,myNeighbors
            adjacency[myIndex]['_policy'] = ruleSets[myIndex]
        if finish:
            finish(adjacency)
        debug((-1,None))

def rulesEqual(myRules,yrRules):
    for myRule in myRules:
        # Look for a matching rule in yrRules
        for yrRule in yrRules:
            if len(yrRule) != len(myRule):
                # Different # of rules, these two rules do not match
                continue
            for attr,val in myRule.items():
                if not yrRule.has_key(attr):
                    # Missing key, these two rules do not match
                    break
                elif val != yrRule[attr]:
                    # Different attribute value, these two rules do not match
                    break
            else:
                # Rules match on every attribute
                break
        else:
            # No equivalent rule
            return False
    return True
