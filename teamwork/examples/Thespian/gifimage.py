
"""
__version__ = "$Revision: 1.24 $"
__date__ = "$Date: 2004/08/11 01:58:03 $"
"""

import wx
import wx.animate

from PythonCard import event, graphic, widget

USE_GENERIC = wx.Platform == '__WXGTK__'

GIFAnimationCtrl = wx.animate.GIFAnimationCtrl
class GifImageSpec(widget.WidgetSpec):
    def __init__(self):
        events = []
        attributes = {
            'file' : { 'presence' : 'optional', 'default':'' },
            # KEA shouldn't there be a 'file' attribute here
            # could call it 'image' to match background above
            # but it is mandatory
            #'bitmap' : { 'presence' : 'optional', 'default' : None },
            # KEA kill border for now, until variations of what is possible are worked out
            # use ImageButton if you want images with transparent border
            #'border' : { 'presence' : 'optional', 'default' : '3d', 'values' : [ '3d', 'transparent', 'none' ] },
            'size' : { 'presence' : 'optional', 'default' : [ -1, -1 ] },
        }
        widget.WidgetSpec.__init__( self, 'GifImage', 'Widget', events, attributes )
        

class GifImage(widget.Widget, GIFAnimationCtrl):
    """
    gif image.
    """

    _spec = GifImageSpec()

    def __init__(self, aParent, aResource):
        self._file = aResource.file

        self._size = tuple(aResource.size)
        w = aResource.size[0]
        if w == -2:
            w = self._bitmap.getWidth()
        h = aResource.size[1]
        if h == -2:
            h = self._bitmap.getHeight()
        size = (w, h)
        #size = wx.Size( self._bitmap.GetWidth(), self._bitmap.GetHeight() )

        ##if aResource.border == 'transparent':
        ##    mask = wx.MaskColour(self._bitmap, wxBLACK)
        ##    self._bitmap.SetMask(mask)

##        StaticBitmap.__init__(
##            self,
##            aParent, 
##            widget.makeNewId(aResource.id),
##            self._bitmap.getBits(), 
##            aResource.position, 
##            size,
##            style = wx.NO_FULL_REPAINT_ON_RESIZE | wx.CLIP_SIBLINGS,
##            name = aResource.name
##            )
        
        GIFAnimationCtrl.__init__(
            self,
            aParent, 
            widget.makeNewId(aResource.id),
            self._file,
            aResource.position, 
            size,
            style = wx.NO_FULL_REPAINT_ON_RESIZE | wx.CLIP_SIBLINGS,
            name = aResource.name
            )
        
        self.Play()
##        GIFAnimationCtrl(self, id, ag_fname, pos=(10, 10))
        
        widget.Widget.__init__( self, aParent, aResource )

        wx.EVT_WINDOW_DESTROY(self, self._OnDestroy)
        
        self._bindEvents(event.WIDGET_EVENTS)

    def _OnDestroy(self, event):
        # memory leak cleanup
        self._bitmap = None
        event.Skip()



    # KEA special handling for -2 size option
    def _setSize(self, aSize):
        self._size = tuple(aSize)
        w = aSize[0]
        if w == -2:
            w = self._bitmap.getWidth()
        h = aSize[1]
        if h == -2:
            h = self._bitmap.getHeight()
        self.SetSize((w, h))

    # KEA 2001-08-02
    # right now the image is loaded from a filename
    # during initialization
    # but later these might not make any sense
    # if setBitmap is used directly in user code
    def _getFile( self ) :
        return self._file

    # KEA 2001-08-14
    # if we're going to support setting the file
    # after initialization, then this will need to handle the bitmap loading
    # overhead
    def _setFile( self, aFile ) :
        self._file = aFile
        self._setBitmap(graphic.Bitmap(aFile))



##    backgroundColor = property(widget.Widget._getBackgroundColor, _setBackgroundColor)
    file = property(_getFile, _setFile)
    size = property(widget.Widget._getSize, _setSize)


import sys
from PythonCard import registry
registry.Registry.getInstance().register(sys.modules[__name__].GifImage)
