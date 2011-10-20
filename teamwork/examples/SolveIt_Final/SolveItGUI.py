import Pmw
import os
from teamwork.shell.PsychShell import getConfig
from teamwork.widgets.PsychGUI.Gui import GuiShell

class SolveItGUI(GuiShell):
    def processResult(self,result):
        print result['decision']

if __name__ == '__main__':
    root = Pmw.initialise()
    root.title('PsychSim')
    config = getConfig(os.path.join(os.path.dirname(__file__),'psychsim.ini'))
    shell = SolveItGUI(root,options=config)
    shell.pack(fill='both',expand='yes')
    shell.mainloop(root)
