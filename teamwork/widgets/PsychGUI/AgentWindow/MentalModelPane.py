import string
import threading
from Tkinter import Button,Scale
import tkMessageBox
import Pmw
from teamwork.widgets.PsychGUI.RadioBox import Rbox
from teamwork.widgets.cookbook import MultiListbox

class MentalModelFrame(Pmw.MegaWidget):
    
    def __init__(self,parent,entity,balloon,**kw):
        optiondefs = (
            ('balloon',None,Pmw.INITOPT),
            ('expert', False,self.setExpert),
            )
        self.defineoptions(kw, optiondefs)
        self.entity = entity
        Pmw.MegaWidget.__init__(self,parent)
        button = self.createcomponent('%s Lock Models' % \
                                      entity.ancestry(),
                                      (),None,Button,
                                      (self.interior(),))
        button.pack(side='top')
        sf = self.createcomponent('Models %s' % (entity.ancestry()),
                                  (),None,
                                  Pmw.ScrolledFrame,
                                  (self.interior(),),
                                  horizflex='elastic')
        boxList = []
        self.mentalwidgets = {}
        for e2 in entity.getEntities():
            e2 = entity.getEntity(e2)
            name = e2.ancestry().replace('_','')
            g = self.createcomponent('%sGroup' % (name),
                                     (),None,
                                     Pmw.Group,
                                     (sf.interior(),),
                                     tag_text = e2.name)
            g.pack(fill = 'x')
            if len(e2.models) > 0:
                rb = self.createcomponent('%s Models' % (name),
                                          (),None,Rbox,
                                          (g.interior(),),
                                          buttontype='radiobutton')
                rb.configure(command=lambda n,e2=e2:e2.setModel(n))
                for key in e2.models.keys():
                    rb.add(key)
                rb.pack(fill='x')
                if e2.model:
                    try:
                        rb.setvalue(e2.model['name'])
                    except KeyError:
                        # This model is not defined for this entity
                        # (can happen in generic society view)
                        pass
##                            raise KeyError,'%s has no model: %s' % \
##                                  (e2.ancestry(),e2.model['name'])
                key = entity.name + '_' + e2.name
                cmd = lambda e2=e2,rb=rb: \
                      rb.setvalue(e2.model['name'])
                self.mentalwidgets[key] = cmd
                boxList.append(rb)
            cmd = lambda e=e2.name,s=self: s.generate(e)
            rb = Button(g.interior(),text='Auto-Generate',command=cmd)
            rb.pack()
        sf.pack(expand = 1, fill = 'both')
        button.configure(command=lambda e=entity,b=button,l=boxList:\
                         setModelChange(e,b,l))
        setModelChange(entity,button,boxList,0)
        self.initialiseoptions()

    def setExpert(self):
        pass
    
    def recreate_mental(self):
        for key in self.mentalwidgets.keys():
            try:
                apply(self.mentalwidgets[key],())
            except TypeError:
                # No mental model set here...ignore
                pass

    def generate(self,entity):
        label = '%s Dialog' % (entity)
        try:
            dialog = self.component(label)
        except KeyError:
            dialog = self.createcomponent(label,(),None,ModelGenerator,
                                          (self.interior(),
                                           self.entity.getEntity(entity)),
                                          title='Auto-Generate Mental Models',
                                          buttons=('Done','Apply'),
                                          defaultbutton='Done',
                                          )
        dialog.activate()
        
def setModelChange(entity,button,radioList,toggle=1):
    if toggle:
        entity.modelChange = not entity.modelChange
    if entity.modelChange:
        button.configure(text='Lock')
    else:
        button.configure(text='Unlock')
    for rBox in radioList:
        if entity.modelChange:
            rBox.enable()
        else:
            rBox.disable()

class ModelGenerator(Pmw.Dialog):
    def __init__(self,parent,entity,**kw):
        optiondefs = (
            ('initialgranularity', 11,   Pmw.INITOPT),
            ('minimumgranularity', 2,    Pmw.INITOPT),
            ('maximumgranularity', 100,  Pmw.INITOPT),
            ('columnWidth',        12,   Pmw.INITOPT),
            ('command',            self.execute, Pmw.INITOPT),
            ('messageFont', ('Courier',10,'normal'), Pmw.INITOPT),
            )
        self.defineoptions(kw, optiondefs)
        self.entity = entity
        Pmw.Dialog.__init__(self,parent)
