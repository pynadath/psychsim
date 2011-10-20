from Tkinter import PhotoImage,Frame,Label,Button
import Pmw
from tkFileDialog import askopenfilename
from teamwork.widgets.images import getImageDirectory,getImage
from teamwork.agent.lightweight import PWLAgent

class PropertyFrame(Pmw.ScrolledFrame):
    """Frame for managing general properties of an entity (e.g., image, 
    description, horizon, belief depth
    """
    
    def __init__(self,parent,entity,**kw):
        optiondefs = (
            ('balloon',None,Pmw.INITOPT),
            ('generic',False,Pmw.INITOPT),
            ('expert', False,None),
            ('step',lambda : None,None),
            ('policy',lambda entity: None,None),
            ('society',{},None),
            ('valueCmd', None,None),
            ('options',None,None),
            )
        self.entity = entity
        self.defineoptions(kw, optiondefs)
        Pmw.ScrolledFrame.__init__(self,parent)
        self.interior().grid_columnconfigure(1,weight=1)
        # Entity image
        try:
            image = PhotoImage(file=self.entity.attributes['imageName'])
        except KeyError:
            image = PhotoImage(file=getImage('nobody.gif'))
        self.entity.attributes['image'] = image
        widget = self.createcomponent('image',(),None,Button,(self.interior(),),
                                      command=self.selectImage,
                                      image=self.entity.attributes['image'],
                                      width=100,height=100)
        widget.grid(row=0,column=0,sticky='nw')
#         # Draw description entry
#         widget = self.createcomponent('description',(),None,Pmw.ScrolledText,
#                                       (self.interior(),),
#                                       hscrollmode='none',
#                                       text_width=40,text_height=10,
#                                       text_wrap='word')
#         try:
#             widget.settext(text=self.entity.description)
#         except AttributeError:
#             widget.settext(text=self.entity.name)
#         widget.component('text').focus_set()
#         widget.grid(row=0,column=1,sticky='ewns',padx=10,pady=10)
        # Button area
        frame = Frame(self.interior())
        row = 0
        if self['generic']:
            if not self.entity.parent:
                widget = Label(frame,text='Horizon:',justify='left')
                widget.grid(row=row,column=0,sticky='w')
                self.createcomponent('Horizon',(),None,Pmw.Counter,(frame,),
                                     entryfield_modifiedcommand=self.getHorizon,
                                     entryfield_value=self.entity.horizon,
                                     entryfield_validate={'validator':'integer',
                                                          'min':1},
                                     ).grid(row=0,column=1,sticky='w')
                row += 1
                if self['balloon']:
                    self['balloon'].bind(widget,'The number of rounds into the future this agent considers when choosing an action.')
                    self['balloon'].bind(self.component('Horizon'),'The number of rounds into the future this agent considers when choosing an action.')
        if not self['generic'] and len(self.entity.actions.getOptions()) > 0:
            # Button box for controlling this agent
            widget = self.createcomponent('%s Run Box' % (self.entity.ancestry()),
                                          (), None,Pmw.ButtonBox,(frame,),
                                          orient='vertical')
            if not self.entity.parent:
                # Can't run a real step for a subjective agent
                widget.add('real',text='Real Step',command=self.stepEntity)
            widget.add('hypo',text='Hypothetical Step',command=self.applyPolicy)
            if len(self.entity.getGoals()) > 0 and self['valueCmd']:
                # Add an expected value button
                widget.add('value',text='Expected Value',
                           command = lambda s=self,e=self.entity:s.value(e))
            widget.grid(row=row,column=1)
            row += 1
        # Control for depth of beliefs
        widget = Label(frame,text='Belief Depth:',justify='left')
        widget.grid(row=row,column=0,sticky='w')
        if self['generic']:
            default = self.entity.depth
        elif isinstance(self.entity,PWLAgent):
            default = 1
        else:
            default = self.entity.beliefHeight()
        self.createcomponent('Depth',(),None,Pmw.Counter,(frame,),
                             entryfield_modifiedcommand=self.getDepth,
                             entryfield_value=default,
                             entryfield_validate={'validator':'integer','min':0},
                             ).grid(row=row,column=1,sticky='w')
        row += 1
        if self['balloon']:
            self['balloon'].bind(widget,'The number of levels of recursive beliefs that this agent will maintain of others.')
            self['balloon'].bind(self.component('Depth'),'The number of levels of recursive beliefs that this agent maintains of others.')
        if self['generic']:
            widget = Button(frame,text='Propagate belief depth',
                            command=self.propagateDepth)
            widget.grid(row=row,column=0,columnspan=2)
            row += 1
            if self['balloon']:
                self['balloon'].bind(widget,'Set the belief depth of all of my subclasses to my value.')
        else:
            self.component('Depth_entry').configure(state='disabled')
            self.component('Depth')._upArrowBtn.unbind('<1>')
            self.component('Depth')._downArrowBtn.unbind('<1>')
        Label(frame,text='Goal Type:').grid(row=row,column=0,sticky='w')
        if isinstance(self.entity,PWLAgent):
            values = ['cumulative']
            initial = 'cumulative'
        else:
            values = self.entity.valueTypes[:]
            initial = self.entity.valueType
        widget = self.createcomponent('goalType',(),None,Pmw.OptionMenu,
                                      (frame,),
                                      items=values,
                                      initialitem=initial)
        if not isinstance(self.entity,PWLAgent):
            widget.configure(command=self.toggleGoals)
        widget.grid(row=row,column=1,sticky='w')
        row += 1
        frame.grid(row=0,column=1,sticky='ewns')
        self.initialiseoptions()

    def selectImage(self):
        """Pops up a dialog to allow user to select image for an entity"""
        filename = askopenfilename(parent=self._hull,
                                   initialdir = getImageDirectory())
        if filename:
            image = PhotoImage(file=filename)
            if image:
                widget = self.component('image')
                widget.configure(image=image)
                self.entity.attributes['image'] = image
                self.entity.attributes['imageName'] = filename
        
    def getHorizon(self):
        widget = self.component('Horizon')
        horizon = int(widget.get())
        self.entity.horizon = horizon

    def getDepth(self):
        widget = self.component('Depth')
        depth = int(widget.get())
        self.entity.depth = depth

    def stepEntity(self):
        self['step']()

    def applyPolicy(self):
        self['policy'](self.entity)

    def propagateDepth(self):
        depth = int(self.component('Depth').get())
        for name in self['society'].descendents(self.entity.name):
            if name != self.entity.name:
                entity = self['society'][name]
                entity.depth = depth
                try:
                    win = entity.attributes['window']
                except KeyError:
                    # Agent not mapped
                    continue
                win.component('General').component('Depth').setvalue(str(depth))
    
    def toggleGoals(self,value):
        self.entity.valueType = value

