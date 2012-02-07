"""
Documentation for the PsychSim Interface

More details about the PsychSim Interface.
"""

# ACTIVEMQ IMPORTS
try:
    import pyactivemq
    from pyactivemq import ActiveMQConnectionFactory
    __ACTIVEMQ__ = True
except ImportError:
    __ACTIVEMQ__ = False

#PSYCHSIM IMPORTS
from teamwork.agent.lightweight import PWLAgent
from teamwork.multiagent.pwlSimulation import PWLSimulation
from teamwork.action.PsychActions import Action
from teamwork.math.Keys import Key,StateKey,LinkKey
from teamwork.math.KeyedVector import UnchangedRow
from teamwork.multiagent.GenericSociety import GenericSociety
from teamwork.multiagent.sequential import SequentialAgents

#XML IMPORTS
from xml.dom import minidom
import xml.parsers.expat
try:
    from minixsv import pyxsval
except:
    pyxsval = None

#SYSTEM IMPORTS
import bz2
import hotshot.stats
import copy
import os.path
import random
import time
import StringIO

"""
Documentation for the MessageListener class

@author J. Crotchett
@date 02/04/2008

More details about the MessageListener class.
"""

if __ACTIVEMQ__:
    class MessageListener(pyactivemq.MessageListener):

        def __init__(self, usim_proxy):
            pyactivemq.MessageListener.__init__(self)
            self.proxy = usim_proxy

        def onMessage(self, message):
            self.proxy.onMessage(message.text)

"""
Documentation for the USim_Proxy class

@author J. Crotchett
@date 02/04/2008

More details about the USim_Proxy class.
"""

class USim_Proxy:
    """
    @ivar actionIDs: mapping from action to unique ID
    @type actionIDs: L{Action}S{->}int
    @cvar epsilon: the minimum absolute value for a delta to be returned
    @type epsilon: float
    @cvar sender: the string name to give myself when sending messages
    @type sender,receiver: str
    @cvar receiver: the string name to give to whomever I'm sending messages
    @ivar lethal: a list of action types that are lethal
    @type lethal: str[]
    @ivar societyName: the location of the society file currently being used
    @type societyName: str
    @ivar profile: if C{True}, run a profiler on message handler (default is C{False}
    @type profile: bool
    @ivar debug: if C{True}, print out simulation results (default is C{False})
    @type debug: bool
    @ivar log: text file to log relevant events
    @type log: file
    @ivar LOEs: a table of lines of effort, each in dictionary form, with attributes C{name} (a string label), C{features} (a list of class-feature pairs that contribute to that line), and C{count} (the number of scenario state features that map to this LOE)
    @type LOEs: dict[]
    @ivar explanations: the conditions under which explanations are generated
    @type explanations: dict[]
    @cvar categories: mapping from class membership to game category
    @type categories: (str,str)[]
    @cvar abbreviations: mapping from verb full names to abbreviations
    @type abbreviations: strS{->}str
    @ivar root: data directory path
    @ivar root: str
    @ivar scenarioName: the external reference label for the current scenario
    @ivar scenarioName: str
    @ivar schema: optional XML validation schema (used only in testing)
    """
    epsilon = 0.0001
    sender = 'behaviorengine'
    receiver = "gamecontroller"

    categories = [
        ('Structures','STRUCTURE'),
        ('Company','GROUP'),
        ('People','INDIVIDUAL'),
        ('Groups','GROUP'),
        ('Regions','REGION'),
        ]

    
    def __init__(self,hostname=None,society=None,scenario=None,
                 conditionFile=None):
        """USim_Proxy Constructor
        @param self: reference to current object
        @type self: reference
        @param hostname: host of AMQ server (optional, default is C{None}, in which case no ActiveMQ connection is established)
        @type hostname: str
        @param society: the name of the generic society file from which any new scenario should be instantiated
        @type society: str
        @param scenario: the name of the scenario to be loaded/created
        @type scenario: str
        @param conditionFile: the name of the file containing explanation conditions
        @type conditionFile: str
        """
        self.root = os.path.join('..','data')

        #[CVM] removing creation of psychsim2.log
        #try: 
        #    self.log = open(os.path.join(self.root,'logs','psychsim2.log'),'w')
        #except IOError:
        #    self.log = sys.stdout

        # Schema validation imports
        try:
            f = open(os.path.join(self.root,'schemas','Master.xsd'),'r')
            self.schema = f.read()
            f.close()
        except:
            self.schema = ''
        self.ReadyAcknowledged = False 
        self.conn = None
        # Set null scenario
        self.scenario = {}

        # Reset Action IDs
        self.actionIDs = {}
        self.lethal = []
        # Reset line mapping
        self.LOEs = []
        self.lineMapping = {}
        # Initialize actions
        self.abbreviations = {}
        self.scenarioName = scenario
        # Initialize explanation conditions
        self.explanations = []
        if conditionFile:
            self.loadConditions(conditionFile)
        
        self.society = GenericSociety()
        self.societyName = None
        self.inputScenario = None
        
        self.profile = False
        self.debug = False
               
        if hostname:
            #ESTABLISH CONNECTION WITH THE AMQ SERVER
            addr = 'tcp://%s:61616?wireFormat=openwire&transport.useAsyncSend=false' % (hostname)
            f = ActiveMQConnectionFactory(addr)
            self.conn = f.createConnection()
            print "Connection established on " + addr

            #CREATE THE OUTBOX
            self.producer_session = self.conn.createSession()
            prodtopic = self.producer_session.createTopic(self.receiver)
            self.producer = self.producer_session.createProducer(prodtopic)

            #CREATE THE INBOX
            self.consumer_session = self.conn.createSession()
            constopic = self.consumer_session.createTopic(self.sender)
            self.consumer = self.consumer_session.createConsumer(constopic)

            #SET THE MESSAGE LISTENER
            self.consumer.messageListener = MessageListener(self)
            self.negotiation_partner = None
        if society:
            self.loadSociety(society)
        if scenario:
            self.loadScenarioData(os.path.join(self.root,'scenarios',scenario,
                                               '%s.xml' % (scenario)))
