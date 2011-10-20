from Tkinter import *
import Pmw
from teamwork.math.KeyedVector import TrueRow
from teamwork.math.KeyedTree import KeyedPlane
from MatrixEditor import MatrixEditor

class AttributeDialog(Pmw.Dialog):
    def __init__(self,parent,entity,**kw):
        self.entity = entity
        optiondefs = (
            ('plane', KeyedPlane(TrueRow(),-.1), self.setPlane),
            )
        self.defineoptions(kw, optiondefs)
        Pmw.Dialog.__init__(self,parent)
        self.createcomponent('attribute',(),None,Label,
                             (self.component('dialogchildsite'),),
                             height=3,wraplength=300,
                             ).pack(side='top',expand='yes')
        # Find all possible state features
        states = {}
        for key in self.entity.getBeliefKeys():
            states[str(key)] = key
        self.createcomponent('selector',(),None,MatrixEditor,
                             (self.component('dialogchildsite'),),
                             states=states,
                             ).pack(side='top',fill='both',expand='yes')
        self.component('selector_type').configure(entry_width=32,
                                                  selectioncommand=self.setBranch)
        self.component('selector').displayBranch(self['plane'])
        for name in self.component('selector').components():
            if self.component('selector').componentgroup(name) == 'feature':
                self.component('selector_%s' % (name)).configure(selectioncommand=self.updatePlane)
        self.initialiseoptions()

    def setPlane(self):
        self.component('attribute').configure(text=self['plane'].simpleText())

    def setBranch(self,rowType):
        self.component('selector').setBranch(rowType)
        self.updatePlane()

    def updatePlane(self,button=None):
        self['plane'] = self.component('selector').getBranch()
