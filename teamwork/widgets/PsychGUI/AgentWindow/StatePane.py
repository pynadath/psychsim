from Tkinter import Frame,Label
import Pmw
import tkMessageBox
from teamwork.math.Keys import StateKey
from teamwork.dynamics.pwlDynamics import PWLDynamics
from teamwork.widgets.pmfScale import PMFScale
from teamwork.widgets.images import loadImages,makeButton
from teamwork.action.PsychActions import ActionCondition
from teamwork.widgets.TreeBuilder import TreeBuilder
from teamwork.reward.goal import PWLGoal

class StateFrame(Pmw.ScrolledFrame):
    """Frame to display the state of an entity
    """
    def __init__(self,parent,**kw):
        optiondefs = (
            ('entity', None,Pmw.INITOPT),
            ('generic',False,Pmw.INITOPT),
            ('society',{},None),
            ('expert',True,self.setExpert),
            ('balloon', None, Pmw.INITOPT),
            ('options',None,None),
            )
        self.defineoptions(kw, optiondefs)
        Pmw.ScrolledFrame.__init__(self,parent)
        self.entity = self['entity']
        # Set up images if available
        self.images = loadImages({'minus': 'icons/minus.gif',
                                  'plus': 'icons/plus.gif',
                                  'lock': 'icons/lock.gif',
                                  'unlock': 'icons/lock-unlock.gif',
                                  'del': 'icons/globe--minus.gif',
                                  'add': 'icons/chart--plus.gif',
                                  'prob': 'icons/chart--arrow.gif',
                                  'elem': 'icons/globe--arrow.gif',
                                  'new': 'icons/globe--plus.gif',
                                  'tree': 'icons/application-tree.gif'},
                                 self['options'].get('Appearance','PIL') == 'yes')
        self.parent = parent
        self.interior().columnconfigure(2,weight=1)
        if self['generic']:
            # Dialog for getting new symbol name
            self.createcomponent('newdialog',(),None,Pmw.PromptDialog,(parent,),
                                 title='New feature',entryfield_labelpos='w',
                                 label_text='Feature:',
                                 defaultbutton = 0,buttons = ('OK', 'Cancel'),
                                 command = self.newFeature).withdraw()
            # Draw the feature deletion dialog box
            self.createcomponent('confirmation',(),None,
                                 Pmw.MessageDialog,(parent,),
                                 title='Confirm Delete',
                                 buttons=('Yes','No'),
                                 defaultbutton='No',
                                 message_justify='left').withdraw()
        # Toolbar
        self.createcomponent('toolbar',(),None,Frame,(self.interior(),),
                             bd=2,relief='raised')
        if self['generic']:
            self.component('toolbar').grid(row=1,column=0,columnspan=4,sticky='ew')
        else:
            self.component('toolbar').grid(row=1,column=0,columnspan=3,sticky='ew')
        if self['generic']:
            # Button for adding new state feature
            button = makeButton(self.component('toolbar'),self.images,'new',
                                self.askNew,'+')
            button.pack(side='left',ipadx=5)
            if self['balloon']:
                self['balloon'].bind(button,'Create new state feature')
            # Button for deleting state feature
            button = makeButton(self.component('toolbar'),self.images,'del',
                                self.delete,'-')
            button.pack(side='left',ipadx=5)
            if self['balloon']:
                self['balloon'].bind(button,'Delete state feature')
        # Button for adding element to distribution
        makeButton(self.component('toolbar'),self.images,'add',
                   self.addElement,'Add Element',self,'element')
        if self['balloon']:
            self['balloon'].bind(self.component('element'),
                                 'Add element to probability distribution')
        # Button for toggling element/probability view of distribution
        makeButton(self.component('toolbar'),self.images,'prob',
                                  self.toggle,'Show probabilities',
                                  self,'probabilistic')
        if self['balloon']:
            self['balloon'].bind(self.component('probabilistic'),
                                'Show probability distribution')
        # Add the scales already present
        if self['generic']:
            featureList = self['entity'].getAllFillers('state')
        else:
            featureList = self['entity'].getStateFeatures()
        featureList.sort(lambda x,y:cmp(x.lower(),y.lower()))
        for i in range(len(featureList)):
            self.addFeature(featureList[i])
        self.selection = None
        self.initialiseoptions()

    def toggle(self,event=None):
        if self.selection is None:
            tkMessageBox.showerror('No selection','Please select the state feature whose view you wish to change.')
            return
        widget = self.component(self.selection)
        view = widget.cget('viewprobs')
        if view:
            if self.images.has_key('prob'):
                self.component('probabilistic').configure(image=self.images['prob'])
            else:
                self.component('probabilistic').configure(text='Show probabilities')
            if self['balloon']:
                self['balloon'].bind(self.component('probabilistic'),
                                     'Show probability distribution')
        else:
            if self.images.has_key('elem'):
                self.component('probabilistic').configure(image=self.images['elem'])
            else:
                self.component('probabilistic').configure(text='Show elements')
            if self['balloon']:
                self['balloon'].bind(self.component('probabilistic'),
                                     'Show elements of distribution')
        widget.configure(viewprobs=not view)

    def setExpert(self):
        if self['expert']:
            self.component('element').pack(side='left',ipadx=5)
            self.component('probabilistic').pack(side='left',ipadx=5)