#        print 'Proxy initialized'

    def loadLOEs(self,filename):
        """Read LOE definitions from the specified XML file
        @type filename: str
        """
        try:
            doc = minidom.parse(filename)
        except IOError:
            self.sendErrorMsg('Unable to LOE definitions: %s' % (filename))
            return
        node = doc.documentElement.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert node.tagName == 'loe'
                loe = {'name':str(node.getAttribute('name')),
                       'features':[],
                       'min':float(node.getAttribute('min')),
                       'count':0}
                child = node.firstChild
                while child:
                    if child.nodeType == child.ELEMENT_NODE:
                        assert child.tagName == 'feature'
                        feature = {'class':str(child.getAttribute('class')),
                                   'feature':str(child.getAttribute('feature')),
                                   'direction':str(child.getAttribute('direction'))}
                        if feature['direction'].lower() == 'minimize':
                            feature['direction'] = -1
                        else:
                            feature['direction'] = 1
                        loe['features'].append(feature)
                    child = child.nextSibling
                self.LOEs.append(loe)
            node = node.nextSibling
        if self.debug:
            print 'Loaded %d LOE definitions from:' % (len(self.LOEs)),filename

    def loadActions(self,filename):
        """Read Action definitions from the specified XML file
        @type filename: str
        """
        try:
            doc = minidom.parse(filename)
        except IOError:
            self.sendErrorMsg('Unable to load Action definitions: %s' % (filename))
            # print 'Unable to load Action definitions: %s' % (filename)
            return
        node = doc.documentElement.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert node.tagName == 'action'
                action = str(node.getAttribute('name'))
                abbreviation = str(node.getAttribute('abbreviation'))
                self.abbreviations[action] = abbreviation
            node = node.nextSibling
        print 'Loaded allowable actions:',filename

    def loadLethal(self,filename):
        """Read lethal actions from the specified XML file
        @type filename: str
        """
        try:
            doc = minidom.parse(filename)
        except IOError:
            self.sendErrorMsg('Unable to load lethal definitions: %s' % \
                              (filename))
            return
        node = doc.documentElement.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert node.tagName == 'action'
                self.lethal.append(str(node.getAttribute('name')))
            node = node.nextSibling
        print 'Loaded lethal actions from:',filename

    def loadConditions(self,filename):
        """Read explanation conditions from the specified XML file
        @type filename: str
        """
        try:
            doc = minidom.parse(filename)
        except IOError:
            self.sendErrorMsg('Unable to load explanation conditions: %s' %\
                              (filename))
            return
        node = doc.documentElement.firstChild
        while node:
            if node.nodeType == node.ELEMENT_NODE:
                assert node.tagName == 'condition'
                condition = {'effect': str(node.getAttribute('effect')),
                             'type': str(node.getAttribute('type')),
                             'alternatives':[]}
                function = str(node.getAttribute('comparator'))
                if function == 'LESS_THAN' or function == '':
                    # Default is less than
                    value = float(node.getAttribute('value'))
                    condition['test'] = lambda delta,threshold=value: \
                                        delta < threshold
                else:
                    raise UserWarning,'Unable to process comparator %s' \
                          % (function)
                child = node.firstChild
                while child:
                    if child.nodeType == child.ELEMENT_NODE:
                        assert child.tagName == 'alternative'
                        alt = {'verb': str(child.getAttribute('verb')),
                               'object': str(child.getAttribute('object'))}
                        condition['alternatives'].append(alt)
                    child = child.nextSibling
                self.explanations.append(condition)
            node = node.nextSibling
        
    def getScenarioFile(self,scenario=None,data=False):
        """
        @param scenario: the name of the scenario (default is current scenario name)
        @type scenario: str
        @param data: if C{True}, returns the path to the "scenario data" file (default is C{False})
        @type data: bool
        @return: the path to the current PsychSim scenario file
        @rtype: str
        """
        if scenario is None:
            scenario = self.scenarioName
        if data:
            filename = '%s_scenario_data.xml' % (scenario)
        else:
            filename = '%s.xml.bz2' % (scenario)
        return os.path.join(self.root,'scenarios',scenario,filename)

    def getSocietyFile(self):
        """
        @return: the path to the current society file
        @rtype: str
        """
        if self.societyName[-4:] == '.soc':
            # Absolute path
            return self.societyName
        else:
            # Relative to data directory
            return os.path.join(self.root,'society',self.societyName,
                                '%s.soc' % (self.societyName))

    def loadSociety(self,society,absolute=False):
        """Load generic society
        """
        self.loadLethal(os.path.join(self.root,'society',society,'lethal-actions.xml'))
        self.loadLOEs(os.path.join(self.root,'society',society,'LOE_Definitions.xml'))
        self.loadActions(os.path.join(self.root,'society',society,'AllowableActions.xml'))
        self.society = GenericSociety()
        self.societyName = society
        if absolute:
            filename = society
        else:
            filename = self.getSocietyFile()
        try:
            f = bz2.BZ2File(filename,'r')
            data = f.read() 
            f.close()
        except IOError:
            self.sendErrorMsg('Unable to load society: %s' % (self.societyName))
            return
        doc = minidom.parseString(data)
        self.society.parse(doc.documentElement) 
        if self.debug:
            print 'Loaded %d classes from society: %s' % \
                (len(self.society),self.societyName)

    def loadScenarioData(self,filename):
        try:
            f = open(filename)
            data = f.read()
            f.close()
        except IOError:
            self.sendErrorMsg('Unable to load XML scenario data: %s' % (filename))
            print 'Unable to load XML scenario: %s' % (filename)
            self.inputScenario = None
            return
        self.inputScenario = minidom.parseString(data)
            
    def run(self):
        """Gets the interface up and running. The call to SendReadyMsg()
           tells the Game Controller that PsychSim is ready to receive and process
           messages.  Make sure the rest of PsychSim is ready before this function
           is called.
        """
        assert self.conn,'No ActiveMQ connection established'
        self.conn.start()
        print "Starting PsychSim activemq client..."
        self.connected = True

        self.sendReadyMsg()

        while (self.connected):
            time.sleep(1)            
        print "activemq client shutting down"


    def shutdown(self):
        print "Shutting down..."
        #if self.log:
        #    self.log.close()
        if self.conn:
            self.connected = False
            try:
                print "Consumer unsubscribe"
                self.consumer_session.unsubscribe('psychsim')
                print "Consumer session close"
                self.consumer_session.close()
                print "Producer session close"
                self.producer_session.close()
                print "Connection close"
                self.conn.close()
                print "Shutdown complete"

            except:
                print "CMS Exception"

    def sendReadyMsg(self):
        """Creates an XML instance of the MESSAGE schema and fill in the attributes.  
        Sends the message to the Game Controller telling it that PsychSim is ready.  
        The message does NOT contain any other data besides the header, 
        with the C{msg_type} attribute set to msg_be_ready.  
        When the message is received by the Game Controller, 
        it will acknowledge it and return back to PsychSim an 
        acknowledgment message with the C{msg_type} set to I{msg_ready_acknowledged} 
        (see L{onMessage} below)."""
        doc = self.generateEmptyMsg('msg_be_ready')
        count = doc.createAttribute('count')
        count.value = '0'
        doc.documentElement.firstChild.setAttributeNode(count)
        msg = doc.toxml()
        self.sendMessage(msg)

    def sendErrorMsg(self,msg):
        """Sends a message to the Game Controller to display text in the UI
        @param msg: the text to send in the LOG_MESSAGE element
        @type msg: str
        """
        doc = self.generateEmptyMsg('msg_messagebox')
        node = doc.createElement('LOG_MESSAGE')
        node.appendChild(doc.createTextNode(str(msg)))
        doc.documentElement.appendChild(node)
        self.sendMessage(doc.toxml())
        
    def generateEmptyMsg(self,msg_type):
        """Generates an empty message of a specific header type
        @param msg_type: The header of the message to send
        @type msg_type: str
        @return: the XML message
        @rtype: Document
        """
        doc = minidom.Document()
        message = doc.createElement('MESSAGE')
        doc.appendChild(message)
        header = doc.createElement('HEADER')
        message.appendChild(header)
        sender = doc.createAttribute('sender')
        sender.value = self.sender
        header.setAttributeNode(sender)
        receiver = doc.createAttribute('receiver')
        receiver.value = self.receiver
        header.setAttributeNode(receiver)
        msg_type_attr = doc.createAttribute('msg_type')
        msg_type_attr.value = msg_type
        header.setAttributeNode(msg_type_attr)
        return doc
        
    def loadScenario(self,name,cacheDynamics=True,absolute=False):
        """Loads a PsychSim scenario from the given file location
        @param name: the name of the scenario
        @type name: str
        @param cacheDynamics: if C{True}, cache dynamics of each scenario action (default is C{True})
        @type cacheDynamics: bool
        """
        if absolute:
            filename = name
        else:
            filename = self.getScenarioFile(name)
        self.scenario = PWLSimulation(observable=True)
        try:
            f = bz2.BZ2File(filename,'r')
            data = f.read()
            f.close()
        except IOError:
            self.sendErrorMsg('Unable to load scenario: %s' % (filename))
            return
        doc = minidom.parseString(data)
        if not self.scenario.parse(doc.documentElement,PWLAgent,
                                   GenericSociety):
            self.sendErrorMsg('Unable to load models: %s' % \
                              (self.scenario.societyFile))
            if self.society:
                for agent in self.scenario.members():
                    agent.society = self.society
            else:
                print 'returning'
                return
        self.scenarioName = name
        if self.scenario.societyFile:
            self.society = self.scenario.members()[0].society
        self.scenario.initialize()
        self.scenario.history = None
        # Set action IDs
        self.actionIDs.clear()
        count = 0
        for agent in self.scenario.members():
            assert agent.world is self.scenario
            for option in agent.actions.getOptions():
                self.actionIDs[str(option[0])] = str(count)
                count += 1
        # Set line mapping
        self.lineMapping.clear()
        for index in range(len(self.LOEs)):
            self.LOEs[index]['count'] = 0
            for mapping in self.LOEs[index]['features']:
                for agent in self.scenario.members():
                    if agent.instanceof(mapping['class']):
                        key = StateKey({'entity':agent.name,
                                        'feature':mapping['feature']})
                        if mapping['direction'] > 0:
                            pointer = index
                        else:
                            # Encode negative weight with negative index
                            pointer = -(len(self.LOEs) - index)
                        try:
                            self.lineMapping[key].append(pointer)
                        except KeyError:
                            self.lineMapping[key] = [pointer]
                        self.LOEs[index]['count'] += 1
            if self.LOEs[index]['count'] == 0:
                print 'LOE %s has no applicable state features' % \
                      (self.LOEs[index]['name'])
        if self.debug:
            printStats(self.scenario)
                
    def getGameObjects(self,msg_type,state=None,scenario=None):
        """Generates a message to the Game Controller containing the current state of all of the Game Objects
        @param msg_type: the msg_type attribute to use in the header
        @type msg_type: str
        @param state: the state vector to use in generating game objects (default is current scenario state)
        @type state: L{KeyedVector}
        @param scenario: optional scenario to use (default is current scenario)
        @rtype: Document
        """
        if scenario is None:
            scenario = self.scenario
        doc = self.generateEmptyMsg(msg_type)
        for agent in scenario.values():
            gameObj = self.createGameObject(doc,agent,state)
            doc.documentElement.appendChild(gameObj)
        if msg_type != 'msg_save_scenario': 
            # Compute initial LOE effect (except during --create)
            state = self.scenario.state.expectation()
            lineActual = {}
            for key,mapping in self.lineMapping.items():
                for line in mapping:
                    actual = state[key]
                    # Add line effect actual values
                    if line < 0:
                        lineChange = -actual
                    else:
                        lineChange = actual
                    try:
                        lineActual[line] += lineChange
                    except KeyError:
                        lineActual[line] = lineChange
            # Add overall line effects of this action
            if self.debug:
                print 'Line effects:'
            for line,value in lineActual.items():
                effect = doc.createElement('LOE_EFFECT')
                effect.setAttribute('LOE_ID',self.LOEs[line]['name'])
                # Average delta over number of features
                value /= float(self.LOEs[line]['count'])
                effect.setAttribute('DELTA',str(0.0))
                effect.setAttribute('ACTUAL',str(value))
                if self.debug:
                    print '\tloe name: %s value: %5.3f' % \
                        (self.LOEs[line]['name'],value)
                doc.documentElement.appendChild(effect)  
        return doc

    def createGameObject(self,doc,agent,worldState=None):
        """
        @param doc: the XML document within which this element is being stored
        @type doc: Document
        @param agent: the agent being represented
        @type agent: Agent
        @param worldState: the state vector to use in generating game objects (default is current scenario state)
        @type worldState: L{KeyedVector}
        @return: an XML element with the Game Object representation of the given agent
        @rtype: Element
        """
        root = doc.createElement('GAME_OBJECT')
        root.setAttribute('GAME_OBJECT_ID',agent.name)
        # GO Identifiers
        root.setAttribute('NAME',agent.name)
        root.setAttribute('DESCRIPTION','')

        try:
            root.setAttribute('IMAGE',agent.attributes['imageName'])
        except KeyError:
            root.setAttribute('IMAGE','')
        brain = doc.createElement('BRAIN')
        root.appendChild(brain)
        # Allowable actions
        for option in agent.actions.getOptions():
            # For now, assume single action per agent per turn
            assert len(option) == 1
            action = doc.createElement('ALLOWABLE_ACTION')
            verb = option[0]['type']
            action.setAttribute('VERB',verb)
            if option[0]['object']:
                action.setAttribute('OBJECT',option[0]['object'])
            if option[0]['self']:
                action.setAttribute('INCLUDE_SELF','true')
            else:
                action.setAttribute('INCLUDE_SELF','false')
            action.setAttribute('ENABLED','true')
