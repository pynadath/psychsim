"""
ELECT-Specific GUI, designed to automatically do the necessary preparatory steps to go from the initial CSV agent spec file all the way to a runnable (compiled) scenario
"""
import copy
from teamwork.widgets.PsychGUI.Gui import GuiShell
from teamwork.multiagent.GenericSociety import GenericSociety
from teamwork.multiagent.sequential import SequentialAgents
from teamwork.agent.Entities import PsychEntity
from teamwork.agent.Generic import GenericModel
from teamwork.math.KeyedVector import ThresholdRow
from teamwork.multiagent.pwlSimulation import PWLSimulation
from teamwork.policy.pwlTable import PWLTable
from elect_reader import elect_reader,classHierarchy

import threading
import time

class ELECTGui(GuiShell):
    """GUI subclass enhanced for using ELECT input files to set up the scenario.
    @ivar original: The original state distribution of this scenario (used on revert)
    """
    def __init__(self,toplevel,filename=None,society=None,scenario=None,
                 instantiate=True,compile=True,debug=0):
        """
        @param filename: the CSV file with the ELECT input data
        @type filename: str
        @param society: the default agent specification (if C{None}, then it is generated from L{filename})
        @type society: L{GenericSociety}
        @param scenario: the set of instantiated agents for execution (if C{None}, then it is generated from L{society})
        @type scenario: L{SequentialAgents}
        @param instantiate: if C{True}, then the shell starts up in scenario execution mode; otherwise, no scenario is generated (default is C{True})
        @type instantiate: bool
        @param compile: if C{True}, then the shell starts up after pre-compiling the scenario; otherwise, the scenario is left uncompiled (default is C{True})
        @type compile: bool
        """
        if society is None:
            # Parse CSV file
            if filename is None:
                self.reader = elect_reader()
            else:
                self.reader = elect_reader(input_file=filename)
            self.reader.process_lines()
            # Create generic society
            society = GenericSociety()
            society.importDict(classHierarchy)
        else:
            self.reader = None
        if instantiate and scenario is None:
            # Instantiate scenario
            print 'Creating agents...'
            entities = map(lambda n:society.instantiate(n,n),
                           self.reader.agents)
            scenario = SequentialAgents(entities)
            for entity in scenario.members():
                for relation,others in society[entity.name].relationships.items():
                    entity.relationships[relation] = others[:]
            print 'Applying defaults...'
            scenario.applyDefaults()
            print 'Compiling dynamics...'
            scenario.compileDynamics()
        if isinstance(scenario,SequentialAgents) and compile:
            # Compile appropriate policies
            assert len(scenario.activeMembers()) == 2,\
                   'I can compile policies only when there are exactly two acting agents.'
            entity,other = scenario.activeMembers()
            print 'Compiling policies...'
            self.initializePolicy(entity,other)
            belief = other.getEntity(entity.name)
            belief.policy.tables.append([entity.policy.getTable()])
            self.initializePolicy(other,entity)
            belief = entity.getEntity(other.name)
            belief.policy.tables.append([other.policy.getTable()])
            entity.policy.tables[0][0].abstractSolve(entity,entity.policy.horizon)
            other.policy.tables[0][0].abstractSolve(other,other.policy.horizon)
       # Start shell
        GuiShell.__init__(self,toplevel,scenario=scenario,classes=society,debug=debug)