##            self.component('dynamics').pack(side='left',ipadx=5)
        else:
            self.component('element').pack_forget() 
            self.component('probabilistic').pack_forget()
##            self.component('dynamics').pack_forget()
           
    def featureString(self,feature):
        """Converts a feature name into a Tk-friendly label string
        @type feature: C{str}
        @rtype: C{str}
        """
        return feature.replace('_',' ')
    
    def addFeature(self,feature,position=None):
        """Draws the widget for a new state feature
        """
        name = self.featureString(feature)
        if feature in self['entity'].getStateFeatures():
            entity = self['entity']
        else:
            other = self['entity'].getInheritor('state',feature)
            entity = self['society'][other]
        distribution = entity.getState(feature)
        # Place this scale in the correct alphabetical position
        if self['generic']:
            featureList = self['entity'].getAllFillers('state')
        else:
            featureList = self['entity'].getStateFeatures()
        featureList = filter(lambda f: f in self.components(),featureList)
        featureList.append(feature)
        featureList.sort(lambda x,y:cmp(x.lower(),y.lower()))
        index = featureList.index(feature)
        # Expand/collapse
        widget = self.createcomponent('%s-view' % (name),(),'expand',Label,
                                      (self.interior(),))
        if self['options'].get('Appearance','PIL') == 'yes':
            widget.configure(image=self.images['plus'])
        else:
            widget.configure(text='+',font=('Courier','24'))
        widget.bind('<ButtonRelease-1>',self.expand)
        widget.grid(row=index+2,column=0,sticky='nw')
        # Feature name widget
        widget = self.createcomponent('%s-label' % (name),(),'label',Label,
                                      (self.interior(),),
                                      text=feature[:32],anchor='w')
        widget.bind('<ButtonRelease-1>',self.select)
        widget.bind('<Double-Button-1>',self.expand)
        widget.grid(row=index+2,column=1,sticky='nwe',padx=10)
        if self['balloon']:
            self['balloon'].add(widget=widget,entity=self['entity'],key=name)
        # Sliders
        widget = self.createcomponent(name,(),'scale',PMFScale,
                                      (self.interior(),),
                                      distribution=distribution,
                                      hull_bd=2,hull_relief='groove',
                                      hull_padx=5,hull_pady=5,
                                      command = self.setValue,
                                      usePIL=self['options'].get('Appearance','PIL') == 'yes'
                                      )