#             try:
#                 action.setAttribute('ABBREVIATION',self.abbreviations[verb])
#             except KeyError:
#                 pass
##                 self.sendErrorMsg('No abbreviation for %s' % (verb))
            brain.appendChild(action)
        # State
        for feature in agent.getStateFeatures():
            state = doc.createElement('STATE_FEATURE')
            state.setAttribute('NAME',feature)
            if worldState:
                value = worldState[StateKey({'entity':agent.name,
                                             'feature':feature})]
            else:
                value = float(agent.getState(feature))
            state.setAttribute('VALUE',str(value))
            brain.appendChild(state)
        # Relationships
        for relation in agent.getLinkTypes():
            for other in agent.getLinkees(relation):
                state = doc.createElement('STATE_FEATURE')
                state.setAttribute('NAME',relation)
                # Note should also handle world state
                state.setAttribute('VALUE',str(agent.getLink(relation,other)))
                state.setAttribute('OBJECT',other)
                brain.appendChild(state)
        # Goals
        for goal in agent.getGoals():
            element = doc.createElement('GOAL')
            element.setAttribute('MAXIMIZE',str(goal.isMax()).lower())
            key = goal.toKey()
            if isinstance(key,StateKey):
                element.setAttribute('OBJECT',key['entity'])
                element.setAttribute('STATE_FEATURE',key['feature'])
            else:
                print 'Unable to serialize goal:',goal
            element.setAttribute('VALUE','%6.4f' % (agent.getGoalWeight(goal)))
            brain.appendChild(element)
        if not isinstance(agent,PWLAgent):
            # Static relationships, too
            for relation,fillers in agent.relationships.items():
                for other in fillers:
                    state = doc.createElement('STATE_FEATURE')
                    state.setAttribute('NAME',relation)
                    # Note should also handle world state
                    state.setAttribute('VALUE','1')
                    state.setAttribute('OBJECT',other)
                    brain.appendChild(state)
        # Category
        category = doc.createElement('TYPE')
        subject = 'false'
        if isinstance(agent,PWLAgent):
            # Scenario object
            for cls in agent.classes:
                node = doc.createElement('CLASS')
                node.appendChild(doc.createTextNode(cls))
                category.appendChild(node)
            for cls, mapping in self.categories:
                if agent.instanceof(cls):
                    category.setAttribute('CATEGORY',mapping)
                    break
            else:
                self.sendErrorMsg('No category for %s' % (agent.name))
            if agent.instanceof('Player'): #Changed from 'Company' to 'Player'
                subject = 'true'
        else:
            # Generic model
            remaining = [agent.name]
            done = {}
            while len(remaining) > 0:
                cls = remaining.pop()
                if not done.has_key(cls):
                    node = doc.createElement('CLASS')
                    node.appendChild(doc.createTextNode(cls))
                    category.appendChild(node)
                    remaining += self.society[cls].getParents()
            for cls,mapping in self.categories:
                if agent.isSubclass(cls):
                    category.setAttribute('CATEGORY',mapping)
                    break
            else:
                self.sendErrorMsg('No category for %s' % (agent.name))
            if agent.isSubclass('Player'):            #Changed from 'Company' to 'Player'
                subject = 'true'
        category.setAttribute('IS_SUBJECT',subject)
        root.appendChild(category)
        return root

    def instantiate(self,nodes,policy=False):
        """Generates a scenario using the given game object nodes, indexed by agent name
        @type nodes: strS{->}Element
        @param policy: if C{True}, then compile policies, too (default is C{False})
        @type policy: bool
        """
        # Generate base scenario
        start = time.time()
        entities = []
        dynamic = {}
        for name,node in nodes.items():
            if self.society.has_key(name):
                # Society directly specifies instance values
                generic = self.society[name]
                entity = self.society.instantiate(name,name)
                for relation,fillers in generic.relationships.items():
                    others = filter(lambda n: nodes.has_key(n),fillers)
                    entity.relationships[relation] = others
            else:
                # Instantiating generic model
                try:
                    subNode = node.getElementsByTagName('CLASS')[0]
                except IndexError:
                    continue
                cls = str(subNode.firstChild.data)
                try:
                    generic = self.society[cls]
                except KeyError:
                    self.sendErrorMsg('Unknown class name %s' % (cls))
                entity = self.society.instantiate(generic.name,name)
            # Process default values
            dynamic[name] = {}
            for subNode in node.getElementsByTagName('STATE_FEATURE'):
                feature = str(subNode.getAttribute('NAME'))
                value = float(subNode.getAttribute('VALUE'))
                other = str(subNode.getAttribute('OBJECT'))
                if other:
                    # Relationship
                    if generic.relationships.has_key(feature):
                        # Static relationship
                        if value > 0.5:
                            try:
                                entity.relationships[feature].append(other)
                            except KeyError:
                                entity.relationships[feature] = [other]
                    else:
                        # Dynamic relationship (store them for later)
                        try:
                            dynamic[name][feature][other] = value
                        except KeyError:
                            dynamic[name][feature] = {other: value}
                else:
                    # State feature
                    entity.setState(feature,value)
            entities.append(entity)
        agents = SequentialAgents(entities)
        agents.society = self.society
        for entity in agents.members(): 
            entity.entities.society = self.society
        agents.applyDefaults(doBeliefs=False)
        # Process en/disabled actions
        for name,node in nodes.items():
            legal = {}
            for subNode in node.getElementsByTagName('ALLOWABLE_ACTION'):
                verb = str(subNode.getAttribute('VERB'))
                object = str(subNode.getAttribute('OBJECT'))
                if object == '':
                    object = None
                if str(subNode.getAttribute('ENABLED')).lower() == 'true':
                    try:
                        legal[verb][object] = True
                    except KeyError:
                        legal[verb] = {object: True}
            index = 0
            while index < len(agents[name].actions.extras):
                option = agents[name].actions.extras[index]
                if legal.has_key(option[0]['type']) and \
                        legal[option[0]['type']].has_key(option[0]['object']):
                    # Enabled
                    index += 1
                elif option[0]['object'] is None:
                    # Null object in .soc, self as object from game controller
                    if legal.has_key(option[0]['type']) and \
                        legal[option[0]['type']].has_key(option[0]['actor']):
                        option[0]['object'] = option[0]['actor']
                        index += 1
                else:
                    # Disabled
                    del agents[name].actions.extras[index]
        # Create lightweight agents right away
        scenario = PWLSimulation(agents)
        scenario.societyFile = self.getSocietyFile()
        for agent in scenario.members():
            agent.society = self.society
            agent.world = scenario
            # Add dynamic relationships
            for feature,others in dynamic[agent.name].items():
                for other,value in others.items():
                    agent.setLink(feature,other,value)
        print 'Generating agents: %d sec' % (int(time.time() - start))
        if policy:
            # Compile policies
            cache = 0
            total = 0
            start = time.time()
            for agent in scenario.members():
                options = agent.actions.getOptions()
                if len(options) > 1 and not agent.instanceof('Player'):
                    # agent.compileGoals() 
                    agent.policy.parallelSolve({}) # [CVM] commented above using this now
                    keyList = filter(lambda k:isinstance(k,StateKey),
                                     agent.goals.domain()[0].keys())
                    total += len(options)*len(keyList)
                    for key in keyList:
                        entity = scenario[key['entity']]
                        if entity.dynamics.has_key(key['feature']):
                            for option in options:
                                try:
                                    if not isinstance(entity.dynamics[key['feature']][option[0]],dict):
                                        cache += 1
                                except KeyError:
                                    pass
            print 'Compiling: %d sec' % (int(time.time()-start))
            print 'Precomputed %d/%d trees' % (cache,total)
        printStats(scenario)
        return scenario
            
    def sendMessage(self, msg):
        """Sends a message to the Game Controller
        @param self: reference to the current object
        @type self: reference
        @param msg: XML formatted message to send to game controller
        @type msg: string
        """
        if self.conn:
            # Send message
            textMessage = self.producer_session.createTextMessage(str(msg))
            self.producer.send(textMessage)
        elif self.schema:
            # Just validate message
            if pyxsval:
                pyxsval.parseAndValidateXmlInputString(msg,self.schema)

    def onMessage(self, data):
        """Message Listener 
        @param self: reference to the current object
        @type self: reference
        @param data: incoming msg
        @type data: string
        """
        try:
            xml_data = StringIO.StringIO(data.encode('utf-8'))
            xmldoc = minidom.parse(xml_data)
        except xml.parsers.expat.ExpatError:
            return
        doc = None
        # Extract the message type
        elementNodes = xmldoc.getElementsByTagName('HEADER')
        msg_type = elementNodes[0].getAttribute("msg_type")
        if self.debug:
            print "psychsim received msg type: " + msg_type
        
        if self.profile:
            prof = hotshot.Profile('/tmp/stats')
            prof.start()
        if msg_type == 'msg_ready_acknowledged':
            self.ReadyAcknowledged = True
        elif msg_type == 'msg_edit_scenario' or \
                 msg_type == 'msg_new_scenario':
            doc = self.generateEmptyMsg(msg_type)
            for agent in self.society.values():
                if agent.name not in ['Entity', 'Player']:
                    gameObj = self.createGameObject(doc,agent)
                    doc.documentElement.appendChild(gameObj)
        elif msg_type == 'msg_load_scenario' or msg_type == 'msg_load_game':
            scenario,society = getScenarioID(xmldoc)
            if society:
                self.loadSociety(society)
            if scenario:
                # Load scenario object
                self.loadScenario(scenario)
            if msg_type == 'msg_load_game':
                # Load in new scenario state
                for element in xmldoc.getElementsByTagName('GAME_OBJECT'):
                    entity = self.scenario[str(element.getAttribute('NAME'))]
                    brain = element.getElementsByTagName('BRAIN')[0]
                    child = brain.firstChild
                    while child:
                        if child.nodeType == child.ELEMENT_NODE:
                            if child.tagName == 'STATE_FEATURE':
                                feature = str(child.getAttribute('NAME'))
                                value = float(child.getAttribute('VALUE'))
                                obj = str(child.getAttribute('OBJECT'))
                                if obj:
                                    # Relationship
                                    entity.setLink(feature,obj,value)
                                else:
                                    # State
                                    entity.setState(feature,value)
                        child = child.nextSibling
            doc = self.getGameObjects(msg_type)
        elif msg_type == 'msg_save_scenario':
            if len(self.society) == 0:
                self.sendErrorMsg('No society to use in scenario creation')
                raise UserWarning
            else:
                if self.debug: print "get scenario id"
                filename,society = getScenarioID(xmldoc)
                if self.debug: print "filename =",filename
                nodes = {}
                if self.debug: print "get game object nodes"
                for node in xmldoc.getElementsByTagName('GAME_OBJECT'):
                    if self.debug: print 'game object name =',str(node.getAttribute('NAME'))
                    name = str(node.getAttribute('NAME'))
                    if name:
                        nodes[name] = node
                if self.debug: print "instantiate scenario"
                scenario = self.instantiate(nodes,True)
                if self.debug: print "saving"
                scenario.save(self.getScenarioFile(filename))
                # Write game object file
                f = open(self.getScenarioFile(filename,True),'w')
                if self.debug: print "get game objects"
                doc = self.getGameObjects(msg_type,scenario=scenario)
                if self.debug: print 'write to file'
                f.write(doc.toxml())
                f.close()
                if self.debug: print 'done writing file'
            doc = self.generateEmptyMsg(msg_type)
        elif msg_type == 'msg_hypothetical_turn' or \
                 msg_type == 'msg_commit_turn':
            hypothetical = (msg_type == 'msg_hypothetical_turn')
            try:
                cycleCount = int(elementNodes[0].getAttribute('count'))
            except:
                cycleCount = 1
            for element in xmldoc.getElementsByTagName('GAMETURN'):
                # Save for computing delta
                if hypothetical:
                    current = {None:self.scenario.state.__class__({copy.copy(self.scenario.state.expectation()):1.})}
                else:
                    current = {None:self.scenario.state}
                original = {None:copy.copy(self.scenario.state.expectation())}
                for entity in self.scenario.members():
                    if len(entity.links) > 0:
                        original[entity.name] = copy.copy(entity.links)
                        if hypothetical:
                            current[entity.name] = copy.copy(entity.links)
                        else:
                            current[entity.name] = entity.links
                # Extract (or initialize) cycles
                cycles = element.getElementsByTagName('CYCLE')
                while len(cycles) < cycleCount:
                    # Generate a new cycle
                    cycle = xmldoc.createElement('CYCLE')
                    cycle.setAttribute('LETHAL','0')
                    cycle.setAttribute('NONLETHAL','0')
                    element.appendChild(cycle)
                    cycles.append(cycle)
                if len(cycles) > 0:
                    # Perform any player moves in first cycle
                    turns = []
                    reqID = self.getPlayerTurns(element,turns)
                    if len(turns) > 0:
                        result = self.scenario.microstep(turns,hypothetical,
                                                         state=current)
                        self.addActions(xmldoc,cycles[0],current,result)
                        if hypothetical:
                            self.scenario.applyChanges(result['delta'],current)
                for t in range(len(cycles)):
                    # Initialize cycle
                    cycle = cycles[t]
                    cycle.setAttribute('CYCLE_ID','%d' % (t+1))
                    if cycle.getAttribute('LETHAL') == '':
                        cycle.setAttribute('LETHAL','0')
                    if cycle.getAttribute('NONLETHAL') == '':
                        cycle.setAttribute('NONLETHAL','0')
                    if reqID:
                        cycle.setAttribute('REQUEST_ID',reqID)
                    # Perform NPC moves
                    start = time.time()
                    turns = self.getNPCTurns(current[None])
                    result = self.scenario.microstep(turns,hypothetical,
                                                     state=current)
                    self.addActions(xmldoc,cycle,current,result)
                    if hypothetical:
                        self.scenario.applyChanges(result['delta'],current)
                    if not hypothetical:
                        # Extract story effect
                        for event in cycle.getElementsByTagName('STORY_EFFECT'):
                            lineEffect = {}
                            lineActual = {}
                            actual = 0
                            effect = event.firstChild
                            while effect:
                                if effect.nodeType == effect.ELEMENT_NODE and \
                                   effect.tagName == 'EFFECT':
                                    subject = str(effect.getAttribute('SUBJECT'))
                                    entity = self.scenario[subject]
                                    feature = str(effect.getAttribute('FEATURE'))
                                    obj = str(effect.getAttribute('OBJECT'))
                                    delta = float(effect.getAttribute('DELTA'))
                                    if obj:
                                        pass
                                    else:
                                        old = entity.getState(feature)
                                        new = min(1.,(max(-1.,old + delta)))
                                        entity.setState(feature,new)
                                        # Calculate each story's LOE effects
                                        state = current[None].expectation()
                                        constantKey = str(subject) + "'s " + str(feature)
                                        for name,vector in original.items():
                                            for key,value in vector.items():
                                                
                                                if name:
                                                    # Relationship effects
                                                    pass
                                                else:                                        
                                                    # State effects
                                                    if str(key) == constantKey:
                                                        actual = state[key]
                                                        difference = actual - value
                                                        # Add line effect actual values
                                                        if self.lineMapping.has_key(key):
                                                            for line in self.lineMapping[key]:
                                                                if line < 0:
                                                                    lineChange = -actual
                                                                else:
                                                                    lineChange = actual
                                                                try:
                                                                    lineActual[line] += lineChange
                                                                except KeyError:
                                                                    lineActual[line] = lineChange
                                                        # Add line effect deltas
                                                        if self.lineMapping.has_key(key):
                                                            for line in self.lineMapping[key]:
                                                                if line < 0:
                                                                    lineChange = -difference
                                                                else:
                                                                    lineChange = difference
                                                                try:
                                                                    lineEffect[line] += lineChange
                                                                except KeyError:
                                                                    lineEffect[line] = lineChange
                                effect = effect.nextSibling                                
                            for line,value in lineEffect.items():
                                LOEeffect = xmldoc.createElement('LOE_EFFECT')
                                LOEeffect.setAttribute('LOE_ID',self.LOEs[line]['name'])
                                # Average delta over number of features
                                value /= float(self.LOEs[line]['count'])
                                actualValue = lineActual[line] / float(self.LOEs[line]['count'])
                                LOEeffect.setAttribute('DELTA',str(value))
                                LOEeffect.setAttribute('ACTUAL',str(actualValue))
                                event.appendChild(LOEeffect)    
                    # Compute cumulative effect
                    if self.debug:
                        print 'Cumulative effect:'
                    lineEffect = {}
                    lineActual = {}
                    cumulative = xmldoc.createElement('CUMULATIVE_EFFECT')
                    state = current[None].expectation()
                    actual = 0
                    for name,vector in original.items():
                        for key,value in vector.items():
                            if name:
                                # Relationship effects
                                entity = self.scenario[key['subject']]
                                assert entity.name == name
                                actual = current[name][key]
                                #print "CURRENT: name: %s - key %s" %(name, key)
                                difference = actual - value
                                if abs(difference) > self.epsilon:
                                    effect = xmldoc.createElement('EFFECT')
                                    effect.setAttribute('SUBJECT',key['subject'])
                                    effect.setAttribute('FEATURE',key['verb'])
                                    effect.setAttribute('OBJECT',key['object'])
                                    effect.setAttribute('DELTA',str(difference))
                                    cumulative.appendChild(effect)
                            else:
                                # State effects
                                actual = state[key]
                                difference = actual - value
                                
                                # Add line effect actual values
                                if self.lineMapping.has_key(key):
                                    for line in self.lineMapping[key]:
                                        if line < 0:
                                            lineChange = -actual
                                        else:
                                            lineChange = actual
                                        try:
                                            lineActual[line] += lineChange
                                        except KeyError:
                                            lineActual[line] = lineChange
                                # Add line effect deltas
                                if self.lineMapping.has_key(key):
                                    for line in self.lineMapping[key]:
                                        if line < 0:
                                            lineChange = -difference
                                        else:
                                            lineChange = difference
                                        try:
                                            lineEffect[line] += lineChange
                                        except KeyError:
                                            lineEffect[line] = lineChange
                                            
                                if abs(difference) > self.epsilon:
                                    effect = xmldoc.createElement('EFFECT')
                                    effect.setAttribute('SUBJECT',key['entity'])
                                    effect.setAttribute('FEATURE',key['feature'])
                                    effect.setAttribute('DELTA',str(difference))
                                    cumulative.appendChild(effect)
                                    
                            #if abs(difference) > self.epsilon:
                            #    print '\t key: %s, dif: %5.3f, actual: %5.3f, previous: $5.3f' % (key,difference, actual, value)
                    # Add overall line effects of this action
                    if self.debug:
                        print 'Line effects:'
                    for line,value in lineEffect.items():
                        #if abs(value) > self.epsilon:
                        effect = xmldoc.createElement('LOE_EFFECT')
                        effect.setAttribute('LOE_ID',self.LOEs[line]['name'])
                        # Average delta over number of features
                        value /= float(self.LOEs[line]['count'])
                        actualValue = lineActual[line] / float(self.LOEs[line]['count'])
                        effect.setAttribute('DELTA',str(value))
                        effect.setAttribute('ACTUAL',str(actualValue))
                        if self.debug:
                            print '\tLOE: %s value: %5.3f' % (self.LOEs[line]['name'],value)
                        cumulative.appendChild(effect)
                    cycle.appendChild(cumulative)
                    if self.debug:
                        state = self.scenario.state.expectation()
                        assert len(state) == len(original[None])
                        if hypothetical:
                            if t == 0:
                                # Test that state hasn't been changed
                                for key,old in original[None].items():
                                    assert state.has_key(key)
                                    assert (state[key] - old) < self.epsilon,'%s is %5.3f instead of %5.3f' % (key,state[key],old)
                        else:
                            # Test that state *has* been changed
                            assert original[None] != self.scenario.state.expectation()
                    if t < len(cycles) - 1:
                        # Update start point for computing delta
                        for key in original.keys():
                            if key:
                                original[key] = copy.copy(current[key])
                            else:
                                original[key] = copy.copy(current[None].expectation())
                    if self.debug:
                        print 'Microstep complete: elapsed time = ',time.time()-start
            # Update header
            elementNodes[0].setAttribute('sender',self.sender)
            elementNodes[0].setAttribute('receiver',self.receiver)
            doc = xmldoc
        elif msg_type == 'msg_quit':
            # Guess we're done
            self.shutdown()
        else:
            print 'Unknown message type:',msg_type
        if self.profile:
            prof.stop()
            prof.close()
        if doc:
            # Got something to say
            self.sendMessage(doc.toxml())

    def getPlayerTurns(self,element,turns=None):
        """Extract any actions by the player
        @param turns: the list for returning player actions in
        @type turns: dict[]
        @return: a REQUEST_ID for these player moves (C{None} if none)
        @rtype: str
        """
        reqID = None
        for move in element.getElementsByTagName('PLAYERMOVE'):
            request = str(move.getAttribute('REQUEST_ID'))
            if request:
                if reqID:
                    assert request == reqID
                reqID = request
            # Extract player's decision
            actor = str(move.getAttribute('SUBJECT'))
            verb = str(move.getAttribute('VERB1'))
            obj = str(move.getAttribute('OBJECT'))
            if obj:
                action = Action({'actor':actor,
                                 'type':verb,
                                 'object':obj})
            else:
                action = Action({'actor':actor,
                                 'type':verb})
            try:
                move.setAttribute('ACTION_ID',self.actionIDs[str(action)])
                if isinstance(turns,list):
                    turns.append({'name':actor,
                                  'choices':[[action]]})
            except KeyError:
                self.sendErrorMsg('Unknown player action: %s' % (action))
        return reqID
        
    def getNPCTurns(self,state):
        """Extract which NPCs can go, and which actions they can perform
        @param state: the current world state, possibly hypothetical
        @type state: L{Distribution<teamwork.math.probability.Distribution>}(L{KeyedVector})
        @rtype: dict[]
        """
        assert len(state) == 1
        state = state.domain()[0]
        turns = []
        for agent in filter(lambda agent: not agent.instanceof('Player'),
                            self.scenario.members()):
            key = StateKey({'entity': agent.name,'feature': 'Legal Subject'})
            if state.has_key(key) and state[key] < self.epsilon:
                # This agent marked as illegal actor
                continue
            choices = []
            for option in agent.actions.getOptions():
                if option[0]['object']:
                    key = StateKey({'entity': option[0]['object'],
                                    'feature': 'Legal Object'})
                    if state.has_key(key) and state[key] < self.epsilon:
                        # This agent marked as illegal object
                        continue
                choices.append(option)
            if len(choices) > 0:
                turns.append({'name':agent.name,'choices':choices})
        return turns

    def actionElement(self,xmldoc,action):
        """Returns an XML element representing the given action
        """
        node = xmldoc.createElement('ACTION')
        node.setAttribute('ACTION_ID',self.actionIDs[str(action)])
        node.setAttribute('PROGRESS',str(0.))
        if action['type'] in self.lethal:
            node.setAttribute('LETHAL','true')
        else:
            node.setAttribute('LETHAL','false')
        return node

    def evaluateLOEs(self,scenario=None):
        if scenario is None:
            scenario = self.scenario
        state = self.scenario.state.expectation()
        lineActual = {}
        for key,mapping in self.lineMapping.items():
            for line in mapping:
                # Add line effect actual values
                if line < 0:
                    lineChange = -state[key]
                else:
                    lineChange = state[key]
                try:
                    lineActual[line] += lineChange
                except KeyError:
                    lineActual[line] = lineChange
        # Add overall line effects of this action
        result = {}
        for line,value in lineActual.items():
            # Average delta over number of features
            value /= float(self.LOEs[line]['count'])
            result[self.LOEs[line]['name']] = int(100.*(value-self.LOEs[line]['min'])/(1.-self.LOEs[line]['min']))
        return result

    def addActions(self,xmldoc,cycle,distribution,result):
        """Extends a cycle by adding the actions and effects from the given microstep result
        """
        state = distribution[None].expectation()
        # Extract effects
        effects = {}
        child = result['explanation'].documentElement.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE and \
                    child.tagName == 'turn':
                effect = {}
                action = None
                subChild = child.firstChild
                while subChild:
                    if subChild.nodeType == subChild.ELEMENT_NODE:
                        if subChild.tagName == 'effect':
                            key = Key()
                            key = key.parse(subChild.firstChild)
                            effect[key] = float(subChild.getAttribute('delta'))
                        elif subChild.tagName == 'decision':
                            action = Action()
                            action.parse(subChild.firstChild)
                    subChild = subChild.nextSibling
                if action:
                    effects[str(action)] = effect
            child = child.nextSibling
        # Package up decisions
        shifts = {}
        for actor,actions in result['decision'].items():
            if len(actions) > 0: # Ignore agents with no actions
                assert len(actions) == 1
                if self.debug:
                    print "actions[0]: ", actions[0]
                action = self.actionElement(xmldoc,actions[0])
                if action.getAttribute('LETHAL') == 'true':
                    attr = 'LETHAL'
                else:
                    attr = 'NONLETHAL'
                cycle.setAttribute(attr,str(int(cycle.getAttribute(attr))+1))
                # Add decision
                decision = xmldoc.createElement('DECISION')
                decision.setAttribute('SUBJECT',actor)
                decision.setAttribute('VERB1',actions[0]['type'])
                if actions[0]['object']:
                    decision.setAttribute('OBJECT',
                                          actions[0]['object'])
                action.appendChild(decision)
                firstEffect = None
                lineEffect = {}
                if effects.has_key(str(actions[0])):
                    for key,value in effects[str(actions[0])].items():
                        
                        # Add effect on world state
                        if abs(value) > self.epsilon:
                            if self.debug:
                                print '\tKey: %s: Value: %5.3f' % (key,value)
                            effect = xmldoc.createElement('EFFECT')
                            effect.setAttribute('DELTA',str(value))
                            # add actual state value when exists
                            
                            if isinstance(key,LinkKey):
                                effect.setAttribute('OBJECT',key['object'])
                                effect.setAttribute('SUBJECT',key['subject'])
                                effect.setAttribute('FEATURE',key['verb'])
                                
                                actual = distribution[key['subject']][key]
                                effect.setAttribute('ACTUAL',str(actual))
                            else:
                                effect.setAttribute('SUBJECT',key['entity'])
                                effect.setAttribute('FEATURE',key['feature'])
                                actual = state[key]
                                effect.setAttribute('ACTUAL',str(actual))
                            if firstEffect:
                                action.insertBefore(effect,firstEffect)
                            else:
                                action.appendChild(effect)
                                firstEffect = effect
                            # Add line effect
                            if self.lineMapping.has_key(key):
                                for line in self.lineMapping[key]:
                                    if line < 0:
                                        lineChange = -value
                                    else:
                                        lineChange = value
                                    try:
                                        lineEffect[line] += lineChange
                                    except KeyError:
                                        lineEffect[line] = lineChange
                    # Add overall line effects of this action
                    for line,value in lineEffect.items():
                        effect = xmldoc.createElement('LOE_EFFECT')
                        effect.setAttribute('LOE_ID',self.LOEs[line]['name'])
                        # Average delta over number of features
                        value /= float(self.LOEs[line]['count'])
                        effect.setAttribute('DELTA',str(value))
                        action.appendChild(effect)
                        conditions = filter(lambda c:c['effect'] == 'LOE_EFFECT' and c['type'] == self.LOEs[line]['name'],self.explanations)
                        if not self.scenario[actor].instanceof('Player'):
                            # Check whether an explanation is needed
                            if not result['raw'].has_key(actor):
                                continue
                            options = result['raw'][actor]['options']
                            best = options[str(actions)]
                            test = lambda c: apply(c['test'],(value,))
                            for cond in filter(test,conditions):
                                for alt in cond['alternatives']:
                                    candidate = Action({'actor':actor,
                                                        'type':alt['verb']})
                                    if alt['object']:
                                        candidate['object'] = alt['object']
                                    try:
                                        proj = options[str([candidate])]
                                    except KeyError:
                                        # This alternative is illegal
                                        continue
                                    alternative = xmldoc.createElement('ALTERNATIVE')
                                    alternative.setAttribute('SUBJECT',actor)
                                    alternative.setAttribute('VERB1',alt['verb'])
                                    if alt['object']:
                                        alternative.setAttribute('OBJECT',alt['object'])
                                    delta = copy.copy(proj['projection'])
                                    for subKey,coeff in best['projection'].items():
                                        try:
                                            delta[subKey] -= coeff
                                        except KeyError:
                                            delta[subKey] = coeff
                                    for subKey,coeff in delta.items():
                                        if isinstance(subKey,StateKey) and abs(coeff) > self.epsilon:
                                            shift = xmldoc.createElement('SHIFT')
                                            shift.setAttribute('SUBJECT',subKey['entity'])
                                            shift.setAttribute('FEATURE',subKey['feature'])
                                            shift.setAttribute('DELTA',str((best['value']-proj['value'])/coeff))
                                            alternative.appendChild(shift)
                                            try:
                                                shifts[subKey].append(shift)
                                            except KeyError:
                                                shifts[subKey] = [shift]
                                    effect.appendChild(alternative)
                cycle.appendChild(action)
        start = time.time()
        # Comment out the following line to turn suggestions back on
        shifts.clear()
        for subKey,shiftList in shifts.items():
            count = 0
            for entity in filter(lambda e: e.instanceof('Player'),
                                 self.scenario.members()):
                for option in entity.actions.getOptions():
                    dynamics,delta = self.scenario.getEffect(option[0],subKey,state)
                    if delta is None:
                        continue
                    elif isinstance(delta,UnchangedRow):
                        continue
                    else:
                        count += 1
                        total = -state[subKey]
                        for key,weight in delta[subKey].items():
                            total += weight*state[key]
                        for shift in shiftList:
                            if float(shift.getAttribute('DELTA')) > \
                                   self.epsilon:
                                if  total > self.epsilon:
                                    alt = xmldoc.createElement('SUGGESTION')
                                    alt.setAttribute('SUBJECT',option[0]['actor'])
                                    alt.setAttribute('VERB1',option[0]['type'])
                                    if option[0]['object']:
                                        alt.setAttribute('OBJECT',option[0]['object'])
                                    shift.appendChild(alt)
                            elif float(shift.getAttribute('DELTA')) < \
                                   -self.epsilon:
                                if  total < -self.epsilon:
                                    alt = xmldoc.createElement('SUGGESTION')
                                    alt.setAttribute('SUBJECT',option[0]['actor'])
                                    alt.setAttribute('VERB',option[0]['type'])
                                    if option[0]['object']:
                                        alt.setAttribute('OBJECT',option[0]['object'])
                                    shift.appendChild(alt)
        if shifts:
            print 'Explaining:',time.time()-start

    def generateTurn(self,turnType='commit',cycleCount=None,doc=None,player=True):
        """Generates a random set of player moves to test
        @param turnType: the type of turn, either C{commit} or C{hypothetical} (default is C{commit})
        @type turnType: str
        @param cycleCount: the number of cycles to execute (default is 1)
        @type cycleCount: int
        @param doc: the message Document to modify (by default, creates a new message)
        @type doc: Document
        @param player: if C{True}, add random player moves to GAMETURN
        @type player: bool
        @return: the new Document
        @rtype: Document
        """
        if doc is None:
            doc = minidom.Document()
            msg = doc.createElement('MESSAGE')
            doc.appendChild(msg)
            header = doc.createElement('HEADER')
            header.setAttribute('msg_type','msg_%s_turn' % (turnType))
            if not cycleCount is None:
                header.setAttribute('count','%d' % (cycleCount))
            msg.appendChild(header)
        else:
            msg = doc.documentElement
        turn = doc.createElement('GAMETURN')
        turn.setAttribute('GAMETURN_ID','0')
        turn.setAttribute('TIMESTAMP','0')
        if turnType == 'commit':
            turn.setAttribute('HYPOTHETICAL','false')
        else:
            turn.setAttribute('HYPOTHETICAL','true')
        if player:
            for agent in self.scenario.members():
                if agent.instanceof('Player'):
                    if isinstance(player,dict) and player.has_key(agent.name):
                        # Pre-specified player move
                        for option in agent.actions.getOptions():
                            action = option[0]
                            if str(action) == str(player[agent.name]):
                                break
                        else:
                            raise UserWarning
                    else:
                        try:
                            action = random.choice(agent.actions.getOptions())[0]
                        except IndexError:
                            # No actions for this player (structure?)
                            continue
                    move = doc.createElement('PLAYERMOVE')
                    actionID = self.actionIDs[str(action)]
                    move.setAttribute('PLAYERMOVE_ID',str(actionID))
                    move.setAttribute('ACTION_ID',str(actionID))
                    move.setAttribute('SUBJECT',agent.name)
                    move.setAttribute('VERB1',action['type'])
                    if action['object']:
                        move.setAttribute('OBJECT',action['object'])
                    turn.appendChild(move)
        msg.appendChild(turn)
        return doc

