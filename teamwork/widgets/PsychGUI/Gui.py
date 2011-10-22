# standard Python packages
import copy
import os
from Queue import Queue,Empty
import re
import threading
import time
from xml.dom.minidom import parseString

# Standard widget packages
import Tkinter
# Hack to fix Tkinter bug 
#Tkinter.wantobjects = 0
import tkMessageBox
import tkFileDialog
import Pmw
# Homegrown widget packages
from teamwork.widgets.images import getImage
from teamwork.widgets.balloon import EntityBalloon
from teamwork.widgets.MultiWin import MultipleWin,InnerWindow
from teamwork.widgets.player import PlayerControl
##from teamwork.widgets.htmlViewer.tkhtml import tkHTMLViewer
import teamwork.widgets.Grapher as Grapher
#from Graph import *
from ScenarioWizard import ScenarioWizard
from objectives import ObjectivesDialog
##from TurnDialog import TurnDialog
from MAID import MAIDFrame
from CampaignAnalysis import AnalysisWizard
from TreeAAR import JiveTalkingAAR
from WorldView import WorldViewer
from AgentWindow.AgentWindow import AgentWin
from NetworkView import PsymWindow
# PsychSim stuff
from teamwork.shell.PsychShell import PsychShell
from teamwork.agent.Generic import GenericModel
from teamwork.multiagent.GenericSociety import GenericSociety
from teamwork.multiagent.Historical import HistoricalAgents
from teamwork.multiagent.pwlSimulation import PWLSimulation
from teamwork.policy.pwlTable import PWLTable
from teamwork.math.Keys import StateKey
from teamwork.math.ProbabilityTree import ProbabilityTree
from teamwork.messages.PsychMessage import Message
# Authentication
from getpass import getuser
##def getuser(): return 'marsella'

class GuiShell(PsychShell,Pmw.MegaWidget):
    """Subclass for Tk interface to PsychSim
    
    Key components for manipulating L{Generic Societies<teamwork.multiagent.GenericSociety>}:
       - L{Class hierarchy viewer<PsymWindow>}
       - L{Windows for individual agents<AgentWin>}
    Key components for manipulating L{Instantiated Scenarios<teamwork.multiagent.Simulation.MultiagentSimulation>}:
       - L{Scenario creation wizard<ScenarioWizard>}
       - L{Social network viewer<PsymWindow>}
       - L{Windows for individual agents<AgentWin>}
       - L{Simulation history and explanation<JiveTalkingAAR>}
       - L{Dialog for entering objectives<ObjectivesDialog>}
       - L{Wizard for analyzing and comparing sets of messages<AnalysisWizard>}
    @ivar menus: dictionary of all of the individual pulldown menus (indexed by label of menu
    @type menus: strS{->}Menu
    """
    titleLabel = "PsychSim"
    # Menu titles
    simulationLabel = 'Simulation'
    explanationLabel = 'expcascade'

    def __init__(self,toplevel,scenario=None,classes=None,agentClass=None,
                 multiagentClass=None,**kw):
        """Constructor
        @param toplevel: the Toplevel widget to contain this widget
        @param scenario: initial scenario
        @param classes: initial generic society
        @param agentClass: object class used to create new agents
        @param multiagentClass: object class used to create new scenarios
        @param debug: level of detail in debugging messages
        """
        optiondefs = (
            ('options',None,Pmw.INITOPT),
            ('debug',0,self.setDebugLevel),
            ('activatecommand',self.splash,Pmw.INITOPT),
            )
        self.defineoptions(kw, optiondefs)
        self.queue = Queue()
        self.themewins = []
        self.entitywins = {}
        self.psymwindow = None
        self.aarWin = None
        self.helpWin = None
        self.worldWin = None
        self.otherHist = {}
        self.resetFlag = 1
        self.supportgraph = None
        self.graph = None
        self.horizon = None

        version = self.__VERSION__
        # Try to parse source code SVN version info
        try:
            f = open('.svn/dir-wcprops')
        except IOError:
            try:
                f = open('.svn/all-wcprops')
            except IOError:
                f = None
        if f:
            data = f.read()
            f.close()
            exp = re.search('(?<=/ver/)\d+(?=/trunk/teamwork)',data,re.DOTALL)
            if exp:
                version += ' (SVN rev %s)' % (exp.group(0))
            else:
                print 'Unable to parse SVN info'
        Pmw.aboutversion(version)
        Pmw.aboutcontact('Stacy Marsella and David V. Pynadath')
        Pmw.MegaWidget.__init__(self)
        # Set some default options
        if self['options']:
            family = self['options'].get('Appearance','fontFamily')
            size = self['options'].get('Appearance','fontSize')
        else:
            family = 'Helvetica'
            size = '14'
        toplevel.option_add('*font','%s -%s bold' % (family,size))
        # Bind the close-window button to stopping PsychSim
        toplevel.protocol('WM_DELETE_WINDOW',self.stop)
        # Set icon for minimization (doesn't work under some WMs)
        toplevel.iconbitmap('@%s' % (getImage('icon.xbm')))
        # Set up balloons
        self.balloon = EntityBalloon(self.component('hull'),state='balloon')
        self.toggleBalloonVar = Tkinter.IntVar()
        self.toggleBalloonVar.set(1)

        self.drawMenubar(toplevel)
        toplevel.config(menu=self.menuBar)
        self.windows = {'Agent':[],
                        'Analysis':[],
                        'Debug':[],
                        'Log':[]
                        }
        self.toolbar = Tkinter.Frame(self.component('hull'),relief='raised',borderwidth=3)
        self.modes = {}
        modeList = []
        key = 'None'
        modeList.append(key)
        self.modes[key] = {'windows':[],
                           'help':'Hide all detail windows'}
        key = 'Agents'
        modeList.append(key)
        self.modes[key] = {'windows':['Agent','Debug'],
                           'help':'View all agent windows'}
        key = 'Run'
        modeList.append(key)
        self.modes[key] = {'windows':['Analysis'],
                           'help':'Run simulation and review agent behavior'}
        key = 'All'
        modeList.append(key)
        self.modes[key] = {'windows':self.windows.keys(),
                           'help':'View all scenario windows'}
        itemList = self.modes.keys()
        width = max(map(lambda n:len(n),itemList))
        self.modeBox = Pmw.OptionMenu(self.toolbar,
                                      menubutton_width=width+5,
                                      items=itemList,
                                      labelpos='w',
                                      label_text='Mode:',
                                      command=self.modeSelect)
        self.modeBox.pack(side='left')
        # Simulation control buttons
        self.control = PlayerControl(self.toolbar,orient='horizontal')
        self.control.add('prev',state='disabled')
        self.control.add('play',command=self.realStep)
        self.control.addImage('play','stop')
        self.control.add('next',state='disabled')
        self.control.pack(side='left')

##        self.slider = Scale(self.toolbar,orient=HORIZONTAL)
##        self.slider.pack()

        if self['options']:
            size = self['options'].get('Appearance','fontSize')
        else:
            size = '14'
        self.timeDisplay = Tkinter.Label(self.toolbar,
                                 font=('Courier',size,'bold'),
                                 background='#000000',foreground='#00bb11',
                                 relief='sunken',justify='right',
                                 anchor='e',width=3)
        self.timeDisplay.pack(side='left',expand=0)
        self.toolbar.pack(side='top',fill='x',expand=0)
        # Main workspace
        self.main =  MultipleWin(parent = self.component('hull'), relief = 'ridge',
                                 borderwidth = 4,
                                 height = 500,
                                 width = 1000,
                                 readyText='Ready',
                                 )
        self.main.pack(side ="top", fill = 'both', expand = 1)
        PsychShell.__init__(self,scenario=scenario,
                            classes=classes,
                            agentClass=agentClass,
                            multiagentClass=multiagentClass,
                            options=self['options'],
                            debug=self['debug'])
        # Set view to generic/specific as appropriate
        self.view = None
        if self.scenario:
            self.viewSelect('scenario',alreadyLoaded=True)
        else:
            self.entities = None
            self.viewSelect('generic',alreadyLoaded=False)
        # Dialog for asking for name of new agent
        self.nameDialog = Pmw.PromptDialog(self.component('hull'),title='New Agent',
                                           entryfield_labelpos='w',
                                           label_text='Name:',
                                           defaultbutton=0,
                                           buttons=('OK','Cancel'),
                                           entryfield_validate=self.validateName,
                                           entryfield_modifiedcommand=self.checkNameValidity,
                                           command=self._addAgent)
        self.nameDialog.withdraw()
        self.nameDialog.component('buttonbox').component('OK').configure(state='disabled')
        self.newParent = None
