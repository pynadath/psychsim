from Tkinter import Label,Scale,Frame
import Pmw
import tkMessageBox
import threading
from teamwork.widgets.images import loadImages
from teamwork.math.probability import Distribution

class PMFScale(Pmw.MegaWidget):
    """
    Widget for displaying a probability mass function (PMF)
    @ivar map: mapping from row index to distribution element
    @type map: dict
    @ivar lock: a C{Lock} used to avoid asynchronyous update problems
    @type lock
    @cvar epsilon: threshold for determining zero probabilites
    @type epsilon: float
    """
    epsilon = 1e-10

    def __init__(self,parent=None,**kw):
        self.map = {}
        self.lock = threading.Lock()
        optiondefs = (
            ('distribution',Distribution(), self.setDistribution),
            ('state','normal',self.setState),
            ('viewprobs',False,self.setView),
            ('command',None,None), # lambda <my name>: ...
            ('fg',None,self.setColor),
            ('bg',None,self.setColor),
            ('floatdomain',True,Pmw.INITOPT),
            ('editable',True,Pmw.INITOPT),
            # Callbacks for expand/collapse options
            ('expand',None,Pmw.INITOPT),
            ('collapse',None,Pmw.INITOPT),
            # Callback for selecting a domain element
            ('select',None,Pmw.INITOPT),
            # Prompt for deletion if probability set to 0
            ('deleteIfZero',True,None),
            # All sliders must sum to 1. if True
            ('normalize',True,None),
            ('usePIL',True,Pmw.INITOPT),
            )
        self.defineoptions(kw,optiondefs)
        Pmw.MegaWidget.__init__(self,parent)
        if self['expand']:
            self.interior().grid_columnconfigure(0,weight=0)
            self.images = loadImages({'minus': 'icons/minus.gif',
                                      'plus': 'icons/plus.gif',},
                                     self['usePIL'])
            self.start = 1
        else:
            self.images = {}
            self.start = 0
        if self['floatdomain']:
            self.interior().grid_columnconfigure(self.start+0,weight=0)
        else:
            self.interior().grid_columnconfigure(self.start+0,weight=1)
        self.interior().grid_columnconfigure(self.start+1,weight=2)
        self.interior().grid_columnconfigure(self.start+2,weight=0)
        self.initialiseoptions(PMFScale)
                             
    def makeRow(self,row,element):
        """Creates the widgets in the given row of the scale
        @param row: the row to put the widgets on
        @type row: int
        @param element: the element for this row (in whatever form it is)
        """
        offset = 0
        if self['expand']:
            for other in range(row):
                if self.isExpanded(other):
                    offset += 1
        if self['expand']:
            # Create expandable bit
            button = self.createcomponent('view%d' % (row),(),'element',
                                          Label,(self.interior(),),
                                          font=('Courier','24'))
            if self['usePIL']:
                button.configure(image=self.images['plus'])
            else:
                button.configure(text='+')
            button.bind('<ButtonRelease-1>',self.expand)
            button.grid(row=offset+row,column=0)
        # Create entry for element value
        self.map[row] = element
        cmd = lambda s=self,r=row: s.setElement(r)
        widget = self.createcomponent('elem%d' % (row),(),'element',
                                      Pmw.EntryField,
                                      (self.interior(),),
                                      hull_bg=self['bg'],
                                      entry_fg=self['fg'],
                                      entry_bg=self['bg'],
                                      command=cmd)
        if self['floatdomain']:
            widget.configure(entry_width=4)
            widget.grid(row=offset+row,column=self.start+0)
        else:
            widget.configure(entry_bd=0)
            widget.grid(row=offset+row,column=self.start+0,sticky='ew')
        if not self['editable']:
            widget.configure(entry_state='readonly')
        if self['select']:
            widget.component('entry').bind('<ButtonRelease-1>',self.select)
        label = getLabel(element)
        if widget.get() != label:
            widget.setvalue(label)
        # Create scale for element value
        cmd = lambda value,s=self,r=row: s.update(r,value)
        widget = self.createcomponent('scal%d' % (row),(),'element',
                                      Scale,(self.interior(),),
                                      orient='horizontal',
                                      fg=self['fg'],bg=self['bg'],
                                      resolution=0.01,command=cmd,
                                      to=1.,showvalue=False)
        if self['viewprobs']:
            widget.configure(from_=0.)
            self.setSlider(row,self['distribution'][element])
        else:
            widget.configure(from_=-1.)
            self.setSlider(row,element)
        widget.grid(row=offset+row,column=self.start+1,sticky='ew')
        # Create probability indicator
        cmd = lambda s=self,r=row: s.setProbability(r)
        widget = self.createcomponent('prob%d' % (row),(),'element',
                                      Pmw.EntryField,
                                      (self.interior(),),
                                      validate={'min':0,'max':100,
                                                'validator':'integer'},
                                      labelpos='e',label_text='%',
                                      label_bg=self['bg'],
                                      label_fg=self['fg'],
                                      hull_bg=self['bg'],
                                      entry_fg=self['fg'],
                                      entry_bg=self['bg'],
                                      entry_justify='right',
                                      entry_width=3,command=cmd)
        widget.setvalue('%d' % (100*self['distribution'][element]))
        # Enable probability slider iff more than one element in distribution
        if len(self['distribution']) > 1 and self['state'] == 'normal':
            widget.configure(entry_state='normal')
        else:
            widget.configure(entry_state='disabled')
        widget.grid(row=offset+row,column=self.start+2)

    def setDistribution(self):
        """Updates the scales to reflect the current distribution
        """
        self.map.clear()
        elements = self['distribution'].domain()
        elements.sort()
        # Hide unneeded widgets
        for name in self.components():
            if self.componentgroup(name) == 'element':
                if int(name[4:]) >= len(elements):
                    self.component(name).grid_forget()
        offset = 0
        for row in range(len(elements)):
            # Check whether this row already exists; otherwise, create it
            try:
                widget = self.component('elem%d' % (row))
            except KeyError:
                if self.lock.acquire():
                    self.makeRow(row,elements[row])
                    self.lock.release()
            if self['expand']:
                self.component('view%d' % (row)).grid(row=offset+row,column=0)
            # Create entry for element value
            element = elements[row]
            self.map[row] = element
            widget = self.component('elem%d' % (row))
            if self['floatdomain']:
                widget.grid(row=offset+row,column=self.start+0)
            else:
                widget.grid(row=offset+row,column=self.start+0,sticky='ew')
            label = getLabel(element)
            if widget.get() != label:
                widget.setvalue(label)
            # Create scale for element value
            widget = self.component('scal%d' % (row))
            if self['viewprobs']:
                self.setSlider(row,self['distribution'][element])
            else:
                self.setSlider(row,element)
            widget.grid(row=offset+row,column=self.start+1,sticky='ew')
            # Create probability indicator
            widget = self.component('prob%d' % (row))
            widget.setvalue('%d' % (100*self['distribution'][element]))
            # Enable probability slider iff more than one element in distribution
            if len(self['distribution']) > 1 and self['state'] == 'normal':
                widget.configure(entry_state='normal')
            else:
                widget.configure(entry_state='disabled')
            widget.grid(row=offset+row,column=self.start+2)
            if self['expand'] and self.isExpanded(row):
                offset += 1
                self.component('pane%d' % (row)).grid(row=offset+row,column=1,
                                                      columnspan=3,sticky='ewns')
                
    def setTroughColor(self,row,value):
        """Sets the trough color of the given slider for the given value
        """
        widget = self.component('scal%d' % (row))
        if self['viewprobs']:
            percent = value
            lo,hi = '#ffffff','#000000'
        else:
            percent = (float(value)+1.)/2.
            lo,hi = '#ff0000','#00ff00'
        widget.configure(troughcolor=blend(lo,hi,percent))

    def setSlider(self,row,value):
        """Sets the given slider to the given value
        """
        self.setTroughColor(row,value)
        self.component('scal%d' % (row)).set(value)

    def addElement(self,new=None,value=None):
        """Add a new element to distribution
        """
        if new is None:
            # Find a new value not in domain
            new = 0.
            while new in self['distribution'].domain():
                if new > self.epsilon:
                    new = -new
                else:
                    new += 0.01
        if value is None:
            value = 0.
        self['distribution'][new] = value
        self.setDistribution()

    def setView(self):
        """Switch sliders to show elements or probabilities as appropriate
        """
        row = 0
        while True:
            try:
                widget = self.component('scal%d' % (row))
            except KeyError:
                break
            if self['viewprobs']:
                self.setSlider(row,self['distribution'][self.map[row]])
                widget.configure(from_=0.)
            else:
                widget.configure(from_=-1.)
                self.setSlider(row,float(self.map[row]))
            row += 1

    def setElement(self,row):
        """Callback for element entry field
        """
        widget = self.component('elem%d' % (row))
        new = widget.getvalue()
        if self['floatdomain']:
            new = float(new)
        if self['viewprobs']:
            # Not viewing element, but need to update behind the scenes
            self.updateElement(row,new)
            if self['command'] and self.lock.acquire(False):
                self['command'](self)
                self.lock.release()
        else:
            # Update the visible scale and let the callback handle the rest
            self.component('scal%d' % (row)).set(float(new))

    def setProbability(self,row):
        """Callback for probability entry field
        """
        widget = self.component('prob%d' % (row))
        new = float(widget.getvalue())/100.
        if self['viewprobs']:
            # Update the visible scale and let the callback handle the rest
            if self.lock.acquire(False):
                self.component('scal%d' % (row)).set(float(new))
                self.lock.release()
        else:
            # Not viewing probability, but need to update behind the scenes
            self.updateProbability(row,new)
            if self['command'] and self.lock.acquire(False):
                self['command'](self)
                self.lock.release()
        
    def update(self,row,new=None):
        """Slider callback"""
        new = float(new)
        if self['viewprobs']:
            if self.lock.acquire(False):
                change = self.updateProbability(row,new)
                if self['deleteIfZero'] and change and new < self.epsilon:
                    # Handle deletion of element if zero probability
                    element = self.map[row]
                    if self['floatdomain']:
                        msg = 'Would you like to delete element %5.2f?' % (element)
                    else:
                        msg = 'Would you like to delete element %s?' % (element)
                    if tkMessageBox.askyesno('Delete?',msg):
                        del self['distribution'][element]
                        self.setDistribution()
                self.lock.release()
        else:
            # Change the element for this scale
            if self.updateElement(row,new):
                self.component('elem%d' % (row)).setvalue(getLabel(new))
                self.setTroughColor(row,new)
        # Do callback (only once)
        if self['command'] and self.lock.acquire(False):
            self['command'](self)
            self.lock.release()

    def updateElement(self,row,new):
        """Updates an element in the distribution based on a change 
        (slider or entry)
        @return: C{True} if there is any change; otherwise, C{False}
        @rtype: bool
        """
        old = self.map[row]
        if old != new:
            if new in self['distribution'].domain():
                # Duplicate! Run for the hills!
                tkMessageBox.showwarning('Duplicate!','Duplicate elements are not allowed.')
                return False
            else:
                prob = self['distribution'][old]
                del self['distribution'][old]
                self['distribution'][new] = prob
                self.map[row] = new
                return True
        else:
            return False

    def updateProbability(self,row,new):
        """Updates an probability in the distribution based on a change 
        (slider or entry)
        @return: C{True} if there is any change; otherwise, C{False}
        @rtype: bool
        """
        if len(self['distribution']) == 1:
            return False
        element = self.map[row]
        # Figure out much probability mass must be re-distributed
        mass = self['distribution'][element] - new
        if abs(mass) < self.epsilon:
            return False
        # Update new set value
        self['distribution'][self.map[row]] = new
        if self['viewprobs']:
            self.setTroughColor(row,new)
        self.component('prob%d' % (row)).setvalue('%d' % (100*new))
        # Normalize if necessary
        while abs(mass) > self.epsilon and self['normalize']:
            rows = self.map.keys()
            rows.remove(row)
            count = float(len(rows))
            for otherRow in rows[:]:
                otherElement = self.map[otherRow]
                delta = mass/count
                if delta > 0.:
                    if self['distribution'][otherElement] + delta < 1.:
                        self['distribution'][otherElement] += delta
                        mass -= delta
                    else:
                        mass -= 1.-self['distribution'][otherElement]
                        self['distribution'][otherElement] = 1.
                        rows.remove(otherRow)
                else:
                    if self['distribution'][otherElement] + delta > 0.:
                        self['distribution'][otherElement] += delta
                        mass -= delta
                    else:
                        mass -= -self['distribution'][otherElement]
                        self['distribution'][otherElement] = 0.
                        rows.remove(otherRow)
                if self['viewprobs']:
                    self.setSlider(otherRow,self['distribution'][otherElement])
                text = '%d' % (100*self['distribution'][otherElement])
                self.component('prob%d' % (otherRow)).setvalue(text)
        return True

    def setState(self):
        row = 0
        while True:
            try:
                widget = self.component('elem%d' % (row))
            except KeyError:
                # Already done all of the rows
                break
            if self['floatdomain']:
                widget.configure(entry_state=self['state'])
            self.component('scal%d' % (row)).configure(state=self['state'])
            if self['state'] == 'disabled' or len(self['distribution']) > 1:
                self.component('prob%d_entry' % (row)).configure(state=self['state'])
            row += 1

    def select(self,event):
        event.widget.select_range(0,'end')
        self['select'](event.widget.get())
            
    def expand(self,event):
        for name in self.components():
            if self.component(name) is event.widget:
                break
        else:
            raise NameError,'Unable to find widget'
        row = int(name[4:])
        if self.isExpanded(row):
            # Collapse
            if self['collapse']:
                self['collapse'](self.map[row])
            self.destroycomponent('pane%d' % (row))
            if self['usePIL']:
                event.widget.configure(image=self.images['plus'])
            else:
                event.widget.configure(text='+')
        else:
            # Expand
            frame = self.createcomponent('pane%d' % (row),(),None,Frame,
                                         (self.interior(),),bd=1,relief='groove')
            self['expand'](self.map[row],frame)
            if self['usePIL']:
                event.widget.configure(image=self.images['minus'])
            else:
                event.widget.configure(text='-')
        self.setDistribution()

    def isExpanded(self,row):
        """
        @param row: the row of interest
        @type row: int
        @return:  C{True} iff the given row's details pane is expanded
        @rtype: bool
        """
        widget = self.component('view%d' % (row))
        if self['usePIL']:
            return str(widget.cget('image')) == str(self.images['minus'])
        else:
            return str(widget.cget('text')) == '-'
            
    def setColor(self):
        """Updates the foreground and background colors for all component widgets
        """
        self.interior().configure(bg=self['bg'])
        row = 0
        while True:
            try:
                widget = self.component('elem%d' % (row))
            except KeyError:
                # Already done all of the rows
                break
            widget.component('entry').configure(fg=self['fg'],bg=self['bg'])
            widget.component('hull').configure(bg=self['bg'])
            self.component('scal%d' % (row)).configure(fg=self['fg'],bg=self['bg'])
            self.component('prob%d_entry' % (row)).configure(fg=self['fg'],
                                                             bg=self['bg'])
            self.component('prob%d_label' % (row)).configure(fg=self['fg'],
                                                             bg=self['bg'])
            self.component('prob%d_hull' % (row)).configure(bg=self['bg'])
            row += 1