def printStats(scenario):
    """Compute some stats"""
    keys = filter(lambda k:isinstance(k,StateKey),
                  scenario.state.expectation().keys())
    stats = {
        'stateFeatures':len(keys),
        'playerActions':[],
        'NPCActions':[],
        'playerEffects':[],
        'NPCEffects':[],
        'NPCs':0,
        'PCs':0,
        'Generators':0,
        'Targets':0,
        }
    bigImpact = {}
    for agent in scenario.members():
        options = agent.actions.getOptions()
        actionCount = len(options)
        effects = 0
        stats[agent.name] = {'verbs':{}}
        for option in options:
            stats[agent.name]['verbs'][option[0]['type']] = True
            optionEffects = 0
            for key in keys:
                try:
                    entity = scenario[key['entity']]
                    optionEffects += 1
                except KeyError:
                    pass
            if optionEffects > 100:
                bigImpact[option[0]['type']] = optionEffects
            effects += optionEffects
        if agent.instanceof('Player'):
            stats['playerActions'].append(actionCount)
            stats['playerEffects'].append(effects)
            stats['PCs'] += 1
        elif actionCount > 0:
            stats['NPCActions'].append(actionCount)
            stats['NPCEffects'].append(effects)
            if actionCount > 1:
                stats['NPCs'] += 1
            else:
                stats['Generators'] += 1
        else:
            stats['Targets'] += 1
        stats[agent.name]['verbs'] = stats[agent.name]['verbs'].keys()
        stats[agent.name]['verbs'].sort(lambda x,y:cmp(x.lower(),y.lower()))
    for entity in ['PCs','NPCs','Generators','Targets']:
        print '%3d %s' % (stats[entity],entity)
    print 'State size:',stats['stateFeatures']
    print 'Total player moves: %d' % (sum(stats['playerActions']))
    print 'Player move combos: %.2e' % (reduce(lambda x,y: x*y,
                                               stats['playerActions'],1))
    print 'Total player effects: %d' % (sum(stats['playerEffects']))
    print 'Total NPC moves: %d' % (sum(stats['NPCActions']))
    print 'NPC move combos: %.2e' % (reduce(lambda x,y: x*y,
                                            stats['NPCActions'],1))
    print 'Total NPC effects: %d' % (sum(stats['NPCEffects']))