##        # Dialog for viewing/editing the turn order of the agents
##        self.turnDialog = TurnDialog(self.component('hull'),
##                                     title='Turn Sequence',
##                                     defaultbutton=0,
##                                     buttons=('OK','Cancel'),
##                                     command=self._editOrder)
##        self.turnDialog.withdraw()
        self.clipboard = {}
##        self.poll()
        self.initialiseoptions()

    def drawTime(self):
        """Updates the simulation time in the toolbar display"""
        if self.entities:
            step = "%03d" % (self.entities.time)
        else:
            step = '   '
        self.timeDisplay.configure(text=step)
        
    def getEntityWin(self):
        """
        @return: the name and window of the top entity window
        @rtype: str,L{AgentWindow}
        """
        selected = self.main.find_current_window(None)
        for name,window in self.entitywins.items():
            if window.win is selected:
                return name,window
        else:
            return None,None

    def copy(self,event=None,cmd='copy'):
        windowID = self.winfo_pathname(self.winfo_id())
        name,window = self.getEntityWin()
        if name is None:
            tkMessageBox.showerror('Unable to Copy','Clipboard is accessible only from agent windows')
            return
        selected = window.getSelection()
        if selected is None:
            tkMessageBox.showerror('Unable to Copy','Nothing selected!')
        else:
            if isinstance(selected,ProbabilityTree):
                self.clipboard_clear(displayof=windowID)
                self.clipboard_append(selected.__xml__().toxml(),displayof=windowID,type='PWL')
                self.clipboard_append(selected.simpleText())
            else:
                tkMessageBox.showerror('Unable to Copy','Sorry, only piecewise linear functions can go onto my clipboard.')
        
    def cut(self,event=None):
        self.copy(cmd='cut')

    def paste(self,event=None):
        windowID = self.winfo_pathname(self.winfo_id())
        try:
            selection = self.selection_get(selection='CLIPBOARD',type='PWL',displayof=windowID)
        except Tkinter.TclError:
            tkMessageBox.showerror('Unable to Paste','My clipboard is bare.')
            return
        doc = parseString(selection)
        tree = ProbabilityTree()
        tree.parse(doc.documentElement)
        name,window = self.getEntityWin()
        if name is None:
            tkMessageBox.showerror('Unable to Paste','Clipboard is usable only in agent windows')
            return
        window.paste(tree)

    def setupScenario( self, agents, progress=None ):
        """initialize L{PsychShell} with given L{scenario<teamwork.multiagent.PsychAgents.PsychAgents>}
        @param agents: the scenario to interact with
        @type agents: L{MultiagentSimulation<teamwork.multiagent.Simulation.MultiagentSimulation>}
        @param progress: optional progress display command
        @type progress: C{lambda}
        """
        PsychShell.setupScenario(self,agents,progress)
        self.aarWin.clear()
        self.viewSelect('scenario',alreadyLoaded=True)

    def showWindow(self,name):
        """Pops up an agent window for the named entity (creates the window if it has not already been drawn)
        """
        if not self.entitywins.has_key(name):
            win = self.createAgentWin(self.entities[name])
            win.win.iconify_window()
        self.entitywins[name].win.show_window()
        if self.psymwindow.rel != '_parent':
            self.psymwindow.setview(name=name)
        
    def initEntities(self,progress=None):
        PsychShell.initEntities(self,progress)
        if isinstance(self.entities,GenericSociety):
            view = 'generic'
        else:
            view = 'scenario'
        if view != self.view:
            self.clear()
        if view == 'generic':
            filename = self.societyFile
        else:
            filename = self.scenarioFile
        if filename:
            name = os.path.split(filename)[1]
            name = os.path.splitext(name)[0]
        else:
            name = "Untitled"
#        self.component('hull').title('%s - %s - %s' % (self.titleLabel,name,view))
        # Network view
        if self.psymwindow:
            self.psymwindow.configure(entities=self.entities)
        else:
            self.psymwindow = PsymWindow(self.main,entities=self.entities,
                                         balloon=self.balloon,
                                         delete=self.removeAgent,
                                         add=self.addAgent,
                                         expert=True,
                                         rename=self.renameAgent,
                                         showWindow=self.showWindow,
                                         options=self.options,
                                         windows=self.entitywins)
            self.psymwindow.place(x = 1, y = 1)
        if self.psymwindow:
            self.psymwindow.rel = None
            self.psymwindow.setview()
            for aw in self.entitywins.values():
                aw.configure(Relationships_network=self.psymwindow)
        # AAR
        if self.aarWin is None:
            if self['options']:
                family = self['options'].get('Appearance','fontFamily')
                size = self['options'].get('Appearance','fontSize')
            else:
                family = 'Helvetica'
                size = '14'
            self.aarWin = JiveTalkingAAR(self.main, title='History',
                                         width=750,height=500,
                                         font = (family,size,'normal'),
                                         fitCommand=self.doFitting,
                                         msgCommand=self.seedMessage,
                                         )
            self.windows['Analysis'].append(self.aarWin)
        self.aarWin.configure(entities=self.scenario)
        # World view
        if self.worldWin is None:
            self.worldWin = WorldViewer(self.main,title='World',
                                        World_generator=self.generate)
            self.windows['Analysis'].append(self.worldWin)
        self.worldWin.configure(entities=self.entities)
##        # Help
##        if self.helpWin is None:
##            self.helpWin = InnerWindow(parent=self.main,title='Help',
##                                       height=500,width=750)
##            self.helpWin.place(x=1,y=1)
##            widget = tkHTMLViewer(self.helpWin.component('frame'))
##            widget.display('%s/doc/index.html' % (self.directory))
##            self.windows['Debug'].append(self.helpWin)
        # Draw Graph window only if matplotlib is installed
        if Grapher.graphAvailable and self.graph is None and \
               view != 'generic':
            self.entities.__class__ = HistoricalAgents
            gw = InnerWindow(parent = self.main,title='Graph',height=600,width=600,x=401,y=1)
            gw.place(x=401,y=1)
            self.graph = Grapher.TkGraphWindow(gw,self.entities)
            self.windows['Analysis'].append(self.graph.gw)
        # Add entries to Windows menu
        menu = self.menus['Window']
        index = 0
        try:
            menu.index('Graph')
        except Tkinter.TclError:
            menu.add_command(label='Graph')
        if self.graph:
            menu.entryconfig(index,state='normal',
                             command=self.graph.gw.show_window)
        else:
            menu.entryconfig(index,state='disabled')
        index += 1
##        try:
##            menu.index('Help')
##            found = True
##        except Tkinter.TclError:
##            # Haven't created that menu yet
##            menu.add_command(label='Help',command=self.helpWin.show_window)
##        index += 1
        try:
            menu.index('History')
        except Tkinter.TclError:
            menu.add_command(label='History',command=self.aarWin.show_window)
        index += 1
        try:
            menu.index('Network')
        except Tkinter.TclError:
            menu.add_command(label='Network',
                             command=self.psymwindow.show_window)
        index += 1
        if menu.type(index) != 'separator':
            # Don't want to draw two
            menu.add_separator()
        index += 1
        self.menuBar.entryconfig('View',state='normal')
