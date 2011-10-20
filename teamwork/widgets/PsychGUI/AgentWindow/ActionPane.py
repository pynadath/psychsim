from Tkinter import Frame,IntVar,Checkbutton,Label,Button
import Pmw
import tkMessageBox
from teamwork.action.PsychActions import Action
from teamwork.dynamics.pwlDynamics import PWLDynamics
from teamwork.agent.Generic import GenericModel
from teamwork.widgets.images import loadImages,makeButton
from teamwork.math.Keys import ActionKey,StateKey
from teamwork.widgets.TreeBuilder import TreeBuilder

class ActionFrame(Pmw.ScrolledFrame):
    """Frame to define and view the entity's available actions
    """
    def __init__(self,parent,**kw):
        palette = Pmw.Color.getdefaultpalette(parent)
        optiondefs = (
            ('entity', None, Pmw.INITOPT),
            ('expert',True,None),
            ('balloon',None, None),
            ('generic',False,Pmw.INITOPT),
            ('command',None, None),
            ('society',{},None),
            ('options',None,None),
            ('entities',{},None),
            )
        self.selection = {}
        self.defineoptions(kw, optiondefs)
        Pmw.ScrolledFrame.__init__(self,parent)
        self.images = loadImages({'minus': 'icons/minus.gif',
                                  'plus': 'icons/plus.gif',
                                  'add': 'icons/hammer--plus.gif',
                                  'del': 'icons/hammer--minus.gif',
                                  'group': 'icons/hammer-screwdriver.gif',
                                  'forbid': 'icons/slash.gif',
                                  'allow': 'icons/tick.gif',
                                  'tree': 'icons/application-tree.gif'},
                                 self['options'].get('Appearance','PIL') == 'yes')
        toolbar = Frame(self.interior(),bd=2,relief='raised')
        self.interior().grid_columnconfigure(0,weight=1)
        toolbar.grid(row=0,column=0,sticky='ew')
        if self['generic']:
            # Dialog for creating new action
            self.createcomponent('dialog',(),None,Pmw.Dialog,(self.interior(),),
                                 buttons=('OK','Cancel'),defaultbutton=0,
                                 command=self.add)
            self.component('dialog').withdraw()
            # Type selector
            b = self.createcomponent('type',(),None,Pmw.ComboBox,
                                     (self.component('dialog').interior(),),
                                     labelpos='n',label_text='Type',
                                     autoclear=True,history=True,unique=True,
                                     )
            b.pack(side='left',fill='both')
            b = self.createcomponent('object',(),None,Pmw.ComboBox,
                                     (self.component('dialog').interior(),),
                                     labelpos='n',label_text='Object',
                                     entry_state='disabled',
                                     entry_disabledforeground=palette['foreground'],
                                     entry_disabledbackground=palette['background'],
                                     )
            b.pack(side='left',fill='both')
            # Button for adding new actions
            button = makeButton(toolbar,self.images,'add',
                                self.promptNew,'+')
            button.pack(side='left',ipadx=5,ipady=3)
            if self['balloon']:
                self['balloon'].bind(button,'Add new action')
            # Button for deleting actions
            button = makeButton(toolbar,self.images,'del',
                                self.delete,'-')
            button.pack(side='left',ipadx=5,ipady=3)
            if self['balloon']:
                self['balloon'].bind(button,'Delete selected actions')
            # Button for creating concurrent actions
            button = makeButton(toolbar,self.images,'group',
                                self.group,'Group')
            button.pack(side='left',ipadx=5,ipady=3)
            if self['balloon']:
                msg = 'Groups the selected actions into a single, concurrent '\
                    'decision that takes place in a single time step.'
                self['balloon'].bind(button,msg)
        # Button for allowing actions
        button = makeButton(toolbar,self.images,'allow',
                            self.selectAll,'Allow')
        button.pack(side='left',ipadx=5,ipady=3)
        if self['balloon']:
            self['balloon'].bind(button,'Activate all actions')
        # Button for allowing actions
        button = makeButton(toolbar,self.images,'forbid',
                            self.deselectAll,'Forbid')
        button.pack(side='left',ipadx=5,ipady=3)
        if self['balloon']:
            self['balloon'].bind(button,'Deactivate all actions')
        # Frame for containing action buttons
        self.createcomponent('options',(),None,Frame,(self.interior(),))
        self.component('options').grid(row=1,column=0,sticky='wnes',
                                       padx=10,pady=10)
        self.component('options').grid_columnconfigure(3,weight=1)
        self.variables = {}
        self.drawActions()
        self.initialiseoptions()
        
    def getOptions(self,sorted=False):
        if isinstance(self['entity'],GenericModel):
            options = self['entity'].getAllFillers('action')
        else:
            options = self['entity'].actions.getOptions()
        if sorted:
            op = lambda a:[a['type'].lower(),str(a['actor']).lower(),a['object']]
            options.sort(lambda x,y:cmp(sum(map(op,x),[]),
                                        sum(map(op,y),[])))
        return options
        
    def setState(self,state):
        for action in self.getOptions():
            name = '%s %s' % (self['entity'].ancestry(),str(action))
            widget = self.component(name)
            widget.configure(state=state)
    
    def getActions(self):
        """
        @return: all of the actions selected
        @rtype: L{Action<teamwork.action.PsychActions.Action>}[][]
        """
        options = []
        for action in self.getOptions():
            key = self['entity'].makeActionKey(action)
            if self.variables[key].get():
                options.append(action)
        return options
    
    def selectAll(self,event=None):
        for action in self.getOptions():
            self.selectAction(action,True)

    def deselectAll(self,event=None):
        for action in self.getOptions():
            self.selectAction(action,False)

    def delete(self,event=None):
        undeleted = []
        if len(self.selection) == 0:
            tkMessageBox.showerror('Nothing selected','Please select at least one action to delete')
        elif tkMessageBox.askyesno('Confirm Delete','Are you sure you want to permanently delete the selected action(s) from this generic society?  If you simply want to omit the actions from the instantiated scenario, you need only de-select them before invoking the wizard.'):
            deleted = []
            society = self['entity'].hierarchy
            for option in self.getOptions():
                actionKey = self['entity'].makeActionKey(option)
                if self.selection.has_key(actionKey):
                    try:
                        self['entity'].actions.extras.remove(option)
                        del self.selection[actionKey]
                        del self.variables[actionKey]
                        deleted.append(actionKey)
                        if len(option) == 1:
                            # Remove goals that refer to this action
                            for agent in society.values():
                                goals = agent.getGoals()
                                change = False
                                for goal in goals[:]:
                                    for key in goal.keys:
                                        if isinstance(key,ActionKey) and \
                                                key['type'] == option[0]['type']:
                                            goals.remove(goal)
                                            change = True
                                if change:
                                    agent.setGoals(goals)
                                    if agent.attributes.has_key('window'):
                                        widget = agent.attributes['window'].component('Goals')
                                        widget.recreate_goals()
                                        # Remove action from choices
                                        widget.selectEntity()
                    except ValueError:
                        undeleted.append(actionKey)
            for actionKey in deleted:
                self.deleteAction(actionKey)
        if len(undeleted) > 0:
            tkMessageBox.showwarning(title='Unable to Delete',message='The following actions cannot be deleted, as they are inherited from ancestor classes: %s' % (';'.join(undeleted)))

    def deleteAction(self,action):
        """Deletes all widgets (in this window and in descendent windows) associated with the given action
        @type action: str
        """
        for name in self.components():
            if self.componentgroup(name) == action and name[-6:] != 'editor':
                # Internal dynamics editor will get deleted with the outer frame
                self.destroycomponent(name)
        society = self['entity'].hierarchy
        descendents = society.descendents(self['entity'].name)
        for name in descendents:
            # Remove from action pane of descendents
            if name != self['entity'].name:
                agent = society[name]
                if agent.attributes.has_key('window'):
                    window = agent.attributes['window']
                    widget = window.component('Actions')
                    if widget.selection.has_key(action):
                        del widget.selection[action]
                    for name in widget.components():
                        if widget.componentgroup(name) == action:
                            widget.destroycomponent(name)


    def promptNew(self,event):
        self.updateTypes()
        self.component('object').insert(0,'None')
        self.component('object').selectitem(0,setentry=1)
        self.updateObjects()
        self.component('type_entry').focus_set()
        self.component('dialog').activate(geometry='centerscreenalways')

    def add(self,button):
        self.component('dialog').deactivate()
        if button == 'OK':
            verb = self.component('type').get()
            if len(verb) > 0:
                action = Action({'actor':self['entity'].name,'type':verb})
                obj = self.component('object').get()
                if self.objects[obj]:
                    action.update(self.objects[obj])
                self['entity'].actions.directAdd([action])
                self.redrawDescendents()
                self.component('type_entryfield').clear()
            else:
                tkMessageBox.showerror('Illegal Action','Action type is empty.')
            
    def group(self,event=None):
        # Accumulate individual actions selected (avoiding duplicates)
        selected = {}
        for original in self.getOptions():
            if self.selection.has_key(self['entity'].makeActionKey(original)):
                for action in original:
                    selected[action] = True
        # Generate concurrent actions
        if len(selected) < 2:
            tkMessageBox.showerror('Illegal Selection','You must select multiple actions to be performed concurrently.')
        else:
            # Generate the new combination
            option = []
            for action in selected.keys():
                # Copy the original action
                option.append(Action(action))
            option.sort()
            # Make sure that this is a new combination
            for original in self.getOptions():
                if self['entity'].makeActionKey(original) == self['entity'].makeActionKey(option):
                    # Match
                    tkMessageBox.showerror('Illegal Selection','That concurrent action already exists in this agent\'s decision space')
                    break
            else:
                # New option
                self['entity'].actions.directAdd(option)
                self.redrawDescendents()

    def redrawDescendents(self):
        agents = self['entity'].hierarchy.descendents(self['entity'].name)
        for name in agents:
            agent = self['entity'].hierarchy[name]
            if agent.attributes.has_key('window'):
                agent.attributes['window'].component('Actions').drawActions()
        
    def updateTypes(self,event=None):
        """Refreshes the list of possible types to choose from when creating a new action"""
        items = {}
        for name in self['entity'].ancestors():
            entity = self['entity'].hierarchy[name]
            for option in entity.actions.getOptions():
                for action in option:
                    items[action['type']] = True
        items = items.keys()
        items.sort(lambda x,y:cmp(x.lower(),y.lower()))
        self.component('type_scrolledlist').setlist(items)
        
    def updateObjects(self,event=None):
        """Refreshes the list of possible objects to choose from when creating a new action"""
        noneLabel = 'None'
        self.objects = {noneLabel:None}
        for cls,agent in self['entity'].hierarchy.items():
            if self['entity'].isSubclass(cls):
                self.objects['%s (including self)' % (cls)] = {'object':cls,
                                                               'self':True}
                self.objects['%s (but not self)' % (cls)] = {'object':cls,
                                                             'self':False}
                for relationship in agent.relationships.keys():
                    if not self.objects.has_key(relationship):
                        self.objects[relationship] = {'object':relationship}
            else:
                self.objects[cls] = {'object':cls}
        items = self.objects.keys()
        items.remove(noneLabel)
        items.sort(lambda x,y:cmp(x.lower(),y.lower()))
        items.insert(0,noneLabel)
        self.component('object_listbox').delete(0,'end')
        for option in items:
            self.component('object_listbox').insert('end',option)

    def drawActions(self):
        """Draws the buttons or labels for the current decision space
        """
        components = filter(lambda n:self.componentgroup(n) == 'Select',
                            self.components())
        options = self.getOptions(sorted=True)
        row = 1
        for index in range(len(options)):
            action = options[index]
            actionKey = self['entity'].makeActionKey(action)
            col = 0
            # Expand/collapse
            name = '%s-view' % (actionKey)
            try:
                b = self.component(name)
            except KeyError:
                b = self.createcomponent(name,(),actionKey,Label,
                                         (self.component('options'),))
                if self['options'].get('Appearance','PIL') == 'yes':
                    b.configure(image=self.images['plus'])
                else:
                    b.configure(text='+')
                b.bind('<ButtonRelease-1>',self.expand)
            b.grid(row=row,column=col,sticky='nw')
            col += 1
            if not self['generic'] and self['entity'].parent is None:
                # Action button
                try:
                    b = self.component(actionKey)
                except KeyError:
                    b = self.createcomponent(actionKey,(),actionKey,Button,
                                             (self.component('options'),),
                                             text=actionKey)
                    cmd = lambda s=self,a=action:s.performAction(a)
                    b.configure(command=cmd)
                b.grid(row=row,column=col,sticky='we')
                col += 1
            else:
                # Action label
                for i in range(len(action)):
                    try:
                        b = self.component('%s actor %d' % (actionKey,i))
                    except KeyError:
                        b = self.createcomponent('%s actor %d' % (actionKey,i),(),actionKey,Label,
                                                 (self.component('options'),),
                                                 text=action[i]['actor'],
                                                 justify='left',anchor='w')
                        b.bind('<Button-1>',self.select)
                    b.grid(row=row,column=col,sticky='ew')
                    try:
                        b = self.component('%s type %d' % (actionKey,i))
                    except KeyError:
                        b = self.createcomponent('%s type %d' % (actionKey,i),(),actionKey,Label,
                                                 (self.component('options'),),
                                                 text=action[i]['type'],
                                                 justify='left',anchor='w')
                        b.bind('<Button-1>',self.select)
                    b.grid(row=row,column=col+1,sticky='ew')
                    try:
                        b = self.component('%s obj %d' % (actionKey,i))
                    except KeyError:
                        if action[i]['object']:
                            obj = action[i]['object']
                        else:
                            obj = ''
                        b = self.createcomponent('%s obj %d' % (actionKey,i),(),actionKey,
                                                 Label,(self.component('options'),),
                                                 text=obj,justify='left',anchor='w')
                        b.bind('<Button-1>',self.select)
                    b.grid(row=row,column=col+2,sticky='ew')
                    col += 3
            # (De)activator
            try:
                b = self.component('%s active' % (actionKey))
            except KeyError:
                self.variables[actionKey] = IntVar()
                cmd = lambda s=self,a=action: s.selectAction(a)
                b = self.createcomponent('%s active' % (actionKey),(),actionKey,Checkbutton,
                                         (self.component('options'),),
                                         command=cmd,
                                         variable = self.variables[actionKey])
            legal = int(not self['entity'].actions.illegal.has_key(str(action)))
            self.variables[actionKey].set(legal)
            b.grid(row=row,column=col)
            col += 1
            row += 1
            # Draw dynamics
            if self.isExpanded(actionKey):
                widget = self.component('%s-dynamics' % (actionKey))
                widget.grid(row=row,column=1,columnspan=4,sticky='ewns')
                row += 1
        # Delete leftover (i.e., out of date) action widgets
        for name in components:
            self.deleteAction(name[7:])

    def performAction(self,action):
        """Callback wrapper for performing an action directly
        """
        if self['command']:
            self['command'](action)

    def event2action(self,event):
        for name in self.components():
            if self.component(name) is event.widget:
                break
        else:
            raise UserWarning,'Selection in unidentifiable widget'
        for option in self.getOptions():
            key = self['entity'].makeActionKey(option)
            if self.componentgroup(name) == key:
                return option