##     print bigImpact
##     for agent in scenario.members():
##         print agent.name
##         for verb in stats[agent.name]['verbs']:
##             print '\t',verb

def printContents(scenario):
    """Prints the contents of this scenario to standard output"""
    keys = filter(lambda k:isinstance(k,StateKey),
                  scenario.state.expectation().keys())
    # Print out effects
    for agent in scenario.members():
        options = agent.actions.getOptions()
        for option in options:
            for key in keys:
                try:
                    entity = scenario[key['entity']]
                    dynamics = entity.dynamics[key['feature']][option[0]['type']]
                    dynamics = entity.getDynamics(option[0],key['feature'])
                    if dynamics:
                        tree = dynamics.getTree()
                        if not tree.isLeaf() or tree.getValue()[key].__class__.__name__ != 'UnchangedRow':
                            print '%s,%s,%s,%s' % (option[0]['actor'],option[0]['type'],option[0]['object'],key)
                            print tree.__xml__().toxml()
                            print tree.simpleText()
                except KeyError:
                    pass
    
def getScenarioID(doc):
    """
    @param doc: the XML message
    @type doc: Document
    @return: the scenario name indicating in this message
    @rtype: str
    """
    nodes = doc.getElementsByTagName('SCENARIO')
    scenario = str(nodes[0].getAttribute('SCENARIO_ID'))
    society = str(nodes[0].getAttribute('SOCIETY_MODEL'))
    return scenario,society

