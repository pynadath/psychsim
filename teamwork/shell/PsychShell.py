"""
The base engine with handlers for typical interactions with PsychSim agents
@version: 1.7
"""
try:
    import inspect
    __DOC__ = True
except ImportError:
    __DOC__ = False
__PROFILE__ = False

from ConfigParser import SafeConfigParser
import copy
import os
from Queue import Queue
import re
import string
import time
from xml.dom.minidom import parseString


from teamwork.agent.Entities import PsychEntity
from teamwork.agent.lightweight import PWLAgent
#from teamwork.agent.AgentClasses import *
from teamwork.utils.PsychUtils import extractEntity,dict2str,extractAction
from teamwork.utils.Debugger import TimedDebugger
from teamwork.multiagent.PsychAgents import PsychAgents
from teamwork.multiagent.GenericSociety import GenericSociety
from teamwork.multiagent.pwlSimulation import PWLSimulation
from teamwork.math.Keys import StateKey
from teamwork.math.KeyedVector import ThresholdRow

if __PROFILE__:
    import hotshot.stats

class PsychShell:
    """The base API for the PsychSim engine
    @cvar __VERSION__: the version of this shell
    @cvar __UNDO__: flag indicating whether UNDO operations are supported
    @type __UNDO__: boolean
    @cvar __KQML__: flag indicating whether KQML communication is supported
    @type __KQML__: boolean
    @ivar multiagentClass: the class of the current scenario (default is L{PsychAgents})
    @ivar agentClass: the class of individual agents in the scenario (default is L{PsychEntity})
    """
    __VERSION__ = '1.99'
    __UNDO__ = False
    __KQML__ = False
    
    actionFormat = [('actor',True),('type',True),('object',False)]
    
    def __init__(self,
                 scenario=None,        # Initial scenario
                 classes=None,         # Class hierarchy
                 agentClass=None,      # Class used for generating agents
                 multiagentClass=None, # Class for generating scenario
                 options=None,         # Configuration object
                 debug=0):
        """
        @param scenario: a L{teamwork.multiagent.PsychAgents.PsychAgents} object (if none provided, shell starts up an initialization phase)
        @type classes: L{GenericSociety}
        """
        self.options = options
        # Find root directory
        path = os.path.dirname(__file__)
        self.directory = os.path.realpath(os.path.join(path,'..'))
        # Set up (multi)agent classes
        if agentClass:
            self.agentClass = agentClass
        else:
            self.agentClass = PsychEntity
        if multiagentClass:
            self.multiagentClass = multiagentClass
        else:
            self.multiagentClass = PsychAgents
        self.debug = TimedDebugger(debug)
        # Set up class hierarchy
        self.resetSociety()
        self.societyFile = None
        if isinstance(classes,str):
            self.loadSociety(classes)
        elif classes:
            self.classes = classes
        self.scenarioFile = None
        self.scenario = None
        if isinstance(scenario,str):
            # String indicates a file name to load entities from
            try:
                PsychShell.load(self,scenario)
                self.phase = 'run'
            except IOError:
                print 'No such file or directory:',scenario
                self.scenario = None
        elif scenario is None:
            # If no entities provided, go into initialization phase
            self.scenario = None
            self.entities = self.classes
            self.phase = 'setup'
        elif isinstance(scenario,list):
            # Convert into PsychAgents object
            scenario = self.setupEntities(scenario)
            self.setupScenario(scenario)
        else:
            # Assume that is instance of PsychAgents
            self.scenario = scenario
            self.entities = self.scenario
            self.phase = 'run'
            self.initEntities()
        self.done = None
        if self.__KQML__:
            # Start up KQML listener
            import teamwork.communication.SocketListener
            self.router = teamwork.communication.SocketListener.KQMLListener()
            self.router.registerHandler(self.handleMsg)
        # Reset known susceptibilities to be empty
        self.susceptibility = None
        self.handlers = {}
        self.tests = {}
        # Add mappings here from command to function
        # (see the 'save' method for an example handler)
        self.handlers['entity'] = self.getEntity
        self.handlers['belief'] = self.getBelief
        self.handlers['act'] = self.performAct
        self.handlers['step'] = self.step
        self.handlers['save'] = self.save
        self.handlers['load'] = self.load
        self.handlers['export'] = self.export
        self.handlers['distill'] = self.distill
        self.handlers['message'] = self.send
        self.handlers['goals'] = self.goals
        self.handlers['policy'] = self.applyPolicy
        self.handlers['entities'] = self.getEntities
        self.handlers['test'] = self.test
        self.handlers['help'] = self.help
        self.handlers['debug'] = self.setDebugLevel
        self.handlers['model'] = self.setModel
        self.handlers['loadgeneric'] = self.loadSociety
        self.handlers['savegeneric'] = self.saveSociety
        if self.__UNDO__:
            # Slot for saving last known entities
            self.lastStep = None
            self.handlers['undo'] = self.undo
        
    def setupScenario(self,agents,progress=None):
        """initialize L{PsychShell} with given L{scenario<teamwork.multiagent.PsychAgents.PsychAgents>}
        @param agents: the scenario to interact with
        @type agents: L{MultiagentSimulation<teamwork.multiagent.Simulation.MultiagentSimulation>}
        @param progress: optional progress display command
        @type progress: C{lambda}
        """
        self.scenario = agents
        self.entities = self.scenario
        self.phase = 'run'
        self.initEntities(progress)
        if self.__UNDO__:
            self.lastStep = copy.deepcopy (self.entities)
        return self.scenario

    def setupEntities(self,entities=None,progress=None,compileDynamics=True,
                      compilePolicies=None,distill=False):
        """Creates a scenario instance from a list of entities and applies the default values across the board
        @param entities: the entities to use in populating the scenario
        @type entities: L{Agent}[]
        @param progress: optional C{Queue} argument is used to give progress updates, in the form of C{(label,pct)}, where:
           - I{label}: a string label to display for the current task
           - I{pct}: an integer percentage (1-100) representing the amount of progress made since the last call
        The thread puts C{None} into the queue when it has finished.
        @type progress: Queue
        @return: a newly created scenario instance
        @rtype: L{multiagentClass}
        @param compileDynamics: Flag indicating whether the scenario dynamics should be compiled as well (default is True)
        @type compileDynamics: boolean
        @param compilePolicies: The belief depth at which all agents will have their policies compiled, where 0 is the belief depth of the real agent.  If the value of this flag is I{n}, then all agents at belief depthS{>=}I{n} will have their policies compiled, while no agents at belief depth<I{n} will.  If omitted, no policies will be compiled
        @type compilePolicies: int
        @param distill: If C{True}, then create a distilled version of these agents (default is C{False}
        @type distill: bool
        """
        agents = self.multiagentClass()
        agents.society = self.classes
        for entity in entities:
            agents.addMember(entity)
        # Compute whether there are any compilations to be "progressed" through
        if progress is not None:
            if not isinstance(progress,Queue):
                raise DeprecationWarning,'"progress" argument should be Queue for proper synchronization.'
            total = agents.actorCount(compilePolicies)
            if compileDynamics:
                # Crude estimate of how many recursive belief there are
                for entity in agents.members():
                    depth = entity.getDefault('depth')
                    total += pow(len(agents.members()),depth)
                # Count how many dynamics functions there are
                total += agents.actionCount(False)
            total = float(total)
        # Nothing else to progress over, so might as well do it here
        agents.applyDefaults(progress=progress,total=total,
                             doBeliefs=not distill)
        if compileDynamics:
            if __PROFILE__:
                filename = '/tmp/stats'
                prof = hotshot.Profile(filename)
                prof.start()
            agents.compileDynamics(progress,total)
            if __PROFILE__:
                prof.stop()
                prof.close()
                print 'loading stats...'
                stats = hotshot.stats.load(filename)
                stats.strip_dirs()
                stats.sort_stats('time', 'calls')
                stats.print_stats()
        agents.compilePolicy(compilePolicies,progress,total)
        if distill:
            # Create lightweight agents right away
            scenario = PWLSimulation(agents)
            # Determine LHS of policies
            attributes = {}
            vectors = {}
            keyList = filter(lambda k:isinstance(k,StateKey),
                             agents.getStateKeys().keys())
            maxAttrs = 8
            for key in keyList:
                for agent in scenario.members():
                    for option in agent.actions.getOptions():
                        for action in option:
                            if len(attributes) >= maxAttrs:
                                continue
                            entity = agents[key['entity']]
                            dynamics = entity.getDynamics(action,
                                                          key['feature'])
                            tree = dynamics.getTree()
                            del entity.dynamics[key['feature']][action]
                            for plane in tree.branches().values():
                                if isinstance(plane.weights,ThresholdRow):
                                    # Needs to be a bit more permissive, but...
                                    label = plane.weights.simpleText()
                                    try:
                                        attributes[label][plane.threshold] = True
                                    except KeyError:
                                        attributes[label] = {plane.threshold: True}
                                        vectors[label] = plane.weights
            # Initialize everyone's policies with default order
            keyList = agents.getStateKeys().keys()
            keyList.sort()
            del agents
            for key,vector in vectors.items():
                vector.fill(keyList)
            # Compile for just one agent
            for agent in scenario.members():
                options = agent.actions.getOptions()
                if len(options) > 0:
                    agent.policy.reset()
                    # Cap the # of attributes
                    for key,values in attributes.items():
                        values = values.keys()
                        values.sort()
                        agent.policy.attributes.append((vectors[key],values))
                    agent.policy.initialize(choices=options)
                    for index in xrange(len(agent.policy.rules)):
                        agent.policy.rules[index] = options[:]
                    scenario.save('/tmp/pynadath/test%02d_%d.xml' % \
                                  (len(scenario),len(agent.policy.rules)))
                    print agent.name
                    print 'done.'
                    sys.exit(0)
            agents = scenario
        # Report to the main thread that we're all done
        if progress:
            progress.put(None)
        return agents

    def initEntities(self,progress=None):
        """A method, to be overridden by subclass, that is invoked whenever there is a new set of entities"""
        pass
    
    def getCommand(self):
        """Abstract method for getting a command from user.
        @rtype: C{str}
        """
        raise NotImplementedError

    def executeCommand(self,cmd):
        start = time.time()
        result = self.execute(cmd)
        diff = time.time()-start
        if result:
            self.displayResult(cmd,`self.debug`)
            self.debug.reset()
            self.displayResult(cmd,result)
            self.displayResult(cmd,'Time: %7.4f' % (diff))
        else:
            self.done = 1
        return result

    def displayResult(self,cmd,result):
        """Abstract method for displaying a result to the user
        @param cmd: the command executed
        @type cmd: C{str}
        @param result: the results of the command
        @type result: C{str[]}
        """
        raise NotImplementedError
    
    def save(self,filename=None,results=None):
        """Saves the state of the current simulation to the named file"""
        if not filename:
            return 'Usage: save <filename>'
        self.scenario.save(filename)
        self.scenarioFile = filename
        return 1
    
    def saveSociety(self,filename=None,results=None):
        """Saves the current generic society to the named file"""
        if not filename:
            return 'Usage: savegeneric <filename>'
        self.classes.save(filename)
        self.societyFile = filename
        return 1

    def load(self,filename=None,results=None):
        """Loads in a L{scenario<teamwork.multiagent.PsychAgents.PsychAgents>} object from the specified file"""
        if not filename:
            return 'Usage: load <filename>'
        if filename[-4:] == '.xml':
            f = open(filename,'r')
        else:
            import bz2
            f = bz2.BZ2File(filename,'r')
        data = f.read()
        f.close()
        doc = parseString(data)
        scenarioClass = str(doc.documentElement.getAttribute('type'))
        if scenarioClass == 'PWLSimulation':
            self.scenario = PWLSimulation()
            agentClass = PWLAgent
        elif scenarioClass == 'GenericSociety':
            # Whoops, we have a generic society instead
            return self.loadSociety(filename,True,results)
        else:
            # We should also handle other specific types here
            self.scenario = self.multiagentClass()
            agentClass = self.agentClass
        self.scenario.parse(doc.documentElement,agentClass,GenericSociety)
        self.entities = self.scenario
        self.scenario.initialize()
        eList = self.entities.members()
        while len(eList) > 0:
            entity = eList.pop()
            entity.setHierarchy(self.classes)
            eList += entity.getEntityBeliefs()
        self.scenarioFile = filename
        self.initEntities()
        return 1

    def loadSociety(self,filename=None,overwrite=True,results=None):
        """Loads in a GenericSociety object from the specified file
        @param overwrite: flag indicating, when C{True} that the existing society should be erased before loading in the new one
        @type overwrite: boolean
        """
        if not filename:
            return 'usage: loadgeneric <filename>'
        if filename[-4:] == '.xml':
            f = open(filename,'r')
        else:
            import bz2
            f = bz2.BZ2File(filename,'r')
        data = f.read()
        f.close()
        doc = parseString(data)
        newClasses = GenericSociety()
        newClasses.parse(doc.documentElement)
        if overwrite:
            self.classes = newClasses
            self.societyFile = filename
            warnings = []
        else:
            warnings = self.classes.merge(newClasses)
            if not self.societyFile:
                self.societyFile = filename
        return warnings

    def export(self,filename=None,results=None):
        """Writes a Web page representation of the current scenario"""
        if filename:
            f = open(filename,'w')
            f.write(self.scenario.toHTML())
            f.close()
            return 1
        else:
            return 'usage: export <filename>'

    def distill(self,filename=None,results=None):
        """Writes a lightweight representation of the current scenario"""
        if filename:
            lightweight = PWLSimulation(self.scenario)
            lightweight.save(filename)
            return 1
        else:
            return 'usage: distill <filename>'
        
    def revert(self):
        """Reverts the current scenario to the last loaded/saved scenario"""
        if self.scenarioFile:
            self.load(self.scenarioFile)

    def step(self,length=1,results=None):
        """Steps the simulation the specified number of micro-steps
        into the future (default is 1)"""
        try:
            length = int(length)
        except TypeError:
            results = length
            length = 1
        sequence = []
        for t in range(int(length)):
            delta = self.entities.microstep(debug=self.debug)
            sequence.append(delta)
            if isinstance(results,list):
                results.append(dict2str(delta,self.debug.level))
        return sequence

    def goals(self,results=None):
        for name in self.entities.agents.keys():
            entity = self.entities.agents[name] 
            value = entity.applyGoals(entity,debug=self.debug)
            if isinstance(results,list):
                results.append(name + ': ' + `value`)

    def send(self,sender,receiver,*content):
        try:
            if receiver == '*':
                # Message sent to all
                receivers = self.entities.agents.keys()
            else:
                receivers = [receiver]
            if isinstance(content[len(content)-1],list):
                results = content[len(content)-1]
                msg = string.join(content[:len(content)-1])
            else:
                results = []
                msg = string.join(content)
        except IndexError:
            return 'Usage: message <sender> <receiver> <content>'
        result = self.entities.performMsg(msg,sender,receivers,[],self.debug)
        if isinstance(results,list):
            results.append(dict2str(result))

    def applyPolicy(self,name,results=None):
        """Returns the action that <entity> will perform, following
        its policy of behavior"""
        entity = extractEntity(name,self.entities)
        if entity:
            action,explanation = entity.applyPolicy(debug=self.debug)
            if isinstance(results,list):
                results.append(entity.name + ' -> ' + `action`)
        else:
            if isinstance(results,list):
                results.append('No such entity: '+name)
        
    def setDebugLevel(self,level=None,results=None):
        """Sets the debug level to the specified integer"""
        if level is None:
            level = self['debug']
        self.debug.level = int(level)
        if isinstance(results,list):
            results.append('Debug level: %d' % (self.debug.level))
        return self.debug.level

    def getEntities(self,results=None):
        if isinstance(results,list):
            results.append(`self.entities`)

    def help(self,results=None):
        """Prints descriptions of available commands"""
        if __DOC__:
            helpStrings = []
            for key,value in self.handlers.items():
                doc = inspect.getdoc(value)
                if doc:
                    doc = doc.replace('\n','\n\t\t')
                else:
                    doc = ''
                helpStrings.append('%-12s\t%s' % (key,doc))
            helpStrings.sort()
            if isinstance(results,list):
                results += helpStrings
        else:
            if isinstance(results,list):
                results.append('Help unavailable under jython')

    def test(self,label,results=None):
        try:
            cmd = self.tests[label]
        except KeyError:
            return 'Valid tests: '+self.tests.keys()
        if isinstance(results,list):
            results.append('Executing "'+cmd+'"')
        return self.execute(cmd,results)

    def undo(self,results=None):
        if self.lastStep:
            self.entities = copy.deepcopy (self.lastStep)
        else:
            if isinstance(results,list):
                results.append('No previous state stored!')

    def getEntity(self,name,results=None):
        """Returns a string representation of the named entity."""
        try:
            entity = self.entities[name]
            if isinstance(results,list):
                results.append(`entity`)
        except KeyError:
            if isinstance(results,list):
                results.append('Unknown entity: '+name)

    def getBelief(self,entityName,beliefName,results=None):
        """Returns a string representation of the belief that the
        first entity has about the second."""
        try:
            entity = self.entities.agents[entityName]
        except KeyError:
            entity = None
            if isinstance(results,list):
                results.append('Unknown entity: '+entityName)
        if entity:
            if isinstance(results,list):
                if beliefName in entity.getEntities():
                    results.append(`entity.getEntity(beliefName)`)
                else:
                    results.append('Unknown entity: '+beliefName)

    def setModel(self,entityName,beliefName,modelName,results=None):
        """Sets the mental model that 'entityName' holds in regard to
        'beliefName' to be 'modelName'"""
        entity = self.entities[entityName]
        entity.getEntity(beliefName).setModel(modelName)
        if isinstance(results,list):
            results.append('%s now models %s as %s' \
                           % (entityName,beliefName,modelName))
        
    def performAct(self,name,actType,obj,results=None):
        """Performs the action of the specified type by the named entity on the specified object (use 'nil' if no object)"""
        # For backward compatibility with previous command format
        if isinstance(obj,list):
            results = obj
            obj = 'nil'
        # Extract the action
        if not obj or obj == 'nil':
            actList = [name,actType]
        else:
            actList = [name,actType,obj]
        return self.__act__(actList,results)

    def doActions(self,actions,results=None):
        """Performs the actions, provided in dictionary form
        @param actions: dictionary of actions to be performed, indexed by actor, e.g.:
           - I{agent1}: [I{act11}, I{act12}, ... ]
           - I{agent2}: [I{act21}, I{act22}, ... ]
           - ...
        @type actions: C{dict:strS{->}L{Action}[]}
        """
        turns = []
        for actor,actList in actions.items():
            turns.append({'name':actor,'choices':[actList]})
        delta = self.entities.microstep(turns,hypothetical=False,
                                        explain=True,
                                        debug=self.debug)
        if isinstance(results,list):
            results.append(dict2str(delta))
        return delta
        
    def __act__(self,actList,results):
        action = extractAction(actList,self.entities,self.actionFormat,
                               self.debug)
        if action:
            if self.__UNDO__:
                self.lastStep=copy.deepcopy (self.entities)
            return self.doActions(actions={action['actor'].name:action},
                                  results=results)
        else:
            results.append('Usage: act <entity> <type> <obj>')
            return {}

    def execute(self,cmd,results=None):
        if not results:
            results = []
        cmd = string.strip(cmd)
        cmd = string.split(cmd)
        try:
            cmd[0] = string.lower(cmd[0])
        except IndexError:
            return '?'
        if cmd[0] == 'quit':
            return None
        else:
            try:
                handler = self.handlers[cmd[0]]
            except KeyError:
                return 'Unknown command: '+cmd[0]
            apply(handler,cmd[1:]+[results])
        return '\n'+string.join(results,'\n')

    def search(self,feature):
        for entity in self.entities.members():
            self.__search__(entity,feature)

    def __search__(self,entity,feature):
        try:
            value = entity.getState(feature)
            print entity.ancestry()
            print '\t',value
        except KeyError:
            pass
        for other in entity.getEntities():
            self.__search__(entity.getEntity(other),feature)

    def setupSusceptibility(self,addr=None):
        self.susceptibility = addr

    def querySusceptibility(self,entity):
        if self.susceptibility:
            if not isinstance(entity,str):
                entity = entity.name
            queryStr = 'request %s %d %s Theme' %\
                       ('127.0.0.1',
                        self.router.server_address[1],
                        entity)
            print queryStr
            return self.router.send(self.susceptibility,queryStr)
        else:
            return None

    def handleMsg(self,msgList):
        for msg in msgList:
            print msg
            if self.susceptibility == msg[0]:
                exp = re.match('(\S+)\s*(\S+)\s*(Accepted):\s+'+\
                               '(.*)\s+(Rejected):\s+(.*)\s+(Neutral):(.*)',
                               msg[1],re.DOTALL)
                if exp:
                    themes = {}
                    for index in [3,5,7]:
                        key = exp.group(index)
                        themes[key] = []
                        entries = string.split(exp.group(index+1),'\n')
                        for entry in entries:
                            items = string.split(entry,', ')
                            try:
                                if len(items[0]) > 0:
                                    themes[key].append(items)
                            except IndexError:
                                pass
                    self.handleSusceptibility(exp.group(1),themes)
                else:
                    print 'Unable to parse susceptibility response'

    def handleSusceptibility(self,entity,themes):
        self.entities[entity].susceptibilities = themes['Accepted']
                
    def iterateModels(self,eList,pIndex,cIndex,modelsUsed):
        if cIndex == len(eList):
            print modelsUsed
            entity = self.entities[eList[pIndex]]
            action,explanation = entity.applyPolicy()
            print action,explanation['value']
            for step in explanation['breakdown'][1:]:
                print '\t',step['decision']
                print '\t',step['breakdown'][0]
                print
            sys.stdout.flush()
        else:
            parent = eList[pIndex]
            child = eList[cIndex]
            if parent == child:
                self.iterateModels(eList,pIndex,cIndex+1,modelsUsed)
            else:
                parent = self.entities[parent]
                child = self.entities[child]
                for model in child.models:
                    parent.getEntity(child).setModel(model)
                    parent.getEntity(parent).getEntity(child).setModel(model)
                    modelsUsed[parent.name][child.name] = model
                    self.iterateModels(eList,pIndex,cIndex+1,modelsUsed)

    def resetSociety(self):
        """Clears any classes in the current generic society"""
        import teamwork.agent.AgentClasses
        self.classes= GenericSociety()
        self.classes.importDict(teamwork.agent.AgentClasses.classHierarchy)
        self.societyFile = None
        
    def mainloop(self):
        while not self.done:
            cmd = self.getCommand()
            self.executeCommand(cmd)
        self.stop()

    def stop(self):
        self.done = 1
        if self.__KQML__:
            self.router.server_close()