##            if name[:len(key)] == key:
##                return option
        raise NameError,'Unable to extract action from widget label: %s' % (name)
        
    def select(self,event):
        action = self.event2action(event)
        actionKey = self['entity'].makeActionKey(action)
        palette = Pmw.Color.getdefaultpalette(self.component('hull'))
        if self.selection.has_key(actionKey):
            fg = palette['foreground']
            bg = palette['background']
            del self.selection[actionKey]
        else:
            fg = palette['selectForeground']
            bg = palette['selectBackground']
            self.selection[actionKey] = True
        for name in self.components():
            if self.componentgroup(name) == actionKey and \
               name[-6:] != 'active' and \
               name[:len(actionKey)+1] == actionKey+' ':
                # Hacky filter
                self.component(name).configure(fg=fg,bg=bg)
        
    def selectAction(self,option,value=None,root=True):
        actionKey = self['entity'].makeActionKey(option)
        if value is None:
            # Figure selection state
            value = self.variables[actionKey].get()
        else:
            # Set to chosen state
            self.variables[actionKey].set(value)
        if root:
            if self['generic']:
                # Inheritance of selection
                agents = self['entity'].hierarchy.descendents(self['entity'].name)
                for name in agents:
                    # Update descendents
                    agent = self['entity'].hierarchy[name]
                    if agent.attributes.has_key('window'):
                        widget = agent.attributes['window'].component('Actions')
                        widget.selectAction(option,value,False)
                    if value:
                        del agent.actions.illegal[str(option)]
                    else:
                        agent.actions.illegal[str(option)] = option
            else:
                if value:
                    try:
                        del self['entity'].actions.illegal[str(option)]
                    except KeyError:
                        # If we're selecting ALL, then this is possible
                        pass
                else:
                    self['entity'].actions.illegal[str(option)] = option
    
    def collapse(self,actionKey):
        # Collapse dynamics frame
        self.component('%s-dynamics' % (actionKey)).grid_forget()
        if self['options'].get('Appearance','PIL') == 'yes':
            self.component('%s-view' % (actionKey)).configure(image=self.images['plus'])
        else:
            self.component('%s-view' % (actionKey)).configure(text='+')

    def expand(self,event):
        action = self.event2action(event)
        actionKey = self['entity'].makeActionKey(action)
        if self.isExpanded(actionKey):
            self.collapse(actionKey)
        else:
            try:
                frame = self.component('%s-dynamics' % (actionKey))
            except KeyError:
                # Create dynamics frame from scratch
                frame = self.createcomponent('%s-dynamics' % (actionKey),(),actionKey,
                                             Frame,(self.component('options'),),
                                             bd=3,relief='ridge')
                # Find existing dynamics relevant to this action
                table = {}
                for entity in self['society'].members():
                    # Extract dynamics
                    for feature,subDynamics in entity.dynamics.items():
                        for label,dynamics in subDynamics.items():
                            if isinstance(dynamics,str):
                                dynamics = self['entity'].hierarchy[dynamics].dynamics[feature][label]
                            if (isinstance(dynamics,dict) and dynamics['condition'].match(action)) or \
                                   (isinstance(dynamics,PWLDynamics) and actionKey == label):
                                key = StateKey({'entity':entity.name,
                                                'feature':feature})
                                if isinstance(dynamics,dict):
                                    dynamics['lhs'] = key
                                    table[str(key)] = dynamics
                                else:
                                    table[str(key)] = {'tree': dynamics.getTree(),'lhs': key}
                assert len(action) == 1
                if action[0]['object']:
                    key = ActionKey({'type': action[0]['type'],
                                     'entity': action[0]['actor'],
                                     'object': action[0]['object']})
                else:
                    key = ActionKey({'type': action[0]['type'],
                                     'entity': action[0]['actor'],
                                     'object': None})
                tree = self.createcomponent('%s-editor' % (actionKey),(),actionKey,
                                            TreeBuilder,(frame,),society=self['society'],
                                            orient='horizontal',expert=True,
                                            delete=self.delTree,key=key,
                                            font=('Helvetica',10),treeWidth=250,
                                            new=self.newTree,table=table)
                tree.pack(side='left',fill='both',expand='yes',padx=10,pady=10)
            if self['options'].get('Appearance','PIL') == 'yes':
                event.widget.configure(image=self.images['minus'])
            else:
                event.widget.configure(text='-')
        # Shuffle widgets up/down
        row = 1
        found = False
        for option in self.getOptions(sorted=True):
            key = self['entity'].makeActionKey(option)
            if found:
                self.component('%s-view' % (key)).grid(row=row)
                if not self['generic'] and self['entity'].parent is None:
                    self.component(key).grid(row=row)
                else:
                    self.component('%s actor 0' % (key)).grid(row=row)
                    self.component('%s type 0' % (key)).grid(row=row)
                    self.component('%s obj 0' % (key)).grid(row=row)
                self.component('%s active' % (key)).grid(row=row)
            row += 1
            if key == actionKey:
                found = True
            if self.isExpanded(key):
                if found:
                    widget = self.component('%s-dynamics' % (key))
                    widget.grid(row=row,column=1,columnspan=4,sticky='ewns')
                row += 1
        
    def isExpanded(self,action):
        """
        @type action: str
        @return:  C{True} iff the given row's details pane is expanded
        @rtype: bool
        """
        widget = self.component('%s-view' % (action))
        if self['options'].get('Appearance','PIL') == 'yes':
            return str(widget.cget('image')) == str(self.images['minus'])
        else:
            return str(widget.cget('text')) == '-'
                
    def newTree(self,key,condition,tree):
        """Callback from L{TreeBuilder} when creating a new dynamics entry
        """
        entity = self['society'][key['entity']]
        try:
            entity.dynamics[key['feature']][str(condition)] = {'condition':condition,'tree':tree}
        except KeyError:
            entity.dynamics[key['feature']] = {str(condition) : {'condition':condition,'tree':tree}}

    def delTree(self,entry):
        """Callback from L{TreeBuilder} when deleting a dynamics entry
        """
        entity = self['society'][entry['lhs']['entity']]
        del entity.dynamics[entry['lhs']['feature']][str(entry['condition'])]

    def getActiveTree(self):
        """
        @return: the active tree editor
        """
        open = filter(lambda name: name[-7:] == '-editor' and \
                          self.isExpanded(name[:-7]),self.components())
        if len(open) == 0:
            return None
        if len(open) == 1:
            return self.component(open[0])
        else:
            # Figure out which tree has focus
            for name in open:
                if self.focus_get() is self.component('%s_tree' % (name)):
                    return self.component(name)
            else:
                raise NameError,'Unable to determine selection when multiple trees open'

    def getSelection(self):
        widget = self.getActiveTree()
        if widget is None:
            return None
        else:
            return widget.getSubtree()

    def paste(self,content):
        widget = self.getActiveTree()
        if widget is None:
            tkMessageBox.showerror('Unable to Paste','No open tree to paste to.')
        else:
            widget.paste(content)
