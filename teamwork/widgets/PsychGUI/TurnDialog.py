import threading
from Tkinter import *
import Pmw
from teamwork.widgets.images import getImage

class TurnDialog(Pmw.Dialog):
    """A dialog for editing the ordering of a sequence"""
    def __init__(self,parent,**kw):
        optiondefs = (
            ('serial',False,Pmw.INITOPT),
            )
        self.defineoptions(kw, optiondefs)
        Pmw.Dialog.__init__(self,parent)
        if self['serial']:
            self.createcomponent('editor',(),None,OldTurnEditor,(self.interior(),),
                                 vertflex='expand',horizflex='expand')
        else:
            self.createcomponent('editor',(),None,TurnEditor,(self.interior(),),
                                 vertflex='expand',horizflex='expand')
        self.component('editor').pack(side='top',fill='both',expand='yes')
        self.initialiseoptions()

class TurnEditor(Pmw.ScrolledFrame):
    def __init__(self,parent,**kw):
        self.lock = threading.Lock()
        optiondefs = (
            ('order',[],self.setOrder),
            ('elements',[],self.setOrder),
            ('editable',True,self.setOrder),
            ('command',None,None),
            )
        self.defineoptions(kw, optiondefs)
        self.variables = {}
        Pmw.ScrolledFrame.__init__(self,parent)
        self.interior().grid_columnconfigure(1,weight=1)
        self.createcomponent('serial',(),None,Pmw.OptionMenu,(self.interior(),),
                             items=('serial','parallel','mixed'),
                             command=self.serialize).grid(row=0,column=0,
                                                          sticky='w')
        Button(self.interior(),text='Preview',command=self.setOrder,
               justify='center').grid(row=0,column=1,sticky='w')

    def setOrder(self):
        """Redraws the control elements based on the new order"""
        for name in self.components():
            if self.componentgroup(name) == 'active':
                if not name[:-7] in self['elements']:
                    self.destroycomponent(name)
            elif self.componentgroup(name) == 'scale':
                if not name[:-6] in self['elements']:
                    self.destroycomponent(name)
        if self['order']:
            if isinstance(self['order'][0],str):
                # Sequential order
                self.component('serial').setvalue('serial')
            elif len(self['order']) == 1:
                # Parallel order
                self.component('serial').setvalue('parallel')
    ##        elif max(map(len,self['order'])) == 1:
    ##            # Sequential order
    ##            self.component('serial').setvalue('serial')
            else:
                # Mixed
                self.component('serial').setvalue('mixed')
        inactive = self['elements'][:]
        # Check whether any previously relevant agents are now gone
        leftover = {}
        leftover.update(self.variables)
        # Draw new control elements
        row = 2
        for pos in range(len(self['order'])):
            names = self['order'][pos]
            if isinstance(names,str):
                # Pretend we're being parallel, even if we're not
                names = [names]
            for name in names:
                self.drawControl(name,row,pos,True)
                row += 1
                inactive.remove(name)
                if leftover.has_key(name):
                    del leftover[name]
        # Draw the unselected checkbuttons
        for name in inactive:
            self.drawControl(name,row,len(self['order']),False)
            row += 1
            if leftover.has_key(name):
                del leftover[name]
        # Delete unused checkbutton variables
        for name in leftover.keys():
            del self.variables[name]

    def drawControl(self,name,row,pos,active):
        """Draws the control for an individual agent's position in order
        @param name: the name of the agent
        @type name: str
        @param row: the position of the agent's widget
        @type row: int
        @param pos: the turn of the agent in the execution order
        @type pos: int
        @param active: if C{True}, the agent gets a turn
        @type active: bool
        """
        try:
            widget = self.component('%s-active' % (name))
        except KeyError:
            self.variables[name] = StringVar()
            widget = self.createcomponent('%s-active' % (name),(),'active',
                                          Checkbutton,(self.interior(),),
                                          text=name,variable=self.variables[name],
                                          command=lambda n=name,s=self:s.toggle(n))
        widget.grid(row=row,column=0,sticky='w')
        # Update checkbuttons indicating active/inactive
        if self.lock.acquire(0):
            if active:
                widget.select()
            else:
                widget.deselect()
            self.lock.release()
        # Create scale widget
        try:
            widget = self.component('%s-scale' % (name))
        except KeyError:
            widget = self.createcomponent('%s-scale' % (name),(),'scale',
                                          Scale,(self.interior(),),
                                          command=lambda v,n=name,s=self:
                                              s.update(n,v),
                                          orient='horizontal',from_=1,
                                          to=len(self['elements']))
        # Update scale's setting
        if self.lock.acquire(0):
            widget.set(pos+1)
            self.lock.release()
        widget.grid(row=row,column=1,sticky='ew')

    def update(self,name,new):
        """Slider callback
        """
        if self.lock.acquire(0):
            new = int(new)
            serial = self.component('serial').getvalue()
            active = int(self.variables[name].get())
            if serial == 'serial':
                if active and new > len(self['order']):
                    # Simply add to end of order
                    self['order'].append(name)
                    if len(self['order']) != new:
                        # It's a few steps beyond the end
                        self.component('%s-scale' % (name)).set(len(self['order']))
                elif active and self['order'][new-1] != name:
                    # Move guy out of new spot
                    old = self['order'].index(name)+1
                    other = self['order'][new-1]
                    self['order'][old-1] = other
                    self['order'][new-1] = name
                    self.component('%s-scale' % (other)).set(old)
            elif serial == 'mixed':
                for names in self['order']:
                    try:
                        names.remove(name)
                        break
                    except ValueError:
                        pass
                if int(self.variables[name].get()):
                    # Add name in new list
                    self['order'][new-1].append(name)
            if self['command']:
                self['command'](self['order'])
            self.lock.release()

    def toggle(self,name):
        """Activation checkbutton callback
        """
        widget = self.component('%s-scale' % (name))
        position = int(widget.get())
        serial = self.component('serial').getvalue()
        active = int(self.variables[name].get())
        if active:
            # Activated previously inactive agent
            widget.configure(state='normal')
            self.update(name,position)
        elif serial == 'serial':
            # Remove agent from sequence
            widget.set(len(self['order']))
            assert self['order'][position-1] == name,'%s not in position %d within %s' % \
            (name,position,str(self['order']))
            del self['order'][position-1]
            for index in range(position-1,len(self['order'])):
                self.component('%s-scale' % (self['order'][index])).set(index+1)
            widget.configure(state='disabled')
        else:
            # Remove agent from parallel grouping
            self['order'][position-1].remove(name)
        if self['command']:
            self['command'](self['order'])

    def serialize(self,serial):
        if serial == 'serial':
            if isinstance(self['order'][0],list):
                # Going from parallel to serial (order is lists of strings)
                for index in range(len(self['order'])):
                    names = self['order'][0]
                    del self['order'][0]
                    for name in names:
                        if int(self.variables[name].get()):
                            self['order'].append(name)
                self.setOrder()
        elif serial == 'parallel':
            if isinstance(self['order'][0],str):
                self['order'][0] = self['order'][:]
            else:
                self['order'][0] += sum(self['order'][1:],[])
            del self['order'][1:]
            self.setOrder()
        else:
            if isinstance(self['order'],str):
                # Going from serial to parallel (order is list of lists of strings)
                for index in range(len(self['order'])):
                    self['order'][index] = [self['order'][index]]
        if self['command']:
            self['command'](self['order'])

