import Pmw
from Queue import Queue,Empty
from threading import Thread
from time import strftime,localtime
from Tkinter import IntVar,StringVar,Label,Frame,Button,PhotoImage,Checkbutton
from tkFileDialog import askopenfilename

from teamwork.agent.Entities import PsychEntity
from teamwork.widgets.ProgressBar import ProgressBar
from teamwork.widgets.images import getImageDirectory,getImage
from objectives import ObjectivesDialog
    
class ScenarioWizard(Pmw.Dialog):
    """Setup wizard dialog widget"""
    frameWidth      = 700
    frameHeight     = 600
    
    def __init__(self, parent=None, **kw):
        optiondefs = (
            ('doActions',False,Pmw.INITOPT),
            ('doObjectives',False,Pmw.INITOPT),
            ('society',{},Pmw.INITOPT),
            ('leavesOnly',False,Pmw.INITOPT),
            ('balloon',None,Pmw.INITOPT),
            ('expert',False,Pmw.INITOPT),
            ('finish',None,None),
            ('command',self.press,None),
            ('agentClass',PsychEntity,None),
            ('scenario',None,Pmw.INITOPT),
            ('beta',False,Pmw.INITOPT),
            )
        self.defineoptions(kw, optiondefs)
        self.scenario = None
        if len(self['society']) == 1:
            # If there's only one thing, then we'd better show it
            self.leaves = self['society'].keys()
        elif self['leavesOnly']:
            # Show only leaf classes
            self.leaves = self['society'].leaves()
        else:
            # Show any non-root classes
            leaves = filter(lambda e:len(e.getParents())>0,
                            self['society'].members())
            self.leaves = map(lambda e:e.name,leaves)
        self.leaves.sort(lambda x,y:cmp(x.lower(),y.lower()))
        self.entities = {}
        self.selected = {}
        self.panes = len(self.leaves) + 2 # population, All done!
        if self['doObjectives']:
            self.panes += 1
        self.pCurrent = 0
        self.pFrame = [None] * self.panes
        try:
            self.nobody = PhotoImage(file=getImage('nobody.gif'))
        except:
            self.nobody = None
        self.toImport = False
        self.thread = None
        Pmw.Dialog.__init__(self,parent)
        self.withdraw()
        # Wizard area
        self.wizard = PhotoImage(file=getImage('wizard.gif'))
        widget = self.createcomponent('illust',(), None,Label,
                                      (self.interior(),),image=self.wizard)
        widget.grid(row=0,column=0,sticky='ns')
        self.interior().columnconfigure(0,weight=0)
        widget = self.createcomponent('dataarea',(), None,Frame,
                                      (self.interior(),), 
                                      relief='flat', bd=1)
        widget.grid(row=0,column=1,sticky='ewns')
        self.interior().columnconfigure(1,weight=1,minsize=450)
        self.interior().rowconfigure(0,weight=1,minsize=350)