#        self.menus['File'].entryconfigure('Properties...',state='normal')
        # Update agent windows
        for index in range(len(self.entities)):
            entity = self.entities.members()[index]
            if self.entitywins.has_key(entity.name):
                self.entitywins[entity.name].update()
        if isinstance(self.entities,GenericSociety):
            for name in self.entities.root:
                self.addToMenu(name,self.menus['Window'])
        else:
            names = self.entities.keys()
            names.sort()
            for name in names:
                self.addToMenu(name,self.menus['Window'])
            self.drawTime()
        self.modeSelect('None')

    def chooseObjectives(self):
        """Dialog box for fitting scenario to observed behavior"""
        dialog = Pmw.Dialog(self.component('hull'),buttons=('OK','Cancel'),
                            title='Objectives')
        obj = dialog.createcomponent('Objectives', (),None,
                                     ObjectivesDialog, (dialog.interior(),),
                                     psyop = 0,
                                     horizflex='elastic',vertflex='elastic',
                                     objectives=self.entities.objectives[:],
                                     entities=self.entities.members())
        obj.pack(side='top',fill='x',expand='yes')
        if dialog.activate() == 'OK':
            self.entities.objectives = obj['objectives']

    def viewMAID(self):
        dialog = Pmw.Dialog(self.component('hull'),buttons=('OK',),
                            title='MAID')
        widget = dialog.createcomponent('MAID',(),None,MAIDFrame,
                                        (dialog.interior(),),
                                        entities=self.entities,
                                        )
        widget.pack(side='top',fill='both',expand='yes')
        dialog.activate()

    def generate(self):
        self.background(target=self.__generate,label='Generating')

    def __generate(self):
        self.scenario.generateWorlds()
        self.queue.put({'command': 'worlds'})
        self.queue.put(None)
            
    def removeAgent(self,entity):
        """Removes the given entity from the simulation"""
        entityList = self.entities.descendents(entity.name)
        if len(entityList) == len(self.entities):
            tkMessageBox.showerror('No Agents Left!',
                                   'At least one agent must remain')
        else:
            # Delete root from Window menu
            parents = entity.getParents()
            if len(parents) == 0:
                self.menus['Window'].delete(entity.name)
            else:
                for name in parents:
                    self.menus[name].delete(entity.name)
            for name in entityList:
                # Delete from society/scenario
                if self.entities[name].attributes.has_key('window'):
                    del self.entities[name].attributes['window']
                del self.entities[name]
                if self.entitywins.has_key(name):
                    # Delete window
                    self.entitywins[name].win.destroy()
                    del self.entitywins[name]
            # Check whether any parents are now leaf nodes
            for name in parents:
                if len(self.entities.network[name]) == 0:
                    # Deleted only child
                    parent = self.entities[name]
                    if parent.getParents():
                        for grand in parent.getParents():
                            index = self.menus[grand].index(name)
                            self.menus[grand].delete(name)
                            self.addToMenu(name,self.menus[grand],index)
                    else:
                        index = self.menus['Window'].index(name)
                        self.menus['Window'].delete(name)
                        self.addToMenu(name,self.menus['Window'],index)
            for window in self.entitywins.values():
                for name in entityList:
                    # Remove agent as relationship filler
                    window.component('Relationships').removeFiller(name)
                    # Remove agent as object of actions
                    entity = window['entity']
                    for option in entity.actions.getOptions():
                        for action in option:
                            if action['object'] == name:
                                entity.actions.extras.remove(option)
                                break
                    if window.component('Actions_object').get() == name:
                        window.component('Actions_object').selectitem(0)
                    # Remove agent as object of goals
                    goals = entity.getGoals()
                    for goal in goals[:]:
                        if name in goal.entity:
                            goals.remove(goal)
                            break
                    entity.setGoals(goals)
                window.component('Actions').drawActions()
                window.component('Goals').recreate_goals()

    def destroyAgentWin(self,window):
        """Cleans up after removing the window for a given entity"""
        try:
            self.windows['Agent'].remove(window)
        except ValueError:
            pass
        for name in self.entitywins.keys():
            if self.entitywins[name].win is window:
                try:
                    del self.entities[name].attributes['window']
                except KeyError:
                    pass
                agentWindow = self.entitywins[name]
                del self.entitywins[name]
                break
        self.queue.put({'command': 'destroy','window':agentWindow})
        
    def renameAgent(self,old,new):
        """Changes the name and references to a given agent
        @type old,new: str
        """
        # Update name in generic society
        self.classes.renameEntity(old,new)
        if self.entitywins.has_key(old):
            # Update agent window table
            self.entitywins[new] = self.entitywins[old]
            del self.entitywins[old]
        for window in self.entitywins.values():
            window.renameEntity(old,new)
        # Update Windows menu entry
        if self.menus.has_key(old):
            newMenu = self.menus[old]
            del self.menus[old]
            self.menus[new] = newMenu
        parents = self.classes[new].getParents()
        if parents:
            # Find all of the parent menus to update
            positions = map(lambda p: self.classes.network[p].index(new),
                            parents)
            menus = map(lambda p: self.menus[p],parents)
        else:
            # Update the root Window menu
            positions = [self.classes.root.index(new)]
            menus = [self.menus['Window']]
        for index in range(len(menus)):
            # Figure out where the separator is
            base = 1
            while menus[index].type(base-1) != 'separator':
                base += 1
            menus[index].delete(old)
            self.addToMenu(new,menus[index],base+positions[index])

    def addAgent(self,entity,agent=None):
        """Adds an agent as a child of the given entity"""
        self.newParent = entity
        if agent:
            self._addAgent('OK',agent)
        else:
            self.nameDialog.component('entry').focus_set()
            self.nameDialog.activate(geometry = 'centerscreenalways',
                                     globalMode=0)

    def _addAgent(self,button,agent=None):
        """Callback from name dialog that actually adds the agent"""
        if button == 'OK':
            if agent is None:
                agent = GenericModel(self.nameDialog.get(),self.newParent.depth)
                todo = True
            else:
                todo = False
            if not self.newParent.name in agent.parentModels:
                agent.parentModels.append(self.newParent.name)
            self.entities.addMember(agent)
#            if todo:
#                window = self.createAgentWin(agent)
#                window.win.iconify_window()
            # New relationship filler
            for window in self.entitywins.values():
                window.component('Relationships').addStaticFiller(agent.name)
            # New window menu item
            if len(self.classes.network[self.newParent.name]) == 1:
                # This is the first child for this parent
                menus = map(lambda p: self.menus[p],
                            self.newParent.getParents())
                if not menus:
                    menus = [self.menus['Window']]
                for menu in menus:
                    index = menu.index(self.newParent.name)
                    menu.delete(index)
                    new = Tkinter.Menu(menu,tearoff=0)
                    cmd = lambda s=self,n=self.newParent.name: s.showWindow(n)
                    new.add_command(label='Show Window',command=cmd)
                    new.add_separator()
                    menu.insert_cascade(index,menu=new,
                                        label=self.newParent.name)
                    self.menus[self.newParent.name] = new
            self.addToMenu(agent.name,self.menus[self.newParent.name])
        else:
            todo = True
        if todo:
            self.nameDialog.deactivate()
            self.nameDialog.deleteentry(0,'end')
        self.newParent = None

    def validateName(self,name):
        """Checks whether the new name being entered in the agent dialog is valid or not"""
        if len(name) == 0:
            # Empty names not allowed
            return Pmw.PARTIAL
        for other in self.entities.members():
            if other.name == name:
                # New agent name must be unique
                return Pmw.PARTIAL
        return Pmw.OK

    def checkNameValidity(self):
        """Disables the OK button on the agent name dialog if the current text entry is invalid"""
        button = self.nameDialog.component('buttonbox').component('OK')
        if self.nameDialog.component('entryfield').valid():
            button.configure(state='normal')
        else:
            button.configure(state='disabled')

    def editOrder(self):
        """Edits the turn order"""
        if self.view == 'generic':
            order = copy.deepcopy(self.entities._keys)
        else:
            order = self.entities.getSequence()
        self.turnDialog.configure(editor_order=order,
                                  editor_elements=self.entities.keys())
        self.turnDialog.configure(editor_editable=True)
        self.turnDialog.activate()

    def _editOrder(self,button):
        """Callback from name dialog that actually adds the agent"""
        if button == 'OK':
            editor = self.turnDialog.component('editor')
            if self.view == 'generic':
                self.entities._keys = editor['order'][:]
            else:
                self.entities.applyOrder(editor['order'][:])
        self.turnDialog.deactivate()
            
    def setState(self,state=None):
        if not state:
            state = self.main['readyText']
        self.state = state
        self.main.Btitle.config(text=self.state)

    # Fitting methods
    
    def doFitting(self,actor,action,step):
        """Fits the agents' goal weights based on behavior in fit window"""
        self.showWindow(actor)
        window = self.entitywins[actor]
        window.win.show_window()
        window.win.select_window()
        # Select goal tab
        notebook = window.component('notebook')
        notebook.selectpage('R')
        target = lambda s=self,n=actor,act=action,t=step:\
                 s.__doFitting(n,act,t)
        self.background(target=target,label='Fitting')

    def __doFitting(self,name,action,step):
        """Fitting helper method (for running in background)"""
        agent = self.entities[name]
        goalPane = self.entitywins[name].component('Goals')
        original = dict(agent.goals)
        goals = agent.fit(action,label=step)
        if isinstance(goals,str):
            # Unable to fit
            self.queue.put({'command':'error','title':'Failure',
                            'message':goals})
            self.queue.put(None)
        else:
            self.queue.put({'command':'updateGoals','widget':goalPane,
                            'agent':agent,'weights':goals})
            # In Python 2.5, we could simply do self.queue.join()
            while not self.queue.empty():
                time.sleep(1)
            if step == self.entities.time:
                # Replace last hypothetical action with the desired one