class OldTurnEditor(Pmw.ScrolledFrame):
    def __init__(self,parent,**kw):
        optiondefs = (
            ('order',[],self.setOrder),
            ('elements',[],self.setElements),
            ('editable',True,self.setEditable),
            )
        self.defineoptions(kw, optiondefs)
        Pmw.ScrolledFrame.__init__(self,parent)
        self.up = PhotoImage(file=getImage('up.gif'))
        self.down = PhotoImage(file=getImage('down.gif'))
        self.createcomponent('active',(),None,Pmw.Group,(self.interior(),),
                             tag_text='Active')
        self.component('active').interior().grid_columnconfigure(1,weight=1)
        self.createcomponent('inactive',(),None,Pmw.Group,(self.interior(),),
                             tag_text='Inactive').pack(side='top',fill='both',
                                                       expand='yes')
        self.component('inactive').interior().grid_columnconfigure(1,weight=1)
        self.initialiseoptions()

    def setOrder(self):
        """Redraws the control elements based on the new order"""
        # Remove any existing control elements
        for name in self.components():
            if self.componentgroup(name) == 'active':
                self.destroycomponent(name)
        frame = self.component('active')
        # Draw new control elements
        for index in range(len(self['order'])):
            self.drawControl(index,self['order'][index],True)
        if len(self['order']) > 0:
            frame.pack(side='top',fill='both',expand='yes',
                       before=self.component('inactive'))

    def setElements(self):
        """Redraws the control elements for the inactive elements"""
        # Remove any existing control elements
        for name in self.components():
            if self.componentgroup(name) == 'inactive':
                self.destroycomponent(name)
        index = len(self['order'])
        for element in self['elements']:
            if not element in self['order']:
                self.drawControl(index,element,False)
                index += 1

    def drawControl(self,index,label,active):
        """Draws a new text box with up/down arrows
        @param index: the row in which to create this widget
        @type index: int
        @param label: the text label for this element
        @type label: str
        @param active: C{True} iff this element is currently active
        @type active: bool
        """
        if active:
            group = 'active'
            offset = 0
        else:
            group = 'inactive'
            offset = len(self['order'])
        w = self.createcomponent('up%d' % (index),(),group,Button,
                                 (self.component(group).interior(),),
                                 image=self.up,
                                 command=lambda i=index:\
                                 self.moveUp(i),
                                 )
        if index == 0 and active:
            w.configure(state='disabled')
        w.grid(row=index-offset,column=0)
        w = self.createcomponent('name%d' % (index),(),group,Label,
                                 (self.component(group).interior(),),
                                 text=label,bd=1,relief='raised',
                                 )
        w.grid(row=index-offset,column=1,sticky='ewns')
        w = self.createcomponent('down%d' % (index),(),group,Button,
                                 (self.component(group).interior(),),
                                 image=self.down,
                                 command=lambda i=index:\
                                 self.moveDown(i),
                                 )
        if index == len(self['elements']) - 1 and not active:
            w.configure(state='disabled')
        w.grid(row=index-offset,column=2)
        
    def setEditable(self):
        """En/disables the order modification buttons, as appropriate"""
        if self['editable']:
            state = 'normal'
        else:
            state = 'disabled'
        for index in range(len(self['order'])):
            if index > 0:
                w = self.component('up%d' % (index))
                w.configure(state=state)
            if index < len(self['elements'])-1:
                w = self.component('down%d' % (index))
                w.configure(state=state)

    def moveUp(self,index):
        """Moves the identified element up in the order"""
        if index < len(self['order']):
            old = self['order'][index-1]
            new = self['order'][index]
            self.component('name%d' % (index)).configure(text=old)
            self.component('name%d' % (index-1)).configure(text=new)
            self['order'][index] = old
            self['order'][index-1] = new
        elif index > len(self['order']):
            old = self.component('name%d' % (index-1)).cget('text')
            new = self.component('name%d' % (index)).cget('text')
            self.component('name%d' % (index)).configure(text=old)
            self.component('name%d' % (index-1)).configure(text=new)
        else:
            # Newly active
            name = self.component('name%d' % (index)).cget('text')
            self['order'].append(name)
            self.setElements()
            self.drawControl(index,name,True)

    def moveDown(self,index):
        """Moves the identified element down in the order"""
        if index < len(self['order']) - 1:
            old = self['order'][index+1]
            new = self['order'][index]
            self.component('name%d' % (index)).configure(text=old)
            self.component('name%d' % (index+1)).configure(text=new)
            self['order'][index] = old
            self['order'][index+1] = new
        elif index >= len(self['order']):
            old = self.component('name%d' % (index+1)).cget('text')
            new = self.component('name%d' % (index)).cget('text')
            self.component('name%d' % (index)).configure(text=old)
            self.component('name%d' % (index+1)).configure(text=new)
        else:
            # Newly inactive
            self['order'].pop()
            for label in ['up','name','down']:
                self.destroycomponent('%s%d' % (label,index))
            self.setElements()

    def deactivate(self, result=None):
        Pmw.Dialog.deactivate(self,result)
        # Delete buttons (can't really re-use them)
        for name in self.components():
            if self.componentgroup(name) in ['active','inactive']:
                self.destroycomponent(name)
