# ---------------------- HelloBlt.py ----------------------
# 
# This program demonstrates more basic functionality like 
# making buttons to control showing of symbols, grids etc.
# The example also shows how to make animated graphs and 
# how to plot the graphs more or less smooth.
# 

import math                  # import the sin-function
from Tkinter import *        # The Tk package
import Pmw                   # The Python MegaWidget package


gcolors = ['#bb0000', '#ccaa00', '#00bb00', '#0000bb', '#aa00aa', '#000000']

gstate = ['militarypower', 'economicpower', 'hardship']

chrome = '#efefef'
bronze = '#7e5b41'
ltbronze = '#9e7b61'

class GrapherWin:

    def __init__(self, win, entities, type='state'):
        self.master = win.frame
        self.step = -1
        self.rel = type
        self.entity = entities.members()[0]
        self.entities = entities
        self.smoothing='linear'
        self.symbols  = 0
        self.color = {}
        self.color['militarypower'] = '#ff2050'
        self.color['economicpower'] = '#00ff00'
        self.color['hardship'] = '#a0a0a0'
	self.names = map(lambda e:e.name, entities.members())


        
        self.bframe = Frame(self.master,
                            # background = 'tan',
                            borderwidth = 1,
                            # highlightbackground = bronze,
                            # highlightcolor = 'gold',
                            highlightthickness = 1,
                            relief = RAISED)

        self.bframe.pack(side='top', expand=1, fill = 'x')
        self.relbuttons = Pmw.OptionMenu(self.bframe, labelpos='w',
                                         label_text=":", command= lambda type,s=self:s.dorels(type))
        self.enbuttons = Pmw.OptionMenu(self.bframe, labelpos='w',
                                        label_text="Entity", command=lambda t,s=self:s.docurves(t))
        self.enbuttons.pack(side = 'left', padx=1, pady=1)
        self.relbuttons.pack(side = 'left', padx=1, pady=1)
        # Initialize colors
        i = 0
        for n in self.entities.members():
            self.color[n.name] = gcolors[i % len(gcolors)]
            i = i + 1
        # Initialize graph vectors
        self.vector_x = Pmw.Blt.Vector()
        self.vector_y = {}
        for n in self.entities.members():
            self.vector_y[n.name] = {}
            for n2 in gstate:
                self.vector_y[n.name][n2] = Pmw.Blt.Vector()
            for n2 in self.entities.members():
                if n.name != n2.name:
                    self.vector_y[n.name][n2.name] = Pmw.Blt.Vector()

        self.relbuttons.setitems(['State', 'Support_For'], 1)
        self.enbuttons.setitems(map(lambda e:e.name, self.entities.members()), 0)
        
        
        self.explorerPane = Pmw.PanedWidget(self.master, orient='vertical')
        self.explorerPane.pack(side=TOP,
                               expand=YES,
                               fill=BOTH)
        self.gpane = self.explorerPane.add('graphPane', min=.3)
        self.tpane = self.explorerPane.add('textPane', min=.1, size = 20)
        self.gpane.pack()
        self.tpane.pack()



        self.g = Pmw.Blt.Stripchart(self.gpane)   # make a new graph area
        self.g.xaxis_configure(min="0.0")
        self.g.xaxis_configure(subdivisions="1")
        self.g.xaxis_configure(majorticks="")
        self.loadHistory()
