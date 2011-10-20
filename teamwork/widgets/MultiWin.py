"""
<Multiple_window> and <Inner_Window> classes 
Idea of multiples windows comes from a Tcl package called mdw_lib.tk
(a classlib for [m]ulti_[d]ocument_[w]indow applications).
The mdw_lib is a number of Tcl/Tk procedures to create and manipulate 
multiple childwindows in one Tk application window 
The  mdw_lib author is Thomas Schwarze <swz@rtws18.ee.tu_berlin.de>
Original package is GPL'ed. However, code and way to implement
multiple windows and mdw_lib are completely different.

           Author: Erick Gallesio [eg@unice.fr]
    Creation date:  5_Apr_1996 18:04
 Last file update:  3_Sep_1999 21:34 (eg)

# (require "Basics")
# (select-module STklos+Tk)

# (export place) # Since it it redefined as a generic ...
"""

from Tkinter import Label,Frame,BitmapImage,Button,IntVar
import Pmw

class MultipleWin (Pmw.MegaWidget):
    """ <Multiple_window> class
     Consider forwarding methods eg
     Pmw.forwardmethods(MyClass, TargetClass,
        MyClass.findtarget, ['dangerous1', 'dangerous2'])
     In both cases, all TargetClass methods will be forwarded from MyClass
     except for dangerous1, dangerous2, special methods like __str__,
     and pre-existing methods like foo.

     so something like 
     Pmw.forwardmethods(InnerWindow, Frame, InnerWindow.interior)
     and it MUST be placed afer class definition
    """
    def __init__ (self, parent, **kw):
        optiondefs = (('relief', 'ridge', None),
                      ('width', 640, None),
                      ('height', 480, None),
                      ('background',     'gray50',     None),
                      ('borderwidth',    2,           None),
                      ('foreground',     'navy',      None),
                      ('readyText',"Windows",Pmw.INITOPT),
                      )
        self.defineoptions(kw, optiondefs)
        # Initialise the base class (after defining the options).
        Pmw.MegaWidget.__init__(self, parent)

        self.propagate(0)
        self.parent = parent
        self.children = []
        self.stack = []
        ##         self.current = 0

        # Ignore the border-width or highlight-thickness given (or implied
        # by a .Xdefaults configuration) to ease window movement in. This
        # is clearly not correct but user should not see the trick
        self.configure(hull_width = self['width'])
        self.configure(hull_height = self['height'])
        self.configure(hull_relief = self['relief'])
        self.configure(hull_background = self['background'])
        #        self.borderwidth = 0
        #        self.highlight_thickness = 0

        # Create the bottom bar
        self.BottomBar = self.createcomponent('BottomBar',
		(), 'Mygroup',
		Frame, (self.interior(),), relief = "groove",
        ##                 background = 'blue',
		borderwidth = 3)
        self.Btitle = self.createcomponent('Btitle',
                                           (), 'Mygroup',
                                           Label, (self.BottomBar,),
                                           text = self['readyText'],
                                           width=10,
                                           ## background = 'lightblue',
                borderwidth=3, relief="ridge", anchor="w")
        self.BottomBar.pack(side='bottom', expand = 0, fill='x')
        self.Btitle.pack(side='left', expand = 0, padx = 3, pady = 3)
        self.initialiseoptions(MultipleWin)
        
    def setTitleColor(self):
        """
        Updates the color of all L{InnerWindow} children
        """
        for w in self.children:
            w.setTitleColor()
            
    def find_current_window (self, avoid):
        """Find a plausible current window (i.e one which is different than avoid and which is not iconified). If no window is available return avoid.
        """
        try:
            return self.stack[-1]
        except IndexError:
            l = self.children[:]
            while True:
                if len(l) == 0: return avoid
                if l[0] == avoid or l[0].iconified:
                    del l[0]
                else:
                    return l[0]

    def height(self):
        widgets = [self.BottomBar,self.Btitle]
        total = self.winfo_height()
        for win in widgets:
            total -= win.winfo_height()
        return total

#######################################
##
## <Inner-window> class
##
###############################
class InnerWindow (Pmw.MegaWidget):
    """@cvar mycursors: InnerWindow contol icons
    """
    mycursors = ["top_left_corner",   "top_side",    "top_right_corner",
	    "left_side",          "crosshair",   "right_side",
		"bottom_left_corner", "bottom_side", "bottom_right_corner"]
    bd = 15    # # of pixels for detecting a border

