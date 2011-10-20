from Tkinter import *
import tkMessageBox
import Pmw

from teamwork.action.PsychActions import ActionCondition

class ActionDialog(Pmw.Dialog):
    """Class for specifying L{ActionCondition}s
    """
    def __init__(self,parent,**kw):
        optiondefs = (
            ('actions', [], None),
            ('activatecommand', self.setActions, None),
            )
        self.defineoptions(kw, optiondefs)
        Pmw.Dialog.__init__(self,parent)
        self.createcomponent('label',(),None,Label,(self.interior(),),
                             bd=2,relief='ridge')
        self.component('label').grid(row=0,column=0,sticky='ew',padx=10,pady=10)
        self.createcomponent('options',(),None,Pmw.RadioSelect,
                               (self.interior(),),orient='vertical',
                               buttontype='checkbutton')
        self.component('options').add('only',text='No other actions can occur')
        self.component('options').grid(row=1,column=0,sticky='ew',
                                         padx=10,pady=10)
        self.createcomponent('actions',(),None,Pmw.ScrolledListBox,
                               (self.interior(),),
                               selectioncommand=self.selectAction,
                               listbox_exportselection=0,
                               listbox_selectmode='multiple')
        self.component('actions').grid(row=2,column=0,sticky='ewns',
                                         padx=10,pady=10)
        self.initialiseoptions(ActionDialog)

    def setActions(self):
        self.component('actions').setlist(self['actions'])
        self.selectAction()

    def selectAction(self):
        """Callback when clicking on the action selection box
        """
        actions = list(self.component('actions').getvalue())
        actions.sort()
        if len(actions) > 0:
            self.component('label').configure(text=', '.join(actions))
        else:
            self.component('label').configure(text='Any action')

    def getCondition(self):
        """
        @return: the currently specified L{ActionCondition}
        @rtype: L{ActionCondition}
        """
        condition = ActionCondition('only' in self.component('options').getvalue())
        for action in self.component('actions').getvalue():
            condition.addCondition(action)
        return condition