##        tickList = (0.,1.)
##        for i in range(1,len(self.vector_x)):
##            tickList = tickList + (float(i+1),)
##        self.g.xaxis_configure(majorticks=tuple(tickList))
##            self.g.xaxis_configure(max="1.0")
        self.g.xaxis_configure(title="Time")
        self.g.xaxis_configure(stepsize="1.0")
        self.g.yaxis_configure(min="-1.0")
        self.g.yaxis_configure(max="1.0")
        self.g.pack(expand=1, fill='both')
        self.scrotxt = Pmw.ScrolledText(self.tpane)
        self.scrotxt.pack(expand=1, fill='both')
        self.scrotxt.tag_config('bolden', font = ("Helvetica", 10, "bold"))

        self.g.configure(title=self.rel)          # enter a title
        # self.g.grid_configure(hide=0,                    # show 
        #                      color="blue",              # with blue color
        #                      dashes=15)                 # and large dashes
                           
        # make s row of buttons
        self.opbuttons = Pmw.RadioSelect(self.bframe,
                                         labelpos='w', label_text='Options',
                                         command =lambda b,s=self:s.doopt(b),
                                         frame_borderwidth = 2,
                                         frame_relief = 'ridge'
                                         )
        self.opbuttons.pack(side='left', padx=1, pady=1)
        self.opbuttons.add('Grid')
        self.opbuttons.add('Smooth')
        # self.buttons.add('Symbols',    command=self.symbolsOnOff)
        # self.buttons.add('Animate',    command=animate)
        # buttons.add('Quit',       command=self.master.quit)
        self.docurves(self.entity.name, self.rel)

    def isEmpty(self):
        return len(self.vector_x) == 0
    
    def saveHistory(self):
        """Updates the history on the entities object (for saving
        purposes)"""
        self.entities.history['x'] = self.vector_x.get()
        if not self.entities.history.has_key('y'):
            self.entities.history['y'] = {}
        for name1,vectorDict in self.vector_y.items():
            if not self.entities.history['y'].has_key(name1):
                self.entities.history['y'][name1] = {}
            for name2,vector in vectorDict.items():
                self.entities.history['y'][name1][name2] = vector.get()

    def loadHistory(self,entities=None):
        """Updates the history vector based on the lists of values stored in
        the entities object"""
        if entities:
            self.entity = entities.members()[0]
            self.entities = entities
        if not self.isEmpty():
            self.deldata()
        if self.entities.history:
            map(lambda x,s=self:s.vector_x.append(x),
                self.entities.history['x'])
            for name1,vectorDict in self.entities.history['y'].items():
                for name2,vector in vectorDict.items():
                    map(lambda y,s=self,n1=name1,n2=name2:
                        s.vector_y[n1][n2].append(y),
                        self.entities.history['y'][name1][name2])
        else:
            # Initialize stored history
            self.entities.history = {}
            self.adddata(0)
        
    def doopt(self, label):
        if label is 'Smooth':
            self.smooth()
        elif label is 'Grid':
            self.g.grid_toggle()

        
    # Empties the plotting window
    def newFile(self):
        for name in self.g.element_names():
            self.g.element_delete(name)


    def trend(self,name,step,type):
        str = ""
        if step - 1 < 0:
            return str
        n = self.entities[name]
        self.entity = n
        if type == n._supportFeature:
                for c in self.entities.members():         # for each curve...
                    if n.name != c.name:
                        ydatanow=self.vector_y[n.name][c.name][step]
                        ydataprev=self.vector_y[n.name][c.name][step - 1]
                        if ydatanow - ydataprev < -0.1:
                            str = str + "Support for " + c.name + " dropping significantly.\n"
                        if ydatanow - ydataprev > 0.1:
                            str = str + "Support for " + c.name + " increasingly significantly.\n"
        else:
                if type in gstate:
                    ydatanow=self.vector_y[n.name][type][step]
                    ydataprev=self.vector_y[n.name][type][step - 1]
                    if ydatanow - ydataprev < -0.1:
                        str = str + n.name + "\'s " + type + " is dropping significantly.\n"
                    if ydatanow - ydataprev > 0.1:
                        str = str + n.name + "\'s " + type + " is increasingly significantly.\n"
        return str
        
    
    def docurves (self,name, type = None):
        n = self.entities[name]
                
        self.newFile()
        if type is None:
            type = self.rel
        else:
            self.rel = type
        self.entity = n
        self.scrotxt.clear()
        if type == n._supportFeature:
            for c in self.entities.members():         # for each curve...
                if n.name != c.name:
                    curvename = c.name                # make a curvename
                    self.g.line_create(curvename,     # and create the graph
                                       xdata=self.vector_x,
                                       ydata=self.vector_y[n.name][c.name],
                                       color=self.color[c.name],
                                       dashes=0,                
                                       linewidth=2,             
                                       symbol='plus')
            self.g.configure(title=n.name + ': Support for')          # enter a title
            if self.step > 0:
                self.scrotxt.component('text').insert('end', self.trend(n.name, self.step, n._supportFeature),('bolden'))
                
        else:
            for c in gstate:
                curvename = c
                self.g.line_create(curvename,     # and create the graph
                                   xdata=self.vector_x,
                                   ydata=self.vector_y[n.name][c],
                                   color=self.color[c],
                                   dashes=0,                
                                   linewidth=2,             
                                   symbol='plus')           
                if self.step > 0:
                    self.scrotxt.component('text').insert('end', self.trend(n.name, self.step, c),('bolden'))

            self.g.configure(title=n.name + ': State')          # enter a title


    def dorels (self,type):
        if type == 'State':
            type = 'state'
        if type == 'Support_For':
            type = entity._supportFeature
        
        self.docurves(self.entity.name, type)


    def adddata(self,step, types=None):
        self.step = step
        if not types:
            types = gstate + ['_liking']
        self.vector_x.append(step)
        for type in types:
            if type in ['_liking']:
                for n in self.entities.members():
                    for n2 in self.entities.members():
                        if n.name != n2.name:
                            try:
                                self.vector_y[n.name][n2.name].append(n.getBelief(n2,type).mean())
                            except KeyError,e:
                                print n.name,n2.name
