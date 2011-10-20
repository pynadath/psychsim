#! /usr/env/python

"""
WizardShell provides a GUI wizard framework.

WizardShell was derived from AppShell which was itself
derived from GuiAppD.py, originally created by
Doug Hellmann (doughellmann@mindspring.com).

"""
import sys
from Tkinter import Tk,Toplevel,Label,Frame,Button,PhotoImage
import Pmw
# Added by pynadath

class WizardShell(Pmw.MegaWidget):        
    wizversion      = '1.0'
    
    frameWidth      = 550
    frameHeight     = 357
    padx            = 5
    pady            = 5
    panes           = 4
    
    busyCursor = 'watch'
    
    def __init__(self, parent=None, **kw):
        self.__illustration = None
        self.__wizimage = None
        optiondefs = (
            ('image', 'wizard.gif', self.changePicture),        
            ('name', 'Generic Wizard Frame', Pmw.INITOPT),
            ('framewidth',     1,          Pmw.INITOPT),
            ('frameheight',    1,          Pmw.INITOPT))
        self.defineoptions(kw, optiondefs)
        if parent:
            self.root = Toplevel(parent)
        else:
            self.root = Tk()
            Pmw.initialise(self.root)

##         self.initializeTk(self.root)
        self.root.title(self['name'])
        self.root.geometry('%dx%d' % (self.frameWidth, self.frameHeight))

        # Initialize the base class
        Pmw.MegaWidget.__init__(self, parent=self.root)
        
        # initialize the wizard
        self.wizardInit()

        # setup panes
        self.pCurrent = 0
        self.pFrame = [None] * self.panes
        
        # create the interface
        self.__createInterface()
        self.changePicture()
        
        # create a table to hold the cursors for
        # widgets which get changed when we go busy
        self.preBusyCursors = None
        
        # pack the container and set focus
        # to ourselves
        self._hull.pack(side='top', fill='both', expand='yes')
        self.focus_set()

        # initialize our options
        self.initialiseoptions(WizardShell)
        
    def wizardInit(self):
        # Called before interface is created (should be overridden).
        pass
        
    def initializeTk(self, root):
        # Initialize platform-specific options
        if sys.platform == 'mac':
            self.__initializeTk_mac(root)
        elif sys.platform == 'win32':
            self.__initializeTk_win32(root)
        else:
            self.__initializeTk_unix(root)

    def __initializeTk_colors_common(self, root):
        root.option_add('*background', 'grey')
        root.option_add('*foreground', 'black')
        root.option_add('*EntryField.Entry.background', 'white')
        root.option_add('*Entry.background', 'white')        
        root.option_add('*MessageBar.Entry.background', 'gray85')
        root.option_add('*Listbox*background', 'white')
        root.option_add('*Listbox*selectBackground', 'dark slate blue')
        root.option_add('*Listbox*selectForeground', 'white')
                        
    def __initializeTk_win32(self, root):
        self.__initializeTk_colors_common(root)
        root.option_add('*Font', 'Verdana 10 bold')
        root.option_add('*EntryField.Entry.Font', 'Courier 10')
        root.option_add('*Listbox*Font', 'Courier 10')
        
    def __initializeTk_mac(self, root):
        self.__initializeTk_colors_common(root)
        
    def __initializeTk_unix(self, root):
        self.__initializeTk_colors_common(root)

    def busyStart(self, newcursor=None):
        if not newcursor:
            newcursor = self.busyCursor
        newPreBusyCursors = {}
        for component in self.busyWidgets:
            newPreBusyCursors[component] = component['cursor']
            component.configure(cursor=newcursor)
            component.update_idletasks()
        self.preBusyCursors = (newPreBusyCursors, self.preBusyCursors)
        
    def busyEnd(self):
        if not self.preBusyCursors:
            return
        oldPreBusyCursors = self.preBusyCursors[0]
        self.preBusyCursors = self.preBusyCursors[1]
        for component in self.busyWidgets:
            try:
                component.configure(cursor=oldPreBusyCursors[component])
            except KeyError:
                pass
            component.update_idletasks()
              
    def __createWizardArea(self):
        # Create data area where data entry widgets are placed.
        self.__illustration = self.createcomponent('illust',
                                                   (), None,
                                                   Label,
                                                   (self._hull,)) 

        self.__illustration.grid(row=0,column=0,sticky='ns')
        self._hull.columnconfigure(0,weight=0)
        self.__dataArea = self.createcomponent('dataarea',
                                               (), None,
                                               Frame,
                                               (self._hull,), 
                                               relief='flat', bd=1)

        self.__dataArea.grid(row=0,column=1,sticky='ewns')
        self._hull.columnconfigure(1,weight=1)
        self._hull.rowconfigure(0,weight=1)

    def __createSeparator(self):
        self.__separator = self.createcomponent('separator',
                                                (), None,
                                                Frame,
                                                (self._hull,),
                                                relief='sunken',
                                                bd=2, height=2)
        self.__separator.grid(row=1,column=0,columnspan=2,sticky='ew')
        self._hull.rowconfigure(1,minsize=5)

    def __createCommandArea(self):
        # Create a command area for application-wide buttons.
        self.__commandFrame = self.createcomponent('commandframe',
                                                   (), None,
                                                   Frame,
                                                   (self._hull,),
                                                   relief='flat', bd=1)
        self.__commandFrame.grid(row=2,column=0,columnspan=2,sticky='ew')
        self._hull.rowconfigure(2,minsize=20)

    def interior(self):
        # Retrieve the interior site where widgets should go.
        return self.__dataArea

    def changePicture(self):
        if self.__illustration:
            if self.__wizimage: del self.__wizimage
            # Modified by pynadath (support image, as well as file name)
            if isinstance(self['image'],str):
                try:
                    self.__wizimage = PhotoImage(file=self['image'])
                except:
                    self.__wizimage = None
            else:
                self.__wizimage = self['image']
            self.__illustration['image'] = self.__wizimage
        
    def buttonAdd(self, buttonName, command=None, state=1):
        # Add a button to the control area.
        frame = Frame(self.__commandFrame)
        newBtn = Button(frame, text=buttonName, command=command)
        newBtn.pack()
        newBtn['state'] = ['disabled','normal'][state]
        frame.pack(side='right')
        return newBtn

    def __createPanes(self):
        for i in range(self.panes):
            self.pFrame[i] = self.createcomponent('pframe'+str(i),
                                               (), None,
                                               Frame,
                                               (self.interior(),),
                                               relief='flat', bd=1)
            if not i == self.pCurrent:
                self.pFrame[i].forget()
            else:
                self.pFrame[i].pack(fill='both', expand='yes')

    def pInterior(self, idx):
        return self.pFrame[idx]

    def next(self):
        cpane = self.pCurrent
        self.pCurrent = self.pCurrent + 1
        self.prevB['state'] = 'normal'
        if self.pCurrent == self.panes - 1:
            self.nextB['text']    = 'Finish'
            self.nextB['command'] = self.done
        self.pFrame[cpane].forget()
        self.pFrame[self.pCurrent].pack(fill='both', expand='yes')
       
    def prev(self):
        cpane = self.pCurrent
        self.pCurrent = self.pCurrent - 1
        if self.pCurrent <= 0:
            self.pCurrent = 0 
            self.prevB['state'] = 'disabled'
        if cpane == self.panes - 1:
            self.nextB['text']    = 'Next'
            self.nextB['command'] = self.next
        self.pFrame[cpane].forget()
        self.pFrame[self.pCurrent].pack(fill='both', expand='yes')

    def done(self):
        #to be Overridden
        pass