##         widget = Label(self.interior(),
##                        text='Number of values to try for each goal:',
##                        borderwidth=3,relief='ridge',
##                        )
##         widget.pack(side='top',fill='x')
        widget = self.createcomponent('Granularity',
                                      (),None,Scale,
                                      (self.interior(),),
                                      label='Number of values to try for each goal',
                                      from_=self['minimumgranularity'],
                                      to=self['maximumgranularity'],
                                      orient='horizontal',
                                      )
        widget.set(self['initialgranularity'])
        widget.pack(side='top',fill='x')
        goals = self.entity.getGoals()
        goals.sort()
        columns = [('\nModel\n',5)]
        for goal in goals:
            if goal.type == 'state':
                entity = string.join(goal.entity,', ')
            else:
                entity = 'Anyone'
            columns.append(('%s\n%s\n%s' % \
                            (goal.direction[:self['columnWidth']],
                             goal.key[:self['columnWidth']],
                             entity[:self['columnWidth']]),
                            self['columnWidth']+1))
        columns.append(('\nStatus\n',12))
        widget = self.createcomponent('Message',(),None,MultiListbox,
                                      (self.interior(),columns),
                                      )
        widget.pack(side='top',fill='both',expand='yes')
        self.initialiseoptions()
        # Threading stuff
        self.thread = None
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.results = {}
        self.root = self.winfo_toplevel()

    def execute(self,cmd):
        if cmd in ['OK','Apply']:
            if self.thread:
                self.event.set()
            else:
                # Update the relevant widgets
                box = self.component('buttonbox')
                box.component('Done').configure(state='disabled')
                box.component('Apply').configure(text='Stop')
                self.component('Message').delete(0,'end')
                # Extract the granularity across each goal dimension
                granularity = self.component('Granularity').get()
                goals = self.entity.getGoals()
                goals.sort()
                # Construct the set of possible points in goal space
                weightList = self.entity.generateSpace(granularity)
                if not self.entity.reachable(weightList,granularity):
                    raise UserWarning
                for index in range(len(weightList)):
                    weighting = weightList[index]
                    element = [index]
                    for goal in goals:
                        element.append('%5.3f' % (weighting[goal]))
                    element.append('')
                    self.component('Message').insert('end',element)
                # Set up threading
                self.event.clear()
                self.queue = []
                self.result = {}
                self.thread = threading.Thread(target=self.entity.clusterSpace,
                                               args=(granularity,weightList,
                                                     self.message,self.done,
                                                     self.event))
                self.root.after(100,self.log)
                self.thread.start()
        elif cmd == 'Help':
            tkMessageBox.showinfo('Auto-Generate Help',
                                  'Sorry, you\'re on your own.')
        if cmd in ['OK','Cancel','Done']:
            self.deactivate()

    def done(self,results):
        self.results = results
        self.event.set()
        
    def message(self,msg):
        self.lock.acquire()
        if isinstance(msg,list):
            msg.reverse()
            self.queue += msg
        else:
            self.queue.insert(0,msg)
        self.lock.release()

    def log(self):
        widget = self.component('Message')
        self.lock.acquire()
        while len(self.queue) > 0:
            line,msg = self.queue.pop()
            if line >= 0:
                self.setMsg(line,msg)
                widget.see(line)
        self.lock.release()
        if self.event.isSet():
            self.root.after(20,self.enable)
        else:
            self.root.after(1,self.log)

    def setMsg(self,line,msg):
        widget = self.component('Message')
        element = widget.get(line)[:-1]+[msg]
        widget.delete(line,line)
        widget.insert(line,element)
        
    def enable(self):
        box = self.component('buttonbox')
        box.component('Done').configure(state='normal')
        box.component('Apply').configure(text='Apply')
        self.thread.join()
        self.thread = None
        if self.results:
            unique = self.results.keys()
            unique.sort()
            unique.reverse()
##             last = unique[0]
##             widget = self.component('Message')
##             widget.delete(last+1,'end')
##             for index in unique[1:]:
##                 print self.results[last].keys()
##                 myNeighbors = filter(lambda k:k != '_policy',
##                                      self.results[last].keys())
##                 myNeighbors.sort()
##                 self.setMsg(last,str(myNeighbors))
##                 self.component('Message').delete(index+1,last-1)
##                 last = index
##             myNeighbors = filter(lambda k:k != '_policy',
##                                  self.results[last].keys())
##             myNeighbors.sort()
##             self.setMsg(0,str(myNeighbors))
        else:
            self.component('Message').delete(0,'end')
        