#         if self['balloon']:
#             self['balloon'].add(widget=widget,entity=self['entity'],
#                                 key=feature)
        widget.grid(row=index+2,column=2,sticky='ew')
        if self['generic'] and self['entity'].getInheritor('state',feature,False):
            # Override default
            widget = self.createcomponent('%s-over' % (name),(),None,Label,
                                          (self.interior(),))
            widget.bind('<Double-Button-1>',self.override)
            if feature in self['entity'].getStateFeatures():
                widget.configure(image=self.images['unlock'],bd=0)
                if self['balloon']:
                    self['balloon'].bind(widget,'Double-click to restore inherited default value')
            else:
                self.component(name).configure(state='disabled')
                widget.configure(image=self.images['lock'],bd=0)
                if self['balloon']:
                    self['balloon'].bind(widget,'Double-click to override inherited default value')
            widget.grid(row=index+2,column=3,padx=5,sticky='nw')
        index += 1
        while index < len(featureList):
            name = self.featureString(featureList[index])
            self.component('%s-view' % (name)).grid(row=index+2,column=0)
            self.component('%s-label' % (name)).grid(row=index+2,column=1,sticky='ew')
            self.component(name).grid(row=index+2,column=2,sticky='ew')
            index += 1

    def event2feature(self,event):
        for feature in self.components():
            if self.component(feature) is event.widget:
                break
        else:
            raise ValueError
        return feature[:feature.rfind('-')]
    
    def expand(self,event=None):
        feature = self.event2feature(event)
        if self.isExpanded(feature):
            self.component('%s-dynamics' % (feature)).grid_forget()
            if self['options'].get('Appearance','PIL') == 'yes':
                event.widget.configure(image=self.images['plus'])
            else:
                event.widget.configure(text='+')
        else:
            try:
                frame = self.component('%s-dynamics' % (feature))
            except KeyError:
                frame = self.createcomponent('%s-dynamics' % (feature),(),'dynamics',
                                             Frame,(self.component(feature).interior(),))
                table = {}
                if not self['entity'].dynamics.has_key(feature):
                    self['entity'].dynamics[feature] = {}
                for action,function in self['entity'].dynamics[feature].items():
                    if isinstance(function,str):
                        # Generic action, skip for now
                        continue