##        # Separator
##        widget = self.createcomponent('separator',(), None,Frame,
##                                      (self.interior(),),
##                                      relief='sunken',bd=2, height=2)
##        widget.grid(row=1,column=0,columnspan=2,sticky='ew')
##        self.interior().rowconfigure(1,minsize=5)
        # Command area
        widget = self.createcomponent('commandframe',(), None,Frame,
                                      (self.interior(),),
                                      relief='flat', bd=1)
        widget.grid(row=2,column=0,columnspan=2,sticky='ew')
        self.interior().rowconfigure(2,minsize=20)
        # Panes
        for i in range(self.panes):
            self.createcomponent('pframe'+str(i),(), None,Frame,
                                 (self.component('dataarea'),),
                                 relief='flat', bd=1)
            self.pFrame[i] = self.component('pframe%d' % (i))
            if not i == self.pCurrent:
                self.pFrame[i].forget()
            else:
                self.pFrame[i].pack(fill='both',expand='yes')
        self.createMain()
        self.initialiseoptions(ScenarioWizard)
        self.protocol('WM_DELETE_WINDOW',self.deactivate)

    def createMain(self):
        self.createPopulation(0)
        for index in range(len(self.leaves)):
            self.createClassPane(1+index,self.leaves[index])
        self.createFinish(len(self.leaves)+1)

    def createPopulation(self,pane):
        frame = Pmw.ScrolledFrame(self.pFrame[pane],)

        self.counters = {}
        for leaf in self.leaves:
            self.counters[leaf] = self.__createCounter(frame.interior(),
                                                       leaf,0,leaf)
        Pmw.alignlabels(self.counters.values())
        frame.grid(row=0,column=0,sticky='ewns')
        self.pFrame[pane].rowconfigure(0,weight=1)
        if self['scenario']:
            widget = Button(self.pFrame[pane],command=self.editScenario,
                            text='Import Current Scenario and Edit')
            if self['balloon']:
                self['balloon'].bind(widget,'Use the current scenario\'s settings for the initial settings in this wizard.')
            widget.grid(row=1,column=0,sticky='ew')
            widget = Button(self.pFrame[pane],command=self.useScenario,
                            text='Import Current Scenario and Finish')
            if self['balloon']:
                self['balloon'].bind(widget,'Use the current scenario\'s settings without any changes.')
            widget.grid(row=2,column=0,sticky='ew')

    def createFinish(self,pane):
        # Create progress message and bar
        group = Pmw.Group(self.pFrame[pane],tag_text='Progress')
        group.grid(row=0,column=1,sticky='ewns')
        self.pFrame[pane].rowconfigure(0,weight=1)
        msg = 'All done!  Click "Finish" to instantiate scenario.'
        self.createcomponent('FinishLabel',(),None,
                             Label,(group.interior(),),
                             text=msg).pack(side='top',fill='both',expand='yes')
        self.progressBar = ProgressBar(master=group.interior(),
                                       labelText='Progress:',
                                       value=0,width=300,
                                       background=None,
                                       labelColor="black",
                                       fillColor="darkgray",
                                       )
        self.progressBar.frame.pack_forget()
        # Set up option for compiling dynamics and policies
        self.compileFlag = IntVar()
        self.compileFlag.set(1)
        self.distillFlag = IntVar()
        self.distillFlag.set(0)
        self.level = StringVar()
        group = Pmw.Group(self.pFrame[pane],tag_text='Options')
        self.createcomponent('Distill',(),None,
                             Checkbutton,(group.interior(),),
                             text='Create lightweight agents',
                             variable=self.distillFlag,
                             )
        self.createcomponent('Compile Dynamics',(),None,
                             Checkbutton,(group.interior(),),
                             text='Compile dynamics',
                             variable=self.compileFlag,
                             )
        self.createcomponent('Compile Policies',(),None,
                             Pmw.OptionMenu,(group.interior(),),
                             labelpos='w',
                             label_text='Compile policies for:',
                             menubutton_textvariable=self.level,
                             )
        if self['beta']:
            self.component('Distill').pack(side='top',fill='both',expand='yes') 
        if self['expert']:
            self.component('Compile Dynamics').pack(side='top',fill='both',
                                                    expand='yes')
        if self['beta']:
            self.component('Compile Policies').pack(side='top',fill='both',
                                                    expand='yes')
        if self['expert']:
            group.grid(row=1,column=1,sticky='ewns')
            self.pFrame[pane].rowconfigure(1,weight=1)
        self.pFrame[pane].columnconfigure(1,weight=1)

    def editScenario(self):
        """Shorthand for L{importScenario} with C{finish=False}"""
        self.importScenario(finish=False)

    def useScenario(self):
        """Shorthand for L{importScenario} with C{finish=True}"""
        self.importScenario(finish=True)

    def importScenario(self,finish=False):
        """Fills out everything using what's present in the current scenario
        @param finish: if C{True}, then jump directly to end without editing any of the current scenario's settings
        @type finish: bool
        """
        self.toImport = True
        for leaf in self.leaves:
            # Reset counters to 0 (gotta be an easier way)
            while int(self.counters[leaf].get()) > 0:
                self.counters[leaf].decrement()
            # Erase any entities already stored
            try:
                self.entities[leaf].clear()
            except KeyError:
                pass
        for entity in self['scenario'].members():
            # Find out which leaves this entity is in
            leaves = []
            for leaf in self.leaves:
                if entity.instanceof(leaf):
                    leaves.append(leaf)
            # Find out the most specific class
            for leaf in leaves[:]:
                for className in self['society'][leaf].getParents():
                    try:
                        leaves.remove(className)
                    except ValueError:
                        pass
            # There should be only one such bottom-level class
            assert len(leaves) == 1
            leaf = leaves[0]
            # Increment the counter for this entity class
            self.counters[leaf].increment()
            # Create a new entity
            new = self['society'].instantiate(leaf,entity.name,
                                              self['agentClass'])
            # Copy relationships
            for relation,others in entity.relationships.items():
                new.relationships[relation] = others[:]
            try:
                self.entities[leaf][entity.name] = new
            except KeyError:
                self.entities[leaf] = {entity.name:new}
        if finish:
            self.next(self.panes - 1)
            self.invoke('Next')
            
    def setPopulation(self):
        """Extract the number of each entity type selected from pane 0 of the wizard"""
        self.population = {}
        for leaf in self.leaves:
            # Look at the counter of each entity type
            counter = self.counters[leaf]
            count = int(counter.get())
            self.population[leaf] = count
            try:
                while len(self.entities[leaf]) > count:
                    # Too many entities...start deleting
                    key = self.entities[leaf].keys()[-1]
                    del self.entities[leaf][key]
            except KeyError:
                # Haven't created any of these entities...start from
                # scratch
                self.entities[leaf] = {}
            while len(self.entities[leaf]) < count:
                # Not enough entities...start making new ones
                
                if count > 1:
                    name = '%s %d' % (leaf,len(self.entities[leaf])+1)
                else:
                    name = '%s' % (leaf)
                newEntity = self['society'].instantiate(leaf,name,
                                                        self['agentClass'])
                self.entities[leaf][name] = newEntity
        for leaf in self.leaves:
            # Set the selection box options for this pane
            box = self.component('%sEntitySelect' % (leaf))
            nameList = self.entities[leaf].keys()
            nameList.sort()
            box.setitems(nameList)
            # Create properties (doesn't work if we haven't set the
            # population first
            book = self.component('%sNotebook' % (leaf))
            if not self.selected.has_key(leaf):
                try:
                    self.selectEntity(nameList[0],leaf,None)
                except IndexError:
                    # No entities of this type
                    pass
            self.createProps(book,leaf)