##                 self.queue.put({'command':'pop','widget':self.aarWin})
                total = 0.
                for goal in agent.getGoals():
                    total += abs(original[str(goal)]-goals[goal.toKey()])
                self.hypothetical(entity=self.scenario[name],real=True)
                delta = int(100.*total)/len(agent.getGoals())
                msg = 'Fitting was successful, with a %d%% shift in goal weights.' % (delta)
                self.queue.put({'command':'info','title':'Success',
                                'message':msg})
            else:
                msg = 'Fitting was successful, and the new goal weights will affect any future actions.  However, the previously selected action cannot be undone and will remain in the history.'
                self.queue.put({'command':'info','title':'Success',
                                'message':msg})
                self.queue.put(None)

    # Simulation methods
    
    def doActions(self,actions,results=None):
        """
        Performs the actions, provided in dictionary form
        @type actions: strS{->}L{Action}[]
        """
        if len(actions) > 1:
            tkMessageBox.showerror('Forced Actions','I am currently unable to force multiple agents to perform fixed actions at the same time.')
        else:
            actor,option = actions.items()[0]
            self.realStep(self.entities[actor],[option])

    def realStep(self,entity=None,choices=None,iterations=1):
        """Queries and performs the given entity for its hypothetical choice"""
        if entity is None:
            invalid = self.actionCheck()
            if invalid:
                tkMessageBox.showerror('Agent Action Error','There are agents with no allowable actions:\n%s\nPlease, either go to the Action pane and select at least one possible choices, or remove the agent from the turn order.' %
                                       ', '.join(invalid))
                return
        args = {'entity':entity,'real':True,'choices':choices,
                'iterations':iterations,
                'explain':self.explanationDetail.get() > 0,
                'suggest':self.explanationDetail.get() > 1,
                }
        self.background(self.hypothetical,kwargs=args)
        
    def hypoStep(self,entity=None,choices=None,iterations=1):
        """Queries and displays the given entity for its hypothetical choice"""
        if entity is None:
            invalid = self.actionCheck()
            if invalid:
                tkMessageBox.showerror('Agent Action Error','There are agents with no allowable actions:\n%s\nPlease, either go to the Action pane and select at least one possible choices, or remove the agent from the turn order.' %
                                       ', '.join(invalid))
                return
        args = {'entity':entity,'real':False,'choices':choices,
                'iterations':iterations,
                'explain':self.explanationDetail.get() > 0,
                'suggest':self.explanationDetail.get() > 1,
                }
        self.background(self.hypothetical,kwargs=args)

    def hypothetical(self,entity=None,real=False,choices=None,iterations=1,
                     explain=False,suggest=False):
        results = []
        for t in range(iterations):
            results.append(self.singleHypothetical(entity,real,choices,
                                                   explain=explain,
                                                   suggest=suggest))
        self.queue.put(None)
        if iterations == 1:
            return results[0]
        else:
            return results

    def actionCheck(self):
        """Verifies that all agents in the current turn sequence have at
        least one action available to perform.
        @return: any agents who do not have any such actions
        @rtype: str[]
        """
        invalid = []
        for key in self.entities.order.keys():
            if isinstance(key,StateKey):
                if len(self.entities[key['entity']].actions.getOptions()) == 0:
                    invalid.append(key['entity'])
        return invalid
    
    def singleHypothetical(self,entity=None,real=False,choices=None,
                           history=None,explain=False,suggest=False):
        if entity and entity.parent:
            # This is a hypothetical action within an agent's belief space
            world = entity.parent.entities
        else:
            # This is a hypothetical action within the real world
            world = self.entities
        if entity:
            if history:
                turn = [{'name':entity.name,'history':history}]
            else:                
                turn = [{'name':entity.name}]
            if choices:
                turn[0]['choices'] = choices
        else:
            turn = []
        result = world.microstep(turn,hypothetical=not real,
                                 explain=explain,suggest=suggest)
        self.processResult(result)
        self.queue.put({'command':'updateNetwork'})
        self.queue.put({'command':'AAR','message':result['explanation']})
        return result
    
    def processResult(self,result):
        """Hook for handling the result of a microstep
        """
        pass

    def validate(self):
        okLabel = 'OK'
        names = map(lambda e:e.name,self.entities.members())
        dialog = Pmw.SelectionDialog(self.component('hull'),
                                     buttons = [okLabel,'Cancel'],
                                     defaultbutton = okLabel,
                                     title = 'Scenario Validation',
                                     scrolledlist_listbox_selectmode = 'multiple',
                                     scrolledlist_labelpos='NW',
                                     scrolledlist_label_text='Please select the entity models that you wish to declare as validated:',
                                     scrolledlist_items=names)
        listbox = dialog.component('scrolledlist')
        listbox.component('listbox').selection_set(0,len(names)-1)
        if dialog.activate() == okLabel:
            for name in listbox.getcurselection():
                entity = self.entities[name]
                entry = {'what':'validated',
                         'who':getuser(),
                         'when':time.time()
                         }
                entity.extendHistory(entry)
            self.balloon.update()
        
    def modeSelect(self,but):
        change = False # Flag to prevent infinite recursion
        for key in self.windows.keys():
            for w in self.windows[key]:
                if key in self.modes[but]['windows']:
                    if w.iconified:
                        change = True
                        w.show_window()
                elif not w.iconified:
                    change = True
                    w.iconify_window()
        if change:
            # Kind of a hacked way of updating the menu and toolbar
            menu = self.menus['View']
            menu.invoke(but)
            self.modeBox.invoke(but)


    def splash(self,soundFile=None):
        if soundFile:
            import popen2
            aud =  os.path.dirname(__file__) + soundFile
            popen2.popen2('aplay ' + aud)
        photo = Tkinter.PhotoImage(file=getImage('faces.gif'))
        palette = Pmw.Color.getdefaultpalette(self.component('hull'))
        dialog = Pmw.AboutDialog(self.component('hull'),
                                 applicationname='PsychSim',
                                 message_fg = palette['background'],
                                 message_bg = palette['foreground'],
                                 icon_image=photo)
        dialog.lift()
        dialog.activate()
        
    def drawMenubar(self,root):
        self.menus = {}
        self.menuBar = Tkinter.Menu(self.component('hull'),tearoff=0)
        aqua = (self.component('hull').tk.call("tk", "windowingsystem") == 'aqua')

        if aqua:
            # Apple menu
            menu = Tkinter.Menu(self.menuBar,name='apple',tearoff=0)
            menu.add_command(command=self.splash,label = 'About PsychSim')
            self.menuBar.add_cascade(label='PsychSim',menu=menu)

        # FILE
        menu = Tkinter.Menu(self.menuBar,tearoff=0)
        menu.add_command(command = self.createScenario,
                         accelerator='CTRL+N',label = 'New Scenario...')
        root.bind_class(root,'<Control-Key-n>',self.createScenario)
        menu.add_command(command = self.load,label = 'Open...',
                         accelerator='CTRL+O')
        root.bind_class(root,'<Control-Key-o>',self.load)
        menu.add_separator()
        menu.add_command(command = self.saveBoth,accelerator='CTRL+S',
                         label = 'Save')
        root.bind_class(root,'<Control-Key-s>',self.saveBoth)
        menu.add_command(command = self.saveAs,label = 'Save As...')
        menu.add_command(command = self.export, label = 'Export...')
        menu.add_command(command = self.distill, label = 'Distill...',state='disabled')
        menu.add_separator()
        menu.add_command(command = self.revert, label = 'Revert')