##   bitmap_cross = None
##   bitmap_icon  = None
##   bitmap_max   = None
##   bitmap_min   = None
    def createBitmaps( self ) :
        if not hasattr( InnerWindow, 'bitmap_cross' ) :
            InnerWindow.bitmap_cross = BitmapImage(data = """
            #define im_width 10
            #define im_height 10
            static unsigned char im_bits[] = {
            0,0,0,0,0xc,3,0x9c,3,0xf8,
            1,0xf0,0,0xf0,0,0xf8,1,0x9c,3,0x0c,3
            };"""  )
        if not hasattr( InnerWindow, 'bitmap_icon' ) :
            InnerWindow.bitmap_icon = BitmapImage(data = """
            #define im_width 10
            #define im_height 10
            static unsigned char im_bits[] = {
            0,0,0,0,0,0,0,0,
            0,0,0,0,0,0,0xfc,3,0xfc,3,0,0
            };""" )
        if not hasattr( InnerWindow, 'bitmap_max' ) :
            InnerWindow.bitmap_max = BitmapImage(data = """
            #define im_width 10 
            #define im_height 10
            static unsigned char im_bits[] = {
            0,0,0,0,0xfc,3,0xfc,
            3,0xfc,3,0xfc,3,0xfc,3,0xfc,3,0xfc,3,0xfc,3
            };""" )
        if not hasattr( InnerWindow, 'bitmap_min' ) :
            InnerWindow.bitmap_min = BitmapImage(data = """
            #define im_width 10
            #define im_height 10
            static unsigned char im_bits[] = {
            0,0,0,0,0,0,0,0,0xf0,
            0,0xf0,0,0xf0,0,0xf0,0,0,0,0,0
            };""" )

    def __init__ (self, parent, **kw):
        palette = Pmw.Color.getdefaultpalette(parent.parent)
        optiondefs = (('relief', 'ridge', None), 
                      ('title','Inner Window',self.setTitle),
                      ('width', 320, None),
                      ('height', 240, None),
                      ('x', 20, None),
                      ('y', 20, None),
                      ('background', palette['background'],     None),
                      ('borderwidth',    2,           None),
                      ('foreground', palette['foreground'],      None),
                      ('destroycommand',None,Pmw.INITOPT),
                      )
        self.defineoptions(kw, optiondefs)
        # Initialise the base class (after defining the options).
        Pmw.MegaWidget.__init__(self, parent.interior())
        self.propagate(0)
        self.width = self['width']
        self.height = self['height']
        self.configure(hull_width = self['width'])
        self.configure(hull_height = self['height'])
        self.configure(hull_relief = self['relief'])
        self.configure(hull_borderwidth = 3)
        self.parent = parent
        self.frame = self.createcomponent('frame',(), 'Mygroup',Frame,
                             (self.interior(),), cursor ="left_ptr",
                             background = self['background'],
                             borderwidth = 0,
                             )
        self.frame.pack(fill='both',expand=1)
        self.createcomponent('title',(), 'Mygroup',Frame,
                             (self.component('frame'),),
                             borderwidth=2, relief='raised',
                             ).pack(side = 'top', fill = 'x', expand = 0)

        self.createcomponent('label',(), 'Mygroup',Label,
                             (self.component('title'),),
                             cursor = "fleur",
                             ).pack(side='left', expand = 1, fill = 'x')
        self.createBitmaps()
        if self['destroycommand']:
            self.createcomponent('destroy',(), 'Mygroup',Button,
                                (self.component('title'),),
                                image = InnerWindow.bitmap_cross,
                                command = self.destroy,
                                ).pack(side = 'right')
        self.createcomponent('maximize',(), 'Mygroup',Button,
                             (self.component('title'),),
                             image = InnerWindow.bitmap_max,
                             command = self.minormax,
                             ).pack(side = 'right')
        self.createcomponent('iconify',(), 'Mygroup',
                             Button, (self.component('title'),),
                             image = InnerWindow.bitmap_icon,
                             command =  self.iconify_window,
                             ).pack(side = 'right')
        
        self.maximized = False
        self.visible = IntVar()
        self.visible.set(1)
        self.iconified = 0
        self.myindex  =  0
        self.resizing = None

        # Associate buttons callbacks
        self.make_inner_window_bindings(None)
        # Add the new window to the multiple-window children list
        parent.children.append(self)
        # Initialise instance variables.
        self.initialiseoptions(InnerWindow)

    def setTitle(self):
        self.component('label').configure(text=self['title'])
        try:
            widget =  self.component('icon')
            widget.configure(text=self['title'],
                             width=min(len(self['title']),15))
        except KeyError:
            pass

    def minormax(self):
        if self.maximized:
            self.minimize_window() 
        else:
            self.maximize_window()

    def unselect_window (self):
        if self in self.parent.stack:
            self.parent.stack.remove(self)
            win = self.parent.find_current_window(self)
            if win is not self:
                win.mwraise()
                win.setTitleColor()
            self.setTitleColor()

    def select_window(self):
        if self in self.parent.stack:
            self.parent.stack.remove(self)
        self.parent.stack.append(self)
        if len(self.parent.stack) > 1:
            self.parent.stack[-2].setTitleColor()
        self.setTitleColor()

    def setTitleColor(self):
        """Updates the title color of this window
        """
        palette = Pmw.Color.getdefaultpalette(self.parent.parent)
        if len(self.parent.stack) > 0 and self is self.parent.stack[-1]:
            self.component('label').configure(fg=palette['selectForeground'],
                                              bg=palette['selectBackground'])
        else:
            self.component('label').configure(fg=palette['foreground'],
                                              bg=palette['background'])

    def mwraise (self,event=None):
        if len(self.parent.stack) == 0 or self is not self.parent.stack[-1]:
            self.select_window()
            Frame.tkraise(self.interior())		
            self.parent.BottomBar.tkraise()

    def lower (self):
        self.unselect_window
        self.interior().lower()

    def destroy (self,override=False):
        if self['destroycommand'] and not override:
            self['destroycommand'](self)
        else:
            parent = self.parent
            if parent.children.count(self): parent.children.remove(self)
            self.unselect_window()
            if self.iconified:
                self.destroycomponent('icon')
            else:
                try:
                    self.parent.stack.remove(self)
                except ValueError:
                    # No big deal
                    pass
            Pmw.MegaWidget.destroy(self)#.interior())

    def maximize_window (self):
        if not self.maximized :
            self.mwraise()
            self.maximized = True
            self['x']  = self.winfo_x()
            self['y']  = self.winfo_y()
            self.width  = self.winfo_width()
            self.height  = self.winfo_height()
            # Use pack to fill the cavity
            self.pack(fill = 'both', expand = 1)
            # Change maximize button
            but = self.component('maximize')
            but.configure(image = InnerWindow.bitmap_min)    

    def minimize_window (self):
        if self.maximized:
            self.maximized = False
            # Forget previous pack
            self.interior().pack_forget()
            self.interior().place(x = self['x'],y = self['y'],
                                  width = self.width,height = self.height)
            # Change maximize button
            self.component('maximize').configure(image=InnerWindow.bitmap_max)

    def iconify_window (self):
        if not self.iconified:
            parent = self.parent
            self.visible.set(0)
            self.iconified = True
            self.unselect_window()
            self.minimize_window()
            # Retain window position before deleting it
            if  self.winfo_y() > 2 and self.winfo_width() > 20 and \
                self.winfo_height() > 20:
                self['x'] = self.winfo_x()
                self['y'] = self.winfo_y()
                self.width = self.winfo_width()
                self.height = self.winfo_height()
            # Create Icon button
            bar = parent.BottomBar
            title = self.component('label').cget('text')
            b = self.createcomponent('icon',(),None,Button,(bar,),
                                     text = title,
                                     font = "-adobe-helvetica-*-r-*-*-*-100-*-*-*-*-*-*",
                                     width =  min(len(title), 15),
                                     anchor = "w",
                                     command = self.show_window)
            b.pack(side = 'left', expand = 0, fill = 'none')
            self.place_forget() 

    def show_window (self) :
        if self.iconified:
            self.iconified = None
            self.visible.set(1)
            self.place( x = self['x'],
                        y = self['y'],
                        width = self.width,
                        height = self.height )
            # Destroy icon
            self.destroycomponent('icon')
        else:
            # raise the window
            self.mwraise()


    def iconify_or_show (self) :
        if self.iconified:
            self.show_window()
        else:
            self.iconify_window()

    def place (self, **kw):
        Frame.place(self.interior(), kw)
        self.mwraise()

    def inner_raise_set(self, event):
        x = event.x_root
        y = event.y_root
        self.mwraise()
        self['x'] = x 
        self['y'] = y

    def inner_place_set(self, event):
        x = event.x_root
        y = event.y_root
        if not self.maximized:
            self.update_idletasks()
            myy = self.encloseY(y)
            myx = self.encloseX(x,25)
            self.place(x = myx, y = myy)
            self['x'] = x
            self['y'] = y

    def encloseX(self,x,pad=0):
        return min(max(self.winfo_x() + (x - self['x']),0),
                   self.parent.winfo_width()-pad)

    def encloseY(self,y,pad=0):
        return min(max(self.winfo_y() + (y - self['y']),0),
                   self.parent.height()-pad)
   
    def inner_lower_set(self, event):
        if self is self.parent.stack[-1]:
            self.lower()

    def in_inner_window (self, event):
        x = event.x
        y = event.y
        w = self.winfo_width()
        h = self.winfo_height()
        bd = self.bd
        ci = 0
        if y < bd :
            ci = 0
        elif y < (h - bd) :
            ci = 3
        else:
            ci = 6
        if x < bd :
            ci = ci
        elif x < (w - bd) :
            ci = ci + 1
        else :
            ci = ci + 2
        self.myindex = ci
        self.interior().config(cursor = self.mycursors[ci])
    
    def resize_inner_window  (self, event):
        x = event.x_root
        y = event.y_root
        if (not self.resizing) and (not self.maximized) :
            self.resizing =  True
        index = self.myindex
        width = self.winfo_width()
        height = self.winfo_height()
        parent = self.parent
        parentHeight = parent.height()
        parentWidth = parent.winfo_width()
        off_x  = parent.winfo_rootx()
        off_y  = parent.winfo_rooty()
        x1 = self.winfo_rootx() - off_x
        y1 = self.winfo_rooty() - off_y
        x2 = x1 + width
        y2 = y1 + height
        if index == 0:
            x1 = min(max(x - off_x,0),x2-25,parentWidth-25)
            y1 = min(max(y - off_y,0),y2-25,parentHeight)
        elif index == 1:
            y1 = min(max(y - off_y,0),y2-25,parentHeight)
        elif index == 2:
            x2 = min(max(x - off_x,x1+25),parentWidth)
        elif index == 3:
            x1 = min(max(x - off_x,0),x2-25,parentWidth-25)
        elif index == 5:
            x2 = min(max(x - off_x,x1+25),parentWidth)
        elif index == 6:
            x1 = min(max(x - off_x,0),x2-25,parentWidth-25)
            y2 = min(max(y - off_y,y1+25),parentHeight)
        elif index == 7:
            y2 = min(max(y - off_y,y1+25),parentHeight)
        elif index == 8:
            x2 = min(max(x - off_x,x1+25),parentWidth)
            y2 = min(max(y - off_y,y1+25),parentHeight)
        self.place(in_ = parent, x = x1, y = y1,
                   width = (x2 - x1), height = (y2 - y1))
        self.resizing = False


    def make_inner_window_bindings (self, button):
        """The hard part: associate bindings to the window corners and to 
        the title bar. This is very long and very ugly; but can it be done
        in another way?
        """
        # The frame
        f = self.interior()
        f.bind("<1>", self.mwraise )
        f.bind("<Enter>", self.in_inner_window)
        f.bind("<Motion>", self.in_inner_window)
        f.bind("<B1-Motion>", self.resize_inner_window)
        # Title label
        self.component('label').bind("<1>", self.inner_raise_set)
        self.component('label').bind("<B1-Motion>", self.inner_place_set)
        self.component('label').bind("<2>", self.inner_lower_set)
        if button:
            # The Destroy button
            button.bind("<Double-1>",
                        lambda event: self.after_idle(self.destroy))




Pmw.forwardmethods(MultipleWin, Frame, MultipleWin.interior)
Pmw.forwardmethods(InnerWindow, Frame, InnerWindow.interior)
