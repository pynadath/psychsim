from teamwork.math.Interval import *

from Tkinter import *
import Pmw

class IntervalScale(Pmw.MegaWidget):
    """ Megawidget containing a scale, confidence and an indicator.
    """
    confidenceValues = ['lo', 'med', 'hi']
    
    def __init__(self, parent = None, **kw):
        # Define the megawidget options.
        optiondefs = (
	    ('color',       1,                None),
	    ('confidence',  1,                Pmw.INITOPT),
	    ('orient',      'vertical',       Pmw.INITOPT),
	    ('labelmargin', 0,                Pmw.INITOPT),
	    ('labelpos',    'w',             Pmw.INITOPT),
            ('text',        '',               Pmw.INITOPT),
            ('showvalue',   0,                self.showValue),
	    ('threshold',   (50,),            None),
	    ('value',       None,             None),
        )
        self.defineoptions(kw, optiondefs)

        # Initialise base class (after defining options).
        Pmw.MegaWidget.__init__(self, parent)

        # Create the components.
        interior = self.interior()

        # Create the indicator component.
        # self.indicator = self.createcomponent('indicator',
        #                                      (), None,
        #                                     Frame, interior,
        #                                      width = 16,
        #                                      height = 16,
        #                                      borderwidth = 2,
        #                                      relief = 'raised')

##        # Create the value component.
##        self.value = self.createcomponent('value', (), None,
##                                          Label, interior, width = 3)
        self.group = self.createcomponent('Group', (), None,
                                          Pmw.Group, interior,
                                          tag_text=self['text'],
                                          tag_font=('Helvetica',14,'bold'))
        widget = self.group.component('tag')
        self.activeFG = widget.cget('activeforeground')
        self.disabledFG = widget.cget('disabledforeground')
        # Create the scale component.
	if self['orient'] == 'vertical':
	    # The default scale range seems to be
	    # the wrong way around - reverse it.
	    from_ = 100
	    to = 0
	else:
	    from_ = 0
	    to = 100

        # Draw scale widget
        self.scale = self.createcomponent('scale',
                                          (), None, Scale,
                                          self.group.interior(),
                                          orient = self['orient'],
                                          # command = self.__doCommand,
##                                          showvalue = 0,
                                          length = 200,
                                          from_ = from_,
                                          to = to)


	if self['orient'] == 'vertical':
            self.scale.pack(side=LEFT,fill=Y,expand=YES)
	else:
            self.scale.pack(side=TOP,fill=X,expand=YES)

        # Frame for any buttons
        self.buttonFrame = Frame(self.group.interior())
        # Draw confidence widget, if applicable
        if self['confidence']:
            self.radio = self.createcomponent('radio',(),None,
                                              Pmw.OptionMenu,
                                              self.buttonFrame,
                                              menubutton_width=3,
                                              labelpos='w',
                                              label_text='Confidence:',
                                              items=self.confidenceValues
                                              )
            self.radio.pack(side=LEFT,fill=Y,expand=YES)
##            self.radio = self.createcomponent('radio',
##                                              (), None, Pmw.RadioSelect,
##                                              self.group.interior(),
##                                              buttontype = 'radiobutton',
##                                              labelpos = 'w',
##                                              label_text = 'Confidence:',
##                                              hull_borderwidth = 0,
##                                              hull_relief = 'ridge',
##                                              hull_width = 2,
##                                              frame_width = 2,
##                                              pady = 1,
##                                              padx = 1,
##                                              hull_height = 2,
##                                              frame_height = 2,
##                                              orient = self['orient'],
##                                              # command = self.__doCommand2,
##                                              )
##            for text in self.confidenceValues:
##                self.radio.add(text)
##            if self['orient'] == 'vertical':
##                self.radio.pack(side=LEFT,fill=Y,expand=YES)
##            else:
##                self.radio.pack(side=TOP,fill=X,expand=YES)
        else:
            self.radio = None
        val = self['value']
        self.setter(val)
        # Check keywords and initialise options.
        self.initialiseoptions()
        self.buttonFrame.pack()
        self.group.pack(side=TOP,fill=X,expand=YES)

    def showValue(self):
        """Configures the value visibility on the scale"""
        self.scale.configure(showvalue=self['showvalue'])
        
    def setter(self, val):
        if val is not None:
           conf = (val.hi - val.lo) / 2.0
           state = self.scale.cget('state')
           if state != NORMAL:
               self.scale.configure(state=NORMAL)
           self.scale.set(val.mean())
           self.scale.configure(state=state)
           if conf >= .4:
               self.radio.invoke('lo')
           elif conf < .2:
               self.radio.invoke('hi')
           else:
               self.radio.invoke('med')

    def get(self):
        mean = self.scale.get()
        confidence = self.radio.getcurselection()
        if confidence == 'lo':
            span = 0.4
        elif confidence == 'med':
            span = 0.2
        else:
            span = 0.0
        return Interval(mean-span,mean+span)
    
    def __doCommand(self, valueStr):
	valueInt = self.scale.get()
        bottom = float(self['scale_from'])
        span = float(self['scale_to'])-bottom
        percent = (float(valueInt)-bottom)/span
        if self['color']:
            newColor = '#%02x%02x00' % \
                       (int((1.0-percent)*255.),int(percent*255.))
        else:
            value = int((1.0-percent)*255.)
            newColor = '#%02x%02x%02x' % (value,value,value)
        self.scale.configure(troughcolor=newColor)
##	self.value.configure(text = valueStr)

    def setState(self,state=NORMAL):
        """Disables all editing widgets"""
        widget = self.group.component('tag')
        widget.configure(state=state)
        self.scale.configure(state=state)
        if state == NORMAL:
            self.scale.configure(fg=self.activeFG)
        else:
            self.scale.configure(fg=self.disabledFG)
        if self['confidence']:
            self.radio.component('menubutton').configure(state=state)
            if state == NORMAL:
                self.radio.component('label').configure(fg=self.activeFG)
            else:
                self.radio.component('label').configure(fg=self.disabledFG)
