import string
import sys

from teamwork.shell.PsychShell import *

class TerminalShell(PsychShell):
    """An interactive terminal version of the base L{PsychShell} class."""
    
    def __init__(self,entities=None,
                 classes=None,
                 agentClass=None,
                 multiagentClass=None,
                 file=None,
                 progress=None,
                 options=None,
                 debug=0,
                 compileDynamics=True,
                 compilePolicies=None,
                 ):
        """Almost identical to the base L{PsychShell} constructor
        @param file: an input stream for reading commands.  If none is
        provided, this stream defaults to standard input.
        @type file: C{str}
        """
        if file:
            self.file = open(file,'r')
        else:
            self.file = sys.stdin
        PsychShell.__init__(self,
                            classes=classes,
                            agentClass=agentClass,
                            multiagentClass=multiagentClass,
                            options=options,
                            debug=debug)
        if self.phase == 'setup':
            scenario = self.setupEntities(entities=self.createEntities(),
                                          progress=progress,
                                          compileDynamics=compileDynamics)
            self.setupScenario(scenario)

    def createEntities(self):
        """Interactive creation of entities for initial scenario"""
        entityList = []
        setupDone = None
        # Grab list of possible classes
        while not setupDone:
            cmd = self.getCommand()
            if cmd == 'quit':
                # Exits from setup *and* overall simulation
                self.done = 1
                setupDone = 1
            elif cmd == 'done':
                # Exits from setup and begins simulation
                if len(entityList) > 0:
                    self.displayResult(cmd,'Entering simulation phase...')
                    setupDone = 1
                else:
                    self.displayResult(cmd,'No entities created yet!')
            elif cmd == 'entities':
                # Prints out currentlist of entity names
                self.displayResult(cmd,
                                   map(lambda e:(e.name,e.__class__.__name__),
                                       entityList))
            else:
                # Otherwise, assume is a class name followed by instance name
                commands = string.split(cmd)
                try:
                    entityClass = commands[0]
                    name = commands[1]
                except IndexError:
                    self.displayResult(cmd,'Usage: <class> <name>')
                    entityClass = None
                if entityClass:
                    entity = createEntity(entityClass,name,self.classes,
                                          self.agentClass)
                    if entity:
                        entityList.append(entity)
                        self.displayResult(cmd,entity.name)
                    else:
                        self.displayResult(cmd,'Unknown entity class: '+entityClass)
        return entityList
        
    def getCommand(self):
        """Terminal version of command entry.  Prints a prompt
        (currently assumes turn-based execution) and reads the command
        entry from the input file."""
        if self.phase == 'setup':
            prompt = '?'
        else:
            next = self.entities.next()
            prompt = '%s (%d)> ' % (next[0]['name'],
                                    self.entities.time)
        print prompt,
        try:
            cmd = string.strip(self.file.readline())
        except KeyboardInterrupt:
            cmd = 'quit'
        return cmd

    def displayResult(self,cmd,result):
        """Terminal version of the output display method.  Uses
        standard output."""
        print result
##        print
        sys.stdout.flush()