##             book.pack(fill=BOTH,expand=YES)
        if self['doObjectives']:
            # Build objectives dialog if not done already
            objPaneName = 'ObjectivesPane'
            try:
                obj = self.component(objPaneName) 
            except KeyError:
                eList = map(lambda e:e.values(),self.entities.values())
                pane = len(self.leaves)+2
                obj = self.createcomponent(objPaneName, (),None,
                                           ObjectivesDialog, 
                                           (self.pFrame[pane],),
                                           psyopFlag = 0,
                                           entities=reduce(lambda x,y:x+y,
                                                           eList,[]))
                obj.pack(side='top',fill='x',expand='yes')
        # Update compile option menu
        count = 0
        for leaf in self.leaves:
            if self.population[leaf] > 0:
                depth = self['society'][leaf].depth
                if depth > count:
                    count = depth
        self.levels = ['All agents']
        self.levels += map(lambda n:'Agents at belief depth %d and below'\
                        % (n+1),range(count))
        self.levels.append('No agents')
        self.component('Compile Policies').setitems(self.levels)
        self.component('Compile Policies').invoke(Pmw.END)
                                     
    def createClassPane(self,pane,className):
        """Create the pane for the specified index and class"""
        # Class label
        self.createcomponent('%sLabel' % (className), (), None,
                             Label,
                             (self.pFrame[pane],),
                             borderwidth=3,relief='ridge',
                             font=('helvetica',18,'bold'),
                             text=className).grid(row=0,column=0,
                                                  sticky='ew')
        cmd = lambda label,s=self,c=className:s.selectEntity(label,c)
        # Entity selection menu
        msg = 'Select which instance of %s you wish to customize:' \
              % (className)
        Label(self.pFrame[pane],text=msg).grid(row=1,column=0,sticky='ew')
        self.createcomponent('%sEntitySelect' % (className), (), None,
                             Pmw.OptionMenu,
                             (self.pFrame[pane],),
                             labelpos='w',label_text='Entity:',
                             command=cmd).grid(row=2,column=0,sticky='ew')
        # Encapsulate all of the entity-specific options
        book = self.createcomponent('%sNotebook' % (className), (), None,
                                    Pmw.NoteBook,(self.pFrame[pane],))
        # Allow user to change the name of selected entity
        book.add('Name')
        widget = self.createcomponent('%sName' % (className), (), None,
                                      Pmw.EntryField,(book.page(0),),
                                      validate={'validator':
                                                self.validateName},
                                      modifiedcommand=self.updateName,
                                      labelpos='nw',
                                      label_text='Entity name:',
                                      )
        widget.grid(row=0,column=0,sticky='EW',ipadx=5)
        # Allow user to select image
        widget = self.createcomponent('%sImage' % (className), (),None,
                                      Button,(book.page(0),),
                                      command=lambda s=self,c=className:\
                                      s.selectImage(c),
                                      width=100,height=100)
        widget.grid(row=0,column=1)