##        self.setExpert()
##        self.explanationDetail.set(0)
        self.history = {}
        if self.scenario:
            self.original = copy.deepcopy(self.scenario.state)
        else:
            self.original = None

    def revert(self):
        """Reverts the current scenario back to the last saved version"""
        if self.original:
            # Reset state (and beliefs)
            sims = [self.scenario]
            while len(sims) > 0:
                scenario = sims.pop()
                scenario.state = copy.deepcopy(self.original)
                entities = scenario.members()
                while len(entities) > 0:
                    entity = entities.pop()
                    sims.insert(0,entity.entities)
                    entity.state = scenario.state
                # Reset simulation time
                scenario.time = 0
                scenario.initializeOrder()
            # Clear history window
            self.aarWin.clear()
        else:
            PsychShell.revert(self)
            if self.supportgraph:
                self.supportgraph.loadHistory(self.entities)
        # Clear action history
        self.history.clear()
        # Update sliders
        self.incUpdate()

    def initializePolicy(self,entity,partner):
        # Find branchpoints in negotiation satisfaction dynamics
        thresholds = {}
        for action,dynamics in entity.dynamics['negSatisfaction'].items():
            if dynamics and not isinstance(dynamics,str):
                for branch in dynamics.getTree().branches().values():
                    if isinstance(branch.weights,ThresholdRow):
                        thresholds[branch.threshold] = True
        # Determine which acts are negotiation moves and which are real
        negoActs = []
        realActs = []
        for option in entity.actions.getOptions():
            if option[0]['type'] in ['accept','reject']:
                option[0]['repeatable'] = False
                negoActs.append(option)
            elif option[0]['type'] == self.reader.deliverAction:
                option[0]['repeatable'] = False
                realActs.insert(0,option)
            elif 'offer' in option[0]['type']:
                option[0]['repeatable'] = False
                negoActs.insert(0,option)
            elif 'request' in option[0]['type']:
                option[0]['repeatable'] = False
                negoActs.insert(0,option)
            elif 'threat' in option[0]['type']:
                option[0]['repeatable'] = False
                negoActs.append(option)
            elif option[0]['type'] == 'doNothingTo':
                option[0]['repeatable'] = True
                negoActs.append(option)
                # To allow agents to renege, uncomment following
                realActs.append(option)
            else:
                option[0]['repeatable'] = False
                realActs.insert(0,option)
        policy = PWLTable()
        entity.policy.tables.append([policy])
        size = 1
        # First attribute: how's my negotiation satisfaction?
        state = entity.entities.state.expectation()
        weights = ThresholdRow(keys=[{'entity':entity.name,
                                      'feature':'negSatisfaction'}])
        weights.fill(state.keys())
        values = thresholds.keys()
        values.sort()
        index = policy.addAttribute(weights,values[0])
        policy.attributes[index] = (weights,values)
        size *= len(values)+1
        # Second attribute: how's my partner's negotiation satisfaction?
        weights = ThresholdRow(keys=[{'entity':partner.name,
                                      'feature':'negSatisfaction'}])
        weights.fill(state.keys())
        values = thresholds.keys()
        values.sort()
        index = policy.addAttribute(weights,values[0])
        policy.attributes[index] = (weights,values)
        size *= len(values)+1
        # Third attribute: is negotiation terminated?
        weights = ThresholdRow(keys=[{'entity':min([entity.name,partner.name]),
                                      'feature':'terminated'}])
        weights.fill(state.keys())
        policy.addAttribute(weights,0.5)
        policy.initialize()
        for index in range(len(policy.attributes)):
            obj,values = policy.attributes[index]
            if obj.specialKeys[0]['feature'] == 'terminated':
                termIndex = index
            elif obj.specialKeys[0]['entity'] == entity.name:
                myIndex = index
                assert obj.specialKeys[0]['feature'] == 'negSatisfaction'
            else:
                assert obj.specialKeys[0]['entity'] == partner.name
                assert obj.specialKeys[0]['feature'] == 'negSatisfaction'
                yrIndex = index
        del policy.rules[0]
        for rule in range(size):
            # Expand all possible rules
            factors = [0,0,0]
            factors[yrIndex] = rule % (len(values)+1)
            factors[myIndex] = rule / (len(values)+1)
            # This is what I can do when not terminated
            entry = {'rhs': None,'lhs': factors[:],'values': {}}
            for option in negoActs:
                entry['values'][entity.makeActionKey(option)] = 0.
            policy.rules.append(entry)
            # This is what I can do when terminated
            factors[termIndex] = 1
            entry = {'rhs': None,'lhs': factors,'values': {}}
            for option in realActs:
                entry['values'][entity.makeActionKey(option)] = 0.
            policy.rules.append(entry)
        
    def createAgentWin(self,entity,x=0,y=0):
        win = GuiShell.createAgentWin(self,entity,x,y)
        # Add special step buttons
        abstract = isinstance(entity,GenericModel)
        if not abstract:
            try:
                widget = win.component('%s Run Box' % (entity.ancestry()))
            except KeyError:
                # Hopefully, because this agent has no actions
                widget = None
            if widget:
                cmd = lambda s=self,e=entity:s.move(e)
                widget.add('move',text='Negotiation Move',command=cmd)
        return win

    def move(self,entity):
        # Get the legal actions from the checkbuttons
        win = self.entitywins[entity.name]
        choices = win.component('Actions').getActions()
        event = threading.Event()
        cmd = lambda s=self,e=entity,c=choices,i=event: s._move(e,c,i)
        self.background(cmd,event)

    def _move(self,entity,choices=None,interrupt=None):
        if entity.parent:
            # This is a hypothetical action within an agent's belief space
            world = entity.parent.entities
        else:
            # This is a hypothetical action within the real world
            world = self.entities
        turn = {'name':entity.name,'history':self.history}
        if choices is not None:
            turn['choices'] = choices
        done = False
        moves = []
        while not done:
            result = world.microstep([turn],
                                     hypothetical=False,
                                     explain=True)
            self.queue.put({'command':'updateNetwork'})
            self.queue.put({'command':'AAR','message':result['explanation']})
            move = result['decision'][entity.name]
            if interrupt and interrupt.isSet():
                done = True
            elif move[0]['type'] in ['doNothingTo','accept','reject']:
                done = True
            else:
                moves.append(move[0])
            for action in move:
                self.history[str(action)] = True
        self.queue.put(None)

    def singleHypothetical(self,entity=None,real=False,choices=None,
                           history=None,explain=False,suggest=False):
        if history is None:
            history = self.history
        result = GuiShell.singleHypothetical(self,entity,real,choices,
                                             history,explain,suggest)
        if real:
            if entity is None:
                name = result['decision'].keys()[0]
            else:
                name = entity.name
            move = result['decision'][name]
            for action in move:
                self.history[str(action)] = True
        return result

    def _distill(self,filename):
        """Writes a lightweight representation of the current scenario"""
        if filename:
            scenario = SequentialAgents()
            for agent in filter(lambda e:not e.instanceof('Hasan'),
                                self.scenario.members()):
                scenario[agent.name] = agent
                if agent.relationships.has_key('negotiateWith'):
                    for partner in agent.relationships['negotiateWith']:
                        if scenario.has_key(partner):
                            print 'Duplicate warning:',partner
                        else:
                            scenario[partner] = agent.getEntity(partner)
            scenario.state = self.scenario.state
            lightweight = PWLSimulation(scenario)
            lightweight.save(filename)
        self.queue.put(None)

