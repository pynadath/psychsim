#We need to do try/except imports just in case the matplotlib module isn't available
#Programs can check for availability by checking the graphAvailable variable
graphAvailable = True
try:
    import pylab
    from matplotlib.ticker import FuncFormatter, MultipleLocator
    from matplotlib import rcParams
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
    from matplotlib.font_manager import FontProperties
    rcParams['toolbar'] = 'toolbar2'
    rcParams['backend'] = 'TkAgg'
except ImportError:
    graphAvailable = False

class TkGraphWindow:
    def __init__(self,win,entities):
        import Tkinter as Tk

        self.gw = win

        #Create the figure and subplot and add it to the window
        figure = Figure(figsize=(5,4), dpi=100)
        plot = figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(figure,master=win.frame)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=Tk.TOP,fill=Tk.BOTH,expand=1)
        toolbar = NavigationToolbar2TkAgg(self.canvas,win.frame)
        toolbar.update()
        self.canvas._tkcanvas.pack(side=Tk.TOP,fill=Tk.BOTH,expand=1)

        #Create the graph object
        self.graph = Graph(entities,figure=figure)
        
        #Now do the initial update
        self.updateGraphWindow()

    def updateGraphWindow(self):
        self.graph.plot()
        self.canvas.draw()
        self.gw.update()


class Graph:
    def __init__(self,entities,figure=None):

        #Initialize some stuff  
        self.availableColors = ['b','g','r','c','m','y','k','w']
        self.availableSymbols = ['o','^','v','<','>','s','+','x','D','d','1','2','3','4','h','H','p','|','_']
        self.usedSymbols = []
        self.startStyle='b--o'
        self.stateHistory = {}
        self.actionHistory = ["Initial State"]
        self.entities = entities
        self.figure = figure
        self.initialized = False

        #Initialize the figure if we have to
        if not figure:
            pylab.subplot(111)
            self.figure = pylab.gcf()

        #initialize the history
        statevector = self.entities.getState().domain()[0]
        for key in statevector.keys():
            if len(key) > 0:
                self.stateHistory[str(key)] = {'val':[], 'style':self.getNextPointStyle()}

        #maybe assert that the actionHistory == stateHistory length 
        self.loadHistory()

        
    def setupGraphAttributes(self):
        ax = self.figure.gca()

        #set up the locator and formatters to control the x-axis ticks
        locator = MultipleLocator(base=1)
        ax.xaxis.set_major_formatter(FuncFormatter(self.xAxisFormatter))
        ax.xaxis.set_major_locator(locator)
        
        #set the title and other things
        ax.legend(loc='best',prop=FontProperties(size='xx-small'),numpoints=2,handlelen=.03,labelsep=.002)
        labels = ax.get_xticklabels()
        ax.set_title("State change over time")
        ax.set_xlabel("Step")
        ax.set_ylabel("State Value")
        pylab.setp(labels, 'rotation', 45, fontsize=8)

    def loadHistory(self):
        #reset the state and action history
        self.actionHistory = ["Initial State"]
        for dict in self.stateHistory.values():
            dict['val'] = []

        #Load the agent's history if there is any into a format more suitable for our purposes
        for history in self.entities.getHistory():
            statevector = history['previousState']
            action = history['action']
            self.actionHistory.append(str(action))
            for key in statevector.keys():
                if len(key) != 0:
                    self.stateHistory[str(key)]['val'].append(statevector[key])

        #Don't forget to add the current state
        statevector = self.entities.getState().domain()[0]
        for key in statevector.keys():
            if len(key) != 0:
                self.stateHistory[str(key)]['val'].append(statevector[key])

    def plot(self):

        #check to see if we have to load the history
        self.loadHistory()

        ax = self.figure.gca()

        for state,dict in self.stateHistory.items():
            ax.plot(range(len(dict['val'])),dict['val'],dict['style'],label=state)

        if not self.initialized:
            self.setupGraphAttributes()
            self.initialized = True

        #Set up the axis size
        ax.set_xlim(xmin=0)
        ax.set_ylim(ymin=-1,ymax=1)

    def xAxisFormatter(self,x,pos):
        if x < 0 or x >= len(self.actionHistory):
            return ""
        else:
            return self.actionHistory[int(x)]

    def getNextPointStyle(self):
        color = self.availableColors.pop(0)
        self.availableColors.append(color)
        if len(self.availableSymbols) > 0:
            symbol = self.availableSymbols.pop(0)
            self.usedSymbols.append(symbol)
        else:
            self.availableSymbols.extend(self.usedSymbols)
            self.usedSymbols = []
            symbol = self.availableSymbols.pop(0)
            if self.startStyle == "%s--%s" % (color,symbol):
                self.availableSymbols.append(symbol)
                symbol = self.availableSymbols.pop(0)
                self.startStyle = "%s--%s" % (color,symbol)
            self.usedSymbols.append(symbol)
        return "%s--%s" % (color,symbol)

if __name__ == '__main__':
    from teamwork.multiagent.GenericSociety import GenericSociety
    from teamwork.multiagent.sequential import SequentialAgents
    import teamwork.examples.school.SchoolClasses as classModule
    from teamwork.multiagent.Historical import HistoricalAgents

    #We need to get a scenario
    society = GenericSociety()
    society.importDict(classModule.classHierarchy)

    #Instantiate the agents 
    victim = society.instantiate("Victim", "Victim")
    onlooker = society.instantiate("Onlooker", "Onlooker")
    bully = society.instantiate("Bully", "Bully")
    teacher = society.instantiate("Teacher", "Teacher")

    #Set up the relationships
    victim.relationships['victim'] = ['Victim']
    onlooker.relationships['victim'] = ['Victim']
    bully.relationships['victim'] = ['Victim']

    #Instantiate the scenario
    entities = [victim, onlooker, bully, teacher]
    agents = SequentialAgents(entities)
    agents.applyDefaults()
    agents.compileDynamics()

    #for debugging purposes, I have a specially made history thingy
    agents.__class__ = HistoricalAgents

    #Create the graph object
    graph = Graph(agents)
    for i in range(3):
        agents.microstep()
    graph.plot()
    agents.microstep()
    graph.plot()
    pylab.show()
