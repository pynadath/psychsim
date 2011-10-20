import os.path
from Tkinter import Label,Button,PhotoImage

imageDirectory = None

def getImageDirectory():
    global imageDirectory
    if imageDirectory is None:
        imageDirectory = os.path.dirname(__file__)
        if len(imageDirectory) == 0:
            imageDirectory = os.getcwd()
        elements = os.path.split(imageDirectory)
        imageDirectory = apply(os.path.join,elements[:-1]+('images',))
    return imageDirectory
    
def getImage(name):
    """Returns the OS-appropriate absolute path for the named image"""
    path = os.path.join(getImageDirectory(),name)
    return path

def getAgentImage(filename):
    if len(filename) > 0:
        import Tkinter
        return Tkinter.PhotoImage(file=filename)
    else:
        return None
 
def getPILImage(filename):
    from PIL import ImageTk
    return ImageTk.PhotoImage(file=getImage(filename))

def loadImage(filename,usePIL=True):
    if filename[-4:] == '.gif':
        return PhotoImage(file=getImage(filename))
    elif usePIL:
        import PIL
        return PIL.ImageTk.PhotoImage(file=getImage(filename))
    else:
        return None
    
def loadImages(mapping,usePIL=True):
    """Loads a series of images and returns a table
    @param mapping: a mapping of keys to file names
    @type mapping: dict
    @return: a table mapping keys to C{PhotoImage} objects
    @rtype: dict
    """
    result = {}
    for key,filename in mapping.items():
        result[key] = loadImage(filename,usePIL)
    return result

def makeButton(frame,table,key,command,text,parent=None,component=None,
               event='<ButtonRelease-1>'):
    """Utility method for making clickable images, or alt-text buttons
    """
    try:
        image = table[key]
    except KeyError:
        image = None
    if parent:
        if image:
            widget = parent.createcomponent(component,(),None,Label,
                                            (frame,),image=image)
            if event:
                widget.bind(event,command)
        else:
            widget = parent.createcomponent(component,(),None,Button,
                                            (frame,),text=text,
                                            command=command)
    else:
        if image:
            widget = Label(frame,image=table[key])
            widget.bind(event,command)
        else:
            widget = Button(frame,text=text,command=command)
    return widget

if __name__ == '__main__':
    print getImage('nobody.gif')
