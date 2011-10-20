
"""
__version__ = "$Revision: 1.10 $"
__date__ = "$Date: 2004/04/24 22:13:31 $"
"""

from PythonCard import model

import string
import sys
import minimalGui



class watermaze(model.Background):
    def on_initialize(self, event):
        self.minimalWindow = model.childWindow(self, minimalGui.MinimalGui)
        self.minimalWindow.visible = False

        
    def on_start_mouseClick(self, event):
        self.minimalWindow.visible = True
        self.visible = False


if __name__ == '__main__':
    
    
    app = model.Application(watermaze)
    

    app.MainLoop()
