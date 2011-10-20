from Tkinter import *
import Pmw
from teamwork.widgets.cookbook import MultiListbox
        
class ObjectivesDialog( Pmw.ScrolledFrame ) :
    def __init__( self, parent=None, **kw):
        optiondefs = (
            ('psyop',1,Pmw.INITOPT),
            ('wildcardLabel','Anybody',Pmw.INITOPT),
            ('entities',[],Pmw.INITOPT),
            ('nameChange',1,Pmw.INITOPT),
            ('name','Psyop Units',Pmw.INITOPT),
            ('objectives',[],Pmw.INITOPT),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.ScrolledFrame.__init__( self, parent )
        if self['psyop']:
            name = "Psyop Objectives"
            Label( self, text="%s:" % (name)).pack( fill = X,
                                                expand=YES,
                                                anchor=NW )
            # Create name entry field
            name = 'Name of Psyop-Associated Entity:' 
            self._nameField = Pmw.EntryField( self.interior(),labelpos = W,
                                              label_text=name,
                                              command=self.updateEntity)
            self._nameField.pack( side=TOP, fill=X, expand=YES, anchor=NW )
            if nameChange:
                self._nameField.component('entry').configure(state=NORMAL)
            else:
                self._nameField.component('entry').configure(state=DISABLED)
            self._nameField.setentry(self.name)
        # Create objective entry box
        self.fields = ['Entity','Feature','Direction']
        widths = {'Feature':16,
                  'Entity':16,
                  'Direction':8}
        g = Pmw.Group(self.interior(),tag_text='Enter new objective:')
        self.buttons = {}
        for index in range(len(self.fields)):
            field = self.fields[index]
            l = Label(g.interior(),text=field+':',anchor=W,
                      justify='left')
            l.grid(row=index,column=0)
            b = Pmw.OptionMenu(g.interior(),
                               menubutton_width=30)
            if field == 'Entity':
                eList = map(lambda e:e.name,self['entities'])
                b.setitems([self['wildcardLabel']]+eList)
                b.configure(command=self.selectEntity)
            elif field == 'Direction':
                b.setitems(['Maximize','Minimize'])
            elif field == 'Feature':
                self.states = []
                self.actions = []
                for entity in self['entities']:
                    for feature in entity.getStateFeatures():
                        if not feature in self.states:
                            self.states.append(feature)
                    for actionList in entity.actions.getOptions():
                        for action in actionList:
                            if not action['type'] in self.actions:
                                self.actions.append(action['type'])
                b.setitems(self.states+self.actions)
            b.grid(row=index,column=1)
            self.buttons[field] = b
        g.pack(fill=X,expand=YES)
        # Create box of add/remove buttons
        box = Pmw.ButtonBox(self.interior())
        box.add('Add',command=self.addItem)
        box.add('Remove',command=self.removeItems)
        box.pack(side=TOP)
        # Create display of current objectives
        self.list = MultiListbox(self.interior(),
                                 map(lambda f,w=widths:(f,w[f]),
                                     self.fields))
        self.list.pack(expand=YES,fill=BOTH)
        for item in self['objectives']:
            self.list.insert(END,item)
        self.initialiseoptions()
        
    def addItem(self):
        item = ()
        for field in self.fields:
            item += (self.buttons[field].getvalue(),)
        if not item in self['objectives']:
            self.list.insert(END,item)
            self['objectives'].append(item)

    def removeItems(self):
        for item in self.list.curselection():
            self.list.delete(item)
            del self['objectives'][int(item)]

    def updateEntity(self):
        name = self._nameField.getvalue()
        oldName = self.name
        self.name = name
        eList = [self['wildcardLabel']]+\
                map(lambda e:e.name,self['entities'])
        self.buttons['Entity'].setitems(eList)
        for index in range(len(self['objectives'])):
            item = self['objectives'][index]
            if item[1] == oldName:
                self['objectives'].remove(item)
                item = (item[0],name,item[2])
                self['objectives'].insert(index,item)
                self.list.delete(index)
                self.list.insert(index,item)

    def selectEntity(self,name):
        pass
