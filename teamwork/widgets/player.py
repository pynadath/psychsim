from Tkinter import *
import Pmw
from images import getImage

class PlayerControl(Pmw.ButtonBox):
    """A ButtonBox subclass for a colleciton of media player buttons"""

    def __init__(self, parent=None, **kw):
        """Accepts all the standard ButtonBox options"""
        optiondefs = ()
        self.defineoptions(kw,optiondefs)
        Pmw.ButtonBox.__init__(self,parent=parent)
        self.initialiseoptions(PlayerControl)
        self.images = {}
        self.state = {}

    def add(self,name,**kw):
        """Adds a button of the given name and corresponding image"""
        button = Pmw.ButtonBox.add(self,name,**kw)
        self.addImage(name,name)
        self.state[name] = 0
        self.drawImage(name)
        return button

    def delete(self,index):
        """Deletes the corresponding button (name-type index preferred"""
        Pmw.ButtonBox.delete(self,index)
        try:
            del self.images[index]
            del self.state[index]
        except KeyError:
            # Hmm, maybe there's a better way
            pass

    def getImage(self,name):
        """Utility method to get the image widget of the named button"""
        try:
            image = PhotoImage(file=getImage('media-%s.gif' % (name)))
        except:
            image = None
        return image

    def addImage(self,name,image):
        """Adds the named image to the named button's toggle sequence"""
        pic = self.getImage(image)
        if pic:
            try:
                self.images[name].append(pic)
            except KeyError:
                self.images[name] = [pic]

    def drawImage(self,name):
        """Utility image that sets named button's label to be its
        currently relevant image"""
        button = self.component(name)
        try:
            button.configure(image=self.images[name][self.state[name]])
        except KeyError:
            button.configure(text=name)
        
    def toggle(self,name):
        """Advances the named button in its image sequence"""
        self.state[name] = (self.state[name]+1) % len(self.images[name])
        self.drawImage(name)
        
if __name__ == '__main__':
    root = Tk()
    Pmw.initialise(root)
    control = PlayerControl(root,orient=HORIZONTAL)
    control.pack(side=TOP,fill=X,expand=1)
    control.add('prev')
    button = control.add('play')
    button.configure(command=lambda c=control:c.toggle('play'))
    control.addImage('play','pause')
    control.add('next')
    # Test adding a button with a missing image
    control.add('hello')
    try:
        root.mainloop()
    except KeyboardInterrupt:
        root.destroy()
    
