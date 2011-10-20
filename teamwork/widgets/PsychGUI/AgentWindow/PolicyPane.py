import os
from Tkinter import Frame,Label,Scale
import tkMessageBox
import tkFileDialog
import Pmw
from teamwork.widgets.cookbook import MultiListbox
from teamwork.widgets.images import loadImages,makeButton
from teamwork.widgets.attribute import AttributeDialog
from teamwork.math.Keys import StateKey
from teamwork.math.KeyedVector import KeyedVector,ThresholdRow
from teamwork.policy.pwlTable import PWLTable
from teamwork.agent.lightweight import PWLAgent
from teamwork.multiagent.GenericSociety import GenericSociety
import random
random.seed()

class PolicyFrame(Pmw.ScrolledFrame):
    
    def __init__(self,parent,entity,**kw):
        optiondefs = (
            ('balloon',None,Pmw.INITOPT),
            ('command',None,None),
            ('generic',False,None),
            ('society',{},None),
            ('expert', False,self.setExpert),
            ('actions',None,None),
            ('options',None,None),
            )
        self.defineoptions(kw, optiondefs)
        self.entity = entity
        self.selected = None
        self.lists = {}
        Pmw.ScrolledFrame.__init__(self,parent)
        self.images = loadImages({'wand': 'icons/wand.gif',
                                  'add': 'icons/traffic-light--plus.gif',
                                  'del': 'icons/traffic-light--minus.gif',
                                  'edit': 'icons/traffic-light--pencil.gif',
                                  'arrow': 'icons/traffic-light--arrow.gif',
                                  'policy': 'icons/traffic-light.gif',
                                  'rand': 'icons/bomb.gif',
                                  'plus': 'icons/plus.gif',
                                  'solve': 'icons/wand--exclamation.gif'},
                                 self['options'].get('Appearance','PIL') == 'yes')
        self.createcomponent('toolbar',(),None,Frame,(self.interior(),),
                             bd=2,relief='raised')
        self.component('toolbar').grid(row=0,column=0,sticky='ew')
        # Button for adding a LHS attributes
        button = makeButton(self.component('toolbar'),self.images,'add',
                            self.newAttribute,'+')
        button.pack(side='left',ipadx=5)
        if self['balloon']:
            msg = 'Add an additional condition to the left-hand side '\
                  'of the rules.'
            self['balloon'].bind(button,msg)
        # Button for removing a LHS attributes
        button = makeButton(self.component('toolbar'),self.images,'del',
                            self.delAttribute,'-')
        button.pack(side='left',ipadx=5)
        if self['balloon']:
            msg = 'Removes the selected condition from the left-hand '\
                  'side of the rules.'
            self['balloon'].bind(button,msg)
        # Button for generating LHS
        button = makeButton(self.component('toolbar'),self.images,'arrow',
                            self.generateLHS,'LHS')
        button.pack(side='left',ipadx=5)
        if self['balloon']:
            msg = 'Automatically generate the possible situations for '\
                  'this agent to consider.'
            self['balloon'].bind(button,msg)
        # Button for viewing current rule
        button = makeButton(self.component('toolbar'),self.images,'edit',
                            self.open,'RHS')
        button.pack(side='left',ipadx=5)
        if self['balloon']:
            msg = 'Opens a dialog box for viewing or editing the action ranking that will be applied in the current state.'
            self['balloon'].bind(button,msg)
        # Button for seeding
        button = makeButton(self.component('toolbar'),self.images,'rand',
                            self.seed,'Randomize')
        button.pack(side='left',ipadx=5)
        if self['balloon']:
            msg = 'Seed the rules with a random initial set of actions.'
            self['balloon'].bind(button,msg)
        # Button for policy iteration
        button = makeButton(self.component('toolbar'),self.images,'wand',
                            self.policyIteration,'Optimize')
        button.pack(side='left',ipadx=5)
        if self['balloon']:
            msg = 'Automatically generate optimal set of actions for the current rules.'
            self['balloon'].bind(button,msg)
        if self['options'] and \
                self['options'].get('General','testing') == 'true':
            # Button for import policy
            button = makeButton(self.component('toolbar'),self.images,'solve',
                                self.solve,'POMDP')
            button.pack(side='left',ipadx=5)
            if self['balloon']:
                msg = 'Use POMDP-based method for finding optimal policy (experimental)'
                self['balloon'].bind(button,msg)
        # Counter for belief depth
        frame = Frame(self.interior())
        Label(frame,text='Belief depth:').grid(row=0,column=0,sticky='ws')
        widget = self.createcomponent('depth',(),None,Scale,(frame,),
                                      orient='horizontal',command=self.getDepth,
                                      to=self.entity.policy.getDepth())
        widget.grid(row=0,column=1,padx=5,pady=5,sticky='w')
        if self['balloon']:
            msg = 'The number of levels of recursive beliefs that this agent '\
                'will maintain of others'
            self['balloon'].bind(widget,msg)
        button = makeButton(frame,self.images,'plus',self.extendDepth,'+')
        button.grid(row=0,column=2,padx=5,pady=5)
        if self['balloon']:
            msg = 'Increase maximum belief depth for this policy.'
            self['balloon'].bind(button,msg)
        # Counter for horizon
        Label(frame,text='Horizon:').grid(row=1,column=0,sticky='ws')
        widget = self.createcomponent('horizon',(),None,Scale,(frame,),
                                      command=self.getHorizon,orient='horizontal',
                                      to=self.entity.policy.getHorizon())
        widget.grid(row=1,column=1,padx=5,pady=5,sticky='w')
        if self['balloon']:
            msg = 'The number of turns into the future this agent '\
                  'considers when choosing an action.'
            self['balloon'].bind(widget,msg)
        button = makeButton(frame,self.images,'plus',self.extendHorizon,'+')
        button.grid(row=1,column=2,padx=5,pady=5)
        if self['balloon']:
            msg = 'Increase maximum horizon for the policy at this belief depth.'
            self['balloon'].bind(button,msg)
        frame.grid(row=1,column=0,sticky='w')
        # Box for displaying policy
        widget = self.createcomponent('Policy',(),None,MultiListbox,
                                      (self.interior(),
                                       [('Action',16)]),
                                      rowselectcommand=self.clickRow,
                                      colselectcommand=self.clickCol,
                                      doublecommand=self.double,
                                      )
        widget.grid(row=2,column=0,columnspan=3,sticky='snew')
        self.interior().columnconfigure(0,weight=1)
        self.interior().rowconfigure(2,weight=1)
        self.createcomponent('order',(),None,Pmw.SelectionDialog,
                             (self.interior(),),
                             defaultbutton='Cancel',buttons=('OK','Cancel'),
                             title='Policy of %s' % (self.entity.ancestry()),
                             scrolledlist_labelpos='n',
                             scrolledlist_label_text='Click to change RHS action',
                             listbox_font=('Courier',12),
                             command=self.selectRHS).withdraw()
