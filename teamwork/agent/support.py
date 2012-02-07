"""
Defines dynamics binary relationships between agents
"""
import copy

from GoalBased import GoalBasedAgent
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.Keys import LinkKey
from teamwork.dynamics.pwlDynamics import PWLDynamics

class Supporter(GoalBasedAgent):
    """Mix-in class that enables and updates support relationships
    @cvar supportLimit: the maximum distance allowed between the goals as stated in another entity's messages and one's own beliefs, when determining whether that entity's messages are in support of one's current beliefs
    @type supportLimit: float
    @ivar links: the current dynamic relationship values
    @type links: L{KeyedVector}
    @ivar linkTypes: list of current dynamic relationship types
    @type linkTypes: str[]
    @ivar linkDynamics: the decision tree defining the effects on the dynamic relationship values, indexed by link type, then by action type
    @type linkDynamics: strS{->}strS{->}PWLDynamics
    """

    _supportFeature = 'likes'
    _trustFeature = 'trusts'
    supportWeights = {'support':0.1,
                      'legitimacy':0.1,
                      'past':0.5,
                      'future':0.3
                      }
    supportLimit = 0.5

    def __init__(self,name=''):
        # Kind of hacky way to make sure we don't do this superclass
        # constructor more than once 
        try:
            self.goals
        except AttributeError:
            GoalBasedAgent.__init__(self,name)
        self.links = KeyedVector()
        self.linkDynamics = {}
        self.linkTypes = [self._supportFeature,self._trustFeature]
        
    # Methods for accessing/manipulating entity state

    def getLinkKey(self,relation,entity):
        """
        @return: the vector index for this entity's relation to the given
        entity
        @rtype: L{LinkKey}
        """
        return LinkKey({'subject':self.name,
                        'verb':relation,
                        'object':entity})
    
    def getLink(self,relationship,entity):
        """
        @param relationship: the dynamic relationship (e.g., 'likes',
        'trusts') to evaluate
        @param entity: the entity who is the object of the
        relationship (e.g., the entity being liked or trusted)
        @type relationship: str
        @type entity: str
        @return: the current value of the link
        @rtype: float
        """
        key = self.getLinkKey(relationship,entity)
        try:
            return self.links[key]
        except KeyError:
            return 0.

    def setLink(self,relationship,entity,value):
        """
        @param relationship: the dynamic relationship (e.g., 'likes',
        'trusts') to evaluate
        @param entity: the entity who is the object of the
        relationship (e.g., the entity being liked or trusted)
        @type relationship: str
        @type entity: str
        @param value: the new value for my trust level
        @type value: float
        """
        key = self.getLinkKey(relationship,entity)
        self.links[key] = value

    def removeLink(self,relationship,entity):
        """
        Removes the given relationship from this entity to the given one
        @param relationship: the dynamic relationship (e.g., 'likes',
        'trusts') to evaluate
        @param entity: the entity who is the object of the
        relationship (e.g., the entity being liked or trusted)
        @type relationship: str
        @type entity: str
        """
        key = self.getLinkKey(relationship,entity)
        del self.links[key]
        
    def getLinkees(self,relationship):
        """
        @param relationship: the dynamic relationship (e.g., 'likes',
        'trusts') to evaluate
        @type relationship: str
        @return: the others to which this entity has explicit
        relationships of the specified type
        @rtype: str[]
        """
        result = []
        for key in self.links.keys():
            if key['subject'] == self.name and key['verb'] == relationship:
                result.append(key['object'])
        return result

    def getLinkTypes(self):
        """
        @return: all of the available dynamics relationship types that
        his entity has
        @rtype: str[]
        """
        return self.linkTypes[:]
        
    def getTrust(self,entity):
        """
        @return: the trust that I have in the given entity
        @rtype: float
        """
        return self.getLink(self._trustFeature,entity)

    def setTrust(self,entity,value):
        """Sets the trust that I have in the given entity
        @param entity: the entity I (dis)trust
        @type entity: str
        @param value: the new value for my trust level
        """
        self.setLink(self._trustFeature,entity,value)

    def getSupport(self,entity):
        """
        @return: the support/liking that I have in the given entity
        @rtype: L{teamwork.math.probability.Distribution}
        """
        return self.getLink(self._supportFeature,entity)

    def setSupport(self,entity,value):
        """Sets the support/liking that I have in the given entity
        @param entity: the entity I (dis)like
        @type entity: str
        @param value: the new value for my support/liking level
        """
        self.setLink(self._supportFeature,entity,value)

    def initEntities(self,entityList):
        """Sets the entities linked to
        """
        # Update my link types
        for myClass in self.classes:
            myType = self.hierarchy[myClass]
            for linkType in myType.getLinkTypes():
                if linkType == self._supportFeature or \
                       linkType == self._trustFeature:
                    pass
                elif linkType in self.linkTypes:
                    # Already found more specific model for this link
                    for action in myType.linkDynamics[linkType].keys():
                        if not self.linkDynamics[linkType].has_key(action):
                            dyn = myType.linkDynamics[linkType][action]
                            self.linkDynamics[linkType][action] = dyn
                else:
                    self.linkTypes.append(linkType)
                    self.linkDynamics[linkType] = {}
                    for action,dyn in myType.linkDynamics[linkType].items():
                        self.linkDynamics[linkType][action] = dyn
        # Update links to other entities
        for other in entityList:
            if other.name != self.name:
                # Assumes you can't have links to yourself.  Questionable.
                for myClass in self.classes:
                    myType = self.hierarchy[myClass]
                    for linkType in myType.getLinkTypes():
                        if not other.name in self.getLinkees(linkType):
                            for yrClass in other.classes:
                                if yrClass in myType.getLinkees(linkType):
                                    value = myType.getLink(linkType,yrClass)
                                    self.setLink(linkType,other.name,value)
                                    break
            
    def getAllBeliefs(self,recurse=True):
        """Packages up all of this agent's beliefs into a handy dictionary
        @param recurse: if C{True}, it's OK to borrow parents' beliefs if no beliefs of our own (you shouldn't use this)
        @type recurse: bool
        @return: the dictionary has the following indices:
           - state: what this agent believes about the state of the world
           - I{name}: what this agent think agent, I{name}, believes (i.e., a recursive call to L{getAllBeliefs})
        @rtype: dict
        """
        result = GoalBasedAgent.getAllBeliefs(self,recurse)
        result['relationships'] = self.links
        return result
        
    def preComStateEstimator(self,beliefs,observations,action,epoch=-1,debug=None,delta=None):
        """
        Computes the hypothetical changes to the given beliefs in response to the given actions
        @param beliefs: the beliefs to be updated (traditionally, the result from L{getAllBeliefs})
        @type beliefs: dict
        @param observations: the actions observed by this agent
        @type observations: C{dict:strS{->}L{Action}}
        @param epoch: the current epoch in which these observations occurred (currently ignored, but potentially important)
        @type epoch: int
        @type debug: L{Debugger}
        @return: the belief changes that would result from the specified observed actions, in dictionary form:
           - beliefs: results as returned by L{hypotheticalAct<SequentialAgents.hypotheticalAct>}
           - observations: the given actions
        @rtype: dict
        @param delta: the delta computed so far (if C{None}, then call superclass method to generate)
        @type delta: dict
        """
        if delta is None:
            delta = GoalBasedAgent.preComStateEstimator(self,beliefs,observations,
                                                        action,epoch,debug)
        else:
            delta['relationships'] = {}
        if beliefs is None:
            # No beliefs for using to compute liking change
            return delta
        diff = None
        change = None
        goals = None
        for link in self.links.keys():
            if observations.has_key(link['object']):
                # Update only relationships with actors?
                if link['verb'] == self._supportFeature:
                    # Liking of an actor
                    if change is None:
                        # First compute the change in our expected utility
                        change = copy.deepcopy(delta['state'].expectation())
                        for key in change.rowKeys():
                            change.set(key,key,change[key][key]-1.)
                    if goals is None:
                        # Compute our goals
                        goals = self.getGoalTree(observations)
                    if diff is None:
                        # We're not distinguishing among the individual effects
                        # of the different actions (if multiple actors act in
                        # parallel), so everyone's liking changes the same
                        diff = goals[beliefs['state']]*change
                    diff[link] = 1.
                    delta['relationships'][link] = diff
                elif link['verb'] == self._trustFeature:
                    pass
                else:
                    # User-defined link
                    table = self.linkDynamics[link['verb']]
                    for action in observations[link['object']]:
                        try:
                            dynamics = table[action['type']]
                        except KeyError:
                            dynamics = None
                        if dynamics:
                            if beliefs is None:
                                beliefs = self.getAllBeliefs()
                            vector = dynamics.instantiateAndApply(beliefs['state'],self,action)[link]
                            try:
                                delta['relationships'][link] += vector
                            except KeyError:
                                delta['relationships'][link] = vector
        return delta

    def updateTrust(self,sender,delta,accept):
        """Updates the given delta based on any changes due to the
        acceptance/reject of a message
        @param sender: the agent sending the message
        @type sender: str
        @param delta: the current effect dictionary
        @type delta: dict
        @param accept: flat indicating whether the message has been accepted
        (C{True} means accepted)
        @type accept: bool
        @return: the updated effect dictionary (original dictionary is changed
        as a side effect)
        @rtype: dict
        """
        if sender in self.getLinkees(self._trustFeature):
            key = self.getLinkKey(self._trustFeature,sender)
            vector = KeyedVector()
            if accept:
                vector[keyConstant] = 0.1
            else:
                vector[keyConstant] = -0.1
            vector.fill(self.entities.state.domain()[0].keys())
            try:
                delta['relationships'][key] = vector
            except KeyError:
                delta['relationships'] = {key: vector}
            if not delta.has_key(self.name):
                delta[self.name] = {}
        return delta
        
    def updateLinks(self,delta):
        """Takes changes to relationships and modifies them accordingly
        """
        goals = None
        for key,diff in delta.items():
            if key['subject'] == self.name:
                try:
                    self.links[key] *= diff[key]
                except KeyError:
                    self.links[key] = 0.
                self.links[key] += diff*self.state.expectation()

    def __xml__(self,doc=None):
        if doc is None:
            doc = GoalBasedAgent.__xml__(self)
        node = doc.createElement('links')
        element = self.links.__xml__().documentElement
        node.appendChild(element)
        doc.documentElement.appendChild(node)
        # Write available link types
        for linkType in self.getLinkTypes():
            node = doc.createElement('linktype')
            node.setAttribute('name',linkType)
            doc.documentElement.appendChild(node)
        # Write link dynamics
        for linkType,table in self.linkDynamics.items():
            for action,dynamics in table.items():
                if isinstance(action,str):
                    node = doc.createElement('linkdynamics')
                    node.setAttribute('feature',linkType)
                    node.setAttribute('action',action)
                    node.appendChild(dynamics.__xml__().documentElement)
                    doc.documentElement.appendChild(node)
        return doc

    def parse(self,element):
        if self.name is None:
            GoalBasedAgent.parse(self,element)
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'links':
                    subChild = child.firstChild
                    while subChild:
                        if subChild.nodeType == child.ELEMENT_NODE:
                            self.links = self.links.parse(subChild)
                        subChild = subChild.nextSibling
                elif child.tagName == 'linktype':
                    linkType = str(child.getAttribute('name'))
                    if not self.linkDynamics.has_key(linkType):
                        self.linkTypes.append(linkType)
                        self.linkDynamics[linkType] = {}
                elif child.tagName == 'linkdynamics':
                    linkType = str(child.getAttribute('feature'))
                    action = str(child.getAttribute('action'))
                    dyn = PWLDynamics()
                    subChild = child.firstChild
                    while subChild:
                        if subChild.nodeType == child.ELEMENT_NODE:
                            dyn.parse(subChild)
                            break
                        subChild = subChild.nextSibling
                    try:
                        self.linkDynamics[linkType][action] = dyn
                    except KeyError:
                        self.linkDynamics[linkType] = {action: dyn}
            child = child.nextSibling
            