if __name__ == '__main__':
    from optparse import OptionParser
    import time
    import sys
    import py_compile

    try:
        py_compile.compile("psychsim_interface.py")
    except:
        print "warning: psychsim_interface.py not found"
    # Speed up Python interpretation, if available
    try:
        import psyco
        psyco.full()
    except ImportError:
        print 'Unable to find pysco module for maximum speed'
    # Process command-line args
    parser = OptionParser()
    # Optional argument that sets the host of the ActiveMQ server
    if __ACTIVEMQ__:
        default = 'localhost'
    else:
        default = None
    parser.add_option('--host',action='store',type='string',dest='host',
                      default=default,
                      help='host of ActiveMQ server [default: %default]')
    # Optional argument that sets the location of the output scenario
    parser.add_option('--scenario',action='store',type='string',
                      dest='scenario',default=None,
                      help='scenario file')
    # Optional argument that sets the location of the society file
    parser.add_option('--society',action='store',type='string',
                      dest='society',default=None,
                      help='society file [default: %default]')
    # Optional argument that prints out generic classes
    parser.add_option('--generic',action='store_true',
                      dest='generic',default=False,
                      help='Print society file generic classes')
    # Optional argument that prints out generic classes minus leaf nodes
    parser.add_option('--noleaves',action='store_true',
                      dest='noleaves',default=False,
                      help='Print society file generic classes without leaf nodes')
    # Optional argument that enters an interactive mode for setting Player classes
    parser.add_option('--player',action='store_true',
                      dest='player',default=False,
                      help='Enters an interactive mode for adding Player class membership')
    # Optional argument that gives the file containing explanation conditions
    parser.add_option('--explain',action='store',
                      dest='explain',type='string',
                      default='data/conditions.xml',
                      help='explanations file [default: %default]')
    # Optional argument that tells proxy to create a new scenario
    parser.add_option('-c','--create',action='store_true',
                      dest='create',default=False,
                      help='create a new scenario [default: %default]')
    # Optional argument that tells proxy to create a random scenario
    parser.add_option('--create-random',action='store_true',
                      dest='random',default=False,
                      help='create a random scenario [default: %default]')
    # Optional argument that tells proxy to test game loading
    parser.add_option('-l','--load',action='store_true',
                      dest='load',default=False,
                      help='test loading saved game [default: %default]')
    # Optional argument that tells proxy to test running a scenario
    parser.add_option('-t','--test',action='store_true',
                      dest='test',default=False,
                      help='test scenario execution [default: %default]')
    # Optional argument that tells proxy to use hypothetical turns
    parser.add_option('--hypothetical',action='store_true',
                      dest='hypothetical',default=False,
                      help='run hypothetical turns [default: %default]')
    # Optional argument that tells proxy how many turns to run
    parser.add_option('-n','--number',action='store',
                      dest='number',type='int',default=1,
                      help='number of turns to simulate [default: %default]')
    # Optional argument that tells proxy how many days to run per turn
    parser.add_option('-d','--days',action='store',
                      dest='days',type='int',default=1,
                      help='number of days to run per turn [default: %default]')
    # Optional argument that tells proxy to run a profiler on a step
    parser.add_option('-p','--profile',action='store_true',
                      dest='profile',default=False,
                      help='run a profiler over test [default: %default]')
    # Optional argument that gives a seed for the random generator
    parser.add_option('-s','--seed',action='store',
                      dest='seed',type='int',default=-1,
                      help='seed random numbers [default: current time]')
    # Optional argument that tells proxy to print out results of simulation
    parser.add_option('--debug',action='store_true',
                      dest='debug',default=False,
                      help='print out results [default: %default]')

    (options, args) = parser.parse_args()
    if options.test or options.create:
        # Don't run ActiveMQ if we're doing scenario creation and/or testing
        options.host = None
    if options.profile:
        # If profiling, run only one step of a test
        options.test = True
        options.number = 1
        options.days = 1
    # Start Behavior Engine
    proxy = USim_Proxy(options.host,society=options.society,
                       scenario=options.scenario,conditionFile=options.explain)
    if options.generic:  
        if proxy.society is None:
            print 'Please specify a society.'
        else:
            for agent in proxy.society.values():   
                # if agent.name not in ['Player']:   #CVM
                doc = proxy.generateEmptyMsg('msg_generic_object')
                gameObj = proxy.createGameObject(doc,agent)
                print gameObj.toxml()
    elif options.noleaves:  
        if proxy.society is None:
            print 'Please specify a society.'
        else:
            for agent in proxy.society.values():   
                # if agent.name not in ['Player']:   #CVM
                if len(proxy.society.descendents(agent.name)) != 1:
                    doc = proxy.generateEmptyMsg('msg_generic_object')
                    gameObj = proxy.createGameObject(doc,agent)
                    print gameObj.toxml()
    elif options.player:
        if proxy.society is None:
            print 'Please specify a society.'
        else:
            # Toggle Player subclass relationship
            while True:
                print
                print 'Enter name of class: ',
                name = sys.stdin.readline().strip()
                if name == '':
                    break
                elif name == 'Player':
                    print 'Cannot change Player status of Player class!'
                try:
                    cls = proxy.society[name]
                except KeyError:
                    print 'Unknown class:',name
                    continue
                try:
                    cls.parentModels.remove('Player')
                    print 'Link removed: %s is no longer Player subclass' % (name)
                except ValueError:
                    cls.parentModels.append('Player')
                    print 'Link added: %s is now a Player subclass' % (name)
            proxy.society.save(proxy.getSocietyFile())
    elif proxy.conn:
        # Run for real only if ActiveMQ is available
        proxy.run()
    else:
        # Run standalone
        proxy.sendReadyMsg()
        if options.seed < 0:
            random.seed()
        else:
            random.seed(options.seed)
        if options.create or options.random:
            # EDIT SCENARIO
            doc = minidom.Document()
            msg = doc.createElement('MESSAGE')
            header = doc.createElement('HEADER')
            header.setAttribute('msg_type','msg_edit_scenario')
            msg.appendChild(header)
            doc.appendChild(msg)
            proxy.onMessage(doc.toxml())
            # SAVE SCENARIO
            doc = minidom.Document()
            msg = doc.createElement('MESSAGE')
            header = doc.createElement('HEADER')
            header.setAttribute('msg_type','msg_save_scenario')
            msg.appendChild(header)
            if proxy.inputScenario is None:
                # No initial scenario, so instantiate all leaf classes in society
                entities = []
                for name in proxy.society.keys():
                    if len(proxy.society.descendents(name)) == 1:
                        # Leaf class
                        entities.append((name,name))
                for name,className in entities:
                    if options.create:
                        # (pre-specified instances)
                        select = True
                        instance = name
                    elif options.random:
                        # (random instances
                        select = random.random() > 0.5
                        instance = 'My ' + name
                    if select:
                        obj = doc.createElement('GAME_OBJECT')
                        obj.setAttribute('NAME',instance)
                        obj.setAttribute('GAME_OBJECT_ID',instance)
                        typeNode = doc.createElement('TYPE')
                        classNode = doc.createElement('CLASS')
                        classNode.appendChild(doc.createTextNode(className))
                        typeNode.appendChild(classNode)
                        obj.appendChild(typeNode)
                        if options.random:
                            # Add random state features
                            brain = doc.createElement('BRAIN')
                            fList = proxy.society[name].getStateFeatures()
                            if fList:
                                feature = random.choice(fList)
                                node = doc.createElement('STATE_FEATURE')
                                node.setAttribute('NAME',feature)
                                node.setAttribute('VALUE',str(random.random()))
                                brain.appendChild(node)
                            obj.appendChild(brain)
                        msg.appendChild(obj)
            else:
                # Use initial scenario to specify all instances
                for node in proxy.inputScenario.getElementsByTagName('GAME_OBJECT'):
                    msg.appendChild(node)