##        self.component('order_dialogchildsite').grid_columnconfigure(1,weight=1)
##       self.component('order_scrolledlist').grid(column=1,row=1,sticky='ew')
##        self.createcomponent('order',(),None,TurnDialog,
##                             (self.interior(),),
##                             serial=True,editor_editable=True,
##                             title='Policy of %s' % (self.entity.ancestry()),
##                             command=self.setOrder).withdraw()
        self.initialiseoptions()
        if len(self.entity.policy.tables) > 0:
            self.component('depth').set(self.entity.policy.getDepth())
            self.component('horizon').set(self.entity.policy.getHorizon())
            self.displayPolicy()

    def setExpert(self):
        pass

    def getOptions(self):
        if self['actions']:
            options = self['actions'].getActions()
        else:
            options = self.entity.actions.getOptions()
        if len(options) == 0:
            tkMessageBox.showerror('Agent Action Error','The agent has no allowable actions!  Please go to the Action pane and select at least one possible choice.')
        return options
    
    def generateLHS(self,event=None):
        if isinstance(self['society'],GenericSociety):
            society = self['society']
        else:
            society = self.entity.hierarchy
        # Find set of entities to work with
        root = self.entity
        while len(root.entities) == 0:
            root = self.entity.parent
        entities = root.getEntityBeliefs()
        state = root.entities.state.expectation()
        # Find set of possible actions
        options = []
        for entity in entities:
            options += entity.actions.getOptions()
        # Search dynamics across generic society to find all threshold branches
        thresholds = {}
        for feature in filter(lambda k: isinstance(k,StateKey),state.keys()):
            for actor in entities:
                for option in actor.actions.getOptions():
                    assert len(option) == 1,'Currently unable to generate LHS for concurrent actions'
                    dynamics = root.getEntity(feature['entity']).getDynamics(option[0],feature['feature'])
                    if dynamics:
                        for branch in dynamics.getTree().branches().values():
                            for key in filter(lambda k: abs(branch.weights[k]) > 1e-8,branch.weights.keys()):
                                if not thresholds.has_key(key):
                                    thresholds[key] = []
                                if not branch.threshold in thresholds[key]:
                                    thresholds[key].append(branch.threshold)
        if thresholds:
            # Create attributes
            attributes = []
            keys = thresholds.keys()
            keys.sort()
            state = self.entity.state.expectation()
            for key in keys:
                values = thresholds[key]
                values.sort()
                weights = ThresholdRow(keys=[key])
                weights.fill(state.keys())
                # Update beliefs about others' policies, too
                entities = [self.entity]
                while len(entities) > 0:
                    entity = entities.pop()
                    entities += entity.entities.activeMembers()
                    policy = self.getTable(entity)
                    index = policy.addAttribute(weights,values[0])
                    policy.attributes[index] = (weights,values[:])
                    if entity.attributes.has_key('window'):
                        widget = entity.attributes['window'].component('Policy')
                        if not widget.lists.has_key(widget.makeHeading(weights)):
                            widget.addList(index,weights)
            # Initialize rules and update display
            entities = [self.entity]
            while len(entities) > 0:
                entity = entities.pop()
                entities += entity.entities.activeMembers()
                self.getTable(entity).initialize(True)
                if entity.attributes.has_key('window'):
                    widget = entity.attributes['window'].component('Policy')
                    widget.displayPolicy()
            
    def policyIteration(self,event=None):
        if self['command']:
            self['command'](self.entity,int(self.component('depth').get()),
                            int(self.component('horizon').get()),
                            self.getOptions())

    def prune(self,event=None):
        depth = int(self.component('depth').get())
        horizon = int(self.component('horizon').get())
        policy = self.entity.policy.tables[depth][horizon]
        policy.prune(rulesOnly=True)
        self.displayPolicy(policy)

    def getTable(self,entity=None):
        if entity is None:
            entity = self.entity
        depth = int(self.component('depth').get())
        horizon = int(self.component('horizon').get())
        while len(entity.policy.tables) <= depth:
            entity.policy.tables.append([])
        while len(entity.policy.tables[depth]) <= horizon:
            entity.policy.tables[depth].append(PWLTable())
        return entity.policy.tables[depth][horizon]
        
    def displayPolicy(self,policy=None):
        try:
            self.component('Policy').delete(0,'end')
        except KeyError:
            # Haven't drawn policy display widget yet, so nothing to do
            return
        if policy is None:
            policy = self.getTable()
            if policy is None:
                return
        columns = self.lists.keys()
        for index in range(len(policy.attributes)-1,-1,-1):
            obj,values = policy.attributes[index]
            if not self.addList(index,obj):
                columns.remove(self.makeHeading(obj))
        # Remove unused columns
        for heading in columns:
            self.component('Policy').delList(heading)
            del self.lists[heading]
        for rule in policy.rules:
            entry = []
            for attr in range(len(policy.attributes)):
                obj,values = policy.attributes[attr]
                if rule['lhs'][attr] is None:
                    entry.append('*')
                elif isinstance(obj,KeyedVector):
                    if len(values) == 1 and abs(values[0]) < 1e-8:
                        # Binary test
                        if rule['lhs'][attr]:
                            entry.append('T')
                        else:
                            entry.append('F')
                    else:
                        # Multiple regions
                        if rule['lhs'][attr] < len(values):
                            entry.append('< %5.3f' % (values[rule['lhs'][attr]]))
                        else:
                            entry.append('>=%5.3f' % (values[-1]))
                else:
                    entry.append(str(values[rule['lhs'][attr]]))
            # Add the RHS
            if rule['rhs'] is None:
                label = '???'
            else:
                label = ','.join(map(str,rule['rhs']))
            entry.append(label)
            # Add entry to listboxes
            self.component('Policy').insert('end',tuple(entry))

    def getDepth(self,depth=None):
        if depth is None:
            depth = self.component('depth').get()
        depth = int(depth)
        self.component('horizon').configure(to=self.entity.policy.getHorizon(depth))
        self.displayPolicy()
        return depth

    def getHorizon(self,horizon=None):
        if horizon is None:
            horizon = self.component('horizon').get()
        horizon = int(horizon)
        self.entity.horizon = horizon
        self.entity.policy.horizon = horizon
        self.displayPolicy()
        return horizon

    def extendDepth(self,event=None):
        self.entity.policy.tables.append([PWLTable()])
        self.component('depth').configure(to=self.entity.policy.getDepth())
        self.component('depth').set(len(self.entity.policy.tables)-1)

    def extendHorizon(self,event=None):
        depth = int(self.component('depth').get())
        self.entity.policy.tables[depth].append(PWLTable())
        self.component('horizon').configure(to=self.entity.policy.getHorizon(depth))
        self.component('horizon').set(len(self.entity.policy.tables[depth])-1)

    def newAttribute(self,event=None):
        """Activates dialog for adding a new attribute
        """
        try:
            dialog = self.component('attribute')
        except KeyError:
            dialog = self.createcomponent('attribute',(),None,AttributeDialog,
                                          (self.interior(),self.entity),
                                          title='New Policy Attribute',
                                          command=self.addAttribute,
                                          buttons=('OK','Cancel'),
                                          defaultbutton='OK')
        dialog.activate()

    def addAttribute(self,button):
        """Callback for finishing with new attribute dialog
        """
        if button == 'OK':
            plane = self.component('attribute')['plane']
            keyList = self.entity.state.domain()[0].keys()
            keyList.sort()
            plane.weights.fill(keyList)
            # Update beliefs about others' policies, too
            entities = [self.entity]
            while len(entities) > 0:
                entity = entities.pop()
                entities += entity.entities.activeMembers()
                policy = self.getTable(entity)
                index = policy.addAttribute(plane.weights,plane.threshold)
                policy.initialize(False)
                if entity.attributes.has_key('window'):
                    widget = entity.attributes['window'].component('Policy')
                    if not widget.lists.has_key(widget.makeHeading(plane.weights)):
                        # New column
                        widget.addList(index,plane.weights)
                    widget.displayPolicy()
        self.component('attribute').deactivate()

    def delAttribute(self,event=None):
        """Removes the selected attribute from the LHS
        """
        if self.selected is None:
            tkMessageBox.showerror('No column selected','First select a column to delete.')
            return
        policy = self.getTable()
        for index in range(len(policy.attributes)):
            obj,values = policy.attributes[index]
            if obj.simpleText() == self.selected:
                break
        else:
            raise NameError,'Trying to delete unknown attribute: %s' % \
                  (self.selected)
        # Remove attribute in this policy and in beliefs about others' policies
        self.selected = None
        entities = [self.entity]
        while len(entities) > 0:
            entity = entities.pop()
            entities += entity.entities.activeMembers()
            policy = self.getTable(entity)
            try:
                policy.delAttribute(index)
            except IndexError:
                pass
            if entity.attributes.has_key('window'):
                # Update policy display
                widget = entity.attributes['window'].component('Policy')
                widget.displayPolicy()
    
    def addList(self,index,attr):
        """
        @return: C{True} iff a new column has been added; otherwise, C{False}
        @rtype: bool
        """
        widget = self.component('Policy')
        msg = self.makeHeading(attr)
        if self.lists.has_key(msg):
            return False
        else:
            try:
                next = self.makeHeading(self.getTable().attributes[index+1][0])
            except IndexError:
                next = 'Action'
            widget.addList(msg,16,next)
            self.lists[msg] = index
            if self['balloon']:
                self['balloon'].bind(widget.component('label %s' % (msg)),msg)
            return True
                
    def clickRow(self,row):
        self.selected = None

    def clickCol(self,col):
        self.selected = col

    def double(self,row,event=None):
        root = self.entity
        while root.parent:
            root = root.parent
        window = root.attributes['window']
        depth = int(self.component('depth').get())
        horizon = int(self.component('horizon').get())
        table = self.getTable()
        items = []
        values = table.rules[row]['values']
        if not values:
            # Initialize RHS value table
            for option in self.getOptions():
                values[self.entity.makeActionKey(option)] = 0.
        options = values.keys()
        options.sort(lambda x,y: -cmp(values[x],values[y]))
        select = None
        for option in options:
            V = values[option]
            if isinstance(V,float):
                Vstr = '%5.2f' % (V)
            else:
                Vstr = '\n'+','.join(map(lambda v: '%5.2f' % (v),V.getArray()))
            msg = '%32s: %s\n' % (option[:32].ljust(32),Vstr)
            if table.rules[row].has_key('rhs'):
                if self.entity.makeActionKey(table.rules[row]['rhs']) == option:
                    select = msg
            items.append(msg)
        listbox = self.component('order_scrolledlist')
        listbox.setlist(items)
        if select:
            listbox.setvalue(select)
        self.component('order').activate()

    def open(self,event=None):
        if isinstance(self.entity,PWLAgent):
            state = self.beliefs
        else:
            state = self.entity.entities.getState()
        policy = self.getTable()
        row = policy.index(state.expectation(),{})
        self.component('Policy').selection_set(row)
        self.double(row)

    def selectRHS(self,button):
        dialog = self.component('order')
        if button == 'OK':
            selection = dialog.component('scrolledlist').getvalue()[0]
            for option in self.getOptions():
                if self.entity.makeActionKey(option) == selection[:32].strip():
                    assert len(self.component('Policy').curselection()) == 1
                    row = int(self.component('Policy').curselection()[0])
                    self.getTable().rules[row]['rhs'] = option
                    self.displayPolicy()
                    break
        dialog.deactivate()

    def setOrder(self,button):
        dialog = self.component('order')
        if button == 'OK':
            for row in self.component('Policy').curselection():
                order = dialog.cget('order')
                if isinstance(order[0],str):
                    # Probably shouldn't happen, but sometimes the RHS are str
                    for index in range(len(order)):
                        for option in self.entity.actions.getOptions():
                            if str(option) == order[index]:
                                break
                        else:
                            raise NameError,'Unknown action: %s' % (order[index])
                        order[index] = option
                if int(row) < len(self.entity.policy.values):
                    order = map(lambda l:l[:l.rfind('(')-1],order)
                    rhs = self.entity.policy.rules[int(row)]
                    for option in rhs:
                        rhs[order.index(str(option))] = option
                else:
                    self.entity.policy.rules[int(row)] = order[:]
            self.displayPolicy()
            self.component('Policy').selection_set(row)
        dialog.deactivate()
        
    def seed(self,event=None):
        """Randomly rearranges the right-hand sides of all of the rules
        """
        choices = self.getOptions()
        policy = self.getTable()
        policy.expandRules()
        for rule in policy.rules:
            if not rule['values']:
                for option in choices:
                    rule['values'][self.entity.makeActionKey(option)] = 0.
            if len(rule['values']) > 1:
                options = filter(lambda o: rule['values'].has_key(self.entity.makeActionKey(o)),choices)
                rule['rhs'] = random.choice(options)
            else:
                rule['rhs'] = []
        self.displayPolicy()
            
    def unpost(self,event):
        event.widget.unpost()

    def makeHeading(self,vector):
        """
        @return: a column heading for the corresponding LHS attribute
        @rtype: str
        """
        return vector.simpleText()
##        return ','.join(map(lambda e: '%5.3f' % (e),vector.getArray()))

    def solve(self,event=None):
        if self['options'] is None:
            cmd = ''
            change = False
        else:
            cmd = self['options'].get('POMDP','solver')
            change = False
        ok = False
        while not ok:
            try:
                os.stat(cmd)
                ok = True
            except OSError:
                msg = 'POMDP Solver'
                cmd = tkFileDialog.askopenfilename(title=msg)
                if cmd:
                    if self['options']:
                        change = True
                else:
                    # Pressed Cancel
                    return
        if change:
            # Update options file
            self['options'].set('POMDP','solver',cmd)
            f = open(self['options'].get('General','config'),'w')
            self['options'].write(f)
            f.close()
        self['command'](self.entity,self.getDepth(),self.getHorizon(),pomdp=True)