#         menu.add_command(command = self.view, label = 'Properties...',
#                          state='disabled')
        menu.add_separator()
        menu.add_command(command = self.close,accelerator='CTRL+W',
                         label = 'Close')
        root.bind_class(root,'<Control-Key-w>',self.close)
        menu.add_command(command = self.stop,label = 'Quit',
                         accelerator='CTRL+Q')
        root.bind_class(root,'<Control-Key-q>',self.stop)
        self.menuBar.add_cascade(label='File',menu=menu)
        self.menus['File'] = menu

        # EDIT
        menu = Tkinter.Menu(self.menuBar,tearoff=0)
        menu.add_command(label='Cut',state='disabled',command=self.cut,
                         accelerator='CTRL+X')
        root.bind_class(root,'<Control-Key-x>',self.cut)
        menu.add_command(label='Copy',command=self.copy,
                         accelerator='CTRL+C')
        root.bind_class(root,'<Control-Key-c>',self.copy)
        menu.add_command(label='Paste',command=self.paste,
                         accelerator='CTRL+V')
        root.bind_class(root,'<Control-Key-v>',self.paste)
        self.menuBar.add_cascade(label='Edit',menu=menu)
        self.menus['Edit'] = menu
        
        # VIEW
        menu = Tkinter.Menu(self.menuBar,tearoff=0)
        menu.add_command(label='Scenario',command=self.viewSelect)
        if self['options'] and \
                self['options'].get('General','testing') == 'true':
            menu.add_command(label='MAID',command=self.viewMAID)
##        menu.add_command(label='Turn Order',command=self.editOrder)
        menu.add_separator()
        menu.add_radiobutton(label='None',
                             command = lambda s=self:s.modeSelect('None'))
        menu.add_radiobutton(label='Agents',
                             command = lambda s=self:s.modeSelect('Agents'))
        menu.add_radiobutton(label='Run',command = lambda s=self:\
                                 s.modeSelect('Run'))
        menu.add_radiobutton(label='All',
                             command = lambda s=self:s.modeSelect('All'))
        self.menuBar.add_cascade(label='View',menu=menu)
        self.menus['View'] = menu

        # OPTIONS
        menu = Tkinter.Menu(self.menuBar,tearoff=0)
        self.explanationDetail = Tkinter.IntVar()
#        subMenu = Menu(menu,tearoff=0)
        menu.add_radiobutton(variable=self.explanationDetail,
                                value = 0,label = 'No Detail',
                                command=self.setExplanation)
        menu.add_radiobutton(value = 1,label = 'Low Detail',
                                variable=self.explanationDetail,
                                command=self.setExplanation)
        menu.add_radiobutton(value = 2,label = 'High Detail',
                                variable=self.explanationDetail,
                                command=self.setExplanation)
        if self['options']:
            # Extract from config file
            self.explanationDetail.set(int(self['options'].get('General','explanation')))
        else:
            self.explanationDetail.set(2)
#        menu.add_cascade(menu=subMenu,label = 'Explanation Detail')
        self.menuBar.add_cascade(label='Options',menu=menu)
        self.menus['Options'] = menu

        # SIMULATION
        menu = Tkinter.Menu(self.menuBar,tearoff=0)
        menu.add_command(command = self.hypoStep,label = 'Hypothetical Step')
        menu.add_command(command = self.realStep, label = 'Step')
        menu.add_command(command = self.run, label = 'Run...')
        menu.add_command(command = self.evaluate, label = 'Evaluate...')
        menu.add_separator()
        menu.add_command(command = self.chooseObjectives,label='Objectives...')
        if self['options'] and \
                self['options'].get('General','psyase') == 'true':
            menu.add_command(state='disabled',command = self.validate,
                             label='Validate...')
        self.menuBar.add_cascade(label=self.simulationLabel,menu=menu,
                                 state='disabled')
        self.menus[self.simulationLabel] = menu

        # WINDOWS
        menu = Tkinter.Menu(self.menuBar,tearoff=0)
        self.menuBar.add_cascade(label='Window',menu=menu)
        self.menus['Window'] = menu

        # HELP
        menu = Tkinter.Menu(self.menuBar,tearoff=0)
        if not aqua:
            menu.add_command(command=self.splash,label = 'About PsychSim')
        menu.add_checkbutton(variable = self.toggleBalloonVar,
                             command = self.toggleBalloon,
                             label = 'Balloon help')
        self.menuBar.add_cascade(label='Help',menu=menu)
        self.menus['Help'] = menu

    def setExplanation(self):
        if self['options']:
            self['options'].set('General','explanation',
                                str(self.explanationDetail.get()))
            f = open(self['options'].get('General','config'),'w')
            self['options'].write(f)
            f.close()

    def viewSelect(self,view=None,alreadyLoaded=False):
        """Toggles between views of generic society and specific scenario"""
        if not alreadyLoaded:
            self.clear()
        if view:
            self.view = view
        elif self.view == 'generic':
            self.view = 'scenario'
        else:
            self.view = 'generic'
        menu = self.menus['File']
        if self.view == 'generic':
            label = 'Scenario'
            new = self.classes
            menu.entryconfigure('Export...',state='disabled')
            menu.entryconfigure('Distill...',state='disabled')
            menu.entryconfigure('Revert',state='disabled')
            self.control.pack_forget()
            self.timeDisplay.pack_forget()
        else:
            label = 'Generic Models'
            new = self.scenario
            menu.entryconfigure('Export...',state='normal')
