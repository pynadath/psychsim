from teamwork.utils.FriendlyFloat import simpleFloat
from Tkinter import StringVar,Scale,Radiobutton,Button
import Pmw

def blend(color1,color2,percentage):
    """
    Generates a color a given point between two extremes.  If the percentage is less than 0, then color1 is returned.  If over 1, then color2 is returned.
    @param color1,color2: the two colors representing the opposite ends of the spectrum
    @type color1,color2: str
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

class MultiScale(Pmw.MegaWidget):
    def __init__(self,parent=None,**kw):
        optiondefs = (
            ('expert',       0,    self.setExpert),
            ('orient',     'horizontal', Pmw.INITOPT),
            ('lo',         0.,           Pmw.INITOPT),
            ('hi',         1.,           Pmw.INITOPT),
            ('resolution', 0.01,         Pmw.INITOPT),
            ('locolor',    '#ffffff',    Pmw.INITOPT),
            ('hicolor',    '#000000',    Pmw.INITOPT),
            ('command',    None,         None),
            ('disabledforeground',None,None),
            ('foreground',None,self.setForeground),
            ('background',None,self.setBackground),
            ('sort',       cmp,          Pmw.INITOPT),
            ('state',      'normal',     self.setState),
            ('toggle', None, Pmw.INITOPT),
            ('modifiable', True, Pmw.INITOPT)
            )
        self.defineoptions(kw,optiondefs)
        self.selected = StringVar()
        Pmw.MegaWidget.__init__(self,parent)
        self.span = float(self['hi'])-float(self['lo'])
        widget = self.createcomponent('box',(),None,Pmw.ButtonBox,
                                      (self.interior(),),
                                      )
        if self['modifiable']:
            widget.grid(columnspan=2,row=0,column=0)

        if self['orient'] == 'horizontal':
            self.interior().grid_columnconfigure(0,weight=0)
            self.interior().grid_columnconfigure(1,weight=1)
        self.initialiseoptions(MultiScale)
        widget = Button(self.interior())
        if self['disabledforeground'] is None:
            self['disabledforeground'] = widget.cget('disabledforeground')
        if self['foreground'] is None:
            self['foreground'] = widget.cget('foreground')
        if self['background'] is None:
            self['background'] = widget.cget('background')
        
    def setState(self):
        """Sets the state to the given value (NORMAL/DISABLED/?)"""
        if not isinstance(self,DistributionScale) and self['state'] == 'disabled':
            raise UserWarning
        widget = self.component('box')
        for button in widget.components():
            if not button in ['frame','hull','label']:
                button = widget.component(button)
                button.configure(state=self['state'])
        if self['state'] == 'disabled':
            fg = self['disabledforeground']
        else:
            fg = self['foreground']
        labels = self.labels()
        if len(labels) > 1:
            for label in labels:
                self.component(label).configure(state=self['state'],
                                                foreground=fg)

    def setForeground(self):
        if self['state'] == 'disabled':
            fg = self['disabledforeground']
        else:
            fg = self['foreground']
        widget = self.component('box')
        for label in widget.components():
            if widget.componentgroup(label) == 'Button':
                widget.component(label).configure(fg=fg)
        labels = self.labels()
        if len(labels) > 1:
            for label in labels:
                self.component(label).configure(foreground=fg)

    def setBackground(self):
        if self['state'] == 'disabled':
            bg = self['disabledbackground']
        else:
            bg = self['background']
        self.component('hull').configure(bg=self['background'])
        widget = self.component('box')
        for label in widget.components():
            if widget.componentgroup(label) == 'Button':
                widget.component(label).configure(bg=bg)
        labels = self.labels()
        if len(labels) > 1:
            for label in labels:
                self.component(label).configure(bg=bg)
                
    def set(self,label,value):
        """Sets the scale named 'label' to the given value"""
        try:
            widget = self.component(self.generateName(label))
        except KeyError:
            widget = self.addScale(label,value)
        cmd = self['command']
        self['command'] = None
        state = widget.cget('state')
        widget.configure(state='normal')
        widget.set(value)
        # For some reason, this state can be None some times... this is bad
        if not state:
            state = 'disabled'
        widget.configure(state=state)
        self['command'] = cmd

    def labels(self):
        """Returns all of the possible scale labels"""
        labels = filter(lambda name:name[:5] == 'scale',self.components())
        if self['sort']:
            labels.sort(self['sort'])
        return labels
    
    def get(self,label):
        """Returns the value of the scale named 'label'"""
        widget = self.component(self.generateName(label))
        return widget.get()

    def addScale(self,label,value=None,**kw):
        """Adds a new scale to this widget
        @param label: The label to be attached to this scale
        @param value: The initial value to set the scale to
        @param kw:    Additional keyword arguments to pass to the Scale widget
        """
        widgetName = self.generateName(label)
        try:
            # Check whether this widget already exists (if so, nothing to do)
            return self.component(widgetName)
        except KeyError:
            pass
        widget = self.createcomponent(widgetName,
                                      (),'scales',Scale,
                                      (self.interior(),),
                                      orient=self['orient'],
                                      label=label,
                                      from_=self['lo'],to=self['hi'],
                                      tickinterval=1.,
                                      resolution=self['resolution'],
                                      command=lambda value,s=self,l=label:\
                                      s.updateValue(l,value),
                                      **kw
                                      )
        self.createcomponent('select%s' % (label),(),'radios',Radiobutton,
                             (self.interior(),),
                             value=label,variable=self.selected)
        if value:
            self.set(label,value)
        # Set the state of the widgets correctly, according to the number of
        # sliders
        labels = self.labels()
        if len(labels) == 1:
            widget.configure(state='disabled')
        elif len(labels) == 2:
            self.configure(state='normal')
        self.reorder()
        self.selected.set(labels[0][6:])
        self.setExpert()
        return widget

    def reorder(self):
        labels = map(lambda n:n[6:],self.labels())
        # Undraw everything
        for name in self.components():
            if name[:5] == 'scale' or name[:6] == 'select' or name == 'box':
                widget = self.component(name)
                widget.grid_forget()
        # (re)Position all of the sliders
        for index in range(len(labels)):
            widget = self.component('select%s' % (labels[index]))
            if self['modifiable'] and self['orient'] == 'horizontal':
                widget.grid(row=index,column=0,sticky='')
            elif self['modifiable']:
                widget.grid(column=index,row=0,sticky='')
            widget = self.component(self.generateName(labels[index]))
            if self['orient'] == 'horizontal':
                widget.grid(row=index,column=1,sticky='EW')
            else:
                widget.grid(column=index,row=1,sticky='NS')
        widget = self.component('box')
        widget.grid(row=len(labels),columnspan=2,column=0,sticky='EW')
##        try:
##            widget = widget.component('Delete')
##        except KeyError:
##            widget = None
##        if widget:
##            if len(labels) < 2:
##                widget.configure(state=DISABLED)
##            else:
##                widget.configure(state=NORMAL)

    def deleteScale(self,label=None):
        """Callback for removing the selected scale"""
        if label is None:
            label = self.selected.get()
        self.destroycomponent('select%s' % (label))
        self.destroycomponent(self.generateName(label))
        self.reorder()
        try:
            widget = self.component('select%s' % (self.labels()[0][6:]))
            widget.invoke()
        except IndexError:
            pass
        # Check whether we're down to only one scale
        labels = self.labels()
        if len(labels) == 1:
            widget = self.component(labels[0])
            widget.configure(state='disabled')
        return label
    
    def generateName(self,label):
        """Returns canonical name for this label's component scale widget"""