##        # Allow user to enter description
##        widget = self.createcomponent('%sDescription' % (className),
##                                      (), None, Pmw.ScrolledText,
##                                      (book.page(0),),
##                                      text_height=5,text_width=40,
##                                      text_wrap='word',
##                                      labelpos='nw',
##                                      label_text='Entity description:',
##                                      )
##        widget.grid(row=1,column=0,columnspan=2,sticky='NESW',padx=5)
        book.page(0).rowconfigure(1,weight=1)
        book.page(0).columnconfigure(0,weight=1)
        book.grid(row=3,column=0,sticky='ewns')
        self.pFrame[pane].rowconfigure(3,weight=1)
        self.pFrame[pane].columnconfigure(0,weight=1)
        
    def selectImage(self,className):
        """Pops up a dialog to allow user to select image for an entity"""
        filename = askopenfilename(#parent=self.root,
                                   initialdir = getImageDirectory())
        if filename:
            try:
                image = PhotoImage(file=filename)
            except:
                image = None
            if image:
                widget = self.component('%sImage' % (className))
                widget.configure(image=image)
                entity = self.selected[className]
                entity.attributes['image'] = image
                entity.attributes['imageName'] = filename
                
    def createProps(self,parent,className):
        """Creates all the background tabs for specializing an entity"""
        try:
            entity = self.entities[className].values()[0]
        except IndexError:
            # No entities of this class
            return
        generic = self['society'][className]
        page = 1
        if self['doActions']:
            # Add action selection pane
            if len(generic.actions.getOptions()) > 0:
                try:
                    parent.add('Actions')
                    menuLabel = '%sActions' % (className)
                except ValueError:
                    # Page already exists
                    menuLabel = None
                if menuLabel:
                    menu = self.createcomponent(menuLabel,(),None,
                                                Pmw.RadioSelect,
                                                (parent.page(page),),
                                                buttontype='checkbutton',
                                                orient='vertical',
                                                )
                    options = generic.actions.getOptions()
                    options.sort(lambda x,y:cmp(str(x),str(y)))
                    map(lambda n:menu.add(str(n)),options)
                    menu.pack(side='top',fill='both',expand='yes')
                page += 1
        # Add relationship fillers
        relationships = {}
        for cls in entity.classes:
            relationships.update(self['society'][cls].relationships)
        for relation in relationships.keys():
            try:
                parent.add(relation)
            except ValueError:
                # Page already exists
                continue
            menuLabel = '%s%sRelation' % (className,relation)
            try:
                menu = self.component(menuLabel)
            except KeyError:
                # Haven't created this menu yet...do so now
                cmd = lambda selected,value,s=self,c=className,r=relation:\
                      s.updateFiller(c,r,selected,value)
                frame = Pmw.ScrolledFrame(parent.page(page))
                menu = self.createcomponent(menuLabel, (),
                                            None, Pmw.RadioSelect,
                                            (frame.interior(),),
                                            buttontype='checkbutton',
                                            command=cmd,
                                            orient='vertical')
                frame.pack(side='top',fill='both',expand='yes')
            menu.pack(side='top',fill='both',expand='yes')
            page += 1
        self.updateRelationships(entity,className)

    def updateRelationships(self,entity,className):
        # Add relationship fillers
        relationships = {}
        for cls in entity.classes:
            relationships.update(self['society'][cls].relationships)
        for relation,objClasses in relationships.items():
            # Add all the appropriate entities to the menu
            objList = []
            for classSet in self.entities.values():
                for other in classSet.values():
                    for objClass in objClasses:
                        if other.instanceof(objClass):
                            objList.append(other)
            menuLabel = '%s%sRelation' % (className,relation)
            menu = self.component(menuLabel)
            # Add relevant object entities
            nameList = map(lambda e:e.name,objList)
            nameList = filter(lambda n: n!= entity.name,nameList)
            nameList.sort()
            # Delete any extraneous buttons
            toDelete = filter(lambda n:menu.componentgroup(n) == 'Button' \
                              and not n in nameList,menu.components())
            for name in toDelete:
                # RadioSelect doesn't provide individual deletion!
                # The following is adapted from source of deletall()
                menu.destroycomponent(name)
                menu._buttonList.remove(name)
                try:
                    menu.selection.remove(name)
                except ValueError:
                    # Wasn't selected
                    pass
            for index in range(len(nameList)):
                name = nameList[index]
                try:
                    widget = menu.component(name)
                except KeyError:
                    widget = menu.add(name)
                widget.grid(row=index)
            if not entity.relationships.has_key(relation):
                entity.relationships[relation] = []
            others = entity.relationships[relation][:]
            menu.setvalue(others)

    def validateName(self,name,**kw):
        """Validator for name entry field.
        Ensures that names are not zero length and that all names are
        unique."""
        if self.pCurrent == 0:
            return Pmw.OK
        elif len(name) > 0:
            className = self.leaves[self.pCurrent-1]
            entity = self.selected[className].name
            for className in self.leaves:
                for other in self.entities[className].keys():
                    if other != entity and name == other:
                        return Pmw.PARTIAL
            else:
                return Pmw.OK
        else:
            return Pmw.PARTIAL

    def updateName(self):
        if self.pCurrent > 0:
            className = self.leaves[self.pCurrent-1]
            entity = self.selected[className]
            self.rename(className,entity.name,
                        self.component('%sName' % (className)).getvalue())
        
    def rename(self,className,old,new):
        entity = self.entities[className][old]
        entity.setName(new)
        # Update all refs to this entity's name
        del self.entities[className][old]
        self.entities[className][entity.name] = entity
        # Update any relationships
        for otherClass in self.leaves:
            for other in self.entities[otherClass].values():
                for objList in other.relationships.values():
                    try:
                        index = objList.index(old)
                        objList[index] = entity.name
                    except ValueError:
                        pass
        # Update name in entity selector
        menu = self.component('%sEntitySelect' % (className))
        menu.component('menu').delete(0,'end')
        menu.setitems(self.entities[className].keys(),new)
        # Update relationship refs in other panes
        for otherClass in self.leaves:
            try:
                other = self.selected[otherClass]
            except KeyError:
                continue
            self.updateRelationships(other,otherClass)

    def updateFiller(self,className,relation,other,value):
        """Updates the relationships of the given entity in response to the click of a single button"""
        entity = self.selected[className]
        if not entity.relationships.has_key(relation):
            entity.relationships[relation] = []
        if value:
            assert other not in entity.relationships[relation]
            entity.relationships[relation].append(other)
        else:
            entity.relationships[relation].remove(other)
        
    def selectEntity(self,label,className,saveOld=1):
        """Change the view when a new entity is selected for viewing/editing"""
        oldName = ''
        if saveOld:
            # Save the description
            entity = self.selected[className]
            oldName = entity.name