##            menu.entryconfigure('Distill...',state='normal')
            menu.entryconfigure('Revert',state='normal')
            self.control.pack(side='left')
            self.timeDisplay.pack(side='left')
        menu = self.menus['View']
        if self.view == 'generic':
            self.menuBar.entryconfig(self.simulationLabel,state='disabled')
            if self['options'] and \
                    self['options'].get('General','testing') == 'true':
                menu.entryconfigure('MAID',state='disabled')
        else:
            self.menuBar.entryconfig(self.simulationLabel,state='normal')
            if self['options'] and \
                    self['options'].get('General','testing') == 'true':
                menu.entryconfigure('MAID',state='normal')
        try:
            menu.entryconfigure('Scenario',label=label)
        except:
            menu.entryconfigure('Generic Models',label=label)
        if label == 'Scenario' and not self.scenario:
            menu.entryconfigure(label,state='disabled')
        else:
            menu.entryconfigure(label,state='normal')
        if not alreadyLoaded:
            alreadyLoaded = (new is self.entities)
        self.entities = new
        if not alreadyLoaded:
            self.initEntities()
        
    def toggleBalloon(self):
        """Toggles visibility of balloon helpIt might not be a good idea to toggle this off right now"""        
        if self.toggleBalloonVar.get():
            self.balloon.configure(state='balloon')
        else:
            self.balloon.configure(state='none')
            
    def createAgentWin(self, entity, x=0, y=0):
        """Creates an agent window for the given entity at the given point"""
        abstract = isinstance(entity,GenericModel)
        if abstract:
            society = self.classes
        else:
            society = self.entities
        if self['options'] and \
                self['options'].get('General','testing') == 'true':
            valueCmd = self.expectedValue
        else:
            valueCmd = None
        aw = AgentWin(self.main,
                      entity=entity, x=x, y=y,society=society,
                      expert=True,balloon=self.balloon,
                      actCmd=self.doActions,stepCmd=self.realStep,
                      msgCmd=self.msgSend,policyCmd=self.compilePolicy,
                      hypoCmd=self.hypoStep,valueCmd=valueCmd,
                      abstract=abstract,options=self.options,
                      destroycommand=self.destroyAgentWin,
                      )
        aw.configure(Relationships_network=self.psymwindow)
        self.windows['Agent'].append(aw.win)
        self.entitywins[entity.name] = aw
        entity.attributes['window'] = aw
        self.menuBar.entryconfig('Window',state='normal')
        return aw

    def addToMenu(self,name,menu,index='end'):
        """Adds a new entry to the given menu for an entity, and any descendents
        """
        cmd = lambda s=self,n=name: s.showWindow(n)
        try:
            children = self.classes.network[name]
        except KeyError:
            children = []
        if len(children) > 0:
            # Cascade
            try:
                new = self.menus[name]
            except KeyError:
                new = Tkinter.Menu(menu,tearoff=0)
                new.add_command(label='Show Window',command=cmd)
                new.add_separator()
                self.menus[name] = new
                for child in children:
                    self.addToMenu(child,new)
            menu.insert_cascade(index,label=name,menu=new)
        else:
            # Command
            menu.insert_command(index,label=name,command=cmd)

    def clear(self):
        # Disable menus
        for label in [self.simulationLabel,'View']:
            self.menuBar.entryconfig(label,state='disabled')
        if self.menus['Window'].index('end'):
            for index in range(int(self.menus['Window'].index('end')),0,-1):
                try:
                    label = self.menus['Window'].entrycget(index,'label')
                except:
                    break
                self.menus['Window'].delete(label)
        if self.entities:
            for name in self.entities.keys():
                if self.menus.has_key(name):
                    del self.menus[name]
        # Close windows
        while len(self.themewins) > 0:
            win = self.themewins.pop()
            win.component('frame').destroy()
            del win
        self.balloon.delete()
        # Reset permanent windows
        if self.aarWin:
            self.aarWin.clear()
        if self.psymwindow:
            self.psymwindow.clear()
        if self.graph:
            for window in self.windows['Analysis']:
                if window.cget('title') == 'Graph':
                    self.windows['Analysis'].remove(window)
                    window.destroy()
                    self.graph = None
                    break
        if self.worldWin:
            self.worldWin.clear()
        for name,win in self.entitywins.items():
            win.destroy()
            del self.entitywins[name]
        self.windows['Agent'] = []
        
    def close(self,event=None,load=False):
        if self.view == 'generic':
            if not load:
                self.resetSociety()
        else:
            self.scenario = None
            self.scenarioFile = None
        if load:
            self.clear()
        else:
            self.viewSelect('generic')

    # Methods for handling interaction with susceptibility component

    def setupSusceptibility(self,addr=None):
        dialog = Pmw.Dialog(self.component('hull'),
                            title='Susceptibility Agent',
                            buttons=['OK','Cancel'],
                            defaultbutton='OK')
        host = Pmw.EntryField(dialog.component('dialogchildsite'),
                              command=dialog.invoke,
                              labelpos='w',
                              label_text='Host:',
                              label_width=7,
                              label_justify='left'
                              )
        if self.susceptibility:
            str = self.susceptibility[0]
        else:
            str = '127.0.0.1' # localhost
        host.setentry(str)
        host.pack(side='top')
        counter = Pmw.Counter(dialog.component('dialogchildsite'),
                              labelpos='w',
                              label_text='Port:',
                              label_width=7,
                              label_justify='left'
                              )
        port = counter.component('entryfield')
        if self.susceptibility:
            port.setentry(`self.susceptibility[1]`)
        counter.pack(side='top')
        if dialog.activate() == 'OK':
            addr = (host.component('entry').get(),
                    int(port.component('entry').get()))
            PsychShell.setupSusceptibility(self,addr)

    def selectSusceptibility(self):
        if self.susceptibility:
            dialog = Pmw.SelectionDialog(self.component('hull'),
                                         title='Susceptibility',
                                         buttons=['OK','Cancel'],
                                         defaultbutton='OK',
                                         scrolledlist_labelpos='n',
                                         scrolledlist_label_text='Select PTA:'
                                         )
            items = map(lambda e:e.name,self.entities.members())
            dialog.component('scrolledlist').setlist(items)
            if dialog.activate() == 'OK':
                for name in dialog.component('scrolledlist').getcurselection():
                    if not self.querySusceptibility(name):
                        msg = 'Unable to query susceptibility agent!'
                        tkMessageBox.showerror('Susceptibility error',msg)
        else:
            tkMessageBox.showerror('Susceptibility error',
                                   'Please configure susceptibility agent '+\
                                   'from Options menu first.  Thank you.')
        
    def handleSusceptibility(self,entity,themes):
        PsychShell.handleSusceptibility(self,entity,themes)
        if len(themes['Accepted']) == 0:
            msg = 'None'
        else:
            msg = '\n'.join(map(lambda i:i[0],themes['Accepted']))
        for win in self.themewins:
            win.change('recipient',win.boxes['recipient'].getvalue())
        tkMessageBox.showinfo(entity+' Susceptibility Result',
                              'Susceptibilities:\n'+msg)

    def displayActions(self,fullresult,step=-1):
        """Displays any explanation from the performance of actions in the appropriate AAR windows
        @param fullresult: an explanation structure, in dictionary form:
           - explanation: a list of 3-tuples of strings, suitable for passing to L{JiveTalkingAAR.displayAAR}
           - I{agent}: explanation substructures for each actor, in dictionary form:
              - decision: the actions chosen by this actor, list format
        @type fullresult: C{dict}
        @param step: the current time step (defaults to the current scenario time
        @type step: C{int}
        """
        if step < 0:
            step = self.entities.time
        self.aarWin.displayAAR(fullresult['explanation'])
        del fullresult['explanation']
        for key,observed in fullresult.items():
            actor = self.entities[key]
            self.acted.append(actor.name)
            print actor.name, '-->',observed['decision']
        self.incUpdate(None,observed['decision'], actor)

    # Threading methods
    
    def background(self,target,event=None,label='Running',kwargs={}):
        """Runs the target command in a background thread.  This handles the disabling/enabling of the relevant GUI elements.
        @param label: optional label that appears in the status bar
        @type label: str
        @param target: the command to run in the background. It should call the L{finishBackground} method when it is done (see L{__step} method for a sample target).
        @type target: lambda
        """
        self.event = event
        self.setState(label)
        self.control.toggle('play')
        self.control.component('play').configure(command=self.stopBackground)
        # Disable agent changes
        for win in self.entitywins.values():
            win.setState('disabled')
        thread = threading.Thread(target=target,kwargs=kwargs)
        thread.start()

    def stopBackground(self):
        if self.event:
            self.event.set()
        
    def finishBackground(self):
        """Cleans up after a background simulation thread"""
        # Enables all of the agent window widgets"""
        for win in self.entitywins.values():
            win.setState('normal')
        self.incUpdate()
        if self.view == 'scenario':
            self.drawTime()
            self.control.toggle('play')
            self.control.component('play').configure(command=self.realStep)
        self.balloon.update()
        self.setState()
        if self.event:
            del self.event
            self.event = None

    # Simulation methods
    
    def getHorizonDialog(self):
        if self.horizon is None:
            self.horizon = Pmw.CounterDialog(self.component('hull'),title='Projection Horizon',
                                             counter_labelpos='n',
                                             label_text='How many time steps should I project into the future?',
                                             buttons=('OK','Cancel'),
                                             defaultbutton='OK',
                                             counter_datatype='numeric',
                                             entryfield_entry_width=3,
                                             entryfield_validate={'min': 0,
                                                                  'minstrict': True},
                                             entryfield_value=1)
        return self.horizon
        
    def evaluate(self):
        dialog = self.getHorizonDialog()
        if dialog.activate() == 'OK':
            event = threading.Event()
            self.background(self.__evaluate,event,'Evaluating')

    def __evaluate(self):
        horizon = int(self.getHorizonDialog().get())
        self.scenario.simulate(horizon-1,self.event,debug=True)
        self.queue.put(None)

    def expectedValue(self,entity,world=None,description=None,
                      initial=None,background=1,display=1):
        """Computes and displays the reward expected by the given entity

        The world defaults to the current scenario.  The description is
        prepended to the AAR.  The initial reward value is subtracted from the
        computed EV (to provide a differential result if desired)."""
        if not world:
            world = self.entities
        target = lambda : self.__expectedValue(entity,world,description,
                                              initial,display)
        if background:
            self.background(target)
        else:
            return target()

    def __expectedValue(self,entity,world,description,initial,display=1):
        """Background computation of expected value"""
        action,explanation = entity.applyPolicy()
        goals = entity.getGoalVector()['state']
        distribution = explanation['options'][str(action)]['value']
        stateValue = distribution.expectation()
        result = {}
        for row,prob in goals.items():
            for key,weight in row.items():
                try:
                    subValue = stateValue[key]
                except KeyError:
                    subValue = 0.
                item = prob*weight*subValue
                try:
                    result[key] += item
                except KeyError:
                    result[key] = item
        if initial:
            result -= initial
        if not description:
            description = '%s expects the current state of the world to:\n' % \
                          entity.name
        value = self.translateReward(result,entity.name)
        if display:
            if self.explanationDetail.get() > 0:
                self.aarWin.displayAAR([description,value,''])
        self.queue.put(None)
        return result

    def compilePolicy(self,entity,depth=-1,horizon=-1,options=None,
                      pomdp=False):
        """Computes policy for a given entity for the given depth and horizon
        @param pomdp: if C{True}, use POMDP solver (default is C{False})
        @type pomdp: bool
        """
        win = self.entitywins[entity.name]
        if options is None:
            options = win.component('Actions').getActions()
        if options:
            event = threading.Event()
            if pomdp:
                cmd = lambda : self.__POMDP(entity,depth,horizon)
            else:
                cmd = lambda : self.__compilePolicy(entity,depth,horizon,options)
            self.background(cmd,event,'Compiling')

    def __compilePolicy(self,entity,depth,horizon,options):
        """Background thread method for computing policy"""
        if not self.scenario.worlds:
            # Not using possible worlds
            try:
                table = entity.policy.tables[0][0]
            except IndexError:
                table = PWLTable()
                try:
                    entity.policy.tables[0].append(table)
                except IndexError:
                    entity.policy.tables.append([table])
            table.abstractSolve(entity,entity.policy.horizon,options,self.event)
        elif depth == 0:
            # Null policy
            self.scenario.nullPolicy()
        else:
            R = entity.getRewardTable(self.scenario)
            if entity.policy.project(R,depth,interrupt=self.event,debug=False):
                pass
            elif self.event.isSet():
                tkMessageBox.showwarning('Interrupted!','The best policy found so far is displayed.')
            else:
                tkMessageBox.showerror('Overflow Error','The full specification of this agent\'s behavior is too complicated to compute and display.')
        self.queue.put({'command':'policy','window':self.entitywins[entity.name]})
        self.queue.put(None)
        
    def __POMDP(self,entity,depth,horizon):
        try:
            entity.solvePOMDP(self['options'].get('POMDP','solver'),
                              depth,horizon,discount=0.9,interrupt=self.event)
        except IOError:
            tkMessageBox.showerror('Solver Failure','Unable to find POMDP solutions.  Perhaps the solver location is improperly specified?')