##        if isinstance(label,float):
##            return 'scale %5.3f' % (label)
##        else:
        return 'scale %s' % (label)
    
    def updateValue(self,label,value):
        """Callback invoked whenever a scale value changes"""
        widget = self.component(self.generateName(label))
        percent = (float(value)-float(self['lo']))/self.span
        widget.configure(troughcolor=blend(self['locolor'],self['hicolor'],
                                           percent))
        if self['command']:
            self['command'](label,value)

    def setExpert(self):
        for label in self.labels():
            widget = self.component(label)
            widget.configure(showvalue=self['expert'])

class DistributionScale(MultiScale):
    def __init__(self,parent=None,**kw):
        optiondefs = (
            ('distribution', None, self.update),
            )
        self.defineoptions(kw,optiondefs)
        MultiScale.__init__(self,parent)
##        box = self.component('box')
##        box.add('Add',command=self.addScale)
##        box.add('Replace',command=self.replaceValue)
        self.createcomponent('newValue',(),None,Scale,
                                      (self.interior(),),
                                      orient='horizontal',
                                      tickinterval=1.,
                                      resolution=self['resolution'],
                                      from_=-1.,to=1.,
                                      showvalue=1,
                                      command=self.updateNew,
                                      )
        self.details = True
        if self['distribution'] and len(self['distribution']) == 1:
            self.toggleDetails()
        else:
            self.update()
        self.initialiseoptions(DistributionScale)

    def setState(self):
        """Sets the state to the given value (NORMAL/DISABLED/?)"""
        MultiScale.setState(self)
        widget = self.component('newValue')
        widget.configure(state=self['state'])
        if self['state'] == 'disabled':
            widget.configure(foreground=self['disabledforeground'])
        else:
            widget.configure(foreground=self['foreground'])

    def setForeground(self):
        MultiScale.setForeground(self)
        if self['state'] == 'disabled':
            fg = self['disabledforeground']
        else:
            fg = self['foreground']
        try:
            self.component('newValue').configure(foreground=fg)
        except KeyError:
            # Must be initialization; haven't created scale yet
            pass

    def setBackground(self):
        MultiScale.setBackground(self)
        if self['state'] == 'disabled':
            bg = self['disabledbackground']
        else:
            bg = self['background']
        try:
            self.component('newValue').configure(bg=bg)
        except KeyError:
            # Must be initialization; haven't created scale yet
            pass
        
    def update(self):
        """Redraws the scales to correspond to the current distribution"""
        if self['distribution'] is None:
            return
        if self['modifiable'] and (len(self['distribution']) > 1 or self.details):
            widget = self.component('box')
            try:
                widget.component('Replace')
            except KeyError:
                widget.insert('Replace',0,command=self.replaceValue)
                widget.insert('Delete',0,command=self.deleteScale)
                widget.insert('Add',0,command=self.addScale)
        if len(self['distribution']) > 1 or self.details:
            valid = []
            for value in self['distribution'].domain():
                prob = self['distribution'][value]
                try:
                    widget = self.component(self.generateName(value))
                except KeyError:
                    widget = self.addScale(value)
                self.set(value,prob)
                valid.append(widget)
            for label in self.components():
                if label[:5] == 'scale':
                    widget = self.component(label)
                    if not widget in valid:
                        self.destroycomponent(label)
            self.reorder()
        elif self['modifiable']:
            widget = self.component('newValue')
            state = widget.cget('state')
            widget.configure(state='normal')
            value = self['distribution'].keys()[0]
            widget.set(value)
            if state != 'normal':
                widget.configure(state=state)
            widget.grid(row=0,columnspan=2,column=0,sticky='EW')
            for name in self.components():
                if self.componentgroup(name) in ['scales','radios']:
                    self.component(name).grid_forget()
            widget = self.component('box')
            widget.grid(row=1,columnspan=2,column=0,sticky='EW')
            try:
                widget.component('Delete')
                widget.delete('Delete')
                widget.delete('Add')
                widget.delete('Replace')
            except KeyError:
                pass

    def reorder(self):
        MultiScale.reorder(self)
        index = len(self.labels())+1
        if self['modifiable']:
            self.component('newValue').grid(row=index,
                                            columnspan=2,column=0,sticky='EW')

    def updateNew(self,value):
        widget = self.component('newValue')
        widget.configure(troughcolor=blend('#ff0000','#00ff00',
                                           (float(value)+1.)/2.))
        if not self.details:
            self['distribution'].clear()
            self['distribution'][float(value)] = 1.
            if self['command']:
                self['command'](None,value)
            
    def updateValue(self,label,value):
        """Callback invoked whenever a scale value changes"""
        MultiScale.updateValue(self,label,value)
        epsilon = self['distribution'].epsilon
        if abs(self['distribution'][label]-float(value)) > epsilon:
            # Must re-normalize
            try:
                factor = (1.-float(value))/(1.-self['distribution'][label])
            except ZeroDivisionError:
                try:
                    factor = (1.-float(value))/\
                             float(len(self['distribution'])-1)
                except ZeroDivisionError:
                    factor = 1.
            for row in self['distribution'].keys():
                if row == label:
                    self['distribution'][row] = float(value)
                else:
                    if self['distribution'][row]:
                        self['distribution'][row] *= factor
                    else:
                        # Previously 0
                        self['distribution'][row] = factor
                    self.set(row,self['distribution'][row])
            if self['command']:
                self['command'](label,value)

    def addScale(self,label=None):
        if label is None:
            label = self.component('newValue').get()
            if not self['distribution'].has_key(label):
                if len(self['distribution']) > 0:
                    self['distribution'][label] = 0.
                else:
                    self['distribution'][label] = 1.
        if len(self['distribution']) > 1:
            if self['toggle']:
                widget = self['toggle']
            else:
                try:
                    widget = self.component('box').button('Make Deterministic')
                except ValueError:
                    box = self.component('box')
                    widget = box.add('Make Deterministic',
                                     command=self.toggleDetails,width=15)
            widget.configure(state='disabled')
            self.details = True
        widget = MultiScale.addScale(self,label,self['distribution'][label])
        widget.configure(label=self.labelValue(label))
        return widget

    def replaceValue(self):
        self.deleteScale()
        self.addScale()
            
    def deleteScale(self,label=None):
        """Removes the selected value and re-normalizes"""
        if label is None:
            label = float(self.selected.get())
        MultiScale.deleteScale(self,label)
        mass = self['distribution'][label]
        total = round(1.0 - mass,10)
        del self['distribution'][label]
        for row,prob in self['distribution'].items():
            try:
                ratio = prob/total
            except ZeroDivisionError:
                ratio = 1./float(len(self['distribution']))
            self['distribution'][row] += mass*ratio
            self.set(row,self['distribution'][row])
        if len(self['distribution']) == 1:
            if self['toggle']:
                widget = self['toggle']
            else:
                widget = self.component('box').button('Make Deterministic')
            widget.configure(state='normal')

    def labelValue(self,value):
        """Returns the expert-sensitive label for the given value"""
        if isinstance(value,str):
            return value
        try:
            num = float(value)
        except ValueError:
            return value
        if self['expert']:
            return '%4.2f' % (num)
        else:
            return simpleFloat(num)
        
    def setExpert(self):
        """Configure the scales according to the current expert mode"""
        if self['distribution'] is None:
            return
        if self.details:
            for value in self['distribution'].keys():
                try:
                    widget = self.component(self.generateName(value))
                    widget.configure(showvalue=self['expert'])
                    widget.configure(label=self.labelValue(value))
                except KeyError:
                    # Haven't drawn this scale yet
                    pass
        widget = self.component('newValue')
        widget.configure(showvalue=self['expert'])
        if self['expert']:
            widget.configure(resolution=self['resolution'])
            if self['toggle'] is None:
                box = self.component('box')
                try:
                    widget = box.add('Make Deterministic',
                                     command=self.toggleDetails,width=15)
                except ValueError:
                    widget = None
                if widget:
                    self.details = True
                    self.toggleDetails(False)
        else:
            widget.configure(resolution=0.1)
            if self['toggle'] is None:
                box = self.component('box')
                try:
                    box.delete('Make Deterministic')
                except ValueError:
                    pass
        MultiScale.setExpert(self)

    def toggleDetails(self,update=True):
        self.details = not self.details
        if self['toggle']:
            widget = self['toggle']
        else:
            try:
                widget = self.component('box').button('Make Deterministic')
            except ValueError:
                widget = None
        if widget:
            if self.details:
                widget.configure(text='Make Deterministic')
            else:
                widget.configure(text='Make Probabilistic')
            if update:
                self.update()
    
if __name__ == '__main__':
    import unittest
    from teamwork.test.widgets.testMultiscale import *

    unittest.main()