#                     name = str(node.getAttribute('GAME_OBJECT_ID'))
#                     if name!='' and name != 'MAP_MESH':
#                         className= str(node.getElementsByTagName('TYPE')[0].getElementsByTagName('CLASS')[0].firstChild.data)
#                         entities.append((name,className))
            obj = doc.createElement('SCENARIO')
            obj.setAttribute('SCENARIO_ID',options.scenario)
            msg.appendChild(obj)
            doc.appendChild(msg)
            proxy.onMessage(doc.toxml())
        if options.scenario:
            if options.society is None:
                print 'Please specify a society'
            else:
                # LOAD SCENARIO
                doc = minidom.Document()
                msg = doc.createElement('MESSAGE')
                header = doc.createElement('HEADER')
                header.setAttribute('msg_type','msg_load_scenario')
                msg.appendChild(header)
                obj = doc.createElement('SCENARIO')
                obj.setAttribute('SCENARIO_ID',options.scenario)
                obj.setAttribute('SOCIETY_MODEL',options.society)
                msg.appendChild(obj)
                doc.appendChild(msg)
                proxy.onMessage(doc.toxml())
        if options.load:
            # LOAD GAME
            doc = minidom.Document()
            msg = doc.createElement('MESSAGE')
            header = doc.createElement('HEADER')
            header.setAttribute('msg_type','msg_load_game')
            for entity in proxy.scenario.members():
                obj = doc.createElement('GAME_OBJECT')
                obj.setAttribute('NAME',entity.name)
                brain = doc.createElement('BRAIN')
                # Add random state
                for feature in entity.getStateFeatures():
                    state = doc.createElement('STATE_FEATURE')
                    state.setAttribute('NAME',feature)
                    state.setAttribute('VALUE',str(random.random()))
                    brain.appendChild(state)
                # Add random relationships
                for feature in entity.getLinkTypes():
                    for other in entity.getLinkees(feature):
                        state = doc.createElement('STATE_FEATURE')
                        state.setAttribute('NAME',feature)
                        state.setAttribute('VALUE',str(random.uniform(-1.,1.)))
                        state.setAttribute('OBJECT',other)
                        brain.appendChild(state)
                obj.appendChild(brain)
                msg.appendChild(obj)
            msg.appendChild(header)
            obj = doc.createElement('SCENARIO')
            obj.setAttribute('SCENARIO_ID',options.scenario)
            msg.appendChild(obj)
            doc.appendChild(msg)
            proxy.onMessage(doc.toxml())
        if options.test:
            # Simulation testing
            proxy.profile = options.profile
            proxy.debug = options.debug
            for t in range(options.number):
                if options.hypothetical:
                    # HYPOTHETICAL TURN
                    doc = proxy.generateTurn('hypothetical',options.days)
                    proxy.onMessage(doc.toxml())
                else:
                    # COMMIT TURN
                    doc = proxy.generateTurn('commit',options.days)
                    proxy.onMessage(doc.toxml())
            if options.profile:
                stats = hotshot.stats.load('/tmp/stats')
                stats.strip_dirs()
                stats.sort_stats('time', 'calls')
                stats.print_stats()
                proxy.profile = False
        
        # QUIT
        doc = minidom.Document()
        msg = doc.createElement('MESSAGE')
        header = doc.createElement('HEADER')
        header.setAttribute('msg_type','msg_quit')
        msg.appendChild(header)
        doc.appendChild(msg)
        proxy.onMessage(doc.toxml())