#        self.queue.put({'command':'policy','window':self.entitywins[entity.name]})
        self.queue.put(None)

    def run(self,num=0):
        if not num:
            dialog = self.getHorizonDialog()
            counter = dialog.component('counter')
            if dialog.activate() == 'OK':
                num = int(counter.component('entryfield').component('entry').get())
            else:
                return
        self.realStep(iterations=num)
    
    def msgSend(self, sender, receiver, subject, msg, force, overhear,
                evaluateOnly=None):
        if evaluateOnly == 'subjective':
            # Hypothetical subjective
            target = lambda s=self,a=sender,r=receiver,j=subject,\
                     m=msg,f=force,o=overhear:s.query(a,r,j,m,f,o)
            self.background(target)
        elif evaluateOnly:
            # Hypothetical objective
            target = lambda s=self,a=sender,r=receiver,j=subject,\
                     m=msg,f=force,o=overhear:s.evaluateMsg(a,r,j,m,f,o)
            self.background(target)
        else:
            world = self.entities
            self.__msgSend(sender,receiver,subject,msg,force,overhear,world)
##            # Update audit trail
##            for entity in self.entities.members():
##                entity.extendHistory({'what':'message',
##                                      'who':getuser(),
##                                      'when':time.time()})
##            self.balloon.update()
            self.incUpdate()

    def query(self,sender,receiver,subject,msg,force,overhear):
        world = copy.deepcopy(self.entities[sender].entities)
        value = self.expectedValue(world[sender],world=world,background=0,
                                   display=0)
        self.__msgSend(sender,receiver,subject,msg,force,overhear,world,0,
                      hypothetical=1)
        delta = self.expectedValue(world[sender],world,
                                   '%s thinks the message will help:\n'\
                                   % (sender),value,0,display=0)
        msgTxt=[{'text':sender,'tag':'bolden'}]
        if float(delta) > 0.0:
            msgTxt.append({'text':' chooses to send\n\n'})
        else:
            msgTxt.append({'text':' chooses not to send\n\n'})
        self.aarWin.displayTaggedText(msgTxt)
        self.queue.put(None)
        
    def evaluateMsg(self,sender,receiver,subject,msg,force,overhear):
        world = copy.deepcopy(self.entities)
        value = -self.expectedValue(world[sender],world=world,background=0,
                                   display=0)
        self.__msgSend(sender,receiver,subject,msg,force,overhear,world,0)
        value += self.expectedValue(world[sender],world,
                                    'Sending the message will help:',value,0,
                                    display=0)
        if float(value) > 0.:
            content = 'Sending the message will help'
        else:
            content = 'Sending the message will not help'
        self.queue.put({'command':'AAR','message':['',content,'\n']})
        self.queue.put(None)
        
    def __msgSend(self, sender, receiver, subject, msg, force,
                 overhear,world,background=1,hypothetical=None):
        if isinstance(overhear,list):
            pass
        elif overhear == None or overhear == 'N' or overhear == '':
            overhear = []
        else:
            overhear = [overhear]
        if receiver == 'All':
            receiver = '*'
        elif isinstance(receiver,list):
            pass
        else:
            receiver = [receiver]
        if isinstance(msg,str):
            pmsg = Message(msg)
        else:
            pmsg = msg
        if force != 'none':
            pmsg.force(value=force)
        target = lambda s=self,w=world,m=pmsg,a=sender,r=receiver,\
                 o=overhear,j=subject,h=hypothetical:\
                 s.performMsg(world=w,msg=m,sender=a,receiver=r,
                              overhear=o,subject=j,hypothetical=h)
        if background:
            self.background(target)
        else:
            target()
        return

    def performMsg(self,world,msg,sender,receiver,overhear,subject,
                   background=1,hypothetical=None):
        explanation = world.performMsg(msg,sender,receiver,overhear,
                              explain=True)
        self.queue.put({'command':'AAR','message':explanation})
        if background:
            self.queue.put(None)

    def view(self):
        """Pops up the properties dialog"""
        if self.view == 'generic':
            agents = self.entities.keys()
            agents.sort()
            dialog = Pmw.Dialog(self.component('hull'),title='Scenario Properties',
                                defaultbutton='OK')
        else:
            dialog = Pmw.TextDialog(self.component('hull'),title='Scenario Properties')
            msg = 'Unable to view scenario properties at this time.'
            dialog.component('scrolledtext').settext(msg)
        dialog.activate()

    def export(self,filename=None,results=None):
        """Writes a Web page representation of the current scenario"""
        if not filename:
            ftypes = [('Web page', '.html'),
                      ('All files', '*')]
            filename = tkFileDialog.asksaveasfilename(filetypes=ftypes,
                                                      defaultextension='.html')
        if filename:
            # Clicked OK
            PsychShell.export(self,filename)

    def distill(self,filename=None,results=None):
        """Writes a lightweight representation of the current scenario"""
        if not filename:
            ftypes = [('XML file', '.xml')]
            filename = tkFileDialog.asksaveasfilename(filetypes=ftypes,
                                                      defaultextension='.xml')
        if filename:
            # Clicked OK
            self.background(lambda s=self,f=filename:
                            s._distill(filename=f),label='Distilling')

    def _distill(self,filename):
        PsychShell.distill(self,filename)
        self.queue.put(None)
            
    def createScenario(self,args=None):
        """Pops up a wizard dialog to instantiate scenario"""
        # This is the code using ScenarioWizard
        dialog = ScenarioWizard( self.component('hull'),
                                 title='Scenario Setup',
                                 society=self.classes,
                                 leavesOnly=False,
                                 balloon=self.balloon,
#                                 root=self.component('hull'),
                                 expert=True,
                                 finish=self.setupEntities,
                                 scenario=self.scenario,
                                 agentClass=self.agentClass,
                                 buttons=('Prev','Cancel','Next'),
                                 defaultbutton='Next',
                                 )
        dialog.activate()
        if dialog.scenario:
            if dialog.toImport:
                dialog.scenario.objectives = self.scenario.objectives[:]
            self.setupScenario(dialog.scenario)
        self.queue.put({'command': 'wizard','window': dialog})


    def saveBoth(self,event=None):
        if self.view == 'generic':
            self.saveSociety(self.societyFile)
        else:
            self.saveScenario(self.scenarioFile)
                
    def saveAs(self, filename=None):
        if self.view == 'generic':
            self.saveSociety()
        else:
            self.saveScenario()

    def saveScenario(self,filename=None):
        if not self.scenario:
            tkMessageBox.showerror('Save Scenario','No scenario present!')
            filename = None
        elif not filename:
            if isinstance(self.scenario,PWLSimulation):
                ftypes = [('Lightweight scenario file', '.xml')]
            else:
                ftypes = [('Scenario file', '.scn')]
            ext = ftypes[0][1]
            filename = tkFileDialog.asksaveasfilename(filetypes=ftypes,
                                                      defaultextension=ext)
        if filename:
            # Clicked OK
            name = os.path.split(filename)[1]
            name = os.path.splitext(name)[0]