if __name__ == "__main__":
    import getopt
    import sys
    try:
	optlist,args = getopt.getopt(sys.argv[1:],'',
				     ['scenario=','society=','debug=','help',
                                      'uninstantiated','uncompiled'])
    except getopt.error:
        error = True
        optlist = []
        args = []

    error = False
    society = None
    scenario = None
    debug = 0
    instantiated = True
    compile = True
    for option in optlist:
        if option[0] == '--scenario':
            scenario = option[1]
        elif option[0] == '--society':
            society = option[1]
        elif option[0] == '--debug':
            try:
                debug = int(option[1])
            except ValueError:
                error = True
        elif option[0] == '--help':
            error = True
        elif option[0] == '--uninstantiated':
            instantiated = False
        elif option[0] == '--uncompiled':
            compile = False

    if len(args) != 1:
        error = True
    else:
        filename = args[0]

    if error:
        print 'Usage: python ELECTgui.py [--scenario <filename>] [--society <filename>] [--uninstantiated] [--debug <level>] [--help] <input_file>'
        print '\t<input_file>:          The CSV file to use as the ELECT agent specification'
        print '\t--society  <filename>: Load the given XML file as the generic society'
        print '\t                       (If none provided, it is generated from the CSV file)'
        print '\t--scenario <filename>: Load the given XML file as the initial scenario'
        print '\t                       (If none provided, it is generated from the society)'
        print '\t--uninstantiated:      Generate a society, but do not instantiate a scenario'
        print '\t--uncompiled:          If generating a scenario, do not compile any policies'
        print '\t--debug <level>:       Set the debugging level of detail to the given integer'
        print '\t--help:                Print this message'
    else:
        import Pmw

        root = Pmw.initialise()
        root.title('ELECT Bilat')
        shell = ELECTGui(root,filename,society,scenario,instantiated,compile,debug)
        shell.pack(fill='both',expand='yes')
        shell.mainloop(root)