##            widget = self.component('%sDescription' % (className))
##            entity.description = widget.get()
        if label != oldName:
            # Set the widget to display properties for new entity
            self.selected[className] =  self.entities[className][label]
            entity = self.selected[className]
            widget = self.component('%sName' % (className))
            widget.setvalue(entity.name)
##            widget = self.component('%sDescription' % (className))
##            widget.settext(entity.description)
            # Set image
            widget = self.component('%sImage' % (className))
            try:
                widget.configure(image=entity.attributes['image'])
            except KeyError:
                widget.configure(image=self.nobody)
            # Set relationship values
            if self.pCurrent > 0:
                self.updateRelationships(entity,className)
                
    def getRelationMenus(self,className):
        """Returns a dictionary of the available relationship menus"""
        result = {}
        try:
            entity = self.selected[className]
        except KeyError:
            return result
        relationships = {}
        for cls in entity.classes:
            relationships.update(self['society'][cls].relationships)
        for relation in relationships.keys():
            if relation[0] == '_':
                label = relation[1:]
            else:
                label = relation
            try:
                menu = self.component('%s%sRelation' % (className,label))
            except KeyError:
                # No menu for this relationship, and that's OK
                continue
            result[relation] = menu
        return result
        
    def saveProps(self):
        """Applies any changes made to the currently selected entity"""
        className = self.leaves[self.pCurrent-1]
        entity = self.selected[className]
        self.selectEntity(entity.name,className)

    def press(self,button):
        if button == 'Next':
            self.next()
        elif button == 'Prev':
            self.prev()
        elif button == 'Cancel':
            self.deactivate(button)
        else:
            self.finish()
            
    def next(self,new=None):
        """Moves the wizard forward to the next applicable pane"""
        if self.pCurrent == 0:
            self.setPopulation()
        elif self.isClassPane():
            # Save results before moving on
            self.saveProps()
        done = None
        cpane = self.pCurrent
        while not done:
            if new is None:
                self.pCurrent = self.pCurrent + 1
            else:
                self.pCurrent = new
            self.component('buttonbox_Prev').configure(state='normal')
            if self.pCurrent == self.panes - 1:
                self.component('buttonbox_Next').configure(text='Finish',command=self.finish)
            if self.isClassPane():
                className = self.leaves[self.pCurrent-1]
                self.component('%sName_entry' % (className)).focus_set()
            done = self.legalPane()
        self.pFrame[cpane].forget()
        self.pFrame[self.pCurrent].pack(fill='both',expand='yes')
       
    def prev(self):
        """Moves the wizard backward to the next applicable pane"""
        if self.isClassPane():
            # Save results before moving on
            self.saveProps()
        done = None
        cpane = self.pCurrent
        while not done:
            self.pCurrent = self.pCurrent - 1
            if self.pCurrent <= 0:
                self.pCurrent = 0 
                self.component('buttonbox_Prev').configure(state='disabled')
            if cpane == self.panes - 1:
                self.component('buttonbox_Next').configure(text='Next',
                                                           command=self.next)
            done = self.legalPane()
        self.pFrame[cpane].forget()
        self.pFrame[self.pCurrent].pack(fill='both',expand='yes')

    def isClassPane(self,pane=-1):
        """
        @return: C{True} iff the pane (defaults to current) is an entity pane"""
        if pane < 0:
            pane = self.pCurrent
        if pane == 0:
            return False
        elif pane > len(self.leaves):
            return False
        else:
            return True
        
    def legalPane(self,pane=-1):
        """@return: C{true} iff the pane (defaults to current) is legal,
        given the current population breakdown"""
        if pane < 0:
            pane = self.pCurrent
        if self.isClassPane(pane):
            return len(self.entities[self.leaves[pane-1]]) > 0
        else:
            return 1

    def validateCount(self,count,className):
        result = Pmw.integervalidator(count)
        if result == Pmw.OK:
            count = int(count)
            if count < 0:
                return Pmw.ERROR
            total = 0
            for other in self.leaves:
                if other == className:
                    total += count
                else:
                    try:
                        counter = self.component('Counter%s' % (other))
                        total += int(counter.getvalue())
                    except KeyError:
                        pass
            if total < 1:
                self.component('buttonbox_Next').configure(state='disabled')
                return Pmw.OK
