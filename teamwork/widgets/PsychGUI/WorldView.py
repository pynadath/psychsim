import copy
from Tkinter import *
import tkFileDialog
import tkMessageBox
import Pmw
from TurnDialog import TurnEditor
from teamwork.widgets.MultiWin import InnerWindow
from teamwork.multiagent.Simulation import MultiagentSimulation
from teamwork.multiagent.GenericSociety import GenericSociety
from teamwork.math.Keys import Key,StateKey

class WorldFrame(Pmw.ScrolledFrame):
    def __init__(self,frame,**kw):
        optiondefs = (
            ('entities', {}, None),
            ('generator',None,None),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.ScrolledFrame.__init__(self,frame)
        b = self.createcomponent('generate',(),None,Button,
                                 (self.interior(),),
                                 text='Generate Worlds',
                                 command=self.generate)
        b.grid(row=0,column=0,padx=20,pady=20)
        b = self.createcomponent('pomdp',(),None,Button,
                                 (self.interior(),),
                                 text='Generate POMDP',
                                 command=self.promptPOMDP)
        b.grid(row=1,column=0,padx=20,pady=20)
        self.interior().configure(padx=10)
        self.interior().grid_columnconfigure(0,weight=1)
        self.initialiseoptions(WorldFrame)

    def generate(self):
        if self['generator']:
            self.component('generate').configure(state='disabled')
            self['generator']()

    def pomdp(self,button):
        """ Generate a file in the Cassandra POMDP-solver's format
        """
        self.component('dialog').deactivate()
        if button == 'OK':
            # Start a file
            filename = tkFileDialog.asksaveasfilename(filetypes=[('All files','*')],
                                                      defaultextension='.pomdp')
            if filename:
                # Generate possible worlds for selected agent's POMDP
                name = self.component('dialog').getcurselection()[0]
                agent = self['entities'][name]
                f = open(filename,'w')
                agent.getPOMDP(f)
                f.close()

    def promptPOMDP(self):
        """Get info needed to generate POMDP format
        """
        names = map(lambda a: a.name,self['entities'].activeMembers())
        names.sort()
        try:
            dialog = self.component('dialog')
        except KeyError:
            dialog = self.createcomponent('dialog',(),None,
                                          Pmw.SelectionDialog,
                                          (self.interior(),),
                                          scrolledlist_items=names,
                                          defaultbutton='OK',
                                          buttons=('OK','Cancel'),
                                          scrolledlist_labelpos='n',
                                          listbox_selectmode='single',
                                          label_text='Which agent should I generate the POMDP for?',
                                          command=self.pomdp)
        dialog.component('scrolledlist').setvalue(names[0])
        dialog.activate()

    def draw(self):
        frame = Pmw.Group(self.interior(),tag_text='Worlds')
        frame.interior().grid_columnconfigure(1,weight=1)
        keys = self['entities'].worlds.keys()
        keys.sort()
        for row in range(len(keys)):
            world = self['entities'].worlds[keys[row]]
            text = '%d' % (keys[row]['world'])
            Label(frame.interior(),text=text,bd=2,relief='raised',justify='right',
                  padx=5,pady=5).grid(row=row+1,column=0,sticky='ew')
            text = ','.join(map(lambda k: '%s=%4.2f' % (k,world[k]),
                                filter(lambda k:isinstance(k,StateKey),
                                       world.keys())))
            Label(frame.interior(),text=text,bd=2,relief='sunken',justify='left',
                  padx=5,pady=5).grid(row=row+1,column=1,sticky='ew')
        frame.grid(row=2,column=0,sticky='nwes',pady=20)
        # Compute transition matrix
        matrix = self['entities'].getDynamicsMatrix()
        frame = Pmw.Group(self.interior(),tag_text='Transition')
        widget = self.createcomponent('selectT',(),None,Pmw.OptionMenu,
                                      (frame.interior(),),command=self.selectT,
                                      items=matrix.keys())
        widget.grid(row=0,column=0,columnspan=len(keys)+1,padx=10,pady=10)
        # Print table headings
        Label(frame.interior(),text='start',bd=2,relief='raised',
                  padx=5,pady=5).grid(row=1,column=0)
        for col in range(len(keys)):
            text = '%d' % (keys[col]['world'])
            Label(frame.interior(),text=text,bd=2,
                  relief='raised').grid(row=1,column=col+1,sticky='ewns')
            frame.interior().grid_columnconfigure(col+1,weight=1)
        for row in range(len(keys)):
            # Print row for each possible start state
            text = '%d' % (keys[row]['world'])
            Label(frame.interior(),text=text,bd=2,
                  relief='raised').grid(row=row+2,column=0,sticky='ewns')
            for col in range(len(keys)):
                self.createcomponent('T%d,%d' % (row,col),(),None,Label,
                                     (frame.interior(),),bd=2,font=('Courier',14),
                                     relief='sunken').grid(row=row+2,column=col+1,
                                                           sticky='ewns')
        widget.invoke()
        frame.grid(row=3,column=0,sticky='nwes',pady=20)
        # Compute reward vector
        frame = Pmw.Group(self.interior(),tag_text='Reward')
        reward = self['entities'].jointReward()
        # Print table headings
        Label(frame.interior(),text='action',bd=2,relief='raised',
                  padx=5,pady=5).grid(row=0,column=0,sticky='ewns')
        for col in range(len(keys)):
            text = '%d' % (keys[col]['world'])
            Label(frame.interior(),text=text,bd=2,
                  relief='raised').grid(row=0,column=col+1,sticky='ewns')
            frame.interior().grid_columnconfigure(col+1,weight=1)
        row = 1
        for action,vector in reward.items():
            # Print row for each possible action
            Label(frame.interior(),text=action,bd=2,
                  relief='raised').grid(row=row,column=0,sticky='ewns')
            for col in range(len(keys)):
                Label(frame.interior(),bd=2,text='%5.2f' % (vector[keys[col]]),
                      font=('Courier',14),justify='right',
                      relief='sunken').grid(row=row,column=col+1,sticky='ewns')
            row += 1
        frame.grid(row=4,column=0,sticky='nwes',pady=20)
        # Compute observation matrices
        frame = self.createcomponent('O',(),None,Pmw.Group,(self.interior(),),
                                     tag_text='Observations')
        observers = filter(lambda e: len(e.omega)>2,self['entities'].members())
        for entity in observers:
            for action in self['entities'].generateActions():
                entity.getObservationMatrix(action,self['entities'].worlds)
        width = max(map(lambda e: len(e.omega),observers))
        widget = self.createcomponent('selectObserver',(),None,Pmw.OptionMenu,
                                      (frame.interior(),),
                                      command=self.selectObserver,
                                      items=map(lambda e: e.name,observers))
        widget.grid(row=0,column=0,columnspan=width+1,padx=10,pady=10,sticky='ew')
        widget.invoke()
        widget = self.createcomponent('selectO',(),None,Pmw.OptionMenu,
                                      (frame.interior(),),command=self.selectO,
                                      items=matrix.keys())
        widget.grid(row=1,column=0,columnspan=width+1,padx=10,pady=10,sticky='ew')
        # Print table headings
        Label(frame.interior(),text='state',bd=2,relief='raised',
                  padx=5,pady=5).grid(row=2,column=0,sticky='ewns')
        # Draw rows for each possible world
        row = 3
        for key in keys:
            Label(frame.interior(),text=key['world'],bd=2,
                  relief='raised').grid(row=row,column=0,sticky='ewns')
            row += 1
        widget.invoke()
        frame.grid(row=5,column=0,sticky='nwes',pady=20)
        # Initialize null policy
        self['entities'].nullPolicy()
        for entity in self['entities'].members():
            try:
                widget = entity.attributes['window'].component('Policy')
            except KeyError:
                widget = None
            if widget: widget.displayPolicy()
        self.component('generate').configure(state='normal')

    def selectT(self,action):
        matrix = self['entities'].transition[action]
        keys = self['entities'].worlds.keys()
        keys.sort()
        for row in range(len(keys)):
            for col in range(len(keys)):
                widget = self.component('T%d,%d' % (row,col))
                text = '%4.2f' % (matrix[keys[row]][keys[col]])
                widget.configure(text=text)

    def selectObserver(self,agent):
        """
        Draw headings for possible observation symbol of the selected agent
        """
        Omega = self['entities'][agent].getOmega()
        for col in range(len(Omega)):
            Label(self.component('O').interior(),text=Omega[col]['type'],bd=2,
                  relief='raised',padx=5,pady=5).grid(row=2,column=col+1,
                                                      sticky='ewns')
        self.updateO(agent=agent)

    def selectO(self,action):
        self.updateO(action=action)

    def updateO(self,agent=None,action=None):
        """Draws observation function based on current selection of agent/action
        """
        if agent is None:
            agent = self.component('selectObserver').getvalue()
        if action is None:
            try:
                action = self.component('selectO').getvalue()
            except KeyError:
                # Too early to draw O
                return
        matrix = self['entities'][agent].getObservationMatrix(action)
        Omega = self['entities'][agent].getOmega()
        keys = self['entities'].worlds.keys()
        keys.sort()
        row = 3
        for key in keys:
            for col in range(len(Omega)):
                text = '%4.2f' % (matrix[Omega[col]][key])
                Label(self.component('O').interior(),text=text,bd=2,
                      relief='sunken',font=('Courier',14),
                      justify='right').grid(row=row,column=col+1,sticky='ewns')
            row += 1
            
    def clear(self):
        pass
    
class ProgressFrame(Pmw.ScrolledFrame):
    columns = ['Agent','States','Actions','Goals']

    def __init__(self,frame,**kw):
        optiondefs = (
            ('entities', {}, self.update),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.ScrolledFrame.__init__(self,frame)
        for col in range(len(self.columns)):
            self.interior().grid_columnconfigure(col,weight=1)
            name = self.columns[col]
            widget = Label(self.interior(),text=name,anchor='nw',
                           relief='raised')
            widget.grid(row=0,column=col,sticky='ew')
        self.initialiseoptions(ProgressFrame)

    def update(self):
        if self['entities']:
            entities = self['entities'].members()
            for row in range(len(entities)):
                agent = entities[row]
                for col in range(len(self.columns)):
                    if self.columns[col] == 'Agent':
                        name = agent.name
                    elif self.columns[col] == 'States':
                        name = len(agent.getStateFeatures())
                    elif self.columns[col] == 'Actions':
                        name = len(agent.actions.getOptions())
                    elif self.columns[col] == 'Goals':
                        name = len(agent.getGoals())
                    widget = Label(self.interior(),text=name,
                                   relief='sunken')
                    if isinstance(name,int):
                        widget.configure(anchor='e')
                    else:
                        widget.configure(anchor='w')
                    widget.grid(row=row+1,column=col,sticky='ew')
        
    def clear(self):
        pass

class DynamicsFrame(Pmw.ScrolledFrame):
    def __init__(self,frame,**kw):
        optiondefs = (
            ('entities', {}, self.update),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.ScrolledFrame.__init__(self,frame)
        self.initialiseoptions(DynamicsFrame)

    def update(self):
        if self['entities']:
            actions = {}
            for agent in self['entities'].members():
                for option in agent.actions.getOptions():
                    for action in option:
                        actions[action['type']] = True
            actions = actions.keys()
            actions.sort()
            widget = Label(self.interior(),text='State',anchor='nw',
                           relief='raised')
            widget.grid(row=0,column=0,sticky='ewns')
            for col in range(len(actions)):
                self.interior().grid_columnconfigure(col+1,weight=1)
                name = actions[col]
                widget = Label(self.interior(),text=name,anchor='nw',
                               relief='raised',width=12,wraplength=96)
                widget.grid(row=0,column=col+1,sticky='ewns')
            row = 1
            for agent in self['entities'].members():
                keyList = agent.state.domainKeys().keys()
                keyList.sort()
                for key in keyList:
                    widget = Label(self.interior(),text=str(key),
                                   relief='sunken',anchor='nw')
                    widget.grid(row=row,column=0,sticky='ewns')
                    for col in range(len(actions)):
                        try:
                            dynamics = agent.dynamics[key['feature']][actions[col]]
                            widget = Label(self.interior(),relief='sunken',
                                           bg='#22dd22')
                        except KeyError:
                            # Unfinished button for editing missing dynamics
                            cmd = lambda s=self,k=key,a=actions[col]:\
                                s.popupDynamics(k,a)
                            widget = Button(self.interior(),relief='sunken',
                                            command=cmd)

    def popupDynamics(self,key,action):
        tkMessageBox.showerror('Not quite ready','I am currently unable to pop up the dialog for editing the effect of %s on %s.' % (action,key))

    def clear(self):
        pass
    
class TurnFrame(Pmw.ScrolledFrame):
    def __init__(self,frame,**kw):
        optiondefs = (
            ('entities', {}, self.update),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.ScrolledFrame.__init__(self,frame)
        widget = self.createcomponent('editor',(),None,TurnEditor,
                                      (self.interior(),),
                                      editable=True,command=self.changeOrder)
        widget.pack(side='top',expand='yes',fill='both')
        self.initialiseoptions(TurnFrame)

    def update(self):
        if isinstance(self['entities'],MultiagentSimulation):
            order = self['entities'].getSequence()
        elif isinstance(self['entities'],GenericSociety):
            order = copy.deepcopy(self['entities']._keys)
        else:
            order = self['entities'].keys()
        self.component('editor').configure(order=order,
                                           elements=self['entities'].keys(),
                                           editable=True)

    def clear(self):
        self.configure(entities={})
        
    def changeOrder(self,order):
        if isinstance(self['entities'],MultiagentSimulation):
            self['entities'].applyOrder(order[:])
        else:
            self['entities']._keys = order[:]
        
class WorldViewer(InnerWindow):
    panes = {
        'Turn': TurnFrame,
        'World': WorldFrame,
        'Progress': ProgressFrame,
        'Dynamics': DynamicsFrame,
        }

    def __init__(self,frame,**kw):
        optiondefs = (
            ('entities', {}, self.update),
            )
        self.defineoptions(kw,optiondefs)
        InnerWindow.__init__(self,frame)
        book = self.createcomponent('book',(),None,Pmw.NoteBook,
                                    (self.component('frame'),),
                                    hull_width=600,hull_height=400)
        for pane,widgetClass in self.panes.items():
            page = book.add(pane)
            widget = self.createcomponent(pane,(),'pane',widgetClass,(page,),
                                          horizflex='expand',vertflex='expand',
                                          entities=self['entities'])
            widget.pack(side='top',fill='both',expand='yes')
        book.pack(fill='both',expand='yes')
        self.initialiseoptions(WorldViewer)

    def update(self):
        for pane in self.components():
            if self.componentgroup(pane) == 'pane':
                self.component(pane)['entities'] = self['entities']

    def clear(self):
        for pane in self.components():
            if self.componentgroup(pane) == 'pane':
                self.component(pane).clear()
