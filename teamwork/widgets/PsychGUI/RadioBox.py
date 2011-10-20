from Tkinter import *
import Pmw

class Rbox(Pmw.RadioSelect):

    def disable(self):
        for index in range(self.numbuttons()):
            self.button(index).configure(state=DISABLED)

    def enable(self):
        for index in range(self.numbuttons()):
            self.button(index).configure(state=NORMAL)