##                return Pmw.PARTIAL
            else:
                self.component('buttonbox_Next').configure(state='normal')
                return Pmw.OK
        else:
            return result
        
    def __createCounter( self, master, labelText, initialValue,
                        className ):
        """Creates a counter widget for changing the population"""
##        validator = lambda value,s=self,n=className:s.validateCount(value,n)
        validator = { 'validator':'integer','min':0, 'max':9 }
        counter = self.createcomponent('Counter%s' % labelText, (), None,
                                       Pmw.Counter,(master,),
                                       padx=8, pady=0,
                                       labelpos = 'w',
                                       label_text = labelText,
                                       entry_width = 3, #Screws Layout
                                       entryfield_validate = validator,
                                       entryfield_value = initialValue )
        # Identify source of this model
        if className and self['balloon']:
            str = ''
            try:
                source = self['society'][className]['source']
            except KeyError:
                source = None
            if source:
                str += 'Created by ' + source['who'] + '\n'
                str += strftime('%x %X',localtime(source['when']))
            try:
                sourceList = self['society'][className]['validated']
            except KeyError:
                sourceList = []
            for source in sourceList:
                str += '\nValidated by ' + source['who'] + '\n'
                str += strftime('%x %X',localtime(source['when']))
            if len(str) > 0:
                self['balloon'].bind(counter,str)
                
        counter.pack( side='top', padx=8)
        return counter
            
    def finish(self):
        self.component('FinishLabel').configure(text='Initializing...')
        self.component('buttonbox_Prev').configure(state='disabled')
        self.component('buttonbox_Next').configure(state='disabled')
        self.component('buttonbox_Cancel').configure(state='disabled')
        self.component('Compile Dynamics').configure(state='disabled')
        self.component('Compile Policies').configure(menubutton_state='disabled')
        self.progressBar.frame.pack(side='top')
        self.progress = Queue()
        if self['command']:
            args = {'level': self.levels.index(self.level.get())}
            eList = map(lambda e:e.values(),self.entities.values())
            args['entities'] = reduce(lambda x,y:x+y,eList,[])
            if self.distillFlag.get():
                args['distill'] = True
            else:
                args['distill'] = False
            if self.compileFlag.get():
                args['compile'] = True
            else:
                args['compile'] = False
            self.thread = Thread(target=self.__finish,kwargs=args)
            self.thread.start()
        result = True
        while result is not None:
            try:
                result = self.progress.get_nowait()
            except Empty:
                result = True
            if isinstance(result,tuple):
                msg,inc = result
                widget = self.component('FinishLabel')
                widget.configure(text=msg)
                self.updateProgress(inc)
            self.mainloop(10)
            self.update()
#        del self.distillFlag
#        del self.compileFlag
#        del self.level
#        if self.nobody:
#            del self.nobody
#        del self.wizard
        self.deactivate('OK')
        
    def __finish(self,entities,compile,distill,level):
        self.scenario = self['finish'](entities,progress=self.progress,
                                       compileDynamics=compile,
                                       compilePolicies=level,
                                       distill=distill)
        
    def progress(self,msg,inc=1):
        if len(msg) == 0:
            msg = 'Done.'
            inc = self.progressBar.max
        widget = self.component('FinishLabel')
        widget.configure(text=msg)
        self.updateProgress(inc)

    def updateProgress(self,inc):
        new = self.progressBar.value + inc
        self.progressBar.updateProgress(new)

    def destroy(self):
        Pmw.Dialog.destroy(self)
        del self.compileFlag
        del self.distillFlag
        del self.level
        del self.wizard
        del self.nobody
        del self._wait