#            self.component('hull').title('%s - %s - %s' % (self.titleLabel,name,self.view))
            self.background(lambda s=self,f=filename:
                            s._saveScenario(filename=f),label='Saving')

    def _saveScenario(self,filename):
        PsychShell.save(self,filename)
        self.queue.put(None)
        
    def saveSociety(self, filename=None):
        if not self.classes:
            tkMessageBox.showerror('Save Generic Society',
                                   'No generic society present!')
            return
        if not filename:
            ftypes = [('Generic society files', '.soc')]
            filename = tkFileDialog.asksaveasfilename(filetypes=ftypes,
                                                      defaultextension='.soc')
        if filename:
            name = os.path.split(filename)[1]
            name = os.path.splitext(name)[0]
##            self.component('hull').title('%s - %s - %s' % (self.titleLabel,name,self.view))
            self.background(lambda s=self,f=filename:
                            s._saveSociety(filename=f),label='Saving')

    def _saveSociety(self,filename):
        PsychShell.saveSociety(self,filename)
        self.queue.put(None)
        
    def load(self, event=None, filename=None,results=[]):
        """Loads a scenario in from a file"""
        if filename is None:
            ftypes = [('Generic society files', '.soc'),
                      ('Scenario files', '.scn'),
                      ('XML files', '.xml')]
            filename = tkFileDialog.askopenfilename(filetypes=ftypes,
                                                    defaultextension='.soc')

            if not filename: return
        self.close(load=True)
        society = (filename[-3:] == 'soc')
        try:
            warnings = PsychShell.load(self,filename)
        except IOError:
            tkMessageBox.showerror('Open','No such file or directory')
            return
        if society:
            if len(warnings) > 0:
                msg = 'The new society contained conflicting values for some '\
                      'model parameters.  The original values have been '\
                      'preserved for the following:\n\n'
                for warning in warnings:
                    msg += '\t%s\n' % (warning)
                tkMessageBox.showwarning('Import Conflict',msg)
            if self.view == 'generic':
                self.entities = self.classes
                self.initEntities()
        else:
            self.aarWin.clear()
            if self.supportgraph:
                self.supportgraph.loadHistory(self.entities)
            self.viewSelect('scenario',alreadyLoaded=True)

    def revert(self):
        """Reverts the current scenario back to the last saved version"""
        PsychShell.revert(self)
        if self.supportgraph:
            self.supportgraph.loadHistory(self.entities)
        self.incUpdate()
        
    def incUpdate(self,res=None, actType=None, actor=None):
        if self.psymwindow:
            if actType:
                if isinstance(actType,dict):
                    actList = [actType]
                else:
                    actList = actType
                for actType in actList:
                    if actType['object']:
                        obj = actType['object']
                        if not isinstance(obj,str):
                            obj = obj.name
                        self.psymwindow.redrawSupportLabel(actor.name, obj,
                                                           `actType`)
            else:
                self.psymwindow.redrawSupport()
        # Update agent windows
        for window in self.entitywins.values():
            window.update()
        if self.graph:
            self.graph.updateGraphWindow()
        if self.worldWin:
            self.worldWin.update()
        self.component('hull').update()

    def seedMessage(self,name,args):
        # Transform arguments into concrete message content
        if args.has_key('key'):
            msgList = [args]
        else:
            msgList = args['messages']
        for msg in msgList:
            msg['sender'] = name
            msg['receiver'] = msg['violator']
            msg['subject'] = msg['key']['entity']
            msg['type'] = msg['key']['feature']
            # Find new value for this feature
            belief = self.entities[msg['receiver']].getBelief(msg['subject'],
                                                              msg['type']) 
            value = float(belief)
            if value < msg['min']:
                # Need to send a higher number.  How much higher?
                if msg['min'] < 0.9:
                    msg['value'] = msg['min']+0.1
                else:
                    msg['value'] = msg['min']+0.01
            elif value > msg['max']:
                # Need to send a lower number.  How much lower?
                if msg['max'] > -0.9:
                    msg['value'] = msg['max']-0.1
                else:
                    msg['value'] = msg['max']-0.01
            else:
                # Could happen if using out-of-date suggestions
                msg['value'] = value
                print '%s already has satisfactory belief about %s: %5.3f' % \
                      (msg['receiver'],msg['key'],value)
        if args.has_key('key'):
            # Configure message pane to display message
            self.showWindow(name)
            window = self.entitywins[name]
            window.win.show_window()
            window.win.select_window()
            notebook = window.component('notebook')
            notebook.selectpage('Messages')
            window.component('Messages').seedMessage(msgList[0])
        else:
            # Launch campaign analysis
            dialog = AnalysisWizard(self.entities,name,[args['violator']],
                                    msgList,self.component('hull'))
            dialog.run()

    def translateReward(self, rew,name):
        entity = self.entities[name]
        content = ''
        good = []
        bad = []
        goals = entity.getGoalVector()['state'].expectation()
        for key,value in rew.items():
            if value > 0.:
                good.append(key)
            elif value < 0.:
                bad.append(key)
        for key in good:
            if goals[key] > 0.:
                verb = 'maximize'
            else:
                verb = 'minimize'
            content += '\t%s %s\n' % (verb,key)
        if len(good) == 0:
            content += '\tnothing\n'
        if len(bad) > 0:
            content += 'but the goal(s) to\n'
            for key in bad:
                if goals[key] > 0.:
                    verb = 'maximize'
                else:
                    verb = 'minimize'
                content += '\t%s %s\n' % (verb,key)
            content += 'may suffer \n'
        return content

    def mainloop(self,root):
        self.splash()
        self.done = False
        self.poll(root)
        while not self.done:
            try:
                root.update()
                root.mainloop()
            except Exception,value:
                import traceback
                msg = traceback.format_exception(value.__class__,value,None)
                if msg[-1] != 'Exception: normal exit\n':
                    traceback.print_exc()

    def poll(self,root):
        try:
            result = self.queue.get_nowait()
        except Empty:
            result = True
        if isinstance(result,dict):
            self.handleCommand(result)
        elif result is None:
            self.finishBackground()
        elif result == 'quit':
            self.done = True
            PsychShell.stop(self)
##            if self.__class__ is GuiShell:
##                # Awkward
##                raise Exception,'normal exit'
##            else:
            root.destroy()
        if not self.done:
            self.component('hull').after(100,lambda s=self,r=root: s.poll(r))
        
    def handleCommand(self,args):
        if args['command'] == 'error':
            tkMessageBox.showerror(args['title'],args['message'])
        elif args['command'] == 'info':
            tkMessageBox.showinfo(args['title'],args['message'])
        elif args['command'] == 'setState':
            args['widget'].setState(args['state'])
        elif args['command'] == 'pop':
            args['widget'].pop()
        elif args['command'] == 'updateGoals':
            if args.has_key('weights'):
                vector = args['weights']
                for goal in args['agent'].getGoals():
                    key = goal.toKey()
                    args['agent'].setGoalWeight(goal,abs(vector[key]),False)
                args['agent'].normalizeGoals()
            args['widget'].recreate_goals()
        elif args['command'] == 'updateNetwork':
            self.psymwindow.redrawSupport()
        elif args['command'] == 'updateTime':
            self.drawTime()
        elif args['command'] == 'worlds':
            self.worldWin.component('World').draw()
        elif args['command'] == 'AAR':
            if args['message'].__class__.__name__ != 'list':
                self.aarWin.displayAAR(args['message'])
            else:
                print 'non-doc explanation'
        elif args['command'] == 'policy':
            args['window'].component('Policy').displayPolicy()
            args['window'].component('Policy').xview('moveto',1.0)
        elif args['command'] == 'destroy':
            args['window'].destroy()
        elif args['command'] == 'wizard':
            args['window'].destroy()
        else:
            raise NotImplementedError,'Unable to handle queue commands of type %s' % (args['command'])
        
    def stop(self,event=None):
        result = tkMessageBox.askyesno('Quit?',
                                       'Are you sure you want to exit?')
        if result:
            self.queue.put('quit')