##                        function = self['society'][function].dynamics[feature][action]
                    elif function is None:
                        # Null dynamics
                        continue
                    if isinstance(function,dict):
                        table[str(function['condition'])] = function                        
                    else:
                        condition = ActionCondition()
                        if isinstance(action,str):
                            condition.addCondition(action)
                        else:
                            condition.addCondition(action['type'])
                            action = str(action)
                        if isinstance(function,PWLDynamics):
                            function = function.getTree()
                        table[action] = {'condition': condition, 'tree': function}
                tree = self.createcomponent('%s-editor' % (feature),(),'editor',
                                            TreeBuilder,(frame,),society=self['society'],
                                            orient='horizontal',expert=True,
                                            key=StateKey({'entity':'self',
                                                          'feature':feature}),
                                            font=('Helvetica',10),treeWidth=250,
                                            delete=self.deleteTree,
                                            new=self.newTree,table=table)
                tree.pack(side='left',fill='both',expand='yes')
            if self['options'].get('Appearance','PIL') == 'yes':
                event.widget.configure(image=self.images['minus'])
            else:
                event.widget.configure(text='-')
            frame.grid(columnspan=3,sticky='ew')

    def deleteTree(self,entry):
        for table in self['entity'].dynamics.values():
            try:
                value = table[str(entry['condition'])]
                if value is entry:
                    del table[str(entry['condition'])]
            except KeyError:
                pass

    def newTree(self,key,condition,tree):
        self['entity'].dynamics[key['feature']][str(condition)] = {'condition':condition,'tree':tree}
        
    def isExpanded(self,feature):
        """
        @return:  C{True} iff the given row's details pane is expanded
        @rtype: bool
        """
        widget = self.component('%s-view' % (feature))
        if self['options'].get('Appearance','PIL') == 'yes':
            return str(widget.cget('image')) == str(self.images['minus'])
        else:
            return str(widget.cget('text')) == '-'
        
    def select(self,event=None):
        """Callback when clicking on a feature"""
        for name in self.components():
            if event.widget is self.component(name):
                feature = name[:-6]
                break
        if self.selection != feature:
            # Only if selection is changing
            palette = Pmw.Color.getdefaultpalette(self.component('hull'))
            if self.selection:
                # Deselect previous selection
                widget = self.component('%s-label' % (self.selection))
                widget.configure(fg=palette['foreground'],
                                 bg=palette['background'],bd=0)
            # Selecting a new scale
            self.selection = feature
            scale = self.component(feature)
            event.widget.configure(fg=palette['selectForeground'],
                                   bg=palette['selectBackground'],bd=3)
            # Update label and state of make probabilistic/deterministic
            button = self.component('probabilistic')
            if scale.cget('viewprobs'):
                if self.images.has_key('elem'):
                    button.configure(image=self.images['elem'])
                else:
                    button.configure(text='Show elements')
            else:
                if self.images.has_key('prob'):
                    button.configure(image=self.images['prob'])
                else:
                    button.configure(text='Show probabilities')

    def setValue(self,widget,value=None):
        for feature in self.components():
            if widget is self.component(feature):
                break
        if value is None:
            value = widget['distribution']
        if feature in self['entity'].getStateFeatures() or self['entity'].parent:
            self['entity'].setState(feature,value)
            if self['generic'] and self['entity'].parent is None:
                for other in self['society'].members():
                    if other.name != self['entity'].name and \
                           other.isSubclass(self['entity'].name) and \
                           feature not in other.getStateFeatures() and \
                           other.attributes.has_key('window'):
                        other.attributes['window'].component('State').set(feature,value)
            
    def update(self):
        try:
            self['generic']
        except KeyError:
            # Tk bug probably because a window's not getting destroyed properly
            print self.entity.ancestry()
            return
        if self['generic']:
            features = self['entity'].getAllFillers('state')
        else:
            features = self['entity'].getStateFeatures()
        for name in self.components():
            # Find out which features we already have scales for
            if self.componentgroup(name) == 'scale':
                try:
                    features.remove(name)
                    self.set(name)
                except ValueError:
                    # This feature no longer there, so we don't need scale
                    self.delete(feature=name,confirm=True)
        # Add needed scales
        for feature in features:
            self.addFeature(feature)
            self.set(feature)
                
    def set(self,feature,value=None):
        name = self.featureString(feature)
        widget = self.component(name)
        if value is None:
            if feature in self['entity'].getStateFeatures():
                entity = self['entity']
            else:
                other = self['entity'].getInheritor('state',feature)
                entity = self['society'][other]
            value = entity.getState(feature)
        try:
            widget['distribution'] = value
        except KeyError:
            # Too early?
            pass
        if self['generic']:
            for name in self['society'].descendents(self['entity'].name):
                other = self['society'][name]
                if other.attributes.has_key('window') and \
                       other.name != self['entity'].name and \
                       feature not in other.getStateFeatures():
                    other.attributes['window'].component('State').set(feature,
                                                                      value)
                    
    def delete(self,event=None,feature=None,confirm=None):
        if feature is None:
            feature = self.selection
        if feature is None:
            tkMessageBox.showerror('No selection','Please select the state feature to delete')
            return
        if confirm is None:
            # Let's check whether there are other references to this feature
            refs = self.checkDynamics(feature)
            if len(refs) > 0:
                msg = []
                for ref in refs:
                    msg.append('Effect of %s on %s\'s %s' % \
                               (ref['action'],ref['entity'].name,
                                ref['feature']))
                msg.sort()
                msg.insert(0,'')
                msg.insert(0,'There are references to this state feature in '\
                           'the internal dynamics that I do not know how to '\
                           'remove:')
                msg.append('')
                msg.append('Please remove these references before deleting.')
                tkMessageBox.showerror('Unable to delete state feature',
                                       '\n'.join(msg))
                return
        else:
            refs = []
        # Check dynamics of this feature
        if self['entity'].dynamics.has_key(feature) and \
               len(self['entity'].dynamics[feature]) > 0:
            refs.append({'type':'dynamics','entity':self['entity']})
        # Check goals for references to this feature
        for entity in self['society'].members():
            for goal in entity.getGoals():
                key = goal.toKey()
                if isinstance(key,StateKey) and key['feature'] == feature:
                    if key['entity'] == self['entity'].name:
                        refs.append({'type':'goal','entity':entity,
                                     'key':key,'goal':goal})
                    elif entity.name == self['entity'].name and \
                         key['entity'] == 'self':
                        refs.append({'type':'goal','entity':entity,
                                     'key':key,'goal':goal})
        dialog = self.component('confirmation')
        if confirm is None:
            query = 'Are you sure you wish to delete this state feature?'
            if len(refs) > 0:
                query += '\nIf you do so, the following references will be removed:'
                for ref in refs:
                    if ref['type'] == 'goal':
                        query += '\n\t%s\'s goal to %s' % \
                                 (ref['entity'].name,str(ref['goal']))
                    elif ref['type'] == 'dynamics':
                        entity = ref['entity']
                        query += '\n\tdynamics of %s' % \
                                 (', '.join(entity.dynamics[feature].keys()))
            dialog.configure(message_text=query,
                             command=lambda c,s=self,f=feature:\
                             s.delete(feature=f,confirm=c=='Yes'))
            dialog.activate()
        else:
            dialog.deactivate()
        if confirm:
            name = self.featureString(feature)
            # Update GUI
            self.destroycomponent('%s-view' % (name))
            self.destroycomponent('%s-label' % (name))
            self.destroycomponent(name)
            try:
                self.destroycomponent('%s-dynamics' % (name))
                self.destroycomponent('%s-editor' % (name))
            except KeyError:
                pass
            if self.selection == name:
                # Deselect
                self.selection = None
            if feature in self['entity'].getStateFeatures():
                self['entity'].deleteState(feature)
            # Delete referring goals
            names = {}
            for ref in refs:
                if ref['type'] == 'goal':
                    names[ref['entity'].name] = True
                    del self['society'][ref['entity'].name].goals[ref['goal']]
            for name in names.keys():
                self['society'][name].normalizeGoals()
                try:
                    window = self['society'][name].attributes['window']
                    window.component('Goals').recreate_goals()
                except KeyError:
                    pass
            # Delete any dynamics
            try:
                del self['entity'].dynamics[feature]
            except KeyError:
                pass
            # Remove state feature from all inheriting subclasses
            if self['generic']:
                for name in self['society'].descendents(self['entity'].name):
                    other = self['society'][name]
                    if other.name != self['entity'].name and \
                           feature not in other.getStateFeatures() and \
                           other.attributes.has_key('window'):
                        other.attributes['window'].component('State').delete(feature=feature,confirm=True)
            
    def override(self,event=None):
        feature = self.event2feature(event)
        widget = self.component(self.featureString(feature))
        # Figure out whether we're overriding or underriding
        if str(event.widget.cget('image')) == str(self.images['lock']):
            value = self['entity'].getCumulativeState(feature)
            self['entity'].setState(feature,value)
            widget.configure(state='normal')
            event.widget.configure(image=self.images['unlock'])
            if self['balloon']:
                self['balloon'].bind(event.widget,'Double-click to restore inherited default value')
        else:
            self['entity'].deleteState(feature)
            widget['distribution'] = self['entity'].getCumulativeState(feature)
            widget.configure(state='disabled')
            event.widget.configure(image=self.images['lock'])
            if self['balloon']:
                self['balloon'].bind(event.widget,'Double-click to override inherited default value')
        
    def addElement(self,event=None):
        if self.selection is None:
            tkMessageBox.showerror('No selection','Please select the state feature whose view you wish to add the element to.')
        else:
            widget = self.component(self.featureString(self.selection))
            widget.addElement()
        
    def askNew(self,event=None):
        """Prompts user for name of new state feature
        """
        self.component('newdialog').activate(geometry = 'centerscreenalways')

    def newFeature(self,button):
        self.component('newdialog').deactivate()
        feature = self.component('newdialog').getvalue()
        self.component('newdialog').clear()
        self.component('newdialog_entry').focus_set()
        if button == 'OK':
            if len(feature) == 0:
                tkMessageBox.showerror('Illegal Feature Name',
                                       'Please enter the name of the new state feature before adding it.')
            elif feature == PWLGoal.goalFeature:
                tkMessageBox.showerror('Illegal Feature Name',
                                       'Cannot use reserved keyword "%s" as feature name' % (feature))
            else:
                self['entity'].setState(feature,0.)
                self.addFeature(feature)
                if self['generic']:
                    for name in self['society'].descendents(self['entity'].name):
                        other = self['society'][name]
                        if other.name != self['entity'].name and \
                               feature not in other.getStateFeatures() and \
                               other.attributes.has_key('window'):
                            widget = other.attributes['window'].component('State')
                            widget.addFeature(feature)
        
    def setState(self,state):
        """Sets the state Tk configuration feature on this widget"""
        for feature in self['entity'].getStateFeatures():
            self.component(self.featureString(feature)).configure(state=state)

    def checkDynamics(self,toDelete):
        """Identifies any references to the given state feature in dynamics
        """
        refs = []
        descendents = self['society'].descendents(self['entity'].name)
        for entity in self['society'].members():
            for feature,table in entity.dynamics.items():
                for actType,dynamics in table.items():
                    if isinstance(dynamics,dict):
                        dynamics = dynamics['tree']
                    keys = {}
                    # Iterate through all nodes
                    remaining = [dynamics]
                    while len(remaining) > 0:
                        tree = remaining.pop()
                        if tree.isLeaf():
                            # Check effect row for refs
                            row = tree.getValue().values()[0]
                            if row.sourceKey['feature'] == toDelete:
                                keys[row.sourceKey] = True
                            if isinstance(row.deltaKey,StateKey) and \
                               row.deltaKey['feature'] == toDelete:
                                keys[row.deltaKey] = True
                        else:
                            # Check branch for refs
                            remaining += tree.children()
                            if not tree.isProbabilistic():
                                for plane in tree.split:
                                    for key in plane.weights.specialKeys:
                                        if isinstance(key,StateKey) and \
                                               key['feature'] == toDelete:
                                            keys[key] = True
                    for key in keys.keys():
                        entry = {'type':'dynamics','entity':entity,
                                 'feature':feature,'key':key,'action':actType}
                        if key['entity'] == 'self':
                            # Check whether I'm someone who has the feature
                            if entity.name in descendents and \
                                   key['feature'] != feature:
                                # Unless it's the dynamics of that feature
                                refs.append(entry)
                        elif key['entity'] == 'actor':
                            # Check whether any possible actor has the feature
                            for other in descendents:
                                agent = self['society'][other]
                                for action in sum(agent.actions.getOptions(),
                                                  []):
                                    if action['type'] == actType:
                                        refs.append(entry)
                                        break
                                else:
                                    # Didn't find any, so go to next agent
                                    continue
                                break
                        elif key['entity'] == 'object':
                            # Check whether any possible objects
                            for other in self['society'].members():
                                for action in sum(other.actions.getOptions(),
                                                  []):
                                    if action['type'] == actType and \
                                       action['object'] in descendents:
                                        refs.append(entry)
                                        break
                                else:
                                    continue
                                break
                        else:
                            # Relationship
                            for other in entity.relationships[key['entity']]:
                                if other in descendents:
                                    refs.append(entry)
                                    break
        return refs

    def getActiveTree(self):
        """
        @return: the active tree editor
        """
        open = filter(lambda name: self.componentgroup(name) == 'editor' and \
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