##                                raise KeyError,e
            else:
                for n in self.entities.members():
                    try:
                        n.getStateTotal(type,self.entities)
                    except KeyError:
                        print "Missing state info:", n.name, type
                    else:
                        tot,exp = n.getStateTotal(type,self.entities)
                        mean = tot.mean()
                        self.vector_y[n.name][type].append(mean)
                        # print n.name, type, self.vector_y[n.name][type]
        self.saveHistory()
        tickList = (0.,1.)
        for i in range(1,len(self.vector_x)):
            tickList = tickList + (float(i+1),)
        self.g.xaxis_configure(majorticks=tuple(tickList))
        
    def deldata(self, typeList=None):
        if not typeList:
            typeList = gstate + ['_liking']
        del self.vector_x[:]
        for type in typeList:
            if type in ['_liking']:
                for n in self.entities.members():
                    for n2 in self.entities.members():
                        if n.name != n2.name:
                            del self.vector_y[n.name][n2.name][:]
            else:
                for n in self.entities.members():
                    del self.vector_y[n.name][type][:]


    def symbolsOnOff():
        global symbols
        symbols = not symbols
        
        for curvename in self.g.element_show():
            if symbols:
                self.g.element_configure(curvename, symbol='diamond')
            else:
                self.g.element_configure(curvename, symbol='')
            

    def smooth(self):
        if self.smoothing == 'linear': self.smoothing='quadratic'
        elif self.smoothing == 'quadratic': self.smoothing='natural'
        elif self.smoothing == 'natural': self.smoothing='step'
        else: self.smoothing = 'linear'

        for curvename in self.g.element_show():
            self.g.element_configure(curvename, smooth=self.smoothing)



if __name__ == '__main__':
    master = Tk()

    g = Pmw.Blt.Graph(master)
    g.pack(expand=1,fill=BOTH)
    vector_x = Pmw.Blt.Vector()
    vector_y = Pmw.Blt.Vector()

##    print vector_x[0]
##    print vector_x.get()
    g.line_create('Graph',
                  xdata=vector_x,
                  ydata=vector_y)
    g.xaxis_configure(min="0.0")
    g.xaxis_configure(subdivisions="1")
    tickList = (0.,1.)
    for i in range(1,len(vector_x)):
        tickList = tickList + (float(i+1),)
    g.xaxis_configure(majorticks=tuple(tickList))
    g.xaxis_configure(title="Time")
    g.xaxis_configure(stepsize="1.0")
    try:
        master.mainloop()
    except KeyboardInterrupt:
        pass