#        if self.__wizimage:
#            del self.__wizimage

    def __createInterface(self):
        self.__createWizardArea()
        self.__createSeparator()
        self.__createCommandArea()
        self.__createPanes()
        #
        # Create the parts of the interface
        # which can be modified by subclasses
        #
        self.busyWidgets = ( self.root, )
        self.createInterface()

    def createInterface(self):
        # Override this method to create the interface for the wiz.
        pass
        
    def main(self):
        # This method should be left intact!
        self.pack()
        try:
            self.mainloop()
        except KeyboardInterrupt:
            self.done()
        
    def run(self):
        self.main()

class TestWizardShell(WizardShell):
    
    def createButtons(self):
        self.buttonAdd('Cancel',            command=self.quit, state=1) 
        self.nextB = self.buttonAdd('Next', command=self.next, state=1)
        self.nextB.configure(default='active')
        self.prevB = self.buttonAdd('Prev', command=self.prev, state=0)
        
    def createMain(self):
        self.w1 = self.createcomponent('w1', (), None,
                                       Label,
                                       (self.pInterior(0),),
                                       text='Wizard Area 1')
        self.w1.pack()
        self.w2 = self.createcomponent('w2', (), None,
                                       Label,
                                       (self.pInterior(1),),
                                       text='Wizard Area 2')
        self.w2.pack()
        
    def createInterface(self):
        WizardShell.createInterface(self)
        self.createButtons()
        self.createMain()
        
    def done(self):
        print 'All Done'

if __name__ == '__main__':
        test = TestWizardShell(image='Icons/faces.gif')
        test.run()
