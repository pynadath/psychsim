from Tkinter import Frame,Checkbutton,IntVar
import tkMessageBox
import Pmw
from teamwork.math.Keys import ObservationKey
from teamwork.widgets.images import loadImages,makeButton
from teamwork.widgets.TreeBuilder import TreeBuilder

class ObservationFrame(Pmw.ScrolledFrame):
    """Frame for specifying model of partial observability
    @ivar images: table of images to use (need to keep this permanently stored)
    @type images: dict
    @cvar anyString: label used for a O function LHS that matches against any action
    @type anyString: str
    """
    anyString = 'any'
    
    def __init__(self,parent,entity,**kw):
        optiondefs = (
            ('balloon',None,Pmw.INITOPT),
            ('generic',False,Pmw.INITOPT),
            ('expert', False,None),
            ('society', {}, None),
            ('options',None,None),
            )
        self.entity = entity
        self.defineoptions(kw, optiondefs)
        Pmw.ScrolledFrame.__init__(self,parent)
        self.images = loadImages({'del': 'icons/binocular--minus.gif',
                                  'add': 'icons/binocular--plus.gif',
                                  'new': 'icons/chart--plus.gif'},
                                 self['options'].get('Appearance','PIL') == 'yes')
        self.interior().grid_columnconfigure(0,weight=1)
        if self['generic']:
            toolbar = Frame(self.interior(),bd=2,relief='raised')
            toolbar.grid(row=0,column=0,sticky='new')
            # Dialog for getting new symbol name
            self.createcomponent('dialog',(),None,Pmw.PromptDialog,(parent,),
                                 title='New observation',entryfield_labelpos='w',
                                 label_text='New observation:',
                                 defaultbutton = 0,buttons = ('OK', 'Cancel'),
                                 command = self.newOmega)
            self.component('dialog').withdraw()
            # Button for adding new observations
            button = makeButton(toolbar,self.images,'add',
                                self.component('dialog').activate,'+')
            button.pack(side='left',ipadx=5,ipady=3)
            if self['balloon']:
                self['balloon'].bind(button,'Add new observation symbol')
            # Button for deleting observation symbols
            button = makeButton(toolbar,self.images,'del',self.delete,'-')
            button.pack(side='left',ipadx=5,ipady=3)
            if self['balloon']:
                self['balloon'].bind(button,'Delete selected observation symbol')
        # Toggle for complete observability
        self.perfect = IntVar()
        button = self.createcomponent('observable',(),None,Checkbutton,
                                      (self.interior(),),command=self.observable,
                                      variable=self.perfect,
                                      text='Perfect observations')
        button.grid(row=1,column=0,sticky='nw',padx=20,pady=20)
        # Space for partial observability
        frame = self.createcomponent('details',(),None,Frame,(self.interior(),))
        # Buttons for existing observation symbols
        widget = self.createcomponent('omega',(),None,Pmw.RadioSelect,(frame,),
                                      labelpos='nw',label_text='Observations:',
                                      buttontype='checkbutton',frame_bd=1,
                                      frame_relief='ridge')
        widget.pack(side='top',anchor='nw',fill='x',padx=20,pady=20)
        # Area for defining observation function
        table = {}
        for entry in entity.observations:
            table[str(entry['actions'])] = entry
        widget = self.createcomponent('editor',(),None,TreeBuilder,(frame,),
                                      orient='horizontal',default=True,
                                      menus_leaves=self.entity.omega.keys(),
                                      society=self['society'],expert=True,
                                      new=self.newO,table=table)
        widget.interior().grid_columnconfigure(1,weight=1)
        widget.pack(side='top',anchor='nw',fill='both',padx=20,pady=20)
        # Set up initial view depending on whether there are pre-defined 
        # observations or not
        self.drawOmega()
        if self.entity.observable():
            button.select()
        else:
            button.deselect()
        self.observable()
        if not self['generic']:
            button.configure(state='disabled')
        self.initialiseoptions(ObservationFrame)

    def observable(self):
        """Callback for toggling complete observability
        """
        if self.perfect.get():
            self.component('details').grid_forget()
        else:
            self.component('details').grid(row=2,column=0,sticky='enws')

    def newOmega(self,button):
        """Callback for a new observation
        """
        self.component('dialog').deactivate()
        if button == 'OK':
            omega = self.component('dialog_entryfield').getvalue().strip()
            key = ObservationKey({'type': omega})
            if not self.entity.omega.has_key(key):
                self.entity.omega[key] = True
                self.drawOmega()
                self.component('dialog_entryfield').clear()
                self.component('editor_menus').configure(leaves=self.entity.omega.keys())

    def drawOmega(self):
        """Updates the display of the current set of possible observations
        """
        Omega = map(str,self.entity.omega.keys())
        Omega.sort()
        widget = self.component('omega')
        widget.deleteall()
        for omega in Omega:
            if omega == str(None) or omega == str(True):
                widget.add(omega,state='disabled')
            else:
                widget.add(omega)

    def validate(self,omega):
        """Validates the uniqueness of the current symbol
        """
        if self.entity.omega.has_key(ObservationKey({'type': omega})):
            return Pmw.PARTIAL
        elif omega == str(None) or omega == str(True):
            # Avoid reserved observation keywords
            return Pmw.PARTIAL
        else:
            return Pmw.OK

    def newO(self,key,option,tree):
        """Callback for creating a new observation function entry
        """
        self.entity.observations.append({'actions': option,'tree': tree})

    def delete(self,event=None):
        """Deletes selected observation symbols
        """
        selection = self.component('omega').getvalue()
        if 'None' in selection:
            tkMessageBox.showerror('Illegal removal','You cannot remove the null observation.')
        elif 'True' in selection:
            tkMessageBox.showerror('Illegal removal','You cannot remove the true observation.')
        elif selection:
            for omega in selection:
                key = ObservationKey({'type': omega})
                del self.entity.omega[key]
            self.drawOmega()
        else:
            tkMessageBox.showerror('No selection','You must first select at least one observation symbol to delete.')
