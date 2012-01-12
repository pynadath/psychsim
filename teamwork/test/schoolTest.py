import threading
import time
import unittest
import Pmw
from teamwork.shell.PsychShell import getConfig
from teamwork.widgets.PsychGUI.Gui import GuiShell

class TestPsychSim(unittest.TestCase):
    def runThread(self):
        root = Pmw.initialise()
        root.title('PsychSim')
        self.shell = GuiShell(root,options=getConfig())
        self.shell.pack(fill='both',expand='yes')
        self.shell.mainloop(root,False)
        
    def setUp(self):
        self.shell = None
        thread = threading.Thread(target=self.runThread)
        thread.start()
        while self.shell is None:
            time.sleep(1)

    def tearDown(self):
        self.shell.queue.put('quit')

    def createChild(self,parent,child):
        """Creates a new subclass
        @param parent: the name of the superclass
        @param child: the name of the new subclass
        @type parent,child: str
        """
        node = self.shell.psymwindow.nodes[parent]
        entity = self.shell.psymwindow['entities'][node.child().text()]
        self.shell.psymwindow.selectNode(None,node)
        self.shell.newParent = entity
        self.shell.nameDialog.insertentry(0,child)
        self.shell._addAgent('OK')
        self.shell.psymwindow.setview(name=self.shell.psymwindow.vname)

    def createState(self,agent,feature):
        window = self.shell.entitywins[agent]
        window.component('State_newdialog').insertentry(0,feature)
        window.component('State').newFeature('OK')

    def createAction(self,agent,verb,obj=None,includeSelf=False):
        window = self.shell.entitywins[agent]
        window.component('Actions').updateTypes()
        window.component('Actions_type_entryfield').setentry(verb)
        window.component('Actions').updateObjects()
        if obj is None:
            obj = 'None'
        elif not window.component('Actions').objects.has_key(obj):
            if includeSelf:
                obj += ' (including self)'
            else:
                obj += ' (but not self)'
        window.component('Actions_object_entryfield').setentry(obj)
        window.component('Actions').add('OK')

    def testPsychSim(self):
        # Create class hier
        self.assertEqual(self.shell.psymwindow.nodes.keys(),['Entity'])
        self.createChild('Entity','student')
        self.shell.psymwindow.raiseWindow(None,self.shell.psymwindow.nodes['student'])
        self.createChild('Entity','teacher')
        self.shell.psymwindow.raiseWindow(None,self.shell.psymwindow.nodes['teacher'])
        self.assert_(self.shell.entities.has_key('Entity'))
        self.assert_(self.shell.entities.has_key('student'))
        self.assert_(self.shell.entities.has_key('teacher'))
        # Create student state features
        self.createState('student','welfare')
        self.assertEqual(self.shell.entities['student'].getStateFeatures(),['welfare'])
        # Create student actions
        self.createAction('student','do nothing')
        self.createAction('student','pick on','student',False)
        self.assertEqual(len(self.shell.entities['student'].actions.getOptions()),2)
        # Create teacher actions
        self.createAction('teacher','do nothing')
        self.createAction('teacher','punish','student')
        self.createAction('teacher','punishClass')
        self.assertEqual(len(self.shell.entities['teacher'].actions.getOptions()),3)
        # Add dynamics
        window = self.shell.entitywins['student']
        window.component('State').expand(feature='welfare')
        
if __name__ == '__main__':
    unittest.main()