def getConfig(filename=None):
    # Load configuration file (default and personalized)
    if filename is None:
        filename = os.path.join(os.path.dirname(__file__),'psychsim.ini')
    default = SafeConfigParser()
    default.read(os.path.join(os.path.dirname(__file__),'default.ini'))
    config = SafeConfigParser()
    config.read(filename)
    change = False
    # Make sure personalized config has all required sections and options
    for section in default.sections():
        if not config.has_section(section):
            change = True
            config.add_section(section)
        for option in default.options(section):
            if not config.has_option(section,option):
                change = True
                config.set(section,option,default.get(section,option))
            if section == 'General' and option == 'config':
                # This should point to the file location
                if config.get(section,option) != filename:
                    change = True
                    config.set(section,option,filename)
    if change:
        # Save updated file
        f = open(filename,'w')
        config.write(f)
        f.close()
    return config
    
if __name__ == '__main__':

    import getopt
    import sys

    try:
        import psyco
        psyco.full()
    except ImportError:
        print 'Unable to find psyco module for maximum speed'

    script = None
    scenario = None
    society = None
    domain = None
    display = 'tk'
    debug = 0
    error = None
    expert = False
    dev = False
    try:
        optlist,args = getopt.getopt(sys.argv[1:],'hf:s:d:vx',
				     ['file=','shell=','domain=','society=',
                                      'debug=','help','version','expert',
                                      'dev'])
    except getopt.error:
        error = 1
        optlist = []
        args = []

    for option in optlist:
        if option[0] == '--file' or option[0] == '-f':
            script = option[1]
        elif option[0] == '--shell' or option[0] == '-s':
            display = option[1]
        elif option[0] == '--domain' or option[0] == '-d':
            raise DeprecationWarning,'Domain dictionaries are no longer supported'
        elif option[0] == '--society':
            society = option[1]
        elif option[0] == '--help' or option[0] == '-h':
            error = 1
        elif option[0] == '--debug':
            debug = int(option[1])
        elif option[0] == '--version' or option[0] == '-v':
            print 'PsychSim %s' % (PsychShell.__VERSION__)
            sys.exit(0)
        elif option[0] == '--expert' or option[0] == '-x':
            expert = True
        elif option[0] == '--dev':
            dev = True
        else:
            error = 1
        
    if len(args) > 0:
        if len(args) > 1:
            error = 1
        else:
            scenario = args[0]

    if error:
        print 'PsychShell.py',\
              '[--domain|-d <domain>]',\
              '[--file|-f <script filename>]',\
              '[--shell|-s tk|terminal]',\
              '[--society <filename>]',\
              '[--expert|-x]',\
              '<scenario filename>'
        print
        print '--domain|-d\tIndicates the class path to the generic society definition'
        print '--society\tIndicates the file name containing the generic society'
        print '--file|-f\tIndicates the file containing a script of commands to execute'
        print '--shell|-s\tIf "tk", use GUI; if "terminal", use interactive text (default is "tk")'
        print '--expert|-x\tTurns on expert mode'
        print '--version|-v\tPrints out version information'
        print '--help|-h\tPrints out this message'
        print
        sys.exit(-1)
    config = getConfig()
    if display == 'tk':
        import Pmw

        root = Pmw.initialise()
        root.title('PsychSim')
        from teamwork.widgets.PsychGUI.Gui import GuiShell
        shell = GuiShell(root,scenario=scenario,classes=society,
                         options=config,debug=debug)
        shell.pack(fill='both',expand='yes')
        shell.mainloop(root)
##        root.destroy()
    else:
        from teamwork.shell.TerminalShell import TerminalShell
        shell = TerminalShell(entities=scenario,classes=society,
                              file=script,options=config,
                              debug=debug)
        shell.mainloop()