def blend(color1,color2,percentage):
    """
    Generates a color a given point between two extremes.  If the percentage is less than 0, then color1 is returned.  If over 1, then color2 is returned.
    @param color1,color2: the two colors representing the opposite ends of the spectrum
    @type color1: str
    @type color2: str
    @param percentage: the percentage of the spectrum between the two where this point is (0. represents color1, 1. represents color2)
    @type percentage: float
    @return: string RGB blending two colors (string RGB) by float percent
    @rtype: str
    """
    red1 = int(color1[1:3],16)
    red2 = int(color2[1:3],16)
    green1 = int(color1[3:5],16)
    green2 = int(color2[3:5],16)
    blue1 = int(color1[5:7],16)
    blue2 = int(color2[5:7],16)
    hi = {'r':max(red1,red2),'g':max(green1,green2),'b':max(blue1,blue2)}
    lo = {'r':min(red1,red2),'g':min(green1,green2),'b':min(blue1,blue2)}
    red =  (1.-percentage)*float(red1) + percentage*float(red2)
    red = min(max(red,lo['r']),hi['r'])
    green =  (1.-percentage)*float(green1) + percentage*float(green2)
    green = min(max(green,lo['g']),hi['g'])
    blue =  (1.-percentage)*float(blue1) + percentage*float(blue2)
    blue = min(max(blue,lo['b']),hi['b'])
    return '#%02x%02x%02x' % (red,green,blue)

def getLabel(element):
    """Generates a canonical string representation of an element
    @rtype: str
    """
    if isinstance(element,float):
        return '%5.2f' % (element)
    elif isinstance(element,int):
        return '%d' % (element)
    else:
        return str(element)
