import copy
from Tkinter import Frame,Label,Button,Checkbutton,IntVar
import Pmw
import tkMessageBox
from teamwork.math.Keys import LinkKey
from teamwork.math.probability import Distribution
from teamwork.widgets.pmfScale import PMFScale
from DynamicsDialog import DynamicsDialog
from teamwork.widgets.images import loadImages,makeButton

class RelationFrame(Pmw.ScrolledFrame):
    """Widget for the display and editing of inter-agent relationships
    """
    def __init__(self,parent=None,**kw):
        optiondefs = (
            ('entity',  None,  Pmw.INITOPT),
            ('society', {},    None),
            ('balloon', None,  Pmw.INITOPT),
            ('expert',  False, self.setExpert),
            ('generic', False, Pmw.INITOPT),
            ('network', None,  None),
            ('options',None,None),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.ScrolledFrame.__init__(self,parent)
        self.images = loadImages({'new': 'icons/chain--plus.gif',
                                  'del': 'icons/chain--minus.gif',
                                  'tree': 'icons/application-tree.gif'},
                                 self['options'].get('Appearance','PIL') == 'yes')
        toolbar = Frame(self.interior(),bd=2,relief='raised')
        toolbar.grid(row=0,column=0,sticky='ew')
        if self['generic']:
            # Button for adding new state feature
            button = makeButton(toolbar,self.images,'new',
                                self.addRelation,'+')
            button.pack(side='left',ipadx=5)
            if self['balloon']:
                self['balloon'].bind(button,'Create new relationship type')
            # Button for deleting state feature
            button = makeButton(toolbar,self.images,'del',self.delete,'-')
            button.pack(side='left',ipadx=5)
            if self['balloon']:
                self['balloon'].bind(button,'Delete relationship type')
        # Button for viewing dynamics
        button = makeButton(toolbar,self.images,'tree',self.dynamics,
                            'Dynamics')
        button.pack(side='left',ipadx=5)
        if self['balloon']:
            self['balloon'].bind(button,'View dynamics of selected relationship')
        # Pages of relationships
        book = self.createcomponent('Relationship Book',(),None,
                                    Pmw.NoteBook,(self.interior(),))
        if self['generic']:
            book.configure(raisecommand=self.selectPage)
        self.links = self['entity'].getLinkTypes()
        if not self['entity']._supportFeature in self.links:
            self.links.append(self['entity']._supportFeature)
        if not self['entity']._trustFeature in self.links:
            self.links.append(self['entity']._trustFeature)
        self.links.sort(lambda x,y:cmp(x.lower(),y.lower()))
        for relation in self.links:
            self.addDynamic(relation)
        for relation in self['entity'].relationships.keys():
            self.addStatic(relation)
        book.grid(row=1,column=0,columnspan=3,sticky='wens',padx=10,pady=10)
        self.interior().grid_columnconfigure(0,weight=1)
        self.interior().grid_rowconfigure(1,weight=1)
        self.initialiseoptions()

    def addRelation(self,confirm=None):
        try:
            dialog = self.component('newdialog')
        except KeyError:
            dialog = self.createcomponent('newdialog',(),None,
                                          Pmw.PromptDialog,
                                          (self.interior(),),
                                          title='New Relationship Type',
                                          entryfield_labelpos = 'n',
                                          label_text='Relationship:',
                                          command=self.addRelation,
                                          defaultbutton=0,
                                          buttons=('OK','Cancel'))
            frame = dialog.component('dialogchildsite')
            self.dynamicVar = IntVar()
            dialog.createcomponent('dynamic',(),None,Checkbutton,(frame,),
                                   text='Dynamic',variable=self.dynamicVar)
            dialog.component('dynamic').pack()
        if isinstance(confirm,str):
            dialog.deactivate()
            if confirm == 'OK':
                name = dialog.get()
                # Check whether new relationship is legal
                if len(name) == 0:
                    tkMessageBox.showerror('Empty Relationship',
                                           'No name entered!')
                elif name in self['entity'].getLinkTypes() or \
                        self['entity'].relationships.has_key(name):
                    tkMessageBox.showwarning('Duplicate Relationship','This agent already has a relationship named "%s"' % (name))
                elif self.dynamicVar.get():
                    # Create new dynamic link
                    self['entity'].linkTypes.append(name)
                    self['entity'].linkDynamics[name] = {}
                    self.addDynamic(name)
                    self.component('Relationship Book').selectpage(name)
                else:
                    # Create new static relationship
                    self['entity'].relationships[name] = []
                    self.addStatic(name)
                    self.component('Relationship Book').selectpage(name)
        else:
            dialog.activate(geometry = 'centerscreenalways')
        
    def setExpert(self):
        pass

    def addDynamic(self,relation,index=Pmw.END):
        """Adds a page for a dynamic relationship"""
        book = self.component('Relationship Book')
        try:
            page = book.page(relation)
        except ValueError:
            page = book.insert(relation,index)
        if self['generic'] and not 'new %s' % (relation) in self.components():
            # Button for adding relationship
            g = Pmw.Group(page,tag_text='New Link')
            palette = Pmw.Color.getdefaultpalette(self.component('hull'))
            b = self.createcomponent('new %s' % (relation),(),None,
                                     Pmw.ComboBox,(g.interior(),),
                                     labelpos='n',label_text='Add link to:',
                                     autoclear=True,history=True,unique=True,
                                     entry_state='disabled',
                                     entry_disabledforeground=palette['foreground'],
                                     entry_disabledbackground=palette['background'],
                                     )
            b.component('popup').bind('<Map>',lambda event,s=self,r=relation:
                                          s.newLinkOptions(r))
            b.pack(side='left')
            Button(g.interior(),command=lambda s=self,r=relation:
                       s.addLinkee(r),text='Add').pack(side='left')
            g.pack(side='top',fill='x',expand='yes')
        try:
            frame = self.component('%s frame' % (relation))
        except KeyError:
            frame = self.createcomponent('%s frame' % (relation),(),None,
                                         Pmw.ScrolledFrame,(page,),
                                         vertflex='expand',horizflex='expand')
            frame.interior().columnconfigure(1,weight=1)
            frame.pack(side='top',fill='both',expand='yes')
        linkees = self['entity'].getLinkees(relation)
        linkees.sort(lambda x,y:cmp(x.lower(),y.lower()))
        # Let's figure out what we already have
        widgetList = filter(lambda w:self.componentgroup(w) == relation,
                            self.components())
        leftover = linkees[:]
        for name in linkees:
            key = self['entity'].getLinkKey(relation,name)
            try:
                widgetList.remove(str(key))
                leftover.remove(name)
            except ValueError:
                pass
        # Leftover widgets are no longer relevant
        for name in widgetList:
            self.destroycomponent(name)
        # Leftover names have no widgets
        last = None
        for name in leftover:
            key = self['entity'].getLinkKey(relation,name)
            try:
                widget = self.component(str(key))
                if last:
                    widget.pack(after=last,side='top',fill='x')
                else:
                    widget.pack(side='top',fill='x')
            except KeyError:
                widget = self.addScale(name,relation)
            last = widget
        self.component('Relationship Book').setnaturalsize()

    def selectPage(self,relation):
        pass
#         if relation in self['entity'].getLinkTypes() and \
#                 relation != self['entity']._supportFeature and \
#                 relation != self['entity']._trustFeature:
#             # Edit dynamics only if dynamic but not built-in
#             self.component('edit').configure(state='normal')
#         else:
#             self.component('edit').configure(state='disabled')

    def dynamics(self):
        # Create the dynamics dialog
        relation = self.component('Relationship Book').getcurselection()
        dynamics = self['entity'].linkDynamics[relation]
        roles = ['actor','object','self']
        roles += self['entity'].relationships.keys()
        roles.sort(lambda x,y:cmp(x.lower(),y.lower()))
        for entity in self['entity'].getEntityBeliefs():
            for newRole in entity.relationships.keys():
                if not newRole in roles:
                    roles.append(newRole)
        self.createcomponent('dialog',(),None,DynamicsDialog,
                             (self.interior(),),expert=self['expert'],
                             buttons=('OK','Cancel'),
                             defaultbutton='OK',
                             title='Dynamics of %s of %s' % \
                             (relation,self['entity'].name),
                             feature=relation,editor_roles=roles,
                             key=LinkKey({'subject':'self',
                                          'verb':relation,
                                          'object':'actor'}),
                             society=self['entity'].hierarchy,
                             dynamics=copy.deepcopy(dynamics),
                             command=self.changeDynamics,
                             usePIL=self['options'].get('Appearance','PIL') == 'yes',
                             ).activate()

    def changeDynamics(self,button):
        """Upon clicking OK in dynamics dialog, change entity's dynamics accordingly
        @param button: the button pressed to close the dialog (generated by Tk callback)
        @type button: str
        """
        dialog = self.component('dialog')
        if button == 'OK':
            dynamics = self['entity'].linkDynamics[dialog['feature']]
            dynamics.clear()
            dynamics.update(dialog['dynamics'])
        dialog.deactivate()
        self.destroycomponent('dialog')

    def newLinkOptions(self,relation):
        names = filter(lambda n: not n in self['entity'].getLinkees(relation),
                       self['entity'].hierarchy.keys())
        widget = self.component('new %s' % (relation))
        names.sort(lambda x,y:cmp(x.lower(),y.lower()))
        widget.component('scrolledlist').setlist(names)

    def addLinkee(self,relation):
        """Add a new dynamic relationship between this entity and the currently selected one in the new link widget
        """
        widget = self.component('new %s' % (relation))
        name = widget.get()
        if name:
            widget.clear()
            self['entity'].setLink(relation,name,0.)
            self.addScale(name,relation)
            if self['network']:
                self['network'].setview()
        else:
            tkMessageBox.showerror('Missing Agent','You have not selected an agent to link to.')
        
    def addScale(self,name,relation):
        value = self['entity'].getLink(relation,name)
        distribution = Distribution({value:1.})
        key = self['entity'].getLinkKey(relation,name)
        page = self.component('%s frame' % (relation)).interior()
        widget = self.createcomponent(str(key),(),relation,
                                      PMFScale,(page,),
                                      distribution=distribution,
                                      usePIL=self['options'].get('Appearance','PIL') == 'yes',
                                      )
        widget.configure(command=self.updateLink)
        # Insert scale into correct slot
        widgetList = filter(lambda w:self.componentgroup(w) == relation,
                            self.components())
        widgetList.sort()
        index = widgetList.index(str(key))
        Label(page,text=name,justify='left').grid(row=index+1,column=0,
                                                  sticky='ewns')
        widget.grid(row=index+1,column=1,sticky='ew')
        return widget
    
    def update(self):
        for relation in self['entity'].getLinkTypes():
            for name in self['entity'].getLinkees(relation):
                key = self['entity'].getLinkKey(relation,name)
                value = self['entity'].getLink(relation,name)
                self.component(str(key))['distribution'] = Distribution({value:1.})
                
    def updateLink(self,widget):
        for name in self.components():
            if widget is self.component(name):
                break
        for relation in self['entity'].getLinkTypes():
            for other in self['entity'].getLinkees(relation):
                key = self['entity'].getLinkKey(relation,other)
                if str(key) == name:
                    break
        self['entity'].setLink(relation,other,widget['distribution'])
        if self['network']:
            self['network'].redrawSupport()

    def addStaticFiller(self,agent):
        """Adds a new button to all of the static relationship selection panes
        @type agent: str
        """
        for name in filter(lambda n:self.componentgroup(n) == 'static',
                           self.components()):
            widget = self.component(name)
            widget.add(agent)
            # Assume we are in generic society viewing
            choices = self['entity'].hierarchy.keys()
            choices.sort(lambda x,y: cmp(x.lower(),y.lower()))
            widget.component(agent).grid(row=choices.index(agent))

    def removeFiller(self,agent):
        """Removes appropriate fillers from all relationship panes
        @type agent: str
        """
        for name in filter(lambda n:self.componentgroup(n) == 'static',
                           self.components()):
            widget = self.component(name)
            widget.destroycomponent(agent)
            if agent in self['entity'].relationships[name]:
                self['entity'].relationships[name].remove(agent)
        for relation in self['entity'].getLinkTypes():
            # Check dynamics relationships
            if agent in self['entity'].getLinkees(relation):
                key = self['entity'].getLinkKey(relation,agent)
                self.destroycomponent(str(key))
                self['entity'].removeLink(relation,agent)
            
    def addStatic(self,relation):
        book = self.component('Relationship Book')
        page = book.add(relation)
        if self['generic']:
            choices = self['entity'].hierarchy.keys()
        else:
            try:
                choices = self['entity'].entities.keys()
            except AttributeError:
                # Hacky way of detecting lightweight agent
                choices = self['entity'].relationships[relation][:]
        frame = Pmw.ScrolledFrame(page)
        menu = self.createcomponent(relation, (), 'static',
                                    Pmw.RadioSelect,
                                    (frame.interior(),),
                                    buttontype='checkbutton',
                                    orient='vertical',
                                    selectmode='multiple',
                                    )
        # Add relevant object entities
        choices.sort()
        # For now, we don't allow changing relationships on instantiated agents
        if self['generic']:
            menu.configure(command=self.selectRelatee)
            activity = 'normal'
        else:
            activity = 'disabled'
        map(lambda n:menu.add(n),choices)
        menu.setvalue(self['entity'].relationships[relation][:])
        map(lambda n:menu.component(n).configure(state=activity),choices)
        menu.pack(side='left',fill='both',expand='yes')
        frame.pack(side='top',fill='both',expand='yes')

    def selectRelatee(self,name,value):
        relation = self.component('Relationship Book').getcurselection()
        if value:
            if name in self['entity'].relationships[relation]:
                # This should never happen...
                raise NameError,'Adding duplicate relationship %s to %s' % \
                      (relation,name)
            else:
                self['entity'].relationships[relation].append(name)
        else:
            self['entity'].relationships[relation].remove(name)

    def delete(self,event=None):
        """Deletes the selected relationship"""
        relation = self.component('Relationship Book').getcurselection()
        result = tkMessageBox.askyesno('Confirm Delete','Are you sure you wish to delete this relationship?')
        if result:
            if self['entity'].relationships.has_key(relation):
                # Static relationship
                self.destroycomponent(relation)
                del self['entity'].relationships[relation]
            else:
                # Dynamic relationship
                del self['entity'].linkDynamics[relation]
                self['entity'].linkTypes.remove(relation)
                self.destroycomponent('%s frame' % (relation))
            self.component('Relationship Book').delete(relation)

    def renameEntity(self,old,new):
        for relation,fillers in self['entity'].relationships.items():
            # Check static relationships
            if new in fillers:
                menu = self.component(relation)
                # RadioSelect doesn't provide individual deletion!
                # The following is adapted from source of deletall()
                menu.destroycomponent(old)
                menu._buttonList.remove(old)
                try:
                    menu.selection.remove(old)
                except ValueError:
                    # Wasn't selected
                    pass
                menu.add(new)
                menu.setvalue(fillers[:])
        for relation in self['entity'].getLinkTypes():
            # Check dynamics relationships
            if new in self['entity'].getLinkees(relation):
                key = self['entity'].getLinkKey(relation,old)
                self.destroycomponent(str(key))
                self.addScale(new,relation)
